"""Runner result models.

These models provide a structured output contract for the application runner and
its Browser Use agent integration (`output_model_schema` / `history.structured_output`).
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class RunStatus(str, Enum):
    """High-level status for a single application run."""

    SUBMITTED = "submitted"
    STOPPED_BEFORE_SUBMIT = "stopped_before_submit"
    SKIPPED = "skipped"
    DUPLICATE_SKIPPED = "duplicate_skipped"
    FAILED = "failed"
    BLOCKED = "blocked"


class StepSummary(BaseModel):
    """Structured summary of an important runner step."""

    name: str
    url: str | None = None
    notes: list[str] = Field(default_factory=list)


class ApplicationRunResult(BaseModel):
    """Structured result for a single application run."""

    success: bool
    status: RunStatus

    final_url: str | None = None
    visited_urls: list[str] = Field(default_factory=list)
    steps: list[StepSummary] = Field(default_factory=list)

    proof_text: str | None = None
    proof_screenshot_path: str | None = None

    errors: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict:
        """Return a JSON-serializable representation."""
        return self.model_dump(mode="python")

    def save_json(self, path: str | Path) -> None:
        """Save the result as JSON on disk."""
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.model_dump_json(indent=2), encoding="utf-8")
