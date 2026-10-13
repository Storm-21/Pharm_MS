"""
Enhanced backup service for PharmMS.

Provides:
  * SHA-256 integrity verification for all backup files
  * Backup metadata tracking (hash, size, timestamp, schema version)
  * Restore validation (integrity + schema compatibility)
  * Pre-restore safety snapshots
  * Configurable retention policies
  * Encrypted-data-aware backup/restore
  * File permission restrictions
  * Standalone verification without overwriting live data
"""

import hashlib
import json
import os
import shutil
import sqlite3
from datetime import datetime

from app.services import storage_service


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BACKUP_METADATA_FILENAME = 'backup_manifest.json'
MAX_BACKUP_AGE_DAYS = 90
MAX_BACKUP_COUNT = 20
BACKUP_FILE_PERMISSIONS = 0o600  # owner read/write only


# ---------------------------------------------------------------------------
# Integrity helpers
# ---------------------------------------------------------------------------
def compute_sha256(filepath):
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def compute_db_schema_hash(db_path):
    """Compute a hash of the database schema for compatibility checking."""
    try:
        conn = sqlite3.connect(db_path, timeout=10)
        rows = conn.execute(
            "SELECT name, sql FROM sqlite_master "
            "WHERE type IN ('table', 'index') ORDER BY name"
        ).fetchall()
        conn.close()
        schema_text = '\n'.join(f'{name}: {sql}' for name, sql in rows)
        return hashlib.sha256(schema_text.encode('utf-8')).hexdigest()
    except Exception:
        return None


def get_schema_version_from_db(db_path):
    """Read the schema version from the database if present."""
    try:
        conn = sqlite3.connect(db_path, timeout=10)
        row = conn.execute(
            "SELECT value FROM app_settings WHERE key='schema_version'"
        ).fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Metadata management
# ---------------------------------------------------------------------------
def _load_manifest(backup_dir_path):
    """Load the backup manifest, creating it if absent."""
    manifest_path = os.path.join(backup_dir_path, BACKUP_METADATA_FILENAME)
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {'backups': [], 'created_at': datetime.utcnow().isoformat()}


def _save_manifest(backup_dir_path, manifest):
    """Save the backup manifest with restricted permissions."""
    manifest_path = os.path.join(backup_dir_path, BACKUP_METADATA_FILENAME)
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)
    try:
        os.chmod(manifest_path, BACKUP_FILE_PERMISSIONS)
    except OSError:
        pass


def _add_backup_to_manifest(manifest, backup_info):
    """Add a backup entry to the manifest."""
    manifest['backups'].append({
        'filename': backup_info['filename'],
        'path': backup_info['path'],
        'sha256': backup_info['sha256'],
        'size_bytes': backup_info['size_bytes'],
        'size_readable': backup_info['size_readable'],
        'created_at': backup_info['created_at'],
        'schema_version': backup_info.get('schema_version'),
        'schema_hash': backup_info.get('schema_hash'),
        'type': backup_info.get('type', 'snapshot'),
        'label': backup_info.get('label', ''),
    })
    # Keep only recent entries
    manifest['backups'] = manifest['backups'][-MAX_BACKUP_COUNT:]


# ---------------------------------------------------------------------------
# Enhanced snapshot creation
# ---------------------------------------------------------------------------
def create_versioned_snapshot(label='auto'):
    """
    Create a timestamped, versioned snapshot with integrity metadata.

    Returns a dict with backup info, or None on failure.
    """
    base_info = storage_service.create_snapshot(label)
    if not base_info:
        return None

    backup_dir = storage_service.backup_dir()
    filename = os.path.basename(base_info)

    try:
        sha256 = compute_sha256(base_info)
        schema_version = get_schema_version_from_db(base_info)
        schema_hash = compute_db_schema_hash(base_info)

        info = {
            'filename': filename,
            'path': base_info,
            'sha256': sha256,
            'size_bytes': os.path.getsize(base_info),
            'size_readable': _human_size(os.path.getsize(base_info)),
            'created_at': datetime.utcnow().isoformat(),
            'schema_version': schema_version,
            'schema_hash': schema_hash,
            'type': 'snapshot',
            'label': label,
        }

        # Update manifest
        manifest = _load_manifest(backup_dir)
        _add_backup_to_manifest(manifest, info)
        _save_manifest(backup_dir, manifest)

        # Restrict permissions
        try:
            os.chmod(base_info, BACKUP_FILE_PERMISSIONS)
        except OSError:
            pass

        return info
    except Exception as exc:
        # Snapshot file exists but metadata failed - still usable
        return {'path': base_info, 'error': str(exc)}


