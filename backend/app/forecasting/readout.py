"""Linear readout training and multi-horizon forecasting for reservoir features.

Trains a multi-output Ridge model on sampled connectome state representations.
Uses validation RMSE to select regularization parameter alpha, then retrains
on combined train+val and evaluates on held-out test data.
"""

from typing import Dict, List, Tuple, Any, Optional
import numpy as np
from sklearn.linear_model import Ridge

from app.forecasting.metrics import compute_metrics


class ReadoutResult:
    def __init__(
        self,
        best_alpha: float,
        test_metrics: Dict[str, float],
        test_predictions_raw: np.ndarray,
        test_actuals_raw: np.ndarray,
        future_forecast_raw: np.ndarray,
        residual_std: float,
        interval_bounds_raw: Tuple[np.ndarray, np.ndarray],
    ):
        self.best_alpha = best_alpha
        self.test_metrics = test_metrics
        self.test_predictions_raw = test_predictions_raw
        self.test_actuals_raw = test_actuals_raw
        self.future_forecast_raw = future_forecast_raw
        self.residual_std = residual_std
        self.interval_bounds_raw = interval_bounds_raw


def build_multi_horizon_targets(
    series: np.ndarray,
    horizon: int,
) -> Tuple[np.ndarray, np.ndarray]:
    """Constructs multi-horizon target matrix Y where Y[t] = [y[t+1], y[t+2], ..., y[t+H]].

    Returns:
        valid_indices: time indices t for which all t+1..t+H exist.
        targets: shape (len(valid_indices), horizon)
    """
    T = len(series)
    max_t = T - horizon
    if max_t <= 0:
        raise ValueError(f"Series length {T} is too short for forecast horizon {horizon}.")

    valid_indices = np.arange(max_t, dtype=int)
    targets = np.zeros((max_t, horizon), dtype=np.float32)
    for h in range(1, horizon + 1):
        targets[:, h - 1] = series[h : max_t + h]

    return valid_indices, targets


def train_and_evaluate_readout(
    features: np.ndarray,
    scaled_target: np.ndarray,
    target_mean: float,
    target_scale: float,
    train_slice: slice,
    val_slice: slice,
    test_slice: slice,
    horizon: int = 5,
    candidate_alphas: Optional[List[float]] = None,
) -> ReadoutResult:
    """Trains multi-output Ridge regression readout on reservoir features."""
    if candidate_alphas is None:
        candidate_alphas = [1e-4, 1e-3, 1e-2, 1e-1, 1.0, 10.0, 100.0]

    T = len(scaled_target)
    washout = min(25, max(5, int(0.05 * T)))

    # Construct targets
    valid_idx, Y_all = build_multi_horizon_targets(scaled_target, horizon)
    X_all = features[valid_idx]

    # Split targets and features according to chronological slices
    train_mask = (valid_idx >= train_slice.start + washout) & (valid_idx < train_slice.stop)
    val_mask = (valid_idx >= val_slice.start) & (valid_idx < val_slice.stop)
    test_mask = (valid_idx >= test_slice.start) & (valid_idx < test_slice.stop)

    X_train, Y_train = X_all[train_mask], Y_all[train_mask]
    X_val, Y_val = X_all[val_mask], Y_all[val_mask]
    X_test, Y_test = X_all[test_mask], Y_all[test_mask]

    if len(X_train) == 0 or len(X_val) == 0 or len(X_test) == 0:
        raise ValueError("Insufficient observations in train, validation, or test split for readout training.")

    # 1. Select best alpha on validation set
    best_alpha = candidate_alphas[0]
    best_val_rmse = float("inf")

    for alpha in candidate_alphas:
        model = Ridge(alpha=alpha, fit_intercept=True)
        model.fit(X_train, Y_train)
        pred_val = model.predict(X_val)
        val_rmse = float(np.sqrt(np.mean((Y_val - pred_val) ** 2)))
        if val_rmse < best_val_rmse:
            best_val_rmse = val_rmse
            best_alpha = alpha

    # 2. Retrain on combined Train + Validation
    X_train_val = np.vstack([X_train, X_val])
    Y_train_val = np.vstack([Y_train, Y_val])
    final_model = Ridge(alpha=best_alpha, fit_intercept=True)
    final_model.fit(X_train_val, Y_train_val)

    # 3. Calculate validation residual std on raw scale for approximate interval
    val_preds_scaled = final_model.predict(X_val)
    val_residuals_raw = (Y_val - val_preds_scaled) * target_scale
    residual_std = float(np.std(val_residuals_raw))
    if residual_std < 1e-6:
        residual_std = 1e-4

    # 4. Evaluate on Test set
    pred_test_scaled = final_model.predict(X_test)

    # Inverse transform to raw unscaled units
    pred_test_raw = (pred_test_scaled * target_scale) + target_mean
    actual_test_raw = (Y_test * target_scale) + target_mean

    test_metrics = compute_metrics(actual_test_raw, pred_test_raw)

    # 5. Future forecast from final observed state
    # Feature at final timestep T-1
    final_feature = features[-1:].reshape(1, -1)
    future_scaled = final_model.predict(final_feature)[0]
    future_raw = (future_scaled * target_scale) + target_mean

    # Approximate 95% residual interval bounds
    lower_bound = future_raw - 1.96 * residual_std
    upper_bound = future_raw + 1.96 * residual_std

    return ReadoutResult(
        best_alpha=best_alpha,
        test_metrics=test_metrics,
        test_predictions_raw=pred_test_raw,
        test_actuals_raw=actual_test_raw,
        future_forecast_raw=future_raw,
        residual_std=residual_std,
        interval_bounds_raw=(lower_bound, upper_bound),
    )
