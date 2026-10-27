# Crossed maze algorithm and decimal source study

Protocol frozen before the new experiment is run. This study does not reuse
maze-level observations from Article 1. The unchanged algorithm and metric
implementation is loaded from `../maze_analytics_lab-15.html`; its SHA-256 is
recorded in the generated manifest. The runner and analysis scripts live in
this directory.

## Questions

1. How do the fourteen selectable implementation variants differ in maze
   topology when they receive matched digit windows?
2. Within each implementation, how much do measured outputs differ among the
   eleven supplied decimal files for numbers known to be irrational?
3. Does a finite digit budget prevent completion, especially for the two
   random-walk algorithms?

The Euler--Mascheroni constant gamma is run through the same matrix but is
reported as a separate arithmetic-status comparator. Its irrationality is
unknown, so it is not counted among the eleven irrational sources.

## Fixed design

* Algorithms: `dfs`, `prim`, `kruskal`, `wilson`, `aldous`, `hunt`, `growing`,
  `division`, `eller`, `sidewinder`, `binary_ur`, `binary_dr`, `binary_ul`,
  `binary_dl`. These are all fourteen choices in the v15 HTML interface.
* Known-irrational files: `pi`, `e`, `phi`, `sqrt2`, `sqrt3`, `sqrt5`,
  `sqrt7`, `ln2`, `inv_pi`, `inv_e`, `apery`.
* Additional, separately labelled file: `euler_m`.
* Primary grid: 10 by 10 cells, 32 windows of 6,000 consecutive five-digit
  blocks per source, beginning at digit position zero. Window boundaries are
  30,000 decimal digits apart and do not overlap within the grid-size series.
* Secondary grid: 20 by 20 cells, 16 windows of 12,000 consecutive five-digit
  blocks per source, also beginning at digit position zero. The two grid-size
  series intentionally reuse the same first 960,000 digits; they are not
  independent replications and are analysed separately.
* Digit phase: zero. Each run reads only its assigned window. No wrap,
  repetition, fallback pseudorandom values, or extension into another window.
* Choices: v15 five-digit `nextInt(n)` with rejection of values at or above
  `floor(100000/n)*n`, except the deterministic `n=1` choice that consumes no
  block. This gives balanced residues for a uniform block input, without
  asserting uniformity of constant digits.
* Algorithm-root and solution-endpoint assignments follow v15
  `balanced_opposite`, using the same `run_index` for every algorithm and
  source. The 16-run cycle balances the four corners for rooted algorithms.
* Each algorithm is given the same physical source window in a condition.
  Equal input budgets do not imply equal consumed block counts.
* All 14 by 12 by (32+16) = 8,064 constant-file attempts are run, of which
  7,392 belong to the known-irrational set. No incomplete or invalid run is
  replaced.
* Seeded pseudo-IID decimal controls use the same five-digit decoder and
  window schedule: 64 independent seeded corpora at 10 by 10 and the first
  16 of these at 20 by 20. This adds 32,256 control attempts, for 40,320
  attempts in total. These computational controls are not additional
  mathematical constants.

## Outcomes and analysis rules

All 55 v15 graph metrics, exact wall codes, an SHA-256 of each completed wall
graph, choice counts, source/window identifiers, and completion status are
retained in the raw CSV. Four topology metrics are foregrounded:
dead-end fraction, diameter divided by V-1, boundary-adjusted horizontal--
vertical anisotropy, and selected-corner solution stretch relative to
Manhattan distance. The physical digit blocks read and budget-exhaustion rate
are resource outcomes. Elapsed runtime is not used as a performance measure.

Primary 10-by-10 results are shown for every algorithm-by-source cell. For
algorithm comparisons, report means over matched windows and the range of
source-specific means. For source comparisons, report means by source and
the algorithm-specific spread. A fixed-factor variance decomposition over
algorithm, source, and interaction is descriptive only. The pseudo-IID
control corpora supply a reference distribution of same-protocol corpus
means; no window is treated as an independent mathematical constant, and no
post-hoc cellwise significance claims are made. The secondary 20-by-20 series
is reported separately. Completion denominators always include exhausted
attempts. Topology summaries exclude incomplete runs and are labelled
conditional on completion; if attrition is appreciable, they are not used to
rank algorithms without a selection warning.

All complete mazes must satisfy the perfect-maze invariants: V-1 edges,
connectedness, acyclicity, reciprocal walls, closed boundaries, and the
expected degree sum. A separate Python audit will decode saved walls and
recalculate the four foreground metrics without using the v15 analyser.

## Scope and interpretation

The objects of comparison are finite stored prefixes and these exact
implementations. Number identity is not a random treatment, the eleven
constants are not a random sample of all irrationals, and related constants
such as pi and 1/pi are not statistically independent sources. The study
cannot establish digit normality or an algorithm's performance on all
possible inputs. File SHA-256 checks prove identity to the supplied corpus,
not independent mathematical correctness of every stored digit. Prior
provenance checks are reused and their unequal depth is reported in the
article.
