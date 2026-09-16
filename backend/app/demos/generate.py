"""Generation and cataloging of built-in demo time-series datasets."""

from pathlib import Path
from typing import Dict, List, Any
import numpy as np
import polars as pl


def generate_lorenz(num_steps: int = 600, dt: float = 0.02, seed: int = 42) -> pl.DataFrame:
    """Generates chaotic Lorenz-63 system trajectory (x-coordinate as target)."""
    sigma, rho, beta = 10.0, 28.0, 8.0 / 3.0
    x, y, z = 1.0, 1.0, 1.0

    xs, ys, zs = [], [], []
    for _ in range(num_steps + 200):  # discard initial transient
        dx = sigma * (y - x) * dt
        dy = (x * (rho - z) - y) * dt
        dz = (x * y - beta * z) * dt
        x += dx
        y += dy
        z += dz
        xs.append(x)
        ys.append(y)
        zs.append(z)

    # Discard transient
    xs = xs[200:]
    ys = ys[200:]
    zs = zs[200:]

    timestamps = [f"t_{i:04d}" for i in range(num_steps)]
    return pl.DataFrame({
        "timestamp": timestamps,
        "x_chaotic": [round(float(v), 4) for v in xs],
        "y_state": [round(float(v), 4) for v in ys],
        "z_state": [round(float(v), 4) for v in zs],
    })


def generate_composite_seasonal(num_steps: int = 600, seed: int = 42) -> pl.DataFrame:
    """Generates composite multi-frequency seasonal series with trend and noise."""
    rng = np.random.default_rng(seed)
    t = np.arange(num_steps)

    # Fast daily-like cycle (period 24)
    fast_cycle = 3.5 * np.sin(2 * np.pi * t / 24.0) + 1.2 * np.cos(4 * np.pi * t / 24.0)
    # Slow weekly-like cycle (period 168)
    slow_cycle = 5.0 * np.sin(2 * np.pi * t / 168.0)
    # Drift
    trend = 0.02 * t
    # Noise
    noise = rng.normal(0, 0.4, size=num_steps)

    signal = 25.0 + fast_cycle + slow_cycle + trend + noise
    timestamps = [f"2026-01-01 {i % 24:02d}:00" if i < 24 else f"2026-01-{(i//24)+1:02d} {i%24:02d}:00" for i in range(num_steps)]

    return pl.DataFrame({
        "timestamp": timestamps,
        "seasonal_signal": [round(float(v), 4) for v in signal],
        "fast_component": [round(float(v), 4) for v in fast_cycle],
        "slow_component": [round(float(v), 4) for v in slow_cycle],
    })


def generate_coupled_oscillator(num_steps: int = 600, dt: float = 0.05, seed: int = 42) -> pl.DataFrame:
    """Generates nonlinear van der Pol / Duffing oscillator dynamics."""
    mu = 1.2
    x, v = 0.1, 0.0
    xs, vs = [], []

    for _ in range(num_steps + 100):
        # Van der Pol: d2x/dt2 - mu*(1 - x^2)*dx/dt + x = 0
        dv = (mu * (1.0 - x**2) * v - x) * dt
        dx = v * dt
        v += dv
        x += dx
        xs.append(x)
        vs.append(v)

    xs = xs[100:]
    vs = vs[100:]
    timestamps = [f"step_{i:04d}" for i in range(num_steps)]

    return pl.DataFrame({
        "timestamp": timestamps,
        "displacement": [round(float(v), 4) for v in xs],
        "velocity": [round(float(v), 4) for v in vs],
    })


DEMO_CATALOG: Dict[str, Dict[str, Any]] = {
    "lorenz": {
        "id": "lorenz",
        "name": "Chaotic Lorenz System",
        "description": "A deterministic chaotic system whose future becomes progressively harder to predict.",
        "time_column": "timestamp",
        "target_column": "x_chaotic",
        "generator": generate_lorenz,
    },
    "seasonal": {
        "id": "seasonal",
        "name": "Seasonal Signal",
        "description": "Multiple compounding seasonal cycles with linear drift and stochastic noise.",
        "time_column": "timestamp",
        "target_column": "seasonal_signal",
        "generator": generate_composite_seasonal,
    },
    "oscillator": {
        "id": "oscillator",
        "name": "Oscillator",
        "description": "Nonlinear oscillatory dynamics exhibiting frequency modulation and limit cycles.",
        "time_column": "timestamp",
        "target_column": "displacement",
        "generator": generate_coupled_oscillator,
    },
}


def ensure_demo_files(output_dir: Path) -> Dict[str, Path]:
    """Generates demo CSV files into output_dir if not present."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for demo_id, meta in DEMO_CATALOG.items():
        csv_path = output_dir / f"{demo_id}.csv"
        if not csv_path.exists():
            df = meta["generator"]()
            df.write_csv(csv_path)
        paths[demo_id] = csv_path
    return paths

