"""
Branding + licensing endpoints.

Branding is gated: a pharmacy name and logo are only applied when a valid
licence key is present, so the shipped product identity cannot be replaced
without a key issued by the vendor.
"""

import os

from flask import Blueprint, request, jsonify, send_file, current_app

from app import db
from app import licensing

branding_bp = Blueprint('branding', __name__, url_prefix='/api/branding')


def _data_dir():
    """Directory holding the database, used for storing uploaded branding."""
    return os.path.dirname(os.path.abspath(db.engine.url.database))


@branding_bp.route('', methods=['GET'])
def get_branding():
    """Current branding, plus whether it is licensed."""
    data = licensing.branding_settings()
    data.update(licensing.licence_status())
    return jsonify({'success': True, 'data': data})


@branding_bp.route('/licence', methods=['POST'])
def activate_licence():
    """Activate a licence key against a pharmacy name."""
    try:
        payload = request.get_json() or {}
        ok, message = licensing.apply_licence(
            payload.get('pharmacy_name'),
            payload.get('licence_key'),
        )
        data = licensing.branding_settings()
        data.update(licensing.licence_status())
        return jsonify({'success': ok, 'message': message, 'error': None if ok else message,
                        'data': data}), (200 if ok else 400)
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400


@branding_bp.route('/licence', methods=['DELETE'])
def deactivate_licence():
    try:
        ok, message = licensing.clear_licence()
        data = licensing.branding_settings()
        data.update(licensing.licence_status())
        return jsonify({'success': ok, 'message': message, 'data': data})
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400


@branding_bp.route('/profile', methods=['PUT'])
def update_profile():
    """
    Save pharmacy contact details for printed prescriptions.

    The pharmacy *name* is part of the licence, so it is not editable here -
    only the surrounding details are.
    """
    try:
        if not licensing.is_licensed():
            return jsonify({
                'success': False,
                'error': 'A licence key is required before editing pharmacy details.',
            }), 403

        payload = request.get_json() or {}
        editable = (
            'pharmacy_address', 'pharmacy_phone', 'pharmacy_email',
            'pharmacy_registration_no', 'pharmacy_gstin', 'pharmacist_name',
            'prescription_footer',
        )
        for field in editable:
            if field in payload:
                licensing.set_setting(field, (payload.get(field) or '').strip())

        db.session.commit()
        data = licensing.branding_settings()
        data.update(licensing.licence_status())
        return jsonify({'success': True, 'message': 'Pharmacy details saved.', 'data': data})
    except Exception as exc:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(exc)}), 400


@branding_bp.route('/logo', methods=['POST'])
def upload_logo():
    """Upload a replacement logo. Requires an active licence."""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file was uploaded.'}), 400

        ok, message, stored = licensing.save_logo(
            request.files['file'], _data_dir()
        )
        data = licensing.branding_settings()
        data.update(licensing.licence_status())
        return jsonify({
            'success': ok,
            'message': message,
            'error': None if ok else message,
            'data': data,
        }), (200 if ok else 400)
    except Exception as exc:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(exc)}), 400


@branding_bp.route('/logo', methods=['GET'])
def get_logo():
    """
    Serve the uploaded logo.

    Falls back to the shipped logo so the UI never shows a broken image.
    """
    path = licensing.logo_path()
    if path:
        return send_file(path, max_age=0)

    shipped = _shipped_logo()
    if shipped:
        return send_file(shipped, max_age=0)
    return jsonify({'success': False, 'error': 'No logo available.'}), 404


@branding_bp.route('/logo', methods=['DELETE'])
def delete_logo():
    try:
        ok, message = licensing.remove_logo()
        return jsonify({'success': ok, 'message': message})
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400


def _shipped_logo():
    """Path to the bundled logo.png, in both frozen and source layouts."""
    import sys

    candidates = []
    if getattr(sys, 'frozen', False):
        base = getattr(sys, '_MEIPASS', None)
        if base:
            candidates.append(os.path.join(base, 'frontend_build', 'logo.png'))
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates.append(os.path.join(
        os.path.dirname(os.path.dirname(here)), 'frontend', 'public', 'logo.png'))
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return None
