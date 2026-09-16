"""Master forecasting pipeline orchestrating preprocessing, reservoir simulation, baselines, and control."""

import time
import hashlib
from typing import Dict, List, Optional, Any, Callable
import numpy as np
import polars as pl

from app.brain.loader import BrainState
from app.brain.reservoir import ReservoirEngine
from app.brain.controls import build_weight_shuffled_matrix
from app.forecasting.preprocessing import PreprocessedData, parse_and_preprocess_csv
from app.forecasting.readout import train_and_evaluate_readout, ReadoutResult
from app.forecasting.baselines import (
    evaluate_persistence_baseline,
    evaluate_autoregressive_ridge_baseline,
)
from app.forecasting.metrics import determine_winner_and_copy


class PipelineResult:
    def __init__(
        self,
        experiment_id: str,
        result_dict: Dict[str, Any],
        predictions_df: pl.DataFrame,
        chart_data: Dict[str, Any],
    ):
        self.experiment_id = experiment_id
        self.result_dict = result_dict
        self.predictions_df = predictions_df
        self.chart_data = chart_data


def run_experiment_pipeline(
    experiment_id: str,
    csv_bytes: bytes,
    brain: BrainState,
    time_column: Optional[str] = None,
    target_column: Optional[str] = None,
    feature_columns: Optional[List[str]] = None,
    forecast_horizon: int = 5,
    run_control: bool = False,
    leak: float = 0.25,
    recurrent_gain: float = 0.95,
    input_gain: float = 0.50,
    seed: int = 42,
    progress_cb: Optional[Callable[[str, int, str], None]] = None,
) -> PipelineResult:
    """Executes the full FlyCast experiment pipeline with timing and progress updates."""
    total_start = time.perf_counter()
    timings: Dict[str, float] = {}

    def update(stage: str, progress: int, msg: str):
        if progress_cb:
            progress_cb(stage, progress, msg)

    # 1. Preprocessing
    update("preprocessing", 10, "Parsing and validating time-series data...")
    t0 = time.perf_counter()
    prep: PreprocessedData = parse_and_preprocess_csv(
        csv_bytes=csv_bytes,
        time_column=time_column,
        target_column=target_column,
        feature_columns=feature_columns,
    )
    timings["preprocessing_seconds"] = round(time.perf_counter() - t0, 3)

    # Compute dataset hash
    dataset_hash = hashlib.sha256(csv_bytes).hexdigest()

    # 2. Reservoir simulation
    update("running_brain", 25, f"Propagating signal through {brain.num_neurons:,} neurons...")
    t0 = time.perf_counter()

    engine = ReservoirEngine(
        csr_matrix=brain.csr_matrix,
        input_indices=brain.input_indices,
        readout_indices=brain.readout_indices,
        leak=leak,
        recurrent_gain=recurrent_gain,
        input_gain=input_gain,
        seed=seed,
    )

    def res_progress(step: int, total: int):
        pct = 25 + int(35 * (step / total))
        update("running_brain", pct, f"Running recurrent step {step} / {total} in CNS")

    readout_features, activity_viz = engine.run(
        inputs=prep.scaled_inputs,
        progress_callback=res_progress,
    )
    timings["reservoir_seconds"] = round(time.perf_counter() - t0, 3)

    # 3. Readout training & evaluation
    update("training_readout", 65, f"Training Ridge readout across {len(brain.readout_indices):,} virtual electrodes...")
    t0 = time.perf_counter()
    readout_res: ReadoutResult = train_and_evaluate_readout(
        features=readout_features,
        scaled_target=prep.scaled_target,
        target_mean=prep.scaler_mean,
        target_scale=prep.scaler_scale,
        train_slice=prep.train_slice,
        val_slice=prep.val_slice,
        test_slice=prep.test_slice,
        horizon=forecast_horizon,
    )
    timings["readout_seconds"] = round(time.perf_counter() - t0, 3)

    # 4. Baselines
    update("running_baselines", 75, "Computing Persistence and Autoregressive baselines...")
    t0 = time.perf_counter()
    pers_res = evaluate_persistence_baseline(
        raw_target=prep.raw_target,
        train_slice=prep.train_slice,
        val_slice=prep.val_slice,
        test_slice=prep.test_slice,
        horizon=forecast_horizon,
    )
    ar_res = evaluate_autoregressive_ridge_baseline(
        scaled_target=prep.scaled_target,
        raw_target=prep.raw_target,
        target_mean=prep.scaler_mean,
        target_scale=prep.scaler_scale,
        train_slice=prep.train_slice,
        val_slice=prep.val_slice,
        test_slice=prep.test_slice,
        horizon=forecast_horizon,
    )
    timings["baseline_seconds"] = round(time.perf_counter() - t0, 3)

    # 5. Scientific control (optional)
    control_result_dict = None
    if run_control:
        update("running_control", 85, "Executing weight-shuffled connectome control...")
        t0 = time.perf_counter()
        shuffled_W = build_weight_shuffled_matrix(brain.csr_matrix, seed=seed)
        ctrl_engine = ReservoirEngine(
            csr_matrix=shuffled_W,
            input_indices=brain.input_indices,
            readout_indices=brain.readout_indices,
            leak=leak,
            recurrent_gain=recurrent_gain,
            input_gain=input_gain,
            seed=seed,
        )
        ctrl_features, _ = ctrl_engine.run(inputs=prep.scaled_inputs)
        ctrl_readout = train_and_evaluate_readout(
            features=ctrl_features,
            scaled_target=prep.scaled_target,
            target_mean=prep.scaler_mean,
            target_scale=prep.scaler_scale,
            train_slice=prep.train_slice,
            val_slice=prep.val_slice,
            test_slice=prep.test_slice,
            horizon=forecast_horizon,
        )
        timings["control_seconds"] = round(time.perf_counter() - t0, 3)
        control_result_dict = {
            "type": "weight_shuffled",
            "metrics": ctrl_readout.test_metrics,
            "future_forecast": [round(float(v), 4) for v in ctrl_readout.future_forecast_raw],
        }

    # 6. Finalize metrics & winner copy
    update("finalizing", 95, "Finalizing metrics and compiling charts...")
    editorial = determine_winner_and_copy(
        fly_metrics=readout_res.test_metrics,
        persistence_metrics=pers_res["metrics"],
        ar_metrics=ar_res["metrics"],
        control_metrics=control_result_dict["metrics"] if control_result_dict else None,
    )

    timings["total_seconds"] = round(time.perf_counter() - total_start, 3)

    # 7. Construct Chart data
    # Select last N history points for chart clarity (up to 150 points)
    n_history = min(120, prep.test_slice.start)
    hist_start = max(0, prep.test_slice.start - n_history)
    
    chart_history = []
    for idx in range(hist_start, prep.test_slice.start):
        chart_history.append({
            "time": str(prep.times[idx]),
            "step": int(idx),
            "actual": round(float(prep.raw_target[idx]), 4),
            "segment": "history",
        })

    # Test set chart points (use h=1 prediction for sequential alignment)
    test_len = len(readout_res.test_actuals_raw)
    chart_test = []
    test_start_t = prep.test_slice.start
    
    csv_rows = []

    for i in range(test_len):
        t_idx = test_start_t + i
        time_str = str(prep.times[t_idx]) if t_idx < len(prep.times) else f"step_{t_idx}"
        act_val = round(float(readout_res.test_actuals_raw[i, 0]), 4)
        fly_val = round(float(readout_res.test_predictions_raw[i, 0]), 4)
        pers_val = round(float(pers_res["predictions_test"][i, 0]), 4)
        ar_val = round(float(ar_res["predictions_test"][i, 0]), 4)

        point = {
            "time": time_str,
            "step": int(t_idx),
            "actual": act_val,
            "flycast": fly_val,
            "persistence": pers_val,
            "autoregressive": ar_val,
            "segment": "test",
        }
        chart_test.append(point)

        csv_rows.append({
            "time": time_str,
            "step": int(t_idx),
            "segment": "test",
            "actual": act_val,
            "flycast": fly_val,
            "persistence": pers_val,
            "autoregressive": ar_val,
            "lower_95": None,
            "upper_95": None,
        })

    # Future forecast points
    chart_future = []
    last_t = prep.simulated_rows - 1
    lower_b, upper_b = readout_res.interval_bounds_raw

    for h in range(forecast_horizon):
        step_h = last_t + h + 1
        time_h = f"+{h+1}h"
        fly_f = round(float(readout_res.future_forecast_raw[h]), 4)
        pers_f = round(float(pers_res["future_forecast"][h]), 4)
        ar_f = round(float(ar_res["future_forecast"][h]), 4)
        lb_val = round(float(lower_b[h]), 4)
        ub_val = round(float(upper_b[h]), 4)

        point = {
            "time": time_h,
            "step": int(step_h),
            "actual": None,
            "flycast": fly_f,
            "persistence": pers_f,
            "autoregressive": ar_f,
            "lower_95": lb_val,
            "upper_95": ub_val,
            "segment": "future",
        }
        chart_future.append(point)

        csv_rows.append({
            "time": time_h,
            "step": int(step_h),
            "segment": "future",
            "actual": None,
            "flycast": fly_f,
            "persistence": pers_f,
            "autoregressive": ar_f,
            "lower_95": lb_val,
            "upper_95": ub_val,
        })

    predictions_df = pl.DataFrame(csv_rows)

    # Assemble comprehensive result.json according to Section 34
    result_dict = {
        "experiment_id": experiment_id,
        "dataset": {
            "rows_original": prep.raw_rows,
            "rows_simulated": prep.simulated_rows,
            "target": prep.target_col,
            "time_column": prep.time_col,
            "features": prep.feature_cols,
            "resampling_note": prep.resampling_note,
        },
        "forecast": {
            "horizon": forecast_horizon,
            "values": [round(float(v), 4) for v in readout_res.future_forecast_raw],
            "interval_lower": [round(float(v), 4) for v in lower_b],
            "interval_upper": [round(float(v), 4) for v in upper_b],
            "residual_std": round(readout_res.residual_std, 4),
        },
        "fly": readout_res.test_metrics,
        "baselines": {
            "persistence": pers_res["metrics"],
            "autoregressive_ridge": {
                **ar_res["metrics"],
                "best_lag": ar_res["best_lag"],
                "best_alpha": ar_res["best_alpha"],
            },
        },
        "control": control_result_dict,
        "winner": editorial["winner"],
        "editorial": editorial,
        "reservoir": {
            "neurons": brain.num_neurons,
            "edges": brain.num_edges,
            "input_neurons": len(brain.input_indices),
            "readout_neurons": len(brain.readout_indices),
            "leak": leak,
            "recurrent_gain": recurrent_gain,
            "input_gain": input_gain,
            "ridge_alpha": readout_res.best_alpha,
            "washout": min(25, max(5, int(0.05 * prep.simulated_rows))),
        },
        "reproducibility": {
            "seed": seed,
            "brain_manifest_hash": brain.manifest.manifest_hash or "fixture-or-unhashed",
            "dataset_sha256": dataset_hash,
            "connectome_version": brain.manifest.dataset,
            "train_size": prep.train_slice.stop - prep.train_slice.start,
            "val_size": prep.val_slice.stop - prep.val_slice.start,
            "test_size": prep.test_slice.stop - prep.test_slice.start,
        },
        "timings": timings,
    }

    chart_data = {
        "history": chart_history,
        "test": chart_test,
        "future": chart_future,
        "activity_viz": activity_viz,
    }

    return PipelineResult(
        experiment_id=experiment_id,
        result_dict=result_dict,
        predictions_df=predictions_df,
        chart_data=chart_data,
    )
