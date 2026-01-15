"""Unit tests for the FitScoringService."""

from __future__ import annotations


class TestScoreSkills:
    """Test skill scoring logic."""

    def test_score_skills_must_have_100_percent_match_returns_one(self):
        """100% required skill match should return 1.0."""
        from src.extractor.models import JobDescription
        from src.scoring.models import UserProfile
        from src.scoring.service import FitScoringService

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
            required_skills=["python", "sql"],
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["Python", "SQL"],
            years_of_experience=3,
        )

        must_score, must_matched, must_missing, *_ = FitScoringService().score_skills(
            job, profile
        )

        assert must_score == 1.0
        assert must_matched == ["python", "sql"]
        assert must_missing == []

    def test_score_skills_must_have_50_percent_match_returns_half(self):
        """50% required skill match should return 0.5."""
        from src.extractor.models import JobDescription
        from src.scoring.models import UserProfile
        from src.scoring.service import FitScoringService

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
            required_skills=["python", "sql"],
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["python"],
            years_of_experience=3,
        )

        must_score, must_matched, must_missing, *_ = FitScoringService().score_skills(
            job, profile
        )

        assert must_score == 0.5
        assert must_matched == ["python"]
        assert must_missing == ["sql"]

    def test_score_skills_must_have_0_percent_match_returns_zero(self):
        """0% required skill match should return 0.0."""
        from src.extractor.models import JobDescription
        from src.scoring.models import UserProfile
        from src.scoring.service import FitScoringService

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
            required_skills=["python"],
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["java"],
            years_of_experience=3,
        )

        must_score, must_matched, must_missing, *_ = FitScoringService().score_skills(
            job, profile
        )

        assert must_score == 0.0
        assert must_matched == []
        assert must_missing == ["python"]

    def test_score_skills_empty_required_skills_returns_one(self):
        """Empty required_skills should return 1.0."""
        from src.extractor.models import JobDescription
        from src.scoring.models import UserProfile
        from src.scoring.service import FitScoringService

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
            required_skills=[],
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["python"],
            years_of_experience=3,
        )

        must_score, must_matched, must_missing, *_ = FitScoringService().score_skills(
            job, profile
        )

        assert must_score == 1.0
        assert must_matched == []
        assert must_missing == []


class TestPreferredSkills:
    """Test preferred skill scoring logic."""

    def test_score_skills_preferred_skills_list_scoring(self):
        """Preferred skills should be scored independently."""
        from src.extractor.models import JobDescription
        from src.scoring.models import UserProfile
        from src.scoring.service import FitScoringService

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
            required_skills=[],
            preferred_skills=["docker", "aws"],
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["docker"],
            years_of_experience=3,
        )

        *_, preferred_score, preferred_matched = FitScoringService().score_skills(
            job, profile
        )

        assert preferred_score == 0.5
        assert preferred_matched == ["docker"]

    def test_score_skills_empty_preferred_skills_returns_one(self):
        """Empty preferred_skills should return 1.0."""
        from src.extractor.models import JobDescription
        from src.scoring.models import UserProfile
        from src.scoring.service import FitScoringService

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
            required_skills=[],
            preferred_skills=[],
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["python"],
            years_of_experience=3,
        )

        *_, preferred_score, preferred_matched = FitScoringService().score_skills(
            job, profile
        )

        assert preferred_score == 1.0
        assert preferred_matched == []


