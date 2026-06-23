from app.infrastructure.job_store import InMemoryJobStore


def test_job_lifecycle():
    store = InMemoryJobStore()
    job = store.create("clip.mp4", "coco_model")
    assert job.state == "queued"
    store.update(job.id, state="processing", progress=40)
    assert store.get(job.id).progress == 40
    assert store.cancel(job.id).state == "cancelled"


def test_video_job_public_contract_exposes_rendered_outputs():
    store = InMemoryJobStore()
    job = store.create("clip.mp4", "yolov8n_pose")
    store.update(
        job.id,
        state="completed",
        progress=100,
        result_url=f"/api/v1/video-jobs/{job.id}/result/avatar",
        avatar_url=f"/api/v1/video-jobs/{job.id}/result/avatar",
        skeleton_url=f"/api/v1/video-jobs/{job.id}/result/skeleton",
        avatar_preview_url=f"/api/v1/video-jobs/{job.id}/preview/avatar",
        skeleton_preview_url=f"/api/v1/video-jobs/{job.id}/preview/skeleton",
    )

    public = store.get(job.id).public()

    assert public["state"] == "completed"
    assert public["result_url"].endswith("/result/avatar")
    assert public["avatar_url"].endswith("/result/avatar")
    assert public["skeleton_url"].endswith("/result/skeleton")
    assert public["avatar_preview_url"].endswith("/preview/avatar")
    assert public["skeleton_preview_url"].endswith("/preview/skeleton")
    assert "cancelled" not in public
