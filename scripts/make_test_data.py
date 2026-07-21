"""Functions to make small test data from the full simulated data

* select_subset_ids - returns a small subset of the IDs in a cohorts dataframe
* get_member_ids - returns all cohort member IDs referenced in a cohorts dataframe
* write_small_data - writes small subset of cohorts/lab_values to CSV

"""

from pathlib import Path
from typing import cast

import pandas as pd

N_SMALL = 5


def select_subset_ids(cohorts: pd.DataFrame, n: int, id_col: str = "id") -> list[str]:
    """
    Returns the first n IDs from a cohorts DataFrame.

    Parameters
    ----------
    cohorts : pd.DataFrame
        DataFrame with an id_col column of person IDs
    n : int
        Number of IDs to select
    id_col : str, optional
        Name of the person-identifier column, by default "id"

    Returns
    -------
    ids : list[str]
        Selected subset of IDs
    """
    return cohorts[id_col].head(n).tolist()


def get_member_ids(cohorts: pd.DataFrame, id_col: str = "id") -> list[str]:
    """
    Returns all cohort member IDs referenced across a cohorts DataFrame.

    Parameters
    ----------
    cohorts : pd.DataFrame
        DataFrame with an id_col column and one or more member columns
    id_col : str, optional
        Name of the person-identifier column, by default "id"

    Returns
    -------
    ids : list[str]
        Unique cohort member IDs found in the member columns
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
    Writes the rows of cohorts belonging to subset_ids to cohorts_small.csv,
    and the rows of lab_values for subset_ids plus all of their cohort
    members to lab_values_small.csv, in output_dir. Including cohort members'
    lab values ensures every member referenced in cohorts_small has data.

    Parameters
    ----------
    cohorts : pd.DataFrame
        Full cohorts DataFrame to select rows from
    lab_values : pd.DataFrame
        Full lab values DataFrame to select rows from
    subset_ids : list[str]
        IDs to keep in cohorts_small.csv
    output_dir : Path
        Directory to write the output CSV files to
    id_col : str, optional
        Name of the person-identifier column, by default "id"
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    cohorts_small = cast(pd.DataFrame, cohorts.loc[cohorts[id_col].isin(subset_ids)])
    lab_value_ids = set(subset_ids) | set(get_member_ids(cohorts_small, id_col))
    lab_values_small = lab_values.loc[lab_values[id_col].isin(lab_value_ids)]

    cohorts_small.to_csv(output_dir / "cohorts_small.csv", index=False)
    lab_values_small.to_csv(output_dir / "lab_values_small.csv", index=False)


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    input_dir = repo_root / "data" / "input"
    output_dir = repo_root / "test" / "data" / "input"

    cohorts = pd.read_csv(input_dir / "cohorts.csv")
    lab_values = pd.read_csv(input_dir / "lab_values.csv")

    subset_ids = select_subset_ids(cohorts, N_SMALL)
    write_small_data(cohorts, lab_values, subset_ids, output_dir)


if __name__ == "__main__":
    main()
