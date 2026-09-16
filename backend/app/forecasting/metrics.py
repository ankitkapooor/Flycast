"""Forecasting evaluation metrics and editorial comparison copy generator."""

from typing import Dict, Any, Optional
import numpy as np


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Computes standard evaluation metrics: MAE, RMSE, R2, sMAPE."""
    y_true = np.asarray(y_true, dtype=np.float64)
    y_pred = np.asarray(y_pred, dtype=np.float64)

    # Flatten for global score calculation
    y_t = y_true.ravel()
    y_p = y_pred.ravel()

    mae = float(np.mean(np.abs(y_t - y_p)))
    rmse = float(np.sqrt(np.mean((y_t - y_p) ** 2)))

    # R-squared
    ss_res = np.sum((y_t - y_p) ** 2)
    ss_tot = np.sum((y_t - np.mean(y_t)) ** 2)
    r2 = float(1.0 - (ss_res / ss_tot)) if ss_tot > 1e-9 else 0.0

    # Symmetric MAPE (stable with values near zero)
    denominator = np.abs(y_t) + np.abs(y_p) + 1e-8
    smape = float(np.mean(200.0 * np.abs(y_t - y_p) / denominator))

    return {
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "r2": round(r2, 4),
        "smape": round(smape, 2),
    }


def determine_winner_and_copy(
    fly_metrics: Dict[str, float],
    persistence_metrics: Dict[str, float],
    ar_metrics: Dict[str, float],
    control_metrics: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Evaluates the primary metric (RMSE) across all models honestly.

    Generates rule-based editorial copy without exaggeration or LLM dependency.
    """
    fly_rmse = fly_metrics["rmse"]
    pers_rmse = persistence_metrics["rmse"]
    ar_rmse = ar_metrics["rmse"]

    candidates = {
        "fly": fly_rmse,
        "persistence": pers_rmse,
        "autoregressive": ar_rmse,
    }
    if control_metrics is not None:
        candidates["control"] = control_metrics["rmse"]

    # Winner has minimum RMSE
    winner = min(candidates, key=candidates.get)
    best_rmse = candidates[winner]

    # Check for near-tie (within 1.5% of best RMSE)
    fly_ratio = (fly_rmse - best_rmse) / max(best_rmse, 1e-6)

    if winner == "fly":
        headline = "THE FLY HAS SPOKEN."
        summary = (
            "On this dataset, the connectome-derived reservoir produced the lowest "
            f"held-out RMSE ({fly_rmse:.4f}), outperforming both persistence ({pers_rmse:.4f}) "
            f"and autoregressive Ridge ({ar_rmse:.4f})."
        )
        verdict = "The fly won."
    elif fly_ratio <= 0.015:
        headline = "A NEAR TIE."
        summary = (
            f"The connectome performed similarly to the strongest baseline ({winner.replace('_', ' ')}). "
            f"FlyCast RMSE ({fly_rmse:.4f}) was within 1.5% of the winning score ({best_rmse:.4f})."
        )
        verdict = "The fly tied."
    else:
        headline = "THE FLY HAS SPOKEN. It should have kept quiet."
        best_name = "Autoregressive Ridge" if winner == "autoregressive" else winner.capitalize()
        summary = (
            f"On this dataset, a simpler forecasting method performed better. {best_name} "
            f"achieved RMSE {best_rmse:.4f}, while FlyCast scored {fly_rmse:.4f}."
        )
        verdict = "The fly lost."

    control_copy = None
    if control_metrics is not None:
        ctrl_rmse = control_metrics["rmse"]
        delta = ctrl_rmse - fly_rmse
        if delta > 0:
            control_copy = (
                f"Shuffling the synaptic weights increased RMSE by {delta:.4f} "
                f"(Real: {fly_rmse:.4f} vs Shuffled: {ctrl_rmse:.4f}), indicating that the observed "
                "synaptic weight structure provided a performance benefit on this configuration."
            )
        else:
            control_copy = (
                f"The weight-shuffled connectome achieved RMSE {ctrl_rmse:.4f} compared to "
                f"{fly_rmse:.4f} for the real connectome (Δ {delta:.4f}). On this series, "
                "scrambling the synaptic weights did not degrade forecast fidelity."
            )

    return {
        "winner": winner,
        "verdict": verdict,
        "headline": headline,
        "summary": summary,
        "control_summary": control_copy,
    }
