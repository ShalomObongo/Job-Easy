# Utils Module Documentation

> Last updated: 2026-01-21
> Module: `src/utils/`

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Core Components](#core-components)
  - [Logging Configuration](#logging-configuration)
- [API Reference](#api-reference)
  - [configure_logging](#configure_logging)
  - [get_logger](#get_logger)
  - [reset_logging](#reset_logging)
- [Module Integration](#module-integration)
- [Usage Patterns](#usage-patterns)
- [Configuration](#configuration)
- [Testing](#testing)
- [Best Practices](#best-practices)

---

## Overview

The `utils` module provides **shared utilities and helper functions** for the Job-Easy application. It serves as the foundation layer that other modules depend on for cross-cutting concerns.

### Purpose

- **Centralized Logging**: Unified logging configuration for the entire application
- **Shared Utilities**: Common helper functions used across multiple modules
- **Cross-Module Support**: Foundation layer with no internal dependencies

### Current Components

Currently, the utils module contains:

1. **Logging System** (`logging.py`): Application-wide logging configuration and management

### Key Features

- Centralized logger configuration with consistent formatting
- Hierarchical logger creation for module-specific logging
- Configurable log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Single configuration point prevents logging conflicts
- Test-friendly with reset capability

---

## Architecture

### File Structure

```
src/utils/
├── __init__.py          # Module exports ("Shared utilities and helpers")
└── logging.py           # Logging configuration and utilities
```

### Design Pattern

The utils module follows these architectural principles:

1. **Leaf Module Pattern**: No dependencies on other internal modules (only external packages)
2. **Singleton Logger**: Global logger instance prevents duplicate handlers and configuration
3. **Hierarchical Naming**: Module-specific child loggers inherit from main logger
4. **Global State Management**: Tracks configuration state to prevent re-initialization

### Dependencies

**External**:
- `logging` (Python stdlib): Core logging functionality
- `sys` (Python stdlib): Standard streams for console output

**Internal**:
- None (utils is a foundational module with no internal dependencies)

**Dependent Modules**:

All major modules use the utils logging system:
- `src/__main__.py`: Main entry point configures logging
- `src/autonomous/`: Autonomous batch processing
- `src/extractor/`: Job description extraction
- `src/runner/`: Application runner
- `src/scoring/`: Fit scoring
- `src/tailoring/`: Document tailoring
- `src/tracker/`: Application tracking
- `src/hitl/`: Human-in-the-loop tools

---

## Core Components

### Logging Configuration

**Location**: `src/utils/logging.py`

The logging module provides a centralized logging configuration system for the entire Job-Easy application.

#### Constants

```python
LOGGER_NAME = "job_easy"
```
The root logger name for the application. All module-specific loggers are children of this logger.

```python
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```
Default log message format including:
- `%(asctime)s`: Timestamp of the log event
- `%(name)s`: Logger name (e.g., `job_easy.extractor.service`)
- `%(levelname)s`: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `%(message)s`: The actual log message

```python
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
```
Default timestamp format (ISO 8601-like): `2026-01-21 15:30:45`

#### Internal State

```python
_configured = False
```
Global flag tracking whether logging has been initialized. Prevents duplicate handler creation.

#### Key Features

1. **Single Configuration Point**: `configure_logging()` is called once at application startup
2. **Console Output**: Logs are written to `stderr` by default
3. **No File Logging**: Currently only console logging (can be extended if needed)
4. **No Propagation**: Prevents log messages from bubbling up to the root Python logger
5. **Handler Management**: Automatically prevents duplicate handlers

---

## API Reference

### configure_logging

```python
def configure_logging(
    level: str | None = None,
    format_string: str = LOG_FORMAT,
    date_format: str = DATE_FORMAT,
) -> logging.Logger
```

Configure and return the main application logger. This should be called once at application startup.

**Parameters**:

- `level` (str | None): Log level as string. One of:
  - `"DEBUG"`: Detailed information for diagnosing problems
  - `"INFO"`: Confirmation that things are working as expected (default)
  - `"WARNING"`: An indication something unexpected happened
  - `"ERROR"`: A serious problem occurred
  - `"CRITICAL"`: A very serious error

  If `None`, defaults to `"INFO"`.

- `format_string` (str): Format string for log messages. Uses Python logging format codes. Default: `LOG_FORMAT`

- `date_format` (str): Format string for timestamps in log messages. Default: `DATE_FORMAT`

**Returns**:
- `logging.Logger`: The configured root application logger with name `"job_easy"`

**Behavior**:

- **First Call**: Creates logger, adds console handler, sets format and level
- **Subsequent Calls**: Updates log level on existing logger without adding new handlers
- **Thread-Safe**: Uses global `_configured` flag to prevent race conditions
- **Handler Management**: Clears any existing handlers on first configuration
- **Stream Output**: Always logs to `sys.stderr`
- **No Propagation**: Sets `propagate=False` to prevent duplicate logging

**Usage Example**:

```python
from src.utils.logging import configure_logging

# Configure at application startup
logger = configure_logging(level="DEBUG")
logger.info("Application starting")

# Reconfigure to change log level
logger = configure_logging(level="WARNING")
```

**Notes**:
- This function should be called in `src/__main__.py` before any other module initialization
- The returned logger is the same instance returned by `logging.getLogger("job_easy")`
- Log level can be overridden by command-line arguments or settings

---

### get_logger

```python
def get_logger(name: str) -> logging.Logger
```

Get a child logger for a specific module. This is the primary way modules should obtain their logger.

**Parameters**:

- `name` (str): The module name or identifier. This will be appended to `"job_easy."` to create the full logger name.

**Returns**:
- `logging.Logger`: A child logger with the name `"job_easy.<name>"`

**Behavior**:

- Creates or retrieves a child logger of the main application logger
- Child loggers automatically inherit:
  - Log level from parent (unless explicitly overridden)
  - Handlers from parent (via propagation mechanism)
  - Format configuration
- The parent logger must be configured first via `configure_logging()`

**Usage Example**:

```python
from src.utils.logging import get_logger

logger = get_logger("extractor")
# Logger name: "job_easy.extractor"

logger.info("Starting extraction")
logger.debug("Processing URL: %s", url)
logger.error("Extraction failed: %s", error)
```

**Common Pattern in Modules**:

Most modules use Python's `__name__` built-in directly with `logging.getLogger()`:

```python
import logging

logger = logging.getLogger(__name__)
# If module is src.extractor.service, logger name is "src.extractor.service"
```

This pattern also works because:
- When `configure_logging()` runs, it sets up the `"job_easy"` logger
- Module loggers automatically inherit configuration through Python's logging hierarchy
- The naming is more specific and shows the full module path

**Note**: The `get_logger()` function is provided as a convenience but most modules in Job-Easy use the `logging.getLogger(__name__)` pattern directly.

---

### reset_logging

```python
def reset_logging() -> None
```

Reset logging configuration. Primarily used for testing to ensure clean state between tests.

**Parameters**: None

**Returns**: None

**Behavior**:

- Removes all handlers from the main application logger
- Resets logger level to `NOTSET` (inherit from parent)
- Resets the `_configured` flag to `False`
- Allows `configure_logging()` to be called again

**Usage Example**:

```python
from src.utils.logging import configure_logging, reset_logging

# In test setup
def setup_function():
    reset_logging()
    configure_logging(level="DEBUG")

# In test teardown
def teardown_function():
    reset_logging()
```

**Warning**: This should **only** be used in test code. Calling this in production code can cause:
- Loss of logging configuration
- Missing log messages
- Unexpected behavior in concurrent code

---

## Module Integration

### How Utils Integrates with Other Modules

The utils module is a **foundational dependency** used throughout the application:

```
┌─────────────────────────────────────────────────────┐
│                    Application                       │
│                  (src/__main__.py)                   │
│                                                      │
│  1. configure_logging(level=settings.log_level)      │
└──────────────────────┬───────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────┐
│                   utils.logging                      │
│                                                      │
│  - Creates "job_easy" root logger                   │
│  - Sets up console handler                          │
│  - Configures format and level                      │
└──────────────────────┬───────────────────────────────┘
                       │
       ┌───────────────┴────────────────┐
       ↓                                ↓
┌─────────────┐                  ┌─────────────┐
│  extractor  │                  │   runner    │
│             │                  │             │
│ logger =    │                  │ logger =    │
│ getLogger   │                  │ getLogger   │
│ (__name__)  │                  │ (__name__)  │
└─────────────┘                  └─────────────┘
       ↓                                ↓
   "job_easy.                      "job_easy.
    extractor.                      runner.
    service"                        service"
```

### Initialization Flow

1. **Application Startup** (`src/__main__.py:382`):
   ```python
   from src.utils.logging import configure_logging

   settings = Settings()
   log_level = parsed.log_level or settings.log_level
   logger = configure_logging(level=log_level)
   ```

2. **Module Logger Creation** (e.g., `src/extractor/service.py:20`):
   ```python
   import logging

   logger = logging.getLogger(__name__)
   ```

3. **Logging in Action**:
   ```python
   logger.info("Starting extraction for URL: %s", url)
   logger.debug("Browser initialized with config: %s", config)
   logger.error("Extraction failed: %s", str(error))
   ```

### Usage Across Modules

| Module | Logger Name Pattern | Example |
|--------|-------------------|---------|
| `autonomous/service.py` | `__name__` | `src.autonomous.service` |
| `autonomous/runner.py` | `__name__` | `src.autonomous.runner` |
| `extractor/service.py` | `__name__` | `src.extractor.service` |
| `extractor/agent.py` | `__name__` | `src.extractor.agent` |
| `runner/service.py` | `__name__` | `src.runner.service` |
| `runner/agent.py` | `__name__` | `src.runner.agent` |
| `scoring/*` | `__name__` | `src.scoring.*` |
| `tailoring/service.py` | `__name__` | `src.tailoring.service` |
| `tailoring/llm.py` | `__name__` | `src.tailoring.llm` |
| `tailoring/resume.py` | `__name__` | `src.tailoring.resume` |
| `tailoring/renderer.py` | `__name__` | `src.tailoring.renderer` |
| `tailoring/cover_letter.py` | `__name__` | `src.tailoring.cover_letter` |
| `tailoring/review.py` | `__name__` | `src.tailoring.review` |
| `tailoring/plan.py` | `__name__` | `src.tailoring.plan` |
| `tracker/*` | `__name__` | `src.tracker.*` |

**Note**: All modules use `logging.getLogger(__name__)` which automatically creates loggers that inherit from the configured root logger.

---

## Usage Patterns

### Standard Module Logging Pattern

The standard pattern used across all Job-Easy modules:

```python
# At the top of the module
import logging

logger = logging.getLogger(__name__)

# In functions/methods
def some_function(data: str) -> None:
    logger.debug("Function called with data: %s", data)

    try:
        result = process(data)
        logger.info("Processing successful")
        return result
    except Exception as e:
        logger.error("Processing failed: %s", str(e), exc_info=True)
        raise
```

### Log Level Guidelines

Use appropriate log levels for different types of messages:

**DEBUG** - Detailed diagnostic information:
```python
logger.debug("Initializing extractor with config: %s", config)
logger.debug("Browser state: %s", browser.get_state())
logger.debug("Parsed %d fields from job description", len(fields))
```

**INFO** - General informational messages:
```python
logger.info("Starting job extraction for URL: %s", url)
logger.info("Extraction completed successfully")
logger.info("Generated resume at: %s", resume_path)
```

**WARNING** - Something unexpected but recoverable:
```python
logger.warning("Retrying extraction after timeout (attempt %d)", retry_count)
logger.warning("Missing optional field: %s", field_name)
logger.warning("Using fallback configuration")
```

**ERROR** - Serious problems that prevented operation:
```python
logger.error("Failed to extract job description: %s", str(error))
logger.error("Database connection failed", exc_info=True)
logger.error("Invalid configuration: %s", validation_error)
```

**CRITICAL** - Very serious errors that may cause shutdown:
```python
logger.critical("Unable to initialize required service")
logger.critical("Database corruption detected")
```

### Structured Logging

Use format strings with `%s` placeholders for efficient logging:

**Good** (efficient, format string only evaluated if log level matches):
```python
logger.debug("Processing item %s with config %s", item_id, config)
```

**Bad** (f-strings always evaluated even if log level prevents output):
```python
logger.debug(f"Processing item {item_id} with config {config}")
```

### Exception Logging

Include stack traces for errors using `exc_info=True`:

```python
try:
    result = risky_operation()
except Exception as e:
    logger.error("Operation failed: %s", str(e), exc_info=True)
    raise
```

---

## Configuration

### Log Level Configuration

Log level can be set in three ways (in order of precedence):

1. **Command-line argument** (highest priority):
   ```bash
   python -m src single https://example.com --log-level DEBUG
   ```

2. **Environment variable**:
   ```bash
   export LOG_LEVEL=DEBUG
   python -m src single https://example.com
   ```

3. **Settings default** (lowest priority):
   - Default: `INFO`
   - Set in `src/config/settings.py`

### Custom Format Configuration

To use a custom log format:

```python
from src.utils.logging import configure_logging

custom_format = "%(levelname)s | %(name)s | %(message)s"
logger = configure_logging(
    level="DEBUG",
    format_string=custom_format,
    date_format="%H:%M:%S"
)
```

### Log Output

Currently, all logs go to **stderr** (console output). This allows:
- Easy viewing during development
- Standard Unix redirection: `python -m src ... 2>app.log`
- Separation of logs from stdout (which may contain JSON or other structured output)

**Future Extensions**:

The logging system can be extended to support:
- File-based logging with rotation
- JSON-formatted logs for structured logging systems
- Remote logging to services like Sentry or CloudWatch
- Multiple handlers (console + file)

---

## Testing

### Test Coverage

The utils module has comprehensive test coverage in `tests/unit/utils/test_logging.py`.

### Test Classes

**TestLoggerConfiguration**:
- `test_configure_logging_creates_logger`: Verifies logger creation
- `test_configure_logging_respects_level`: Tests log level configuration
- `test_configure_logging_default_level_is_info`: Validates default behavior

**TestLogOutput**:
- `test_log_message_includes_level`: Checks format includes level
- `test_log_message_includes_timestamp`: Validates timestamp in output

**TestGetLogger**:
- `test_get_logger_returns_child_logger`: Tests child logger creation
- `test_get_logger_inherits_level`: Validates level inheritance

### Running Tests

```bash
# Run all utils tests
pytest tests/unit/utils/

# Run with coverage
pytest tests/unit/utils/ --cov=src/utils --cov-report=term-missing

# Run specific test
pytest tests/unit/utils/test_logging.py::TestLoggerConfiguration::test_configure_logging_creates_logger
```

### Test Pattern Example

```python
from src.utils.logging import configure_logging, reset_logging

def test_logging_level():
    # Setup: Reset to clean state
    reset_logging()

    # Act: Configure with DEBUG level
    logger = configure_logging(level="DEBUG")

    # Assert: Verify configuration
    assert logger.level == logging.DEBUG

    # Cleanup: Reset after test
    reset_logging()
```

---

## Best Practices

### 1. Logger Initialization

**Do**: Use `logging.getLogger(__name__)` in modules
```python
import logging

logger = logging.getLogger(__name__)
```

**Don't**: Create new loggers with custom names
```python
# Avoid this - breaks hierarchy
logger = logging.getLogger("my_custom_logger")
```

### 2. Configure Once

**Do**: Configure logging once at application startup
```python
# In src/__main__.py
logger = configure_logging(level=settings.log_level)
```

**Don't**: Call `configure_logging()` in multiple places
```python
# Avoid this - can cause handler duplication
def my_function():
    configure_logging()  # NO!
```

### 3. Use Lazy Formatting

**Do**: Use `%s` format strings
```python
logger.debug("Processing %s with %s", item, config)
```

**Don't**: Use f-strings or string concatenation
```python
# Avoid - always evaluates even if not logged
logger.debug(f"Processing {item} with {config}")
logger.debug("Processing " + item + " with " + str(config))
```

### 4. Include Context in Log Messages

**Do**: Include relevant identifiers and context
```python
logger.info("Extraction completed for job %s at company %s",
           job_id, company_name)
```

**Don't**: Use vague messages
```python
logger.info("Extraction completed")  # Not enough context
```

### 5. Log Exceptions Properly

**Do**: Use `exc_info=True` for tracebacks
```python
try:
    risky_operation()
except Exception as e:
    logger.error("Operation failed: %s", str(e), exc_info=True)
```

**Don't**: Lose stack trace information
```python
except Exception as e:
    logger.error(str(e))  # Missing traceback
```

### 6. Choose Appropriate Log Levels

**Do**: Match severity to log level
```python
logger.debug("Starting process")     # Diagnostic
logger.info("Process completed")     # Informational
logger.warning("Retrying after timeout")  # Unexpected but handled
logger.error("Process failed", exc_info=True)  # Error condition
```

**Don't**: Use inappropriate levels
```python
logger.error("Starting process")  # Not an error!
logger.debug("Critical system failure")  # Too low severity!
```

### 7. Test-Friendly Logging

**Do**: Reset logging state in test fixtures
```python
import pytest
from src.utils.logging import reset_logging, configure_logging

@pytest.fixture(autouse=True)
def setup_logging():
    reset_logging()
    configure_logging(level="DEBUG")
    yield
    reset_logging()
```

**Don't**: Leave logging state dirty between tests
```python
# This can cause test pollution
def test_something():
    configure_logging(level="ERROR")
    # ... test code ...
    # Forgot to reset!
```

### 8. Performance Considerations

**Do**: Be mindful of expensive operations in debug logs
```python
if logger.isEnabledFor(logging.DEBUG):
    expensive_debug_info = compute_expensive_data()
    logger.debug("Debug data: %s", expensive_debug_info)
```

**Don't**: Perform expensive operations unconditionally
```python
# This runs even if DEBUG is disabled
logger.debug("Debug data: %s", compute_expensive_data())
```

### 9. Avoid Sensitive Data

**Do**: Redact sensitive information
```python
logger.info("User logged in: %s", user_id)  # OK
```

**Don't**: Log passwords, tokens, or PII
```python
logger.info("Password: %s", password)  # NEVER!
logger.debug("API token: %s", api_token)  # NO!
logger.info("SSN: %s", ssn)  # DANGEROUS!
```

### 10. Module-Specific Loggers

**Do**: Use module-level loggers for better filtering
```python
# Each module gets its own logger
# src/extractor/service.py
logger = logging.getLogger(__name__)  # "src.extractor.service"

# src/runner/agent.py
logger = logging.getLogger(__name__)  # "src.runner.agent"
```

This allows filtering logs by module:
```python
# Show only extractor logs
logging.getLogger("src.extractor").setLevel(logging.DEBUG)
logging.getLogger("src.runner").setLevel(logging.WARNING)
```

---

## Future Enhancements

### Potential Extensions

1. **File Logging**:
   ```python
   def configure_logging(
       level: str | None = None,
       file_path: Path | None = None,
       max_bytes: int = 10_000_000,  # 10MB
       backup_count: int = 5,
   ) -> logging.Logger:
       # Add RotatingFileHandler
   ```

2. **JSON Structured Logging**:
   ```python
   # For integration with log aggregation systems
   import json

   class JSONFormatter(logging.Formatter):
       def format(self, record):
           return json.dumps({
               "timestamp": record.created,
               "level": record.levelname,
               "logger": record.name,
               "message": record.getMessage(),
               "module": record.module,
           })
   ```

3. **Context Managers for Temporary Log Levels**:
   ```python
   from contextlib import contextmanager

   @contextmanager
   def log_level(logger, level):
       old_level = logger.level
       logger.setLevel(level)
       try:
           yield
       finally:
           logger.setLevel(old_level)

   # Usage
   with log_level(logger, logging.DEBUG):
       # Temporary DEBUG logging
       process_with_verbose_logging()
   ```

4. **Per-Module Log Configuration**:
   ```python
   def configure_module_logging(
       module_levels: dict[str, str]
   ) -> None:
       """
       Configure different log levels per module.

       Example:
           configure_module_logging({
               "extractor": "DEBUG",
               "runner": "INFO",
               "scoring": "WARNING",
           })
       """
   ```

5. **Log Filtering**:
   ```python
   class SensitiveDataFilter(logging.Filter):
       def filter(self, record):
           # Redact sensitive data from log messages
           record.msg = redact_sensitive_data(record.msg)
           return True
   ```

---

## Summary

The **utils module** is a foundational component of Job-Easy that provides:

- **Centralized Logging**: Single configuration point for application-wide logging
- **Hierarchical Logger Management**: Module-specific loggers with inheritance
- **Flexible Configuration**: Configurable levels, formats, and output streams
- **Test-Friendly**: Reset capability for clean test isolation
- **Production-Ready**: Used by all major modules in the application

### Key Takeaways

1. **Configure once** at application startup in `__main__.py`
2. **Use module loggers** with `logging.getLogger(__name__)`
3. **Choose appropriate log levels** for different message types
4. **Use lazy formatting** with `%s` placeholders for performance
5. **Include stack traces** with `exc_info=True` for errors
6. **Reset logging** in tests for clean state

### Related Documentation

- [Config Module](./config.md): Settings and configuration management
- [Development Guide](./dev.md): Development workflow and testing
- [Extractor Module](./extractor.md): Job extraction service (uses logging)
- [Runner Module](./runner.md): Application runner (uses logging)
- [Autonomous Module](./autonomous.md): Batch processing (uses logging)

---

*For questions or issues with the utils module, see the test suite in `tests/unit/utils/` or examine usage in `src/__main__.py` and service modules.*
