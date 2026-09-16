"""Connectome loader for FlyCast.

Loads the preprocessed sparse CSR connectome matrix, metadata, and neuron indices
using memory-mapped arrays where possible to avoid redundant RAM usage.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import numpy as np
import scipy.sparse as sp

from app.config import settings
from app.brain.manifest import ConnectomeManifest
from app.brain.fixture import save_fixture_to_disk

logger = logging.getLogger("flycast.brain.loader")


class BrainState:
    """In-memory or memory-mapped handles to the runtime connectome."""

    def __init__(
        self,
        manifest: ConnectomeManifest,
        body_ids: np.ndarray,
        csr_matrix: sp.csr_matrix,
        input_indices: np.ndarray,
        readout_indices: np.ndarray,
        input_metadata: Optional[Dict[str, Any]] = None,
        readout_metadata: Optional[Dict[str, Any]] = None,
    ):
        self.manifest = manifest
        self.body_ids = body_ids
        self.csr_matrix = csr_matrix
        self.input_indices = input_indices
        self.readout_indices = readout_indices
        self.input_metadata = input_metadata or {}
        self.readout_metadata = readout_metadata or {}

    @property
    def num_neurons(self) -> int:
        return self.manifest.neurons

    @property
    def num_edges(self) -> int:
        return self.manifest.edges


_GLOBAL_BRAIN: Optional[BrainState] = None


def is_brain_ready(brain_dir: Optional[Path] = None) -> bool:
    """Checks if valid brain artifacts exist in brain_dir."""
    target_dir = brain_dir or settings.brain_dir
    manifest_path = target_dir / "manifest.json"
    if not manifest_path.exists():
        return False
    required_files = [
        "body_ids.npy",
        "indptr.npy",
        "indices.npy",
        "weights.npy",
        "input_indices.npy",
        "readout_indices.npy",
    ]
    return all((target_dir / f).exists() for f in required_files)


def load_brain(brain_dir: Optional[Path] = None, force_reload: bool = False) -> BrainState:
    """Loads connectome arrays into BrainState.

    If USE_FIXTURE_BRAIN is configured and brain does not exist,
    automatically builds a synthetic fixture connectome.
    """
    global _GLOBAL_BRAIN
    if _GLOBAL_BRAIN is not None and not force_reload:
        return _GLOBAL_BRAIN

    target_dir = brain_dir or settings.brain_dir

    if not is_brain_ready(target_dir):
        if settings.USE_FIXTURE_BRAIN or not (target_dir / "manifest.json").exists():
            logger.info("Initializing fixture connectome for testing/lightweight mode at %s", target_dir)
            save_fixture_to_disk(target_dir, num_neurons=300, seed=settings.CONNECTOME_SEED)
        else:
            raise FileNotFoundError(f"Connectome not ready at {target_dir}. Please run bootstrap first.")

    manifest_path = target_dir / "manifest.json"
    with open(manifest_path, "r") as f:
        manifest_data = json.load(f)
    manifest = ConnectomeManifest(**manifest_data)

    logger.info("Loading connectome from %s (Neurons: %d, Edges: %d)", target_dir, manifest.neurons, manifest.edges)

    # Load arrays
    body_ids = np.load(target_dir / "body_ids.npy")
    indptr = np.load(target_dir / "indptr.npy")
    indices = np.load(target_dir / "indices.npy")
    weights = np.load(target_dir / "weights.npy")
    input_indices = np.load(target_dir / "input_indices.npy")
    readout_indices = np.load(target_dir / "readout_indices.npy")

    # Read metadata if present
    input_meta_path = target_dir / "input_metadata.json"
    input_meta = {}
    if input_meta_path.exists():
        with open(input_meta_path, "r") as f:
            input_meta = json.load(f)

    readout_meta_path = target_dir / "readout_metadata.json"
    readout_meta = {}
    if readout_meta_path.exists():
        with open(readout_meta_path, "r") as f:
            readout_meta = json.load(f)

    num_neurons = len(body_ids)
    csr = sp.csr_matrix(
        (weights, indices, indptr),
        shape=(num_neurons, num_neurons),
        dtype=np.float32,
    )

    _GLOBAL_BRAIN = BrainState(
        manifest=manifest,
        body_ids=body_ids,
        csr_matrix=csr,
        input_indices=input_indices,
        readout_indices=readout_indices,
        input_metadata=input_meta,
        readout_metadata=readout_meta,
    )
    return _GLOBAL_BRAIN


def get_brain() -> BrainState:
    """Returns the loaded global brain or loads it."""
    global _GLOBAL_BRAIN
    if _GLOBAL_BRAIN is None:
        return load_brain()
    return _GLOBAL_BRAIN
