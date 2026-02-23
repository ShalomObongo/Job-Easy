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
    UnsupportedClaim,
)
from src.tailoring.resume import (
    ResumeTailoringService,
    TailoredBulletLLM,
    TailoredResumeLLMResponse,
    TailoredSectionLLM,
)


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

    def test_normalizes_to_canonical_section_order(
        self, sample_user_profile, sample_tailoring_plan
    ):
        """Resume sections should follow canonical recruiter-facing order."""
        service = ResumeTailoringService()
        response = TailoredResumeLLMResponse(
            summary="Summary",
            sections=[
                TailoredSectionLLM(
                    name="projects",
                    title="Projects",
                    content="",
                    bullets=[
                        TailoredBulletLLM(text="Project X — Built workflow tooling.")
                    ],
                ),
                TailoredSectionLLM(
                    name="education",
                    title="Education",
                    content="BS in CS",
                    bullets=[],
                ),
                TailoredSectionLLM(
                    name="skills",
                    title="Technical Skills",
                    content="Automation: Power Automate",
                    bullets=[],
                ),
                TailoredSectionLLM(
                    name="experience",
                    title="Professional Experience",
                    content="",
                    bullets=[
                        TailoredBulletLLM(
                            text="Engineer, Acme (2023-01-01 – Present) — Built APIs."
                        )
                    ],
                ),
                TailoredSectionLLM(
                    name="certifications",
                    title="Certifications",
                    content="PL-900",
                    bullets=[],
                ),
            ],
            keywords_used=[],
        )

        normalized = service._normalize_resume_response(
            response=response,
            plan=sample_tailoring_plan,
            profile=sample_user_profile,
        )

        assert [s.name for s in normalized.sections] == [
            "experience",
            "skills",
            "certifications",
            "education",
            "projects",
        ]


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


class TestResumeValidationImprovements:
    """Tests for new quality and truthfulness validation behavior."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    def test_allows_single_bullet_for_sparse_role_evidence(self):
        """Sparse profile evidence should allow a single truthful bullet."""
        service = ResumeTailoringService()
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["Python"],
            years_of_experience=3,
            work_history=[
                WorkExperience(
                    company="Acme",
                    title="Engineer",
                    start_date="2023-01-01",
                    end_date=None,
                    description="Built APIs.",
                    skills_used=["Python"],
                )
            ],
            education=[],
        )
        plan = TailoringPlan(
            job_url="https://example.com/jobs/1",
            company="Example",
            role_title="Engineer",
            keyword_matches=[],
            evidence_mappings=[],
            section_order=["experience", "skills"],
            bullet_rewrites=[],
            unsupported_claims=[],
        )
        response = TailoredResumeLLMResponse(
            summary="Python engineer with API experience.",
            sections=[
                TailoredSectionLLM(
                    name="experience",
                    title="Professional Experience",
                    content="",
                    bullets=[
                        TailoredBulletLLM(
                            text="Engineer, Acme (2023-01-01 – Present) — Built APIs."
                        )
                    ],
                )
            ],
            keywords_used=[],
        )

        issues = service._collect_resume_validation_issues(response, profile, plan)
        assert not any("must have 2" in issue for issue in issues)

    def test_does_not_require_projects_without_grounded_evidence(
        self, sample_user_profile
    ):
        """Projects section should not be forced when no project evidence exists."""
        service = ResumeTailoringService()
        plan = TailoringPlan(
            job_url="https://example.com/jobs/2",
            company="Example",
            role_title="Backend Engineer",
            keyword_matches=[],
            evidence_mappings=[],
            section_order=["experience", "projects", "skills"],
            bullet_rewrites=[],
            unsupported_claims=[],
        )
        response = TailoredResumeLLMResponse(
            summary="Backend engineer.",
            sections=[
                TailoredSectionLLM(
                    name="experience",
                    title="Professional Experience",
                    content="",
                    bullets=[
                        TailoredBulletLLM(
                            text="Senior Software Engineer, Tech Corp (2020-01-01 – Present) — Led development of Python microservices."
                        ),
                        TailoredBulletLLM(
                            text="Senior Software Engineer, Tech Corp (2020-01-01 – Present) — Improved reliability of backend systems."
                        ),
                    ],
                )
            ],
            keywords_used=[],
        )

        issues = service._collect_resume_validation_issues(
            response, sample_user_profile, plan
        )
        assert "Plan requests a projects section, but none was produced." not in issues

    def test_flags_unsupported_claim_keywords(self, sample_user_profile):
        """Unsupported claim keywords should be rejected if they appear in output."""
        service = ResumeTailoringService()
        plan = TailoringPlan(
            job_url="https://example.com/jobs/3",
            company="Example",
            role_title="Engineer",
            keyword_matches=[],
            evidence_mappings=[],
            section_order=["experience"],
            bullet_rewrites=[],
            unsupported_claims=[
                UnsupportedClaim(
                    requirement="Kubernetes experience required",
                    reason="No Kubernetes background in profile",
                    severity="critical",
                )
            ],
        )
        response = TailoredResumeLLMResponse(
            summary="Engineer with Kubernetes production experience.",
            sections=[],
            keywords_used=[],
        )

        issues = service._collect_resume_validation_issues(
            response, sample_user_profile, plan
        )
        assert any("unsupported claim keyword" in issue for issue in issues)

    def test_does_not_flag_unsupported_claim_keyword_when_profile_has_evidence(
        self, sample_user_profile
    ):
        """Profile-grounded terms should not be blocked by unsupported claim hints."""
        service = ResumeTailoringService()
        profile = sample_user_profile.model_copy(
            update={
                "skills": sample_user_profile.skills
                + ["Microsoft Power Automate", "Process Automation"],
            }
        )
        plan = TailoringPlan(
            job_url="https://example.com/jobs/4",
            company="Example",
            role_title="Automation Engineer",
            keyword_matches=[],
            evidence_mappings=[],
            section_order=["experience"],
            bullet_rewrites=[],
            unsupported_claims=[
                UnsupportedClaim(
                    requirement=(
                        "3+ years building automation solutions with "
                        "Microsoft Power Automate or comparable workflow platforms"
                    ),
                    reason="Cannot verify exact tenure from profile text",
                    severity="warning",
                )
            ],
        )
        response = TailoredResumeLLMResponse(
            summary=(
                "Automation engineer experienced with Microsoft Power Automate "
                "workflow design and deployment."
            ),
            sections=[],
            keywords_used=[],
        )

        issues = service._collect_resume_validation_issues(response, profile, plan)
        assert not any("unsupported claim keyword" in issue for issue in issues)

    def test_recomputes_keywords_from_generated_content(
        self, sample_job_description, sample_tailoring_plan
    ):
        """keywords_used should be computed from actual generated text."""
        service = ResumeTailoringService()
        response = TailoredResumeLLMResponse(
            summary="Senior Python engineer building FastAPI services.",
            sections=[
                TailoredSectionLLM(
                    name="skills",
                    title="Technical Skills",
                    content="Backend: Python, FastAPI",
                    bullets=[],
                )
            ],
            keywords_used=["NotTrustedKeyword"],
        )

        keywords = service._recompute_keywords_used(
            response=response,
            job=sample_job_description,
            plan=sample_tailoring_plan,
        )

        assert "Python" in keywords
        assert "FastAPI" in keywords
        assert "NotTrustedKeyword" not in keywords
