"""Evidence identity for explicitly generated company interpretations (D08)."""
import hashlib
import json
from datetime import datetime, timezone


def snapshot_fingerprint(snapshot):
    return hashlib.sha256(json.dumps(snapshot, sort_keys=True, default=str, ensure_ascii=False).encode("utf-8")).hexdigest()


def save_interpretation(snapshot, model, text):
    return {"symbol": snapshot["symbol"], "model": model, "fingerprint": snapshot_fingerprint(snapshot),
            "text": text, "generated_at": datetime.now(timezone.utc).isoformat()}


def interpretation_matches(saved, snapshot, model):
    return isinstance(saved, dict) and saved.get("symbol") == snapshot.get("symbol") and saved.get("model") == model and saved.get("fingerprint") == snapshot_fingerprint(snapshot)
