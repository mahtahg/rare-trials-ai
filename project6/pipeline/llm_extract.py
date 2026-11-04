"""Project 6, step 3: LLM-assisted extraction (tasks T1-T4 of the protocol).

Runs headless Claude Code on the Claude subscription (CLAUDE_CODE_OAUTH_TOKEN), never
the paid API. Prompt and schema are version-controlled and frozen before the
validation sample is drawn; the model id is pinned and recorded per output.
Resumable: re-running skips trials already extracted; stops cleanly at a usage limit.

    python project6/pipeline/llm_extract.py --model claude-sonnet-5-5 --batch 8
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROMPT_FILE = ROOT / "project6/prompts/extract_v1.md"
LIMIT_RE = re.compile(r"usage limit|rate limit|limit reached|hit your .{0,20}limit|resets \d|too many requests|429", re.IGNORECASE)

STOP = ["insufficient_accrual", "funding", "sponsor_business_decision", "drug_supply", "efficacy_futility", "safety",
        "regulatory_ethics_contractual", "logistics_site_investigator", "covid19", "scientific_landscape_changed", "other"]
SCHEMA = {
    "type": "object", "required": ["trials"],
    "properties": {"trials": {"type": "array", "items": {
        "type": "object",
        "required": ["trial_id", "condition_category", "condition_confidence", "drugs", "stop_reasons", "primary_stop_reason", "funder_type"],
        "properties": {
            "trial_id": {"type": "string"},
            "condition_category": {"enum": ["rare", "ntd", "both", "neither", "uncertain"]},
            "orpha_codes": {"type": "array", "items": {"type": "string"}},
            "ntd_groups": {"type": "array", "items": {"type": "string"}},
            "condition_confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "drugs": {"type": "array", "items": {"type": "object", "required": ["name", "repurposed", "confidence"], "properties": {
                "name": {"type": "string"}, "chembl_id": {"type": ["string", "null"]},
                "repurposed": {"enum": ["true", "false", "not_applicable", "uncertain"]},
                "reason": {"type": "string"}, "confidence": {"type": "number", "minimum": 0, "maximum": 1}}}},
            "stop_reasons": {"type": "array", "items": {"enum": STOP}},
            "primary_stop_reason": {"enum": STOP + ["not_stated"]},
            "funder_type": {"enum": ["industry", "academic_hospital", "government", "nonprofit_foundation", "mixed", "unclear"]},
            "funder_confidence": {"type": "number", "minimum": 0, "maximum": 1},
        }}}},
}


def record_view(r: dict, drug_map: dict) -> dict:
    ref = []
    for n in r["drugs"]:
        hit = drug_map["names"].get(n, {})
        prof = drug_map["parents"].get(hit.get("parent_chembl_id"), {}) if not hit.get("unmatched") else {}
        ref.append({"intervention": n, "chembl_parent": hit.get("parent_chembl_id"), "max_phase": prof.get("max_phase"),
                    "first_approval": prof.get("first_approval"), "approved_indications": prof.get("approved_indications", [])[:25]})
    return {
        "trial_id": r["trial_id"], "title": r["title"], "start_date": r["start_date"], "conditions": r["conditions"],
        "condition_mesh": r["condition_mesh"], "orphanet_candidates": r["match"]["rare"] + r["match"]["rare_broad_only"],
        "ntd_lexicon_hits": r["match"]["ntd"], "drug_reference": ref, "why_stopped": r["why_stopped"],
        "lead_sponsor": r["lead_sponsor"], "lead_sponsor_class": r["lead_sponsor_class"], "collaborators": r["collaborators"],
    }


def run_batch(batch: list[dict], model: str, prompt: str) -> tuple[list[dict] | None, str | None, bool]:
    msg = prompt + "\n\nTRIALS (JSON):\n" + json.dumps(batch, ensure_ascii=False)
    cmd = ["claude", "-p", msg, "--model", model, "--output-format", "json", "--json-schema", json.dumps(SCHEMA),
           "--tools", "", "--strict-mcp-config", "--no-session-persistence", "--setting-sources", "", "--max-turns", "3"]
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    p = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=tempfile.gettempdir(), timeout=900)
    try:
        res = json.loads(p.stdout)
    except json.JSONDecodeError:
        err = (p.stderr or p.stdout)[-800:]
        return None, err, bool(LIMIT_RE.search(err))
    if res.get("is_error"):
        err = str(res.get("result"))[:800]
        return None, err, bool(LIMIT_RE.search(err))
    out = res.get("structured_output")
    if out is None:
        try:
            out = json.loads(res.get("result") or "")
        except json.JSONDecodeError:
            return None, "no structured output", False
    return out.get("trials"), None, False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cohort", default=str(ROOT / "project6/data/cohort_ctgov.jsonl.gz"))
    ap.add_argument("--drug-map", default=str(ROOT / "project6/data/drug_map.json"))
    ap.add_argument("--out", default=str(ROOT / "project6/data/llm_extract_v1.jsonl"))
    ap.add_argument("--model", default="claude-sonnet-5-5")
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--max-minutes", type=float, default=300)
    a = ap.parse_args()
    if os.getenv("ANTHROPIC_API_KEY"):
        print("Refusing: ANTHROPIC_API_KEY set (would bill the API).", file=sys.stderr)
        return 2
    prompt = PROMPT_FILE.read_text()
    prompt_sha = hashlib.sha256((prompt + json.dumps(SCHEMA, sort_keys=True)).encode()).hexdigest()[:12]
    drug_map = json.loads(Path(a.drug_map).read_text())
    done = set()
    out_p = Path(a.out)
    if out_p.exists():
        done = {json.loads(line)["trial_id"] for line in out_p.read_text().splitlines() if line.strip()}
    recs = []
    with gzip.open(a.cohort, "rt") as f:
        for line in f:
            r = json.loads(line)
            if r["trial_id"] not in done:
                recs.append(record_view(r, drug_map))
    onc = re.compile(r"cancer|carcinoma|neoplasm|tumou?r|leuk(a)?emia|lymphoma|myeloma|sarcoma|glioma|blastoma|melanoma|"
                     r"malignan|myelodysplas|metasta", re.IGNORECASE)
    recs.sort(key=lambda v: bool(onc.search(" ".join(v["conditions"] + v["condition_mesh"]))))  # stable: non-oncology first
    print(f"{len(recs)} trials to extract (prompt {prompt_sha}, model {a.model})", flush=True)
    deadline = time.monotonic() + a.max_minutes * 60
    n = 0
    for i in range(0, len(recs), a.batch):
        if time.monotonic() > deadline:
            print("time budget reached; resume later", flush=True)
            break
        batch = recs[i:i + a.batch]
        trials, err, limited = run_batch(batch, a.model, prompt)
        if limited:
            print(f"USAGE LIMIT: {err[:200]}; stopping, resume later", flush=True)
            break
        if trials is None:
            print(f"batch {i}: error {err[:200]}", flush=True)
            continue
        ids = {b["trial_id"] for b in batch}
        with out_p.open("a") as f:
            for t in trials:
                if t.get("trial_id") in ids:
                    t.update({"_model": a.model, "_prompt_sha": prompt_sha, "_extracted_at": datetime.now(timezone.utc).isoformat()})
                    f.write(json.dumps(t, ensure_ascii=False) + "\n")
                    n += 1
        print(f"{i + len(batch)}/{len(recs)} extracted={n}", flush=True)
    remaining = len(recs) - n
    (out_p.parent / "llm_extract_v1.REMAINING").write_text(str(remaining))
    print(f"done {n}, remaining {remaining}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
