# Job-Easy

Browser Use-powered job application automation system.

## Overview

Job-Easy helps you apply to jobs efficiently by:
- Extracting job descriptions and metadata
- Tailoring resumes and generating cover letters
- Completing applications with human oversight
- Preventing duplicate applications

## Documentation

See the `docs/` directory for detailed documentation:
- [Project Brief](docs/project-brief.md) - Product vision and architecture
- [Research](docs/research.md) - Browser Use integration details
- [Workflow](docs/workflow-diagram.md) - System flow diagrams

## Quick Start

```bash
# Install dependencies
pip install -e ".[dev]"

# Run in single-job mode
python -m src single https://example.com/job/123

# Run tests
pytest
```

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
