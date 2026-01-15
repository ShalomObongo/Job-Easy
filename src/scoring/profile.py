"""Profile loading and validation utilities."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from pydantic import ValidationError

from src.scoring.config import ScoringConfig, get_scoring_config
from src.scoring.models import UserProfile


class ProfileService:
    """Service for loading and validating user profiles."""

    def __init__(self, config: ScoringConfig | None = None) -> None:
        self.config = config or get_scoring_config()

    def load_profile(self, path: Path | str | None = None) -> UserProfile:
        """Load and validate a profile from YAML or JSON."""
        profile_path = Path(path) if path is not None else self.config.profile_path
        if not profile_path.exists():
            raise FileNotFoundError(f"Profile not found: {profile_path}")

        suffix = profile_path.suffix.lower()
        if suffix in {".yaml", ".yml"}:
            data = self._load_yaml(profile_path)
        elif suffix == ".json":
            data = self._load_json(profile_path)
        else:
            data = self._load_unknown(profile_path)

        try:
            return UserProfile.model_validate(data)
        except ValidationError:
            raise

    def validate_profile(self, profile: UserProfile) -> list[str]:
        """Return warnings for incomplete profiles."""
        warnings: list[str] = []

        if not profile.phone:
            warnings.append("Missing phone number")
        if not profile.linkedin_url:
            warnings.append("Missing LinkedIn URL")
        if not profile.skills:
            warnings.append("Skills list is empty")

        return warnings

    def _load_yaml(self, path: Path) -> dict:
        try:
            with path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except FileNotFoundError:
            raise
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML profile: {path}") from e

        if data is None:
            data = {}
        if not isinstance(data, dict):
            raise ValueError(f"Profile must be a mapping/dict: {path}")
        return data

    def _load_json(self, path: Path) -> dict:
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            raise
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON profile: {path}") from e

        if not isinstance(data, dict):
            raise ValueError(f"Profile must be a mapping/dict: {path}")
        return data

    def _load_unknown(self, path: Path) -> dict:
        """Auto-detect and load a profile when the file extension is unknown."""
        raw = path.read_text(encoding="utf-8")
        raw_stripped = raw.lstrip()

        # Try JSON first if it looks like JSON, otherwise fall back to YAML.
        if raw_stripped.startswith("{") or raw_stripped.startswith("["):
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = None
            else:
                if not isinstance(data, dict):
                    raise ValueError(f"Profile must be a mapping/dict: {path}")
                return data

        try:
            data = yaml.safe_load(raw)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid profile format: {path}") from e

        if data is None:
            data = {}
        if not isinstance(data, dict):
            raise ValueError(f"Profile must be a mapping/dict: {path}")
        return data
