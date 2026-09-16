"""Pydantic schemas for experiment jobs, status, and responses."""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    QUEUED = "queued"
    PREPROCESSING = "preprocessing"
    RUNNING_BRAIN = "running_brain"
    TRAINING_READOUT = "training_readout"
    RUNNING_BASELINES = "running_baselines"
    RUNNING_CONTROL = "running_control"
    FINALIZING = "finalizing"
    COMPLETE = "complete"
    FAILED = "failed"


class ExperimentStatusResponse(BaseModel):
    id: str
    status: JobStatus
    progress: int = Field(ge=0, le=100)
    message: str
    created_at: str
    updated_at: str
    error: Optional[str] = None


class ExperimentCreateResponse(BaseModel):
    id: str
    status: JobStatus = JobStatus.QUEUED
    message: str = "Experiment successfully queued"


class ExperimentConfig(BaseModel):
    id: str
    time_column: Optional[str] = None
    target_column: Optional[str] = None
    feature_columns: List[str] = Field(default_factory=list)
    forecast_horizon: int = 5
    run_control: bool = False
    demo_id: Optional[str] = None
    client_ip: Optional[str] = None
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
