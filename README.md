# Job-Easy

**AI-powered job application automation with human oversight**

---

## What is Job-Easy?

Job-Easy is an intelligent job application system that combines browser automation with AI to streamline your job search. It extracts job details, evaluates your fit, tailors your documents, and assists with applications — all while keeping you in control of every submission.

---

## Key Features

### Intelligent Job Extraction
Automatically pulls structured data from job postings across major platforms including Greenhouse, Lever, Workday, LinkedIn, Indeed, and Glassdoor. Captures role requirements, qualifications, salary information, and company details.

### Smart Fit Scoring
Evaluates how well each opportunity matches your profile using a weighted algorithm that considers skills alignment, experience level, education requirements, and role relevance. Provides clear recommendations: apply, review, or skip.

### Document Tailoring
Generates customized resumes and cover letters for each application. Uses AI to naturally integrate relevant keywords while maintaining truthfulness — never fabricates experience or skills you don't have.

### Human-in-the-Loop Safety
Every critical decision requires your explicit approval. You review tailored documents before they're used, confirm each submission, and can override any automated recommendation. No application is ever submitted without your consent.

### Duplicate Prevention
Tracks all your applications in a local database. Automatically detects when you've already applied to a position (or a similar one at the same company) and prevents accidental resubmissions.

### Batch Processing
Process multiple job opportunities from a leads file. The system deduplicates against your history, ranks by fit score, and processes each sequentially with full HITL gates.

---

## Requirements

- Python 3.11 or higher
- Chrome browser for browser automation
- LLM API access from OpenAI, Anthropic, or a compatible provider

---

## Installation

### Step 1: Clone and Create Environment

```bash
# Clone the repository
git clone https://github.com/ShalomObongo/job-easy.git
cd job-easy

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install with development dependencies
pip install -e ".[dev]"
```

### Step 2: Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit with your settings
nano .env  # or use your preferred editor
```

**Required Settings:**

| Setting | Description |
|---------|-------------|
| **EXTRACTOR_LLM_PROVIDER** | Your LLM provider: openai, anthropic, or auto |
| **OPENAI_API_KEY** or **ANTHROPIC_API_KEY** | API credentials for your chosen provider |
| **SCORING_PROFILE_PATH** | Path to your candidate profile (default: profiles/profile.yaml) |

**Optional but Recommended:**

| Setting | Description |
|---------|-------------|
| **USE_EXISTING_CHROME_PROFILE** | Set to true to reuse your browser sessions |
| **CHROME_USER_DATA_DIR** | Path to your Chrome user data directory |
| **CHROME_PROFILE_DIR** | Name of the Chrome profile to use (e.g., Default, Profile 1) |
| **MAX_APPLICATIONS_PER_DAY** | Daily limit for autonomous mode (default: 10) |
| **PROHIBITED_DOMAINS** | Comma-separated list of domains to never apply to |

### Step 3: Create Your Profile

```bash
# Copy the example profile
cp profiles/profile.example.yaml profiles/profile.yaml

# Edit with your information
nano profiles/profile.yaml
```

**Profile Sections:**

| Section | Contents |
|---------|----------|
| **Basic Info** | Name, email, phone, location, LinkedIn URL |
| **Skills & Experience** | Your technical skills, years of experience, current title, professional summary |
| **Work History** | Previous positions with company, title, dates, description, and skills used |
| **Education** | Degrees with institution, field, and graduation year |
| **Certifications** | Professional certifications with issuer and dates |
| **Preferences** | Work type (remote/hybrid/onsite), target locations, visa requirements, salary expectations |

The scoring system uses this profile to evaluate job fit and the tailoring module uses it to generate customized documents.

### Step 4: Verify Installation

```bash
# Check that everything is set up correctly
python -m src tracker stats
```

If the database doesn't exist, it will be created automatically.

---

## Usage

### Single Job Mode

Process one job URL through the complete pipeline:

```bash
# Full pipeline with application
python -m src single https://jobs.lever.co/company/position-id

