"""Descriptive orthogonal partitions of frozen completed maze observations.

Equal family and source contributions are preserved in the secondary series by
giving completed run ajw weight q_a W/m_aj. This is a definition of a conditional
descriptive estimand, not imputation, inverse-probability weighting, or a test.
"""
from pathlib import Path
import json
import importlib.util

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RAW = ROOT / "data/crossed_v1/runs.csv"
OUT = HERE / "outputs"
spec = importlib.util.spec_from_file_location("archived_analysis", ROOT / "revision_v12/analysis_v12.py")
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)
ALGORITHMS, SOURCES, METRICS = old.ALGORITHMS, old.SOURCES, old.VMETRICS
LABEL = "Window within irrational source"
COMPONENTS = ["algorithm_percent", "source_percent", "interaction_percent", "window_within_irrational_source_percent"]


def partition(panel, nominal_windows, equal_variants=False, check_projection=False):
    algorithms = [a for a in ALGORITHMS if a in set(panel.algorithm)]
    index = pd.MultiIndex.from_product([algorithms, SOURCES], names=["algorithm", "source_id"])
    counts = panel.groupby(["algorithm", "source_id"]).size().reindex(index)
    assert counts.notna().all() and counts.ge(1).all() and counts.le(nominal_windows).all()
    assert panel.status.eq("ok").all()
    assert panel[METRICS].notna().all().all()
    assert not panel.duplicated(["algorithm", "source_id", "window_index"]).any()
    q = np.array([1. if equal_variants else old.weight(a) for a in algorithms])
    ai = panel.algorithm.map(dict(zip(algorithms, range(len(algorithms))))).to_numpy()
    ji = panel.source_id.map(dict(zip(SOURCES, range(len(SOURCES))))).to_numpy()
    m = counts.to_numpy().reshape(len(algorithms), len(SOURCES))
    v = q[ai] * nominal_windows / m[ai, ji]
    total_weight = nominal_windows * len(SOURCES) * q.sum()
    assert np.isclose(v.sum(), total_weight)
    grouped_weight = np.zeros_like(m, dtype=float)
    np.add.at(grouped_weight, (ai, ji), v)
    assert np.allclose(grouped_weight, nominal_windows * q[:, None])
    records = []
    for metric in METRICS:
        y = panel[metric].to_numpy()
        cm = panel.groupby(["algorithm", "source_id"])[metric].mean().reindex(index).to_numpy().reshape(m.shape)
        am = cm.mean(axis=1)
        sm = np.average(cm, weights=q, axis=0)
        grand = np.average(am, weights=q)
        effects = np.column_stack([am[ai] - grand, sm[ji] - grand,
            cm[ai, ji] - am[ai] - sm[ji] + grand, y - cm[ai, ji]])
        direct = np.sum(v[:, None] * effects ** 2, axis=0)
        between = [nominal_windows * len(SOURCES) * np.sum(q * (am - grand) ** 2),
                   nominal_windows * q.sum() * np.sum((sm - grand) ** 2),
                   nominal_windows * np.sum(q[:, None] * (cm-am[:, None]-sm[None, :]+grand) ** 2)]
        ss = np.array(between + [direct[3]])
        total = np.sum(v * (y - grand) ** 2)
        assert np.allclose(ss, direct, rtol=1e-11, atol=1e-11)
        assert np.isclose(ss.sum(), total, rtol=1e-11, atol=1e-11)
        assert np.all(ss >= 0)
        cross = effects.T @ (v[:, None] * effects)
        off_diagonal = cross - np.diag(np.diag(cross))
        assert np.max(np.abs(off_diagonal)) < max(1., total) * 1e-11
        projection_check = None
        if check_projection:
            # Independent weighted least-squares projection. Reverse main-effect
            # order to verify orthogonality under the explicit completed-cell weights.
            design_a = np.column_stack([np.ones(len(y)), np.eye(len(algorithms))[ai, 1:]])
            design_j = np.column_stack([np.ones(len(y)), np.eye(len(SOURCES))[ji, 1:]])
            design_both = np.column_stack([design_a, design_j[:, 1:]])
            sqrt_v = np.sqrt(v)
            def sse(design):
                beta = np.linalg.lstsq(design * sqrt_v[:, None], y * sqrt_v, rcond=None)[0]
                return np.sum(v * (y - design @ beta) ** 2)
            sse_a, sse_j, sse_additive = sse(design_a), sse(design_j), sse(design_both)
            projected = [total-sse_a, sse_a-sse_additive, sse_additive-direct[3], direct[3]]
            assert np.allclose(projected, ss, rtol=1e-9, atol=1e-9)
            assert np.isclose(total-sse_j, ss[1], rtol=1e-9, atol=1e-9)
            assert np.isclose(sse_j-sse_additive, ss[0], rtol=1e-9, atol=1e-9)
            projection_check = "Weighted least-squares components agree; reversing main-effect order does not change shares"
        records.append({"metric": metric,
            "scheme": "equal_variants_completed_cell_balanced" if equal_variants else "family_and_completed_cell_balanced",
            "variant_levels": len(algorithms), "family_weight_sum": float(q.sum()),
            "nominal_windows": nominal_windows, "actual_completed": len(panel),
            "minimum_completed_in_cell": int(m.min()), "maximum_completed_in_cell": int(m.max()),
            "total_observation_weight": float(total_weight), "ss_total": float(total),
            "ss_algorithm": float(ss[0]), "ss_source": float(ss[1]), "ss_interaction": float(ss[2]),
            "ss_window_within_irrational_source": float(ss[3]),
            **dict(zip(COMPONENTS, map(float, 100 * ss / total))),
            "maximum_absolute_weighted_cross_product": float(np.abs(off_diagonal).max()),
            "projection_check": projection_check})
    return pd.DataFrame(records)


