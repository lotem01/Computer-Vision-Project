from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from app.domain.contracts import ModelDefinition, ModelMetadata, ModelState, RawPose


class PoseNetTFLiteAdapter:
    """Runs the classic PoseNet MobileNet TFLite model behind the common pose adapter contract."""

    def __init__(self, definition: ModelDefinition):
        self.definition = definition
        self._interpreter: Any | None = None
        self._lock = threading.Lock()
        self._input_index: int | None = None
        self._input_height = int(definition.extras.get("input_size", 257))
        self._input_width = int(definition.extras.get("input_size", 257))
        self._input_dtype: Any = np.float32
        self._heatmap_index: int | None = None
        self._offset_index: int | None = None
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
        model_path = Path(self.definition.path)
        if not model_path.exists():
            raise FileNotFoundError(f"PoseNet model file was not found: {model_path}")

        Interpreter = self._interpreter_class()
        model_content = model_path.read_bytes()
        try:
            self._interpreter = Interpreter(model_content=model_content, num_threads=2)
        except TypeError:
            self._interpreter = Interpreter(model_content=model_content)
        self._interpreter.allocate_tensors()
        self._configure_io()

    def warm(self) -> None:
        if self._interpreter is None:
            raise RuntimeError("Model has not been loaded")
        dummy = np.zeros((320, 320, 3), dtype=np.uint8)
        self.infer(dummy)

    def infer(self, image: np.ndarray) -> RawPose | None:
        if self._interpreter is None:
            raise RuntimeError("Model is not ready")
        if self._input_index is None or self._heatmap_index is None or self._offset_index is None:
            raise RuntimeError("PoseNet input/output tensors were not configured")

        original_height, original_width = image.shape[:2]
        tensor = self._preprocess(image)
        with self._lock:
            self._interpreter.set_tensor(self._input_index, tensor)
            self._interpreter.invoke()
            heatmaps = self._interpreter.get_tensor(self._heatmap_index)
            offsets = self._interpreter.get_tensor(self._offset_index)

        xy, confidence = self._decode(heatmaps, offsets, original_width, original_height)
        if not confidence or max(confidence) < 0.12:
            return None

        box = self._box_from_pose(xy, confidence, original_width, original_height)
        return RawPose(
            xy=xy,
            confidence=confidence,
            box=box,
            person_confidence=float(max(confidence)),
            width=original_width,
            height=original_height,
        )

    def _interpreter_class(self):
        try:
            from tflite_runtime.interpreter import Interpreter

            return Interpreter
        except ImportError:
            try:
                from tensorflow.lite.python.interpreter import Interpreter

                return Interpreter
            except ImportError as exc:
                raise RuntimeError(
                    "PoseNet requires TensorFlow Lite support. Install tensorflow==2.10.1 "
                    "or tflite_runtime in the backend virtual environment."
                ) from exc

    def _configure_io(self) -> None:
        if self._interpreter is None:
            raise RuntimeError("Model has not been loaded")

        input_details = self._interpreter.get_input_details()
        if not input_details:
            raise RuntimeError("PoseNet TFLite model has no input tensors")
        input_detail = input_details[0]
        shape = list(input_detail["shape"])
        self._input_index = int(input_detail["index"])
        self._input_height = int(shape[1])
        self._input_width = int(shape[2])
        self._input_dtype = input_detail["dtype"]

        for detail in self._interpreter.get_output_details():
            shape = list(detail["shape"])
            if len(shape) >= 4 and int(shape[-1]) == len(self.definition.joint_names):
                self._heatmap_index = int(detail["index"])
            elif len(shape) >= 4 and int(shape[-1]) == len(self.definition.joint_names) * 2:
                self._offset_index = int(detail["index"])

        if self._heatmap_index is None or self._offset_index is None:
            raise RuntimeError("PoseNet TFLite outputs must include heatmaps and offsets")

    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb, (self._input_width, self._input_height), interpolation=cv2.INTER_LINEAR)
        if self._input_dtype == np.float32:
            resized = (resized.astype(np.float32) - 127.5) / 127.5
        else:
            resized = resized.astype(self._input_dtype)
        return np.expand_dims(resized, axis=0)

    def _decode(
        self,
        heatmaps: np.ndarray,
        offsets: np.ndarray,
        original_width: int,
        original_height: int,
    ) -> tuple[list[tuple[float, float]], list[float]]:
        if heatmaps.ndim == 4:
            heatmaps = heatmaps[0]
        if offsets.ndim == 4:
            offsets = offsets[0]

        heatmap_height, heatmap_width, joint_count = heatmaps.shape
        stride_y = (self._input_height - 1) / max(1, heatmap_height - 1)
        stride_x = (self._input_width - 1) / max(1, heatmap_width - 1)
        xy: list[tuple[float, float]] = []
        confidence: list[float] = []

        for joint_index in range(joint_count):
            joint_heatmap = heatmaps[:, :, joint_index]
            y_index, x_index = np.unravel_index(int(np.argmax(joint_heatmap)), joint_heatmap.shape)
            y = y_index * stride_y + float(offsets[y_index, x_index, joint_index])
            x = x_index * stride_x + float(offsets[y_index, x_index, joint_index + joint_count])
            x = max(0.0, min(float(self._input_width - 1), x))
            y = max(0.0, min(float(self._input_height - 1), y))
            xy.append((x / self._input_width * original_width, y / self._input_height * original_height))
            confidence.append(float(self._sigmoid(joint_heatmap[y_index, x_index])))

        return xy, confidence

    def _box_from_pose(
        self,
        xy: list[tuple[float, float]],
        confidence: list[float],
        width: int,
        height: int,
    ) -> tuple[float, float, float, float]:
        usable = [point for point, score in zip(xy, confidence) if score >= min(0.25, self.definition.threshold)]
        if not usable:
            usable = xy
        xs = [point[0] for point in usable]
        ys = [point[1] for point in usable]
        margin_x = width * 0.04
        margin_y = height * 0.04
        return (
            max(0.0, min(xs) - margin_x),
            max(0.0, min(ys) - margin_y),
            min(float(width), max(xs) + margin_x),
            min(float(height), max(ys) + margin_y),
        )

    @staticmethod
    def _sigmoid(value: float) -> float:
        return float(1 / (1 + np.exp(-np.clip(value, -50, 50))))
