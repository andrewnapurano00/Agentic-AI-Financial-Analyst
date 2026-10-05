# Deep Research V2 quarterly-derived TTM team

Date: 2026-10-03 (America/New_York)
Mode: build
Run ID: 2026-10-03-deep-research-v2-quarterly-ttm-team
Baseline: 619494cec1e0ac716b3ba7b9d72391171eed5825

Outcome: derive V2 TTM operating metrics from validated quarterly statements without TTM endpoint access; preserve V1 behavior.

Acceptance: four unique consecutive fiscal quarters, aligned currency/security/window; no TTM endpoint use in V2; point-in-time balance sheet; deterministic ratios with explicit missing data and provenance; offline tests and independent review.

## Initial working tree

```text
 M AGENTS.md
 M DEEP_RESEARCH.md
 M PLAN.md
 M README.md
 M app.py
 M docs/PROJECT_SKILLS.md
 M src/langgraphagenticai/deep_research/crew_committee.py
 M src/langgraphagenticai/deep_research/manager.py
 M src/langgraphagenticai/deep_research/v2.py
 M src/langgraphagenticai/ui/deep_research_v2_tab.py
?? .agents/skills/code-review-agent/
?? .agents/skills/code-review-team/
?? .agents/skills/feature-development-team/
?? FMP_API_References_and_Example_Schemas.xlsx
?? docs/diagnostics/
?? docs/reviews/
?? fmp_data_reference/
?? src/langgraphagenticai/deep_research/v2_workflow.py
?? tests/test_deep_research_v2_recovery.py
```

## Initial scoped SHA-256 snapshot

```json
{
  "src\\langgraphagenticai\\deep_research\\context.py": "46888d3f52386b954c793a1331aeaf9d2e98c456741baf9fabfc6f0ae6bd6d66",
  "src\\langgraphagenticai\\deep_research\\crew_committee.py": "e751ec07c278bdb3b77cb079f23a283682b344b2cadcc9c1669e3ed19c303ce1",
  "src\\langgraphagenticai\\deep_research\\data.py": "a97fb80d9d99a7968b690170b53ac6b6de5ea774a080dd5e01aeee88db7862c2",
  "src\\langgraphagenticai\\deep_research\\manager.py": "5e6e7d76a19585dc543ab88866118bdc50450dc83153c273cabb8a8220593606",
  "src\\langgraphagenticai\\deep_research\\models.py": "c1a23212c555b243f8c356326386172c216881a2a48701654988e6fb4682870d",
  "src\\langgraphagenticai\\deep_research\\presentation.py": "54cd2a0c545e57db17ec3f947f48cfbf10412072d3fbb28dddc61733a33ef030",
  "src\\langgraphagenticai\\deep_research\\prompt_context.py": "30cf6dbda1f0d1985350ea21dcea20bdf01bc8dfdedae4e5307c3dbe71f83256",
  "src\\langgraphagenticai\\deep_research\\sector.py": "27847e8e1629061b800470bc802e667b56bc883c2b48d6861c081bc2765024f7",
  "src\\langgraphagenticai\\deep_research\\v2.py": "42e45108a0c5d821411b3ac691577491ebfc26610053aa9693961fd0f09e419c",
  "src\\langgraphagenticai\\deep_research\\v2_workflow.py": "a82e5c0be97068813898ae6557c2bed66a8148f843ecdee5bcdd86c001517c7c",
  "src\\langgraphagenticai\\deep_research\\__init__.py": "96a92dfaaf56f524dc48db0d2754722d3503cc75a54eddb93bef74ceb8ee0b51",
  "tests\\test_deep_research.py": "3ce3e4910b5a4737922f06b323fd9a703b36fb43ad43506a24510f5913f58606",
  "tests\\test_deep_research_recovery.py": "310dc69f4ec961fd97e35b6d664d260c414c65486c3d8785f08f034bba20b7ae",
  "tests\\test_deep_research_ui.py": "9d596b8f111c751dbe1fbe555297b805c23aa3a0de207b6a76d9eb183801b4e9",
  "tests\\test_deep_research_v2.py": "70f26551771e8d176c71485f7a3776febb8b042e4dd2188fbd15e274f83cf6b0",
  "tests\\test_deep_research_v2_recovery.py": "6bc940981401cb6578b40686e729ab6019dc33f4ca6687f32fc70d0e10e182c3",
  "README.md": "6766f9ca017f9bbe505d0dfe27433fa8eb6e23904cf24fcad89e7fa86c8c5973",
  "DEEP_RESEARCH.md": "2cc12407f994312b96440432c3b749083b71ce24f47a94420f5bd707844c8d9f",
  "PLAN.md": "c962c87a6c8a50c991f8278349b87900b9a9c250ac6f092a06fe5334914d6f0f"
}
```

