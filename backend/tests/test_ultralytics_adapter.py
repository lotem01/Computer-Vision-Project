import numpy as np

from app.domain.contracts import ModelDefinition
from app.models.ultralytics_adapter import UltralyticsPoseAdapter


class EmptyTensor:
    def cpu(self):
        return self

    def numpy(self):
        return np.array([])


class EmptyBoxes:
    conf = EmptyTensor()


class EmptyKeypoints:
    def __len__(self):
        return 1


class EmptyDetectionResult:
    keypoints = EmptyKeypoints()
    boxes = EmptyBoxes()


class EmptyDetectionModel:
    def predict(self, *args, **kwargs):
        return [EmptyDetectionResult()]


def test_adapter_returns_none_when_boxes_are_empty():
    definition = ModelDefinition(
        id="fake",
        label="Fake",
        description="Fake adapter",
        path="unused.pt",
        source="test",
        joint_names=["head"],
        edges=[],
    )
    adapter = UltralyticsPoseAdapter(definition)
    adapter._model = EmptyDetectionModel()

    assert adapter.infer(np.zeros((64, 64, 3), dtype=np.uint8)) is None
