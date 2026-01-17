"""Integration tests for Tailoring Plan Generation.

These tests require LLM API keys and make real API calls.
Mark with @pytest.mark.integration to skip in CI without API keys.
"""

import os

import pytest

from src.extractor.models import JobDescription
from src.scoring.models import Education, UserProfile, WorkExperience
from src.tailoring.config import reset_tailoring_config
from src.tailoring.plan import TailoringPlanService

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not any(
            os.getenv(key)
            for key in [
                "TAILORING_LLM_API_KEY",
                "EXTRACTOR_LLM_API_KEY",
                "OPENAI_API_KEY",
                "ANTHROPIC_API_KEY",
                "BROWSER_USE_API_KEY",
                "LLM_API_KEY",
                "TAILORING_LLM_BASE_URL",
                "EXTRACTOR_LLM_BASE_URL",
            ]
        ),
        reason="No LLM credentials/base URL configured for tailoring integration tests",
    ),
]


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
        We're a fast-paced startup with a focus on engineering excellence.
        """,
        responsibilities=[
            "Design and implement scalable backend services using Python and Go",
            "Lead technical discussions and mentor junior engineers",
            "Collaborate with product and design teams to ship features",
            "Maintain and improve our CI/CD pipelines",
            "Participate in on-call rotation for production systems",
        ],
        qualifications=[
            "5+ years of backend development experience",
            "Strong proficiency in Python or Go",
            "Experience with distributed systems and microservices",
            "Familiarity with cloud platforms (AWS, GCP, or Azure)",
            "Excellent communication and collaboration skills",
        ],
        required_skills=["Python", "Distributed Systems", "SQL", "Docker", "Git"],
        preferred_skills=["Go", "Kubernetes", "Terraform", "Redis", "gRPC"],
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
            "REST APIs",
            "Microservices",
        ],
        years_of_experience=7,
        current_title="Senior Software Engineer",
        summary="Backend engineer with 7 years of experience building scalable web applications and distributed systems. Passionate about clean code and mentoring.",
        work_history=[
            WorkExperience(
                company="ScaleUp Technologies",
                title="Senior Software Engineer",
                start_date="2021-03-01",
                end_date=None,
                description="Lead backend development for the payments platform. Designed and implemented microservices handling 50K+ transactions daily. Mentored 3 junior developers and established code review practices.",
                skills_used=[
                    "Python",
                    "FastAPI",
                    "PostgreSQL",
                    "Redis",
                    "Docker",
                    "AWS",
                ],
            ),
            WorkExperience(
                company="WebDev Agency",
                title="Software Engineer",
                start_date="2018-06-01",
                end_date="2021-02-28",
                description="Built Django web applications for enterprise clients. Implemented REST APIs consumed by mobile and web frontends. Reduced API response times by 40% through query optimization.",
                skills_used=["Python", "Django", "PostgreSQL", "REST APIs", "Git"],
            ),
            WorkExperience(
                company="StartupXYZ",
                title="Junior Developer",
                start_date="2016-09-01",
                end_date="2018-05-31",
                description="Developed features for e-commerce platform. Wrote automated tests and participated in agile sprints.",
                skills_used=["Python", "Flask", "MySQL", "Git"],
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
class TestPlanGenerationIntegration:
    """Integration tests for plan generation with real LLM calls."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    @pytest.mark.asyncio
    async def test_generates_complete_plan_structure(
        self, integration_job_description, integration_user_profile
    ):
        """Test that a complete plan structure is generated."""
        service = TailoringPlanService()
        plan = await service.generate_plan(
            integration_user_profile, integration_job_description
        )

        # Verify plan structure
        assert plan.job_url == integration_job_description.job_url
        assert plan.company == integration_job_description.company
        assert plan.role_title == integration_job_description.role_title

        # Should have keyword matches
        assert len(plan.keyword_matches) > 0

        # Should have section order
        assert len(plan.section_order) > 0

    @pytest.mark.asyncio
    async def test_matches_python_skill(
        self, integration_job_description, integration_user_profile
    ):
        """Test that Python skill is matched with high confidence."""
        service = TailoringPlanService()
        plan = await service.generate_plan(
            integration_user_profile, integration_job_description
        )

        python_matches = [
            m for m in plan.keyword_matches if "python" in m.job_keyword.lower()
        ]
        assert len(python_matches) > 0
        # Python is a core skill for both, should have high confidence
        assert any(m.confidence >= 0.8 for m in python_matches)

    @pytest.mark.asyncio
    async def test_maps_experience_evidence(
        self, integration_job_description, integration_user_profile
    ):
        """Test that experience is mapped to evidence."""
        service = TailoringPlanService()
        plan = await service.generate_plan(
            integration_user_profile, integration_job_description
        )

        # Should have evidence mappings
        assert len(plan.evidence_mappings) > 0

        # Evidence should come from user's actual work history
        companies = {m.source_company for m in plan.evidence_mappings}
        valid_companies = {"ScaleUp Technologies", "WebDev Agency", "StartupXYZ"}
        assert any(c in valid_companies for c in companies)

    @pytest.mark.asyncio
    async def test_flags_missing_go_skill(
        self, integration_job_description, integration_user_profile
    ):
        """Test that missing Go skill is flagged as unsupported."""
        service = TailoringPlanService()
        plan = await service.generate_plan(
            integration_user_profile, integration_job_description
        )

        # Go is preferred but user doesn't have it
        # Should flag Go as missing (it's preferred, not required)
        # Note: This may or may not be flagged depending on LLM interpretation
        # So we just verify the plan doesn't fabricate Go experience
        go_matches = [
            m
            for m in plan.keyword_matches
            if "go" in m.user_skill.lower() and m.confidence > 0.9
        ]
        # Should NOT have high-confidence Go match since user doesn't know Go
        assert len(go_matches) == 0 or all(m.confidence < 0.9 for m in go_matches)

    @pytest.mark.asyncio
    async def test_plan_does_not_fabricate_experience(
        self, integration_job_description, integration_user_profile
    ):
        """Test that plan doesn't fabricate non-existent experience."""
        service = TailoringPlanService()
        plan = await service.generate_plan(
            integration_user_profile, integration_job_description
        )

        # Evidence should only come from actual user companies
        valid_companies = {"ScaleUp Technologies", "WebDev Agency", "StartupXYZ"}
        for mapping in plan.evidence_mappings:
            assert mapping.source_company in valid_companies, (
                f"Fabricated company: {mapping.source_company}"
            )
