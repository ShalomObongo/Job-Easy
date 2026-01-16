"""Unit tests for the main TailoringService.

Tests for full tailoring pipeline, service initialization,
error handling, and output artifacts.
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.extractor.models import JobDescription
from src.scoring.models import Education, UserProfile, WorkExperience
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
)
from src.tailoring.service import TailoringResult, TailoringService


@pytest.fixture
def sample_job_description():
    """Create a sample job description for testing."""
    return JobDescription(
        company="Acme Corp",
        role_title="Senior Python Developer",
        job_url="https://acme.com/jobs/123",
        location="San Francisco, CA",
        description="Join our team to build scalable Python applications.",
        responsibilities=["Design microservices", "Lead code reviews"],
        required_skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
        preferred_skills=["Kubernetes", "Redis"],
        experience_years_min=5,
    )


@pytest.fixture
def sample_user_profile():
    """Create a sample user profile for testing."""
    return UserProfile(
        name="John Doe",
        email="john@example.com",
        phone="555-123-4567",
        location="San Francisco, CA",
        linkedin_url="https://linkedin.com/in/johndoe",
        skills=["Python", "FastAPI", "Django", "PostgreSQL", "Docker", "AWS"],
        years_of_experience=8,
        current_title="Senior Software Engineer",
        summary="Experienced software engineer.",
        work_history=[
            WorkExperience(
                company="Tech Corp",
                title="Senior Software Engineer",
                start_date="2020-01-01",
                end_date=None,
                description="Led Python development",
                skills_used=["Python", "FastAPI"],
            )
        ],
        education=[
            Education(
                institution="MIT",
                degree="Bachelor's",
                field="Computer Science",
                graduation_year=2016,
            )
        ],
    )


@pytest.fixture
def mock_tailoring_plan():
    """Create a mock tailoring plan."""
    return TailoringPlan(
        job_url="https://acme.com/jobs/123",
        company="Acme Corp",
        role_title="Senior Python Developer",
        keyword_matches=[
            KeywordMatch(job_keyword="Python", user_skill="Python", confidence=1.0)
        ],
        evidence_mappings=[
            EvidenceMapping(
                requirement="5+ years Python",
                evidence="8 years experience",
                source_company="Tech Corp",
                source_role="Senior Engineer",
                relevance_score=0.9,
            )
        ],
        section_order=["summary", "experience", "skills"],
        bullet_rewrites=[],
        unsupported_claims=[],
    )


@pytest.fixture
def mock_tailored_resume():
    """Create a mock tailored resume."""
    return TailoredResume(
        name="John Doe",
        email="john@example.com",
        phone="555-123-4567",
        location="San Francisco, CA",
        linkedin_url="https://linkedin.com/in/johndoe",
        summary="Senior Python developer with 8 years experience.",
        sections=[
            TailoredSection(
                name="experience",
                title="Experience",
                content="",
                bullets=[
                    TailoredBullet(text="Led Python development", keywords_used=["Python"])
                ],
            )
        ],
        keywords_used=["Python", "FastAPI"],
        target_job_url="https://acme.com/jobs/123",
        target_company="Acme Corp",
        target_role="Senior Python Developer",
    )


@pytest.fixture
def mock_cover_letter():
    """Create a mock cover letter."""
    return CoverLetter(
        opening="Dear Hiring Manager...",
        body="I am excited to apply...",
        closing="Best regards, John Doe",
        full_text="Full text",
        word_count=350,
        target_job_url="https://acme.com/jobs/123",
        target_company="Acme Corp",
        target_role="Senior Python Developer",
        key_qualifications=["Python", "Leadership"],
    )


class TestTailoringServiceConfiguration:
    """Tests for TailoringService configuration."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    def test_uses_default_config(self):
        """Test that service uses default config when not provided."""
        service = TailoringService()
        assert service.config is not None

    def test_uses_custom_config(self):
        """Test that service uses provided config."""
        config = TailoringConfig(llm_provider="anthropic")
        service = TailoringService(config=config)
        assert service.config.llm_provider == "anthropic"


