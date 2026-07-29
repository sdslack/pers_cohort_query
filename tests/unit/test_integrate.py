"""Unit tests for pers_cohort_query.integrate module."""

from datetime import date

from pers_cohort_query.integrate import (
    get_density_peak,
    load_tabular_data,
    load_query_inputs,
    get_all_density_peak,
    get_pers_cohort_density_peaks,
    compute_cohort_shifts,
)
import pandas as pd
import pytest

# region: tests for load_tabular_data


@pytest.mark.parametrize(
    "suffix, sep",
    [
        (".csv", ","),
        (".tsv", "\t"),
    ],
)
def test_load_tabular_data_reads_delimited_files(tmp_path, suffix, sep):
    file = tmp_path / f"test{suffix}"
    file.write_text(f"col1{sep}col2\n1{sep}2020-01-01\n2{sep}2020-01-02")

    df = load_tabular_data(file, parse_dates=["col2"])

    assert df.shape == (2, 2)
    assert list(df["col1"]) == [1, 2]
    assert list(df["col2"]) == [
        date(2020, 1, 1),
        date(2020, 1, 2),
    ]


def test_load_tabular_data_raises_error_for_invalid_file(tmp_path):
    file = tmp_path / "test.invalid"
    file.write_text("col1,col2\n1,2020-01-01\n2,2020-01-02")

    with pytest.raises(ValueError) as exc_info:
        load_tabular_data(file)

    assert "Unsupported file type" in str(exc_info.value)


def test_load_tabular_data_raises_error_for_nonexistent_file():
    with pytest.raises(FileNotFoundError):
        load_tabular_data("nonexistent_file.csv")


def test_load_tabular_data_raises_error_for_invalid_date_column(tmp_path):
    file = tmp_path / "test.csv"
    file.write_text("col1,col2\n1,2020-01-01\n2,2020-01-02")
    with pytest.raises(ValueError) as exc_info:
        load_tabular_data(file, parse_dates=["nonexistent_col"])
    assert "Missing column provided to 'parse_dates'" in str(exc_info.value)


@pytest.mark.parametrize(
    "invalid_date",
    [
        "invalid-date",
        "20200-01-02",
        "2020-13-01",
        "2020-01-35",
    ],
)
def test_load_tabular_data_raises_error_for_invalid_date_format(tmp_path, invalid_date):
    file = tmp_path / "test.csv"
    file.write_text(f"col1,col2\n1,2020-01-01\n2,{invalid_date}")

    with pytest.raises(ValueError):
        load_tabular_data(file, parse_dates=["col2"])


def test_load_tabular_data_handles_date_and_datetime_formats(tmp_path):
    file = tmp_path / "test.csv"
    file.write_text("col1,col2\n1,2020-01-01\n2,2020-01-02 12:34:56")

    df = load_tabular_data(file, parse_dates=["col2"])

    assert list(df["col2"]) == [
        date(2020, 1, 1),
        date(2020, 1, 2),
    ]


def test_load_tabular_data_raises_error_for_empty_file(tmp_path):
    file = tmp_path / "test.csv"
    file.write_text("")

    with pytest.raises(pd.errors.EmptyDataError):
        load_tabular_data(file)


# endregion


# region: tests for load_query_inputs
def test_load_query_inputs_loads_both_files(tmp_path):
    lab_values_file = tmp_path / "lab_values.csv"
    lab_values_file.write_text(
        "id,date,value\n1,2020-01-01,10\n2,2020-01-02,20\n3,2020-01-03,30\n4,2020-01-04,40"
    )

    cohorts_file = tmp_path / "cohorts.csv"
    cohorts_file.write_text("id,member_1,member_2\n1,2,3\n2,3,4")

    lab_values, cohorts = load_query_inputs(lab_values_file, cohorts_file)

    assert lab_values.shape == (4, 3)
    assert cohorts.shape == (2, 3)


def test_load_query_inputs_raises_error_if_error_in_lab_values(tmp_path):
    lab_values_file = tmp_path / "lab_values.csv"
    lab_values_file.write_text("id,date,wrong_name\n1,2020-01-01,10\n2,2020-01-02,20")

    cohorts_file = tmp_path / "cohorts.csv"
    cohorts_file.write_text("id,member_1,member_2\n1,2,3\n2,3,4")

    with pytest.raises(KeyError) as exc_info:
        load_query_inputs(lab_values_file, cohorts_file)
    assert "Missing required columns in lab values" in str(exc_info.value)


def test_load_query_inputs_raises_error_if_error_in_cohorts(tmp_path):
    lab_values_file = tmp_path / "lab_values.csv"
    lab_values_file.write_text("id,date,value\n1,2020-01-01,10\n2,2020-01-02,20")

    cohorts_file = tmp_path / "cohorts.csv"
    cohorts_file.write_text("wrong_name,member_1,member_2\n1,2,3\n2,3,1")

    with pytest.raises(KeyError) as exc_info:
        load_query_inputs(lab_values_file, cohorts_file)
    assert "Missing required columns in cohorts" in str(exc_info.value)


