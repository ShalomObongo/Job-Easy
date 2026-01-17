"""Q&A bank for learning screening questions.

Stores previously answered application questions so future runs can reuse answers
without prompting the user again.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_WHITESPACE_RE = re.compile(r"\s+")
_TRAILING_PUNCT_RE = re.compile(r"[\s\?\!\.\:]+$")


def normalize_question(question: str) -> str:
    """Normalize a question for stable lookup."""
    normalized = question.strip().lower()
    normalized = _WHITESPACE_RE.sub(" ", normalized)
    normalized = _TRAILING_PUNCT_RE.sub("", normalized)
    return normalized


class QABank:
    """A simple JSON-backed Q&A store."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._answers: dict[str, dict[str, str | None]] = {}

    def load(self) -> None:
        """Load the Q&A bank from disk (no-op if missing)."""
        if not self.path.exists():
            self._answers = {}
            return

        raw = json.loads(self.path.read_text(encoding="utf-8"))
        entries = raw.get("entries", [])
        if not isinstance(entries, list):
            self._answers = {}
            return

        answers: dict[str, dict[str, str | None]] = {}
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            question = entry.get("question")
            answer = entry.get("answer")
            if not isinstance(question, str) or not isinstance(answer, str):
                continue
            normalized = normalize_question(question)
            answers[normalized] = {
                "question": question,
                "answer": answer,
                "context": entry.get("context")
                if isinstance(entry.get("context"), str)
                else None,
            }

        self._answers = answers

    def save(self) -> None:
        """Persist the Q&A bank to disk deterministically."""
        self.path.parent.mkdir(parents=True, exist_ok=True)

        entries = []
        for key in sorted(self._answers.keys()):
            entry = self._answers[key]
            entries.append(
                {
                    "question": entry.get("question") or "",
                    "answer": entry.get("answer") or "",
                    "context": entry.get("context"),
                }
            )

        payload = {"entries": entries}

        tmp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp_path.replace(self.path)

    def get_answer(self, question: str, _context: str | None = None) -> str | None:
        """Get a saved answer for a question (best-effort)."""
        if not self._answers and self.path.exists():
            self.load()

        key = normalize_question(question)
        entry = self._answers.get(key)
        if entry is None:
            return None
        return entry.get("answer") or None

    def record_answer(
        self, question: str, answer: str, context: str | None = None
    ) -> None:
        """Record an answer and persist to disk."""
        key = normalize_question(question)
        self._answers[key] = {
            "question": question,
            "answer": answer,
            "context": context,
        }
        self.save()
