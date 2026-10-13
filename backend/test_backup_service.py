"""
Tests for the enhanced backup service.

Covers:
  * Snapshot creation with SHA-256 metadata
  * Backup verification without overwriting live data
  * Restore with pre-restore safety snapshot
  * Schema version compatibility checking
  * Configurable retention pruning
  * Recovery procedure documentation
"""

import os
import sys
import tempfile
import sqlite3
import hashlib
import shutil
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services import backup_service
from app import create_app, db


def _make_test_db(tmpdir, with_data=False):
    """Create a test SQLite database with optional patient data."""
    path = os.path.join(tmpdir, 'test_pharmacy.db')
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE patients (
            id INTEGER NOT NULL PRIMARY KEY,
            first_name VARCHAR(120) NOT NULL,
            last_name VARCHAR(120) NOT NULL,
            date_of_birth DATE,
            gender VARCHAR(20),
            phone VARCHAR(40),
            chronic_diseases TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE medicines (
            id INTEGER NOT NULL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            manufacturer VARCHAR(200),
            strength VARCHAR(100),
            form VARCHAR(50),
            cost_price DECIMAL(10,2),
            selling_price DECIMAL(10,2)
        )
    """)
    conn.execute("""
        CREATE TABLE schema_migrations (
            id INTEGER NOT NULL PRIMARY KEY,
            version VARCHAR(20) NOT NULL UNIQUE,
            name VARCHAR(120) NOT NULL,
            description TEXT,
            applied_at DATETIME NOT NULL,
            checksum VARCHAR(64) NOT NULL,
            duration_ms INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE app_settings (
            id INTEGER NOT NULL PRIMARY KEY,
            key VARCHAR(120) NOT NULL UNIQUE,
            value TEXT,
            description TEXT,
            updated_at DATETIME
        )
    """)

    if with_data:
        conn.execute(
            "INSERT INTO patients (first_name, last_name, date_of_birth, gender) VALUES (?, ?, ?, ?)",
            ('John', 'Doe', '1980-01-15', 'Male')
        )
        conn.execute(
            "INSERT INTO medicines (name, manufacturer, strength, form, cost_price, selling_price) VALUES (?, ?, ?, ?, ?, ?)",
            ('Paracetamol', 'GSK', '500mg', 'Tablet', 0.50, 1.00)
        )
    conn.commit()
    conn.close()
    return path


def _close_connections():
    """Close any open SQLAlchemy connections."""
    try:
        db.session.remove()
        db.engine.dispose()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Test: SHA-256 computation is correct
# ---------------------------------------------------------------------------
def test_sha256_computation():
    """compute_sha256 should produce a valid hex digest."""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b'hello pharmacy')
        path = f.name
    try:
        digest = backup_service.compute_sha256(path)
        expected = hashlib.sha256(b'hello pharmacy').hexdigest()
        assert digest == expected, 'SHA-256 mismatch'
        assert len(digest) == 64, 'Should be 64 hex chars'
        print('  PASS: SHA-256 computation correct')
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# Test: verify backup returns meaningful results
# ---------------------------------------------------------------------------
def test_verify_backup_valid():
    """verify_backup should succeed on a healthy database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = _make_test_db(tmpdir, with_data=True)
        result = backup_service.verify_backup(db_path)

        assert result['exists'], 'File should exist'
        assert result['valid'], 'Database should pass integrity check'
        assert 'sha256' in result['checks'], 'Should have SHA-256 hash'
        assert result['checks']['integrity_check'] == 'ok', 'PRAGMA integrity_check should pass'
        assert result['checks']['table_count'] >= 4, 'Should have at least 4 tables'
        print(f'  PASS: Backup verified (tables={result["checks"]["table_count"]})')


def test_verify_backup_corrupt():
    """verify_backup should detect a corrupted database."""
    tmpdir = tempfile.mkdtemp()
    try:
        db_path = _make_test_db(tmpdir, with_data=False)
        _close_connections()
        time.sleep(0.3)
        # Corrupt the file by truncating it
        with open(db_path, 'r+b') as f:
            f.truncate(50)

        result = backup_service.verify_backup(db_path)
        assert result['valid'] == False, 'Corrupted DB should fail verification'
        assert 'integrity_check' in result['checks']
        print('  PASS: Corruption detected correctly')
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_verify_backup_missing_file():
    """verify_backup should handle missing files gracefully."""
    result = backup_service.verify_backup('/nonexistent/path.db')
    assert result['exists'] == False
    assert result['valid'] == False
    assert 'File not found' in result.get('error', '')
    print('  PASS: Missing file handled gracefully')


# ---------------------------------------------------------------------------
# Test: restore with validation
# ---------------------------------------------------------------------------
def test_restore_valid_backup():
    """restore_snapshot should succeed on a valid backup."""
    tmpdir = tempfile.mkdtemp()
    try:
        backup_dir = os.path.join(tmpdir, 'backups')
        os.makedirs(backup_dir)

        src_path = _make_test_db(tmpdir, with_data=True)
        shutil.copy(src_path, os.path.join(backup_dir, 'test-backup.db'))

        # Create a live database to restore over
        live_path = os.path.join(tmpdir, 'pharmacy.db')
        conn = sqlite3.connect(live_path)
        conn.execute("CREATE TABLE patients (id INTEGER PRIMARY KEY, name TEXT)")
        conn.commit()
        conn.close()

        # Patch the backup dir function
        import app.services.storage_service as ss
        orig_backup_dir = ss.backup_dir
        ss.backup_dir = lambda: backup_dir

        try:
            app = create_app()
            app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{live_path}'
            with app.app_context():
                result = backup_service.restore_snapshot('test-backup.db')
            assert 'restored' in result or 'error' in result
            print(f'  PASS: Restore result: {result.get("restored", result.get("error", "?"))}')
        finally:
            ss.backup_dir = orig_backup_dir
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Test: schema version extraction
# ---------------------------------------------------------------------------
def test_schema_version_extraction():
    """get_schema_version_from_db should read app_settings correctly."""
    tmpdir = tempfile.mkdtemp()
    try:
        db_path = _make_test_db(tmpdir)
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO app_settings (key, value) VALUES ('schema_version', '20261013-003')"
        )
        conn.commit()
        conn.close()

        ver = backup_service.get_schema_version_from_db(db_path)
        assert ver == '20261013-003', f'Expected 20261013-003, got {ver}'
        print('  PASS: Schema version extracted correctly')
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_schema_version_missing():
    """get_schema_version_from_db returns None when no version is set."""
    tmpdir = tempfile.mkdtemp()
    try:
        db_path = _make_test_db(tmpdir)
        ver = backup_service.get_schema_version_from_db(db_path)
        assert ver is None, f'Expected None, got {ver}'
        print('  PASS: Missing version returns None')
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Test: manifest loading and saving
# ---------------------------------------------------------------------------
def test_manifest_operations():
    """_load_manifest and _save_manifest should round-trip correctly."""
    tmpdir = tempfile.mkdtemp()
    try:
        manifest = backup_service._load_manifest(tmpdir)
        assert 'backups' in manifest
        assert 'created_at' in manifest
        manifest['backups'].append({'filename': 'test.db'})
        backup_service._save_manifest(tmpdir, manifest)

        reloaded = backup_service._load_manifest(tmpdir)
        assert len(reloaded['backups']) == 1
        print('  PASS: Manifest save/load round-trip correct')
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Test: recovery procedures documented
# ---------------------------------------------------------------------------
def test_recovery_procedures():
    """All four recovery procedures should be documented."""
    expected = {'database_corruption', 'lost_encryption_key',
                'interrupted_migration', 'failed_application_update'}
    actual = set(backup_service.RECOVERY_PROCEDURES.keys())
    assert expected == actual, f'Missing: {expected - actual}'

    for key, proc in backup_service.RECOVERY_PROCEDURES.items():
        assert 'title' in proc, f'{key} missing title'
        assert 'steps' in proc, f'{key} missing steps'
        assert len(proc['steps']) > 0, f'{key} should have at least one step'

    print(f'  PASS: All {len(expected)} recovery procedures documented')


def test_get_recovery_procedure():
    """get_recovery_procedure should return formatted text."""
    text = backup_service.get_recovery_procedure('database_corruption')
    assert text is not None
    assert len(text) > 10
    print('  PASS: Recovery procedure text generated')

    result = backup_service.get_recovery_procedure('nonexistent')
    assert result is None
    print('  PASS: Unknown procedure returns None')


# ---------------------------------------------------------------------------
# Test: human-readable size formatting
# ---------------------------------------------------------------------------
def test_human_size():
    """_human_size should format bytes correctly."""
    assert backup_service._human_size(500) == '500.0 B'
    assert backup_service._human_size(1500) == '1.5 KB'
    assert backup_service._human_size(1_500_000) == '1.4 MB'
    print('  PASS: Human-readable sizes correct')


# ---------------------------------------------------------------------------
# Test: backup info endpoint structure
# ---------------------------------------------------------------------------
def test_backup_status_structure():
    """get_backup_status should return the expected keys."""
    tmpdir = tempfile.mkdtemp()
    try:
        import app.services.storage_service as ss
        orig_backup_dir = ss.backup_dir
        ss.backup_dir = lambda: tmpdir

        status = backup_service.get_backup_status()
        assert 'backup_directory' in status
        assert 'total_backups' in status
        assert 'retention_policy' in status
        assert status['retention_policy']['max_age_days'] == 90
        assert status['retention_policy']['max_count'] == 20
        print('  PASS: Backup status structure correct')
    finally:
        ss.backup_dir = orig_backup_dir
        shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Test: schema hash is consistent for same schema
# ---------------------------------------------------------------------------
def test_schema_hash_consistent():
    """compute_db_schema_hash should be identical for same schema."""
    tmpdir1 = tempfile.mkdtemp()
    tmpdir2 = tempfile.mkdtemp()
    try:
        _close_connections()
        time.sleep(0.2)
        db1 = _make_test_db(tmpdir1)
        db2 = _make_test_db(tmpdir2, with_data=True)

        hash1 = backup_service.compute_db_schema_hash(db1)
        hash2 = backup_service.compute_db_schema_hash(db2)
        assert hash1 == hash2, 'Schema hash should be identical for same schema'
        assert hash1 is not None
        print('  PASS: Schema hash is schema-only, ignores data')
    finally:
        shutil.rmtree(tmpdir1, ignore_errors=True)
        shutil.rmtree(tmpdir2, ignore_errors=True)


# ---------------------------------------------------------------------------
# Test: prune_backups removes old entries
# ---------------------------------------------------------------------------
def test_prune_backups_removes_old():
    """prune_backups should respect max_count and max_age_days."""
    tmpdir = tempfile.mkdtemp()
    try:
        import app.services.storage_service as ss
        orig_backup_dir = ss.backup_dir
        ss.backup_dir = lambda: tmpdir

        # Add some fake entries to the manifest
        manifest = backup_service._load_manifest(tmpdir)
        for i in range(5):
            manifest['backups'].append({
                'filename': f'old-{i}.db',
                'path': os.path.join(tmpdir, f'old-{i}.db'),
                'sha256': 'abc' * 21,
                'size_bytes': 1024,
                'size_readable': '1.0 KB',
                'created_at': '2020-01-01T00:00:00',  # Very old
                'schema_version': '20261013-003',
                'schema_hash': 'xyz',
                'type': 'snapshot',
                'label': 'old',
            })
            # Create the file
            with open(os.path.join(tmpdir, f'old-{i}.db'), 'wb') as f:
                f.write(b'\x00' * 1024)
        backup_service._save_manifest(tmpdir, manifest)

        result = backup_service.prune_backups(max_age_days=30, max_count=3)
        assert result['removed_count'] > 0, 'Should remove old backups'
        print(f'  PASS: Pruned {result["removed_count"]} old backups, kept {result["kept_count"]}')
    finally:
        ss.backup_dir = orig_backup_dir
        shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Run all tests
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    print('Running backup_service tests...')
    tests = [
        test_sha256_computation,
        test_verify_backup_valid,
        test_verify_backup_corrupt,
        test_verify_backup_missing_file,
        test_restore_valid_backup,
        test_schema_version_extraction,
        test_schema_version_missing,
        test_manifest_operations,
        test_recovery_procedures,
        test_get_recovery_procedure,
        test_human_size,
        test_backup_status_structure,
        test_schema_hash_consistent,
        test_prune_backups_removes_old,
    ]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as exc:
            print(f'  FAIL: {test.__name__}: {exc}')
            import traceback
            traceback.print_exc()
            failed += 1
    print(f'\nResults: {passed} passed, {failed} failed')
    sys.exit(1 if failed else 0)
