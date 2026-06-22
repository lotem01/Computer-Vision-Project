from __future__ import annotations

import asyncio
from collections.abc import Callable

from app.config import model_definitions
from app.domain.contracts import ModelMetadata, ModelState
from app.models.normalizer import NamedKeypointNormalizer
from app.models.ultralytics_adapter import UltralyticsPoseAdapter


class ModelRegistry:
    def __init__(self, adapter_factory: Callable = UltralyticsPoseAdapter):
        definitions = model_definitions()
        self.adapters = {item.id: adapter_factory(item) for item in definitions}
        self.normalizers = {item.id: NamedKeypointNormalizer(item.joint_names, item.threshold) for item in definitions}
        self.definitions = {item.id: item for item in definitions}
        self.completed = False

    async def preload(self) -> None:
        for adapter in self.adapters.values():
            try:
                adapter.set_state(ModelState.LOADING)
                await asyncio.to_thread(adapter.load)
                adapter.set_state(ModelState.WARMING)
                await asyncio.to_thread(adapter.warm)
                adapter.set_state(ModelState.READY)
            except Exception as exc:
                adapter.set_state(ModelState.FAILED, f"{type(exc).__name__}: {exc}")
        self.completed = True

    def require(self, model_id: str) -> UltralyticsPoseAdapter:
        adapter = self.adapters.get(model_id)
        if adapter is None:
            raise KeyError(f"Unknown model: {model_id}")
        if adapter.metadata.state != ModelState.READY:
            raise RuntimeError(adapter.metadata.error or f"{adapter.metadata.label} is not ready")
        return adapter

    def metadata(self) -> list[ModelMetadata]:
        return [adapter.metadata for adapter in self.adapters.values()]

    def readiness(self) -> dict:
        models = self.metadata()
        ready = sum(item.state == ModelState.READY for item in models)
        return {
            "apiVersion": "v1",
            "completed": self.completed,
            "readyCount": ready,
            "totalCount": len(models),
            "models": [item.model_dump(mode="json") for item in models],
        }

