"""Dataset validation, parsing, downsampling, and chronological preprocessing.

Ensures zero data leakage: scalers are strictly fitted on training observations only.
"""

import io
import re
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import polars as pl
from sklearn.preprocessing import StandardScaler


class PreprocessedData:
    def __init__(
        self,
        raw_rows: int,
        simulated_rows: int,
        time_col: str,
        target_col: str,
        feature_cols: List[str],
        times: np.ndarray,
        raw_target: np.ndarray,
        scaled_inputs: np.ndarray,
        scaled_target: np.ndarray,
        scaler_mean: float,
        scaler_scale: float,
        train_slice: slice,
        val_slice: slice,
        test_slice: slice,
        resampling_note: Optional[str] = None,
    ):
        self.raw_rows = raw_rows
        self.simulated_rows = simulated_rows
        self.time_col = time_col
        self.target_col = target_col
        self.feature_cols = feature_cols
        self.times = times
        self.raw_target = raw_target
        self.scaled_inputs = scaled_inputs
        self.scaled_target = scaled_target
        self.scaler_mean = scaler_mean
        self.scaler_scale = scaler_scale
        self.train_slice = train_slice
        self.val_slice = val_slice
        self.test_slice = test_slice
        self.resampling_note = resampling_note


def detect_delimiter(sample_text: str) -> str:
    """Infers CSV delimiter (comma, tab, semicolon)."""
    first_lines = sample_text.splitlines()[:5]
    if not first_lines:
        return ","
    header = first_lines[0]
    counts = {
        ",": header.count(","),
        "\t": header.count("\t"),
        ";": header.count(";"),
    }
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else ","


def parse_and_preprocess_csv(
    csv_bytes: bytes,
    time_column: Optional[str] = None,
    target_column: Optional[str] = None,
    feature_columns: Optional[List[str]] = None,
    max_simulation_steps: int = 1000,
    min_required_rows: int = 100,
) -> PreprocessedData:
    """Parses, validates, sorts, scales, and splits input CSV data."""
    text_sample = csv_bytes[:4096].decode("utf-8", errors="ignore")
    delimiter = detect_delimiter(text_sample)

    try:
        df = pl.read_csv(io.BytesIO(csv_bytes), separator=delimiter, infer_schema_length=1000)
    except Exception as e:
        raise ValueError(f"Could not parse CSV file: {str(e)}")

    raw_rows = len(df)
    if raw_rows < min_required_rows:
        raise ValueError(
            f"The fly needs more history. Upload at least {min_required_rows} usable observations. (Found {raw_rows})"
        )

    # 1. Identify or validate time column
    cols = df.columns
    if not time_column or time_column not in cols:
        time_candidates = [c for c in cols if any(k in c.lower() for k in ["time", "date", "timestamp", "year", "epoch", "step"])]
        time_col = time_candidates[0] if time_candidates else cols[0]
    else:
        time_col = time_column

    # 2. Identify or validate target column
    numeric_cols = [
        c for c in cols
        if c != time_col and df[c].dtype.is_numeric()
    ]
    if not numeric_cols:
        raise ValueError("I found the timestamps, but nothing numeric to predict.")

    if not target_column or target_column not in numeric_cols:
        # Default to first numeric column or one with 'target', 'close', 'value', 'price'
        target_candidates = [c for c in numeric_cols if any(k in c.lower() for k in ["target", "close", "value", "price", "y", "signal"])]
        target_col = target_candidates[0] if target_candidates else numeric_cols[0]
    else:
        target_col = target_column

    # Optional feature columns (up to 5 numeric columns)
    selected_features: List[str] = [target_col]
    if feature_columns:
        for f in feature_columns:
            if f in numeric_cols and f != target_col and f not in selected_features:
                selected_features.append(f)
                if len(selected_features) >= 5:
                    break

    # 3. Clean and sort chronologically
    df_clean = df.select([time_col] + selected_features).drop_nulls()

    # Sort by time column
    try:
        df_clean = df_clean.sort(time_col)
    except Exception:
        # If time column is mixed string, sort as string
        df_clean = df_clean.sort(pl.col(time_col).cast(pl.String))

    # Drop duplicate timestamps
    df_clean = df_clean.unique(subset=[time_col], keep="first", maintain_order=True)

    clean_rows = len(df_clean)
    if clean_rows < min_required_rows:
        raise ValueError(
            f"After removing invalid/null/duplicate rows, only {clean_rows} observations remained. "
            f"At least {min_required_rows} are required."
        )

    # 4. Check for constant/flat series
    target_series = df_clean[target_col].to_numpy()
    std_val = float(np.std(target_series))
    if std_val < 1e-6:
        raise ValueError("This signal barely changes, so forecasting it would not be a meaningful reservoir experiment.")

    # 5. Chronological downsampling if rows > max_simulation_steps
    resampling_note = None
    if clean_rows > max_simulation_steps:
        # Uniform chronological stride
        step_indices = np.linspace(0, clean_rows - 1, max_simulation_steps, dtype=int)
        df_clean = df_clean[step_indices]
        resampling_note = (
            f"Your dataset contained {clean_rows:,} observations. It was chronologically resampled "
            f"to {max_simulation_steps:,} timesteps for this experiment."
        )

    simulated_rows = len(df_clean)
    times = df_clean[time_col].to_numpy()
    raw_target = df_clean[target_col].to_numpy().astype(np.float64)

    # 6. Chronological split (70% Train, 15% Validation, 15% Test)
    n_train = int(simulated_rows * 0.70)
    n_val = int(simulated_rows * 0.15)
    n_test = simulated_rows - n_train - n_val

    train_slice = slice(0, n_train)
    val_slice = slice(n_train, n_train + n_val)
    test_slice = slice(n_train + n_val, simulated_rows)

    # 7. Scaler strictly fitted on Train!
    # Assemble input matrix (simulated_rows, num_features)
    inputs_raw = np.column_stack([df_clean[col].to_numpy().astype(np.float64) for col in selected_features])
    
    input_scaler = StandardScaler()
    input_scaler.fit(inputs_raw[train_slice])
    scaled_inputs = input_scaler.transform(inputs_raw).astype(np.float32)

    # Scaled target is the first column
    scaled_target = scaled_inputs[:, 0]
    target_mean = float(input_scaler.mean_[0])
    target_scale = float(input_scaler.scale_[0]) if input_scaler.scale_[0] > 1e-9 else 1.0

    return PreprocessedData(
        raw_rows=raw_rows,
        simulated_rows=simulated_rows,
        time_col=time_col,
        target_col=target_col,
        feature_cols=selected_features,
        times=times,
        raw_target=raw_target,
        scaled_inputs=scaled_inputs,
        scaled_target=scaled_target,
        scaler_mean=target_mean,
        scaler_scale=target_scale,
        train_slice=train_slice,
        val_slice=val_slice,
        test_slice=test_slice,
        resampling_note=resampling_note,
    )