class TestScoreExperience:
    """Test experience scoring logic."""

    def test_score_experience_within_range_returns_one(self):
        """Profile within the experience range should score 1.0."""
        from src.extractor.models import JobDescription
        from src.scoring.models import UserProfile
        from src.scoring.service import FitScoringService

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
            experience_years_min=3,
            experience_years_max=5,
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["python"],
            years_of_experience=4,
        )

        score, reasoning = FitScoringService().score_experience(job, profile)

        assert score == 1.0
        assert isinstance(reasoning, str) and reasoning

    def test_score_experience_below_min_by_one_returns_partial(self):
        """Below min by 1 year should return partial score."""
        from src.extractor.models import JobDescription
        from src.scoring.models import UserProfile
        from src.scoring.service import FitScoringService

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
            experience_years_min=5,
            experience_years_max=7,
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["python"],
            years_of_experience=4,
        )

        score, _reasoning = FitScoringService().score_experience(job, profile)

        assert 0.0 < score < 1.0

    def test_score_experience_above_max_by_one_returns_partial(self):
        """Above max by 1 year should return partial score."""
        from src.extractor.models import JobDescription
        from src.scoring.models import UserProfile
        from src.scoring.service import FitScoringService

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
            experience_years_min=3,
            experience_years_max=5,
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["python"],
            years_of_experience=6,
        )

        score, _reasoning = FitScoringService().score_experience(job, profile)

        assert 0.0 < score < 1.0

    def test_score_experience_way_outside_range_returns_zero(self):
        """Way outside the range should return 0.0."""
        from src.extractor.models import JobDescription
        from src.scoring.models import UserProfile
        from src.scoring.service import FitScoringService

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
            experience_years_min=5,
            experience_years_max=7,
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["python"],
            years_of_experience=0,
        )

        score, _reasoning = FitScoringService().score_experience(job, profile)

        assert score == 0.0

    def test_score_experience_no_requirement_returns_one(self):
        """No experience requirement should return 1.0."""
        from src.extractor.models import JobDescription
        from src.scoring.models import UserProfile
        from src.scoring.service import FitScoringService

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["python"],
            years_of_experience=0,
        )

        score, _reasoning = FitScoringService().score_experience(job, profile)

        assert score == 1.0


class TestScoreEducation:
    """Test education scoring logic."""

    def test_score_education_meets_requirement_returns_one(self):
        """Meeting the education requirement should score 1.0."""
        from src.extractor.models import JobDescription
        from src.scoring.models import Education, UserProfile
        from src.scoring.service import FitScoringService

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
            education="Bachelor's",
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["python"],
            years_of_experience=3,
            education=[
                Education(
                    institution="University",
                    degree="Bachelor's",
                    field="Computer Science",
                    graduation_year=2020,
                )
            ],
        )

        score, reasoning = FitScoringService().score_education(job, profile)

        assert score == 1.0
        assert isinstance(reasoning, str) and reasoning

    def test_score_education_exceeds_requirement_returns_one(self):
        """Exceeding the education requirement should still score 1.0."""
        from src.extractor.models import JobDescription
        from src.scoring.models import Education, UserProfile
        from src.scoring.service import FitScoringService

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
            education="Bachelor's",
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["python"],
            years_of_experience=3,
            education=[
                Education(
                    institution="University",
                    degree="Master's",
                    field="Computer Science",
                    graduation_year=2022,
                )
            ],
        )

        score, _reasoning = FitScoringService().score_education(job, profile)

        assert score == 1.0

    def test_score_education_one_level_below_returns_partial(self):
        """One level below should return partial score."""
        from src.extractor.models import JobDescription
        from src.scoring.models import Education, UserProfile
        from src.scoring.service import FitScoringService

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
            education="Master's",
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["python"],
            years_of_experience=3,
            education=[
                Education(
                    institution="University",
                    degree="Bachelor's",
                    field="Computer Science",
                )
            ],
        )

        score, _reasoning = FitScoringService().score_education(job, profile)

        assert 0.0 < score < 1.0

    def test_score_education_way_below_returns_zero(self):
        """Way below requirement should return 0.0."""
        from src.extractor.models import JobDescription
        from src.scoring.models import Education, UserProfile
        from src.scoring.service import FitScoringService

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
            education="Master's",
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["python"],
            years_of_experience=3,
            education=[
                Education(
                    institution="School",
                    degree="High School",
                    field="General",
                )
            ],
        )

        score, _reasoning = FitScoringService().score_education(job, profile)

        assert score == 0.0

    def test_score_education_no_requirement_returns_one(self):
        """No education requirement should return 1.0."""
        from src.extractor.models import JobDescription
        from src.scoring.models import UserProfile
        from src.scoring.service import FitScoringService

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
            education=None,
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["python"],
            years_of_experience=3,
        )

        score, reasoning = FitScoringService().score_education(job, profile)

        assert score == 1.0
        assert isinstance(reasoning, str) and reasoning


