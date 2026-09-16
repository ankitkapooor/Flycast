"""Manifest definitions and serialization for the runtime connectome."""

from datetime import datetime, timezone
from typing import Dict, Optional
from pydantic import BaseModel, Field


class ConnectomeManifest(BaseModel):
    dataset: str = "male-cns:v1.0"
    built_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    neurons: int
    edges: int
    published_neurons: int = 166691
    raw_source_hashes: Dict[str, str] = Field(default_factory=dict)
    runtime_artifact_hashes: Dict[str, str] = Field(default_factory=dict)
    input_neurons: int = 512
    readout_neurons: int = 4096
    weight_transform: str = "log1p"
    normalization: str = "incoming_l1"
    sign_mode: str = "unsigned"
    seed: int = 42
    manifest_hash: Optional[str] = None
