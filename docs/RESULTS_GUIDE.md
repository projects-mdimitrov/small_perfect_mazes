# Scientific results guide

This guide connects the frozen observations to the numerical results. It does
not depend on an article file, document hash, figure number or table number.
All paths are relative to the package root. `I` denotes known-irrational input
files and `C` denotes seeded pseudorandom control corpora.

## Canonical inputs and populations

The canonical attempt-level data are
`article_all_algorithms_v1/data/crossed_v1/runs.csv`. Source-file identities,
generation settings and expected total counts are in the adjacent
`manifest.json`. The frozen runner, HTML core and decimal files are part of
the package; their hashes are checked before replay.

The exact seeded control sequences are also saved in
`control_corpora/control_10x10.jsonl` and `control_20x20.jsonl`. These backups
are tied to the raw rows by `corpus_seed` and `source_sha256`; they do not
introduce new observations. See `docs/CONTROL_CORPORA.md` for the format.

| Input class and size | Corpora | Windows per corpus and variant | Attempts | Completed |
|---|---:|---:|---:|---:|
| I, 10×10 | 11 | 32 | 4,928 | 4,928 |
| C, 10×10 | 64 | 32 | 28,672 | 28,672 |
| I, 20×20 | 11 | 16 | 2,464 | 2,446 |
| C, 20×20 | 16 | 16 | 3,584 | 3,562 |

The current I/C population has 39,648 attempts and 39,608 completed mazes.
The raw archive additionally retains 672 ancillary attempts, of which 670
completed, for a frozen total of 40,320 attempts. Select current populations
with `source_role` equal to `known_irrational` or `pseudo_iid_control`.
Ancillary `unknown_irrationality` rows are not an additional irrational source
in current I/C summaries. Preserve them for exact original replay.

## Analysis layers

| Scientific output | Reference files or calculation | Definition |
|---|---|---|
| Completion and exhaustion | Raw data grouped by size, source role, algorithm and status | Actual unweighted scheduled attempts; failures are never replaced. |
| Current algorithm means for I/C | `article_all_algorithms_v1/revision_v21/outputs/algorithm_means_10_I.csv`, `algorithm_means_10_C.csv`, `algorithm_means_20_I.csv`, `algorithm_means_20_C.csv` | Completed-window topology means within each algorithm–corpus cell, then equal-corpus means within each input class. |
| Current family-balanced overall means | `article_all_algorithms_v1/revision_v21/outputs/analysis_v21.json`, `sizes["10"/"20"]["I"/"C"]["grand"]` | Equal-corpus algorithm means, combined with variant weights 1/4 for each Binary Tree orientation and 1 for every other variant. |
| Current I source margins | `reference_results/current_reanalysis/current_source_means_10.csv` and `current_source_means_20.csv` | Source-specific algorithm means combined with the same family weights; all fourteen variants, including available completed Wilson and Aldous–Broder runs. |
| Current four-component I/C variability partitions | `article_all_algorithms_v1/revision_v21/outputs/variance_partition_10_I.csv`, `variance_partition_10_C.csv`, `variance_partition_20_I.csv`, `variance_partition_20_C.csv` | Algorithm, source/corpus, interaction and within-cell window shares of the weighted run-level sum of squares. |
| Current all-completed I secondary partition and weighting sensitivity | `article_all_algorithms_v1/revision_v18/outputs/secondary_variance.json` | Completed-cell-balanced decomposition, including the two random-walk variants; also retains the equal-variant sensitivity calculation. |
| Algorithm-by-I-source means | `article_all_algorithms_v1/revision_v12/outputs/tables/algorithm_source_cells_10.csv` and `algorithm_source_cells_20.csv` | Eight topology columns include signed and absolute adjusted anisotropy; attempted and completed counts are explicit. |
| Current source deviations | `reference_results/current_reanalysis/deviations_{size}_{metric}.csv` | Source-specific completed-window mean minus that algorithm's equal-source mean, for sizes 10/20 and the four foreground display metrics described below. |
| Within-variant completed-run distributions | `article_all_algorithms_v1/revision_v12/outputs/tables/run_dispersion_10.csv` and `run_dispersion_20.csv` | Pooled successful runs, without preliminary equal-source averaging; completed n, mean, sample SD, median, quantiles and extrema. |
| Current minimum–maximum plot data | `reference_results/current_reanalysis/minmax_boxplot_data.json` and `reference_results/minmax_boxplots/config.json` | Box Q25–Q75, central median, whiskers at observed minimum and maximum. The helper is `analysis/minmax_plots.py`. |
| Primary control reference | `article_all_algorithms_v1/revision_v12/outputs/tables/primary_control_corpus_means.csv` and `primary_control_reference.csv` | Sixty-four corpus margins, each family-balanced; empirical 2.5th–97.5th percentiles of those corpus means, not a confidence interval for a constant effect. |
| Fixed complete-panel comparisons and weighting sensitivity | `article_all_algorithms_v1/revision_v12/outputs/tables/common_panel_sources_*.csv`, `common_panel_source_contrasts_*.csv`, `weighting_sensitivity_*.csv` | Supplemental numerical checks with the panel and scheme recorded in each file; not automatic replacements for the current all-variant outputs. |

