import numpy as np

from app.domain.contracts import Keypoint
from app.renderers.fast import FastAvatarRenderer, SkeletonRenderer


def test_renderers_preserve_source_dimensions():
    image = np.zeros((240, 320, 3), dtype=np.uint8)
    image[40:200, 100:220] = (80, 130, 220)
    different_source = np.full((240, 320, 3), 255, dtype=np.uint8)
    points = [
        Keypoint(name="nose", x=.5, y=.18, confidence=.9),
        Keypoint(name="l_shoulder", x=.35, y=.3, confidence=.9),
        Keypoint(name="r_shoulder", x=.65, y=.3, confidence=.9),
        Keypoint(name="l_hip", x=.42, y=.62, confidence=.9),
        Keypoint(name="r_hip", x=.58, y=.62, confidence=.9),
    ]
    edges = [("l_shoulder", "r_shoulder")]
    avatar = FastAvatarRenderer().render(image, points, edges)
    assert avatar.shape == image.shape
    assert avatar.sum() > 0
    assert np.array_equal(avatar, FastAvatarRenderer().render(different_source, points, edges))
    assert SkeletonRenderer().render(image, points, edges).shape == image.shape
