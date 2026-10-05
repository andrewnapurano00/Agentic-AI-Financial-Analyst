# Sector-aware research metrics and financial calculation audit

Run ID: 2026-10-04-sector-aware-research-ttm-team
Mode: build, with tested isolated candidate before local product-code installation.
Baseline: 7a0026487644c9f273f4767b7348d11cf9740fad; initial working tree clean.
Isolated candidate: C:\Users\andna\AppData\Local\Temp\axiom-sector-ttm-z_kv2t55\checkout
Baseline hashes: C:\Users\andna\AppData\Local\Temp\axiom-sector-ttm-z_kv2t55\baseline-hashes.json

## Outcome and acceptance

Both Deep Research versions use Equity Report's canonical sector applicability and show supported metrics, with missing inputs disclosed. Audit all displayed numerical metrics and their units/fiscal bases. Income/cash-flow TTM uses four consecutive standalone quarters; balance sheets use latest quarterly snapshots, with matching periods required for combined ratios. No fabricated provider-sector metrics, summed shares/EPS or balance stocks. Validate currencies, zero/missing inputs, growth, ratios, exports and sector rendering with offline tests. Retain V1/V2 orchestration and saved-session recovery. Track verified findings and implementation progress in AAFA; apply product source to local tree only after checks pass. No commit/push or hosted deployment requested.

## Handoffs and verification

Financial specialist, planner, builder and a distinct independent verifier completed. Earlier delegation/usage-limit notes are historical and superseded by successful delegation after the user reset usage.

## Jira ledger

Up to five creation attempts across this run. Used: 1 of 5. Pending: none. Confirmed implementation ticket: AAFA-6. User explicitly requests tracking updates, authorizing issue comments/status tracking within this scope. Duplicate checks and supported project metadata required before creation.

## Financial specialist handoff - D01-D10

D01: saved stable quarterly statement routes FMP-061 income, FMP-063 balance, FMP-065 cash flow support eight records across eleven tickers; profile FMP-018 and full quote FMP-045, annual estimates FMP-031 and historical FMP-136. Exact sample root `fmp_data_reference/samples/<API>/20261003T044241108241Z/`; quarterly routes use period=quarter,limit=8, annual period=annual,limit=5. Restricted quarterly ratios/key-metric variants are not substituted contracts.
D02: require unique consecutive fiscal quarters, identity/currency/date validation; AAPL FY2026Q1 ends December2025, so calendar-year inference is unsafe.
D03: AAPL FY2025 saved quarter sums reconcile exactly: revenue416161M,NI112010M,OCF111482M,capex-12715M,FCF98767M USD. JPM revenue quarterly280333M vsannual279745M; PLD NI quarterly3328231K vsannual3410663K. Differences remain unexplained; do not overwrite quarterly data to force reconciliation or claim global standalone/YTD equivalence. As-reported YTD flows need duration-confirmed differencing and are outside current standardized-route assumptions.
D04: audit all current comparison aliases and formulas: four-quarter flow sums, aligned margins/conversion/intensities, exact-year annual CAGR, prior-TTM growth, independent latest snapshot leverage, average beginning/end ROE/ROA, positive-denominator/current-currency valuation, explicitly simplified EV, unsupported specialist/per-share metrics. Missing values do not become zero.
D05: independently display latest quarterly balance, retaining separate matched TTM-end/prior-year snapshots for mixed ratios.
D06: V1 provider-TTM versus V2 calculated discrepancy; unsafe debt/cash and selected-period fallbacks; build focused shared audited boundary and label legacy saved methodologies without recollection.
D07: canonical sector registry/mapping already shared with EquityReport; mask applicability per company across mixed-sector matrices/prompts/PDF. Banks/REIT specialist KPIs, including NIM/FFO/AFFO, remain missing absent validated contracts.
D08: annual forward estimate basis for FY labels; no stale historical fallback, negative-EPSmultiple or truncated far-future selection; quote/estimate currency assumptions labeled.
D09: technical indicators use stated price basis/dated history, not total returns; YTD needs separate calendar-year rule. Saved rawclose examples do not prove adjusted history entitlement.
D10: explicit units/status/formulas shared with display/exports/prompts, replacing magnitude-based percentage guessing; offline arithmetic verification does not certify model-written numeric claims.

