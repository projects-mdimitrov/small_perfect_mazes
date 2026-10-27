# Data dictionary for the frozen runs archive

The canonical raw file is
`article_all_algorithms_v1/data/crossed_v1/runs.csv`. It is retained unchanged.
It has one header row followed by 40,320 generation-attempt rows. Its SHA-256 is
`e39fb8b796950642fe2f7be8f6716b7325b1af3299e99ea48b86fee6a9383949`.

Each row records one algorithm × source/corpus × grid-size × window attempt.
There is no implicit average in a raw row. Within the study, the combination
`series`, `source_role`, `source_id`, `corpus_seed`, `algorithm`, `window_index`
identifies the attempt; `source_id` alone does not distinguish control corpora.
CSV numbers use a decimal point, and missing fields are empty. Booleans are
written as `true` or `false`. Incomplete attempts have empty graph metrics, not
zero-valued topology.

## Included populations

| Role and series | Corpora | Windows per corpus and variant | Attempts | Completed | Exhausted |
|---|---:|---:|---:|---:|---:|
| `known_irrational`, `primary_10x10` | 11 | 32 | 4,928 | 4,928 | 0 |
| `pseudo_iid_control`, `primary_10x10` | 64 | 32 | 28,672 | 28,672 | 0 |
| `known_irrational`, `secondary_20x20` | 11 | 16 | 2,464 | 2,446 | 18 |
| `pseudo_iid_control`, `secondary_20x20` | 16 | 16 | 3,584 | 3,562 | 22 |
| `unknown_irrationality`, both series combined | 1 | 32 and 16 | 672 | 670 | 2 |

The main irrational/control analysis uses the first four rows: 39,648 attempts and 39,608
successful mazes. The last group is retained only as part of the frozen
archive. It is not one of the eleven irrational sources used in the study.
The archive as a whole has 40,278 `ok` and 42 `stream_exhausted` rows.

At 20×20, the reported irrational-source failures are 5 Wilson and 13
Aldous–Broder attempts; the control failures are 3 Wilson and 19 Aldous–Broder
attempts. All failure-rate denominators include these attempts. Topology
summaries use successful attempts only and are conditional on completion.

## Identifiers and design fields

| Column | Meaning |
|---|---|
| `study_id` | Frozen study identifier `maze-crossed-algorithms-constants-2026-v1`. |
| `series` | `primary_10x10` or `secondary_20x20`; archival names, not independent replications. |
| `source_id` | `pi`, `e`, `phi`, `sqrt2`, `sqrt3`, `sqrt5`, `sqrt7`, `ln2`, `inv_pi`, `inv_e`, `apery`; controls use `control_pseudo_iid_decimal`. The ancillary file uses `euler_m`. |
| `source_role` | `known_irrational`, `pseudo_iid_control` or `unknown_irrationality`. Use this field to select analysis populations. |
| `source_sha256` | SHA-256 of the decimal input source. The frozen file manifest records source-file identity; controls use the generated digit-string hash. A hash establishes identity, not mathematical validation of every digit. |
| `corpus_seed` | Empty for supplied constants. For controls, exact seed `maze-crossed-algorithms-constants-2026-v1/pseudo-iid/NNN`, where NNN is 001–064. |
| `algorithm` | `dfs`, `prim`, `kruskal`, `wilson`, `aldous`, `hunt`, `growing`, `division`, `eller`, `sidewinder`, `binary_ur`, `binary_dr`, `binary_ul` or `binary_dl`. |
| `cols`, `rows` | Grid dimensions in cells. N = cols × rows. |
| `window_index` | Zero-based index, 0–31 at 10×10 and 0–15 at 20×20. It also determines the balanced construction-root/endpoint schedule. |
| `digit_phase` | Decimal-block phase; fixed at 0 in this experiment. |
| `digit_start` | Zero-based starting decimal-digit offset, inclusive. |
| `digit_end_exclusive` | Assigned window's ending decimal-digit offset, exclusive. This is the budget boundary, not the last consumed position. |
| `units_budget` | Assigned number of five-digit blocks: 6,000 at 10×10 or 12,000 at 20×20. |
| `endpoint_pair_id` | Ordered opposite-corner endpoint identifiers, such as `nw_se`. |
| `solution_start_index`, `solution_goal_index` | Zero-based row-major cell indices of the selected solution endpoints: index = y × cols + x. |
| `construction_root_index` | Construction root for rooted algorithms; empty when not applicable. It is separate from the solution endpoints. |

At 10×10, each window contains 30,000 digits; at 20×20, 60,000 digits.
`digit_start = window_index × units_budget × 5`. Each size uses the first
960,000 decimal digits. The two size series reuse those same digits in
different partitions. No wrapping, fallback sequence, borrowing from the next
window or replacement of an exhausted run is allowed. Unused digits in one
window are not transferred to another run.

## Status and consumption fields

