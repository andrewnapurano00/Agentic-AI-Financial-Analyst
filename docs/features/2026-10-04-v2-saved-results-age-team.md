# Deep Research V2 saved-result timestamp and age

Date: 2026-10-04 (America/New_York). Mode: build.
Run ID: 2026-10-04-v2-saved-results-age-team
Baseline: 619494cec1e0ac716b3ba7b9d72391171eed5825, main, with substantial pre-existing working-tree changes.
Initial source/document/test snapshot: `C:\Users\andna\AppData\Local\Temp\axiom-v2-timestamp-baseline-sqb9sanc` (outside repository); status, diff and SHA-256 hashes retained there.

## Scope and acceptance

Persist generation timestamps for saved V2 research results, render timestamp/age on reuse, handle missing/invalid legacy timestamps without fabricating dates. Ordinary reruns/navigation must not trigger provider/model calls. Preserve V1. Offline tests, fresh health/browser interaction and documentation required.

User explicitly overrides normal team publication sequence: create one AAFA implementation ticket before coding, update it with progress/verification, commit and push only scoped changes, deploy existing configured workflow, close only after verified deployment. Substantive unresolved follow-ups require duplicate checks and share the five-create-attempt budget.

## Handoffs

Financial specialist pending. Planner, builder, independent verifier pending.

## Jira ledger

No creation attempts yet. Budget: five. Duplicate check and metadata pending.

## Verification and deployment

Pending. No configured hosting target found in initial repo scan; Dockerfile is not a deployed target. Unrelated work must not enter the commit.

## Financial data handoff

D01: shared created_at is run start, not report generation. D02: generation age differs from evidence retrieved_at and quote_as_of. D03: legacy saved sessions must not fabricate a generation date. No new financial/provider requirements. Source: manager.py, models.py, v2_data.py, v2 UI/workflow.

## Implementation-ticket duplicate check

Live full AAFA search including all statuses returned AAFA-1 through AAFA-4, pagination complete. AAFA-1/2 concern failure/recovery, not report generation age; AAFA-3/4 are access checks. No duplicate outcome. AAFA create permission confirmed; Task is supported.

## Creation attempt 1

Timestamp UTC: 2026-10-04T23:20:00.069404+00:00
Disposition: pending. Snapshot rechecked. Coordinator authorizes this user-requested implementation ticket before coding. Remaining creation budget after this attempt: four.

```json
{
  "cloudId": "https://bigmeatpete717.atlassian.net",
  "projectKey": "AAFA",
  "issueType": "Task",
  "summary": "Show generation timestamp and age for saved Deep Research V2 results",
  "description": "## User outcome\nSaved Deep Research V2 results should show when the report was generated and how old it is, so reopening a saved result does not imply fresh research.\n\n## Acceptance criteria\n- Persist a timezone-aware generation timestamp for new V2 reports and show readable timestamp/age near the selected saved result.\n- Preserve timestamp on normal reruns, history navigation and saved-result reuse; no additional provider or model calls.\n- Handle legacy missing/malformed timestamps without inventing a date; distinguish report generation from evidence as-of dates.\n- Preserve Deep Research V1 behavior. Add offline lifecycle/formatting/UI tests and update README, subsystem docs and PLAN.\n- Independently verify source changes, focused tests, compile/import, Streamlit health and a mocked browser interaction.\n- Commit/push only this feature's delta, preserving unrelated local work; deploy the existing configured target. Mark complete only after deployment verification. If no target is configured, request the target after implementation and verification.\n\n## Run and baseline\nRun: 2026-10-04-v2-saved-results-age-team\nItem: P01\nBaseline: 619494cec1e0ac716b3ba7b9d72391171eed5825 on main; substantial pre-existing local changes are outside this ticket.\n\nRequested implementation ticket before coding; user explicitly authorized progress/verification updates, scoped commit/push and deployment. No implementation or deployment is claimed yet.\n\n## Planned verification\nMocked offline timestamp lifecycle and Streamlit saved-reuse/history interactions; no paid model or live financial-provider calls. Evidence retrieval dates remain separate from report generation age.",
  "labels": [
    "feature-development-team",
    "v2-saved-results-age"
  ]
}
```

