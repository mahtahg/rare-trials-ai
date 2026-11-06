"""Project 6, step 4: draw the human-validation sample (protocol §6.3). Run once, after prompts are frozen.

Stratified by condition group x status group; records with any LLM confidence < 0.7
are over-sampled 2:1 and carry inverse-probability weights for re-weighted estimates.
First 30 records = calibration set (joint extraction, excluded from agreement stats).
Writes project6/data/validation_sample.json with record ids, strata, weights, seed.
"""

from __future__ import annotations

import argparse
import gzip
import json
import random
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STALL_STATUSES = {"TERMINATED", "WITHDRAWN", "SUSPENDED"}


def status_group(r: dict) -> str:
    s = r.get("overall_status") or ""
    if s in STALL_STATUSES:
        return "stopped"
    if s == "COMPLETED":
        return "completed"
    return "ongoing_or_unknown"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cohort", default=str(ROOT / "project6/data/cohort_ctgov.jsonl.gz"))
    ap.add_argument("--llm", default=str(ROOT / "project6/data/llm_extract_v1.jsonl"))
    ap.add_argument("--n", type=int, default=350)
    ap.add_argument("--n-calibration", type=int, default=30)
    ap.add_argument("--seed", type=int, default=20261103)
    ap.add_argument("--out", default=str(ROOT / "project6/data/validation_sample.json"))
    a = ap.parse_args()
    if Path(a.out).exists():
        raise SystemExit("validation sample already drawn; refusing to redraw (protocol: draw once)")
    cal_p = ROOT / "project6/data/validation_calibration.json"
    cal_ids = set()
    if cal_p.exists():  # calibration drawn separately (deviation 2026-11-06): draw test records only
        cal_ids = {x["trial_id"] for x in json.loads(cal_p.read_text())["records"]}
        a.n, a.n_calibration = a.n - len(cal_ids), 0
    llm = {}
    for line in Path(a.llm).read_text().splitlines():
        if line.strip():
            x = json.loads(line)
            llm[x["trial_id"]] = x
    strata = defaultdict(list)
    with gzip.open(a.cohort, "rt") as f:
        for line in f:
            r = json.loads(line)
            x = llm.get(r["trial_id"])
            if x is None or r["trial_id"] in cal_ids:
                continue
            cg = "ntd" if r["match"]["ntd"] else "rare"
            confs = [x.get("condition_confidence", 1)] + [d.get("confidence", 1) for d in x.get("drugs", [])]
            low = min(confs) < 0.7
            strata[(cg, status_group(r), low)].append(r["trial_id"])
    rng = random.Random(a.seed)
    pop = {k: len(v) for k, v in strata.items()}
    # allocation proportional to stratum size, low-confidence strata weighted x2
    wsum = sum(n * (2 if k[2] else 1) for k, n in pop.items())
    alloc = {k: max(1, round(a.n * n * (2 if k[2] else 1) / wsum)) for k, n in pop.items()}
    picks = []
    for k, ids in sorted(strata.items()):
        m = min(alloc[k], len(ids))
        for tid in rng.sample(ids, m):
            picks.append({"trial_id": tid, "stratum": list(k), "weight": len(ids) / m})
    rng.shuffle(picks)
    picks = picks[: a.n]
    for i, p in enumerate(picks):
        p["set"] = "calibration" if i < a.n_calibration else "test"
    Path(a.out).write_text(json.dumps({
        "drawn_at": datetime.now(timezone.utc).isoformat(), "seed": a.seed, "n": len(picks),
        "population_by_stratum": {"|".join(map(str, k)): n for k, n in pop.items()},
        "records": picks}, indent=1))
    print(f"drew {len(picks)} ({a.n_calibration} calibration) from {sum(pop.values())} extracted records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
