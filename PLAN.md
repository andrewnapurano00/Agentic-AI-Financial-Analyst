# Axiom Research - Living Status and Improvement Plan

**Last repository-wide audit:** 2026-10-01. **Latest scoped update:** 2026-10-10 (P01-P05 local implementation/status reconciliation; P05 / AAFA-12 release gates remain open). **Implementation baseline:** `77f7275`. This records verified local working-tree changes; earlier delivery baselines remain in dated records below.

## Purpose and how to read this file

Build one trustworthy research workstation: transparent data, connected workflows, grounded conclusions, reliable portfolio analytics, and predictable cost. [AGENTS.md](AGENTS.md) defines engineering requirements; this file records what exists, how it works, what was verified, and what remains.

- **Implemented:** the named capability exists in code; verification scope is recorded separately.
- **Partial:** useful foundations exist, but the roadmap acceptance criteria are unmet.
- **Pilot:** isolated experimental capability; production promotion requires additional evaluation.
- **Planned:** proposed work without evidence of completion.
- **Verified:** a specific dated check passed. It never means all behavior in that area is covered.

Use stable roadmap IDs R01-R10 and delivery/verification IDs below when adding work. Keep historical entries and append evidence; update the current matrices when behavior changes.

## P01-P05 current delivery status (2026-10-10)

The five scoped improvements are implemented locally. P01-P04 minimum local acceptance passed; P05 source implementation is finished, while release acceptance remains incomplete. This summary supersedes stale current-state wording, not the dated historical verification records. No commit/push or hosted deployment was performed by these deliveries.

