# Implementation Plan: Fit Scoring

> Track ID: track_20260115_190146
> Methodology: Test-Driven Development (TDD)

---

## Phase 1: Module Setup & Configuration

### [ ] Task 1.1: Create module structure
- [ ] Create `/src/scoring/` directory
- [ ] Create `__init__.py` with placeholder exports
- [ ] Create empty module files: `models.py`, `config.py`, `profile.py`, `service.py`, `matchers.py`
- [ ] Create `/tests/unit/scoring/` directory with `__init__.py`
- [ ] Create `/tests/integration/scoring/` directory with `__init__.py`
- [ ] Create `/profiles/` directory with `.gitkeep`

### [ ] Task 1.2: Implement ScoringConfig
- [ ] Write tests for ScoringConfig (test_config.py)
  - [ ] Test default values load correctly
  - [ ] Test environment variable overrides work
  - [ ] Test singleton pattern (get_scoring_config / reset_scoring_config)
  - [ ] Test weight validation (should sum to ~1.0)
- [ ] Implement ScoringConfig in `config.py`
  - [ ] Define all config fields with defaults
  - [ ] Add env_prefix="SCORING_"
  - [ ] Implement singleton pattern
- [ ] Update `.env.example` with new SCORING_* variables
- [ ] Verify all config tests pass

### [ ] Task 1.3: Conductor - User Manual Verification 'Phase 1' (Protocol in workflow.md)

---

## Phase 2: Data Models

### [ ] Task 2.1: Implement WorkExperience and Education models
- [ ] Write tests for WorkExperience model
  - [ ] Test valid WorkExperience creation
  - [ ] Test optional fields (end_date, skills_used)
  - [ ] Test to_dict/from_dict serialization
- [ ] Write tests for Education model
  - [ ] Test valid Education creation
  - [ ] Test optional graduation_year
  - [ ] Test to_dict/from_dict serialization
- [ ] Implement WorkExperience dataclass/Pydantic model
- [ ] Implement Education dataclass/Pydantic model
- [ ] Verify tests pass

### [ ] Task 2.2: Implement UserProfile model
- [ ] Write tests for UserProfile model
  - [ ] Test valid profile with all fields
  - [ ] Test profile with only required fields
  - [ ] Test default values for optional fields
  - [ ] Test work_type_preferences defaults to all types
  - [ ] Test to_dict/from_dict serialization
  - [ ] Test validation errors for missing required fields
- [ ] Implement UserProfile Pydantic model
- [ ] Verify tests pass

### [ ] Task 2.3: Implement FitScore model
- [ ] Write tests for FitScore
  - [ ] Test creation with all fields
  - [ ] Test score values are 0.0-1.0 range
  - [ ] Test matched/missing skills lists
- [ ] Implement FitScore dataclass
- [ ] Verify tests pass

### [ ] Task 2.4: Implement ConstraintResult model
- [ ] Write tests for ConstraintResult
  - [ ] Test passed=True with empty violations
  - [ ] Test passed=False with violations
  - [ ] Test soft warnings separate from hard violations
- [ ] Implement ConstraintResult dataclass
- [ ] Verify tests pass

### [ ] Task 2.5: Implement FitResult model
- [ ] Write tests for FitResult
  - [ ] Test creation with all components
  - [ ] Test recommendation values (apply/skip/review)
  - [ ] Test evaluated_at default timestamp
- [ ] Implement FitResult dataclass
- [ ] Verify tests pass

### [ ] Task 2.6: Conductor - User Manual Verification 'Phase 2' (Protocol in workflow.md)

---

## Phase 3: Skill Matching Utilities

### [ ] Task 3.1: Implement skill normalization
- [ ] Write tests for normalize_skill
  - [ ] Test lowercase conversion
  - [ ] Test whitespace stripping
  - [ ] Test special character handling
- [ ] Implement normalize_skill function in `matchers.py`
- [ ] Verify tests pass

### [ ] Task 3.2: Implement exact skill matching
- [ ] Write tests for exact skill matching
  - [ ] Test exact case-insensitive match
  - [ ] Test common variations (JavaScript/JS, Python/Python3)
  - [ ] Test no match returns False
- [ ] Implement skills_match function (exact mode)
- [ ] Verify tests pass

### [ ] Task 3.3: Implement fuzzy skill matching
- [ ] Write tests for fuzzy skill matching
  - [ ] Test similar skills match above threshold
  - [ ] Test dissimilar skills don't match
  - [ ] Test threshold configuration
- [ ] Add fuzzy matching to skills_match function
- [ ] Verify tests pass

