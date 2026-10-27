"""Family-balanced reanalysis of frozen maze observations; no maze generation.

Binary Tree remains four variant levels. Each observation from those variants
has weight 1/4 in cross-variant summaries. Other variants have weight 1.
Individual-variant summaries and actual attempt counts remain unweighted.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.metadata
import json
import platform
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RAW = ROOT / "data/crossed_v1/runs.csv"
OUT = HERE / "outputs"
ALGORITHMS = ["dfs", "prim", "kruskal", "wilson", "aldous", "hunt",
              "growing", "division", "eller", "sidewinder",
              "binary_ur", "binary_dr", "binary_ul", "binary_dl"]
SOURCES = ["pi", "e", "phi", "sqrt2", "sqrt3", "sqrt5", "sqrt7",
           "ln2", "inv_pi", "inv_e", "apery"]
ALABELS = dict(zip(ALGORITHMS, ["DFS", "Prim", "Kruskal", "Wilson", "Aldous-Broder",
    "Hunt and Kill", "Growing Tree", "Recursive Division", "Eller", "Sidewinder",
    "Binary UR", "Binary DR", "Binary UL", "Binary DL"]))
SLABELS = dict(zip(SOURCES, ["π", "e", "φ", "√2", "√3", "√5", "√7",
                            "ln(2)", "1/π", "1/e", "ζ(3)"]))
METRICS = ["dead_end_fraction", "junction_fraction", "straight_fraction", "turn_fraction",
           "diameter_normalized", "adjusted_orientation_anisotropy", "solution_stretch"]
VMETRICS = [METRICS[i] for i in (0, 1, 4, 5, 6)]
MLABELS = dict(zip(METRICS, ["Dead-end cells (%)", "Branch cells (%)", "Straight cells (%)",
    "Turn cells (%)", "Normalized diameter", "Signed anisotropy", "Path stretch"]))
COMMON = [a for a in ALGORITHMS if a not in {"wilson", "aldous"}]


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def weight(a):
    return .25 if a.startswith("binary_") else 1.


def scale(metric):
    return 100. if metric.endswith("_fraction") else 1.


def save(frame, name):
    frame.to_csv(OUT / "tables" / name, index=False, float_format="%.15g")


def source_means(panel):
    cells = panel.groupby(["algorithm", "source_id"])[METRICS].mean()
    records = []
    for source in SOURCES:
        part = cells.xs(source, level="source_id")
        w = np.array([weight(a) for a in part.index])
        values = np.average(part.to_numpy(), weights=w, axis=0)
        records.append({"source_id": source, "variant_levels": len(part),
            "family_weight_sum": w.sum(),
            "actual_completed": int((panel.source_id == source).sum()),
            **dict(zip(METRICS, values))})
        # Check weighting by a separately grouped family representation.
        family = part.copy()
        family.index = ["binary" if a.startswith("binary_") else a for a in part.index]
        assert np.allclose(values, family.groupby(level=0).mean().mean().to_numpy())
    return pd.DataFrame(records)


def decompose(panel, equal_variants=False):
    algorithms = [a for a in ALGORITHMS if a in set(panel.algorithm)]
    counts = panel.groupby(["algorithm", "source_id"]).size()
    assert counts.nunique() == 1 and panel.status.eq("ok").all()
    windows = int(counts.iloc[0])
    w = np.ones(len(algorithms)) if equal_variants else np.array([weight(a) for a in algorithms])
    omega = w.sum()
    records = []
    for metric in VMETRICS:
        x = np.empty((len(algorithms), 11, windows))
        for i, a in enumerate(algorithms):
            for j, s in enumerate(SOURCES):
                values = panel.loc[(panel.algorithm == a) & (panel.source_id == s)]
                x[i, j] = values.sort_values("window_index")[metric]
        grand = np.sum(w[:, None, None] * x) / (omega * 11 * windows)
        am = x.mean(axis=(1, 2))
        sm = np.average(x.mean(axis=2), axis=0, weights=w)
        cm = x.mean(axis=2)
        ss = np.array([
            11 * windows * np.sum(w * (am - grand) ** 2),
            omega * windows * np.sum((sm - grand) ** 2),
            windows * np.sum(w[:, None] * (cm-am[:, None]-sm[None, :]+grand)**2),
            np.sum(w[:, None, None] * (x-cm[:, :, None])**2)])
        total = np.sum(w[:, None, None] * (x-grand)**2)
        assert np.isclose(ss.sum(), total, rtol=1e-11, atol=1e-10)
        # Independent integer-frequency interpretation: other observations
        # are repeated four times and Binary observations once.
        rep = np.repeat(x, (w * 4).astype(int), axis=0)
        assert np.isclose(np.square(rep-rep.mean()).sum()/4, total)
        records.append({"metric": metric, "scheme": "equal_variants" if equal_variants else "family_balanced",
            "variant_levels": len(algorithms), "family_weight_sum": omega,
            "windows_per_cell": windows, "actual_completed": len(panel),
            "ss_total": total, **dict(zip(["algorithm_percent", "source_percent",
                "interaction_percent", "within_cell_percent"], 100*ss/total))})
    return pd.DataFrame(records)


def dispersion(panel):
    result = []
    for a in ALGORITHMS:
        part = panel.loc[panel.algorithm == a]
        for m in METRICS + ["absolute_adjusted_anisotropy"]:
            y = part[m].to_numpy() * scale(m)
            q = np.quantile(y, [.05, .25, .5, .75, .95], method="linear")
            result.append({"algorithm": a, "metric": m, "n_completed": len(y),
                "unit": "percent_of_all_cells" if scale(m) == 100 else "dimensionless",
                "pooled_completed_mean": y.mean(), "sample_sd": y.std(ddof=1),
                **dict(zip(["q05", "q25", "median", "q75", "q95"], q)),
                "minimum": y.min(), "maximum": y.max()})
    return pd.DataFrame(result)


def draw_partition(frame, title, filename):
    im = Image.new("RGB", (1750, 690), "white")
    draw = ImageDraw.Draw(im)
    colors = ["#165c9b", "#dd8f20", "#b54352", "#9aa8b8"]
    left = np.zeros(len(frame))
    draw.text((45, 25), title, font=font(37, True), fill="#111111")
    draw.text((45, 80), "Binary Tree orientations: weight 1/4 each; other variants: weight 1",
              font=font(25), fill="#444444")
    for key, label, color in zip(["algorithm_percent", "source_percent", "interaction_percent",
            "within_cell_percent"], ["Variant", "Source", "Interaction", "Within cell"], colors):
        x = frame[key].to_numpy()
        for i, value in enumerate(x):
            y = 160+i*80
            x0, x1 = 490+left[i]*11.8, 490+(left[i]+value)*11.8
            draw.rectangle((x0, y, x1, y+46), fill=color)
            if value > 6:
                draw.text(((x0+x1)/2, y+23), f"{value:.1f}%", anchor="mm", font=font(26),
                          fill="white" if key == "algorithm_percent" else "black")
        left += x
    for i, m in enumerate(frame.metric):
        draw.text((45, 167+i*80), MLABELS[m], font=font(28), fill="#111111")
    draw.text((490, 566), "Share of weighted run-level sum of squares (%)", font=font(27), fill="#333333")
    for i, (label, color) in enumerate(zip(["Variant", "Source", "Interaction", "Within cell"], colors)):
        x = 490+i*270
        draw.rectangle((x, 628, x+25, 653), fill=color)
        draw.text((x+40, 624), label, font=font(27), fill="#111111")
    im.save(OUT/"figures"/filename, dpi=(300, 300))


def font(size, bold=False):
    candidates = [Path("C:/Windows/Fonts")/("arialbd.ttf" if bold else "arial.ttf"),
                  Path("/usr/share/fonts/truetype/dejavu")/
                  ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")]
    for p in candidates:
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default(size=size)


def draw_distributions(panel, grid, filename, axis_limits):
    im = Image.new("RGB", (1800, 1770), "white")
    draw = ImageDraw.Draw(im)
    draw.text((35, 20), f"Completed-run distributions on {grid} grids", font=font(38, True), fill="#111111")
    draw.text((35, 78), "Box: 25th–75th percentiles; line: median; whiskers: 5th–95th percentiles",
              font=font(28), fill="#444444")
    for k, metric in enumerate([METRICS[i] for i in (0, 1, 4, 6)]):
        bx, by = 35+(k%2)*890, 140+(k//2)*800
        draw.text((bx+10, by), MLABELS[metric], font=font(34, True), fill="#111111")
        x0, x1 = bx+245, bx+825
        quantiles = [np.quantile(panel.loc[panel.algorithm == a, metric]*scale(metric),
                                [.05, .25, .5, .75, .95]) for a in ALGORITHMS]
        lo, hi = axis_limits[metric]
        px = lambda v: x0+(v-lo)/(hi-lo)*(x1-x0)
        for tick in np.linspace(lo, hi, 5):
            xx = px(tick)
            draw.line((xx, by+70, xx, by+725), fill="#e2e5e8", width=2)
            label = f"{tick:.1f}" if scale(metric)==100 else f"{tick:.2f}"
            draw.text((xx, by+740), label, anchor="mt", font=font(28), fill="#444444")
        for i, (a, q) in enumerate(zip(ALGORITHMS, quantiles)):
            y = by+90+i*46
            label = ALABELS[a].replace("Recursive Division", "Division").replace("Hunt and Kill", "Hunt & Kill")
            if grid == "20 × 20" and a in {"wilson", "aldous"}:
                label += "*"
            draw.text((bx+10, y), label, anchor="lm", font=font(30), fill="#111111")
            draw.line((px(q[0]), y, px(q[4]), y), fill="#165c9b", width=3)
            for value in (q[0], q[4]):
                draw.line((px(value), y-8, px(value), y+8), fill="#165c9b", width=3)
            draw.rectangle((px(q[1]), y-11, px(q[3]), y+11), fill="#dce8f5", outline="#165c9b", width=2)
            draw.line((px(q[2]), y-13, px(q[2]), y+13), fill="#8c2539", width=4)
    im.save(OUT/"figures"/filename, dpi=(300, 300))


def draw_profiles(cells, grid, filename, axis_limits):
    im=Image.new("RGB",(1800,1260),"white"); draw=ImageDraw.Draw(im)
    draw.text((35,20),f"Algorithm profiles on {grid} grids",font=font(38,True),fill="#111111")
    draw.text((35,78),"Point: equal-source mean; whiskers: minimum–maximum source means; matched axes across sizes",
              font=font(28),fill="#444444")
    for k,metric in enumerate([METRICS[i] for i in (0,4,6,1)]):
        bx,by=35+(k%2)*890,140+(k//2)*550
        draw.text((bx+10,by),MLABELS[metric],font=font(34,True),fill="#111111")
        x0,x1=bx+245,bx+825; lo,hi=axis_limits[metric]
        px=lambda v:x0+(v-lo)/(hi-lo)*(x1-x0)
        for tick in np.linspace(lo,hi,5):
            xx=px(tick); draw.line((xx,by+65,xx,by+495),fill="#e2e5e8",width=2)
            draw.text((xx,by+505),f"{tick:.1f}" if scale(metric)==100 else f"{tick:.2f}",
                      anchor="mt",font=font(28),fill="#444444")
        for i,variant in enumerate(ALGORITHMS):
            y=by+82+i*31
            label=ALABELS[variant].replace("Recursive Division","Division").replace("Hunt and Kill","Hunt & Kill")
            if grid=="20 × 20" and variant in {"wilson","aldous"}: label+="*"
            draw.text((bx+10,y),label,anchor="lm",font=font(30),fill="#111111")
            values=cells.xs(variant,level="algorithm")[metric]*scale(metric)
            left,right,mid=px(values.min()),px(values.max()),px(values.mean())
            draw.line((left,y,right,y),fill="#165c9b",width=3)
            for xx in (left,right): draw.line((xx,y-6,xx,y+6),fill="#165c9b",width=3)
            draw.ellipse((mid-5,y-5,mid+5,y+5),fill="#165c9b")
    im.save(OUT/"figures"/filename,dpi=(300,300))


def audit_cells():
    statuses = Counter(); checked = 0; keys = set()
    with RAW.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            key = tuple(r[k] for k in ("series", "source_id", "corpus_seed", "algorithm", "window_index"))
            assert key not in keys; keys.add(key); statuses[r["status"]] += 1
            if r["status"] != "ok":
                continue
            masks = [15 ^ int(c, 16) for c in r["wall_code_hex"]]
            n = int(r["cols"]) * int(r["rows"])
            degree = Counter(m.bit_count() for m in masks)
            straight = sum(m in (5, 10) for m in masks)
            turn = degree[2]-straight; branch = degree[3]+degree[4]
            counts = [degree[0], degree[1], straight, turn, degree[3], degree[4]]
            for k, v in zip(["degree_0_count", "degree_1_count", "degree_2_straight_count",
                "degree_2_turn_count", "degree_3_count", "degree_4_count"], counts):
                assert int(r[k]) == v
            for k, v in zip(METRICS[:4], [degree[1], branch, straight, turn]):
                assert abs(float(r[k])-v/n) < 1e-12
            assert degree[0] == 0 and sum(counts) == n
            assert degree[1] == degree[3]+2*degree[4]+2
            checked += 1
    report = {"status": "pass", "raw_sha256": sha(RAW), "actual_attempts": len(keys),
        "statuses": dict(statuses), "completed_wall_strings_checked": checked,
        "checks": ["all four cell fractions and six degree counts reconstructed from walls",
                   "partition of all cells", "tree leaf/branch identity", "unique attempt keys"],
        "scope": "Extends, does not replace, the archived full graph/four-foreground-metric audit."}
    (OUT / "cell_metric_audit.json").write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")


def main():
    for folder in ["tables", "figures"]:
        (OUT / folder).mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT / "data/crossed_v1/manifest.json").read_text())
    assert sha(RAW) == manifest["runs_csv_sha256"]
    for path, expected in [(ROOT/"protocol.md", manifest["protocol_sha256"]),
        (ROOT/"run_crossed_study.js", manifest["runner_sha256"]),
        (ROOT.parent/"maze_analytics_lab-15.html", manifest["html_sha256"])]:
        assert sha(path) == expected
    for info in manifest["sources"].values():
        assert sha(ROOT.parent/info["file"]) == info["sha256"]
    data = pd.read_csv(RAW, low_memory=False)
    data["absolute_adjusted_anisotropy"] = data.adjusted_orientation_anisotropy.abs()
    known = data.loc[data.source_role == "known_irrational"]
    panels = {size: known.loc[(known.series == series) & (known.status == "ok")].copy()
        for size, series in [(10, "primary_10x10"), (20, "secondary_20x20")]}
    assert len(panels[10]) == 4928 and len(panels[20]) == 2446
    max_stretch_q95 = max(
        np.quantile(part.solution_stretch, .95)
        for panel in panels.values() for _, part in panel.groupby("algorithm"))
    axis_limits = {"dead_end_fraction": (0,40), "junction_fraction": (0,35),
        "diameter_normalized": (0,1), "solution_stretch": (1,float(np.ceil(max_stretch_q95)))}
    (OUT/"figures/axis_limits.json").write_text(json.dumps(axis_limits,indent=2)+"\n")
    profile_limits={"dead_end_fraction":(0,40),"junction_fraction":(0,35),
                    "diameter_normalized":(0,.8),"solution_stretch":(0,5)}
    (OUT/"figures/profile_axis_limits.json").write_text(json.dumps(profile_limits,indent=2)+"\n")
    results = {}
    for size, panel in panels.items():
        common = panel.loc[panel.algorithm.isin(COMMON)]
        margin_panel = panel if size == 10 else common
        sources = source_means(margin_panel); save(sources, f"source_means_{size}.csv")
        matched = source_means(common); save(matched, f"common_panel_sources_{size}.csv")
        alg = panel.groupby(["algorithm", "source_id"])[METRICS+["absolute_adjusted_anisotropy"]].mean()
        cells_export=alg.copy()
        cells_export["n_completed"]=panel.groupby(["algorithm","source_id"]).size()
        attempts=known.loc[known.series==("primary_10x10" if size==10 else "secondary_20x20")]
        cells_export["n_attempted"]=attempts.groupby(["algorithm","source_id"]).size()
        cells_export["mean_blocks_read_all_attempts"]=attempts.groupby(["algorithm","source_id"]).units_read.mean()
        save(cells_export.reset_index(), f"algorithm_source_cells_{size}.csv")
        algorithm_export=alg.groupby("algorithm").mean().reindex(ALGORITHMS)
        algorithm_export["n_completed"]=panel.groupby("algorithm").size()
        algorithm_export["n_attempted"]=attempts.groupby("algorithm").size()
        algorithm_export["mean_blocks_read_all_attempts"]=attempts.groupby("algorithm").units_read.mean()
        save(algorithm_export.reset_index(), f"algorithm_means_{size}.csv")
        draw_profiles(alg,f"{size} × {size}",f"profiles_{size}.png",profile_limits)
        stats = dispersion(panel); save(stats, f"run_dispersion_{size}.csv")
        balance = panel if size == 10 else common
        weighted, unweighted = decompose(balance), decompose(balance, True)
        save(weighted, f"weighted_variance_{size}.csv")
        save(pd.concat([weighted, unweighted]), f"weighting_sensitivity_{size}.csv")
        draw_partition(weighted, f"Family-balanced variance partition on {size} × {size} grids",
                       f"variance_{size}.png")
        draw_distributions(panel, f"{size} × {size}", f"distributions_{size}.png", axis_limits)
        results[str(size)] = {"source_means": sources.to_dict("records"),
            "variance": weighted.to_dict("records"),
            "common_panel_summary": {m: float(matched[m].mean()) for m in METRICS},
            "actual_common_panel_completed": len(common), "common_panel_family_weight_sum": 9}
        # Fixed complete-panel source contrasts: all 55 pairs, same weights at both sizes.
        contrasts = []
        for l, r in combinations(SOURCES, 2):
            for m in METRICS:
                means = matched.set_index("source_id")[m]
                contrasts.append({"source_left": l, "source_right": r, "metric": m,
                    "family_balanced_left_minus_right": means[l]-means[r]})
        save(pd.DataFrame(contrasts), f"common_panel_source_contrasts_{size}.csv")
    # Main primary source contrasts and unchanged pairwise variant contrasts.
    p = panels[10]
    save(source_means(p), "primary_family_balanced_source_means.csv")
    c = p.groupby(["algorithm", "source_id"])[METRICS].mean()
    contrasts = []
    for l, r in combinations(SOURCES, 2):
        diff = c.xs(l, level="source_id")-c.xs(r, level="source_id")
        w = [weight(a) for a in diff.index]
        for m in METRICS:
            contrasts.append({"source_left": l, "source_right": r, "metric": m,
                "family_balanced_left_minus_right": np.average(diff[m], weights=w)})
    save(pd.DataFrame(contrasts), "primary_source_contrasts.csv")
    vc = []
    for l, r in combinations(ALGORITHMS, 2):
        for m in METRICS:
            vc.append({"variant_left": l, "variant_right": r, "metric": m,
                "matched_mean_difference": c.xs(l)[m].mean()-c.xs(r)[m].mean()})
    save(pd.DataFrame(vc), "primary_variant_contrasts.csv")
    control = data.loc[(data.source_role == "pseudo_iid_control") &
                       (data.series == "primary_10x10") & (data.status == "ok")]
    corpus_records = []
    for seed, part in control.groupby("corpus_seed"):
        means = part.groupby("algorithm")[METRICS].mean()
        values = np.average(means, weights=[weight(a) for a in means.index], axis=0)
        corpus_records.append({"corpus_seed": seed, **dict(zip(METRICS, values))})
    corpus = pd.DataFrame(corpus_records)
    save(corpus, "primary_control_corpus_means.csv")
    refs = []
    sm = source_means(p).set_index("source_id")
    for m in METRICS:
        lo, hi = corpus[m].quantile([.025, .975])
        refs.append({"metric": m, "n_corpora": len(corpus), "q025": lo, "q975": hi,
            "mean": corpus[m].mean(), "sample_sd": corpus[m].std(ddof=1),
            "below": "|".join(sm.index[sm[m] < lo]), "above": "|".join(sm.index[sm[m] > hi])})
    save(pd.DataFrame(refs), "primary_control_reference.csv")
    audit_cells()
    versions = {name: importlib.metadata.version(name)
        for name in ["numpy", "pandas", "Pillow"]}
    (OUT/"environment.json").write_text(json.dumps({"python": sys.version,
        "platform": platform.platform(), "packages": versions, "raw_sha256": sha(RAW)}, indent=2)+"\n")
    (OUT/"summary.json").write_text(json.dumps(results, indent=2)+"\n")
    print(json.dumps({s: results[s]["variance"][:1] for s in results}, indent=2))


if __name__ == "__main__":
    main()
