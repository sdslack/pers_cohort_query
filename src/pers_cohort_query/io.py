"""Input-output helpers for the pers_cohort_query package."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import numpy as np


def _validate_not_empty(df: pd.DataFrame, name: str) -> None:
    if df.empty:
        raise ValueError(f"{name} file must have at least one row.")


def _validate_required_columns(
    df: pd.DataFrame, required_columns: set[str], name: str
) -> None:
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise KeyError(
            f"{name} is missing required columns: {', '.join(sorted(missing_columns))}"
        )


def _validate_no_missing_values(
    df: pd.DataFrame, required_columns: set[str], name: str
) -> None:
    na_columns = df[list(required_columns)].isna().any()
    if na_columns.any():
        raise ValueError(
            f"{name} contain missing values in required columns: "
            f"{', '.join(na_columns[na_columns].index)}"
        )


def validate_lab_values(
    lab_values: pd.DataFrame,
    *,
    id_col: str = "id",
    date_col: str = "date",
    value_col: str = "value",
) -> tuple[pd.Series, pd.Series]:
    """Validate the lab values DataFrame, returning the parsed `date_col` and
    `value_col` columns.
    """
    _validate_not_empty(lab_values, "Lab values")
    required_columns = {id_col, date_col, value_col}
    _validate_required_columns(lab_values, required_columns, "Lab values")
    _validate_no_missing_values(lab_values, required_columns, "Lab values")

    try:
        dates = pd.to_datetime(lab_values[date_col], errors="raise", format="mixed")
    except ValueError as e:
        raise ValueError(f"Invalid date format in column '{date_col}': {e}") from e

    try:
        values = pd.to_numeric(lab_values[value_col], errors="raise")
    except ValueError as e:
        raise ValueError(
            f"Column '{value_col}' must contain only finite numeric values."
        ) from e

    if not np.isfinite(values).all():
        raise ValueError(
            f"Column '{value_col}' must contain only finite numeric values."
        )

    return dates, values


def validate_cohorts(
    cohorts: pd.DataFrame,
    *,
    id_col: str = "id",
):
    _validate_not_empty(cohorts, "Cohorts")

    required_columns = {id_col}
    _validate_required_columns(cohorts, required_columns, "Cohorts")
    _validate_no_missing_values(cohorts, cohorts.columns, "Cohorts")

    member_columns = [col for col in cohorts.columns if col != id_col]
    if len(member_columns) < 2:
        raise ValueError(
            "Cohorts file must have at least two member columns in addition to"
            "the `id_col` column."
        )

    if cohorts[id_col].duplicated().any():
        raise ValueError(
            "Cohorts cannot contain duplicate values in the `id_col` column."
        )

    member_values = cohorts[member_columns].to_numpy()
    id_values = cohorts[[id_col]].to_numpy()

    self_membership = (member_values == id_values).any(axis=1)
    if self_membership.any():
        bad_id = cohorts.loc[self_membership, id_col].iloc[0]
        raise ValueError(f"Person '{bad_id}' is in their own cohort.")

    sorted_members = np.sort(member_values, axis=1)
    has_duplicates = (sorted_members[:, :-1] == sorted_members[:, 1:]).any(axis=1)
    if has_duplicates.any():
        raise ValueError("Cohort members cannot be repeated within a single cohort.")


def load_query_inputs(
    lab_values_path: str | Path,
    cohorts_path: str | Path,
    *,
    id_col: str = "id",
    date_col: str = "date",
    value_col: str = "value",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load and validate the lab values and cohort input TSV files, ensuring
    the same individuals are in both.

    Returns a lab values DataFrame with at least columns `id_col`, `date_col`,
    and `value_col`, and a cohorts DataFrame with at least columns `id_col` and two
    or more columns listing cohort members.
    """
    lab_values = pd.read_csv(lab_values_path, sep="\t", dtype={id_col: str})
    parsed_dates, parsed_values = validate_lab_values(
        lab_values, id_col=id_col, date_col=date_col, value_col=value_col
    )
    cohorts = pd.read_csv(cohorts_path, sep="\t", dtype=str)
    validate_cohorts(cohorts, id_col=id_col)

    # Remove time information since downstream only uses dates
    lab_values[date_col] = parsed_dates.dt.date
    lab_values[value_col] = parsed_values

    lab_ids = set(lab_values[id_col])
    cohort_member_columns = [column for column in cohorts.columns if column != id_col]
    cohort_ids = set(cohorts[id_col]) | set(
        cohorts[cohort_member_columns].to_numpy().ravel()
    )
    missing_in_lab = cohort_ids - lab_ids
    if missing_in_lab:
        raise ValueError(
            f"Individuals in cohorts not found in lab values: {', '.join(missing_in_lab)}"
        )
    missing_in_cohort = lab_ids - cohort_ids
    if missing_in_cohort:
        raise ValueError(
            f"Individuals in lab values not found in cohorts: {', '.join(missing_in_cohort)}"
        )

    return lab_values, cohorts
