# pers_cohort_query

This personalized cohort query tool dynamically creates genetically matched
cohorts for biobank participants and extracts laboratory values for each
individual and their cohort members. It then estimates the density peak of the
laboratory value distribution for both an individual's personalized cohort and
the entire biobank, and computes the shift between the two peaks. Finally, this
shift is summarized to characterize individual- and cohort-level shifts in
laboratory values relative to standard population-level reference ranges.

**TO NOTE:** This tool is still under development and the current
implementation handles only the data integration stage.

## Input/Output (Data Integration Stage)

The first version of this tool handles only the data integration stage.
It requires two input files:

1. a CSV/TSV file with lab values, in columns: `id`, `date`, `value`. Assumes
that filtering of the lab values has already been done.

+ Dates should be in ISO 8601 format (e.g., YYYY-MM-DD or YYYY-MM-DD HH:MM:SS).
+ There can be no missing values in any of the three columns.

2. a CSV/TSV file with personalized cohort definitions, where each row is a
cohort. Column one should be called `id` and is the ID of an individual, and
columns 2-(N+1) are that individual's personalized cohort members, any column
names are accepted.

+ All cohorts must be the same size, and the number of members must be at
    least 2.
+ There can be no missing values in the input file.
+ This can be generated from GenoSiS or using PCA.

Note that the same set of individuals must be present in both input files, and
the individual ID in the first column of the cohorts file cannot be present in
the rest of that row (i.e., an individual cannot be in their own cohort).

It outputs a TSV file with two columns:

+ individual ID
+ persoanlized cohort shift in lab value relative to the population-level
    reference range

## Installation

### From Source

Clone the repository and install the package:

```bash
git clone git@github.com:sdslack/pers_cohort_query.git
cd pers_cohort_query
pip install .

```

**Note:** The repository includes example input files in `data/input/` that are
used in the example usage below.


## Example Usage

The repository includes example input files in `data/input/` and an example
output file in `data/output/`. To run the tool:

```bash
pers-cohort-query \
    --lab-values data/input/lab_values.csv \
    --cohorts data/input/cohorts.csv \
    --output data/output/cohort_shifts.tsv

```

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

## Development TODOs

+ Need to revisit how to handle longitudinal data
+ Likely want to revisit get_density_peak and save more than just peak - maybe
    object with peak, mean, stdev?
+ Need to add more tests? For example, for function like
    get_pers_cohort_density_peaks, do I need to test invalid date input, or
    okay to assume that and similar tests run upstream by other functions?
