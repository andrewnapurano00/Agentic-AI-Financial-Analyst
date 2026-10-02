---
name: axiom-streamlit-workflows
description: "Fix Axiom Streamlit controls, charts, reruns, saved results, and ticker handoffs between workspaces without repeat AI calls."
---

# Axiom Streamlit Workflows

Make the requested control change real application state, preserve completed work, and verify the rendered result.

Read the repository AGENTS.md. Reuse `src/langgraphagenticai/ui/app_shell.py` for the Axiom terminal design; this skill does not request a redesign.

## Locate state and ownership

- `src/langgraphagenticai/main.py`: workspace routing and pending research queries.
- `ui/introduction_tab.py`, `ui/top_movers_tab.py`: market interactions and company handoff.
- `ui/streamlitui/loadui.py`, `ui/streamlitui/display_result.py`: chat controls and result display.
- `ui/deep_research_tab.py`, `ui/deep_research_v2_tab.py`: explicit run/recovery actions.
- `deep_research/context.py`: allowlisted app evidence bridge, not a universal navigation context.
- Abbreviated paths are under `src/langgraphagenticai/`.

Search the exact widget key and session key before changing either. Existing handoffs include `next_workspace`, `intro_company_symbol`, `intro_company_query`, and `pending_research_query`; confirm their current readers. A universal typed ResearchContext is roadmap work, not an existing interface to assume.

## Implement the interaction

1. Define the flow as workspace -> action -> expected state/output. Check whether the control is a real widget or decorative HTML.
2. Give widget state a stable owner. For dependent selectboxes, reconcile a saved selection when options change. Avoid resetting unrelated page filters or completed research.
3. Separate evidence retrieval, deterministic transformations, and AI generation. Ordinary widget reruns, downloads, formatting, and navigation must reuse saved AI output; generation/recovery needs an explicit user action.
4. Tie range controls to actual dated history. Show the selected period, source, latest observation, and price/return basis; provide useful empty and partial states. Do not fabricate sparklines.
5. Carry a normalized ticker and explicit intent across the handoff. If changing an existing session-key contract, update producers and consumers together. Do not migrate every workspace for a small control fix.
6. Escape provider-controlled HTML and validate external link destinations. Prefer shared components and native widgets over new page-specific CSS.

## Verify

Use Streamlit AppTest with mocked provider/model boundaries. Exercise the initial view, changed control, rerun, and relevant return navigation; assert both resulting state and paid-call counts. Existing examples: `tests/test_market_tabs.py`, `tests/test_deep_research_ui.py`.

Start or reuse a suitable local Streamlit server, check `/_stcore/health`, and exercise the actual control in a browser when tooling is available. Use the installed browser skill and an isolated session. For layout changes, inspect laptop and narrow widths. Keep screenshots and temporary harnesses outside the repository.

Report the observed interaction and any state or browser behavior that could not be verified.