Attempt 1 confirmed: created [AAFA-5](https://bigmeatpete717.atlassian.net/browse/AAFA-5). Budget consumed: 1/5. No other tickets created.

Jira progress: comment 10107 added; confirmed available transition 21 moved AAFA-5 to In Progress. Existing target identified in README: Hugging Face Space andrewnap211/Agentic-AI-Financial-Analyst-v2 (Docker, sleeping); remote source lacks Deep Research V2. Local Hugging Face authentication absent; GitHub CLI token invalid, while normal git fetch works. Deployment unverified; no other ticket writes.

Release isolation checkout: `C:/Users/andna/AppData/Local/Temp/axiom-v2-timestamp-release-orbddx05/checkout` detached at baseline; no original working files removed.

## Completed team handoffs

Financial specialist D01-D03: no new financial/provider requirements; operation-generation age distinct from start/evidence timestamps, legacy unknown explicit. Planner P01-P03: focused metadata helper, V2-only lifecycle/display, offline preservation cases, health/browser/docs. Builder: six scoped files with run/resume hooks and timestamp/UI tests. Independent verifier: F01 isolated-checkout encoding error corrected/rechecked; no other introduced defect or eligible follow-up. All four distinct roles ran sequentially; no nested teams.

## Actual verification


### V-20261004-01 - Saved V2 result generation age (isolated release)

AAFA-5 / R02 / R06: the release candidate applies only the timestamp enhancement to committed baseline `619494c`; earlier uncommitted V2 recovery/quarterly work remains local and is excluded. The new helper and 23 timestamp tests are identical in the working tree and isolated release. UI integration uses each version's existing manager factory, with equivalent completed run/resume hooks and read-only rendering.

- Full isolated release inventory: `PYTHONPATH=src; python -m pytest -q` -> **108 passed**, 127 existing Altair/jsonschema deprecation warnings, 57.32s. Anaconda Python 3.12.7, pytest 7.4.4, Streamlit 1.64.0. Offline mocks/fixtures; no paid model or live financial-provider calls. This is the release inventory, not a remeasurement of the larger uncommitted working tree.
- Working-tree builder evidence: 23 dedicated timestamp tests passed (28.14s); earlier combined run of 22 timestamp + 28 recovery tests passed (50 tests, 49.74s); two temporary tests for pre-existing finalization/decision-retry controls passed (11.56s). Temporary tests are not part of the release inventory.
- Independent verifier: corrected candidate's 23 timestamp tests passed (30.98s); affected modules compiled and diff checks passed. F01 encoding error in candidate preparation was corrected and rechecked; no unresolved introduced defect or follow-up ticket candidate.
- Final candidate: `python -m compileall -q app.py src` and import of app/main/timestamp helper/V2 UI passed. Fresh full-app Streamlit startup and `/_stcore/health` passed on port 8530; offline harness health passed on 8531. Health is separate from page-interaction evidence.
- Fresh browser test used the actual candidate V2 UI with synthetic saved modern/legacy results and mocked research factory; HTTP/model boundaries blocked. History selection displayed explicit legacy-unavailable fallback. A new synthetic operation recorded UTC time, saved reuse retained it, and full rerun/tab navigation/memo download retained the exact timestamp with research operations=1 and external calls=0. Browser screenshots/harness stayed outside the repo; harness PDF was a placeholder, and actual PDF generation was not retested for this metadata-only change.
- Scope limitations: no live financial-quality run, clean dependency installation, Docker build or hosted deployment verification. Existing Hugging Face Space is identified but has no local authenticated credentials; GitHub has no Actions workflow/deployment records. AAFA-5 remains In Progress until deployed verification. No follow-up tickets were warranted. Broad R02/R06 acceptance criteria remain open.

## Release and deployment disposition

Ready to commit timestamp-only source/tests/docs plus this report on main. The staging source is the independently verified isolated candidate, not the entire current V2 files. Previous local edits remain unchanged outside this run's delta. Existing Hugging Face Docker Space predates Deep Research V2; deployment would require the complete verified committed application source, preserving Space configuration. Authentication requested through local CLI; no token requested in chat. No deployment or ticket completion claimed.


### Local deployment verification - 2026-10-04

The user clarified that deployment means updating the local application; Hugging Face publishing is outside this run. Local source changes are installed in the existing working tree. A fresh local app on port 8533 returned `ok` from `/_stcore/health`; affected modules compiled and app/main/V2 imports passed. A separate offline browser harness on 8532 exercised the actual working-tree V2 UI: modern/legacy history, new generation, saved reuse, Sources tab, memo download and full rerun. UTC timestamp remained `2026-10-04T23:34:54...` across reuse, with research operations=1 and external calls=0. The synthetic report/PDF boundary is mocked; no paid/live financial calls. The earlier isolated-release checks remain separate evidence. This verifies the requested local deployment, not a hosted release. AAFA-5 can complete after the verified scoped commit/push; no follow-up defect ticket was warranted.

User clarification supersedes the earlier hosting/authentication blocker. Local deployment is verified; source sync remains authorized. Implementation ticket will be completed only after recording verification and scoped GitHub push. Four creation attempts remain unused.


### Final delivery ? 2026-10-04

Local deployment was verified as requested; no Hugging Face deployment was performed. Feature commit `31580ef0dd667357bd836849aea9c6d5906eaaf3` was pushed to `origin/main`, and its remote SHA was verified. AAFA-5 received verification comment 10108 and was transitioned to **Done** after local deployment verification. No substantive unresolved issues required follow-up tickets. Unrelated working-tree changes were preserved.