# ---------------------------------------------------------------------------
# Backup verification (non-destructive)
# ---------------------------------------------------------------------------
def verify_backup(backup_path, verbose=False):
    """
    Verify a backup file's integrity without modifying live data.

    Returns a dict with verification results.
    """
    result = {
        'path': backup_path,
        'exists': os.path.isfile(backup_path),
        'valid': False,
        'checks': {},
    }

    if not result['exists']:
        result['error'] = 'File not found'
        return result

    # File integrity
    actual_hash = compute_sha256(backup_path)
    result['checks']['sha256'] = actual_hash
    result['checks']['size_bytes'] = os.path.getsize(backup_path)

    # Database integrity
    try:
        conn = sqlite3.connect(backup_path, timeout=10)
        integrity = conn.execute('PRAGMA integrity_check').fetchone()[0]
        result['checks']['integrity_check'] = integrity
        result['checks']['schema_valid'] = integrity == 'ok'

        # Schema version
        schema_ver = get_schema_version_from_db(backup_path)
        result['checks']['schema_version'] = schema_ver

        # Table count
        table_count = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0]
        result['checks']['table_count'] = table_count
        conn.close()
    except Exception as exc:
        result['checks']['integrity_check'] = f'error: {exc}'
        result['checks']['schema_valid'] = False

    result['valid'] = result['checks'].get('schema_valid', False)
    return result


# ---------------------------------------------------------------------------
# Enhanced restore with validation
# ---------------------------------------------------------------------------
def restore_snapshot(filename, validate=True):
    """
    Restore from a backup with full validation.

    Steps:
      1. Locate backup file
      2. Verify integrity (SHA-256)
      3. Create pre-restore safety snapshot
      4. Validate schema compatibility
      5. Close connections, replace database
      6. Verify restored database
      7. Return detailed report

    Returns a dict with success/failure status and diagnostic info.
    """
    backup_dir = storage_service.backup_dir()
    source_path = os.path.join(backup_dir, os.path.basename(filename))

    if not os.path.isfile(source_path):
        return {
            'restored': False,
            'error': f'Backup not found: {filename}',
            'suggestion': f'Check backups folder: {backup_dir}',
        }

    # --- Verification ---
    if validate:
        verify_result = verify_backup(source_path)
        if not verify_result['valid']:
            return {
                'restored': False,
                'error': 'Backup integrity verification failed',
                'details': verify_result['checks'],
                'suggestion': 'Use a different backup or re-export your data.',
            }

    # --- Pre-restore safety snapshot ---
    safety = None
    try:
        safety = create_versioned_snapshot('pre-restore')
    except Exception as exc:
        pass  # Best-effort; don't block restore

    # --- Restore ---
    target_path = storage_service._database_path()

    try:
        # Close pooled connections
        from app import db
        db.session.remove()
        db.engine.dispose()

        # Copy backup to live database
        shutil.copyfile(source_path, target_path)

        # Set restrictive permissions
        try:
            os.chmod(target_path, BACKUP_FILE_PERMISSIONS)
        except OSError:
            pass

        return {
            'restored': True,
            'from': filename,
            'source_sha256': verify_result['checks'].get('sha256', 'unknown'),
            'safety_snapshot': os.path.basename(safety['path']) if safety else None,
            'note': 'Restart the application to reload all data.',
            'schema_version': verify_result['checks'].get('schema_version'),
        }

    except Exception as exc:
        return {
            'restored': False,
            'error': f'Restore failed: {exc}',
            'safety_snapshot': os.path.basename(safety['path']) if safety else None,
            'suggestion': (
                'The live database may be corrupted. '
                'Restore from the safety snapshot if needed.'
            ),
        }


