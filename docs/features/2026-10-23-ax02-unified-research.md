# AX-02 - Unified Deep Research UX (2026-10-23)

Current status: unified default controls, combined saved library and explicit saved-evidence continuation implemented locally; offline, health and guarded browser verification passed. The initial preview delivery and its historical verification are retained below. Working tree only; no publication, deployment, Jira writes or live financial/model calls authorized.

## Baseline and scoped plan

HEAD e94c6771c9f41b9c087a4b538f2c83487ce09c02. Pre-existing changes: AGENTS.md, PLAN.md, README.md, advisor guide/UI, AX-01 editor/tests/report and roadmap reorganization. Preserve all. AX-01 is locally delivered; rerun its 19 focused UI tests before proceeding.

Initial SHA256: workspace 53D7EC1B5E954D48EDF4CDA9C2664EE0BBED907767E6884C7A96F53A5331420F; Standard UI 35FACFFABFAFC866AA8335EDED1EB960FB5FB41995025FB597974562EF003F56; pilot UI 3488D2881B99D90FE41387F7D57D0F1EB99DFB3580F29B16602805B0EBDD91D5; unified tests DA2AEEEB833CCEB91968BC82B975AA46D2BF87BF158439F5F32C28756E75DB34.

This is a scoped implementation request, not explicit invocation of the feature-development-team skill. No delegation or Jira creation. Data requirements: reuse existing audited evidence and immutable saved narrative; no new metric, provider, financial basis or verification assertion. AX-06 verification indicators are excluded.

Plan: opt-in wrapper with outcome presets, documented fixed default routes and expert override; preserve legacy route behind rollback switch; collapse engine controls in preview; common read-only saved-result overview, with unavailable sections explicit; retain engine-specific histories, recovery, follow-ups, committee and exports. Add offline preset/state/call-boundary tests, run existing research regressions and full suite for workspace routing, compile/import, health and guarded browser checks.

## Routing and boundaries

| Preset | Default engine | Depth | Model/stages | Cost boundary |
| --- | --- | --- | --- | --- |
| Quick Brief | Low cost V2 pilot | Standard | Economy: existing plan/draft routing; no decision | Existing editable USD 0.35 estimated-model budget; unknown pricing is not a hard dollar ceiling |
| Deep Dive | Standard V1 | Standard | Sidebar model; existing collection/plan/investigate/single-pass report | Existing per-stage token/time limits, four targeted investigations; no enforced dollar ceiling |
| Investment Committee | Standard V1 | Extended | Same report path, optional explicitly disclosed committee | Eight targeted investigations plus existing committee bounds; no enforced dollar ceiling |

Advanced engine override supports V1 Quick (Standard), V2 Deep Dive/Committee (Extended Balanced, Full committee only for Committee). There is no automatic fallback when dependencies are missing. All routes retain existing core audited financial collection, optional news and partial-evidence behavior. Presets configure defaults only; expert choices remain authoritative. Committee intent preselects its checkbox/decision option, with disclosure before explicit submit; it never launches from selecting the preset. Quick is an intent, not a measured latency/cost promise.

## Delivered delta

- Added `ui/research_intent.py`: deterministic intent defaults, read-only section extraction and common overview. Missing named sections remain explicit; no narrative/model generation or financial recalculation occurs.
- Updated `ui/deep_research_workspace.py`: opt-in session checkbox and reversible legacy selector; three presets, engine override and explicit pilot/cost/committee disclosures. No automatic dependency fallback.
- Updated both engine renderers with optional presentation configuration; unchanged collectors, managers, financial contracts, session histories, recovery, follow-ups, decision and export functions. Preview-only expanders contain expert controls. Original reports and exports remain unchanged.
- Added `tests/test_research_intent.py`: six engine/preset form submissions, call-free reruns, saved-history/rollback preservation, section immutability and two timeout cases.
- README explains the optional journey; DEEP_RESEARCH records compatibility; PLAN and roadmap record this bounded delivery, retaining open criteria.

## Verification

Project `../venv/python.exe`: Python 3.12.0 / pytest 9.1.1 / Streamlit 1.61.1; `PYTHONPATH=src`. Tests guard external transport and use synthetic provider/model boundaries.

- Fresh AX-01 check: `python -m pytest tests/test_advisor_guided_ui.py tests/test_portfolio_architect_ui.py tests/test_robo_advisor_ui.py -q --tb=short`: 19 passed in 46.55s. Confirms local delivery; no AX-05 risk enforcement claimed.
- Initial research-focused command: `python -m pytest tests/test_research_intent.py tests/test_unified_deep_research.py tests/test_deep_research_ui.py tests/test_deep_research_v2_recovery.py -q --tb=short`: 52 passed in 36.47s before two timeout additions/final caption changes. After adding timeout cases, intent-only run: 10 passed in 24.83s. Final `python -m pytest tests/test_research_intent.py tests/test_deep_research_ui.py -q --tb=short`: 18 passed in 39.83s after the final partial-state wording and saved-run details expander.
- `python -m compileall -q app.py src`; `import app; import langgraphagenticai.main` passed. Main app health 8579 and guarded fixture health 8578 returned `ok`.
- Agent-browser isolated session `ax02-20261023` exercised actual workspace and both forms using temporary fixture outside Git, blocked requests/httpx and synthetic managers. Preview/Quick Brief selected pilot, retained incomplete evidence and showed partial status; explicit Run produced a completed fixture. Committee selected Standard/Extended and its preselected committee checkbox was visible under Advanced settings with an above-form spending disclosure. Opening controls and switching goals retained generation count one; rollback restored Research format and count one. Browser console errors command was empty. Desktop and 390px screenshots outside Git were visually inspected. The temporary harness adds a title to match the app's normal header spacing. Fixture/browser and both temporary servers were stopped afterward.
- Full guarded `python -m pytest -q --tb=short`: **1144 passed in 457.10s**. Collection included eight new intent tests and five pre-existing AX-01 additions; the two timeout tests were added after collection and passed separately in the final 18-test run. The full run began before the final display-only wording/caption adjustment, which the final focused run covers. This is not a fresh full inventory of the final expanded collection. No live providers, paid models, clean install, hosted/deployment checks or native export-file inspection. Existing regression tests cover committee/PDF semantics; browser PDF bytes are mocked, not export-layout evidence.

