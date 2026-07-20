# pers_cohort_query

The first version of this tool handles only the data integration stage.
It requires two input files:

1. a CSV/TSV file with lab values, in columns: `id`, `date`, `value`. Assumes that 
filtering of the lab values has already been done.

+ Dates should be in ISO 8601 format (e.g., YYYY-MM-DD or YYYY-MM-DD HH:MM:SS).
+ There can be no missing values in any of the three columns.

2. a CSV/TSV file with personalized cohort definitions, where each row is a cohort.
Column one should be called `id` and is the ID of an individual, and columns
2-(N+1) are that individual's personalized cohort members, any column names are
accepted.

+ All cohorts must be the same size, and the number of members must be at least 2.
+ There can be no missing values in the input file.
+ This can be generated from GenoSiS or using PCA.

It outputs a TSV file with:

+ individual ID
+ personalized cohort lab value mean
+ personalized cohort lab value standard deviation

### Setup

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

### Development TODOs

+ Need to revisit how to handle longitudinal data
+ Likely want to revisit get_density_peak and save more than just peak - maybe
    object with peak, mean, stdev?
+ Do I need to add more tests? For example, for function like
    get_pers_cohort_density_peaks, so I need to test invalid date input, or
    okay to assume that and similar tests run upstream by other functions?
