from __future__ import annotations

import asyncio
import hashlib
import json
import math
import time
import uuid
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np

from app.config import Settings
from app.domain.contracts import Keypoint
from app.domain.exercise import ExerciseCompareResult, ExerciseFrame, ExerciseInstructor, ExerciseSummary, JointFeedback
from app.services.inference import InferenceService, NoPersonDetectedError


CORE_JOINTS = [
    "nose", "head", "l_shoulder", "r_shoulder", "l_elbow", "r_elbow", "l_wrist", "r_wrist",
    "l_hip", "r_hip", "l_knee", "r_knee", "l_ankle", "r_ankle",
]
MATCH_THRESHOLD = 0.18
INITIAL_MATCH_SCORE = 40


def _visible(points: Iterable[Keypoint]) -> dict[str, Keypoint]:
    return {point.name: point for point in points if point.visible and point.confidence >= 0.2}


def _center(points: dict[str, Keypoint]) -> tuple[float, float]:
    centers: list[tuple[float, float]] = []
    for a, b in (("l_hip", "r_hip"), ("l_shoulder", "r_shoulder")):
        if a in points and b in points:
            centers.append(((points[a].x + points[b].x) / 2, (points[a].y + points[b].y) / 2))
    if centers:
        return (sum(item[0] for item in centers) / len(centers), sum(item[1] for item in centers) / len(centers))
    values = list(points.values())
    if not values:
        return (0.5, 0.5)
    return (sum(point.x for point in values) / len(values), sum(point.y for point in values) / len(values))


def _scale(points: dict[str, Keypoint]) -> float:
    pairs = [("l_shoulder", "r_shoulder"), ("l_hip", "r_hip"), ("l_shoulder", "l_hip"), ("r_shoulder", "r_hip")]
    distances: list[float] = []
    for a, b in pairs:
        if a in points and b in points:
            distances.append(math.dist((points[a].x, points[a].y), (points[b].x, points[b].y)))
    if distances:
        return max(0.08, sum(distances) / len(distances))
    values = list(points.values())
    if len(values) >= 2:
        xs = [point.x for point in values]
        ys = [point.y for point in values]
        return max(0.08, max(max(xs) - min(xs), max(ys) - min(ys)))
    return 0.2


def normalized_pose(points: list[Keypoint]) -> dict[str, tuple[float, float]]:
    visible = _visible(points)
    center_x, center_y = _center(visible)
    scale = _scale(visible)
    return {
        name: ((point.x - center_x) / scale, (point.y - center_y) / scale)
        for name, point in visible.items()
    }


def compare_keypoints(instructor: list[Keypoint], user: list[Keypoint]) -> tuple[float, list[JointFeedback]]:
    instructor_norm = normalized_pose(instructor)
    user_norm = normalized_pose(user)
    feedback: list[JointFeedback] = []
    for name in CORE_JOINTS:
        if name not in instructor_norm or name not in user_norm:
            continue
        distance = math.dist(instructor_norm[name], user_norm[name])
        joint_score = max(0, min(100, 100 * (1 - distance / (MATCH_THRESHOLD * 2.2))))
        feedback.append(JointFeedback(
            name=name,
            distance=round(distance, 4),
            score=round(joint_score, 1),
            close=distance <= MATCH_THRESHOLD,
            instructor=instructor_norm[name],
            user=user_norm[name],
        ))
    if not feedback:
        return 0, []
    score = sum(item.score for item in feedback) / len(feedback)
    return round(score, 1), feedback


