"""Data-integration helpers for personalized cohort analysis."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

import scipy.stats

logger = logging.getLogger(__name__)


class ZeroVarianceError(ValueError):
    """Raised when density peak estimation is attempted on constant values."""


@dataclass
class PersCohortValues:
    """Lab values and summary statistics for an individual's personalized cohort."""

    person_id: str
    values: np.ndarray
    peak: float
    mean: float
    stddev: float


def get_density_peak(values: pd.Series | np.ndarray | list[float]) -> float:
    """Return the x-position at the peak of the Gaussian kernel density
    estimate.

    Bandwidth is chosen with Silverman's rule of thumb, and the density is
    evaluated on an evenly spaced grid with 512 points. Bandwidth and grid size
    match the R implementation of this function.

    Raises a ValueError if values are empty, contain NaNs, or contain fewer
    than two values. Raises a ZeroVarianceError if all values are identical.
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
        raise ZeroVarianceError(
            "Cannot compute density peak: all values are identical."
        )

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
) -> dict[str, PersCohortValues]:
    """Compute a density peak for each person's pooled cohort lab values. Save
    values, peak, mean, and standard deviation for each person in
    PersCohortValues objects, returned in a dictionary keyed by person ID.
    """
    member_columns = [column for column in cohorts.columns if column != id_col]
    people_values: dict[str, np.ndarray] = {
        person_id: group.to_numpy()
        for person_id, group in lab_values.groupby(id_col)[value_col]
    }

    peaks: dict[str, PersCohortValues] = {}
    for _, cohort_row in cohorts.iterrows():
        person_id = cohort_row[id_col]
        members = cohort_row[member_columns]
        cohort_members = members.tolist()
        cohort_values = np.concatenate(
            [people_values[member] for member in cohort_members]
        )

        try:
            peak = get_density_peak(cohort_values)
            mean = float(np.mean(cohort_values))
            stddev = float(np.std(cohort_values))
        except ZeroVarianceError:
            logger.warning(
                "Cohort for person '%s' has zero variance; setting peak to NaN.",
                person_id,
            )
            peak = np.nan
            mean = np.nan
            stddev = np.nan

        peaks[person_id] = PersCohortValues(
            person_id=person_id,
            values=cohort_values,
            peak=peak,
            mean=mean,
            stddev=stddev,
        )

    return peaks


def compute_cohort_shifts(
    lab_values: pd.DataFrame,
    cohorts: pd.DataFrame,
    *,
    id_col: str = "id",
    value_col: str = "value",
) -> pd.DataFrame:
    """Compute the shift in density between each person's cohort and the full
    lab values dataset.

    The shift is calculated as the overall dataset peak minus the person's
    cohort peak. Returns one row per person with columns `id_col` and `shift`.
    """
    full_peak = get_all_density_peak(lab_values, value_col=value_col)
    cohort_peaks = get_pers_cohort_density_peaks(
        lab_values, cohorts, id_col=id_col, value_col=value_col
    )

    rows: list[dict[str, Any]] = [
        {id_col: person_id, "shift": full_peak - cohort.peak}
        for person_id, cohort in cohort_peaks.items()
    ]
    return pd.DataFrame(rows)
