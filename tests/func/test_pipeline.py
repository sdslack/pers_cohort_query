"""Basic functional (end-to-end) tests for pers_cohort_query.

These tests read the fixture files under tests/data/input and run the full
tool pipeline as if it were being run from the command line.
"""

from pathlib import Path

import pandas as pd
import pytest

from pers_cohort_query.cli import main
from pers_cohort_query.integrate import compute_cohort_shifts, load_query_inputs

INPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "input"

LAB_VALUES_PATH = INPUT_DIR / "lab_values_small.csv"
COHORTS_PATH = INPUT_DIR / "cohorts_small.csv"

EXPECTED_SHIFTS = {
    "S001": pytest.approx(-4.211079, abs=1e-4),
    "S002": pytest.approx(1.030917, abs=1e-4),
    "S003": pytest.approx(-0.309737, abs=1e-4),
    "S004": pytest.approx(3.692773, abs=1e-4),
    "S005": pytest.approx(-2.062041, abs=1e-4),
}


def test_pipeline_computes_expected_shifts_from_small_fixtures():
    lab_values, cohorts = load_query_inputs(LAB_VALUES_PATH, COHORTS_PATH)

    shifts = compute_cohort_shifts(lab_values, cohorts)

    assert list(shifts.columns) == ["id", "shift"]
    assert set(shifts["id"]) == set(EXPECTED_SHIFTS)
    for _, row in shifts.iterrows():
        assert row["shift"] == EXPECTED_SHIFTS[row["id"]]


def test_cli_writes_output_file_from_small_fixtures(tmp_path):
    output_path = tmp_path / "cohort_shifts_small.csv"

    main(
        [
            "--lab-values",
            str(LAB_VALUES_PATH),
            "--cohorts",
            str(COHORTS_PATH),
            "--output",
            str(output_path),
        ]
    )

    assert output_path.exists()
    written = pd.read_csv(output_path, dtype={"id": str})
    assert list(written.columns) == ["id", "shift"]
    assert set(written["id"]) == set(EXPECTED_SHIFTS)
    for _, row in written.iterrows():
        assert row["shift"] == EXPECTED_SHIFTS[row["id"]]
