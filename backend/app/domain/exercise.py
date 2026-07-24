from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from app.domain.contracts import Keypoint


class ExerciseFrame(BaseModel):
    index: int
    timestamp: float
    keypoints: list[Keypoint]
    skeleton_url: str = Field(alias="skeletonUrl")


class ExerciseInstructor(BaseModel):
    id: str
    filename: str
    model_id: str = Field(alias="modelId")
    state: str
    progress: float = 0
    fps: float = 6
    frame_count: int = Field(default=0, alias="frameCount")
    duration: float = 0
    cached: bool = False
    error: Optional[str] = None
    frames: list[ExerciseFrame] = []


class JointFeedback(BaseModel):
    name: str
    distance: float
    score: float
    close: bool
    instructor: Optional[tuple[float, float]] = None
    user: Optional[tuple[float, float]] = None


class ExerciseCompareResult(BaseModel):
    instructor_id: str = Field(alias="instructorId")
    frame_index: int = Field(alias="frameIndex")
    matched_initial: bool = Field(alias="matchedInitial")
    score: float
    detected_joints: int = Field(alias="detectedJoints")
    joint_feedback: list[JointFeedback] = Field(alias="jointFeedback")
    user_skeleton: str = Field(alias="userSkeleton")
    message: Optional[str] = None


class ExerciseSummary(BaseModel):
    average_score: float = Field(alias="averageScore")
    best_joints: list[JointFeedback] = Field(alias="bestJoints")
    improve_joints: list[JointFeedback] = Field(alias="improveJoints")
    samples: int
