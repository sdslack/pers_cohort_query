"""Make small simulated test data in tests/data/input/.

Simulates 100 individuals, then keeps the first `N_SMALL` cohorts and lab
values and PCs for those individuals and their cohort members.
"""

from pathlib import Path
from typing import cast

import numpy as np
import pandas as pd

from simulate_data import (
    SEED,
    make_ids,
    make_lab_values,
    make_pcs,
    make_pers_cohorts,
)

N_SMALL = 5


def select_subset_ids(cohorts: pd.DataFrame, n: int, id_col: str = "id") -> list[str]:
    return cohorts[id_col].head(n).tolist()


def get_member_ids(cohorts: pd.DataFrame, id_col: str = "id") -> list[str]:
    """
    Return unique cohort member IDs excluding primary IDs in `id_col`.
    """
    member_columns = [column for column in cohorts.columns if column != id_col]
    members = cohorts[member_columns].to_numpy().ravel()
    return pd.unique(members[pd.notna(members)]).tolist()


def write_small_data(
    cohorts: pd.DataFrame,
    lab_values: pd.DataFrame,
    pcs: pd.DataFrame,
    subset_ids: list[str],
    output_dir: Path,
    id_col: str = "id",
) -> None:
    """
    Write a subset of cohort, lab values, and PCs data for testing.

    Includes cohort rows for `subset_ids`, and lab values and PCs for those IDs
    as well as their cohort members.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    cohorts_small = cast(pd.DataFrame, cohorts.loc[cohorts[id_col].isin(subset_ids)])
    small_ids = set(subset_ids) | set(get_member_ids(cohorts_small, id_col))
    lab_values_small = lab_values.loc[lab_values[id_col].isin(small_ids)]
    pcs_small = pcs.loc[pcs[id_col].isin(small_ids)]
    thresholds_small = pd.DataFrame({"low": [70.0], "high": [130.0]})

    cohorts_small.to_csv(output_dir / "cohorts_small.tsv", sep="\t", index=False)
    lab_values_small.to_csv(output_dir / "lab_values_small.tsv", sep="\t", index=False)
    pcs_small.to_csv(output_dir / "pcs_small.tsv", sep="\t", index=False)
    thresholds_small.to_csv(output_dir / "thresholds_small.tsv", sep="\t", index=False)


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    output_dir = repo_root / "tests" / "data" / "input"

    ids = make_ids(100)
    rng = np.random.default_rng(SEED)
    cohorts = make_pers_cohorts(ids, 10, rng)
    lab_values = make_lab_values(ids, rng)
    # Generated last so earlier simulated data is unchanged by adding PCs
    pcs = make_pcs(ids, 16, 3, rng)

    subset_ids = select_subset_ids(cohorts, N_SMALL)
    write_small_data(cohorts, lab_values, pcs, subset_ids, output_dir)


if __name__ == "__main__":
    main()
