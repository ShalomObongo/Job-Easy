"""Unit tests for the PDF Renderer.

Tests for HTML template rendering, PDF generation, file naming,
and output path handling.
"""

import tempfile
from pathlib import Path

import pytest

from src.tailoring.config import TailoringConfig, reset_tailoring_config
from src.tailoring.models import (
    CoverLetter,
    TailoredBullet,
    TailoredResume,
    TailoredSection,
)
from src.tailoring.renderer import PDFRenderer, RenderResult


@pytest.fixture
def sample_tailored_resume():
    """Create a sample tailored resume for testing."""
    return TailoredResume(
        name="John Doe",
        email="john@example.com",
        phone="555-123-4567",
        location="San Francisco, CA",
        linkedin_url="https://linkedin.com/in/johndoe",
        github_url="https://github.com/johndoe",
        summary="Senior Python developer with 8 years of experience building scalable microservices.",
        sections=[
            TailoredSection(
                name="experience",
                title="Professional Experience",
                content="",
                bullets=[
                    TailoredBullet(
                        text="Led development of FastAPI microservices handling 10K+ requests/sec",
                        keywords_used=["FastAPI", "microservices"],
                    ),
                    TailoredBullet(
                        text="Optimized PostgreSQL queries reducing response time by 40%",
                        keywords_used=["PostgreSQL"],
                    ),
                ],
            ),
            TailoredSection(
                name="skills",
                title="Technical Skills",
                content="Python, FastAPI, Django, PostgreSQL, Docker, AWS, Redis",
                bullets=[],
            ),
            TailoredSection(
                name="education",
                title="Education",
                content="Bachelor's in Computer Science from MIT (2016)",
                bullets=[],
            ),
        ],
        keywords_used=["Python", "FastAPI", "PostgreSQL", "Docker"],
        target_job_url="https://acme.com/jobs/123",
        target_company="Acme Corp",
        target_role="Senior Python Developer",
    )


@pytest.fixture
def sample_cover_letter():
    """Create a sample cover letter for testing."""
    return CoverLetter(
        opening="Dear Hiring Manager,\n\nI am excited to apply for the Senior Python Developer position at Acme Corp.",
        body="With 8 years of Python experience, I have consistently delivered high-quality solutions. At Tech Corp, I led a team that built microservices handling over 10,000 requests per second.",
        closing="I look forward to discussing how my experience can contribute to Acme Corp's continued success.\n\nBest regards,\nJohn Doe",
        full_text="Dear Hiring Manager,\n\nI am excited to apply...",
        word_count=350,
        target_job_url="https://acme.com/jobs/123",
        target_company="Acme Corp",
        target_role="Senior Python Developer",
        key_qualifications=["8 years Python", "10K+ requests/sec", "Team leadership"],
    )


class TestPDFRendererConfiguration:
    """Tests for PDFRenderer configuration."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    def test_uses_default_config(self):
        """Test that renderer uses default config when not provided."""
        renderer = PDFRenderer()
        assert renderer.config is not None
        assert renderer.config.template_dir is not None

    def test_uses_custom_config(self):
        """Test that renderer uses provided config."""
        config = TailoringConfig(output_dir=Path("/custom/output"))
        renderer = PDFRenderer(config=config)
        assert renderer.config.output_dir == Path("/custom/output")


class TestFileNaming:
    """Tests for file naming convention."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    def test_generates_resume_filename(self, sample_tailored_resume):
        """Test resume filename follows convention."""
        renderer = PDFRenderer()
        filename = renderer._generate_filename(
            sample_tailored_resume.target_company,
            sample_tailored_resume.target_role,
            "resume",
        )

        # Should follow pattern: {company}_{role}_{date}_resume.pdf
        assert filename.endswith("_resume.pdf")
        assert "acme" in filename.lower() or "corp" in filename.lower()

    def test_generates_cover_letter_filename(self, sample_cover_letter):
        """Test cover letter filename follows convention."""
        renderer = PDFRenderer()
        filename = renderer._generate_filename(
            sample_cover_letter.target_company,
            sample_cover_letter.target_role,
            "cover",
        )

        assert filename.endswith("_cover.pdf")

    def test_sanitizes_filename(self):
        """Test that special characters are sanitized from filename."""
        renderer = PDFRenderer()
        filename = renderer._generate_filename(
            "Acme/Corp Inc.",
            "Senior Dev (Remote)",
            "resume",
        )

        # Should not contain special characters
        assert "/" not in filename
        assert "(" not in filename
        assert ")" not in filename


