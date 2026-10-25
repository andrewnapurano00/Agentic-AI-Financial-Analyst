# AX-01 - Guided Robo Advisor delivery (2026-10-22)

Status: implemented locally; scoped offline, health and browser verification passed. No source publication/deployment.

## Scope and baseline

User request: implement AX-01 from the User Improvement Roadmap. Baseline HEAD `e94c6771c9f41b9c087a4b538f2c83487ce09c02`. Pre-existing working changes: AGENTS.md and PLAN.md edits, root proposal removal and untracked docs/roadmap directory from the preceding authorized organization task. Preserved those edits; source/tests were clean before this implementation. Detailed specification: [AX roadmap](../roadmap/user-improvements.md); current status: [PLAN](../../PLAN.md).

This is a page-local build, not an invocation of the feature-development-team skill. No delegated agents, independent verifier, Jira publication or live financial research was requested/performed. Data handoff: no new metric, provider, fiscal basis or calculation; reuse saved domain/provider contracts unchanged.

## Baseline observations and plan

- Existing page used explicit Interpret and a versioned form/Build, with session-backed results and separate saved snapshots. Main and focused launcher both render the same page.
- Basic style/horizon/risk/amount controls were interleaved with holdings/assets/sizing; only limits were collapsed. All controls were described as enforced constraints despite descriptive risk preference. No field-origin preview or saved-result mismatch notice existed.
- Plan: extract a presentation-only editor, group advanced controls, make three stages explicit, label supported parser extraction versus suggestions/defaults/edits, preserve original reports and financial inputs, expose the existing saved limits and fallback, then exercise offline state/call invariants and responsive browser flow.

## Delivered delta and acceptance

- `ui/advisor_mandate_editor.py`: editor extraction with original widget keys/defaults and form semantics; basic field origin preview; collapsed full advanced controls; conflicting risk clarification; local draft/result comparison.
- `ui/portfolio_architect_tab.py`: three-stage labels, collapsed collection details, interpretation-origin metadata, applied constraints/limitations and prior-result mismatch message. Original collection, local checkpoint, optional AI review/retry, diagnostics, result tabs, exports and saved snapshots retained.
- `tests/test_advisor_guided_ui.py`: five tests cover unparsed amounts/horizons and edit/AI provenance, all advanced controls, three-stage simple Build, no hidden collection, independent research state, saved-result mismatch, infeasible/provider-failed rebuild recovery, empty prompts and conflicting risk words. Existing AI review/rerun tests also passed.
- README and advisor guide explain confirmation, advanced options, limitations and preserved-result recovery. PLAN records local status and actual evidence; original AX acceptance criteria retained.

Simple prompt -> Interpret -> review defaults -> Build works without opening Advanced settings. Build confirms the displayed choices; a form's unsubmitted edits are intentionally not sent to Python until submission. User-edited input and generated result remain distinct. Unsupported prompt content is not silently certified as extracted. Descriptive risk/horizon preferences do not become optimizer guarantees. All existing result tabs, reference evidence and download formats remain available.

## Verification

Project environment: Python 3.12.0 / pytest 9.1.1 / Streamlit 1.61.1, `PYTHONPATH=src`.

```powershell
& ../venv/python.exe -m pytest tests/test_advisor_guided_ui.py tests/test_advisor_packet_budget.py tests/test_advisor_mandate_fit.py tests/test_advisor_construction.py tests/test_advisor_batches.py tests/test_advisor_screen.py tests/test_portfolio_architect.py tests/test_portfolio_architect_provider.py tests/test_portfolio_architect_ui.py tests/test_robo_advisor_ui.py -q --tb=short
```

162 passed in 61.72s. External test transport guarded; synthetic provider/model responses; no paid calls. Earlier existing UI/routes 14 passed in 28.23s. Initial new preview test asserted string formatting of an integer default; corrected the assertion to check numeric value before final passing run.

Affected UI compileall/import passed. Main app startup/health on port 8577 and fixture health 8576 returned ok. Agent-browser session `ax01-guided-20261022` exercised an external-transport-blocked temporary harness around the actual renderer and shared shell. Interpret: collection count zero. Edited USD amount to 25,000 and Build: one synthetic collection, correct result amount and user-edit provenance. Save, open Advanced settings and change objective: count stayed one; saved result and mismatch notice remained. Desktop 1440x1000 and narrow 390x844 screenshots visually inspected; temporary harness/screenshots stored outside Git. Native tables scroll horizontally at narrow widths. Browser errors command returned no errors.

No full-suite run for this page-local change; no shared routing/transport/domain math changed. No live provider/model, AI prose-quality, clean install, hosted checks, native file download inspection or universal accessibility certification. Existing full inventory retains its earlier source-sync scope and date. AX-05, ETF look-through, universal financial contracts and hosting acceptance remain open.

## Remaining work and rollback

The local parser still does not extract amounts or arbitrary horizon wording; the UI explicitly requires confirmation. AI suggestions require review. Risk preference remains descriptive until separately implemented risk-policy work. Future slices must preserve saved report/form behavior. Rollback is limited to these two UI files and the new test/documentation changes; do not revert pre-existing roadmap organization edits or domain/provider implementations.

No unresolved observed in-scope defect after focused tests/browser checks. No Jira issue creation attempts (0); no commits or pushes.

## Final provenance follow-up

Extraction provenance now uses the submitted objective, preventing an AI-rewritten objective from certifying its own inferred style as user-supplied. Added a regression assertion for an AI growth objective against a submitted balanced prompt. Final three-file UI/routes run: 19 passed in 37.76s after this change; affected compileall passed. The broader 162-test run above preceded this correction. Final browser re-Interpret retained the original saved portfolio, displayed the mismatch notice and kept fixture collection count at one. Fixture browser/server closed. No provider or financial/domain contract changed.
