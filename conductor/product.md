# Product Guide — Job-Easy

> A Browser Use-powered job application automation system

---

## Overview

Job-Easy is an end-to-end job application assistant that helps users apply to jobs efficiently by:
- Extracting job descriptions and metadata from job postings
- Tailoring resumes and generating cover letters based on job requirements
- Completing applications in the browser with human oversight
- Preventing duplicate applications through intelligent tracking
- Providing human-in-the-loop checkpoints for safety and accuracy

The system operates in two modes:
1. **Autonomous Mode**: Continuously collects job leads, deduplicates, ranks, and processes applications on a schedule
2. **Single-Job Mode**: User provides a specific job URL and the system runs a single application attempt

---

## Target Users

### Primary User: Job Seeker
- Wants fast, targeted applications with minimal errors
- Values quality over quantity in job applications
- Appreciates automation that doesn't sacrifice personalization
- Needs transparency and control over the application process

### Secondary User: Power User
- Comfortable configuring domains, schedules, and custom prompts
- May run autonomous mode with custom lead sources
- Wants detailed logging and audit capabilities

---

## Core Features

### 1. Job Extraction
- Open job URL in controlled browser session
- Extract job description, company, role, location, requirements
- Output structured JSON for downstream processing

### 2. Fit Scoring
- Match must-have requirements against user profile
- Check constraints (location, visa, seniority)
- Decide apply/skip based on configurable thresholds

### 3. Resume & Cover Letter Tailoring
- Generate keyword map from job description
- Map evidence from user's experience to requirements
- Produce tailored resume + cover letter (PDF/DOCX)
- Maintain truthfulness—no fabricated claims

### 4. Application Execution
- Navigate job portal forms
- Fill fields using applicant profile and Q&A bank
- Upload tailored documents
- Handle common form patterns across job boards

### 5. Human-in-the-Loop Checkpoints
- Document review before upload
- Confirmation before final submission
- Duplicate detection prompts
- CAPTCHA/2FA manual intervention requests

### 6. Application Tracker
- Prevent duplicate applications via fingerprinting
- Log all application attempts with artifacts
- Capture proof of submission (screenshots, confirmation IDs)

---

## Product Goals

1. **Reduce time per application** without sacrificing quality
2. **Tailor documents** per job description using a reproducible pipeline
3. **Avoid duplicate applications** by maintaining a robust application log
4. **Operate safely** with human-in-the-loop gates for critical actions
5. **Maintain audit trail** for compliance and troubleshooting

---

## Success Metrics

- 90%+ duplicate detection accuracy (fingerprint match)
- Tailored resume/cover letter generated for every "apply" job
- 80%+ form completion rate without manual intervention (excluding CAPTCHA/2FA)
- 100% of submissions require positive user confirmation
- Complete proof artifacts (confirmation text and/or screenshot) for every submission

---

## Non-Goals (v1)

- Bypassing anti-bot systems (CAPTCHA solving, stealth automation)
- Mass "spray and pray" submissions at scale
- Automatic claims fabrication or experience invention
