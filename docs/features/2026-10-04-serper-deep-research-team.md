# Serper news in Deep Research V1 and V2

Run ID: 2026-10-04-serper-deep-research-team
Mode: build. Outcome: ensure both workflows explicitly retrieve Serper news when enabled and configured, with observable missing/partial/failure states and offline regression coverage. No new authorization to commit, push or deploy. No live financial-provider/model calls.

Baseline commit: a31fd347ddbc0cc63d367fa09e673a883fe0fa49
Baseline snapshot: C:\Users\andna\AppData\Local\Temp\axiom-serper-baseline-um8zyllc
Initial working-tree changes are preserved; target files may contain earlier user work.

## Acceptance criteria

- Both run paths wire the configured Serper key and call the news endpoint with requested lookback.
- News-disabled paths make no Serper news calls; ordinary UI reruns do not collect news.
- Saved evidence preserves news source metadata and distinguishes missing credentials, zero results and request failures without discarding financial evidence.
- Offline adapter/orchestration/UI checks and relevant documentation are updated; independent review completes.

## Handoffs and verification

Pending specialist, planner, builder and verifier.

## Jira attempt ledger

Creation budget: five. Attempts used: zero. Only substantive unresolved issues may be candidates; no activity ticket for completed work.

### Specialist handoff ? D01?D06

Both V1 ResearchManager.run and V2 QuarterlyResearchManager.run already reach POST https://google.serper.dev/news, gated by include_news. Shared sidebar key plumbing is present. Adapter uses bounded POST timeout (5,25), X-API-KEY, company query, num5 and tbs=qdr:dN. News[] title/link/snippet/date/source normalize to title/url/snippet/published/publisher; provider publication strings are not exact timestamp/lookback proof. Planner investigations use /search organic[] separately. Missing key avoids network; structured news failures preserve financial evidence. Malformed collection types currently can throw TypeError and stop collection. Adapter retrieval time is not propagated into Evidence. V2 lacks explicit successful fresh-run news integration coverage and visible configuration/coverage feedback. No saved live Serper sample was found. Official Serper site advertises News (https://serper.dev); playground is login/client gated, so existing exact route/payload contract is retained without a new primary-documentation claim. Specialist performed read-only inspection only. Live access, credits and completeness remain unverified.

### Planner handoff ? P01?P05

P01: reject malformed news/organic collection shapes without failing the run. P02: propagate adapter retrieval timestamp into saved news evidence. P03: shared V1/V2 coverage presentation, including partial/zero coverage and V2 configuration help. P04: real factory-to-manager-to-mocked-HTTP news integration for both versions. P05: disabled/reuse/resume no-recollection checks and documentation. Shared changes require full pytest, compile/import, health and synthetic browser checks.

Delegation: specialist and planner completed read-only handoffs. Planner source inspection was useful but reported it could not locate the requested skill despite the explicit repo path; coordinator read and applies the skill. New agent creation reached the environment thread limit. Existing /root/planner (from the earlier timestamp task, distinct from this run's serper_planner) was reused as builder. A fourth distinct verifier may be unavailable; any role reuse for final independent-of-builder review will be disclosed, rather than claiming a fourth agent was spawned.

Scope decision: build the bounded P01?P05 slice. Existing endpoint and credentials routing are retained; no new provider, live-news entitlement claim, or automatic research calls. Null/absent response collections remain safe empty; malformed non-list collections become explicit failures.


## Final verification and disposition

- Fresh root inventory: `PYTHONPATH=src;<temporary guard directory> python -m pytest -q -p offline_guard` completed with **214 passed, 2 failed, 128 warnings in 89.56s** (216 collected cases). This includes 23 new Serper tests, the existing application tests, and four untracked FMP reference tests. The suite is not fully passing. Both failures are the existing reference collector's certificate export (`ssl.create_default_context().get_ca_certs(binary_form=True)` raises `truststore.NotImplementedError`), outside the Serper delta. Market modules' existing global truststore injection and reference collector source were unchanged. Temporary autouse guard blocked unmocked Requests/httpx sends; no live financial/model calls.
- Builder focused suite: 92 passed, 100 dependency warnings, 73.87s. Reviewer independently ran 23 Serper tests: all passed, 22.45s. Python 3.12.7 / pytest 7.4.4 / Streamlit 1.64.0 in installed Anaconda environment.
- Coordinator compileall `app.py src` and imports of app/main, Serper adapter, manager, shared news UI and both page modules passed. Diff validation passed; baseline hashes confirmed unrelated source/test files preserved.
- Fresh app startup/health passed on port 8534. Offline actual-page browser harness health passed on 8535. Browser exercised V1 full/partial coverage and V2 full/partial/zero/disabled news, missing-key help, Sources navigation and full rerun. Coverage showed saved UTC retrieval date; unexpected provider/research calls stayed zero. Synthetic saved data and blocked network/factories; screenshots and harness outside repository. Fresh factory-to-HTTP behavior is established by mocked integration tests, not a live browser research run.
- No live Serper entitlement/credits check, live model run, clean install, Docker/hosted deployment or new export artifact validation. No source commit/push requested for this run. Independent review found no unresolved Serper defects; Jira queue empty, zero creation attempts/writes. Fourth distinct agent was unavailable under environment thread limit, so the planner was reused as reviewer independently of the builder. R02/R04/R06 remain partial beyond this slice.

Delivered files: `tools/serper_tools.py`, `deep_research/manager.py`, `ui/research_news.py`, both research page modules, `tests/test_serper_deep_research.py`, one intentional assertion update in `tests/test_deep_research_ui.py`, README/DEEP_RESEARCH/PLAN and this report. Source delta was compared to the initial snapshot; previous recovery, quarterly TTM and skill edits remain separate. V2 checkbox help was corrected and independently rechecked to qualify company-news lookback separately from planner web research. No eligible unresolved ticket payloads; ledger attempts used **0/5**, no pending/failed/uncertain entries. Implementation and Serper acceptance are verified offline; broader root suite remains limited by the two existing FMP collector failures.

## Resumed correction: user-reported zero live news results

User reported AAPL and MSFT news gaps reading ?No matching search results returned,? plus separate app-finance investigation failures. These are user-observed live results, not an agent live test. D03/D06/D07 specialist clarification: simplify initial news q to company name plus normalized ticker (ticker-only fallback), retaining endpoint, requested lookback, locale, five-result limit, timeout, concurrency and call count. Existing topic keyword list may be restrictive, but actual cause is not proven. Distinguish genuine empty provider list from missing expected collection and nonempty records all rejected for malformed/unsafe links. No live provider/model calls or extra fallback calls authorized. Investigation tool failures remain separate. Reuse original report/ledger; attempts remain zero. Builder correction and independent recheck pending.

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
