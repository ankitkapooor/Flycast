"""Scientific control models for the Drosophila connectome reservoir.

Preserves exact network topology and weight distribution while permuting
connection magnitudes to isolate whether biological wiring organization matters.
"""

import numpy as np
import scipy.sparse as sp


def build_weight_shuffled_matrix(
    csr: sp.csr_matrix,
    seed: int = 42,
) -> sp.csr_matrix:
    """Builds a weight-shuffled control matrix.

    Preserves:
      - identical directed graph topology (same non-zero locations)
      - identical number of neurons and connections
      - identical global weight distribution

    Permutes connection weights across existing edges, then reapplies
    incoming L1 normalization to preserve stability and comparability.
    """
    rng = np.random.default_rng(seed)
    
    # Copy CSR structure
    shuffled = csr.copy()
    
    # Randomly permute the non-zero data entries
    shuffled_data = shuffled.data.copy()
    rng.shuffle(shuffled_data)
    shuffled.data = shuffled_data

    # Re-normalize incoming weights (row normalization for W[post, pre])
    row_sums = np.array(shuffled.sum(axis=1)).flatten()
    row_sums[row_sums == 0] = 1.0
    diag_inv = sp.diags(1.0 / row_sums)
    normalized_shuffled = (diag_inv @ shuffled).tocsr()

    return normalized_shuffled
