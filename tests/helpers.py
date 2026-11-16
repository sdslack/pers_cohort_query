"""Shared test helpers."""

import shutil
from pathlib import Path

import numpy as np
import pytest

requires_plink2 = pytest.mark.skipif(
    shutil.which("plink2") is None, reason="PLINK2 is not installed"
)


def write_two_group_vcf(
    path: Path, ids: list[str], n_snps: int = 200, seed: int = 0
) -> np.ndarray:
    """Write a small phased VCF with two groups of allele frequenices."""
    rng = np.random.default_rng(seed)
    groups = (np.arange(len(ids)) >= len(ids) // 2).astype(int)

    lines = [
        "##fileformat=VCFv4.2",
        "##contig=<ID=1>",
        '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">',
        "\t".join(
            ["#CHROM", "POS", "ID", "REF", "ALT", "QUAL", "FILTER", "INFO", "FORMAT"]
            + ids
        ),
    ]
    for i in range(n_snps):
        freq0 = rng.uniform(0.2, 0.8)
        freqs = np.array([freq0, np.clip(freq0 + rng.choice([-0.4, 0.4]), 0.05, 0.95)])
        alleles = rng.random((len(ids), 2)) < freqs[groups][:, None]
        gts = [f"{a:d}|{b:d}" for a, b in alleles]
        lines.append(
            "\t".join(
                ["1", str((i + 1) * 10_000), ".", "A", "G", ".", "PASS", ".", "GT"]
            )
            + "\t"
            + "\t".join(gts)
        )

    path.write_text("\n".join(lines) + "\n")
    return groups
