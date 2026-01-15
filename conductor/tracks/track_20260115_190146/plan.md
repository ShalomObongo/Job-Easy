# Implementation Plan: Fit Scoring

> Track ID: track_20260115_190146
> Methodology: Test-Driven Development (TDD)

---

## Phase 1: Module Setup & Configuration

### [x] Task 1.1: Create module structure
- [x] Create `/src/scoring/` directory
- [x] Create `__init__.py` with placeholder exports
- [x] Create empty module files: `models.py`, `config.py`, `profile.py`, `service.py`, `matchers.py`
- [x] Create `/tests/unit/scoring/` directory with `__init__.py`
- [x] Create `/tests/integration/scoring/` directory with `__init__.py`
- [x] Create `/profiles/` directory with `.gitkeep`

### [x] Task 1.2: Implement ScoringConfig
- [x] Write tests for ScoringConfig (test_config.py)
  - [x] Test default values load correctly
  - [x] Test environment variable overrides work
  - [x] Test singleton pattern (get_scoring_config / reset_scoring_config)
  - [x] Test weight validation (should sum to ~1.0)
- [x] Implement ScoringConfig in `config.py`
  - [x] Define all config fields with defaults
  - [x] Add env_prefix="SCORING_"
  - [x] Implement singleton pattern
- [x] Update `.env.example` with new SCORING_* variables
- [x] Verify all config tests pass

### [x] Task 1.3: Conductor - User Manual Verification 'Phase 1' (Protocol in workflow.md)

---

## Phase 2: Data Models

### [x] Task 2.1: Implement WorkExperience and Education models
- [x] Write tests for WorkExperience model
  - [x] Test valid WorkExperience creation
  - [x] Test optional fields (end_date, skills_used)
  - [x] Test to_dict/from_dict serialization
- [x] Write tests for Education model
  - [x] Test valid Education creation
  - [x] Test optional graduation_year
  - [x] Test to_dict/from_dict serialization
- [x] Implement WorkExperience dataclass/Pydantic model
- [x] Implement Education dataclass/Pydantic model
- [x] Verify tests pass

### [x] Task 2.2: Implement UserProfile model
- [x] Write tests for UserProfile model
  - [x] Test valid profile with all fields
  - [x] Test profile with only required fields
  - [x] Test default values for optional fields
  - [x] Test work_type_preferences defaults to all types
  - [x] Test to_dict/from_dict serialization
  - [x] Test validation errors for missing required fields
- [x] Implement UserProfile Pydantic model
- [x] Verify tests pass

### [x] Task 2.3: Implement FitScore model
- [x] Write tests for FitScore
  - [x] Test creation with all fields
  - [x] Test score values are 0.0-1.0 range
  - [x] Test matched/missing skills lists
- [x] Implement FitScore dataclass
- [x] Verify tests pass

### [x] Task 2.4: Implement ConstraintResult model
- [x] Write tests for ConstraintResult
  - [x] Test passed=True with empty violations
  - [x] Test passed=False with violations
  - [x] Test soft warnings separate from hard violations
- [x] Implement ConstraintResult dataclass
- [x] Verify tests pass

### [x] Task 2.5: Implement FitResult model
- [x] Write tests for FitResult
  - [x] Test creation with all components
  - [x] Test recommendation values (apply/skip/review)
  - [x] Test evaluated_at default timestamp
- [x] Implement FitResult dataclass
- [x] Verify tests pass

### [x] Task 2.6: Conductor - User Manual Verification 'Phase 2' (Protocol in workflow.md)

---

## Phase 3: Skill Matching Utilities

### [x] Task 3.1: Implement skill normalization
- [x] Write tests for normalize_skill
  - [x] Test lowercase conversion
  - [x] Test whitespace stripping
  - [x] Test special character handling
- [x] Implement normalize_skill function in `matchers.py`
- [x] Verify tests pass

### [x] Task 3.2: Implement exact skill matching
- [x] Write tests for exact skill matching
  - [x] Test exact case-insensitive match
  - [x] Test common variations (JavaScript/JS, Python/Python3)
  - [x] Test no match returns False
- [x] Implement skills_match function (exact mode)
- [x] Verify tests pass

### [x] Task 3.3: Implement fuzzy skill matching
- [x] Write tests for fuzzy skill matching
  - [x] Test similar skills match above threshold
  - [x] Test dissimilar skills don't match
  - [x] Test threshold configuration
- [x] Add fuzzy matching to skills_match function
- [x] Verify tests pass

### [x] Task 3.4: Implement find_matching_skills
- [x] Write tests for find_matching_skills
  - [x] Test returns matched and missing lists
  - [x] Test with multiple skills
  - [x] Test empty lists handling
  - [x] Test with fuzzy matching enabled/disabled
