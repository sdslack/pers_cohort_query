# pers_cohort_query

**TO NOTE:** This tool is still under development.

This personalized cohort query tool dynamically creates genetically matched
cohorts for biobank participants and extracts laboratory values for each
individual and their cohort members. It then estimates the density peak of the
laboratory value distribution for both an individual's personalized cohort and
the entire biobank, and computes the shift between the two peaks. Finally, this
shift is summarized to characterize individual- and cohort-level shifts in
laboratory values relative to standard population-level reference ranges.

## Installation

### From Source

Clone the repository and install the package:

```bash
git clone git@github.com:sdslack/pers_cohort_query.git
cd pers_cohort_query
pip install .

```

**Note:** The repository includes an example in `examples/` that is used in
the example usage below: real genotypes from 1000 Genomes Phase 3 chr21 (2,504
unrelated samples), with lab values simulated at random. Shared inputs are in
`examples/input/` (the downloaded genotypes go in `examples/input/genetics/`),
and each cohort method has its own folder (`examples/pca/`,
`examples/genosis/`) used as `--output-dir`.

## Development

To contribute to the project or modify the source code, create the development
environment and install the package in editable mode:

1. Clone and enter this repo:

```bash
git clone git@github.com:sdslack/pers_cohort_query.git
cd pers_cohort_query

```

2. Create and activate the conda environment:

```bash
conda env create -f environment.yaml
conda activate pers_cohort_query

```

3. Install this package in development mode:

```bash
pip install -e ".[dev]"

```

4. Install precommit hooks:

```bash
pre-commit install

```

Small simulated test data is in  `tests/data/input/`. To regenerate:

```bash
python scripts/make_test_data.py

```


## Inputs/Outputs

### Stage 0: Extract Data

This stage is currently not implemented and must be run by hand. It includes
extraction and filtering of longitudinal lab measures, as well as getting the
genotype data or pre-computed genetic PCs for the individuals in the lab values
file.

### Stage 1: Build Cohorts

This is the first step if running the tool from start to finish. The tool
builds a genetically-matched cohort for every individual using one of two
methods: genetic PCA or
[GenoSiS](https://github.com/kristen-schneider/genosis).

It requires two input files:

1. a TSV file with lab values, in columns: `id`, `date`, `value` (or passed
with `id_col`, `date_col`, and `value_col`). Assumes that filtering of the lab
values has already been done.

+ Dates should be in ISO 8601 format (e.g., YYYY-MM-DD or YYYY-MM-DD HH:MM:SS).
+ There can be no missing values in any of the three columns.
+ An individual can have multiple lab values.
+ Lab values must be numeric, and any non-numeric values will raise an error.

2. genotype data for the individuals in the lab values file in VCF format.

+ If using genetic PCA, you can input a VCF (`--vcf`) or pre-computed genetic
    PCs (`--pcs`)
+ If using GenoSiS, this input VCF must include haplotype phasing information.

Note that the same set of individuals must be present in both input files with
the same ID format and column name as given with `id_col`.

This stage outputs a TSV file with personalized cohort definitions, where each
row is a cohort (see detailed description below in stage 2).

### Stage 2: Integrate Data

This step will automatically follow stage 1 if the whole tool is run. It can
also be run independently. It requires two input files:

1. the same TSV as described in stage 1

2. a TSV file with personalized cohort definitions, where each row is a
cohort. Column one should be called `id` (or passed with `id_col`), and is the
ID of an individual, and columns 2-(N+1) are that individual's personalized
cohort members, any column names are accepted.

+ All cohorts must contain the same number of individuals, and the number of
    members must be at least 2.
+ There can be no missing values in the input file.
+ This can be generated from GenoSiS or using PCA.
+ An individual cannot be in their own cohort, and each individual can only
    have one personalized cohort (no duplicates in the first column).

Note that the same set of individuals must be present in both input files with
the same ID format and column name as given with `id_col`, and the individual
ID in the first column of the cohorts file cannot be present in the rest of
that row (i.e., an individual cannot be in their own cohort).

This stage outputs a TSV file with two columns:

+ `id`: individual ID
+ `shift`: shift between the density peak of the lab values in the
    individual's personalized cohort and in the entire biobank

### **Stage 3: Summarize Thresholds**

*TODO: this to be added once implementation is updated beyond current*
*skeleton.*


## Example Usage

`examples/input/` includes simulated lab values `lab_values.tsv` and a
threshold range `thresholds.tsv`.

### PCA-based Cohorts

For PCA-based cohorts, genetic PCs `pcs.tsv` computed from the 1000 Genomes
genetic data are included at `examples/pca`.

All output files are written to `--output-dir` with fixed names (`shifts.tsv`,
plus the files described below).

#### Build from PCs

To build cohorts from genetic PCs with `--pcs`, give a TSV file with columns
`id` (or `id_col`) and `PC1`..`PCN`. Each individual's cohort is their
`--k-neighbors` (default 100) nearest neighbors by Euclidean distance over all
PC columns (or only `PC1`..`PC<n>` with `--n-pcs`).

```bash
pers-cohort-query \
    --lab-values examples/input/lab_values.tsv \
    --pcs examples/pca/pcs.tsv \
    --output-dir examples/pca

```

The built cohorts and the matching neighbor distances are written to
`--output-dir` as `cohorts.tsv` and `cohort_distances.tsv`, which are also
included for reference.

Optionally, add `--thresholds` with a TSV file containing a single standard/
population reference range (columns `low` and/or `high`) to also run the step
that summarizes the cohort shifts. If only one of `low`/`high` is given, only
that end is checked. Each person's personalized range (standard range minus
their shift) is used to calculate:

