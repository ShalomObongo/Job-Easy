"""Skill matching utilities for Fit Scoring."""

from __future__ import annotations

import re
from difflib import SequenceMatcher

_SKILL_ALIASES: dict[str, str] = {
    "js": "javascript",
    "javascript": "javascript",
    "python3": "python",
    "python": "python",
    "nodejs": "node.js",
    "node.js": "node.js",
}


def normalize_skill(skill: str) -> str:
    """Normalize a skill string for comparison.

    Performs lowercasing, whitespace normalization, and trims common
    surrounding punctuation while preserving meaningful characters
    like "+", "#", and "." (e.g. "C++", "C#", "Node.js").
    """
    value = skill.strip().lower()
    value = re.sub(r"\s+", " ", value)
    return value.strip(" ,;")


def _canonicalize_skill(skill: str) -> str:
    normalized = normalize_skill(skill)
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
