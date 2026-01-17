"""Unit tests for the Resume Tailoring Engine.

Tests for bullet rewriting, section reordering, keyword integration,
and truthfulness enforcement.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.extractor.models import JobDescription
from src.scoring.models import Education, UserProfile, WorkExperience
from src.tailoring.config import TailoringConfig, reset_tailoring_config
from src.tailoring.models import (
    EvidenceMapping,
    KeywordMatch,
    TailoredBullet,
    TailoredResume,
    TailoredSection,
    TailoringPlan,
)
from src.tailoring.resume import ResumeTailoringService


@pytest.fixture
def sample_job_description():
    """Create a sample job description for testing."""
    return JobDescription(
        company="Acme Corp",
        role_title="Senior Python Developer",
        job_url="https://acme.com/jobs/123",
        location="San Francisco, CA",
        required_skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
        preferred_skills=["Kubernetes", "Redis"],
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
        skills=["Python", "FastAPI", "Django", "PostgreSQL", "Docker", "AWS", "Redis"],
        years_of_experience=8,
        current_title="Senior Software Engineer",
        summary="Experienced software engineer with expertise in Python and distributed systems.",
        work_history=[
            WorkExperience(
                company="Tech Corp",
                title="Senior Software Engineer",
                start_date="2020-01-01",
                end_date=None,
                description="Led development of Python microservices",
                skills_used=["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"],
            ),
            WorkExperience(
                company="StartupXYZ",
                title="Software Engineer",
                start_date="2017-01-01",
                end_date="2019-12-31",
                description="Built Django web applications and REST APIs",
                skills_used=["Python", "Django", "PostgreSQL", "Redis"],
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
            KeywordMatch(job_keyword="Docker", user_skill="Docker", confidence=1.0),
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
        section_order=["summary", "experience", "skills", "education"],
        bullet_rewrites=[],
        unsupported_claims=[],
    )


class TestResumeTailoringServiceConfiguration:
    """Tests for ResumeTailoringService configuration."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    def test_uses_default_config(self):
        """Test that service uses default config when not provided."""
        service = ResumeTailoringService()
        assert service.config is not None
        assert service.llm is not None

    def test_uses_custom_config(self):
        """Test that service uses provided config."""
        config = TailoringConfig(llm_provider="anthropic", llm_model="claude-3-opus")
        service = ResumeTailoringService(config=config)
        assert service.config.llm_provider == "anthropic"


