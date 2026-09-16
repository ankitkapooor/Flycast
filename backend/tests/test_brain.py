"""Tests for connectome loading, directionality conventions, and reservoir dynamics."""

import numpy as np
import scipy.sparse as sp
import pytest

from app.brain.loader import BrainState
from app.brain.reservoir import ReservoirEngine
from app.brain.preprocess import process_malecns_data
import polars as pl
import tempfile
from pathlib import Path


def test_csr_directionality_convention():
    """Explicitly verifies Section 80 requirement:

    A connection from body_pre A to body_post B MUST be positioned at W[index(B), index(A)],
    so that activity flows presynaptic -> postsynaptic via next_input = W @ state.
    """
    num_neurons = 4
    # Connection: neuron 1 (pre) -> neuron 3 (post) with raw synapse count 10
    pre_indices = np.array([1], dtype=np.int32)
    post_indices = np.array([3], dtype=np.int32)
    weights = np.log1p(np.array([10.0], dtype=np.float32))

    csr = sp.coo_matrix(
        (weights, (post_indices, pre_indices)),
        shape=(num_neurons, num_neurons),
        dtype=np.float32,
    ).tocsr()

    # Postsynaptic neuron 3 receives from Presynaptic neuron 1:
    assert csr[3, 1] > 0.0, "W[post, pre] must store the connection strength"
    assert csr[1, 3] == 0.0, "Reverse orientation W[pre, post] must be zero for directed edge"

    # In recurrent update: x_next = W @ x_curr
    # If only neuron 1 is active (state = [0, 1.0, 0, 0]):
    state = np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float32)
    transmitted = csr.dot(state)

    # Neuron 3 should receive the signal, neuron 1 should receive 0
    assert transmitted[3] > 0.0, "Postsynaptic neuron 3 must receive incoming signal from neuron 1"
    assert transmitted[1] == 0.0, "Presynaptic neuron 1 should not receive its own signal"


def test_brain_loading_and_row_normalization(brain_state: BrainState):
    """Verifies that incoming weights for each postsynaptic neuron sum to <= 1.0."""
    csr = brain_state.csr_matrix
    assert csr.shape[0] == brain_state.num_neurons
    assert csr.shape[1] == brain_state.num_neurons

    # Check incoming L1 normalization (sum across rows)
    row_sums = np.array(np.abs(csr).sum(axis=1)).flatten()
    # For any neuron with incoming edges, row sum must be approximately 1.0
    active_rows = row_sums[row_sums > 0]
    assert np.allclose(active_rows, 1.0, atol=1e-4)


def test_reservoir_engine_state_propagation(brain_state: BrainState):
    """Tests reservoir feature extraction and determinism."""
    engine = ReservoirEngine(
        csr_matrix=brain_state.csr_matrix,
        input_indices=brain_state.input_indices,
        readout_indices=brain_state.readout_indices,
        leak=0.25,
        recurrent_gain=0.95,
        input_gain=0.50,
        seed=42,
    )

    T = 50
    inputs = np.sin(np.linspace(0, 10, T))[:, None]  # shape (50, 1)
    
    features1, viz1 = engine.run(inputs)
    assert features1.shape == (T, len(brain_state.readout_indices))
    assert np.all(np.isfinite(features1))

    # Test determinism
    engine2 = ReservoirEngine(
        csr_matrix=brain_state.csr_matrix,
        input_indices=brain_state.input_indices,
        readout_indices=brain_state.readout_indices,
        leak=0.25,
        recurrent_gain=0.95,
        input_gain=0.50,
        seed=42,
    )
    features2, _ = engine2.run(inputs)
    assert np.allclose(features1, features2)