## Data handoff

D01: FMP-061 /stable/income-statement symbol=AAPL period=quarter limit=8; saved successful sample samples/FMP-061/20261003T044241108241Z/AAPL-quarter.json. Latest 4 quarters FY2025 Q4-FY2026 Q3 through 2026-06-27 USD. Revenue 466823000000, gross profit 227123000000, operating income 154859000000, EBITDA 168486000000, net income 128930000000. Require unique consecutive fiscal identity, consistent symbol/currency and plausible dates; missing is not zero.
D02: FMP-065 /stable/cash-flow-statement same quarterly controls; saved sample samples/FMP-065/20261003T044241108241Z/AAPL-quarter.json. Current totals OCF 146724000000, signed capex -10041000000, FCF 136683000000. Standardized quarterly flows are additive, cash balances not additive. Require identical income/cash windows for cross-statement ratios; independent successful data survives failures.
D03: FMP-063 /stable/balance-sheet-statement quarterly limit=8; sample samples/FMP-063/20261003T044241108241Z/AAPL-quarter.json. Use matched end snapshot, never sum balances. Debt 84307000000, cash equivalents 39544000000, cash+investments 62399000000, net debt 44763000000, equity 107520000000. Explicit cash convention: sample provider netDebt subtracts cash equivalents. Average beginning/end equity/assets may support labeled ROE/ROA if prior-year snapshot available. Missing balance inputs stay missing.
D04: Recompute flow margins, OCF/net-income conversion and R&D/SBC/absolute capex intensity from aggregates. Valuation can use positive-denominator market-cap/net-income P/E, P/S, P/FCF, earnings/FCF yields and matched equity P/B, only with known matching quote/report currency. Simplified EV = market cap + debt - explicitly chosen cash equivalents, disclose exclusions and quote versus statement date. Do not sum shares or claim summed EPS/provider equivalence. Unsupported ROIC, debt-service coverage, per-share book values, inventory days, CCC, dividend yields remain missing unless defensible additional methodologies established.
D05: Eight valid quarters support current/prior-four TTM growth; five only supports quarterly year-over-year. Preserve annual evidence for 3-year CAGR. Derived evidence must retain source references/IDs, fiscal labels/dates/currency, formula and retrieval timestamps, with calculated label and limitations.
D06: Historical successful TTM ratio/metric samples do not override user's current lack of access; quarter ratios/metrics were restricted. V2 needs focused domain helper and explicit quarterly-only source mode; retain 8 rows internally and reuse quarter requests. Avoid TTM through investigation get_valuation_bundle and other TTM-backed tools; preserve V1 and saved resume. Schemas/dictionary are inferred observed unions, not guarantees.
Offline cases: exact AAPL totals above; synthetic missing/duplicate/restated quarter, mixed annual rows, symbols/currencies/windows, bad dates/fiscal sequence, nonfinite/bool values, missing versus zero, partial providers, sign conventions, nonpositive denominators, no TTM endpoint spy and V1 compatibility. Specialist read-only; no live collection.


## Plan and implementation

Selected P01-P06: pure validated quarterly TTM domain helper; V2-only 8-quarter data collection strategy; supported derived ratios with matched snapshot and currency/window guards; V2 investigation tool isolation; versioned saved reuse and context provenance; offline verification and scoped documentation. Unsupported provider-specific ratios stay missing. V1 behavior preserved. Builder started; no live collection authorized.

## Verification

Baseline focused offline suite: `pytest tests/test_deep_research.py tests/test_deep_research_recovery.py tests/test_deep_research_v2.py tests/test_deep_research_v2_recovery.py -q`: 79 passed, 100 dependency warnings, 59.37s, Anaconda Python 3.12.7. No live services.

## Jira drafts and results
No candidates yet.

## Durable creation attempt ledger
No attempts (0/5).

## Coordinator preliminary browser verification

