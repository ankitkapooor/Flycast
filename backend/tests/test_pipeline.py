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