class TestHTMLRendering:
    """Tests for HTML template rendering."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    def test_renders_resume_html(_, sample_tailored_resume):
        """Test that resume is rendered to HTML."""
        renderer = PDFRenderer()
        html = renderer._render_resume_html(sample_tailored_resume)

        # HTML should contain key content
        assert "John Doe" in html
        assert "Senior Python developer" in html
        assert "FastAPI" in html
        assert "github.com/johndoe" in html

    def test_renders_cover_letter_html(_, sample_cover_letter):
        """Test that cover letter is rendered to HTML."""
        renderer = PDFRenderer()
        html = renderer._render_cover_letter_html(sample_cover_letter)

        # HTML should contain key content
        assert "Dear Hiring Manager" in html
        assert "Acme Corp" in html


class TestPDFGeneration:
    """Tests for PDF generation."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    def test_render_resume_returns_result(self, sample_tailored_resume):
        """Test that render_resume returns a RenderResult."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = TailoringConfig(output_dir=Path(tmpdir))
            renderer = PDFRenderer(config=config)

            result = renderer.render_resume(sample_tailored_resume)

            assert isinstance(result, RenderResult)
            assert result.success
            assert result.file_path is not None
            assert Path(result.file_path).exists()
            assert result.file_path.endswith(".pdf")

    def test_render_cover_letter_returns_result(self, sample_cover_letter):
        """Test that render_cover_letter returns a RenderResult."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = TailoringConfig(output_dir=Path(tmpdir))
            renderer = PDFRenderer(config=config)

            result = renderer.render_cover_letter(sample_cover_letter)

            assert isinstance(result, RenderResult)
            assert result.success
            assert result.file_path is not None
            assert Path(result.file_path).exists()

    def test_creates_output_directory(self, sample_tailored_resume):
        """Test that output directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "nested" / "output"
            config = TailoringConfig(output_dir=output_dir)
            renderer = PDFRenderer(config=config)

            result = renderer.render_resume(sample_tailored_resume)

            assert result.success
            assert output_dir.exists()


class TestOutputPaths:
    """Tests for output path handling."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    def test_saves_to_configured_output_dir(self, sample_tailored_resume):
        """Test that PDFs are saved to configured output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "artifacts"
            config = TailoringConfig(output_dir=output_dir)
            renderer = PDFRenderer(config=config)

            result = renderer.render_resume(sample_tailored_resume)

            assert result.success
            assert str(output_dir) in result.file_path

    def test_render_result_includes_metadata(self, sample_tailored_resume):
        """Test that RenderResult includes useful metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = TailoringConfig(output_dir=Path(tmpdir))
            renderer = PDFRenderer(config=config)

            result = renderer.render_resume(sample_tailored_resume)

            assert result.success
            assert result.file_path is not None
            assert result.rendered_at is not None


class TestRenderBoth:
    """Tests for rendering both resume and cover letter."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    def test_render_both_documents(self, sample_tailored_resume, sample_cover_letter):
        """Test rendering both resume and cover letter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = TailoringConfig(output_dir=Path(tmpdir))
            renderer = PDFRenderer(config=config)

            resume_result = renderer.render_resume(sample_tailored_resume)
            cover_result = renderer.render_cover_letter(sample_cover_letter)

            assert resume_result.success
            assert cover_result.success
            assert resume_result.file_path != cover_result.file_path

            # Both files should exist
            assert Path(resume_result.file_path).exists()
            assert Path(cover_result.file_path).exists()
