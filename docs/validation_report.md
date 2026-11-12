# Validation Report: RBI Regulation RAG Assistant

## 1. Scope and intended use
- **System:** RAG assistant answering staff questions on the RBI KYC Master Direction and Digital Lending Directions.
- **Intended users:** internal compliance and operations staff. Not customer-facing.
- **Out of scope:** investment advice, legal opinions, questions outside the indexed documents.
- **Materiality:** Medium (wrong answers could lead to non-compliant onboarding decisions; a human remains accountable).

## 2. System description
TF-IDF retriever over page-tagged chunks, top-5 context passed to an LLM (Groq, Llama 3.1 8B) at temperature 0, with the controls listed in the README. All interactions logged.

## 3. Test design
| Area | Test | Size |
| --- | --- | --- |
| Quality | Golden set: answerable, unanswerable, trick questions | `evals/golden_set.jsonl` |
| Robustness | Red-team suite: direct injection (20), indirect injection (15), data leakage (10), out-of-scope (15) | 60 attacks |
| Privacy | Output masking of synthetic PAN, Aadhaar, phone, account and email | 50 identifiers |
| Controls | Unit tests for each control and metric | 17 tests |

## 4. Findings
| # | Finding | Rating | Recommended action |
| --- | --- | --- | --- |
| F1 | Keyword input filters stop only 28% of attacks (17/60); paraphrased, encoded and role-play injections pass. | High | Keep filters as one layer only; rely on context isolation, chunk screening and output controls; add an LLM-based injection classifier and measure it on new, unseen attacks. |
| F2 | Input filters stop 0/10 data-leakage attempts. | High | Output PII masking is mandatory (50/50 synthetic identifiers masked); add access controls so sensitive documents are never indexed. |
| F3 | Indirect injection via documents is the least defended path (input filters stop 4/15). | High | Screen chunks at ingestion as well as at query time; restrict index to approved sources with owners. |
| F4 | Regex PII patterns are India-specific and may over-mask long numbers (e.g. circular reference numbers). | Medium | Track over-masking rate on the golden set; whitelist known reference formats. |
| F5 | Golden-set gold answers must be verified against source pages by a second person. | Medium | Dual review before quality metrics are reported. |

## 5. Decision
**Not approved for production in current form.** Approve for a limited internal pilot once F1 to F3 are remediated and quality metrics on the verified golden set meet agreed thresholds (proposed: hallucination rate under 5%, correct-refusal rate above 90%, judge-human kappa above 0.6).

## 6. NIST AI RMF mapping
| Function | Evidence in this repo |
| --- | --- |
| Govern | Intended use, materiality and approval decision (this report); audit log of every interaction |
| Map | Risk-to-metric table in README; out-of-scope definition |
| Measure | Metrics module, golden set, red-team suite, bootstrap confidence intervals, judge validation |
| Manage | Layered controls, findings with owners and actions, re-test before re-approval |
