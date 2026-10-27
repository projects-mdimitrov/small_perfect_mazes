"""Independent full-row audit of the new study's saved wall graphs."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "crossed_v1"
RUNS = DATA / "runs.csv"
MANIFEST = DATA / "manifest.json"
OUT = DATA / "independent_audit.json"
FOREGROUND = (
    "dead_end_fraction",
    "diameter_normalized",
    "adjusted_orientation_anisotropy",
    "solution_stretch",
)


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def bfs(adjacency: list[list[int]], root: int) -> tuple[list[int], int]:
    distances = [-1] * len(adjacency)
    distances[root] = 0
    queue = deque([root])
    farthest = root
    while queue:
        node = queue.popleft()
        for nxt in adjacency[node]:
            if distances[nxt] < 0:
                distances[nxt] = distances[node] + 1
                queue.append(nxt)
                if distances[nxt] > distances[farthest]:
                    farthest = nxt
    return distances, farthest


def independently_measure(row: dict[str, str]) -> dict[str, float]:
    cols, rows = int(row["cols"]), int(row["rows"])
    n = cols * rows
    walls = row["wall_code_hex"]
    assert len(walls) == n
    codes = [int(char, 16) for char in walls]
    adjacency = [[] for _ in range(n)]
    horizontal = vertical = 0
    for idx, code in enumerate(codes):
        x, y = idx % cols, idx // cols
        if y == 0:
            assert code & 1
        if x == cols - 1:
            assert code & 2
        if y == rows - 1:
            assert code & 4
        if x == 0:
            assert code & 8
        if x < cols - 1:
            other = codes[idx + 1]
            assert bool(code & 2) == bool(other & 8)
            if not (code & 2):
                adjacency[idx].append(idx + 1)
                adjacency[idx + 1].append(idx)
                horizontal += 1
        if y < rows - 1:
            other = codes[idx + cols]
            assert bool(code & 4) == bool(other & 1)
            if not (code & 4):
                adjacency[idx].append(idx + cols)
                adjacency[idx + cols].append(idx)
                vertical += 1
    assert horizontal + vertical == n - 1
    start_distances, a = bfs(adjacency, 0)
    assert all(distance >= 0 for distance in start_distances)
    diameter_distances, b = bfs(adjacency, a)
    degrees = [len(neighbors) for neighbors in adjacency]
    assert sum(degrees) == 2 * (n - 1)
    start = int(row["solution_start_index"])
    goal = int(row["solution_goal_index"])
    end_distances, _ = bfs(adjacency, start)
    manhattan = abs(start % cols - goal % cols) + abs(start // cols - goal // cols)
    horizontal_density = horizontal / (rows * (cols - 1))
    vertical_density = vertical / (cols * (rows - 1))
    return {
        "dead_end_fraction": degrees.count(1) / n,
        "diameter_normalized": diameter_distances[b] / (n - 1),
        "adjusted_orientation_anisotropy":
            (horizontal_density - vertical_density) / (horizontal_density + vertical_density),
        "solution_stretch": end_distances[goal] / manhattan,
    }


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert sha256(RUNS.read_bytes()) == manifest["runs_csv_sha256"]
    for source_id, info in manifest["sources"].items():
        path = ROOT.parent / info["file"]
        raw = path.read_bytes()
        assert len(raw) == info["digit_count"], source_id
        assert sha256(raw) == info["sha256"], source_id
        assert all(48 <= char <= 57 for char in raw), source_id
    assert sha256((ROOT.parent / "maze_analytics_lab-15.html").read_bytes()) == manifest["html_sha256"]
    assert sha256((ROOT / "protocol.md").read_bytes()) == manifest["protocol_sha256"]
    assert sha256((ROOT / "run_crossed_study.js").read_bytes()) == manifest["runner_sha256"]

    counts: Counter[str] = Counter()
    by_series_algorithm: Counter[tuple[str, str, str]] = Counter()
    observed: set[tuple[str, str, str, str, int]] = set()
    controls_by_seed: defaultdict[str, set[str]] = defaultdict(set)
    failed: list[str] = []
    with RUNS.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for line_no, row in enumerate(reader, start=2):
            try:
                series = row["series"]
                algorithm = row["algorithm"]
                source = row["source_id"]
                seed = row["corpus_seed"]
                index = int(row["window_index"])
                key = (series, source, seed, algorithm, index)
                assert key not in observed
                observed.add(key)
                assert algorithm in manifest["algorithms"]
                assert row["study_id"] == manifest["study_id"]
                assert row["digit_phase"] == "0"
                size = next(item for item in manifest["size_design"] if item["series"] == series)
                assert int(row["cols"]) == size["cols"]
                assert int(row["rows"]) == size["rows"]
                assert 0 <= index < size["windows"]
                assert int(row["units_budget"]) == size["budget"]
                assert int(row["digit_start"]) == 5 * index * size["budget"]
                assert int(row["digit_end_exclusive"]) == 5 * (index + 1) * size["budget"]
                assert 0 <= int(row["units_read"]) <= size["budget"]
                assert 0 <= int(row["rejected_units"]) <= int(row["units_read"])
                if source == "control_pseudo_iid_decimal":
                    assert seed
                    controls_by_seed[seed].add(row["source_sha256"])
                else:
                    assert not seed
                    assert row["source_sha256"] == manifest["sources"][source]["sha256"]
                status = row["status"]
                assert status in ("ok", "stream_exhausted")
                if status == "ok":
                    assert row["algorithm_completed"] == "true"
                    assert row["perfect_maze"] == "true"
                    assert not row["error_code"]
                    expected_hash = sha256(
                        f"maze-wall-hex-v1\n{size['cols']}x{size['rows']}\n{row['wall_code_hex']}".encode("ascii")
                    )
                    assert row["wall_sha256"] == expected_hash
                    independent = independently_measure(row)
                    for metric in FOREGROUND:
                        assert abs(float(row[metric]) - independent[metric]) < 1e-12, metric
                else:
                    assert algorithm in ("wilson", "aldous")
                    assert series == "secondary_20x20"
                    assert row["algorithm_completed"] == "false"
                    assert row["perfect_maze"] == "false"
                    assert int(row["units_read"]) == size["budget"]
                    assert not row["wall_code_hex"] and not row["wall_sha256"]
                    assert all(not row[metric] for metric in FOREGROUND)
                counts[status] += 1
                by_series_algorithm[(series, algorithm, status)] += 1
            except Exception as exc:
                failed.append(f"line {line_no}: {type(exc).__name__} {exc}")
                if len(failed) >= 20:
                    break
    assert not failed, "\n".join(failed)
    assert sum(counts.values()) == manifest["rows"] == 40320
    assert dict(counts) == manifest["statuses"]
    assert len(controls_by_seed) == 64
    assert all(len(hashes) == 1 for hashes in controls_by_seed.values())
    for source in [*manifest["sources"], "control_pseudo_iid_decimal"]:
        seeds = [""] if source != "control_pseudo_iid_decimal" else list(controls_by_seed)
        for seed in seeds:
            for size in manifest["size_design"]:
                if source == "control_pseudo_iid_decimal" and int(seed.rsplit("/", 1)[-1]) > size["controls"]:
                    continue
                for algorithm in manifest["algorithms"]:
                    for index in range(size["windows"]):
                        assert (size["series"], source, seed, algorithm, index) in observed
    report = {
        "status": "pass",
        "row_count": sum(counts.values()),
        "status_counts": dict(counts),
        "independently_recomputed_metrics": list(FOREGROUND),
        "complete_wall_graphs_checked": counts["ok"],
        "unique_run_keys": len(observed),
        "source_files_hash_checked": len(manifest["sources"]),
        "control_corpora": len(controls_by_seed),
        "by_series_algorithm": [
            {"series": series, "algorithm": algorithm, "status": status, "count": count}
            for (series, algorithm, status), count in sorted(by_series_algorithm.items())
        ],
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "by_series_algorithm"}))


if __name__ == "__main__":
    main()
