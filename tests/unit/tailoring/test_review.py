"""Unit tests for the Doc Review Packet.

Tests for review summary generation, keyword highlighting,
evidence mapping display, and file path collection.
"""

from datetime import datetime

import pytest

from src.tailoring.config import TailoringConfig, reset_tailoring_config
from src.tailoring.models import (
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
from src.tailoring.review import ReviewPacketService


@pytest.fixture
def sample_tailoring_plan():
    """Create a sample tailoring plan for testing."""
    return TailoringPlan(
        job_url="https://acme.com/jobs/123",
        company="Acme Corp",
        role_title="Senior Python Developer",
        keyword_matches=[
            KeywordMatch(job_keyword="Python", user_skill="Python", confidence=1.0),
            KeywordMatch(job_keyword="FastAPI", user_skill="FastAPI", confidence=0.95),
            KeywordMatch(job_keyword="Docker", user_skill="Docker", confidence=0.9),
        ],
        evidence_mappings=[
            EvidenceMapping(
                requirement="5+ years Python experience",
                evidence="8 years developing Python applications",
                source_company="Tech Corp",
                source_role="Senior Software Engineer",
                relevance_score=0.95,
            ),
            EvidenceMapping(
                requirement="Experience with microservices",
                evidence="Led development of microservices handling 10K+ requests/sec",
                source_company="Tech Corp",
                source_role="Senior Software Engineer",
                relevance_score=0.9,
            ),
        ],
        section_order=["summary", "experience", "skills", "education"],
        bullet_rewrites=[],
        unsupported_claims=[
            UnsupportedClaim(
                requirement="Kubernetes certification",
                reason="No Kubernetes certification found",
                severity="warning",
            )
        ],
    )


@pytest.fixture
def sample_tailored_resume():
    """Create a sample tailored resume for testing."""
    return TailoredResume(
        name="John Doe",
        email="john@example.com",
        phone="555-123-4567",
        location="San Francisco, CA",
        linkedin_url="https://linkedin.com/in/johndoe",
        summary="Senior Python developer with 8 years of experience.",
        sections=[
            TailoredSection(
                name="experience",
                title="Experience",
                content="",
                bullets=[
                    TailoredBullet(
                        text="Led FastAPI microservices development",
                        keywords_used=["FastAPI", "microservices"],
                    )
                ],
            )
        ],
        keywords_used=["Python", "FastAPI", "Docker"],
        target_job_url="https://acme.com/jobs/123",
        target_company="Acme Corp",
        target_role="Senior Python Developer",
    )


@pytest.fixture
def sample_cover_letter():
    """Create a sample cover letter for testing."""
    return CoverLetter(
        opening="Dear Hiring Manager...",
        body="I am excited to apply...",
        closing="Best regards, John Doe",
        full_text="Full cover letter text",
        word_count=350,
        target_job_url="https://acme.com/jobs/123",
        target_company="Acme Corp",
        target_role="Senior Python Developer",
        key_qualifications=["8 years Python", "Microservices"],
    )


class TestReviewPacketServiceConfiguration:
    """Tests for ReviewPacketService configuration."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    def test_uses_default_config(self):
        """Test that service uses default config when not provided."""
        service = ReviewPacketService()
        assert service.config is not None

    def test_uses_custom_config(self):
        """Test that service uses provided config."""
        config = TailoringConfig(llm_provider="anthropic")
        service = ReviewPacketService(config=config)
        assert service.config.llm_provider == "anthropic"


class TestReviewSummaryGeneration:
    """Tests for review summary generation."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    def test_generates_changes_summary(
        self, sample_tailoring_plan, sample_tailored_resume, sample_cover_letter
    ):
        """Test that changes summary is generated."""
        service = ReviewPacketService()
        packet = service.create_review_packet(
            plan=sample_tailoring_plan,
            resume=sample_tailored_resume,
            cover_letter=sample_cover_letter,
            resume_path="/path/resume.pdf",
            cover_letter_path="/path/cover.pdf",
        )

        assert isinstance(packet, DocReviewPacket)
        assert len(packet.changes_summary) > 0

    def test_summary_includes_keyword_count(
        self, sample_tailoring_plan, sample_tailored_resume, sample_cover_letter
    ):
        """Test that summary includes keyword count."""
        service = ReviewPacketService()
        packet = service.create_review_packet(
            plan=sample_tailoring_plan,
            resume=sample_tailored_resume,
            cover_letter=sample_cover_letter,
            resume_path="/path/resume.pdf",
        )

        # Should mention keywords
        summary_text = " ".join(packet.changes_summary).lower()
        assert "keyword" in summary_text or len(packet.keywords_highlighted) > 0


