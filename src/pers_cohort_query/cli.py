from __future__ import annotations

import argparse
from pathlib import Path
from importlib.metadata import version

import pandas as pd

from .build import (
    DEFAULT_N_PCS,
    build_genosis_cohorts,
    build_pc_cohorts,
    compute_pcs,
)
from .io import load_pcs, load_query_inputs, validate_pcs
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
            "Built cohorts and neighbor distances are written to --output-dir."
        ),
    )
    cohort_source.add_argument(
        "-g",
        "--vcf",
        type=Path,
        help=(
            "Path to a genotypes VCF file to build cohorts from with --method. "
            "With --method pca, the PCs are also written to --output-dir."
        ),
    )
    parser.add_argument(
        "-m",
        "--method",
        choices=["pca", "genosis"],
        default="pca",
        help=(
            "Method to build cohorts from --vcf: pca (compute genetic PCs with "
            "plink2, then match as with --pcs) or genosis (not implemented "
            "yet) (default: %(default)s)"
        ),
    )
    parser.add_argument(
        "-k",
        "--k-neighbors",
        type=int,
        default=100,
        help=(
            "Number of nearest neighbors per cohort with --pcs or --vcf "
            "(default: %(default)s)"
        ),
    )
    parser.add_argument(
        "--n-pcs",
        type=int,
        default=None,
        help=(
            "Use only PC1..PC<n-pcs> with --pcs (default: all PC columns), or "
            f"number of PCs to compute with --vcf (default: {DEFAULT_N_PCS})"
        ),
    )
    parser.add_argument(
        "-t",
        "--thresholds",
        type=Path,
        default=None,
        help=(
            "Optional path to a thresholds TSV file with a single row "
            "(columns: low and/or high) giving the standard reference range. "
            "If provided, summarizes shifts on person- and measurement-level."
        ),
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("data/output"),
        help=(
            "Directory to write output TSV files to: shifts.tsv, plus "
            "pcs.tsv (with --vcf and --method pca), cohorts.tsv and "
            "cohort_distances.tsv (with --pcs or --vcf), and measurements.tsv "
            "(with --thresholds). "
            "Existing files are overwritten (default: %(default)s)"
        ),
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
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.method == "genosis" and args.vcf is None:
        parser.error("--method genosis requires --vcf")

    output_dir = args.output_dir
    shifts_path = output_dir / "shifts.tsv"
    pcs_path = output_dir / "pcs.tsv"
    distances_path = output_dir / "cohort_distances.tsv"
    measurements_path = output_dir / "measurements.tsv"

    paths = {
        "--lab-values": args.lab_values.resolve(),
        "shifts output": shifts_path.resolve(),
    }
    if args.cohorts is None:
        cohorts_path = output_dir / "cohorts.tsv"
        paths["cohorts output"] = cohorts_path.resolve()
        paths["cohort distances output"] = distances_path.resolve()
        if args.pcs is not None:
            paths["--pcs"] = args.pcs.resolve()
        else:
            paths["--vcf"] = args.vcf.resolve()
            if args.method == "pca":
                paths["pcs output"] = pcs_path.resolve()
    else:
        cohorts_path = args.cohorts
        paths["--cohorts"] = args.cohorts.resolve()
    if args.thresholds is not None:
        paths["--thresholds"] = args.thresholds.resolve()
        paths["measurements output"] = measurements_path.resolve()
    if len(set(paths.values())) != len(paths):
        raise ValueError("Input and output paths can't point to the same file.")

    output_dir.mkdir(parents=True, exist_ok=True)

    if args.cohorts is None:
        if args.method == "genosis":
            built_cohorts, cohort_distances = build_genosis_cohorts(
                args.vcf, args.k_neighbors, id_col=args.id_col
            )
        else:
            if args.pcs is not None:
                pcs = load_pcs(args.pcs, id_col=args.id_col, n_pcs=args.n_pcs)
            else:
                pcs = compute_pcs(
                    args.vcf, args.n_pcs or DEFAULT_N_PCS, id_col=args.id_col
                )
                validate_pcs(pcs, id_col=args.id_col)
                pcs.to_csv(pcs_path, sep="\t", index=False)
                print(f"Wrote PCs to {pcs_path}")
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
        classified.to_csv(measurements_path, sep="\t", index=False)
        print(f"Wrote measurement-level output to {measurements_path}")

    shifts.to_csv(shifts_path, sep="\t", index=False)
    print(f"Wrote shifts to {shifts_path}")


if __name__ == "__main__":
    main()
