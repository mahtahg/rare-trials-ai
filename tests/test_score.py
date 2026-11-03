import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "eval"))
from score import mcnemar_exact, score_answer, token_f1, wilson  # noqa: E402


def q(t, gold, **kw):
    return {"answer_type": t, "gold": gold, **kw}


def test_bool_and_notfound():
    assert score_answer(q("bool", True), {"answer": "Yes"})["correct"]
    assert not score_answer(q("bool", True), {"answer": False})["correct"]
    assert score_answer(q("notfound", None), {"answer": None, "not_found": True})["correct"]
    assert not score_answer(q("notfound", None), {"answer": "NCT01234567", "not_found": False})["correct"]
    r = score_answer(q("bool", True), {"answer": "x", "not_found": True})
    assert r["abstained"] and not r["correct"]


def test_numeric_tolerance():
    assert score_answer(q("count", 100, tol_rel=0.1), {"answer": "108 trials"})["correct"]
    assert not score_answer(q("count", 100, tol_rel=0.1), {"answer": 120})["correct"]
    assert score_answer(q("year", 1994, tol_abs=1), {"answer": 1995})["correct"]


def test_set_f1_and_aliases():
    r = score_answer(q("set", ["DMD", "UTRN"], aliases={"DYSTROPHIN": "DMD"}), {"answer": ["dystrophin", "SGCA"]})
    assert r["precision"] == 0.5 and r["recall"] == 0.5 and r["correct"]


def test_enrollment():
    g = {"count": 12, "type": "ACTUAL"}
    assert score_answer(q("enrollment", g), {"answer": {"count": 12, "type": "Actual"}})["correct"]
    assert score_answer(q("enrollment", g), {"answer": {"count": 12, "type": "ESTIMATED"}})["score"] == 0.5


def test_stats():
    assert token_f1("low accrual", "Study stopped due to low accrual") > 0.4
    assert mcnemar_exact(0, 0) == 1.0
    assert mcnemar_exact(10, 0) < 0.01
    lo, hi = wilson(50, 100)
    assert lo < 0.5 < hi


def test_parse_fail():
    assert score_answer(q("bool", True), None)["parse_fail"]
