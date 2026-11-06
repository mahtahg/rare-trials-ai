"""All RareMCP tools in one server (convenient for Claude Desktop / agents)."""

from __future__ import annotations

import importlib

from raremcp.servers import make_server, run

MODULES = ["ctgov", "opentargets", "chembl", "fda", "europepmc", "orphanet"]

INSTRUCTIONS = (
    "Public biomedical data for rare and neglected disease drug development: ClinicalTrials.gov (ctgov_*), "
    "Open Targets (opentargets_*), ChEMBL (chembl_*), US FDA (fda_*), Europe PMC (europepmc_*) and Orphanet "
    "(orphanet_*). Typical repurposing workflow: resolve disease -> associated targets -> drugs acting on them -> "
    "approval and generic status -> existing trials -> literature."
)

server = make_server("raremcp-all", INSTRUCTIONS)
for _m in MODULES:
    try:
        importlib.import_module(f"raremcp.servers.{_m}").register(server)
    except ModuleNotFoundError as exc:  # optional module not yet present
        if exc.name != f"raremcp.servers.{_m}":
            raise


def main() -> None:
    run(server)


if __name__ == "__main__":
    main()
