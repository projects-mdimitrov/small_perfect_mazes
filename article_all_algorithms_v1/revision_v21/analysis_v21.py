"""Read frozen observations and compare irrational and seeded control corpora.

No maze generation and no changes to existing inputs or earlier outputs.
All topology estimates are conditional on successful completion. Corpus means
are weighted equally within each input class; Binary Tree family weight is one.
"""
from pathlib import Path
from hashlib import sha256
import json

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RAW = ROOT / "data/crossed_v1/runs.csv"
OUT = HERE / "outputs"
ALGORITHMS = ["dfs", "prim", "kruskal", "wilson", "aldous", "hunt", "growing",
              "division", "eller", "sidewinder", "binary_ur", "binary_dr", "binary_ul", "binary_dl"]
LABELS = ["DFS", "Prim", "Kruskal", "Wilson", "Aldous-Broder", "Hunt and Kill", "Growing Tree",
          "Recursive Division", "Eller", "Sidewinder", "Binary UR", "Binary DR", "Binary UL", "Binary DL"]
METRICS = ["dead_end_fraction", "junction_fraction", "straight_fraction", "turn_fraction",
           "diameter_normalized", "adjusted_orientation_anisotropy", "absolute_adjusted_anisotropy", "solution_stretch"]
VAR_METRICS = [METRICS[i] for i in (0, 1, 4, 5, 7)]
VAR_LABELS = ["Dead-end cells (%)", "Branch cells (%)", "Normalized diameter", "Signed anisotropy", "Path stretch"]
COMPONENTS = ["algorithm_percent", "source_percent", "interaction_percent", "window_percent"]
Q = np.array([.25 if a.startswith("binary_") else 1. for a in ALGORITHMS])


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def partition(panel, windows):
    """Exact weighted descriptive SS partition with equal completed-cell weight."""
    sources = sorted(panel.corpus.unique())
    index = pd.MultiIndex.from_product([ALGORITHMS, sources], names=["algorithm", "corpus"])
    counts = panel.groupby(["algorithm", "corpus"]).size().reindex(index)
    assert counts.notna().all() and counts.between(1, windows).all()
    assert not panel.duplicated(["algorithm", "corpus", "window_index"]).any()
    ai = panel.algorithm.map(dict(zip(ALGORITHMS, range(14)))).to_numpy()
    si = panel.corpus.map(dict(zip(sources, range(len(sources))))).to_numpy()
    n = counts.to_numpy().reshape(14, len(sources))
    v = Q[ai] * windows / n[ai, si]
    assert np.isclose(v.sum(), windows * len(sources) * Q.sum())
    records = []
    for metric in VAR_METRICS:
        y = panel[metric].to_numpy()
        cm = panel.groupby(["algorithm", "corpus"])[metric].mean().reindex(index).to_numpy().reshape(n.shape)
        am = cm.mean(axis=1)
        sm = np.average(cm, axis=0, weights=Q)
        grand = np.average(am, weights=Q)
        effects = np.column_stack((am[ai] - grand, sm[si] - grand,
            cm[ai, si] - am[ai] - sm[si] + grand, y - cm[ai, si]))
        direct = np.sum(v[:, None] * effects**2, axis=0)
        ss = np.array([windows * len(sources) * np.sum(Q * (am - grand)**2),
            windows * Q.sum() * np.sum((sm - grand)**2),
            windows * np.sum(Q[:, None] * (cm - am[:, None] - sm[None, :] + grand)**2), direct[3]])
        total = np.sum(v * (y - grand)**2)
        assert np.allclose(ss, direct, atol=1e-10, rtol=1e-11)
        assert np.isclose(ss.sum(), total, atol=1e-10, rtol=1e-11)
        cross = effects.T @ (v[:, None] * effects)
        off = cross - np.diag(np.diag(cross))
        assert np.abs(off).max() < max(1., total) * 1e-11
        shares = 100 * ss / total
        assert np.all(shares >= 0) and np.isclose(shares.sum(), 100.)
        records.append({"metric": metric, "corpora": len(sources), "windows": windows,
            "completed": len(panel), "minimum_completed_per_cell": int(n.min()),
            "ss_total": float(total), "total_weight": float(v.sum()),
            "weighted_variance": float(total / v.sum()),
            "max_orthogonality_cross_product": float(np.abs(off).max()),
            **dict(zip(COMPONENTS, map(float, shares)))})
    return records


