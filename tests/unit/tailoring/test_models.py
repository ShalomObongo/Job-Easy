"""Unit tests for tailoring data models.

Tests TailoringPlan, TailoredResume, CoverLetter, and DocReviewPacket models.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from src.tailoring.models import (
    BulletRewrite,
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


class TestKeywordMatch:
    """Tests for KeywordMatch model."""

    def test_valid_keyword_match(self):
        """Test creating a valid keyword match."""
        match = KeywordMatch(
            job_keyword="Python",
            user_skill="Python 3.x",
            confidence=0.95,
        )
        assert match.job_keyword == "Python"
        assert match.user_skill == "Python 3.x"
        assert match.confidence == 0.95

    def test_confidence_bounds(self):
        """Test confidence must be between 0 and 1."""
        with pytest.raises(ValidationError):
            KeywordMatch(job_keyword="Python", user_skill="Python", confidence=1.5)

        with pytest.raises(ValidationError):
            KeywordMatch(job_keyword="Python", user_skill="Python", confidence=-0.1)

    def test_confidence_edge_values(self):
        """Test confidence at boundary values."""
        match_zero = KeywordMatch(job_keyword="Test", user_skill="Test", confidence=0.0)
        assert match_zero.confidence == 0.0

        match_one = KeywordMatch(job_keyword="Test", user_skill="Test", confidence=1.0)
        assert match_one.confidence == 1.0


class TestEvidenceMapping:
    """Tests for EvidenceMapping model."""

    def test_valid_evidence_mapping(self):
        """Test creating a valid evidence mapping."""
        mapping = EvidenceMapping(
            requirement="5+ years Python experience",
            evidence="8 years developing Python applications at Acme Corp",
            source_company="Acme Corp",
            source_role="Senior Developer",
            relevance_score=0.9,
        )
        assert mapping.requirement == "5+ years Python experience"
        assert mapping.evidence == "8 years developing Python applications at Acme Corp"
        assert mapping.source_company == "Acme Corp"

    def test_relevance_score_bounds(self):
        """Test relevance_score must be between 0 and 1."""
        with pytest.raises(ValidationError):
            EvidenceMapping(
                requirement="Req",
                evidence="Ev",
                source_company="Co",
                source_role="Role",
                relevance_score=2.0,
            )


class TestBulletRewrite:
    """Tests for BulletRewrite model."""

    def test_valid_bullet_rewrite(self):
        """Test creating a valid bullet rewrite suggestion."""
        rewrite = BulletRewrite(
            original="Developed software applications",
            suggested="Architected and deployed Python microservices handling 10K+ requests/sec",
            keywords_added=["Python", "microservices", "deployed"],
            emphasis_reason="Aligns with job requirement for distributed systems",
        )
        assert rewrite.original == "Developed software applications"
        assert "microservices" in rewrite.keywords_added

    def test_empty_keywords_allowed(self):
        """Test that empty keywords list is allowed."""
        rewrite = BulletRewrite(
            original="Original text",
            suggested="New text",
            keywords_added=[],
            emphasis_reason="Minor improvement",
        )
        assert rewrite.keywords_added == []


class TestUnsupportedClaim:
    """Tests for UnsupportedClaim model."""

    def test_valid_unsupported_claim(self):
        """Test creating an unsupported claim warning."""
        claim = UnsupportedClaim(
            requirement="Kubernetes certification",
            reason="No Kubernetes certification found in profile",
            severity="warning",
        )
        assert claim.requirement == "Kubernetes certification"
        assert claim.severity == "warning"

    def test_severity_values(self):
        """Test severity must be warning or critical."""
        claim = UnsupportedClaim(
            requirement="Req",
            reason="No evidence",
            severity="critical",
        )
        assert claim.severity == "critical"

        with pytest.raises(ValidationError):
            UnsupportedClaim(
                requirement="Req",
                reason="No evidence",
                severity="info",
            )


class TestTailoringPlan:
    """Tests for TailoringPlan model."""

    def test_valid_tailoring_plan(self):
        """Test creating a valid tailoring plan."""
        plan = TailoringPlan(
            job_url="https://example.com/job/123",
            company="Acme Corp",
            role_title="Senior Developer",
            keyword_matches=[
                KeywordMatch(
                    job_keyword="Python", user_skill="Python 3.x", confidence=0.95
                )
            ],
            evidence_mappings=[
                EvidenceMapping(
                    requirement="5+ years experience",
                    evidence="8 years at Acme",
                    source_company="Acme",
                    source_role="Developer",
                    relevance_score=0.9,
                )
            ],
            section_order=["summary", "experience", "skills", "education"],
            bullet_rewrites=[],
            unsupported_claims=[],
        )
        assert plan.company == "Acme Corp"
        assert len(plan.keyword_matches) == 1
        assert plan.section_order[0] == "summary"

    def test_tailoring_plan_with_unsupported_claims(self):
        """Test plan with unsupported claims."""
        plan = TailoringPlan(
            job_url="https://example.com/job/123",
            company="Tech Co",
            role_title="DevOps Engineer",
            keyword_matches=[],
            evidence_mappings=[],
            section_order=["experience", "skills"],
            bullet_rewrites=[],
            unsupported_claims=[
                UnsupportedClaim(
                    requirement="AWS certification",
                    reason="No AWS cert in profile",
                    severity="warning",
                )
            ],
        )
        assert len(plan.unsupported_claims) == 1
        assert plan.unsupported_claims[0].severity == "warning"

    def test_tailoring_plan_requires_company(self):
        """Test that company is required."""
        with pytest.raises(ValidationError):
            TailoringPlan(
                job_url="https://example.com",
                role_title="Developer",
                keyword_matches=[],
                evidence_mappings=[],
                section_order=[],
                bullet_rewrites=[],
                unsupported_claims=[],
            )

    def test_tailoring_plan_to_dict(self):
        """Test serialization to dict."""
        plan = TailoringPlan(
            job_url="https://example.com/job/123",
            company="Test Co",
            role_title="Engineer",
            keyword_matches=[],
            evidence_mappings=[],
            section_order=["experience"],
            bullet_rewrites=[],
            unsupported_claims=[],
        )
        data = plan.to_dict()
        assert isinstance(data, dict)
        assert data["company"] == "Test Co"


class TestTailoredSection:
    """Tests for TailoredSection model."""

    def test_valid_tailored_section(self):
        """Test creating a tailored section."""
        section = TailoredSection(
            name="experience",
            title="Professional Experience",
            content="Tailored work history content",
            bullets=[
                TailoredBullet(
                    text="Led development of Python microservices",
                    keywords_used=["Python", "microservices"],
                )
            ],
        )
        assert section.name == "experience"
        assert len(section.bullets) == 1


class TestTailoredBullet:
    """Tests for TailoredBullet model."""

    def test_valid_tailored_bullet(self):
        """Test creating a tailored bullet."""
        bullet = TailoredBullet(
            text="Developed scalable APIs using FastAPI",
            keywords_used=["FastAPI", "APIs", "scalable"],
        )
        assert "FastAPI" in bullet.keywords_used

    def test_empty_keywords(self):
        """Test bullet with no special keywords."""
        bullet = TailoredBullet(
            text="Managed team of 5 engineers",
            keywords_used=[],
        )
        assert bullet.keywords_used == []


class TestTailoredResume:
    """Tests for TailoredResume model."""

    def test_valid_tailored_resume(self):
        """Test creating a complete tailored resume."""
        resume = TailoredResume(
            name="John Doe",
            email="john@example.com",
            phone="555-123-4567",
            location="San Francisco, CA",
            linkedin_url="https://linkedin.com/in/johndoe",
            summary="Experienced Python developer with 8+ years building scalable systems",
            sections=[
                TailoredSection(
                    name="experience",
                    title="Experience",
                    content="",
                    bullets=[
                        TailoredBullet(
                            text="Led Python development team",
                            keywords_used=["Python"],
                        )
                    ],
                )
            ],
            keywords_used=["Python", "FastAPI", "PostgreSQL"],
            target_job_url="https://example.com/job/123",
            target_company="Acme Corp",
            target_role="Senior Developer",
        )
        assert resume.name == "John Doe"
        assert "Python" in resume.keywords_used
        assert len(resume.sections) == 1

    def test_tailored_resume_requires_name(self):
        """Test that name is required."""
        with pytest.raises(ValidationError):
            TailoredResume(
                email="test@example.com",
                summary="Summary",
                sections=[],
                keywords_used=[],
                target_job_url="https://example.com",
                target_company="Co",
                target_role="Role",
            )

    def test_tailored_resume_to_dict(self):
        """Test serialization."""
        resume = TailoredResume(
            name="Jane Doe",
            email="jane@example.com",
            phone=None,
            location="NYC",
            linkedin_url=None,
            summary="Summary text",
            sections=[],
            keywords_used=["Python"],
            target_job_url="https://example.com/job",
            target_company="Test Co",
            target_role="Engineer",
        )
        data = resume.to_dict()
        assert data["name"] == "Jane Doe"
        assert data["phone"] is None


class TestCoverLetter:
    """Tests for CoverLetter model."""

    def test_valid_cover_letter(self):
        """Test creating a valid cover letter."""
        cover = CoverLetter(
            opening="Dear Hiring Manager,\n\nI am excited to apply for the Senior Developer position at Acme Corp.",
            body="With 8 years of Python experience, I have consistently delivered high-quality solutions. At my previous role, I led a team that reduced deployment time by 50%.",
            closing="I look forward to discussing how my experience can benefit your team.\n\nBest regards,\nJohn Doe",
            full_text="Dear Hiring Manager,\n\nI am excited to apply...",
            word_count=350,
            target_job_url="https://example.com/job/123",
            target_company="Acme Corp",
            target_role="Senior Developer",
            key_qualifications=[
                "8 years Python",
                "Team leadership",
                "50% deployment improvement",
            ],
        )
        assert cover.word_count == 350
        assert cover.target_company == "Acme Corp"
        assert len(cover.key_qualifications) == 3

    def test_cover_letter_word_count_validation(self):
        """Test word count must be positive."""
        with pytest.raises(ValidationError):
            CoverLetter(
                opening="Opening",
                body="Body",
                closing="Closing",
                full_text="Full",
                word_count=-10,
                target_job_url="https://example.com",
                target_company="Co",
                target_role="Role",
                key_qualifications=[],
            )

    def test_cover_letter_to_dict(self):
        """Test serialization."""
        cover = CoverLetter(
            opening="Dear...",
            body="Body content",
            closing="Best,",
            full_text="Dear... Body content Best,",
            word_count=100,
            target_job_url="https://example.com",
            target_company="Test Co",
            target_role="Developer",
            key_qualifications=["Skill 1"],
        )
        data = cover.to_dict()
        assert isinstance(data, dict)
        assert data["word_count"] == 100


class TestDocReviewPacket:
    """Tests for DocReviewPacket model."""

    def test_valid_review_packet(self):
        """Test creating a valid doc review packet."""
        packet = DocReviewPacket(
            job_url="https://example.com/job/123",
            company="Acme Corp",
            role_title="Senior Developer",
            changes_summary=[
                "Reordered sections to emphasize Python experience",
                "Added 5 job-specific keywords",
                "Rewrote 3 bullet points",
            ],
            keywords_highlighted=["Python", "FastAPI", "microservices"],
            requirements_vs_evidence=[
                {
                    "requirement": "5+ years Python",
                    "evidence": "8 years at Acme Corp",
                    "matched": True,
                },
                {
                    "requirement": "AWS certification",
                    "evidence": None,
                    "matched": False,
                },
            ],
            resume_path="/artifacts/acme_senior_dev_2026-01-16_resume.pdf",
            cover_letter_path="/artifacts/acme_senior_dev_2026-01-16_cover.pdf",
            generated_at=datetime.now(),
        )
        assert packet.company == "Acme Corp"
        assert len(packet.changes_summary) == 3
        assert len(packet.requirements_vs_evidence) == 2
        assert packet.resume_path.endswith(".pdf")

    def test_review_packet_optional_cover_letter(self):
        """Test that cover letter path is optional."""
        packet = DocReviewPacket(
            job_url="https://example.com",
            company="Test",
            role_title="Role",
            changes_summary=[],
            keywords_highlighted=[],
            requirements_vs_evidence=[],
            resume_path="/path/resume.pdf",
            cover_letter_path=None,
            generated_at=datetime.now(),
        )
        assert packet.cover_letter_path is None

    def test_review_packet_to_dict(self):
        """Test serialization."""
        now = datetime.now()
        packet = DocReviewPacket(
            job_url="https://example.com",
            company="Co",
            role_title="Role",
            changes_summary=["Change 1"],
            keywords_highlighted=["Key1"],
            requirements_vs_evidence=[],
            resume_path="/path/resume.pdf",
            cover_letter_path="/path/cover.pdf",
            generated_at=now,
        )
        data = packet.to_dict()
        assert data["company"] == "Co"
        assert "generated_at" in data

    def test_review_packet_from_dict(self):
        """Test deserialization."""
        now = datetime.now()
        data = {
            "job_url": "https://example.com",
            "company": "Test Co",
            "role_title": "Engineer",
            "changes_summary": ["Rewritten summary"],
            "keywords_highlighted": ["Python"],
            "requirements_vs_evidence": [],
            "resume_path": "/resume.pdf",
            "cover_letter_path": None,
            "generated_at": now.isoformat(),
        }
        packet = DocReviewPacket.from_dict(data)
        assert packet.company == "Test Co"
        assert packet.keywords_highlighted == ["Python"]