- [x] Implement find_matching_skills function
- [x] Verify tests pass

### [x] Task 3.5: Conductor - User Manual Verification 'Phase 3' (Protocol in workflow.md)

---

## Phase 4: Profile Loading

### [x] Task 4.1: Create example profile template
- [x] Create `profiles/profile.example.yaml` with all fields documented
- [x] Add comments explaining each field

### [x] Task 4.2: Implement profile loading from YAML
- [x] Write tests for YAML profile loading
  - [x] Test loading valid complete profile
  - [x] Test loading minimal profile (required fields only)
  - [x] Test FileNotFoundError handling
  - [x] Test invalid YAML handling
  - [x] Test validation error handling
- [x] Implement ProfileService.load_profile for YAML
- [x] Verify tests pass

### [x] Task 4.3: Implement profile loading from JSON
- [x] Write tests for JSON profile loading
  - [x] Test loading valid JSON profile
  - [x] Test auto-detection of file format
- [x] Add JSON support to ProfileService.load_profile
- [x] Verify tests pass

### [x] Task 4.4: Implement profile validation
- [x] Write tests for validate_profile
  - [x] Test complete profile returns no warnings
  - [x] Test missing optional fields return appropriate warnings
  - [x] Test empty skills list warning
- [x] Implement ProfileService.validate_profile
- [x] Verify tests pass

### [x] Task 4.5: Conductor - User Manual Verification 'Phase 4' (Protocol in workflow.md)

---

## Phase 5: Scoring Algorithm

### [x] Task 5.1: Implement must-have skills scoring
- [x] Write tests for score_skills (must-have)
  - [x] Test 100% match returns 1.0
  - [x] Test 50% match returns 0.5
  - [x] Test 0% match returns 0.0
  - [x] Test returns correct matched/missing lists
  - [x] Test with empty required_skills (should return 1.0)
- [x] Implement score_skills for must-have skills
- [x] Verify tests pass

### [x] Task 5.2: Implement preferred skills scoring
- [x] Write tests for preferred skills scoring
  - [x] Test scoring for preferred_skills list
  - [x] Test empty preferred_skills returns 1.0
- [x] Add preferred skills to score_skills return
- [x] Verify tests pass

### [x] Task 5.3: Implement experience scoring
- [x] Write tests for score_experience
  - [x] Test profile within JD range returns 1.0
  - [x] Test profile below min by 1 year returns partial score
  - [x] Test profile above max by 1 year returns partial score
  - [x] Test profile way outside range returns 0.0
  - [x] Test JD with no experience requirement returns 1.0
  - [x] Test returns reasoning string
- [x] Implement score_experience
- [x] Verify tests pass

### [x] Task 5.4: Implement education scoring
- [x] Write tests for score_education
  - [x] Test profile meets requirement returns 1.0
  - [x] Test profile exceeds requirement returns 1.0
  - [x] Test profile one level below returns partial score
  - [x] Test profile way below returns 0.0
  - [x] Test JD with no education requirement returns 1.0
  - [x] Test returns reasoning string
- [x] Implement score_education
- [x] Verify tests pass

### [x] Task 5.5: Implement weighted fit score calculation
- [x] Write tests for calculate_fit_score
  - [x] Test weighted sum calculation
  - [x] Test with perfect scores returns 1.0
  - [x] Test with mixed scores returns weighted average
  - [x] Test FitScore object has all fields populated
- [x] Implement calculate_fit_score
- [x] Verify tests pass

### [x] Task 5.6: Conductor - User Manual Verification 'Phase 5' (Protocol in workflow.md)

---

## Phase 6: Constraint Checking

### [x] Task 6.1: Implement location/work_type constraint
- [x] Write tests for location constraint
  - [x] Test remote job always passes
  - [x] Test onsite job with matching location passes
  - [x] Test onsite job with non-matching location fails (strict mode)
  - [x] Test onsite job with non-matching location warns (non-strict mode)
  - [x] Test hybrid job handling
  - [x] Test target_locations=None accepts all
- [x] Implement location constraint in check_constraints
- [x] Verify tests pass

### [x] Task 6.2: Implement visa constraint
- [x] Write tests for visa constraint
  - [x] Test profile not needing sponsorship always passes
  - [x] Test profile needing sponsorship with sponsoring job passes
  - [x] Test profile needing sponsorship with non-sponsoring job fails (strict)
  - [x] Test visa keyword detection in job description
- [x] Implement visa constraint in check_constraints
- [x] Verify tests pass

