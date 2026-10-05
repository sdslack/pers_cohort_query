"""Unit tests for pers_cohort_query.summarize module."""

from pers_cohort_query.summarize import (
    get_threshold_ends,
    summarize_measurements,
    summarize_warning_status,
    summarize_shifts,
)
import pandas as pd
import pytest


# region: tests for get_threshold_ends


def test_get_threshold_ends_both():
    thresholds = pd.DataFrame({"low": [10.0], "high": [20.0]})

    assert get_threshold_ends(thresholds) == {"low": 10.0, "high": 20.0}


def test_get_threshold_ends_only_one_end():
    assert get_threshold_ends(pd.DataFrame({"high": [20.0]})) == {"high": 20.0}
    assert get_threshold_ends(pd.DataFrame({"low": [10.0], "high": [None]})) == {
        "low": 10.0
    }


def test_get_threshold_ends_raises_if_none():
    with pytest.raises(ValueError):
        get_threshold_ends(pd.DataFrame({"other": [1.0]}))


# endregion

# region: tests for summarize_measurements


def test_summarize_measurements_personalized_thresholds_and_confusion():
    lab_values = pd.DataFrame(
        {
            "id": ["1", "1", "1"],
            "date": ["2020-01-01", "2020-01-02", "2020-01-03"],
            "value": [5.0, 8.0, 16.0],
        }
    )
    thresholds = pd.DataFrame({"low": [10.0], "high": [20.0]})
    shifts = pd.DataFrame({"id": ["1"], "shift": [5.0]})

    classified = summarize_measurements(lab_values, thresholds, shifts)

    assert classified.shape[0] == 3
    # personalized threshold as ground truth
    assert list(classified["pers_low"]) == [5.0, 5.0, 5.0]
    assert list(classified["pers_high"]) == [15.0, 15.0, 15.0]
    assert list(classified["conf_low"]) == ["tp", "fp", "tn"]
    assert list(classified["conf_high"]) == ["tn", "tn", "fn"]


def test_summarize_measurements_only_one_end():
    lab_values = pd.DataFrame({"id": ["1"], "date": ["2020-01-01"], "value": [16.0]})
    thresholds = pd.DataFrame({"high": [20.0]})
    shifts = pd.DataFrame({"id": ["1"], "shift": [5.0]})

    classified = summarize_measurements(lab_values, thresholds, shifts)

    assert "conf_low" not in classified.columns
    assert list(classified["conf_high"]) == ["fn"]


# endregion

# region: tests for summarize_warning_status


def test_summarize_warning_status_categories():
    classified = pd.DataFrame(
        {
            "id": ["1", "2", "2", "3", "4", "5", "5", "6"],
            "date": [
                "2020-01-01",
                "2020-01-01",
                "2020-06-01",
                "2020-01-01",
                "2020-01-01",
                "2020-01-01",
                "2020-06-01",
                "2020-01-01",
            ],
            "conf_low": ["tn", "fn", "tp", "fn", "fp", "fp", "tp", "tp"],
        }
    )

    status = summarize_warning_status(classified)

    assert list(status["id"]) == ["1", "2", "3", "4", "5", "6"]
    assert list(status["low_status"]) == [
        "normal",
        "pers_early",
        "pers_only",
        "standard_only",
        "standard_same_or_early",
        "standard_same_or_early",
    ]
    assert "high_status" not in status.columns


# endregion

# region: tests for summarize_shifts


def test_summarize_shifts_keeps_every_person():
    lab_values = pd.DataFrame(
        {
            "id": ["1", "2"],
            "date": pd.to_datetime(["2020-01-01", "2020-01-01"]),
            "value": [5.0, 15.0],
        }
    )
    thresholds = pd.DataFrame({"low": [10.0], "high": [20.0]})
    shifts = pd.DataFrame({"id": ["1", "2"], "shift": [0.0, 0.0]})

    person_summary, classified = summarize_shifts(lab_values, thresholds, shifts)

    assert list(person_summary.columns) == ["id", "shift", "low_status", "high_status"]
    assert list(person_summary["id"]) == ["1", "2"]
    assert list(person_summary["low_status"]) == ["standard_same_or_early", "normal"]
    assert list(person_summary["high_status"]) == ["normal", "normal"]
    assert classified.shape[0] == 2


# endregion
