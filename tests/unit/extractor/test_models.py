"""Tests for extractor data models."""

import json
from datetime import datetime
from pathlib import Path

import pytest


class TestJobDescription:
    """Test JobDescription Pydantic model."""

    def test_job_description_has_required_metadata_fields(self):
        """JobDescription should have required metadata fields: company, role_title, job_url."""
        from src.extractor.models import JobDescription

        job = JobDescription(
            company="Acme Corp",
            role_title="Software Engineer",
            job_url="https://jobs.lever.co/acme/123",
        )

        assert job.company == "Acme Corp"
        assert job.role_title == "Software Engineer"
        assert job.job_url == "https://jobs.lever.co/acme/123"

    def test_job_description_has_optional_fields_with_none_defaults(self):
        """JobDescription optional fields should default to None."""
        from src.extractor.models import JobDescription

        job = JobDescription(
            company="Acme Corp",
            role_title="Software Engineer",
            job_url="https://jobs.lever.co/acme/123",
        )

        # Basic metadata optional fields
        assert job.location is None
        assert job.apply_url is None
        assert job.job_id is None

        # Job description content
        assert job.description is None
        assert job.responsibilities == []
        assert job.qualifications == []

        # Requirements breakdown
        assert job.required_skills == []
        assert job.preferred_skills == []
        assert job.experience_years_min is None
        assert job.experience_years_max is None
        assert job.education is None

        # Compensation & work type
        assert job.salary_min is None
        assert job.salary_max is None
        assert job.salary_currency is None
        assert job.work_type is None
        assert job.employment_type is None

        # Extraction metadata
        assert job.extraction_source is None

    def test_job_description_validates_work_type_literal(self):
        """JobDescription should validate work_type as Literal['remote', 'hybrid', 'onsite']."""
        from pydantic import ValidationError

        from src.extractor.models import JobDescription

        # Valid work types
        job_remote = JobDescription(
            company="Acme Corp",
            role_title="Software Engineer",
            job_url="https://example.com/job/123",
            work_type="remote",
        )
        assert job_remote.work_type == "remote"

        job_hybrid = JobDescription(
            company="Acme Corp",
            role_title="Software Engineer",
            job_url="https://example.com/job/123",
            work_type="hybrid",
        )
        assert job_hybrid.work_type == "hybrid"

        job_onsite = JobDescription(
            company="Acme Corp",
            role_title="Software Engineer",
            job_url="https://example.com/job/123",
            work_type="onsite",
        )
        assert job_onsite.work_type == "onsite"

        # Invalid work type should raise ValidationError
        with pytest.raises(ValidationError):
            JobDescription(
                company="Acme Corp",
                role_title="Software Engineer",
                job_url="https://example.com/job/123",
                work_type="invalid_type",
            )

    def test_job_description_validates_employment_type_literal(self):
        """JobDescription should validate employment_type as Literal['full-time', 'part-time', 'contract']."""
        from pydantic import ValidationError

        from src.extractor.models import JobDescription

        # Valid employment types
        job_fulltime = JobDescription(
            company="Acme Corp",
            role_title="Software Engineer",
            job_url="https://example.com/job/123",
            employment_type="full-time",
        )
        assert job_fulltime.employment_type == "full-time"

        job_parttime = JobDescription(
            company="Acme Corp",
            role_title="Software Engineer",
            job_url="https://example.com/job/123",
            employment_type="part-time",
        )
        assert job_parttime.employment_type == "part-time"

        job_contract = JobDescription(
            company="Acme Corp",
            role_title="Software Engineer",
            job_url="https://example.com/job/123",
            employment_type="contract",
        )
        assert job_contract.employment_type == "contract"

        # Invalid employment type should raise ValidationError
        with pytest.raises(ValidationError):
            JobDescription(
                company="Acme Corp",
                role_title="Software Engineer",
                job_url="https://example.com/job/123",
                employment_type="freelance",
            )

    def test_job_description_serializes_to_json(self):
        """JobDescription should serialize to JSON correctly."""
        from src.extractor.models import JobDescription

        now = datetime.now()
        job = JobDescription(
            company="Acme Corp",
            role_title="Software Engineer",
            job_url="https://jobs.lever.co/acme/123",
            location="Remote",
            description="Great opportunity to work on exciting projects.",
            responsibilities=["Write code", "Review PRs"],
            qualifications=["3+ years experience", "Python expertise"],
            required_skills=["Python", "FastAPI"],
            preferred_skills=["Kubernetes", "AWS"],
            experience_years_min=3,
            experience_years_max=7,
            work_type="remote",
            employment_type="full-time",
            salary_min=100000,
            salary_max=150000,
            salary_currency="USD",
            extracted_at=now,
            extraction_source="lever",
        )

        # Serialize to JSON
        json_str = job.model_dump_json()
        data = json.loads(json_str)

        assert data["company"] == "Acme Corp"
        assert data["role_title"] == "Software Engineer"
        assert data["job_url"] == "https://jobs.lever.co/acme/123"
        assert data["location"] == "Remote"
        assert data["responsibilities"] == ["Write code", "Review PRs"]
        assert data["required_skills"] == ["Python", "FastAPI"]
        assert data["work_type"] == "remote"
        assert data["employment_type"] == "full-time"
        assert data["salary_min"] == 100000
        assert data["salary_currency"] == "USD"

    def test_job_description_from_dict_creates_valid_instance(self):
        """JobDescription.from_dict() should create a valid instance."""
        from src.extractor.models import JobDescription

        data = {
            "company": "TechCo",
            "role_title": "Backend Developer",
            "job_url": "https://greenhouse.io/techco/backend-dev",
            "location": "San Francisco, CA",
            "description": "Join our team!",
            "responsibilities": ["Build APIs", "Optimize queries"],
            "qualifications": ["5+ years experience"],
            "required_skills": ["Go", "PostgreSQL"],
            "preferred_skills": ["Redis"],
            "experience_years_min": 5,
            "work_type": "hybrid",
            "employment_type": "full-time",
            "extracted_at": "2026-01-15T10:30:00",
            "extraction_source": "greenhouse",
        }

        job = JobDescription.from_dict(data)

        assert job.company == "TechCo"
        assert job.role_title == "Backend Developer"
        assert job.job_url == "https://greenhouse.io/techco/backend-dev"
        assert job.location == "San Francisco, CA"
        assert job.work_type == "hybrid"
        assert job.required_skills == ["Go", "PostgreSQL"]
        assert job.extraction_source == "greenhouse"

    def test_job_description_to_dict_returns_dict(self):
        """JobDescription.to_dict() should return a dictionary."""
        from src.extractor.models import JobDescription

        job = JobDescription(
            company="Acme Corp",
            role_title="Software Engineer",
            job_url="https://jobs.lever.co/acme/123",
            location="Remote",
            work_type="remote",
        )

        result = job.to_dict()

        assert isinstance(result, dict)
        assert result["company"] == "Acme Corp"
        assert result["role_title"] == "Software Engineer"
        assert result["location"] == "Remote"
        assert result["work_type"] == "remote"

    def test_job_description_save_json_creates_file(self, tmp_path: Path):
        """JobDescription.save_json() should save to a JSON file."""
        from src.extractor.models import JobDescription

        job = JobDescription(
            company="Acme Corp",
            role_title="Software Engineer",
            job_url="https://jobs.lever.co/acme/123",
            location="Remote",
            work_type="remote",
        )

        output_file = tmp_path / "jd.json"
        job.save_json(output_file)

        assert output_file.exists()

        # Read and verify content
        with open(output_file) as f:
            data = json.load(f)

        assert data["company"] == "Acme Corp"
        assert data["role_title"] == "Software Engineer"
        assert data["work_type"] == "remote"

    def test_job_description_extracted_at_defaults_to_now(self):
        """JobDescription.extracted_at should default to current time if not provided."""
        from src.extractor.models import JobDescription

        before = datetime.now()
        job = JobDescription(
            company="Acme Corp",
            role_title="Software Engineer",
            job_url="https://example.com/job/123",
        )
        after = datetime.now()

        assert job.extracted_at is not None
        assert before <= job.extracted_at <= after

    def test_job_description_validates_salary_range(self):
        """JobDescription should allow valid salary ranges."""
        from src.extractor.models import JobDescription

        job = JobDescription(
            company="Acme Corp",
            role_title="Software Engineer",
            job_url="https://example.com/job/123",
            salary_min=100000,
            salary_max=150000,
            salary_currency="USD",
        )

        assert job.salary_min == 100000
        assert job.salary_max == 150000
        assert job.salary_currency == "USD"

    def test_job_description_validates_experience_years(self):
        """JobDescription should allow valid experience year ranges."""
        from src.extractor.models import JobDescription

        job = JobDescription(
            company="Acme Corp",
            role_title="Software Engineer",
            job_url="https://example.com/job/123",
            experience_years_min=3,
            experience_years_max=7,
        )

        assert job.experience_years_min == 3
        assert job.experience_years_max == 7
