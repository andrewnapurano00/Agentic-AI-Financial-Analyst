# Repository layout

Updated 2026-10-24. The app runs from `app.py` and the package under `src/`. Extra folders below support verification, contributor guidance and retained evidence; they are not separate active applications.

| Location | Purpose / retention rule |
| --- | --- |
| `app.py`, `src/langgraphagenticai/` | Current Streamlit app, provider/domain layers and retained tested compatibility engines. Do not prune by filename or static import search alone. |
| `portfolio_architect_app.py` | Supported focused Robo Advisor launcher. |
| `requirements*.txt`, `constraints.txt`, `pyproject.toml`, `runtime.txt` | Dependency/install/test configuration. |
| `.streamlit/`, `.env.example` | Public configuration and key-name examples; real secrets stay ignored. |
| `Dockerfile`, `Dockerfile.verify`, `.dockerignore`, `.github/workflows/`, `scripts/` | Runtime/verification definitions and release inventory/gates; passing local tests do not certify clean installs or hosting. |
| `tests/`, `data/sample_holdings.csv` | Offline tests and synthetic example holdings. Never substitute private portfolios into fixtures. |
| `fmp_data_reference/` | Retained provider schemas, bounded samples, dictionaries and reference scripts. Tests/Docker verification use sample files; it is not stale runtime code. Workbook remains `FMP_API_References_and_Example_Schemas.xlsx` in the repository root, matching its reference-script contract. Raw provider captures remain ignored. |
| `README.md` | Current user workflow guide. |
| `AGENTS.md`, `.agents/skills/`, `docs/PROJECT_SKILLS.md` | Contributor requirements and scoped workflows. |
| `PLAN.md`, `docs/roadmap/` | Current status/evidence and detailed remaining work. `deep-research-cost-optimization.md` is a historical design checklist, not current completion status. |
| `docs/features/`, `docs/reviews/`, `docs/diagnostics/` | Dated delivery, review and diagnostic records. Retain their historical scope/limitations. |
| `docs/redesign/`, remaining `docs/` specifications | Canonical design/QA material and deployment/domain references. |
| `docs/references/` | Experimental provider notebook; not a runtime dependency. Root `mcp_prompts.txt` remains developer test-prompt reference. |
| `exports/`, `outputs/`, `verification/`, caches, `.env` | Local outputs/credentials, ignored by Git. Preserve user work; never force-add. |
| `Live_Agent_Traders/`, `debug_codex.txt` | Ignored local course/debug material. Not app dependencies; retained locally after Windows access restrictions. |

The root FMP workbook and MCP prompt reference are intentionally retained without duplicate tracked copies. The experimental notebook and historical cost roadmap are organized in their documented locations. Credentials, raw outputs and course material are not part of publication.

The retired Portfolio Ideas/simulation paths remain source/fixtures for compatibility checks; the sidebar does not expose them. Runtime Docker copies `app.py`/`src`, while the derived verification image also needs selected tests/data/reference fixtures. Monitoring and hosted durable jobs remain disabled pending their documented gates.

Saved executive memo PDFs use pure deferred download callbacks: opening a report does not render its complete evidence appendices. The original evidence and PDF contents remain retained. See PLAN for the navigation regression and measured layout cost.
