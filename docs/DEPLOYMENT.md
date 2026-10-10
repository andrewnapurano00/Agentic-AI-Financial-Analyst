# Deployment rehearsal runbook

P05 local automation is preparation for a protected preview. The hosting target,
preview identity, hosted smoke checks and rollback rehearsal remain pending.
Passing offline checks does not establish provider entitlement, financial
freshness, model quality or production readiness.

## Reproducible checks

CI installs requirements-dev.txt with constraints.txt on Python 3.11 and 3.12,
runs pip check, the full offline pytest inventory, compileall and app imports.
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
3. Confirm readiness states with keys absent, then verify all eight navigation
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
protected preview back to that digest, verify health and all-eight readiness,
and verify a new session's representative workflow. Record the target, both
digests, operator, timings and results. Session-only histories may be lost across
restart; disclose this before any release. No deployment or rollback has been
performed merely by adding this runbook.
