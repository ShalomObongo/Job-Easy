# Python Styleguide — Job-Easy

> Python-specific coding standards for the project

---

## Code Formatting

### Formatter: Ruff
- Use `ruff format` for consistent formatting
- Line length: 88 characters (Black default)
- Configure in `pyproject.toml`

```toml
[tool.ruff]
line-length = 88
target-version = "py312"

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

---

## Imports

### Organization (in order)
1. Standard library imports
2. Third-party imports
3. Local application imports

### Style
- One import per line for clarity
- Use absolute imports
- Avoid wildcard imports (`from x import *`)

```python
# Good
import os
from pathlib import Path

from browser_use import Agent, Browser

from src.config import Settings
from src.tracker import ApplicationTracker
```

---

## Type Hints

### When to Use
- Function signatures (parameters and return types)
- Class attributes
- Complex data structures

### Style
- Use modern syntax (Python 3.10+)
- Use `|` for unions: `str | None`
- Use lowercase generics: `list[str]`, `dict[str, int]`

```python
def extract_job_data(url: str, timeout: int = 30) -> dict[str, str] | None:
    """Extract job data from the given URL."""
    ...
```

### Optional Type Checking
- Run `mypy` for static analysis (optional)
- Prioritize type hints in public interfaces

---

## Async/Await Patterns

### Browser Use Integration
- Use `async`/`await` for all browser operations
- Properly await coroutines
- Use `asyncio.gather()` for parallel operations

```python
async def process_job(url: str) -> ApplicationResult:
    async with Browser() as browser:
        page = await browser.new_page()
        await page.navigate(url)
        data = await extract_job_data(page)
        return data
```

### Error Handling in Async
- Use try/except within async functions
- Properly close resources with context managers
- Consider timeouts for browser operations

---

## Classes and Data Structures

### Dataclasses for Data Objects
```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class TrackerRecord:
    fingerprint: str
    canonical_url: str
    company: str
    role_title: str
    status: str
    first_seen_at: datetime
```

### Pydantic for Validation
```python
from pydantic import BaseModel

class JobDescription(BaseModel):
    company: str
    role_title: str
    location: str
    requirements_must: list[str]
    requirements_nice: list[str] = []
```

---

## Error Handling

### Custom Exceptions
```python
class JobEasyError(Exception):
    """Base exception for Job-Easy."""
    pass

class ExtractionError(JobEasyError):
    """Failed to extract job data."""
    pass

class DuplicateApplicationError(JobEasyError):
    """Application already exists in tracker."""
    pass
```

### Handling Patterns
```python
try:
    result = await extract_job(url)
except ExtractionError as e:
    logger.error(f"Extraction failed for {url}: {e}")
    raise
except Exception as e:
    logger.exception(f"Unexpected error: {e}")
    raise
```

---

## Logging

### Configuration
```python
import logging

logger = logging.getLogger(__name__)
```

### Usage
```python
logger.info(f"Processing job: {job_url}")
logger.debug(f"Extracted data: {data}")
logger.warning(f"Duplicate detected: {fingerprint}")
logger.error(f"Failed to submit: {error}")
```

### Levels
- DEBUG: Detailed diagnostic information
- INFO: Key workflow events
- WARNING: Unexpected but handled situations
- ERROR: Failures that need attention

---

## Configuration

### Environment Variables
```python
import os
from pathlib import Path

TRACKER_DB_PATH = Path(os.getenv("TRACKER_DB_PATH", "./data/tracker.db"))
AUTO_SUBMIT = os.getenv("AUTO_SUBMIT", "false").lower() == "true"
```

### Settings Class
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    mode: str = "single"
    auto_submit: bool = False
    max_applications_per_day: int = 10
    tracker_db_path: Path = Path("./data/tracker.db")

    class Config:
        env_file = ".env"
```

---

## Testing

### pytest Fixtures
```python
import pytest

@pytest.fixture
def mock_tracker(tmp_path):
    db_path = tmp_path / "test_tracker.db"
    return ApplicationTracker(db_path)
```

### Async Tests
```python
import pytest

@pytest.mark.asyncio
async def test_job_extraction():
    result = await extract_job("https://example.com/job/123")
    assert result.company == "ExampleCo"
```

### Assertions
```python
# Good - specific assertions
assert result.status == "submitted"
assert "React" in result.requirements_must

# Avoid - vague assertions
assert result  # What are we checking?
```

---

## Project Structure

```
/src
    __init__.py
    /config
        __init__.py
        settings.py
    /tracker
        __init__.py
        models.py
        repository.py
        fingerprint.py
    /extractor
        __init__.py
        schema.py
        parser.py
    /tailoring
        __init__.py
        planner.py
        generator.py
    /runner
        __init__.py
        agent.py
        adapters/
    /hitl
        __init__.py
        prompts.py
    /utils
        __init__.py
        logging.py
/tests
    conftest.py
    /unit
    /integration
```
