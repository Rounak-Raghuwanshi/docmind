"""Retrieval evaluation for DocMind.

Asks every question in a dataset against /api/workspaces/{ws}/search in four retrieval
configurations and reports Hit@k and MRR, plus a recommended relevance-gate threshold.

    python eval/run_eval.py --email you@example.com --password ... --workspace <uuid>
    python eval/run_eval.py ... --label chunk400 --dataset eval/dataset.jsonl

Dataset: one JSON object per line
    {"question": "...", "document": "Income-Tax-Act.pdf", "page": 412}
    {"question": "...", "document": "...", "pages": [12, 13]}       # any of these pages
    {"question": "Who won the 1998 world cup?", "answerable": false} # tunes the gate

Only needs httpx:  pip install httpx
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import httpx

MODES = ["vector", "keyword", "hybrid", "hybrid_rerank"]
LABELS = {
    "vector": "Vector only",
    "keyword": "Keyword only (full-text)",
    "hybrid": "Hybrid (RRF)",
    "hybrid_rerank": "Hybrid + rerank",
}


@dataclass
class Item:
    question: str
    document: str | None
    pages: list[int]
    answerable: bool = True


@dataclass
class ModeResult:
    hits: int = 0
    reciprocal_ranks: list[float] = field(default_factory=list)
    latencies_ms: list[int] = field(default_factory=list)
    misses: list[str] = field(default_factory=list)


def load_dataset(path: Path) -> list[Item]:
    items = []
    for n, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip() or line.lstrip().startswith("//"):
            continue
        row = json.loads(line)
        answerable = row.get("answerable", True)
        pages = row.get("pages") or ([row["page"]] if "page" in row else [])
        if answerable and (not row.get("document") or not pages):
            sys.exit(f"{path}:{n}: answerable rows need 'document' and 'page' or 'pages'")
        items.append(Item(row["question"], row.get("document"), pages, answerable))
    return items


class Client:
    def __init__(self, api: str, email: str, password: str) -> None:
        self.http = httpx.Client(base_url=api.rstrip("/"), timeout=60)
        r = self.http.post("/api/auth/login", json={"email": email, "password": password})
        if r.status_code != 200:
            sys.exit(f"login failed: {r.status_code} {r.text}")
        self.http.headers["Authorization"] = f"Bearer {r.json()['access_token']}"

    def search(self, ws: str, query: str, mode: str, top_k: int) -> dict:
        for _ in range(10):
            r = self.http.post(f"/api/workspaces/{ws}/search", json={"query": query, "mode": mode, "top_k": top_k})
            if r.status_code == 429:  # respect the API's rate limit instead of failing
                time.sleep(float(r.headers.get("Retry-After", "5")))
                continue
            r.raise_for_status()
            return r.json()
        sys.exit("gave up after repeated rate limiting; run the API with RATE_LIMIT_ENABLED=false")


def is_hit(hit: dict, item: Item) -> bool:
    if (item.document or "").lower() != hit["filename"].lower():
        return False
    return any(hit["page_start"] <= p <= hit["page_end"] for p in item.pages)


def evaluate(client: Client, ws: str, items: list[Item], k: int, depth: int) -> tuple[dict[str, ModeResult], list[tuple[float, bool]]]:
    results = {m: ModeResult() for m in MODES}
    gate_scores: list[tuple[float, bool]] = []  # (top rerank score, answerable)
    for i, item in enumerate(items, start=1):
        print(f"\r  {i}/{len(items)}", end="", file=sys.stderr, flush=True)
        for mode in MODES:
            if not item.answerable and mode != "hybrid_rerank":
                continue
            data = client.search(ws, item.question, mode, depth)
            hits = data["hits"]
            if mode == "hybrid_rerank" and hits and hits[0]["rerank_score"] is not None:
                gate_scores.append((hits[0]["rerank_score"], item.answerable))
            if not item.answerable:
                continue
            res = results[mode]
            res.latencies_ms.append(data["retrieval_ms"] + data["rerank_ms"])
            rank = next((r for r, h in enumerate(hits, start=1) if is_hit(h, item)), None)
            res.reciprocal_ranks.append(1 / rank if rank else 0.0)
            if rank and rank <= k:
                res.hits += 1
            else:
                res.misses.append(item.question)
    print(file=sys.stderr)
    return results, gate_scores


def best_threshold(scores: list[tuple[float, bool]]) -> tuple[float, float] | None:
    """Threshold that best separates answerable from unanswerable questions."""
    if not any(not a for _, a in scores) or not any(a for _, a in scores):
        return None
    candidates = sorted({s for s, _ in scores})
    best = (candidates[0], 0.0)
    for i, t in enumerate(candidates):
        # gate passes if score >= t; try midpoints between observed scores
        cut = (t + candidates[i - 1]) / 2 if i else t - 0.01
        acc = sum((s >= cut) == a for s, a in scores) / len(scores)
        if acc > best[1]:
            best = (round(cut, 2), acc)
    return best


def report(results: dict[str, ModeResult], answerable: int, k: int, gate: list[tuple[float, bool]], label: str) -> str:
    lines = [
        f"### Retrieval eval — {label} ({datetime.now():%Y-%m-%d %H:%M})",
        "",
        f"{answerable} answerable questions · Hit@{k} = correct page in the top {k} · MRR over the top results",
        "",
        f"| Configuration | Hit@{k} | MRR | p50 latency |",
        "| --- | --- | --- | --- |",
    ]
    for mode in MODES:
        r = results[mode]
        hit = r.hits / answerable if answerable else 0
        mrr = statistics.mean(r.reciprocal_ranks) if r.reciprocal_ranks else 0
        p50 = statistics.median(r.latencies_ms) if r.latencies_ms else 0
        lines.append(f"| {LABELS[mode]} | {hit:.1%} | {mrr:.3f} | {p50:.0f} ms |")
    if gate:
        lines += ["", "**Relevance gate** (top rerank score):"]
        ans = [s for s, a in gate if a]
        una = [s for s, a in gate if not a]
        if ans:
            lines.append(f"- answerable: median {statistics.median(ans):.2f}, min {min(ans):.2f}")
        if una:
            lines.append(f"- unanswerable: median {statistics.median(una):.2f}, max {max(una):.2f}")
        if bt := best_threshold(gate):
            lines.append(f"- suggested `RELEVANCE_THRESHOLD={bt[0]}` (separates {bt[1]:.0%} of questions correctly)")
    misses = results["hybrid_rerank"].misses
    if misses:
        lines += ["", f"<details><summary>{len(misses)} misses for hybrid + rerank</summary>", ""]
        lines += [f"- {q}" for q in misses] + ["", "</details>"]
    return "\n".join(lines)


def main() -> None:
    here = Path(__file__).parent
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--api", default=os.environ.get("DOCMIND_API", "http://localhost:8000"))
    p.add_argument("--email", default=os.environ.get("DOCMIND_EMAIL"), required="DOCMIND_EMAIL" not in os.environ)
    p.add_argument("--password", default=os.environ.get("DOCMIND_PASSWORD"), required="DOCMIND_PASSWORD" not in os.environ)
    p.add_argument("--workspace", required=True)
    p.add_argument("--dataset", type=Path, default=here / "dataset.jsonl")
    p.add_argument("--k", type=int, default=5)
    p.add_argument("--depth", type=int, default=20, help="results fetched per query for MRR")
    p.add_argument("--label", default="default settings")
    args = p.parse_args()

    items = load_dataset(args.dataset)
    answerable = sum(i.answerable for i in items)
    print(f"Evaluating {len(items)} questions ({answerable} answerable) …", file=sys.stderr)
    client = Client(args.api, args.email, args.password)
    results, gate = evaluate(client, args.workspace, items, args.k, args.depth)
    md = report(results, answerable, args.k, gate, args.label)
    print(md)

    out = here / "results"
    out.mkdir(exist_ok=True)
    slug = "".join(c if c.isalnum() else "-" for c in args.label.lower()).strip("-")
    path = out / f"{datetime.now():%Y%m%d-%H%M}-{slug}.md"
    path.write_text(md + "\n")
    print(f"\nSaved {path}", file=sys.stderr)


if __name__ == "__main__":
    main()
