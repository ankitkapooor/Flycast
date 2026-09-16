"""Tests for Persistence and Autoregressive Ridge baselines."""

import numpy as np
from app.forecasting.baselines import (
    evaluate_persistence_baseline,
    evaluate_autoregressive_ridge_baseline,
)


def test_persistence_baseline():
    """Verifies that persistence repeats the last observed value for all horizons."""
    T = 100
    series = np.arange(T, dtype=np.float64)  # 0, 1, 2, ..., 99
    train_slice = slice(0, 70)
    val_slice = slice(70, 85)
    test_slice = slice(85, 100)
    horizon = 3

    res = evaluate_persistence_baseline(
        raw_target=series,
        train_slice=train_slice,
        val_slice=val_slice,
        test_slice=test_slice,
        horizon=horizon,
    )

    # Future forecast should repeat the very last element (99)
    assert np.allclose(res["future_forecast"], [99.0, 99.0, 99.0])
    assert "rmse" in res["metrics"]
    assert "mae" in res["metrics"]


def test_autoregressive_ridge_baseline():
    """Verifies AR Ridge baseline fits and predicts multi-horizon values."""
    T = 200
    t = np.linspace(0, 20, T)
    series = np.sin(t)
    train_slice = slice(0, 140)
    val_slice = slice(140, 170)
    test_slice = slice(170, 200)
    horizon = 5

    res = evaluate_autoregressive_ridge_baseline(
        scaled_target=series,
        raw_target=series,
        target_mean=0.0,
        target_scale=1.0,
        train_slice=train_slice,
        val_slice=val_slice,
        test_slice=test_slice,
        horizon=horizon,
        candidate_lags=[10, 20],
    )

    assert len(res["future_forecast"]) == horizon
    assert res["metrics"]["rmse"] >= 0.0
    assert "best_lag" in res
    assert "best_alpha" in res
