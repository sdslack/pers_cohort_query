"""Functions to make simulated data inputs."""

from pathlib import Path
import numpy as np
import pandas as pd

SEED = 42


def make_ids(n_indv: int) -> list[str]:
    """
    Generate given number of sequential simulated IDs.
    """
    return [f"S{i:03d}" for i in range(1, n_indv + 1)]


def make_pers_cohorts(
    ids: list[str], cohort_size: int, rng: np.random.Generator
) -> pd.DataFrame:
    """
    Generate simulated cohorts for each ID.

    Each ID is assigned `cohort_size` cohort members sampled from the given list
    of IDs. The random number generator is passed for reproducible generation.
    """
    cohorts = []

    for id_ in ids:
        cohort = rng.choice(
            [i for i in ids if i != id_], size=cohort_size, replace=False
        )

        row = {"id": id_}
        for idx, member in enumerate(cohort):
            row[f"member_{idx + 1}"] = member

        cohorts.append(row)

    return pd.DataFrame(cohorts)


def make_lab_values(ids: list[str], rng: np.random.Generator) -> pd.DataFrame:
    """Generate simulated longitudinal lab values for each ID.

    Each person is assigned 3-10 measurements with simulated within-person and
    between-person variation. The random number generator is passed for
    reproducible generation.
    """
    lab_values = pd.DataFrame()

    # To simulate lab values with reasonable within-person and between-person
    # variation, first sample a baseline from a normal distribution for each
    # individual, then sample measurements from a normal distribution around
    # each individual's baseline
    for id_ in ids:
        baseline = rng.normal(loc=100, scale=10)
        n_measurements = rng.integers(3, 11)
        dates = pd.date_range(
            start="2010-01-01", end="2020-12-31", periods=n_measurements
        )

        measurements = pd.DataFrame(
            {
                "id": id_,
                "date": dates,
                "value": rng.normal(loc=baseline, scale=15, size=n_measurements),
            }
        )
        lab_values = pd.concat([lab_values, measurements], ignore_index=True)

    return lab_values


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    output_dir = repo_root / "examples" / "input"

    ids = make_ids(100)

    rng = np.random.default_rng(SEED)
    cohorts = make_pers_cohorts(ids, 10, rng)

    lab_values = make_lab_values(ids, rng)

    output_dir.mkdir(parents=True, exist_ok=True)
    cohorts.to_csv(output_dir / "cohorts.tsv", sep="\t", index=False)
    lab_values.to_csv(output_dir / "lab_values.tsv", sep="\t", index=False)


if __name__ == "__main__":
    main()
