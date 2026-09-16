"""Integration test for the master forecasting pipeline."""

from app.brain.loader import BrainState
from app.demos.generate import generate_lorenz
from app.forecasting.pipeline import run_experiment_pipeline


def test_full_pipeline_execution(brain_state: BrainState):
    """Executes the full pipeline with progress tracking and control comparison."""
    df = generate_lorenz(num_steps=250, seed=42)
    csv_bytes = df.write_csv().encode("utf-8")

    stages_seen = []

    def progress_callback(stage: str, progress: int, msg: str):
        stages_seen.append(stage)

    res = run_experiment_pipeline(
        experiment_id="test-exp-001",
        csv_bytes=csv_bytes,
        brain=brain_state,
        time_column="timestamp",
        target_column="x_chaotic",
        forecast_horizon=5,
        run_control=True,
        progress_cb=progress_callback,
    )

    assert "preprocessing" in stages_seen
    assert "running_brain" in stages_seen
    assert "training_readout" in stages_seen
    assert "running_baselines" in stages_seen
    assert "running_control" in stages_seen

    result_dict = res.result_dict
    assert result_dict["experiment_id"] == "test-exp-001"
    assert "fly" in result_dict
    assert "rmse" in result_dict["fly"]
    assert "baselines" in result_dict
    assert "persistence" in result_dict["baselines"]
    assert "autoregressive_ridge" in result_dict["baselines"]
    assert result_dict["control"] is not None
    assert "winner" in result_dict
    assert "editorial" in result_dict
    assert len(result_dict["forecast"]["values"]) == 5

    # Check predictions DataFrame
    assert len(res.predictions_df) > 0
    assert "flycast" in res.predictions_df.columns
    assert "actual" in res.predictions_df.columns

    # Check chart payload
    assert "history" in res.chart_data
    assert "test" in res.chart_data
    assert "future" in res.chart_data
    assert "activity_viz" in res.chart_data


def test_polars_schema_override_and_mixed_float_regression():
    """Regression test for Polars builder error:

    'could not append value: 126.8119 of type: f64 to the builder; make sure that all rows have the same schema'
    Demonstrates that schema_overrides + infer_schema_length=None correctly handles
    initial nulls in interval bounds followed by floating-point values like 126.8119.
    """
    import polars as pl

    # Construct 120 test rows where lower_95 / upper_95 are None
    rows = []
    for i in range(120):
        rows.append({
            "time": f"2026-01-{(i % 28) + 1:02d}",
            "step": int(i),
            "segment": "test",
            "actual": float(i * 10),
            "flycast": float(i * 10 + 1),
            "persistence": float(i * 10),
            "autoregressive": float(i * 10 + 2),
            "lower_95": None,
            "upper_95": None,
        })

    # Append future rows with actual: None and float bounds (e.g. 126.8119)
    for h in range(5):
        rows.append({
            "time": f"+{h+1}h",
            "step": int(120 + h),
            "segment": "future",
            "actual": None,
            "flycast": float(130.0 + h),
            "persistence": float(120.0),
            "autoregressive": float(128.0 + h),
            "lower_95": float(126.8119 + h),
            "upper_95": float(150.2500 + h),
        })

    # Polars DataFrame construction with explicit schema overrides
    df = pl.DataFrame(
        rows,
        schema_overrides={
            "actual": pl.Float64,
            "flycast": pl.Float64,
            "persistence": pl.Float64,
            "autoregressive": pl.Float64,
            "lower_95": pl.Float64,
            "upper_95": pl.Float64,
        },
        infer_schema_length=None,
    )

    assert df.height == 125
    assert df["lower_95"].dtype == pl.Float64
    assert df["upper_95"].dtype == pl.Float64
    assert df["actual"].dtype == pl.Float64
    assert df["flycast"].dtype == pl.Float64
    # Check that 126.8119 was preserved exactly
    assert df["lower_95"][120] == 126.8119
    assert df["actual"][120] is None
    assert df["lower_95"][0] is None


