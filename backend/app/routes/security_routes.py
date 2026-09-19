"""
Security / authorship endpoints.

These expose the creator identity and the tamper-verification results so that
the frontend can prove - visibly, on the splash screen - that the copy of the
database it is talking to has not been altered outside this application.
"""

from flask import Blueprint, jsonify

from app.models import Medicine
from app.branding import branding_payload, verify_identity
from app.security import verify_all, SEAL_VERSION, SEALED_MEDICINE_FIELDS

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