class TestKeywordHighlighting:
    """Tests for keyword highlighting."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    def test_highlights_keywords_from_plan(
        self, sample_tailoring_plan, sample_tailored_resume, sample_cover_letter
    ):
        """Test that keywords from plan are highlighted."""
        service = ReviewPacketService()
        packet = service.create_review_packet(
            plan=sample_tailoring_plan,
            resume=sample_tailored_resume,
            cover_letter=sample_cover_letter,
            resume_path="/path/resume.pdf",
        )

        assert len(packet.keywords_highlighted) > 0
        assert "Python" in packet.keywords_highlighted

    def test_includes_matched_keywords(
        self, sample_tailoring_plan, sample_tailored_resume, sample_cover_letter
    ):
        """Test that matched keywords are included."""
        _ = sample_cover_letter
        service = ReviewPacketService()
        packet = service.create_review_packet(
            plan=sample_tailoring_plan,
            resume=sample_tailored_resume,
            resume_path="/path/resume.pdf",
        )

        # Keywords should come from plan's keyword matches
        expected_keywords = {"Python", "FastAPI", "Docker"}
        assert expected_keywords.issubset(set(packet.keywords_highlighted))


class TestEvidenceMappingDisplay:
    """Tests for evidence mapping display."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    def test_includes_requirements_vs_evidence(
        self, sample_tailoring_plan, sample_tailored_resume, sample_cover_letter
    ):
        """Test that requirements vs evidence mapping is included."""
        service = ReviewPacketService()
        packet = service.create_review_packet(
            plan=sample_tailoring_plan,
            resume=sample_tailored_resume,
            cover_letter=sample_cover_letter,
            resume_path="/path/resume.pdf",
        )

        assert len(packet.requirements_vs_evidence) > 0

    def test_evidence_mapping_structure(
        self, sample_tailoring_plan, sample_tailored_resume, sample_cover_letter
    ):
        """Test that evidence mapping has correct structure."""
        _ = sample_cover_letter
        service = ReviewPacketService()
        packet = service.create_review_packet(
            plan=sample_tailoring_plan,
            resume=sample_tailored_resume,
            resume_path="/path/resume.pdf",
        )

        for mapping in packet.requirements_vs_evidence:
            assert "requirement" in mapping
            assert "matched" in mapping

    def test_flags_unmatched_requirements(
        self, sample_tailoring_plan, sample_tailored_resume, sample_cover_letter
    ):
        """Test that unmatched requirements are flagged."""
        _ = sample_cover_letter
        service = ReviewPacketService()
        packet = service.create_review_packet(
            plan=sample_tailoring_plan,
            resume=sample_tailored_resume,
            resume_path="/path/resume.pdf",
        )

        # Should include unsupported claims as unmatched
        unmatched = [m for m in packet.requirements_vs_evidence if not m.get("matched")]
        # Plan has one unsupported claim
        assert len(unmatched) >= 1


class TestFilePathCollection:
    """Tests for file path collection."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    def test_includes_resume_path(
        self, sample_tailoring_plan, sample_tailored_resume, sample_cover_letter
    ):
        """Test that resume path is included."""
        _ = sample_cover_letter
        service = ReviewPacketService()
        packet = service.create_review_packet(
            plan=sample_tailoring_plan,
            resume=sample_tailored_resume,
            resume_path="/path/to/resume.pdf",
        )

        assert packet.resume_path == "/path/to/resume.pdf"

    def test_includes_cover_letter_path_when_provided(
        self, sample_tailoring_plan, sample_tailored_resume, sample_cover_letter
    ):
        """Test that cover letter path is included when provided."""
        service = ReviewPacketService()
        packet = service.create_review_packet(
            plan=sample_tailoring_plan,
            resume=sample_tailored_resume,
            cover_letter=sample_cover_letter,
            resume_path="/path/resume.pdf",
            cover_letter_path="/path/cover.pdf",
        )

        assert packet.cover_letter_path == "/path/cover.pdf"

    def test_cover_letter_path_optional(
        self, sample_tailoring_plan, sample_tailored_resume
    ):
        """Test that cover letter path is optional."""
        service = ReviewPacketService()
        packet = service.create_review_packet(
            plan=sample_tailoring_plan,
            resume=sample_tailored_resume,
            resume_path="/path/resume.pdf",
        )

        assert packet.cover_letter_path is None


class TestReviewPacketMetadata:
    """Tests for review packet metadata."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    def test_includes_job_info(
        self, sample_tailoring_plan, sample_tailored_resume, sample_cover_letter
    ):
        """Test that job info is included."""
        _ = sample_cover_letter
        service = ReviewPacketService()
        packet = service.create_review_packet(
            plan=sample_tailoring_plan,
            resume=sample_tailored_resume,
            resume_path="/path/resume.pdf",
        )

        assert packet.job_url == "https://acme.com/jobs/123"
        assert packet.company == "Acme Corp"
        assert packet.role_title == "Senior Python Developer"

    def test_includes_generation_timestamp(
        self, sample_tailoring_plan, sample_tailored_resume
    ):
        """Test that generation timestamp is included."""
        service = ReviewPacketService()
        packet = service.create_review_packet(
            plan=sample_tailoring_plan,
            resume=sample_tailored_resume,
            resume_path="/path/resume.pdf",
        )

        assert packet.generated_at is not None
        assert isinstance(packet.generated_at, datetime)

    def test_packet_serialization(self, sample_tailoring_plan, sample_tailored_resume):
        """Test that packet can be serialized to dict."""
        service = ReviewPacketService()
        packet = service.create_review_packet(
            plan=sample_tailoring_plan,
            resume=sample_tailored_resume,
            resume_path="/path/resume.pdf",
        )

        data = packet.to_dict()
        assert isinstance(data, dict)
        assert data["company"] == "Acme Corp"
