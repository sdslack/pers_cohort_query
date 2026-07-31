"""Unit tests for pers_cohort_query.integrate module."""

from datetime import date

from pers_cohort_query.integrate import (
    validate_lab_values,
    validate_cohorts,
    load_query_inputs,
    get_all_density_peak,
    get_density_peak,
    get_pers_cohort_density_peaks,
    compute_cohort_shifts,
)
import pandas as pd
import pytest

# region: tests for validate_lab_values


def test_validate_lab_values_raises_error_for_empty_file():
    lab_values = pd.DataFrame(
        {
            "id": [],
            "date": [],
            "value": [],
        }
    )
    with pytest.raises(
        ValueError,
        match=r"Lab values file must have at least one row\.",
    ):
        validate_lab_values(lab_values)


def test_validate_lab_values_raises_error_for_invalid_date_column():
    lab_values = pd.DataFrame(
        {
            "id": [1, 2],
            "date": ["2020-01-01", "2020-01-02"],
            "value": [10, 20],
        }
    )
    with pytest.raises(
        KeyError,
        match="Missing required columns in lab values",
    ):
        validate_lab_values(lab_values, date_col="nonexistent_col")


@pytest.mark.parametrize(
    "invalid_date",
    [
        "invalid-date",
        "20200-01-02",
        "2020-13-01",
        "2020-01-35",
    ],
)
def test_validate_lab_values_raises_error_for_invalid_date_format(invalid_date):
    lab_values = pd.DataFrame(
        {
            "id": [1, 2],
            "date": ["2020-01-01", invalid_date],
            "value": [10, 20],
        }
    )
    with pytest.raises(ValueError):
        validate_lab_values(lab_values, date_col="date")


def test_validate_lab_values_handles_date_and_datetime_formats():
    lab_values = pd.DataFrame(
        {
            "id": [1, 2],
            "date": ["2020-01-01", "2020-01-02 12:34:56"],
            "value": [10, 20],
        }
    )
    validate_lab_values(lab_values, date_col="date")


def test_validate_lab_values_raises_error_for_missing_required_columns():
    lab_values = pd.DataFrame(
        {
            "id": [1, 2],
            "date": ["2020-01-01", "2020-01-02"],
            # missing 'value' column
        }
    )
    with pytest.raises(
        KeyError,
        match="Missing required columns in lab values",
    ):
        validate_lab_values(lab_values)


def test_validate_lab_values_raises_error_for_missing_values_in_required_columns():
    lab_values = pd.DataFrame(
        {
            "id": [1, 2],
            "date": ["2020-01-01", None],  # missing value in 'date' column
            "value": [10, 20],
        }
    )
    with pytest.raises(
        ValueError,
        match="Lab values contain missing values in required columns",
    ):
        validate_lab_values(lab_values)


@pytest.mark.parametrize(
    "id_col,date_col,value_col",
    [
        ("IDS", "Dates", "y"),
        ("patient_id", "collection_date", "measurement"),
        ("a", "date", "value"),
    ],
)
def test_validate_lab_values_accepts_custom_column_names(id_col, date_col, value_col):
    lab_values = pd.DataFrame(
        {
            id_col: [1, 2],
            date_col: ["2020-01-01", "2020-01-02"],
            value_col: [10, 20],
        }
    )

    validate_lab_values(
        lab_values,
        id_col=id_col,
        date_col=date_col,
        value_col=value_col,
    )


# endregion

# region tests for validate_cohorts


def test_validate_cohorts_raises_error_for_empty_file():
    cohorts = pd.DataFrame(
        {
            "id": [],
            "member_1": [],
            "member_2": [],
        }
    )
    with pytest.raises(
        ValueError,
        match=r"Cohorts file must have at least one row\.",
    ):
        validate_cohorts(cohorts)