class TestCalculateFitScore:
    """Test weighted fit score calculation."""

    def test_calculate_fit_score_with_perfect_scores_returns_one(self):
        """Perfect component scores should yield total_score=1.0."""
        from src.extractor.models import JobDescription
        from src.scoring.models import UserProfile
        from src.scoring.service import FitScoringService

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
            required_skills=[],
            preferred_skills=[],
            experience_years_min=None,
            experience_years_max=None,
            education=None,
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["python"],
            years_of_experience=3,
        )

        fit_score = FitScoringService().calculate_fit_score(job, profile)

        assert fit_score.total_score == 1.0

    def test_calculate_fit_score_weighted_sum_calculation(self):
        """Weighted sum should match config weights and component scores."""
        from src.extractor.models import JobDescription
        from src.scoring.config import ScoringConfig
        from src.scoring.models import Education, UserProfile
        from src.scoring.service import FitScoringService

        config = ScoringConfig(
            _env_file=None,
            weight_must_have=0.25,
            weight_preferred=0.25,
            weight_experience=0.25,
            weight_education=0.25,
            experience_tolerance_years=1,
        )

        service = FitScoringService(config=config)

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
            required_skills=["python", "sql"],  # must-have score = 0.5
            preferred_skills=["docker"],  # preferred score = 0.0
            experience_years_min=5,  # delta=1, tolerance=1 => experience score = 0.5
            experience_years_max=7,
            education="Master's",  # profile bachelor's => education score = 0.5
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["python"],
            years_of_experience=4,
            education=[
                Education(
                    institution="University",
                    degree="Bachelor's",
                    field="Computer Science",
                )
            ],
        )

        fit_score = service.calculate_fit_score(job, profile)

        assert fit_score.must_have_score == 0.5
        assert fit_score.preferred_score == 0.0
        assert fit_score.experience_score == 0.5
        assert fit_score.education_score == 0.5

        assert fit_score.total_score == 0.375

    def test_calculate_fit_score_populates_fit_score_fields(self):
        """FitScore should include matched/missing lists and reasoning strings."""
        from src.extractor.models import JobDescription
        from src.scoring.config import ScoringConfig
        from src.scoring.models import UserProfile
        from src.scoring.service import FitScoringService

        config = ScoringConfig(_env_file=None)
        service = FitScoringService(config=config)

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
            required_skills=["python"],
            preferred_skills=[],
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=[],
            years_of_experience=3,
        )

        fit_score = service.calculate_fit_score(job, profile)

        assert fit_score.must_have_matched == []
        assert fit_score.must_have_missing == ["python"]
        assert isinstance(fit_score.experience_reasoning, str)
        assert isinstance(fit_score.education_reasoning, str)