+ `low_status`, `high_status` (added to `shifts.tsv`): `normal` (flagged by
  neither threshold), `pers_early` (flagged by both, personalized first),
  `pers_only` (flagged only by personalized), `standard_only` (flagged only by
  standard), or `standard_same_or_early` (flagged by both, standard on the same
  date or earlier)
+ a measurement-level file, `measurements.tsv`, with each measurement's
  standard and personalized thresholds and a confusion matrix
  `conf_low`/`conf_high` label (`tp`, `fp`, `fn`, `tn`, treating the
  personalized threshold as ground truth)

*TO NOTE: thresholds not fully implemented in current tool version!*

```bash
pers-cohort-query \
    --lab-values examples/input/lab_values.tsv \
    --pcs examples/pca/pcs.tsv \
    --thresholds examples/input/thresholds.tsv \
    --output-dir examples/pca

```

#### Use Existing Cohorts

If cohorts are already defined, compute each individual's shift by passing them
with `--cohorts`. An example file `cohorts.tsv` is included at `examples/pca`.

```bash
pers-cohort-query \
    --lab-values examples/input/lab_values.tsv \
    --cohorts examples/pca/cohorts.tsv \
    --output-dir examples/pca

```

#### Build from Genetic Data

To start from genetic data, pass a VCF with `--vcf` instead. To build PCA-based
cohorts, add the `--method pca` flag. The tool computes `--n-pcs` (default 10)
genetic PCs using [PLINK2](https://www.cog-genomics.org/plink/2.0/) (current
implementation is simple PCA on biallelic SNPs with MAF >= 0.05 after LD
pruning), writes them as `pcs.tsv`, and then builds cohorts as if given
`--pcs`.

For the example, use the provided script to download the 1000 Genomes chr21
genetic data to `examples/input/genetics/` and regenerate
`examples/input/lab_values.tsv` and `examples/pca/pcs.tsv`:

```bash
bash scripts/make_example_1000g.sh

```

Then, run the tool:

```bash
pers-cohort-query \
    --vcf examples/input/genetics/ALL.chr21.phase3_shapeit2_mvncall_integrated_v5b.20130502.genotypes.vcf.gz \
    --method pca \
    --lab-values examples/input/lab_values.tsv \
    --output-dir examples/pca

```

`pcs.tsv`, `cohorts.tsv`, and `cohort_distances.tsv` are written to
`--output-dir` (this overwrites the provided `pcs.tsv` with the same PCs).

### GenoSiS-based Cohorts

*TO NOTE: this not implemented in current tool version!*

#### Build from Genetic Data

Pass a VCF with `--vcf` and add `--method genosis` to build cohorts with
GenoSiS from a phased VCF.

For the example, use the provided script to download the 1000 Genomes chr21
genetic data to `examples/input/genetics/` and regenerate
`examples/input/lab_values.tsv`:

```bash
bash scripts/make_example_1000g.sh

```

Then, run the tool:

```bash
pers-cohort-query \
    --vcf examples/input/genetics/ALL.chr21.phase3_shapeit2_mvncall_integrated_v5b.20130502.genotypes.vcf.gz \
    --method genosis \
    --lab-values examples/input/lab_values.tsv \
    --output-dir examples/genosis

```

`cohorts.tsv` and `cohort_distances.tsv` are written to `--output-dir`.
