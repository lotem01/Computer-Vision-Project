import numpy as np

from app.domain.contracts import ModelDefinition
from app.models.posenet_tflite_adapter import PoseNetTFLiteAdapter
from app.models.registry import create_pose_adapter


class FakeInterpreter:
    def __init__(self):
        self.input = None
        self.heatmaps = np.zeros((1, 9, 9, 17), dtype=np.float32)
        self.offsets = np.zeros((1, 9, 9, 34), dtype=np.float32)
        self.heatmaps[0, 4, 5, :] = 8.0

    def set_tensor(self, index, value):
        assert index == 0
        self.input = value

    def invoke(self):
        pass

    def get_tensor(self, index):
        return self.heatmaps if index == 1 else self.offsets


def definition(path="posenet.tflite") -> ModelDefinition:
    return ModelDefinition(
        id="posenet",
        label="PoseNet",
        description="TFLite test model",
        path=path,
        source="test",
        joint_names=[
            "nose", "l_eye", "r_eye", "l_ear", "r_ear", "l_shoulder", "r_shoulder",
            "l_elbow", "r_elbow", "l_wrist", "r_wrist", "l_hip", "r_hip",
            "l_knee", "r_knee", "l_ankle", "r_ankle",
        ],
        edges=[],
        threshold=0.25,
        extras={"adapter": "posenet_tflite", "input_size": 257},
    )


def test_registry_factory_uses_tflite_adapter_for_posenet():
    adapter = create_pose_adapter(definition())

    assert isinstance(adapter, PoseNetTFLiteAdapter)


def test_posenet_adapter_decodes_heatmaps_and_offsets():
    adapter = PoseNetTFLiteAdapter(definition())
    adapter._interpreter = FakeInterpreter()
    adapter._input_index = 0
    adapter._input_height = 257
    adapter._input_width = 257
    adapter._input_dtype = np.float32
    adapter._heatmap_index = 1
    adapter._offset_index = 2

    raw = adapter.infer(np.zeros((720, 1280, 3), dtype=np.uint8))

    assert raw is not None
    assert len(raw.xy) == 17
    assert len(raw.confidence) == 17
    assert raw.confidence[0] > 0.99
    assert 780 < raw.xy[0][0] < 805
    assert 355 < raw.xy[0][1] < 365
