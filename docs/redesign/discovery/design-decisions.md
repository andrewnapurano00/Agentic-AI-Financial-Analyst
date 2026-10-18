# Gate 1 design decisions — 2026-10-13

1. Keep Streamlit, Axiom Research branding and the eight existing route strings. Show `Introduction` as Market Brief in navigation and page title. Group the radio choices visually under Discover, Analyze and Allocate only through a method that preserves `active_workspace` values and keyboard operation.
2. P02 uses the implementation contract's navy/gold tokens as initial values. Gold denotes selection/action; green/red denote signed market direction. Missing, zero and negative values retain text labels. No decorative gradient, synthetic live marker or fetched font.
3. Treat the three images as composition and density references. Their specific prices, report content, coverage scores, dates, portfolio presets, Global Equities selector and commands are illustrative. No functional control is added solely to match an image.
4. Preserve current page bodies and exports during shared-shell work. Later page owners relocate only mapped active content and controls, then verify them. `source-ui-inventory.csv` includes inactive/legacy candidates, so its 755 rows are a discovery backlog, not a claim of 755 simultaneously rendered items.
5. The earlier company terminal implementation already supplies ordered metric grids, earnings and peer panels with partial-coverage disclosures. Their dynamic UI is included in the preservation map. Additional D04/D05 heatmap ETF return and sector size bases remain unverified; RDS-09 is separate and no heatmap tab is made functional in P02.
6. Shared components accept normalized page data; page modules own controls and backend orchestration. Integration owns `main.py` and `loadui.py`, shared UI owner owns shell/presentation helpers. This resolves the early-return shell discrepancy with one coordinated edit boundary.
7. Evidence status never infers freshness from a credential, cache hit, render time or generated-image badge. Provider facts, calculated metrics, AI interpretation and user assumptions remain distinct.

## Proposed shared interface signatures for P02 review

Existing calls keep these signatures and behavior unless the integration owner approves an adapter in the same integration change:

| Interface | Exact callable contract | Caller/return behavior |
| --- | --- | --- |
| Shell CSS | `inject_app_shell_css() -> None` | `LoadStreamlitUI`; style injection only |
| Global command | `render_command_bar() -> str` | `main.py`; returns stripped query only after explicit Run; keys `terminal_command`, `terminal_run` |
| Market context | `render_market_strip() -> None` | `main.py`; static labels only until real market evidence supplied |
| Page title | `render_page_header(page: str) -> None` | `main.py`; route ID in, display label via `PAGE_LABELS` |
| Readiness footer | `render_terminal_status(model_name: str, *, fmp_ready: bool, openai_ready: bool) -> None` | `main.py`; configured status/page-render time, never data freshness |
| Evidence row | `render_evidence_row(items) -> None` | Page renderers; ordered `(label, value)` pairs, escaped on display |
| Company context | `render_company_header(symbols, company="", detail="") -> None` | Research/page renderers; escaped metadata |
| Summary cards | `render_executive_cards(cards) -> None` | Page renderers; ordered `(label, value, note)` tuples, bounded to three, escaped |
| State banner | `render_workspace_state(message, *, state="empty") -> None` | Page renderers; `failure`, `partial`, `stale` retain visible warning/error distinction |
| Opening scope | `opening_styles() -> None` | Introduction and Top Movers; P02 unifies its tokens with shell |
| Opening card/notes | `heading(title, subtitle)`, `cards(items)`, `observations(items)` | Existing opening renderers; data and order unchanged |

For sidebar grouping, the safest P02 contract is still `st.sidebar.radio(..., key="active_workspace")` over the unchanged eight string values with `format_func` displaying Market Brief. Group labels can be inert headings adjacent to the radio only if keyboard navigation and the single selected control remain clear; if that cannot be done cleanly, retain the radio and defer visual grouping. Do not replace it with separate controls that reset `active_workspace` or typed handoffs.

`docs/redesign/references/` now contains the three repository reference copies supplied by integration. The integration owner must review these signatures and the route readback before Gate 1 PASS. App edits wait for that record.