Primary references: [SEC financial statements guide](https://www.sec.gov/files/investor/pubs/begfinstmtguide.htm) distinguishes balance stocks from income/cash flows. [FMP FAQ](https://site.financialmodelingprep.com/faqs?code=statements) notes cash-flow updates can wait for filed statements even when earnings-release financials are available; no authoritative universal standalone/YTD conversion guarantee was established. Source-document browsing is separate from live provider data/API calls.

Jira connection freshly verified via local MCP stdio helper (`C:/Users/andna/.codex/mcp/atlassian/check.py`), tools21. Cloud fa84d787-6378-47fc-bac7-60e49031f5ef. All AAFA issues1-5 across statuses searched, isLast=true; no duplicate sector/TTM issue. Create permission verified forAAFA10066; Task10074 supported. Required fields summary/project/issuetype/reporter (authenticateddefault). Zero attempts so far.

## Plan and delegation limit

P01 shared validated quarterly flows and separate latest balance; P02 complete safe comparison contracts (growth/forward/ratios/units); P03 per-company sector applicability in shared UI/PDF/prompt; P04 explicit formula/status inventory and legacy preservation; P05 offline complete regression/health/browser, then local installation. Planner delegation failed with account usage limit; coordinator proceeds without claiming a fourth independent review.

## Jira creation attempt 1

Timestamp: 2026-10-05T00:57:31.556994+00:00
Disposition: confirmed - AAFA-6 (original pending write reconciled successfully)
Payload:
```json
{
  "cloudId": "fa84d787-6378-47fc-bac7-60e49031f5ef",
  "projectKey": "AAFA",
  "issueType": "Task",
  "summary": "Align Deep Research sector metrics and audit quarterly TTM calculations in V1 and V2",
  "description": "## User outcome\nBoth Deep Research workspaces should use Equity Report's shared sector applicability and reproducible financial metrics: rolling four-quarter income/cash-flow TTM versus independently latest quarterly balance snapshots.\n\n## Verified baseline gaps\nBaseline 7a0026487644c9f273f4767b7348d11cf9740fad: V1 still uses provider TTM paths; V2 derives quarterly flows but couples balance display to income end. Shared sector registry exists, while union columns can display other sectors' downweighted metrics. Comparison aliases need explicit units, fiscal/currency alignment and missing-value rules; forward quarterly estimates can be labeled FY, and annual CAGR permits a two-year result under a 3Y label.\n\n## Acceptance\n- Both fresh workflows share validated four-consecutive-quarter flow sums, never summed balances/shares/EPS.\n- Latest valid balance snapshot remains visible independently of income availability; mixed ratios disclose matched numerator/denominator dates.\n- Validate identities, currency, missing/nonfinite/zero/negative inputs, growth, valuation, fiscal dates and explicit fraction/percentage units.\n- Sector applicability is applied per company in tables and supported exports/prompts; unavailable banking/REIT specialist metrics remain disclosed rather than fabricated.\n- Audit each displayed metric family with a documented formula/unit/source/basis or unsupported status. Preserve saved legacy research without silent recollection.\n- Add offline source/calculation/UI/export regressions, run full suite, compile/import, app health and synthetic browser interaction. No paid or live financial-provider calls in tests.\n- Build/test in isolated checkout; apply to local app only after checks pass, update docs and Jira evidence. No GitHub push or hosted deployment requested.\n\n## Evidence limits\nSaved FMP standardized quarterly samples cover eleven tickers. AAPL FY2025 quarterly flow sums reconcile to annual; JPM revenue and PLD net income differ from annual in dated samples, with unknown cause. Do not force reconciliation or claim universal provider semantics/live entitlement/AI factual correctness.\n\nRun: 2026-10-04-sector-aware-research-ttm-team. Item: P01-P05. Data requirements D01-D10. All AAFA issues including closed searched; no duplicate. Financial specialist read-only handoff completed; further delegation blocked by account usage limit, disclosed in local report."
}
```

Attempt1 confirmed created: AAFA-6 https://bigmeatpete717.atlassian.net/browse/AAFA-6
Attemptsused1/5. No pending/uncertain outcomes.

Usage reset confirmed by user; planner restarted successfully. Earlier account-limit note is historical and superseded. AAFA-6 progress comment10109 posted; transitioned to In Progress using freshlylisted21. Product code remains unchanged.

## Planner handoff and selected scope

Planner completed after usage reset. P01: shared fresh quarterly collection and calculations across V1/V2; selected-period history distinct from annual CAGR and annual estimates. P02: every existing visible comparison key/alias gets explicit units/source/period/formula/status, positive-denominator and alignment policies, no missing-as-zero or TTM-to-selected-period substitution. P03: canonical EquityReport sector registry per-cell applicability across UI/PDF/AI context. P04: metric audit and clear legacy labels, preserving old evidence/numbers without network. P05: complete offline regression and docs, then isolated full-suite/compile/import/health/browser before local installation. Unsupported provider KPIs remain explicitly unavailable; no claims that registry coverage or deterministic checks establish every AI narrative number. Builder /root/planner is distinct from /root/serper_planner; candidate checkout only, root code untouched.

Numerical policies include exact three-year annual CAGR (not two-year), independent latest balance with separate matched begin/end ROE/ROA, annual future estimates selected before truncation, named profile-currency inference, explicit fraction versus percentage-point units and dated consistent technical price basis. No unrelated EquityReport calculation changes.

## Independent numerical check during candidate build

Coordinator checked the isolated candidate's `quarterly_ttm.aggregate` against separately computed plain-Python sums saved before implementation in the external `independent-recorded-expectations.json`. Result: all 33 income/cash-flow totals and six four-quarter fiscal windows matched for AAPL, JPM and PLD. Interpreter: project Python 3.12.0. Inputs: exact recorded FMP-061/FMP-065 quarterly samples dated 20261003T044241108241Z. No network/model calls. This is focused arithmetic evidence on recorded samples, not final suite, browser or live-provider evidence; candidate is still changing and will receive final checks.

Current Jira ledger: attempt 1 confirmed AAFA-6, 1/5 attempts used; none pending. Status In Progress. Progress comments 10109 and 10110 confirmed. Earlier account usage-limit/delegation notes are historical: user reset usage and planner completed. Builder is working in the isolated checkout; root product files have not been installed.

## Coordinator regression evidence (candidate still under correction)

Project environment Python 3.12.0 / Streamlit 1.61.1 / pytest 9.1.1. New audit module initially passed 30 tests in 17.84s under the temporary offline guard (`requests`/`httpx` unmocked sends rejected). Full suite then: 258 passed, 2 failed in 69.81s. Failures: legacy saved-evidence recovery fixture did not acknowledge the new notice; new compact-evidence budget regression measured 26220 characters against 22000 and found empty excerpts. Findings sent to builder for correction; this is not a passing release check. `compileall -q app.py src` and app/main/new-module imports passed (expected Streamlit no-runtime cache warnings). Browser harness on8535 opens actual V1 saved-report page with recorded evidence and blocked external sends/model factories; final interaction evidence pending stabilized source. Jira progress comment10111 confirmed; issue remains In Progress. Root product source still unchanged.

## Independent verifier findings under correction

Fourth distinct agent `/root/financial_verifier` successfully delegated after builder stabilization; earlier delegation limitations are historical. Independent guarded subset: 90 passed in 13.66s, while adversarial checks found gaps not covered by the initial tests. Findings returned to builder in isolated checkout; no local installation yet.

- FID01 medium: annual CAGR calculation used annual data but audit input IDs/values/dates cited selected-period evidence. Requires both actual annual endpoints in the contract.
- FID02 medium: explicit YTD/unknown durations were rejected for TTM but not disclosed/guarded in latest reported-period metrics or raw financial trends. Requires validated duration labels or exclusion and no mismatched-basis YoY.
- FID03 high: four-company evidence at supported 18k/22k budgets produced ~26k characters and entirely empty excerpts. Requires bounded serialized context retaining substantive inputs for each company.
- FID04 high: optional V2 quick-decision brief copied full raw metric contracts (~464k characters under a 10k budget) and unprojected sector-inappropriate figures. Requires shared sector projection and bounded compact audit context.

Verifier systematically checked all thirteen canonical sector frameworks and mapped aliases; no projection leaks found in that specific synthetic check. Fresh candidate app startup/health8534 returned `ok`; provisional actual-page offline browser showed V1 four-quarter totals, negative bank OCF, preserved zero capex, and excluded bank EBITDA/FCF cells. Browser harness uses recorded samples and blocks external sends/model factories. Final browser/full suite/compile/import checks will follow fixes. No live market/provider/model validation is established.

## Correction-stage verification and remaining gate

Builder corrected FID01/02/04 and numeric-budget portion of FID03; independent recheck approved those corrections. Independent guarded subset: 102 passed in41.65s. Four-company quick packet9756/10000chars and evidence15900/18000chars retained all companies and excluded sector-downweighted metrics. Supplemental audit fixes include alternate estimate/target field names and both forward-growth/return-denominator observations.

Coordinator full suite initially271passed/1failed137.13s: unchanged reference collector hit Windows WinError5 while atomically replacing its temporary request_cache.json. Focused unchanged reference module rerun:4passed1.82s. Fresh full rerun:273passed74.44s, project Python3.12.0/Streamlit1.61.1/pytest9.1.1 and offline_guard. Compileall and app/main/model_packets imports passed (expected bare-runtime cache warnings); diff validation passed. Source hashes unchanged during this verification except PLAN documentation.

Independent recheck then found FID03 compaction regression: universal financial field whitelist erased investigation content, technicals and calculated trends. Builder is correcting category-specific preservation and actual YTD-prompt exclusions before final approval. Therefore the273 inventory is passing historical correction-stage evidence, not completion of final acceptance. Root159baselinefilehashes still unchanged; no installation yet. Jira progress comment10112 confirmed; AAFA-6 remains In Progress.


## Final verified delivery and local installation

P01-P05 delivered locally: common fresh V1/V2 quarterly collection, audited financial contracts, independently latest balance snapshots, correctly matched return denominators, shared canonical sector applicability, explicit units/dates/formulas and input source records, audit CSV/JSON/PDF, bounded sector-projected report/decision contexts, duration guards and preserved legacy sessions. No unsupported specialist metrics are fabricated. Both fresh factories keep existing bounded news behavior. Unverified cross-workspace financial packets are disabled with an explanation.

Final inventory: **276 offline tests passed in64.91s**, project Python3.12.0 / Streamlit1.61.1 / pytest9.1.1. The temporary guard blocks unmocked Requests/httpx sends. Independent reviewer:105 guarded cases passed17.47s and approved FID01-FID04 plus actual-alias/two-observation provenance corrections. Test-only recovery budget adjustment approved: valid source membership, balanced substantive coverage, correct omission count, strict serialization budget and full input immutability; it does not separately assert ID uniqueness. Builder recovery/audit66passed15.78s. All13 sector frameworks/aliases checked independently. Financial arithmetic checked independently against33 recorded totals and6 windows for AAPL/JPM/PLD; unsupported provider duration assumptions and JPM/PLD annual differences are disclosed rather than silently reconciled.

Final compilation/imports and diff checks passed. Fresh isolated candidate and installed-root startup health returned `ok`. Actual V1/V2 browser interactions through an external recorded-data harness exercised comparison/audit expansion, TTM numbers/negative cash flow/zero values, sector applicability and saved legacy history without console errors; provider/model sends and factories are blocked. Audit mediaCSV HTTP200 contained642 contract rows across3 companies and explicit units. Automated Chrome file-save capture was cancelled, so that automation path is unverified; served payload validation and offline export tests passed. Local installed-module paths were confirmed in the harness diagnostics. No live-provider entitlement/freshness or model narrative accuracy was tested.

Immediately before application, all159 root baseline hashes matched and no concurrent user edit was overwritten. Exactly25 scoped candidate files copied; all installed hashes matched. Root app/source compilation and imports passed; both installed-root research comparison/audit interactions and fresh health checked. Documentation current workspace/roadmap subitems updated with V-20261004-04 while broader R01-R10 acceptance stays partial. Manifest retained outside repository at final-candidate-manifest.json in the run temp directory. Root changes are local/uncommitted; no GitHub push or hosted deployment. Existing user server preserved.

Independent approval reports no unresolved substantive follow-ups. One implementation ticket created under explicit user tracking instruction; zero additional tickets recommended. Final Jira verification comment/status update follows local verification. Earlier failed/interim checks above remain historical; all final acceptance gates are now satisfied within the documented offline scope.

Final Jira outcome: AAFA-6 https://bigmeatpete717.atlassian.net/browse/AAFA-6; verification comment10113 confirmed. Fresh transition metadata listed Done31; transition returned statusName Done after verified local installation. Creation attempts1/5; no pending or uncertain outcomes; zero follow-up tickets. Coordinator-owned verification servers/browser closed; user server untouched.
