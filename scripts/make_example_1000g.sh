#!/usr/bin/env bash

# Make the 1000 Genomes example: download Phase 3 chr21 genotypes and the
# sample panel to examples/input/genetics/ (git-ignored), then write lab values
# simulated for the same samples to examples/input/ and genetic PCs computed
# from the VCF to examples/pca/.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DATA_DIR="$REPO_ROOT/examples/input/genetics"
BASE_URL="https://ftp.1000genomes.ebi.ac.uk/vol1/ftp/release/20130502"
FILES=(
    "ALL.chr21.phase3_shapeit2_mvncall_integrated_v5b.20130502.genotypes.vcf.gz"
    "integrated_call_samples_v3.20130502.ALL.panel"
)

mkdir -p "$DATA_DIR"

for f in "${FILES[@]}"; do
    if [[ -f "$DATA_DIR/$f" ]]; then
        echo "Already downloaded: $f"
    else
        echo "Downloading: $f"
        curl -fsSL --retry 3 -o "$DATA_DIR/$f.part" "$BASE_URL/$f"
        mv "$DATA_DIR/$f.part" "$DATA_DIR/$f"
    fi
done

python "$SCRIPT_DIR/simulate_lab_values_1000g.py"

# Also save the PCs as an example input, so --pcs can be run without the VCF
python -c '
import sys
from pers_cohort_query.build import compute_pcs
compute_pcs(sys.argv[1]).to_csv(sys.argv[2], sep="\t", index=False)
' "$DATA_DIR/${FILES[0]}" "$REPO_ROOT/examples/pca/pcs.tsv"
