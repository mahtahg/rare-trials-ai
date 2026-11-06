# rare-trials-ai

Open infrastructure and research for drug development in rare and neglected tropical diseases (NTDs).

- **`biomcp`**: MCP servers that give Claude (or any MCP client) traceable access to six public biomedical sources.
- **`eval/`**: a benchmark of 254 questions grounded in real clinical-development needs, with gold answers computed independently from source data.
- **`project6/`**: a pre-registered meta-research study of stalled drug-repurposing trials, with LLM-assisted extraction validated against blinded dual human review.

## biomcp servers

| Server | Source | Tools |
|---|---|---|
| `biomcp-ctgov` | ClinicalTrials.gov API v2 | `ctgov_search_trials`, `ctgov_get_trial`, `ctgov_data_version` |
| `biomcp-opentargets` | Open Targets Platform (GraphQL) | `opentargets_search`, `opentargets_disease_targets`, `opentargets_disease_drugs`, `opentargets_drug` |
| `biomcp-chembl` | ChEMBL REST | `chembl_search_molecules`, `chembl_get_molecule`, `chembl_mechanisms`, `chembl_indications` |
| `biomcp-fda` | openFDA (Drugs@FDA, SPL labels) | `fda_generic_availability`, `fda_label` |
| `biomcp-europepmc` | Europe PMC | `europepmc_search`, `europepmc_get_article` |
| `biomcp-orphanet` | Orphadata API (CC-BY-4.0) | `orphanet_lookup`, `orphanet_prevalence` |
| `biomcp-all` | all of the above | 17 tools |

Every tool returns the same envelope:

```json
{"data": {...}, "total": 42, "next_page_token": "...", "notes": ["caveats, proxies, truncation"],
 "provenance": [{"source": "chembl", "url": "https://www.ebi.ac.uk/chembl/api/data/molecule/CHEMBL1431.json",
                 "status": 200, "retrieved_at": "2026-11-03T19:46:02+00:00", "source_version": "ChEMBL_37", "sha256": "..."}]}
```

The envelope exists so an answer can be traced to the exact request behind it:

- `data: null` means the entity does not exist. It is never an empty guess.
- Derived judgements (US generic availability as an off-patent proxy, EU rarity) state the rule they applied in `notes`.

### Install

```bash
pip install "git+https://github.com/mahtahg/rare-trials-ai"
```

Claude Desktop (`claude_desktop_config.json`), or any MCP client:

```json
{"mcpServers": {"biomcp": {"command": "biomcp-all"}}}
```

Claude Code: `claude mcp add biomcp -- biomcp-all`. For a shared HTTP endpoint: `biomcp-all --transport streamable-http --port 8000`.

No API keys are needed; all sources are public. The client throttles each host politely and retries 429 and 5xx responses with backoff.

### Reproducibility

`BIOMCP_CASSETTE_MODE=record|replay|auto` records every HTTP response to `tests/cassettes/`, or replays it from there. Replayed tests run offline and give identical results.

CI runs a live contract check against every upstream API weekly. These tests have already caught real schema drift:

- Open Targets replaced `knownDrugs` with `drugAndClinicalCandidates`.
- ChEMBL files mechanisms under parent compounds.

## Eval

`eval/build_questions.py` samples rare diseases from Orphanet (EU definition, exact MONDO mapping) and the WHO NTD list. It then builds 13 question types, covering trial-registry facts, feasibility counts, disease-target evidence, drug approval and generic status, multi-hop repurposing questions, and non-existent entities.

Gold answers come from raw source data through code that is independent of the tools under test. A clinician rates every question for realism, and about 10% of gold answers are spot-checked by hand.

`eval/harness.py` runs each question under three conditions, with the same model, system prompt and turn cap. Only the tools differ:

| Condition | Tools |
|---|---|
| `no_tools` | none |
| `web_search` | Claude Code WebSearch/WebFetch |
| `biomcp` | the biomcp MCP server |

Runs use headless Claude Code authenticated with a Claude subscription token (`CLAUDE_CODE_OAUTH_TOKEN`). The harness refuses to start if `ANTHROPIC_API_KEY` is set.

`eval/score.py` reports:

- deterministic accuracy with Wilson confidence intervals;
- paired McNemar tests and bootstrap CIs between conditions;
- hallucinated-identifier rate, with every emitted NCT/CHEMBL/PMID checked live;
- for biomcp, the share of identifiers that never appeared in a tool output;
- calibration (ECE, Brier), cost and latency.

`eval/compare.py` builds the cross-run tables (`eval/results/COMPARISON.md` for the reviewed set, `all_COMPARISON.md` for the full set). `eval/process_fabrication.py` screens no-tools answers for narrated tool use. `eval/review/` holds the question review, the gold audit with archived primary-source payloads (`gold_audit.md`) and the workbook builders.

### Results (full set, 314 questions, one run each)

| | No tools | Web search | Servers |
|---|---|---|---|
| Base tier, Sonnet 5.5 | 46.9% | 81.9% | 100% |
| Base tier, Haiku 5.5 | 38.6% | 78.3% | 97.2% |
| Hard tier, Sonnet 5.5 | 36.7% | 73.3% | 90.0% |
| Hard tier, Haiku 5.5 | 23.3% | 70.0% | 88.3% |

The servers beat web search in every row (paired McNemar p ≤ 0.013). No server or web-search answer cited a non-existent identifier. Without tools, Haiku narrated tool calls that never ran in 7 of 314 answers (Sonnet 0 of 314).

## Project 6

See [`project6/PROTOCOL.md`](project6/PROTOCOL.md). The pipeline runs in four stages:

1. Deterministic cohort building.
2. ChEMBL/FDA drug normalisation.
3. LLM extraction with a frozen prompt and pinned model.
4. A draw-once stratified validation sample for blinded dual human extraction.
5. Analysis (`pipeline/analyze.py`): stall proportions with Wilson CIs by stratum and subgroup, sensitivity analyses, logistic regression, Rogan–Gladen correction. `results/prelim_ctgov_det/` is a PRELIMINARY run on ClinicalTrials.gov with the deterministic repurposing rule, made before validation; see `DEVIATIONS.md`.

## Licence

Code: MIT. Data retains its source licences: ClinicalTrials.gov is public domain; Orphanet is CC-BY-4.0; ChEMBL is CC-BY-SA-3.0; Open Targets is CC0; Europe PMC metadata follows its own terms; openFDA follows openFDA terms.
