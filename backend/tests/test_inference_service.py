import numpy as np

from app.domain.contracts import ModelDefinition, ModelMetadata, RawPose
from app.media.opencv_processor import OpenCVMediaProcessor
from app.models.normalizer import NamedKeypointNormalizer
from app.services.inference import InferenceService


class FakeAdapter:
    metadata = ModelMetadata(
        id="fake_pose",
        label="Fake Pose",
        description="Deterministic test adapter",
        joint_count=5,
        joint_names=["head", "l_shoulder", "r_shoulder", "l_hip", "r_hip"],
        source="test",
        state="ready",
    )

    def infer(self, image):
        height, width = image.shape[:2]
        return RawPose(
            xy=[
                (width * .50, height * .18),
                (width * .35, height * .38),
                (width * .65, height * .38),
                (width * .42, height * .70),
                (width * .58, height * .70),
            ],
            confidence=[.95, .9, .9, .85, .85],
            box=(width * .25, height * .08, width * .75, height * .85),
            person_confidence=.93,
            width=width,
            height=height,
        )


class FakeRegistry:
    definitions = {
        "fake_pose": ModelDefinition(
            id="fake_pose",
            label="Fake Pose",
            description="Deterministic test adapter",
            path="unused.pt",
            source="test",
            joint_names=["head", "l_shoulder", "r_shoulder", "l_hip", "r_hip"],
            edges=[("head", "l_shoulder"), ("head", "r_shoulder"), ("l_shoulder", "l_hip"), ("r_shoulder", "r_hip")],
        )
    }
    normalizers = {
        "fake_pose": NamedKeypointNormalizer(["head", "l_shoulder", "r_shoulder", "l_hip", "r_hip"], .35)
    }

    def require(self, model_id):
        assert model_id == "fake_pose"
        return FakeAdapter()


def test_inference_service_returns_full_pose_result_contract():
    image = np.zeros((180, 240, 3), dtype=np.uint8)
    service = InferenceService(FakeRegistry(), OpenCVMediaProcessor())

    result = service.infer(image, "fake_pose", frame_id=12)

    assert result.frame_id == 12
    assert result.source_size == (240, 180)
    assert result.detected_joints == 5
    assert result.person_box.confidence == .93
    assert [point.name for point in result.keypoints] == ["head", "l_shoulder", "r_shoulder", "l_hip", "r_hip"]
    assert result.original.startswith("data:image/jpeg;base64,")
    assert result.skeleton.startswith("data:image/jpeg;base64,")
    assert result.avatar.startswith("data:image/jpeg;base64,")
