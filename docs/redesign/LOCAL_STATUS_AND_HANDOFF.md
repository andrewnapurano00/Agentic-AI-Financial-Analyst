# Axiom local redesign: status and return-to-work guide

**Snapshot:** 2026-10-16, local working tree on `main` at `be858cd`. This is a status record, not a release sign-off. Check `git status`, [PLAN.md](../../PLAN.md), and the [acceptance matrix](qa/acceptance-matrix.csv) before treating any item below as current. The canonical supplied specification is retained in [implementation-contract.md](implementation-contract.md) and adjacent design/reference files. October18 cleanup archived the superseded `partial_redesign/` upload outside the repository after verifying all eight assets were byte-identical to their canonical copies.

## What is implemented locally

The existing eight-route Streamlit app is intact. A shared navy/gold terminal shell, navigation grouping, configuration disclosure, executive/evidence presentation, and responsive page compositions have been added across Market Brief, Top Movers, Research Chat and Guided, Equity Report, Stock Screener, Portfolio Optimizer and AI Manager, Deep Research V1, and the separate V2 pilot. The detailed source-to-destination inventory is in [`preservation-map.csv`](discovery/preservation-map.csv); the dated design and implementation account is in the [team report](../features/2026-10-13-professional-redesign-team.md).

The page changes emphasize saved results and recovery while keeping explicit provider/model actions. Research Chat shows prior findings above its editable draft. Guided, Equity, and both Deep Research versions put saved findings ahead of new-run setup. The Optimizer retains a completed result across ordinary reruns and failed attempts. Screener retains a prior result through four empty-result exits. Screener universe and enrichment requests now use the caller's FMP key with credential-scoped caches, tested across separate synthetic sessions. Existing financial and model workflows were preserved in bounded page slices; this statement does not certify every conditional branch.

Representative PDF, XLSX, CSV, and JSON downloads are parsed in offline tests. Direct CSV and Equity XLSX output now sanitize formula-like text, including categorical cells and dynamic labels; Guided JSON is bounded and filtered for credentials. Saved numeric values and source frames remain unchanged. These checks cover selected artifacts, not every output state.

