# Verification commands

Run from the Git repository root in the project's installed Python environment. These are examples to adapt to the changed area, not a command to run every check for every documentation edit.

## Environment and source path

PowerShell:

```powershell
python -c "import sys, streamlit, pytest; print(sys.executable); print(streamlit.__version__)"
$env:PYTHONPATH = (Resolve-Path "src").Path
```

If the interpreter lacks dependencies, locate the project's existing environment before installing anything. Do not hard-code another developer's machine path into repository scripts.

## Offline tests

Select existing tests that actually cover the change:

```powershell
python -m pytest tests/test_market_tabs.py tests/test_hardening.py -q
python -m pytest tests/test_deep_research.py tests/test_deep_research_recovery.py tests/test_deep_research_v2.py -q
python -m pytest tests/test_equity_committee.py -q
python -m pytest -q
```

The first three are area examples; the last is the full suite. New provider/model code needs mocked boundaries before it enters these tests. Do not use real API credentials in fixtures.

## Compile/import affected modules

Example for an Introduction change:

```powershell
python -m compileall -q src/langgraphagenticai/ui/introduction_tab.py src/langgraphagenticai/providers/market_history.py
python -c "import langgraphagenticai.ui.introduction_tab; import langgraphagenticai.providers.market_history"
```

Adapt paths to the actual changed modules. Import success alone does not prove a page renders.

## Streamlit startup and health

Choose a free port. Reuse only a matching, suitable project instance; never stop an unrelated server.

```powershell
python -m streamlit run app.py --server.headless true --server.port 8510
```

In another tool session or terminal:

```powershell
curl.exe --fail --silent --show-error http://localhost:8510/_stcore/health
```

The app loads .env automatically. Browser page rendering can invoke live providers even though startup/health appears local. Use a temporary mocked Streamlit harness when the check must remain offline; otherwise identify it as a live provider smoke check and keep model actions unclicked.

Use the installed browser workflow if available, with an isolated session, and test the concrete changed control. Capture screenshots outside the repository. The health endpoint checks the server, not the page logic.

## Diff and hygiene

```powershell
git status --short
git diff --check
git diff --stat
git diff --cached --stat
```

Inspect the actual diff before concluding that only intended files changed. Do not stage or commit as part of verification.

Inspect .env.example, ignored secret paths, download inputs, and changed URLs using secret-safe methods. Never cat .env or dump session state/configuration to prove a secret check.

## Documentation-only or skill changes

Validate skill manifests, UI YAML, linked references, repository paths, and runnable examples. State that application tests/startup/browser checks were not rerun if app behavior did not change. Do not report the previous task's tests as newly run verification.
