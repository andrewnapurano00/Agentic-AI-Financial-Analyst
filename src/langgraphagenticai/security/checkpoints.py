"""Encrypted local service foundation, not a hosted login or background worker.

Only a trusted server-side identity adapter may issue grants after authenticating
its principal. No UI currently creates this store, issues grants or saves reports.
"""
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
import uuid

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from langgraphagenticai.analysis.investment_memo import clean
from langgraphagenticai.utils.logging_utils import log_event


class CheckpointDenied(RuntimeError):
    """Generic failure avoids disclosing another owner's record existence."""


@dataclass(frozen=True, repr=False)
class AccessGrant:
    owner: str
    expires: int
    scopes: tuple[str, ...]
    nonce: str
    signature: str


class CheckpointStore:
    """SQLite CAS/checkpoint storage with signed scoped grants and encrypted rows.

    The 32-byte key is injected by a server secret manager, never a UI parameter.
    Protected filesystem/volume ownership and external disk quotas are required.
    Grants are bearer capabilities: keep them server-side and out of logs.
    """
    def __init__(self, root, key, *, clock=time.time):
        if not isinstance(key, bytes) or len(key) != 32:
            raise ValueError("A server-managed 32-byte checkpoint key is required.")
        root = Path(root).absolute()
        if any(p.is_symlink() for p in (root, *root.parents)):
            raise ValueError("Checkpoint root must not contain symlinks.")
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = root / "checkpoints.sqlite3"
        if self.path.is_symlink():
            raise ValueError("Checkpoint database must not be a symlink.")
        # Pre-create with restrictive permissions (POSIX). Windows requires ACLs
        # on the server-owned directory; chmod is not an ACL substitute.
        fd = os.open(self.path, os.O_CREAT | os.O_WRONLY, 0o600)
        os.close(fd)
        self.clock = clock
        self._cipher = AESGCM(key)
        self._grant_key = hmac.digest(key, b"axiom-grants-v1", "sha256")
        self._owner_key = hmac.digest(key, b"axiom-owners-v1", "sha256")
        with self._db() as db:
            db.execute("CREATE TABLE IF NOT EXISTS checkpoints(owner TEXT, id TEXT, revision INTEGER, nonce BLOB, payload BLOB, size INTEGER, PRIMARY KEY(owner,id))")

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def _signature(self, owner, expires, scopes, nonce):
        raw = json.dumps([owner, expires, scopes, nonce], separators=(",", ":")).encode()
        return hmac.new(self._grant_key, raw, hashlib.sha256).hexdigest()

    def issue_for_authenticated_owner(self, owner, *, scopes=("read", "write", "export", "delete"), ttl=900):
        """Trusted adapter API. This method does not authenticate a caller."""
        if (not isinstance(owner, str) or not re.fullmatch(r"[A-Za-z0-9._:@-]{1,100}", owner)
                or type(ttl) is not int or not 1 <= ttl <= 3600
                or not isinstance(scopes, tuple) or not scopes or len(set(scopes)) != len(scopes)
                or not set(scopes) <= {"read", "write", "export", "delete"}):
            raise ValueError("Invalid owner, grant scopes or lifetime.")
        expires = int(self.clock()) + ttl
        nonce = secrets.token_hex(16)
        return AccessGrant(owner, expires, scopes, nonce, self._signature(owner, expires, scopes, nonce))

    def _authorize(self, grant, scope):
        try:
            valid = (isinstance(grant, AccessGrant) and scope in grant.scopes
                     and type(grant.expires) is int and self.clock() < grant.expires
                     and hmac.compare_digest(grant.signature, self._signature(grant.owner, grant.expires, grant.scopes, grant.nonce)))
            if not valid:
                raise CheckpointDenied("Checkpoint unavailable or access denied.")
            return hmac.new(self._owner_key, grant.owner.encode(), hashlib.sha256).hexdigest()
        except (TypeError, ValueError, AttributeError):
            raise CheckpointDenied("Checkpoint unavailable or access denied.") from None

    @staticmethod
    def _identifier(run_id):
        if not isinstance(run_id, str) or not re.fullmatch(r"[0-9a-f]{32}", run_id):
            raise CheckpointDenied("Checkpoint unavailable or access denied.")

    @staticmethod
    def _aad(owner, run_id, revision):
        return json.dumps(["axiom-checkpoint-v1", owner, run_id, revision], separators=(",", ":")).encode()

    def save(self, grant, payload, *, run_id=None, expected_revision=0, credentials=()):
        owner = self._authorize(grant, "write")
        run_id = uuid.uuid4().hex if run_id is None else run_id
        self._identifier(run_id)
        if (type(expected_revision) is not int or expected_revision < 0 or expected_revision >= 1_000_000
                or not isinstance(payload, dict) or payload.get("kind") not in {"research_report", "portfolio_report"}
                or payload.get("status") not in {"partial", "complete", "failed"}):
            raise ValueError("Invalid checkpoint kind, status or revision.")
        raw = json.dumps(clean(payload, credentials), allow_nan=False, sort_keys=True, ensure_ascii=False).encode()
        if len(raw) > 1_000_000:
            raise ValueError("Checkpoint exceeds the one-megabyte payload limit.")
        revision = expected_revision + 1
        nonce = secrets.token_bytes(12)
        encrypted = self._cipher.encrypt(nonce, raw, self._aad(owner, run_id, revision))
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute("SELECT revision,size FROM checkpoints WHERE owner=? AND id=?", (owner, run_id)).fetchone()
            if (old["revision"] if old else 0) != expected_revision:
                raise CheckpointDenied("Checkpoint changed; reload before saving.")
            totals = db.execute("SELECT count(*),coalesce(sum(size),0) FROM checkpoints WHERE owner=?", (owner,)).fetchone()
            global_totals = db.execute("SELECT count(*),coalesce(sum(size),0) FROM checkpoints").fetchone()
            delta = len(encrypted)-(old["size"] if old else 0)
            if ((not old and (totals[0] >= 20 or global_totals[0] >= 1000))
                    or totals[1]+delta > 10_000_000 or global_totals[1]+delta > 100_000_000):
                raise ValueError("Checkpoint storage quota reached; remove an obsolete checkpoint.")
            self._authorize(grant, "write")
            db.execute("INSERT OR REPLACE INTO checkpoints VALUES(?,?,?,?,?,?)", (owner, run_id, revision, nonce, encrypted, len(encrypted)))
        log_event("checkpoint_save", provider="checkpoint", status="ok", run_id=run_id)
        return run_id, revision

    def _load(self, grant, run_id, scope):
        owner = self._authorize(grant, scope)
        self._identifier(run_id)
        with self._db() as db:
            row = db.execute("SELECT * FROM checkpoints WHERE owner=? AND id=?", (owner, run_id)).fetchone()
        if not row:
            raise CheckpointDenied("Checkpoint unavailable or access denied.")
        try:
            raw = self._cipher.decrypt(row["nonce"], row["payload"], self._aad(owner, run_id, row["revision"]))
            payload = json.loads(raw)
        except (InvalidTag, ValueError, TypeError, UnicodeError):
            raise CheckpointDenied("Checkpoint integrity check failed.") from None
        self._authorize(grant, scope)
        return row["revision"], payload

    def read(self, grant, run_id):
        result = self._load(grant, run_id, "read")
        log_event("checkpoint_read", provider="checkpoint", status="ok", run_id=run_id)
        return result

    def export(self, grant, run_id):
        revision, payload = self._load(grant, run_id, "export")
        log_event("checkpoint_export", provider="checkpoint", status="ok", run_id=run_id)
        return json.dumps({"revision": revision, "saved": payload}, allow_nan=False, sort_keys=True, ensure_ascii=False).encode()

    def delete(self, grant, run_id, *, expected_revision):
        owner = self._authorize(grant, "delete")
        self._identifier(run_id)
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            self._authorize(grant, "delete")
            cursor = db.execute("DELETE FROM checkpoints WHERE owner=? AND id=? AND revision=?", (owner, run_id, expected_revision))
            if cursor.rowcount != 1:
                raise CheckpointDenied("Checkpoint unavailable or changed.")
        log_event("checkpoint_delete", provider="checkpoint", status="ok", run_id=run_id)
