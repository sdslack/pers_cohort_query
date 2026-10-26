"""Build personalized cohorts from extracted biobank data."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from .io import get_pc_columns


# TODO: revisit this to structue this part like aggregation step of GenoSiS,
# where getting PCs is equivalent to embedding GenoSiS step
def build_pc_cohorts(
    pcs: pd.DataFrame,
    k_neighbors: int = 100,
    *,
    id_col: str = "id",
    n_pcs: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Match each individual to their `k_neighbors` nearest neighbors by
    Euclidean distance in genetic PC space.

    Returns cohorts and distances DataFrames. Members are ordered from nearest
    to farthest.
    """
    if k_neighbors < 2:
        raise ValueError("`k_neighbors` must be at least 2.")
    n_indv = len(pcs)
    if k_neighbors >= n_indv:
        raise ValueError(
            f"`k_neighbors` ({k_neighbors}) must be less than the number of "
            f"individuals ({n_indv})."
        )

    pc_matrix = pcs[get_pc_columns(pcs, n_pcs=n_pcs)].to_numpy(dtype=float)
    ids = pcs[id_col].to_numpy()

    distances, indices = cKDTree(pc_matrix).query(pc_matrix, k=k_neighbors + 1)

    # Remove self if present, otherwise remove farthest neighbor
    is_self = indices == np.arange(n_indv)[:, None]
    is_self[~is_self.any(axis=1), -1] = True
    keep = ~is_self
    indices = indices[keep].reshape(n_indv, k_neighbors)
    distances = distances[keep].reshape(n_indv, k_neighbors)

    ranks = range(1, k_neighbors + 1)
    cohorts = pd.DataFrame(ids[indices], columns=[f"member_{i}" for i in ranks])
    cohorts.insert(0, id_col, ids)
    cohort_distances = pd.DataFrame(distances, columns=[f"dist_{i}" for i in ranks])
    cohort_distances.insert(0, id_col, ids)

    return cohorts, cohort_distances
