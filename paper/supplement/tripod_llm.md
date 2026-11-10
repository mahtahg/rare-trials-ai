## Supplementary Note 1. TRIPOD-LLM checklist

Checklist: TRIPOD-LLM (Gallifant et al., Nat. Med. 31, 60–69, 2025), 19 items and their subitems as published. Item wording is paraphrased; the answers are also entered on the official fillable checklist from the TRIPOD-LLM website.

**Research design categories that apply:** LLM methods (augmenting models with tools; no change to model weights) and LLM evaluation. Not de novo development, and not evaluation in a dedicated healthcare setting. **LLM task categories:** long-form question answering and information retrieval. Items limited to other designs or tasks are marked "Not applicable", with the reason. Locations refer to sections of the main manuscript (M) or this Supplementary Information (SI).

### Title and abstract

| Item | Requirement (paraphrased) | Applies | Where and what is reported |
|---|---|---|---|
| 1 | Identify the study as developing, tuning or evaluating an LLM, with the task, population and outcome | Yes | Title: language models with tools; clinical-development question answering; rare and neglected tropical diseases |
| 2 | Abstract following TRIPOD-LLM for Abstracts | Yes | Abstract (unstructured, 150 words, as the journal requires): objective, tools and sources, models, conditions, question set, number of runs, main accuracy results with P values, main limitation (shared error) and conclusion |

### Introduction

| Item | Requirement (paraphrased) | Applies | Where and what is reported |
|---|---|---|---|
| 3a | Healthcare use case, rationale and existing approaches | Yes | M, Introduction paragraphs 1–2: information needs of rare-disease and NTD clinical-development teams; limits of parametric memory; tool-using models (GeneGPT, Toolformer); prior MCP evaluations |
| 3b | Target population, intended use in the care pathway and intended users | Yes | M, Introduction paragraph 1 (clinical-development and repurposing teams); Discussion, final paragraph (information look-up with human checking of cited records; not for decisions about individual patients) |
| 4 | Objectives, including whether development, tuning or evaluation | Yes | M, Introduction paragraph 3: build open MCP tools and a question set, and evaluate two existing models with four tool conditions; no model training or fine-tuning (Methods, Conditions and models) |

### Methods

| Item | Requirement (paraphrased) | Applies | Where and what is reported |
|---|---|---|---|
| 5a | Data sources for development, tuning or evaluation, and why chosen | Yes | M, Methods, Servers and Question set and gold answers: ClinicalTrials.gov, Open Targets, ChEMBL, openFDA, Europe PMC, Orphadata; Orphanet disorders with MONDO cross-references; WHO-listed NTDs |
| 5b | Data points and their distribution | Yes | M, Results, Question set and runs; Fig. 1; Table 1 (18 templates, tier, n, sources, answer types); SI Table 1 |
| 5c | Dates of the oldest and newest text used | Yes | M, Methods: gold answers computed from live sources on 3–4 November 2026; audit re-fetches in November 2026; each question stores its retrieval time; runs 3–10 November 2026 |
| 5d | Preprocessing and quality checks, and whether consistent across groups | Yes | M, Methods, Question set and gold answers (deterministic code separate from the servers; non-existent identifiers confirmed by HTTP 404) and Gold audit and correction (41-question re-derivation; full Drugs@FDA re-derivation); the same rules for rare-disease and NTD questions |
| 5e | Missing and imbalanced data; reasons for omitting data | Yes | M, Results (41 unparseable no-tools answers scored incorrect); Methods, Conditions and models (172 infrastructure-failed attempts re-run); Methods, Question screening (10 exclusions, sensitivity only); rarity template balanced 10/10 |
| 6a | LLM name, version and training cut-off | Yes | M, Methods, Conditions and models: Claude Sonnet 5.5 (claude-sonnet-5-5) and Claude Haiku 5.5 (claude-haiku-5-5); published reliable knowledge cut-off June 2026; served model confirmed from logs |
| 6b | Development details: architecture, training, fine-tuning, alignment (LLM methods) | Yes, partly | M, Methods, Servers: architecture of the tool layer (17 read-only MCP tools, response envelope, provenance, retries, record/replay). No training, fine-tuning or alignment was done |
| 6c | How text was generated: prompting, output consistency, inference settings | Yes | M, Methods, Conditions and models: one shared system prompt (full text in repository); default sampling of headless Claude Code; 20 turns; 600 s timeout; one run per question, model and condition, so consistency was not measured (stated as a limitation) |
| 6d | Initial and post-processed outputs | Yes | M, Methods, Outcomes: answer read from a final JSON block; unparseable blocks scored incorrect; raw outputs, tool calls and tool outputs archived (Data availability) |
| 6e | Classification: how probabilities and thresholds were derived | Not applicable | Not a classification or forecasting task. Stated confidence was used only for calibration (M, Methods, Outcomes) |
| 7a | Quality metrics for generated output against a reference | Yes | M, Table 1 (per-template scoring rules: exact match, tolerance, set F1, token F1, abstention); Methods, Outcomes (identifier validity, grounding, calibration) |
| 7b | Relevance of metrics to deployment; correlation with human evaluation | Yes | M, Discussion paragraphs 1 and 6: metrics measure retrieval of source facts, not clinical truth. No human evaluation of outputs, so no correlation with human judgement is reported |
| 7c | Outcome definition, how predictions were computed, inference dates for closed models | Yes | M, Methods, Outcomes and Conditions and models: inference 3–10 November 2026 (RareMCP 0.1.1 re-run 8 November; BioMCP condition re-run 9–10 November after a client–server connection fault) |
| 7d | Subjective assessment: assessors, instructions, agreement | Not applicable | All scoring was automatic. The AI-assisted question screening is described in M, Methods, Question screening; no human expert rating or inter-rater agreement is reported |
| 7e | Comparison with other LLMs, humans or benchmarks | Yes | M, Methods, Conditions and models and Statistics: two models; no tools, web search and an external MCP server (BioMCP 0.9.3, behind a pass-through proxy) as comparators; paired tests. No human comparator |
| 8a | How text was labelled, with guidelines | Yes | M, Methods, Question set and gold answers: gold answers computed by deterministic code from raw source responses; rules in Table 1; code in repository |
| 8b | Number of annotators, proportion double-annotated, inter-annotator agreement | Yes | No human annotators. Re-derivation by separate code: 41/41 agreement on a stratified sample; all 58 Drugs@FDA-dependent answers re-derived with a broader search, 8 changed (M, Methods, Gold audit and correction; SI Table 4) |
| 8c | Annotator background, or characteristics of a labelling model | Yes | Labels from deterministic Python code (repository); the language model used for screening is named in M, Methods, Question screening and Use of language models in this study |
| 9a | Prompt design, curation and selection | Yes | M, Methods, Conditions and models: one prompt for all conditions, written before the main runs and not iterated on evaluation results |
| 9b | Data used to develop prompts | Yes | No evaluation questions were used to develop the prompt (M, Methods, Conditions and models) |
| 10 | Preprocessing before summarisation | Not applicable | No summarisation task |
| 11 | Instruction tuning or alignment: instructions, data, interface, evaluators | Not applicable | No instruction tuning or alignment was done |
| 12 | Compute resources | Yes | M, Methods, Conditions and models: GitHub-hosted Linux runners, two runs at a time; about 13 h summed run time; about 4.7 million output tokens; API-equivalent cost about US$41 |
| 13 | Ethics body and consent, or waiver | Yes | M, Methods, Ethics and reporting: public, non-identifiable data only; no human participants; approval not required |
| 14a | Funding and funders' role | Yes | M, Acknowledgements: no specific funding |
| 14b | Conflicts of interest for all authors | Yes | M, Competing interests: none |
| 14c | Protocol access, or that none was prepared | Yes (reported although not required for this design) | M, Methods, Ethics and reporting: no protocol published in advance; post hoc analyses labelled |
| 14d | Registration, or that the study was not registered | Yes (as 14c) | M, Methods, Ethics and reporting: not registered |
| 14e | Data availability | Yes | M, Data availability: questions, gold answers, corrections, audit payloads, raw logs and scores (GitHub; Zenodo archive) |
| 14f | Code availability | Yes | M, Methods, Code availability: RareMCP 0.1.1, generators, harness and analysis code under the MIT licence |
| 15 | Patient and public involvement | Yes (as 14c) | M, Methods, Ethics and reporting: none |

