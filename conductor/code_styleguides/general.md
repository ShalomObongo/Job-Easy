# General Code Styleguide

> Universal coding standards for the Job-Easy project

---

## Guiding Principles

### 1. Clarity Over Cleverness
- Write code that is easy to read and understand
- Favor explicit over implicit behavior
- Choose descriptive names over abbreviations

### 2. Consistency
- Follow established patterns in the codebase
- Use consistent naming conventions
- Maintain uniform code formatting

### 3. Simplicity
- Prefer simple solutions over complex ones
- Avoid premature optimization
- Only add abstraction when genuinely needed

---

## Naming Conventions

### Files and Directories
- Use `snake_case` for file names: `job_extractor.py`
- Use lowercase for directory names: `src/tracker/`
- Test files mirror source: `test_job_extractor.py`

### Variables and Functions
- Descriptive names that indicate purpose
- Avoid single-letter variables (except in short loops)
- Boolean variables start with `is_`, `has_`, `can_`

### Classes and Types
- Use clear, noun-based names for classes
- Name interfaces/protocols with descriptive verbs
- Type aliases should clarify intent

---

## Code Organization

### File Structure
1. Imports (stdlib, third-party, local)
2. Constants
3. Type definitions
4. Main code (functions, classes)
5. Entry point / `if __name__ == "__main__"`

### Function Design
- Single responsibility per function
- Keep functions focused and small
- Limit parameters (3-4 max preferred)
- Return early for guard clauses

### Module Design
- One concept per module
- Clear public interface
- Internal helpers prefixed or in submodule

---

## Comments and Documentation

### When to Comment
- Explain "why", not "what"
- Document non-obvious behavior
- Add context for business logic

### When NOT to Comment
- Don't explain obvious code
- Don't leave commented-out code
- Don't add redundant docstrings

### Documentation
- README for each major component
- Inline comments for complex algorithms
- Type hints serve as documentation

---

## Error Handling

### Principles
- Fail fast and fail clearly
- Provide actionable error messages
- Log errors with context

### Patterns
- Use specific exception types
- Handle errors at appropriate level
- Don't swallow exceptions silently

---

## Testing Standards

### Test Organization
- Mirror source structure in tests
- One test file per module
- Group related tests in classes

### Test Naming
- Describe the scenario being tested
- Include expected outcome in name
- Example: `test_fingerprint_matches_when_job_id_same`

### Test Quality
- One assertion per concept
- Test edge cases explicitly
- Keep tests independent
