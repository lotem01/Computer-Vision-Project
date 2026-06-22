from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import get_settings
from app.infrastructure.job_store import InMemoryJobStore
from app.media.opencv_processor import OpenCVMediaProcessor
from app.models.registry import ModelRegistry
from app.renderers.diffusion import DiffusionAvatarRenderer
from app.services.inference import InferenceService
from app.services.video import VideoService


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    registry = ModelRegistry()
    media = OpenCVMediaProcessor()
    inference = InferenceService(registry, media)
    jobs = InMemoryJobStore()
    app.state.settings = settings
    app.state.registry = registry
    app.state.media = media
    app.state.inference = inference
    app.state.jobs = jobs
    app.state.video = VideoService(inference, jobs, settings)
    app.state.diffusion = DiffusionAvatarRenderer(settings.enable_diffusion)

    async def run_service(service, image, model_id, frame_id=None):
        return await asyncio.to_thread(service.infer, image, model_id, frame_id)

    app.state.run_service = run_service
    app.state.run_inference = lambda image, model_id, frame_id=None: run_service(inference, image, model_id, frame_id)
    preload_task = asyncio.create_task(registry.preload())
    yield
    if not preload_task.done():
        preload_task.cancel()


app = FastAPI(
    title="PoseLab API",
    version="1.0.0",
    description="Modular pose-to-avatar inference studio",
    lifespan=lifespan,
)
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "PoseLab"}


frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")

