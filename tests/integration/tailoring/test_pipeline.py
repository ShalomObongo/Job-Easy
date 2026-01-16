"""Integration tests for the full tailoring pipeline.

These tests require LLM API keys and make real API calls.
Mark with @pytest.mark.integration to skip in CI without API keys.
"""

import tempfile
from pathlib import Path

import pytest

from src.extractor.models import JobDescription
from src.scoring.models import Education, UserProfile, WorkExperience
from src.tailoring import TailoringConfig, TailoringService
from src.tailoring.config import reset_tailoring_config


@pytest.fixture
def integration_job_description():
    """Create a realistic job description for integration testing."""
    return JobDescription(
        company="TechCorp Inc",
        role_title="Senior Backend Engineer",
        job_url="https://techcorp.com/careers/backend-senior",
        location="Remote (US)",
        description="""
        TechCorp is looking for a Senior Backend Engineer to join our Platform team.
        You'll be working on high-scale distributed systems that power our core product.
        """,
        responsibilities=[
            "Design and implement scalable backend services",
            "Lead technical discussions and mentor junior engineers",
            "Collaborate with product and design teams",
        ],
        qualifications=[
            "5+ years of backend development experience",
            "Strong proficiency in Python",
            "Experience with distributed systems",
        ],
        required_skills=["Python", "SQL", "Docker", "Git"],
        preferred_skills=["Go", "Kubernetes", "Redis"],
        experience_years_min=5,
        experience_years_max=10,
        work_type="remote",
        employment_type="full-time",
    )


@pytest.fixture
def integration_user_profile():
    """Create a realistic user profile for integration testing."""
    return UserProfile(
        name="Jane Smith",
        email="jane.smith@email.com",
        phone="555-123-4567",
        location="Austin, TX",
        linkedin_url="https://linkedin.com/in/janesmith",
        skills=[
            "Python",
            "Django",
            "FastAPI",
            "PostgreSQL",
            "Redis",
            "Docker",
            "AWS",
            "Git",
        ],
        years_of_experience=7,
        current_title="Senior Software Engineer",
        summary="Backend engineer with 7 years of experience building scalable systems.",
        work_history=[
            WorkExperience(
                company="ScaleUp Technologies",
                title="Senior Software Engineer",
                start_date="2021-03-01",
                end_date=None,
                description="Lead backend development for the payments platform. Designed microservices handling 50K+ transactions daily.",
                skills_used=["Python", "FastAPI", "PostgreSQL", "Redis", "Docker", "AWS"],
            ),
            WorkExperience(
                company="WebDev Agency",
                title="Software Engineer",
                start_date="2018-06-01",
                end_date="2021-02-28",
                description="Built Django web applications for enterprise clients. Reduced API response times by 40%.",
                skills_used=["Python", "Django", "PostgreSQL", "Git"],
            ),
        ],
        education=[
            Education(
                institution="University of Texas",
                degree="Bachelor's",
                field="Computer Science",
                graduation_year=2016,
            )
        ],
        work_type_preferences=["remote", "hybrid"],
        visa_sponsorship_needed=False,
        experience_level="senior",
    )


@pytest.mark.integration
class TestFullPipelineIntegration:
    """Integration tests for full tailoring pipeline with real LLM calls."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    @pytest.mark.asyncio
    async def test_complete_tailoring_pipeline(
        self, integration_job_description, integration_user_profile
    ):
        """Test the complete tailoring pipeline end-to-end."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = TailoringConfig(output_dir=Path(tmpdir))
            service = TailoringService(config=config)

            result = await service.tailor(
                integration_user_profile, integration_job_description
            )

            # Verify success
            assert result.success, f"Pipeline failed: {result.error}"

            # Verify all artifacts generated
            assert result.plan is not None
            assert result.resume is not None
            assert result.cover_letter is not None
            assert result.review_packet is not None

            # Verify PDF files created
            assert result.resume_path is not None
            assert Path(result.resume_path).exists()
            assert result.cover_letter_path is not None
            assert Path(result.cover_letter_path).exists()

    @pytest.mark.asyncio
    async def test_tailoring_plan_quality(
        self, integration_job_description, integration_user_profile
    ):
        """Test that tailoring plan has quality content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = TailoringConfig(output_dir=Path(tmpdir))
            service = TailoringService(config=config)

            result = await service.tailor(
                integration_user_profile, integration_job_description
            )

            assert result.success
            plan = result.plan

            # Should have keyword matches
            assert len(plan.keyword_matches) > 0

            # Python should be matched with high confidence
            python_matches = [
                m for m in plan.keyword_matches if "python" in m.job_keyword.lower()
            ]
            assert len(python_matches) > 0

            # Should have section order
            assert len(plan.section_order) > 0

    @pytest.mark.asyncio
    async def test_resume_contains_keywords(
        self, integration_job_description, integration_user_profile
    ):
        """Test that tailored resume contains job keywords."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = TailoringConfig(output_dir=Path(tmpdir))
            service = TailoringService(config=config)

            result = await service.tailor(
                integration_user_profile, integration_job_description
            )

            assert result.success
            resume = result.resume

            # Should have keywords integrated
            assert len(resume.keywords_used) > 0

            # Resume should preserve contact info
            assert resume.name == integration_user_profile.name
            assert resume.email == integration_user_profile.email

    @pytest.mark.asyncio
    async def test_cover_letter_word_count(
        self, integration_job_description, integration_user_profile
    ):
        """Test that cover letter meets word count target."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = TailoringConfig(output_dir=Path(tmpdir))
            service = TailoringService(config=config)

            result = await service.tailor(
                integration_user_profile, integration_job_description
            )

            assert result.success
            cover = result.cover_letter

            # Word count should be in range
            assert cover.word_count >= 200  # Allow some flexibility
            assert cover.word_count <= 500

            # Should be personalized
            assert integration_job_description.company in cover.full_text

    @pytest.mark.asyncio
    async def test_review_packet_completeness(
        self, integration_job_description, integration_user_profile
    ):
        """Test that review packet is complete."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = TailoringConfig(output_dir=Path(tmpdir))
            service = TailoringService(config=config)

            result = await service.tailor(
                integration_user_profile, integration_job_description
            )

            assert result.success
            packet = result.review_packet

            # Should have job info
            assert packet.company == integration_job_description.company
            assert packet.role_title == integration_job_description.role_title

            # Should have changes summary
            assert len(packet.changes_summary) > 0

            # Should have keywords highlighted
            assert len(packet.keywords_highlighted) > 0

            # Should have file paths
            assert packet.resume_path is not None
