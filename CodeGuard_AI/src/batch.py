"""Batch helpers: ranking, clusters, matrix ordering and summaries."""
from __future__ import annotations

from collections import Counter

import config


def top_pairs(results: list, n: int = 10) -> list:
    return sorted(results, key=lambda r: r.overall, reverse=True)[:n]


def _components(edges: list) -> list:
    """Connected components of a list of result edges (union-find)."""
    parent: dict = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for r in edges:
        parent[find(r.file_a)] = find(r.file_b)
    groups: dict = {}
    for r in edges:
        groups.setdefault(find(r.file_a), []).append(r)
    return list(groups.values())


def find_clusters(results: list, threshold: float, max_size: int = 10,
                  min_density: float = 0.5) -> list:
    """Groups of files linked by pairs scoring >= threshold.

    Plain connected components chain unrelated files together through weak
    links, so a component that is large (> max_size) or sparse (fewer than
    ``min_density`` of all possible pairs linked) is split by raising the
    threshold in 5-point steps. A group that cannot be refined is returned with
    ``loose=True``. Returns dicts: files, max, pairs, threshold, loose (largest
    group first). Singletons are omitted.
    """
    out: list = []

    def refine(edges: list, thr: float) -> None:
        files = {n for r in edges for n in (r.file_a, r.file_b)}
        n = len(files)
        possible = n * (n - 1) / 2
        density = len(edges) / possible if possible else 1.0
        if n <= max_size and density >= min_density:
            out.append({"files": sorted(files), "max": max(r.overall for r in edges),
                        "pairs": len(edges), "threshold": thr, "loose": False})
            return
        higher = [r for r in edges if r.overall >= thr + 5]
        if not higher or thr + 5 > 100:
            out.append({"files": sorted(files), "max": max(r.overall for r in edges),
                        "pairs": len(edges), "threshold": thr, "loose": True})
            return
        for comp in _components(higher):
            refine(comp, thr + 5)

    for comp in _components([r for r in results if r.overall >= threshold]):
        refine(comp, threshold)
    out.sort(key=lambda g: (len(g["files"]), g["max"]), reverse=True)
    return out


def similarity_matrix(names: list, results: list) -> list:
    index = {n: i for i, n in enumerate(names)}
    z = [[None] * len(names) for _ in names]
    for i in range(len(names)):
        z[i][i] = 100.0
    for r in results:
        if r.file_a in index and r.file_b in index:
            i, j = index[r.file_a], index[r.file_b]
            z[i][j] = z[j][i] = r.overall
    return z


def cluster_order(names: list, results: list) -> list:
    """Order files so similar ones sit next to each other (greedy chain)."""
    if len(names) <= 2:
        return list(names)
    score: dict = {}
    for r in results:
        score[(r.file_a, r.file_b)] = score[(r.file_b, r.file_a)] = r.overall
    best_total = {n: sum(score.get((n, m), 0) for m in names) for n in names}
    remaining = set(names)
    current = max(names, key=lambda n: best_total[n])
    order = [current]
    remaining.discard(current)
    while remaining:
        current = max(remaining, key=lambda m: (score.get((order[-1], m), 0), best_total[m]))
        order.append(current)
        remaining.discard(current)
    return order


def summarize(results: list) -> dict:
    """Counts and a one-paragraph text summary for a batch of results."""
    if not results:
        return {"pairs": 0, "text": "No pairs were compared.", "risk": {}, "average": 0.0}
    risk = Counter(r.risk for r in results)
    avg = sum(r.overall for r in results) / len(results)
    top = max(results, key=lambda r: r.overall)
    files = {n for r in results for n in (r.file_a, r.file_b)}
    text = (f"{len(results)} pair(s) from {len(files)} file(s) were compared. "
            f"{risk[config.RISK_HIGH]} pair(s) are in the High indicator band, "
            f"{risk[config.RISK_MODERATE]} Moderate and {risk[config.RISK_LOW]} Low; "
            f"the average similarity is {avg:.1f}%. The highest pair is "
            f"{top.file_a} and {top.file_b} at {top.overall:.1f}%.")
    return {"pairs": len(results), "text": text, "risk": dict(risk), "average": round(avg, 1)}
