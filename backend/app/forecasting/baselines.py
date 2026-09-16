"""Baseline forecasting models: Persistence and Autoregressive Ridge.

Provides honest, standard benchmarks to evaluate whether the biological connectome
provides genuine predictive value over simple time-series methods.
"""

from typing import Dict, List, Tuple, Any, Optional
import numpy as np
from sklearn.linear_model import Ridge

from app.forecasting.metrics import compute_metrics
from app.forecasting.readout import build_multi_horizon_targets


def evaluate_persistence_baseline(
    raw_target: np.ndarray,
    train_slice: slice,
    val_slice: slice,
    test_slice: slice,
    horizon: int = 5,
) -> Dict[str, Any]:
    """Baseline A: Persistence (Last-Value).

    For every timestep t, forecasts y[t+h] = y[t] for all h in 1..H.
    """
    valid_idx, Y_all = build_multi_horizon_targets(raw_target, horizon)
    test_mask = (valid_idx >= test_slice.start) & (valid_idx < test_slice.stop)

    test_indices = valid_idx[test_mask]
    Y_test = Y_all[test_mask]

    # Persistence prediction: repeat raw_target[t] across all horizon columns
    pred_test = np.tile(raw_target[test_indices, None], (1, horizon))
    metrics = compute_metrics(Y_test, pred_test)

    # Future forecast from final observed value
    future_forecast = np.full(horizon, raw_target[-1], dtype=np.float64)

    return {
        "metrics": metrics,
        "future_forecast": future_forecast.tolist(),
        "predictions_test": pred_test,
        "actuals_test": Y_test,
    }


def build_lagged_features(
    series: np.ndarray,
    lag: int,
    horizon: int,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Constructs lagged input matrix X and multi-horizon target matrix Y.

    For each timestep t in [lag - 1, T - horizon - 1]:
      X[t] = [series[t], series[t-1], ..., series[t - lag + 1]]
      Y[t] = [series[t+1], ..., series[t+horizon]]
    """
    T = len(series)
    start_t = lag - 1
    end_t = T - horizon
    if end_t <= start_t:
        raise ValueError(f"Series length {T} insufficient for lag {lag} and horizon {horizon}.")

    valid_t = np.arange(start_t, end_t, dtype=int)
    num_samples = len(valid_t)

    X = np.zeros((num_samples, lag), dtype=np.float32)
    for i, t in enumerate(valid_t):
        X[i] = series[t - lag + 1 : t + 1][::-1]  # most recent first

    Y = np.zeros((num_samples, horizon), dtype=np.float32)
    for h in range(1, horizon + 1):
        Y[:, h - 1] = series[valid_t + h]

    return valid_t, X, Y


def evaluate_autoregressive_ridge_baseline(
    scaled_target: np.ndarray,
    raw_target: np.ndarray,
    target_mean: float,
    target_scale: float,
    train_slice: slice,
    val_slice: slice,
    test_slice: slice,
    horizon: int = 5,
    candidate_lags: Optional[List[int]] = None,
    candidate_alphas: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """Baseline B: Autoregressive Ridge Regression.

    Selects optimal lag and Ridge alpha on validation set,
    retrains on train + val, and evaluates on held-out test data.
    """
    if candidate_alphas is None:
        candidate_alphas = [1e-3, 1e-2, 1e-1, 1.0, 10.0, 100.0]

    train_len = train_slice.stop - train_slice.start
    if candidate_lags is None:
        raw_lags = [10, 20, 40]
        # Ensure lag fits well within training data
        candidate_lags = [lg for lg in raw_lags if lg < train_len // 3]
        if not candidate_lags:
            candidate_lags = [max(2, min(5, train_len // 4))]

    best_lag = candidate_lags[0]
    best_alpha = candidate_alphas[0]
    best_val_rmse = float("inf")

    # Hyperparameter selection over (lag, alpha) on validation set
    for lag in candidate_lags:
        valid_t, X_all, Y_all = build_lagged_features(scaled_target, lag, horizon)
        train_mask = (valid_t >= train_slice.start) & (valid_t < train_slice.stop)
        val_mask = (valid_t >= val_slice.start) & (valid_t < val_slice.stop)

        X_tr, Y_tr = X_all[train_mask], Y_all[train_mask]
        X_v, Y_v = X_all[val_mask], Y_all[val_mask]

        if len(X_tr) == 0 or len(X_v) == 0:
            continue

        for alpha in candidate_alphas:
            model = Ridge(alpha=alpha, fit_intercept=True)
            model.fit(X_tr, Y_tr)
            pred_v = model.predict(X_v)
            val_rmse = float(np.sqrt(np.mean((Y_v - pred_v) ** 2)))
            if val_rmse < best_val_rmse:
                best_val_rmse = val_rmse
                best_lag = lag
                best_alpha = alpha

    # Final fit with best (lag, alpha) on Train + Validation
    valid_t, X_all, Y_all = build_lagged_features(scaled_target, best_lag, horizon)
    train_mask = (valid_t >= train_slice.start) & (valid_t < train_slice.stop)
    val_mask = (valid_t >= val_slice.start) & (valid_t < val_slice.stop)
    test_mask = (valid_t >= test_slice.start) & (valid_t < test_slice.stop)

    X_tr_val = np.vstack([X_all[train_mask], X_all[val_mask]])
    Y_tr_val = np.vstack([Y_all[train_mask], Y_all[val_mask]])

    model = Ridge(alpha=best_alpha, fit_intercept=True)
    model.fit(X_tr_val, Y_tr_val)

    # Evaluate on Test
    X_test = X_all[test_mask]
    Y_test_scaled = Y_all[test_mask]
    pred_test_scaled = model.predict(X_test)

    # Inverse transform to unscaled units
    pred_test_raw = (pred_test_scaled * target_scale) + target_mean
    actual_test_raw = (Y_test_scaled * target_scale) + target_mean

    metrics = compute_metrics(actual_test_raw, pred_test_raw)

    # Future forecast
    latest_lags_scaled = scaled_target[-best_lag:][::-1].reshape(1, -1)
    future_scaled = model.predict(latest_lags_scaled)[0]
    future_raw = (future_scaled * target_scale) + target_mean

    return {
        "metrics": metrics,
        "best_lag": best_lag,
        "best_alpha": best_alpha,
        "future_forecast": future_raw.tolist(),
        "predictions_test": pred_test_raw,
        "actuals_test": actual_test_raw,
    }
