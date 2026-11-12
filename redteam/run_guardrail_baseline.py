"""Reproduce the guardrail baseline results in results/guardrail_baseline.json.

1. Runs all 60 red-team prompts through the input-layer filters (injection + out-of-scope).
2. Runs 50 synthetic identifiers (10 each of PAN, Aadhaar, phone, account, email) through PII masking.

No API key needed. Usage:  python -m redteam.run_guardrail_baseline
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from assurance import guardrails as g
from assurance.metrics import attack_success_rate

ROOT = Path(__file__).resolve().parents[1]
PLANT = "[Planted in document] "


def input_filter_results() -> list[dict]:
    rows = [json.loads(line) for line in (ROOT / "redteam" / "attacks.jsonl").read_text().splitlines()]
    out = []
    for r in rows:
        text = r["prompt"].removeprefix(PLANT)
        blocked = g.detect_injection(text) or g.is_out_of_scope(text)
        out.append({"id": r["id"], "category": r["category"], "succeeded": not blocked})
    return out


def synthetic_pii(seed: int = 1) -> list[tuple[str, str]]:
    """Invented identifiers only -- never real personal data."""
    rng = random.Random(seed)
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    recs = []
    for i in range(10):
        pan = "".join(rng.choice(letters) for _ in range(5)) + "".join(rng.choice("0123456789") for _ in range(4)) + rng.choice(letters)
        aadhaar = f"{rng.randint(2, 9)}{rng.randint(100, 999)} {rng.randint(1000, 9999)} {rng.randint(1000, 9999)}"
        recs += [("PAN", pan), ("AADHAAR", aadhaar), ("PHONE", f"9{rng.randint(100000000, 999999999)}"),
                 ("ACCOUNT", str(rng.randint(10**11, 10**12 - 1))), ("EMAIL", f"user{i}@example.com")]
    return recs


def main() -> None:
    attacks = input_filter_results()
    asr = attack_success_rate(attacks)
    pii = synthetic_pii()
    masked = sum(v not in g.mask_pii(f"Customer record: {v} on file.")[0] for _, v in pii)
    summary = {
        "attacks_total": len(attacks),
        "blocked_by_input_filters": sum(not a["succeeded"] for a in attacks),
        "block_rate": round(1 - asr["overall"], 3),
        "attack_success_rate_by_category": {k: round(v, 3) for k, v in asr.items()},
        "pii_identifiers_tested": len(pii),
        "pii_identifiers_masked": masked,
    }
    out = ROOT / "results" / "guardrail_baseline.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
