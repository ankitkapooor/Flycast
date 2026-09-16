"""Tests ensuring strict absence of data leakage between train, validation, and test splits."""

import numpy as np
import polars as pl
from app.forecasting.preprocessing import parse_and_preprocess_csv


def test_zero_data_leakage_in_preprocessing():
    """Verifies that the normalization scaler parameters (mean and std) are fitted

    strictly on training slice rows, without incorporating any validation or test data.
    """
    T = 200
    # Create dataset where training set has mean 10.0, but test set has an extreme spike mean 1000.0
    times = [f"t_{i:04d}" for i in range(T)]
    
    # 70% train = 140 rows, 15% val = 30 rows, 15% test = 30 rows
    train_vals = np.full(140, 10.0)
    val_vals = np.full(30, 20.0)
    test_vals = np.full(30, 1000.0)
    signal = np.concatenate([train_vals, val_vals, test_vals])

    # Add small noise so std > 0
    rng = np.random.default_rng(42)
    signal += rng.normal(0, 0.5, size=T)

    df = pl.DataFrame({"timestamp": times, "target": signal})
    csv_bytes = df.write_csv().encode("utf-8")

    prep = parse_and_preprocess_csv(
        csv_bytes=csv_bytes,
        time_column="timestamp",
        target_column="target",
    )

    # Train slice
    n_train = prep.train_slice.stop
    expected_train_mean = float(np.mean(signal[:n_train]))
    expected_train_scale = float(np.std(signal[:n_train]))

    # Scaler mean must match training data mean, NOT the full dataset mean
    full_dataset_mean = float(np.mean(signal))
    assert abs(prep.scaler_mean - expected_train_mean) < 1e-4
    assert abs(prep.scaler_mean - full_dataset_mean) > 100.0, "Scaler leaked future test values into mean!"

    # Training scaled inputs should have mean ~ 0.0 and std ~ 1.0
    train_scaled = prep.scaled_inputs[prep.train_slice, 0]
    assert abs(float(np.mean(train_scaled))) < 1e-3
    assert abs(float(np.std(train_scaled)) - 1.0) < 1e-2

    # Test scaled inputs should NOT have mean 0.0 because of the future shift
    test_scaled = prep.scaled_inputs[prep.test_slice, 0]
    assert float(np.mean(test_scaled)) > 100.0, "Test data was improperly scaled with test statistics!"
