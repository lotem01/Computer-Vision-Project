from __future__ import annotations

import math

import cv2
import numpy as np

from app.domain.contracts import Keypoint


Point = tuple[int, int]
Color = tuple[int, int, int]


def _visible_map(keypoints: list[Keypoint], width: int, height: int) -> dict[str, Point]:
    return {
        point.name: (int(point.x * width), int(point.y * height))
        for point in keypoints if point.visible
    }


def _mid(a: Point, b: Point) -> Point:
    return ((a[0] + b[0]) // 2, (a[1] + b[1]) // 2)


def _distance(a: Point, b: Point) -> float:
    return float(np.hypot(a[0] - b[0], a[1] - b[1]))


def _angle(a: Point, b: Point) -> float:
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))


def _blend(canvas: np.ndarray, overlay: np.ndarray, alpha: float) -> None:
    cv2.addWeighted(overlay, alpha, canvas, 1 - alpha, 0, canvas)


def _soft_background(width: int, height: int) -> np.ndarray:
    yy, xx = np.mgrid[:height, :width]
    glow = np.clip(1 - np.sqrt(((xx - width * .5) / width) ** 2 + ((yy - height * .45) / height) ** 2) * 1.55, 0, 1)
    canvas = np.zeros((height, width, 3), dtype=np.uint8)
    canvas[..., 0] = 17 + (glow * 22).astype(np.uint8)
    canvas[..., 1] = 18 + (glow * 26).astype(np.uint8)
    canvas[..., 2] = 29 + (glow * 42).astype(np.uint8)
    for y in range(0, height, max(28, height // 22)):
        cv2.line(canvas, (0, y), (width, y), (31, 33, 48), 1, cv2.LINE_AA)
    return canvas


def _segment_polygon(a: Point, b: Point, radius_a: int, radius_b: int) -> np.ndarray:
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = max(1.0, math.hypot(dx, dy))
    nx, ny = -dy / length, dx / length
    return np.array([
        (int(a[0] + nx * radius_a), int(a[1] + ny * radius_a)),
        (int(b[0] + nx * radius_b), int(b[1] + ny * radius_b)),
        (int(b[0] - nx * radius_b), int(b[1] - ny * radius_b)),
        (int(a[0] - nx * radius_a), int(a[1] - ny * radius_a)),
    ], np.int32)


def _draw_body_segment(
    canvas: np.ndarray,
    a: Point | None,
    b: Point | None,
    radius_a: int,
    radius_b: int,
    fill: Color,
    outline: Color,
    highlight: Color | None = None,
) -> None:
    if a is None or b is None:
        return
    polygon = _segment_polygon(a, b, radius_a, radius_b)
    cv2.fillConvexPoly(canvas, polygon, outline, cv2.LINE_AA)
    inner = _segment_polygon(a, b, max(2, radius_a - 4), max(2, radius_b - 4))
    cv2.fillConvexPoly(canvas, inner, fill, cv2.LINE_AA)
    cv2.circle(canvas, a, max(2, radius_a - 4), fill, -1, cv2.LINE_AA)
    cv2.circle(canvas, b, max(2, radius_b - 4), fill, -1, cv2.LINE_AA)
    if highlight:
        cv2.line(canvas, a, b, highlight, max(2, min(radius_a, radius_b) // 4), cv2.LINE_AA)


def _draw_rotated_ellipse(canvas: np.ndarray, center: Point, axes: tuple[int, int], angle: float, fill: Color, outline: Color | None = None, thickness: int = 3) -> None:
    if outline:
        cv2.ellipse(canvas, center, (axes[0] + thickness, axes[1] + thickness), angle, 0, 360, outline, -1, cv2.LINE_AA)
    cv2.ellipse(canvas, center, axes, angle, 0, 360, fill, -1, cv2.LINE_AA)


def _head_center(points: dict[str, Point], shoulder_span: int, neck: Point | None) -> Point | None:
    face = [points[name] for name in ("l_eye", "r_eye", "l_ear", "r_ear", "nose") if name in points]
    if len(face) >= 2:
        center = tuple(np.mean(np.array(face), axis=0).astype(int))
        return (center[0], center[1] + int(shoulder_span * .16))
    if "nose" in points:
        nose = points["nose"]
        return (nose[0], nose[1] + int(shoulder_span * .18))
    if "head" in points:
        return points["head"]
    if neck is not None:
        return (neck[0], max(0, int(neck[1] - shoulder_span * .68)))
    return None


class FastAvatarRenderer:
    """Consistent CPU-friendly animated human avatar driven by normalized pose joints."""

    id = "fast"

    def available(self) -> tuple[bool, str | None]:
        return True, None

    def render(self, image: np.ndarray, keypoints: list[Keypoint], edges: list[tuple[str, str]]) -> np.ndarray:
        height, width = image.shape[:2]
        points = _visible_map(keypoints, width, height)
        canvas = _soft_background(width, height)
        if not points:
            return canvas

        ls, rs = points.get("l_shoulder"), points.get("r_shoulder")
        lh, rh = points.get("l_hip"), points.get("r_hip")
        le, re = points.get("l_elbow"), points.get("r_elbow")
        lw, rw = points.get("l_wrist"), points.get("r_wrist")
        lk, rk = points.get("l_knee"), points.get("r_knee")
        la, ra = points.get("l_ankle"), points.get("r_ankle")

        shoulder_span = max(62, int(_distance(ls, rs))) if ls and rs else max(58, width // 8)
        neck = _mid(ls, rs) if ls and rs else None
        hip_center = _mid(lh, rh) if lh and rh else None

        outline = (8, 10, 18)
        skin = (174, 207, 232)
        skin_light = (210, 230, 244)
        hair = (26, 22, 18)
        shirt = (176, 86, 56)
        shirt_shadow = (108, 50, 42)
        shirt_light = (226, 139, 82)
        pants = (66, 63, 102)
        pants_light = (116, 115, 162)
        shoe = (28, 30, 42)

        # Ground shadow.
        feet = [point for point in (la, ra) if point]
        if feet:
            foot_center = tuple(np.mean(np.array(feet), axis=0).astype(int))
            cv2.ellipse(canvas, (foot_center[0], min(height - 8, foot_center[1] + shoulder_span // 5)), (max(56, shoulder_span), max(9, shoulder_span // 8)), 0, 0, 360, (6, 7, 13), -1, cv2.LINE_AA)

        # Legs behind torso.
        if all((lh, rh, lk, rk)):
            shorts = np.array([
                (lh[0] - shoulder_span // 6, lh[1] - shoulder_span // 18),
                (rh[0] + shoulder_span // 6, rh[1] - shoulder_span // 18),
                (rk[0] + shoulder_span // 7, int(rk[1] * .55 + rh[1] * .45)),
                (lk[0] - shoulder_span // 7, int(lk[1] * .55 + lh[1] * .45)),
            ], np.int32)
            cv2.fillConvexPoly(canvas, shorts, outline, cv2.LINE_AA)
            cv2.fillConvexPoly(canvas, shorts + np.array([[0, 3]], np.int32), pants, cv2.LINE_AA)
        _draw_body_segment(canvas, lh, lk, int(shoulder_span * .30), int(shoulder_span * .21), pants, outline, pants_light)
        _draw_body_segment(canvas, rh, rk, int(shoulder_span * .30), int(shoulder_span * .21), pants, outline, pants_light)
        _draw_body_segment(canvas, lk, la, int(shoulder_span * .22), int(shoulder_span * .16), pants, outline, pants_light)
        _draw_body_segment(canvas, rk, ra, int(shoulder_span * .22), int(shoulder_span * .16), pants, outline, pants_light)
        for ankle, knee, side in ((la, lk, -1), (ra, rk, 1)):
            if ankle:
                angle = _angle(knee, ankle) if knee else 0
                _draw_rotated_ellipse(canvas, (ankle[0] + side * shoulder_span // 12, ankle[1] + shoulder_span // 16), (max(14, shoulder_span // 4), max(6, shoulder_span // 10)), angle, shoe, outline, 3)

        # Torso and jacket/shirt shape.
        if all((ls, rs, rh, lh)):
            waist_l = (int(lh[0] * .70 + (hip_center[0] if hip_center else lh[0]) * .30), lh[1])
            waist_r = (int(rh[0] * .70 + (hip_center[0] if hip_center else rh[0]) * .30), rh[1])
            torso = np.array([
                (ls[0] - shoulder_span // 5, ls[1] + shoulder_span // 18),
                (rs[0] + shoulder_span // 5, rs[1] + shoulder_span // 18),
                (waist_r[0] + shoulder_span // 5, waist_r[1]),
                (waist_l[0] - shoulder_span // 5, waist_l[1]),
            ], np.int32)
            cv2.fillConvexPoly(canvas, torso, outline, cv2.LINE_AA)
            inner = np.array([
                (ls[0] - shoulder_span // 7, ls[1] + shoulder_span // 10),
                (rs[0] + shoulder_span // 7, rs[1] + shoulder_span // 10),
                (waist_r[0] + shoulder_span // 7, waist_r[1] - shoulder_span // 20),
                (waist_l[0] - shoulder_span // 7, waist_l[1] - shoulder_span // 20),
            ], np.int32)
            cv2.fillConvexPoly(canvas, inner, shirt, cv2.LINE_AA)
            center = _mid(_mid(ls, rs), _mid(lh, rh))
            cv2.line(canvas, (center[0], ls[1] + shoulder_span // 8), (center[0], lh[1] - shoulder_span // 12), shirt_light, max(3, shoulder_span // 18), cv2.LINE_AA)
            collar = np.array([
                (center[0] - shoulder_span // 5, ls[1] + shoulder_span // 10),
                (center[0], ls[1] + shoulder_span // 4),
                (center[0] + shoulder_span // 5, ls[1] + shoulder_span // 10),
            ], np.int32)
            cv2.polylines(canvas, [collar], False, (235, 238, 232), max(2, shoulder_span // 26), cv2.LINE_AA)
            cv2.line(canvas, waist_l, waist_r, (25, 27, 38), max(4, shoulder_span // 12), cv2.LINE_AA)

        # Arms on top of the torso: short sleeves, forearms and hands.
        _draw_body_segment(canvas, ls, le, int(shoulder_span * .24), int(shoulder_span * .18), shirt_shadow, outline, shirt_light)
        _draw_body_segment(canvas, rs, re, int(shoulder_span * .24), int(shoulder_span * .18), shirt_shadow, outline, shirt_light)
        _draw_body_segment(canvas, le, lw, int(shoulder_span * .17), int(shoulder_span * .13), skin, outline, skin_light)
        _draw_body_segment(canvas, re, rw, int(shoulder_span * .17), int(shoulder_span * .13), skin, outline, skin_light)
        for wrist in (lw, rw):
            if wrist:
                _draw_rotated_ellipse(canvas, wrist, (max(9, shoulder_span // 7), max(7, shoulder_span // 9)), 0, skin, outline, 3)

        # Neck and head.
        if neck:
            _draw_body_segment(canvas, (neck[0], neck[1] - shoulder_span // 8), neck, max(7, shoulder_span // 10), max(8, shoulder_span // 9), skin, outline, skin_light)
        head = _head_center(points, shoulder_span, neck)
        if head:
            head_w = max(24, int(shoulder_span * .36))
            head_h = max(30, int(shoulder_span * .48))
            _draw_rotated_ellipse(canvas, head, (head_w, head_h), 0, skin, outline, 4)
            cv2.ellipse(canvas, (head[0], head[1] - head_h // 3), (head_w + 2, max(9, head_h // 2)), 0, 180, 360, hair, -1, cv2.LINE_AA)
            cv2.ellipse(canvas, (head[0] - head_w // 3, head[1] - head_h // 9), (max(3, head_w // 8), max(2, head_h // 16)), 0, 0, 360, (245, 245, 238), -1, cv2.LINE_AA)
            cv2.ellipse(canvas, (head[0] + head_w // 3, head[1] - head_h // 9), (max(3, head_w // 8), max(2, head_h // 16)), 0, 0, 360, (245, 245, 238), -1, cv2.LINE_AA)
            cv2.circle(canvas, (head[0] - head_w // 3, head[1] - head_h // 9), max(1, head_w // 22), (30, 25, 20), -1, cv2.LINE_AA)
            cv2.circle(canvas, (head[0] + head_w // 3, head[1] - head_h // 9), max(1, head_w // 22), (30, 25, 20), -1, cv2.LINE_AA)
            cv2.ellipse(canvas, (head[0], head[1] + head_h // 3), (max(4, head_w // 4), max(2, head_h // 12)), 0, 0, 180, (118, 58, 66), 2, cv2.LINE_AA)

        # Tiny cinematic rim light to make it feel like one polished animated character.
        overlay = canvas.copy()
        if all((ls, rs, lh, rh)):
            silhouette = np.array([ls, rs, rh, lh], np.int32)
            cv2.polylines(overlay, [silhouette], True, (200, 232, 255), 1, cv2.LINE_AA)
        _blend(canvas, overlay, .28)
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
