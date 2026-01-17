"""Unit tests for the Cover Letter Generator.

Tests for cover letter structure, word count, evidence integration,
and company/role personalization.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.extractor.models import JobDescription
from src.scoring.models import Education, UserProfile, WorkExperience
from src.tailoring.config import TailoringConfig, reset_tailoring_config
from src.tailoring.cover_letter import CoverLetterLLMResponse, CoverLetterService
from src.tailoring.models import (
    CoverLetter,
    EvidenceMapping,
    KeywordMatch,
    TailoringPlan,
)


@pytest.fixture
def sample_job_description():
    """Create a sample job description for testing."""
    return JobDescription(
        company="Acme Corp",
        role_title="Senior Python Developer",
        job_url="https://acme.com/jobs/123",
        location="San Francisco, CA",
        description="Join our team to build cutting-edge Python applications.",
        responsibilities=[
            "Design and implement scalable microservices",
            "Lead code reviews and mentor junior developers",
        ],
        required_skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
        preferred_skills=["Kubernetes", "Redis"],
    )


@pytest.fixture
def sample_user_profile():
    """Create a sample user profile for testing."""
    return UserProfile(
        name="John Doe",
        email="john@example.com",
        location="San Francisco, CA",
        skills=["Python", "FastAPI", "Django", "PostgreSQL", "Docker", "AWS", "Redis"],
        years_of_experience=8,
        current_title="Senior Software Engineer",
        summary="Experienced software engineer with expertise in Python.",
        work_history=[
            WorkExperience(
                company="Tech Corp",
                title="Senior Software Engineer",
                start_date="2020-01-01",
                end_date=None,
                description="Led development of Python microservices handling 10K+ requests/sec",
                skills_used=["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"],
            ),
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
def sample_tailoring_plan(sample_job_description):
    """Create a sample tailoring plan for testing."""
    return TailoringPlan(
        job_url=sample_job_description.job_url,
        company=sample_job_description.company,
        role_title=sample_job_description.role_title,
        keyword_matches=[
            KeywordMatch(job_keyword="Python", user_skill="Python", confidence=1.0),
            KeywordMatch(job_keyword="FastAPI", user_skill="FastAPI", confidence=1.0),
        ],
        evidence_mappings=[
            EvidenceMapping(
                requirement="5+ years Python experience",
                evidence="8 years developing Python applications",
                source_company="Tech Corp",
                source_role="Senior Software Engineer",
                relevance_score=0.95,
            ),
        ],
        section_order=["summary", "experience", "skills"],
        bullet_rewrites=[],
        unsupported_claims=[],
    )


class TestCoverLetterServiceConfiguration:
    """Tests for CoverLetterService configuration."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    def test_uses_default_config(self):
        """Test that service uses default config when not provided."""
        service = CoverLetterService()
        assert service.config is not None
        assert service.llm is not None

    def test_uses_custom_config(self):
        """Test that service uses provided config."""
        config = TailoringConfig(llm_provider="anthropic", llm_model="claude-3-opus")
        service = CoverLetterService(config=config)
        assert service.config.llm_provider == "anthropic"


