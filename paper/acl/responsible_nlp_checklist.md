# ACL Responsible NLP Research checklist: answers for the ARR form

Section references are to `raremcp_acl.tex`. Items still to settle before submission are marked **TO DO**.

## A. For every submission
- **A1 Limitations discussed?** Yes. "Limitations" section, after the Discussion.
- **A2 Potential risks discussed?** Yes. Ethics statement covers misuse for individual-patient decisions and the clinically unsound "untested target drug" lists. Section 5.5 covers fabricated tool use. Section 6 covers "Retrieval is not judgement".

## B. Did you use or create scientific artifacts? Yes
- **B1 Cited the creators of artifacts used?** Yes. Sources: ClinicalTrials.gov, Open Targets, ChEMBL, openFDA, Europe PMC, Orphadata. Software: BioMCP and llama.cpp. Models: Claude, Gemma 4 and gpt-oss (§3, §4).
- **B2 License or terms discussed?** Yes.
  - All six sources are public and free to use. Each source's terms are cited by its home page.
  - Gemma 4 and gpt-oss-20b are Apache-2.0 (§4).
  - BioMCP is MIT-licensed (stated in its repository, checked 27 November 2026).
  - Our code and data will be released under MIT (Ethics statement).
- **B3 Use consistent with intended use?** Yes. All use is read-only look-up through public APIs. The released tools are for research look-up with human checking and not for patient care (Ethics statement).
- **B4 Personal or offensive content checked?** Yes. There are no personal data. Trial records, drug and disease data are public and contain no patient-level information (Ethics statement).
- **B5 Documentation of artifacts?** Yes.
  - §3 and Appendix A cover the 18 templates, sources, scoring rules and population.
  - The repository README covers the tool list, response envelope and installation.
- **B6 Statistics of data (splits, sizes)?** Yes. §3 gives 314 questions (254 base, 60 hard; 246 rare-disease, 48 NTD, 20 rarity) and Appendix A gives n per template. The benchmark has no training split.

## C. Did you run computational experiments? Yes
- **C1 Parameters and compute reported?**
  - Model sizes: Gemma 4 E4B (about 4B effective parameters) and gpt-oss-20b (about 21B total, 3.6B active). Claude model sizes are not public.
  - Compute is in Appendix D, "Compute". **TO DO:** add the open-model runner hours from the run logs.
- **C2 Experimental setup and hyperparameters?** Yes (§4).
  - Shared system prompt, 20-turn cap and timeouts.
  - Sampling: Claude Code defaults for Claude. Developer-recommended settings for the open models: Gemma temperature 1.0, top-p 0.95, top-k 64; gpt-oss temperature 1.0, top-p 1.0.
  - Context 32,768 tokens; tool-output cap 12,000 characters.
  - The prompt was not tuned on results.
- **C3 Descriptive statistics, error bars, number of runs?** Yes. Wilson 95% intervals, McNemar tests, paired bootstrap intervals and one run per cell (stated). A full repeat was made of the closed-model study (§5.7).
- **C4 Existing packages used, with versions?** Yes. MCP SDK 2.x, biomcp-cli 0.9.3 and Claude Code (version logged per run). The llama.cpp release tag and the weight revisions are recorded with every shard.

## D. Did you use human annotators or participants? Yes: three expert raters of the questions
- **D1 Full instructions given to raters?** **TO DO:** add the rating instructions (1–5 scales for clinical relevance, realism and gold-answer correctness, and their anchors) to the appendix or the repository.
- **D2 Recruitment and payment?** **TO DO:** state how the two independent raters were recruited and whether they were paid. One rater is an author.
- **D3 Consent and data use explained?** **TO DO:** state that the raters agreed to their ratings being used and released.
- **D4 Ethics review?** No approval was needed: no human-subjects data, only expert judgements about questions (Ethics statement). **TO DO:** confirm with KCL's research ethics office if unsure.
- **D5 Demographics of raters?** Professional background only: clinical pharmacologist (10 years' NHS experience), consultant epidemiologist, and a clinician–ML researcher (author). No other demographics were collected.

## E. AI assistants
- **E1 Use of AI assistants disclosed?** Yes, in the Ethics statement.
  - Claude Opus 5.5, through Claude Code, wrote most of the code, assisted with question screening and the gold audit, and drafted the paper under the authors' direction.
  - The authors checked the code, results and text.
