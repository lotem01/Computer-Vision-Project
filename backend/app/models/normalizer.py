from __future__ import annotations

from app.domain.contracts import Keypoint, PersonBox, RawPose


class NamedKeypointNormalizer:
    def __init__(self, names: list[str], threshold: float):
        self.names = names
        self.threshold = threshold

    def normalize(self, raw: RawPose) -> tuple[list[Keypoint], PersonBox]:
        points: list[Keypoint] = []
        for name, (x, y), confidence in zip(self.names, raw.xy, raw.confidence):
            points.append(Keypoint(
                name=name,
                x=max(0.0, min(1.0, x / raw.width)),
                y=max(0.0, min(1.0, y / raw.height)),
                confidence=max(0.0, min(1.0, confidence)),
                visible=confidence >= self.threshold and x > 0 and y > 0,
            ))
        x1, y1, x2, y2 = raw.box
        box = PersonBox(
            x=max(0, x1 / raw.width), y=max(0, y1 / raw.height),
            width=max(0, min(1, (x2 - x1) / raw.width)),
            height=max(0, min(1, (y2 - y1) / raw.height)),
            confidence=max(0, min(1, raw.person_confidence)),
        )
        return points, box

