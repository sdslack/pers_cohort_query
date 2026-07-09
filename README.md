# pers_cohort_query

The first version of the tool will handle the data integration stage.
It requires two input files:

1. a TSV file with lab values, in columns: id, value, date

*TODO: add more detail here.*
*TODO: can this be more general than "lab values"?*
*TODO: revisit what data file formats are best.*

2. a TSV file with personalized cohort definitions, where each row is a cohort,
so column 1 is the ID of an individual, and columns 2-101 are that individual's
personalized cohort.

+ This can be generated from GenoSiS or using PCA.

It outputs a TSV file with:

+ individual ID
+ personalized cohort lab value mean
+ personalized cohort lab value standard deviation

*TODO: how to handle longitudinal data?*

### Setup

1. Clone and enter this repo:

```bash
git clone git@github.com:sdslack/pers_cohort_query.git
cd pers-cohort-query

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
