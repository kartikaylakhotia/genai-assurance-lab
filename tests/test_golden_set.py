"""Data-integrity checks: a golden set with wrong evidence would make every metric meaningless."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROWS = [json.loads(l) for l in (ROOT / "evals" / "golden_set.jsonl").read_text().splitlines() if l.strip()]


def _corpus() -> str:
    text = " ".join(p.read_text(encoding="utf-8") for p in (ROOT / "data" / "corpus").glob("*.txt"))
    return re.sub(r"\s+", " ", text.lower())


def test_ids_unique_and_types_valid():
    assert len({r["id"] for r in ROWS}) == len(ROWS)
    assert {r["type"] for r in ROWS} <= {"answerable", "unanswerable", "trick"}


def test_every_evidence_quote_is_verbatim_in_corpus():
    corpus = _corpus()
    for r in ROWS:
        if r["type"] != "unanswerable":
            assert r["gold_evidence"] and r["gold_evidence"] in corpus, r["id"]


def test_unanswerable_questions_have_no_evidence():
    assert all(r["gold_evidence"] is None for r in ROWS if r["type"] == "unanswerable")
