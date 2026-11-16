"""Simulate lab values for the 1000 Genomes example.

Called by scripts/make_example_1000g.sh.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from simulate_data import SEED, make_lab_values

PANEL_NAME = "integrated_call_samples_v3.20130502.ALL.panel"


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    panel_path = repo_root / "examples" / "input" / "genetics" / PANEL_NAME
    output_dir = repo_root / "examples" / "input"

    ids = pd.read_csv(panel_path, sep="\t", dtype={"sample": str})["sample"]

    rng = np.random.default_rng(SEED)
    lab_values = make_lab_values(ids.to_list(), rng)

    output_dir.mkdir(parents=True, exist_ok=True)
    lab_values.to_csv(output_dir / "lab_values.tsv", sep="\t", index=False)


if __name__ == "__main__":
    main()
