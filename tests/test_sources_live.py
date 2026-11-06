"""Contract tests against real APIs.

In CI they run with network and RAREMCP_CASSETTE_MODE=record, committing cassettes.
Locally they replay those cassettes, so the suite is deterministic offline.
Assertions are biological/regulatory facts that should stay true across releases.
"""

import pytest

from raremcp.sources import chembl, ctgov, europepmc, fda, opentargets

pytestmark = pytest.mark.live


def _prov_ok(out):
    assert out["provenance"], "every result must carry provenance"
    for p in out["provenance"]:
        assert p["url"].startswith("https://") and p["status"] == 200


async def test_ctgov_search_and_get():
    out = await ctgov.search_trials(condition="Duchenne muscular dystrophy", statuses=["TERMINATED"], page_size=5)
    _prov_ok(out)
    assert out["total"] and out["total"] >= 5
    assert all(t["overall_status"] == "TERMINATED" for t in out["data"])
    nct = out["data"][0]["nct_id"]
    one = await ctgov.get_trial(nct)
    assert one["data"]["nct_id"] == nct
    assert "eligibility" in one["data"]


async def test_ctgov_filters_phase_and_dates():
    out = await ctgov.search_trials(condition="malaria", phases=["PHASE3"], start_from="2015-01-01", start_to="2016-12-31", page_size=10)
    assert out["data"]
    for t in out["data"]:
        assert "PHASE3" in t["phases"]
        assert t["start_date"][:4] in {"2015", "2016"}


async def test_ctgov_missing_trial():
    out = await ctgov.get_trial("NCT99999999")
    assert out["data"] is None


async def test_ctgov_version():
    out = await ctgov.version()
    assert "dataTimestamp" in out["data"]


async def test_opentargets_search_disease_and_targets():
    s = await opentargets.search("Duchenne muscular dystrophy", "disease", 5)
    _prov_ok(s)
    assert s["provenance"][0]["source_version"]
    did = s["data"][0]["id"]
    t = await opentargets.disease_targets(did, size=10)
    assert "DMD" in [x["symbol"] for x in t["data"]["targets"]]


async def test_opentargets_drug_metformin():
    d = await opentargets.drug("CHEMBL1431")
    assert d["data"]["name"].upper() == "METFORMIN"
    print("OT metformin stage:", d["data"]["max_clinical_stage"])
    assert d["data"]["is_approved"] is True
    assert d["data"]["indications"]


async def test_opentargets_disease_drugs():
    s = await opentargets.search("cystic fibrosis", "disease", 1)
    out = await opentargets.disease_drugs(s["data"][0]["id"], size=200)
    names = {r["drug"].upper() for r in out["data"]["rows"]}
    assert "IVACAFTOR" in names
    stages = {r["max_stage_for_disease"] for r in out["data"]["rows"]}
    print("OT stage values:", sorted(s for s in stages if s))


async def test_chembl_metformin():
    s = await chembl.search_molecules("metformin", 5)
    _prov_ok(s)
    assert s["data"][0]["pref_name"] == "METFORMIN"
    m = await chembl.get_molecule("CHEMBL1431")
    assert float(m["data"]["max_phase"]) == 4
    assert m["provenance"][0]["source_version"].startswith("ChEMBL_")
    mech = await chembl.mechanisms("CHEMBL941")  # imatinib: curated kinase-inhibitor mechanisms
    assert any(r["action_type"] == "INHIBITOR" for r in mech["data"])
    ind = await chembl.indications("CHEMBL1431")
    assert any("diabetes" in (r["mesh_heading"] or "").lower() for r in ind["data"])


async def test_fda_generic_and_label():
    g = await fda.generic_availability("metformin hydrochloride")
    _prov_ok(g)
    assert g["data"]["generic_available_us"] is True
    assert g["data"]["n_anda"] > 10
    lab = await fda.label("sirolimus")
    assert "lymphangioleiomyomatosis" in (lab["data"]["indications_and_usage"] or "").lower()


async def test_fda_unknown_ingredient():
    g = await fda.generic_availability("notarealdrugxyz")
    assert g["data"] is None


async def test_europepmc_search_and_get():
    s = await europepmc.search('"drug repurposing" AND "rare disease"', page_size=3, from_year=2020)
    _prov_ok(s)
    assert s["total"] > 50
    first = next(r for r in s["data"] if r["pmid"])
    a = await europepmc.get_article(first["pmid"])
    assert a["data"]["pmid"] == first["pmid"]
    assert a["data"]["title"] == first["title"]


async def test_orphanet_lookup_and_prevalence():
    from raremcp.sources import orphanet

    a = await orphanet.lookup("ORPHA:98896")
    _prov_ok(a)
    assert a["data"]["name"] == "Duchenne muscular dystrophy"
    assert "MONDO" in a["data"]["xrefs"]
    p = await orphanet.prevalence("98896")
    assert p["data"]["eu_rarity"]["rare_eu"] is True
    b = await orphanet.lookup("Duchenne muscular dystrophy")
    assert b["data"]["orpha_code"] == 98896
