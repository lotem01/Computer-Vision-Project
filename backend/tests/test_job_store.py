from app.infrastructure.job_store import InMemoryJobStore


def test_job_lifecycle():
    store = InMemoryJobStore()
    job = store.create("clip.mp4", "coco_model")
    assert job.state == "queued"
    store.update(job.id, state="processing", progress=40)
    assert store.get(job.id).progress == 40
    assert store.cancel(job.id).state == "cancelled"