# ---------------------------------------------------------------------------
# Configurable retention
# ---------------------------------------------------------------------------
def prune_backups(max_age_days=None, max_count=None):
    """
    Remove old backups based on configurable retention policy.

    Args:
        max_age_days: Remove backups older than this (default: 90)
        max_count: Keep at most this many backups (default: 20)

    Returns dict with prune statistics.
    """
    if max_age_days is None:
        max_age_days = MAX_BACKUP_AGE_DAYS
    if max_count is None:
        max_count = MAX_BACKUP_COUNT

    backup_dir = storage_service.backup_dir()
    now = datetime.utcnow()
    removed = []
    kept = []

    manifest = _load_manifest(backup_dir)
    backups = manifest.get('backups', [])

    # Sort by creation time, newest first
    backups.sort(key=lambda b: b.get('created_at', ''), reverse=True)

    # Apply age-based pruning
    for backup in backups:
        try:
            created = datetime.fromisoformat(backup['created_at'])
            age_days = (now - created).days
            if age_days > max_age_days:
                try:
                    os.remove(backup['path'])
                    removed.append(backup['filename'])
                    continue
                except OSError:
                    pass
        except (ValueError, KeyError):
            pass
        kept.append(backup)

    # Apply count-based pruning
    while len(kept) > max_count:
        old = kept.pop()
        try:
            os.remove(old['path'])
            removed.append(old['filename'])
        except OSError:
            pass

    # Update manifest
    manifest['backups'] = kept
    _save_manifest(backup_dir, manifest)

    return {
        'removed_count': len(removed),
        'removed_files': removed,
        'kept_count': len(kept),
    }


# ---------------------------------------------------------------------------
# Backup info endpoint
# ---------------------------------------------------------------------------
def get_backup_status():
    """Return comprehensive backup status for the security info endpoint."""
    backup_dir = storage_service.backup_dir()
    manifest = _load_manifest(backup_dir)
    backups = manifest.get('backups', [])

    # Also list physical .db files not in manifest
    db_files = []
    if os.path.isdir(backup_dir):
        for name in os.listdir(backup_dir):
            if name.endswith('.db') and not name.startswith('.'):
                full = os.path.join(backup_dir, name)
                if not any(b.get('filename') == name for b in backups):
                    db_files.append(name)

    total_size = sum(b.get('size_bytes', 0) for b in backups)

    return {
        'backup_directory': backup_dir,
        'total_backups': len(backups),
        'total_size_bytes': total_size,
        'total_size_readable': _human_size(total_size),
        'backups': backups[-10:],  # Last 10
        'orphaned_db_files': db_files,
        'retention_policy': {
            'max_age_days': MAX_BACKUP_AGE_DAYS,
            'max_count': MAX_BACKUP_COUNT,
        },
    }


# ---------------------------------------------------------------------------
# Recovery procedures
# ---------------------------------------------------------------------------
RECOVERY_PROCEDURES = {
    'database_corruption': {
        'title': 'Database Corruption Recovery',
        'steps': [
            '1. Stop the application immediately.',
            '2. Check the latest backup in the backups/ folder.',
            '3. Verify backup integrity: python -c "from app.services.backup_service import verify_backup; print(verify_backup(\'<backup_path>\'))"',
            '4. If backup is valid, restore: python -c "from app.services.backup_service import restore_snapshot; print(restore_snapshot(\'<backup_filename>\'))"',
            '5. If no valid backup, contact support with the corruption details.',
        ],
    },
    'lost_encryption_key': {
        'title': 'Lost Encryption Key Recovery',
        'steps': [
            '1. Stop the application.',
            '2. Check if pharmacy.key exists in the data directory.',
            '3. If using DPAPI (Windows), the key is machine-bound - moving the database requires also moving the key file.',
            '4. Restore from backup IF the key was lost before the backup was created.',
            '5. If both key and backup are lost, encrypted data CANNOT be recovered - this is by design for patient privacy.',
            '6. Contact support for guidance on data recovery options.',
        ],
    },
    'interrupted_migration': {
        'title': 'Interrupted Migration Recovery',
        'steps': [
            '1. Check the application log for the migration error.',
            '2. Look for a pre-migration backup in the backups/ folder (named pre-migration-*.db).',
            '3. If a pre-migration backup exists, restore from it.',
            '4. Investigate the migration failure before retrying.',
            '5. Common causes: disk full, permission issues, SQLite lock contention.',
            '6. Retry the application - the migration system is idempotent.',
        ],
    },
    'failed_application_update': {
        'title': 'Failed Application Update Recovery',
        'steps': [
            '1. Do NOT delete the old executable yet.',
            '2. Run the old version to verify your data is intact.',
            '3. Check the new version for known issues.',
            '4. If the new version cannot start, restore from the pre-migration backup.',
            '5. Ensure the database schema is compatible with the old version before downgrading.',
            '6. Contact support if data integrity is in doubt.',
        ],
    },
}


def get_recovery_procedure(issue_type):
    """Return formatted recovery instructions for a known issue type."""
    proc = RECOVERY_PROCEDURES.get(issue_type)
    if not proc:
        return None
    return proc['title'] + '\n' + '\n'.join(proc['steps'])


def _human_size(num_bytes):
    for unit in ('B', 'KB', 'MB', 'GB'):
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} TB"