class TestConstraintLocation:
    """Test location/work_type constraint handling."""

    def test_location_constraint_remote_job_always_passes(self):
        """Remote jobs should not be blocked by location matching."""
        from src.extractor.models import JobDescription
        from src.scoring.models import UserProfile
        from src.scoring.service import FitScoringService

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
            work_type="remote",
            location="San Francisco, CA",
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="New York, NY",
            skills=["python"],
            years_of_experience=3,
            target_locations=["New York, NY"],
        )

        result = FitScoringService().check_constraints(job, profile)

        assert result.passed is True

    def test_location_constraint_onsite_matching_location_passes(self):
        """Onsite jobs with matching target location should pass."""
        from src.extractor.models import JobDescription
        from src.scoring.models import UserProfile
        from src.scoring.service import FitScoringService

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
            work_type="onsite",
            location="New York, NY",
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="New York, NY",
            skills=["python"],
            years_of_experience=3,
            target_locations=["New York, NY"],
        )

        result = FitScoringService().check_constraints(job, profile)

        assert result.passed is True

    def test_location_constraint_onsite_non_matching_location_fails_in_strict_mode(
        self,
    ):
        """Onsite jobs with non-matching location should fail in strict mode."""
        from src.extractor.models import JobDescription
        from src.scoring.config import ScoringConfig
        from src.scoring.models import UserProfile
        from src.scoring.service import FitScoringService

        service = FitScoringService(
            config=ScoringConfig(_env_file=None, location_strict=True)
        )

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
            work_type="onsite",
            location="San Francisco, CA",
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="New York, NY",
            skills=["python"],
            years_of_experience=3,
            target_locations=["New York, NY"],
        )

        result = service.check_constraints(job, profile)

        assert result.passed is False
        assert result.hard_violations

    def test_location_constraint_onsite_non_matching_location_warns_in_non_strict_mode(
        self,
    ):
        """Onsite jobs with non-matching location should warn in non-strict mode."""
        from src.extractor.models import JobDescription
        from src.scoring.config import ScoringConfig
        from src.scoring.models import UserProfile
        from src.scoring.service import FitScoringService

        service = FitScoringService(
            config=ScoringConfig(_env_file=None, location_strict=False)
        )

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
            work_type="onsite",
            location="San Francisco, CA",
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="New York, NY",
            skills=["python"],
            years_of_experience=3,
            target_locations=["New York, NY"],
        )

        result = service.check_constraints(job, profile)

        assert result.passed is True
        assert result.soft_warnings

    def test_location_constraint_hybrid_job_handling(self):
        """Hybrid jobs should be treated like onsite for location matching."""
        from src.extractor.models import JobDescription
        from src.scoring.config import ScoringConfig
        from src.scoring.models import UserProfile
        from src.scoring.service import FitScoringService

        service = FitScoringService(
            config=ScoringConfig(_env_file=None, location_strict=True)
        )

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
            work_type="hybrid",
            location="San Francisco, CA",
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="New York, NY",
            skills=["python"],
            years_of_experience=3,
            target_locations=["New York, NY"],
        )

        result = service.check_constraints(job, profile)

        assert result.passed is False

    def test_location_constraint_target_locations_none_accepts_all(self):
        """target_locations=None should accept any location."""
        from src.extractor.models import JobDescription
        from src.scoring.models import UserProfile
        from src.scoring.service import FitScoringService

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
            work_type="onsite",
            location="San Francisco, CA",
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="New York, NY",
            skills=["python"],
            years_of_experience=3,
            target_locations=None,
        )

        result = FitScoringService().check_constraints(job, profile)

        assert result.passed is True


class TestConstraintVisa:
    """Test visa sponsorship constraint handling."""

    def test_visa_constraint_profile_not_needing_sponsorship_always_passes(self):
        """If the profile does not need sponsorship, visa constraint should pass."""
        from src.extractor.models import JobDescription
        from src.scoring.models import UserProfile
        from src.scoring.service import FitScoringService

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
            description="No visa sponsorship is available for this role.",
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["python"],
            years_of_experience=3,
            visa_sponsorship_needed=False,
        )

        result = FitScoringService().check_constraints(job, profile)

        assert result.passed is True

    def test_visa_constraint_sponsoring_job_passes_for_profile_needing_sponsorship(
        self,
    ):
        """Jobs that offer sponsorship should pass for candidates needing sponsorship."""
        from src.extractor.models import JobDescription
        from src.scoring.models import UserProfile
        from src.scoring.service import FitScoringService

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
            description="Visa sponsorship available for qualified candidates.",
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["python"],
            years_of_experience=3,
            visa_sponsorship_needed=True,
        )

        result = FitScoringService().check_constraints(job, profile)

        assert result.passed is True

    def test_visa_constraint_non_sponsoring_job_fails_in_strict_mode(self):
        """Non-sponsoring jobs should fail when visa_strict=True."""
        from src.extractor.models import JobDescription
        from src.scoring.config import ScoringConfig
        from src.scoring.models import UserProfile
        from src.scoring.service import FitScoringService

        service = FitScoringService(
            config=ScoringConfig(_env_file=None, visa_strict=True)
        )

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
            description="No visa sponsorship is available for this role.",
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["python"],
            years_of_experience=3,
            visa_sponsorship_needed=True,
        )

        result = service.check_constraints(job, profile)

        assert result.passed is False
        assert result.hard_violations

    def test_visa_keyword_detection_in_job_description(self):
        """Visa sponsorship keyword detection should recognize common phrases."""
        from src.extractor.models import JobDescription
        from src.scoring.config import ScoringConfig
        from src.scoring.models import UserProfile
        from src.scoring.service import FitScoringService

        service = FitScoringService(
            config=ScoringConfig(_env_file=None, visa_strict=True)
        )

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
            description="We do not sponsor visas. Must be authorized to work in the US.",
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["python"],
            years_of_experience=3,
            visa_sponsorship_needed=True,
        )

        result = service.check_constraints(job, profile)

        assert result.passed is False


