# Configuration Module Documentation

> Last updated: 2026-01-21
> Module: `src/config/`

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Core Components](#core-components)
  - [Settings Class](#settings-class)
  - [Mode Enum](#mode-enum)
- [Configuration Categories](#configuration-categories)
  - [Operating Mode](#operating-mode)
  - [Safety Settings](#safety-settings)
  - [Paths](#paths)
  - [Runner Settings](#runner-settings)
  - [Chrome Profile Settings](#chrome-profile-settings)
  - [API Settings](#api-settings)
  - [Logging](#logging)
- [Environment Variables](#environment-variables)
- [Module Integration](#module-integration)
- [API Reference](#api-reference)
- [Configuration Examples](#configuration-examples)
- [Testing](#testing)
- [Best Practices](#best-practices)

---

## Overview

The `config` module is the **centralized configuration management system** for Job-Easy. It provides a type-safe, validated, and environment-driven configuration layer that all other modules depend on.

### Purpose

- **Centralized Settings**: Single source of truth for application-wide configuration
- **Environment-Driven**: Load settings from environment variables or `.env` files
- **Type Safety**: Pydantic-based validation with type hints
- **Sensible Defaults**: All settings have reasonable defaults for quick setup
- **Singleton Pattern**: Global settings instance prevents configuration drift

### Key Features

- Environment variable loading with `.env` file support
- Automatic type conversion and validation
- Field-level validation with custom validators
- Singleton pattern for global configuration access
- Support for multiple input formats (JSON, comma-separated, newline-separated)
- Case-insensitive environment variable names

---

## Architecture

### File Structure

```
src/config/
├── __init__.py          # Module exports
└── settings.py          # Main Settings class and Mode enum
```

### Design Pattern

The module uses the **Singleton Pattern** combined with **Pydantic Settings**:

1. **Pydantic BaseSettings**: Automatic environment variable loading and validation
2. **Global Singleton**: Single `Settings` instance accessed via `get_settings()`
3. **Lazy Initialization**: Settings loaded on first access
4. **Reset Support**: `reset_settings()` for testing and reinitialization

### Dependencies

**External**:
- `pydantic` (>=2.0.0): Data validation and settings management
- `pydantic-settings` (>=2.0.0): Environment variable integration
- `python-dotenv` (implicit via pydantic-settings): `.env` file loading

**Internal**:
- No internal module dependencies (config is a leaf module)

---

## Core Components

### Settings Class

**Location**: `src/config/settings.py`

```python
class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All settings have sensible defaults and can be overridden via
    environment variables or a .env file.
    """
```

#### Configuration

- **Environment Prefix**: None (direct environment variable names)
- **Environment File**: `.env` (if present)
- **Case Sensitivity**: False (case-insensitive matching)
- **Extra Fields**: Ignored (allows environment variables not in schema)
- **Encoding**: UTF-8

#### Model Configuration

```python
model_config = SettingsConfigDict(
    env_file=".env",
    env_file_encoding="utf-8",
    case_sensitive=False,
    enable_decoding=False,
    extra="ignore",
)
```

### Mode Enum

**Location**: `src/config/settings.py`

```python
class Mode(str, Enum):
    """Application operating mode."""
    SINGLE = "single"
    AUTONOMOUS = "autonomous"
```

Defines the two primary operating modes:
- **SINGLE**: Process one job URL at a time (interactive)
- **AUTONOMOUS**: Batch processing of multiple job URLs

---

## Configuration Categories

### Operating Mode

Controls how the application runs.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `mode` | `Mode` | `Mode.SINGLE` | Operating mode: 'single' for one job, 'autonomous' for batch |

**Environment Variable**: `MODE`

**Validation**: Must be "single" or "autonomous" (case-insensitive)

**Usage**:
```python
settings = get_settings()
if settings.mode == Mode.SINGLE:
    # Process single job
elif settings.mode == Mode.AUTONOMOUS:
    # Batch processing
```

---

### Safety Settings

Safety controls to prevent accidental submissions.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `auto_submit` | `bool` | `False` | If True, submit applications automatically (NOT RECOMMENDED) |
| `max_applications_per_day` | `int` | `10` | Maximum applications to process per day in autonomous mode |

**Environment Variables**:
- `AUTO_SUBMIT`
- `MAX_APPLICATIONS_PER_DAY`

**Validation**:
- `max_applications_per_day`: Must be > 0

**Safety Notes**:
- `auto_submit=False` ensures human confirmation before submission
- `max_applications_per_day` prevents runaway batch processing

---

### Paths

File system paths for data storage and artifacts.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `tracker_db_path` | `Path` | `./data/tracker.db` | Path to the SQLite tracker database |
| `output_dir` | `Path` | `./artifacts` | Directory for generated artifacts |
| `allowlist_log_path` | `Path` | `./data/allowlist.log` | Append-only log of encountered non-prohibited domains |
| `qa_bank_path` | `Path` | `./data/qa_bank.json` | Path to the persistent Q&A bank used for application questions |

**Environment Variables**:
- `TRACKER_DB_PATH`
- `OUTPUT_DIR`
- `ALLOWLIST_LOG_PATH`
- `QA_BANK_PATH`

**Usage**:
```python
settings = get_settings()
tracker_path = settings.tracker_db_path
output_dir = settings.output_dir
output_dir.mkdir(parents=True, exist_ok=True)
```

---

### Runner Settings

Configuration for the browser automation runner (application form filling).

#### Browser Settings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `runner_headless` | `bool` | `False` | Run application browser headless |
| `runner_window_width` | `int` | `1280` | Browser window width |
| `runner_window_height` | `int` | `720` | Browser window height |

**Environment Variables**: `RUNNER_HEADLESS`, `RUNNER_WINDOW_WIDTH`, `RUNNER_WINDOW_HEIGHT`

#### Agent Behavior

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `runner_max_failures` | `int` | `3` | Maximum retry attempts for failed runner steps |
| `runner_max_actions_per_step` | `int` | `4` | Max actions per agent step (form fill batching) |
| `runner_step_timeout` | `int` | `120` | Timeout per runner step in seconds |
| `runner_use_vision` | `str` | `"auto"` | Runner vision mode: 'auto', 'true', or 'false' |
| `runner_assume_yes` | `bool` | `False` | Assume "yes" for non-submit prompts (fit/doc approval); final submit still gated unless auto-submit enabled |
| `runner_yolo_mode` | `bool` | `False` | Enable YOLO mode (best-effort auto-answering) |
| `runner_auto_submit` | `bool` | `False` | Auto-confirm final submit without human prompt (requires YOLO + assume-yes) |

**Environment Variables**: `RUNNER_MAX_FAILURES`, `RUNNER_MAX_ACTIONS_PER_STEP`, `RUNNER_STEP_TIMEOUT`, `RUNNER_USE_VISION`, `RUNNER_ASSUME_YES`, `RUNNER_YOLO_MODE`, `RUNNER_AUTO_SUBMIT`

**Validation**:
- `runner_max_failures`: Must be > 0
- `runner_max_actions_per_step`: Must be > 0
- `runner_step_timeout`: Must be > 0
- `runner_use_vision`: Must be one of: "auto", "true", "false"
- `runner_auto_submit`: Requires both `runner_yolo_mode=True` and `runner_assume_yes=True`

#### Domain Restrictions

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `prohibited_domains` | `list[str]` | `[]` | Domain patterns the runner must NOT navigate to (blocklist-first policy) |

**Environment Variable**: `PROHIBITED_DOMAINS`

**Supported Formats**:
- **JSON List**: `["example.com", "*.example.com"]`
- **Comma-separated**: `example.com, *.example.com`
- **Newline-separated**: Multi-line strings

**Examples**:
- `example.com` - Exact domain
- `*.example.com` - Wildcard subdomain
- `http*://example.com` - Protocol pattern

**Validation**: Custom parser handles multiple input formats

#### LLM Configuration

Runner can use a different LLM than the extractor.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `runner_llm_provider` | `str \| None` | `None` | Runner LLM provider: 'openai', 'anthropic', 'browser_use', or 'auto' |
| `runner_llm_base_url` | `str \| None` | `None` | Runner LLM base URL for OpenAI-compatible endpoints |
| `runner_llm_api_key` | `str \| None` | `None` | Runner LLM API key (overrides extractor provider keys) |
| `runner_llm_model` | `str \| None` | `None` | Runner LLM model ID (e.g., 'gpt-4o', 'claude-sonnet-4-20250514') |
| `runner_llm_reasoning_effort` | `str \| None` | `None` | Reasoning effort for supported models (e.g., 'none', 'minimal', 'low', 'medium', 'high', 'xhigh') |

**Environment Variables**:
- `RUNNER_LLM_PROVIDER`
- `RUNNER_LLM_BASE_URL`
- `RUNNER_LLM_API_KEY`
- `RUNNER_LLM_MODEL`
- `RUNNER_LLM_REASONING_EFFORT`

**Validation**:
- `runner_llm_provider`: Must be one of: "auto", "openai", "anthropic", "browser_use" (or None)

**Fallback Behavior**:
- If `runner_llm_*` settings are `None`, runner falls back to `EXTRACTOR_LLM_*` settings

---

### Chrome Profile Settings

Configure reuse of existing Chrome profiles for session persistence.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `use_existing_chrome_profile` | `bool` | `False` | Use an existing Chrome profile for sessions |
| `chrome_user_data_dir` | `Path \| None` | `None` | Chrome user data directory path |
| `chrome_profile_dir` | `str` | `"Default"` | Chrome profile directory name |
| `chrome_profile_mode` | `str` | `"auto"` | Chrome profile mode: 'copy' (safe), 'direct' (use in place), or 'auto' |

**Environment Variables**:
- `USE_EXISTING_CHROME_PROFILE`
- `CHROME_USER_DATA_DIR`
- `CHROME_PROFILE_DIR`
- `CHROME_PROFILE_MODE`

**Validation**:
- `chrome_profile_mode`: Must be one of: "auto", "copy", "direct"

**Profile Modes**:
- **auto**: Try copy first, fall back to direct on permission errors
- **copy**: Safest (Browser Use copies profile to temp directory)
- **direct**: Use profile in place (riskier; close Chrome first)

**Platform-Specific Paths**:
- **macOS**: `~/Library/Application Support/Google/Chrome`
- **Windows**: `C:\Users\<username>\AppData\Local\Google\Chrome\User Data`
- **Linux**: `~/.config/google-chrome`

**Warning**: Using existing profiles can lead to permission errors. The `auto` mode provides the best balance.

---

### API Settings

Generic LLM API configuration (used as fallback).

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `llm_api_key` | `str \| None` | `None` | API key for LLM provider (OpenAI, Anthropic, etc.) |

**Environment Variable**: `LLM_API_KEY`

**Note**: Module-specific configurations (e.g., `EXTRACTOR_LLM_API_KEY`, `TAILORING_LLM_API_KEY`, `RUNNER_LLM_API_KEY`) take precedence over this generic setting.

---

### Logging

Configure application logging level.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `log_level` | `str` | `"INFO"` | Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL |

**Environment Variable**: `LOG_LEVEL`

**Validation**: Must be one of: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL" (case-insensitive, normalized to uppercase)

---

## Environment Variables

### Complete Environment Variable Reference

| Environment Variable | Type | Default | Module | Description |
|---------------------|------|---------|--------|-------------|
| `MODE` | str | `"single"` | config | Operating mode |
| `AUTO_SUBMIT` | bool | `false` | config | Auto-submit applications |
| `MAX_APPLICATIONS_PER_DAY` | int | `10` | config | Max applications per day |
| `TRACKER_DB_PATH` | Path | `./data/tracker.db` | config | Tracker database path |
| `OUTPUT_DIR` | Path | `./artifacts` | config | Artifacts directory |
| `PROHIBITED_DOMAINS` | list | `[]` | config | Blocked domains |
| `ALLOWLIST_LOG_PATH` | Path | `./data/allowlist.log` | config | Allowlist log path |
| `QA_BANK_PATH` | Path | `./data/qa_bank.json` | config | Q&A bank path |
| `RUNNER_HEADLESS` | bool | `false` | config | Run browser headless |
| `RUNNER_WINDOW_WIDTH` | int | `1280` | config | Browser width |
| `RUNNER_WINDOW_HEIGHT` | int | `720` | config | Browser height |
| `RUNNER_MAX_FAILURES` | int | `3` | config | Max retry attempts |
| `RUNNER_MAX_ACTIONS_PER_STEP` | int | `4` | config | Max actions per step |
| `RUNNER_STEP_TIMEOUT` | int | `120` | config | Step timeout (seconds) |
| `RUNNER_USE_VISION` | str | `"auto"` | config | Vision mode |
| `RUNNER_ASSUME_YES` | bool | `false` | config | Assume yes for fit/doc prompts (final submit still gated) |
| `RUNNER_YOLO_MODE` | bool | `false` | config | Enable runner YOLO mode |
| `RUNNER_LLM_PROVIDER` | str | `None` | config | Runner LLM provider |
| `RUNNER_LLM_BASE_URL` | str | `None` | config | Runner LLM base URL |
| `RUNNER_LLM_API_KEY` | str | `None` | config | Runner LLM API key |
| `RUNNER_LLM_MODEL` | str | `None` | config | Runner LLM model |
| `RUNNER_LLM_REASONING_EFFORT` | str | `None` | config | Runner reasoning effort |
| `USE_EXISTING_CHROME_PROFILE` | bool | `false` | config | Use existing Chrome profile |
| `CHROME_USER_DATA_DIR` | Path | `None` | config | Chrome user data directory |
| `CHROME_PROFILE_DIR` | str | `"Default"` | config | Chrome profile directory |
| `CHROME_PROFILE_MODE` | str | `"auto"` | config | Chrome profile mode |
| `LLM_API_KEY` | str | `None` | config | Generic LLM API key |
| `LOG_LEVEL` | str | `"INFO"` | config | Logging level |

### Loading Order

Pydantic Settings loads configuration in this order (later sources override earlier ones):

1. **Field defaults** (defined in `Settings` class)
2. **Environment variables** (from system environment)
3. **`.env` file** (if present in working directory)
4. **Constructor arguments** (explicit overrides)

### .env File Format

See `.env.example` for the complete reference. Example:

```bash
# Operating Mode
MODE=single
AUTO_SUBMIT=false

# Paths
OUTPUT_DIR=./artifacts
TRACKER_DB_PATH=./data/tracker.db

# Runner Settings
RUNNER_HEADLESS=false
RUNNER_WINDOW_WIDTH=1280
RUNNER_WINDOW_HEIGHT=720

# Domain Restrictions
PROHIBITED_DOMAINS=example.com, *.evil.com

# Chrome Profile (Optional)
USE_EXISTING_CHROME_PROFILE=true
CHROME_USER_DATA_DIR=/Users/username/Library/Application Support/Google/Chrome
CHROME_PROFILE_DIR=Default
CHROME_PROFILE_MODE=auto

# Logging
LOG_LEVEL=INFO
```

---

## Module Integration

The `config` module is a **foundational dependency** for all other modules. It has no internal dependencies but is imported by:

### Direct Consumers

#### 1. Main Application (`src/__main__.py`)

```python
from src.config.settings import Settings

settings = Settings()
logger = configure_logging(level=settings.log_level)
```

**Usage**: Load settings at application startup, configure logging, resolve output directories.

#### 2. Extractor Module (`src/extractor/`)

The extractor has its own `ExtractorConfig` (in `src/extractor/config.py`) but uses the main `Settings` for Chrome profile configuration.

```python
from src.config.settings import get_settings

settings = get_settings()
if settings.use_existing_chrome_profile:
    # Use Chrome profile settings
```

**Integration Point**: Chrome profile settings (`use_existing_chrome_profile`, `chrome_user_data_dir`, `chrome_profile_dir`, `chrome_profile_mode`)

#### 3. Runner Module (`src/runner/`)

```python
from src.config.settings import get_settings

settings = get_settings()
prohibited_domains = settings.prohibited_domains
qa_bank_path = settings.qa_bank_path
```

**Usage**: Domain restrictions, Q&A bank path, runner LLM configuration, Chrome profile settings.

#### 4. Autonomous Module (`src/autonomous/`)

```python
# Receives settings instance from main application
def __init__(self, settings: Settings, ...):
    self.settings = settings
```

**Usage**: Mode detection, max applications per day, auto-submit flag.

#### 5. Tracker Module (`src/tracker/`)

```python
settings = get_settings()
db_path = settings.tracker_db_path
```

**Usage**: Database path configuration.

### Configuration Hierarchy

Job-Easy uses a **hierarchical configuration pattern**:

```
src/config/settings.py (Global)
    ├─ src/extractor/config.py (ExtractorConfig)
    │   └─ Env prefix: EXTRACTOR_*
    ├─ src/tailoring/config.py (TailoringConfig)
    │   └─ Env prefix: TAILORING_* (fallback to EXTRACTOR_*)
    ├─ src/scoring/config.py (ScoringConfig)
    │   └─ Env prefix: SCORING_*
    └─ src/runner/ (Uses global Settings)
```

**Design Rationale**:
- **Global Settings**: Application-wide configuration (mode, paths, safety)
- **Module Configs**: Module-specific settings with appropriate prefixes
- **Fallback Chain**: Tailoring falls back to Extractor, Runner falls back to Extractor

---

## API Reference

### Functions

#### `get_settings() -> Settings`

Get the application settings singleton.

**Returns**: The global `Settings` instance

**Behavior**:
- Lazy initialization: Creates settings on first call
- Subsequent calls return the same instance
- Thread-safe (global variable access)

**Example**:
```python
from src.config.settings import get_settings

settings = get_settings()
print(f"Running in {settings.mode} mode")
```

#### `reset_settings() -> None`

Reset the settings singleton.

**Returns**: None

**Use Case**: Testing and reinitialization

**Example**:
```python
from src.config.settings import reset_settings, get_settings

# In test teardown
reset_settings()

# Next call to get_settings() creates a fresh instance
settings = get_settings()
```

### Field Validators

#### `validate_mode(cls, v: str | Mode) -> Mode`

Convert string mode to `Mode` enum.

**Validation**:
- Accepts: "single", "autonomous" (case-insensitive)
- Rejects: Any other value

**Raises**: `ValueError` if invalid mode

#### `parse_prohibited_domains(cls, v: object) -> list[str]`

Parse `PROHIBITED_DOMAINS` from environment-friendly formats.

**Supported Formats**:
- JSON list: `["example.com", "*.example.com"]`
- Comma-separated: `example.com, *.example.com`
- Newline-separated: Multi-line string
- Single value: `example.com`

**Returns**: List of domain patterns (empty list if None)

#### `validate_log_level(cls, v: str) -> str`

Validate log level is a known level.

**Validation**:
- Accepts: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL" (case-insensitive)
- Normalizes to uppercase

**Raises**: `ValueError` if invalid log level

#### `validate_chrome_profile_mode(cls, v: str) -> str`

Validate `chrome_profile_mode`.

**Validation**:
- Accepts: "auto", "copy", "direct" (case-insensitive)
- Normalizes to lowercase

**Raises**: `ValueError` if invalid mode

#### `validate_runner_use_vision(cls, v: str) -> str`

Validate `runner_use_vision`.

**Validation**:
- Accepts: "auto", "true", "false" (case-insensitive)
- Normalizes to lowercase

**Raises**: `ValueError` if invalid value

#### `validate_runner_llm_provider(cls, v: str | None) -> str | None`

Validate `runner_llm_provider`.

**Validation**:
- Accepts: "auto", "openai", "anthropic", "browser_use" (case-insensitive), or None
- Normalizes to lowercase

**Raises**: `ValueError` if invalid provider

---

## Configuration Examples

### Example 1: Basic Single-Job Mode

```python
# .env
MODE=single
AUTO_SUBMIT=false
OUTPUT_DIR=./artifacts
LOG_LEVEL=INFO
```

```python
from src.config.settings import get_settings

settings = get_settings()
assert settings.mode == "single"
assert settings.auto_submit is False
```

### Example 2: Autonomous Mode with Limits

```python
# .env
MODE=autonomous
MAX_APPLICATIONS_PER_DAY=25
AUTO_SUBMIT=false
PROHIBITED_DOMAINS=scam.com, *.fake.com
```

```python
settings = get_settings()
assert settings.mode == "autonomous"
assert settings.max_applications_per_day == 25
assert "scam.com" in settings.prohibited_domains
```

### Example 3: Chrome Profile Configuration

```python
# .env
USE_EXISTING_CHROME_PROFILE=true
CHROME_USER_DATA_DIR=/Users/john/Library/Application Support/Google/Chrome
CHROME_PROFILE_DIR=Profile 1
CHROME_PROFILE_MODE=copy
```

```python
from pathlib import Path

settings = get_settings()
assert settings.use_existing_chrome_profile is True
assert settings.chrome_profile_dir == "Profile 1"
assert settings.chrome_profile_mode == "copy"
```

### Example 4: Runner LLM Override

```python
# .env
# Extractor uses OpenAI
EXTRACTOR_LLM_PROVIDER=openai
EXTRACTOR_LLM_API_KEY=sk-...

# Runner uses Anthropic
RUNNER_LLM_PROVIDER=anthropic
RUNNER_LLM_API_KEY=sk-ant-...
RUNNER_LLM_MODEL=claude-sonnet-4-20250514
```

```python
settings = get_settings()
assert settings.runner_llm_provider == "anthropic"
assert settings.runner_llm_model == "claude-sonnet-4-20250514"
```

### Example 5: Testing with Reset

```python
import os
from src.config.settings import get_settings, reset_settings

def test_custom_config():
    # Set test environment
    os.environ["MODE"] = "autonomous"
    os.environ["MAX_APPLICATIONS_PER_DAY"] = "5"

    # Reset to pick up new env vars
    reset_settings()

    settings = get_settings()
    assert settings.mode == "autonomous"
    assert settings.max_applications_per_day == 5

    # Cleanup
    del os.environ["MODE"]
    del os.environ["MAX_APPLICATIONS_PER_DAY"]
    reset_settings()
```

### Example 6: Programmatic Override

```python
from src.config.settings import Settings

# Override defaults programmatically
settings = Settings(
    mode="autonomous",
    max_applications_per_day=50,
    runner_headless=True,
)

assert settings.mode == "autonomous"
assert settings.max_applications_per_day == 50
assert settings.runner_headless is True
```

---

## Testing

### Test Coverage

The config module has comprehensive unit tests in `tests/unit/config/test_settings.py`.

**Test Categories**:

1. **Default Values** (`TestSettingsDefaults`)
   - Verify all fields have correct defaults
   - No environment variables required

2. **Environment Loading** (`TestSettingsFromEnvironment`)
   - Test environment variable parsing
   - Multiple input formats for `PROHIBITED_DOMAINS`
   - Path configurations

3. **Validation** (`TestSettingsValidation`)
   - Invalid mode values rejected
   - Positive integer constraints enforced
   - Log level validation

4. **Optional Fields** (`TestSettingsOptionalFields`)
   - Chrome profile settings optional
   - LLM API key optional
   - Null handling

### Running Tests

```bash
# Run all config tests
pytest tests/unit/config/

# Run specific test class
pytest tests/unit/config/test_settings.py::TestSettingsDefaults

# Run with coverage
pytest tests/unit/config/ --cov=src/config --cov-report=term-missing
```

### Test Utilities

**Reset Settings Between Tests**:
```python
import pytest
from src.config.settings import reset_settings

@pytest.fixture(autouse=True)
def reset_config():
    """Reset settings singleton before each test."""
    reset_settings()
    yield
    reset_settings()
```

**Mock Environment Variables**:
```python
def test_with_env(monkeypatch):
    monkeypatch.setenv("MODE", "autonomous")
    monkeypatch.setenv("MAX_APPLICATIONS_PER_DAY", "25")

    reset_settings()
    settings = get_settings()
    assert settings.mode == "autonomous"
```

---

## Best Practices

### 1. Use Singleton Pattern

**Do**:
```python
from src.config.settings import get_settings

settings = get_settings()
```

**Don't**:
```python
# Creates new instance, bypasses singleton
from src.config.settings import Settings
settings = Settings()
```

### 2. Environment Variable Naming

**Convention**: Use UPPERCASE with underscores

```bash
# Good
MODE=single
RUNNER_HEADLESS=false

# Bad (will still work due to case-insensitivity, but inconsistent)
mode=single
runner_headless=false
```

### 3. Testing Configuration

**Always reset settings in tests**:
```python
from src.config.settings import reset_settings

def test_something():
    reset_settings()  # Start with clean state
    # ... test logic ...
```

### 4. Validation Early

**Load and validate settings at startup**:
```python
def main():
    try:
        settings = Settings()
    except Exception as e:
        print(f"Configuration error: {e}")
        return 1

    # Continue with validated settings
    run_app(settings)
```

### 5. Type Hints

**Use type hints when passing settings**:
```python
def process_job(settings: Settings, url: str) -> None:
    if settings.mode == Mode.SINGLE:
        # IDE autocomplete and type checking work
        pass
```

### 6. Path Handling

**Use Path objects, create directories as needed**:
```python
settings = get_settings()
output_dir = settings.output_dir
output_dir.mkdir(parents=True, exist_ok=True)

# Write to path
report_path = output_dir / "report.json"
report_path.write_text(json.dumps(data))
```

### 7. Prohibited Domains

**Use specific patterns**:
```bash
# Good: Specific patterns
PROHIBITED_DOMAINS=phishing-site.com, *.scam.net, http*://malicious.org

# Bad: Too broad
PROHIBITED_DOMAINS=*.com
```

### 8. Chrome Profile Safety

**Use "auto" mode for best compatibility**:
```bash
CHROME_PROFILE_MODE=auto  # Recommended
# Falls back gracefully on permission errors
```

### 9. Environment Variable Documentation

**Document all custom env vars in .env.example**:
```bash
# Always keep .env.example up to date with new settings
# Include descriptions and examples
```

### 10. Avoid Hardcoding

**Don't**:
```python
db_path = "./data/tracker.db"  # Hardcoded
```

**Do**:
```python
settings = get_settings()
db_path = settings.tracker_db_path  # Configurable
```

---

## Security Considerations

### 1. API Keys

- Never commit `.env` files with API keys
- Use environment variables or secret management systems in production
- Rotate keys regularly

### 2. Chrome Profile Access

- Using `chrome_profile_mode=direct` can expose browser cookies/sessions
- Prefer `copy` mode to isolate automation from personal browsing
- Never use profiles with sensitive logged-in sessions

### 3. Auto-Submit Flag

- **Default is False** for safety
- Only enable `auto_submit=True` in fully trusted, tested scenarios
- Always log submission actions

### 4. Prohibited Domains

- Maintain a curated blocklist
- Review allowlist log regularly
- Add patterns defensively (e.g., `*.suspicious-tld`)

---

## Troubleshooting

### Problem: Settings not loading from .env

**Cause**: `.env` file not in working directory or syntax error

**Solution**:
```bash
# Verify .env location
ls -la .env

# Check for syntax errors (no spaces around =)
MODE=single  # Correct
MODE = single  # Wrong
```

### Problem: Chrome profile permission denied

**Cause**: Profile directory has restricted permissions or is in use

**Solution**:
```bash
# Use auto mode (recommended)
CHROME_PROFILE_MODE=auto

# Or try a different profile
CHROME_PROFILE_DIR=Profile 2

# Or fix permissions (macOS/Linux)
chmod -R u+r "$CHROME_USER_DATA_DIR/$CHROME_PROFILE_DIR"
```

### Problem: Invalid configuration value

**Cause**: Validation error in Pydantic

**Solution**: Check error message for field name and expected format
```python
# Error: "mode must be 'single' or 'autonomous'"
MODE=single  # Fix: Use valid value
```

### Problem: Singleton returns old values after env change

**Cause**: Settings cached in singleton

**Solution**: Reset settings after environment changes
```python
reset_settings()
settings = get_settings()  # Reloads from environment
```

---

## Migration Guide

### From Hardcoded Configs

**Before**:
```python
HEADLESS = False
MAX_APPS = 10
DB_PATH = "./data/tracker.db"
```

**After**:
```python
from src.config.settings import get_settings

settings = get_settings()
headless = settings.runner_headless
max_apps = settings.max_applications_per_day
db_path = settings.tracker_db_path
```

### From Old Environment Variables

If migrating from a different naming convention:

1. Update `.env` file with new names
2. Update environment variable names in deployment systems
3. Use `.env.example` as reference

---

## Future Enhancements

Potential improvements to the config module:

1. **Configuration Profiles**: Support for multiple named profiles (dev, prod, test)
2. **Remote Configuration**: Load settings from remote config service
3. **Schema Validation**: JSON Schema export for documentation
4. **Hot Reload**: Watch `.env` file for changes
5. **Encryption**: Encrypted settings for sensitive values
6. **Configuration UI**: Web interface for config management

---

## Related Documentation

- [Project Brief](project-brief.md) - Overall architecture and design
- [Development Guide](dev.md) - Development workflow and conventions
- `.env.example` - Complete environment variable reference

---

## Changelog

- **2026-01-19**: Added `runner_llm_reasoning_effort` configuration
- **2026-01-15**: Initial config module implementation
- **2026-01-15**: Added Chrome profile settings support
