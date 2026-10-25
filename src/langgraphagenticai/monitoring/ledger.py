"""Durable OFFLINE rehearsal ledger. No scheduler, authentication adapter or execution."""
from contextlib import contextmanager
from datetime import timedelta
import hashlib
import json
import secrets
import sqlite3
from .models import ModelSnapshot, PriceEvent, encoded, concentration_advisory, utc_stamp


class RehearsalLedger:
    """Owner is a test/rehearsal namespace, never a claimed authenticated principal."""
    def __init__(self,path):
        self.path=str(path)
        with self._db() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS plans(owner TEXT, id TEXT, model TEXT, scope TEXT, expires TEXT,
              enabled INTEGER NOT NULL DEFAULT 0, budget INTEGER, PRIMARY KEY(owner,id));
            CREATE TABLE IF NOT EXISTS jobs(owner TEXT, plan TEXT, event TEXT, hash TEXT, payload TEXT,
              status TEXT, attempts INTEGER DEFAULT 0, token TEXT, lease TEXT, error TEXT,
              PRIMARY KEY(owner,plan,event));
            CREATE TABLE IF NOT EXISTS advisories(owner TEXT, plan TEXT, event TEXT, payload TEXT,
              decision TEXT DEFAULT 'pending', PRIMARY KEY(owner,plan,event));
            ''')

    @contextmanager
    def _db(self):
        db=sqlite3.connect(self.path,timeout=5)
        db.row_factory=sqlite3.Row
        try:
            with db: yield db
        finally: db.close()

    def register(self,owner,model,scope,expires,*,max_events=20):
        model=ModelSnapshot.model_validate(model.model_dump())
        fields=model.model_dump(exclude={"schema_version","fingerprint"})
        if hashlib.sha256(encoded(fields).encode()).hexdigest()!=model.fingerprint:
            raise ValueError("Saved model fingerprint mismatch.")
        if (not owner or len(owner)>100 or not 1<=max_events<=100 or len(scope)!=64
                or any(c not in "0123456789abcdef" for c in scope)):
            raise ValueError("Invalid offline owner/scope/event budget.")
        utc_stamp(expires)
        weights=[p.weight for p in model.positions]
        sectors={}
        for p in model.positions: sectors[p.sector]=sectors.get(p.sector,0)+p.weight
        if (not weights or len({p.ticker for p in model.positions})!=len(weights)
                or abs(sum(weights)+model.cash-1)>1e-9 or model.cash<model.minimum_cash-1e-9
                or max(weights)>model.position_cap+1e-9 or max(sectors.values())>model.sector_cap+1e-9):
            raise ValueError("Saved allocation does not reconcile to constraints.")
        payload=model.model_dump_json()
        with self._db() as db:
            old=db.execute('SELECT * FROM plans WHERE owner=? AND id=?',(owner,model.fingerprint)).fetchone()
            if old and (old['model'],old['scope'],old['expires'],old['budget'])!=(payload,scope,expires,max_events):
                raise ValueError("Immutable offline plan already exists with different settings.")
            db.execute('INSERT OR IGNORE INTO plans(owner,id,model,scope,expires,budget) VALUES(?,?,?,?,?,?)',
                       (owner,model.fingerprint,payload,scope,expires,max_events))
        return model.fingerprint

    def set_rehearsal_enabled(self,owner,plan,enabled):
        """Only enables this explicitly invoked offline queue, not app monitoring."""
        with self._db() as db:
            cursor=db.execute('UPDATE plans SET enabled=? WHERE owner=? AND id=?',(int(bool(enabled)),owner,plan))
            if cursor.rowcount!=1: raise ValueError("Offline plan unavailable in this owner namespace.")
            if not enabled:
                db.execute("UPDATE jobs SET status='cancelled',token=NULL WHERE owner=? AND plan=? AND status IN ('queued','running')",(owner,plan))

    def submit(self,owner,plan,event,reference):
        event=PriceEvent.model_validate(event.model_dump())
        payload=event.model_dump_json()
        digest=hashlib.sha256(encoded(event.model_dump()).encode()).hexdigest()
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            p=db.execute('SELECT * FROM plans WHERE owner=? AND id=?',(owner,plan)).fetchone()
            if not p: raise ValueError("Offline plan unavailable in this owner namespace.")
            old=db.execute('SELECT * FROM jobs WHERE owner=? AND plan=? AND event=?',(owner,plan,event.event_id)).fetchone()
            if old:
                if old['hash']!=digest: raise ValueError("Event ID collision: changed evidence cannot replace a saved event.")
                return old['status']
            if not p['enabled']: return 'disabled'
            if utc_stamp(p['expires'])<utc_stamp(reference) or event.credential_scope!=p['scope']: return 'credential_expired_or_changed'
            count=db.execute('SELECT count(*) FROM jobs WHERE owner=? AND plan=?',(owner,plan)).fetchone()[0]
            if count>=p['budget']: return 'budget_exhausted'
            db.execute("INSERT INTO jobs(owner,plan,event,hash,payload,status) VALUES(?,?,?,?,?,'queued')",(owner,plan,event.event_id,digest,payload))
        return 'queued'

    def claim(self,owner,reference):
        clock=utc_stamp(reference)
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            rows=db.execute("SELECT * FROM jobs WHERE owner=? AND status IN ('queued','running') ORDER BY rowid",(owner,)).fetchall()
            for job in rows:
                p=db.execute('SELECT * FROM plans WHERE owner=? AND id=?',(owner,job['plan'])).fetchone()
                if not p['enabled'] or utc_stamp(p['expires'])<clock:
                    db.execute("UPDATE jobs SET status='cancelled',token=NULL WHERE owner=? AND plan=? AND event=?",(owner,job['plan'],job['event']))
                    continue
                if job['status']=='running' and utc_stamp(job['lease'])>clock: continue
                if job['attempts']>=3:
                    db.execute("UPDATE jobs SET status='dead_letter',token=NULL WHERE owner=? AND plan=? AND event=?",(owner,job['plan'],job['event']))
                    continue
                token=secrets.token_hex(24)
                db.execute("UPDATE jobs SET status='running',attempts=attempts+1,token=?,lease=? WHERE owner=? AND plan=? AND event=?",
                    (token,(clock+timedelta(seconds=60)).isoformat(),owner,job['plan'],job['event']))
                return {'owner':owner,'plan':job['plan'],'event':job['event'],'token':token,
                        'model':ModelSnapshot.model_validate_json(p['model']),'evidence':PriceEvent.model_validate_json(job['payload'])}
        return None

    def finish(self,claim,reference,*,transient_failure=False):
        """Lease/disable/expiry checked again atomically before committing one advisory."""
        failure=None
        owner,plan,event=claim['owner'],claim['plan'],claim['event']
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM jobs WHERE owner=? AND plan=? AND event=?',(owner,plan,event)).fetchone()
            p=db.execute('SELECT * FROM plans WHERE owner=? AND id=?',(owner,plan)).fetchone()
            if not row or row['status']!='running' or row['token']!=claim['token']: return 'lease_lost'
            if not p['enabled'] or utc_stamp(p['expires'])<utc_stamp(reference):
                status='cancelled'
            elif utc_stamp(row['lease'])<utc_stamp(reference): return 'lease_lost'
            elif transient_failure:
                status='dead_letter' if row['attempts']>=3 else 'queued'
                failure='transient_rehearsal_failure'
            else:
                # Load canonical stored evidence, never a caller-mutated lease payload.
                try:
                    finding=concentration_advisory(ModelSnapshot.model_validate_json(p['model']),PriceEvent.model_validate_json(row['payload']),reference)
                    status='done'
                    if finding:
                        db.execute('INSERT OR IGNORE INTO advisories(owner,plan,event,payload) VALUES(?,?,?,?)',(owner,plan,event,encoded(finding)))
                except (ValueError,TypeError,KeyError,OverflowError):
                    failure='evidence_unavailable_or_incompatible'
                    status='blocked'
            db.execute('UPDATE jobs SET status=?,error=?,token=NULL WHERE owner=? AND plan=? AND event=?',(status,failure,owner,plan,event))
        return status

    def process_next(self,owner,reference):
        claim=self.claim(owner,reference)
        return self.finish(claim,reference) if claim else 'idle'

    def advisories(self,owner,plan):
        with self._db() as db:
            rows=db.execute('SELECT event,payload,decision FROM advisories WHERE owner=? AND plan=? ORDER BY rowid',(owner,plan)).fetchall()
        return [{'event':r['event'],'advisory':json.loads(r['payload']),'decision':r['decision']} for r in rows]

    def decide(self,owner,plan,event,decision):
        if decision not in {'approved','rejected'}: raise ValueError("Explicit advisory approval or rejection is required.")
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT decision FROM advisories WHERE owner=? AND plan=? AND event=?',(owner,plan,event)).fetchone()
            if not row: raise ValueError("Advisory unavailable in this owner namespace.")
            if row['decision'] not in {'pending',decision}: raise ValueError("Decision is already recorded; it cannot be silently replaced.")
            db.execute('UPDATE advisories SET decision=? WHERE owner=? AND plan=? AND event=?',(decision,owner,plan,event))
        return 'advisory_only_no_portfolio_change'