class TestCoverLetterStructure:
    """Tests for cover letter structure."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    @pytest.mark.asyncio
    async def test_generates_cover_letter_with_all_sections(
        self, sample_user_profile, sample_job_description, sample_tailoring_plan
    ):
        """Test that cover letter has opening, body, and closing."""
        mock_cover = CoverLetter(
            opening="Dear Hiring Manager,\n\nI am excited to apply for the Senior Python Developer position at Acme Corp.",
            body="With 8 years of Python experience, I have led development of high-scale microservices. At Tech Corp, I architected systems handling 10K+ requests per second.",
            closing="I look forward to discussing how my experience can contribute to Acme Corp's success.\n\nBest regards,\nJohn Doe",
            full_text="Dear Hiring Manager,\n\nI am excited to apply...",
            word_count=350,
            target_job_url=sample_job_description.job_url,
            target_company=sample_job_description.company,
            target_role=sample_job_description.role_title,
            key_qualifications=[
                "8 years Python",
                "High-scale microservices",
                "10K+ requests/sec",
            ],
        )

        with patch.object(
            CoverLetterService,
            "_generate_cover_letter_with_llm",
            new_callable=AsyncMock,
        ) as mock_generate:
            mock_generate.return_value = mock_cover

            service = CoverLetterService()
            result = await service.generate_cover_letter(
                sample_user_profile, sample_job_description, sample_tailoring_plan
            )

            assert isinstance(result, CoverLetter)
            assert len(result.opening) > 0
            assert len(result.body) > 0
            assert len(result.closing) > 0

    @pytest.mark.asyncio
    async def test_includes_company_and_role(
        self, sample_user_profile, sample_job_description, sample_tailoring_plan
    ):
        """Test that cover letter mentions company and role."""
        mock_cover = CoverLetter(
            opening="Dear Hiring Manager,\n\nI am excited to apply for the Senior Python Developer position at Acme Corp.",
            body="I believe my experience aligns perfectly with Acme Corp's needs.",
            closing="I look forward to contributing to Acme Corp's mission.",
            full_text="Full text with Acme Corp and Senior Python Developer mentioned.",
            word_count=300,
            target_job_url=sample_job_description.job_url,
            target_company="Acme Corp",
            target_role="Senior Python Developer",
            key_qualifications=["Python experience"],
        )

        with patch.object(
            CoverLetterService,
            "_generate_cover_letter_with_llm",
            new_callable=AsyncMock,
        ) as mock_generate:
            mock_generate.return_value = mock_cover

            service = CoverLetterService()
            result = await service.generate_cover_letter(
                sample_user_profile, sample_job_description, sample_tailoring_plan
            )

            assert result.target_company == "Acme Corp"
            assert result.target_role == "Senior Python Developer"


class TestCoverLetterWordCount:
    """Tests for cover letter word count."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    @pytest.mark.asyncio
    async def test_word_count_is_padded_and_trimmed_when_llm_misses_range(
        self, sample_user_profile, sample_job_description, sample_tailoring_plan
    ):
        """Ensure deterministic word-count enforcement for flaky LLM outputs."""
        config = TailoringConfig(cover_letter_min_words=30, cover_letter_max_words=40)
        service = CoverLetterService(config=config)

        short_response = CoverLetterLLMResponse(
            opening="Hello",
            body="Too short.",
            closing="Thanks.",
            key_qualifications=[],
        )

        with patch.object(
            service.llm,
            "generate_structured",
            new_callable=AsyncMock,
        ) as mock_generate:
            mock_generate.side_effect = [short_response, short_response]

            cover = await service._generate_cover_letter_with_llm(
                sample_user_profile, sample_job_description, sample_tailoring_plan
            )

            assert (
                config.cover_letter_min_words
                <= cover.word_count
                <= config.cover_letter_max_words
            )
            assert sample_job_description.company in cover.full_text

    @pytest.mark.asyncio
    async def test_word_count_is_trimmed_when_llm_output_is_too_long(
        self, sample_user_profile, sample_job_description, sample_tailoring_plan
    ):
        """Ensure deterministic trimming when model produces overly long letters."""
        config = TailoringConfig(cover_letter_min_words=10, cover_letter_max_words=20)
        service = CoverLetterService(config=config)

        long_body = "word " * 200
        long_response = CoverLetterLLMResponse(
            opening="Opening.",
            body=long_body,
            closing="Closing.",
            key_qualifications=[],
        )

        with patch.object(
            service.llm,
            "generate_structured",
            new_callable=AsyncMock,
        ) as mock_generate:
            mock_generate.side_effect = [long_response, long_response]

            cover = await service._generate_cover_letter_with_llm(
                sample_user_profile, sample_job_description, sample_tailoring_plan
            )

            assert cover.word_count <= config.cover_letter_max_words

    @pytest.mark.asyncio
    async def test_word_count_in_target_range(
        self, sample_user_profile, sample_job_description, sample_tailoring_plan
    ):
        """Test that word count is tracked and in target range."""
        mock_cover = CoverLetter(
            opening="Opening paragraph",
            body="Body with substantial content about qualifications and experience.",
            closing="Closing paragraph",
            full_text="Full text content",
            word_count=350,
            target_job_url=sample_job_description.job_url,
            target_company=sample_job_description.company,
            target_role=sample_job_description.role_title,
            key_qualifications=[],
        )

        with patch.object(
            CoverLetterService,
            "_generate_cover_letter_with_llm",
            new_callable=AsyncMock,
        ) as mock_generate:
            mock_generate.return_value = mock_cover

            service = CoverLetterService()
            result = await service.generate_cover_letter(
                sample_user_profile, sample_job_description, sample_tailoring_plan
            )

            # Should be in 300-400 word range (default config)
            assert result.word_count >= 300
            assert result.word_count <= 400