# Generate documents without applying (dry run)
python -m src single https://jobs.lever.co/company/position-id --dry-run
```

The system will:

1. Check for duplicates in your application history
2. Extract job details from the posting
3. Score the opportunity against your profile
4. Generate a tailored resume and cover letter
5. Present documents for your approval
6. Assist with form filling (with your confirmation before submission)

### Autonomous Mode

Process multiple jobs from a leads file:

```bash
# Process all jobs in the leads file
python -m src autonomous leads.txt

# Dry run with minimum score filter
python -m src autonomous leads.txt --dry-run --min-score 0.8

# Skip confirmation prompt and limit to 5 jobs
python -m src autonomous leads.txt --yes --limit 5
```

**Leads File Format:**

```text
# One URL per line (lines starting with # are comments)
https://jobs.lever.co/company/position-1
https://boards.greenhouse.io/company/jobs/123456
https://company.wd5.myworkdayjobs.com/careers/job/location/title_JR001234
```

**Autonomous Mode Options:**

| Option | Effect |
|--------|--------|
| **--dry-run** | Generate documents without applying |
| **--min-score** | Skip jobs below this fit score (0.0 to 1.0) |
| **--include-skips** | Include jobs even if scoring recommends skip |
| **--yes** | Skip the initial batch confirmation prompt |
| **--limit** | Maximum number of jobs to process |

### Component Commands

Run individual pipeline stages for debugging, reruns, or custom workflows:

```bash
# Extract job data only
python -m src extract https://jobs.lever.co/company/position-id

# Score a previously extracted job
python -m src score --jd artifacts/runs/<run_id>/jd.json --profile profiles/profile.yaml

# Generate tailored documents
python -m src tailor --jd artifacts/runs/<run_id>/jd.json --profile profiles/profile.yaml

# Run application with existing documents
python -m src apply https://jobs.lever.co/company/apply --resume resume.pdf --cover-letter cover.pdf

# Preview a ranked batch without processing
python -m src queue leads.txt --profile profiles/profile.yaml --min-score 0.7
```

### Tracker Commands

Query and manage your application history:

```bash
# View application statistics
python -m src tracker stats

# List recent applications
python -m src tracker recent

# Look up a specific application
python -m src tracker lookup https://jobs.lever.co/company/position-id

