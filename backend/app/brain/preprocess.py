"""Connectome parsing and CSR artifact generation for MaleCNS v1.0.

Converts raw Feather connectome files into high-efficiency CSR sparse arrays
using bounded-memory streaming Arrow IPC ingestion, W[post, pre] orientation,
log1p synaptic weighting, and incoming postsynaptic L1 normalization.
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Dict, Tuple, Any, List, Optional
import numpy as np
import polars as pl
import pyarrow as pa
import pyarrow.ipc as ipc
import scipy.sparse as sp

from app.brain.manifest import ConnectomeManifest
from app.brain.feather_reader import read_feather_safe

logger = logging.getLogger("flycast.brain.preprocess")


def log_memory(stage: str) -> None:
    """Logs current process RSS memory using psutil."""
    try:
        import psutil
        rss_mb = psutil.Process().memory_info().rss / (1024 * 1024)
        logger.info("[MEM] %s: %.1f MB RSS", stage, rss_mb)
    except Exception:
        pass


def hash_file(file_path: Path) -> str:
    """Computes SHA-256 hash of a file in bounded 1MB chunks."""
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
    """Processes MaleCNS Feather files into CSR sparse arrays and metadata

    using bounded-memory streaming Arrow IPC ingestion.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # 1. Annotations load & valid neuron curation
    # -------------------------------------------------------------------------
    log_memory("before annotation load")
    logger.info("Reading annotations from %s using safe feather reader", annotations_feather_path)
    annotations_df = read_feather_safe(annotations_feather_path)

    # Identify body ID column
    if "body" in annotations_df.columns:
        body_id_col = "body"
    elif "bodyId" in annotations_df.columns:
        body_id_col = "bodyId"
    elif "bodyid" in annotations_df.columns:
        body_id_col = "bodyid"
    else:
        raise ValueError(f"Annotations missing body ID column. Columns: {annotations_df.columns}")

    super_col = "superclass" if "superclass" in annotations_df.columns else "Superclass"
    if super_col not in annotations_df.columns:
        raise ValueError(f"Annotations missing superclass column. Columns: {annotations_df.columns}")

    # Curate valid neurons: bodies with non-null superclass
    valid_neurons_df = annotations_df.filter(pl.col(super_col).is_not_null())
    valid_body_ids = np.unique(valid_neurons_df[body_id_col].to_numpy()).astype(np.int64)

    # Sort body IDs for deterministic 0..N-1 index mapping
    sorted_body_ids = np.sort(valid_body_ids)
    num_neurons = len(sorted_body_ids)
    logger.info("Identified %d valid curated neurons with superclass annotations", num_neurons)

    # Extract superclasses for curated neurons
    ann_bids = valid_neurons_df[body_id_col].to_numpy()
    ann_scs = valid_neurons_df[super_col].to_list()
    body_to_super = dict(zip(ann_bids, ann_scs))
    superclasses = [body_to_super.get(int(bid), "unknown") for bid in sorted_body_ids]

    # Free annotation DataFrames immediately
    del valid_neurons_df, annotations_df, body_to_super
    log_memory("after annotation load")

    # -------------------------------------------------------------------------
    # 2. Neurotransmitter predictions load (MaleCNS uses column 'body')
    # -------------------------------------------------------------------------
    log_memory("before neurotransmitter load")
    nt_map: Dict[int, str] = {}
    if neurotransmitters_feather_path and neurotransmitters_feather_path.exists():
        try:
            logger.info("Reading neurotransmitters from %s using safe feather reader", neurotransmitters_feather_path)
            nt_df = read_feather_safe(neurotransmitters_feather_path)

            # Robust body ID column resolution
            if "body" in nt_df.columns:
                nt_id_col = "body"
            elif "bodyId" in nt_df.columns:
                nt_id_col = "bodyId"
            elif "bodyid" in nt_df.columns:
                nt_id_col = "bodyid"
            else:
                logger.warning("Neurotransmitter table missing body column. Columns: %s", nt_df.columns)
                nt_id_col = None

            # Robust neurotransmitter prediction column resolution
            nt_name_col = None
            for candidate in ["consensus_nt", "predicted_nt", "neurotransmitter", "nt_type"]:
                if candidate in nt_df.columns:
                    nt_name_col = candidate
                    break

            if nt_id_col and nt_name_col:
                nt_bids = nt_df[nt_id_col].to_numpy()
                nt_names = nt_df[nt_name_col].to_list()
                nt_map = {
                    int(bid): str(name)
                    for bid, name in zip(nt_bids, nt_names)
                    if bid is not None and name is not None
                }
                logger.info("Joined %d neurotransmitter predictions using column '%s'", len(nt_map), nt_id_col)
            else:
                logger.warning("Could not identify neurotransmitter prediction columns in: %s", nt_df.columns)

            del nt_df
        except Exception as e:
            logger.warning("Could not read neurotransmitter predictions: %s", e)

    # Precompute per-neuron signs for Dale's principle / heuristic sign mode
    neuron_signs = np.ones(num_neurons, dtype=np.float32)
    if sign_mode == "heuristic":
        for i, bid in enumerate(sorted_body_ids):
            pred_nt = nt_map.get(int(bid), "").lower()
            if pred_nt in ("gaba", "glutamate", "glycine"):
                neuron_signs[i] = -1.0
    log_memory("after neurotransmitter load")

    # -------------------------------------------------------------------------
    # 3. Streaming Arrow IPC Ingestion: Validate Schema
    # -------------------------------------------------------------------------
    log_memory("before weights scan")
    logger.info("Opening connectivity Feather file via memory-mapped Arrow IPC: %s", weights_feather_path)
    source = pa.memory_map(str(weights_feather_path), "r")
    reader = ipc.open_file(source)

    schema_names = reader.schema.names
    num_batches = reader.num_record_batches
    logger.info("Connectivity file opened successfully. Record batches: %d, Schema: %s", num_batches, schema_names)

    # Resolve pre, post, weight column names
    pre_col = None
    for cand in ["body_pre", "bodyId_pre", "bodyid_pre", "pre"]:
        if cand in schema_names:
            pre_col = cand
            break

    post_col = None
    for cand in ["body_post", "bodyId_post", "bodyid_post", "post"]:
        if cand in schema_names:
            post_col = cand
            break

    weight_col = None
    for cand in ["weight", "synapse_count", "count"]:
        if cand in schema_names:
            weight_col = cand
            break

    if not (pre_col and post_col and weight_col):
        raise ValueError(
            f"Connectivity table missing required columns. Schema names: {schema_names}, "
            f"resolved: pre={pre_col}, post={post_col}, weight={weight_col}"
        )

    logger.info("Using connectivity columns: pre='%s', post='%s', weight='%s'", pre_col, post_col, weight_col)

    # -------------------------------------------------------------------------
    # 4. PASS 1: Count retained edges & accumulate incoming weight totals
    # -------------------------------------------------------------------------
    logger.info("[PASS 1] Starting scan of %d record batches to count valid edges and compute incoming sums...", num_batches)
    incoming_totals = np.zeros(num_neurons, dtype=np.float64)
    total_valid_edges = 0
    total_raw_rows = 0

    for i in range(num_batches):
        batch = reader.get_batch(i)
        raw_pre = batch.column(pre_col).to_numpy(zero_copy_only=False).astype(np.int64, copy=False)
        raw_post = batch.column(post_col).to_numpy(zero_copy_only=False).astype(np.int64, copy=False)
        raw_weights = batch.column(weight_col).to_numpy(zero_copy_only=False).astype(np.float32, copy=False)

        total_raw_rows += len(raw_pre)

        # Vectorized membership check using np.searchsorted
        idx_pre = np.searchsorted(sorted_body_ids, raw_pre)
        valid_pre_b = idx_pre < num_neurons
        safe_idx_pre = np.where(valid_pre_b, idx_pre, 0)
        mask_pre = valid_pre_b & (sorted_body_ids[safe_idx_pre] == raw_pre)

        idx_post = np.searchsorted(sorted_body_ids, raw_post)
        valid_post_b = idx_post < num_neurons
        safe_idx_post = np.where(valid_post_b, idx_post, 0)
        mask_post = valid_post_b & (sorted_body_ids[safe_idx_post] == raw_post)

        valid_mask = mask_pre & mask_post
        n_valid = int(np.count_nonzero(valid_mask))
        if n_valid > 0:
            valid_post_idx = idx_post[valid_mask]
            valid_w = np.maximum(raw_weights[valid_mask], 0.0)
            transformed = np.log1p(valid_w, dtype=np.float32)
            np.add.at(incoming_totals, valid_post_idx, transformed)
            total_valid_edges += n_valid

        if (i + 1) % 10 == 0 or (i + 1) == num_batches:
            try:
                import psutil
                rss_mb = psutil.Process().memory_info().rss / (1024 * 1024)
            except Exception:
                rss_mb = 0.0
            logger.info(
                "[PASS 1] batch %d / %d | raw rows: %d | valid edges: %d | RSS: %.1f MB",
                i + 1, num_batches, total_raw_rows, total_valid_edges, rss_mb
            )

        del batch, raw_pre, raw_post, raw_weights, idx_pre, idx_post, mask_pre, mask_post, valid_mask

    log_memory("after pass 1")
    logger.info(
        "Pass 1 complete: scanned %d raw rows, retained %d valid edges among %d curated neurons",
        total_raw_rows, total_valid_edges, num_neurons
    )

    if total_valid_edges == 0:
        raise ValueError("No valid edges found matching curated neuron body IDs.")

    # -------------------------------------------------------------------------
    # 5. PASS 2: Generate normalized edges into disk-backed temporary arrays
    # -------------------------------------------------------------------------
    # Ensure zero incoming totals do not cause division by zero
    incoming_denominators = np.where(incoming_totals > 0, incoming_totals, 1.0).astype(np.float32)
    del incoming_totals

    temp_rows_path = output_dir / "temp_rows.bin"
    temp_cols_path = output_dir / "temp_cols.bin"
    temp_weights_path = output_dir / "temp_weights.bin"

    rows_mm = np.memmap(temp_rows_path, dtype=np.int32, mode="w+", shape=(total_valid_edges,))
    cols_mm = np.memmap(temp_cols_path, dtype=np.int32, mode="w+", shape=(total_valid_edges,))
    weights_mm = np.memmap(temp_weights_path, dtype=np.float32, mode="w+", shape=(total_valid_edges,))

    log_memory("before pass 2")
    logger.info("[PASS 2] Streaming batches to write normalized edges to disk-backed memmap...")
    offset = 0
    sample_edge_pre: Optional[int] = None
    sample_edge_post: Optional[int] = None

    for i in range(num_batches):
        batch = reader.get_batch(i)
        raw_pre = batch.column(pre_col).to_numpy(zero_copy_only=False).astype(np.int64, copy=False)
        raw_post = batch.column(post_col).to_numpy(zero_copy_only=False).astype(np.int64, copy=False)
        raw_weights = batch.column(weight_col).to_numpy(zero_copy_only=False).astype(np.float32, copy=False)

        idx_pre = np.searchsorted(sorted_body_ids, raw_pre)
        valid_pre_b = idx_pre < num_neurons
        safe_idx_pre = np.where(valid_pre_b, idx_pre, 0)
        mask_pre = valid_pre_b & (sorted_body_ids[safe_idx_pre] == raw_pre)

        idx_post = np.searchsorted(sorted_body_ids, raw_post)
        valid_post_b = idx_post < num_neurons
        safe_idx_post = np.where(valid_post_b, idx_post, 0)
        mask_post = valid_post_b & (sorted_body_ids[safe_idx_post] == raw_post)

        valid_mask = mask_pre & mask_post
        n_valid = int(np.count_nonzero(valid_mask))
        if n_valid > 0:
            valid_pre_idx = idx_pre[valid_mask].astype(np.int32)
            valid_post_idx = idx_post[valid_mask].astype(np.int32)
            valid_w = np.maximum(raw_weights[valid_mask], 0.0)

            # Biological direction: pre -> post maps to row = post, col = pre
            row = valid_post_idx
            col = valid_pre_idx

            # Normalized weight: log1p(raw_weight) / incoming_totals[post]
            norm_w = np.log1p(valid_w, dtype=np.float32) / incoming_denominators[valid_post_idx]

            if sign_mode == "heuristic":
                norm_w = norm_w * neuron_signs[valid_pre_idx]

            rows_mm[offset : offset + n_valid] = row
            cols_mm[offset : offset + n_valid] = col
            weights_mm[offset : offset + n_valid] = norm_w

            if sample_edge_pre is None:
                sample_edge_pre = int(valid_pre_idx[0])
                sample_edge_post = int(valid_post_idx[0])

            offset += n_valid

        if (i + 1) % 10 == 0 or (i + 1) == num_batches:
            try:
                import psutil
                rss_mb = psutil.Process().memory_info().rss / (1024 * 1024)
            except Exception:
                rss_mb = 0.0
            logger.info(
                "[PASS 2] batch %d / %d | edges written: %d / %d | RSS: %.1f MB",
                i + 1, num_batches, offset, total_valid_edges, rss_mb
            )

        del batch, raw_pre, raw_post, raw_weights, idx_pre, idx_post, mask_pre, mask_post, valid_mask

    assert offset == total_valid_edges, f"Expected {total_valid_edges} edges written, got {offset}"
    rows_mm.flush()
    cols_mm.flush()
    weights_mm.flush()

    # Close and release memory mapped IPC reader
    del reader, source
    log_memory("after pass 2")

    # -------------------------------------------------------------------------
    # 6. CSR Construction & Verification
    # -------------------------------------------------------------------------
    log_memory("before CSR construction")
    logger.info("Constructing sparse CSR matrix shape (%d, %d)...", num_neurons, num_neurons)
    W = sp.csr_matrix(
        (weights_mm, (rows_mm, cols_mm)),
        shape=(num_neurons, num_neurons),
        dtype=np.float32,
    )
    W.sum_duplicates()
    W.sort_indices()

    # Immediately release memmaps and delete disk-backed temporary files
    del rows_mm, cols_mm, weights_mm
    temp_rows_path.unlink(missing_ok=True)
    temp_cols_path.unlink(missing_ok=True)
    temp_weights_path.unlink(missing_ok=True)
    log_memory("after CSR construction")

    # Rigorous validation before serializing artifacts
    assert W.shape == (num_neurons, num_neurons), f"Expected shape {(num_neurons, num_neurons)}, got {W.shape}"
    retained_edge_count = int(W.nnz)
    assert retained_edge_count > 0, "Constructed CSR matrix has 0 nonzero entries"
    assert np.isfinite(W.data).all(), "Non-finite weights found in CSR matrix"
    assert W.data.dtype == np.float32, f"Expected float32 data, got {W.data.dtype}"

    # Directionality verification
    if sample_edge_post is not None and sample_edge_pre is not None:
        assert W[sample_edge_post, sample_edge_pre] != 0.0, (
            f"Directionality check failed: biological pre ({sample_edge_pre}) -> post ({sample_edge_post}) "
            f"must have W[post, pre] != 0, but W[{sample_edge_post}, {sample_edge_pre}] == 0"
        )

    # -------------------------------------------------------------------------
    # 7. Sensory Input Neurons and Readout Electrodes Selection
    # -------------------------------------------------------------------------
    rng = np.random.default_rng(seed)
    sensory_indices = np.array([
        i for i, sc in enumerate(superclasses)
        if "sensory" in str(sc).lower() or "visual" in str(sc).lower() or "olfactory" in str(sc).lower()
    ], dtype=np.int32)

    if len(sensory_indices) < num_input_neurons:
        logger.warning("Found %d annotated sensory neurons; supplementing with deterministic sample", len(sensory_indices))
        sensory_indices = np.arange(min(num_neurons, num_input_neurons * 2), dtype=np.int32)

    selected_inputs = rng.choice(sensory_indices, size=min(num_input_neurons, len(sensory_indices)), replace=False)
    selected_inputs.sort()

    all_indices = np.arange(num_neurons, dtype=np.int32)
    selected_readouts = rng.choice(all_indices, size=min(num_readout_neurons, num_neurons), replace=False)
    selected_readouts.sort()

    # -------------------------------------------------------------------------
    # 8. Artifact Serialization
    # -------------------------------------------------------------------------
    log_memory("before artifact serialization")
    np.save(output_dir / "body_ids.npy", sorted_body_ids)
    np.save(output_dir / "indptr.npy", W.indptr.astype(np.int64))
    np.save(output_dir / "indices.npy", W.indices.astype(np.int32))
    np.save(output_dir / "weights.npy", W.data.astype(np.float32))
    np.save(output_dir / "input_indices.npy", selected_inputs.astype(np.int32))
    np.save(output_dir / "readout_indices.npy", selected_readouts.astype(np.int32))

    # Write metadata JSON files
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
    del meta_df

    # File hashes
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
        edges=retained_edge_count,
        runtime_neurons=num_neurons,
        runtime_edges=retained_edge_count,
        matrix_shape=[num_neurons, num_neurons],
        matrix_nnz=retained_edge_count,
        published_neurons=166691,
        raw_source_hashes=source_hashes,
        runtime_artifact_hashes=artifact_hashes,
        input_neurons=len(selected_inputs),
        readout_neurons=len(selected_readouts),
        weight_transform="log1p",
        normalization="incoming_l1",
        sign_mode=sign_mode,
        seed=seed,
        is_fixture=False,
        brain_mode="real",
        manifest_hash=artifact_hashes["weights_npy"],
    )

    with open(output_dir / "manifest.json", "w") as f:
        f.write(manifest.model_dump_json(indent=2))

    log_memory("after artifact serialization")

    logger.info(
        "Successfully built MaleCNS connectome artifacts at %s:\n"
        "  - Dataset: %s\n"
        "  - Brain Mode: %s\n"
        "  - Is Fixture: %s\n"
        "  - Runtime Neurons: %d\n"
        "  - Runtime Edges: %d\n"
        "  - Matrix Shape: (%d, %d)\n"
        "  - Matrix NNZ: %d\n"
        "  - Sensory Input Neurons: %d\n"
        "  - Readout Electrodes: %d",
        output_dir,
        manifest.dataset,
        manifest.brain_mode,
        manifest.is_fixture,
        manifest.runtime_neurons,
        manifest.runtime_edges,
        manifest.matrix_shape[0],
        manifest.matrix_shape[1],
        manifest.matrix_nnz,
        manifest.input_neurons,
        manifest.readout_neurons,
    )
    return manifest
