"""Functions to make small test data from the simulated data."""

from pathlib import Path
from typing import cast

import pandas as pd

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
    subset_ids: list[str],
    output_dir: Path,
    id_col: str = "id",
) -> None:
    """
    Write a subset of cohort and lab values data for testing.

    Includes cohort rows for `subset_ids` and lab values for those IDs as well
    as their cohort members.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    cohorts_small = cast(pd.DataFrame, cohorts.loc[cohorts[id_col].isin(subset_ids)])
    lab_value_ids = set(subset_ids) | set(get_member_ids(cohorts_small, id_col))
    lab_values_small = lab_values.loc[lab_values[id_col].isin(lab_value_ids)]

    cohorts_small.to_csv(output_dir / "cohorts_small.tsv", sep="\t", index=False)
    lab_values_small.to_csv(output_dir / "lab_values_small.tsv", sep="\t", index=False)


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    input_dir = repo_root / "examples" / "input"
    output_dir = repo_root / "tests" / "data" / "input"

    cohorts = pd.read_csv(input_dir / "cohorts.tsv", sep="\t", dtype=str)
    lab_values = pd.read_csv(input_dir / "lab_values.tsv", sep="\t", dtype={"id": str})

    subset_ids = select_subset_ids(cohorts, N_SMALL)
    write_small_data(cohorts, lab_values, subset_ids, output_dir)


if __name__ == "__main__":
    main()
