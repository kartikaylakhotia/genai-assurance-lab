import math

import pytest

from assurance import metrics as m


def test_hit_at_k():
    assert m.retrieval_hit_at_k([[1, 2, 3], [4, 5, 6]], [3, 9], k=3) == 0.5
    assert m.retrieval_hit_at_k([[1, 2, 3]], [3], k=2) == 0.0


def test_hit_at_k_length_mismatch():
    with pytest.raises(ValueError):
        m.retrieval_hit_at_k([[1]], [1, 2])


def test_hallucination_rate_counts_any_unsupported_claim():
    assert m.hallucination_rate([[True, True], [True, False], []]) == pytest.approx(1 / 3)


def test_refusal_accuracy():
    r = m.refusal_accuracy([True, False, True, False], [True, True, False, False])
    assert r["correct_refusal_rate"] == 0.5
    assert r["over_refusal_rate"] == 0.5


def test_consistency_normalises_case_and_space():
    assert m.consistency_rate([["Yes", " yes "], ["A", "B"]]) == 0.5


def test_attack_success_rate_by_category():
    out = m.attack_success_rate([
        {"category": "x", "succeeded": True}, {"category": "x", "succeeded": False},
        {"category": "y", "succeeded": False},
    ])
    assert out["x"] == 0.5 and out["y"] == 0.0 and out["overall"] == pytest.approx(1 / 3)


def test_cohen_kappa_perfect_and_chance():
    assert m.cohen_kappa([1, 0, 1, 0], [1, 0, 1, 0]) == 1.0
    assert m.cohen_kappa([1, 1, 0, 0], [1, 0, 1, 0]) == 0.0


def test_bootstrap_ci_contains_mean():
    vals = [1, 0, 1, 1, 0, 1, 1, 1, 0, 1]
    lo, hi = m.bootstrap_ci(vals)
    assert lo <= sum(vals) / len(vals) <= hi
    assert not math.isnan(lo)
