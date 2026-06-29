import asyncio
from types import SimpleNamespace

from app.api.routes import video_preview
from app.infrastructure.job_store import InMemoryJobStore


def test_video_preview_serves_animated_webp_inline(tmp_path):
    store = InMemoryJobStore()
    job = store.create("clip.mp4", "yolov8n_pose")
    store.update(job.id, state="completed", progress=100)
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir()
    (jobs_dir / f"{job.id}-avatar-preview.webp").write_bytes(b"fake webp")
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                jobs=store,
                settings=SimpleNamespace(runtime_dir=tmp_path),
            ),
        ),
    )

    response = asyncio.run(video_preview(request, job.id, "avatar"))

    assert response.media_type == "image/webp"
    assert response.headers["content-disposition"].startswith("inline;")
    assert str(response.path).endswith(f"{job.id}-avatar-preview.webp")