class ExerciseService:
    def __init__(self, inference: InferenceService, settings: Settings):
        self.inference = inference
        self.settings = settings
        self.root = settings.runtime_dir / "exercises"
        self.cache_dir = self.root / "cache"
        self.upload_dir = self.root / "uploads"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.instructors: dict[str, ExerciseInstructor] = {}

    def list_instructors(self) -> list[ExerciseInstructor]:
        loaded = list(self.instructors.values())
        known = {item.id for item in loaded}
        for manifest in self.cache_dir.glob("*/manifest.json"):
            try:
                instructor = self._load_manifest(manifest.parent, state="completed", cached=True)
            except Exception:
                continue
            if instructor.id not in known:
                loaded.append(instructor)
        return sorted(loaded, key=lambda item: item.filename.lower())

    async def submit(self, filename: str, model_id: str, payload: bytes, render_fps: float | None = None) -> ExerciseInstructor:
        digest = hashlib.sha256(payload).hexdigest()
        cached_dir = self.cache_dir / digest
        if (cached_dir / "manifest.json").exists():
            instructor = self._load_manifest(cached_dir, state="completed", cached=True)
            self.instructors[instructor.id] = instructor
            return instructor
        job_id = digest[:16] + "-" + uuid.uuid4().hex[:8]
        suffix = Path(filename).suffix or ".mp4"
        source = self.upload_dir / f"{job_id}{suffix}"
        source.write_bytes(payload)
        instructor = ExerciseInstructor(
            id=job_id,
            filename=filename or "exercise-video.mp4",
            modelId=model_id,
            state="queued",
            progress=0,
            fps=max(1.0, min(float(render_fps or 6), float(self.settings.maximum_video_fps))),
            cached=False,
        )
        self.instructors[job_id] = instructor
        asyncio.create_task(asyncio.to_thread(self._process, instructor, source, cached_dir))
        return instructor

    def get(self, instructor_id: str) -> ExerciseInstructor | None:
        if instructor_id in self.instructors:
            return self.instructors[instructor_id]
        manifest = self.cache_dir / instructor_id / "manifest.json"
        if manifest.exists():
            instructor = self._load_manifest(manifest.parent, state="completed", cached=True)
            self.instructors[instructor.id] = instructor
            return instructor
        for manifest in self.cache_dir.glob("*/manifest.json"):
            try:
                instructor = self._load_manifest(manifest.parent, state="completed", cached=True)
            except Exception:
                continue
            if instructor.id == instructor_id:
                self.instructors[instructor.id] = instructor
                return instructor
        return None

    def compare(self, instructor_id: str, frame_index: int, image: np.ndarray, model_id: str) -> ExerciseCompareResult:
        instructor = self.get(instructor_id)
        if instructor is None or instructor.state != "completed" or not instructor.frames:
            raise KeyError("Exercise instructor is not ready.")
        frame = instructor.frames[min(max(0, frame_index), len(instructor.frames) - 1)]
        result = self.inference.infer(image, model_id)
        score, feedback = compare_keypoints(frame.keypoints, result.keypoints)
        colored = self._render_feedback_skeleton(image, result.keypoints, self.inference.registry.definitions[model_id].edges, feedback)
        return ExerciseCompareResult(
            instructorId=instructor.id,
            frameIndex=frame.index,
            matchedInitial=score >= INITIAL_MATCH_SCORE,
            score=score,
            detectedJoints=len(feedback),
            jointFeedback=feedback,
            userSkeleton=self.inference.media.encode_data_url(colored),
            message=None if feedback else "No comparable joints were visible.",
        )

    def _render_feedback_skeleton(self, image: np.ndarray, keypoints: list[Keypoint], edges: list[tuple[str, str]], feedback: list[JointFeedback]) -> np.ndarray:
        output = image.copy()
        height, width = output.shape[:2]
        points = {point.name: (int(point.x * width), int(point.y * height)) for point in keypoints if point.visible}
        status = {item.name: item.close for item in feedback}
        overlay = output.copy()
        for start, end in edges:
            if start in points and end in points:
                close_count = int(status.get(start, False)) + int(status.get(end, False))
                color = (65, 225, 122) if close_count == 2 else (55, 67, 240)
                cv2.line(overlay, points[start], points[end], color, 7, cv2.LINE_AA)
        output = cv2.addWeighted(overlay, .86, output, .14, 0)
        for name, point in points.items():
            if name not in status:
                color = (210, 210, 220)
            else:
                color = (65, 235, 130) if status[name] else (45, 55, 245)
            cv2.circle(output, point, 12, color, -1, cv2.LINE_AA)
            cv2.circle(output, point, 17, (255, 255, 255), 2, cv2.LINE_AA)
        return output

    def frame_path(self, instructor_id: str, frame_index: int) -> Path | None:
        instructor = self.get(instructor_id)
        if instructor is None or instructor.state != "completed" or not instructor.frames:
            return None
        frame = instructor.frames[min(max(0, frame_index), len(instructor.frames) - 1)]
        for manifest in self.cache_dir.glob("*/manifest.json"):
            try:
                payload = json.loads(manifest.read_text(encoding="utf-8"))
            except Exception:
                continue
            if payload.get("id") != instructor.id:
                continue
            path = manifest.parent / "frames" / f"{frame.index:04d}.webp"
            return path if path.exists() else None
        return None

    def summarize(self, samples: list[dict]) -> ExerciseSummary:
        joint_scores: dict[str, list[float]] = {}
        total: list[float] = []
        for sample in samples:
            score = float(sample.get("score", 0))
            total.append(score)
            for joint in sample.get("jointFeedback", []):
                name = joint.get("name")
                if name:
                    joint_scores.setdefault(name, []).append(float(joint.get("score", 0)))
        ranked = [
            JointFeedback(name=name, distance=0, score=round(sum(values) / len(values), 1), close=(sum(values) / len(values)) >= 70)
            for name, values in joint_scores.items() if values
        ]
        ranked.sort(key=lambda item: item.score)
        return ExerciseSummary(
            averageScore=round(sum(total) / len(total), 1) if total else 0,
            improveJoints=ranked[:2],
            bestJoints=list(reversed(ranked[-2:])),
            samples=len(total),
        )

    def _process(self, instructor: ExerciseInstructor, source: Path, cached_dir: Path) -> None:
        capture = cv2.VideoCapture(str(source))
        frames_dir = cached_dir / "frames"
        try:
            instructor.state = "processing"
            if not capture.isOpened():
                raise ValueError("The instructor video could not be opened.")
            source_fps = capture.get(cv2.CAP_PROP_FPS) or 24
            total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            max_source_frames = int(min(total or source_fps * self.settings.maximum_video_seconds, source_fps * self.settings.maximum_video_seconds))
            step = max(1, round(source_fps / instructor.fps))
            cached_dir.mkdir(parents=True, exist_ok=True)
            frames_dir.mkdir(parents=True, exist_ok=True)
            frames: list[ExerciseFrame] = []
            frame_index = 0
            output_index = 0
            while frame_index < max_source_frames:
                ok, frame = capture.read()
                if not ok:
                    break
                if frame_index % step == 0:
                    try:
                        result = self.inference.infer(frame, instructor.model_id)
                    except NoPersonDetectedError:
                        frame_index += 1
                        continue
                    skeleton = self.inference.media.decode_data_url(result.skeleton)
                    skeleton_path = frames_dir / f"{output_index:04d}.webp"
                    cv2.imwrite(str(skeleton_path), skeleton, [cv2.IMWRITE_WEBP_QUALITY, 84])
                    frames.append(ExerciseFrame(
                        index=output_index,
                        timestamp=round(frame_index / source_fps, 3),
                        keypoints=result.keypoints,
                        skeletonUrl=f"/api/v1/exercise/instructors/{instructor.id}/frames/{output_index}/skeleton",
                    ))
                    output_index += 1
                frame_index += 1
                instructor.progress = min(99, frame_index / max(1, max_source_frames) * 100)
            if not frames:
                raise ValueError("No usable instructor poses were found in the video.")
            instructor.frames = frames
            instructor.frame_count = len(frames)
            instructor.duration = frames[-1].timestamp if frames else 0
            instructor.progress = 100
            instructor.state = "completed"
            self._save_manifest(instructor, cached_dir)
        except Exception as exc:
            instructor.state = "failed"
            instructor.error = f"{type(exc).__name__}: {exc}"
        finally:
            capture.release()
            source.unlink(missing_ok=True)

    def _save_manifest(self, instructor: ExerciseInstructor, cached_dir: Path) -> None:
        payload = instructor.model_dump(mode="json", by_alias=True)
        payload["cached"] = True
        payload["state"] = "completed"
        (cached_dir / "manifest.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _load_manifest(self, cached_dir: Path, state: str, cached: bool) -> ExerciseInstructor:
        payload = json.loads((cached_dir / "manifest.json").read_text(encoding="utf-8"))
        payload["state"] = state
        payload["cached"] = cached
        return ExerciseInstructor.model_validate(payload)
