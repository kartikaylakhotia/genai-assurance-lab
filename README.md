# GenAI Assurance Lab

**Independent validation of an LLM retrieval-augmented (RAG) assistant for banking regulation, done the way a second-line Model & AI Risk team would before approving it for use.**

The assistant answers questions on RBI regulations (KYC Master Direction, Digital Lending Directions). The point of this repo is not the assistant: it is the evidence on whether the assistant can be trusted, where it fails, and which controls reduce that risk.

## Headline findings (guardrail baseline)

| Test | Result |
| --- | --- |
| Red-team attacks run | 60, across 4 categories |
| Attacks stopped by keyword input filters alone | **17 / 60 (28%)** |
| Data-leakage attempts stopped by input filters | 0 / 10 (handled by the output PII mask instead) |
| Synthetic identifiers masked in output (PAN, Aadhaar, phone, account, email) | **50 / 50** |
| Unit tests | 17 passing |

**Interpretation:** pattern-based input filters are a weak single line of defence. They miss paraphrased and encoded injections and do nothing for leakage. The design therefore layers controls (below) instead of relying on any one of them. Reproduce with `python -m redteam.run_guardrail_baseline` (output: `results/guardrail_baseline.json`).

## What is validated

| Risk | Metric | Code |
| --- | --- | --- |
| Wrong source retrieved | Retrieval hit rate @k | `assurance/metrics.py::retrieval_hit_at_k` |
| Made-up facts | Hallucination rate (share of answers with any unsupported claim) | `hallucination_rate` |
| Answering beyond its knowledge | Correct-refusal and over-refusal rates | `refusal_accuracy` |
| Unstable output | Consistency across repeated runs | `consistency_rate` |
| Untrustworthy LLM judge | Judge vs human agreement (Cohen's kappa) | `cohen_kappa` |
| Small-sample noise | Bootstrap 95% confidence intervals | `bootstrap_ci` |
| Manipulation | Attack success rate by category | `attack_success_rate` |

## Controls (defence in depth)

1. **Context isolation:** retrieved text is wrapped in delimiters and the system prompt declares it data, never instructions.
2. **Input filters:** prompt-injection and out-of-scope patterns (investment advice, evading KYC/AML).
3. **Retrieved-chunk screening:** chunks containing injection patterns are dropped before reaching the model (indirect injection).
4. **Low-confidence refusal:** if the best retrieval score is below a threshold, the assistant refuses rather than guesses.
5. **Output PII masking:** Indian identifiers are redacted before any answer is returned.
6. **Audit log:** every interaction (question, retrieved chunks, model, controls fired, answer) is written to `runs/log.jsonl`.

Each control has a unit test, including one that shows PII **leaks when guardrails are off** and is masked when on (`tests/test_rag.py`).

## Repository layout

```
assurance/   rag.py (system under test), guardrails.py (controls), metrics.py (validation metrics)
redteam/     attacks.jsonl (60 attacks), run_guardrail_baseline.py
evals/       golden_set.jsonl (answerable, unanswerable and trick questions)
docs/        validation_report.md (scope, findings, ratings, NIST AI RMF mapping)
results/     machine-readable outputs of each run
tests/       pytest suite
```

## Quick start

```bash
pip install -r requirements.txt
pytest                                   # 17 tests, no API key needed
python -m redteam.run_guardrail_baseline # reproduces the headline table
export GROQ_API_KEY=...                  # only for end-to-end LLM runs
```

## Method notes

- **Judge independence:** the LLM used as judge must differ from the generator, and its labels are checked against human labels with Cohen's kappa before any judge-based metric is reported.
- **Synthetic data only:** all PII in tests is randomly generated. No real personal data is used.
- **No tuning to the test set:** the guardrail baseline is reported as first measured. Improving filters against the same 60 attacks would overstate their real-world strength, so new attacks are added before any re-measurement.

## Framework mapping

Tests are mapped to the NIST AI Risk Management Framework functions (Govern, Map, Measure, Manage) in `docs/validation_report.md`.
