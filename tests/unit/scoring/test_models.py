"""Tests for scoring data models."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest


class TestWorkExperience:
    """Test WorkExperience model."""

    def test_work_experience_valid_creation(self):
        """WorkExperience should validate required fields."""
        from src.scoring.models import WorkExperience

        experience = WorkExperience(
            company="ExampleCo",
            title="Software Engineer",
            start_date=date(2022, 1, 1),
            end_date=date(2023, 1, 1),
            description="Built features.",
            skills_used=["python", "sql"],
        )

        assert experience.company == "ExampleCo"
        assert experience.title == "Software Engineer"
        assert experience.start_date == date(2022, 1, 1)
        assert experience.end_date == date(2023, 1, 1)
        assert experience.skills_used == ["python", "sql"]

    def test_work_experience_optional_fields(self):
        """WorkExperience should allow optional end_date and skills_used."""
        from src.scoring.models import WorkExperience

        experience = WorkExperience(
            company="ExampleCo",
            title="Software Engineer",
            start_date=date(2022, 1, 1),
            end_date=None,
            description="Built features.",
        )

        assert experience.end_date is None
        assert experience.skills_used == []

    def test_work_experience_to_dict_from_dict_round_trip(self):
        """WorkExperience should serialize/deserialize with to_dict/from_dict."""
        from src.scoring.models import WorkExperience

        experience = WorkExperience(
            company="ExampleCo",
            title="Software Engineer",
            start_date=date(2022, 1, 1),
            end_date=None,
            description="Built features.",
            skills_used=["python"],
        )

        data = experience.to_dict()
        restored = WorkExperience.from_dict(data)

        assert restored.company == experience.company
        assert restored.title == experience.title
        assert restored.start_date == experience.start_date
        assert restored.end_date == experience.end_date
        assert restored.skills_used == experience.skills_used


class TestEducation:
    """Test Education model."""

    def test_education_valid_creation(self):
        """Education should validate required fields."""
        from src.scoring.models import Education

        education = Education(
            institution="University",
            degree="Bachelor's",
            field="Computer Science",
            graduation_year=2020,
        )

        assert education.institution == "University"
        assert education.degree == "Bachelor's"
        assert education.field == "Computer Science"
        assert education.graduation_year == 2020

    def test_education_optional_graduation_year(self):
        """Education should allow graduation_year to be omitted."""
        from src.scoring.models import Education

        education = Education(
            institution="University",
            degree="Bachelor's",
            field="Computer Science",
        )

        assert education.graduation_year is None

    def test_education_to_dict_from_dict_round_trip(self):
        """Education should serialize/deserialize with to_dict/from_dict."""
        from src.scoring.models import Education

        education = Education(
            institution="University",
            degree="Bachelor's",
            field="Computer Science",
            graduation_year=None,
        )

        data = education.to_dict()
        restored = Education.from_dict(data)

        assert restored.institution == education.institution
        assert restored.degree == education.degree
        assert restored.field == education.field
        assert restored.graduation_year == education.graduation_year


class TestUserProfile:
    """Test UserProfile model."""

    def test_user_profile_valid_with_all_fields(self):
        """UserProfile should validate with all fields present."""
        from src.scoring.models import Education, UserProfile, WorkExperience

        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            phone="555-555-5555",
            location="New York, NY",
            linkedin_url="https://linkedin.com/in/janedoe",
            skills=["python", "sql", "aws"],
            years_of_experience=5,
            current_title="Software Engineer",
            summary="Experienced engineer.",
            work_history=[
                WorkExperience(
                    company="ExampleCo",
                    title="Engineer",
                    start_date=date(2021, 1, 1),
                    end_date=None,
                    description="Did stuff.",
                    skills_used=["python"],
                )
            ],
            education=[
                Education(
                    institution="University",
                    degree="Bachelor's",
                    field="Computer Science",
                    graduation_year=2020,
                )
            ],
            work_type_preferences=["remote", "hybrid"],
            target_locations=["New York, NY"],
            visa_sponsorship_needed=False,
            min_salary=120000,
            preferred_salary=150000,
            salary_currency="USD",
            experience_level="mid",
        )

        assert profile.name == "Jane Doe"
        assert profile.email == "jane@example.com"
        assert profile.work_history[0].company == "ExampleCo"
        assert profile.education[0].degree == "Bachelor's"

    def test_user_profile_valid_with_required_fields_only(self):
        """UserProfile should validate with only required fields."""
        from src.scoring.models import UserProfile

        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["python"],
            years_of_experience=3,
        )

        assert profile.phone is None
        assert profile.linkedin_url is None
        assert profile.current_title == ""
        assert profile.summary == ""
        assert profile.work_history == []
        assert profile.education == []
        assert profile.work_type_preferences == ["remote", "hybrid", "onsite"]
        assert profile.target_locations is None
        assert profile.visa_sponsorship_needed is False
        assert profile.min_salary is None
        assert profile.preferred_salary is None
        assert profile.salary_currency == "USD"
        assert profile.experience_level is not None

    def test_user_profile_work_type_preferences_defaults_to_all_types(self):
        """work_type_preferences should default to all work types."""
        from src.scoring.models import UserProfile

        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["python"],
            years_of_experience=3,
        )

        assert profile.work_type_preferences == ["remote", "hybrid", "onsite"]

    def test_user_profile_to_dict_from_dict_round_trip(self):
        """UserProfile should serialize/deserialize with to_dict/from_dict."""
        from src.scoring.models import UserProfile

        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["python"],
            years_of_experience=3,
        )

        data = profile.to_dict()
        restored = UserProfile.from_dict(data)

        assert restored.name == profile.name
        assert restored.email == profile.email
        assert restored.location == profile.location
        assert restored.skills == profile.skills
        assert restored.years_of_experience == profile.years_of_experience

    def test_user_profile_missing_required_fields_raises(self):
        """Missing required fields should raise validation errors."""
        from pydantic import ValidationError

        from src.scoring.models import UserProfile

        with pytest.raises(ValidationError):
            UserProfile(email="jane@example.com", location="Remote", skills=["python"])


class TestFitScore:
    """Test FitScore dataclass."""

    def test_fit_score_creation_with_all_fields(self):
        """FitScore should be creatable with all fields."""
        from src.scoring.models import FitScore

        score = FitScore(
            total_score=0.9,
            must_have_score=1.0,
            must_have_matched=["python"],
            must_have_missing=[],
            preferred_score=0.5,
            preferred_matched=["sql"],
            experience_score=0.8,
            experience_reasoning="Good match",
            education_score=0.7,
            education_reasoning="Meets requirement",
        )

        assert score.total_score == 0.9
        assert score.must_have_matched == ["python"]
        assert score.preferred_matched == ["sql"]

    def test_fit_score_validates_score_ranges(self):
        """FitScore scores should be constrained to 0.0-1.0."""
        from src.scoring.models import FitScore

        with pytest.raises(ValueError):
            FitScore(
                total_score=1.5,
                must_have_score=1.0,
                must_have_matched=["python"],
                must_have_missing=[],
                preferred_score=0.5,
                preferred_matched=["sql"],
                experience_score=0.8,
                experience_reasoning="Good match",
                education_score=0.7,
                education_reasoning="Meets requirement",
            )

    def test_fit_score_matched_and_missing_lists(self):
        """FitScore should preserve matched/missing lists."""
        from src.scoring.models import FitScore

        score = FitScore(
            total_score=0.5,
            must_have_score=0.5,
            must_have_matched=["python"],
            must_have_missing=["docker"],
            preferred_score=1.0,
            preferred_matched=["sql"],
            experience_score=0.5,
            experience_reasoning="OK",
            education_score=0.5,
            education_reasoning="OK",
        )

        assert score.must_have_missing == ["docker"]


class TestConstraintResult:
    """Test ConstraintResult dataclass."""

    def test_constraint_result_passed_true_with_empty_violations(self):
        """ConstraintResult passed=True should have no hard violations."""
        from src.scoring.models import ConstraintResult

        result = ConstraintResult(passed=True, hard_violations=[], soft_warnings=[])

        assert result.passed is True
        assert result.hard_violations == []
        assert result.soft_warnings == []

    def test_constraint_result_passed_false_with_violations(self):
        """ConstraintResult passed=False should include hard violations."""
        from src.scoring.models import ConstraintResult

        result = ConstraintResult(
            passed=False, hard_violations=["Visa required"], soft_warnings=[]
        )

        assert result.passed is False
        assert result.hard_violations == ["Visa required"]

    def test_constraint_result_soft_warnings_separate_from_hard_violations(self):
        """Soft warnings should be separate from hard violations."""
        from src.scoring.models import ConstraintResult

        result = ConstraintResult(
            passed=True,
            hard_violations=[],
            soft_warnings=["Salary not disclosed"],
        )

        assert result.passed is True
        assert result.hard_violations == []
        assert result.soft_warnings == ["Salary not disclosed"]


class TestFitResult:
    """Test FitResult dataclass."""

    def test_fit_result_creation_with_all_components(self):
        """FitResult should be creatable with all components."""
        from src.scoring.models import ConstraintResult, FitResult, FitScore

        result = FitResult(
            job_url="https://example.com/jobs/123",
            job_title="Software Engineer",
            company="ExampleCo",
            fit_score=FitScore(
                total_score=0.8,
                must_have_score=1.0,
                must_have_matched=["python"],
                must_have_missing=[],
                preferred_score=0.5,
                preferred_matched=["sql"],
                experience_score=0.8,
                experience_reasoning="Good match",
                education_score=0.7,
                education_reasoning="Meets requirement",
            ),
            constraints=ConstraintResult(passed=True),
            recommendation="apply",
            reasoning="Good fit",
        )

        assert result.job_url == "https://example.com/jobs/123"
        assert result.recommendation == "apply"

    def test_fit_result_recommendation_values(self):
        """FitResult recommendation should allow apply/skip/review."""
        from src.scoring.models import ConstraintResult, FitResult, FitScore

        score = FitScore(
            total_score=0.8,
            must_have_score=1.0,
            must_have_matched=[],
            must_have_missing=[],
            preferred_score=1.0,
            preferred_matched=[],
            experience_score=1.0,
            experience_reasoning="",
            education_score=1.0,
            education_reasoning="",
        )
        constraints = ConstraintResult(passed=True)

        assert (
            FitResult(
                job_url="https://example.com/jobs/123",
                job_title="Engineer",
                company="ExampleCo",
                fit_score=score,
                constraints=constraints,
                recommendation="apply",
                reasoning="",
            ).recommendation
            == "apply"
        )
        assert (
            FitResult(
                job_url="https://example.com/jobs/123",
                job_title="Engineer",
                company="ExampleCo",
                fit_score=score,
                constraints=constraints,
                recommendation="skip",
                reasoning="",
            ).recommendation
            == "skip"
        )
        assert (
            FitResult(
                job_url="https://example.com/jobs/123",
                job_title="Engineer",
                company="ExampleCo",
                fit_score=score,
                constraints=constraints,
                recommendation="review",
                reasoning="",
            ).recommendation
            == "review"
        )

    def test_fit_result_evaluated_at_defaults_to_timestamp(self):
        """FitResult should default evaluated_at timestamp."""
        from src.scoring.models import ConstraintResult, FitResult, FitScore

        score = FitScore(
            total_score=0.8,
            must_have_score=1.0,
            must_have_matched=[],
            must_have_missing=[],
            preferred_score=1.0,
            preferred_matched=[],
            experience_score=1.0,
            experience_reasoning="",
            education_score=1.0,
            education_reasoning="",
        )

        before = datetime.now(UTC)
        result = FitResult(
            job_url="https://example.com/jobs/123",
            job_title="Engineer",
            company="ExampleCo",
            fit_score=score,
            constraints=ConstraintResult(passed=True),
            recommendation="review",
            reasoning="",
        )
        after = datetime.now(UTC)

        assert before <= result.evaluated_at <= after
