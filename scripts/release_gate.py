"""Report declared release evidence; never activate hosted runtime or deploy."""
import argparse
import json
from pathlib import Path

GATES = ("offline_tests", "dependency_audit", "clean_python_311", "clean_python_312",
         "container_build", "non_root_runtime", "remote_ci", "authenticated_identity",
         "cross_user_isolation", "durable_jobs", "protected_preview", "hosted_smoke",
         "backup_restore", "rollback")


def report(manifest):
    if not isinstance(manifest, dict) or set(manifest) != set(GATES):
        raise ValueError("Release manifest must contain exactly the required gate IDs.")
    if any(v not in {"unverified", "partial", "failed", "passed"} for v in manifest.values()):
        raise ValueError("Invalid release gate status.")
    return {"schema_version": "axiom-release-gates-v1", "declared_gates": manifest,
            "evidence_is_declaration_not_attestation": True,
            "hosted_identity_adapter_available": False,
            "production_ready": False,
            "blocking_gates": [k for k in GATES if manifest[k] != "passed"] + ["hosted_identity_adapter"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path(__file__).resolve().parents[1]/"docs/roadmap/production-gates.json")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-ready", action="store_true")
    args = parser.parse_args()
    result = report(json.loads(args.manifest.read_text(encoding="utf-8")))
    text = json.dumps(result, sort_keys=True, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text)
    if args.require_ready and not result["production_ready"]:
        raise SystemExit(1)