def test_load_query_inputs_raises_error_for_too_few_cohort_columns(tmp_path):
    lab_values_file = tmp_path / "lab_values.csv"
    lab_values_file.write_text("id,date,value\n1,2020-01-01,10\n2,2020-01-02,20")

    cohorts_file = tmp_path / "cohorts.csv"
    cohorts_file.write_text("id,member_1\n1,2\n2,3")

    with pytest.raises(ValueError, match="at least three columns"):
        load_query_inputs(lab_values_file, cohorts_file)


def test_load_query_inputs_raises_error_for_missing_lab_values(tmp_path):
    lab_values_file = tmp_path / "lab_values.csv"
    lab_values_file.write_text("id,date,value\n1,2020-01-01,10\n2,2020-01-02,")

    cohorts_file = tmp_path / "cohorts.csv"
    cohorts_file.write_text("id,member_1,member_2\n1,2,3\n2,3,4")

    with pytest.raises(ValueError, match="Lab values contain missing values"):
        load_query_inputs(lab_values_file, cohorts_file)


def test_load_query_inputs_raises_error_for_missing_cohort_values(tmp_path):
    lab_values_file = tmp_path / "lab_values.csv"
    lab_values_file.write_text("id,date,value\n1,2020-01-01,10\n2,2020-01-02,20")

    cohorts_file = tmp_path / "cohorts.csv"
    cohorts_file.write_text("id,member_1,member_2\n1,2,\n2,3,4")

    with pytest.raises(ValueError, match="Cohorts contain missing values"):
        load_query_inputs(lab_values_file, cohorts_file)


def test_load_query_inputs_raises_error_for_ids_in_cohorts_not_in_lab_values(tmp_path):
    lab_values_file = tmp_path / "lab_values.csv"
    lab_values_file.write_text("id,date,value\n1,2020-01-01,10\n2,2020-01-02,20")

    cohorts_file = tmp_path / "cohorts.csv"
    cohorts_file.write_text("id,member_1,member_2\n1,2,3\n3,4,5")

    with pytest.raises(
        ValueError, match="Individuals in cohorts not found in lab values"
    ):
        load_query_inputs(lab_values_file, cohorts_file)


def test_load_query_inputs_raises_error_for_ids_in_lab_values_not_in_cohorts(tmp_path):
    lab_values_file = tmp_path / "lab_values.csv"
    lab_values_file.write_text(
        "id,date,value\n1,2020-01-01,10\n2,2020-01-02,20\n3,2020-01-03,30\n4,2020-01-04,40"
    )

    cohorts_file = tmp_path / "cohorts.csv"
    cohorts_file.write_text("id,member_1,member_2\n1,2,3")

    with pytest.raises(
        ValueError, match="Individuals in lab values not found in cohorts"
    ):
        load_query_inputs(lab_values_file, cohorts_file)


def test_load_query_inputs_raises_error_for_cohort_id_column_not_first(tmp_path):
    lab_values_file = tmp_path / "lab_values.csv"
    lab_values_file.write_text(
        "id,date,value\n1,2020-01-01,10\n2,2020-01-02,20\n3,2020-01-03,30\n4,2020-01-04,40"
    )

    cohorts_file = tmp_path / "cohorts.csv"
    cohorts_file.write_text("member_1,id,member_2,member_3\n2,1,3,4")

    with pytest.raises(
        ValueError, match="The first column of the cohorts file must be 'id'"
    ) as exc_info:
        load_query_inputs(lab_values_file, cohorts_file)

    print(str(exc_info.value))


# endregion

# region: tests for get_density_peak


def test_get_density_peak_multiple_values():
    values = [1.0, 2.0, 2.0, 3.0]
    peak = get_density_peak(values)
    assert peak == pytest.approx(2.0, abs=0.1)  # peak around 2.0 for KDE implementation


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


def test_get_all_density_peak_missing_values_col_raises():
    lab_values = pd.DataFrame(
        {
            "id": ["1", "1", "2", "3"],
            "date": ["2020-01-01", "2020-01-02", "2020-01-03", "2020-01-04"],
            # missing 'value' column
        }
    )

    with pytest.raises(KeyError):
        get_all_density_peak(lab_values)


# endregion

# region: tests for get_personalized_cohort_density_peaks


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
            "member_2": ["3"],  # person 3 is missing lab values
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


def test_get_pers_cohort_density_peaks_empty_cohorts():
    lab_values = pd.DataFrame(
        {"id": ["1", "2"], "date": ["2020-01-01", "2020-01-02"], "value": [10.0, 20.0]}
    )

    cohorts = pd.DataFrame(columns=["id", "member_1", "member_2"])

    # Assert raises value error
    with pytest.raises(ValueError, match=r"Cohorts file must have at least one row\."):
        get_pers_cohort_density_peaks(lab_values, cohorts)


def test_get_pers_cohort_density_peaks_person_in_own_cohort():
    lab_values = pd.DataFrame(
        {"id": ["1", "2"], "date": ["2020-01-01", "2020-01-02"], "value": [10.0, 20.0]}
    )

    cohorts = pd.DataFrame(
        {
            "id": ["1"],
            "member_1": ["1"],  # person 1 is in their own cohort
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
            "member_2": [None],  # missing cohort member
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
