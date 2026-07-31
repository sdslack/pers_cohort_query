from __future__ import annotations

import argparse
from pathlib import Path
from importlib.metadata import version

from .integrate import compute_cohort_shifts, load_query_inputs


def build_parser() -> argparse.ArgumentParser:
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
        "--id-col",
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
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=version("pers-cohort-query"),
        help="Show the version of pers-cohort-query and exit",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)

    paths = {
        "--lab-values": args.lab_values.resolve(),
        "--cohorts": args.cohorts.resolve(),
        "--output": args.output.resolve(),
    }
    if len(set(paths.values())) != len(paths):
        raise ValueError("Multiple input paths can't point to the same file.")

    lab_values, cohorts = load_query_inputs(
        args.lab_values,
        args.cohorts,
        id_col=args.id_col,
        date_col=args.date_col,
        value_col=args.value_col,
    )
    shifts = compute_cohort_shifts(
        lab_values, cohorts, id_col=args.id_col, value_col=args.value_col
    )

    output_dir = Path(args.output).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    shifts.to_csv(Path(args.output), sep="\t", index=False)
    print(f"Wrote output to {args.output}")


if __name__ == "__main__":
    main()
