# Axiom project skills

These nine repository skills give Codex reusable workflows for maintaining Axiom Research. They live in `.agents/skills/`, alongside the project, and refer to its actual modules and tests. They are coding workflows; creating them does not add new agents or buttons inside the Streamlit app.

## Getting started

Open this repository in Codex. Choose a skill from the skill picker or include its name in your prompt:

```text
Use $axiom-provider-debug to fix missing price and volume data on Top Movers.
Preserve the existing ranking rules and add offline regression tests.
```

Include the affected workspace, the symptom or desired behavior, and any constraint that matters. Mention a ticker, metric, chart range, error, or reproduction step when you have one. You do not need to provide every implementation detail.

Codex can also select a matching skill automatically from a normal request. Naming one explicitly makes your intended workflow clear. Repository skills are discovered from `.agents/skills`; if a new skill does not appear, restart Codex and reopen this project. See [official OpenAI skill documentation](https://learn.chatgpt.com/docs/build-skills).

If your client does not expose a picker or recognize the name yet, use the file directly:

```text
Read .agents/skills/axiom-provider-debug/SKILL.md and use that workflow
to fix missing data on Top Movers.
```

No global installation, API key, or additional plugin is needed just to load these instruction-only skills. Carrying out a task can require the project's Python dependencies, a browser, or explicitly authorized provider access. The skill does not replace those requirements.

## Which skill to choose

| Skill | Use it when | Example request |
| --- | --- | --- |
| [axiom-provider-debug](../.agents/skills/axiom-provider-debug/SKILL.md) | Quotes/news are missing, stale, inconsistent, or failing. | `Use $axiom-provider-debug to explain and fix N/A values for BRK.B without substituting another listing.` |
| [axiom-financial-correctness](../.agents/skills/axiom-financial-correctness/SKILL.md) | You question TTM, growth, valuation, scores, or price-return math. | `Use $axiom-financial-correctness to review Equity Report revenue growth and show any fiscal-period mismatches. Do not edit yet.` |
| [axiom-streamlit-workflows](../.agents/skills/axiom-streamlit-workflows/SKILL.md) | Buttons/charts do not react, results reset, or ticker handoffs break. | `Use $axiom-streamlit-workflows to preserve Top Movers filters when I open a snapshot and return.` |
| [axiom-research-grounding](../.agents/skills/axiom-research-grounding/SKILL.md) | AI reports have unsupported claims, bad citations, fragile structured output, or failed recovery. | `Use $axiom-research-grounding to make unknown citations visible and preserve the draft when review times out.` |
| [axiom-portfolio-validation](../.agents/skills/axiom-portfolio-validation/SKILL.md) | Weights/caps, cash, proposed trades, or optimizer risk metrics look wrong. | `Use $axiom-portfolio-validation to verify that position and sector caps still hold after allocation, including residual cash.` |
| [axiom-cost-performance](../.agents/skills/axiom-cost-performance/SKILL.md) | Pages are slow, calls repeat, or Deep Research spending is hard to explain. | `Use $axiom-cost-performance to measure rerun call counts and remove duplicate AI calls without changing my selected model.` |
| [axiom-safe-refactor](../.agents/skills/axiom-safe-refactor/SKILL.md) | You want to extract a focused responsibility from a large module. | `Use $axiom-safe-refactor to extract Equity Report export builders while preserving saved payloads and report content.` |
| [axiom-export-safety](../.agents/skills/axiom-export-safety/SKILL.md) | PDF/Excel/CSV/JSON content is wrong, unreadable, or potentially unsafe. | `Use $axiom-export-safety to fix the Excel download and test numeric cells, formula injection, and credential filtering.` |
| [axiom-release-check](../.agents/skills/axiom-release-check/SKILL.md) | You want evidence that a change is ready to hand off or release. | `Use $axiom-release-check to verify the current changes. Report failed and untested checks; do not commit or deploy.` |

## A useful everyday sequence

For a bug, start with the skill that matches the symptom. Ask for a fix when you want changes, or say "review only" when you want findings. The skills distinguish those modes.

For a larger calculation change, combine two relevant skills instead of asking Codex to apply all nine:

```text
Use $axiom-financial-correctness and $axiom-export-safety to fix
the affected valuation metrics and keep the Excel/PDF outputs consistent.
Use synthetic inputs and do not make paid API calls.
```

For a performance issue, specify what must stay reliable:

```text
Use $axiom-cost-performance to reduce Deep Research V2 latency.
Keep citation validation, preserve the selected models, and show
before/after call counts and prompt sizes using mocked responses.
```

After a substantial change, request the release check:

```text
Use $axiom-release-check to verify the change against AGENTS.md.
Run the relevant offline checks and tell me what remains unverified.
```

The release check verifies readiness; committing, deploying, or publishing still requires a separate instruction. Loading a skill does not itself run tests or call providers. The task determines which actions are appropriate.

## What a good result should include

Expect the concrete fix or review finding, the reason, relevant verification, and remaining limits. For numerical work, request a small reproducible example. For performance work, request measured call counts and clearly labelled cost estimates. For a control change, request proof that the rendered interaction changes the expected state.

The skills inherit the repository's engineering requirements from AGENTS.md. They add workflow-specific guidance such as FMP/Yahoo symbol translation, fiscal-quarter checks, cap-aware cash handling, citation recovery, and spreadsheet export inspection. They do not duplicate or replace the global requirements.

## Maintaining the skills

Each skill contains:

```text
axiom-skill-name/
  SKILL.md              Scope and task-specific workflow
  agents/openai.yaml    Picker label and suggested starting prompt
  references/           Optional fixtures or commands for that workflow
```

Edit the relevant SKILL.md when a real project change makes its workflow outdated. Update referenced module paths and examples when code is moved. Keep its description focused so automatic selection remains useful.

Supporting references are loaded only when needed. No new executable helper scripts or dependencies were added for this collection. The release-check reference includes commands for the existing runtime and tests; adapt the interpreter and affected modules to your environment.

These files can be committed with the repository so collaborators receive the same workflows. The skills are discoverable by file layout, but actual picker visibility depends on the running Codex client; validation of the files is not a live-client discovery test.
