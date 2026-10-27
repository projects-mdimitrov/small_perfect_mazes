# Crossed maze experiment data and code

This is a self-contained research-data and code package for the crossed maze
experiment on 10 by 10 and 20 by 20 grids. It contains the input digit files,
original generation implementation and runner, frozen attempt-level data,
numeric analysis code, reference results and validation records. The package
does not contain a research article, a Word template or an editorial document.
Neither an article nor a DOI is needed to run its scientific checks.

The experiment compares fourteen selectable generator variants under matched
decimal windows from eleven known irrational constants and seeded pseudorandom
control corpora. It measures completion, digit-block consumption and maze
structure. Larger-grid experiments and earlier unrelated experiments are not
included.

## Start here

The canonical raw data are in
`article_all_algorithms_v1/data/crossed_v1/runs.csv`. Each row is one generation
attempt, not an algorithm average. Read `docs/DATA_DICTIONARY.md` for column
definitions, units and population filters, and `docs/RESULTS_GUIDE.md` for the
current estimators and their result files.

| Location | Contents |
|---|---|
| `maze_analytics_lab-15.html` | Frozen maze generators, decimal decoder, pseudorandom generator and graph metrics. |
| `irrational_numbers/` | Twelve original decimal input files required by the frozen runner. |
| `control_corpora/` | Saved exact control sequences: 64 records for 10x10 and the shared first 16 for 20x20, with hashes and verification records. |
| `article_all_algorithms_v1/run_crossed_study.js` | Original batch-generation runner. |
| `article_all_algorithms_v1/protocol.md` | Unchanged pre-run protocol; later analysis definitions are explained in the results guide. |
| `article_all_algorithms_v1/data/crossed_v1/` | Original `runs.csv`, generation manifest and independent graph-audit results. |
| `article_all_algorithms_v1/revision_v12/` | Baseline numeric analysis, reference tables and numerical diagnostics. |
| `article_all_algorithms_v1/revision_v18/` | All-completed-run secondary-series variability analysis. |
| `article_all_algorithms_v1/revision_v21/` | Irrational/control comparisons at both sizes, including completed-cell-balanced partitions. |
| `analysis/minmax_plots.py` | Numeric-only helpers for completed-run quartiles and observed-extrema boxplots. |
| `reference_results/current_reanalysis/` | Current all-variant source means, cell deviations and minimum–maximum summaries. |
| `reference_results/minmax_boxplots/config.json` | Numeric boxplot configuration and reference summaries, without document inputs. |
| `provenance/code_adaptations.json` | Origin and scope of the packaging adaptations to the analysis code. |
| `provenance/scientific_validation/` | Scientific replay, audit and numerical-regression records; start with `validation.json`. |
| `SHA256SUMS.json` | Package file-integrity inventory. |
| `package_manifest.json` | Package scope, copy provenance and data counts. |

Revision directory names identify analysis-code provenance. They do not mean
that the package contains several different experiments. The original maze
generation code and observations remain frozen. Analysis adaptations remove
editorial dependencies and make the numerical workflow independent of Word;
their exact scope is recorded in `provenance/code_adaptations.json`.

## Requirements

The original experiment used Node.js v24.19.0. Generation requires only Node
built-ins, not npm packages, a browser or a web server. Scientific analysis uses
Python 3.12 and these recorded direct dependencies:

```text
numpy==2.3.5
pandas==3.0.1
Pillow==12.3.0
```

Install the Python dependencies with:

```text
python -m pip install -r requirements-lock.txt
```

Dependency installation may require Internet access. The experiment and
analysis themselves use local package files and make no network requests.
Word, `python-docx`, a document renderer and a DOI are not required. Plot font
availability can affect visual appearance, not the numerical results; the
analysis uses an Arial/DejaVu font fallback.

## Verify and reproduce

Run commands from the package root:

```text
python -B -X utf8 reproduce.py verify
python -B -X utf8 reproduce.py self-test
python -B -X utf8 reproduce.py regenerate
python -B -X utf8 reproduce.py audit
python -B -X utf8 reproduce.py analyse
node tools/export_control_corpora.js --verify
```

- `verify` checks the packaged file hashes and frozen experiment inputs. It
  needs only Python's standard library.
- `self-test` checks all fourteen generator variants on a deterministic
  10 by 10 test case.
- `regenerate` executes the complete original design in an isolated working
  copy and checks whether the regenerated CSV is byte-identical to the frozen
  original. The new generation manifest's timestamp is expected to differ.
- `audit` independently decodes saved completed maze graphs and checks the
  generation design and the four original foreground metrics.
- `analyse` recomputes numerical summaries, current source margins, variability
  partitions, irrational/control comparisons, cell deviations and scientific
  plots, and compares the results with the numeric references.

The entry point checks frozen files before and after each task. Tasks that
write results create a new directory under `reproduced/`. An existing output
directory is never overwritten. To choose another new location or an explicit
Node executable:

```text
python -B -X utf8 reproduce.py analyse --out "new_analysis_run"
python -B -X utf8 reproduce.py regenerate --node "C:/path/to/node.exe" --out "new_generation_run"
```

Do not run the frozen runner's `--run` directly in the archive: it intentionally
refuses its existing data directory. Use the entry point above. New test
outputs are not replacements for the frozen references. The scientific
validation report records which checks were performed; a hash match alone
does not validate a scientific interpretation.

## Populations and interpretation

The original CSV contains 40,320 attempts: 7,392 known-irrational, 32,256
control and 672 ancillary attempts. The current irrational/control analysis
uses the first two groups, totalling 39,648 attempts. The ancillary rows and
twelfth digit file are retained to preserve the frozen archive and permit
exact replay; they do not enter the current comparisons. No raw row has been
deleted.

Controls are reconstructed deterministically from the `corpus_seed` values in
the raw CSV and the included generator. Exact sequence backups are also saved
in `control_corpora/control_10x10.jsonl` and `control_20x20.jsonl`; see
`docs/CONTROL_CORPORA.md` for their format. Each record stores 960,000 digits
as text, preserving leading zeroes. These are the original controls, not a
new random draw. The 10 by 10 series uses 64 seeded corpora; the 20 by 20
series uses the first 16 of those same corpora. Both size series reuse the
same digits under different window partitions and are not independent samples.
The original maze runner still regenerates controls from seeds; saving these
backup files does not change the experiment or the numeric results.

Topology summaries condition on completion. Exhausted attempts remain in
completion-rate and resource-consumption denominators. Cross-variant
family-balanced aggregates give each Binary Tree orientation weight 1/4 and
each other variant weight 1; actual attempt counts and individual-variant
boxplots are not reweighted in this way.

Some baseline secondary reference tables retain the twelve-variant complete
panel, excluding Wilson and Aldous–Broder. They are not the current all-variant
secondary comparisons. Current results include the available completed runs
of both random-walk algorithms. The results guide identifies these files.

The zeta(3) input has 980,380 digits despite its filename; do not pad it. Do not
add a BOM or line endings, change decimal files, or re-save the raw CSV.
SHA-256 establishes byte identity, not mathematical correctness of the digits.
Any retained historical digit-validation reports have the limited scope they
state. This package does not establish digit normality, a general property of
irrational numbers or scientific novelty by itself.

## Release and rights

The data/code package can be checked and deposited independently of a later
article. An article can cite the DOI of a specific published package version
without becoming an input to the scientific analysis. Adding a citation or
changing article formatting does not require changing these data.

No new licence is assigned here. Before public deposit, decide the licence
for the investigator's code and data and review the rights and any retained
notices for third-party material. No external upload or DOI registration is
performed by the reproduction scripts.
