"""Autonomous mode data models."""

from __future__ import annotations

from dataclasses import dataclass, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from src.extractor.models import JobDescription
from src.scoring.models import FitResult


def _jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if is_dataclass(value):
        return {field: _jsonable(getattr(value, field)) for field in value.__dict__}
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return _jsonable(to_dict())
    return value


@dataclass
class LeadItem:
    """A single line item from a leads file."""

    url: str
    line_number: int
    valid: bool
    error: str | None = None

    def __post_init__(self) -> None:
        if self.line_number < 1:
            raise ValueError("line_number must be >= 1")
        if self.valid and self.error is not None:
            raise ValueError("error must be None when valid=True")
        if not self.valid and self.error is None:
            raise ValueError("error is required when valid=False")

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(self)


class QueueStatus(str, Enum):
    """Processing status for a queued job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class QueuedJob:
    """A job queued for batch processing."""

    url: str
    fingerprint: str
    job_description: JobDescription
    fit_result: FitResult
    status: QueueStatus = QueueStatus.PENDING

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(self)


@dataclass
class JobResult:
    """Result of processing a single queued job."""

    url: str
    fingerprint: str
    status: QueueStatus
    error: str | None
    duration_seconds: float

    def __post_init__(self) -> None:
        if self.duration_seconds < 0:
            raise ValueError("duration_seconds must be >= 0")

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(self)


@dataclass
class BatchResult:
    """Summary of running a batch of queued jobs."""

    processed: int
    submitted: int
    skipped: int
    failed: int
    duration_seconds: float
    job_results: list[JobResult]

    def __post_init__(self) -> None:
        if self.processed < 0:
            raise ValueError("processed must be >= 0")
        if self.submitted < 0:
            raise ValueError("submitted must be >= 0")
        if self.skipped < 0:
            raise ValueError("skipped must be >= 0")
        if self.failed < 0:
            raise ValueError("failed must be >= 0")
        if self.duration_seconds < 0:
            raise ValueError("duration_seconds must be >= 0")

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(self)