Five redesign follow-up Jira Tasks were created and read back: [AAFA-15](https://bigmeatpete717.atlassian.net/browse/AAFA-15) Market/Movers, [AAFA-16](https://bigmeatpete717.atlassian.net/browse/AAFA-16) Research/Equity, [AAFA-17](https://bigmeatpete717.atlassian.net/browse/AAFA-17) Deep Research, [AAFA-18](https://bigmeatpete717.atlassian.net/browse/AAFA-18) Screener/Portfolio, and [AAFA-19](https://bigmeatpete717.atlassian.net/browse/AAFA-19) heatmap data contract. Their creation is tracking, not proof that their acceptance criteria are complete. The original team run's five-create-attempt budget is exhausted; no existing Jira issues were updated during this redesign run.

## What remains to implement or decide locally

1. **RDS-09 sector heatmap — bounded October 16 delivery.** Market Brief now includes the eleven-sector interactive mosaic, an FMP latest-price versus historical-adjClose Day/Week/YTD table (October16 price-basis correction) and explicit-load screened-industry membership. Equal-sized tiles and unavailable industry-wide returns disclose remaining data limits. Comprehensive constituent market-cap sizing, dated industry returns and live entitlement remain open under AAFA-19; see the [current contract](sector-heatmap-contract.md) and PLAN's D-20261016-HEATMAP rather than the earlier quote-only discovery boundary.
2. **Reference fidelity.** The three reference compositions and remaining page bodies have bounded implementations, but exact side-by-side approval is outstanding. Recorded deviations include the V1 Deep Research thesis starting below the first 1440x900 viewport and Manager results appearing below lengthy inputs. Review these with the [visual comparison](qa/visual-comparison.md), then make scoped local corrections that preserve widget/session behavior.
3. **Full preservation parity.** The inventory contains 795 rows, 714 classified active/reachable. Selected rows have fixture evidence; most are source-traced with conditional runtime checks pending. Every active row needs a verified destination and applicable branch evidence before declaring full spec completion. A reachable call site alone is not a rendered-state pass.
4. **Broader product roadmap.** [PLAN.md](../../PLAN.md) retains partial R01-R10 outcomes, including universal financial provenance/freshness, complete Portfolio/Compare handoffs, broader provider normalization, and V2 evaluation. These are not silently included in the redesign completion claim.

No currently confirmed blocking defect remains from the last scoped Screener credential-isolation and representative-export reviews. Open items above mix known missing functionality with acceptance work that may reveal further local fixes.

## Awaiting testing and acceptance

The [acceptance matrix](qa/acceptance-matrix.csv) is the item-by-item source of truth: **ACC-01 passed** for accessibility of all eight routes and nested modes in a guarded walkthrough; **ACC-02 is open**; **ACC-03 through ACC-12 are partial**. In particular, complete:

- Conditional success, empty, partial, stale, mismatch, failure, retry, and saved-result browser journeys for each redesigned route; verify cross-route remount and separate-session state isolation.
- Instrumented no-paid-call checks for ordinary filters, chart ranges, tabs, selection, navigation, reruns, and downloads, while confirming explicit actions still call only their intended providers/models.
- Full export schema/content parity for conditional branches and browser file-save completion. The browser automation download command canceled on both Axiom Screener and an isolated minimal Streamlit control, so the latter remains a tooling-limited check, not a proven app defect.
- Financial source/basis/currency/unit and scoring checks for conditional result paths, plus optional bounded live-provider contract sampling when authorized. Offline fixtures cannot certify current entitlements, freshness, or model narrative accuracy.
- Lower-panel overflow, keyboard/focus order, contrast, and signed-value cues at 1440, 1920, 1024, and 390 px. Some synthetic captures exist at those widths; the full accessibility/conditional audit does not.

The latest final-source guarded full suite passed **521 tests in 155.51 seconds** on Python 3.12.0, pytest 9.1.1, Streamlit 1.61.1. Focused Screener credential tests passed 16/16. `compileall` of `app.py` and `src`, app/main imports, `pip check`, and `git diff --check` passed. A fresh guarded Streamlit server returned `/_stcore/health` = `ok`; two synthetic browser sessions retained distinct Screener results (AAA and BBB). These are recorded in [PLAN.md](../../PLAN.md) and the [team report](../features/2026-10-13-professional-redesign-team.md). Tests blocked external provider/model transport; no live financial or paid AI calls were used. After any code change, rerun the checks required by [AGENTS.md](../../AGENTS.md), rather than reusing these dated results.

## Outside this local-only phase

Docker/runtime image and derived verification image were not certified because package-download transport failed; clean Python 3.11/3.12 installs, non-root image startup, and the remote GitHub CI matrix remain unverified. Hosting target, protected access, hosted smoke, and rollback rehearsal await deployment planning. See [deployment runbook](../../docs/DEPLOYMENT.md) and AAFA-12. None of these are evidence that the local app cannot be tested now.

This redesign is in the working tree and has **not** been staged, committed, pushed, or deployed in this run. The original `partial_redesign/` folder remains untracked. Preserve unrelated changes and inspect the diff before any later Git action.

## Where to resume

Start with the [acceptance matrix](qa/acceptance-matrix.csv), [visual comparison](qa/visual-comparison.md), the page-specific files under [`discovery/`](discovery/), and the [team report](../features/2026-10-13-professional-redesign-team.md). Prioritize ACC-02 and conditional no-call/recovery/export checks; fix defects found in local code. Treat RDS-09 as a separately gated financial-data feature. Update this document, the matrix, and PLAN with dated evidence as work proceeds, distinguishing implemented behavior from tested behavior and deployment gates.

October18 repository cleanup: the October16 working-tree status above is historical. The duplicate upload and obsolete valuation handoff shell were archived outside the repository under the user-authorized cleanup; current source, canonical design files and QA evidence are retained. See PLAN D-20261018-REPOSITORY-CLEANUP for publication status.
