"""Unit test for bounded-memory streaming Arrow IPC connectome preprocessing."""

from pathlib import Path
import json
import numpy as np
import pyarrow as pa
import pyarrow.ipc as ipc
import pyarrow.feather as feather
import polars as pl
import scipy.sparse as sp
import pytest

from app.brain.preprocess import process_malecns_data


def test_streaming_preprocess_multi_batch_and_validation(tmp_path: Path):
    """Verifies that:

    1. Multi-batch Arrow IPC files are streamed and processed independently.
    2. Invalid / non-curated body IDs (both pre and post) are discarded.
    3. Biological direction A -> B maps to W[index(B), index(A)].
    4. Incoming postsynaptic weights are L1 normalized to 1.0.
    5. Neurotransmitter table using 'body' column joins correctly.
    6. Heuristic sign mode applies inhibitory negative weights to GABA/glutamate presynaptic neurons.
    """
    data_dir = tmp_path / "raw"
    data_dir.mkdir(parents=True, exist_ok=True)
    out_dir = tmp_path / "output_brain"

    # 1. Annotations table with 4 curated neurons and 1 non-curated row (superclass is null)
    annotations_file = data_dir / "annotations.feather"
    ann_table = pa.table({
        "body": pa.array([101, 102, 103, 104, 999], type=pa.int64()),
        "superclass": pa.array(["sensory_visual", "central", "central", "motor", None], type=pa.string()),
    })
    feather.write_feather(ann_table, annotations_file)

    # 2. Neurotransmitters table using column 'body' and 'consensus_nt'
    nt_file = data_dir / "neurotransmitters.feather"
    nt_table = pa.table({
        "body": pa.array([101, 102, 103, 104], type=pa.int64()),
        "cell_type": pa.array(["vis_1", "ct_2", "ct_3", "mot_4"], type=pa.string()),
        "consensus_nt": pa.array(["acetylcholine", "gaba", "glutamate", "acetylcholine"], type=pa.string()),
    })
    feather.write_feather(nt_table, nt_file)

    # 3. Connectivity table with 3 distinct Arrow record batches
    weights_file = data_dir / "weights.feather"
    schema = pa.schema([
        ("body_pre", pa.int64()),
        ("body_post", pa.int64()),
        ("weight", pa.float32()),
    ])

    # Batch 0:
    # 101 -> 102 (valid, w=10)
    # 999 -> 102 (invalid pre 999)
    # 102 -> 103 (valid, w=20)
    batch0 = pa.record_batch([
        pa.array([101, 999, 102], type=pa.int64()),
        pa.array([102, 102, 103], type=pa.int64()),
        pa.array([10.0, 50.0, 20.0], type=pa.float32()),
    ], schema=schema)

    # Batch 1:
    # 101 -> 103 (valid, w=30)
    # 104 -> 101 (valid, w=5)
    # 888 -> 102 (invalid pre 888)
    batch1 = pa.record_batch([
        pa.array([101, 104, 888], type=pa.int64()),
        pa.array([103, 101, 102], type=pa.int64()),
        pa.array([30.0, 5.0, 99.0], type=pa.float32()),
    ], schema=schema)

    # Batch 2:
    # 102 -> 999 (invalid post 999)
    # 103 -> 104 (valid, w=40)
    batch2 = pa.record_batch([
        pa.array([102, 103], type=pa.int64()),
        pa.array([999, 104], type=pa.int64()),
        pa.array([15.0, 40.0], type=pa.float32()),
    ], schema=schema)

    with pa.OSFile(str(weights_file), "wb") as sink:
        with pa.ipc.new_file(sink, schema) as writer:
            writer.write_batch(batch0)
            writer.write_batch(batch1)
            writer.write_batch(batch2)

    # 4. Run preprocessing with heuristic sign mode
    manifest = process_malecns_data(
        weights_feather_path=weights_file,
        annotations_feather_path=annotations_file,
        neurotransmitters_feather_path=nt_file,
        output_dir=out_dir,
        seed=42,
        num_input_neurons=1,
        num_readout_neurons=2,
        sign_mode="heuristic",
    )

    # 5. Verify Manifest
    assert manifest.dataset == "male-cns:v1.0"
    assert manifest.brain_mode == "real"
    assert manifest.is_fixture is False
    assert manifest.neurons == 4
    assert manifest.runtime_neurons == 4
    # Exactly 5 valid edges retained out of 8 raw rows
    assert manifest.edges == 5
    assert manifest.runtime_edges == 5
    assert manifest.matrix_shape == [4, 4]
    assert manifest.matrix_nnz == 5

    # 6. Load resulting CSR matrix and verify properties
    body_ids = np.load(out_dir / "body_ids.npy")
    assert list(body_ids) == [101, 102, 103, 104]

    indptr = np.load(out_dir / "indptr.npy")
    indices = np.load(out_dir / "indices.npy")
    weights = np.load(out_dir / "weights.npy")

    W = sp.csr_matrix((weights, indices, indptr), shape=(4, 4), dtype=np.float32)
    assert W.shape == (4, 4)
    assert W.nnz == 5
    assert np.isfinite(W.data).all()
    assert W.data.dtype == np.float32

    # 7. Verify Directionality:
    # Body IDs map to indices: 101 -> 0, 102 -> 1, 103 -> 2, 104 -> 3
    # Edge 101 -> 102: pre=0, post=1 -> W[post, pre] = W[1, 0] != 0
    assert W[1, 0] != 0.0
    assert W[0, 1] == 0.0, "Reverse direction must be zero"

    # Edge 104 -> 101: pre=3, post=0 -> W[0, 3] != 0
    assert W[0, 3] != 0.0

    # 8. Verify Neurotransmitter Heuristic Signs & Normalization:
    # Neuron 102 is GABAergic (inhibitory). Its outgoing edge to 103 (pre=1, post=2) must be NEGATIVE
    assert W[2, 1] < 0.0, f"Expected inhibitory weight for GABAergic pre neuron, got {W[2, 1]}"

    # Neuron 101 is Cholinergic (excitatory). Its outgoing edge to 103 (pre=0, post=2) must be POSITIVE
    assert W[2, 0] > 0.0, f"Expected excitatory weight for cholinergic pre neuron, got {W[2, 0]}"

    # Check incoming L1 normalization on row 2 (post=103):
    # |W[2, 0]| + |W[2, 1]| == 1.0
    row2_l1 = abs(W[2, 0]) + abs(W[2, 1])
    assert np.isclose(row2_l1, 1.0, atol=1e-5), f"Expected row L1 norm of 1.0, got {row2_l1}"

    # Row 0 (post=101) has only one incoming edge from 104:
    assert np.isclose(abs(W[0, 3]), 1.0, atol=1e-5)

    # 9. Verify joined neurotransmitters in metadata.parquet
    meta_df = pl.read_parquet(out_dir / "metadata.parquet")
    assert meta_df.height == 4
    assert meta_df.filter(pl.col("body_id") == 102)["neurotransmitter"][0] == "gaba"
    assert meta_df.filter(pl.col("body_id") == 101)["neurotransmitter"][0] == "acetylcholine"