Fresh app startup: `python -m streamlit run app.py --server.headless true --server.port 8521 --browser.gatherUsageStats false`; `curl.exe --fail --silent --show-error http://localhost:8521/_stcore/health` returned ok. Browser not opened on real app (avoids live provider rendering).
Offline browser harness outside repository at temporary `axiom-v2-quarterly-ttm-browser.py`, port 8522, actual V2 source/manager/UI with mocked HTTP and model factories. agent-browser named session axiom-ttm-qa selected AAPL/Quarterly/Stop after evidence, submitted, opened Comparison/TTM performance, asserted exact saved-sample revenue 466823000000 and FCF 136683000000 through 2026-06-27. Mock counters after collection: 8 providers, 1 planning call; resubmission with saved reuse plus full page rerun retained 8/1. This was run while builder finalizing sources; repeat/revalidate affected checks after final changes. Harness PDF output is a placeholder; this check is not PDF artifact validation or live financial accuracy.
Environment: Python 3.12.7, pytest 7.4.4, Streamlit 1.64.0.

## Independent review and correction ledger

- F01 High, fixed: prior/current four-quarter TTM growth could cross a missing fiscal year or different reporting currency. Builder now validates an eight-quarter contiguous common-identity/currency window before growth; current valid TTM survives invalid prior data. Independent original reproduction produced 25% from FY2025 USD versus FY2023 EUR; corrected reproduction suppressed growth.
- F02 High, fixed: a mismatched quote/profile security could supply another company's cap/price/name to AAPL. Explicit security identity now required and wrong records excluded without losing valid AAPL statement flows. Independent original reproduction used MSFT quote/profile with saved AAPL flows and displayed Microsoft/AAPL P/E20; corrected reproduction excluded quote/company/valuation.
- F04 Medium, fixed: shared comparison ratios could override safe calculated ratios with negative-denominator margins/intensities. V2 comparison now guards its own financial fields; legacy V1 helper remains unchanged.
- Average beginning/end ROE/ROA added with explicit two-snapshot methodology and validated prior-year snapshot. Independent saved AAPL ROE expectation 128930000000 / average matching current/prior equity = 1.4875108162676667 agreed.
- F05 Medium, fixed and independently verified: UI/PDF percentage magnitude heuristic mislabels calculated ROE2.5 as2.5% rather than250%; V2 fraction scaling must be explicit while growth/intensity percentage points remain unchanged.
- F06 Medium, fixed and independently verified: PDF financial basis table uses income currency/date for independently valid cash flows; require family-specific currency and end-date annotations.

## F03 Jira draft - blocked publication

Title: Make offline FMP reference collector compatible with truststore SSL injection
Type: Bug proposed; actual project type/priority metadata unavailable. Severity: Medium. Run/finding: 2026-10-03-deep-research-v2-quarterly-ttm-team / F03; D01-D03 saved-evidence tooling.
Baseline: existing untracked fmp_data_reference tree predates this team run; app truststore injection is already present in HEAD. This is a separate follow-up, not a V2 introduced defect.
Problem/impact: fmp_data_reference/scripts/reference.py:111 exports native roots through ssl.create_default_context().get_ca_certs(binary_form=True). App modules company_snapshot.py:21, market_overview_data.py:18 and top_movers_data.py:17 inject truststore globally; its get_ca_certs raises NotImplementedError. Collector initialization aborts before retry/cache/security tests, so combined root test inventory fails.
Evidence: root pytest before final fixes2failed137passed105.29s; both failures in CollectionTests.test_http_200_errors_and_reflected_credentials and test_transient_retry_is_bounded_and_cached. Standalone reference suite4passed1.76s. Explicit truststore.inject_into_ssl then same suite2failed2passed1.99s; no provider/model calls. Python3.12.7 Anaconda.
Proposed correction: choose supported CA acquisition/transport compatible with injected SSL while preserving TLS verification and credential filtering; do not disable verification.
Acceptance: collector initializes with native and injected SSL; all four offline reference tests pass alone and after app UI imports; retry/cache and reflected-credential quarantine remain covered; no live-provider request required.
Publication status: blocked. Independent verifier's isolated agent-browser session displayed Atlassian 'Log in to continue'. No authenticated Jira tools exposed; metadata/create permission/duplicate checks unavailable. No create call attempted, no ticket key claimed; attempt ledger remains0/5. Draft retained for later authenticated publication.

## Final delivery and verification

