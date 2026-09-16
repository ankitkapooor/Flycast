"""Synthetic Drosophila CNS fixture for testing, CI, and lightweight local development.

Generates a realistic small-scale graph (300 neurons, ~3,000 directed edges)
following the exact schema and CSR conventions of MaleCNS v1.0.
"""

import json
import numpy as np
import scipy.sparse as sp
from pathlib import Path
from typing import Dict, Any

from app.brain.manifest import ConnectomeManifest


def generate_fixture_connectome(
    num_neurons: int = 300,
    edge_density: float = 0.035,
    seed: int = 42,
) -> Dict[str, Any]:
    """Generates synthetic Drosophila CNS graph data."""
    rng = np.random.default_rng(seed)

    # 1. Generate unique 64-bit body IDs (mimicking FlyEM IDs)
    base_id = 5813000000
    body_ids = np.array(
        [base_id + i * 137 for i in range(num_neurons)], dtype=np.int64
    )

    # 2. Annotate superclasses: 20% sensory, 60% central/interneuron, 20% motor/efferent
    superclasses = []
    n_sensory = max(16, int(num_neurons * 0.20))
    n_motor = max(16, int(num_neurons * 0.20))
    n_central = num_neurons - n_sensory - n_motor

    for _ in range(n_sensory):
        superclasses.append("sensory")
    for _ in range(n_central):
        superclasses.append("central")
    for _ in range(n_motor):
        superclasses.append("motor")

    # 3. Directed connections: pre -> post
    # Ensure recurrent connectivity with realistic log-normal synapse counts
    adj = rng.random((num_neurons, num_neurons)) < edge_density
    # No self-loops in primary connectome
    np.fill_diagonal(adj, False)

    # Ensure every neuron has at least some incoming connections
    for i in range(num_neurons):
        if not np.any(adj[i, :]):
            donor = rng.integers(0, num_neurons)
            if donor != i:
                adj[i, donor] = True

    post_indices, pre_indices = np.where(adj)
    # Synapse counts follow heavy-tailed log-normal distribution
    raw_synapses = np.clip(rng.lognormal(mean=1.5, sigma=1.0, size=len(pre_indices)), 1, 500).astype(np.int32)

    # 4. Weight transform: log1p(raw_synapses)
    weights = np.log1p(raw_synapses).astype(np.float32)

    # Construct CSR matrix with orientation W[post, pre]
    # In SciPy: coo_matrix((weights, (post_indices, pre_indices)), shape=(N, N)).tocsr()
    csr = sp.coo_matrix(
        (weights, (post_indices, pre_indices)),
        shape=(num_neurons, num_neurons),
        dtype=np.float32,
    ).tocsr()

    # Incoming L1 normalization: row normalization for W[post, pre]
    # For each postsynaptic neuron i, sum of incoming weights = sum over row i
    row_sums = np.array(csr.sum(axis=1)).flatten()
    row_sums[row_sums == 0] = 1.0  # avoid division by zero
    diag_inv = sp.diags(1.0 / row_sums)
    normalized_csr = (diag_inv @ csr).tocsr()

    # Input neurons: deterministic subset from sensory superclass
    sensory_indices = np.array([i for i, sc in enumerate(superclasses) if sc == "sensory"], dtype=np.int32)
    # Readout neurons: deterministic subset across all neurons
    all_indices = np.arange(num_neurons, dtype=np.int32)
    
    # Deterministic selection
    sub_rng = np.random.default_rng(seed)
    n_inputs = min(64, len(sensory_indices))
    input_indices = sub_rng.choice(sensory_indices, size=n_inputs, replace=False)
    input_indices.sort()

    n_readouts = min(128, num_neurons)
    readout_indices = sub_rng.choice(all_indices, size=n_readouts, replace=False)
    readout_indices.sort()

    return {
        "num_neurons": num_neurons,
        "num_edges": len(pre_indices),
        "body_ids": body_ids,
        "superclasses": superclasses,
        "csr": normalized_csr,
        "input_indices": input_indices,
        "readout_indices": readout_indices,
    }


def save_fixture_to_disk(target_dir: Path, num_neurons: int = 300, seed: int = 42) -> ConnectomeManifest:
    """Builds and writes a complete fixture dataset to target_dir."""
    target_dir.mkdir(parents=True, exist_ok=True)
    fixture = generate_fixture_connectome(num_neurons=num_neurons, seed=seed)

    csr = fixture["csr"]
    np.save(target_dir / "body_ids.npy", fixture["body_ids"])
    np.save(target_dir / "indptr.npy", csr.indptr.astype(np.int64))
    np.save(target_dir / "indices.npy", csr.indices.astype(np.int32))
    np.save(target_dir / "weights.npy", csr.data.astype(np.float32))
    np.save(target_dir / "input_indices.npy", fixture["input_indices"].astype(np.int32))
    np.save(target_dir / "readout_indices.npy", fixture["readout_indices"].astype(np.int32))

    # Metadata
    input_meta = {
        "count": len(fixture["input_indices"]),
        "body_ids": [int(fixture["body_ids"][i]) for i in fixture["input_indices"]],
        "superclasses": [fixture["superclasses"][i] for i in fixture["input_indices"]],
    }
    with open(target_dir / "input_metadata.json", "w") as f:
        json.dump(input_meta, f, indent=2)

    readout_meta = {
        "count": len(fixture["readout_indices"]),
        "body_ids": [int(fixture["body_ids"][i]) for i in fixture["readout_indices"]],
        "superclasses": [fixture["superclasses"][i] for i in fixture["readout_indices"]],
    }
    with open(target_dir / "readout_metadata.json", "w") as f:
        json.dump(readout_meta, f, indent=2)

    manifest = ConnectomeManifest(
        dataset="male-cns:fixture-v1.0",
        neurons=fixture["num_neurons"],
        edges=fixture["num_edges"],
        published_neurons=166691,
        input_neurons=len(fixture["input_indices"]),
        readout_neurons=len(fixture["readout_indices"]),
        weight_transform="log1p",
        normalization="incoming_l1",
        sign_mode="unsigned",
        seed=seed,
        is_fixture=True,
        brain_mode="fixture",
        manifest_hash="fixture-hash-male-cns",
    )

    with open(target_dir / "manifest.json", "w") as f:
        f.write(manifest.model_dump_json(indent=2))

    return manifest
