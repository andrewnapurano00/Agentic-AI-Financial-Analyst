# Deployment rehearsal runbook

P05 local automation prepares broader release verification. The user reported a successful single-owner Hugging Face deployment on 2026-10-25; [setup and access limits](HUGGING_FACE.md) describe that bounded adapter. Independent hosted smoke, multi-user identity and rollback rehearsal remain pending.
Passing offline checks does not establish provider entitlement, financial
freshness, model quality or production readiness.

## Reproducible checks

CI installs requirements-dev.txt with constraints.txt on Python 3.11 and 3.12,
runs pip check, a dependency vulnerability audit, the full offline pytest inventory, compileall and app imports.
The constraints preserve the reviewed Python 3.12 baseline and select NumPy's
Python 3.11 compatible 2.3 line. They constrain direct dependencies rather than
locking every transitive dependency. Pytest blocks external socket connections;
synthetic services provide all financial and model evidence.

```sh
python -m pip install -r requirements-dev.txt -c constraints.txt
python -m pip check
PYTHONPATH=src python -m pytest -q
python -m compileall -q app.py src
PYTHONPATH=src python -c 'import app; import langgraphagenticai.main'
docker build -t axiom-runtime:local .
docker build -f Dockerfile.verify -t axiom-verify:local .
docker run --rm --network none axiom-verify:local
docker run --rm -p 7860:7860 axiom-runtime:local
```

Check `http://127.0.0.1:7860/_stcore/health` after startup. Runtime runs as UID
1000 and contains app.py/src, excluding tests and local reports. The derived
verification image inherits that runtime source and separately adds pytest and
synthetic tests. Runtime health and offline AppTest evidence are separate checks.
CI retains JUnit test results, Python/dependency version identifiers and the
runtime image identifier for 14 days. It excludes environment dumps, saved
financial output and credential-bearing logs.

For an enterprise TLS proxy, provide an approved public CA bundle outside the
repository with `docker build --secret id=build_ca,src=/path/to/public-ca.pem ...`
for both images. The optional BuildKit secret is mounted only during pip
installation, preserves certificate verification and is not copied into layers.
Do not use insecure trusted-host flags or include private keys in this bundle.

## Protected preview and paid smoke checks (pending)

1. Select a host supporting Streamlit WebSockets, HTTPS, non-root containers,
   health checks and an access-controlled preview. Record the image digest,
   source commit, dependency versions and preview URL before testing.
2. Inject required keys using the host's secret manager (key names in
   `.env.example`). Never bake keys into images, command arguments, artifacts
   or source. Restrict preview access before injecting provider credentials.
3. Confirm readiness states with keys absent, then verify all nine navigation
   routes and the synthetic discovery → Guided research → saved brief workflow.
   Annual FY research is separate from an independently saved audited TTM report;
   generation time does not establish evidence freshness.
4. If separately authorized, run a bounded paid smoke: one named ticker, one
   prepare action and one run action, at most three tools/two model attempts;
   record supplied prices, usage and ceiling. Unknown-price acknowledgement
   cannot guarantee a dollar cap. Ordinary reruns/downloads must add zero calls.
5. In two independent browser sessions verify saved histories, keys and ticker
   drafts remain isolated. A session is not an authenticated user identity;
   hosted authentication/access control requires its own evidence. Do not
   publish private reports to shared storage without an explicit ownership model.

## Rollback rehearsal (pending)

Keep the previous verified image digest and secret configuration. Switch the
protected preview back to that digest, verify health and all-nine readiness,
and verify a new session's representative workflow. Record the target, both
digests, operator, timings and results. Session-only histories may be lost across
restart; disclose this before any release. No deployment or rollback has been
performed merely by adding this runbook.


## AX-10 local controls and blocked hosted mode (2026-10-24)

`AXIOM_RUNTIME_MODE` defaults to `local` for desktop development (blank also means local). This is a trusted, single-operator research mode, not hosted authentication. Bind local development to loopback. The runtime Dockerfile now defaults to `huggingface_single_owner`, which requires a 24-1024 character `AXIOM_OWNER_PASSWORD` and session sign-in before workspace/credential controls. See [Hugging Face setup](HUGGING_FACE.md). Generic `hosted` mode still denies access. Unknown modes also deny access. There is no UI switch to bypass these access checks. Both the main app and focused advisor launcher apply this gate. The verification image explicitly uses local mode for offline fixtures only; never expose that verification image as a service.

