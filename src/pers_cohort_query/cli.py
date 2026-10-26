from __future__ import annotations

import argparse
from pathlib import Path
from importlib.metadata import version

import pandas as pd

from .io import load_pcs, load_query_inputs
from .extract import build_pc_cohorts
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
    cohort_source = parser.add_mutually_exclusive_group(required=True)
    cohort_source.add_argument(
        "-c",
        "--cohorts",
        type=Path,
        help="Path to the cohorts CSV/TSV file",
    )
    cohort_source.add_argument(
        "-p",
        "--pcs",
        type=Path,
        help=(
            "Path to a genetic PCs TSV file (columns: id_col, PC1..PCN) to "
            "build PC-matched cohorts from, instead of passing --cohorts. "
            "Built cohorts and neighbor distances are written next to --output."
        ),
    )
    parser.add_argument(
        "-k",
        "--k-neighbors",
        type=int,
        default=100,
        help="Number of nearest neighbors per cohort with --pcs (default: %(default)s)",
    )
    parser.add_argument(
        "--n-pcs",
        type=int,
        default=None,
        help="Use only PC1..PC<n-pcs> with --pcs (default: all PC columns)",
    )
    parser.add_argument(
        "-t",
        "--thresholds",
        type=Path,
        default=None,
        help=(
            "Optional path to a thresholds TSV file with a single row"
            "(columns: low and/or high) giving the standard reference range."
            "If provided, summarizes shifts on person- and measurement-level."
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
        "--output": args.output.resolve(),
    }
    if args.pcs is not None:
        cohorts_path = args.output.with_name(
            f"{args.output.stem}_cohorts{args.output.suffix}"
        )
        distances_path = args.output.with_name(
            f"{args.output.stem}_cohort_distances{args.output.suffix}"
        )
        paths["--pcs"] = args.pcs.resolve()
        paths["cohorts output"] = cohorts_path.resolve()
        paths["cohort distances output"] = distances_path.resolve()
    else:
        cohorts_path = args.cohorts
        paths["--cohorts"] = args.cohorts.resolve()
    if args.thresholds is not None:
        paths["--thresholds"] = args.thresholds.resolve()
        measurements_output = args.output.with_name(
            f"{args.output.stem}_measurements{args.output.suffix}"
        )
        paths["measurements output"] = measurements_output.resolve()
    if len(set(paths.values())) != len(paths):
        raise ValueError("Multiple input paths can't point to the same file.")

    output_dir = Path(args.output).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.pcs is not None:
        pcs = load_pcs(args.pcs, id_col=args.id_col, n_pcs=args.n_pcs)
        built_cohorts, cohort_distances = build_pc_cohorts(
            pcs, args.k_neighbors, id_col=args.id_col, n_pcs=args.n_pcs
        )
        built_cohorts.to_csv(cohorts_path, sep="\t", index=False)
        cohort_distances.to_csv(distances_path, sep="\t", index=False)
        print(f"Wrote cohorts to {cohorts_path}")
        print(f"Wrote cohort distances to {distances_path}")

    lab_values, cohorts = load_query_inputs(
        args.lab_values,
        cohorts_path,
        id_col=args.id_col,
        date_col=args.date_col,
        value_col=args.value_col,
    )
    shifts = compute_cohort_shifts(
        lab_values, cohorts, id_col=args.id_col, value_col=args.value_col
    )

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
