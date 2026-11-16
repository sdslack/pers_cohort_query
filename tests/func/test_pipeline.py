"""Basic functional (end-to-end) tests for pers_cohort_query.

These tests read the fixture files under tests/data/input and run the full
tool pipeline as if it were being run from the command line.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pers_cohort_query.cli import main
from pers_cohort_query.io import load_query_inputs
from pers_cohort_query.integrate import compute_cohort_shifts
from helpers import requires_plink2, write_two_group_vcf

INPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "input"

LAB_VALUES_PATH = INPUT_DIR / "lab_values_small.tsv"
COHORTS_PATH = INPUT_DIR / "cohorts_small.tsv"
THRESHOLDS_PATH = INPUT_DIR / "thresholds_small.tsv"
PCS_PATH = INPUT_DIR / "pcs_small.tsv"

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
    output_path = tmp_path / "shifts.tsv"

    main(
        [
            "--lab-values",
            str(LAB_VALUES_PATH),
            "--cohorts",
            str(COHORTS_PATH),
            "--output-dir",
            str(tmp_path),
        ]
    )

    assert output_path.exists()
    written = pd.read_csv(output_path, sep="\t", dtype={"id": str})
    assert list(written.columns) == ["id", "shift"]
    assert set(written["id"]) == set(EXPECTED_SHIFTS)
    for _, row in written.iterrows():
        assert row["shift"] == EXPECTED_SHIFTS[row["id"]]


def test_cli_adds_summary_columns_with_thresholds(tmp_path):
    output_path = tmp_path / "shifts.tsv"

    main(
        [
            "--lab-values",
            str(LAB_VALUES_PATH),
            "--cohorts",
            str(COHORTS_PATH),
            "--thresholds",
            str(THRESHOLDS_PATH),
            "--output-dir",
            str(tmp_path),
        ]
    )

    written = pd.read_csv(output_path, sep="\t", dtype={"id": str})
    assert list(written.columns) == ["id", "shift", "low_status", "high_status"]
    assert set(written["id"]) == set(EXPECTED_SHIFTS)
    assert len(written) == len(EXPECTED_SHIFTS)

    measurements_path = tmp_path / "measurements.tsv"
    measurements = pd.read_csv(measurements_path, sep="\t", dtype={"id": str})
    # Only measurements for people with a shift (not cohort members) are kept.
    lab_values = pd.read_csv(LAB_VALUES_PATH, sep="\t", dtype={"id": str})
    assert len(measurements) == lab_values["id"].isin(EXPECTED_SHIFTS).sum()
    assert {"low", "pers_low", "conf_low", "high", "pers_high", "conf_high"} <= set(
        measurements.columns
    )


def test_cli_builds_cohorts_from_pcs(tmp_path):
    lab_values = pd.read_csv(LAB_VALUES_PATH, sep="\t", dtype={"id": str})
    ids = sorted(lab_values["id"].unique())
    output_path = tmp_path / "shifts.tsv"

    main(
        [
            "--lab-values",
            str(LAB_VALUES_PATH),
            "--pcs",
            str(PCS_PATH),
            "--k-neighbors",
            "4",
            "--output-dir",
            str(tmp_path),
        ]
    )

    cohorts = pd.read_csv(tmp_path / "cohorts.tsv", sep="\t", dtype=str)
    distances = pd.read_csv(tmp_path / "cohort_distances.tsv", sep="\t")
    assert cohorts.shape == (len(ids), 5)
    assert distances.shape == (len(ids), 5)
    written = pd.read_csv(output_path, sep="\t", dtype={"id": str})
    assert set(written["id"]) == set(ids)


@requires_plink2
def test_cli_builds_cohorts_from_vcf(tmp_path):
    # plink2 LD pruning needs at least 50 samples
    ids = [f"S{i:02d}" for i in range(60)]
    vcf_path = tmp_path / "genotypes.vcf"
    write_two_group_vcf(vcf_path, ids)
    lab_values_path = tmp_path / "lab_values.tsv"
    pd.DataFrame(
        {
            "id": np.repeat(ids, 3),
            "date": np.tile(["2020-01-01", "2021-01-01", "2022-01-01"], len(ids)),
            "value": np.random.default_rng(0).normal(100, 10, 3 * len(ids)),
        }
    ).to_csv(lab_values_path, sep="\t", index=False)
    output_path = tmp_path / "shifts.tsv"

    main(
        [
            "--lab-values",
            str(lab_values_path),
            "--vcf",
            str(vcf_path),
            "--n-pcs",
            "3",
            "--k-neighbors",
            "4",
            "--output-dir",
            str(tmp_path),
        ]
    )

    pcs = pd.read_csv(tmp_path / "pcs.tsv", sep="\t", dtype={"id": str})
    assert list(pcs.columns) == ["id", "PC1", "PC2", "PC3"]
    assert set(pcs["id"]) == set(ids)
    cohorts = pd.read_csv(tmp_path / "cohorts.tsv", sep="\t", dtype=str)
    assert cohorts.shape == (len(ids), 5)
    written = pd.read_csv(output_path, sep="\t", dtype={"id": str})
    assert set(written["id"]) == set(ids)


def test_cli_rejects_both_cohorts_and_pcs(tmp_path):
    with pytest.raises(SystemExit):
        main(
            [
                "--lab-values",
                str(LAB_VALUES_PATH),
                "--cohorts",
                str(COHORTS_PATH),
                "--pcs",
                str(tmp_path / "pcs.tsv"),
            ]
        )


def test_cli_rejects_input_that_output_would_overwrite(tmp_path):
    thresholds_path = tmp_path / "measurements.tsv"
    thresholds_path.write_text(THRESHOLDS_PATH.read_text())

    with pytest.raises(ValueError, match="same file"):
        main(
            [
                "--lab-values",
                str(LAB_VALUES_PATH),
                "--cohorts",
                str(COHORTS_PATH),
                "--thresholds",
                str(thresholds_path),
                "--output-dir",
                str(tmp_path),
            ]
        )


def test_cli_rejects_genosis_without_vcf(tmp_path):
    with pytest.raises(SystemExit):
        main(
            [
                "--lab-values",
                str(LAB_VALUES_PATH),
                "--pcs",
                str(PCS_PATH),
                "--method",
                "genosis",
                "--output-dir",
                str(tmp_path),
            ]
        )


def test_cli_genosis_not_implemented_yet(tmp_path):
    with pytest.raises(NotImplementedError):
        main(
            [
                "--lab-values",
                str(LAB_VALUES_PATH),
                "--vcf",
                str(tmp_path / "genotypes.vcf"),
                "--method",
                "genosis",
                "--output-dir",
                str(tmp_path),
            ]
        )
