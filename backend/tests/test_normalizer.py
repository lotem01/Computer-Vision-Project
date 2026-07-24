from app.config import CANONICAL_13
from app.domain.contracts import RawPose
from app.models.normalizer import NamedKeypointNormalizer


def test_normalizer_names_and_bounds():
    raw = RawPose(
        xy=[(50, 25)] * 13,
        confidence=[0.9] * 13,
        box=(10, 5, 90, 95),
        person_confidence=0.88,
        width=100,
        height=100,
    )
    points, box = NamedKeypointNormalizer(CANONICAL_13, 0.35).normalize(raw)
    assert [point.name for point in points] == CANONICAL_13
    assert all(point.visible for point in points)
    assert points[0].x == 0.5
    assert box.width == 0.8


def test_low_confidence_joint_is_hidden():
    raw = RawPose([(1, 1)], [0.1], (0, 0, 10, 10), 0.8, 10, 10)
    points, _ = NamedKeypointNormalizer(["head"], 0.35).normalize(raw)
    assert points[0].visible is False

