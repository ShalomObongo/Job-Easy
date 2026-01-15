"""Fit scoring and recommendation system.

This module provides functionality for evaluating job-candidate fit by
comparing extracted job requirements against a user profile.

Public API:
    - FitScoringService: Main scoring and evaluation service
    - ProfileService: Load and validate user profiles
    - UserProfile: Profile model
    - FitResult: Evaluation output model
    - ScoringConfig: Configuration settings
"""

from src.scoring.config import ScoringConfig, get_scoring_config, reset_scoring_config
from src.scoring.models import (
    ConstraintResult,
    Education,
    FitResult,
    FitScore,
    UserProfile,
    WorkExperience,
)
from src.scoring.profile import ProfileService
from src.scoring.service import FitScoringService

__all__ = [
    "FitScoringService",
    "ProfileService",
    "UserProfile",
    "WorkExperience",
    "Education",
    "FitScore",
    "ConstraintResult",
    "FitResult",
    "ScoringConfig",
    "get_scoring_config",
    "reset_scoring_config",
]
