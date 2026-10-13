"""
Storage / backup endpoints - the "memory" layer for local data.

Everything here operates on files on this machine only. Nothing is uploaded.
"""

import json

from flask import Blueprint, request, jsonify, send_file

from app.services import storage_service, backup_service
from app.models.audit_log import audit_log
from app.services.import_validator import validate_import_payload

storage_bp = Blueprint('storage', __name__, url_prefix='/api/storage')


@storage_bp.route('/info', methods=['GET'])
def get_info():
    """Where the data lives, how big it is, and how many records there are."""
    return jsonify({'success': True, 'data': storage_service.database_info()})


@storage_bp.route('/snapshots', methods=['GET'])
def list_snapshots():
    """List available snapshots with enhanced metadata from backup_service."""
    status = backup_service.get_backup_status()
    return jsonify({'success': True, 'data': status})


@storage_bp.route('/snapshots', methods=['POST'])
def create_snapshot():
    """Take a manual snapshot now with integrity tracking."""
    try:
        info = backup_service.create_versioned_snapshot('manual')
        if not info:
            return jsonify({'success': False, 'error': 'No database to snapshot yet.'}), 400
        return jsonify({
            'success': True,
            'message': 'Snapshot created.',
            'data': {
                'filename': info['filename'],
                'path': info['path'],
                'sha256': info.get('sha256'),
                'size_readable': info.get('size_readable'),
                'schema_version': info.get('schema_version'),
            },
        })
    except Exception as exc:
        return jsonify({'success': False, 'error': 'Could not create snapshot.'}), 400


@storage_bp.route('/snapshots/verify', methods=['POST'])
def verify_snapshot():
    """
    Verify a backup's integrity WITHOUT restoring it.
    Safe to run on any backup file, including copies stored elsewhere.
    """
    try:
        data = request.get_json() or {}
        filepath = data.get('filepath') or data.get('filename')
        verbose = bool(data.get('verbose', False))

        if not filepath:
            return jsonify({'success': False, 'error': 'filepath or filename is required'}), 400

        result = backup_service.verify_backup(filepath, verbose=verbose)
        return jsonify({'success': result['valid'], 'data': result})
    except Exception as exc:
        return jsonify({'success': False, 'error': f'Verification failed: {exc}'}), 400


@storage_bp.route('/snapshots/restore', methods=['POST'])
def restore_snapshot():
    """Roll back to a snapshot with full validation and pre-restore safety snapshot."""
    try:
        data = request.get_json() or {}
        filename = data.get('filename')
        validate = data.get('validate', True)
        if not filename:
            return jsonify({'success': False, 'error': 'filename is required'}), 400
        result = backup_service.restore_snapshot(filename, validate=validate)
        status = 200 if result.get('restored') else 400
        if result.get('restored'):
            audit_log('restore_snapshot', 'system', detail='restored from %s' % filename)
        return jsonify({'success': result.get('restored', False), 'data': result}), status
    except Exception as exc:
        return jsonify({'success': False, 'error': 'Could not restore snapshot.'}), 400


@storage_bp.route('/snapshots/prune', methods=['POST'])
def prune_snapshots():
    """Remove old backups based on retention policy."""
    try:
        data = request.get_json() or {}
        max_age_days = data.get('max_age_days')
        max_count = data.get('max_count')
        result = backup_service.prune_backups(max_age_days=max_age_days, max_count=max_count)
        audit_log('prune_backups', 'system', detail=f'removed {result["removed_count"]} backups')
        return jsonify({'success': True, 'data': result})
    except Exception as exc:
        return jsonify({'success': False, 'error': 'Prune failed: ' + str(exc)}), 400


@storage_bp.route('/backup/info', methods=['GET'])
def backup_info():
    """Comprehensive backup status including SHA-256 metadata."""
    return jsonify({'success': True, 'data': backup_service.get_backup_status()})


@storage_bp.route('/recovery/procedures', methods=['GET'])
def recovery_procedures():
    """Return documented recovery procedures for common failure scenarios."""
    return jsonify({
        'success': True,
        'data': {k: v['steps'] for k, v in backup_service.RECOVERY_PROCEDURES.items()},
    })


@storage_bp.route('/migrations', methods=['GET'])
def migration_status():
    """Show current schema version and migration history."""
    try:
        from app import db
        from app.migrations_v2 import (
            get_schema_version, get_migration_history, verify_migration_integrity
        )
        version = get_schema_version(db)
        history = get_migration_history(db)
        integrity_ok, issues = verify_migration_integrity(db)
        return jsonify({
            'success': True,
            'data': {
                'current_version': version,
                'expected_version': '20261013-003',
                'history': history,
                'integrity_ok': integrity_ok,
                'issues': issues,
            },
        })
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 500


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