def font(size, bold=False):
    return ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf", size)


def draw_partition(groups, size):
    im = Image.new("RGB", (2100, 1120), "white")
    draw = ImageDraw.Draw(im)
    draw.text((42, 28), f"Variability partition on {size} × {size} grids", font=font(43, True), fill="#111111")
    draw.text((42, 89), "I: irrational digits     C: pseudorandom controls     Equal total weight per algorithmic family",
              font=font(32), fill="#333333")
    colors = ["#165c9b", "#dd8f20", "#b54352", "#9aa8b8"]
    left, width, top, pitch = 600, 1440, 172, 132
    for k in range(0, 101, 20):
        x = left + width * k / 100
        draw.line((x, top-8, x, top + pitch*4 + 92), fill="#e2e2e2", width=2)
        draw.text((x, 850), str(k), font=font(32), anchor="mt", fill="#333333")
    for i, label in enumerate(VAR_LABELS):
        y = top + i * pitch
        draw.text((42, y + 39), label, font=font(36), anchor="lm", fill="#111111")
        for j, kind in enumerate(("I", "C")):
            ybar = y + j*45
            draw.text((555, ybar+19), kind, font=font(31, True), anchor="mm", fill="#222222")
            offset = 0.
            for component, color in zip(COMPONENTS, colors):
                value = groups[kind][i][component]
                x0, x1 = left + width*offset/100, left + width*(offset+value)/100
                draw.rectangle((x0, ybar, x1, ybar+35), fill=color)
                if value >= 7:
                    draw.text(((x0+x1)/2, ybar+18), f"{value:.1f}%", font=font(30), anchor="mm",
                              fill="white" if component == "algorithm_percent" else "#111111")
                offset += value
            assert np.isclose(offset, 100.)
    draw.text((1320, 905), "Share of weighted run-level sum of squares (%)", font=font(32), anchor="mt", fill="#222222")
    legend = [("Algorithm", 300, 980), ("Source / control corpus", 880, 980),
              ("Algorithm × source / corpus", 300, 1042), ("Window within source / corpus", 1100, 1042)]
    for (label, x, y), color in zip(legend, colors):
        draw.rectangle((x, y, x+31, y+29), fill=color)
        draw.text((x+45, y-1), label, font=font(32), fill="#111111")
    im.save(OUT / f"comparison_variance_{size}.png", dpi=(300, 300))


