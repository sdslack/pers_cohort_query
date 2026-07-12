"""Functions to make test data

* make_ids - returns given number of IDs in a list
* make_pers_cohorts - returns dataframe with random cohort of the given
    size for each of the IDs in list, made with only the IDs in list
* make_lab_values - returns dataframe with random lab values, with 3-10
    measurements per person for each ID in list
* write_data - writes given dataframe to specified output directory

"""

from pathlib import Path
import numpy as np
import pandas as pd

SEED = 42


def make_ids(n_indv: int) -> list[str]:
    """
    Returns given number of IDs as a list.

    Parameters
    ----------
    n_indv : int
        Number of individuals to generate IDs for

    Returns
    -------
    ids : list
        String list of generated sequential IDs
    """
    return [f"S{i:03d}" for i in range(1, n_indv + 1)]


def make_pers_cohorts(
    ids: list[str], cohort_size: int, rng: np.random.Generator
) -> pd.DataFrame:
    """
    Returns dataframe with random cohort of the given size for each of the IDs
    in list, made with only the IDs in list. First column is "id" for an
    individual, and all remaining "member_#" columns in that row are their
    cohort members.

    Parameters
    ----------
    ids : list[str]
        IDs to generate cohorts for and to use in cohorts
    cohort_size: int
        Size of cohorts to generate
    rng : np.random.Generator
        Random number generator to use for reproducibility

    Returns
    -------
    cohorts : pd.DataFrame
        DataFrame with generated cohorts
    """
    cohorts = []

    for id_ in ids:
        cohort = rng.choice(ids, size=cohort_size, replace=False)

        row = {"id": id_}
        for idx, member in enumerate(cohort):
            row[f"member_{idx + 1}"] = member

        cohorts.append(row)

    return pd.DataFrame(cohorts)


def make_lab_values(ids: list[str], rng: np.random.Generator) -> pd.DataFrame:
    """
    Returns dataframe with random lab values and dates between 2010-2020,
    with 3-10 measurements per person for each ID in list. Columns are "id",
    "date", and "value".

    Parameters
    ----------
    ids : list[str]
        IDs to generate lab values for
    rng : np.random.Generator
        Random number generator to use for reproducibility

    Returns
    -------
    lab_values : pd.DataFrame
        DataFrame with generated lab values and dates between 2010-2020
    """
    lab_values = pd.DataFrame()

    # Generate measurements by first sampling a baseline from a normal
    # distribution for each individual, then sample measurements from a normal
    # distribution around each individual's baseline
    for id_ in ids:
        baseline = rng.normal(loc=100, scale=10)
        n_measurements = rng.integers(3, 11)
        # Evenly spaced dates between 2010 and 2020 by number of measurements
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


def write_data(df: pd.DataFrame, output_path: Path) -> None:
    """
    Writes given DataFrame to the specified output path

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame to write to CSV
    output_path : Path
        Path to write the generated data to
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)


def main() -> None:
    repo_root = Path(__file__).resolve().parent
    output_dir = repo_root / "test" / "data" / "input"

    # Make IDs for all individuals in the test data
    ids = make_ids(100)

    # Make personalized cohorts for each individual in the test data, using
    # the generated IDs, with given cohort size
    rng = np.random.default_rng(SEED)
    cohorts = make_pers_cohorts(ids, 10, rng)

    # Make the lab values for each individual in the test data, using the
    # generated IDs
    lab_values = make_lab_values(ids, rng)

    # Write out test data
    write_data(cohorts, output_dir / "cohorts.csv")
    write_data(lab_values, output_dir / "lab_values.csv")


if __name__ == "__main__":
    main()
