# Tailoring & Document Generation Specification

> Track for Job-Easy: Resume tailoring and cover letter generation

---

## Overview

Build a tailoring system that takes a user's profile (YAML/JSON) and a job description
(from the extractor) and produces:
1. A fully tailored resume with aggressive rewriting and reordering
2. A full-length cover letter (300-400 words)
3. PDF outputs via WeasyPrint
4. A doc review packet for user confirmation before upload

The system uses a configurable LLM provider (OpenAI, Anthropic, or others via LiteLLM)
for content generation while enforcing truthfulness—no fabricated experience.

---

## Functional Requirements

### FR-1: Tailoring Plan Generator
- Input: `UserProfile` + `JobDescription`
- Output: `TailoringPlan` containing:
  - **Keyword map**: Job requirements → matching user skills/experience
  - **Evidence mapping**: Each job requirement → specific user accomplishments
  - **Section reordering**: Recommended order of resume sections for this job
  - **Bullet rewrite suggestions**: Which bullets to emphasize/rewrite
  - **Unsupported claims warnings**: Flag any requirement without user evidence

### FR-2: Resume Tailoring Engine
- Fully rewrite all resume content to align with job requirements
- Reorder sections/bullets by relevance to the specific job
- Integrate job keywords naturally into descriptions
- Preserve truthfulness—only rephrase existing experience, never fabricate
- Output: Structured tailored resume data ready for rendering

### FR-3: Cover Letter Generator
- Generate 300-400 word cover letter (full page)
- Structure: Opening hook → Top 2-3 qualifications → Company/role enthusiasm → Call to action
- Map specific user accomplishments to job requirements
- Maintain authentic voice while being compelling
- Output: Structured cover letter content ready for rendering

### FR-4: PDF Renderer (WeasyPrint)
- HTML/CSS templates for professional document styling
- Render tailored resume to PDF
- Render cover letter to PDF
- Deterministic file naming: `{company}_{role}_{date}_resume.pdf`, `{company}_{role}_{date}_cover.pdf`
- Support custom templates (future extensibility)

### FR-5: Doc Review Packet
- Summary of key changes made to resume
- List of highlighted keywords/skills
- Side-by-side: job requirements vs user evidence used
- Generated file paths for user review
- Ready for HITL confirmation gate before upload

---

## Non-Functional Requirements

### NFR-1: LLM Flexibility
- Support multiple LLM providers via configuration
- Use LiteLLM for unified API access
- Configurable model selection (e.g., gpt-4, claude-3-opus)
- Structured output enforcement via Pydantic schemas

### NFR-2: Performance
- Complete tailoring pipeline in < 60 seconds per job
- Efficient prompt design to minimize token usage
- Cache templates and static assets

### NFR-3: Error Handling
- Graceful degradation if LLM fails (retry with backoff)
- Validation of all generated content against schemas
- Clear error messages for debugging

---

## Acceptance Criteria

1. **Tailoring Plan**: Given a profile and JD, produces a keyword map and evidence mapping
2. **Resume Output**: Generates a fully tailored PDF resume with all content rewritten for the job
3. **Cover Letter Output**: Generates a 300-400 word PDF cover letter aligned to job themes
4. **Truthfulness**: System flags and refuses to generate claims without supporting evidence
5. **Doc Review**: Produces a review packet summarizing changes and evidence mapping
6. **Integration**: Works with existing `UserProfile` and `JobDescription` models

---

## Out of Scope

- Multiple resume templates (v1 uses single professional template)
- DOCX output format (PDF only for v1)
- A/B testing of different tailoring strategies
- Resume parsing from existing PDF/DOCX (uses YAML profile as source)
- Cover letter tone customization (uses professional tone)

---

## Technical Notes

### Input Models
- `UserProfile` from `src/scoring/models.py`
- `JobDescription` from `src/extractor/models.py`

### Output Artifacts
- `{company}_{role}_{date}_resume.pdf` - Tailored resume
- `{company}_{role}_{date}_cover.pdf` - Cover letter
- `review_packet.json` - Structured review data for HITL gate

### Dependencies
- `litellm` - Multi-provider LLM access
- `weasyprint` - HTML/CSS to PDF conversion
- `jinja2` - Template rendering
