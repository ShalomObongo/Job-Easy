# Technology Stack — Job-Easy

> Technical specifications and architecture for the Job-Easy system

---

## Programming Languages

### Primary: Python 3.12
- Latest stable version for modern features
- Required for Browser Use compatibility
- Type hints encouraged (PEP 484)
- Async/await patterns for browser automation

---

## Core Dependencies

### Browser Automation
- **Browser Use**: Primary automation framework
  - Agent-based browser control
  - Built-in extraction tools
  - Human-in-the-loop support
  - Chrome profile integration
  - Docs: https://docs.browser-use.com

### Database & Storage
- **SQLite**: Application tracker and fingerprint store
  - Single file database for simplicity
  - No external server required
  - ACID compliant for data integrity

### Document Generation
- **PDF output**: Primary format for resumes and cover letters
- Libraries to consider:
  - `reportlab` - Direct PDF generation
  - `weasyprint` - HTML/CSS to PDF
  - `pypdf` - PDF manipulation

### LLM Integration
- Browser Use built-in LLM for page extraction
- Custom LLM calls for resume tailoring and cover letter generation
- Support for multiple providers (OpenAI, Anthropic, etc.)

---

## Architecture

### Pattern: Modular Monolith
```
/src
  /config         # Configuration loading and validation
  /tracker        # Fingerprinting, storage, and queries
  /extractor      # JD extraction and schemas
  /tailoring      # Tailoring plan + resume/CL generation
  /runner         # Browser automation runner + site adapters
  /hitl           # Human-in-the-loop tools/prompts
  /autonomous     # Queue + scheduler (autonomous mode)
  /utils          # Shared helpers
/tests
  /unit
  /integration
/artifacts
  /runs           # Per-application artifacts
  /docs           # Generated documents
```

### Design Principles
- Single responsibility per module
- Clear interfaces between components
- Configuration-driven behavior
- Comprehensive logging throughout

---

## Development Tools

### Package Management
- **uv** or **pip**: Package installation
- `pyproject.toml`: Project configuration and dependencies

### Testing
- **pytest**: Test framework
- **pytest-asyncio**: Async test support
- **pytest-cov**: Coverage reporting

### Code Quality
- **ruff**: Fast Python linter and formatter
- **mypy**: Static type checking (optional)
- **pre-commit**: Git hooks for quality checks

### Development
- **VSCode** or **Cursor**: Recommended IDE
- **Python extension**: Language support
- Debugger configured for async code

---

## Browser Configuration

### Chrome Profile Integration
- Support for existing Chrome profiles
- Configurable `user_data_dir` and `profile_directory`
- Safety guidance: copy profile before automation

### Domain Controls
- `allowed_domains`: Restrict navigation to job sites
- `prohibited_domains`: Block unwanted sites

### Session Management
- Configurable headless/headed mode
- DevTools access for debugging
- Screenshot capture for proof

---

## External Services

### Required
- LLM API (OpenAI, Anthropic, or compatible)
  - Job description analysis
  - Resume tailoring
  - Cover letter generation

### Optional
- Email notifications (SMTP)
- Cloud storage for artifacts (S3, GCS)

---

## Configuration

### Environment Variables
```
MODE=single|autonomous
AUTO_SUBMIT=false
MAX_APPLICATIONS_PER_DAY=10
TRACKER_DB_PATH=./data/tracker.db
OUTPUT_DIR=./artifacts
LLM_API_KEY=<your-api-key>
USE_EXISTING_CHROME_PROFILE=true
CHROME_USER_DATA_DIR=<path>
CHROME_PROFILE_DIR=Default
```

### Configuration Files
- `config.yaml`: Application settings
- `.env`: Sensitive credentials (gitignored)
- `profiles/`: User resume and profile data

---

## Security Considerations

- Never store API keys in code
- Limit file access via `available_file_paths`
- Use `sensitive_data` dict for PII
- Enable domain allowlisting by default
- All submissions require human confirmation