class TestFullTailoringPipeline:
    """Tests for full tailoring pipeline."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    @pytest.mark.asyncio
    async def test_tailor_returns_complete_result(
        self,
        sample_user_profile,
        sample_job_description,
        mock_tailoring_plan,
        mock_tailored_resume,
        mock_cover_letter,
    ):
        """Test that tailor returns a complete TailoringResult."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = TailoringConfig(output_dir=Path(tmpdir))

            with (
                patch(
                    "src.tailoring.service.TailoringPlanService"
                ) as mock_plan_service,
                patch(
                    "src.tailoring.service.ResumeTailoringService"
                ) as mock_resume_service,
                patch(
                    "src.tailoring.service.CoverLetterService"
                ) as mock_cover_service,
            ):
                # Set up mocks
                mock_plan_service.return_value.generate_plan = AsyncMock(
                    return_value=mock_tailoring_plan
                )
                mock_resume_service.return_value.tailor_resume = AsyncMock(
                    return_value=mock_tailored_resume
                )
                mock_cover_service.return_value.generate_cover_letter = AsyncMock(
                    return_value=mock_cover_letter
                )

                service = TailoringService(config=config)
                result = await service.tailor(sample_user_profile, sample_job_description)

                assert isinstance(result, TailoringResult)
                assert result.success
                assert result.plan is not None
                assert result.resume is not None
                assert result.cover_letter is not None
                assert result.review_packet is not None

    @pytest.mark.asyncio
    async def test_tailor_without_cover_letter(
        self,
        sample_user_profile,
        sample_job_description,
        mock_tailoring_plan,
        mock_tailored_resume,
    ):
        """Test tailoring without cover letter generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = TailoringConfig(output_dir=Path(tmpdir))

            with (
                patch(
                    "src.tailoring.service.TailoringPlanService"
                ) as mock_plan_service,
                patch(
                    "src.tailoring.service.ResumeTailoringService"
                ) as mock_resume_service,
            ):
                mock_plan_service.return_value.generate_plan = AsyncMock(
                    return_value=mock_tailoring_plan
                )
                mock_resume_service.return_value.tailor_resume = AsyncMock(
                    return_value=mock_tailored_resume
                )

                service = TailoringService(config=config)
                result = await service.tailor(
                    sample_user_profile,
                    sample_job_description,
                    generate_cover_letter=False,
                )

                assert result.success
                assert result.cover_letter is None


class TestServiceInitialization:
    """Tests for service initialization."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    def test_initializes_sub_services(self):
        """Test that sub-services are initialized."""
        service = TailoringService()
        assert service.plan_service is not None
        assert service.resume_service is not None
        assert service.cover_letter_service is not None
        assert service.renderer is not None
        assert service.review_service is not None


class TestErrorHandling:
    """Tests for error handling."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    @pytest.mark.asyncio
    async def test_handles_plan_generation_error(
        self, sample_user_profile, sample_job_description
    ):
        """Test handling of plan generation errors."""
        with patch("src.tailoring.service.TailoringPlanService") as mock_plan_service:
            mock_plan_service.return_value.generate_plan = AsyncMock(
                side_effect=Exception("LLM Error")
            )

            service = TailoringService()
            result = await service.tailor(sample_user_profile, sample_job_description)

            assert not result.success
            assert result.error is not None
            assert "LLM Error" in result.error


class TestOutputArtifacts:
    """Tests for output artifacts."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    @pytest.mark.asyncio
    async def test_generates_pdf_files(
        self,
        sample_user_profile,
        sample_job_description,
        mock_tailoring_plan,
        mock_tailored_resume,
        mock_cover_letter,
    ):
        """Test that PDF files are generated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = TailoringConfig(output_dir=Path(tmpdir))

            with (
                patch(
                    "src.tailoring.service.TailoringPlanService"
                ) as mock_plan_service,
                patch(
                    "src.tailoring.service.ResumeTailoringService"
                ) as mock_resume_service,
                patch(
                    "src.tailoring.service.CoverLetterService"
                ) as mock_cover_service,
            ):
                mock_plan_service.return_value.generate_plan = AsyncMock(
                    return_value=mock_tailoring_plan
                )
                mock_resume_service.return_value.tailor_resume = AsyncMock(
                    return_value=mock_tailored_resume
                )
                mock_cover_service.return_value.generate_cover_letter = AsyncMock(
                    return_value=mock_cover_letter
                )

                service = TailoringService(config=config)
                result = await service.tailor(sample_user_profile, sample_job_description)

                assert result.success
                assert result.resume_path is not None
                assert Path(result.resume_path).exists()

    @pytest.mark.asyncio
    async def test_review_packet_includes_file_paths(
        self,
        sample_user_profile,
        sample_job_description,
        mock_tailoring_plan,
        mock_tailored_resume,
        mock_cover_letter,
    ):
        """Test that review packet includes file paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = TailoringConfig(output_dir=Path(tmpdir))

            with (
                patch(
                    "src.tailoring.service.TailoringPlanService"
                ) as mock_plan_service,
                patch(
                    "src.tailoring.service.ResumeTailoringService"
                ) as mock_resume_service,
                patch(
                    "src.tailoring.service.CoverLetterService"
                ) as mock_cover_service,
            ):
                mock_plan_service.return_value.generate_plan = AsyncMock(
                    return_value=mock_tailoring_plan
                )
                mock_resume_service.return_value.tailor_resume = AsyncMock(
                    return_value=mock_tailored_resume
                )
                mock_cover_service.return_value.generate_cover_letter = AsyncMock(
                    return_value=mock_cover_letter
                )

                service = TailoringService(config=config)
                result = await service.tailor(sample_user_profile, sample_job_description)

                assert result.review_packet is not None
                assert result.review_packet.resume_path is not None
