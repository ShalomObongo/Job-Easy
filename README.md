# Job-Easy

Browser Use-powered job application automation system.

## Overview

Job-Easy helps you apply to jobs efficiently by:
- Extracting job descriptions and metadata
- Scoring fit against a user profile
- Tailoring resumes and generating cover letters
- Completing applications with human oversight
- Preventing duplicate applications

In addition to end-to-end modes (`single`, `autonomous`), the CLI exposes component commands so you can run each stage independently for debugging and reruns.

## Documentation

See the `docs/` directory for detailed documentation:
- [Project Brief](docs/project-brief.md) - Product vision and architecture
- [Research](docs/research.md) - Browser Use integration details
- [Workflow](docs/workflow-diagram.md) - System flow diagrams

## Quick Start

```bash
# Use the project venv
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Run in single-job mode
python -m src single https://example.com/job/123

# Run in autonomous (batch) mode
python -m src autonomous leads.txt --dry-run --yes

# Component flows
python -m src extract "https://example.com/job/123"
python -m src score --jd artifacts/runs/<run_id>/jd.json --profile profiles/profile.yaml
python -m src tailor --jd artifacts/runs/<run_id>/jd.json --profile profiles/profile.yaml
python -m src apply "https://example.com/apply" --resume resume.pdf
python -m src queue leads.txt --profile profiles/profile.yaml
python -m src tracker stats

# Run tests
pytest
```

## Commands

### End-to-end

- `python -m src single <job_url>`: run tracker -> extract -> score -> tailor -> apply with HITL gates
- `python -m src autonomous <leads_file>`: process a batch of URLs (supports `--dry-run`)

### Component flows

- `python -m src extract <job_url> [--out-run-dir <dir>]`
- `python -m src score --jd <jd.json> --profile <profile.yaml> [--out-run-dir <dir>]`
- `python -m src tailor --jd <jd.json> --profile <profile.yaml> [--no-cover-letter] [--out-run-dir <dir>]`
- `python -m src apply <url> --resume <file> [--cover-letter <file>] [--profile <profile.yaml>] [--out-run-dir <dir>]`
- `python -m src queue <leads_file> --profile <profile.yaml> [--min-score <0..1>] [--include-skips] [--limit <n>] [--out-run-dir <dir>]`
- `python -m src tracker stats|lookup|recent|mark ...`

## Artifacts

Most commands write artifacts under `artifacts/runs/<run_id>/` by default.

Common outputs:
- `jd.json` (extract)
- `fit_result.json` (score)
- `review_packet.json` + PDFs (tailor)
- `conversation.jsonl` + `application_result.json` (apply)
- `queue.json` (queue)

## Safety

- No final submission happens without explicit user confirmation (YES).
- CAPTCHA/2FA is not bypassed; the flow stops and asks for help.
- Duplicate submissions are prevented by default; overrides require confirmation.

## Autonomous Mode

Autonomous mode processes a batch of job URLs from a text file, deduplicates them
against the tracker, ranks by fit score, and runs the existing single-job
pipeline sequentially.

Leads file format:

```text
# one URL per line
https://example.com/jobs/123
https://example.com/jobs/456
```

Flags:
- `--dry-run`: generate documents without applying
- `--min-score 0.0-1.0`: skip jobs below the threshold
- `--include-skips`: include jobs even if fit scoring recommends skip
- `--yes`: skip the batch confirmation prompt

## Fit Scoring

1. Copy `profiles/profile.example.yaml` to `profiles/profile.yaml` and customize it.
2. Set `SCORING_PROFILE_PATH=profiles/profile.yaml` in your `.env` (see `.env.example`).

Example usage:

```python
from src.extractor.models import JobDescription
from src.scoring import FitScoringService, ProfileService

profile = ProfileService().load_profile("profiles/profile.yaml")
job = JobDescription(company="ExampleCo", role_title="Engineer", job_url="https://example.com/jobs/123")
result = FitScoringService().evaluate(job, profile)
print(FitScoringService().format_result(result))
```

## Development

See `conductor/workflow.md` for development methodology and conventions.

## License

MIT
