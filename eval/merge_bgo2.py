"""Replace the BioMCP (biomcp_go) runs in the main result folders with the proxied re-run (bgo2-*).

The first BioMCP arm (6-8 November 2026) ran `biomcp serve` directly under Claude Code; the server exited about
5 s after each connection, so in-flight calls failed with "Connection closed" (350 of 628 runs affected;
eval/results/bgo-debug). The re-run (bgo2-*) used tools/bgo_proxy.py. This script archives the original
biomcp_go records of each main run to raw_biomcp_go_v1.jsonl (kept for audit) and puts the bgo2 records in
raw.jsonl, so every downstream script and the rescore workflow use the corrected arm unchanged. Idempotent.

    python eval/merge_bgo2.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "eval/results"
PAIRS = {"v1-sonnet": "bgo2-sonnet", "v1-haiku": "bgo2-haiku", "hard-sonnet": "bgo2-hard-sonnet", "hard-haiku": "bgo2-hard-haiku"}


def main() -> int:
    for main_run, new_run in PAIRS.items():
        raw, arch, new = RES / main_run / "raw.jsonl", RES / main_run / "raw_biomcp_go_v1.jsonl", RES / new_run / "raw.jsonl"
        if not new.exists():
            print(f"{new_run}: no results yet, skipped")
            continue
        rows = [json.loads(x) for x in raw.read_text().splitlines() if x.strip()]
        old = [r for r in rows if r["condition"] == "biomcp_go"]
        if not arch.exists():
            arch.write_text("".join(json.dumps(r) + "\n" for r in old))
        keep = [r for r in rows if r["condition"] != "biomcp_go"]
        add = [json.loads(x) for x in new.read_text().splitlines() if x.strip()]
        add = [r for r in add if r["condition"] == "biomcp_go"]
        for r in add:
            r["bgo_proxy"] = True
        raw.write_text("".join(json.dumps(r) + "\n" for r in keep + add))
        ok = {(r["qid"], r["model"]) for r in add if not r.get("error")}
        print(f"{main_run}: archived {len(old)} original biomcp_go records; added {len(add)} proxied ({len(ok)} jobs without error)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
