"""Skill matching utilities for Fit Scoring."""

from __future__ import annotations

import re
from difflib import SequenceMatcher

_SKILL_ALIASES: dict[str, str] = {
    "js": "javascript",
    "javascript": "javascript",
    "typescript": "typescript",
    "python3": "python",
    "python": "python",
    "numpy": "numpy",
    "nodejs": "node.js",
    "node js": "node.js",
    "node.js": "node.js",
    "react": "react",
    "reactjs": "react",
    "react.js": "react",
    "react js": "react",
    "nextjs": "next.js",
    "next js": "next.js",
    "next.js": "next.js",
    "html5": "html",
    "html": "html",
    "css3": "css",
    "css": "css",
    "mongo db": "mongodb",
    "mongodb": "mongodb",
    "jquery": "jquery",
}

_SKILL_IMPLICATIONS: dict[str, set[str]] = {
    # Web stacks.
    "react": {"javascript", "html", "css"},
    "next.js": {"react", "javascript", "html", "css"},
    "node.js": {"javascript"},
    # Broad skill buckets that imply fundamentals (fit scoring only).
    "full stack development": {"javascript", "html", "css", "testing", "debugging"},
    "software development": {"testing", "debugging"},
    "mobile software development": {"software development"},
}


def normalize_skill(skill: str) -> str:
    """Normalize a skill string for comparison.

    Performs lowercasing, whitespace normalization, and trims common
    surrounding punctuation while preserving meaningful characters
    like "+", "#", and "." (e.g. "C++", "C#", "Node.js").
    """
    value = skill.strip().lower()
    value = re.sub(r"\([^)]*\)", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip(" ,;")


def _canonicalize_skill(skill: str) -> str:
    normalized = normalize_skill(skill)
    if "test" in normalized:
        normalized = "testing"
    if "debug" in normalized or "optim" in normalized:
        normalized = "debugging"
    return _SKILL_ALIASES.get(normalized, normalized)


def skills_match(
    skill1: str, skill2: str, fuzzy: bool = True, threshold: float = 0.85
) -> bool:
    """Return True if two skills are considered a match."""
    canonical1 = _canonicalize_skill(skill1)
    canonical2 = _canonicalize_skill(skill2)

    if canonical1 == canonical2:
        return True

    if not fuzzy:
        return False

    if threshold <= 0.0:
        return True
    if threshold > 1.0:
        return False

    similarity = SequenceMatcher(None, canonical1, canonical2).ratio()
    return similarity >= threshold


def find_matching_skills(
    required: list[str],
    available: list[str],
    fuzzy: bool = True,
    threshold: float = 0.85,
) -> tuple[list[str], list[str]]:
    """Return the subset of required skills that match, and those missing."""
    matched: list[str] = []
    missing: list[str] = []

    for requirement in required:
        if any(
            skills_match(requirement, skill, fuzzy=fuzzy, threshold=threshold)
            for skill in available
        ):
            matched.append(requirement)
        else:
            missing.append(requirement)

    return matched, missing


def expand_skills(skills: list[str]) -> list[str]:
    """Return a normalized + inferred list of skills for matching.

    Used by fit scoring to infer high-confidence fundamentals for common stacks
    (e.g. "React" implies "JavaScript/HTML/CSS").
    """
    canonical = {_canonicalize_skill(s) for s in skills if str(s).strip()}
    expanded = set(canonical)
    stack = list(canonical)

    while stack:
        current = stack.pop()
        for implied in _SKILL_IMPLICATIONS.get(current, set()):
            implied_canon = _canonicalize_skill(implied)
            if implied_canon not in expanded:
                expanded.add(implied_canon)
                stack.append(implied_canon)

    return sorted(expanded)
