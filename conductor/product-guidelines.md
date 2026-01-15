# Product Guidelines — Job-Easy

> Design principles and standards for the Job-Easy application

---

## Brand Voice

### Tone: Professional
- Clear, expert, and confident communication
- Focus on helping users succeed in their job search
- Concise messaging that respects users' time
- Avoid jargon—explain technical concepts simply

### Writing Guidelines
- Use active voice ("Job-Easy found 3 matching positions" not "3 matching positions were found")
- Be direct and action-oriented
- Lead with the most important information
- Use consistent terminology throughout the application

### Example Messages
- Good: "Ready to submit your application to ExampleCo. Review your documents below."
- Avoid: "Your application is almost ready! We've worked hard to prepare everything for you."

---

## Design Principles

### 1. Efficiency First
- Minimize steps and clicks required to complete tasks
- Batch operations where possible (e.g., fill multiple form fields at once)
- Provide smart defaults based on user history and preferences
- Show progress indicators for long-running operations

### 2. Transparency
- Always show what the system is doing and why
- Display clear status indicators for each application stage
- Provide access to logs and artifacts for debugging
- Never hide important information from users

### 3. User Control
- Users can interrupt automation at any point
- Provide override options for automated decisions
- Allow customization of behaviors and thresholds
- Make it easy to review and edit generated content

### 4. Safety Gates (Non-Negotiable)
- Always require confirmation before final submission
- Prompt when duplicate applications are detected
- Request manual intervention for CAPTCHA/2FA
- Never fabricate or exaggerate claims

---

## UX Guidelines

### Primary Flow Optimization
- Streamline the happy path for common use cases
- Reduce friction in single-job mode (paste URL → review → submit)
- Batch prompts where possible to minimize interruptions
- Pre-fill forms using saved profile data

### Error Handling
- Provide clear, actionable error messages
- Offer recovery options when possible
- Log errors for debugging without overwhelming users
- Graceful degradation when site structures change

### Notifications & Prompts
- Use prompts sparingly—only for critical decisions
- Group related information in single prompts
- Provide context for why a decision is needed
- Default to safe options when prompts are dismissed

---

## Content Guidelines

### Generated Documents
- Tailored content must be truthful and evidence-based
- Highlight genuine experience matching job requirements
- Maintain professional formatting and structure
- Include versioning in filenames for traceability

### User-Facing Text
- Keep messages under 2 sentences when possible
- Use consistent capitalization and formatting
- Avoid exclamation marks and excessive enthusiasm
- Provide helpful context without being verbose

### Naming Conventions
- Artifacts: `Resume__{Company}__{Role}__{YYYY-MM-DD}.pdf`
- Logs: `artifacts/runs/{fingerprint}/run.log`
- Proof: `artifacts/runs/{fingerprint}/proof.png`

---

## Accessibility

- Ensure CLI output is screen-reader friendly
- Use clear color coding (not color-only indicators)
- Support keyboard-only navigation where applicable
- Provide text alternatives for visual elements
