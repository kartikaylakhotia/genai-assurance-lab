# Validation Report: RBI KYC Regulation RAG Assistant

## 1. Scope and intended use
- **System:** RAG assistant answering staff questions on the RBI Master Direction on Know Your Customer (KYC), 2016, updated August 14, 2025.
- **Intended users:** internal compliance and operations staff. Not customer-facing.
- **Out of scope:** investment advice, legal opinions, questions outside the indexed documents.
- **Materiality:** Medium (wrong answers could lead to non-compliant onboarding decisions; a human remains accountable).

## 2. System description
TF-IDF retriever over 251 chunks of the RBI KYC Master Direction (33,505 words), top-5 context passed to an LLM (Groq, Llama 3.1 8B) at temperature 0, with the controls listed in the README. All interactions logged.

## 3. Test design
| Area | Test | Size |
| --- | --- | --- |
| Quality | Golden set with verbatim evidence: 28 answerable, 6 trick, 10 unanswerable | 44 questions |
| Robustness | Red-team suite: direct injection (20), indirect injection (15), data leakage (10), out-of-scope (15) | 60 attacks |
| Privacy | Output masking of synthetic PAN, Aadhaar, phone, account and email | 50 identifiers |
| Controls | Unit and data-integrity tests | 20 tests |

## 4. Findings
| # | Finding | Rating | Recommended action |
| --- | --- | --- | --- |
| F1 | Keyword input filters stop only 28% of attacks (17/60); paraphrased, encoded and role-play injections pass. | High | Keep filters as one layer only; rely on context isolation, chunk screening and output controls; add an LLM-based injection classifier and measure it on new, unseen attacks. |
| F2 | Input filters stop 0/10 data-leakage attempts. | High | Output PII masking is mandatory (50/50 synthetic identifiers masked); add access controls so sensitive documents are never indexed. |
| F3 | Indirect injection via documents is the least defended path (input filters stop 4/15). | High | Screen chunks at ingestion as well as at query time; restrict index to approved sources with owners. |
| F4 | Retrieval finds the right passage in the top 5 for 91% of questions but ranks it first for only 56%; misses include definitions (Principal Officer, shell bank) and a false-premise question. | Medium | Try embedding or hybrid retrieval and re-rank; re-measure on the same golden set. |
| F5 | A retrieval-score threshold cannot separate answerable from unanswerable questions: at 0.20 it refuses 80% of unanswerable but also 26% of answerable questions. | High | Do not rely on score thresholds alone; require the model to refuse when context lacks the answer, and measure refusal with the LLM run. |
| F6 | Chunk screening removed 4 of 15 planted instructions in real regulatory text, with 0 false flags on 251 clean chunks. | High | Precise but weak; add a model-based classifier and test on unseen attacks. |
| F7 | Regex PII patterns are India-specific and may over-mask long numbers (e.g. circular reference numbers). | Medium | Track over-masking rate on the golden set; whitelist known reference formats. |
| F8 | Golden-set answers were written by one reviewer against verbatim evidence. | Medium | Second-person review before quality metrics are used for approval. |

## 5. Decision
**Not approved for production in current form.** Approve for a limited internal pilot once F1, F2, F3, F5 and F6 are remediated and LLM metrics on the golden set meet agreed thresholds (proposed: answer accuracy above 90%, hallucination rate under 5%, correct-refusal rate above 90%, judge-human kappa above 0.6).

## 6. NIST AI RMF mapping
| Function | Evidence in this repo |
| --- | --- |
| Govern | Intended use, materiality and approval decision (this report); audit log of every interaction |
| Map | Risk-to-metric table in README; out-of-scope definition |
| Measure | Metrics module, evidence-backed golden set, red-team suite, bootstrap confidence intervals, judge validation |
| Manage | Layered controls, findings with actions, CI re-test on every change before re-approval |