class TestConstraintExperience:
    """Test experience constraint handling."""

    def test_experience_constraint_profile_within_range_passes(self):
        """Profile within job range should pass."""
        from src.extractor.models import JobDescription
        from src.scoring.models import UserProfile
        from src.scoring.service import FitScoringService

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
            experience_years_min=3,
            experience_years_max=5,
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["python"],
            years_of_experience=4,
        )

        result = FitScoringService().check_constraints(job, profile)

        assert result.passed is True

    def test_experience_constraint_within_tolerance_passes(self):
        """Profile within tolerance should pass (with warning)."""
        from src.extractor.models import JobDescription
        from src.scoring.config import ScoringConfig
        from src.scoring.models import UserProfile
        from src.scoring.service import FitScoringService

        service = FitScoringService(
            config=ScoringConfig(_env_file=None, experience_tolerance_years=2)
        )

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
            experience_years_min=5,
            experience_years_max=7,
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["python"],
            years_of_experience=4,
        )

        result = service.check_constraints(job, profile)

        assert result.passed is True
        assert result.soft_warnings

    def test_experience_constraint_outside_tolerance_fails(self):
        """Profile outside tolerance should fail."""
        from src.extractor.models import JobDescription
        from src.scoring.config import ScoringConfig
        from src.scoring.models import UserProfile
        from src.scoring.service import FitScoringService

        service = FitScoringService(
            config=ScoringConfig(_env_file=None, experience_tolerance_years=2)
        )

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
            experience_years_min=5,
            experience_years_max=7,
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["python"],
            years_of_experience=2,
        )

        result = service.check_constraints(job, profile)

        assert result.passed is False
        assert result.hard_violations

    def test_experience_constraint_no_requirement_passes(self):
        """No experience requirement should pass."""
        from src.extractor.models import JobDescription
        from src.scoring.models import UserProfile
        from src.scoring.service import FitScoringService

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["python"],
            years_of_experience=0,
        )

        result = FitScoringService().check_constraints(job, profile)

        assert result.passed is True


class TestConstraintSalary:
    """Test salary constraint handling."""

    def test_salary_constraint_salary_above_min_passes(self):
        """JD salary above profile minimum should pass."""
        from src.extractor.models import JobDescription
        from src.scoring.config import ScoringConfig
        from src.scoring.models import UserProfile
        from src.scoring.service import FitScoringService

        service = FitScoringService(
            config=ScoringConfig(_env_file=None, salary_strict=True)
        )

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
            salary_min=120000,
            salary_max=150000,
            salary_currency="USD",
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["python"],
            years_of_experience=3,
            min_salary=100000,
        )

        result = service.check_constraints(job, profile)

        assert result.passed is True

    def test_salary_constraint_salary_below_min_fails_in_strict_mode(self):
        """JD salary below profile minimum should fail when salary_strict=True."""
        from src.extractor.models import JobDescription
        from src.scoring.config import ScoringConfig
        from src.scoring.models import UserProfile
        from src.scoring.service import FitScoringService

        service = FitScoringService(
            config=ScoringConfig(_env_file=None, salary_strict=True)
        )

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
            salary_min=100000,
            salary_max=120000,
            salary_currency="USD",
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["python"],
            years_of_experience=3,
            min_salary=150000,
        )

        result = service.check_constraints(job, profile)

        assert result.passed is False
        assert result.hard_violations

    def test_salary_constraint_no_salary_info_passes(self):
        """JD with no salary info should pass."""
        from src.extractor.models import JobDescription
        from src.scoring.models import UserProfile
        from src.scoring.service import FitScoringService

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
            salary_min=None,
            salary_max=None,
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["python"],
            years_of_experience=3,
            min_salary=100000,
        )

        result = FitScoringService().check_constraints(job, profile)

        assert result.passed is True

    def test_salary_constraint_profile_with_no_min_salary_passes(self):
        """Profile with no min_salary should pass regardless of JD salary."""
        from src.extractor.models import JobDescription
        from src.scoring.models import UserProfile
        from src.scoring.service import FitScoringService

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
            salary_min=1,
            salary_max=2,
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["python"],
            years_of_experience=3,
            min_salary=None,
        )

        result = FitScoringService().check_constraints(job, profile)

        assert result.passed is True


