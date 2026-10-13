"""
Storage / backup endpoints - the "memory" layer for local data.

Everything here operates on files on this machine only. Nothing is uploaded.
"""

import json

from flask import Blueprint, request, jsonify, send_file

from app.services import storage_service
from app.models.audit_log import audit_log
from app.services.import_validator import validate_import_payload

storage_bp = Blueprint('storage', __name__, url_prefix='/api/storage')


@storage_bp.route('/info', methods=['GET'])
def get_info():
    """Where the data lives, how big it is, and how many records there are."""
    return jsonify({'success': True, 'data': storage_service.database_info()})


@storage_bp.route('/snapshots', methods=['GET'])
def list_snapshots():
    return jsonify({'success': True, 'data': storage_service.list_snapshots()})


@storage_bp.route('/snapshots', methods=['POST'])
def create_snapshot():
    """Take a manual snapshot now."""
    try:
        path = storage_service.create_snapshot('manual')
        if not path:
            return jsonify({'success': False, 'error': 'No database to snapshot yet.'}), 400
        return jsonify({
            'success': True,
            'message': 'Snapshot created.',
            'data': {'filename': path.split('\\')[-1].split('/')[-1], 'path': path},
        })
    except Exception as exc:
        return jsonify({'success': False, 'error': 'Could not create snapshot.'}), 400


@storage_bp.route('/snapshots/restore', methods=['POST'])
def restore_snapshot():
    """Roll back to a snapshot. A pre-restore snapshot is taken automatically."""
    try:
        data = request.get_json() or {}
        filename = data.get('filename')
        if not filename:
            return jsonify({'success': False, 'error': 'filename is required'}), 400
        result = storage_service.restore_snapshot(filename)
        status = 200 if result.get('restored') else 400
        if result.get('restored'):
            audit_log('restore_snapshot', 'system', detail='restored from %s' % filename)
        return jsonify({'success': result.get('restored', False), 'data': result}), status
    except Exception as exc:
        return jsonify({'success': False, 'error': 'Could not restore snapshot.'}), 400


@storage_bp.route('/export', methods=['POST'])
def export_data():
    """
    Write a portable JSON export to the backups folder.

    Set ?download=1 to receive the file itself, which is what the UI uses so the
    browser can save it wherever the user chooses.
    """
    try:
        data = request.get_json(silent=True) or {}
        include_medicines = bool(data.get('include_medicines', True))
        path, payload = storage_service.export_to_file(include_medicines=include_medicines)
        audit_log('export_data', 'system', detail='exported %d records' % payload['record_count'])

        if request.args.get('download') == '1':
            return send_file(
                path,
                as_attachment=True,
                download_name=path.split('\\')[-1].split('/')[-1],
                mimetype='application/json',
            )
        return jsonify({
            'success': True,
            'message': f"Exported {payload['record_count']} records.",
            'data': {'path': path, 'record_count': payload['record_count']},
        })
    except Exception as exc:
        return jsonify({'success': False, 'error': 'Could not create export.'}), 400


@storage_bp.route('/import', methods=['POST'])
def import_data():
    """
    Load an export back in.

    Accepts either an uploaded file (multipart) or a JSON body. Pass
    replace_patients=true to wipe existing patients first - destructive.
    """
    try:
        replace = request.args.get('replace_patients', 'false').lower() == 'true'

        if 'file' in request.files:
            uploaded = request.files['file']
            raw = uploaded.read()
            if not raw:
                return jsonify({'success': False, 'error': 'Uploaded file is empty.'}), 400
            payload = json.loads(raw.decode('utf-8'))
        else:
            payload = request.get_json(silent=True)

        if not payload:
            return jsonify({'success': False, 'error': 'No import payload supplied.'}), 400

        # Validate before touching the database.
        ok, errors = validate_import_payload(payload)
        if not ok:
            return jsonify({'success': False, 'error': 'Validation failed',
                            'details': errors[:10]}), 400

        result = storage_service.import_data(payload, replace_patients=replace)
        status = 200 if result.get('imported') else 400
        if result.get('imported'):
            stats = result.get('stats', {})
            total_added = sum(v for v in stats.values() if isinstance(v, int))
            audit_log('import_data', 'system',
                      detail='imported %d rows (replace_patients=%s)' % (total_added, replace))
        return jsonify({'success': result.get('imported', False), 'data': result}), status
    except json.JSONDecodeError:
        return jsonify({'success': False, 'error': 'Import payload is not valid JSON.'}), 400
    except Exception as exc:
        return jsonify({'success': False, 'error': 'Import failed: ' + str(exc)}), 400
