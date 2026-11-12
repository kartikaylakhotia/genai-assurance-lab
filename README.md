# GenAI Assurance Lab

**Independent validation of an LLM retrieval-augmented (RAG) assistant for banking regulation, done the way a second-line Model & AI Risk team would before approving it for use.**

The assistant answers staff questions on the RBI Master Direction on Know Your Customer (KYC). The point of this repo is not the assistant: it is the evidence on whether the assistant can be trusted, where it fails, and which controls reduce that risk.

## Headline results

Evaluated on the real **RBI Master Direction on KYC (2016, updated August 2025)**: 33,505 words split into 251 chunks, with a 44-question golden set (28 answerable, 6 trick, 10 unanswerable) whose every answer is backed by a verbatim quote from the regulation.

| Test | Result | What it means |
| --- | --- | --- |
| Retrieval hit rate @5 | **91% (31/34)**, 95% CI 79% to 100% | The right passage usually reaches the model |
| Retrieval hit rate @1 | 56% (19/34) | Ranking is weak; the model must read all 5 chunks |
| Low-confidence refusal (score < 0.20) | refuses 80% of unanswerable questions, but also 26% of answerable ones | A retrieval score alone cannot separate the two; refusal must also come from the model |
| Planted instructions in real chunks removed by screening | 4/15, with **0/251** clean chunks falsely flagged | Precise but weak; layered defences needed |
| Red-team attacks stopped by keyword input filters | **17/60 (28%)** | Pattern filters are a weak single line of defence |
| Synthetic identifiers masked in output | **50/50** | Output PII mask works on Indian formats |
| Unit and data-integrity tests | 20 passing in CI | Every metric and control is tested |

Reproduce: `python -m redteam.run_guardrail_baseline` and `python -m evals.run_eval` (outputs in `results/`). Both run automatically in GitHub Actions on every push.

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
evals/       golden_set.jsonl (44 questions with verbatim evidence), run_eval.py
data/corpus/ RBI KYC Master Direction (public regulatory text)
.github/     CI workflow: tests, red-team baseline, offline evaluation, optional LLM run
docs/        validation_report.md (scope, findings, ratings, NIST AI RMF mapping)
results/     machine-readable outputs of each run
tests/       pytest suite
```

## Quick start

```bash
pip install -r requirements.txt
pytest                                   # 20 tests, no API key needed
python -m redteam.run_guardrail_baseline # red-team baseline
python -m evals.run_eval                 # retrieval, refusal and injection results on the RBI corpus
GROQ_API_KEY=... python -m evals.run_eval --llm   # adds answer accuracy and consistency
```

## Method notes

- **Judge independence:** the LLM used as judge must differ from the generator, and its labels are checked against human labels with Cohen's kappa before any judge-based metric is reported.
- **Evidence-backed golden set:** every answerable question carries a verbatim quote from the regulation, and a test fails if any quote is missing from the corpus.
- **Synthetic data only:** all PII in tests is randomly generated. No real personal data is used.
- **No tuning to the test set:** results are reported as first measured. Improving filters against the same attacks would overstate their real-world strength, so new attacks are added before any re-measurement.

## Framework mapping

Tests are mapped to the NIST AI Risk Management Framework functions (Govern, Map, Measure, Manage) in `docs/validation_report.md`.

## LLM metrics

Answer accuracy (graded by a larger judge model, Llama 3.3 70B, against the gold answers) and consistency over 3 runs need a Groq API key. Add it as the repository secret `GROQ_API_KEY`, then run the workflow manually with "run_llm" ticked. Results are saved to `results/eval_full.json`.