class TestConstraintCombined:
    """Test combined constraint checking behavior."""

    def test_check_constraints_all_passing_returns_passed_true(self):
        """All passing constraints should return passed=True."""
        from src.extractor.models import JobDescription
        from src.scoring.models import UserProfile
        from src.scoring.service import FitScoringService

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
            work_type="remote",
            description="Visa sponsorship available.",
            experience_years_min=1,
            experience_years_max=5,
            salary_min=120000,
            salary_max=150000,
            salary_currency="USD",
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["python"],
            years_of_experience=3,
            visa_sponsorship_needed=False,
            min_salary=100000,
        )

        result = FitScoringService().check_constraints(job, profile)

        assert result.passed is True
        assert result.hard_violations == []

    def test_check_constraints_one_hard_violation_returns_passed_false(self):
        """One hard violation should return passed=False."""
        from src.extractor.models import JobDescription
        from src.scoring.models import UserProfile
        from src.scoring.service import FitScoringService

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
            description="No visa sponsorship is available for this role.",
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["python"],
            years_of_experience=3,
            visa_sponsorship_needed=True,
        )

        result = FitScoringService().check_constraints(job, profile)

        assert result.passed is False
        assert result.hard_violations

    def test_check_constraints_soft_warnings_with_passed_true(self):
        """Soft warnings should not flip passed to False."""
        from src.extractor.models import JobDescription
        from src.scoring.config import ScoringConfig
        from src.scoring.models import UserProfile
        from src.scoring.service import FitScoringService

        service = FitScoringService(
            config=ScoringConfig(_env_file=None, location_strict=False)
        )

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
            work_type="onsite",
            location="San Francisco, CA",
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="New York, NY",
            skills=["python"],
            years_of_experience=3,
            target_locations=["New York, NY"],
        )

        result = service.check_constraints(job, profile)

        assert result.passed is True
        assert result.soft_warnings

    def test_check_constraints_multiple_violations_accumulated(self):
        """Multiple hard violations should be accumulated."""
        from src.extractor.models import JobDescription
        from src.scoring.config import ScoringConfig
        from src.scoring.models import UserProfile
        from src.scoring.service import FitScoringService

        service = FitScoringService(
            config=ScoringConfig(
                _env_file=None,
                location_strict=True,
                visa_strict=True,
                salary_strict=True,
                experience_tolerance_years=0,
            )
        )

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
            work_type="onsite",
            location="San Francisco, CA",
            description="No visa sponsorship is available.",
            experience_years_min=5,
            salary_max=100000,
            salary_currency="USD",
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="New York, NY",
            skills=["python"],
            years_of_experience=0,
            target_locations=["New York, NY"],
            visa_sponsorship_needed=True,
            min_salary=150000,
        )

        result = service.check_constraints(job, profile)

        assert result.passed is False
        assert len(result.hard_violations) >= 2


class TestEvaluationRecommendation:
    """Test evaluate() recommendation logic."""

    def test_recommendation_apply_when_score_meets_threshold_and_constraints_pass(
        self, monkeypatch
    ):
        """Score >= threshold and passing constraints should recommend apply."""
        from src.extractor.models import JobDescription
        from src.scoring.config import ScoringConfig
        from src.scoring.models import ConstraintResult, FitScore, UserProfile
        from src.scoring.service import FitScoringService

        service = FitScoringService(
            config=ScoringConfig(
                _env_file=None, fit_score_threshold=0.75, review_margin=0.05
            )
        )

        job = JobDescription(
            company="ExampleCo", role_title="Engineer", job_url="https://x"
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["python"],
            years_of_experience=3,
        )

        monkeypatch.setattr(
            service,
            "calculate_fit_score",
            lambda _job, _profile: FitScore(
                total_score=0.80,
                must_have_score=1.0,
                must_have_matched=[],
                must_have_missing=[],
                preferred_score=1.0,
                preferred_matched=[],
                experience_score=1.0,
                experience_reasoning="",
                education_score=1.0,
                education_reasoning="",
            ),
        )
        monkeypatch.setattr(
            service,
            "check_constraints",
            lambda _job, _profile: ConstraintResult(passed=True),
        )

        result = service.evaluate(job, profile)

        assert result.recommendation == "apply"

    def test_recommendation_skip_when_score_below_threshold(self, monkeypatch):
        """Score well below threshold should recommend skip."""
        from src.extractor.models import JobDescription
        from src.scoring.config import ScoringConfig
        from src.scoring.models import ConstraintResult, FitScore, UserProfile
        from src.scoring.service import FitScoringService

        service = FitScoringService(
            config=ScoringConfig(
                _env_file=None, fit_score_threshold=0.75, review_margin=0.05
            )
        )

        job = JobDescription(
            company="ExampleCo", role_title="Engineer", job_url="https://x"
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["python"],
            years_of_experience=3,
        )

        monkeypatch.setattr(
            service,
            "calculate_fit_score",
            lambda _job, _profile: FitScore(
                total_score=0.60,
                must_have_score=1.0,
                must_have_matched=[],
                must_have_missing=[],
                preferred_score=1.0,
                preferred_matched=[],
                experience_score=1.0,
                experience_reasoning="",
                education_score=1.0,
                education_reasoning="",
            ),
        )
        monkeypatch.setattr(
            service,
            "check_constraints",
            lambda _job, _profile: ConstraintResult(passed=True),
        )

        result = service.evaluate(job, profile)

        assert result.recommendation == "skip"