### [x] Task 6.3: Implement experience constraint
- [x] Write tests for experience constraint
  - [x] Test profile within range passes
  - [x] Test profile within tolerance passes
  - [x] Test profile outside tolerance fails
  - [x] Test JD with no experience requirement passes
- [x] Implement experience constraint in check_constraints
- [x] Verify tests pass

### [x] Task 6.4: Implement salary constraint
- [x] Write tests for salary constraint
  - [x] Test JD salary >= profile min passes
  - [x] Test JD salary < profile min fails (strict)
  - [x] Test JD with no salary info passes
  - [x] Test profile with no min salary passes
- [x] Implement salary constraint in check_constraints
- [x] Verify tests pass

### [x] Task 6.5: Implement combined constraint checking
- [x] Write tests for full check_constraints
  - [x] Test all constraints passing returns passed=True
  - [x] Test one hard violation returns passed=False
  - [x] Test soft warnings with passed=True
  - [x] Test multiple violations accumulated
- [x] Combine all constraints in check_constraints method
- [x] Verify tests pass

### [x] Task 6.6: Conductor - User Manual Verification 'Phase 6' (Protocol in workflow.md)

---

## Phase 7: Evaluation & Recommendation

### [x] Task 7.1: Implement recommendation logic
- [x] Write tests for recommendation determination
  - [x] Test score >= threshold AND passed constraints -> "apply"
  - [x] Test score < threshold -> "skip"
  - [x] Test constraint violations -> "skip"
  - [x] Test score within review margin -> "review"
- [x] Implement recommendation logic in evaluate method
- [x] Verify tests pass

### [x] Task 7.2: Implement full evaluate method
- [x] Write tests for evaluate
  - [x] Test returns complete FitResult
  - [x] Test reasoning string is informative
  - [x] Test all components populated correctly
- [x] Implement FitScoringService.evaluate
- [x] Verify tests pass

### [x] Task 7.3: Implement format_result
- [x] Write tests for format_result
  - [x] Test output includes score
  - [x] Test output includes recommendation
  - [x] Test output includes skill matches/gaps
  - [x] Test output includes constraint issues
- [x] Implement format_result for CLI output
- [x] Verify tests pass

### [x] Task 7.4: Conductor - User Manual Verification 'Phase 7' (Protocol in workflow.md)

---

## Phase 8: Integration & Public API

### [x] Task 8.1: Export public API
- [x] Update `__init__.py` with all public exports
  - [x] FitScoringService
  - [x] ProfileService
  - [x] UserProfile, WorkExperience, Education
  - [x] FitScore, ConstraintResult, FitResult
  - [x] ScoringConfig, get_scoring_config, reset_scoring_config
- [x] Verify imports work correctly

### [x] Task 8.2: Integration test with JobDescription
- [x] Write integration test
  - [x] Load sample profile from YAML
  - [x] Create JobDescription with realistic data
  - [x] Run full evaluation
  - [x] Verify complete FitResult returned
  - [x] Test with apply recommendation case
  - [x] Test with skip recommendation case
- [x] Verify integration test passes

### [x] Task 8.3: Create sample profiles
- [x] Create `profiles/profile.example.yaml` with comprehensive example
- [x] Add comments documenting each field
- [x] Validate example loads correctly

### [x] Task 8.4: Update project documentation
- [x] Add SCORING_* variables to `.env.example`
- [x] Update README if needed

### [x] Task 8.5: Run full test suite
- [x] Run `pytest tests/unit/scoring/` - all pass
- [x] Run `pytest tests/integration/scoring/` - all pass
- [x] Run `pytest --cov=src/scoring` - verify 80%+ coverage
- [x] Run `ruff check src/scoring` - no errors
- [x] Run `ruff format --check src/scoring` - properly formatted

### [x] Task 8.6: Conductor - User Manual Verification 'Phase 8' (Protocol in workflow.md)

---

## Summary

| Phase | Description | Tasks |
|-------|-------------|-------|
| 1 | Module Setup & Configuration | 3 |
| 2 | Data Models | 6 |
| 3 | Skill Matching Utilities | 5 |
| 4 | Profile Loading | 5 |
| 5 | Scoring Algorithm | 6 |
| 6 | Constraint Checking | 6 |
| 7 | Evaluation & Recommendation | 4 |
| 8 | Integration & Public API | 6 |
| **Total** | | **41 tasks** |

---

## Definition of Done

- [x] All unit tests pass
- [x] All integration tests pass
- [x] Code coverage >= 80%
- [x] No ruff linting errors
- [x] Code properly formatted
- [x] Public API exported in `__init__.py`
- [x] Example profile created
- [x] `.env.example` updated