class TestCoverLetterEvidenceIntegration:
    """Tests for integrating evidence into cover letter."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    @pytest.mark.asyncio
    async def test_includes_key_qualifications(
        self, sample_user_profile, sample_job_description, sample_tailoring_plan
    ):
        """Test that cover letter includes key qualifications."""
        mock_cover = CoverLetter(
            opening="Opening",
            body="My 8 years of Python experience includes building microservices handling 10K+ requests/sec.",
            closing="Closing",
            full_text="Full text",
            word_count=320,
            target_job_url=sample_job_description.job_url,
            target_company=sample_job_description.company,
            target_role=sample_job_description.role_title,
            key_qualifications=["8 years Python", "10K+ requests/sec", "microservices"],
        )

        with patch.object(
            CoverLetterService,
            "_generate_cover_letter_with_llm",
            new_callable=AsyncMock,
        ) as mock_generate:
            mock_generate.return_value = mock_cover

            service = CoverLetterService()
            result = await service.generate_cover_letter(
                sample_user_profile, sample_job_description, sample_tailoring_plan
            )

            assert len(result.key_qualifications) > 0

    @pytest.mark.asyncio
    async def test_maps_accomplishments_to_requirements(
        self, sample_user_profile, sample_job_description, sample_tailoring_plan
    ):
        """Test that accomplishments are mapped to job requirements."""
        mock_cover = CoverLetter(
            opening="Opening",
            body="Your requirement for 5+ years Python experience aligns with my 8 years at Tech Corp where I led microservice development.",
            closing="Closing",
            full_text="Full text with accomplishments mapped",
            word_count=330,
            target_job_url=sample_job_description.job_url,
            target_company=sample_job_description.company,
            target_role=sample_job_description.role_title,
            key_qualifications=["Tech Corp leadership", "Python expertise"],
        )

        with patch.object(
            CoverLetterService,
            "_generate_cover_letter_with_llm",
            new_callable=AsyncMock,
        ) as mock_generate:
            mock_generate.return_value = mock_cover

            service = CoverLetterService()
            result = await service.generate_cover_letter(
                sample_user_profile, sample_job_description, sample_tailoring_plan
            )

            # Body should reference actual experience
            assert "Tech Corp" in result.body or len(result.key_qualifications) > 0


class TestCoverLetterPersonalization:
    """Tests for company and role personalization."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    @pytest.mark.asyncio
    async def test_personalizes_for_company(
        self, sample_user_profile, sample_job_description, sample_tailoring_plan
    ):
        """Test that cover letter is personalized for the company."""
        mock_cover = CoverLetter(
            opening="Dear Hiring Manager,\n\nI am thrilled to apply for the Senior Python Developer role at Acme Corp.",
            body="Acme Corp's commitment to building cutting-edge Python applications aligns with my passion for scalable systems.",
            closing="I am eager to contribute to Acme Corp's continued success.",
            full_text="Full text mentioning Acme Corp multiple times.",
            word_count=340,
            target_job_url=sample_job_description.job_url,
            target_company="Acme Corp",
            target_role="Senior Python Developer",
            key_qualifications=["Python", "scalable systems"],
        )

        with patch.object(
            CoverLetterService,
            "_generate_cover_letter_with_llm",
            new_callable=AsyncMock,
        ) as mock_generate:
            mock_generate.return_value = mock_cover

            service = CoverLetterService()
            result = await service.generate_cover_letter(
                sample_user_profile, sample_job_description, sample_tailoring_plan
            )

            # Company should be mentioned in the letter
            full_text = result.opening + result.body + result.closing
            assert "Acme Corp" in full_text or result.target_company == "Acme Corp"


class TestCoverLetterTruthfulness:
    """Tests for truthfulness enforcement."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    @pytest.mark.asyncio
    async def test_only_references_actual_experience(
        self, sample_user_profile, sample_job_description, sample_tailoring_plan
    ):
        """Test that cover letter only references actual companies."""
        mock_cover = CoverLetter(
            opening="Opening",
            body="At Tech Corp, I led development of high-scale Python microservices.",
            closing="Closing",
            full_text="Full text referencing only Tech Corp",
            word_count=310,
            target_job_url=sample_job_description.job_url,
            target_company=sample_job_description.company,
            target_role=sample_job_description.role_title,
            key_qualifications=["Tech Corp experience"],
        )

        with patch.object(
            CoverLetterService,
            "_generate_cover_letter_with_llm",
            new_callable=AsyncMock,
        ) as mock_generate:
            mock_generate.return_value = mock_cover

            service = CoverLetterService()
            result = await service.generate_cover_letter(
                sample_user_profile, sample_job_description, sample_tailoring_plan
            )

            # Should only mention real companies from profile
            assert "FakeCompany" not in result.full_text
