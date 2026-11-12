"""The system under test: a small, deliberately simple RAG assistant.

Retrieval uses TF-IDF as a transparent baseline (an embedding retriever can be swapped in).
The LLM sits behind a tiny interface so the same tests run against Groq, Gemini or a mock.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Protocol

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from . import guardrails as g


def chunk_pages(pages: list[str], chunk_words: int = 300, overlap: int = 50) -> list[dict]:
    """Split page texts into overlapping word windows, keeping the page number on every chunk."""
    if overlap >= chunk_words:
        raise ValueError("overlap must be smaller than chunk_words")
    chunks = []
    for page_no, text in enumerate(pages, start=1):
        words = text.split()
        step = chunk_words - overlap
        for start in range(0, max(len(words), 1), step):
            piece = " ".join(words[start:start + chunk_words])
            if piece:
                chunks.append({"id": f"p{page_no}-{start}", "page": page_no, "text": piece})
            if start + chunk_words >= len(words):
                break
    return chunks


class Retriever:
    def __init__(self, chunks: list[dict]):
        if not chunks:
            raise ValueError("no chunks to index")
        self.chunks = chunks
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self.matrix = self.vectorizer.fit_transform([c["text"] for c in chunks])

    def search(self, query: str, k: int = 5) -> list[dict]:
        scores = cosine_similarity(self.vectorizer.transform([query]), self.matrix)[0]
        top = scores.argsort()[::-1][:k]
        return [{**self.chunks[i], "score": float(scores[i])} for i in top]


class LLM(Protocol):
    name: str

    def complete(self, system: str, user: str) -> str: ...


@dataclass
class GroqLLM:
    model: str = "llama-3.1-8b-instant"
    name: str = "groq"

    def complete(self, system: str, user: str) -> str:  # pragma: no cover - needs network + key
        from groq import Groq

        client = Groq(api_key=os.environ["GROQ_API_KEY"])
        resp = client.chat.completions.create(
            model=self.model, temperature=0,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        return resp.choices[0].message.content


@dataclass
class Assistant:
    retriever: Retriever
    llm: LLM
    guardrails_on: bool = True
    log_path: str | None = "runs/log.jsonl"
    k: int = 5
    _log: list = field(default_factory=list)

    def answer(self, question: str) -> dict:
        hits = self.retriever.search(question, self.k)
        record = {"ts": time.time(), "question": question, "model": self.llm.name,
                  "guardrails": self.guardrails_on, "retrieved": [h["id"] for h in hits]}
        if self.guardrails_on:
            if g.is_out_of_scope(question) or g.detect_injection(question):
                record.update(answer=g.REFUSAL, blocked_by="input_filter")
                return self._finish(record)
            if g.should_refuse_low_confidence(hits[0]["score"] if hits else 0.0):
                record.update(answer=g.REFUSAL, blocked_by="low_confidence")
                return self._finish(record)
            hits = [h for h in hits if not g.detect_injection(h["text"])]
            context = g.wrap_context(hits)
            system = g.SYSTEM_PROMPT
        else:
            context = "\n\n".join(f"[page {h['page']}] {h['text']}" for h in hits)
            system = "Answer the question using the context."
        raw = self.llm.complete(system, f"{context}\n\nQuestion: {question}")
        answer, pii = g.mask_pii(raw) if self.guardrails_on else (raw, [])
        record.update(answer=answer, pii_masked=pii, retrieved_pages=[h["page"] for h in hits])
        return self._finish(record)

    def _finish(self, record: dict) -> dict:
        """Every interaction is logged: an auditable trail is itself a control."""
        if self.log_path:
            os.makedirs(os.path.dirname(self.log_path) or ".", exist_ok=True)
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        return record