def test_validate_cohorts_raises_error_for_missing_required_columns():
    cohorts = pd.DataFrame(
        {
            "wrong_id": [1, 2],
            "member_1": [2, 3],
            "member_2": [3, 4],
        }
    )
    with pytest.raises(
        KeyError,
        match="Missing required columns in cohorts",
    ):
        validate_cohorts(cohorts)


def test_validate_cohorts_raises_error_for_too_few_cohort_members():
    cohorts = pd.DataFrame(
        {
            "id": [1, 2],
            "member_1": [2, 3],
        }
    )
    with pytest.raises(
        ValueError,
        match="Cohorts file must have at least two member columns in addition to",
    ):
        validate_cohorts(cohorts)


def test_validate_cohorts_raises_error_for_missing_values_in_columns():
    cohorts = pd.DataFrame(
        {
            "id": [1, 2],
            "member_1": [2, None],
            "member_2": [3, 4],
        }
    )
    with pytest.raises(
        ValueError,
        match="Cohorts contain missing values in columns",
    ):
        validate_cohorts(cohorts)


def test_validate_cohorts_accepts_custom_id_column_name():
    cohorts = pd.DataFrame(
        {
            "custom_id": [1, 2],
            "member_1": [2, 3],
            "member_2": [3, 4],
        }
    )
    validate_cohorts(cohorts, id_col="custom_id")


def test_validate_cohorts_accepts_different_member_column_names():
    cohorts = pd.DataFrame(
        {
            "id": [1, 2],
            "a": [2, 3],
            "b": [3, 4],
        }
    )
    validate_cohorts(cohorts)


def test_validate_cohorts_raises_error_for_duplicate_ids():
    cohorts = pd.DataFrame(
        {
            "id": [1, 1, 2, 3],
            "member_1": [2, 3, 1, 1],
            "member_2": [3, 4, 2, 4],
        }
    )
    with pytest.raises(
        ValueError,
        match="Cohorts cannot contain duplicate values in the `id_col` column",
    ):
        validate_cohorts(cohorts)


# endregion

# region: tests for load_query_inputs


def test_load_query_inputs_loads_both_files(tmp_path):
    lab_values_file = tmp_path / "lab_values.tsv"
    lab_values_file.write_text(
        "id\tdate\tvalue\n1\t2020-01-01\t10\n2\t2020-01-02\t20\n3\t2020-01-03\t30\n4\t2020-01-04\t40"
    )

    cohorts_file = tmp_path / "cohorts.tsv"
    cohorts_file.write_text("id\tmember_1\tmember_2\n1\t2\t3\n2\t3\t4")

    lab_values, cohorts = load_query_inputs(lab_values_file, cohorts_file)

    assert lab_values.shape == (4, 3)
    assert cohorts.shape == (2, 3)


def test_load_query_inputs_raises_error_if_error_in_lab_values(tmp_path):
    lab_values_file = tmp_path / "lab_values.tsv"
    lab_values_file.write_text(
        "id\tdate\twrong_name\n1\t2020-01-01\t10\n2\t2020-01-02\t20"
    )

    cohorts_file = tmp_path / "cohorts.tsv"
    cohorts_file.write_text("id\tmember_1\tmember_2\n1\t2\t3\n2\t3\t4")

    with pytest.raises(
        KeyError,
        match="Missing required columns in lab values",
    ):
        load_query_inputs(lab_values_file, cohorts_file)


def test_load_query_inputs_raises_error_if_error_in_cohorts(tmp_path):
    lab_values_file = tmp_path / "lab_values.tsv"
    lab_values_file.write_text("id\tdate\tvalue\n1\t2020-01-01\t10\n2\t2020-01-02\t20")

    cohorts_file = tmp_path / "cohorts.tsv"
    cohorts_file.write_text("wrong_name\tmember_1\tmember_2\n1\t2\t3\n2\t3\t1")

    with pytest.raises(
        KeyError,
        match="Missing required columns in cohorts",
    ):
        load_query_inputs(lab_values_file, cohorts_file)


