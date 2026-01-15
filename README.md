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

## Development

See `conductor/workflow.md` for development methodology and conventions.

## License

MIT
