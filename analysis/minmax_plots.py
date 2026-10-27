"""Scientific min/max boxplots; no document or Word dependency.

The two functions below are unchanged extractions of the original numeric
summary and plotting functions. See provenance/code_adaptations.json.
"""
from pathlib import Path
import importlib.util
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent / "article_all_algorithms_v1"
spec = importlib.util.spec_from_file_location("boxplot_baseline", ROOT / "revision_v12/analysis_v12.py")
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)
METRICS = ["dead_end_fraction", "junction_fraction", "diameter_normalized", "solution_stretch"]
FIGURES = ROOT / "current_results"


def panel_summaries(panel, size):
    records = []
    for algorithm in analysis.ALGORITHMS:
        subset = panel.loc[panel.algorithm == algorithm]
        for metric in METRICS:
            values = subset[metric].to_numpy() * analysis.scale(metric)
            assert len(values) > 0 and np.isfinite(values).all()
            quartiles = np.quantile(values, [.25, .5, .75], method="linear")
            records.append({"size": size, "algorithm": algorithm,
                "metric": metric, "n_completed": len(values),
                "minimum": float(values.min()), "q25": float(quartiles[0]),
                "median": float(quartiles[1]), "q75": float(quartiles[2]),
                "maximum": float(values.max())})
    archived = pd.read_csv(ROOT / f"revision_v12/outputs/tables/run_dispersion_{size}.csv")
    for record in records:
        old = archived.loc[(archived.algorithm == record["algorithm"]) &
                           (archived.metric == record["metric"])].iloc[0]
        assert int(old.n_completed) == record["n_completed"]
        for name in ("minimum", "q25", "median", "q75", "maximum"):
            assert np.isclose(record[name], old[name], rtol=1e-12, atol=1e-12), record
    return records


def draw_distributions(records, size, axis_limits):
    grid = "10 × 10" if size == 10 else "20 × 20"
    im = Image.new("RGB", (1800, 1770), "white")
    draw = ImageDraw.Draw(im)
    draw.text((35, 20), f"Completed-run distributions on {grid} grids",
              font=analysis.font(38, True), fill="#111111")
    draw.text((35, 78),
        "Box: 25th–75th percentiles; red line: median; whiskers: observed minimum–maximum",
        font=analysis.font(28), fill="#444444")
    lookup = {(r["algorithm"], r["metric"]): r for r in records}
    for k, metric in enumerate(METRICS):
        bx, by = 35 + (k % 2) * 890, 140 + (k // 2) * 800
        draw.text((bx + 10, by), analysis.MLABELS[metric],
                  font=analysis.font(34, True), fill="#111111")
        x0, x1 = bx + 245, bx + 825
        lo, hi = axis_limits[metric]
        def px(value):
            assert lo - 1e-12 <= value <= hi + 1e-12, (metric, value, lo, hi)
            return x0 + (value - lo) / (hi - lo) * (x1 - x0)
        for tick in np.linspace(lo, hi, 5):
            xx = px(tick)
            draw.line((xx, by + 70, xx, by + 725), fill="#e2e5e8", width=2)
            label = f"{tick:g}" if analysis.scale(metric) == 100 else f"{tick:.2f}"
            draw.text((xx, by + 740), label, anchor="mt",
                      font=analysis.font(28), fill="#444444")
        for i, algorithm in enumerate(analysis.ALGORITHMS):
            record = lookup[algorithm, metric]
            y = by + 90 + i * 46
            label = analysis.ALABELS[algorithm].replace("Recursive Division", "Division").replace(
                "Hunt and Kill", "Hunt & Kill")
            if size == 20 and algorithm in {"wilson", "aldous"}:
                label += "*"
            draw.text((bx + 10, y), label, anchor="lm",
                      font=analysis.font(30), fill="#111111")
            left, right = px(record["minimum"]), px(record["maximum"])
            draw.line((left, y, right, y), fill="#165c9b", width=3)
            for xx in (left, right):
                draw.line((xx, y - 8, xx, y + 8), fill="#165c9b", width=3)
            draw.rectangle((px(record["q25"]), y - 11, px(record["q75"]), y + 11),
                           fill="#dce8f5", outline="#165c9b", width=2)
            draw.line((px(record["median"]), y - 13, px(record["median"]), y + 13),
                      fill="#8c2539", width=4)
    path = FIGURES / f"distributions_minmax_{size}.png"
    im.save(path, dpi=(300, 300))
    return path
