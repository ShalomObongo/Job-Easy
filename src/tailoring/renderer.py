"""PDF Renderer using WeasyPrint.

Renders tailored resumes and cover letters to PDF using HTML/CSS templates.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from src.tailoring.config import TailoringConfig, get_tailoring_config
from src.tailoring.models import CoverLetter, TailoredResume

logger = logging.getLogger(__name__)


@dataclass
class RenderResult:
    """Result of a PDF rendering operation."""

    success: bool
    file_path: str | None = None
    error: str | None = None
    rendered_at: datetime = field(default_factory=datetime.now)


class PDFRenderer:
    """PDF renderer for tailored documents.

    Uses Jinja2 templates and WeasyPrint to generate
    professional PDF documents from tailored content.
    """

    def __init__(self, config: TailoringConfig | None = None):
        """Initialize the PDF renderer.

        Args:
            config: Optional TailoringConfig. Uses global config if not provided.
        """
        self.config = config or get_tailoring_config()
        self._setup_jinja()

    def _setup_jinja(self) -> None:
        """Set up Jinja2 template environment."""
        template_dir = self.config.template_dir
        if not template_dir.exists():
            # Use default templates from package
            template_dir = Path(__file__).parent / "templates"

        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=True,
        )

    def _load_styles(self) -> str:
        """Load CSS styles from template directory."""
        styles_path = self.config.get_styles_path()
        if not styles_path.exists():
            # Try package templates
            styles_path = Path(__file__).parent / "templates" / "styles.css"

        if styles_path.exists():
            return styles_path.read_text()
        return ""

    def _prepare_resume_sections(
        self, sections: list[Any]
    ) -> list[dict[str, Any]]:
        """Prepare resume sections for rendering.

        Adds derived fields that help templates render list-like content
        (e.g., skills) and structured entries (e.g., experience) with better
        hierarchy than a long, comma-heavy bullet list.
        """

        dash = r"[—–-]"

        def clean_line(text: str) -> str:
            return re.sub(r"^[\s•\-\*]+", "", text).strip()

        def split_semicolons(text: str) -> list[str]:
            parts = [clean_line(p) for p in text.split(";") if clean_line(p)]
            if 2 <= len(parts) <= 6 and all(len(p) >= 25 for p in parts):
                return parts
            return [clean_line(text)]

        def split_on_delimiters(text: str) -> list[str]:
            parts = [clean_line(p) for p in re.split(r"[;\n]+", text) if clean_line(p)]
            return parts

        def normalize_section(section: Any) -> dict[str, Any]:
            if hasattr(section, "model_dump"):
                section_dict = section.model_dump(mode="python")
            else:
                section_dict = dict(section)

            section_dict.setdefault("name", "")
            section_dict.setdefault("title", "")
            section_dict.setdefault("content", "")
            section_dict.setdefault("bullets", [])
            return section_dict

        def is_summary_section(section_dict: dict[str, Any]) -> bool:
            name_lower = str(section_dict.get("name") or "").lower()
            title_lower = str(section_dict.get("title") or "").lower()
            return "summary" in name_lower or "summary" in title_lower

        def is_experience_section(section_dict: dict[str, Any]) -> bool:
            name_lower = str(section_dict.get("name") or "").lower()
            title_lower = str(section_dict.get("title") or "").lower()
            return "experience" in name_lower or "experience" in title_lower

        def is_skills_section(section_dict: dict[str, Any]) -> bool:
            name_lower = str(section_dict.get("name") or "").lower()
            title_lower = str(section_dict.get("title") or "").lower()
            return "skill" in name_lower or "skill" in title_lower

        def is_projects_section(section_dict: dict[str, Any]) -> bool:
            name_lower = str(section_dict.get("name") or "").lower()
            title_lower = str(section_dict.get("title") or "").lower()
            return "project" in name_lower or "project" in title_lower

        def parse_items_from_commas(text: str) -> list[str]:
            items = [clean_line(item) for item in text.split(",")]
            return [item for item in items if item]

        def parse_experience_bullet(text: str) -> dict[str, str | None] | None:
            text = clean_line(text)

            patterns = [
                rf"^(?P<role>[^,\n]+),\s*(?P<company>[^()]+?)(?:\s*\((?P<dates>[^)]+)\))?\s*(?:{dash}|:)\s*(?P<body>.+)$",
                rf"^(?P<role>[^()\n]+?)\s*{dash}\s*(?P<company>[^()]+?)(?:\s*\((?P<dates>[^)]+)\))?\s*(?:{dash}|:)\s*(?P<body>.+)$",
            ]

            for pattern in patterns:
                match = re.match(pattern, text)
                if not match:
                    continue

                role = clean_line(match.group("role"))
                company = clean_line(match.group("company"))
                dates = match.groupdict().get("dates")
                if dates:
                    dates = clean_line(dates).replace(" - ", " – ")

                body = clean_line(match.group("body"))

                if not role or not company or not body:
                    return None

                return {"role": role, "company": company, "dates": dates, "body": body}

            return None

        def parse_project_bullet(text: str) -> dict[str, str | None] | None:
            text = clean_line(text)

            pattern = rf"^(?P<project>[^()\n]+?)(?:\s*\((?P<context>[^)]+)\))?\s*(?:{dash}|:)\s*(?P<body>.+)$"
            match = re.match(pattern, text)
            if not match:
                return None

            project = clean_line(match.group("project"))
            context = match.groupdict().get("context")
            if context:
                context = clean_line(context)
            body = clean_line(match.group("body"))

            if not project or not body:
                return None

            return {"project": project, "context": context, "body": body}

        raw_sections = [normalize_section(s) for s in sections]
        raw_sections = [s for s in raw_sections if not is_summary_section(s)]

        # Merge multiple experience sections into a single Experience block so job
        # titles don’t appear as top-level section headings.
        combined: list[dict[str, Any]] = []
        experience_sections: list[dict[str, Any]] = []
        experience_placeholder_index: int | None = None
        for section_dict in raw_sections:
            if is_experience_section(section_dict):
                if experience_placeholder_index is None:
                    experience_placeholder_index = len(combined)
                    combined.append({"__placeholder": "experience"})
                experience_sections.append(section_dict)
                continue
            combined.append(section_dict)

        if experience_sections and experience_placeholder_index is not None:
            merged_title = next(
                (
                    str(s.get("title") or "")
                    for s in experience_sections
                    if "experience" in str(s.get("title") or "").lower()
                ),
                "Experience",
            )
            merged_bullets: list[Any] = []
            for section_dict in experience_sections:
                merged_bullets.extend(section_dict.get("bullets") or [])

            combined[experience_placeholder_index] = {
                "name": "experience",
                "title": merged_title,
                "content": "",
                "bullets": merged_bullets,
            }

        # Force a consistent resume flow: Experience before Projects.
        experience_index = next(
            (
                i
                for i, s in enumerate(combined)
                if not s.get("__placeholder") and is_experience_section(s)
            ),
            None,
        )
        projects_index = next(
            (
                i
                for i, s in enumerate(combined)
                if not s.get("__placeholder") and is_projects_section(s)
            ),
            None,
        )
        if (
            experience_index is not None
            and projects_index is not None
            and experience_index > projects_index
        ):
            experience_section = combined.pop(experience_index)
            combined.insert(projects_index, experience_section)

        prepared: list[dict[str, Any]] = []
        for section_dict in combined:
            if section_dict.get("__placeholder") == "experience":
                continue

            content = str(section_dict.get("content") or "").strip()
            name_lower = str(section_dict.get("name") or "").strip().lower()
            title_lower = str(section_dict.get("title") or "").strip().lower()

            section_dict["is_experience"] = "experience" in name_lower or "experience" in title_lower
            section_dict["is_projects"] = "project" in name_lower or "project" in title_lower
            section_dict["is_skills"] = "skill" in name_lower or "skill" in title_lower

            content_lines: list[str] = []
            content_items: list[str] = []

            if content:
                # Prefer preserving intentional line/category breaks.
                if "\n" in content or ";" in content:
                    content_lines = split_on_delimiters(content)

                # Skills are commonly returned as comma-separated tokens; render as a list.
                if not content_lines and section_dict["is_skills"]:
                    items = parse_items_from_commas(content)
                    if len(items) >= 2:
                        content_items = items

                # Generic fallback for list-like comma strings (avoid breaking sentences).
                if not content_lines and not content_items:
                    comma_count = content.count(",")
                    period_count = content.count(".")
                    items = parse_items_from_commas(content)
                    if len(items) >= 4 and period_count <= 1 and comma_count >= 3:
                        content_items = items

            # Derive skill groups for better readability than long comma strings.
            skill_groups: list[dict[str, Any]] = []
            if section_dict["is_skills"]:
                lines = content_lines or ([content] if content else [])
                for line in lines:
                    if ":" in line:
                        label, rest = line.split(":", 1)
                        items = parse_items_from_commas(rest)
                        if items:
                            skill_groups.append(
                                {"label": clean_line(label), "items": items}
                            )
                    else:
                        items = parse_items_from_commas(line)
                        if items:
                            skill_groups.append({"label": "Skills", "items": items})

                if skill_groups:
                    content_lines = []
                    content_items = []

            # Derive structured entries for experience/projects.
            entries: list[dict[str, Any]] = []
            bullets = section_dict.get("bullets") or []
            if (section_dict["is_experience"] or section_dict["is_projects"]) and bullets:
                grouped: dict[tuple[str | None, str | None], dict[str, Any]] = {}
                order: list[tuple[str | None, str | None]] = []

                for bullet in bullets:
                    bullet_text = ""
                    if isinstance(bullet, dict):
                        bullet_text = str(bullet.get("text") or "")
                    else:
                        bullet_text = str(getattr(bullet, "text", bullet) or "")

                    parsed: dict[str, str | None] | None
                    if section_dict["is_experience"]:
                        parsed = parse_experience_bullet(bullet_text)
                        if parsed:
                            key = (parsed["role"], parsed["company"])
                            entry = grouped.get(key)
                            if entry is None:
                                entry = {
                                    "heading": parsed["role"],
                                    "subheading": parsed["company"],
                                    "dates": parsed["dates"],
                                    "bullets": [],
                                }
                                grouped[key] = entry
                                order.append(key)

                            if parsed["dates"] and not entry.get("dates"):
                                entry["dates"] = parsed["dates"]

                            entry["bullets"].extend(split_semicolons(parsed["body"] or ""))
                            continue
                    else:
                        parsed = parse_project_bullet(bullet_text)
                        if parsed:
                            key = (parsed["project"], parsed.get("context"))
                            entry = grouped.get(key)
                            if entry is None:
                                entry = {
                                    "heading": parsed["project"],
                                    "subheading": parsed.get("context"),
                                    "dates": None,
                                    "bullets": [],
                                }
                                grouped[key] = entry
                                order.append(key)
                            entry["bullets"].extend(split_semicolons(parsed["body"] or ""))
                            continue

                    # Unparsed bullets fall back into a headerless entry.
                    key = (None, None)
                    entry = grouped.get(key)
                    if entry is None:
                        entry = {"heading": None, "subheading": None, "dates": None, "bullets": []}
                        grouped[key] = entry
                        order.append(key)
                    entry["bullets"].append(clean_line(bullet_text))

                # Keep headerless entry last.
                if (None, None) in order and order[-1] != (None, None):
                    order = [k for k in order if k != (None, None)] + [(None, None)]

                entries = [grouped[k] for k in order if grouped.get(k)]
                if entries:
                    section_dict["bullets"] = []

            section_dict["content_lines"] = content_lines
            section_dict["content_items"] = content_items
            section_dict["skill_groups"] = skill_groups
            section_dict["entries"] = entries
            prepared.append(section_dict)

        return prepared

    def _generate_filename(
        self,
        company: str,
        role: str,
        doc_type: str,
    ) -> str:
        """Generate a deterministic filename.

        Args:
            company: Company name.
            role: Job role/title.
            doc_type: Document type ('resume' or 'cover').

        Returns:
            Sanitized filename following convention.
        """

        # Sanitize company and role
        def sanitize(s: str) -> str:
            # Remove special characters, replace spaces with underscores
            s = re.sub(r"[^\w\s-]", "", s)
            s = re.sub(r"\s+", "_", s)
            return s.lower()[:30]

        company_clean = sanitize(company)
        role_clean = sanitize(role)
        date_str = datetime.now().strftime("%Y-%m-%d")

        return f"{company_clean}_{role_clean}_{date_str}_{doc_type}.pdf"

    def _ensure_output_dir(self) -> Path:
        """Ensure output directory exists."""
        output_dir = self.config.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def _render_resume_html(self, resume: TailoredResume) -> str:
        """Render resume to HTML.

        Args:
            resume: Tailored resume content.

        Returns:
            Rendered HTML string.
        """
        template = self.jinja_env.get_template(self.config.resume_template)
        styles = self._load_styles()

        return template.render(
            name=resume.name,
            email=resume.email,
            phone=resume.phone,
            location=resume.location,
            linkedin_url=resume.linkedin_url,
            summary=resume.summary,
            sections=self._prepare_resume_sections(resume.sections),
            keywords_used=resume.keywords_used,
            styles=styles,
        )

    def _render_cover_letter_html(self, cover: CoverLetter) -> str:
        """Render cover letter to HTML.

        Args:
            cover: Cover letter content.

        Returns:
            Rendered HTML string.
        """
        template = self.jinja_env.get_template(self.config.cover_letter_template)
        styles = self._load_styles()

        # Split body into paragraphs
        body_paragraphs = [p.strip() for p in cover.body.split("\n\n") if p.strip()]

        return template.render(
            opening=cover.opening,
            body_paragraphs=body_paragraphs,
            closing=cover.closing,
            target_company=cover.target_company,
            target_role=cover.target_role,
            date=datetime.now().strftime("%B %d, %Y"),
            styles=styles,
        )

    def render_resume(self, resume: TailoredResume) -> RenderResult:
        """Render a tailored resume to PDF.

        Args:
            resume: Tailored resume content.

        Returns:
            RenderResult with file path or error.
        """
        try:
            # Generate HTML
            html_content = self._render_resume_html(resume)

            # Generate filename and path
            filename = self._generate_filename(
                resume.target_company,
                resume.target_role,
                "resume",
            )
            output_dir = self._ensure_output_dir()
            output_path = output_dir / filename

            # Render to PDF
            HTML(string=html_content).write_pdf(str(output_path))

            logger.info(f"Rendered resume to {output_path}")

            return RenderResult(
                success=True,
                file_path=str(output_path),
            )

        except Exception as e:
            logger.error(f"Failed to render resume: {e}")
            return RenderResult(
                success=False,
                error=str(e),
            )

    def render_cover_letter(self, cover: CoverLetter) -> RenderResult:
        """Render a cover letter to PDF.

        Args:
            cover: Cover letter content.

        Returns:
            RenderResult with file path or error.
        """
        try:
            # Generate HTML
            html_content = self._render_cover_letter_html(cover)

            # Generate filename and path
            filename = self._generate_filename(
                cover.target_company,
                cover.target_role,
                "cover",
            )
            output_dir = self._ensure_output_dir()
            output_path = output_dir / filename

            # Render to PDF
            HTML(string=html_content).write_pdf(str(output_path))

            logger.info(f"Rendered cover letter to {output_path}")

            return RenderResult(
                success=True,
                file_path=str(output_path),
            )

        except Exception as e:
            logger.error(f"Failed to render cover letter: {e}")
            return RenderResult(
                success=False,
                error=str(e),
            )

    def render_both(
        self,
        resume: TailoredResume,
        cover: CoverLetter,
    ) -> tuple[RenderResult, RenderResult]:
        """Render both resume and cover letter.

        Args:
            resume: Tailored resume content.
            cover: Cover letter content.

        Returns:
            Tuple of (resume_result, cover_result).
        """
        resume_result = self.render_resume(resume)
        cover_result = self.render_cover_letter(cover)
        return resume_result, cover_result