def draw_partition(frame, size, filename):
    # Rebuild a scientific chart from numeric shares, not from an edited bitmap.
    image = Image.new("RGB", (1750, 730), "white")
    draw = ImageDraw.Draw(image)
    colors = ["#165c9b", "#dd8f20", "#b54352", "#9aa8b8"]
    draw.text((45, 25), f"Family-balanced variance partition on {size} × {size} grids", font=old.font(37, True), fill="#111111")
    draw.text((45, 80), "Binary Tree orientations: family weight 1/4 each; other variants: family weight 1", font=old.font(25), fill="#444444")
    if size == 20:
        draw.text((45, 118), "Completed windows reweighted within each algorithm–source combination", font=old.font(24), fill="#444444")
    left = np.zeros(len(frame))
    for key, color in zip(COMPONENTS, colors):
        values = frame[key].to_numpy()
        for i, value in enumerate(values):
            top = 180 + i * 80
            x0, x1 = 490 + left[i]*11.8, 490 + (left[i]+value)*11.8
            draw.rectangle((x0, top, x1, top+46), fill=color)
            if value > 6:
                draw.text(((x0+x1)/2, top+23), f"{value:.1f}%", anchor="mm", font=old.font(26), fill="white" if key == COMPONENTS[0] else "black")
        left += values
    assert np.allclose(left, 100)
    for i, metric in enumerate(frame.metric):
        draw.text((45, 187+i*80), old.MLABELS[metric], font=old.font(28), fill="#111111")
    draw.text((490, 586), "Share of weighted run-level sum of squares (%)", font=old.font(27), fill="#333333")
    cursor = 300
    for label, color in zip(["Variant", "Source", "Interaction", LABEL], colors):
        draw.rectangle((cursor, 655, cursor+25, 680), fill=color)
        draw.text((cursor+40, 651), label, font=old.font(27), fill="#111111")
        cursor += 40 + draw.textbbox((0, 0), label, font=old.font(27))[2] + 42
    assert cursor < 1750, cursor
    image.save(filename, dpi=(300, 300))


def analyse():
    raw = pd.read_csv(RAW, usecols=["series", "source_role", "source_id", "algorithm", "window_index", "status"] + METRICS)
    known = raw[raw.source_role.eq("known_irrational")]
    primary = known[known.series.eq("primary_10x10") & known.status.eq("ok")]
    secondary = known[known.series.eq("secondary_20x20") & known.status.eq("ok")]
    assert len(primary) == 4928 and len(secondary) == 2446
    primary_results = partition(primary, 32)
    results = partition(secondary, 16, check_projection=True)
    sensitivity = partition(secondary, 16, equal_variants=True)
    complete_results = partition(secondary[secondary.algorithm.isin(old.COMMON)], 16)
    for actual, filename in [(primary_results, "weighted_variance_10.csv"), (complete_results, "weighted_variance_20.csv")]:
        archived = pd.read_csv(ROOT / "revision_v12/outputs/tables" / filename)
        for current, prior in zip(COMPONENTS, ["algorithm_percent", "source_percent", "interaction_percent", "within_cell_percent"]):
            assert np.allclose(actual[current], archived[prior], rtol=0, atol=1e-10)
    expected = pd.read_csv(ROOT.parent / "reference_results/current_reanalysis/current_source_means_20.csv").set_index("source_id")
    source_means = secondary.groupby(["algorithm", "source_id"])[METRICS].mean()
    for source_id in SOURCES:
        block = source_means.xs(source_id, level="source_id").reindex(ALGORITHMS)
        q = np.array([old.weight(a) for a in ALGORITHMS])
        assert np.allclose(np.average(block, axis=0, weights=q), expected.loc[source_id, METRICS].to_numpy())
    OUT.mkdir(parents=True, exist_ok=True)
    data = {"completed_observations": 2446, "planned_observations": 2464,
            "cell_count": 154, "family_weight_sum": 11,
            "observation_weight": "q_a * 16 / m_aj for completed runs only",
            "definition": "Window within irrational source is variation among completed windows within a fixed algorithm–source combination; it is not a separately estimated window-index effect",
            "family_balanced": results.to_dict("records"), "equal_variants": sensitivity.to_dict("records"),
            "cell_completion_counts_and_weights": [
                {"algorithm": algorithm, "source_id": source, "completed": int(count), "attempted": 16,
                 "family_variant_weight": old.weight(algorithm),
                 "completed_observation_weight": old.weight(algorithm) * 16 / int(count),
                 "equal_variant_completed_observation_weight": 16 / int(count)}
                for (algorithm, source), count in secondary.groupby(["algorithm", "source_id"]).size().items()],
            "checks": ["Raw rows unchanged", "Every algorithm-source cell has completed runs", "All 2446 completed known-source secondary runs included", "Four orthogonal shares sum to 100", "No missing topology imputed", "Independent weighted least-squares projection agrees", "Primary shares and archived complete-panel shares reproduced", "Cell-balanced source means agree with the frozen numerical source reference"]}
    (OUT / "secondary_variance.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    draw_partition(primary_results, 10, OUT / "figure5.png")
    draw_partition(results, 20, OUT / "figure10.png")
    return primary_results, results, sensitivity, data


if __name__ == "__main__":
    _, results, _, _ = analyse()
    print(results[["metric"] + COMPONENTS].to_json(orient="records", indent=2))
