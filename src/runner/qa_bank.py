"""Q&A bank for learning screening questions.

Stores previously answered application questions so future runs can reuse answers
without prompting the user again.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Literal

_WHITESPACE_RE = re.compile(r"\s+")
_TRAILING_PUNCT_RE = re.compile(r"[\s\?\!\.\:]+$")

ScopeType = Literal["global", "company", "domain", "job"]
ScopeHint = tuple[ScopeType, str | None]


def _normalize_scope_key(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    return normalized or None


def _is_motivation_category(value: str | None) -> bool:
    if value is None:
        return False
    normalized = str(value).strip().lower()
    return normalized in {"motivation", "why_company", "why_role", "essay"}


def _scope_rank(scope_type: ScopeType) -> int:
    # Higher priority first.
    return {"job": 0, "company": 1, "domain": 2, "global": 3}.get(scope_type, 9)


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
        # Keyed by normalized question; values are a list of scoped entries.
        self._answers: dict[str, list[dict[str, Any]]] = {}

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

        answers: dict[str, list[dict[str, Any]]] = {}
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            question = entry.get("question")
            answer = entry.get("answer")
            if not isinstance(question, str) or not isinstance(answer, str):
                continue

            scope_type: ScopeType = "global"
            raw_scope_type = entry.get("scope_type")
            if isinstance(raw_scope_type, str):
                candidate = raw_scope_type.strip().lower()
                if candidate in {"global", "company", "domain", "job"}:
                    scope_type = candidate  # type: ignore[assignment]

            scope_key = _normalize_scope_key(
                entry.get("scope_key")
                if isinstance(entry.get("scope_key"), str)
                else None
            )

            context_value = (
                entry.get("context") if isinstance(entry.get("context"), str) else None
            )

            category_value = (
                entry.get("category")
                if isinstance(entry.get("category"), str)
                else None
            )

            source_value = (
                entry.get("source") if isinstance(entry.get("source"), str) else None
            )

            normalized = normalize_question(question)
            answers.setdefault(normalized, []).append(
                {
                    "question": question,
                    "answer": answer,
                    "context": context_value,
                    "scope_type": scope_type,
                    "scope_key": scope_key,
                    "source": source_value,
                    "category": category_value,
                }
            )

        self._answers = answers

    def save(self) -> None:
        """Persist the Q&A bank to disk deterministically."""
        self.path.parent.mkdir(parents=True, exist_ok=True)

        entries = []
        for key in sorted(self._answers.keys()):
            scoped = self._answers[key]
            if not isinstance(scoped, list):
                continue
            scoped_sorted = sorted(
                scoped,
                key=lambda item: (
                    _scope_rank(item.get("scope_type", "global")),
                    str(item.get("scope_key") or ""),
                    str(item.get("question") or ""),
                ),
            )
            for item in scoped_sorted:
                entries.append(
                    {
                        "question": item.get("question") or "",
                        "answer": item.get("answer") or "",
                        "context": item.get("context"),
                        "scope_type": item.get("scope_type") or "global",
                        "scope_key": item.get("scope_key"),
                        "source": item.get("source"),
                        "category": item.get("category"),
                    }
                )

        payload = {"entries": entries}

        tmp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp_path.replace(self.path)

    def get_answer(
        self,
        question: str,
        _context: str | None = None,
        scope_hints: list[ScopeHint] | None = None,
        category: str | None = None,
    ) -> str | None:
        """Get a saved answer for a question (best-effort).

        Args:
            question: Question text.
            _context: Legacy context string (retained for backwards compatibility).
            scope_hints: Optional list of scoped lookup hints in priority order.
            category: Optional category hint (used to prevent unsafe global reuse).
        """
        if not self._answers and self.path.exists():
            self.load()

        key = normalize_question(question)
        candidates = self._answers.get(key) or []
        if not candidates:
            return None

        forbid_global = _is_motivation_category(category)

        def is_allowed(entry: dict[str, Any]) -> bool:
            if entry.get("scope_type") != "global":
                return True
            if forbid_global:
                return False
            return not _is_motivation_category(entry.get("category"))

        if scope_hints:
            for scope_type, scope_key in scope_hints:
                normalized_key = _normalize_scope_key(scope_key)
                for entry in candidates:
                    if (
                        entry.get("scope_type") == scope_type
                        and entry.get("scope_key") == normalized_key
                        and is_allowed(entry)
                    ):
                        answer = entry.get("answer")
                        return answer if isinstance(answer, str) and answer else None

        # Fallback: return the first allowed global answer if present.
        for entry in candidates:
            if entry.get("scope_type") == "global" and is_allowed(entry):
                answer = entry.get("answer")
                return answer if isinstance(answer, str) and answer else None

        return None

    def record_answer(
        self,
        question: str,
        answer: str,
        context: str | None = None,
        *,
        scope_type: ScopeType = "global",
        scope_key: str | None = None,
        source: str | None = None,
        category: str | None = None,
    ) -> None:
        """Record an answer and persist to disk."""
        scope_key = _normalize_scope_key(scope_key)
        key = normalize_question(question)

        entry = {
            "question": question,
            "answer": answer,
            "context": context,
            "scope_type": scope_type,
            "scope_key": scope_key,
            "source": source,
            "category": category,
        }

        existing = self._answers.get(key) or []
        replaced = False
        for idx, item in enumerate(existing):
            if (
                item.get("scope_type") == scope_type
                and item.get("scope_key") == scope_key
            ):
                existing[idx] = entry
                replaced = True
                break

        if not replaced:
            existing.append(entry)

        self._answers[key] = existing
        self.save()
