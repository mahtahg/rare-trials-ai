"""Merge sharded open-model results (raw.shard{i}of{n}.jsonl) into raw.jsonl so score.py can read them.

    python eval/merge_shards.py eval/results/open-gemma4
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    d = Path(sys.argv[1])
    parts = sorted(d.glob("raw.shard*of*.jsonl"))
    lines = [ln for p in parts for ln in p.read_text().splitlines() if ln.strip()]
    (d / "raw.jsonl").write_text("\n".join(lines) + "\n")
    print(f"{d}: merged {len(parts)} shards, {len(lines)} records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
