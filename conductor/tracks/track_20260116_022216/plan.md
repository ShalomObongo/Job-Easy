# Implementation Plan: Tailoring & Document Generation

> Track: E3 - Resume tailoring, cover letter generation, and PDF rendering

---

## Phase 1: Foundation & Data Models

### [x] Task 1.1: Write Tests - Tailoring Models
- Create `tests/unit/tailoring/test_models.py`
- Test TailoringPlan model validation
- Test TailoredResume model validation
- Test CoverLetter model validation
- Test DocReviewPacket model validation
- Tests should fail initially (Red)

### [x] Task 1.2: Implement - Tailoring Models
- Create `src/tailoring/models.py`
- Implement TailoringPlan Pydantic model
- Implement TailoredResume Pydantic model
- Implement CoverLetter Pydantic model
- Implement DocReviewPacket Pydantic model
- Run tests (Green)

### [x] Task 1.3: Write Tests - Tailoring Configuration
- Create tests for TailoringConfig in `tests/unit/tailoring/test_config.py`
- Test LLM provider settings
- Test model selection
- Test template paths
- Test output directory settings

### [x] Task 1.4: Implement - Tailoring Configuration
- Create `src/tailoring/config.py`
- Implement TailoringConfig with pydantic-settings
- Support environment variable overrides
- Configure LLM provider, model, and paths

### [x] Task 1.5: Conductor - User Manual Verification 'Phase 1: Foundation' (Protocol in workflow.md)

---

## Phase 2: LLM Integration Layer

### [x] Task 2.1: Write Tests - LLM Client
- Create `tests/unit/tailoring/test_llm.py`
- Test client initialization with different providers
- Test structured output parsing
- Test error handling and retries
- Mock LLM responses for unit tests

### [x] Task 2.2: Implement - LLM Client
- Create `src/tailoring/llm.py`
- Implement TailoringLLM class using LiteLLM
- Support structured output via Pydantic schemas
- Implement retry logic with exponential backoff
- Handle provider-specific quirks

### [x] Task 2.3: Conductor - User Manual Verification 'Phase 2: LLM Integration' (Protocol in workflow.md)

---

## Phase 3: Tailoring Plan Generator

### [x] Task 3.1: Write Tests - Keyword Extraction
- Create `tests/unit/tailoring/test_plan.py`
- Test keyword extraction from JobDescription
- Test skill matching against UserProfile
- Test evidence mapping generation
- Test unsupported claims detection

### [x] Task 3.2: Implement - Tailoring Plan Service
- Create `src/tailoring/plan.py`
- Implement TailoringPlanService class
- Generate keyword map from JD requirements
- Map user evidence to job requirements
- Detect and flag unsupported claims
- Generate section reordering recommendations

### [x] Task 3.3: Integration Test - Plan Generation
- Create `tests/integration/tailoring/test_plan_integration.py`
- Test full plan generation with real profile and JD
- Validate output structure and content quality

### [x] Task 3.4: Conductor - User Manual Verification 'Phase 3: Plan Generator' (Protocol in workflow.md)

---

## Phase 4: Resume Tailoring Engine

### [x] Task 4.1: Write Tests - Resume Tailoring
- Create `tests/unit/tailoring/test_resume.py`
- Test bullet rewriting logic
- Test section reordering
- Test keyword integration
- Test truthfulness enforcement (no fabrication)

### [x] Task 4.2: Implement - Resume Tailoring Service
- Create `src/tailoring/resume.py`
- Implement ResumeTailoringService class
- Full content rewriting based on tailoring plan
- Section reordering by relevance
- Keyword integration into descriptions
- Enforce truthfulness (only rephrase, never fabricate)

### [x] Task 4.3: Conductor - User Manual Verification 'Phase 4: Resume Tailoring' (Protocol in workflow.md)

---

## Phase 5: Cover Letter Generator

### [x] Task 5.1: Write Tests - Cover Letter Generation
- Create `tests/unit/tailoring/test_cover_letter.py`
- Test cover letter structure (opening, body, closing)
- Test word count (300-400 words)
- Test evidence integration
- Test company/role personalization

### [x] Task 5.2: Implement - Cover Letter Service
- Create `src/tailoring/cover_letter.py`
- Implement CoverLetterService class
- Generate structured cover letter content
- Map accomplishments to job requirements
- Enforce 300-400 word target length

### [x] Task 5.3: Conductor - User Manual Verification 'Phase 5: Cover Letter' (Protocol in workflow.md)

---

## Phase 6: PDF Rendering

### [x] Task 6.1: Write Tests - PDF Renderer
- Create `tests/unit/tailoring/test_renderer.py`
- Test HTML template rendering
- Test PDF generation
- Test file naming convention
- Test output path handling

### [x] Task 6.2: Create HTML/CSS Templates
- Create `src/tailoring/templates/resume.html`
- Create `src/tailoring/templates/cover_letter.html`
- Create `src/tailoring/templates/styles.css`
- Professional, clean design
- Print-optimized styling

### [x] Task 6.3: Implement - PDF Renderer
- Create `src/tailoring/renderer.py`
- Implement PDFRenderer class using WeasyPrint
- Render resume template with tailored content
- Render cover letter template
- Implement deterministic file naming

### [x] Task 6.4: Conductor - User Manual Verification 'Phase 6: PDF Rendering' (Protocol in workflow.md)

---

## Phase 7: Doc Review Packet

### [x] Task 7.1: Write Tests - Review Packet
- Create `tests/unit/tailoring/test_review.py`
- Test review summary generation
- Test keyword highlighting
- Test evidence mapping display
- Test file path collection

### [x] Task 7.2: Implement - Review Packet Service
- Create `src/tailoring/review.py`
- Implement ReviewPacketService class
- Generate summary of changes made
- List highlighted keywords/skills
- Create requirements vs evidence mapping
- Collect generated file paths

### [x] Task 7.3: Conductor - User Manual Verification 'Phase 7: Review Packet' (Protocol in workflow.md)

---

## Phase 8: Service Integration & API

### [x] Task 8.1: Write Tests - Main Service
- Create `tests/unit/tailoring/test_service.py`
- Test full tailoring pipeline
- Test service initialization
- Test error handling
- Test output artifacts

### [x] Task 8.2: Implement - TailoringService
- Create `src/tailoring/service.py`
- Implement main TailoringService class
- Orchestrate plan → resume → cover letter → render → review
- Handle errors and partial failures
- Return complete tailoring result

### [x] Task 8.3: Update Module Exports
- Update `src/tailoring/__init__.py`
- Export public API (TailoringService, models, config)

### [x] Task 8.4: Integration Test - Full Pipeline
- Create `tests/integration/tailoring/test_pipeline.py`
- Test complete tailoring workflow
- Validate PDF output
- Validate review packet

### [x] Task 8.5: Conductor - User Manual Verification 'Phase 8: Integration' (Protocol in workflow.md)

---

## Dependencies

### Python Packages
- `litellm` - Multi-provider LLM access
- `weasyprint` - HTML/CSS to PDF conversion
- `jinja2` - Template rendering

### Existing Modules
- `src/scoring/models.py` - UserProfile model
- `src/extractor/models.py` - JobDescription model

### Test Fixtures
- Sample user profiles (YAML)
- Sample job descriptions (JSON)
- Expected output artifacts for validation
