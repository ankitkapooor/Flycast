"""Tests proving the connectome wiring directly affects computation (Section 101: No Fake Brain)."""

import numpy as np
from app.brain.loader import BrainState
from app.brain.reservoir import ReservoirEngine
from app.brain.controls import build_weight_shuffled_matrix
from app.forecasting.readout import train_and_evaluate_readout


def test_connectome_participates_in_computation(brain_state: BrainState):
    """Section 101 Acceptance Criterion:

    Running the same input signal with the same seed through:
    1. Real graph
    vs
    2. Weight-shuffled graph
    MUST produce distinct reservoir states and different forecast metrics.
    This guarantees that connectome synaptic organization actively participates in computation.
    """
    T = 150
    t = np.linspace(0, 15, T)
    inputs = (np.sin(t) + 0.5 * np.cos(3 * t))[:, None]

    # 1. Real connectome reservoir
    engine_real = ReservoirEngine(
        csr_matrix=brain_state.csr_matrix,
        input_indices=brain_state.input_indices,
        readout_indices=brain_state.readout_indices,
        leak=0.25,
        recurrent_gain=0.95,
        input_gain=0.50,
        seed=42,
    )
    features_real, _ = engine_real.run(inputs)

    # 2. Control connectome: same topology, shuffled weights
    shuffled_W = build_weight_shuffled_matrix(brain_state.csr_matrix, seed=42)
    engine_shuffled = ReservoirEngine(
        csr_matrix=shuffled_W,
        input_indices=brain_state.input_indices,
        readout_indices=brain_state.readout_indices,
        leak=0.25,
        recurrent_gain=0.95,
        input_gain=0.50,
        seed=42,
    )
    features_shuffled, _ = engine_shuffled.run(inputs)

    # Features must differ!
    diff = np.max(np.abs(features_real - features_shuffled))
    assert diff > 1e-3, f"Real and shuffled reservoir produced identical states! (diff={diff})"

    # Forecasts produced from readouts must also differ
    target_series = inputs[:, 0]
    train_slice = slice(0, 100)
    val_slice = slice(100, 125)
    test_slice = slice(125, 150)

    res_real = train_and_evaluate_readout(
        features=features_real,
        scaled_target=target_series,
        target_mean=0.0,
        target_scale=1.0,
        train_slice=train_slice,
        val_slice=val_slice,
        test_slice=test_slice,
        horizon=5,
    )

    res_shuffled = train_and_evaluate_readout(
        features=features_shuffled,
        scaled_target=target_series,
        target_mean=0.0,
        target_scale=1.0,
        train_slice=train_slice,
        val_slice=val_slice,
        test_slice=test_slice,
        horizon=5,
    )

    pred_diff = np.max(np.abs(res_real.future_forecast_raw - res_shuffled.future_forecast_raw))
    assert pred_diff > 1e-4, f"Real and shuffled connectomes produced identical forecasts! (diff={pred_diff})"
