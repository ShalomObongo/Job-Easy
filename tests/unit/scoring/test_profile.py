"""Tests for profile loading and validation."""

from __future__ import annotations

import json

import pytest


class TestProfileLoadingYaml:
    """Test ProfileService.load_profile for YAML."""

    def test_loads_valid_complete_profile(self, tmp_path):
        """Should load a complete YAML profile."""
        from src.scoring.profile import ProfileService

        profile_path = tmp_path / "profile.yaml"
        profile_path.write_text(
            """
name: Jane Doe
email: jane@example.com
location: Remote
skills: [Python, SQL]
years_of_experience: 5
current_title: Software Engineer
summary: Test summary
work_history: []
education: []
work_type_preferences: [remote, hybrid]
target_locations: null
visa_sponsorship_needed: false
min_salary: 120000
preferred_salary: 150000
salary_currency: USD
experience_level: mid
""".lstrip(),
            encoding="utf-8",
        )

        profile = ProfileService().load_profile(profile_path)

        assert profile.name == "Jane Doe"
        assert profile.years_of_experience == 5
        assert profile.skills == ["Python", "SQL"]

    def test_loads_minimal_profile(self, tmp_path):
        """Should load a minimal YAML profile with defaults."""
        from src.scoring.profile import ProfileService

        profile_path = tmp_path / "profile.yaml"
        profile_path.write_text(
            """
name: Jane Doe
email: jane@example.com
location: Remote
skills: [Python]
years_of_experience: 3
""".lstrip(),
            encoding="utf-8",
        )

        profile = ProfileService().load_profile(profile_path)

        assert profile.name == "Jane Doe"
        assert profile.salary_currency == "USD"
        assert profile.work_type_preferences == ["remote", "hybrid", "onsite"]

    def test_raises_file_not_found_error(self, tmp_path):
        """Should raise FileNotFoundError when the profile path does not exist."""
        from src.scoring.profile import ProfileService

        missing_path = tmp_path / "missing.yaml"

        with pytest.raises(FileNotFoundError):
            ProfileService().load_profile(missing_path)

    def test_raises_value_error_on_invalid_yaml(self, tmp_path):
        """Should raise ValueError when YAML is invalid."""
        from src.scoring.profile import ProfileService

        profile_path = tmp_path / "profile.yaml"
        profile_path.write_text("name: [unclosed\n", encoding="utf-8")

        with pytest.raises(ValueError):
            ProfileService().load_profile(profile_path)

    def test_raises_validation_error_on_invalid_profile_data(self, tmp_path):
        """Should raise ValidationError when profile data fails validation."""
        from pydantic import ValidationError

        from src.scoring.profile import ProfileService

        profile_path = tmp_path / "profile.yaml"
        profile_path.write_text(
            """
email: jane@example.com
location: Remote
skills: [Python]
years_of_experience: not-a-number
""".lstrip(),
            encoding="utf-8",
        )

        with pytest.raises(ValidationError):
            ProfileService().load_profile(profile_path)


class TestProfileLoadingJson:
    """Test ProfileService.load_profile for JSON."""

    def test_loads_valid_json_profile(self, tmp_path):
        """Should load a JSON profile."""
        from src.scoring.profile import ProfileService

        profile_path = tmp_path / "profile.json"
        profile_path.write_text(
            json.dumps(
                {
                    "name": "Jane Doe",
                    "email": "jane@example.com",
                    "location": "Remote",
                    "skills": ["Python"],
                    "years_of_experience": 3,
                }
            ),
            encoding="utf-8",
        )

        profile = ProfileService().load_profile(profile_path)

        assert profile.name == "Jane Doe"


class TestProfileValidation:
    """Test ProfileService.validate_profile warnings."""

    def test_validate_profile_complete_profile_has_no_warnings(self):
        """A complete profile should return no warnings."""
        from src.scoring.models import UserProfile
        from src.scoring.profile import ProfileService

        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            phone="555-555-5555",
            location="Remote",
            linkedin_url="https://linkedin.com/in/jane",
            skills=["Python"],
            years_of_experience=3,
        )

        warnings = ProfileService().validate_profile(profile)

        assert warnings == []

    def test_validate_profile_missing_optional_fields_returns_warnings(self):
        """Missing optional fields should return warnings."""
        from src.scoring.models import UserProfile
        from src.scoring.profile import ProfileService

        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=["Python"],
            years_of_experience=3,
        )

        warnings = ProfileService().validate_profile(profile)

        assert "Missing phone number" in warnings
        assert "Missing LinkedIn URL" in warnings

    def test_validate_profile_empty_skills_list_warns(self):
        """Empty skills list should return a warning."""
        from src.scoring.models import UserProfile
        from src.scoring.profile import ProfileService

        profile = UserProfile(
            name="Jane Doe",
            email="jane@example.com",
            location="Remote",
            skills=[],
            years_of_experience=3,
        )

        warnings = ProfileService().validate_profile(profile)

        assert "Skills list is empty" in warnings

    def test_auto_detects_json_format(self, tmp_path):
        """Should auto-detect JSON format when file extension is unknown."""
        from src.scoring.profile import ProfileService

        profile_path = tmp_path / "profile.data"
        profile_path.write_text(
            json.dumps(
                {
                    "name": "Jane Doe",
                    "email": "jane@example.com",
                    "location": "Remote",
                    "skills": ["Python"],
                    "years_of_experience": 3,
                }
            ),
            encoding="utf-8",
        )

        profile = ProfileService().load_profile(profile_path)

        assert profile.name == "Jane Doe"
