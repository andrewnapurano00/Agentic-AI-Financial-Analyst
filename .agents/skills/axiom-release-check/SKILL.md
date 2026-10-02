---
name: axiom-release-check
description: "Run scoped Axiom pre-release or handoff verification, checking tests, imports, Streamlit health, workflows, and documentation."
---

# Axiom Release Checks

Produce an evidence-based handoff for the current change. Running this skill verifies readiness; it does not authorize commits, publishing, deployment, or unrelated fixes.

Read the repository AGENTS.md. Read [verification-commands.md](references/verification-commands.md) when running checks.

## Scope the verification

Inspect staged, unstaged, and relevant untracked changes; preserve work that belongs to another task. Match checks to the changed behavior and affected consumers. Record failing baseline checks separately from introduced failures.

Use the configured Python environment. This is a src-layout package supporting Python 3.11/3.12; a shell's default python may lack dependencies. Check interpreter identity and imports before diagnosing a project failure.

## Run applicable checks

- Focused offline tests for modified calculations, normalization, adapters, agent validation, state, or exports.
- Full offline suite for shared infrastructure or routing changes, or when the user requests broad release verification.
- Compile/import affected Python modules; keep import checks distinct from a healthy full-app startup.
- For app-level changes, start or reuse a matching Streamlit instance and check /_stcore/health. A health response alone does not prove that pages render.
- Exercise the changed workflow with mocked providers/models and, when available, an actual browser. Verify completed-work preservation and paid-call counts for reruns/navigation/downloads.
- Inspect relevant PDF/Excel/CSV/JSON artifacts when exports changed.
- Check documentation against actual navigation, key names, provider behavior, workflow, and model-call gates. Update README.md for changed workflows; update PLAN.md only for completed/rescoped milestones.
- Inspect changes for credentials, unsafe URL/HTML handling, debug artifacts, and accidental unrelated edits without printing real secrets.

Tests must not consume paid credits. App startup loads .env, so even a local browser visit can cause live provider calls; use a mocked harness or explicit live-smoke scope as appropriate. Do not claim an offline run when provider access was live.

## Report readiness

Provide a compact check/result table with commands or test scope and the outcome. Identify any failure by its concrete user impact. State tests not run, browser/provider limits, remaining risks, and whether the requested acceptance criteria were met.

A missing runtime or browser is an unverified check, not a pass. For a review-only task, leave application files unchanged and report findings. If fixes are requested, make focused repairs and repeat affected checks.
