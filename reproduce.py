"""Portable, non-destructive entry point for the frozen crossed maze experiment.

The frozen maze implementation, runner, raw data and digits are unchanged.
Analysis scripts have documented packaging adaptations and require no manuscript.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
PACKAGE = Path(__file__).resolve().parent
ART = Path("article_all_algorithms_v1")
RAW_REL = ART / "data/crossed_v1/runs.csv"


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def verify():
    inventory = json.loads((PACKAGE / "SHA256SUMS.json").read_text(encoding="utf-8"))
    errors = []
    for rel, expected in inventory["files"].items():
        path = (PACKAGE / rel).resolve()
        if not path.is_relative_to(PACKAGE):
            raise ValueError(f"Unsafe inventory path: {rel}")
        if not path.is_file() or sha(path) != expected:
            errors.append(rel)
    if errors:
        raise RuntimeError("Missing or changed package files: " + ", ".join(errors))
    manifest = json.loads((PACKAGE / ART / "data/crossed_v1/manifest.json").read_text())
    assert sha(PACKAGE / RAW_REL) == manifest["runs_csv_sha256"]
    assert sha(PACKAGE / "maze_analytics_lab-15.html") == manifest["html_sha256"]
    assert sha(PACKAGE / ART / "run_crossed_study.js") == manifest["runner_sha256"]
    assert sha(PACKAGE / ART / "protocol.md") == manifest["protocol_sha256"]
    for info in manifest["sources"].values():
        path = PACKAGE / info["file"]
        assert sha(path) == info["sha256"] and path.stat().st_size == info["digit_count"]
    result = {"status": "pass", "files_checked": len(inventory["files"]),
              "runs_csv_sha256": manifest["runs_csv_sha256"]}
    print(json.dumps(result), flush=True)
    return result


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def new_workspace(task, supplied=None):
    default = PACKAGE / "reproduced" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") + "_" + task)
    work = Path(supplied).resolve() if supplied else default
    if work.exists():
        raise FileExistsError(f"Use a NEW output directory, not {work}")
    if work == PACKAGE or PACKAGE.is_relative_to(work):
        raise ValueError("Output directory must not contain the package")
    work.mkdir(parents=True)
    return work


def copy_to(work, rel):
    source, target = PACKAGE / rel, work / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def stage(work, raw=False, analysis=False):
    for rel in [Path("maze_analytics_lab-15.html"), ART / "run_crossed_study.js", ART / "protocol.md"]:
        copy_to(work, rel)
    for path in (PACKAGE / "irrational_numbers").iterdir():
        if path.is_file():
            copy_to(work, path.relative_to(PACKAGE))
    if raw:
        for name in ("runs.csv", "manifest.json"):
            copy_to(work, ART / "data/crossed_v1" / name)
    if analysis:
        for rel in ["revision_v12/analysis_v12.py", "revision_v18/analysis_v18.py",
                    "revision_v21/analysis_v21.py", "audit_crossed_study.py"]:
            copy_to(work, ART / rel)
        copy_to(work, Path("analysis/minmax_plots.py"))
        copy_to(work, Path("reference_results/current_reanalysis/current_source_means_20.csv"))


def node_binary(value):
    result = shutil.which(value)
    if result:
        return result
    path = Path(value)
    if path.is_file():
        return str(path.resolve())
    raise FileNotFoundError("Node.js not found. Supply --node /absolute/path/to/node")


def self_test(node):
    subprocess.run([node_binary(node), str(PACKAGE / ART / "run_crossed_study.js"), "--self-test"],
                   cwd=PACKAGE, check=True)


def regenerate(work, node):
    stage(work)
    subprocess.run([node_binary(node), str(work / ART / "run_crossed_study.js"), "--run"],
                   cwd=work, check=True)
    expected = sha(PACKAGE / RAW_REL)
    actual = sha(work / RAW_REL)
    assert actual == expected, "Regenerated CSV differs from frozen observations"
    report = {"status": "pass", "runs_csv_byte_identical": True,
              "runs_csv_sha256": actual, "note": "Manifest timestamp is expected to differ."}
    save_json(work / "regeneration_check.json", report)
    return report


def compare_frames(actual_path, expected_path):
    import pandas as pd
    actual, expected = pd.read_csv(actual_path), pd.read_csv(expected_path)
    pd.testing.assert_frame_equal(actual, expected, check_dtype=False,
                                  check_exact=False, rtol=1e-11, atol=1e-11)


def analyse(work):
    import numpy as np
    import pandas as pd
    stage(work, raw=True, analysis=True)
    root = work / ART
    baseline = load("packaged_analysis_v12", root / "revision_v12/analysis_v12.py")
    baseline.main()
    for expected in (PACKAGE / ART / "revision_v12/outputs/tables").glob("*.csv"):
        compare_frames(root / "revision_v12/outputs/tables" / expected.name, expected)
    secondary = load("packaged_analysis_v18", root / "revision_v18/analysis_v18.py")
    secondary.analyse()
    current = load("packaged_analysis_v21", root / "revision_v21/analysis_v21.py")
    # Packaging-only portability change: numerical functions are untouched.
    current.font = baseline.font
    current.main()
    for expected in (PACKAGE / ART / "revision_v21/outputs").glob("*.csv"):
        compare_frames(root / "revision_v21/outputs" / expected.name, expected)

    raw = pd.read_csv(root / "data/crossed_v1/runs.csv", low_memory=False)
    raw["absolute_adjusted_anisotropy"] = raw.adjusted_orientation_anisotropy.abs()
    known = raw[raw.source_role.eq("known_irrational") & raw.status.eq("ok")].copy()
    out = root / "current_results"
    out.mkdir()
    # These are CURRENT all-variant source margins, not old complete-panel margins.
    for size in (10, 20):
        panel = known[known.cols.eq(size)]
        cells = panel.groupby(["algorithm", "source_id"])[current.METRICS].mean()
        rows = []
        for source in baseline.SOURCES:
            frame = cells.xs(source, level="source_id").reindex(current.ALGORITHMS)
            values = np.average(frame.to_numpy(), axis=0, weights=current.Q)
            rows.append({"source_id": source, **dict(zip(current.METRICS, values))})
        pd.DataFrame(rows).to_csv(out / f"current_source_means_{size}.csv", index=False, float_format="%.15g")
        for metric in ("dead_end_fraction", "diameter_normalized", "solution_stretch", "junction_fraction"):
            cell_means = panel.groupby(["algorithm", "source_id"])[metric].mean().unstack("source_id")
            cell_means = cell_means.reindex(index=current.ALGORITHMS, columns=baseline.SOURCES)
            deviations = cell_means.sub(cell_means.mean(axis=1), axis=0)
            # Cell fractions: percentage points. Diameter and stretch: unscaled.
            if metric.endswith("_fraction"):
                deviations *= 100
            deviations.to_csv(out / f"deviations_{size}_{metric}.csv", float_format="%.15g")

    boxplots = load("packaged_minmax", work / "analysis/minmax_plots.py")
    boxplots.FIGURES = out
    records = {size: boxplots.panel_summaries(known[known.cols.eq(size)], size) for size in (10, 20)}
    old = json.loads((PACKAGE / "reference_results/minmax_boxplots/config.json").read_text(encoding="utf-8"))
    limits = old["matched_axes"]
    for size in (10, 20):
        boxplots.draw_distributions(records[size], size, limits)
    save_json(out / "minmax_boxplot_data.json", {str(k): v for k, v in records.items()})
    for expected in (PACKAGE / "reference_results/current_reanalysis").glob("*.csv"):
        compare_frames(out / expected.name, expected)
    def compare_json(actual, expected, location="root"):
        if isinstance(expected, dict):
            assert actual.keys() == expected.keys(), location
            for key in expected:
                compare_json(actual[key], expected[key], location + "/" + str(key))
        elif isinstance(expected, list):
            assert len(actual) == len(expected), location
            for i, (x, y) in enumerate(zip(actual, expected)):
                compare_json(x, y, location + "/" + str(i))
        elif isinstance(expected, (int, float)) and not isinstance(expected, bool):
            assert np.isclose(actual, expected, rtol=1e-11, atol=1e-11), location
        else:
            assert actual == expected, location
    for relative in [ART / "revision_v18/outputs/secondary_variance.json",
                     ART / "revision_v21/outputs/analysis_v21.json"]:
        compare_json(json.loads((work / relative).read_text(encoding="utf-8")),
                     json.loads((PACKAGE / relative).read_text(encoding="utf-8")))
    compare_json(json.loads((out / "minmax_boxplot_data.json").read_text(encoding="utf-8")),
                 json.loads((PACKAGE / "reference_results/current_reanalysis/minmax_boxplot_data.json").read_text(encoding="utf-8")))
    report = {"status": "pass", "baseline_and_current_numeric_csvs_match": True,
              "current_source_margins_and_deviations_match": True, "scientific_json_outputs_match": True,
              "no_manuscript_required": True,
              "raw_sha256": sha(root / "data/crossed_v1/runs.csv"),
              "archive_raw_unchanged": sha(PACKAGE / RAW_REL),
              "font_override": "v21 uses the archived v12 Arial/DejaVu fallback; numerical code unchanged",
              "scope": "Recomputed statistics, deviations and scientific plots; no manuscript is required."}
    save_json(work / "analysis_check.json", report)
    return report


def audit(work):
    stage(work, raw=True)
    copy_to(work, ART / "audit_crossed_study.py")
    subprocess.run([sys.executable, "-B", "-X", "utf8", str(work / ART / "audit_crossed_study.py")],
                   cwd=work, check=True)
    return json.loads((work / ART / "data/crossed_v1/independent_audit.json").read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["verify", "self-test", "regenerate", "analyse", "audit"])
    parser.add_argument("--node", default="node", help="Node.js executable for self-test/regenerate")
    parser.add_argument("--out", help="NEW output folder; existing folders are never overwritten")
    args = parser.parse_args()
    verify()
    if args.command == "verify":
        return
    if args.command == "self-test":
        self_test(args.node)
        return
    work = new_workspace(args.command, args.out)
    if args.command == "regenerate":
        result = regenerate(work, args.node)
    elif args.command == "analyse":
        result = analyse(work)
    else:
        result = audit(work)
    verify()
    print(json.dumps({"output_directory": str(work), "result": result}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