def test_load_query_inputs_raises_error_for_ids_in_cohorts_not_in_lab_values(tmp_path):
    lab_values_file = tmp_path / "lab_values.tsv"
    lab_values_file.write_text("id\tdate\tvalue\n1\t2020-01-01\t10\n2\t2020-01-02\t20")

    cohorts_file = tmp_path / "cohorts.tsv"
    cohorts_file.write_text("id\tmember_1\tmember_2\n1\t2\t3\n3\t4\t5")

    with pytest.raises(
        ValueError, match="Individuals in cohorts not found in lab values"
    ):
        load_query_inputs(lab_values_file, cohorts_file)


def test_load_query_inputs_raises_error_for_ids_in_lab_values_not_in_cohorts(tmp_path):
    lab_values_file = tmp_path / "lab_values.tsv"
    lab_values_file.write_text(
        "id\tdate\tvalue\n1\t2020-01-01\t10\n2\t2020-01-02\t20\n3\t2020-01-03\t30\n4\t2020-01-04\t40"
    )

    cohorts_file = tmp_path / "cohorts.tsv"
    cohorts_file.write_text("id\tmember_1\tmember_2\n1\t2\t3")

    with pytest.raises(
        ValueError, match="Individuals in lab values not found in cohorts"
    ):
        load_query_inputs(lab_values_file, cohorts_file)


def test_load_query_inputs_removes_time_information_from_dates(tmp_path):
    lab_values_file = tmp_path / "lab_values.tsv"
    lab_values_file.write_text(
        "id\tdate\tvalue\n1\t2020-01-01 12:34:56\t10\n2\t2020-01-02 23:45:01\t20\n3\t2020-01-03 00:00:00\t30"
    )

    cohorts_file = tmp_path / "cohorts.tsv"
    cohorts_file.write_text("id\tmember_1\tmember_2\n1\t2\t3")

    lab_values, _ = load_query_inputs(lab_values_file, cohorts_file)

    assert all(isinstance(d, date) for d in lab_values["date"])


def test_load_query_inputs_raises_error_for_invalid_date_format_in_lab_values(tmp_path):
    lab_values_file = tmp_path / "lab_values.tsv"
    lab_values_file.write_text(
        "id\tdate\tvalue\n1\t2020-01-01\t10\n2\tinvalid-date\t20"
    )

    cohorts_file = tmp_path / "cohorts.tsv"
    cohorts_file.write_text("id\tmember_1\tmember_2\n1\t2\t3")

    with pytest.raises(
        ValueError,
        match="Invalid date format in column",
    ):
        load_query_inputs(lab_values_file, cohorts_file)


@pytest.mark.parametrize(
    "lab_values_cols, id_col, date_col, value_col",
    [
        ("person_id\tdate\tvalue", "person_id", "date", "value"),
        ("id\tDATES\tvalue", "id", "DATES", "value"),
        ("id\tdate\tMeasure", "id", "date", "Measure"),
        ("ID\tDATE\tVALUE", "ID", "DATE", "VALUE"),
    ],
)
def test_load_query_inputs_accepts_custom_column_names(
    tmp_path,
    lab_values_cols,
    id_col,
    date_col,
    value_col,
):
    lab_values_file = tmp_path / "lab_values.tsv"
    lab_values_file.write_text(
        f"{lab_values_cols}\n1\t2020-01-01\t10\n2\t2020-01-02\t20\n3\t2020-01-03\t30"
    )

    cohorts_file = tmp_path / "cohorts.tsv"
    cohorts_file.write_text(f"{id_col}\tmember_1\tmember_2\n1\t2\t3")

    lab_values, cohorts = load_query_inputs(
        lab_values_file,
        cohorts_file,
        id_col=id_col,
        date_col=date_col,
        value_col=value_col,
    )

    assert list(lab_values.columns) == [id_col, date_col, value_col]
    assert list(cohorts.columns) == [id_col, "member_1", "member_2"]
    assert lab_values.shape == (3, 3)
    assert cohorts.shape == (1, 3)


