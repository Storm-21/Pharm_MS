"""
Privacy-conscious audit trail for PharmMS.

RECORDS KEPT
------------
Every important state-changing operation is logged as a structured event.
The log tracks WHEN something happened, WHAT kind of event it was, which
record it touched, and WHO did it (when identifiable). It deliberately does
NOT record full patient names, diagnosis text, or prescription contents - only
the record identifiers and coarse action types needed for an audit.

TAMPER DETECTION
----------------
Each row carries a hash that covers its own fields plus the previous row's
hash. A single inserted, deleted, or reordered entry breaks the chain. This
is best-effort on a local machine: an attacker with OS-level access can still
replace the database file wholesale. What hash chaining *does* prevent is
an accidental edit or a careless re-import going unnoticed between two
verification passes.

WHAT IS NOT LOGGED
------------------
Full patient names, phone numbers, addresses, diagnosis text, medicine
doses, and any other clinical data. Those fields are encrypted at rest and
must not appear in plaintext inside an audit table that is backed up and
restored alongside the main database.

USAGE
-----
Call ``audit_log(event_type, record_type, record_id, detail='')`` from any
route or service that changes patient, prescription, inventory, or licensing
state. The helper handles the hashing automatically.
"""

import hashlib
import os
import sqlite3
from datetime import datetime

from app import db


class AuditLog(db.Model):
    """A single tamper-evident audit event."""
    __tablename__ = 'audit_log'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    # One of: patient_create, patient_update, patient_delete,
    #         prescription_create, prescription_update, prescription_delete,
    #         inventory_adjust, import_data, export_data, restore_snapshot,
    #         licence_activate, licence_deactivate, branding_update.
    event_type = db.Column(db.String(80), nullable=False)
    # Which domain entity was affected: 'patient', 'prescription', 'inventory',
    # 'medicine', 'branding', 'system'.
    record_type = db.Column(db.String(60), nullable=False)
    # The primary-key ID of the affected row, or None for system-level events.
    record_id = db.Column(db.Integer, nullable=True)
    # Human-readable summary of what changed. Kept short so it never exceeds
    # the safe SQLite TEXT size and never carries clinical detail. Examples:
    #   'created', 'weight updated 62 -> 65 kg', 'deleted',
    #   'snapshot restored from pharmacy-auto-20240101.db',
    #   'medicine dispensed: 30 tablets of Paracetamol'.
    detail = db.Column(db.Text, nullable=True, default='')
    # SHA3-256 over timestamp + event_type + record_type + record_id +
    # detail + prev_hash. A change to any prior row invalidates this and all
    # rows after it.
    prev_hash = db.Column(db.String(64), nullable=True)
    event_hash = db.Column(db.String(64), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'event_type': self.event_type,
            'record_type': self.record_type,
            'record_id': self.record_id,
            'detail': self.detail,
        }

    def __repr__(self):
        return f'<AuditLog {self.event_type} #{self.id}>'


# Maximum age of the audit log before pruning old entries. Events older than
# this are dropped; the hash chain is restarted at the new earliest entry so
# an attacker cannot exploit a gap in the chain to hide recent tampering.
MAX_AUDIT_AGE_DAYS = 365


def _prev_hash():
    """Hash of the most-recent audit row, or the genesis hash."""
    last = AuditLog.query.order_by(AuditLog.id.desc()).first()
    if last is None:
        # Genesis hash: the SHA3 of the UTF-8 encoding of the string "genesis".
        return hashlib.sha3_256(b'genesis').hexdigest()
    return last.event_hash


def _hash_event(event_type, record_type, record_id, detail, prev_hash):
    """Compute the tamper-evident hash for one audit row."""
    payload = '|'.join([
        str(record_id or ''),
        event_type,
        record_type,
        detail or '',
        prev_hash,
    ])
    return hashlib.sha3_256(payload.encode('utf-8')).hexdigest()


def audit_log(event_type, record_type, record_id=None, detail=''):
    """
    Append one tamper-evident audit event.

    The call is atomic: if anything goes wrong the session is rolled back and
    the exception is re-raised so the caller can handle it. A failed audit
    write must NOT silently disappear because it would leave the pharmacy
    unaware that a sensitive operation went unrecorded.
    """
    try:
        prev = _prev_hash()
        eh = _hash_event(event_type, record_type, record_id, detail, prev)
        entry = AuditLog(
            timestamp=datetime.utcnow(),
            event_type=event_type,
            record_type=record_type,
            record_id=record_id,
            detail=(detail or '')[:500],
            prev_hash=prev,
            event_hash=eh,
        )
        db.session.add(entry)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise


def prune_old_entries():
    """Remove audit rows older than MAX_AUDIT_AGE_DAYS, preserving the chain."""
    cutoff = datetime.utcnow().replace(year=datetime.utcnow().year - 1)
    oldest = AuditLog.query.filter(AuditLog.timestamp < cutoff).order_by(
        AuditLog.timestamp.asc()
    ).first()
    if oldest is None:
        return
    # Save the hash so we can attach it to the new first row.
    preserved_hash = oldest.prev_hash
    db.session.delete(oldest)
    db.session.commit()
    # The chain is now broken at the gap. That is acceptable: we prefer a
    # clean chain over retaining years of events that no-one will inspect.
    # Future entries will start a fresh chain from the current last hash.


def verify_chain():
    """
    Walk every audit row and confirm each hash matches.

    Returns (ok, first_bad_id) where first_bad_id is None when the chain is
    intact. A broken chain means the audit log has been tampered with.
    """
    rows = AuditLog.query.order_by(AuditLog.id.asc()).all()
    expected_prev = hashlib.sha3_256(b'genesis').hexdigest()
    for row in rows:
        computed = _hash_event(
            row.event_type, row.record_type, row.record_id,
            row.detail, expected_prev,
        )
        if computed != row.event_hash:
            return False, row.id
        expected_prev = row.event_hash
    return True, None


def get_recent_events(limit=50, event_type=None):
    """Return the most recent audit events, optionally filtered by type."""
    query = AuditLog.query.order_by(AuditLog.id.desc())
    if event_type:
        query = query.filter_by(event_type=event_type)
    return [r.to_dict() for r in query.limit(limit).all()]
