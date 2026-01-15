# Development Workflow — Job-Easy

> Process and methodology for development

---

## Methodology: Test-Driven Development (TDD)

### The TDD Cycle

1. **Red**: Write a failing test that defines expected behavior
2. **Green**: Write the minimum code to make the test pass
3. **Refactor**: Improve code quality while keeping tests green

### When to Use TDD

| Component | Approach |
|-----------|----------|
| Tracker (fingerprint, storage) | Full TDD |
| Extractor (schema, parsing) | Full TDD |
| Tailoring (plan, generation) | Full TDD |
| Config (loading, validation) | Full TDD |
| HITL (prompts) | TDD for logic, manual test UX |
| Runner (browser automation) | Integration/E2E tests |

### Testing Levels

- **Unit Tests**: Core logic, data transformations, utilities
- **Integration Tests**: Component interactions, database operations
- **E2E Tests**: Browser automation flows (for runner module)

---

## Commit Strategy: Conventional Commits

### Format
```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting, no logic change)
- `refactor`: Code restructuring (no behavior change)
- `test`: Adding or updating tests
- `chore`: Maintenance (dependencies, config)

### Scopes
- `tracker`: Application tracker module
- `extractor`: Job extraction module
- `tailoring`: Resume/cover letter tailoring
- `runner`: Browser automation runner
- `hitl`: Human-in-the-loop prompts
- `config`: Configuration system
- `autonomous`: Autonomous mode queue/scheduler

### Examples
```
feat(tracker): add fingerprint-based duplicate detection

fix(extractor): handle missing job ID in Greenhouse URLs

test(tailoring): add tests for keyword extraction

refactor(runner): extract site adapters to separate module

chore(deps): update browser-use to 1.2.0
```

---

## Development Process

### 1. Starting a Task

1. Claim the story in `progress-tracker.yaml`
2. Create a feature branch: `git checkout -b feat/tracker-fingerprint`
3. Read the story requirements and acceptance criteria
4. Plan the implementation (identify modules, tests needed)

### 2. Implementation (TDD Cycle)

```
For each feature unit:
  1. Write test → Run (expect fail)
  2. Write code → Run (expect pass)
  3. Refactor → Run (expect pass)
  4. Commit with conventional message
```

### 3. Completing a Task

1. Ensure all tests pass: `pytest`
2. Check code quality: `ruff check . && ruff format --check .`
3. Update `progress-tracker.yaml` (mark complete, add evidence)
4. Create PR or commit to main (per team policy)

---

## Testing Requirements

### Minimum Coverage
- New modules: 80%+ line coverage
- Critical paths: 100% coverage
- Edge cases: Explicit test for each

### Test Naming Convention
```python
def test_<unit>_<scenario>_<expected_outcome>():
    ...

# Examples:
def test_fingerprint_with_job_id_returns_stable_hash():
def test_tracker_insert_duplicate_raises_error():
def test_extractor_missing_title_returns_none():
```

### Running Tests
```bash
# All tests
pytest

# With coverage
pytest --cov=src --cov-report=term-missing

# Specific module
pytest tests/unit/tracker/

# Integration tests only
pytest tests/integration/ -m integration
```

---

## Code Review Standards

### Before Submitting
- [ ] All tests pass
- [ ] No linting errors
- [ ] Type hints on public interfaces
- [ ] Complex logic has comments explaining "why"
- [ ] No secrets or credentials in code

### Review Focus
- Does the code solve the stated problem?
- Are edge cases handled?
- Is the approach consistent with codebase patterns?
- Are tests meaningful (not just coverage)?

---

## Branch Strategy

### Naming
- Features: `feat/<short-description>`
- Fixes: `fix/<short-description>`
- Chores: `chore/<short-description>`

### Flow
1. Branch from `main`
2. Develop with atomic commits
3. Rebase on `main` before merge (if needed)
4. Squash or merge (per team preference)

---

## Definition of Done (per Story)

- [ ] Implementation complete
- [ ] Unit tests written and passing
- [ ] Integration tests (if applicable)
- [ ] Code reviewed (if team workflow)
- [ ] Documentation updated (if needed)
- [ ] `progress-tracker.yaml` updated
- [ ] Artifacts saved (logs, screenshots if relevant)

---

## Safety Requirements (Non-Negotiable)

These rules must never be violated:

1. **No auto-submit without confirmation**
   - Default: `AUTO_SUBMIT=false`
   - Must have explicit user "YES" before final submit

2. **Duplicate detection prompt**
   - Always prompt when fingerprint match found
   - Log override decisions

3. **No CAPTCHA/2FA bypass**
   - Pause and request user intervention
   - Do not implement automated solving

4. **Truthful documents only**
   - Never fabricate experience or claims
   - Tailoring = rephrasing evidence, not inventing it