def main():
    manifest = json.loads((ROOT / "data/crossed_v1/manifest.json").read_text())
    assert digest(RAW) == manifest["runs_csv_sha256"]
    OUT.mkdir(parents=True, exist_ok=True)
    columns = ["series", "source_role", "source_id", "corpus_seed", "algorithm", "window_index", "status", "units_read",
        "units_budget", "cols", "rows", "degree_1_count", "degree_2_straight_count", "degree_2_turn_count", "degree_3_count", "degree_4_count"]
    raw = pd.read_csv(RAW, usecols=columns + [m for m in METRICS if m != "absolute_adjusted_anisotropy"])
    raw = raw[raw.source_role.isin(["known_irrational", "pseudo_iid_control"])].copy()
    raw["absolute_adjusted_anisotropy"] = raw.adjusted_orientation_anisotropy.abs()
    raw["corpus"] = np.where(raw.source_role.eq("known_irrational"), raw.source_id, raw.corpus_seed)
    assert raw.corpus.notna().all()
    successful = raw[raw.status.eq("ok")]
    degrees = successful[["degree_1_count", "degree_2_straight_count", "degree_2_turn_count", "degree_3_count", "degree_4_count"]]
    assert np.array_equal(degrees.sum(axis=1), successful.cols * successful.rows)
    assert np.array_equal(successful.degree_1_count, successful.degree_3_count + 2*successful.degree_4_count + 2)
    expected = {10: {"I": (4928, 4928, 11), "C": (28672, 28672, 64)},
                20: {"I": (2464, 2446, 11), "C": (3584, 3562, 16)}}
    report = {"raw_sha256": digest(RAW),
        "metrics": METRICS, "algorithms": ALGORITHMS, "algorithm_labels": LABELS,
        "weighting": "Equal means per corpus then per variant; family weight 1 with 1/4 per Binary Tree orientation. Completed run partition weight q_a W/m_ac.",
        "block_consumption": "Mean over all attempts within each corpus, then equal-corpus mean; includes unfinished attempts.", "sizes": {}}
    for size, windows in ((10, 32), (20, 16)):
        result = {}
        for kind, role in (("I", "known_irrational"), ("C", "pseudo_iid_control")):
            attempts = raw[raw.cols.eq(size) & raw.source_role.eq(role)].copy()
            panel = attempts[attempts.status.eq("ok")].copy()
            attempted, completed, corpora = expected[size][kind]
            assert (len(attempts), len(panel), attempts.corpus.nunique()) == (attempted, completed, corpora)
            assert attempts.groupby(["algorithm", "corpus"]).size().eq(windows).all()
            assert attempts.units_budget.eq(6000 if size == 10 else 12000).all()
            cm = panel.groupby(["algorithm", "corpus"])[METRICS].mean()
            am = cm.groupby("algorithm").mean().reindex(ALGORITHMS)
            blocks = attempts.groupby(["algorithm", "corpus"]).units_read.mean().groupby("algorithm").mean()
            n_ok = panel.groupby("algorithm").size()
            n_all = attempts.groupby("algorithm").size()
            records = []
            for a, label in zip(ALGORITHMS, LABELS):
                records.append({"algorithm": a, "label": label, "completed": int(n_ok[a]), "attempted": int(n_all[a]),
                    **{m: float(am.loc[a, m]) for m in METRICS}, "blocks_read": float(blocks[a])})
            # Independent family-first representation checks the grand mean.
            fam = am.copy()
            fam.index = ["binary" if a.startswith("binary_") else a for a in am.index]
            grand = np.average(am.to_numpy(), axis=0, weights=Q)
            assert np.allclose(grand, fam.groupby(level=0).mean().mean().to_numpy(), atol=1e-14)
            part = partition(panel, windows)
            if kind == "I":
                old = pd.read_csv(ROOT / f"revision_v12/outputs/tables/algorithm_means_{size}.csv").set_index("algorithm").reindex(ALGORITHMS)
                assert np.allclose(old[METRICS].to_numpy(), am[METRICS].to_numpy(), atol=1e-13)
                if size == 10:
                    oldvar = pd.read_csv(ROOT / "revision_v12/outputs/tables/weighted_variance_10.csv")
                    for p, row in zip(part, oldvar.to_dict("records")):
                        assert all(np.isclose(p[k], row["within_cell_percent" if k == "window_percent" else k], atol=1e-10) for k in COMPONENTS)
                else:
                    oldvar = json.loads((ROOT / "revision_v18/outputs/secondary_variance.json").read_text())["family_balanced"]
                    for p, row in zip(part, oldvar):
                        assert all(np.isclose(p[k], row["window_within_irrational_source_percent" if k == "window_percent" else k], atol=1e-10) for k in COMPONENTS)
            result[kind] = {"attempted": attempted, "completed": completed, "corpora": corpora,
                "windows_per_corpus": windows, "algorithms": records, "grand": dict(zip(METRICS, map(float, grand))), "partition": part,
                "failures_by_algorithm": {str(a): int(n) for a, n in attempts[attempts.status.ne("ok")].groupby("algorithm").size().items()}}
            pd.DataFrame(records).to_csv(OUT / f"algorithm_means_{size}_{kind}.csv", index=False, float_format="%.15g")
            pd.DataFrame(part).to_csv(OUT / f"variance_partition_{size}_{kind}.csv", index=False, float_format="%.15g")
        differences = []
        for metric in METRICS:
            values = [(a, result["I"]["algorithms"][i][metric] - result["C"]["algorithms"][i][metric]) for i, a in enumerate(ALGORITHMS)]
            a, delta = max(values, key=lambda x: abs(x[1]))
            differences.append({"metric": metric, "max_absolute_algorithm_difference": abs(delta), "algorithm": a,
                "I_minus_C_at_maximum": delta, "family_balanced_I_minus_C": result["I"]["grand"][metric] - result["C"]["grand"][metric]})
        result["differences"] = differences
        report["sizes"][str(size)] = result
        draw_partition({k: result[k]["partition"] for k in ("I", "C")}, size)
    assert digest(RAW) == manifest["runs_csv_sha256"]
    (OUT / "analysis_v21.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({s: {"I_grand": r["I"]["grand"], "C_grand": r["C"]["grand"],
        "differences": r["differences"], "I_partition": r["I"]["partition"], "C_partition": r["C"]["partition"]}
        for s, r in report["sizes"].items()}, indent=2))


if __name__ == "__main__":
    main()
