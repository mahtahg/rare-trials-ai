"""Probe every candidate endpoint and save real responses (truncated) for schema work.

Run on a machine with open internet (GitHub Actions). Output: probe/out/<name>.json
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import httpx

OUT = Path(__file__).parent / "out"
OUT.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "biomcp-probe/0.1 (+https://github.com/mahtahg/rare-trials-ai)"}
LIMIT = 150_000
BIG = {"ot_schema_full": 3_000_000}

OT = "https://api.platform.opentargets.org/api/v4/graphql"

GQL = {
    "ot_meta": "{ meta { name apiVersion { x y z } dataVersion { year month iteration } } }",
    "ot_search": '{ search(queryString: "Duchenne muscular dystrophy", entityNames: ["disease","drug","target"], page:{index:0,size:5}) { total hits { id entity name description } } }',
    "ot_disease_targets": '{ disease(efoId: "MONDO_0010679") { id name dbXRefs associatedTargets(page:{index:0,size:5}) { count rows { score target { id approvedSymbol approvedName } } } } }',
    "ot_disease_knowndrugs": '{ disease(efoId: "MONDO_0010679") { id name knownDrugs(size: 5) { uniqueDrugs count rows { drug { id name } phase status mechanismOfAction ctIds } } } }',
    "ot_drug": '{ drug(chemblId: "CHEMBL1431") { id name drugType maximumClinicalTrialPhase isApproved yearOfFirstApproval hasBeenWithdrawn synonyms tradeNames mechanismsOfAction { rows { mechanismOfAction actionType targets { id approvedSymbol } } } indications { count rows { maxPhaseForIndication disease { id name } } } } }',
    "ot_orphanet_id": '{ disease(efoId: "Orphanet_98896") { id name dbXRefs } }',
    "ot_mapids": '{ mapIds(queryTerms: ["Orphanet:98896", "ORPHA:324"], entityNames: ["disease"]) { mappings { term hits { id name } } } }',
    "ot_target_knowndrugs": '{ target(ensemblId: "ENSG00000198947") { id approvedSymbol knownDrugs(size: 5) { count rows { drug { id name isApproved } phase disease { id name } } } } }',
    "ot_drug_knowndrugs": '{ drug(chemblId: "CHEMBL1431") { knownDrugs(size: 3) { count rows { disease { id name } phase status } } } }',
    "ot_introspect_query": '{ __type(name: "Query") { fields { name } } }',
    "ot_schema_full": '{ __schema { types { name kind fields { name args { name } type { name kind ofType { name kind ofType { name kind ofType { name } } } } } } } }',
    "ot_disease_dacc": '{ disease(efoId: "MONDO_0009061") { id name drugAndClinicalCandidates { count } } }',
    "ot_introspect_disease": '{ __type(name: "Disease") { fields { name args { name } type { name kind ofType { name kind ofType { name } } } } } }',
    "ot_introspect_drug": '{ __type(name: "Drug") { fields { name args { name } type { name kind ofType { name kind ofType { name } } } } } }',
    "ot_introspect_target": '{ __type(name: "Target") { fields { name args { name } type { name kind ofType { name kind ofType { name } } } } } }',
}

GETS = {
    # ClinicalTrials.gov v2
    "ctg_version": "https://clinicaltrials.gov/api/v2/version",
    "ctg_study": "https://clinicaltrials.gov/api/v2/studies/NCT01908426",
    "ctg_search": "https://clinicaltrials.gov/api/v2/studies?query.cond=Duchenne&filter.overallStatus=TERMINATED&pageSize=3&countTotal=true",
    "ctg_search_adv": "https://clinicaltrials.gov/api/v2/studies?query.term=AREA%5BStartDate%5DRANGE%5B2015-01-01%2C2016-12-31%5D%20AND%20AREA%5BPhase%5DPHASE2&query.cond=malaria&pageSize=2&countTotal=true&fields=NCTId%2COverallStatus%2CWhyStopped%2CPhase",
    "ctg_study_docs": "https://clinicaltrials.gov/api/v2/studies?query.term=AREA%5BLargeDocHasSAP%5Dtrue&pageSize=1&fields=NCTId%2CLargeDocumentModule",
    "ctg_metadata": "https://clinicaltrials.gov/api/v2/studies/metadata",
    # ChEMBL
    "chembl_status": "https://www.ebi.ac.uk/chembl/api/data/status.json",
    "chembl_search": "https://www.ebi.ac.uk/chembl/api/data/molecule/search.json?q=metformin&limit=3",
    "chembl_mol": "https://www.ebi.ac.uk/chembl/api/data/molecule/CHEMBL1431.json",
    "chembl_mech": "https://www.ebi.ac.uk/chembl/api/data/mechanism.json?molecule_chembl_id=CHEMBL1431",
    "chembl_ind": "https://www.ebi.ac.uk/chembl/api/data/drug_indication.json?molecule_chembl_id=CHEMBL1431&limit=5",
    "chembl_synonym": "https://www.ebi.ac.uk/chembl/api/data/molecule.json?molecule_synonyms__molecule_synonym__iexact=glucophage",
    "chembl_approved_page": "https://www.ebi.ac.uk/chembl/api/data/molecule.json?max_phase=4&molecule_type=Small%20molecule&limit=2&offset=500",
    "chembl_target": "https://www.ebi.ac.uk/chembl/api/data/target/CHEMBL1293188.json",
    # openFDA
    "fda_drugsfda": 'https://api.fda.gov/drug/drugsfda.json?search=openfda.generic_name:"metformin"&limit=2',
    "fda_drugsfda_anda": 'https://api.fda.gov/drug/drugsfda.json?search=openfda.generic_name:"metformin hydrochloride"+AND+application_number:ANDA*&limit=1',
    "fda_label": 'https://api.fda.gov/drug/label.json?search=openfda.generic_name:"sirolimus"&limit=1',
    "fda_download_index": "https://api.fda.gov/download.json",
    "fda_orange_book_page": "https://www.fda.gov/drugs/drug-approvals-and-databases/orange-book-data-files",
    "fda_orphan_db": "https://www.accessdata.fda.gov/scripts/opdlisting/oopd/",
    # DailyMed
    "dailymed_spls": "https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json?drug_name=sirolimus&pagesize=2",
    # Europe PMC
    "epmc_search": "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=drug%20repurposing%20AND%20%22rare%20disease%22&format=json&pageSize=2&resultType=core",
    "epmc_article": "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:31740836%20AND%20SRC:MED&format=json&resultType=core",
    # Orphanet / Orphadata candidates
    "orpha_api_root": "https://api.orphadata.com/",
    "orpha_api_xref": "https://api.orphadata.com/rd-cross-referencing/orphacodes/98896?lang=en",
    "orpha_api_epi": "https://api.orphadata.com/rd-epidemiology/orphacodes/98896?lang=en",
    "orpha_api_name": "https://api.orphadata.com/rd-cross-referencing/orphacodes/names/Duchenne%20muscular%20dystrophy?lang=en",
    "orpha_api_epi_all": "https://api.orphadata.com/rd-epidemiology?lang=en",
    "orphadata_prev_xml": "https://www.orphadata.com/data/xml/en_product9_prev.xml",
    "orphadata_xref_xml": "https://www.orphadata.com/data/xml/en_product1.xml",
    # WHO ICTRP and other registries (Project 6)
    "ictrp_home": "https://trialsearch.who.int/",
    "ictrp_api": "https://trialsearch.who.int/api/Trial?TrialID=ISRCTN12345678",
    "who_ictrp_downloads": "https://www.who.int/tools/clinical-trials-registry-platform/network/who-data-set",
    "isrctn_api": "https://www.isrctn.com/api/query/format/default?q=malaria&limit=2",
    "euctr_ctis": "https://euclinicaltrials.eu/ctis-public-api/search",
    "anzctr": "https://www.anzctr.org.au/TrialSearch.aspx?searchTxt=malaria",
    "ctri": "https://ctri.nic.in/Clinicaltrials/advsearch.php",
    "aact_downloads": "https://aact.ctti-clinicaltrials.org/downloads",
    "aact_snapshots": "https://aact.ctti-clinicaltrials.org/pipe_files",
    "who_ictrp_dl_page": "https://www.who.int/tools/clinical-trials-registry-platform/network/who-data-set/downloading-records-from-the-ictrp-database",
    "who_ictrp_providers": "https://www.who.int/tools/clinical-trials-registry-platform/network/data-providers",
    "aact_home": "https://aact.ctti-clinicaltrials.org/",
    "euctr_search": "https://www.clinicaltrialsregister.eu/ctr-search/search?query=malaria",
    "drks_api": "https://drks.de/search/en",
    "pactr": "https://pactr.samrc.ac.za/",
    "jrct": "https://jrct.mhlw.go.jp/en-latest-list",
    "chictr": "https://www.chictr.org.cn/searchprojEN.html",
    # WHO NTD list
    "who_ntd": "https://www.who.int/health-topics/neglected-tropical-diseases",
    # MONDO / EBI OLS for mappings
    "ols_mondo": "https://www.ebi.ac.uk/ols4/api/search?q=Duchenne&ontology=mondo&rows=2",
}


def save(name: str, status: int | str, headers: dict, text: str) -> None:
    lim = BIG.get(name, LIMIT)
    rec = {
        "name": name,
        "status": status,
        "content_type": headers.get("content-type"),
        "content_length": headers.get("content-length"),
        "bytes": len(text),
        "text": text[:lim],
    }
    (OUT / f"{name}.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    print(f"{status!s:>5}  {len(text):>9}B  {name}")


def main() -> int:
    only = set(sys.argv[1:])
    with httpx.Client(headers=UA, timeout=40, follow_redirects=True) as c:
        for name, url in GETS.items():
            if only and name not in only:
                continue
            try:
                # big XML: stream only the head
                if url.endswith(".xml"):
                    with c.stream("GET", url) as r:
                        buf = b""
                        for chunk in r.iter_bytes():
                            buf += chunk
                            if len(buf) > LIMIT:
                                break
                        save(name, r.status_code, dict(r.headers), buf.decode("utf-8", "replace"))
                else:
                    r = c.get(url)
                    save(name, r.status_code, dict(r.headers), r.text)
            except Exception as exc:  # noqa: BLE001
                save(name, f"ERR {type(exc).__name__}", {}, str(exc))
            time.sleep(0.4)
        for name, q in GQL.items():
            if only and name not in only:
                continue
            try:
                r = c.post(OT, json={"query": q})
                save(name, r.status_code, dict(r.headers), r.text)
            except Exception as exc:  # noqa: BLE001
                save(name, f"ERR {type(exc).__name__}", {}, str(exc))
            time.sleep(0.3)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
