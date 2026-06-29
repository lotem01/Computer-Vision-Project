from __future__ import annotations

import asyncio
from pathlib import Path

import cv2
from PIL import Image

from app.config import Settings
from app.infrastructure.job_store import InMemoryJobStore, VideoJob
from app.services.inference import InferenceService, NoPersonDetectedError


class VideoService:
    def __init__(self, inference: InferenceService, jobs: InMemoryJobStore, settings: Settings):
        self.inference = inference
        self.jobs = jobs
        self.settings = settings
        self.job_dir = settings.runtime_dir / "jobs"
        self.job_dir.mkdir(parents=True, exist_ok=True)

    async def submit(self, filename: str, model_id: str, payload: bytes, render_fps: float | None = None) -> VideoJob:
        job = self.jobs.create(filename, model_id)
        source = self.job_dir / f"{job.id}-source{Path(filename).suffix or '.mp4'}"
        source.write_bytes(payload)
        asyncio.create_task(asyncio.to_thread(self._process, job.id, source, render_fps))
        return job

    def _process(self, job_id: str, source: Path, render_fps: float | None = None) -> None:
        avatar_output = self.job_dir / f"{job_id}-avatar.mp4"
        skeleton_output = self.job_dir / f"{job_id}-skeleton.mp4"
        avatar_preview = self.job_dir / f"{job_id}-avatar-preview.webp"
        skeleton_preview = self.job_dir / f"{job_id}-skeleton-preview.webp"
        capture = cv2.VideoCapture(str(source))
        writers: dict[str, cv2.VideoWriter] = {}
        preview_frames: dict[str, list[Image.Image]] = {"avatar": [], "skeleton": []}
        try:
            if not capture.isOpened():
                raise ValueError("The video could not be opened.")
            source_fps = capture.get(cv2.CAP_PROP_FPS) or 24
            total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            max_source_frames = int(min(total or source_fps * self.settings.maximum_video_seconds, source_fps * self.settings.maximum_video_seconds))
            target_fps = max(1.0, min(float(render_fps or self.settings.maximum_video_fps), float(self.settings.maximum_video_fps)))
            step = max(1, round(source_fps / target_fps))
            output_fps = min(source_fps, target_fps)
            preview_fps = min(8, max(1, output_fps))
            preview_step = max(1, round(output_fps / preview_fps))
            preview_duration_ms = max(1, round(1000 / preview_fps))
            max_preview_frames = 240
            self.jobs.update(job_id, state="processing")
            frame_index = 0
            written = 0

            def writer_for(kind: str, path: Path, frame):
                if kind in writers:
                    return writers[kind]
                height, width = frame.shape[:2]
                writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), output_fps, (width, height))
                if not writer.isOpened():
                    raise ValueError(f"Could not open the {kind} video writer.")
                writers[kind] = writer
                return writer

            def remember_preview(kind: str, frame) -> None:
                frames = preview_frames[kind]
                if written % preview_step != 0 or len(frames) >= max_preview_frames:
                    return
                height, width = frame.shape[:2]
                max_width = 720
                if width > max_width:
                    scale = max_width / width
                    frame = cv2.resize(frame, (max_width, max(1, round(height * scale))), interpolation=cv2.INTER_AREA)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append(Image.fromarray(rgb))

            def save_preview(kind: str, path: Path) -> str | None:
                frames = preview_frames[kind]
                if not frames:
                    return None
                first, *rest = frames
                first.save(
                    path,
                    format="WEBP",
                    save_all=True,
                    append_images=rest,
                    duration=preview_duration_ms,
                    loop=0,
                    quality=82,
                    method=4,
                )
                for frame in frames:
                    frame.close()
                return f"/api/v1/video-jobs/{job_id}/preview/{kind}"

            while frame_index < max_source_frames:
                job = self.jobs.get(job_id)
                if job is None or job.cancelled:
                    return
                ok, frame = capture.read()
                if not ok:
                    break
                if frame_index % step == 0:
                    try:
                        result = self.inference.infer(frame, job.model_id)
                        avatar = self.inference.media.decode_data_url(result.avatar)
                        skeleton = self.inference.media.decode_data_url(result.skeleton)
                    except NoPersonDetectedError:
                        avatar = frame
                        skeleton = frame
                    writer_for("avatar", avatar_output, avatar).write(avatar)
                    writer_for("skeleton", skeleton_output, skeleton).write(skeleton)
                    remember_preview("avatar", avatar)
                    remember_preview("skeleton", skeleton)
                    written += 1
                frame_index += 1
                self.jobs.update(job_id, progress=min(99, frame_index / max(1, max_source_frames) * 100))
            if not writers or written == 0:
                raise ValueError("No usable frames were found in the video.")
            for writer in writers.values():
                writer.release()
            writers.clear()
            avatar_url = f"/api/v1/video-jobs/{job_id}/result/avatar"
            skeleton_url = f"/api/v1/video-jobs/{job_id}/result/skeleton"
            avatar_preview_url = save_preview("avatar", avatar_preview)
            skeleton_preview_url = save_preview("skeleton", skeleton_preview)
            self.jobs.update(
                job_id,
                state="completed",
                progress=100,
                result_url=avatar_url,
                avatar_url=avatar_url,
                skeleton_url=skeleton_url,
                avatar_preview_url=avatar_preview_url,
                skeleton_preview_url=skeleton_preview_url,
                avatar_preview_kind="image" if avatar_preview_url else None,
                skeleton_preview_kind="image" if skeleton_preview_url else None,
            )
        except Exception as exc:
            self.jobs.update(job_id, state="failed", error=f"{type(exc).__name__}: {exc}")
        finally:
            capture.release()
            for writer in writers.values():
                writer.release()
            source.unlink(missing_ok=True)
