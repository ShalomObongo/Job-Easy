"""Main Tailoring Service.

Orchestrates the complete tailoring pipeline from profile/JD to
tailored resume, cover letter, PDFs, and review packet.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from src.tailoring.config import TailoringConfig, get_tailoring_config
from src.tailoring.cover_letter import CoverLetterService
from src.tailoring.plan import TailoringPlanService
from src.tailoring.renderer import PDFRenderer
from src.tailoring.resume import ResumeTailoringService
from src.tailoring.review import ReviewPacketService

if TYPE_CHECKING:
    from src.extractor.models import JobDescription
    from src.scoring.models import UserProfile
    from src.tailoring.models import (
        CoverLetter,
        DocReviewPacket,
        TailoredResume,
        TailoringPlan,
    )

logger = logging.getLogger(__name__)


@dataclass
class TailoringResult:
    """Result of a complete tailoring operation."""

    success: bool
    error: str | None = None

    # Generated artifacts
    plan: TailoringPlan | None = None
    resume: TailoredResume | None = None
    cover_letter: CoverLetter | None = None
    review_packet: DocReviewPacket | None = None

    # File paths
    resume_path: str | None = None
    cover_letter_path: str | None = None

    # Metadata
    completed_at: datetime = field(default_factory=datetime.now)


class TailoringService:
    """Main service for document tailoring.

    Orchestrates the complete pipeline:
    1. Generate tailoring plan from profile and JD
    2. Tailor resume with keywords and evidence
    3. Generate cover letter (optional)
    4. Render PDFs
    5. Create review packet for HITL confirmation
    """

    def __init__(self, config: TailoringConfig | None = None):
        """Initialize the tailoring service.

        Args:
            config: Optional TailoringConfig. Uses global config if not provided.
        """
        self.config = config or get_tailoring_config()

        # Initialize sub-services
        self.plan_service = TailoringPlanService(config=self.config)
        self.resume_service = ResumeTailoringService(config=self.config)
        self.cover_letter_service = CoverLetterService(config=self.config)
        self.renderer = PDFRenderer(config=self.config)
        self.review_service = ReviewPacketService(config=self.config)

    async def tailor(
        self,
        profile: UserProfile,
        job: JobDescription,
        generate_cover_letter: bool = True,
    ) -> TailoringResult:
        """Run the complete tailoring pipeline.

        Args:
            profile: User's profile with skills and experience.
            job: Job description to tailor for.
            generate_cover_letter: Whether to generate a cover letter.

        Returns:
            TailoringResult with all artifacts or error.
        """
        logger.info(f"Starting tailoring pipeline for {job.company} - {job.role_title}")

        try:
            # Step 1: Generate tailoring plan
            logger.info("Step 1: Generating tailoring plan...")
            plan = await self.plan_service.generate_plan(profile, job)

            # Step 2: Tailor resume
            logger.info("Step 2: Tailoring resume...")
            resume = await self.resume_service.tailor_resume(profile, job, plan)

            # Step 3: Generate cover letter (optional)
            cover_letter = None
            if generate_cover_letter:
                logger.info("Step 3: Generating cover letter...")
                cover_letter = await self.cover_letter_service.generate_cover_letter(
                    profile, job, plan
                )

            # Step 4: Render PDFs
            logger.info("Step 4: Rendering PDFs...")
            resume_result = self.renderer.render_resume(resume)
            if not resume_result.success:
                return TailoringResult(
                    success=False,
                    error=f"Failed to render resume: {resume_result.error}",
                    plan=plan,
                    resume=resume,
                )

            cover_letter_path = None
            if cover_letter:
                cover_result = self.renderer.render_cover_letter(cover_letter)
                if cover_result.success:
                    cover_letter_path = cover_result.file_path
                else:
                    logger.warning(
                        f"Failed to render cover letter: {cover_result.error}"
                    )

            # Step 5: Create review packet
            logger.info("Step 5: Creating review packet...")
            review_packet = self.review_service.create_review_packet(
                plan=plan,
                resume=resume,
                resume_path=resume_result.file_path,
                cover_letter=cover_letter,
                cover_letter_path=cover_letter_path,
            )

            logger.info("Tailoring pipeline completed successfully")

            return TailoringResult(
                success=True,
                plan=plan,
                resume=resume,
                cover_letter=cover_letter,
                review_packet=review_packet,
                resume_path=resume_result.file_path,
                cover_letter_path=cover_letter_path,
            )

        except Exception as e:
            logger.error(f"Tailoring pipeline failed: {e}")
            return TailoringResult(
                success=False,
                error=str(e),
            )

    async def tailor_resume_only(
        self,
        profile: UserProfile,
        job: JobDescription,
    ) -> TailoringResult:
        """Tailor resume only, without cover letter.

        Args:
            profile: User's profile.
            job: Job description.

        Returns:
            TailoringResult with resume artifacts.
        """
        return await self.tailor(profile, job, generate_cover_letter=False)
