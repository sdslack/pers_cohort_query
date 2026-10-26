"""Unit tests for pers_cohort_query.extract module."""

import numpy as np
import pandas as pd
import pytest

from pers_cohort_query.extract import build_pc_cohorts
from pers_cohort_query.io import validate_cohorts


# region: tests for build_pc_cohorts


def make_line_pcs() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id": ["A", "B", "C", "D", "E"],
            "PC1": [0.0, 1.0, 3.0, 6.0, 10.0],
            "PC2": [0.0, 0.0, 0.0, 0.0, 0.0],
        }
    )


def test_build_pc_cohorts_returns_nearest_neighbors_and_distances():
    cohorts, distances = build_pc_cohorts(make_line_pcs(), 2)

    assert list(cohorts.columns) == ["id", "member_1", "member_2"]
    assert list(distances.columns) == ["id", "dist_1", "dist_2"]
    assert cohorts.to_dict("records") == [
        {"id": "A", "member_1": "B", "member_2": "C"},
        {"id": "B", "member_1": "A", "member_2": "C"},
        {"id": "C", "member_1": "B", "member_2": "A"},
        {"id": "D", "member_1": "C", "member_2": "E"},
        {"id": "E", "member_1": "D", "member_2": "C"},
    ]
    np.testing.assert_allclose(
        distances[["dist_1", "dist_2"]].to_numpy(),
        [[1, 3], [1, 2], [2, 3], [3, 4], [4, 7]],
    )


def test_build_pc_cohorts_output_passes_cohort_validation():
    rng = np.random.default_rng(0)
    pcs = pd.DataFrame(
        rng.normal(size=(50, 16)), columns=[f"PC{i}" for i in range(1, 17)]
    )
    pcs.insert(0, "id", [f"S{i:03d}" for i in range(50)])

    cohorts, _ = build_pc_cohorts(pcs, 10)

    validate_cohorts(cohorts)


def test_build_pc_cohorts_excludes_self_when_pcs_are_identical():
    pcs = pd.DataFrame(
        {
            "id": ["A", "B", "C", "D"],
            "PC1": [0.0, 0.0, 0.0, 5.0],
        }
    )

    cohorts, distances = build_pc_cohorts(pcs, 2)

    validate_cohorts(cohorts)
    np.testing.assert_allclose(distances.loc[:2, ["dist_1", "dist_2"]], 0)


def test_build_pc_cohorts_uses_only_first_n_pcs():
    pcs = make_line_pcs()
    pcs["PC2"] = [0.0, 100.0, 0.0, 0.0, 0.0]

    cohorts, _ = build_pc_cohorts(pcs, 2, n_pcs=1)

    assert cohorts.loc[0, ["member_1", "member_2"]].tolist() == ["B", "C"]


def test_build_pc_cohorts_accepts_custom_id_column():
    pcs = make_line_pcs().rename(columns={"id": "research_id"})

    cohorts, distances = build_pc_cohorts(pcs, 2, id_col="research_id")

    assert cohorts.columns[0] == "research_id"
    assert distances.columns[0] == "research_id"


@pytest.mark.parametrize("k_neighbors", [1, 5, 6])
def test_build_pc_cohorts_raises_error_for_invalid_k(k_neighbors):
    with pytest.raises(ValueError, match="`k_neighbors`"):
        build_pc_cohorts(make_line_pcs(), k_neighbors)


# endregion
