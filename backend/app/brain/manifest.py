"""Manifest definitions and serialization for the runtime connectome."""

from datetime import datetime, timezone
from typing import Dict, Optional, List
from pydantic import BaseModel, Field


class ConnectomeManifest(BaseModel):
    dataset: str = "male-cns:v1.0"
    built_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    neurons: int
    edges: int
    runtime_neurons: Optional[int] = None
    runtime_edges: Optional[int] = None
    matrix_shape: Optional[List[int]] = None
    matrix_nnz: Optional[int] = None
    published_neurons: int = 166691
    raw_source_hashes: Dict[str, str] = Field(default_factory=dict)
    runtime_artifact_hashes: Dict[str, str] = Field(default_factory=dict)
    input_neurons: int = 512
    readout_neurons: int = 4096
    weight_transform: str = "log1p"
    normalization: str = "incoming_l1"
    sign_mode: str = "unsigned"
    seed: int = 42
    is_fixture: bool = False
    brain_mode: str = "real"  # "real" or "fixture"
    manifest_hash: Optional[str] = None

    def model_post_init(self, __context) -> None:
        if self.runtime_neurons is None:
            self.runtime_neurons = self.neurons
        if self.runtime_edges is None:
            self.runtime_edges = self.edges
        if self.matrix_shape is None:
            self.matrix_shape = [self.neurons, self.neurons]
        if self.matrix_nnz is None:
            self.matrix_nnz = self.edges
