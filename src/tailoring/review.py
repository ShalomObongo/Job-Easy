"""Doc Review Packet Service.

Generates review summaries for HITL confirmation before document upload,
including changes made, keywords highlighted, and evidence mapping.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

from src.tailoring.config import TailoringConfig, get_tailoring_config
from src.tailoring.models import DocReviewPacket

if TYPE_CHECKING:
    from src.tailoring.models import CoverLetter, TailoredResume, TailoringPlan

logger = logging.getLogger(__name__)


class ReviewPacketService:
    """Service for creating doc review packets.

    Generates summaries of tailoring changes for human review
    before uploading documents.
    """

    def __init__(self, config: TailoringConfig | None = None):
        """Initialize the review packet service.

        Args:
            config: Optional TailoringConfig. Uses global config if not provided.
        """
        self.config = config or get_tailoring_config()

    def create_review_packet(
        self,
        plan: TailoringPlan,
        resume: TailoredResume,
        resume_path: str,
        cover_letter: CoverLetter | None = None,
        cover_letter_path: str | None = None,
    ) -> DocReviewPacket:
        """Create a review packet summarizing tailoring changes.

        Args:
            plan: The tailoring plan used.
            resume: The tailored resume.
            resume_path: Path to the generated resume PDF.
            cover_letter: Optional cover letter.
            cover_letter_path: Optional path to cover letter PDF.

        Returns:
            DocReviewPacket for HITL review.
        """
        logger.info(f"Creating review packet for {plan.company} - {plan.role_title}")

        # Generate changes summary
        changes_summary = self._generate_changes_summary(plan, resume, cover_letter)

        # Extract highlighted keywords
        keywords_highlighted = self._extract_keywords(plan, resume)

        # Build requirements vs evidence mapping
        requirements_vs_evidence = self._build_evidence_mapping(plan)

        packet = DocReviewPacket(
            job_url=plan.job_url,
            company=plan.company,
            role_title=plan.role_title,
            changes_summary=changes_summary,
            keywords_highlighted=keywords_highlighted,
            requirements_vs_evidence=requirements_vs_evidence,
            resume_path=resume_path,
            cover_letter_path=cover_letter_path,
            generated_at=datetime.now(),
        )

        logger.info(
            f"Review packet created with {len(changes_summary)} changes, "
            f"{len(keywords_highlighted)} keywords"
        )

        return packet

    def _generate_changes_summary(
        self,
        plan: TailoringPlan,
        resume: TailoredResume,
        cover_letter: CoverLetter | None,
    ) -> list[str]:
        """Generate a summary of changes made.

        Args:
            plan: The tailoring plan.
            resume: The tailored resume.
            cover_letter: Optional cover letter.

        Returns:
            List of change descriptions.
        """
        changes = []

        # Keyword matches
        if plan.keyword_matches:
            high_confidence = [m for m in plan.keyword_matches if m.confidence >= 0.9]
            changes.append(
                f"Integrated {len(plan.keyword_matches)} job keywords "
                f"({len(high_confidence)} with high confidence match)"
            )

        # Section reordering
        if plan.section_order:
            changes.append(
                f"Reordered resume sections for relevance: {' → '.join(plan.section_order[:4])}"
            )

        # Evidence mappings
        if plan.evidence_mappings:
            changes.append(
                f"Mapped {len(plan.evidence_mappings)} job requirements "
                "to your experience"
            )

        # Bullet rewrites
        if plan.bullet_rewrites:
            changes.append(
                f"Suggested {len(plan.bullet_rewrites)} bullet point rewrites"
            )

        # Resume keywords
        if resume.keywords_used:
            changes.append(
                f"Resume highlights {len(resume.keywords_used)} relevant skills"
            )

        # Cover letter
        if cover_letter:
            changes.append(
                f"Generated {cover_letter.word_count}-word cover letter with "
                f"{len(cover_letter.key_qualifications)} key qualifications"
            )

        # Warnings
        if plan.unsupported_claims:
            critical = [c for c in plan.unsupported_claims if c.severity == "critical"]
            warnings = [c for c in plan.unsupported_claims if c.severity == "warning"]
            if critical:
                changes.append(
                    f"⚠️ {len(critical)} critical requirements not supported by your profile"
                )
            if warnings:
                changes.append(f"ℹ️ {len(warnings)} preferred requirements not matched")

        return changes

    def _extract_keywords(
        self,
        plan: TailoringPlan,
        resume: TailoredResume,
    ) -> list[str]:
        """Extract keywords to highlight.

        Args:
            plan: The tailoring plan.
            resume: The tailored resume.

        Returns:
            List of keywords.
        """
        keywords = set()

        # From plan keyword matches
        for match in plan.keyword_matches:
            keywords.add(match.job_keyword)

        # From resume keywords used
        for kw in resume.keywords_used:
            keywords.add(kw)

        return sorted(keywords)

    def _build_evidence_mapping(
        self,
        plan: TailoringPlan,
    ) -> list[dict[str, Any]]:
        """Build requirements vs evidence mapping.

        Args:
            plan: The tailoring plan.

        Returns:
            List of requirement/evidence mappings.
        """
        mappings = []

        # Matched requirements
        for mapping in plan.evidence_mappings:
            mappings.append(
                {
                    "requirement": mapping.requirement,
                    "evidence": mapping.evidence,
                    "source": f"{mapping.source_company} - {mapping.source_role}",
                    "relevance": mapping.relevance_score,
                    "matched": True,
                }
            )

        # Unmatched requirements (unsupported claims)
        for claim in plan.unsupported_claims:
            mappings.append(
                {
                    "requirement": claim.requirement,
                    "evidence": None,
                    "reason": claim.reason,
                    "severity": claim.severity,
                    "matched": False,
                }
            )

        return mappings
