"""Project 6: draw the 30-record calibration set ahead of the main validation sample (deviation logged 2026-11-06).

The calibration set is extracted jointly by both reviewers to align on definitions and is excluded from
agreement statistics (protocol §6.3), so it does not depend on LLM confidence. It is drawn from the whole
ClinicalTrials.gov cohort, stratified by condition group x status group, with its own seed. The main draw
(draw_validation_sample.py) then excludes these trials and draws all 320 test records.

    python project6/pipeline/draw_calibration.py
"""

from __future__ import annotations

import gzip
import json
import random
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "project6/data/validation_calibration.json"
SEED, N = 20261106, 30


def status_group(s: str) -> str:
    return "stopped" if s in {"TERMINATED", "WITHDRAWN", "SUSPENDED"} else ("completed" if s == "COMPLETED" else "ongoing_or_unknown")


def main() -> int:
    if OUT.exists():
        raise SystemExit("calibration set already drawn; refusing to redraw")
    strata = defaultdict(list)
    recs = {}
    with gzip.open(ROOT / "project6/data/cohort_ctgov.jsonl.gz", "rt") as f:
        for line in f:
            r = json.loads(line)
            if not r["drugs"]:
                continue
            strata[("ntd" if r["match"]["ntd"] else "rare", status_group(r["overall_status"]))].append(r["trial_id"])
            recs[r["trial_id"]] = r
    rng = random.Random(SEED)
    # equal allocation across strata so calibration covers every combination (stopped trials exercise field 3)
    keys = sorted(strata)
    per = {k: N // len(keys) for k in keys}
    for k in keys[: N - sum(per.values())]:
        per[k] += 1
    picks = [{"trial_id": t, "stratum": list(k), "set": "calibration"} for k in keys for t in rng.sample(strata[k], min(per[k], len(strata[k])))]
    rng.shuffle(picks)
    OUT.write_text(json.dumps({"drawn_at": datetime.now(timezone.utc).isoformat(), "seed": SEED, "n": len(picks),
                               "population_by_stratum": {"|".join(k): len(v) for k, v in strata.items()}, "records": picks}, indent=1))
    print(f"drew {len(picks)} calibration records across {len(keys)} strata")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
