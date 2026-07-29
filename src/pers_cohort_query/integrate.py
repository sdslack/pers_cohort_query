"""Data-integration helpers for personalized cohort analysis."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import scipy.stats


def load_tabular_data(path: str | Path, *, date_col: str | None = None) -> pd.DataFrame:
    """Load a CSV or TSV file into a DataFrame.

    If `date_col` is provided, the column is validated and converted to
    date-only format by discarding time information. Invalid dates raise an
    error.
    """

    file_path = Path(path)
    suffix = file_path.suffix.lower()
    if suffix == ".tsv":
        separator = "\t"
    elif suffix == ".csv":
        separator = ","
    else:
        raise ValueError(f"Unsupported file type: {suffix}.")

    df = pd.read_csv(file_path, sep=separator, parse_dates=date_col)

    # Validate dates and discard time information since downstream is date-based
    if date_col is not None:
        df[date_col] = pd.to_datetime(
            df[date_col], errors="raise", format="mixed"
        ).dt.date

    return df


def load_query_inputs(
    lab_values_path: str | Path,
    cohorts_path: str | Path,
    *,
    date_col: str = "date",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load and validate the lab values and cohort input tables.

    Returns a lab values DataFrame with at least columns `id`, `date`, and
    `value`, and a cohorts DataFrame with at least columns `id` and two or more
    columns listing cohort members.
    """
    lab_values = load_tabular_data(lab_values_path, date_col=date_col)
    cohorts = load_tabular_data(cohorts_path)

    required_lab_columns = {"id", date_col, "value"}
    missing_lab_columns = required_lab_columns - set(lab_values.columns)
    if missing_lab_columns:
        raise KeyError(
            f"Missing required columns in lab values: {', '.join(missing_lab_columns)}"
        )

    required_cohort_columns = {"id"}
    missing_cohort_columns = required_cohort_columns - set(cohorts.columns)
    if missing_cohort_columns:
        raise KeyError(
            f"Missing required columns in cohorts: {', '.join(missing_cohort_columns)}"
        )

    if cohorts.columns[0] != "id":
        raise ValueError(
            "The first column of the cohorts file must be 'id', followed by "
            "at least two cohort member columns."
        )
    if cohorts.shape[1] < 3:
        raise ValueError(
            "Cohorts file must have at least three columns: `id` and at least "
            "two cohort members."
        )

    na_lab_columns = lab_values[list(required_lab_columns)].isna().any()
    if na_lab_columns.any():
        raise ValueError(
            "Lab values contain missing values in required columns: "
            f"{', '.join(na_lab_columns[na_lab_columns].index)}"
        )

    na_cohort_columns = cohorts.isna().any()
    if na_cohort_columns.any():
        raise ValueError(
            "Cohorts contain missing values in columns: "
            f"{', '.join(na_cohort_columns[na_cohort_columns].index)}"
        )

    lab_ids = set(lab_values["id"].astype(str))
    cohort_member_columns = [column for column in cohorts.columns if column != "id"]
    cohort_ids = set(cohorts["id"].astype(str)) | set(
        cohorts[cohort_member_columns].astype(str).to_numpy().ravel()
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
    if value_col not in lab_values.columns:
        raise KeyError(f"Missing '{value_col}' column in lab_values")

    return get_density_peak(lab_values[value_col])


def get_pers_cohort_density_peaks(
    lab_values: pd.DataFrame,
    cohorts: pd.DataFrame,
    person_col: str = "id",
    value_col: str = "value",
) -> dict[str, float]:
    """Compute density peaks for each person's pooled cohort lab values.

    For each person in `cohorts`, all lab values from their listed cohort
    members are used to compute a single density peak.
    """
    if person_col not in lab_values.columns:
        raise KeyError(f"Missing '{person_col}' column in lab_values")
    if value_col not in lab_values.columns:
        raise KeyError(f"Missing '{value_col}' column in lab_values")
    if person_col not in cohorts.columns:
        raise KeyError(f"Missing '{person_col}' column in cohorts")
    if cohorts.shape[0] == 0:
        raise ValueError("Cohorts file must have at least one row.")

    member_columns = [column for column in cohorts.columns if column != person_col]
    people_values: dict[str, list[float]] = {
        str(person_id): group.tolist()
        for person_id, group in lab_values.groupby(person_col)[value_col]
    }

    peaks: dict[str, float] = {}
    for _, cohort_row in cohorts.iterrows():
        person_id = str(cohort_row[person_col])
        if str(person_id) in cohort_row[member_columns].astype(str).tolist():
            raise ValueError(f"Person '{person_id}' is in their own cohort.")
        if cohort_row[member_columns].isna().any():
            raise ValueError(
                f"Cohort members for person '{person_id}' contain missing values."
            )
        cohort_members = [str(member) for member in cohort_row[member_columns].tolist()]
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
    person_col: str = "id",
    value_col: str = "value",
) -> pd.DataFrame:
    """Compute the shift in density between eaech person's cohort and the full
    lab values dataset.

    The shift is calculated as the overall dataset peak minus the person's
    cohort peak. Returns one row per person with columns `person_col` and `shift`.
    """
    full_peak = get_all_density_peak(lab_values, value_col=value_col)
    cohort_peaks = get_pers_cohort_density_peaks(
        lab_values, cohorts, person_col=person_col, value_col=value_col
    )

    rows: list[dict[str, Any]] = [
        {person_col: person_id, "shift": full_peak - cohort_peak}
        for person_id, cohort_peak in cohort_peaks.items()
    ]
    return pd.DataFrame(rows)
