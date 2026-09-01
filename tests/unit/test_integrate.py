"""Unit tests for pers_cohort_query.integrate module."""

from pers_cohort_query.integrate import (
    get_all_density_peak,
    get_density_peak,
    get_pers_cohort_density_peaks,
    compute_cohort_shifts,
    PersCohortValues,
    ZeroVarianceError,
)
import numpy as np
import pandas as pd
import pytest


# region: tests for get_density_peak


def test_get_density_peak_multiple_values():
    values = [1.0, 2.0, 2.0, 3.0]
    peak = get_density_peak(values)
    assert peak == pytest.approx(2.0, abs=0.1)  # for KDE implementation


def test_get_density_peak_single_value_raises():
    with pytest.raises(ValueError, match="at least two values"):
        get_density_peak([5.0])


def test_get_density_peak_empty_raises():
    with pytest.raises(ValueError, match="no values"):
        get_density_peak([])


def test_get_density_peak_nan_raises():
    with pytest.raises(ValueError, match="NaN"):
        get_density_peak([1.0, float("nan"), 3.0])


def test_get_density_peak_zero_variance_raises():
    with pytest.raises(ZeroVarianceError, match="identical"):
        get_density_peak([5.0, 5.0, 5.0])


# endregion

# region: tests for get_all_density_peak


def test_get_all_density_peak_all_lab_values():
    lab_values = pd.DataFrame(
        {
            "id": ["1", "1", "2", "3"],
            "date": ["2020-01-01", "2020-01-02", "2020-01-03", "2020-01-04"],
            "value": [10.0, 20.0, 20.0, 30.0],
        }
    )

    peak = get_all_density_peak(lab_values)

    assert isinstance(peak, float)
    assert peak == pytest.approx(20.0, abs=0.1)


# endregion

# region: tests for get_pers_cohort_density_peaks


def test_get_pers_cohort_density_peaks_example():
    lab_values = pd.DataFrame(
        {
            "id": ["1", "2", "3", "4"],
            "date": ["2020-01-01", "2020-01-02", "2020-01-03", "2020-01-04"],
            "value": [10.0, 20.0, 30.0, 40.0],
        }
    )

    cohorts = pd.DataFrame(
        {"id": ["1", "2"], "member_1": ["2", "3"], "member_2": ["3", "4"]}
    )

    pers_peaks = get_pers_cohort_density_peaks(lab_values, cohorts)

    assert isinstance(pers_peaks, dict)
    assert set(pers_peaks.keys()) == {"1", "2"}
    assert all(isinstance(v, PersCohortValues) for v in pers_peaks.values())
    assert all(isinstance(v.peak, float) for v in pers_peaks.values())


def test_get_pers_cohort_density_peaks_extra_person_in_lab_values():
    lab_values = pd.DataFrame(
        {
            "id": ["1", "2", "3", "4"],
            "date": ["2020-01-01", "2020-01-02", "2020-01-03", "2020-01-04"],
            "value": [10.0, 20.0, 30.0, 40.0],
        }
    )

    cohorts = pd.DataFrame({"id": ["1"], "member_1": ["2"], "member_2": ["3"]})

    pers_peaks = get_pers_cohort_density_peaks(lab_values, cohorts)

    assert isinstance(pers_peaks, dict)
    assert set(pers_peaks.keys()) == {"1"}
    assert all(isinstance(v, PersCohortValues) for v in pers_peaks.values())
    assert all(isinstance(v.peak, float) for v in pers_peaks.values())


def test_get_pers_cohort_density_peaks_zero_variance_cohort_is_nan(caplog):
    lab_values = pd.DataFrame(
        {
            "id": ["1", "2", "3"],
            "date": ["2020-01-01", "2020-01-02", "2020-01-03"],
            "value": [10.0, 20.0, 20.0],
        }
    )

    cohorts = pd.DataFrame({"id": ["1"], "member_1": ["2"], "member_2": ["3"]})

    with caplog.at_level("WARNING"):
        pers_peaks = get_pers_cohort_density_peaks(lab_values, cohorts)

    assert np.isnan(pers_peaks["1"].peak)
    assert np.isnan(pers_peaks["1"].mean)
    assert np.isnan(pers_peaks["1"].stddev)
    assert "zero variance" in caplog.text


# endregion

# region: tests compute_cohort_shifts


def test_compute_cohort_shifts_example():
    measurements = pd.DataFrame(
        {
            "id": ["1", "2", "3", "4"],
            "date": ["2020-01-01", "2020-01-02", "2020-01-03", "2020-01-04"],
            "value": [10.0, 20.0, 30.0, 40.0],
        }
    )

    cohorts = pd.DataFrame(
        {"id": ["1", "2"], "member_1": ["2", "3"], "member_2": ["3", "4"]}
    )

    shifts = compute_cohort_shifts(measurements, cohorts)

    assert isinstance(shifts, pd.DataFrame)
    assert shifts.shape[0] == 2
    assert shifts.shape[1] == 2
    assert list(shifts.columns) == ["id", "shift"]
    assert shifts["id"].iloc[0] == "1"
    assert isinstance(shifts["shift"].iloc[0], float)
    assert shifts["id"].iloc[1] == "2"
    assert isinstance(shifts["shift"].iloc[1], float)


# endregion
