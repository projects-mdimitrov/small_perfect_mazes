# Saved control digit sequences

The two JSONL data files archive the exact pseudorandom decimal sequences
used by the frozen experiment. They were reconstructed from the recorded
seeds using the original generator and checked against every control row in
the unchanged raw CSV. This is a redundant data backup, not a new experiment
or a change in randomization.

| File | Records | Digits per record | Five-digit blocks per record |
|---|---:|---:|---:|
| `control_corpora/control_10x10.jsonl` | 64 | 960,000 | 192,000 |
| `control_corpora/control_20x20.jsonl` | 16 | 960,000 | 192,000 |

Each file is UTF-8 without BOM, with one JSON object per line and LF line
endings. JSONL is plain text, not a spreadsheet. One long record contains a
complete corpus; the file is not one uninterrupted digit sequence across
different seeds. The four fields are:

- `corpus_index`: integer 1 through 64, or 1 through 16 for the second file.
- `corpus_seed`: the complete textual seed used by the original runner.
- `source_sha256`: SHA-256 of the ASCII `digits` string alone. It matches the
  raw CSV field of the same name for that seed. It is not the hash of the
  entire JSON object or JSONL file.
- `digits`: the exact 960,000 decimal characters as a JSON string. Leading
  zeroes are significant; never convert this string or its five-digit blocks
  into numbers and then serialize them without zero-padding.

The complete second file contains the same records as the first sixteen
records of the first file. Those are shared corpora, not sixteen new,
independently drawn sequences. The manifest in `control_corpora/manifest.json`
records file hashes, corpus hashes, source-code identity and generator
telemetry. `export_check.json` records the source-generator verification.
The package's scientific validation directory contains an additional
independent-check report.

## Use the saved sequences

Select a record by the raw row's `corpus_seed`, then extract its assigned
window using the raw row's digit offsets:

```python
import json

with open("control_corpora/control_10x10.jsonl", encoding="utf-8") as stream:
    for line in stream:
        record = json.loads(line)
        if record["corpus_seed"] == wanted_seed:
            digits = record["digits"]
            window = digits[digit_start:digit_end_exclusive]
            break
```

`wanted_seed`, `digit_start` and `digit_end_exclusive` in this example come
from the selected `runs.csv` row. Offsets are zero-based; the end is exclusive.
For window index w, the 10x10 offsets are `[30000*w, 30000*(w+1))`; the 20x20
offsets are `[60000*w, 60000*(w+1))`. Inside the assigned window, split the
string into consecutive blocks of five digits from position zero. The
original decoder's rejection rule is unchanged. Store all source blocks,
including those the maze decoder rejected or never needed to consume.

The corpus generator itself uses the textual seed through cyrb128 and then
xoshiro128**. It converts accepted 32-bit draws to uniform integers below
100,000 and zero-pads each to five digits. This is the frozen batch runner's
seed path, not the interactive HTML interface's separate master-seed workflow.

## Verify or reproduce the files

From the package root:

```text
node tools/export_control_corpora.js --verify
```

This checks all 80 saved records, all 64 unique sequences against fresh seed
replay, the hashes recorded in all 32,256 control attempt rows, record counts,
window schedules and the overlap between sizes. It does not generate mazes
or change the files.

To reconstruct a separate backup without overwriting the archive:

```text
node tools/export_control_corpora.js --export --out new_control_export
```

The target data files must not already exist. Ordinary experiment commands
remain unchanged: the frozen maze runner reconstructs controls from seeds.
The saved sequences provide an additional way to inspect and independently
replay the inputs, without modifying the original generation code.
