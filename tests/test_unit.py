import pytest

from raremcp.core.envelope import clip, dig
from raremcp.core.http import _canonical_url, _cassette_key
from raremcp.sources import ctgov


def test_build_query_phases_dates_sponsor():
    p = ctgov.build_query(condition="malaria", phases=["PHASE2", "phase3"], sponsor_class="other",
                          start_from="2010-01-01", statuses=["terminated"])
    assert p["query.cond"] == "malaria"
    assert p["filter.overallStatus"] == "TERMINATED"
    t = p["query.term"]
    assert "AREA[Phase]PHASE2 OR AREA[Phase]PHASE3" in t
    assert "AREA[LeadSponsorClass]OTHER" in t
    assert "AREA[StartDate]RANGE[2010-01-01,MAX]" in t


@pytest.mark.parametrize("kw", [{"phases": ["PHASE9"]}, {"statuses": ["DONE"]}, {"sponsor_class": "PHARMA"}, {}])
def test_build_query_rejects_bad_input(kw):
    with pytest.raises(ValueError):
        ctgov.build_query(**kw)


async def test_get_trial_rejects_malformed_id():
    with pytest.raises(ValueError):
        await ctgov.get_trial("NCT123")


def test_summarize_minimal_record():
    s = ctgov.summarize_study({
        "protocolSection": {
            "identificationModule": {"nctId": "NCT00000001", "briefTitle": "x"},
            "statusModule": {"overallStatus": "TERMINATED", "whyStopped": "Low accrual"},
            "designModule": {"enrollmentInfo": {"count": 4, "type": "ACTUAL"}, "phases": ["PHASE2"]},
            "contactsLocationsModule": {"locations": [{"country": "Kenya"}, {"country": "Kenya"}, {"country": "Uganda"}]},
        },
        "documentSection": {"largeDocumentModule": {"largeDocs": [{"typeAbbrev": "Prot_SAP", "hasSap": True, "filename": "Prot_SAP_000.pdf"}]}},
    })
    assert s["why_stopped"] == "Low accrual"
    assert s["n_sites"] == 3 and s["countries"] == ["Kenya", "Uganda"]
    assert s["documents"][0]["url"] == "https://cdn.clinicaltrials.gov/large-docs/01/NCT00000001/Prot_SAP_000.pdf"


def test_cassette_key_stable_and_param_order_independent():
    a = _canonical_url("https://x/y", {"b": 2, "a": 1, "c": None})
    b = _canonical_url("https://x/y", {"a": 1, "b": 2})
    assert a == b
    assert _cassette_key("GET", a, None) == _cassette_key("get", b, None)
    assert _cassette_key("POST", a, {"q": 1}) != _cassette_key("POST", a, {"q": 2})


def test_helpers():
    assert clip("a  b\n c") == "a b c"
    assert clip("x" * 10, 5) == "xxxx…"
    assert dig({"a": [{"b": 1}]}, "a", 0, "b") == 1
    assert dig({"a": []}, "a", 0, "b", default="z") == "z"


def test_orphanet_rarity_rule():
    from raremcp.sources.orphanet import classify_rarity

    pv = lambda c, g="Worldwide", t="Point prevalence": {
        "PrevalenceType": t, "PrevalenceClass": c, "PrevalenceGeographic": g, "PrevalenceValidationStatus": "Validated"}
    assert classify_rarity([pv("1-9 / 100 000")])["rare_eu"] is True
    assert classify_rarity([pv("6-9 / 10 000")])["rare_eu"] is False
    # Worldwide preferred over a national estimate
    assert classify_rarity([pv("6-9 / 10 000", "Italy"), pv("1-5 / 10 000")])["rare_eu"] is True
    # birth prevalence ignored; no point prevalence -> presumed rare, low confidence
    r = classify_rarity([pv(">1 / 1000", t="Prevalence at birth")])
    assert r["rare_eu"] is True and r["confidence"] == "low"
