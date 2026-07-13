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
        List of column names to parse as dates, by default None

    Returns
    -------
    df : pd.DataFrame
        Loaded DataFrame
    """

    file_path = Path(path)
    suffix = file_path.suffix.lower()
    if suffix == ".tsv":
        separator = "\t"
    else:
        separator = ","

    return pd.read_csv(file_path, sep=separator, parse_dates=parse_dates)


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
        DataFrame containing lab values and DataFrame containing cohorts

    """
    lab_values = load_tabular_data(lab_values_path, parse_dates=[date_col])
    cohorts = load_tabular_data(cohorts_path)
    return lab_values, cohorts


def get_density_peak(values: pd.Series | np.ndarray | list[float]) -> float:
    """Return the x-position at the peak of a Gaussian kernel density estimate.

    Bandwidth is chosen with Silverman's rule of thumb, and the density is
    evaluated on an evenly spaced grid with a default of 512 points.

    Parameters
    ----------
    values : pd.Series | np.ndarray | list[float]
        Values to estimate density from

    Returns
    -------
    peak : float
        Grid location of maximum estimated density, or NaN if there are no
        values to estimate from
    """
    values = np.asarray(values, dtype=float)
    values = values[~np.isnan(values)]

    if len(values) == 0:
        return float("nan")
    if len(values) == 1 or np.std(values) == 0:
        return float(values[0])

    # TODO: revisit bandwidth selection, current implementation matches previous
    # analysis in R
    kde = scipy.stats.gaussian_kde(values, bw_method="silverman")
    x_vals = np.linspace(values.min(), values.max(), 512)
    peak = float(x_vals[np.argmax(kde(x_vals))])
    return peak


# TODO: need to revisit how to handle longitudinal data
# TODO: likely want to revisit and save more than just peak --> maybe object
# with peak, meand, stdev
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


def get_pers_cohort_density_peak(
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

    member_columns = [column for column in cohorts.columns if column != person_col]
    people_values: dict[str, list[float]] = {
        str(person_id): group.tolist()
        for person_id, group in lab_values.groupby(person_col)[value_col]
    }

    peaks: dict[str, float] = {}
    for _, cohort_row in cohorts.iterrows():
        person_id = str(cohort_row[person_col])
        cohort_members = [
            str(member)
            for member in cohort_row[member_columns].tolist()
            if pd.notna(member)
        ]
        cohort_values: list[float] = []
        for member in cohort_members:
            cohort_values.extend(people_values.get(member, []))

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
        One row per person, with columns `person_col` and "shift"
    """
    full_peak = get_all_density_peak(measurements, value_col=value_col)
    cohort_peaks = get_pers_cohort_density_peak(
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
