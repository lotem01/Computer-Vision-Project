from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel

from app.domain.contracts import ModelDefinition

ROOT = Path(__file__).resolve().parents[1]
LOCAL_CONFIG = ROOT / "runtime" / "config"
LOCAL_CONFIG.mkdir(parents=True, exist_ok=True)
# Keep third-party runtime state inside the project so the demo is portable.
os.environ.setdefault("YOLO_CONFIG_DIR", str(LOCAL_CONFIG / "ultralytics"))
os.environ.setdefault("MPLCONFIGDIR", str(LOCAL_CONFIG / "matplotlib"))

COCO_17 = [
    "nose", "l_eye", "r_eye", "l_ear", "r_ear", "l_shoulder", "r_shoulder",
    "l_elbow", "r_elbow", "l_wrist", "r_wrist", "l_hip", "r_hip",
    "l_knee", "r_knee", "l_ankle", "r_ankle",
]
CANONICAL_13 = [
    "head", "r_ankle", "r_knee", "r_hip", "l_hip", "l_knee", "l_ankle",
    "r_wrist", "r_elbow", "r_shoulder", "l_shoulder", "l_elbow", "l_wrist",
]
COCO_EDGES = [
    ("l_shoulder", "r_shoulder"), ("l_shoulder", "l_elbow"),
    ("l_elbow", "l_wrist"), ("r_shoulder", "r_elbow"),
    ("r_elbow", "r_wrist"), ("l_shoulder", "l_hip"),
    ("r_shoulder", "r_hip"), ("l_hip", "r_hip"), ("l_hip", "l_knee"),
    ("l_knee", "l_ankle"), ("r_hip", "r_knee"), ("r_knee", "r_ankle"),
    ("nose", "l_eye"), ("nose", "r_eye"), ("l_eye", "l_ear"),
    ("r_eye", "r_ear"),
]
BODY_13_EDGES = [
    ("head", "r_shoulder"), ("head", "l_shoulder"),
    ("r_shoulder", "l_shoulder"), ("r_shoulder", "r_elbow"),
    ("r_elbow", "r_wrist"), ("l_shoulder", "l_elbow"),
    ("l_elbow", "l_wrist"), ("r_shoulder", "r_hip"),
    ("l_shoulder", "l_hip"), ("r_hip", "l_hip"), ("r_hip", "r_knee"),
    ("r_knee", "r_ankle"), ("l_hip", "l_knee"), ("l_knee", "l_ankle"),
]


class Settings(BaseModel):
    api_version: str = "v1"
    confidence_threshold: float = 0.35
    maximum_upload_mb: int = 200
    maximum_video_seconds: int = 60
    maximum_video_fps: int = 12
    enable_diffusion: bool = False
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    runtime_dir: Path = ROOT / "runtime"


def get_settings() -> Settings:
    return Settings(enable_diffusion=os.getenv("POSEAPP_ENABLE_DIFFUSION", "0") == "1")


def model_definitions() -> list[ModelDefinition]:
    weights = ROOT / "weights"
    shared = {"threshold": 0.35}
    return [
        ModelDefinition("coco_model", "COCO Specialist", "Fine-tuned for precise full-body COCO keypoints.", str(weights / "coco_model.pt"), "COCO 2017", COCO_17, COCO_EDGES, **shared),
        ModelDefinition("unified_model", "Unified 13", "A compact joint system trained across unified body-part data.", str(weights / "unified_model.pt"), "Unified body-13", CANONICAL_13, BODY_13_EDGES, **shared),
        ModelDefinition("pseudo_labeled_model", "Pseudo-Labeled", "Student pose model expanded with pseudo-labeled MPII data.", str(weights / "pseudo_labeled_model.pt"), "MPII + pseudo labels", COCO_17, COCO_EDGES, **shared),
        ModelDefinition("yolov8n_pose", "YOLOv8 Baseline", "Fast pretrained baseline for dependable live comparison.", str(weights / "yolov8n-pose.pt"), "Ultralytics COCO", COCO_17, COCO_EDGES, **shared),
    ]
