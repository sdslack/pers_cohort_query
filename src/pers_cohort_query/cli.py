from __future__ import annotations

import argparse
from pathlib import Path
from importlib.metadata import version

import pandas as pd

from .io import load_query_inputs
from .integrate import compute_cohort_shifts
from .summarize import summarize_shifts


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
        "-t",
        "--thresholds",
        type=Path,
        default=None,
        help=(
            "Path to a thresholds TSV file with a single row (columns: low "
            "and/or high) giving the standard reference range applied to "
            "everyone. If provided, also adds each person's warning status "
            "for each end as columns in the output, and writes "
            "measurement-level classifications to <output>_measurements.tsv."
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("data/output/cohort_shifts.tsv"),
        help="Path to write the output TSV file (default: %(default)s)",
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
    if args.thresholds is not None:
        paths["--thresholds"] = args.thresholds.resolve()
        measurements_output = args.output.with_name(
            f"{args.output.stem}_measurements{args.output.suffix}"
        )
        paths["measurements output"] = measurements_output.resolve()
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

    if args.thresholds is not None:
        thresholds = pd.read_csv(args.thresholds, sep="\t")
        shifts, classified = summarize_shifts(
            lab_values,
            thresholds,
            shifts,
            id_col=args.id_col,
            date_col=args.date_col,
            value_col=args.value_col,
        )
        classified.to_csv(measurements_output, sep="\t", index=False)
        print(f"Wrote measurement-level output to {measurements_output}")

    shifts.to_csv(Path(args.output), sep="\t", index=False)
    print(f"Wrote output to {args.output}")


if __name__ == "__main__":
    main()