## Remaining criteria and rollback

AX-02 ships as an opt-in local preview; broader rollout and AX-06 verification indicators remain open. Legacy narratives do not share a structured section schema; overview uses titled excerpts with explicit unavailable states, retaining full originals. No new resumability guarantee: existing engine recovery/decision actions remain, and an incomplete run without a supported recovery requires an explicit fresh submission. No financial, semantic-quality, real cost or latency certification follows. Turn off Try research intent preview to restore legacy format controls. No engine/schema migration occurred.

No tickets/creation attempts (0), staging, commits, pushes or deployment. Pre-existing AX-01 and roadmap edits preserved.


## Implementation continuation (2026-10-23)

Explicit user request IMPLEMENT AX-02: finish unified default controls, combined saved-run navigation and explicit saved-evidence continuation. Baseline includes the entire preceding preview and unrelated AX-01/roadmap changes. Workspace SHA256 51F51CD4AE120A17D11C7AA1877B11B02787F69C2C82CAC9B4990FD36014082D; intent helper 47A67C0355D07941981AC6249C84CDB5B5416EF7A6DFF4F2C339E84733138EE8. Plan: retain reversible legacy controls, no engine migration, saved lineage and budgets; recovery requires acknowledgement, uses saved model configuration, constructs no collection tools, preserves originals on failure, and never invokes a committee. Verify both engines, full offline suite and guarded browser flow. AX-06 indicators remain excluded.


### Continuation delivery

- Unified controls default on for new sessions; prior explicit preferences survive widget cleanup. The original checkbox key is retained for session compatibility, with the new visible Use unified research controls label. Turning it off restores classic controls. Default Deep Dive remains V1; existing Low cost preference initializes Quick Brief, retaining the pilot engine. No engine or saved financial schema migration occurs.
- Combined saved selector carries only engine/run identity and selects the existing history entry; no provider/model call. Both old engine histories and expert controls remain available.
- Explicit Continue saved research requires acknowledgement of stale/legacy evidence. Standard constructs its manager without collection tools; V2 uses its saved routes/runtime/budget through the existing saved-manager path. Both call resume only, on a defensive copy. A changed run ID/request/evidence is rejected. An unfinished/failed continuation retains original report, evidence and download state, with sanitized failure and attempted model-cost diagnostics/reservations. Success retains original text in Original report before continuation; V2 stamps operation time separately from evidence dates. No automatic committee occurs after recovery.
- New tests cover both engines' successful/failed continuation, disabled-until-acknowledged behavior, original preservation, no run/committee calls, combined navigation, default/rollback, no Standard collection-tool construction and failed-cost reservations. First continuation run exposed a V2 widget-state write after selectbox mounting; saving the already-selected run without rewriting that widget fixed it. Earlier success-test fixture mismatches were corrected by representing current single-pass saved records explicitly.
- Current modified AX-02 paths: four UI files, tests/test_research_intent.py and the classic-route fixture in tests/test_unified_deep_research.py; README, DEEP_RESEARCH, PLAN and roadmap. No source changes to managers, collectors, audited financial calculations or exports.

### Continuation verification

- Existing project environment remains Python 3.12.0 / pytest 9.1.1 / Streamlit 1.61.1. Initial existing+preview research checks: 54 passed in 39.61s. After continuation cases, two V2 widget-state failures / 59 passed in 42.62s were corrected. Final intent tests: 17 passed in 19.77s; after original-text retention, 17 passed in 31.44s. External test transport guarded; all model/provider evidence synthetic.
- Fresh app/src compileall and app/main imports passed. Main health 8581 and guarded fixture health 8580 returned ok. Browser session ax02-final-20261023 exercised actual controls/continuation in both engines, with requests/httpx blocked and mocked model/PDF boundaries. Acknowledging alone left counters zero; Standard continuation produced recovery one and retained original text; combined saved selector opened the pilot without generating; pilot continuation produced recovery two with generation count zero. Desktop and 390px images outside Git visually inspected; errors command empty. Browser and temporary servers stopped.
- Full guarded `python -m pytest -q --tb=short`: **1153 passed in 335.37s**. All 17 intent cases were collected. The full run started before the additive original-text-retention field/view; that small addition and its assertion are covered by the final 17-test run. No live financial/model calls, real pricing/quality/latency certification, native PDF artifact inspection, clean install, deployment or Jira writes performed. AX-06 verification indicators remain deferred; legacy evidence without usable records/configuration requires explicit fresh research.
