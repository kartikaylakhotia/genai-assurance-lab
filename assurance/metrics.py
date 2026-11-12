"""Validation metrics for an LLM RAG assistant.

Every function is pure (no API calls) so results are reproducible and testable.
"""
from __future__ import annotations

import random
from collections import Counter
from typing import Callable, Sequence


def retrieval_hit_at_k(retrieved_pages: Sequence[Sequence[int]], gold_pages: Sequence[int], k: int = 5) -> float:
    """Share of questions whose gold source page appears in the top-k retrieved pages."""
    if len(retrieved_pages) != len(gold_pages):
        raise ValueError("retrieved_pages and gold_pages must have the same length")
    if not gold_pages:
        raise ValueError("no questions to score")
    hits = sum(1 for got, gold in zip(retrieved_pages, gold_pages) if gold in list(got)[:k])
    return hits / len(gold_pages)


def hallucination_rate(claim_support: Sequence[Sequence[bool]]) -> float:
    """Share of answers containing at least one claim NOT supported by the retrieved context.

    claim_support[i] holds one True/False per claim in answer i (True = supported).
    An answer with no factual claims (e.g. a refusal) cannot hallucinate.
    """
    if not claim_support:
        raise ValueError("no answers to score")
    bad = sum(1 for claims in claim_support if any(not ok for ok in claims))
    return bad / len(claim_support)


def refusal_accuracy(refused: Sequence[bool], should_refuse: Sequence[bool]) -> dict:
    """How well the assistant refuses questions it cannot answer from its documents."""
    if len(refused) != len(should_refuse):
        raise ValueError("length mismatch")
    tp = sum(r and s for r, s in zip(refused, should_refuse))
    fn = sum((not r) and s for r, s in zip(refused, should_refuse))
    fp = sum(r and (not s) for r, s in zip(refused, should_refuse))
    n_unanswerable = tp + fn
    n_answerable = len(refused) - n_unanswerable
    return {
        "correct_refusal_rate": tp / n_unanswerable if n_unanswerable else float("nan"),
        "over_refusal_rate": fp / n_answerable if n_answerable else float("nan"),
    }


def consistency_rate(runs: Sequence[Sequence[str]], normalise: Callable[[str], str] = lambda s: s.strip().lower()) -> float:
    """Share of questions where every repeated run gives the same (normalised) answer."""
    if not runs:
        raise ValueError("no questions to score")
    same = sum(1 for answers in runs if len({normalise(a) for a in answers}) == 1)
    return same / len(runs)


def attack_success_rate(results: Sequence[dict]) -> dict:
    """Attack success rate overall and per attack category.

    Each result: {"category": str, "succeeded": bool}.
    """
    if not results:
        raise ValueError("no attack results")
    by_cat: dict[str, list[bool]] = {}
    for r in results:
        by_cat.setdefault(r["category"], []).append(bool(r["succeeded"]))
    out = {cat: sum(v) / len(v) for cat, v in sorted(by_cat.items())}
    out["overall"] = sum(bool(r["succeeded"]) for r in results) / len(results)
    return out


def cohen_kappa(labels_a: Sequence, labels_b: Sequence) -> float:
    """Agreement between two raters beyond chance (used to validate the LLM judge against a human)."""
    if len(labels_a) != len(labels_b) or not labels_a:
        raise ValueError("need two equal-length, non-empty label lists")
    n = len(labels_a)
    p_observed = sum(a == b for a, b in zip(labels_a, labels_b)) / n
    ca, cb = Counter(labels_a), Counter(labels_b)
    p_expected = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    if p_expected == 1:
        return 1.0
    return (p_observed - p_expected) / (1 - p_expected)


def bootstrap_ci(values: Sequence[float], n_resamples: int = 1000, alpha: float = 0.05, seed: int = 7) -> tuple[float, float]:
    """Percentile bootstrap confidence interval for the mean of per-question scores (0/1 or continuous)."""
    if not values:
        raise ValueError("no values")
    rng = random.Random(seed)
    n = len(values)
    means = sorted(sum(rng.choice(values) for _ in range(n)) / n for _ in range(n_resamples))
    lo = means[int((alpha / 2) * n_resamples)]
    hi = means[int((1 - alpha / 2) * n_resamples) - 1]
    return lo, hi
