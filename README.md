# genosis_aou

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

1. Open All of Us or local analysis environment.

2. Install pre-commit on system:

```bash
pip install pre-commit

```

3. Clone and enter this repo:

```bash
git clone git@github.com:sdslack/genosis_aou.git
cd genosis_aou

```

4. Install precommit to this repo:

```bash
pre-commit install

```


