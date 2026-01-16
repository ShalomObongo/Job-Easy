"""Resume and cover letter tailoring module.

This module provides functionality for:
- Generating tailoring plans from job descriptions and user profiles
- Tailoring resumes with keyword integration and evidence mapping
- Generating personalized cover letters
- Rendering documents to PDF
- Creating review packets for HITL confirmation

Main Entry Point:
    TailoringService - Orchestrates the complete tailoring pipeline

Example:
    from src.tailoring import TailoringService

    service = TailoringService()
    result = await service.tailor(user_profile, job_description)

    if result.success:
        print(f"Resume: {result.resume_path}")
        print(f"Cover Letter: {result.cover_letter_path}")
"""

from src.tailoring.config import TailoringConfig, get_tailoring_config
from src.tailoring.cover_letter import CoverLetterService
from src.tailoring.models import (
    BulletRewrite,
    CoverLetter,
    DocReviewPacket,
    EvidenceMapping,
    KeywordMatch,
    TailoredBullet,
    TailoredResume,
    TailoredSection,
    TailoringPlan,
    UnsupportedClaim,
)
from src.tailoring.plan import TailoringPlanService
from src.tailoring.renderer import PDFRenderer, RenderResult
from src.tailoring.resume import ResumeTailoringService
from src.tailoring.review import ReviewPacketService
from src.tailoring.service import TailoringResult, TailoringService

__all__ = [
    # Main service
    "TailoringService",
    "TailoringResult",
    # Configuration
    "TailoringConfig",
    "get_tailoring_config",
    # Sub-services
    "TailoringPlanService",
    "ResumeTailoringService",
    "CoverLetterService",
    "PDFRenderer",
    "RenderResult",
    "ReviewPacketService",
    # Models
    "TailoringPlan",
    "KeywordMatch",
    "EvidenceMapping",
    "BulletRewrite",
    "UnsupportedClaim",
    "TailoredResume",
    "TailoredSection",
    "TailoredBullet",
    "CoverLetter",
    "DocReviewPacket",
]