Implemented: focused quarterly_ttm.py domain calculations and V2-only v2_data.py shared REST collection; eight-quarter collection with four-quarter validated flows, matched point-in-time balance, common-basis growth, positive-denominator supported ratios and labeled two-snapshot ROE/ROA. Missing data/currency/security failures preserve independent successes. V2 tools exclude TTM-backed bundles; V1 default source/tools/comparison remain intact. Methodology-versioned reuse prevents silent old-run reuse; legacy recovery is explicit. Unverified app packets are visibly excluded. UI/PDF retain financial-family currencies, dates and correct percentage units. README/DEEP_RESEARCH/PLAN updated; new compact saved AAPL fixture and 53 quarterly test cases.

Final root command: `python -m pytest -q` with PYTHONPATH=src: 168 passed, 2 failed, 128 dependency warnings, 164.03s; 170 total cases, all 166 application cases passed. Both failures are existing standalone reference SSL incompatibility F03, independently reproduced before/from existing app injection, not V2 source changes. Final independent `pytest tests/test_quarterly_ttm.py tests/test_deep_research_ui.py -q`:62passed75.32s. Builder final quarterly/sharedUI/core subset94passed96.52s including actual PDF text extraction. Earlier scoped results retained above; interrupted intermediate full run does not count as a completed inventory.

Final compileall of app.py/src and app/main/domain/source/workflow imports passed after source freeze; existing cache/deprecation warnings only. Fresh real-app startup/health on8521 and offline harness health8522 passed. Final restarted browser harness reran AAPL/Quarterly/Stop after evidence, exact saved-sample revenue466823000000/FCF136683000000 through2026-06-27, displayed calculated-basis caption and separate cash/income dates/currencies. Saved resubmission, full rerun and comparison/tab navigation held mock counters8providers/1planning; no paid or live data calls. Screenshot: C:/Users/andna/AppData/Local/Temp/axiom-v2-quarterly-ttm-final.png. Browser PDF placeholder is not export evidence; actual generated PDF is verified independently by tests.

Independent review final disposition: F01/F02/F04/F05/F06 corrected; no remaining in-scope defect found. Only F03 follow-up Jira draft retained. Authenticated publication unavailable (Atlassian login), duplicate checks/metadata not performed; zero issues created and zero attempts. No commits, pushes or deployment. Unrelated working-tree edits preserved. Not verified: live entitlement, model narrative accuracy/quality or financial-provider formula equivalence, clean install/Docker and all-workspace exports. Unsupported ROIC/per-share formulas remain unavailable. Start Force fresh research for new-methodology data; old saved evidence remains explicitly legacy.

## Final source/test SHA-256 snapshot

```json
{
  "app.py": "6244de308a88235f4800a705ed32d9d5aa760ff0de262e3e259ec8af3b12a109",
  "src/langgraphagenticai/deep_research/quarterly_ttm.py": "2b931b0a0e45427739cf78d98c497c8519865f7dda037d3b03f35a7704971f7d",
  "src/langgraphagenticai/deep_research/v2_data.py": "7d11d73a27a7817ab8f019d617987c15ccb0c21618379d01198411ec915216e3",
  "src/langgraphagenticai/deep_research/v2_workflow.py": "ac9a1dbf97c89f8ae277b9e6c6613bd1bb76598389e88e75efa9af04afcc62e2",
  "src/langgraphagenticai/deep_research/manager.py": "7492d6e3283ce55874d86aa6fb358d5e2485aa951502f02dfd6f65f92a9ede08",
  "src/langgraphagenticai/deep_research/v2.py": "ec4916dc6537a0a6b9462ff6b7e8dfdedbbb3e5244d9e4d8fa861592837105af",
  "src/langgraphagenticai/deep_research/prompt_context.py": "0602c84e0d36195f875b2c2b2e4f04b642f8dd9a41d314a6e616f4bfaf839ea6",
  "src/langgraphagenticai/deep_research/presentation.py": "db36d214471f53a10a3e9735134892a569e7a3b0e21afe061220ac8abe4c42d8",
  "src/langgraphagenticai/ui/deep_research_tab.py": "3a5ad93b1a6646108afd617233d89aacd412e53077463cdd6ae277fdf95dafd2",
  "src/langgraphagenticai/ui/deep_research_v2_tab.py": "2767ecce38957145ddd5ad7778fca5061218719ed3936cff943cd83fb4095293",
  "tests/test_quarterly_ttm.py": "49e812504f01a4a405ad31fae33a6c2ea0c41fda137b7ad7d486281f8734ae4b",
  "tests/fixtures/aapl_quarterly_ttm_20261003.json": "8d01f0bf1700ca541c8aaf9ab7c004da63513f6803f03b6224d8a34891fff75d"
}
```
