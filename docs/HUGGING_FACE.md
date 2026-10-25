# Hugging Face single-owner setup

The app owner reported successful deployment on 2026-10-25 at
[the Axiom Space](https://huggingface.co/spaces/andrewnap211/Agentic-AI-Financial-Analyst-v2).
This records that report, not an independent audit of every hosted workflow.

## Prepare the upload

From the repository root, run:

```sh
python scripts/export_huggingface.py --output exports/axiom-huggingface-runtime.zip
```

Create a **Docker** Space, extract the archive and upload its **contents** at the
Space root. Preserve `src/`, `docs/` and the hidden `.streamlit/` folder. The
generated README includes the Hugging Face YAML configuration (`sdk: docker`,
`app_port: 7860`); the GitHub README stays focused on using the app.

The archive contains app.py, the complete Git-visible runtime source under src,
requirements.txt, constraints.txt, Dockerfile, .dockerignore, the dark-theme
configuration and setup documentation. It excludes private credentials, tests,
course material, caches and saved research outputs. Inspect new source files
before exporting; filename filtering cannot detect arbitrary embedded secrets.

## Configure secrets

In **Settings > Variables and secrets > Secrets**, enter raw values without quotes:

| Secret | Purpose |
| --- | --- |
| `AXIOM_OWNER_PASSWORD` | Required unique random owner password, 24 to 1024 characters; generate it in a password manager. |
| `FMP_API_KEY` | Most company data, screening and quotes. |
| `OPENAI_API_KEY` | Main AI workflows, chat and report generation. |
| `SERPER_API_KEY` | Search and supported research evidence. |
| `MARKETAUX_API_KEY` | Additional financial news and supported news chat tools. |
| `GROQ_API_KEY` | Optional Low cost Deep Research stages. |

Docker Spaces inject these as environment variables. The existing provider-key
loader supports them; no `.env`, `secrets.toml`, `HF_TOKEN` or OpenRouter key is
needed for the active app. Missing provider access disables dependent features.

Leave `AXIOM_RUNTIME_MODE` unset in Space variables: the Dockerfile selects
`huggingface_single_owner`. Remove a conflicting old override and rebuild. Never
set `local` to bypass hosted access. The generic `hosted` mode remains blocked.

The container uses port 7860, UID 1000 and a writable home. The theme file is
explicitly copied into the image. If fields appear white, replace Dockerfile and
the shared `src/langgraphagenticai/ui/app_shell.py`, upload
`.streamlit/config.toml`, rebuild and reload the page. Do not upload secrets to Git.

## Sign-in and data boundaries

Use a private Space and keep the owner password private. This is a bounded
**single-owner** adapter, not multi-user account authentication: every authorized
browser uses the same owner's provider credits. Sign-in is checked before
workspace controls, with constant-time digest comparison, a process-wide limit
of five attempts per minute and an eight-hour session lifetime. A process restart
resets the attempt budget. Successful attempts count toward that budget too.

Password rotation invalidates sessions on their next app rerun. After changing
Space secrets, restart the Space. **Sign out** clears the current session's work.
Already offered downloads are not retroactively revoked. Sessions and model
resources remain bounded/session-backed; no durable save/resume, authenticated
background jobs, monitoring, alerts or broker execution is activated here.

## Verification limits

Local synthetic authentication, startup, theme and export checks are recorded in
[PLAN](https://github.com/andrewnapurano00/Agentic-AI-Financial-Analyst/blob/main/PLAN.md) in the repository. The successful hosted deployment is
user-reported. The historical failed dependency audit, clean-install/remote-CI,
multi-user identity, durable jobs and backup/rollback gates remain separate;
single-owner sign-in does not establish full AX-10 or production readiness.
See [the deployment runbook](DEPLOYMENT.md) for those broader gates.
