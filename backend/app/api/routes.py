from __future__ import annotations

import base64
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from app.services.inference import InferenceService, NoPersonDetectedError

router = APIRouter(prefix="/api/v1")


def _error(exc: Exception) -> HTTPException:
    if isinstance(exc, KeyError):
        return HTTPException(404, str(exc))
    if isinstance(exc, (ValueError, NoPersonDetectedError)):
        return HTTPException(422, str(exc))
    return HTTPException(503, str(exc))


@router.get("/readiness")
async def readiness(request: Request):
    return request.app.state.registry.readiness()


@router.get("/models")
async def models(request: Request):
    diffusion = request.app.state.diffusion
    enabled, reason = diffusion.available()
    return {
        "apiVersion": "v1",
        "models": [item.model_dump(mode="json") for item in request.app.state.registry.metadata()],
        "renderers": [
            {"id": "fast", "label": "Realtime avatar", "available": True, "reason": None},
            {"id": "diffusion", "label": "Generative avatar", "available": enabled, "reason": reason},
        ],
    }


@router.post("/infer/image")
async def infer_image(
    request: Request,
    model_id: str = Form(..., alias="modelId"),
    image: UploadFile = File(...),
):
    payload = await image.read()
    if len(payload) > request.app.state.settings.maximum_upload_mb * 1024 * 1024:
        raise HTTPException(413, "The file is larger than the configured upload limit.")
    try:
        decoded = request.app.state.media.decode_image(payload)
        result = await request.app.state.run_inference(decoded, model_id)
        return result.model_dump(mode="json", by_alias=True)
    except Exception as exc:
        raise _error(exc) from exc


@router.post("/infer/diffusion")
async def infer_diffusion(
    request: Request,
    model_id: str = Form(..., alias="modelId"),
    image: UploadFile = File(...),
):
    available, reason = request.app.state.diffusion.available()
    if not available:
        raise HTTPException(503, reason)
    try:
        decoded = request.app.state.media.decode_image(await image.read())
        service = InferenceService(request.app.state.registry, request.app.state.media, request.app.state.diffusion)
        result = await request.app.state.run_service(service, decoded, model_id)
        return result.model_dump(mode="json", by_alias=True)
    except Exception as exc:
        raise _error(exc) from exc


@router.websocket("/live")
async def live(websocket: WebSocket):
    await websocket.accept()
    app = websocket.app
    try:
        while True:
            message = await websocket.receive_json()
            frame_id = int(message.get("frameId", 0))
            model_id = message.get("modelId", "yolov8n_pose")
            encoded = message.get("image", "")
            try:
                payload = base64.b64decode(encoded.split(",", 1)[-1])
                image = app.state.media.decode_image(payload)
                result = await app.state.run_inference(image, model_id, frame_id)
                await websocket.send_json({"type": "result", "data": result.model_dump(mode="json", by_alias=True)})
            except NoPersonDetectedError:
                await websocket.send_json({"type": "no_pose", "frameId": frame_id})
            except Exception as exc:
                await websocket.send_json({"type": "error", "frameId": frame_id, "message": str(exc)})
    except WebSocketDisconnect:
        return


@router.post("/video-jobs", status_code=202)
async def create_video_job(
    request: Request,
    model_id: str = Form(..., alias="modelId"),
    render_fps: Optional[float] = Form(None, alias="renderFps"),
    video: UploadFile = File(...),
):
    payload = await video.read()
    if len(payload) > request.app.state.settings.maximum_upload_mb * 1024 * 1024:
        raise HTTPException(413, "The video is larger than the configured upload limit.")
    try:
        request.app.state.registry.require(model_id)
        job = await request.app.state.video.submit(video.filename or "upload.mp4", model_id, payload, render_fps)
        return job.public()
    except Exception as exc:
        raise _error(exc) from exc


@router.get("/video-jobs/{job_id}")
async def video_job(request: Request, job_id: str):
    job = request.app.state.jobs.get(job_id)
    if job is None:
        raise HTTPException(404, "Video job not found")
    return job.public()


@router.delete("/video-jobs/{job_id}")
async def cancel_video_job(request: Request, job_id: str):
    if request.app.state.jobs.get(job_id) is None:
        raise HTTPException(404, "Video job not found")
    return request.app.state.jobs.cancel(job_id).public()


@router.get("/video-jobs/{job_id}/result")
async def video_result_alias(request: Request, job_id: str, download: bool = False):
    return await video_result(request, job_id, "avatar", download)


@router.get("/video-jobs/{job_id}/result/{kind}")
async def video_result(request: Request, job_id: str, kind: str, download: bool = False):
    job = request.app.state.jobs.get(job_id)
    if kind not in {"avatar", "skeleton"}:
        raise HTTPException(404, "Video result type is not available")
    path = request.app.state.settings.runtime_dir / "jobs" / f"{job_id}-{kind}.mp4"
    if job is None or job.state != "completed" or not path.exists():
        raise HTTPException(404, "Video result is not available")
    label = "pose-avatar" if kind == "avatar" else "pose-map"
    return FileResponse(
        path,
        media_type="video/mp4",
        filename=f"{label}-{job_id[:8]}.mp4",
        content_disposition_type="attachment" if download else "inline",
    )


@router.get("/video-jobs/{job_id}/preview/{kind}")
async def video_preview(request: Request, job_id: str, kind: str):
    job = request.app.state.jobs.get(job_id)
    if kind not in {"avatar", "skeleton"}:
        raise HTTPException(404, "Video preview type is not available")
    path = request.app.state.settings.runtime_dir / "jobs" / f"{job_id}-{kind}-preview.webp"
    if job is None or job.state != "completed" or not path.exists():
        raise HTTPException(404, "Video preview is not available")
    return FileResponse(path, media_type="image/webp", filename=f"{kind}-preview-{job_id[:8]}.webp", content_disposition_type="inline")
