"""Command-line interface for pers_cohort_query."""

from __future__ import annotations

import argparse
from pathlib import Path

from .integrate import compute_cohort_shifts, load_query_inputs


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="pers-cohort-query",
        description=(
            "Compute personalized-cohort density shifts from a lab values "
            "file and a cohort definitions file."
        ),
    )
    parser.add_argument(
        "-l",
        "--lab-values",
        type=Path,
        help="Path to the lab values CSV/TSV file",
        required=True,
    )
    parser.add_argument(
        "-c",
        "--cohorts",
        type=Path,
        help="Path to the cohorts CSV/TSV file",
        required=True,
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("data/output/cohort_shifts.csv"),
        help="Path to write the output CSV file (default: %(default)s)",
    )
    parser.add_argument(
        "--person-col",
        default="id",
        help="Name of the person-identifier column shared by both inputs (default: %(default)s)",
    )
    parser.add_argument(
        "--value-col",
        default="value",
        help="Name of the value column in the lab values file (default: %(default)s)",
    )
    parser.add_argument(
        "--date-col",
        default="date",
        help="Name of the date column in the lab values file (default: %(default)s)",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    """Run the CLI: load inputs, compute cohort shifts, and write the output CSV."""
    args = build_parser().parse_args(argv)

    lab_values, cohorts = load_query_inputs(
        args.lab_values, args.cohorts, date_col=args.date_col
    )
    shifts = compute_cohort_shifts(
        lab_values, cohorts, person_col=args.person_col, value_col=args.value_col
    )

    output_dir = Path(args.output).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    shifts.to_csv(Path(args.output), index=False)
    print(f"Wrote output to {args.output}")


if __name__ == "__main__":
    main()
