"""Turn eval/questions.jsonl into a write batch for the review artifact's `questions` collection.

Flags a seeded, stratified ~10% spot-check sample (>=2 per template) for gold verification.
Writes eval/review_seed.json: {"spot_check_ids": [...], "ops": [{"op": "set", "path": "questions/<id>", "data": {...}}]}
"""

from __future__ import annotations

import json
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def gold_display(q: dict) -> str:
    g = q["gold"]
    if q["answer_type"] == "notfound":
        return "Does not exist (the model should say so)"
    if q["answer_type"] == "enrollment":
        return f'{g["count"]} ({g["type"]})'
    if isinstance(g, list):
        return ", ".join(map(str, g))
    if isinstance(g, bool):
        return "Yes" if g else "No"
    return str(g)


def main() -> int:
    src = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "eval/questions.jsonl")
    qs = [json.loads(line) for line in src.read_text().splitlines() if line.strip()]
    rng = random.Random(20261103)
    by = defaultdict(list)
    for q in qs:
        by[q["template"]].append(q["id"])
    spot = set()
    for _t, ids in sorted(by.items()):
        spot |= set(rng.sample(ids, min(len(ids), max(2, round(0.1 * len(ids))))))
    ops = []
    for i, q in enumerate(qs):
        ops.append({"op": "set", "path": f"questions/{q['id']}", "data": {
            "order": i, "template": q["template"], "question": q["question"], "answer_format": q.get("answer_format"),
            "gold_display": gold_display(q), "gold_sources": q.get("gold_sources", [])[:3], "spot_check": q["id"] in spot,
            "population": q.get("population", "rare"),
        }})
    out = ROOT / "eval/review_seed.json"
    out.write_text(json.dumps({"spot_check_ids": sorted(spot), "ops": ops}, ensure_ascii=False))
    print(f"{len(ops)} questions, {len(spot)} spot checks -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
