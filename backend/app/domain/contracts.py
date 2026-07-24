from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class ModelState(str, Enum):
    PENDING = "pending"
    LOADING = "loading"
    WARMING = "warming"
    READY = "ready"
    FAILED = "failed"


class Keypoint(BaseModel):
    name: str
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    visible: bool = True


class PersonBox(BaseModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(ge=0, le=1)
    height: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)


class Timing(BaseModel):
    inference_ms: float
    rendering_ms: float
    total_ms: float


class ModelMetadata(BaseModel):
    id: str
    label: str
    description: str
    joint_count: int
    joint_names: list[str]
    source: str
    state: ModelState = ModelState.PENDING
    error: Optional[str] = None


class PoseResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    api_version: str = Field(default="v1", alias="apiVersion")
    frame_id: Optional[int] = Field(default=None, alias="frameId")
    model: ModelMetadata
    keypoints: list[Keypoint]
    person_box: Optional[PersonBox] = Field(default=None, alias="personBox")
    source_size: tuple[int, int] = Field(alias="sourceSize")
    detected_joints: int = Field(alias="detectedJoints")
    warnings: list[str] = []
    timing: Timing
    original: str
    skeleton: str
    avatar: str


@dataclass
class RawPose:
    xy: list[tuple[float, float]]
    confidence: list[float]
    box: tuple[float, float, float, float]
    person_confidence: float
    width: int
    height: int


@dataclass
class ModelDefinition:
    id: str
    label: str
    description: str
    path: str
    source: str
    joint_names: list[str]
    edges: list[tuple[str, str]]
    threshold: float = 0.35
    extras: dict[str, Any] = field(default_factory=dict)
