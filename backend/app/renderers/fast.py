from __future__ import annotations

import cv2
import numpy as np

from app.domain.contracts import Keypoint


def _visible_map(keypoints: list[Keypoint], width: int, height: int) -> dict[str, tuple[int, int]]:
    return {
        point.name: (int(point.x * width), int(point.y * height))
        for point in keypoints if point.visible
    }


class FastAvatarRenderer:
    """A fast, dependency-light renderer designed to be replaced by custom art."""

    id = "fast"

    def available(self) -> tuple[bool, str | None]:
        return True, None

    def render(self, image: np.ndarray, keypoints: list[Keypoint], edges: list[tuple[str, str]]) -> np.ndarray:
        height, width = image.shape[:2]
        canvas = np.zeros((height, width, 3), dtype=np.uint8)
        # Layered cinematic background.
        yy, xx = np.mgrid[:height, :width]
        glow = np.clip(1 - np.sqrt(((xx - width * .52) / width) ** 2 + ((yy - height * .42) / height) ** 2) * 1.8, 0, 1)
        canvas[..., 0] = 18 + (glow * 27).astype(np.uint8)
        canvas[..., 1] = 11 + (glow * 18).astype(np.uint8)
        canvas[..., 2] = 28 + (glow * 44).astype(np.uint8)
        points = _visible_map(keypoints, width, height)
        for start, end in edges:
            if start not in points or end not in points:
                continue
            a, b = points[start], points[end]
            cv2.line(canvas, a, b, (226, 91, 52), 28, cv2.LINE_AA)
            cv2.line(canvas, a, b, (250, 186, 74), 16, cv2.LINE_AA)
        # A stylized torso makes the output read as an avatar, not a stick figure.
        required = [points.get(name) for name in ("l_shoulder", "r_shoulder", "r_hip", "l_hip")]
        if all(required):
            torso = np.array(required, np.int32)
            overlay = canvas.copy()
            cv2.fillConvexPoly(overlay, torso, (167, 48, 119), cv2.LINE_AA)
            canvas = cv2.addWeighted(overlay, .78, canvas, .22, 0)
            cv2.polylines(canvas, [torso], True, (255, 136, 219), 4, cv2.LINE_AA)
        head = points.get("head") or points.get("nose")
        if head:
            body_span = max(14, int(min(width, height) * .035))
            cv2.circle(canvas, head, body_span + 6, (87, 30, 137), -1, cv2.LINE_AA)
            cv2.circle(canvas, head, body_span, (225, 87, 179), -1, cv2.LINE_AA)
            cv2.ellipse(canvas, head, (body_span // 2, body_span // 3), 0, 0, 180, (255, 224, 126), 3, cv2.LINE_AA)
        for point in points.values():
            cv2.circle(canvas, point, 9, (255, 247, 210), -1, cv2.LINE_AA)
            cv2.circle(canvas, point, 14, (241, 100, 204), 3, cv2.LINE_AA)
        return canvas


class SkeletonRenderer:
    def render(self, image: np.ndarray, keypoints: list[Keypoint], edges: list[tuple[str, str]]) -> np.ndarray:
        output = image.copy()
        height, width = output.shape[:2]
        points = _visible_map(keypoints, width, height)
        overlay = output.copy()
        for start, end in edges:
            if start in points and end in points:
                cv2.line(overlay, points[start], points[end], (255, 174, 48), 7, cv2.LINE_AA)
                cv2.line(overlay, points[start], points[end], (255, 66, 188), 3, cv2.LINE_AA)
        output = cv2.addWeighted(overlay, .88, output, .12, 0)
        for point in points.values():
            cv2.circle(output, point, 8, (255, 255, 255), -1, cv2.LINE_AA)
            cv2.circle(output, point, 13, (225, 56, 190), 3, cv2.LINE_AA)
        return output