### [ ] Task 3.4: Implement find_matching_skills
- [ ] Write tests for find_matching_skills
  - [ ] Test returns matched and missing lists
  - [ ] Test with multiple skills
  - [ ] Test empty lists handling
  - [ ] Test with fuzzy matching enabled/disabled
- [ ] Implement find_matching_skills function
- [ ] Verify tests pass

### [ ] Task 3.5: Conductor - User Manual Verification 'Phase 3' (Protocol in workflow.md)

---

## Phase 4: Profile Loading

### [ ] Task 4.1: Create example profile template
- [ ] Create `profiles/profile.example.yaml` with all fields documented
- [ ] Add comments explaining each field

### [ ] Task 4.2: Implement profile loading from YAML
- [ ] Write tests for YAML profile loading
  - [ ] Test loading valid complete profile
  - [ ] Test loading minimal profile (required fields only)
  - [ ] Test FileNotFoundError handling
  - [ ] Test invalid YAML handling
  - [ ] Test validation error handling
- [ ] Implement ProfileService.load_profile for YAML
- [ ] Verify tests pass

### [ ] Task 4.3: Implement profile loading from JSON
- [ ] Write tests for JSON profile loading
  - [ ] Test loading valid JSON profile
  - [ ] Test auto-detection of file format
- [ ] Add JSON support to ProfileService.load_profile
- [ ] Verify tests pass

### [ ] Task 4.4: Implement profile validation
- [ ] Write tests for validate_profile
  - [ ] Test complete profile returns no warnings
  - [ ] Test missing optional fields return appropriate warnings
  - [ ] Test empty skills list warning
- [ ] Implement ProfileService.validate_profile
- [ ] Verify tests pass

### [ ] Task 4.5: Conductor - User Manual Verification 'Phase 4' (Protocol in workflow.md)

---

## Phase 5: Scoring Algorithm

### [ ] Task 5.1: Implement must-have skills scoring
- [ ] Write tests for score_skills (must-have)
  - [ ] Test 100% match returns 1.0
  - [ ] Test 50% match returns 0.5
  - [ ] Test 0% match returns 0.0
  - [ ] Test returns correct matched/missing lists
  - [ ] Test with empty required_skills (should return 1.0)
- [ ] Implement score_skills for must-have skills
- [ ] Verify tests pass

### [ ] Task 5.2: Implement preferred skills scoring
- [ ] Write tests for preferred skills scoring
  - [ ] Test scoring for preferred_skills list
  - [ ] Test empty preferred_skills returns 1.0
- [ ] Add preferred skills to score_skills return
- [ ] Verify tests pass

### [ ] Task 5.3: Implement experience scoring
- [ ] Write tests for score_experience
  - [ ] Test profile within JD range returns 1.0
  - [ ] Test profile below min by 1 year returns partial score
  - [ ] Test profile above max by 1 year returns partial score
  - [ ] Test profile way outside range returns 0.0
  - [ ] Test JD with no experience requirement returns 1.0
  - [ ] Test returns reasoning string
- [ ] Implement score_experience
- [ ] Verify tests pass

### [ ] Task 5.4: Implement education scoring
- [ ] Write tests for score_education
  - [ ] Test profile meets requirement returns 1.0
  - [ ] Test profile exceeds requirement returns 1.0
  - [ ] Test profile one level below returns partial score
  - [ ] Test profile way below returns 0.0
  - [ ] Test JD with no education requirement returns 1.0
  - [ ] Test returns reasoning string
- [ ] Implement score_education
- [ ] Verify tests pass

### [ ] Task 5.5: Implement weighted fit score calculation
- [ ] Write tests for calculate_fit_score
  - [ ] Test weighted sum calculation
  - [ ] Test with perfect scores returns 1.0
  - [ ] Test with mixed scores returns weighted average
  - [ ] Test FitScore object has all fields populated
- [ ] Implement calculate_fit_score
- [ ] Verify tests pass

### [ ] Task 5.6: Conductor - User Manual Verification 'Phase 5' (Protocol in workflow.md)

---

## Phase 6: Constraint Checking

### [ ] Task 6.1: Implement location/work_type constraint
- [ ] Write tests for location constraint
  - [ ] Test remote job always passes
  - [ ] Test onsite job with matching location passes
  - [ ] Test onsite job with non-matching location fails (strict mode)
  - [ ] Test onsite job with non-matching location warns (non-strict mode)
  - [ ] Test hybrid job handling
  - [ ] Test target_locations=None accepts all
- [ ] Implement location constraint in check_constraints
- [ ] Verify tests pass

