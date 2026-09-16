"""Reservoir computing dynamics on the Drosophila connectome graph.

Implements the Echo State Network leaky tanh recurrent rate model:
x[t+1] = (1 - leak) * x[t] + leak * tanh(recurrent_gain * (W @ x[t]) + Win @ u[t])
"""

from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import scipy.sparse as sp


class ReservoirEngine:
    """Manages input projection, recurrent propagation, and state feature extraction."""

    def __init__(
        self,
        csr_matrix: sp.csr_matrix,
        input_indices: np.ndarray,
        readout_indices: np.ndarray,
        leak: float = 0.25,
        recurrent_gain: float = 0.95,
        input_gain: float = 0.50,
        seed: int = 42,
    ):
        self.W = csr_matrix
        self.num_neurons = csr_matrix.shape[0]
        self.input_indices = np.asarray(input_indices, dtype=np.int32)
        self.readout_indices = np.asarray(readout_indices, dtype=np.int32)
        self.leak = float(leak)
        self.recurrent_gain = float(recurrent_gain)
        self.input_gain = float(input_gain)
        self.seed = int(seed)

    def build_input_weights(self, num_features: int) -> sp.csr_matrix:
        """Constructs sparse input projection matrix Win of shape (num_neurons, num_features).

        Partitions sensory input neurons deterministically among the feature columns.
        Coefficients sampled from Uniform(-1, 1) * input_gain.
        """
        rng = np.random.default_rng(self.seed)
        num_inputs = len(self.input_indices)
        
        # Partition sensory neurons across features
        subgroup_size = max(1, num_inputs // num_features)
        
        rows: List[int] = []
        cols: List[int] = []
        vals: List[float] = []

        for f in range(num_features):
            start = f * subgroup_size
            end = num_inputs if f == num_features - 1 else (f + 1) * subgroup_size
            feature_sensory_indices = self.input_indices[start:end]
            
            # Uniform(-1, 1) * input_gain
            coeffs = rng.uniform(-1.0, 1.0, size=len(feature_sensory_indices)) * self.input_gain
            for neuron_idx, coeff in zip(feature_sensory_indices, coeffs):
                rows.append(int(neuron_idx))
                cols.append(f)
                vals.append(float(coeff))

        Win = sp.coo_matrix(
            (vals, (rows, cols)),
            shape=(self.num_neurons, num_features),
            dtype=np.float32,
        ).tocsr()
        return Win

    def run(
        self,
        inputs: np.ndarray,
        progress_callback: Optional[Any] = None,
        sample_viz_neurons: int = 64,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Propagates input sequence through the recurrent connectome.

        Args:
            inputs: Standardized array of shape (T, num_features).
            progress_callback: Optional callable(step, total_steps) for job reporting.
            sample_viz_neurons: Number of neurons to record for UI activity visualizer.

        Returns:
            Tuple of:
              - readout_features: shape (T, len(readout_indices)), float32
              - activity_viz: dictionary with temporal activity metrics for frontend
        """
        T, num_features = inputs.shape
        Win = self.build_input_weights(num_features)

        # Preallocate readout state array: (T, num_readouts)
        num_readouts = len(self.readout_indices)
        readout_features = np.zeros((T, num_readouts), dtype=np.float32)

        # Activity summary metrics for frontend
        # Subsample visualizer neurons from readout or central set
        viz_subset = self.readout_indices[: min(sample_viz_neurons, num_readouts)]
        viz_samples: List[List[float]] = []
        mean_abs_states: List[float] = []
        max_abs_states: List[float] = []

        # Current state vector x[t]
        x = np.zeros(self.num_neurons, dtype=np.float32)
        leak = self.leak
        one_minus_leak = 1.0 - leak
        rec_gain = self.recurrent_gain

        for t in range(T):
            u_t = inputs[t].astype(np.float32)  # shape (num_features,)
            
            # Recurrent term: W[post, pre] @ x flows presynaptic -> postsynaptic
            recurrent_input = rec_gain * self.W.dot(x)
            
            # Input sensory injection: Win @ u[t]
            sensory_input = Win.dot(u_t)

            # Combined total input
            total_drive = recurrent_input + sensory_input

            # Leaky tanh activation
            x = (one_minus_leak * x) + (leak * np.tanh(total_drive))

            # Check numerical stability
            if np.isnan(x[0]) or np.isinf(x[0]):
                raise FloatingPointError(
                    f"Numerical instability detected at timestep {t}: State contains NaN or Inf. "
                    "The current reservoir configuration became numerically unstable."
                )

            # Record readout slice
            readout_features[t] = x[self.readout_indices]

            # Periodic visualizer metrics downsampling (max ~100 points for UI)
            if T <= 100 or t % (max(1, T // 100)) == 0:
                abs_x = np.abs(x)
                mean_abs_states.append(float(np.mean(abs_x)))
                max_abs_states.append(float(np.max(abs_x)))
                viz_samples.append([float(v) for v in x[viz_subset]])

            # Report progress
            if progress_callback and (t % 25 == 0 or t == T - 1):
                progress_callback(t + 1, T)

        # Check for excessive saturation
        saturated_ratio = np.mean(np.abs(x) > 0.999)
        if saturated_ratio > 0.95:
            raise FloatingPointError(
                f"Reservoir saturated: {saturated_ratio:.1%} of neurons reached saturation (> 0.999). "
                "Adjust gain or leak for numerical stability."
            )

        activity_viz = {
            "timesteps": len(mean_abs_states),
            "mean_abs_activity": mean_abs_states,
            "max_abs_activity": max_abs_states,
            "sample_activity": viz_samples,
            "num_sampled_neurons": len(viz_subset),
        }

        return readout_features, activity_viz
