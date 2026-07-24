from __future__ import annotations

import time

import numpy as np

from app.domain.contracts import PoseResult, Timing
from app.media.opencv_processor import OpenCVMediaProcessor
from app.models.registry import ModelRegistry
from app.renderers.fast import FastAvatarRenderer, SkeletonRenderer


class NoPersonDetectedError(ValueError):
    pass


class InferenceService:
    def __init__(self, registry: ModelRegistry, media: OpenCVMediaProcessor, avatar_renderer=None):
        self.registry = registry
        self.media = media
        self.avatar_renderer = avatar_renderer or FastAvatarRenderer()
        self.skeleton_renderer = SkeletonRenderer()

    def infer(self, image: np.ndarray, model_id: str, frame_id: int | None = None) -> PoseResult:
        started = time.perf_counter()
        adapter = self.registry.require(model_id)
        inference_started = time.perf_counter()
        raw = adapter.infer(image)
        inference_ms = (time.perf_counter() - inference_started) * 1000
        if raw is None:
            raise NoPersonDetectedError("No person was detected. Try a clearer, full-body view.")
        keypoints, box = self.registry.normalizers[model_id].normalize(raw)
        edges = self.registry.definitions[model_id].edges
        render_started = time.perf_counter()
        skeleton = self.skeleton_renderer.render(image, keypoints, edges)
        avatar = self.avatar_renderer.render(image, keypoints, edges)
        rendering_ms = (time.perf_counter() - render_started) * 1000
        total_ms = (time.perf_counter() - started) * 1000
        visible = sum(point.visible for point in keypoints)
        warnings = [] if visible >= max(5, len(keypoints) // 2) else ["Only a partial pose was detected."]
        return PoseResult(
            frameId=frame_id,
            model=adapter.metadata,
            keypoints=keypoints,
            personBox=box,
            sourceSize=(image.shape[1], image.shape[0]),
            detectedJoints=visible,
            warnings=warnings,
            timing=Timing(inference_ms=inference_ms, rendering_ms=rendering_ms, total_ms=total_ms),
            original=self.media.encode_data_url(image),
            skeleton=self.media.encode_data_url(skeleton),
            avatar=self.media.encode_data_url(avatar),
        )