| Item | Local outcome | Tracking and evidence |
| --- | --- | --- |
| P01 | Metadata-only company handoffs, explicit Research drafts, saved-result/chat preservation and action-scoped readiness | [AAFA-8](https://bigmeatpete717.atlassian.net/browse/AAFA-8), last verified Done; [team report](docs/features/2026-10-05-p01-connected-context-team.md) |
| P02 | Shared terminal headers, executive cards and honest evidence/readiness presentation | [AAFA-9](https://bigmeatpete717.atlassian.net/browse/AAFA-9), last verified Done; [team report](docs/features/2026-10-06-p02-terminal-ui-team.md) |
| P03 | Explicit bounded one-company Guided research with annual FY evidence, cited-field validation and partial-result/session reuse | [AAFA-10](https://bigmeatpete717.atlassian.net/browse/AAFA-10), last verified Done; [team report](docs/features/2026-10-07-p03-guided-research-team.md) |
| P04 | Shared saved investment briefs, audited earnings-multiple sensitivities and safe bounded provenance exports | [AAFA-11](https://bigmeatpete717.atlassian.net/browse/AAFA-11), last verified Done; [team report](docs/features/2026-10-08-p04-investment-brief-team.md) |
| P05 | Offline CI definitions, aligned direct manifests, guarded cross-workspace smoke, separate Docker verification and deployment runbook | [AAFA-12](https://bigmeatpete717.atlassian.net/browse/AAFA-12), last verified In Progress; [team report](docs/features/2026-10-10-p05-release-automation-team.md) |

**Latest measured inventory:** 430 guarded offline tests passed in597.19s on installed Python3.12.0 / pytest9.1.1 / Streamlit1.61.1, independently verified in V-20261010-P05. Eight workspace routes have readiness/render smoke coverage; this is not exhaustive behavioral or export coverage. Fresh P05 health/browser/session evidence is recorded in that entry; documentation reconciliation does not rerun those checks. Jira statuses above are the dated delivery confirmations, not a fresh live Jira query.

**Next release work:** resolve the intercepted package-download transport and verify clean installs, runtime Docker non-root health and derived-image workflow; run the configured GitHub Python3.11/3.12 matrix after authorized source synchronization; select/authorize a protected host and verify secret/access controls, hosted interactions and rollback. No image or hosted URL is certified. The broader R01-R10 roadmap remains partial; no P06 scope is automatically authorized. See [deployment runbook](docs/DEPLOYMENT.md).

## Current application status

There are **eight navigation entries: seven main workspaces and one V2 pilot**. Session-backed results and bounded typed company navigation exist; universal typed financial provenance and complete handoff adoption remain open.

| Workspace | Current capability and implementation approach | Verification and remaining limits |
| --- | --- | --- |
| Introduction | Live market overview and company snapshot, news and explicit AI summaries. Both price charts share eight horizons, configurable SMA/EMA/Wilder RSI/MACD/Bollinger, separate oscillator panels, period-aware provider wall-clock axes, source/basis/coverage labels and explicit structured technical AI. Saved company and technical interpretations survive controls; changed evidence is labelled. | V-20261004-05: 54 focused cases and 322 full offline cases; all eight ranges on both surfaces exercised in a fresh synthetic browser harness. Live entitlement, complete bars, unknown provider timezone/adjustment and model narrative accuracy remain unverified. Universal provenance remains open. |
| Top Movers | Five-trading-day rankings, direction/sector filters, breadth, Serper news, and company handoff. Normalized symbol joins and a bounded quote batch enrich displayed global leaders/laggards. Missing/nonpositive average volume remains unavailable; partial failures preserve valid rows. | Synthetic enrichment/coverage tests and filter interaction coverage. Sector-filtered rows outside the enriched global set may still lack fields. P01 actual handoff/prefill regressions and P05 readiness render are covered; remaining discovery/portfolio behavior is not exhaustive. |
| Research | LangGraph finance chat with FMP/Marketaux tools, thread checkpoints, structured table handling, response formatting, and sanitized event logs. P03 adds an opt-in one-company Guided plan/run workflow with strict allowlisted tools, exact field citations, bounded attempts/spend reservations and session reuse. | P01 explicit-submit/thread/navigation and P03 Guided schema, citation, partial-failure, budget and reuse regressions are covered; P05 adds the cross-workspace synthetic journey. Complete LangGraph tool-routing/chat interaction coverage remains missing. P01 preserves chat on configuration changes, displays mismatches in Research and requires explicit New thread before changed settings are used. Full tool-routing coverage remains open. |
| Equity Report | Sector-aware financial/technical scoring, peers, rankings, optional saved narrative, PDF/Excel/CSV exports, and explicit CrewAI debate over a saved scorecard with fingerprinting and structured output. Duplicate active helper definitions were removed. | Three committee tests cover bounded packets/schema/universe validation. Full report scoring/UI/export coverage is incomplete. The UI module remains approximately 5,707 lines. |
| Stock Screener | FMP universe filters, paginated results, optional metric enrichment, shared transport, and partial-result metadata. Saved results remain visible on return and open Introduction; OpenAI is not required. | Pagination partial-failure metadata and P01 saved-return/Introduction handoff are covered; P05 adds readiness render. Full filtering/enrichment interactions remain incomplete; module-global key and cache behavior need review for session isolation. |
| Portfolio Lab | Historical Yahoo adjusted-price optimizer plus hybrid AI manager, constraints, evidence, recommendations, rebalance/monitoring, and reports. Allocation caps preserve residual cash rather than renormalizing above caps. | Constraint/parser regressions, missing-OpenAI optimizer readiness and P05 route render are covered. Broad optimizer math, risk assumptions, trade reconciliation, full UI, and Excel/PDF artifact coverage remain incomplete. |
| Deep Research (V1) | Evidence collection, bounded investigation tools, planning, streaming draft, review/patching, saved checkpoints, retry/resume, follow-ups, comparison output, PDF/JSON/CSV downloads, and optional committee. Fresh financial research uses the shared quarterly source and audited contracts; unverified cross-workspace financial packets are disabled. Per-company Equity Report sector applicability, latest balance snapshots, explicit metric audit and legacy notices are shared with V2. Shared Serper news coverage shows usable articles, company coverage and retrieval dates, with partial/missing states. P04 adds a shared saved investment brief, strict audited earnings-multiple sensitivities and bounded JSON/CSV exports without new calls. | Core/recovery/UI financial coverage is recorded in dated inventories; P04 saved-brief/scenario/export regressions and P05 independent saved-result journey extend it. Citation existence/recovery tests do not prove every factual claim. Real-provider/model quality and full committee costs are not certified by offline tests. Earlier financial verification: V-20261004-04 (276 offline tests, independent review, fresh startup/health and recorded browser interaction); live access and model narrative accuracy remain unverified. P04 verification: V-20261008-P04; live input eligibility and narrative semantics remain unverified. |
| Deep Research V2 | Isolated cost pilot with compact mode/company-aware prompts, lazy stage routing/preflight, honest failure states, saved-evidence/draft recovery, post-review mechanical checks and isolated explicit decision retries. Reuse includes saved runtime/context inputs; V1 remains separate. Both fresh versions now share supported four-quarter flows and independently latest balance snapshots, with matched beginning/end balances for return ratios. Per-company sector projections, explicit formulas/units/input records, bounded decision contexts and saved legacy notices are shared; no provider TTM substitution is used. Shared Serper news coverage shows usable articles, company coverage and retrieval dates, with partial/missing states. P04 adds a shared saved investment brief, strict audited earnings-multiple sensitivities and bounded JSON/CSV exports without new calls. | Five helper/fixture, 28 recovery/workflow and 53 quarterly financial/UI/PDF cases; fresh independent verification and offline browser checks recorded in V-20261003-01. Earlier environment-specific reference failures remain historical; V-20261004-04 records the prior 276-case inventory; V-20261004-05 records the historical 322-case inventory; V-20261010-P05 records the latest 430-case full inventory. No live quality/savings benchmark; session reuse does not refresh provider evidence and unknown-price models weaken dollar-budget enforcement. Serper verification: V-20261004-02; live access remains unverified. P04 verification: V-20261008-P04; live input eligibility and narrative semantics remain unverified. |

Entry points: [app.py](app.py), [main.py](src/langgraphagenticai/main.py), [sidebar routing](src/langgraphagenticai/ui/streamlitui/loadui.py). Shared design: [app_shell.py](src/langgraphagenticai/ui/app_shell.py).

**Current readiness boundary:** P01 removed the global OpenAI-key block. Screener, optimizer, deterministic report paths and saved results remain accessible; individual AI actions enforce their own requirements. V2 retains stage-specific provider preflight. Configuration readiness is not proof of provider entitlement or fresh evidence.

## Delivered foundations and how they were built

| Foundation | Current implementation | Boundaries still outstanding |
| --- | --- | --- |
| Provider reliability | Shared FMP REST sessions, safe-GET retries, bounded timeouts and sanitized provider exceptions under `providers/`. FMP MCP has its own bounded transport and investigation budget. | This is shared transport, not one canonical adapter/schema for every financial/news source. |
| Credential handling | Recursive redaction and safe UI/provider errors in `utils/safety.py`; sanitized timing/request events avoid logging raw prompts. | Complete HTML, link, download, persistence and dependency audits are still required. |
| Financial correctness | Introduction TTM validates quarterly period/currency alignment; zero is preserved; portfolio caps retain cash; unavailable liquidity is not fabricated as zero. | Universal period/currency/return-basis validation and broad optimizer/scoring tests are incomplete. |
| Market controls/data | `providers/symbol_history.py` validates and shares Introduction history; `market_history.py` retains compatibility. Histories sort/deduplicate, reject future observations, select latest one/five observed trading dates and retain a complete labelled provider series. Top Movers tolerates enrichment failures. | Observed dates do not certify complete exchange sessions or gap-free history. FMP adjustment/timezone and long/index entitlement remain unverified; Yahoo uses a separate auto-adjusted series. |
| Model-call safety | Explicit AI actions and result reuse; P01 drafts avoid auto-submit, P03 limits two model attempts/three tools, and P04/P05 preserve saved results without new calls. | Scoped rerun/navigation/download regressions exist; complete app-wide coverage and enforceable all-stage dollar ceilings remain open. |
| Deep Research recovery | Separate evidence/draft/review checkpoints, stage-specific failures, draft preservation, exact review patches and resume paths; model usage estimates when response usage is absent. | Mechanical citation checks are narrower than factual/semantic validation. |
| Deployment baseline | P05 aligned 28 direct requirements/package dependencies, Python-specific NumPy constraints, offline CI definitions, explicit runtime source copies, separate Docker verification and deployment runbook. | Constraints are not a full transitive lock. Clean installs, actual image startup/workflow, remote CI and hosted operations remain unverified; local package downloads failed through intercepted transport. |
| Contributor workflows | Thirteen repo-local skills with UI metadata, targeted references and [usage guide](docs/PROJECT_SKILLS.md), including GitHub sync, independent review, explicit review/Jira and feature development team workflows. The feature team can use the verified local MCP stdio bridge when native Jira tools are absent. | These guide coding agents; Jira publication requires authenticated access at invocation time. The Windows trust/HTTP/2 bridge is workstation-local. They do not add Streamlit agents, runtime dependencies or automatic deployments. |

The standalone `crew_ai/stock_picker` example and experimental notebooks are separate from the eight main navigation entries.

## Delivery history

### D-20261004-02 - Feature-team access through the working Jira MCP bridge

R06 scoped contributor-tooling follow-up: updated only feature-development-team Jira routing to use the existing local MCP stdio helper when native tools are absent, instead of stopping at a reload instruction. Added a linked access reference covering Windows trust and HTTP/2, schema/operation discovery, safe subprocess JSON arguments, project permissions, MCP error/created-key validation and uncertain-create reconciliation. Preserved explicit invocation, four roles, five creation attempts, duplicate checks, snapshots and durable ledgers. Sources: `.agents/skills/feature-development-team/SKILL.md`, `references/jira-mcp-access.md`, `docs/PROJECT_SKILLS.md`, `README.md`. Working tree only; unrelated existing edits preserved, no commit/push. R06 remains partial; application interaction/CI acceptance criteria are unchanged.

Verification for this skill update: Anaconda Python 3.12.7 / PyYAML 6.0.3; `quick_validate.py .agents/skills/feature-development-team` passed. `git diff --check` passed with existing line-ending notices. System Python 3.12 direct helper check freshly completed MCP initialize and tools/list (21 tools); this was a live Atlassian connection check, not an offline application test. Markdown/reference and explicit-only UI policy inspection completed. No new scripts or runtime code were added to the repository.

Earlier connection evidence from this conversation, separate from skill-update verification: Node 24.16.0, npm 11.13.0 and pinned mcp-remote 0.14.3; certificate issuer identified Norton Web/Mail Shield, HTTP/1.1 metadata decoding failed, and Windows system trust plus HTTP/2 restored access. The local bridge listed three Jira projects, read AAFA issue types and created [AAFA-4](https://bigmeatpete717.atlassian.net/browse/AAFA-4) at the user's explicit request. This supersedes the earlier unresolved connection status below, without rewriting its historical evidence. Global config/bridge files remain outside the repository and TLS verification remains enabled.

Not performed during the skill update: executing the four-agent team, creating additional tickets, paid models/financial-provider calls, application pytest/import/startup/health/browser checks or a new test inventory. Remaining limits: local helper availability and future authentication/project permissions must be checked per run; full team duplicate/ledger execution has not been exercised by this update. Existing pending report drafts were not published.

### Delivery 2026-10-04: Jira MCP routing in existing teams

R06 scoped contributor-workflow improvement: feature-development-team and code-review-team now diagnose MCP tool exposure, configuration, authentication and project permissions separately. Coordinator-only MCP access can publish independently verified writer payloads under existing duplicate checks and attempt ledgers; browser fallback is explicit. Existing team roles, caps and unrelated application changes are preserved. Sources: both team SKILL.md files, docs/PROJECT_SKILLS.md and README.md. Working tree only; no app behavior changed or roadmap milestone completed.

Local integration evidence: `codex mcp list` initially reported no configured servers; current session had no Jira tool catalog. Added global `atlassian` server at Atlassian's documented `https://mcp.atlassian.com/v2/mcp` using `codex mcp add`. Codex CLI 0.146.0 login returned `No authorization support detected`; list reports enabled/Auth Unsupported. No authenticated project, duplicates or publication verified; no tickets created. Configuration is outside the repository. Authentication/connection recovery remains outstanding; earlier V2 report and drafts remain pending. No application test inventory or new health/browser evidence claimed for this documentation/configuration change.

Verification: installed Anaconda Python 3.12.7 skill-creator quick validation passed for both edited skills. System `python` lacked PyYAML, so validation was rerun with the installed project interpreter. Instruction inspection confirms MCP-first routing, child/coordinator access distinction, retained duplicate checks/caps and explicit browser fallback. Direct endpoint returned HTTP 401 with an OAuth metadata challenge; fetching that metadata with curl failed on malformed chunk framing, although raw output contained authorization-server metadata. This suggests a transport/discovery problem; its origin is not established. No credentials inspected or TLS verification disabled.

Append new rows; do not rewrite previous delivery claims into release certification.

| ID / date | Delivery and approach | Evidence / status |
| --- | --- | --- |
| D-20260927-01 | Hardening and research features: shared transports/redaction, allocation and TTM fixes, partial coverage, bounded model calls, V1 recovery, and optional Equity Report debate. | Commit `ac3e349`; historical [code review](docs/code_review.md). Corresponding fixes exist; broader roadmap acceptance remains open. |
| D-20260927-02 | Separate V2 cost pilot with compact stage packets/routing, validators, reuse, optional decisions and evaluation fixtures. | Commit `7c73deb`; [V2 implementation](src/langgraphagenticai/deep_research/v2.py). Pilot, not proven savings or default promotion. |
| D-20260927-03 | README refreshed for the then-current app and pilot. | Commit `ff1709e`; superseded test inventory is corrected in this audit. |
| D-20261001-01 | Repaired Introduction historical controls and missing commodity/crypto quotes; hardened Top Movers enrichment and missing liquidity; saved summaries survive chart reruns without automatic AI calls. | Current working tree: `market_history.py`, `introduction_tab.py`, `market_overview_data.py`, `top_movers_data.py`, `top_movers_tab.py`, shared shell CSS and `tests/test_market_tabs.py`. V-20261001-01/02 below. |
| D-20261001-02 | Added nine focused coding skills, invocation guide, metadata and provider/financial/portfolio/export/release references. | Current working tree: `.agents/skills/`, `docs/PROJECT_SKILLS.md`, README. Skill manifests, links, YAML and referenced repository paths validated during that task. |
| D-20261001-03 | Rebuilt current-state documentation with workspace matrix, dated test inventory, delivery ledger and maintainable roadmap; separated requirements from implementation. | Documentation-only audit. Fresh offline suite and compile/import checks: V-20261001-02. No deployment or new app feature in this entry. |
| D-20261002-01 | Added `axiom-github-sync`: verifies repository/branch, change scope and applicable checks, then commits/pushes when requested; preserves unrelated work and disallows force-push. Collection now has ten skills. | Skill/docs-only change. Manifest/UI YAML, references and diff checks validated; app tests and live publication not repeated. October 1 work was pushed in commit `930d332`; this skill is a subsequent local change. |
| D-20261002-02 | Investigated AAFA-1: V2 incomplete/review-pending runs are labelled ready, saved warnings and retries are missing, optional decision/setup failures have misleading errors. Identified compact-token versus long-memo mismatch as a possible original-run trigger. | [Diagnostic and proposed repair](docs/diagnostics/AAFA-1.md), baseline `619494c`. 60 focused tests passed; five additional mocked UI scenarios and factory checks reproduced control-flow defects. Investigation only; no app fix or paid run. R04/R06/R07 remain partial. |
| D-20261002-03 | Implemented AAFA-2 after the user's explicit instruction to proceed: accurate status/warnings, saved-evidence/draft recovery, isolated decision retries, safe provider preflight, lazy stage setup, compact V2 prompts, supported reasoning settings and blocked/failed-cost diagnostics. Added runtime/context-aware reuse, post-patch mechanical validation, workflow hot reload and saved Ollama committee endpoint support. | Local working tree: `v2_workflow.py`, V2 UI/helpers, opt-in shared manager/committee settings, app reload hook, 28 new tests and subsystem documentation. V-20261002-01 below. No commit, push, deployment or paid quality run performed. Broad R04/R06/R07 milestones remain partial. |

## Verification ledger


### V-20261003-01 - Quarterly-derived V2 TTM

- Final root offline command: `python -m pytest -q` with `PYTHONPATH=src`: **168 passed, 2 failed, 128 warnings, 164.03 seconds**, 170 collected cases. All **166 application cases** passed across 12 test modules; four previously added standalone reference-collector cases contribute two passes/two failures. Added `tests/test_quarterly_ttm.py` has 53 cases; earlier application inventory remains historical. Environment: Anaconda Python 3.12.7, pytest 7.4.4, Streamlit 1.64.0; existing environment, not a clean-install/deployment certification.
- Failures: `fmp_data_reference/scripts/test_reference.py::CollectionTests::test_http_200_errors_and_reflected_credentials` and `test_transient_retry_is_bounded_and_cached`, both `reference.py:111` attempting unsupported truststore `get_ca_certs()`. These files predate this delivery and were not modified. Standalone reference tests: 4 passed in 1.76s. Explicit truststore injection followed by the same tests: 2 failed/2 passed in 1.99s. TLS verification remains enabled. Separate F03 draft, not an introduced V2 regression.
- Independent final command: `python -m pytest tests/test_quarterly_ttm.py tests/test_deep_research_ui.py -q`: **62 passed, 75.32 seconds**, including generated PDF text assertions and V1 UI compatibility. Builder final scoped quarterly/shared-UI/core command: **94 passed, 96.52 seconds**, including actual PDF extraction. Earlier results are scoped separately in the team report; an intermediate full run was interrupted after additional review corrections, not counted as a completed inventory.
- `python -m compileall -q app.py src` and app/main/quarterly/V2 imports passed after source freeze; imports emitted existing caching/deprecation warnings. `git diff --check` passed with existing line-ending notices. Source/test hashes independently rechecked unchanged after final review.
- Fresh `streamlit run app.py --server.headless true --server.port 8521 --browser.gatherUsageStats false` startup and `curl.exe --fail --silent --show-error http://localhost:8521/_stcore/health` returned ok. Full app browser rendering was not used to avoid live-provider access.
- Fresh temporary offline V2 browser harness on port 8522 used the actual quarterly source/manager/UI with saved AAPL statements and mocked HTTP/model boundaries. AAPL/Quarterly/Stop after evidence produced exact revenue 466823000000 and FCF 136683000000 through 2026-06-27; the TTM table showed the calculated basis and separate income/cash currencies/dates. Eight mocked provider requests and one planning call remained unchanged after saved reuse, full rerun and table/tab navigation. Temporary harness PDF was a placeholder; actual PDF generation/text verification is established by the separate tests above. Browser screenshot/harness remained outside the repository.
- Report: [team delivery and Jira draft](docs/features/2026-10-03-deep-research-v2-quarterly-ttm-team.md). Independent findings F01/F02/F04/F05/F06 corrected and rechecked; no remaining in-scope defect found. F03 publication blocked: isolated Jira browser showed login, so project metadata/duplicate checks unavailable; zero issues created, zero creation attempts. Draft preserved.
- No live provider data collection, paid model calls, credentials, staging, commit, push or deployment. Unrelated working-tree edits preserved. Remaining limits: live entitlement/financial quality, provider-equivalent ROIC/per-share formulas, ambiguous restatements, global typed provenance and cross-workspace context acceptance remain unverified/unmet. Broad R01-R10 milestones stay partial.

### V-20261002-01 - AAFA-2 implementation

- Final full offline suite: **113 passed, 128 warnings, 76.24 seconds**. Warnings: 127 existing Altair/jsonschema deprecations plus one LangGraph pending deprecation. Inventory: the previous ten modules/85 cases plus `test_deep_research_v2_recovery.py` (28 cases). Historical inventories below retain their original dates.
- New cases cover saved runtime/history, explicit writing/review/evidence-only retries, empty/length/timeout drafting, malformed review, post-patch mechanical checks, missing evidence/tickers/provider settings, blocked budgets, failed decision cost reservations, quick/full decision isolation, saved-result reuse and unchanged call counts on rerun. V1 core/recovery/UI tests also pass.
- Python 3.12.7, pytest 7.4.4, Streamlit 1.64.0, existing local environment. Previously recorded constraint/developer-version drift still applies; this is not clean-install certification.
- Compilation of app/source/new tests and app/main/V2-workflow imports passed. Import emitted existing caching/deprecation warnings.
- Fresh full-app Streamlit startup on port 8514 and `/_stcore/health` passed. A separate synthetic V2 harness on ports 8513/8515 passed health and browser timeout-to-retry-to-report interaction: one provider collection and three total model calls including the failed draft. Tabs/download clicks did not add calls. No live provider/model calls were used.
- Browser download saving was canceled by the automation tool; JSON/Markdown/PDF media responses returned HTTP 200 and were retrieved separately. Audit status/content, memo content and extracted PDF thesis text passed. Browser-side file saving is not certified. No JavaScript errors were recorded; artifacts stayed outside the repository.
- Actual report quality, achieved savings, alternate-provider service availability and the original incident's live response are unverified. Tests do not consume paid API credits. Browser artifacts/harness are outside the repository.

### V-20261001-02 - Fresh documentation audit

- Full offline pytest: **85 passed, 128 warnings, 116.66 seconds**, across ten modules. Provider/model boundaries in these tests use synthetic/mocked inputs; no paid workflow was requested.
- Environment: Python **3.12.7**, pytest **7.4.4**, Streamlit **1.64.0**, existing local Anaconda interpreter. The declared dev requirement is pytest >=8,<10; deployment constraints pin Streamlit 1.61.1. This run verifies the current environment, not a clean constrained installation.
- `python -m compileall -q app.py src` passed. `import app; import langgraphagenticai.main` passed. Import emitted caching and LangGraph deprecation warnings; import success is not full app startup.
- Pytest warnings: 127 Altair/jsonschema deprecation warnings plus one imported-plugin assertion-rewrite warning from the inventory wrapper. No test failures.
- No new startup/health, browser interaction, live-provider/model, Docker build, dependency upgrade or paid evaluation was performed for this documentation-only audit.
- Documentation checks passed: local links and referenced paths, UTF-8/encoding, code-fence balance and `git diff --check`. Hash comparison confirmed all 136 existing source, test and skill files were unchanged by this audit.

Reproduce in the project's installed environment from the repository root:

```powershell
$env:PYTHONPATH = (Resolve-Path "src").Path
python -m pytest -q
python -m compileall -q app.py src
python -c "import app; import langgraphagenticai.main"
```

The audit used a pytest collection plugin to count module inventory; a normal pytest invocation need not reproduce its extra plugin warning. Do not hard-code this developer's interpreter path into shared scripts.

### V-20261001-01 - Earlier market-repair verification

The earlier repair task ran the suite (**85 passed, 127 warnings**), compile/import checks, and Streamlit startup/health on port 8507. Browser checks exercised Introduction 1D/1M/1Y charts, restored commodity/crypto quote cards, Top Movers Leaders/Laggards, desktop and 390px mobile layouts. These were live-provider smoke checks with AI actions left unclicked, not an offline certification. Browser console showed chart-library warnings; no JavaScript errors were observed.

This is prior task evidence retained for traceability, not newly repeated by the documentation audit. It does not certify every workspace or currency/coverage combination.

### Historical test inventory at V-20261001-02

| Module | Collected | Actual protection |
| --- | ---: | --- |
| `test_app_health.py` | 2 | Configuration validation only; despite the filename, no startup or HTTP health check |
| `test_deep_research.py` | 32 | Evidence/provider envelopes, financial periods/trends, tool bounds, orchestration, citation failures and PDF/JSON helpers |
| `test_deep_research_recovery.py` | 14 | Checkpoints, retries, draft preservation, stream/output failures, review patching and bounded prompts |
| `test_deep_research_ui.py` | 9 | Mocked V1 Streamlit interactions, saved runs, follow-ups and recovery |
| `test_deep_research_v2.py` | 5 | Routing/limits, mechanical validators, cache-key inputs, committee packet/estimated usage and fixture presence |
| `test_equity_committee.py` | 3 | Bounded packet, structured decision consistency and selected-universe guard |
| `test_formatters.py` | 3 | Numeric formatting and rectangular tables |
| `test_hardening.py` | 6 | Allocation caps, redaction, TTM alignment, parsers, mover partial batches and Screener metadata |
| `test_market_tabs.py` | 8 | History/fallback/alias/enrichment contracts and three Streamlit control/state tests |
| `test_response_cleaner.py` | 3 | Research headings/bullets formatting |
| **Total** | **85** | **Twelve Streamlit interaction cases are concentrated in V1 Deep Research and market controls** |

Counts describe collected cases, not a code-coverage percentage. The inventory and coverage matrix below are historical October1 evidence; current P01-P05 additions and the 430-case inventory are summarized above and in V-20261010-P05.

| Coverage target | Current evidence | Remaining acceptance gap |
| --- | --- | --- |
| Financial/domain unit tests | Several important regressions protected | Broad scoring, return/risk math, currency, short history and trade reconciliation |
| Provider contracts | Synthetic FMP/MCP/Serper/Yahoo boundaries in selected tests | Uniform timeout/rate-limit/malformed/stale/empty cases across all adapters, including Marketaux |
| Streamlit workflows | V1 Deep Research, market controls and V2 recovery/submission contracts | Research, Equity Report, Screener, Portfolio Lab and complete cross-page path; live V2 provider/model evaluation |
| Agent/AI validation | Recovery, citation existence, structured decisions and helper routing | End-to-end tool choice, numerical grounding, model quality, adversarial cases and paid-call invariants |
| Exports | Deep Research PDF/JSON and formatting helpers | All-workspace PDF/Excel/CSV/JSON artifacts, credential/URL checks and data consistency |
| Integration/deployment | Fresh compile/import; earlier local health/browser smoke | Automated startup/health plus mocked full workflow, clean install and Docker/CI |
| Evaluation/observability | Five V2 scenario fixtures; local events and stage diagnostics | Executed scored benchmark, real per-agent usage, application-wide traces and quality thresholds |

## Configured limits versus measured outcomes

These are current settings, not measured performance promises.

| Scope | Current settings / mechanism | Limitation |
| --- | --- | --- |
| Market cache | Overview/history 300s; Top Movers and company snapshot 900s; company summary 1,800s | No universal freshness-state or narrative evidence fingerprint |
| Other data caches | Screener universe uses 3,600s; Screener enrichment 1,800s; optimizer price downloads 900s | TTLs alone do not establish correct cross-session/provider/credential cache identity |
| V1 model stages | Plan 1,200 output tokens / 75s; draft 4,500 standard or 6,000 extended / 150s; review 3,000 / 120s; follow-up 2,200 / 90s | Specific stage policies differ from other direct/graph clients |
| V2 output/context | Economy draft 1,800 standard / 3,000 extended; other modes 2,200 / 3,500. Draft context 22,000 / 34,000 characters; compact review/follow-up packets | Mechanical validation is not numerical claim verification |
| V2 routing | Economy defaults to nano light stages and mini drafting; Balanced uses optional review; Maximum Quality uses larger drafting/lead model. Groq/Ollama are opt-in light-stage routes | Alternate-provider operational quality is not established by helper tests |
| Budget/usage | V2 default UI budget $0.35; stage estimates and session diagnostics; CrewAI aggregate usage split is explicitly estimated | Unknown model prices can evade dollar checks; no proven complete per-agent cost attribution |
| Guided research | Prepare/Run actions: at most two model attempts, three tool dispatches, 12 graph steps; bounded 16,000-input/1,800-completion reservations per attempt, timeout60s, no model retries | Tool dispatches are not HTTP call counts; configured price estimates are user supplied, and unknown prices cannot guarantee a dollar ceiling |
| Saved results | V1/V2 histories isolated; V1 retains five runs, V2 eight; explicit refresh/later-synthesis controls | Session reuse is not durable persistence or a universal freshness-aware cache |

Cold/warm render latency, call-count budgets per workspace, and achieved savings have **not** been benchmarked here. Static model pricing tables need maintenance; do not treat estimates as current provider bills.

## Ten-step roadmap

All ten broad milestones remain **partial**. Individual delivered foundations below do not satisfy every acceptance criterion. Preserve the numbered dependency order; tests accompany each behavioral change rather than waiting for R06.

| ID | Milestone | Current status | Next acceptance focus |
| --- | --- | --- | --- |
| R01 | Canonical market data and provenance | Partial | Typed shared records/adapters and provider contract matrix |
| R02 | Universal freshness/source/data-quality UX | Partial | Consistent states and currency/period/source visibility across pages |
| R03 | Shared company context and connected journey | Partial; P01 supported typed metadata handoffs/state preservation delivered | Remaining Portfolio/Compare paths and canonical financial provenance |
| R04 | Evidence-first validated AI research | Partial; P03 cited-field contract and P04 audited saved sensitivities delivered | Numerical/period/currency grounding beyond the bounded Guided slice; AI narrative semantics |
| R05 | Stable domain modules | Partial | Characterized extraction of large mixed-responsibility modules |
| R06 | User-critical automated workflow coverage | Partial; P01-P05 interactions and eight-route release smoke added | Remaining success/failure paths, complete portfolio journey and executed CI |
| R07 | Performance/cache/AI economics | Partial; V2 pilot and P03 bounded attempts/reservations | App-wide measured latency and complete enforceable cost accounting; unknown prices remain unsupported |
| R08 | Portfolio decision and monitoring workflow | Partial | Unified holdings/constraints, assumptions and trade reconciliation |
| R09 | Observability, evaluations and feedback | Partial | Executed versioned evaluation and end-to-end sanitized traces |
| R10 | Documentation/deployment readiness | Partial | P05 CI/manifests/runbook delivered locally; actual GitHub matrix, clean-install/container gates and authorized hosted rehearsal/rollback remain pending |

### R01 - Canonical data and provenance

**Impact: very high. Effort: high.** Shared FMP transport and labelled history fallbacks are implemented. REST, MCP, news and portfolio adapters still have different contracts.

- [x] Bounded shared REST transport, safe errors and selected partial-result metadata.
- [x] Introduction market/company history shares normalized symbol/range retrieval with dated source/basis/timezone/partial/stale metadata (AAFA-7, 2026-10-04); universal typed records remain open.
- [x] Shared fresh V1/V2 financial source and explicit metric contracts: rolling flows, independent balance stocks and source/input audit (AAFA-6, V-20261004-04).
- [x] V2-only quarterly-derived TTM source records, fiscal windows and formula/currency metadata (2026-10-03); universal typed records remain unmet.
- [ ] Typed security, quote, history, financial value, news and provider-error records with provider, retrieved time, source as-of, unit/currency, period and status.
- [ ] Consolidate duplicate retrieval/normalization; define source precedence and uniform safe retry/rate-limit behavior.
- [ ] Normalize/deduplicate Marketaux and Serper news under one contract.

**Acceptance:** two workspaces resolve the same quote through the same adapter/metadata model; failures preserve typed partial results; contracts cover success/timeout/rate limit/malformed/empty/stale; secrets are absent from logs/errors/diagnostics/exports.

### R02 - Universal data-quality UX

Saved V2 generation-time metadata delivered in AAFA-5 (V-20261004-01); evidence freshness and universal provenance remain open.

**Impact: very high. Effort: medium.** Source/date notes and partial warnings exist in market and research paths; shared shell styling exists.

- [x] Market quote/fallback source notes, unavailable liquidity and partial coverage.
- [x] Both research comparisons expose dates/currencies/units/applicability, audit exports and saved legacy notices (AAFA-6); universal page freshness remains open.
- [x] P02 shared honest workspace headers, saved evidence rows and bounded executive cards in Introduction/Research/V2; V1 evidence row. Configuration and interface render clock are separate from evidence retrieval.
- [ ] Universal freshness indicators and data-quality drawer across remaining pages.
- [ ] Relevant quote/statement/news dates, currency, period and retrieval time on every data-heavy page.
- [x] P01 removes the global model-key gate and scopes dependencies to AI actions; V2 keeps stage-specific preflight.
- [ ] Universal provider-entitlement/freshness/readiness states across remaining workspace actions.

**Acceptance:** every major workspace distinguishes live/delayed/cached/stale/fallback/partial/unavailable using text as well as color; successful partial data survives; provider facts, calculations and AI interpretation are visibly different.

### R03 - Connected company context

**Impact: very high. Effort: medium.** Existing navigation keys, selected-company handoffs, saved filters/results and Deep Research context collection provide foundations.

- [x] Selected ticker handoffs and allowlisted saved context in some paths.
- [x] P01 bounded metadata-only `ResearchContext`: validated normalized symbols, destination, origin, intent and optional saved reference/source/as-of. Shared one-shot adapters connect Introduction/Top Movers to Research, Equity Report and both Deep Research versions; Screener to Introduction.
- [ ] Migrate remaining handoffs and canonical evidence/provenance records; Portfolio/Compare journeys remain outside P01.
- [ ] Consistent Snapshot/Research/Report/Deep Research/Compare/Portfolio actions and return-to-results.
- [x] P01 Research drafts require explicit submit; configuration changes preserve the conversation and offer a visible New thread action. Non-Research navigation does not reset chat.
- [ ] Recent securities/pinned comparisons and complete saved-filter preservation across all workspaces.

**Acceptance:** mover -> prefilled Research -> Deep Research without re-entry; returning preserves filters; no silent loss of completed work; full path covered by mocked interactions.

### R04 - Grounded and validated conclusions

**Impact: very high. Effort: high.** V1 evidence/review recovery, period-aware helpers and committee schemas exist. V2 adds mechanical report checks.

- [x] Evidence identifiers, unknown-citation failure handling, saved packets and structured committee outputs.
- [x] Introduction technical AI uses bounded structured explicit-action analysis with chart identity, input fingerprint and usable evidence-reference validation (AAFA-7); prose numerical certification remains open.
- [x] Shared audited deterministic research metrics and sector-projected report/decision contexts (AAFA-6); model prose numerical certification remains unmet.
- [x] V2 deterministic quarterly TTM validation and supported metric formulas with unavailable-input disclosure (2026-10-03); universal claim validation remains unmet.
- [x] P03 exact cited-field validation for the bounded Guided annual slice; P04 shared immutable saved brief and audited sensitivities with explicit unavailable states.
- [ ] Structured briefs/recommendations/risks/catalysts/invalidation across remaining AI surfaces.
- [ ] Deterministic numerical/date/currency/period/scenario checks against evidence; surface unsupported or contradictory claims.
- [ ] Shared grounded renderer and clickable source blocks across chat, snapshots, reports and committees.

**Acceptance:** material numerical claims map to evidence or labelled estimates; invalid periods/citations fail visibly; AI cannot overwrite facts/calculations; saved inputs audit the conclusion.

### R05 - Domain extraction

**Impact: high. Effort: high.** Focused transports/history/validators exist; duplicate active Equity Report names were removed. Major modules remain large: Equity Report ~5,707 lines, portfolio decision engine ~1,893, portfolio data sources ~1,140 at this audit.

- [x] New history adapter and focused safety/constraint boundaries.
- [x] Extract shared quarterly collection, audited metrics/workflow and bounded model packets with compatibility entry points (AAFA-6).
- [ ] Characterization tests before extracting Equity Report retrieval, normalization, scoring, narrative, exports and rendering.
- [ ] Extract portfolio policy/signals/constraints/synthesis/validation with stable interfaces.
- [ ] Remove provider HTTP from primary pages; consolidate formatting, parsing and report components.

**Acceptance:** materially smaller mixed modules, stable tested public interfaces, and equivalent report outputs before/after extraction.

### R06 - Workflow protection

P02 adds 19 focused offline cases for saved metadata, mixed-offset retrieval ranges, safe links, escaped shell markup, actual saved Introduction range changes and V2 ordinary reruns. Broader browser/full-suite acceptance is recorded separately; universal interaction and CI criteria remain open.

Saved V2 timestamp/reuse interactions have 23 offline cases; the isolated AAFA-5 release inventory is 108 passing cases (V-20261004-01). Remaining workspace/CI criteria stay open.

**Impact: high. Effort: medium-high.** Latest full inventory is 430 guarded passing offline cases (V-20261010-P05, independently run in the installed local app environment). Earlier inventories and environment-specific failures remain dated historical evidence; V1/V2 recovery and market controls have direct interaction protection.

Contributor-tooling follow-up D-20261004-02 documents a verified local Jira MCP access route for the feature team; it does not satisfy the application interaction or CI criteria below.

- [x] Offline core/recovery/UI cases and market repair contracts.
- [x] Recorded/synthetic research financial, sector, audit, prompt-budget, legacy and export regressions plus fresh V1/V2 browser interaction (AAFA-6, V-20261004-04).
- [x] 53 V2 quarterly TTM, provider/tool isolation, comparison and UI/PDF unit cases (2026-10-03); full-workspace interaction coverage remains unmet.
- [ ] Unit/contract boundary coverage for scoring, filters, optimizer math, periods/currencies and missing/negative/short histories.
- [ ] Success and empty/failure interactions for every workspace and navigation action.
- [ ] Mocked discover -> snapshot -> research -> deep research -> portfolio workflow.
- [x] P05 defines `.github/workflows/offline-release.yml`: Python3.11/3.12 constrained install/pip check, guarded full tests, compile/import and safe artifacts; separate Docker health/non-root/derived workflow job.
- [x] P05 synthetic discovery -> Guided annual plan -> independently saved Deep brief, partial failures, counted explicit actions, saved immutability, two-session isolation and all-eight readiness/render smoke.
- [ ] Execute CI/clean-install/Docker gates successfully; lint/format/type gates and exhaustive workspace success/failure coverage remain open.

**Acceptance:** each workspace has successful and failed/empty interactions, no paid tests, and CI blocks routing/provider/export/weight regressions.

### R07 - Performance and cost

**Impact: high. Effort: medium-high.** Cached evidence, bounded requests, saved analyses and V2 stage profiles exist.

- [x] Isolated Economy/Balanced/Maximum Quality pilot, compact packets and labelled usage estimates.
- [x] Introduction chart ranges/settings reuse separate five-minute intraday/one-hour daily caches; indicator changes make zero model calls and explicit technical analysis preserves prior results on failure (AAFA-7).
- [x] Complete serialized four-company evidence and quick/committee packet budgets retain substantive balanced evidence and disclose omissions (AAFA-6); full dollar-cost enforcement remains open.
- [ ] Cold/warm latency, provider/model call counts, prompt/output size baselines and measurable budgets by workspace.
- [ ] Evidence-content/freshness-aware reuse, bounded batching/concurrency and explicit refresh.
- [ ] Complete CrewAI/model cost attribution, unknown-price handling and enforceable pre-run/run ceilings.
- [ ] Rerun/navigation/download paid-call regression checks and a scored V1/V2 comparison.

**Acceptance:** no unnecessary warm-cache calls; standard research <=3 model calls unless recovery; all-stage cost is included or clearly unknown; latency is visible and the economical route meets quality criteria. Claimed savings require measurements.

### R08 - Portfolio decisions and monitoring

**Impact: high. Effort: high.** Optimizer, AI manager, risk/regime analyses, constraints and monitoring exist; cap arithmetic has targeted protection.

- [x] Cap-safe constrained allocations with residual cash.
- [ ] Canonical imported tickers/quantities/cost basis/account/cash and unified optimizer/manager holdings model.
- [ ] Current/target weights, reconciled trades/capital, turnover, tax/slippage assumptions, exposures and risk contributions.
- [ ] Explicit benchmark/window/frequency/risk-free/return basis; scenario/stress and attribution methodology.
- [ ] Saved decision snapshots and evidence/constraint explanations for recommendation changes.

**Acceptance:** trades reconcile within tolerance, corrections are deterministic/explained, assumptions are visible and every proposed trade traces to evidence/constraint/objective.

### R09 - Operating evidence and evaluations

**Impact: medium-high. Effort: medium.** Sanitized events/request IDs, Deep Research stage diagnostics and five V2 scenario fixtures exist.

- [x] Local event safety/timing and versioned large-cap/sparse/same-sector/cross-sector/missing-data fixtures.
- [ ] Request IDs spanning UI/providers/tools/models/exports; cache/error/token/cost telemetry across the app.
- [ ] Execute evaluation for factual/numerical/citation/risk/readability/latency/cost criteria, including adverse news.
- [ ] Quality thresholds before provider/model default changes and privacy-conscious feedback/issue capture.

**Acceptance:** failed actions are traceable without secrets; releases compare fixed scored fixtures; defaults meet accuracy/latency thresholds; errors offer actionable recovery.

### R10 - Deployment and documentation

**Impact: medium-high. Effort: medium.** Current README, subsystem guide, requirements/constraints, non-root Docker setup and project skills are present. This audit repairs documentation organization and stale test claims.

- [x] Eight-entry workspace documentation, living status ledger and contributor skills.
- [x] P05 direct runtime manifests agree; newspaper4k namespace conflict removed and Python-specific NumPy constraints defined.
- [ ] Verify clean supported-Python installs and reproducible transitive dependencies; installed pip check is not clean-install proof.
- [ ] Local/test/production profiles and operational key/capability/freshness matrix.
- [ ] Dependency/secrets/HTML/URL/export/container checks; accessibility/responsive/onboarding/troubleshooting.
- [x] P05 runtime/derived-image CI definitions and protected-preview/secrets/spend/isolation/rollback runbook in `docs/DEPLOYMENT.md`.
- [ ] Execute Docker health/non-root/derived workflow and remote CI; verify chosen host/access/rollback. Release versioning, migration/backup and complete operations remain open.

**Acceptance:** documented clean setup/test/start works; Docker CI passes; docs match runtime limits/paid actions; no known secret/debug artifact/mojibake remains. Local imports and a healthy earlier server alone do not satisfy this.

## Delivery sequence and success measures

- **Milestone A - Trusted data:** R01-R02.
- **Milestone B - Connected, grounded research:** R03-R04.
- **Milestone C - Maintainable and tested platform:** R05-R07.
- **Milestone D - Portfolio product and production readiness:** R08-R10.

Begin with canonical provider records/contracts, then consistent data-quality display and intent-bearing context. Add tests with each slice. V2 quality/cost experiments stay isolated while these foundations mature.

Track metric provenance coverage; provider failure/partial recovery rate; cold/warm render latency; cross-page completion; citation/numerical validation; calls/tokens/cost per task; workspace interaction coverage; portfolio reconciliation; user usefulness/trust. Targets and measured baselines must be dated, not invented.

**Non-goals until R01-R06 are complete:** more loosely integrated providers, autonomous brokerage execution, more agents as a quality proxy, sensitive durable portfolio storage without privacy/authentication design, or mobile-native expansion before responsive workflows are reliable.

## Documentation boundaries and design notes

- AGENTS: durable engineering rules and maintenance procedure. PLAN: current implementation and dated proof. README: user setup/workflows. [DEEP_RESEARCH.md](DEEP_RESEARCH.md): subsystem behavior.
- [Cost optimization TODO](TODO_DEEP_RESEARCH_COST_OPTIMIZATION.md) is the original design checklist, not a completion ledger; V2 status and unmet acceptance are recorded here.
- [Historical code review](docs/code_review.md) retains the September findings and remediation history; its old environment/test counts are not current verification.
- Shared transport is a foundation for canonical adapters, not a substitute for them. Existing session handoffs are a foundation for typed context, not that model itself.
- V2 is an isolated experimental boundary. Promote defaults only after executed quality/cost evaluation; keep V1 recovery behavior protected.

## Template for continuing updates

For each meaningful change, update the relevant matrix and Rxx checkboxes, then append:

```text
Delivery ID / date:
Related roadmap IDs and workspaces:
User outcome and acceptance criteria:
Implementation approach / architectural decision:
Source paths and test paths:
Commit or working-tree status:
Verification ID, commands, environment, results:
Mocks/live services and checks not performed:
Remaining risks, follow-up IDs and next acceptance step:
```

A verification entry should retain the exact date/result and scope even after test counts grow. A delivered subitem can be checked while its parent milestone remains partial. Do not erase unverified work by describing a whole feature as done.

## Delivery 2026-10-02: Project-local code review skill

- Related roadmap: R07 contributor verification workflow; no roadmap acceptance criteria or milestone status changed.
- Outcome: moved the explicitly invoked `code-review-agent` from `C:/Users/andna/.codex/skills/` into `.agents/skills/code-review-agent/` so its instructions and picker metadata can be tracked with this project.
- Approach: preserve independent reviewer delegation and explicit-only invocation; save UTF-8 reports under `docs/reviews/` using `YYYY-MM-DD-task-slug.md` and numeric suffixes on collisions. Exclude generated review reports from review inputs; preserve existing reports and implementation files.
- Sources: `.agents/skills/code-review-agent/SKILL.md`, `.agents/skills/code-review-agent/agents/openai.yaml`, `docs/PROJECT_SKILLS.md`, `README.md`, and contributor skill count in `AGENTS.md`. Working-tree changes only; not committed or pushed. Earlier unrelated changes preserved.
- Verification: `C:/Users/andna/anaconda3/python.exe C:/Users/andna/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/code-review-agent` passed; `git diff --check` passed with line-ending notices. Documentation/instruction changes only; no new tests, app startup, browser interaction, live providers, or paid calls performed. Test inventory unchanged.
- Remaining limits: picker discovery may require reopening the project; independent review execution and collision handling were inspected as instructions, not exercised in a new review. The separate installed `independent-reviewer` plugin remains outside the project and was not moved.
## Delivery 2026-10-02: Three-agent code review and Jira triage

- Related roadmap: R06 verification/agent workflow support; no application coverage target or parent milestone marked complete.
- User outcome: an explicit project-local `code-review-team` skill coordinates an independent code reviewer, summarizer/prioritizer, and Jira writer. Accepts scoped reviews/audits and dry runs; saves uniquely named team reports in `docs/reviews/`.
- Publication rules: defaults to the user's AAFA project at `bigmeatpete717.atlassian.net`; ranks evidence-based findings, merges shared root causes, checks Jira duplicates, and caps the whole run at six create attempts. Records attempts durably before writes, reconciles uncertain results without blind retries, and retains drafts when access is blocked. Calling the skill authorizes selected Jira creation; creating the skill does not invoke it.
- Implementation: `.agents/skills/code-review-team/SKILL.md` and `agents/openai.yaml`, with explicit-only invocation. Updated `docs/PROJECT_SKILLS.md`, `README.md`, contributor count in `AGENTS.md`, and current contributor workflow status above. The existing single-reviewer skill remains available. Working tree only; no commit/push or Jira writes.
- Verification: Anaconda Python 3.12.7/PyYAML 6.0.3; `quick_validate.py .agents/skills/code-review-team` passed, UI YAML parsed and explicit-only policy checked, and `git diff --check` passed with line-ending notices. An independent validation subagent inspected scenarios for scoped dry runs, zero findings, duplicates/reserves, uncertain creation, concurrent source edits, unavailable Jira, and resume behavior without executing the skill. Its two findings prompted durable pre-write attempt logging and refreshed report/source checks after revalidation.
- Checks not performed: actual three-stage review execution, live Jira metadata/authentication/creation, browser workflow, app tests/startup/health, paid services. This is instruction/documentation validation; test inventory unchanged and no live Jira success claimed.
- Remaining limits: live publication requires authenticated Jira tools or an authenticated `agent-browser` session and supported project fields. Skill discovery may require reopening the project. Cap and retry behavior are instructions, not an installed Jira service or programmatic enforcement layer.
## Delivery 2026-10-03: Feature development team skill

- Related roadmap: R05 contributor architecture/workflow support and R06 verification guidance; no product milestone or coverage acceptance marked complete.
- User outcome: separate project-local `feature-development-team` with planner, builder, and independent verifier/Jira writer roles. Plan-only runs assess scoped improvements; build runs implement authorized outcomes and independently verify them. Reports use unique `docs/features/YYYY-MM-DD-task-team.md` names.
- Boundaries: explicit-only invocation; creating this skill does not run it. `drafts only` disables Jira writes; `dry run` disables implementation and publication. Jira defaults to AAFA, with duplicate checks, durable pre-write ledger, and five creation attempts across an interrupted/resumed run. Existing tickets, commits, pushes and deployments require separate authorization. Unrelated working-tree changes preserved.
- Sources: `.agents/skills/feature-development-team/SKILL.md`, `agents/openai.yaml`, `docs/PROJECT_SKILLS.md`, `README.md`, contributor count in `AGENTS.md`, and this status record. Working tree only, not committed or pushed.
- Verification: Anaconda Python 3.12.7 and PyYAML 6.0.3; `quick_validate.py .agents/skills/feature-development-team` passed; UI YAML parsing/explicit-only policy checked; `git diff --check` passed with existing line-ending notices. Independent instruction validation covered planning/publication, build/drafts, build/dry-run, missing scope, dirty target files, fix/reverify, empty queue, duplicate candidates, timeout and resume cap. Its two findings were addressed with original-run reuse and per-ticket source freshness checks.
- Not performed: actual feature-team execution, app tests/startup/health/browser, live Jira authentication/metadata/creation, or paid/provider calls. Skill/documentation-only validation; test inventory unchanged.
- Remaining limits: publication needs authenticated Jira tools or browser access; instructions are not programmatic Jira enforcement. Feature acceptance and runtime verification must be established when this workflow is invoked for an actual outcome. Skill picker discovery may require reopening the project.
## Delivery 2026-10-03: Financial data handoff in the existing feature team

- Related roadmap: R01 data/provenance guidance and R06 contributor verification support; instruction-only delivery, with all existing workspace and parent roadmap statuses retained. No application adapter or automated coverage acceptance completed.
- User outcome: the existing `feature-development-team` now runs financial data specialist -> planner -> builder -> independent verifier/Jira writer. The specialist maps task-specific FMP routes, ticker/variant coverage, fields, fiscal basis, currency/units, dates, restrictions and saved samples to D IDs. Builder/reviewer handoffs preserve these requirements and send contradictory or new assumptions back for clarification.
- Sources: `.agents/skills/feature-development-team/SKILL.md`, its `agents/openai.yaml`, `docs/PROJECT_SKILLS.md`, `README.md`, and this record. Working tree only; pre-existing changes preserved; no commit/push. No overlapping team or additional skill created.
- Boundaries retained: explicit invocation, plan-only/build/dry-run/drafts modes, five Jira creation attempts, duplicate checks, durable publication ledger, independent fix/recheck loop. Editing the skill does not execute the team. Live recollection requires separate explicit authorization and remains outside offline verification.
- Verification: Anaconda Python 3.12.7 / PyYAML 6.0.3; `quick_validate.py .agents/skills/feature-development-team` passed; UI YAML parsed and explicit-only policy preserved; `git diff --check` passed with pre-existing line-ending notices. Instruction inspection checked unrelated-data tasks, missing references, legacy restrictions, changed data requirements and publication-role numbering. No new test inventory measured.
- Not performed: executing the four-agent workflow, live provider collection, paid model calls, Jira authentication or publication, app tests/startup/health/browser checks. Remaining limits: actual skill discovery and end-to-end team execution depend on the client; FMP reference evidence is dated and not a guarantee of entitlement or field semantics.


### Delivery 2026-10-03 - V2 quarterly-derived TTM (working tree)

R01/R02/R04/R06/R07: delivered a bounded V2 financial-basis improvement: validated four-quarter flow aggregation, matched balance snapshots, supported positive-denominator/currency-aligned valuations, eight-quarter prior-TTM growth, annual-history preservation, quarterly-only shared REST collection, TTM-free targeted investigation allowlist, methodology-versioned cache and disclosed legacy recovery. V1 provider behavior remains unchanged. Sources/tests: `deep_research/quarterly_ttm.py`, `deep_research/v2_data.py`, `deep_research/v2_workflow.py`, `tests/test_quarterly_ttm.py`, compact AAPL fixture under `tests/fixtures/`. Existing unrelated working-tree edits are retained. Roadmap acceptance criteria for universal provenance, typed cross-page context and end-to-end accuracy remain open.

Builder verification: Anaconda Python 3.12.7; first focused quarterly/V2 recovery subset: 44 passed, 100 dependency warnings, 83.52s. Synthetic and saved-response inputs only; no live provider/model calls. Expanded focused verification, full inventory, fresh health/browser checks and independent review are recorded by the coordinator after final source stabilization; do not treat the earlier subset as their evidence. Remaining limitations: no live entitlement check; conservative ambiguous-restatement rejection; unsupported provider formulas omitted; quote/statement dates differ for simplified market valuation.

Review corrections (2026-10-03): prior-TTM growth requires eight consecutive quarters with one security and currency, including the boundary between current and prior windows; invalid prior history preserves current TTM. Quote/profile security identities must match the requested ticker. Calculated ROE/ROA use TTM net income divided by the average of positive matched end and same-quarter prior-year equity/assets, with the balance dates and formula retained; this is a two-snapshot average, not a provider-equivalent quarterly average. ROIC and per-share provider formulas remain unavailable.

Additional review corrections: V2 comparison uses the same positive-denominator margin/intensity policy as its calculation helper, including sector aliases; zero/negative revenue cannot reintroduce invalid margins. The saved-app-data control is visibly disabled with an explanation because all unverified cross-workspace packets are excluded in this mode.

Currency display correction: V2 comparison retains separate income/cash-flow TTM and selected-period dates/currencies. Derived-only formatting uses each financial family currency rather than the selected annual income currency; independent cash flows survive mismatches while cross-statement ratios stay unavailable. Builder review-fix checks: quarterly suite 31 passed in 7.35s; V2 recovery interaction suite 28 passed in 79.97s (100 dependency warnings). Offline fixtures/mocks only, Python 3.12.7. Compile and diff validation passed. Coordinator maintains final full-suite/health/browser/independent-review evidence separately.

Final renderer/export review corrections: V2 fraction-valued margins, ROE/ROA and earnings/FCF yields always scale by 100, including values greater than 2; growth and expense intensities remain percentage points. V1 retains its earlier formatting. PDF financial-basis FCF uses the cash-flow currency and explicitly annotates the cash-flow period end separately from income. Builder focused quarterly/shared-renderer/Deep Research suite: 94 passed in 65.65s, with a follow-up actual PDF text-extraction assertion recorded separately by the coordinator. PDF table cells are independently checked for EUR/JPY cash-flow amounts, dates and 250% ROE; no paid or live calls.

### 2026-10-04 - R02 / R06 saved V2 result generation age (AAFA-5)

Working-tree delivery adds a dedicated `deep_research/v2_timestamps.py` helper and bounded V2 UI hooks for an explicit operation-completion timestamp, UTC display and elapsed age. Evidence-only/incomplete returns are labeled as saved results; this timestamp is distinct from evidence freshness and report completeness (D01-D03). Legacy timestamps remain unavailable rather than inferred. History, cache reuse and ordinary reruns preserve saved time; optional decisions and finalization do not advance it. Sources: `src/langgraphagenticai/ui/deep_research_v2_tab.py`, `tests/test_deep_research_v2_timestamps.py`. This delivers only the saved-generation-time subitem; universal provenance/freshness and remaining R02/R06 acceptance criteria stay open. Fresh verification and release evidence are recorded separately by the feature coordinator.


### V-20261004-01 - Saved V2 result generation age (isolated release)

AAFA-5 / R02 / R06: the release candidate applies only the timestamp enhancement to committed baseline `619494c`; earlier uncommitted V2 recovery/quarterly work remains local and is excluded. The new helper and 23 timestamp tests are identical in the working tree and isolated release. UI integration uses each version's existing manager factory, with equivalent completed run/resume hooks and read-only rendering.

- Full isolated release inventory: `PYTHONPATH=src; python -m pytest -q` -> **108 passed**, 127 existing Altair/jsonschema deprecation warnings, 57.32s. Anaconda Python 3.12.7, pytest 7.4.4, Streamlit 1.64.0. Offline mocks/fixtures; no paid model or live financial-provider calls. This is the release inventory, not a remeasurement of the larger uncommitted working tree.
- Working-tree builder evidence: 23 dedicated timestamp tests passed (28.14s); earlier combined run of 22 timestamp + 28 recovery tests passed (50 tests, 49.74s); two temporary tests for pre-existing finalization/decision-retry controls passed (11.56s). Temporary tests are not part of the release inventory.
- Independent verifier: corrected candidate's 23 timestamp tests passed (30.98s); affected modules compiled and diff checks passed. F01 encoding error in candidate preparation was corrected and rechecked; no unresolved introduced defect or follow-up ticket candidate.
- Final candidate: `python -m compileall -q app.py src` and import of app/main/timestamp helper/V2 UI passed. Fresh full-app Streamlit startup and `/_stcore/health` passed on port 8530; offline harness health passed on 8531. Health is separate from page-interaction evidence.
- Fresh browser test used the actual candidate V2 UI with synthetic saved modern/legacy results and mocked research factory; HTTP/model boundaries blocked. History selection displayed explicit legacy-unavailable fallback. A new synthetic operation recorded UTC time, saved reuse retained it, and full rerun/tab navigation/memo download retained the exact timestamp with research operations=1 and external calls=0. Browser screenshots/harness stayed outside the repo; harness PDF was a placeholder, and actual PDF generation was not retested for this metadata-only change.
- Scope limitations: no live financial-quality run, clean dependency installation, Docker build or hosted deployment verification. Existing Hugging Face Space is identified but has no local authenticated credentials; GitHub has no Actions workflow/deployment records. AAFA-5 remains In Progress until deployed verification. No follow-up tickets were warranted. Broad R02/R06 acceptance criteria remain open.


### Local deployment verification - 2026-10-04

The user clarified that deployment means updating the local application; Hugging Face publishing is outside this run. Local source changes are installed in the existing working tree. A fresh local app on port 8533 returned `ok` from `/_stcore/health`; affected modules compiled and app/main/V2 imports passed. A separate offline browser harness on 8532 exercised the actual working-tree V2 UI: modern/legacy history, new generation, saved reuse, Sources tab, memo download and full rerun. UTC timestamp remained `2026-10-04T23:34:54...` across reuse, with research operations=1 and external calls=0. The synthetic report/PDF boundary is mocked; no paid/live financial calls. The earlier isolated-release checks remain separate evidence. This verifies the requested local deployment, not a hosted release. AAFA-5 can complete after the verified scoped commit/push; no follow-up defect ticket was warranted.


### Final delivery ? 2026-10-04

Local deployment was verified as requested; no Hugging Face deployment was performed. Feature commit `31580ef0dd667357bd836849aea9c6d5906eaaf3` was pushed to `origin/main`, and its remote SHA was verified. AAFA-5 received verification comment 10108 and was transitioned to **Done** after local deployment verification. No substantive unresolved issues required follow-up tickets. Unrelated working-tree changes were preserved.

### Delivery 2026-10-04 - Shared Deep Research Serper news coverage (working tree)

R02/R04/R06 bounded delivery: both Deep Research workspaces expose saved Serper news coverage with requested lookback, usable article/company counts, retrieval timestamps and missing/partial states. V2 displays key configuration and news-control guidance. Serper invalid collections become structured missing evidence while successful news retains the transport retrieval timestamp; existing endpoint, key-header and timeout contracts are preserved. Saved results/recovery do not recollect news. Sources: `tools/serper_tools.py`, `deep_research/manager.py`, `ui/research_news.py`, both Deep Research page modules; offline regressions: `tests/test_serper_deep_research.py`. Prior dirty/untracked work is preserved and is not attributed to this delivery. Broad roadmap acceptance remains partial.

Verification for this delivery is recorded separately after source stabilization by the feature-team coordinator in `docs/features/2026-10-04-serper-deep-research-team.md`. No commit, push, deployment, live financial-provider call, paid model call or freshness guarantee is part of this scoped implementation. Existing dated full-suite inventories are retained.

Scoped existing-test adjustment: `tests/test_deep_research_ui.py` now expects the partial-news warning after successful review recovery when its saved fixture covers AAPL but not the requested MSFT; review warnings still clear. This reflects the newly visible coverage state, not a remaining review failure.

Builder verification (2026-10-04): Anaconda Python 3.12.7, pytest 7.4.4, Streamlit 1.64.0; `PYTHONPATH=src python -m pytest tests/test_serper_deep_research.py tests/test_deep_research.py tests/test_deep_research_ui.py tests/test_deep_research_v2_recovery.py -q`: **92 passed, 100 dependency warnings, 73.87 seconds**. Synthetic/mocked HTTP, model and financial boundaries; no live calls. Focused compileall and imports of all changed application modules passed; `git diff --check` passed with existing line-ending notices. Full-suite inventory, fresh startup/health/browser verification and independent review remain coordinator checks and are not claimed by this builder entry.


### V-20261004-02 - Serper news coverage in both research versions

- Fresh root inventory: `PYTHONPATH=src;<temporary guard directory> python -m pytest -q -p offline_guard` completed with **214 passed, 2 failed, 128 warnings in 89.56s** (216 collected cases). This includes 23 new Serper tests, the existing application tests, and four untracked FMP reference tests. The suite is not fully passing. Both failures are the existing reference collector's certificate export (`ssl.create_default_context().get_ca_certs(binary_form=True)` raises `truststore.NotImplementedError`), outside the Serper delta. Market modules' existing global truststore injection and reference collector source were unchanged. Temporary autouse guard blocked unmocked Requests/httpx sends; no live financial/model calls.
- Builder focused suite: 92 passed, 100 dependency warnings, 73.87s. Reviewer independently ran 23 Serper tests: all passed, 22.45s. Python 3.12.7 / pytest 7.4.4 / Streamlit 1.64.0 in installed Anaconda environment.
- Coordinator compileall `app.py src` and imports of app/main, Serper adapter, manager, shared news UI and both page modules passed. Diff validation passed; baseline hashes confirmed unrelated source/test files preserved.
- Fresh app startup/health passed on port 8534. Offline actual-page browser harness health passed on 8535. Browser exercised V1 full/partial coverage and V2 full/partial/zero/disabled news, missing-key help, Sources navigation and full rerun. Coverage showed saved UTC retrieval date; unexpected provider/research calls stayed zero. Synthetic saved data and blocked network/factories; screenshots and harness outside repository. Fresh factory-to-HTTP behavior is established by mocked integration tests, not a live browser research run.
- No live Serper entitlement/credits check, live model run, clean install, Docker/hosted deployment or new export artifact validation. No source commit/push requested for this run. Independent review found no unresolved Serper defects; Jira queue empty, zero creation attempts/writes. Fourth distinct agent was unavailable under environment thread limit, so the planner was reused as reviewer independently of the builder. R02/R04/R06 remain partial beyond this slice.

### Serper follow-up correction (2026-10-04)

The user reported live AAPL and MSFT news evidence saying ?No matching search results returned,? alongside two separate missing investigation records. No live reproduction was authorized or performed. The earlier company-news query appended many topic words, which may restrict matching; that is a hypothesis, not an established live root cause. Company news now queries only company name plus ticker (ticker alone if the name is unavailable), preserving the same news endpoint, requested lookback, five-result cap, bounded timeouts and include-news gate. No additional requests or web fallback were introduced. The adapter now distinguishes a genuinely empty collection from a missing expected response collection and a nonempty collection whose rows lack usable safe links. Provider/model failures in investigation remain separate evidence gaps.

Previously saved results are preserved, including their original news gaps. Select **Force fresh research** in V2, or start a new V1 research run, to apply the new query; reopening or reusing a saved result does not silently refresh news or incur calls. Offline tests verify exact company/ticker and ticker-only queries and the three response diagnostics. These checks cannot establish live news coverage, entitlement or the cause of the reported empty responses.

Follow-up builder verification (2026-10-04): Python 3.12.7 / pytest 7.4.4; `PYTHONPATH=src python -m pytest tests/test_serper_deep_research.py tests/test_deep_research.py -q`: **63 passed in 22.00 seconds**, with synthetic HTTP/model/financial boundaries only. Focused compilation, adapter/manager imports and diff validation passed. No live query reproduction, new startup/browser check or full-suite inventory is claimed by this follow-up entry.


### V-20261004-03 - Serper empty-news query correction, actual local app environment

The user reported live AAPL/MSFT news gaps with the generic empty-results message. Initial queries now use company name plus ticker (or ticker alone), removing the compound topic list; this is a bounded relevance correction, not proof of the live root cause. Missing expected collections and nonempty collections with no usable safe source links now have distinct sanitized diagnostics; genuine empty lists retain the empty-results message. Request count, news/search endpoints, lookback, five-result limit and timeouts remain unchanged. Saved old evidence is retained; restart Streamlit and explicitly select Force fresh research in V2 to test the correction. App-finance investigation gaps are separate and were not attributed to Serper.

- Builder: 63 focused Serper/core tests passed in 22.00s using Anaconda Python 3.12.7. Independent reviewer: 31 Serper tests passed in 22.35s; final scoped source approved, zero Jira candidates/attempts.
- Fresh full inventory in the user's running-app environment (`.../Agentic_AI_Financial_Analyst_V3/venv/python.exe`): **224 passed in 55.21s**, Python 3.12.0, Streamlit 1.61.1, pytest 9.1.1. Command: `PYTHONPATH=src;<temporary guard directory> python -m pytest -q -p offline_guard`; temporary guard blocks unmocked Requests/httpx sends. This includes 31 Serper tests and the FMP reference tests. The earlier Anaconda inventory's two truststore failures did not recur in this environment; retain earlier evidence as environment-specific history.
- Changed modules compiled/imported successfully in the user's environment. Existing app process health returned `ok` on port 7860; this is an existing-server health check, not a new startup/browser run. Earlier actual-page synthetic browser evidence applies to unchanged coverage UI; no fresh live news/model/browser research or entitlement/credit test was performed.
- Source remains local/uncommitted. No additional provider calls, fallback providers, live financial/model calls, Jira writes, commit/push or deployment. Source confidence is offline; live query success remains to be checked by the next explicit fresh user run.


### GitHub synchronization - 2026-10-04

User authorized publishing the current project state: V2 recovery, quarterly-derived TTM and shared render/export corrections, Serper coverage/query diagnostics, offline tests, contributor skills, delivery records and sanitized FMP reference material. Raw responses/request caches, scraped diagnostic HTML and local CA certificates remain local and are ignored. Validation reuses the same unchanged source/test inputs from V-20261004-03: 224 offline tests passed in the actual local app environment, affected compilation/import and health passed; earlier browser evidence retains its original recorded scope/date. Source synchronization does not establish hosted deployment. Final remote SHA will be verified after the commit/push.

### Delivery 2026-10-04 - Sector-aware audited Deep Research candidate (AAFA-6)

R01/R02/R04/R05/R06 bounded isolated candidate: shared fresh V1/V2 quarterly transport and calculation contracts, separate annual histories/future annual consensus, independently latest snapshots, matched beginning/end returns, canonical per-company sector projection, explicit units and full visible-metric audit/export. `sector-quarterly-audit-v2` rejects missing fiscal identity, inconsistent quarters/currencies and explicit nonstandalone durations; absent durations remain a disclosed standardized-route assumption. Saved legacy comparisons are preserved and labelled; universal typed provenance and AI prose numerical verification remain unmet. Sources: `deep_research/quarterly_data.py`, `research_metrics.py`, `research_workflow.py`, compatibility `v2_data.py`, `quarterly_ttm.py`, shared manager/prompt/presentation, both page factories and reload dependency order. Tests: `tests/test_sector_research_audit.py`, dated compact three-company fixture, quarterly/legacy recovery compatibility expectations. Product installation, full inventory and fresh health/browser/independent-review gates remain coordinator work; no commit/push/deployment or live providers were performed. Broad R01-R10 milestones remain partial.

Observed saved-sample reconciliation: AAPL FY2025 exact quarterly/annual flows; JPM revenue and PLD NI discrepancies retained diagnostically, cause unknown. Unsupported sector/per-share/dividend/inventory/ROIC formulas remain explicitly unavailable. Quote/estimate currency inference and differing valuation dates are disclosed. Prior verification inventories remain historical and unchanged until a fresh full suite is measured.

Builder verification for the isolated candidate: project venv Python3.12.0 / Streamlit1.61.1 / pytest9.1.1. Combined new audit/quarterly/core/Serper/V1 UI/V2 recovery command: **189 passed in53.17s** after compact-context fixes. Final updated audit/quarterly/V2 timestamp/V2 recovery command: **141 passed in30.43s**, including the new methodology-aware timestamp fixture and shared safe investigation allowlist. Recorded/synthetic inputs and mocked financial/model transport only; no live API or paid calls. `compileall` over app/src/new tests, app/main/new-module imports and `git diff --check` passed. Parent full-suite inventory, final startup/health/browser checks and independent review remain separate gates; earlier interim checks are not final delivery evidence. Root product files remain untouched by this builder.

Independent-review corrections (isolated candidate, 2026-10-04): metric audit inputs now identify both actual annual CAGR endpoints, beginning/end ROE/ROA snapshots, both annual forward-growth observations and actual estimate/target aliases with their source IDs, dates, values and currencies. Explicit YTD/as-reported/unknown selected-period flows are excluded from comparable latest metrics and model evidence; trends require compatible standalone durations and plausible prior-year dates. Model contexts select balanced substantive company evidence within the serialized budget, retaining omitted sources in the saved audit rather than emitting empty excerpts. `model_packets.py` shares per-company sector projection and compact audited units across analysis, quick decisions and full committee packets, bounds the complete JSON packet, and distinguishes legacy assumptions. Four-company18k/22k evidence and three/four-company10k decision/committee cases are covered offline. Earlier verification remains historical; final correction checks are recorded separately.

Correction verification (isolated candidate): six focused audit/quarterly/core/V2 helper/recovery/timestamp modules: **189 passed in122.62s**. Final audit-module check after actual-alias, both-observation and profile-currency-inference provenance updates: **49 passed in33.73s**. Project Python3.12.0; synthetic/recorded inputs only. App/src/new-test compileall and diff validation passed after final changes; prior app/main/model-packet imports passed. No live/provider/model calls or root product installation. The coordinator owns a fresh full-suite inventory and independent FID01-FID04 recheck on this frozen correction snapshot.


2026-10-04 FID03 recheck correction: model-context compaction now preserves category-specific nested investigation/transcript/DCF/peer payloads, financial trend values and dates, technical observations and price basis, and news content. Statement excerpts retain duration exclusions rather than treating narrative/tool schemas as financial statements. Four-company synthetic category regressions cover 18,000 and 48,000 character budgets alongside recorded financial/decision budget tests. Focused audit tests and compile checks are offline; parent final integration/browser verification remains separate.


### V-20261004-04 - Shared sector-aware research financial audit (AAFA-6)

Final isolated-candidate inventory: **276 passed in 64.91s**. Command: `PYTHONPATH=src;<temporary offline guard> python -m pytest -q -p offline_guard`, project Python **3.12.0**, Streamlit **1.61.1**, pytest **9.1.1**. Recorded/synthetic financial data and mocked transport/model boundaries; the guard rejects unmocked Requests/httpx sends. Includes **52 sector-audit cases**, earlier financial/recovery/UI/Serper suites and four reference cases. Tests do not establish full-workspace coverage or certify model-written figures.

Independent team verification approved FID01-FID04 and supplemental provenance fixes: **105 guarded tests passed in 17.47s**; all thirteen sector-framework aliases were checked. Final test-only source-budget adjustment approved independently and **66 guarded recovery/audit cases passed in 15.78s**. New source selection retains balanced substantive company evidence, reports omitted sources, respects actual serialized limits and preserves saved evidence without mutation. Valid source-ID membership is tested; that assertion does not separately establish uniqueness.

`python -m compileall -q app.py src` and app/main/new-module imports passed; expected bare-runtime Streamlit cache warnings occurred. Fresh candidate `streamlit run app.py` on port8534 returned `ok` from `/_stcore/health`. Agent-browser isolated session exercised actual V1/V2 pages through an external recorded-data harness with provider/model sends and factories blocked: comparison/audit expansion, TTM figures, per-company sector masks, saved-history changes and legacy notices. No browser console errors. The audit CSV media endpoint returned HTTP200; its actual payload contained642 contract rows across AAPL/JPM/PLD with explicit units. Automated Chrome file-saving reported cancelled downloads, so browser file-save completion is unverified; served CSV contents and offline export tests passed. Server shutdown can emit Windows connection-reset warnings.

Earlier correction-stage failures are retained in the run report: one Windows temporary-file replacement error passed module/full retries; source-budget test was updated for explicit balanced omissions; independent review exposed and corrected audit provenance, duration and context-erasure issues. Final passing inventory supersedes those checks without erasing their history. No paid or live financial-provider/model calls, hosted deployment, commit or push. Root installation follows the verified candidate after baseline-preservation and scoped-copy checks. Broad R01-R10 acceptance remains partial. Run report: `docs/features/2026-10-04-sector-aware-research-ttm-team.md`.


Local installation verified (2026-10-04, AAFA-6): all159 baseline file hashes matched immediately before scoped application;25 candidate code/test/document files copied and every installed hash matched the verified candidate. Root app/source compiled and app/main imports passed. Fresh root Streamlit startup health on8534 returned `ok`; an external offline harness imported the installed root modules and exercised both V1/V2 comparison/audit views without provider/model calls or browser console errors. The existing user Streamlit session was preserved. Changes remain local/uncommitted; no GitHub push or hosted deployment. Test-server/browser resources are coordinator-owned and will be stopped after handoff. Final status is recorded in the linked run report and AAFA-6.

AAFA-6 completion confirmed after local verification: final Jira comment10113 records evidence/limitations; transition31 returned Done. Zero additional follow-up tickets. Scoped source remains local/uncommitted; coordinator verification servers/browser closed and user session preserved.


### 2026-10-04 - Introduction technical charts (AAFA-7)

User outcome: both market and company charts expose 1D/5D/1M/3M/1Y/3Y/5Y/10Y, configurable SMA/EMA/Wilder RSI/MACD/Bollinger indicators, a deterministic dated summary and explicit-action structured technical AI interpretation. The company chart no longer depends on the snapshot performance history. `providers/symbol_history.py` shares bounded single-source retrieval and range selection; `providers/market_history.py` preserves its public compatibility wrapper. Daily and intraday data cache separately, settings reuse history, latest observed sessions define 1D/5D, and partial/stale/unknown basis/timezone states are visible. Valid partial FMP data remains intact; fallback uses one separate Yahoo auto-adjusted series without stitching.

Focused domain modules `technical_analysis/indicators.py`, `evidence.py`, and `agent.py` define arithmetic, compact evidence/fingerprints, and bounded structured interpretation. `ui/technical_chart.py` shares controls/rendering, preserves provider wall-clock axis fields and original source timestamps, pads the finite price/overlay axis, isolates RSI/MACD panels and retains previous AI results with mismatch notices. One adapter call per cache miss uses existing shared FMP transport (up to two bounded retries); at most one Yahoo download follows if no usable FMP series exists. Indicator windows are observed bars, max500; EMA seeded from available history, Wilder RSI arithmetic and population-standard-deviation Bollinger convention are disclosed.

Scope: Introduction only; pre-existing Deep Research source/document edits retained. Local working-tree delivery; no commit/push/deployment. Saved FMP AAPL five-row intraday/daily observations support historical schema examples only; ten-year/index entitlement, complete trading-session coverage, provider timezone and adjustment remain unverified. Unsupported/insufficient indicator history stays missing. Structured schema/identity/citation membership does not certify every model-written numerical claim. Broad R01/R02/R04/R05/R06/R07/R10 acceptance remains partial.

Focused verification (builder, 2026-10-04): `PYTHONPATH=src;<temporary offline guard> python -m pytest -p offline_guard -q tests/test_introduction_technical.py tests/test_market_tabs.py`: **50 passed in23.54s**, project Python3.12.0, pandas3.0.5, Pydantic2.12.5, Streamlit1.61.1. All transports/models mocked; guard blocks Requests/httpx/curl_cffi sends. Includes all eight ranges on both surfaces, malformed/zero/nonfinite/duplicate/timezone/partial inputs, single-source fallback, cache reuse, independent indicator expectations, warmup, axes, fingerprint/schema/citation checks, invalid-MACD disabled action, explicit AI call count and saved mismatch/failure behavior. An earlier expanded test run had49 passes/one test-protocol assertion failure; its chart element name assertion was replaced with actual rendered-frame preservation evidence, then the50-case focused run passed. Earlier45-case pass remains historical.

Changed module/test compileall and changed imports passed; expected bare-runtime Streamlit cache warnings occurred. `git diff --check` passed (existing PLAN line-ending warning only). Full suite inventory, app/startup health and browser checks belong to the coordinator's fresh final verification and must be recorded separately before declaring acceptance complete. No live provider/model validation, clean install or hosted deployment performed. Run report: `docs/features/2026-10-04-introduction-technical-chart-team.md`.


AAFA-7 independent-review correction (FID-I01, 2026-10-04): Introduction history now rejects future timezone-aware timestamps against the exact actual UTC instant, and rejects timezone-unknown naive records only when their calendar date exceeds the current UTC date. Today's naive wall-clock values are retained because their same-day ordering against UTC is unverifiable; no source timezone is fabricated. Rejected observations cannot define chart as-of, warmup, range coverage or model evidence, and excluded-record counts survive FMP-to-Yahoo whole-series fallback. README records this date policy. Four added regressions cover future/current naive dates, aware-offset exact boundaries, range/indicator/AI contamination and exclusion-count accumulation. Builder guarded focused verification: **54 passed in34.30s** (`tests/test_introduction_technical.py`, `tests/test_market_tabs.py`), project Python3.12.0, all provider/model boundaries mocked. Changed provider/test compileall and provider import passed; diff check passed with existing PLAN line-ending notice. The coordinator's318-case passing full run preceded this correction and remains historical; fresh final inventory and independent recheck are required separately.

### V-20261004-05 - Introduction technical charts (AAFA-7)

Final local working-tree inventory after FID-I01: **322 passed in 241.76s**. Command: `PYTHONPATH=src;<temporary offline guard> python -m pytest -q -p offline_guard`; project Python **3.12.0**, Streamlit **1.61.1**, pytest **9.1.1**, pandas **3.0.5**, Pydantic **2.12.5**, Altair **6.2.2**. Includes 46 new technical-chart cases plus the existing inventory. Synthetic/recorded inputs and mocked financial/model boundaries; temporary guard blocks unmocked Requests, httpx and curl_cffi transport. The pre-correction 318-case run passed in135.77s and is historical.

Builder final focused checks: **54 passed in34.30s**. Independent verifier checked actual FMP135/136 samples, contracts, arithmetic, source basis, axes, explicit agent behavior and corrected future-date filtering. Its initial final scoped run had53 passes and one existing AppTest3-second timeout under concurrent verification; isolated rerun of that interaction and four future-date regressions passed **5 cases in32.70s**. No product exception or model-call failure occurred; final full suite passed, and FID-I01 was independently approved. No unresolved substantive findings or additional Jira tickets.

Final `python -m compileall -q app.py src` and imports of app/main/history/chart/agent passed. Fresh root Streamlit8536 and fresh external offline Introduction harness8537 each returned `ok` at `/_stcore/health` after the correction. Agent-browser isolated session exercised actual root renderers using synthetic raw provider histories and recorded model outputs, with external transports blocked: **all eight ranges on both market/company charts**, all five indicators, SMA50, correct short/long date axes, separate oscillators, saved company summary, explicit mock technical action once per surface, unchanged model count on ordinary controls, and mismatch notices. Browser errors were empty. Source timestamps and unknown adjustment/timezone remain labelled. Screenshots and harnesses are outside the repository.

Browser automation initially timed out during cold imports, encountered Streamlit's sticky toolbar during an automated company-button click, and asserted before a streamed rerun finished; waiting for actual rendered state and scrolling the Streamlit container resolved these harness issues. They are not concealed as passing first attempts. The independent AppTest timing issue is retained above. No live financial providers or paid models, numerical prose certification, long-range entitlement check, clean-install/container test, commit, push or hosted deployment. Existing user sessions and prior Deep Research edits are preserved. Local delivery and final Jira status are recorded in `docs/features/2026-10-04-introduction-technical-chart-team.md`.

AAFA-7 completion confirmed after final local gates: comment10116 records actual evidence and limits; transition31 returned Done. No additional tickets. Coordinator-owned verification servers8536/8537 and named browser were closed; existing user sessions preserved. Scoped local changes remain uncommitted.

### D-20261004-08 - Current engineering guidance and GitHub synchronization

User outcome: publish the current verified local application and engineering record to the existing GitHub repository. AGENTS implementation orientation now identifies the shared research financial/sector/audit/model-packet boundaries, legacy and news timestamp contracts, eight Introduction chart horizons, configurable technical-domain/agent modules, price source/date policies and current verification limits. PLAN's current status and dated inventory include AAFA-6 and AAFA-7 without replacing historical evidence or completing unmet R01-R10 acceptance.

Scope: all intentional outstanding source, test, documentation and feature-report changes for the recent research and Introduction deliveries, plus this documentation update. No ignored credentials, populated secrets, caches, personal portfolio data or temporary verification artifacts are published. Expected remote `andrewnapurano00/Agentic-AI-Financial-Analyst`, branch main; authenticated fetch confirmed local and remote were aligned before the sync. These changes form the current synchronization commit; its revision is available in Git history and the verified push result is reported with the commit link.

Verification for this documentation/sync step: application source/test hashes remain unchanged from the final 322-case offline run, compile/import, health and synthetic browser checks recorded in V-20261004-05; reuse those dated results rather than reporting a new test/deployment run. Current edits require UTF-8, local-reference, credential-pattern and staged-diff validation. No live provider/model call or hosted deployment is performed by synchronization.

Documentation/sync validation (2026-10-04): application/test hash comparison confirmed unchanged verified inputs; UTF-8/local-link checks, intended-file credential-pattern scan and ignored-secret exclusions passed. `git diff --check` passed. Prior 322-case verification is reused with its original date/scope; no new application test or deployment is implied.


### D-20261005-P01 - Connected company navigation and action readiness (AAFA-8)

Local working-tree implementation, based on `77f7275`; deployment pending. User outcome: company discovery prepares the selected destination without submitting research, saved chat/reports remain accessible, and non-AI workspaces no longer require OpenAI configuration. Scope is P01 only from `docs/features/2026-10-04-five-day-predeployment-plan.md`; R03 remains partial.

Implementation: `state/research_context.py` validates company identity (including BRK-B), destinations/cardinality and metadata-only references (D01-D02). `ui/workspace_handoff.py` applies one-shot pre-widget adapters; Introduction/Top Movers launch Research, Equity Report and V1/V2, and saved Screener output launches Introduction. `main.py` removes the global OpenAI routing gate, prepares legacy/command requests as editable drafts, and requires explicit submit; chat configuration handling is Research-only with explicit New thread. V1/Portfolio/Equity paid controls explain missing dependencies while preserving deterministic/saved output access. V2 retains stage-specific provider preflight and a stable Companies widget key. Saved Screener rendering is separated from collection. The audited V1/V2 saved-financial bridges remain disabled; navigation carries no financial values, credentials, collection authority or inferred evidence times (D03-D05).

Tests/source: `tests/test_workspace_handoffs.py`, `tests/test_market_tabs.py`, `tests/test_deep_research_ui.py`, existing V2 and health cases; source changes remain local. No provider/metric basis or financial arithmetic changed. Remaining work: broad typed-context adoption, universal provenance, recent/pinned securities and complete Portfolio/comparison paths. Full-suite, health, browser and independent review evidence will be recorded after source stabilization in the feature-team report; this delivery entry does not itself certify those checks.

### V-20261005-P01-builder - Focused offline verification

Initial compatibility run: project Python3.12.0, Streamlit1.61.1 and pytest9.1.1; `PYTHONPATH=src;<temporary offline guard> ../venv/python.exe -m pytest -q -p offline_guard tests/test_market_tabs.py tests/test_deep_research_ui.py tests/test_deep_research_v2.py tests/test_app_health.py`: **24 passed in29.37s**. Synthetic/mocked transport; guard blocks unmocked Requests/httpx/curl_cffi. Final focused set: the same command with `tests/test_workspace_handoffs.py` added passed **50 tests in42.49s**, including26 new P01 cases. The first P01-only run had21 passes/two test-label failures; correcting the V2 disabled-bridge assertion to its actual label produced23 passes, before adding command-navigation, saved-report and alternate-provider cases. `../venv/python.exe -m compileall -q app.py src` and `PYTHONPATH=src ../venv/python.exe -c "import app; import langgraphagenticai.main; import langgraphagenticai.state.research_context; import langgraphagenticai.ui.workspace_handoff"` passed; bare-mode Streamlit cache warnings were expected. Follow-up scoped check after the Introduction action-placement and deterministic V1 finalization-readiness corrections: `pytest -q -p offline_guard tests/test_workspace_handoffs.py::test_saved_v1_report_roundtrip_does_not_collect tests/test_market_tabs.py tests/test_deep_research_ui.py` passed **18 tests in22.66s**; compileall was repeated successfully. No live financial/model calls, paid credits, hosted deployment, clean-install certification or export-behavior certification are part of this check. Prior322-case inventory remains historical until a fresh full-suite run is recorded.


### V-20261005-P01 - Full local offline verification

Fresh full inventory: **348 passed in 87.37s**, including 26 new P01 cases. Command: `PYTHONPATH=src;<temporary offline guard> ../venv/python.exe -m pytest -q -p offline_guard`. Installed project interpreter Python **3.12.0**, Streamlit **1.61.1**, pytest **9.1.1**. Synthetic/recorded fixtures and mocked model/provider boundaries; temporary guard blocks unmocked Requests/httpx/curl_cffi. No paid model or live financial-provider calls. Builder compileall and app/main/context/handoff imports passed; source remained unchanged during the full run.

Fresh root Streamlit `app.py` on port8542 returned `ok` from `/_stcore/health`. The browser used a separate offline harness on8541 with actual sidebar, main routing and page renderers, synthetic financial providers and forbidden paid factories. Observed Top Movers to editable AAPL Research draft and V2 Companies, Screener to AAPL Introduction and return to saved results (one screen call), Introduction to Equity Report/V1, optimizer availability without OpenAI, disabled relevant AI actions and financial bridges, preserved chat on outside-Research use-case changes and visible Research mismatch. Model counter remained zero. Initial Introduction bottom handoff controls were covered by the fixed status bar; moved above charts and independently re-exercised successful pointer navigation. Browser screenshots/harness remain outside the repository under temporary axiom-p01-verification. Independent review and final isolation checks are recorded in the run report after completion.

No live entitlement/freshness/model-quality audit, clean install, Docker image verification, new export artifact audit, source commit/push or hosted deployment. Deployment remains pending. R03 and other broad milestones remain partial.


Final P01 verification after F01 (stale reset notice) correction: **348 passed in 107.95s**, same full guarded pytest command/interpreter and 26 P01 cases. The prior 87.37s result predates this final ordering change. Updated configuration regression passed1case13.52s; compileall and app/main/context/handoff imports repeated successfully. Independent verifier ran26P01cases48.53s before the final correction, then inspected final warning ordering and updated assertion; no outstanding scoped defects or follow-up candidates. Browser rechecked the corrected New thread notice and two-session isolation: first chat reset to0 with one prior screen call, second retained chat1 with screen0 and no inherited company context. Model counts stayed0 and browser error list empty. Rootapp8542/harness8541 fresh health passed. Source snapshot matches reviewed final hashes. See [feature-team report](docs/features/2026-10-05-p01-connected-context-team.md) for Jira outcome and ledger.


Final P01 cleanup verification after F02 (duplicate widget defaults): keyed Introduction/Equity/V2 inputs initialize session ownership before rendering and omit duplicate default arguments; queued symbols remain authoritative. Independent source recheck approved the narrow fix. Builder26handoffcases passed28.72s, including no-duplicate-warning assertions. Final complete guarded offline inventory: **348 passed in75.21s**, same project interpreter/command. Compileall and diffcheck repeated successfully; fresh actual-main browser imported edited modules. Restarted rootapp8542/harness8541 health returnedok. Fresh browser entered lowercase aapl in Introduction, opened normalized AAPL in V2 and Equity Report and returned; no duplicate-default warnings, saved chat retained, model counter0, browser errors empty. This supersedes the earlier107.95s source snapshot while retaining its dated checks. All reported P01 findings resolved; broad R03 remains partial, deployment pending. Jira final cleanup evidence follows comment10118 on AAFA-8; report records confirmed result.


## D-20261006-P02 - Evidence-first terminal presentation (AAFA-9)

Local working-tree delivery preserving the existing P01 changes. R02/R06 remain partial. Shared `ui/app_shell.py` provides compact company identity, at most three executive cards, evidence rows, reusable progress/empty/failure components, keyboard focus and a wrapping mobile footer. All eight generic headers avoid unverified readiness; sidebar/footer key presence is configuration, and the current clock is Page rendered at. Pure `ui/workspace_presentation.py` reads saved dates, usable record counts/gaps/source labels and rejects unsafe or credential-bearing source URLs; aware retrieval dates order by UTC instant and naive dates explicitly retain unknown timezone.

Introduction identity/status/cards/saved interpretation precede chart and financial/news details; missing change stays missing and quote/financial currencies are not defaulted to USD. Historical chart arithmetic/settings/provider contracts stay unchanged. Research consumes the P01 typed company context as navigation metadata, keeps the explicit draft/submit/reset contract and places saved AI findings before expandable conversation details without inventing chat provenance. V2 selected saved identity/evidence/cards precede its collapsed new-research form and provider/limitations details; performance/cache metrics move behind Performance, original generation captions/recovery controls/warnings remain. V1 receives the same saved evidence row and safe descriptive source links. Source paths: `main.py`, `ui/{app_shell,workspace_presentation,introduction_tab,deep_research_tab,deep_research_v2_tab,streamlitui/loadui}.py`; tests `tests/test_workspace_presentation.py`; README workflow notes. Coordinator report: `docs/features/2026-10-06-p02-terminal-ui-team.md`. No commit/push/live financial/model calls/deployment.

Remaining work: universal financial provenance/freshness, unchanged report/portfolio table redesign, complete workspace interaction/CI coverage, real-provider/model quality and hosted deployment. Shared UI validation does not certify factual accuracy of saved AI prose.

## V-20261006-P02-builder - Focused local verification

Interpreter: installed project Python3.12.0 (`../venv/python.exe`), Streamlit1.61.1, pytest9.1.1. Offline environment: `PYTHONPATH=src;C:/Users/andna/AppData/Local/Temp/axiom-p01-verification` with the existing external network guard. No paid provider/model calls.

- `python -m pytest -q tests/test_workspace_presentation.py`: 13 passed, 11.23s on final saved-preview ordering (earlier source-link guard check: 19.17s) (saved metadata, safe links, shell escaping/configuration, actual Intro range rerun and V2 saved rerun). Earlier nine-case presentation plus P01 handoff selection: 35 passed, 68.71s; presentation plus V2 helpers/V1 UI: 23 passed, 21.24s, before the two additional actual-view cases. Final presentation/V1UI/V2-helper selection: 25 passed, 23.05s before the last two URL edge cases. These scoped counts are not the full repository inventory.
- After collapsing V2 setup/configuration details, `python -m pytest -q tests/test_workspace_presentation.py tests/test_deep_research_v2_recovery.py tests/test_deep_research_v2_timestamps.py`: 64 passed, 40.08s. Saved recovery/reuse/generation contracts and new presentation cases passed offline.
- `python -m compileall -q app.py src` and imports of app/main/presentation/Introduction/V1/V2 succeeded; harmless bare-mode Streamlit cache warnings. Final compile and diff-whitespace checks passed after saved-preview ordering; final full-suite/health/browser checks remain coordinator evidence.
- External actual-renderer harness: `C:/Users/andna/AppData/Local/Temp/axiom-p02-verification/browser_harness.py`; synthetic saved/empty/partial/stale/failure/loading scenarios, old evidence dates/new generation operation, blocked network and paid-action counters. Initial actual-main AppTest Intro/Research passed; V2 fixture initially lacked comparison and was corrected. Browser screenshots, fresh health and guarded full inventory are coordinator verification, not claimed by this builder record.

No live entitlement, financial freshness, model quality, clean install, export completeness or hosted deployment check performed. Earlier inventories remain historical until a fresh full-suite result is recorded.

## V-20261006-P02-pre-F03 - Local verification before market correction

Final working-tree source, after F01/F02 corrections: **361 passed in 106.77s**, including 13 new P02 presentation cases. Command: `PYTHONPATH=src;<temporary offline guard> ../venv/python.exe -m pytest -q -p offline_guard`. Installed project Python **3.12.0**, Streamlit **1.61.1**, pytest **9.1.1**. Guard blocks unmocked Requests/httpx/curl_cffi; synthetic/recorded evidence and model stubs, no paid model or live financial-provider calls. The earlier 361-case 114.73s run predates the final V2 ordering and remains supplemental. An alternate Anaconda baseline had 346 passes/two pre-existing truststore certificate-enumeration failures; it is not the project delivery inventory.

`../venv/python.exe -m compileall -q app.py src` and imports of app/main/all affected UI modules passed; bare-mode cache warnings were expected. Fresh local root app8544 and synthetic actual-main harness8543 health returned `ok`. Independent final-snapshot presentation/handoff/timestamp checks: **62 passed in 52.83s**, compile/diff checks passed, no unresolved introduced defect or substantive follow-up ticket. Reviewed source/test hashes match final source; prior P01 and unrelated workspace changes preserved.

Fresh isolated agent-browser screenshots/interactions cover Introduction, Research and V2 at **1440x900, 1280x800 and 390x844**. All primary layouts show three cards; page width matches viewport, shared headers/evidence/cards do not overflow, and no Streamlit exceptions occurred. F01 mobile footer clipping was corrected with static wrapping; F02 V2 setup preceding saved findings was corrected with collapsed setup and findings immediately after cards. Keyboard Tab showed a visible amber 2px focus outline. Source expanders and descriptive public links were usable; unsafe URL and escaped provider-text fixtures are covered by offline regressions. V1 shared evidence row was exercised separately. Introduction-to-Research handoff retained AAPL, editable draft and saved chat. Saved V2 evidence retrieval (September15 fixture) remained separate from October5 generation time across navigation, tabs and expander reopening. Empty, partial, loading, failed-report and explicitly stale chart fixtures show textual states. All observed navigation/settings/detail counters remained **zero model/paid calls**. New AppTest cases additionally cover saved Introduction range changes and ordinary V2 reruns. Screenshot/fixture/JSON artifacts are outside the repository in the temporary P02 verification directory.

No live entitlement, evidence freshness, model narrative quality, clean-install, Docker/hosted deployment, or new export certification is established. Existing report/portfolio tables retain their prior behavior; broad R02/R06 and universal provenance/freshness/CI criteria remain partial. Local P02 implementation is complete; deployment remains pending. Jira outcome and exact ledger are in [the feature-team report](docs/features/2026-10-06-p02-terminal-ui-team.md). No commit/push/deployment performed.

## V-20261006-P02 - Final local verification

Final corrected source after F03: **367 guarded offline tests passed in 95.19s**, including **19 new P02 cases**. Same project command/environment as the pre-F03 record: `PYTHONPATH=src;<temporary offline guard> ../venv/python.exe -m pytest -q -p offline_guard`, Python3.12.0 / Streamlit1.61.1 / pytest9.1.1. Synthetic/recorded evidence; unmocked Requests/httpx/curl_cffi blocked, no paid or live financial calls. Full compileall and app/main/affected imports repeated successfully; final diffcheck passed.

F03 corrected an empty-map status edge: market coverage now counts actual price presence against requested indexes. Empty or all-missing quotes report Missing, partial requested coverage/warnings report Partial, and zero remains distinct from missing. The actual empty Introduction market view shows Missing plus existing error/retry guidance; no page exception or model call, with no shared-component/page overflow at all three requested sizes. Independent F03 source review and **27 presentation/market cases passed in20.73s**, with refreshed hashes matching. Earlier **62 focused** and **361 full** checks remain historical snapshots, not a second current inventory. All F01/F02/F03 findings are resolved; no substantive unresolved follow-up ticket candidate.

Primary-view browser screenshots, keyboard/source/expander checks and saved-date/navigation fixtures in the pre-F03 record remain applicable: F03 changed only the market status adapter/call-site/empty guard and six regression cases. Final health checks returnedok for root8544 and harness8543. Local P02 delivery complete, deployment pending; R02/R06 remain partial. Jira AAFA-9 tracks the local implementation and its verification; no commit, push or deployment.


## D-20261007-P03 - Explicit bounded Guided research

R04/R06/R07 scoped local delivery, working tree only: Research users can inspect a one-company plan before explicit collection/synthesis. Presentation is isolated in `ui/guided_research_tab.py`; typed schemas and a two-node LangGraph workflow are in `research/guided_schemas.py` and `research/guided_workflow.py`. A narrow `providers/guided_research.py` adapter reuses shared FMP transport with saved FMP-018/FMP-045/FMP-061 contracts and a bounded Marketaux news request (D01-D04). The legacy chat graph and both Deep Research orchestrators remain separate.

Three logical dispatches/two model attempts/12 graph steps are separate caps. Complete model inputs use a conservative UTF-8 byte token bound with protocol reserve; completion reserves include reasoning. Known user-configured prices are reserved before calls; unknown prices require explicit acknowledgement and cannot guarantee a dollar ceiling. Model retries are disabled. Failed attempts remain consumed and successful evidence survives partial failures. Shared FMP transport can retry requests, so logical dispatch limits are not HTTP-attempt or hard wall-clock limits. Profile business dates and actual quote currency/adjustment remain unknown; annual FY monetary fields are neither TTM nor growth/ratio substitutions. News is one page with disclosed filtered/duplicate omissions.

Exact structured facts validate citation ID, field/value, currency, date and basis; unsupported facts are withheld. This does not certify narrative semantics. Session-owned fingerprints cover config/plan/evidence, unique run IDs distinguish explicit new generations, and consumed plans cannot replay collection at the workflow boundary. UI reruns/downloads/repeated Run reuse results, input changes disclose mismatch, and Chat/Guided transitions preserve drafts/controls/conversation. Deep Research handoff navigates without starting it. No clients, keys or private prompts are saved; configured credentials are redacted before model packets and persisted/download state.

Source/tests: the four new modules above, small Research mode gate in `main.py`, `tests/test_guided_research.py`, README. Baseline P01/P02 and unrelated changes preserved. Broad R04/R06/R07 criteria remain partial: autonomous browsing, cross-restart durability, universal provenance, live model-quality/entitlement guarantees and app-wide spend coverage are deferred. Local browser/independent verification and final full-suite inventory are recorded separately below when actually completed. Deployment remains pending; no commit/push/deployment.

## V-20261007-P03-builder - Scoped offline verification

Installed project Python 3.12.0 / Streamlit 1.61.1 / pytest 9.1.1, `PYTHONPATH=src;C:/Users/andna/AppData/Local/Temp/axiom-p03-verification`. Command `../venv/python.exe -m pytest -q -p offline_guard tests/test_guided_research.py`: **19 passed in 36.17s** before the final plain-purpose URL validation. Synthetic provider/model doubles plus exact saved AAPL FMP-018/FMP-045/FMP-061 samples; guard blocks unmocked Requests/httpx/curl_cffi. Tests cover hostile/oversized/duplicate/extra-field plans, model/tool/spend caps, partial failures, zero/bool/nonfinite values, fiscal and citation mismatch, invalid news/dedup/empty states, credential removal before prompts/state, new-run identities, consumed replay, failed model usage, independent sessions, saved-evidence tamper and actual-main Chat/Guided draft/navigation controls. No paid or live provider/model calls.

Full compile/import, full guarded inventory and actual browser/health checks are pending in this builder entry until fresh results are appended; earlier P01/P02 records are historical. No live freshness/entitlement, clean install, Docker/hosted deployment or AI narrative quality check claimed.


Initial builder full-suite result before independent-review corrections: `../venv/python.exe -m pytest -q -p offline_guard` completed **386 passed in 159.93s (2:39)**, comprising the preserved 367-case baseline plus 19 Guided cases. Same Python3.12.0/Streamlit1.61.1/pytest9.1.1 and blocked-network guard. `../venv/python.exe -m compileall -q app.py src` passed; imports of app, main and Guided workflow passed with expected bare-mode Streamlit cache warnings. `git diff --check` passed. Actual health/browser and independent review remain coordinator/verifier evidence and are not implied by these offline results.


### P03 independent-review corrections (same October7 delivery run)

F01: full configured credentials are now replaced before regex processing and provider text truncation, avoiding credential fragments at excerpt boundaries. An end-to-end profile/news -> model-packet -> saved result/export regression covers the boundary. F02: unknown model pricing uses null reserved dollars and explicit unknown pricing status, while known pricing remains numeric and preflight-enforced. F03: JSON-mode SDK requests explicitly instruct JSON; strict Pydantic validation is local, and JSON mode alone does not enforce the schema. SDK doubles verify JSON context, bounded completion including reasoning, timeout/retries, usage and refusal/truncation behavior. Earlier 386-case result is historical before these corrections. Focused corrected suite: **22 passed in 19.59s**, with a final refusal assertion additionally included in the full rerun. Final full inventory/compile/health/browser/review are recorded only as actually completed. No live provider/model or deployment calls.


### Final corrected P03 builder verification

Same October7 run, checks completed October8 local time: **389 guarded offline tests passed in 86.07s (1:26)** on F01/F02/F03 corrected source, including **22 Guided cases**. Command `PYTHONPATH=src;C:/Users/andna/AppData/Local/Temp/axiom-p03-verification ../venv/python.exe -m pytest -q -p offline_guard`; Python3.12.0 / Streamlit1.61.1 / pytest9.1.1. Final suite includes the explicit SDK refusal assertion and credential-boundary prompt/export regression. Recorded/synthetic provider/model responses only; unmocked Requests/httpx/curl_cffi blocked, no paid calls. `../venv/python.exe -m compileall -q app.py src`, imports of app/main/Guided workflow and `git diff --check` passed. Bare-mode Streamlit cache warnings are expected. Fresh health/browser and independent final-snapshot review are coordinator/verifier evidence, recorded separately; these commands do not establish live provider freshness, entitlement, narrative quality, clean-install or hosted deployment. No commit/push/deployment; R04/R06/R07 remain partial.


## D-20261008-P03 - Final local acceptance verification

Resumed the original AAFA-10 delivery. Added explicit evidence limitations for inferred Unix-seconds quote timestamps and independently unverified annual monetary scaling, retaining raw provider values and annual FY basis; exact saved-sample regression assertions added. All other P03 implementation and P01/P02 working-tree changes preserved. R04/R06/R07 remain partial; this accepts only the one-company bounded Guided research slice. Independent final source/browser/export review approved local completion; AAFA-10 is verified **Done** with completion comment10122. Detailed Jira outcome is recorded in the original [team report](docs/features/2026-10-07-p03-guided-research-team.md). No commit/push/deployment.

## V-20261008-P03 - Fresh final local verification

Python3.12.0 / pytest9.1.1 / Streamlit1.61.1, installed project `../venv/python.exe`, `PYTHONPATH=src;C:/Users/andna/AppData/Local/Temp/axiom-p03-verification`. Full `-m pytest -q -p offline_guard`: **389 passed in167.06s**; builder focused `tests/test_guided_research.py`: **22 passed in25.75s**; independent focused: **22 passed in18.35s**, exit0. Exact saved AAPL and synthetic provider/model responses; unmocked Requests/httpx/curl_cffi blocked and no paid calls. Initial concurrent focused AppTest3second timeout resolved in full/sequential reruns without source/test-timeout changes. Compileall app.py/src, corrected actual-module imports and diff check passed. Independent final-source review rechecked F01-F03, exact data contracts and hashes, with no actionable defects.

Fresh actual-app Streamlit startup8534 and final-source synthetic actual-main harness8533 health endpoints returned **ok**. Actual-app browser not opened to avoid .env-triggered live providers. Agent-browser actual-main fixture checks passed explicit Prepare0providers, plan inspection, partial-news Run with preserved financial zero, repeat Run/evidence/download/ChatGuided no additional calls, ticker/model mismatch, explicit new run, isolated AAPL/MSFT sessions and explicit Deep Research navigation without execution. Single-run limits remain distinct from repeated explicit new generations. Screenshots/assertions at1440x900,1280x800,390x844 showed no page overflow or Streamlit exception. Artifacts/scripts are outside repository in `C:/Users/andna/AppData/Local/Temp/axiom-p03-completion-20261008`.

Native browser CLI file saving reported canceled twice; actual browser-requested JSON endpoint returned HTTP200 and curl-retrieved export content passed identity, zero-value, null/unknown-cost, partial-evidence and configured-credential checks. Native file-save behavior is unconfirmed; response/content and download-rerun call counts are verified. Cold-load wait and label-locator issues were resolved by waiting for render and using fresh snapshot refs/Enter; no application failure inferred from them. No live provider entitlement/freshness, real narrative-quality, clean-install, Docker or hosted deployment checks. This fresh389 inventory supersedes earlier P03 inventories for local offline verification, without broad-workspace coverage claims.

## D-20261008-P04 - Saved investment brief and audited sensitivities

R04/R06 scoped local working-tree delivery, tracked by AAFA-11: V1/V2 share a sixth result tab with original saved narrative excerpts, retained evidence IDs, explicit missing topics, deterministic Bull/Base/Bear total equity sensitivities and a P/E chart. Financial eligibility requires resolvable actual audited contracts/source records, positive four-quarter TTM earnings and dated cap, explicit compatible quote currency, canonical sector applicability and a maximum seven UTC-calendar-day quote age. Future instants, malformed/legacy contracts, inferred currency, REITs and unknown sectors are unavailable. Banks retain canonical earnings-multiple applicability. No silent recalculation, provider/model calls or saved-report mutation.

Design note: immutable eligibility/arithmetic belongs in `analysis/scenarios.py`; saved narrative/evidence/safe bounded exports belong in `analysis/investment_brief.py`; `ui/investment_brief.py` owns shared rendering and workspace/run/ticker controls. Existing V1/V2 orchestration remains separate. Original report exports are preserved. Scenario defaults are demonstrative user assumptions; formulas/period/currency/date/source and existing timestamp/quarter/raw-scale assumptions remain disclosed. JSON/CSV contain bounded provenance, configured-credential filtering, safe links and formula-safe text.

Sources/tests: the new analysis/UI modules, narrow V1/V2 tab integration, `tests/test_investment_brief.py`, updated V2 recovery download-label assertions. Existing P01-P03 changes preserved; no commit/push/deployment. R04/R06 and all broad roadmap milestones remain partial. See [team report](docs/features/2026-10-08-p04-investment-brief-team.md) for role handoffs, independent acceptance and the Jira ledger.

## V-20261008-P04 - Local verification

Installed project Python3.12.0 / pytest9.1.1 / Streamlit1.61.1, `../venv/python.exe`; `PYTHONPATH=src;C:/Users/andna/AppData/Local/Temp/2026-10-08-p04-investment-brief-team`. Final builder `-m pytest -q -p offline_guard`: **419 passed in107.24s**. Final focused P04 + V2 recovery: **58 passed in39.86s**. Guard blocks unmocked Requests/httpx/curl_cffi; exact recorded financial and explicitly synthetic eligible/provider/model fixtures only, no paid calls. Compileall app.py/src, imports app/main/new domain/UI and diff check passed. Coordinator C01 timestamp sanitizer correction included in this final inventory. Independent/browser evidence follows below; earlier interim checks are not claimed as final.


Final coordinator acceptance (October8 local / October9 UTC): fresh actual-app8544 and corrected actual-main synthetic harness8543 health returned `ok`. Agent-browser exercised V1 eligible narrative excerpts, edited Base15%/PE17, JSON/CSV browser responses, REIT unavailable, bank applicability, ticker state, inferred currency/stale quote/legacy audit unavailable, partial narrative and saved reopening; navigated into V2 shared panel and verified identical exported scenario arithmetic. Per-fragment observers showed zero external attempts, original histories preserved and no Streamlit exceptions throughout. At1440x900,1280x800,390x844 document width did not overflow; actual screenshots inspected, mobile controls stack and currency/date/formula labels wrap. Artifacts/scripts/screenshots remain outside repo in the run temporary directory. V1 and V2 Base value2520581500000 USD and difference-48.57030712966501% independently checked against retained NI128930000000 and cap4901023823640. Independent reviewer inspected actual JSON/CSV dates/IDs/currency/formulas/bounds and documentation, with no blocking defect.

Native agent-browser download file-save reported canceled for V1 JSON/CSV and V2 JSON. Exact browser-requested media URLs returnedHTTP200; retrieved response bodies passed arithmetic/provenance/credentials/CSV checks. Native filesystem save completion remains unconfirmed. No live providers, paid models, live financial freshness/entitlement, real narrative semantics, clean-install, Docker or hosted deployment certification. Final source hashes match the419-test/independent-reviewed snapshot; only documentation changed afterward. Existing P01-P03/unrelated edits preserved. No commit/push/deployment. Broad R04/R06 and other roadmap milestones remain partial.


P04 independent final artifact/document/payload approval passed with no blocking findings. AAFA-11 final comment10125 confirmed and transition31 returned verified **Done**. P04 minimum is complete locally; detailed ledger in the team report. Deployment remains pending; no commit/push.

## D-20261010-P05 - Local release automation

Scoped R08/R09/R10 preparation: `.github/workflows/offline-release.yml` defines Python3.11/3.12 constrained clean installation, pip check, the full guarded offline inventory, compile/import and retained JUnit/version artifacts. Dependency manifests now match; newspaper3k removed to avoid competing with newspaper4k for `newspaper`. NumPy2.5.2 requires Python3.12, so Python3.11 uses its compatible2.3 line. Direct constraints are not a transitive lock.

Runtime Docker now explicitly copies app.py/src, retaining non-root UID1000 and health. `Dockerfile.verify` derives from the runtime and adds pytest/tests plus three exact saved AAPL FMP samples; it runs synthetic AppTest checks with network disabled. Optional BuildKit public CA secret supports enterprise TLS verification without retaining a trust bundle in image layers. The deployment runbook records protected preview, secret injection, explicit paid-call bounds, session-versus-identity limits and rollback requirements.

`tests/test_release_workflow.py` exercises actual Introduction AAPL handoff, Guided prepare/run with annual FY facts and independent news failure, separately seeded immutable saved Deep TTM brief/scenarios, zero additional model/provider calls on ordinary reruns and a second isolated session. Eight workspace cases establish readiness/render only. D01-D07 traced in test/doc comments; synthetic USD quote eligibility is not observed quote-currency proof. `tests/conftest.py` rejects Requests/httpx/curl_cffi and external sockets before collection and during tests. `tests/test_release_contracts.py` checks manifest agreement and external transport rejection.

Working-tree delivery only; P01-P04 edits preserved. Hosted target, protected preview, hosted authentication/session tests, bounded live smoke, actual GitHub CI execution and rollback remain pending; AAFA-12 remains open. Broad roadmap criteria remain unmet. Parent-owned [team report](docs/features/2026-10-10-p05-release-automation-team.md) records fresh acceptance results and limitations.

## V-20261010-P05-builder - verification in progress

Installed project interpreter `../venv/python.exe`: Python3.12.0 (Anaconda), Streamlit1.61.1, pytest9.1.1. Installed pip check passed; compileall app.py/src/scripts and imports app/main passed. New dependency/transport contracts:2 passed. Initial9-case workflow run had8 pass and one test-only SafeSessionState.get failure; assertion corrected. Fresh focused/full final-source inventories are recorded below when complete; no earlier count is promoted to new evidence. Docker/health/browser and independent evidence belong to coordinator/verifier checks, not assumed by this entry. No paid models or live financial provider calls authorized.


## V-20261010-P05 - Final local verification and remaining release gates

Independent final-source `PYTHONPATH=src ../venv/python.exe -m pytest -q`: **430 passed in597.19s**. Python3.12.0 (project Anaconda environment), pytest9.1.1, Streamlit1.61.1, NumPy2.5.2, pandas3.0.5, CrewAI1.14.4, FastMCP3.4.7. Guard applies before collection and each test: Requests/httpx/curl_cffi plus external DNS/socket connections rejected; recorded/synthetic services only. Builder focused release workflow/contracts11 passed150.15s; final DNS/transport contracts2 passed1.78s. Superseded intermediate full-suite process was stopped; it supplies no inventory. Compileall app.py/src/scripts, app/main imports, installed pip check and final diff check passed. Independent review found no remaining source defect; one low runbook artifact-description issue corrected/rechecked. Existing P01-P04 source SHA256 values are unchanged by P05. This fresh430 inventory supersedes419 for offline testing, without exhaustive workspace coverage claims.

Fresh actual app8554 and synthetic actual-main harness8553 `/_stcore/health` returned `ok`. Agent-browser exercised Introduction AAPL handoff into editable Research draft with zero calls, pricing acknowledgement then explicit Guided prepare/run with2 synthetic model attempts and3 tool dispatches. Failed news is disclosed while annualFY facts remain available. A separately seeded saved audited Deep Research brief displays original source/date/currency/formula labels; edited Bear earnings to-100%, navigated out/back and reopened shared brief. Per-session observer retains2/3/0(model/tool/external), immutable saved history and Guided result. Second independent browser session has0/0/0 and no saved/Guided result; zero Streamlit exceptions. Browser screenshots/harness are outside repo; fixed2026-10-08 scenario clock and augmented USD quote are explicitly synthetic, not provider currency/freshness proof. Eight-route tests cover readiness/rendering, not exhaustive behavior. Browser daemon snapshot/timeouts and shell quoting issues were corrected with a nonperiodic observer and encoded DOM observations; only completed final checks count. Download click completed; native file-save/content verification was not part of this release smoke.

Docker28.3.0/Desktop4.43.1 engine started successfully, but runtime image builds failed during package downloads: initial local CA trust error, then intercepted HTTP/1 responses with `InvalidChunkLength` after optional public CA BuildKit injection. Two temporary external transport-only identity-encoding variants also failed (five build attempts total). TLS verification stayed enabled; no private keys/global trust changes. These are observed transport failures, not evidence of a dependency conflict. **No runtime image was produced:** non-root image startup/health, derived image workflow, Python3.11 clean install and fresh GitHub CI matrix are unverified. Installed pip check is not clean-install certification. Hosted target/access, hosted URL, paid live smoke and actual rollback remain pending. No staging/commit/push/deployment or live financial/model checks. AAFA-12 remains In Progress for unmet release gates; no duplicate follow-up ticket needed.

P05 local source implementation is finished; full P05 release acceptance and broad R09/R10 milestones remain partial. See [team report](docs/features/2026-10-10-p05-release-automation-team.md) and [deployment runbook](docs/DEPLOYMENT.md).


## D-20261010-DOCS - P01-P05 status reconciliation

Documentation-only working-tree update to PLAN.md and AGENTS.md: refreshed current delivery/workspace/architecture boundaries, corrected obsolete global key-gate and absent-CI claims, linked P01-P05 evidence and dated Jira outcomes, and updated the current inventory to the already measured430 cases. R02/R03/R06/R10 record delivered subitems separately from unmet universal/empirical acceptance. Historical delivery/verification records retained. P05 local code is finished; clean-install/container/remote-CI/hosted/rollback gates remain open. No source changes, new Jira actions, commit/push or deployment.

## V-20261010-DOCS - Documentation validation

Validated UTF-8 text, Markdown fences/local links, referenced source/test/workflow/report paths, current statements against implementation and P01-P05 handoffs, and `git diff --check`. Hash comparison checks preservation of every preexisting file outside PLAN.md/AGENTS.md. Application tests, compile/import, health/browser, live Jira/provider/model calls, clean installs, Docker and deployment were not rerun for this documentation-only change. The430 tests and P05 browser evidence remain dated V-20261010-P05 results.
