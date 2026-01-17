"""Unit tests for the Tailoring Plan Generator.

Tests for keyword extraction, skill matching, evidence mapping,
unsupported claims detection, and section reordering.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.extractor.models import JobDescription
from src.scoring.models import Education, UserProfile, WorkExperience
from src.tailoring.config import TailoringConfig, reset_tailoring_config
from src.tailoring.models import (
    BulletRewrite,
    EvidenceMapping,
    KeywordMatch,
    TailoringPlan,
    UnsupportedClaim,
)
from src.tailoring.plan import TailoringPlanService


@pytest.fixture
def sample_job_description():
    """Create a sample job description for testing."""
    return JobDescription(
        company="Acme Corp",
        role_title="Senior Python Developer",
        job_url="https://acme.com/jobs/123",
        location="San Francisco, CA",
        description="We are looking for a Senior Python Developer to join our team.",
        responsibilities=[
            "Design and implement scalable microservices",
            "Lead code reviews and mentor junior developers",
            "Collaborate with product team on feature requirements",
        ],
        qualifications=[
            "5+ years of Python experience",
            "Experience with FastAPI or Django",
            "Strong knowledge of SQL databases",
            "Experience with AWS or GCP",
        ],
        required_skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
        preferred_skills=["Kubernetes", "Redis", "GraphQL"],
        experience_years_min=5,
        experience_years_max=10,
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
        summary="Experienced software engineer with expertise in Python and distributed systems.",
        work_history=[
            WorkExperience(
                company="Tech Corp",
                title="Senior Software Engineer",
                start_date="2020-01-01",
                end_date=None,
                description="Led development of Python microservices handling 10K+ requests/sec",
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


class TestKeywordExtraction:
    """Tests for extracting keywords from job descriptions."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    @pytest.mark.asyncio
    async def test_extracts_required_skills_as_keywords(
        self, sample_job_description, sample_user_profile
    ):
        """Test that required skills are extracted as keywords."""
        mock_plan = TailoringPlan(
            job_url=sample_job_description.job_url,
            company=sample_job_description.company,
            role_title=sample_job_description.role_title,
            keyword_matches=[
                KeywordMatch(job_keyword="Python", user_skill="Python", confidence=1.0),
                KeywordMatch(
                    job_keyword="FastAPI", user_skill="FastAPI", confidence=1.0
                ),
            ],
            evidence_mappings=[],
            section_order=["experience", "skills", "education"],
            bullet_rewrites=[],
            unsupported_claims=[],
        )

        with patch.object(
            TailoringPlanService, "_generate_plan_with_llm", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.return_value = mock_plan

            service = TailoringPlanService()
            plan = await service.generate_plan(
                sample_user_profile, sample_job_description
            )

            assert len(plan.keyword_matches) >= 2
            keywords = [m.job_keyword for m in plan.keyword_matches]
            assert "Python" in keywords
            assert "FastAPI" in keywords


class TestSkillMatching:
    """Tests for matching user skills to job requirements."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    @pytest.mark.asyncio
    async def test_matches_exact_skills(
        self, sample_job_description, sample_user_profile
    ):
        """Test exact skill matches have high confidence."""
        mock_plan = TailoringPlan(
            job_url=sample_job_description.job_url,
            company=sample_job_description.company,
            role_title=sample_job_description.role_title,
            keyword_matches=[
                KeywordMatch(job_keyword="Python", user_skill="Python", confidence=1.0),
                KeywordMatch(job_keyword="Docker", user_skill="Docker", confidence=1.0),
            ],
            evidence_mappings=[],
            section_order=["experience", "skills"],
            bullet_rewrites=[],
            unsupported_claims=[],
        )

        with patch.object(
            TailoringPlanService, "_generate_plan_with_llm", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.return_value = mock_plan

            service = TailoringPlanService()
            plan = await service.generate_plan(
                sample_user_profile, sample_job_description
            )

            python_match = next(
                (m for m in plan.keyword_matches if m.job_keyword == "Python"), None
            )
            assert python_match is not None
            assert python_match.confidence >= 0.9

    @pytest.mark.asyncio
    async def test_matches_similar_skills(
        self, sample_job_description, sample_user_profile
    ):
        """Test similar skills are matched with appropriate confidence."""
        mock_plan = TailoringPlan(
            job_url=sample_job_description.job_url,
            company=sample_job_description.company,
            role_title=sample_job_description.role_title,
            keyword_matches=[
                KeywordMatch(
                    job_keyword="AWS or GCP", user_skill="AWS", confidence=0.85
                ),
            ],
            evidence_mappings=[],
            section_order=["experience"],
            bullet_rewrites=[],
            unsupported_claims=[],
        )

        with patch.object(
            TailoringPlanService, "_generate_plan_with_llm", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.return_value = mock_plan

            service = TailoringPlanService()
            plan = await service.generate_plan(
                sample_user_profile, sample_job_description
            )

            # AWS should match "AWS or GCP" requirement
            aws_match = next(
                (m for m in plan.keyword_matches if "AWS" in m.job_keyword), None
            )
            assert aws_match is not None


class TestEvidenceMapping:
    """Tests for mapping user experience to job requirements."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    @pytest.mark.asyncio
    async def test_maps_experience_to_requirements(
        self, sample_job_description, sample_user_profile
    ):
        """Test that experience is mapped to job requirements."""
        mock_plan = TailoringPlan(
            job_url=sample_job_description.job_url,
            company=sample_job_description.company,
            role_title=sample_job_description.role_title,
            keyword_matches=[],
            evidence_mappings=[
                EvidenceMapping(
                    requirement="5+ years of Python experience",
                    evidence="8 years developing Python applications at Tech Corp and StartupXYZ",
                    source_company="Tech Corp",
                    source_role="Senior Software Engineer",
                    relevance_score=0.95,
                ),
                EvidenceMapping(
                    requirement="Design and implement scalable microservices",
                    evidence="Led development of Python microservices handling 10K+ requests/sec",
                    source_company="Tech Corp",
                    source_role="Senior Software Engineer",
                    relevance_score=0.9,
                ),
            ],
            section_order=["experience", "skills"],
            bullet_rewrites=[],
            unsupported_claims=[],
        )

        with patch.object(
            TailoringPlanService, "_generate_plan_with_llm", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.return_value = mock_plan

            service = TailoringPlanService()
            plan = await service.generate_plan(
                sample_user_profile, sample_job_description
            )

            assert len(plan.evidence_mappings) >= 1
            # Check that experience requirement is mapped
            exp_mapping = next(
                (m for m in plan.evidence_mappings if "years" in m.requirement.lower()),
                None,
            )
            assert exp_mapping is not None
            assert exp_mapping.relevance_score > 0.8


class TestUnsupportedClaimsDetection:
    """Tests for detecting requirements without supporting evidence."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    @pytest.mark.asyncio
    async def test_flags_missing_skills(
        self, sample_job_description, sample_user_profile
    ):
        """Test that missing required skills are flagged."""
        # User doesn't have Kubernetes
        mock_plan = TailoringPlan(
            job_url=sample_job_description.job_url,
            company=sample_job_description.company,
            role_title=sample_job_description.role_title,
            keyword_matches=[],
            evidence_mappings=[],
            section_order=["experience"],
            bullet_rewrites=[],
            unsupported_claims=[
                UnsupportedClaim(
                    requirement="Kubernetes experience",
                    reason="No Kubernetes experience found in profile",
                    severity="warning",
                )
            ],
        )

        with patch.object(
            TailoringPlanService, "_generate_plan_with_llm", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.return_value = mock_plan

            service = TailoringPlanService()
            plan = await service.generate_plan(
                sample_user_profile, sample_job_description
            )

            # Kubernetes is in preferred_skills but user doesn't have it
            k8s_warning = next(
                (c for c in plan.unsupported_claims if "Kubernetes" in c.requirement),
                None,
            )
            assert k8s_warning is not None
            assert k8s_warning.severity == "warning"


class TestSectionReordering:
    """Tests for section reordering recommendations."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    @pytest.mark.asyncio
    async def test_recommends_section_order(
        self, sample_job_description, sample_user_profile
    ):
        """Test that section order is recommended based on job relevance."""
        mock_plan = TailoringPlan(
            job_url=sample_job_description.job_url,
            company=sample_job_description.company,
            role_title=sample_job_description.role_title,
            keyword_matches=[],
            evidence_mappings=[],
            section_order=["summary", "experience", "skills", "education"],
            bullet_rewrites=[],
            unsupported_claims=[],
        )

        with patch.object(
            TailoringPlanService, "_generate_plan_with_llm", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.return_value = mock_plan

            service = TailoringPlanService()
            plan = await service.generate_plan(
                sample_user_profile, sample_job_description
            )

            assert len(plan.section_order) >= 3
            # Experience should be high priority for senior role
            assert "experience" in plan.section_order


class TestBulletRewriteSuggestions:
    """Tests for bullet rewrite suggestions."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    @pytest.mark.asyncio
    async def test_suggests_bullet_rewrites(
        self, sample_job_description, sample_user_profile
    ):
        """Test that bullet rewrites are suggested to add keywords."""
        mock_plan = TailoringPlan(
            job_url=sample_job_description.job_url,
            company=sample_job_description.company,
            role_title=sample_job_description.role_title,
            keyword_matches=[],
            evidence_mappings=[],
            section_order=["experience"],
            bullet_rewrites=[
                BulletRewrite(
                    original="Led development of Python microservices",
                    suggested="Architected and deployed Python microservices using FastAPI, handling 10K+ requests/sec with Docker containers on AWS",
                    keywords_added=["FastAPI", "Docker", "AWS"],
                    emphasis_reason="Aligns with required skills: FastAPI, Docker, AWS",
                )
            ],
            unsupported_claims=[],
        )

        with patch.object(
            TailoringPlanService, "_generate_plan_with_llm", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.return_value = mock_plan

            service = TailoringPlanService()
            plan = await service.generate_plan(
                sample_user_profile, sample_job_description
            )

            assert len(plan.bullet_rewrites) >= 1
            rewrite = plan.bullet_rewrites[0]
            assert len(rewrite.keywords_added) > 0


class TestTailoringPlanServiceConfiguration:
    """Tests for TailoringPlanService configuration."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    def test_uses_default_config(self):
        """Test that service uses default config when not provided."""
        service = TailoringPlanService()
        assert service.config is not None
        assert service.llm is not None

    def test_uses_custom_config(self):
        """Test that service uses provided config."""
        config = TailoringConfig(llm_provider="anthropic", llm_model="claude-3-opus")
        service = TailoringPlanService(config=config)
        assert service.config.llm_provider == "anthropic"
