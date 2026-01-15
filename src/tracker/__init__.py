"""Application tracking and fingerprinting.

This module provides the Application Tracker system for detecting
and managing duplicate job applications.

Public API:
- TrackerService: Main service for duplicate detection and record management
- TrackerRepository: Database repository for tracker records
- TrackerRecord: Data model for job application records
- ApplicationStatus: Enum for application status values
- SourceMode: Enum for job source modes
"""

from src.tracker.models import ApplicationStatus, SourceMode, TrackerRecord
from src.tracker.repository import TrackerRepository
from src.tracker.service import TrackerService

__all__ = [
    "TrackerService",
    "TrackerRepository",
    "TrackerRecord",
    "ApplicationStatus",
    "SourceMode",
]