### [ ] Task 6.2: Implement visa constraint
- [ ] Write tests for visa constraint
  - [ ] Test profile not needing sponsorship always passes
  - [ ] Test profile needing sponsorship with sponsoring job passes
  - [ ] Test profile needing sponsorship with non-sponsoring job fails (strict)
  - [ ] Test visa keyword detection in job description
- [ ] Implement visa constraint in check_constraints
- [ ] Verify tests pass

### [ ] Task 6.3: Implement experience constraint
- [ ] Write tests for experience constraint
  - [ ] Test profile within range passes
  - [ ] Test profile within tolerance passes
  - [ ] Test profile outside tolerance fails
  - [ ] Test JD with no experience requirement passes
- [ ] Implement experience constraint in check_constraints
- [ ] Verify tests pass

### [ ] Task 6.4: Implement salary constraint
- [ ] Write tests for salary constraint
  - [ ] Test JD salary >= profile min passes
  - [ ] Test JD salary < profile min fails (strict)
  - [ ] Test JD with no salary info passes
  - [ ] Test profile with no min salary passes
- [ ] Implement salary constraint in check_constraints
- [ ] Verify tests pass

### [ ] Task 6.5: Implement combined constraint checking
- [ ] Write tests for full check_constraints
  - [ ] Test all constraints passing returns passed=True
  - [ ] Test one hard violation returns passed=False
  - [ ] Test soft warnings with passed=True
  - [ ] Test multiple violations accumulated
- [ ] Combine all constraints in check_constraints method
- [ ] Verify tests pass

### [ ] Task 6.6: Conductor - User Manual Verification 'Phase 6' (Protocol in workflow.md)

---

## Phase 7: Evaluation & Recommendation

### [ ] Task 7.1: Implement recommendation logic
- [ ] Write tests for recommendation determination
  - [ ] Test score >= threshold AND passed constraints -> "apply"
  - [ ] Test score < threshold -> "skip"
  - [ ] Test constraint violations -> "skip"
  - [ ] Test score within review margin -> "review"
- [ ] Implement recommendation logic in evaluate method
- [ ] Verify tests pass

### [ ] Task 7.2: Implement full evaluate method
- [ ] Write tests for evaluate
  - [ ] Test returns complete FitResult
  - [ ] Test reasoning string is informative
  - [ ] Test all components populated correctly
- [ ] Implement FitScoringService.evaluate
- [ ] Verify tests pass

### [ ] Task 7.3: Implement format_result
- [ ] Write tests for format_result
  - [ ] Test output includes score
  - [ ] Test output includes recommendation
  - [ ] Test output includes skill matches/gaps
  - [ ] Test output includes constraint issues
- [ ] Implement format_result for CLI output
- [ ] Verify tests pass

### [ ] Task 7.4: Conductor - User Manual Verification 'Phase 7' (Protocol in workflow.md)

---

## Phase 8: Integration & Public API

### [ ] Task 8.1: Export public API
- [ ] Update `__init__.py` with all public exports
  - [ ] FitScoringService
  - [ ] ProfileService
  - [ ] UserProfile, WorkExperience, Education
  - [ ] FitScore, ConstraintResult, FitResult
  - [ ] ScoringConfig, get_scoring_config, reset_scoring_config
- [ ] Verify imports work correctly

### [ ] Task 8.2: Integration test with JobDescription
- [ ] Write integration test
  - [ ] Load sample profile from YAML
  - [ ] Create JobDescription with realistic data
  - [ ] Run full evaluation
  - [ ] Verify complete FitResult returned
  - [ ] Test with apply recommendation case
  - [ ] Test with skip recommendation case
- [ ] Verify integration test passes

### [ ] Task 8.3: Create sample profiles
- [ ] Create `profiles/profile.example.yaml` with comprehensive example
- [ ] Add comments documenting each field
- [ ] Validate example loads correctly

### [ ] Task 8.4: Update project documentation
- [ ] Add SCORING_* variables to `.env.example`
- [ ] Update README if needed

### [ ] Task 8.5: Run full test suite
- [ ] Run `pytest tests/unit/scoring/` - all pass
- [ ] Run `pytest tests/integration/scoring/` - all pass
- [ ] Run `pytest --cov=src/scoring` - verify 80%+ coverage
- [ ] Run `ruff check src/scoring` - no errors
- [ ] Run `ruff format --check src/scoring` - properly formatted

### [ ] Task 8.6: Conductor - User Manual Verification 'Phase 8' (Protocol in workflow.md)

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

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Code coverage >= 80%
- [ ] No ruff linting errors
- [ ] Code properly formatted
- [ ] Public API exported in `__init__.py`
- [ ] Example profile created
- [ ] `.env.example` updated
