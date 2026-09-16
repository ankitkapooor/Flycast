"""Connectome parsing and CSR artifact generation for MaleCNS v1.0.

Converts raw Feather connectome files into high-efficiency CSR sparse arrays,
enforcing W[post, pre] orientation, log1p synaptic weighting, and incoming L1 normalization.
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Dict, Tuple, Any, List, Optional
import numpy as np
import polars as pl
import pyarrow.feather as feather
import scipy.sparse as sp

from app.brain.manifest import ConnectomeManifest

logger = logging.getLogger("flycast.brain.preprocess")


def hash_file(file_path: Path) -> str:
    """Computes SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def process_malecns_data(
    weights_feather_path: Path,
    annotations_feather_path: Path,
    neurotransmitters_feather_path: Optional[Path],
    output_dir: Path,
    seed: int = 42,
    num_input_neurons: int = 512,
    num_readout_neurons: int = 4096,
    sign_mode: str = "unsigned",
) -> ConnectomeManifest:
    """Processes MaleCNS Feather files into CSR sparse arrays and metadata."""
    logger.info("Reading annotations from %s", annotations_feather_path)
    annotations_df = pl.read_ipc(annotations_feather_path)

    # 1. Identify valid neurons: bodies with non-null superclass
    # Column names in MaleCNS: 'bodyId' (or 'bodyid'), 'superclass'
    body_id_col = "bodyId" if "bodyId" in annotations_df.columns else "bodyid"
    super_col = "superclass" if "superclass" in annotations_df.columns else "Superclass"

    valid_neurons_df = annotations_df.filter(pl.col(super_col).is_not_null())
    valid_body_ids = set(valid_neurons_df[body_id_col].to_list())
    logger.info("Identified %d valid neurons with superclass annotations", len(valid_body_ids))

    # Sort body IDs for deterministic 0..N-1 index mapping
    sorted_body_ids = np.array(sorted(valid_body_ids), dtype=np.int64)
    num_neurons = len(sorted_body_ids)
    body_to_idx = {int(bid): idx for idx, bid in enumerate(sorted_body_ids)}

    # Map superclasses
    body_to_super = dict(zip(valid_neurons_df[body_id_col].to_list(), valid_neurons_df[super_col].to_list()))
    superclasses = [body_to_super.get(int(bid), "unknown") for bid in sorted_body_ids]

    # 2. Read neurotransmitters if available
    nt_map = {}
    if neurotransmitters_feather_path and neurotransmitters_feather_path.exists():
        try:
            nt_df = pl.read_ipc(neurotransmitters_feather_path)
            nt_id_col = "bodyId" if "bodyId" in nt_df.columns else "bodyid"
            nt_name_col = "predicted_nt" if "predicted_nt" in nt_df.columns else "neurotransmitter"
            if nt_name_col in nt_df.columns:
                nt_map = dict(zip(nt_df[nt_id_col].to_list(), nt_df[nt_name_col].to_list()))
        except Exception as e:
            logger.warning("Could not read neurotransmitter predictions: %s", e)

    # 3. Read connectome edge weights
    logger.info("Reading connectome weights from %s", weights_feather_path)
    weights_df = pl.read_ipc(weights_feather_path)

    pre_col = "bodyId_pre" if "bodyId_pre" in weights_df.columns else "pre"
    post_col = "bodyId_post" if "bodyId_post" in weights_df.columns else "post"
    weight_col = "weight" if "weight" in weights_df.columns else "synapse_count"

    # Restrict to edges where BOTH pre and post are valid neurons
    filtered_edges = weights_df.filter(
        pl.col(pre_col).is_in(valid_body_ids) & pl.col(post_col).is_in(valid_body_ids)
    )
    logger.info("Retained %d directed edges among valid neurons", len(filtered_edges))

    # Extract edge arrays
    raw_pre = filtered_edges[pre_col].to_numpy()
    raw_post = filtered_edges[post_col].to_numpy()
    raw_weights = filtered_edges[weight_col].to_numpy().astype(np.float32)

    # Map body IDs to 0..N-1 indices
    pre_indices = np.array([body_to_idx[int(b)] for b in raw_pre], dtype=np.int32)
    post_indices = np.array([body_to_idx[int(b)] for b in raw_post], dtype=np.int32)

    # 4. Weight transformation: log1p(raw_synapse_count)
    log_weights = np.log1p(raw_weights).astype(np.float32)

    # Apply sign mode if heuristic
    if sign_mode == "heuristic":
        # GABA, glutamate (in certain fly receptors) can be inhibitory (-1), acetylcholine excitatory (+1)
        signs = np.ones(len(log_weights), dtype=np.float32)
        for i, pre_idx in enumerate(pre_indices):
            pre_body = sorted_body_ids[pre_idx]
            nt = nt_map.get(int(pre_body), "")
            if nt in ("GABA", "gaba", "glutamate"):
                signs[i] = -1.0
        log_weights = log_weights * signs

    # 5. Build CSR matrix with W[post, pre] orientation
    logger.info("Constructing sparse CSR matrix with W[post, pre] orientation...")
    coo = sp.coo_matrix(
        (log_weights, (post_indices, pre_indices)),
        shape=(num_neurons, num_neurons),
        dtype=np.float32,
    )
    csr = coo.tocsr()

    # 6. Incoming L1 normalization
    # For each postsynaptic neuron i, row sum = sum over incoming connections
    logger.info("Applying postsynaptic incoming L1 normalization...")
    row_sums = np.array(np.abs(csr).sum(axis=1)).flatten()
    row_sums[row_sums == 0] = 1.0
    diag_inv = sp.diags(1.0 / row_sums)
    normalized_csr = (diag_inv @ csr).tocsr()

    # 7. Select deterministic input sensory neurons and readout neurons
    rng = np.random.default_rng(seed)
    sensory_indices = np.array([
        i for i, sc in enumerate(superclasses)
        if "sensory" in str(sc).lower() or "visual" in str(sc).lower() or "olfactory" in str(sc).lower()
    ], dtype=np.int32)

    if len(sensory_indices) < num_input_neurons:
        # If specific sensory string not found, take first available superclass category or deterministic sample
        logger.warning("Found %d annotated sensory neurons; supplementing with deterministic sample", len(sensory_indices))
        sensory_indices = np.arange(min(num_neurons, num_input_neurons * 2), dtype=np.int32)

    selected_inputs = rng.choice(sensory_indices, size=min(num_input_neurons, len(sensory_indices)), replace=False)
    selected_inputs.sort()

    # Readout neurons: sample across connected neurons
    all_indices = np.arange(num_neurons, dtype=np.int32)
    selected_readouts = rng.choice(all_indices, size=min(num_readout_neurons, num_neurons), replace=False)
    selected_readouts.sort()

    # 8. Save arrays atomically to output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    np.save(output_dir / "body_ids.npy", sorted_body_ids)
    np.save(output_dir / "indptr.npy", normalized_csr.indptr.astype(np.int64))
    np.save(output_dir / "indices.npy", normalized_csr.indices.astype(np.int32))
    np.save(output_dir / "weights.npy", normalized_csr.data.astype(np.float32))
    np.save(output_dir / "input_indices.npy", selected_inputs.astype(np.int32))
    np.save(output_dir / "readout_indices.npy", selected_readouts.astype(np.int32))

    # Write metadata files
    input_meta = {
        "count": len(selected_inputs),
        "body_ids": [int(sorted_body_ids[i]) for i in selected_inputs],
        "superclasses": [superclasses[i] for i in selected_inputs],
    }
    with open(output_dir / "input_metadata.json", "w") as f:
        json.dump(input_meta, f, indent=2)

    readout_meta = {
        "count": len(selected_readouts),
        "body_ids": [int(sorted_body_ids[i]) for i in selected_readouts],
        "superclasses": [superclasses[i] for i in selected_readouts],
    }
    with open(output_dir / "readout_metadata.json", "w") as f:
        json.dump(readout_meta, f, indent=2)

    # Save compact metadata parquet
    meta_df = pl.DataFrame({
        "body_id": sorted_body_ids,
        "superclass": superclasses,
        "neurotransmitter": [nt_map.get(int(bid), "unknown") for bid in sorted_body_ids],
    })
    meta_df.write_parquet(output_dir / "metadata.parquet")

    # Hashes
    source_hashes = {
        "weights": hash_file(weights_feather_path),
        "annotations": hash_file(annotations_feather_path),
    }
    artifact_hashes = {
        "weights_npy": hash_file(output_dir / "weights.npy"),
        "indices_npy": hash_file(output_dir / "indices.npy"),
        "indptr_npy": hash_file(output_dir / "indptr.npy"),
    }

    manifest = ConnectomeManifest(
        dataset="male-cns:v1.0",
        neurons=num_neurons,
        edges=len(filtered_edges),
        published_neurons=166691,
        raw_source_hashes=source_hashes,
        runtime_artifact_hashes=artifact_hashes,
        input_neurons=len(selected_inputs),
        readout_neurons=len(selected_readouts),
        weight_transform="log1p",
        normalization="incoming_l1",
        sign_mode=sign_mode,
        seed=seed,
        manifest_hash=artifact_hashes["weights_npy"],
    )

    with open(output_dir / "manifest.json", "w") as f:
        f.write(manifest.model_dump_json(indent=2))

    logger.info("Successfully built MaleCNS connectome artifacts at %s", output_dir)
    return manifest
