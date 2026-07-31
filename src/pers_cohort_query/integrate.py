"""Data-integration helpers for personalized cohort analysis."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import scipy.stats


def validate_lab_values(
    lab_values: pd.DataFrame,
    *,
    id_col: str = "id",
    date_col: str = "date",
    value_col: str = "value",
):
    if lab_values.empty:
        raise ValueError("Lab values file must have at least one row.")

    required_lab_columns = {id_col, date_col, value_col}
    missing_lab_columns = required_lab_columns - set(lab_values.columns)
    if missing_lab_columns:
        raise KeyError(
            f"Missing required columns in lab values: {', '.join(missing_lab_columns)}"
        )

    na_lab_columns = lab_values[list(required_lab_columns)].isna().any()
    if na_lab_columns.any():
        raise ValueError(
            "Lab values contain missing values in required columns: "
            f"{', '.join(na_lab_columns[na_lab_columns].index)}"
        )

    try:
        pd.to_datetime(lab_values[date_col], errors="raise", format="mixed")
    except ValueError as e:
        raise ValueError(f"Invalid date format in column '{date_col}': {e}") from e


def validate_cohorts(
    cohorts: pd.DataFrame,
    *,
    id_col: str = "id",
):
    if cohorts.empty:
        raise ValueError("Cohorts file must have at least one row.")

    required_cohort_columns = {id_col}
    missing_cohort_columns = required_cohort_columns - set(cohorts.columns)
    if missing_cohort_columns:
        raise KeyError(
            f"Missing required columns in cohorts: {', '.join(missing_cohort_columns)}"
        )

    member_columns = [col for col in cohorts.columns if col != id_col]
    if len(member_columns) < 2:
        raise ValueError(
            "Cohorts file must have at least two member columns in addition to"
            "the `id_col` column."
        )

    na_cohort_columns = cohorts.isna().any()
    if na_cohort_columns.any():
        raise ValueError(
            "Cohorts contain missing values in columns: "
            f"{', '.join(na_cohort_columns[na_cohort_columns].index)}"
        )

    if cohorts[id_col].duplicated().any():
        raise ValueError(
            "Cohorts cannot contain duplicate values in the `id_col` column."
        )

    for _, row in cohorts.iterrows():
        person_id = row[id_col]
        if person_id in row[member_columns].tolist():
            raise ValueError(f"Person '{person_id}' is in their own cohort.")


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


def get_density_peak(values: pd.Series | np.ndarray | list[float]) -> float:
    """Return the x-position at the peak of the Gaussian kernel density
    estimate.

    Bandwidth is chosen with Silverman's rule of thumb, and the density is
    evaluated on an evenly spaced grid with 512 points. Bandwidth and grid size
    match the R implementation of this function.

    Raises a ValueError if values are empty, contain NaNs, contain fewer than
    two values, or have zero variance.
    """
    values = np.asarray(values, dtype=float)

    if len(values) == 0:
        raise ValueError("Cannot compute density peak: no values provided.")
    if np.isnan(values).any():
        raise ValueError("Cannot compute density peak: values contain NaN.")
    if len(values) == 1:
        raise ValueError(
            "Cannot compute density peak: at least two values are required."
        )
    # scipy.stats.gaussian_kde cannot estimate a density when input variance is zero
    if np.isclose(np.std(values), 0):
        raise ValueError("Cannot compute density peak: all values are identical.")

    kde = scipy.stats.gaussian_kde(values, bw_method="silverman")
    x_vals = np.linspace(values.min(), values.max(), 512)
    peak = float(x_vals[np.argmax(kde(x_vals))])
    return peak


def get_all_density_peak(lab_values: pd.DataFrame, value_col: str = "value") -> float:
    return get_density_peak(lab_values[value_col])


def get_pers_cohort_density_peaks(
    lab_values: pd.DataFrame,
    cohorts: pd.DataFrame,
    id_col: str = "id",
    value_col: str = "value",
) -> dict[str, float]:
    """Compute density peaks for each person's pooled cohort lab values.

    For each person in `cohorts`, all lab values from their listed cohort
    members are used to compute a single density peak.
    """
    member_columns = [column for column in cohorts.columns if column != id_col]
    people_values: dict[str, list[float]] = {
        person_id: group.tolist()
        for person_id, group in lab_values.groupby(id_col)[value_col]
    }

    peaks: dict[str, float] = {}
    for _, cohort_row in cohorts.iterrows():
        person_id = cohort_row[id_col]
        if person_id in cohort_row[member_columns].tolist():
            raise ValueError(f"Person '{person_id}' is in their own cohort.")
        if cohort_row[member_columns].isna().any():
            raise ValueError(
                f"Cohort members for person '{person_id}' contain missing values."
            )
        cohort_members = [member for member in cohort_row[member_columns].tolist()]
        cohort_values: list[float] = []
        for member in cohort_members:
            if member not in people_values:
                raise ValueError(
                    f"Missing lab values for person '{member}', "
                    f"a cohort member of person '{person_id}'."
                )
            cohort_values.extend(people_values[member])

        peaks[person_id] = get_density_peak(cohort_values)

    return peaks


def compute_cohort_shifts(
    lab_values: pd.DataFrame,
    cohorts: pd.DataFrame,
    *,
    id_col: str = "id",
    value_col: str = "value",
) -> pd.DataFrame:
    """Compute the shift in density between eaech person's cohort and the full
    lab values dataset.

    The shift is calculated as the overall dataset peak minus the person's
    cohort peak. Returns one row per person with columns `id_col` and `shift`.
    """
    full_peak = get_all_density_peak(lab_values, value_col=value_col)
    cohort_peaks = get_pers_cohort_density_peaks(
        lab_values, cohorts, id_col=id_col, value_col=value_col
    )

    rows: list[dict[str, Any]] = [
        {id_col: person_id, "shift": full_peak - cohort_peak}
        for person_id, cohort_peak in cohort_peaks.items()
    ]
    return pd.DataFrame(rows)