General multi-user hosted identity is not implemented merely by setting environment variables or editing a manifest. The bounded single-owner adapter does not satisfy the broader identity/job gates. A real deployment-specific identity adapter, per-user authorization on every resume/export, credential/cache boundaries, protected network and release evidence must be integrated before this hard block can be removed. Local mode must not be used as an unauthenticated hosting workaround. AX-08 monitoring remains disabled.

`python scripts/release_gate.py` reports the declared gate inventory from `docs/roadmap/production-gates.json`. `--require-ready` exits nonzero while blocked, even if every declaration says passed: the missing hosted adapter is an independent blocker. This inventory is not signed release attestation. Do not change unverified/failed entries based on older tests. The dependency-audit record is `docs/roadmap/dependency-audit-2026-10-24.json`; it describes the installed project environment, not a clean dependency resolution. Findings require reviewed remediation and re-audit. CI adds pip-audit without vulnerability exemptions. Network/certificate errors must fail the audit, not become a clean result.

FMP shared transport now permits only HTTPS FMP destinations without embedded credentials/query/fragment or redirects. Connect/read timeouts cap at 5/30 seconds per attempt. GET retries remain two (three HTTP attempts total); backoff/Retry-After sleeps cap at two seconds. Process-local guards admit at most 300 logical requests/minute and eight in flight per credential, 64 globally; each admitted logical request may perform the bounded retries. Five transient logical failures open a 30-second circuit with one recovery probe. The 4096-entry registry expires idle scopes after an hour and fails closed at capacity. No keys are stored as registry identifiers. These are process/credential limits, not authenticated per-user/distributed quotas; other provider/model routes need their own adoption before hosting.

Telemetry accepts fixed event/category names, UUID lineage, bounded counts/times/cost fields and opaque source hashes. Unknown text, prompts, holdings, credentials, URLs, exception strings/traces and arbitrary metadata are removed before logging handlers. Model families replace full names. ContextVar scopes isolate nested/threaded events. Cost fields distinguish supplied estimates from supplied actuals; absent billing telemetry is not synthesized. Existing FMP transport and chat are instrumented; universal model/stage usage coverage remains open. Chat has a 12-step LangGraph limit. Its graph/repair resources are session-scoped and bounded to two configurations rather than sharing conversation memory across equal-key sessions.

## Encrypted checkpoint service contract (not an active resume workflow)

`security/checkpoints.py` is an explicitly invoked server-side foundation. No app page creates a database, issues a grant, automatically saves a report or resumes paid work. A trusted future identity adapter must first authenticate its subject and then call `issue_for_authenticated_owner`; that method itself does not authenticate anyone. Its short-lived signed bearer grants are server-side capabilities, not browser sign-in tokens. Keep the 32-byte AES-GCM key in a server secret manager, separate from the database and backups. Never expose store/grant APIs directly to user-controlled Python or HTTP handlers without the adapter.

Saved rows encrypt sanitized research/portfolio state with owner/run/revision authenticated as associated data. Owner namespaces use a keyed digest. Read, write, export and delete require separate signed scopes and unexpired grants. Saves use transactional compare-and-swap revisions, preventing silent last-writer wins. Run IDs are UUID hex, never filenames supplied by report titles. Limits: one-megabyte plaintext row, 20 rows/10MB ciphertext per owner, 1000 rows/100MB globally; infrastructure disk/retention limits are still needed. Checkpoints preserve partial/failed/complete status without changing evidence dates or dispatching models. Scope guards are rechecked before return/commit; no refresh or job scheduler is implied.

Use a protected server-owned volume, with POSIX directory/file permissions or explicit Windows ACLs; chmod is not a Windows ACL substitute. Symlinked roots/database paths are rejected, but hostile administrators/filesystem races are outside this local service threat model. SQLite backups require a consistent SQLite backup operation, not a mid-write file copy. Preserve the encryption key separately and verify access with fresh grants after restoration. The offline test rehearses restart, encrypted backup/restore, tampering, owner isolation and simultaneous revisions. It does not certify an operational hosted backup system or rollback. Key rotation requires a separately designed migration retaining old keys until records are re-encrypted; replacing the key alone denies access to old records and grants. Do not rotate by blindly replacing a secret.

For container rehearsals use loopback publishing plus `--read-only`, a bounded `/tmp` tmpfs, `--cap-drop ALL`, `--security-opt no-new-privileges`, CPU/memory/PID limits. CI contains this launch preparation, but local Docker engine unavailability and unexecuted remote CI mean it is not runtime evidence. Current open gates still include clean Python 3.11/3.12 installations, image build/non-root start, real authenticated concurrent sessions, durable hosted jobs, dependency remediation, protected preview/live smoke and hosted backup/rollback. Live financial/provider checks remain separately authorized and bounded.
