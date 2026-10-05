---
name: code-review-team
description: On explicit invocation, coordinate three subagents to review scoped Axiom code, summarize and prioritize findings, and create up to six highest-priority Jira tickets with a saved review report. Supports dry runs without Jira writes; do not invoke automatically during implementation.
---

# Code Review Team

## Jira connection handling

Prefer Jira/Atlassian MCP. Before delegating publication, the coordinator checks the current tool catalog and uses tool discovery when available, recording the connection/tool names for the writer. The writer checks its own tool access; when only the coordinator has MCP tools, the coordinator may execute the writer's verified payloads under the existing duplicate checks, ledger, and run-wide attempt cap. This does not authorize unrelated writes.

Diagnose missing tools separately from missing configuration, authentication failure, and project permission failure. For local Codex, `codex mcp list` can check configured connections without printing credentials. Empty MCP resource lists do not prove missing Jira tools. If configured MCP tools are not loaded, report the need to reload the client/session and preserve drafts rather than sending the user to another browser login. Browser fallback requires the user's request or acceptance after MCP is confirmed unusable. Never request secrets in chat or inspect credential stores.

The parent coordinates three distinct subagents in order: reviewer, summarizer, and Jira writer. Each stage depends on the previous stage's completed output; do not run them concurrently against incomplete findings. Keep the existing single-reviewer skill separate.

Explicit invocation authorizes this delegation, local report creation, and creation of the selected Jira issues. A request to create or edit this skill does not invoke it or authorize an actual review run. `dry run`, `drafts only`, or `do not create tickets` overrides Jira-write authorization. Do not fix implementation files, commit, push, change existing Jira issues, or send other messages.

## Coordinator: establish the run

- Resolve the repository root and applicable AGENTS.md files. Respect a requested folder, file, feature, commit, or branch. Default to staged, unstaged, and relevant untracked changes against HEAD. Include unchanged code only when explicitly requested as an audit or when necessary to understand changed code.
- Record the baseline commit, requested scope, relevant file contents/diffs, and initial worktree status. Exclude secrets, dependencies, caches, generated output, `docs/reviews/`, and legacy `Review.md` from review inputs.
- Default destination: `https://bigmeatpete717.atlassian.net`, project `AAFA`. Honor an explicitly supplied alternative site/project; never silently redirect ticket creation elsewhere.
- Set a run-wide maximum of six issue-creation attempts, lowered if the user requests fewer. Do not aim for a minimum ticket count; zero findings means zero tickets. Include any attempts with uncertain outcomes in this budget.
- Reserve an unused report path: `docs/reviews/YYYY-MM-DD-<task-slug>-team.md`, using the user's timezone, lowercase hyphen-separated task scope, and `-2`, `-3`, etc. on collisions. Record the run ID as this report's filename stem. Never overwrite earlier reports.
- Spawn each role with fresh context (`fork_turns="none"`), absolute repository path, applicable instructions, permitted operations, and required input/output below. All roles preserve existing implementation files and do not spawn additional agents.
- If delegation is unavailable, save a limitation report and ticket drafts if supported by evidence; do not claim a three-agent review occurred or publish unreviewed findings.

## Agent 1: independent code reviewer

Give this agent the scope, baseline, source snapshot/diff, and project requirements, without seeding suspected findings. It may read relevant code and run useful focused offline checks with the project's installed Python environment. No live providers, paid API calls, Jira mutations, or source edits.

Inspect staged/unstaged changes separately, relevant untracked files, and interactions with surrounding code. Prioritize correctness, financial period/currency alignment, missing versus zero values, provenance, security/privacy, data loss, failure recovery, bounded calls, paid calls during reruns, and realistic missing regression coverage. Distinguish introduced defects from pre-existing issues; in an explicit audit, pre-existing defects within scope are eligible and must be labeled. Exclude style-only preferences and speculative claims.

Return a structured findings list with stable IDs (`F01`, `F02`, ...). Each finding includes:

- severity (`Critical`, `High`, `Medium`, `Low`), short title, file and specific line;
- concrete trigger, user impact, observed evidence, and observed versus inferred status;
- smallest correction direction, proposed acceptance criteria, and regression-check suggestion;
- introduced versus pre-existing classification and confidence/verification limitations.

Also return checks actually performed (commands/results), inspection-only areas, and unverified interactions. Explicitly state when no actionable findings exist.

## Agent 2: summarizer and prioritizer

Give this agent the reviewer's full findings, scope, baseline, evidence, and verification limits. This is an editorial/evidence pass, not a second implementation agent. It may inspect cited source to verify claims but must not invent a reproduction, test result, severity, or new unsupported defect.