class TestEvaluateMethod:
    """Test full evaluate method behavior."""

    def test_evaluate_returns_complete_fit_result(self):
        """evaluate() should return a populated FitResult."""
        from src.extractor.models import JobDescription
        from src.scoring.config import ScoringConfig
        from src.scoring.models import UserProfile
        from src.scoring.service import FitScoringService

        service = FitScoringService(
            config=ScoringConfig(
                _env_file=None, fit_score_threshold=0.75, review_margin=0.05
            )
        )

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
            required_skills=[],
            preferred_skills=[],
            work_type="remote",
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["python"],
            years_of_experience=3,
        )

        result = service.evaluate(job, profile)

        assert result.job_url == job.job_url
        assert result.job_title == job.role_title
        assert result.company == job.company
        assert result.fit_score.total_score == 1.0
        assert result.constraints.passed is True
        assert result.recommendation == "apply"
        assert result.evaluated_at is not None

    def test_evaluate_reasoning_string_is_informative(self):
        """evaluate() should produce a non-empty reasoning string."""
        from src.extractor.models import JobDescription
        from src.scoring.config import ScoringConfig
        from src.scoring.models import UserProfile
        from src.scoring.service import FitScoringService

        service = FitScoringService(
            config=ScoringConfig(
                _env_file=None, fit_score_threshold=0.75, review_margin=0.05
            )
        )

        job = JobDescription(
            company="ExampleCo",
            role_title="Engineer",
            job_url="https://example.com/jobs/123",
            required_skills=[],
            preferred_skills=[],
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["python"],
            years_of_experience=3,
        )

        result = service.evaluate(job, profile)

        assert isinstance(result.reasoning, str) and result.reasoning
        assert "fit_score=" in result.reasoning
        assert "threshold=" in result.reasoning


