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
):
    _validate_not_empty(lab_values, "Lab values")
    required_columns = {id_col, date_col, value_col}
    _validate_required_columns(lab_values, required_columns, "Lab values")
    _validate_no_missing_values(lab_values, required_columns, "Lab values")

    try:
        pd.to_datetime(lab_values[date_col], errors="raise", format="mixed")
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

    for _, row in cohorts.iterrows():
        person_id = row[id_col]
        members = row[member_columns].tolist()
        if person_id in members:
            raise ValueError(f"Person '{person_id}' is in their own cohort.")

        if len(members) != len(set(members)):
            raise ValueError(
                "Cohort members cannot be repeated within a single cohort."
            )


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
    and `value`, and a cohorts DataFrame with at least columns `id_col` and two
    or more columns listing cohort members.
    """
    lab_values = pd.read_csv(lab_values_path, sep="\t", dtype={id_col: str})
    validate_lab_values(
        lab_values, id_col=id_col, date_col=date_col, value_col=value_col
    )
    cohorts = pd.read_csv(cohorts_path, sep="\t", dtype=str)
    validate_cohorts(cohorts, id_col=id_col)

    # Remove time information since downstream only uses dates
    lab_values[date_col] = pd.to_datetime(
        lab_values[date_col], errors="raise", format="mixed"
    ).dt.date

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