| Column | Meaning |
|---|---|
| `status` | `ok` for completed, validated mazes; `stream_exhausted` when the assigned window ends. The runner can also record `invalid_topology` or `generation_error`, but the frozen manifest records no such cases. |
| `error_code` | Empty on success; exception or validation identifier on failure. |
| `algorithm_completed` | Whether the generator returned normally before validation. This is not a substitute for `status == "ok"`. |
| `perfect_maze` | True only when graph validation succeeded. Successful topology requires connectedness, acyclicity, reciprocal walls, closed outer boundaries, N−1 edges and degree sum 2(N−1). |
| `units_read` | Physical five-digit blocks consumed, including rejected blocks. This is an integer per attempt, not the number of carved passages and not necessarily the number of decoder calls. |
| `rejected_units` | Blocks discarded by decoder rejection sampling; already included in `units_read`. |
| `next_int_calls` | Attempted calls to `nextInt(n)`, including n=1 calls that read no block; a final failing call can be counted when the stream is exhausted. |

The decoder forms an integer x in 0–99,999 from five consecutive decimal
digits, including blocks with leading zeroes. For n > 1 it accepts x only if
x < floor(100000/n) × n, then returns x modulo n; otherwise it consumes the
next block. For n=1 it returns 0 without reading a block. Rejection equalizes
residue multiplicities for uniform block input; it does not prove uniformity
or independence of the supplied constants' blocks.

In the summary tables, **Average Blocks Read** averages `units_read`
over all attempts within each corpus, then weights corpus means equally
within an algorithm and input class. It includes exhausted attempts. The
display is rounded to a whole number; the raw counts and analysis outputs
retain their original precision. Two displayed integer means can coincide
even when individual attempts and maze structures differ.

Controls are generated deterministically by the original HTML's xoshiro128**
implementation and five-digit decimal generator. Each corpus has 192,000
five-digit blocks (960,000 digits). The first sixteen seeds are reused for
the 20×20 series. The seeds, generator implementation and source hashes allow
regeneration independently of backup files. The exact generated sequences
are additionally archived in `control_corpora/control_10x10.jsonl` and
`control_20x20.jsonl`; their record format and zero-based window extraction
are described in `docs/CONTROL_CORPORA.md`. The recorded `source_sha256` is
the hash of the digits string alone, not the entire JSONL record or file.

## Wall encodings and hashes

| Column | Meaning |
|---|---|
| `wall_code_hex` | One hexadecimal digit per cell, in row-major order. Its four bits encode closed walls: bit 0 up, bit 1 right, bit 2 down, bit 3 left; set means a wall is present. Saved only for successful validated mazes. |
| `wall_sha256` | SHA-256 of the exact string `maze-wall-hex-v1\n{cols}x{rows}\n{wall_code_hex}`. This is the main exact graph-identity check. |
| `maze_hash_fnv1a32` | Original HTML's compact FNV-1a maze hash. Useful for traceability, but it is not a cryptographic substitute for SHA-256. |

## Cell and edge metrics

For a successful maze, N is the cell count and E=N−1 the number of open
internal passages. A cell's degree counts open passages to neighbouring
cells, not exterior openings. All fractions in this section are stored on a
0–1 scale. The analysis displays the four cell-type fractions as percent
of **all** cells, not as percent of degree-two cells.

| Column | Definition or unit |
|---|---|
| `degree_0_count` | Isolated cells; 0 for the successful nontrivial connected mazes in this study. |
| `degree_1_count` | Dead-end cells. |
| `degree_2_straight_count` | Degree-two cells with opposite, collinear open passages. |
| `degree_2_turn_count` | Degree-two cells with adjacent, perpendicular open passages. |
| `degree_3_count`, `degree_4_count` | Cells with respectively three and four open passages. |
| `junction_count` | `degree_3_count + degree_4_count`; called branch cells in the analysis. |
| `dead_end_fraction` | `degree_1_count / N`. |
| `straight_fraction` | `degree_2_straight_count / N`. |
| `turn_fraction` | `degree_2_turn_count / N`. |
| `junction_fraction` | `junction_count / N`; analysis label Branch cells (%). |
| `mean_degree` | Sum of degrees divided by N, equal to 2(N−1)/N for a tree. |
| `cell_type_entropy_bits` | Shannon entropy of the four dead-end/straight/turn/branch proportions; bits. |
| `junctions_per_dead_end` | `junction_count / degree_1_count`; ratio. |
| `horizontal_edge_count`, `vertical_edge_count` | Unique open horizontal/vertical passages; edges. |
| `horizontal_edge_fraction`, `vertical_edge_fraction` | Corresponding edge count divided by E. |
| `orientation_anisotropy` | Raw signed (H−V)/E; dimensionless. |
| `absolute_orientation_anisotropy` | Absolute value of the preceding raw index; dimensionless. |
| `adjusted_orientation_anisotropy` | (h−v)/(h+v), with h=H/[rows×(cols−1)] and v=V/[cols×(rows−1)]; dimensionless signed index. On these square grids it equals the raw index up to floating-point roundoff. |
| `vertical_mirror_cell_agreement` | Fraction of cells whose wall pattern agrees with the reflected cell across the vertical centreline, swapping left/right wall directions. Cell-weighted, not a probability of global maze symmetry. |