def test_end_to_end_uploaded_series_730_rows(brain_state: BrainState):
    """Executes an end-to-end experiment on a 730-row dataset containing early integer-looking values

    and later floating-point values (e.g. 126.8119), verifying serialization.
    """
    import json
    import io
    import numpy as np
    import polars as pl

    # Create 730 rows of energy_demand
    # Early rows: integer-looking values (100.0, 105.0, 95.0)
    # Later rows: floating-point values including 126.8119
    rng = np.random.default_rng(42)
    t = np.arange(730)
    base_signal = 100.0 + 20.0 * np.sin(2 * np.pi * t / 365.0) + rng.normal(0, 5, size=730)
    # Ensure early values look like integers
    base_signal[:50] = np.round(base_signal[:50])
    # Place target value 126.8119 in dataset
    base_signal[500] = 126.8119

    from datetime import datetime, timedelta
    base_date = datetime(2023, 1, 1)
    df_upload = pl.DataFrame({
        "date": [(base_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(730)],
        "energy_demand": [float(v) for v in base_signal],
    })
    csv_bytes = df_upload.write_csv().encode("utf-8")

    res = run_experiment_pipeline(
        experiment_id="exp-energy-730",
        csv_bytes=csv_bytes,
        brain=brain_state,
        time_column="date",
        target_column="energy_demand",
        forecast_horizon=5,
        run_control=False,
    )

    # 1. Verify predictions_df structure and dtypes
    assert isinstance(res.predictions_df, pl.DataFrame)
    assert res.predictions_df["actual"].dtype == pl.Float64
    assert res.predictions_df["flycast"].dtype == pl.Float64
    assert res.predictions_df["lower_95"].dtype == pl.Float64
    assert res.predictions_df["upper_95"].dtype == pl.Float64

    # 2. Verify CSV writing succeeds without schema issues
    csv_output = res.predictions_df.write_csv()
    assert len(csv_output) > 0
    assert "lower_95" in csv_output

    # 3. Verify JSON serialization of result_dict and chart_data
    result_json_str = json.dumps(res.result_dict)
    assert len(result_json_str) > 0
    assert "forecast" in res.result_dict

    chart_json_str = json.dumps(res.chart_data)
    assert len(chart_json_str) > 0
    assert len(res.chart_data["future"]) == 5


def test_target_nan_inf_rejection_and_null_preservation():
    """Verifies that:

    - NaN in target raises a clear ValueError
    - Inf in target raises a clear ValueError
    - Nulls in target are cleanly handled by drop_nulls
    """
    import pytest
    import numpy as np
    from app.forecasting.preprocessing import parse_and_preprocess_csv

    # 1. NaN in target column
    nan_csv = (
        "date,energy_demand\n" +
        "\n".join([f"2024-01-{i%28+1:02d}_{i},{100.0 if i != 50 else 'NaN'}" for i in range(120)])
    ).encode("utf-8")

    with pytest.raises(ValueError, match="non-finite \\(NaN or Inf\\)"):
        parse_and_preprocess_csv(nan_csv, time_column="date", target_column="energy_demand")

    # 2. Inf in target column
    inf_csv = (
        "date,energy_demand\n" +
        "\n".join([f"2024-01-{i%28+1:02d}_{i},{100.0 if i != 50 else 'Infinity'}" for i in range(120)])
    ).encode("utf-8")

    with pytest.raises(ValueError, match="non-finite \\(NaN or Inf\\)"):
        parse_and_preprocess_csv(inf_csv, time_column="date", target_column="energy_demand")

    # 3. Nulls (empty values) are preserved and dropped, allowing valid series to proceed
    null_csv = (
        "date,energy_demand\n" +
        "\n".join([f"2024-01-{i%28+1:02d}_{i},{100.0 + i if i != 10 else ''}" for i in range(120)])
    ).encode("utf-8")

    prep = parse_and_preprocess_csv(null_csv, time_column="date", target_column="energy_demand")
    # 1 row dropped, 119 rows remain
    assert prep.simulated_rows == 119
    assert prep.raw_target.dtype == np.float64

