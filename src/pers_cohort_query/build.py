"""Functions to build genetically matched cohorts."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from .io import get_pc_columns

DEFAULT_N_PCS = 10
MIN_MAF = 0.05
# plink2 --indep-pairwise window size (variants), step size (variants), r^2
LD_PRUNE = ("50", "5", "0.2")


def run_plink2(*args: str) -> None:
    try:
        subprocess.run(["plink2", *args], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"plink2 failed:\n{e.stdout}\n{e.stderr}") from e


# TODO: revisit & revise this method later, especially if want to re-generate
# AoU PCs
def compute_pcs(
    vcf_path: str | Path,
    n_pcs: int = DEFAULT_N_PCS,
    *,
    id_col: str = "id",
) -> pd.DataFrame:
    """Simple computation of genetic PCs from a VCF with plink2."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        prefix = str(Path(tmp_dir) / "genotypes")
        run_plink2(
            "--vcf", str(vcf_path),
            "--snps-only", "just-acgt",
            "--max-alleles", "2",
            "--maf", str(MIN_MAF),
            "--set-all-var-ids", "@:#:$r:$a",
            "--make-pgen",
            "--out", prefix,
        )  # fmt: skip
        run_plink2("--pfile", prefix, "--indep-pairwise", *LD_PRUNE, "--out", prefix)
        run_plink2(
            "--pfile", prefix,
            "--extract", f"{prefix}.prune.in",
            "--pca", str(n_pcs),
            "--out", prefix,
        )  # fmt: skip

        pcs = pd.read_csv(f"{prefix}.eigenvec", sep="\t", dtype={"#IID": str})

    # plink2 writes "#IID PC1 .. PCN" for VCF input
    return pcs.rename(columns={"#IID": id_col})


def build_pc_cohorts(
    pcs: pd.DataFrame,
    k_neighbors: int = 100,
    *,
    id_col: str = "id",
    n_pcs: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Get each individual's `k_neighbors` nearest neighbors by Euclidean
    distance in genetic PC space.
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


def build_genosis_cohorts(
    vcf_path: str | Path,
    k_neighbors: int = 100,
    *,
    id_col: str = "id",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """TODO: to be implemented."""
    raise NotImplementedError("GenoSiS cohorts are not implemented yet.")