`absolute_adjusted_anisotropy` is an **analysis-derived** column, not a raw
CSV field. It is `abs(adjusted_orientation_anisotropy)` computed per run
before averaging. Thus mean(|A|) is not |mean(A)|. The tree identity
`degree_1_count = degree_3_count + 2*degree_4_count + 2` holds, and the four
cell fractions sum to one. They are dependent descriptors, not independent
outcomes in an inferential sense.

## Endpoint path and off-path metrics

| Column | Definition or unit |
|---|---|
| `solution_vertex_count` | Number of cells on the unique path between the selected endpoints. |
| `solution_length_edges` | Path length in edges, `solution_vertex_count - 1`. |
| `manhattan_min_edges` | abs(dx)+abs(dy) for the endpoints: 18 at 10×10 and 38 at 20×20. |
| `euclidean_distance` | sqrt(dx²+dy²), in cell spacings. |
| `solution_stretch` | `solution_length_edges / manhattan_min_edges`; dimensionless Path stretch in the analysis. |
| `endpoint_path_euclidean_ratio` | `solution_length_edges / euclidean_distance`; a different ratio, not the analysis's Path stretch. |
| `solution_turn_count` | Direction changes along the selected endpoint path; turns. |
| `solution_turn_rate` | `solution_turn_count / (solution_length_edges - 1)` when defined; fraction of eligible internal path positions. |
| `decision_point_count` | Path vertices, excluding the final goal, with more than one forward graph neighbour. |
| `heuristic_choice_complexity_bits` | Sum of log2(forward choices) at path decision points; exploratory bits-like proxy, not validated human solving difficulty. |
| `decision_density_per_10_edges` | `10 * decision_point_count / solution_length_edges`. |
| `off_path_branch_count` | Number of non-path subtrees attached directly to the selected endpoint path. This is not the count of degree-three/four branch cells. |
| `off_path_vertex_count` | Total cells in those subtrees; equals N minus `solution_vertex_count`. |
| `off_path_fraction` | `off_path_vertex_count / N`. |
| `off_path_branch_size_mean`, `off_path_branch_size_median`, `off_path_branch_size_q90`, `off_path_branch_size_max` | Summary of subtree sizes in cells, one size per off-path attachment. |
| `off_path_branch_depth_mean`, `off_path_branch_depth_median`, `off_path_branch_depth_q90`, `off_path_branch_depth_max` | Summary of each off-path subtree's greatest distance from its path attachment, in edges. |

## Corridors and diameter

| Column | Definition or unit |
|---|---|
| `dead_end_depth_mean`, `dead_end_depth_median`, `dead_end_depth_q90`, `dead_end_depth_max` | Summary over leaves of the distance from a leaf through degree-two cells to the first non-degree-two cell; edges. |
| `corridor_count` | Number of maximal paths whose internal cells all have degree two. |
| `corridor_length_mean`, `corridor_length_median`, `corridor_length_q90`, `corridor_length_max` | Summary of maximal-corridor lengths in edges. |
| `diameter_edges` | Largest shortest-path distance between any two cells. Computed by two BFS sweeps on the validated tree; it need not equal the selected endpoint path length. |
| `diameter_normalized` | `diameter_edges / (N - 1)`; dimensionless 0–1 value, not multiplied by 100 in the main irrational/control analysis's diameter-deviation figures. |

Quantiles in the metric implementation use linear interpolation. An empty
underlying collection may produce missing summary values rather than a zero.
The exact original formulas are in `METRIC_CODEBOOK` and `analyzeMaze` in
`maze_analytics_lab-15.html`; these definitions do not imply that every stored
exploratory metric is analysed in the article.

## Analysis population and weighting rules

Algorithm means average completed windows within a corpus, then give all
corpora equal weight. Cross-algorithm means assign weight 1/4 to each of the
four Binary Tree orientations and weight 1 to every other variant, for eleven
family-weight units. The orientations remain fourteen distinct factor levels;
weighting does not merge four maze graphs or create independent replications.
Actual sample counts and within-variant run-level boxplots are not weighted
by 1/4.

For current descriptive variance partitions, each completed observation in
algorithm–corpus cell (a,c) receives weight q_a × W / m_ac. All available
completed Wilson and Aldous–Broder attempts enter the current 20×20 partition.
Older `revision_v12` complete-panel secondary margins/partitions omit those
two variants and are retained as archival sensitivity results, not current
all-variant results. See `RESULTS_MAP.md` before selecting an output file.

The observations are finite deterministic windows, not independent samples
from all irrational numbers. Related constants and reuse of the same digit
prefixes across sizes limit inference. Unsuccessful runs are missing topology
because their budget ended; balancing completed cells does not remove that
selection. File hashes do not prove digit normality, independence or complete
mathematical validation of every prefix. Runtime is not an experimental
benchmark outcome in this study.
