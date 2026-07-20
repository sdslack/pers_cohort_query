"""Data-integration helpers for personalized cohort analysis.

+ load_tabular_data: Load CSV or TSV into a DataFrame
+ load_query_inputs: Load the two input tables used by the analysis pipeline
+ get_density_peak: Calculate the peak of a distribution
+ get_all_density_peak: Calculate the density peak across all lab values
+ get_pers_cohort_density_peak: Calculate each person's cohort density peak
+ compute_cohort_shifts: Compute the cohort-specific density shift for each person
+ write_output: Write the output DataFrame to a CSV file

"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import scipy.stats


def load_tabular_data(
    path: str | Path, *, parse_dates: list[str] | None = None
) -> pd.DataFrame:
    """Load a CSV or TSV file into a DataFrame. 

    Parameters
    ----------
    path : str | Path
        Path to the CSV or TSV file

    parse_dates : list[str] | None, optional
        List of column names to parse as dates, by default None. Dates should
        be in ISO 8601 format (e.g., YYYY-MM-DD or YYYY-MM-DD HH:MM:SS). Only
        date is kept, not time.

    Returns
    -------
    df : pd.DataFrame
        Loaded DataFrame
    """

    file_path = Path(path)
    suffix = file_path.suffix.lower()
    if suffix == ".tsv":
        separator = "\t"
    elif suffix == ".csv":
        separator = ","
    else:
        raise ValueError(f"Unsupported file type: {suffix}.")
    
    df = pd.read_csv(file_path, sep=separator, parse_dates=parse_dates)

    # Ensure all values in date column are valid dates or missing values, and
    # convert to dates only
    if parse_dates is not None:
        for col in parse_dates:
            df[col] = pd.to_datetime(
                df[col], errors="raise", format = "mixed").dt.date

    return df


def load_query_inputs(
    lab_values_path: str | Path,
    cohorts_path: str | Path,
    *,
    date_col: str = "date",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load the two query input tables.

    Parameters
    ----------
    lab_values_path : str | Path
        Path to the lab values CSV or TSV file
    cohorts_path : str | Path
        Path to the cohorts CSV or TSV file
    date_col : str, optional
        Name of the date column in the lab values file to parse as a date,
        by default "date"

    Returns
    -------
    lab_values, cohorts : tuple[pd.DataFrame, pd.DataFrame]
        DataFrame containing lab values and DataFrame containing cohorts. Lab
        values DataFrame has at least columns `id`, `date`, and `value`.
        Cohorts DataFrame has at least columns `id` and two or more cohort
        member columns.

    """
    lab_values = load_tabular_data(lab_values_path, parse_dates=[date_col])
    cohorts = load_tabular_data(cohorts_path)

    # Check for required columns in lab values
    required_lab_columns = {"id", date_col, "value"}
    missing_lab_columns = required_lab_columns - set(lab_values.columns)
    if missing_lab_columns:
        raise KeyError(
            f"Missing required columns in lab values: {', '.join(missing_lab_columns)}"
        )

    # Check for required columns in cohorts
    required_cohort_columns = {"id"}
    missing_cohort_columns = required_cohort_columns - set(cohorts.columns)
    if missing_cohort_columns:
        raise KeyError(
            f"Missing required columns in cohorts: {', '.join(missing_cohort_columns)}"
        )
    if cohorts.shape[1] < 3:
        raise ValueError(
            "Cohorts file must have at least three columns: `id` and at least "
            "two cohort members."
        )

    # Check for missing values in required lab values columns
    na_lab_columns = lab_values[list(required_lab_columns)].isna().any()
    if na_lab_columns.any():
        raise ValueError(
            "Lab values contain missing values in required columns: "
            f"{', '.join(na_lab_columns[na_lab_columns].index)}"
        )

    # Check for missing values in cohorts columns
    na_cohort_columns = cohorts.isna().any()
    if na_cohort_columns.any():
        raise ValueError(
            "Cohorts contain missing values in columns: "
            f"{', '.join(na_cohort_columns[na_cohort_columns].index)}"
        )

    # Check that same individuals are present in both lab_values and cohorts
    lab_ids = set(lab_values["id"].astype(str))
    cohort_ids = set(cohorts["id"].astype(str))
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
    """Return the x-position at the peak of a Gaussian kernel density estimate.

    Bandwidth is chosen with Silverman's rule of thumb, and the density is
    evaluated on an evenly spaced grid with a default of 512 points.
    NOTE: this decision was made to match R implementation.

    Parameters
    ----------
    values : pd.Series | np.ndarray | list[float]
        Values to estimate density from. Must contain at least two values,
        none of which may be NaN.

    Returns
    -------
    peak : float
        Grid location of maximum estimated density

    Raises
    ------
    ValueError
        If `values` is empty, contains any NaN values, or has fewer than
        two values, since downstream callers require a valid peak.
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

    kde = scipy.stats.gaussian_kde(values, bw_method="silverman")
    x_vals = np.linspace(values.min(), values.max(), 512)
    peak = float(x_vals[np.argmax(kde(x_vals))])
    return peak


def get_all_density_peak(lab_values: pd.DataFrame, value_col: str = "value") -> float:
    """Return a float with the density peak of all values.

    Parameters
    ----------
    lab_values : pd.DataFrame
        Measurements containing at least a value column
    value_col : str, optional
        Name of the value column in `lab_values`, by default "value"

    Returns
    -------
    peak : float
        Density peak across all measurements
    """
    if value_col not in lab_values.columns:
        raise KeyError(f"Missing '{value_col}' column in lab_values")

    return get_density_peak(lab_values[value_col])


def get_pers_cohort_density_peaks(
    lab_values: pd.DataFrame,
    cohorts: pd.DataFrame,
    person_col: str = "id",
    value_col: str = "value",
) -> dict[str, float]:
    """Return a dictionary mapping each person to their cohort density peak.

    For each row in `cohorts`, gathers the `lab_values` measurements
    belonging to that person's listed cohort members and computes the
    density peak across those pooled values.

    Parameters
    ----------
    lab_values : pd.DataFrame
        Measurements with a person-identifier column and a value column
    cohorts : pd.DataFrame
        Cohort membership table; the `person_col` column identifies the
        person, and all other columns list that person's cohort members
    person_col : str, optional
        Name of the person-identifier column shared by both inputs, by default "id"
    value_col : str, optional
        Name of the value column in `lab_values`, by default "value"

    Returns
    -------
    peaks : dict[str, float]
        Mapping of person ID to the density peak of their cohort's pooled values
    """
    if person_col not in lab_values.columns:
        raise KeyError(f"Missing '{person_col}' column in lab_values")
    if value_col not in lab_values.columns:
        raise KeyError(f"Missing '{value_col}' column in lab_values")
    if person_col not in cohorts.columns:
        raise KeyError(f"Missing '{person_col}' column in cohorts")
    
    # Check cohorts has at least one row after header row
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
        if person_id in cohort_row[member_columns].tolist():
            raise ValueError(
                f"Person '{person_id}' is in their own cohort."
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
    measurements: pd.DataFrame,
    cohorts: pd.DataFrame,
    *,
    person_col: str = "id",
    value_col: str = "value",
) -> pd.DataFrame:
    """Compute the cohort-specific density shift for each person.

    The shift is the difference between the full-cohort density peak and the
    density peak of the cohort members listed for each person.

    Parameters
    ----------
    measurements : pd.DataFrame
        Measurements with a person-identifier column and a value column
    cohorts : pd.DataFrame
        Cohort membership table; the `person_col` column identifies the
        person, and all other columns list that person's cohort members
    person_col : str, optional
        Name of the person-identifier column shared by both inputs, by default "id"
    value_col : str, optional
        Name of the value column in `measurements`, by default "value"

    Returns
    -------
    shifts : pd.DataFrame
        One row per person, with columns `person_col` and `shift`
    """
    full_peak = get_all_density_peak(measurements, value_col=value_col)
    cohort_peaks = get_pers_cohort_density_peaks(
        measurements, cohorts, person_col=person_col, value_col=value_col
    )

    rows: list[dict[str, Any]] = [
        {person_col: person_id, "shift": full_peak - cohort_peak}
        for person_id, cohort_peak in cohort_peaks.items()
    ]
    return pd.DataFrame(rows)


def write_output(df: pd.DataFrame, output_path: str | Path) -> None:
    """Write the output DataFrame to a CSV file.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame to write to CSV
    output_path : str | Path
        Path to the output CSV file
    """
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    df.to_csv(Path(output_path), index=False)
