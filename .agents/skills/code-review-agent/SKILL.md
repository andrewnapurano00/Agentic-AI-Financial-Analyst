---
name: code-review-agent
description: Spawn an independent code review subagent on explicit invocation and save its findings to a uniquely named Markdown report in docs/reviews/ in the reviewed repository. Use when the user calls this review agent; do not invoke automatically during implementation.
---

# Code Review Agent

When invoked, spawn one independent reviewer using the available collaboration spawn tool. The parent coordinates the review and writes the report; the reviewer does not modify project files. Invocation authorizes this delegation and writing the report, not code fixes or commits.

## Scope and delegation

- Resolve the current repository root and read applicable AGENTS.md instructions. Respect the user's requested files, branch, or baseline. Default to all staged, unstaged, and relevant untracked changes relative to HEAD.
- Inspect status and the requested diff to establish scope. Exclude docs/reviews/ reports and legacy Review.md files, secrets, dependencies, caches, and generated output from review inputs. Do not print secret contents.
- Spawn with minimal fresh context (for example, fork_turns="none"). Give the reviewer the absolute repository path, scope/baseline, applicable project requirements, and the review instructions below. Do not seed it with the parent's suspected findings or implementation conclusions.
- If no local changes exist, report that there are no changes to review; do not silently switch to a whole-repository audit. An explicitly requested wider review still proceeds.
- If delegation is unavailable, disclose that the independent agent could not be spawned. Do not claim an independent review occurred; record the limitation in the report.

## Instructions to pass to the reviewer

Review the complete requested change set and relevant surrounding code independently. Inspect staged and unstaged diffs separately and read relevant untracked files. Follow applicable repository instructions. Preserve all existing work: do not edit, stage, commit, reset, or publish files, and do not spawn further agents.

Prioritize concrete correctness regressions, security/privacy defects, data loss, recovery failures, compatibility and performance problems, and missing tests with a realistic failure path. For financial research code, check period/currency alignment, missing versus zero values, provenance, bounded provider calls, secret handling, and whether ordinary UI reruns can trigger paid calls. Distinguish newly introduced issues from pre-existing issues. Avoid style-only or speculative findings.

Use focused offline checks only when useful and allowed; never consume paid API credits or call live providers during verification. Return findings ordered by severity, each with file and specific line, concrete trigger and consequence, evidence, and the smallest correction direction. State what checks ran and their results, what was inspected only, and what remains unverified. If no actionable findings exist, say so explicitly without implying the code is proven defect-free.

## Write the report

Wait for the reviewer to finish, then write a UTF-8 Markdown report under `docs/reviews/` relative to the repository root unless the user specified another output path. Create the folder if needed. Name it `YYYY-MM-DD-<task-slug>.md`, using the review date in the user's timezone and a concise lowercase, hyphen-separated description of the requested task or actual reviewed changes; for example, `2026-10-02-deep-research-v2-recovery.md`. If that filename exists, append `-2`, `-3`, and so on before `.md` until the filename is unused. Never overwrite or append to an existing report unless explicitly requested. Preserve the reviewer's conclusions and uncertainty. Verify cited paths/lines where practical; do not invent results or downgrade findings without evidence.

The report must include:

1. Review date with timezone, repository, baseline commit, and reviewed scope.
2. A brief outcome and findings ordered by Critical, High, Medium, Low. Each finding includes a file/line reference, failure scenario, impact, and recommended correction.
3. Verification performed with commands/results and explicit limitations, including live services or interactions not exercised.
4. Any scope gaps or changes that arrived during the review. Recheck status before writing so concurrent edits are not silently treated as reviewed.

When no actionable issues were found, write that plainly. Modify only the report; fixes require a separate user request. End with a concise outcome and a clickable link to the report.