Where a row lists additional filenames without a directory, they use the same
directory as the first filename. Wildcards and braces in the guide describe
filename families, not additional files to download.

The analysis revision names identify code provenance. The package adaptations
remove only editorial dependencies, reorganize numerical plot helpers and
record the resulting source changes in `provenance/code_adaptations.json`.
Use `reproduce.py analyse` rather than trying to execute a historical document
construction sequence.

## Units and display transformations

Raw cell fractions are on a 0–1 scale and use all cells as the denominator.
Their percentage form is the fraction multiplied by 100. Dead-end and branch
deviations are therefore percentage-point differences. Current
`diameter_normalized` deviations and `solution_stretch` deviations are
dimensionless and are not multiplied by 100.

`adjusted_orientation_anisotropy` is a signed index A.
`absolute_adjusted_anisotropy` is derived per run as abs(A), then averaged.
Mean(abs(A)) must not be replaced by abs(mean(A)). The current variability
partitions use signed A, not mean absolute anisotropy.

`units_read` counts consumed physical five-digit blocks, including rejected
blocks. Current `blocks_read` means average all attempts within each corpus
and then average corpus means equally. Exhausted attempts remain included.
The full-precision numeric means should be used for checks; rounding to a
whole block for presentation does not make individual raw counts equal.

The raw CSV and numerical reference files retain machine-readable precision.
Any later article can round these values without changing the underlying
experiment. Comparison with a later document should allow for its stated
rounding rather than compare the document's byte hash.

## Weighting and completion

Within an algorithm a and corpus c, topology first averages successful
windows. Algorithm summaries average those corpus means equally. For
cross-variant summaries, q_a = 1/4 for each of four Binary Tree orientations
and q_a = 1 for each other variant; the total weight is 11 families.
Orientations remain separate variant levels. Actual attempt counts and
individual-variant distributions do not receive these weights.

For the current variability partition, each completed observation in cell
(a,c) has weight q_a × W / m_ac, where W is the planned window count and m_ac
is the number completed in that cell. Every cell therefore has total weight
q_a × W. The four orthogonal components sum to the weighted total sum of
squares, and their percentage shares sum to 100 before rounding. This is a
conditional descriptive definition, not imputation, a hypothesis test or a
correction for completion-related selection bias.

At 20×20, the I population has 5 exhausted Wilson and 13 exhausted
Aldous–Broder attempts; C has 3 and 19 respectively. Topology conditions on
the remaining runs. Resource and completion denominators include failures.
Pooled completed-run distributions and equal-corpus means need not coincide
when completion counts differ.

## Baseline results that have a different panel

The following baseline files are deliberately retained for numerical
cross-checks, but they have a narrower secondary panel:

- `article_all_algorithms_v1/revision_v12/outputs/tables/source_means_20.csv`
  and `weighted_variance_20.csv` exclude Wilson and Aldous–Broder. Their panel
  has twelve variants and a family-weight sum of nine. Use the current
  all-variant source means and v18/v21 partitions for the current secondary
  comparison.
- `common_panel_sources_10.csv`, `common_panel_sources_20.csv` and their
  contrasts use the same twelve complete variants at both sizes. They answer
  a matched-panel sensitivity question, not the all-variant question.
- The dispersion CSVs retain q05 and q95 as valid numerical descriptors.
  Current minimum–maximum boxplots use the minimum and maximum columns, not
  those two quantiles. Boxplots do not display confidence intervals.

## What the scientific checks establish

The package separates file identity, execution replay, graph audits and
numerical analysis checks. `reproduce.py verify` checks hashes.
`regenerate` replays the frozen generation design and compares the complete
CSV byte for byte. `audit` independently reconstructs saved graph properties
and the four original foreground metrics. `analyse` recomputes the numerical
outputs and compares them with the references. See
`provenance/scientific_validation/validation.json` for the performed checks
and associated reports, rather than treating documentation as proof that a
command passed.

The current source margins, deviations and min/max data can be regenerated
from `runs.csv`; no article is used as a numerical input or validation guard.
The data/code release can be checked and assigned a DOI before a later
article is written or formatted. Checking that later article's numbers is a
separate task against this fixed numerical release.

These checks establish reproducibility and specified numerical consistency,
not scientific novelty, unbiased inference after exhaustion, normality of
the stored decimal digits or validity for all irrational numbers. Both size
series reuse digit prefixes; related mathematical constants are not
independent random samples. Cell-type fractions are also dependent: they
partition all cells, and for these perfect grid trees n1 = n3 + 2 n4 + 2.
Any historical digit-validation report has only the scope it explicitly
states; file hashes do not independently validate digit mathematics.
