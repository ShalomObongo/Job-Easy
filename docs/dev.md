# dev.md — Multi-Agent Development Guide

> Last updated: 2026-01-15  
> This guide tells AI agents **how to start development**, **how to pick work**, and **how to coordinate safely** when multiple agents run in parallel.

This repo includes:
- `project-brief.md` — product + architecture goals
- `workflow-diagram.md` — detailed runtime flow
- `research.md` — Browser Use docs research and references
- `epics-stories.md` — epics, stories, acceptance criteria, and sprint mapping
- `sprint-status.yaml` — dependencies + concurrency guidance
- `progress-tracker.yaml` — **the single source of truth** for what is being worked on right now (locks + status)

---

## 1) Golden Rules (must follow)

1. **Never start work without claiming it in `progress-tracker.yaml`.**
2. **Respect concurrency constraints**:
   - If the sprint/story is marked as blocked or in a mutex group, do not start it.
3. **One lock per agent at a time** (unless explicitly allowed by the tracker).
4. **Default safety**:
   - No CAPTCHA/2FA bypassing.
   - No auto-submission without explicit “YES” confirmation by default.
5. **Update the tracker frequently**:
   - On start, on milestone, on blocker, on completion.

---

## 2) How to choose what to work on (the selection algorithm)

### Step A — Read the planning files
Read in this order:
1. `sprint-status.yaml` (dependencies + what can run in parallel)
2. `epics-stories.md` (stories + acceptance criteria)
3. `progress-tracker.yaml` (what is already claimed / blocked / done)

### Step B — Pick the highest-priority unclaimed story that is unblocked
A story is eligible if:
- Its sprint is **not blocked** by unmet dependencies.
- Its story ID is not already **claimed** (locked) by another agent.
- It does not violate a **mutex group** (see `progress-tracker.yaml > rules > mutex_groups`).

### Step C — Claim it (lock protocol)
You must create a lock entry in `progress-tracker.yaml` **before writing code**.

---

## 3) Locking protocol (prevents parallel collisions)

### 3.1 Lock structure
A lock is a “lease” with:
- `lock_id` (unique)
- `agent_id` (your name/identifier)
- `scope` (sprint/epic/story/hotspot)
- `scope_id` (e.g., `S4` or `E4-S3` or `core-config`)
- `acquired_at`, `expires_at` (leases expire to avoid deadlocks)
- `notes` (what you’re doing)

### 3.2 Acquire a lock
1. Open `progress-tracker.yaml`.
2. Confirm:
   - The target story is not done
   - No other active lock conflicts (same story or same mutex group)
   - All blockers for that sprint/story are marked done
3. Add your lock under `locks.active[]` and set:
   - `state: active`
   - `expires_at`: **now + 4 hours** (or shorter if task is tiny)
4. Set the story’s `status: in_progress` and `owner: <agent_id>`.

### 3.3 Renew a lock
If your work runs longer:
- Extend `expires_at` before it expires (renew).
- Add a note describing what changed.

### 3.4 Release a lock
When done:
- Move the lock from `locks.active` to `locks.history` (or set `state: released`)
- Update story status to `done` (or `in_review`)
- Record artifacts/tests/results in the story’s `evidence` fields.

### 3.5 If you see an expired lock
- If `expires_at` is in the past and the owner hasn’t updated status recently:
  - Mark the old lock as `state: expired`
  - Create a new lock for yourself
  - Add a note explaining why you took over

---

## 4) Work etiquette (multi-agent friendly)

- Prefer **small PRs**: one story per PR.
- Do not refactor unrelated modules while another agent is active in them.
- Use the tracker’s `shared_hotspots` and mutex groups to avoid conflicts.
- If you must touch a hotspot, acquire a **hotspot lock** (e.g., `core-config`, `runner-core`).

---

## 5) Recommended repo structure (agents should follow)

```
/src
  /config         # config loading + validation
  /tracker        # fingerprinting + storage + queries
  /extractor      # JD extraction + schemas
  /tailoring      # tailoring plan + resume/CL generation
  /runner         # browser automation runner + site adapters
  /hitl           # human-in-the-loop tools/prompts
  /autonomous     # queue + scheduler
  /utils          # shared helpers
/tests
  /unit
  /integration
/artifacts
  /runs
  /docs
```

---

## 6) Engineering standards (DoD per story)

Each story should include:
- Implementation
- Minimal tests (unit or integration)
- Logs / artifacts where relevant
- Updated tracker status + evidence

### Logging conventions
Per job run, generate:
- `artifacts/runs/<fingerprint>/jd.json`
- `artifacts/runs/<fingerprint>/tailoring_plan.json`
- `artifacts/runs/<fingerprint>/resume.pdf|docx`
- `artifacts/runs/<fingerprint>/cover_letter.pdf|docx`
- `artifacts/runs/<fingerprint>/proof.png` (optional)
- `artifacts/runs/<fingerprint>/run.log` (optional)

---

## 7) Safety requirements (must not regress)
- Default: **stop before final submit** and require explicit user confirmation (“YES”).
- If duplicate detected: prompt user whether to proceed; log override decision.
- CAPTCHA/2FA: prompt user; do not attempt bypass.

---

## 8) How to update `progress-tracker.yaml` correctly

Update these fields whenever they change:
- Story: `status`, `owner`, `started_at`, `updated_at`, `blocked`, `blockers`, `notes`
- Locks: add/renew/release with correct timestamps
- Sprint: overall rollups (`progress_percent`, `status`)

**If you are unsure whether work can run in parallel**:
- Check `progress-tracker.yaml > rules > mutex_groups`
- Check `sprint-status.yaml` dependencies
- If still uncertain, choose a different story that is clearly parallel-safe.

---

## 9) Suggested first tasks (on a fresh repo)

If nothing exists yet, the safest order is:
1. S0 (repo + harness)
2. S1 (tracker + fingerprinting)
3. S2 (JD extraction + scoring)
Then parallelize:
- S3 (doc gen) with S4 (runner) with S5 (browser config), coordinated through shared types.

