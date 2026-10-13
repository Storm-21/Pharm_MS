"""
Security / authorship endpoints.

These expose the creator identity, the tamper-verification results, and the
current encryption/key state so the frontend can display a visible status
indicator rather than leaving it opaque.
"""

import os
import sys

from flask import Blueprint, jsonify, request

from app.models import Medicine
from app.branding import branding_payload, verify_identity
from app.security import verify_all, SEAL_VERSION, SEALED_MEDICINE_FIELDS
from app.crypto import key_path, _dpapi_key_path
from app.models.audit_log import get_recent_events, verify_chain

security_bp = Blueprint('security', __name__, url_prefix='/api/security')


@security_bp.route('/branding', methods=['GET'])
def get_branding():
    """Creator attribution + app identity, with integrity status."""
    return jsonify({'success': True, 'data': branding_payload()})


@security_bp.route('/verify', methods=['GET'])
def verify_database():
    """Re-hash every authored medicine and report anything that was altered."""
    medicines = Medicine.query.all()
    report = verify_all(medicines)
    identity_ok, _ = verify_identity()

    report['identity_ok'] = identity_ok
    report['seal_version'] = SEAL_VERSION
    report['sealed_field_count'] = len(SEALED_MEDICINE_FIELDS)

    return jsonify({'success': True, 'data': report}), (200 if report['ok'] else 409)


@security_bp.route('/info', methods=['GET'])
def get_security_info():
    """
    Summary of the security posture without exposing secrets.

    Reports whether encryption is active, whether the key file exists and
    appears valid, and whether any DPAPI wrapping is present. The raw key is
    never returned.
    """
    key_exists = os.path.exists(key_path())
    dpapi_exists = os.path.exists(_dpapi_key_path())
    key_valid = False
    if key_exists:
        try:
            with open(key_path(), 'rb') as handle:
                raw = handle.read().strip()
            key_valid = len(raw) == 44
        except OSError:
            pass
    chain_ok, bad_id = verify_chain()

    return jsonify({
        'success': True,
        'data': {
            'encryption_active': key_exists or dpapi_exists,
            'key_file_exists': key_exists,
            'dpapi_wrapped': dpapi_exists,
            'key_valid': key_valid,
            'audit_log_chain_ok': chain_ok,
            'first_bad_audit_id': bad_id,
            'audit_event_count': __import__('app.models.audit_log', fromlist=['AuditLog']).AuditLog.query.count(),
        }
    })


@security_bp.route('/audit', methods=['GET'])
def get_audit():
    """
    Recent audit events.

    Pagination is optional; defaults to the last 50 entries.
    ?limit=N&offset=M&event_type=patient_update
    """
    limit = min(int(request.args.get('limit', 50)), 200)
    offset = max(int(request.args.get('offset', 0)), 0)
    event_type = request.args.get('event_type')

    from app.models.audit_log import get_recent_events
    events = get_recent_events(limit=limit + offset, event_type=event_type)
    # Return only the slice the caller asked for (offset + limit).
    return jsonify({
        'success': True,
        'data': events[offset:],
        'total': len(events),
    })
