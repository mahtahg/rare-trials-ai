You are extracting data for a pre-registered meta-research study of drug-repurposing trials in rare diseases and WHO neglected tropical diseases (NTDs). Follow these definitions exactly. Use only the trial record and the reference data provided; do not use outside knowledge to override the reference data. When the record does not support a judgement, answer "uncertain" and give a low confidence.

DEFINITIONS
1. condition_category
   - "rare": at least one studied condition is a disease with Orphanet point prevalence <= 5 per 10,000 (the reference data lists candidate Orphanet matches and how each was found; "broader" MeSH matches need confirmation from the condition text).
   - "ntd": at least one studied condition is a WHO NTD group (Buruli ulcer; Chagas disease; dengue; dracunculiasis; echinococcosis; foodborne trematodiases; human African trypanosomiasis; leishmaniasis; leprosy; lymphatic filariasis; mycetoma, chromoblastomycosis and other deep mycoses; noma; onchocerciasis; rabies; scabies and other ectoparasitoses; schistosomiasis; soil-transmitted helminthiases; snakebite envenoming; taeniasis/cysticercosis; trachoma; yaws).
   - "both", or "neither" (e.g. the trial studies a common condition and the rare match is incidental, or the participants are healthy volunteers).
2. For each drug intervention: repurposed = true if the active ingredient had a regulatory approval (reference: ChEMBL max_phase 4 and first_approval year) BEFORE the trial start year AND the trial's condition is not among the drug's approved indications. Vaccines, placebo, diagnostics and supplements without drug approval are "not_applicable". If the ingredient is unmatched in reference data, use "uncertain".
3. stop_reasons (only if a why_stopped text is present; else []): any of
   "insufficient_accrual", "funding", "sponsor_business_decision", "drug_supply", "efficacy_futility", "safety",
   "regulatory_ethics_contractual", "logistics_site_investigator", "covid19", "scientific_landscape_changed", "other".
   primary_stop_reason = the first reason stated, or "not_stated".
4. funder_type, from lead sponsor and collaborators: "industry", "academic_hospital", "government", "nonprofit_foundation", "mixed" (industry plus non-industry), or "unclear".

Return one object per trial, in the order given, matching the JSON schema.