- Verify file/line references and concrete impact. Preserve uncertainty and unresolved findings in the report; keep unsupported or disputed findings out of the ticket queue and explain why.
- Merge findings that share one root cause into a single actionable item, retaining original finding IDs. Keep independent fixes separate.
- Rank by severity first, then concrete impact and evidence confidence. Prioritize financial correctness, security, and data loss over convenience. Do not inflate priority to fill the budget.
- Produce a concise executive summary, all retained findings, excluded/merged findings with reasons, and a ranked candidate queue. Initially select at most six within the configured cap; retain a ranked reserve list so duplicates can be skipped without dropping higher-priority remaining work.
- For each candidate, draft an actionable title, description, severity/rationale, affected paths and baseline, trigger/reproduction or inspection evidence, user impact, smallest proposed fix, acceptance criteria, offline test recommendation, finding IDs, and run ID. Label proposed checks as proposed. Describe inferred risks as inferred.

## Coordinator: save evidence before publication

Write the UTF-8 report before the Jira writer starts. Include date/timezone, task, scope, baseline, executive summary, all findings and exclusions, actual verification and limitations, and the ordered ticket drafts. Reserve a Jira-results section for the writer's outcomes. Do not include credentials or raw secret-bearing errors in drafts or reports.

Recheck the scoped file contents/diffs against the original snapshot. If reviewed source changed during the run, retain the historical report but stop publication of affected findings until the reviewer and summarizer revalidate them. Save refreshed evidence and drafts in a clearly dated report update, withdraw any invalidated candidates, and compare source against the revalidated snapshot again before resuming affected publication. Unrelated concurrent changes must not expand the scope.

## Agent 3: Jira writer

Give only this agent write authority to the specified Jira project. Pass the completed report, ranked candidate queue/reserves, evidence, run ID, explicit dry-run state, and remaining run-wide attempt budget. It may read Jira and create selected issues; it may not change existing issues, transition statuses, assign users, create epics/subtasks, or alter implementation files.

1. In dry-run mode, return the selected drafts as `draft-only` without Jira mutations. Otherwise use authenticated Jira MCP tools following the connection handling above. Use the browser only under the fallback conditions above and after reading the `agent-browser` skill's current CLI workflow. Confirm the intended site/project, create permission, supported issue types, and priority values from live metadata/UI before writing; do not assume internal IDs or priority names.
2. If authentication, project access, required-field metadata, or tooling is unavailable, return `blocked` with the reason and preserved drafts. Request only the missing access/input when necessary. Never request credentials in chat or claim authentication from a historical issue link.
3. Search the target project for existing matching issues before each create, including closed issues and earlier attempts from this run. Compare root cause, component, symptom, and proposed fix; title similarity alone is insufficient. Record a matching issue as `duplicate-skipped` with its key/URL and do not modify it. Do not automatically recreate a resolved issue; report any concrete recurrence separately for user review. If duplicate checks fail, stop publishing and keep drafts.
4. Select the highest-ranked eligible nonduplicate candidates up to the remaining cap, using reserves when needed. Use a supported Bug type for defects, or another suitable type only if the project's metadata supports it. Map severity to available priorities by meaning, recording the mapping; if unclear, omit optional priority rather than inventing one. Include the full evidence-based draft in the description, with run/finding IDs and baseline. Local report paths are references, not remotely accessible evidence; include enough detail for a Jira reader without the report.
5. Create sequentially and count every create attempt toward the six-attempt run-wide cap. Before each create call, send the finding ID and intended payload to the coordinator; the coordinator durably records the next attempt number, timestamp, run/finding IDs, and `pending` disposition in the report, then acknowledges the saved entry. Do not call create without that acknowledgment or if the attempt budget is exhausted. After each confirmed creation, send its finding ID, issue key, and URL immediately to the coordinator, which updates the ledger before the next attempt. Do not repeat a successful create or blindly retry a failed/timeout create. On an uncertain outcome, search by run ID, finding ID, and matching root cause; confirm an existing issue or mark `uncertain` and stop further writes. On other create failure, preserve drafts and stop; do not restart the budget by spawning another writer.
6. Return a disposition for every selected candidate: `created`, `duplicate-skipped`, `draft-only`, `blocked`, `failed`, or `uncertain`, with verified keys/URLs where available and sanitized reasons. Return total attempts and unresolved outcomes. Never claim success without a verified issue key.

## Coordinator: finish the run

Update the report with actual Jira dispositions, keys/URLs, attempt count, remaining drafts/reserve findings, and limitations. Preserve earlier findings and verification claims. If interrupted, use the existing run report's durable attempt ledger and Jira searches to reconcile outcomes before resuming; all recorded attempts (including `pending`, failed, and uncertain entries) retain their budget and must not be silently recreated. An unresolved ledger entry blocks further writes; an unavailable or corrupted ledger permits drafts only, not a fresh publishing budget for the same run.

Finish with a concise review outcome, report link, number of confirmed created issues, links to those issues, and any duplicate skips, blocked writes, or uncertain outcomes. A clean review or insufficient evidence may legitimately create no tickets. Do not present skill validation as a live review or Jira execution.
