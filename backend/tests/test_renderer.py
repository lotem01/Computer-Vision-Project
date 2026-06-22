import numpy as np

from app.domain.contracts import Keypoint
from app.renderers.fast import FastAvatarRenderer, SkeletonRenderer


def test_renderers_preserve_source_dimensions():
    image = np.zeros((240, 320, 3), dtype=np.uint8)
    points = [
        Keypoint(name="l_shoulder", x=.35, y=.3, confidence=.9),
        Keypoint(name="r_shoulder", x=.65, y=.3, confidence=.9),
    ]
    edges = [("l_shoulder", "r_shoulder")]
    assert FastAvatarRenderer().render(image, points, edges).shape == image.shape
    assert SkeletonRenderer().render(image, points, edges).shape == image.shape