# Manually update status
python -m src tracker mark https://jobs.lever.co/company/position-id --status interviewed
```

---

## Workflow Overview

### Complete Pipeline Flow

```
Job URL → Duplicate Check → Extraction → Scoring → Tailoring → Review → Application
```

**Duplicate Check** — Queries your tracker database to prevent reapplying to the same position

**Extraction** — Opens the job posting in a browser, uses AI to extract structured data including requirements, qualifications, salary, and company information

**Scoring** — Compares job requirements against your profile to calculate a fit score and recommendation

**Tailoring** — Generates a customized resume highlighting relevant experience and a cover letter addressing the specific role

**Review** — Presents the generated documents for your approval before proceeding

**Application** — Opens the application form, assists with filling fields, and waits for your explicit confirmation before submitting

### Safety Gates

Every run includes multiple checkpoints where you maintain control:

1. **Duplicate Override** — If a potential duplicate is detected, you decide whether to proceed
2. **Fit Review** — For borderline scores, you decide whether the opportunity is worth pursuing
3. **Document Approval** — You review and approve all generated documents
4. **Submit Confirmation** — Final submission requires you to type YES

---

## Configuration Reference

### LLM Settings

Job-Easy supports multiple LLM providers with a fallback chain:

| Provider | Models | Notes |
|----------|--------|-------|
| **OpenAI** | gpt-4o, gpt-4o-mini | Recommended for best results |
| **Anthropic** | claude-sonnet-4-20250514 | Alternative with strong performance |
| **Custom** | Any OpenAI-compatible API | Set BASE_URL for local models or Azure |

Each module can use different LLM settings. The tailoring and runner modules fall back to extractor settings if not explicitly configured.

### Scoring Weights

The fit score is calculated from four weighted components:

| Component | Default Weight | Evaluates |
|-----------|----------------|-----------|
| **Must-Have Skills** | 40% | Required skills match |
| **Preferred Skills** | 20% | Nice-to-have skills match |
| **Experience** | 25% | Years of experience alignment |
| **Education** | 15% | Degree level match |

Adjust weights in your .env file if you want to prioritize different factors.

### Score Thresholds

| Threshold | Default | Meaning |
|-----------|---------|---------|
| **Apply** | ≥ 0.75 | Automatically recommended |
| **Review** | 0.70 - 0.74 | Borderline, your decision |
| **Skip** | < 0.70 | Not recommended |

---

## System Architecture

Job-Easy is built from nine specialized modules:

| Module | Responsibility |
|--------|----------------|
| **config** | Centralized settings and environment configuration |
| **extractor** | Browser-based job data extraction using AI |
| **scoring** | Fit evaluation with skills matching and constraint checking |
| **tailoring** | Resume and cover letter generation with PDF rendering |
| **runner** | Browser automation for form filling and submission |
| **tracker** | Application history with duplicate detection |
| **autonomous** | Batch processing orchestration |
| **hitl** | Human-in-the-loop prompts and safety gates |
| **utils** | Shared logging and helper utilities |

---

## Artifacts

Each run generates artifacts in a timestamped directory under **artifacts/runs/**:

| File | Stage | Contents |
|------|-------|----------|
| **jd.json** | Extract | Structured job description data |
| **fit_result.json** | Score | Fit score breakdown and recommendation |
| **review_packet.json** | Tailor | Document review summary |
| **resume.pdf** | Tailor | Tailored resume |
| **cover_letter.pdf** | Tailor | Generated cover letter |
| **conversation.jsonl** | Apply | Browser agent interaction log |
| **application_result.json** | Apply | Final submission status and details |

---

## Documentation

Comprehensive documentation is available in the **docs/** directory:

### Module Documentation
- **autonomous.md** — Batch processing and queue management
- **config.md** — Configuration options and environment variables
- **extractor.md** — Job data extraction and browser setup
- **hitl.md** — Human-in-the-loop workflow and safety gates
- **runner.md** — Application execution and form automation
- **scoring.md** — Fit evaluation algorithms and scoring criteria
- **tailoring.md** — Document generation and PDF rendering
- **tracker.md** — Application history and duplicate detection
- **utils.md** — Logging system and shared utilities

### Project Documentation
- **project-brief.md** — Product vision and architecture overview
- **workflow-diagram.md** — System flow visualizations
- **dev.md** — Development setup and guidelines

---

## Troubleshooting

### Common Issues

**Browser won't start or crashes immediately**
- Ensure Chrome is installed and accessible
- If using an existing profile, close all Chrome windows first
- Try setting CHROME_PROFILE_MODE to "copy" for safer profile handling

**LLM requests failing**
- Verify your API key is set correctly in .env
- Check that your provider account has available credits
- For local models, ensure the server is running and accessible

**Documents not generating**
- Confirm your profile.yaml is valid YAML syntax
- Check that all required profile fields are populated
- Review the tailoring logs for specific error messages

**Duplicate detection not working**
- The tracker database may not exist yet; run any command to create it
- Check TRACKER_DB_PATH points to a writable location

---

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test module
pytest tests/unit/scoring/

# Run integration tests
pytest tests/integration/
```

---

## Safety Reminders

- **Never** set AUTO_SUBMIT to true unless you fully understand the implications
- **Always** review generated documents before approving
- **Keep** your profile.yaml accurate and up-to-date
- **Use** dry-run mode when testing new configurations
- **Monitor** the allowlist.log to see which domains are being accessed

---

## License

MIT

---

*Built with Browser Use and AI-powered document generation*