def test_load_query_inputs_raises_error_for_invalid_custom_column_names(tmp_path):
    lab_values_file = tmp_path / "lab_values.tsv"
    lab_values_file.write_text("id\tdate\tvalue\n1\t2020-01-01\t10\n2\t2020-01-02\t20")

    cohorts_file = tmp_path / "cohorts.tsv"
    cohorts_file.write_text("id\tmember_1\tmember_2\n1\t2\t3")

    with pytest.raises(
        KeyError,
        match="Missing required columns in lab values",
    ):
        load_query_inputs(
            lab_values_file,
            cohorts_file,
            id_col="wrong_id",
            date_col="date",
            value_col="value",
        )


def test_load_query_inputs_raises_error_for_mismatched_id_column_names(tmp_path):
    lab_values_file = tmp_path / "lab_values.tsv"
    lab_values_file.write_text("id\tdate\tvalue\n1\t2020-01-01\t10\n2\t2020-01-02\t20")

    cohorts_file = tmp_path / "cohorts.tsv"
    cohorts_file.write_text("diff_id\tmember_1\tmember_2\n1\t2\t3")

    with pytest.raises(
        KeyError,
        match="Missing required columns in cohorts",
    ):
        load_query_inputs(lab_values_file, cohorts_file)


def test_load_query_inputs_recognizes_different_string_same_numeric_ids(tmp_path):
    lab_values_file = tmp_path / "lab_values.tsv"
    lab_values_file.write_text(
        "id\tdate\tvalue\n01\t2020-01-01\t10\n1\t2020-01-02\t20\n2\t2020-01-03\t30"
    )

    cohorts_file = tmp_path / "cohorts.tsv"
    cohorts_file.write_text("id\tmember_1\tmember_2\n01\t2\t1\n1\t01\t2")

    lab_values, cohorts = load_query_inputs(lab_values_file, cohorts_file)

    assert list(lab_values["id"]) == ["01", "1", "2"]
    assert list(cohorts["id"]) == ["01", "1"]


# endregion

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
    assert all(isinstance(peak, float) for peak in pers_peaks.values())


def test_get_pers_cohort_density_peaks_missing_person_in_lab_values():
    lab_values = pd.DataFrame(
        {"id": ["1", "2"], "date": ["2020-01-01", "2020-01-02"], "value": [10.0, 20.0]}
    )

    cohorts = pd.DataFrame(
        {
            "id": ["1"],
            "member_1": ["2"],
            "member_2": ["3"],
        }
    )

    with pytest.raises(ValueError, match="Missing lab values for person"):
        get_pers_cohort_density_peaks(lab_values, cohorts)


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
    assert all(isinstance(peak, float) for peak in pers_peaks.values())


def test_get_pers_cohort_density_peaks_person_in_own_cohort():
    lab_values = pd.DataFrame(
        {"id": ["1", "2"], "date": ["2020-01-01", "2020-01-02"], "value": [10.0, 20.0]}
    )

    cohorts = pd.DataFrame(
        {
            "id": ["1"],
            "member_1": ["1"],
            "member_2": ["2"],
        }
    )

    with pytest.raises(ValueError, match=r"Person '1' is in their own cohort\."):
        get_pers_cohort_density_peaks(lab_values, cohorts)


def test_get_pers_cohort_density_peaks_missing_cohort_member():
    lab_values = pd.DataFrame(
        {"id": ["1", "2"], "date": ["2020-01-01", "2020-01-02"], "value": [10.0, 20.0]}
    )

    cohorts = pd.DataFrame(
        {
            "id": ["1"],
            "member_1": ["2"],
            "member_2": [None],
        }
    )

    with pytest.raises(
        ValueError, match=r"Cohort members for person '1' contain missing values\."
    ):
        get_pers_cohort_density_peaks(lab_values, cohorts)


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