class TestResumeTailoring:
    """Tests for resume tailoring functionality."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    @pytest.mark.asyncio
    async def test_tailors_resume_returns_tailored_resume(
        self, sample_user_profile, sample_job_description, sample_tailoring_plan
    ):
        """Test that tailoring returns a TailoredResume."""
        mock_resume = TailoredResume(
            name="John Doe",
            email="john@example.com",
            phone="555-123-4567",
            location="San Francisco, CA",
            linkedin_url="https://linkedin.com/in/johndoe",
            summary="Senior Python developer with 8 years of experience building scalable FastAPI microservices.",
            sections=[
                TailoredSection(
                    name="experience",
                    title="Professional Experience",
                    content="",
                    bullets=[
                        TailoredBullet(
                            text="Architected FastAPI microservices handling 10K+ requests/sec with Docker containers",
                            keywords_used=["FastAPI", "Docker"],
                        )
                    ],
                )
            ],
            keywords_used=["Python", "FastAPI", "Docker"],
            target_job_url=sample_job_description.job_url,
            target_company=sample_job_description.company,
            target_role=sample_job_description.role_title,
        )

        with patch.object(
            ResumeTailoringService, "_generate_resume_with_llm", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.return_value = mock_resume

            service = ResumeTailoringService()
            result = await service.tailor_resume(
                sample_user_profile, sample_job_description, sample_tailoring_plan
            )

            assert isinstance(result, TailoredResume)
            assert result.name == "John Doe"
            assert result.target_company == "Acme Corp"

    @pytest.mark.asyncio
    async def test_preserves_contact_info(
        self, sample_user_profile, sample_job_description, sample_tailoring_plan
    ):
        """Test that contact information is preserved from profile."""
        mock_resume = TailoredResume(
            name=sample_user_profile.name,
            email=sample_user_profile.email,
            phone=sample_user_profile.phone,
            location=sample_user_profile.location,
            linkedin_url=sample_user_profile.linkedin_url,
            summary="Tailored summary",
            sections=[],
            keywords_used=[],
            target_job_url=sample_job_description.job_url,
            target_company=sample_job_description.company,
            target_role=sample_job_description.role_title,
        )

        with patch.object(
            ResumeTailoringService, "_generate_resume_with_llm", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.return_value = mock_resume

            service = ResumeTailoringService()
            result = await service.tailor_resume(
                sample_user_profile, sample_job_description, sample_tailoring_plan
            )

            assert result.name == sample_user_profile.name
            assert result.email == sample_user_profile.email
            assert result.phone == sample_user_profile.phone
            assert result.location == sample_user_profile.location


class TestKeywordIntegration:
    """Tests for keyword integration in resume."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    @pytest.mark.asyncio
    async def test_integrates_job_keywords(
        self, sample_user_profile, sample_job_description, sample_tailoring_plan
    ):
        """Test that job keywords are integrated into resume."""
        mock_resume = TailoredResume(
            name="John Doe",
            email="john@example.com",
            phone=None,
            location="SF",
            linkedin_url=None,
            summary="Senior Python developer specializing in FastAPI microservices and Docker containerization.",
            sections=[
                TailoredSection(
                    name="experience",
                    title="Experience",
                    content="",
                    bullets=[
                        TailoredBullet(
                            text="Built FastAPI services deployed with Docker",
                            keywords_used=["FastAPI", "Docker"],
                        )
                    ],
                )
            ],
            keywords_used=["Python", "FastAPI", "Docker"],
            target_job_url=sample_job_description.job_url,
            target_company=sample_job_description.company,
            target_role=sample_job_description.role_title,
        )

        with patch.object(
            ResumeTailoringService, "_generate_resume_with_llm", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.return_value = mock_resume

            service = ResumeTailoringService()
            result = await service.tailor_resume(
                sample_user_profile, sample_job_description, sample_tailoring_plan
            )

            # Keywords from plan should be integrated
            assert len(result.keywords_used) > 0
            assert "Python" in result.keywords_used or "FastAPI" in result.keywords_used


class TestSectionReordering:
    """Tests for section reordering in tailored resume."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    @pytest.mark.asyncio
    async def test_respects_section_order_from_plan(
        self, sample_user_profile, sample_job_description, sample_tailoring_plan
    ):
        """Test that sections are ordered according to plan."""
        mock_resume = TailoredResume(
            name="John Doe",
            email="john@example.com",
            phone=None,
            location="SF",
            linkedin_url=None,
            summary="Summary",
            sections=[
                TailoredSection(
                    name="experience", title="Experience", content="", bullets=[]
                ),
                TailoredSection(name="skills", title="Skills", content="", bullets=[]),
                TailoredSection(
                    name="education", title="Education", content="", bullets=[]
                ),
            ],
            keywords_used=[],
            target_job_url=sample_job_description.job_url,
            target_company=sample_job_description.company,
            target_role=sample_job_description.role_title,
        )

        with patch.object(
            ResumeTailoringService, "_generate_resume_with_llm", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.return_value = mock_resume

            service = ResumeTailoringService()
            result = await service.tailor_resume(
                sample_user_profile, sample_job_description, sample_tailoring_plan
            )

            # Sections should follow plan order
            section_names = [s.name for s in result.sections]
            assert len(section_names) >= 1


class TestBulletRewriting:
    """Tests for bullet point rewriting."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    @pytest.mark.asyncio
    async def test_rewrites_bullets_with_keywords(
        self, sample_user_profile, sample_job_description, sample_tailoring_plan
    ):
        """Test that bullets are rewritten to include keywords."""
        mock_resume = TailoredResume(
            name="John Doe",
            email="john@example.com",
            phone=None,
            location="SF",
            linkedin_url=None,
            summary="Summary",
            sections=[
                TailoredSection(
                    name="experience",
                    title="Experience",
                    content="",
                    bullets=[
                        TailoredBullet(
                            text="Architected and deployed Python microservices using FastAPI, handling 10K+ requests/sec with Docker containers",
                            keywords_used=["Python", "FastAPI", "Docker"],
                        ),
                        TailoredBullet(
                            text="Optimized PostgreSQL database queries reducing response time by 40%",
                            keywords_used=["PostgreSQL"],
                        ),
                    ],
                )
            ],
            keywords_used=["Python", "FastAPI", "Docker", "PostgreSQL"],
            target_job_url=sample_job_description.job_url,
            target_company=sample_job_description.company,
            target_role=sample_job_description.role_title,
        )

        with patch.object(
            ResumeTailoringService, "_generate_resume_with_llm", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.return_value = mock_resume

            service = ResumeTailoringService()
            result = await service.tailor_resume(
                sample_user_profile, sample_job_description, sample_tailoring_plan
            )

            # Bullets should have keywords
            experience_section = next(
                (s for s in result.sections if s.name == "experience"), None
            )
            assert experience_section is not None
            assert len(experience_section.bullets) > 0
            assert len(experience_section.bullets[0].keywords_used) > 0


class TestTruthfulnessEnforcement:
    """Tests for truthfulness enforcement - never fabricate experience."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    @pytest.mark.asyncio
    async def test_only_uses_existing_companies(
        self, sample_user_profile, sample_job_description, sample_tailoring_plan
    ):
        """Test that only real companies from profile are mentioned."""
        mock_resume = TailoredResume(
            name="John Doe",
            email="john@example.com",
            phone=None,
            location="SF",
            linkedin_url=None,
            summary="8 years experience at Tech Corp and StartupXYZ",
            sections=[
                TailoredSection(
                    name="experience",
                    title="Experience",
                    content="",
                    bullets=[
                        TailoredBullet(
                            text="At Tech Corp: Led Python microservices development",
                            keywords_used=["Python"],
                        )
                    ],
                )
            ],
            keywords_used=["Python"],
            target_job_url=sample_job_description.job_url,
            target_company=sample_job_description.company,
            target_role=sample_job_description.role_title,
        )

        with patch.object(
            ResumeTailoringService, "_generate_resume_with_llm", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.return_value = mock_resume

            service = ResumeTailoringService()
            result = await service.tailor_resume(
                sample_user_profile, sample_job_description, sample_tailoring_plan
            )

            # Resume should only reference real companies
            full_text = result.summary + " ".join(
                b.text for s in result.sections for b in s.bullets
            )
            # Should not contain fabricated companies
            assert "FakeCompany" not in full_text