class TestFormatResult:
    """Test format_result output."""

    def test_format_result_includes_score_and_recommendation(self):
        """Output should include score and recommendation."""
        from src.scoring.models import ConstraintResult, FitResult, FitScore
        from src.scoring.service import FitScoringService

        result = FitResult(
            job_url="https://example.com/jobs/123",
            job_title="Engineer",
            company="ExampleCo",
            fit_score=FitScore(
                total_score=0.5,
                must_have_score=0.5,
                must_have_matched=["python"],
                must_have_missing=["sql"],
                preferred_score=1.0,
                preferred_matched=["docker"],
                experience_score=1.0,
                experience_reasoning="",
                education_score=1.0,
                education_reasoning="",
            ),
            constraints=ConstraintResult(
                passed=True, hard_violations=[], soft_warnings=["Salary not disclosed"]
            ),
            recommendation="review",
            reasoning="Test",
        )

        output = FitScoringService().format_result(result)

        assert "score=0.50" in output
        assert "Recommendation:" in output
        assert "REVIEW" in output

    def test_format_result_includes_skill_matches_and_gaps(self):
        """Output should include must-have matched/missing skills."""
        from src.scoring.models import ConstraintResult, FitResult, FitScore
        from src.scoring.service import FitScoringService

        result = FitResult(
            job_url="https://example.com/jobs/123",
            job_title="Engineer",
            company="ExampleCo",
            fit_score=FitScore(
                total_score=0.5,
                must_have_score=0.5,
                must_have_matched=["python"],
                must_have_missing=["sql"],
                preferred_score=1.0,
                preferred_matched=[],
                experience_score=1.0,
                experience_reasoning="",
                education_score=1.0,
                education_reasoning="",
            ),
            constraints=ConstraintResult(passed=True),
            recommendation="review",
            reasoning="Test",
        )

        output = FitScoringService().format_result(result)

        assert "Must-have matched" in output
        assert "python" in output
        assert "Must-have missing" in output
        assert "sql" in output

    def test_format_result_includes_constraint_issues(self):
        """Output should include constraint issues (warnings/violations)."""
        from src.scoring.models import ConstraintResult, FitResult, FitScore
        from src.scoring.service import FitScoringService

        result = FitResult(
            job_url="https://example.com/jobs/123",
            job_title="Engineer",
            company="ExampleCo",
            fit_score=FitScore(
                total_score=0.5,
                must_have_score=0.5,
                must_have_matched=[],
                must_have_missing=[],
                preferred_score=1.0,
                preferred_matched=[],
                experience_score=1.0,
                experience_reasoning="",
                education_score=1.0,
                education_reasoning="",
            ),
            constraints=ConstraintResult(
                passed=False,
                hard_violations=["Visa required"],
                soft_warnings=["Salary not disclosed"],
            ),
            recommendation="skip",
            reasoning="Test",
        )

        output = FitScoringService().format_result(result)

        assert "Constraints: FAILED" in output
        assert "Hard violations" in output
        assert "Visa required" in output
        assert "Warnings" in output
        assert "Salary not disclosed" in output

    def test_recommendation_review_when_score_within_margin(self, monkeypatch):
        """Score within review_margin should recommend review."""
        from src.extractor.models import JobDescription
        from src.scoring.config import ScoringConfig
        from src.scoring.models import ConstraintResult, FitScore, UserProfile
        from src.scoring.service import FitScoringService

        service = FitScoringService(
            config=ScoringConfig(
                _env_file=None, fit_score_threshold=0.75, review_margin=0.05
            )
        )

        job = JobDescription(
            company="ExampleCo", role_title="Engineer", job_url="https://x"
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["python"],
            years_of_experience=3,
        )

        monkeypatch.setattr(
            service,
            "calculate_fit_score",
            lambda _job, _profile: FitScore(
                total_score=0.72,
                must_have_score=1.0,
                must_have_matched=[],
                must_have_missing=[],
                preferred_score=1.0,
                preferred_matched=[],
                experience_score=1.0,
                experience_reasoning="",
                education_score=1.0,
                education_reasoning="",
            ),
        )
        monkeypatch.setattr(
            service,
            "check_constraints",
            lambda _job, _profile: ConstraintResult(passed=True),
        )

        result = service.evaluate(job, profile)

        assert result.recommendation == "review"

    def test_recommendation_skip_when_constraints_fail(self, monkeypatch):
        """Constraint violations should force skip."""
        from src.extractor.models import JobDescription
        from src.scoring.config import ScoringConfig
        from src.scoring.models import ConstraintResult, FitScore, UserProfile
        from src.scoring.service import FitScoringService

        service = FitScoringService(
            config=ScoringConfig(
                _env_file=None, fit_score_threshold=0.75, review_margin=0.05
            )
        )

        job = JobDescription(
            company="ExampleCo", role_title="Engineer", job_url="https://x"
        )
        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["python"],
            years_of_experience=3,
        )

        monkeypatch.setattr(
            service,
            "calculate_fit_score",
            lambda _job, _profile: FitScore(
                total_score=0.90,
                must_have_score=1.0,
                must_have_matched=[],
                must_have_missing=[],
                preferred_score=1.0,
                preferred_matched=[],
                experience_score=1.0,
                experience_reasoning="",
                education_score=1.0,
                education_reasoning="",
            ),
        )
        monkeypatch.setattr(
            service,
            "check_constraints",
            lambda _job, _profile: ConstraintResult(
                passed=False, hard_violations=["Visa required"], soft_warnings=[]
            ),
        )

        result = service.evaluate(job, profile)

        assert result.recommendation == "skip"
