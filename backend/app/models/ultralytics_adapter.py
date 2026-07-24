from __future__ import annotations

import threading

import numpy as np

from app.domain.contracts import ModelDefinition, ModelMetadata, ModelState, RawPose


class UltralyticsPoseAdapter:
    """Keeps Ultralytics details behind the domain's pose-model contract."""

    def __init__(self, definition: ModelDefinition):
        self.definition = definition
        self._model = None
        self._lock = threading.Lock()
        self._metadata = ModelMetadata(
            id=definition.id,
            label=definition.label,
            description=definition.description,
            joint_count=len(definition.joint_names),
            joint_names=definition.joint_names,
            source=definition.source,
        )

    @property
    def metadata(self) -> ModelMetadata:
        return self._metadata

    def set_state(self, state: ModelState, error: str | None = None) -> None:
        self._metadata.state = state
        self._metadata.error = error

    def load(self) -> None:
        from ultralytics import YOLO

        self._model = YOLO(self.definition.path)

    def warm(self) -> None:
        if self._model is None:
            raise RuntimeError("Model has not been loaded")
        dummy = np.zeros((320, 320, 3), dtype=np.uint8)
        with self._lock:
            self._model.predict(dummy, verbose=False, imgsz=320, conf=0.25, device="cpu")

    def infer(self, image: np.ndarray) -> RawPose | None:
        if self._model is None:
            raise RuntimeError("Model is not ready")
        with self._lock:
            result = self._model.predict(image, verbose=False, conf=0.25, device="cpu")[0]
        if result.keypoints is None or len(result.keypoints) == 0 or result.boxes is None:
            return None
        boxes = result.boxes.conf.cpu().numpy()
        if boxes.size == 0:
            return None
        best = int(boxes.argmax())
        xy = result.keypoints.xy[best].cpu().numpy()
        conf_tensor = result.keypoints.conf
        confidence = conf_tensor[best].cpu().numpy() if conf_tensor is not None else np.ones(len(xy))
        box = result.boxes.xyxy[best].cpu().numpy()
        height, width = image.shape[:2]
        return RawPose(
            xy=[(float(x), float(y)) for x, y in xy],
            confidence=[float(value) for value in confidence],
            box=tuple(float(value) for value in box),
            person_confidence=float(boxes[best]),
            width=width,
            height=height,
        )