### Results

| Item | Requirement (paraphrased) | Applies | Where and what is reported |
|---|---|---|---|
| 16a | Flow of participants or records, numbers with and without outcome | Not applicable | No patient or EHR data. Flow of questions and runs: M, Results, Question set and runs (314 questions, 2,512 runs, 41 unparseable answers) |
| 16b | Characteristics of the data overall and by source and split | Not applicable | No patient data. Question-set characteristics: Table 1; SI Tables 1 and 3 |
| 16c | Comparison of key variables between development and evaluation data | Not applicable | No development data; no model was trained |
| 16d | Numbers of participants and events in each analysis | Not applicable | No patient data. The n for each analysis is given in Tables 2–4, SI Tables 1–3 and the text |
| 17 | Performance against pre-specified metrics and human evaluation | Yes | M, Results; Figs. 2 and 3; Tables 2–4; SI Tables 1–3 and 5 |
| 18 | Results of any updating, including the updated model's performance | Yes | The tool, not the model, was updated: RareMCP 0.1.1 (Drugs@FDA fix), post hoc re-run of 58 questions (M, Results, A shared error between a tool and the gold answers; Fig. 3; Table 3) |

### Discussion

| Item | Requirement (paraphrased) | Applies | Where and what is reported |
|---|---|---|---|
| 19a | Interpretation, including fairness, in light of objectives and prior work | Yes | M, Discussion paragraphs 1–5; rare-disease versus NTD performance in M, Results, Rare diseases and NTDs, and SI Table 3 |
| 19b | Limitations and their effect on bias, uncertainty and generalisability | Yes | M, Discussion paragraph 6 |
| 19c | Known data challenges for the task (representation, missingness, harmonisation, bias) | Yes | M, Results and Discussion: missing openFDA metadata in older Drugs@FDA records; several prevalence estimates per disorder; source drift; small NTD subset |
| 19d | Intended use: input, end users, autonomy and human oversight | Yes | M, Discussion, final paragraph: look-up support for clinical-development and research teams, with a person checking the cited records via provenance; not for decisions about individual patients |
| 19e | How poor-quality or unavailable input is assessed and handled | Yes | Non-existent identifiers used to test abstention (M, Methods, Question set and gold answers; Results, Identifiers, grounding and calibration); retries and provenance in M, Methods, Servers |
| 19f | User interaction requirements and expertise | Yes | M, Discussion, final paragraph: any MCP-compatible client, no credentials needed; users check cited records |
| 19g | Next steps for applicability and generalisability | Yes | M, Discussion, final paragraph: repeat runs, other model families and clients, independent expert review, use by repurposing teams |
