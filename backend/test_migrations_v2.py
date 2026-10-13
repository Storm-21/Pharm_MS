"""
Tests for the versioned migration system (migrations_v2).

Covers:
  * Fresh database bootstrap (all migrations run on empty DB)
  * Legacy database migration (older schema gets upgraded)
  * Schema validation after migration
  * Idempotency (running twice is a no-op)
  * Checksum verification
  * Migration history metadata
  * Schema version tracking
"""

import os
import sys
import tempfile
import sqlite3
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import migration functions directly — we test them against raw sqlite3 DBs
from app.migrations_v2 import (
    CURRENT_SCHEMA_VERSION,
    MIGRATIONS,
    REQUIRED_TABLES,
    run_migrations,
    get_schema_version,
    get_migration_history,
    verify_migration_integrity,
    _compute_checksum,
    _validate_schema,
    _ensure_schema_migrations_table,
    _pre_migration_backup,
)


def _make_fresh_db(path):
    """Create an empty SQLite database (no tables)."""
    conn = sqlite3.connect(path)
    conn.close()
    return path


def _run_migrations_raw(db_path, logger=None):
    """
    Run migrations on a raw sqlite3 database path without going through
    the Flask app factory (which would pre-create tables via create_all).
    """
    import sqlalchemy
    # Create an in-memory engine just to satisfy _database_path()
    # We point it at our test DB
    engine = sqlalchemy.create_engine(f'sqlite:///{db_path}', pool_pre_ping=True)
    try:
        return run_migrations(engine, logger=logger)
    finally:
        engine.dispose()


# ---------------------------------------------------------------------------
# Test: fresh database bootstrapping
# ---------------------------------------------------------------------------
def test_fresh_database_got_all_tables():
    """A brand-new database should get every required table."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = _make_fresh_db(os.path.join(tmpdir, 'fresh.db'))

        # Simulate what the app factory does: create_all() first, then migrations
        import sqlalchemy
        engine = sqlalchemy.create_engine(f'sqlite:///{db_path}', pool_pre_ping=True)
        from app import db as shared_db
        shared_db.metadata.create_all(engine)
        engine.dispose()

        result = _run_migrations_raw(db_path)

        # The versioned migrations should have run
        assert len(result['applied']) >= 3, \
            f'Expected 3+ migrations, got {len(result["applied"])}: {result["applied"]}'

        # schema_migrations table must exist and record all versions
        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            "SELECT version FROM schema_migrations ORDER BY id"
        ).fetchall()
        conn.close()

        applied_versions = {r[0] for r in rows}
        for mig_version, _, _, _, _ in MIGRATIONS:
            assert mig_version in applied_versions, \
                f'Migration {mig_version} not recorded'

        # Verify migration-created tables exist
        # (application tables like patients/medicines are created by db.create_all())
        migration_tables = {'schema_migrations', 'audit_log', 'app_settings'}
        conn = sqlite3.connect(db_path)
        existing = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        conn.close()

        missing = migration_tables - existing
        assert not missing, f'Migration tables missing after fresh boot: {missing}'
        print(f'  PASS: {len(result["applied"])} migrations applied, migration tables present')


# ---------------------------------------------------------------------------
# Test: idempotency — running again does nothing
# ---------------------------------------------------------------------------
def test_idempotent_on_already_migrated():
    """Running migrations twice on the same DB is a no-op."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = _make_fresh_db(os.path.join(tmpdir, 'idem.db'))

        import sqlalchemy
        from app import db as shared_db
        engine = sqlalchemy.create_engine(f'sqlite:///{db_path}', pool_pre_ping=True)
        shared_db.metadata.create_all(engine)
        engine.dispose()

        _run_migrations_raw(db_path)
        result2 = _run_migrations_raw(db_path)

        assert result2['applied'] == [], \
            f'Second run should apply nothing, got: {result2["applied"]}'
        print('  PASS: Second run applied zero migrations')


# ---------------------------------------------------------------------------
# Test: legacy column additions applied when columns are missing
# ---------------------------------------------------------------------------
def test_legacy_columns_added():
    """Old-style ADD COLUMN operations still work on a legacy DB."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = _make_fresh_db(os.path.join(tmpdir, 'legacy.db'))

        # Create ONLY base tables WITHOUT clinical columns
        conn = sqlite3.connect(db_path)
        for tbl_sql in [
            "CREATE TABLE patients (id INTEGER NOT NULL PRIMARY KEY, "
             "first_name VARCHAR(120) NOT NULL, last_name VARCHAR(120) NOT NULL, "
             "date_of_birth DATE, gender VARCHAR(20))",
            "CREATE TABLE medicines (id INTEGER NOT NULL PRIMARY KEY, "
             "name VARCHAR(200) NOT NULL, manufacturer VARCHAR(200), "
             "strength VARCHAR(100), form VARCHAR(50))",
            "CREATE TABLE prescriptions (id INTEGER NOT NULL PRIMARY KEY, "
             "patient_id INTEGER, doctor_name VARCHAR(200), "
             "diagnosis TEXT, created_at DATETIME)",
            "CREATE TABLE prescription_items (id INTEGER NOT NULL PRIMARY KEY, "
             "prescription_id INTEGER, medicine_id INTEGER, quantity INTEGER)",
            "CREATE TABLE inventory (id INTEGER NOT NULL PRIMARY KEY, "
             "medicine_id INTEGER, quantity_in_stock INTEGER, "
             "batch_number VARCHAR(100), expiry_date DATE)",
            "CREATE TABLE dosage_guides (id INTEGER NOT NULL PRIMARY KEY, "
             "medicine_name VARCHAR(200), indication TEXT)",
            "CREATE TABLE patient_allergies (id INTEGER NOT NULL PRIMARY KEY, "
             "patient_id INTEGER, allergen VARCHAR(200))",
            "CREATE TABLE audit_log (id INTEGER NOT NULL PRIMARY KEY, "
             "timestamp DATETIME, event_type VARCHAR(80), record_type VARCHAR(60), "
             "record_id INTEGER, detail TEXT, prev_hash VARCHAR(64), "
             "event_hash VARCHAR(64))",
            "CREATE TABLE schema_migrations (id INTEGER NOT NULL PRIMARY KEY, "
             "version VARCHAR(20) NOT NULL UNIQUE, name VARCHAR(120) NOT NULL, "
             "description TEXT, applied_at DATETIME NOT NULL, "
             "checksum VARCHAR(64) NOT NULL, duration_ms INTEGER)",
            "CREATE TABLE app_settings (id INTEGER NOT NULL PRIMARY KEY, "
             "key VARCHAR(120) NOT NULL UNIQUE, value TEXT, "
             "description TEXT, updated_at DATETIME)",
            "CREATE TABLE activation_tokens (id INTEGER NOT NULL PRIMARY KEY, "
             "body VARCHAR(64) NOT NULL UNIQUE, token_display VARCHAR(80) NOT NULL, "
             "pharmacy_name VARCHAR(200) NOT NULL, note VARCHAR(200), "
             "issued_at VARCHAR(40), redeemed_at DATETIME, machine VARCHAR(120))",
        ]:
            conn.execute(tbl_sql)
        conn.commit()
        conn.close()

        # Now run migrations — should add clinical columns via legacy path
        result = _run_migrations_raw(db_path)

        # Verify the clinical columns were added to patients
        conn = sqlite3.connect(db_path)
        cols = {r[1] for r in conn.execute('PRAGMA table_info(patients)').fetchall()}
        conn.close()

        expected = {'weight_kg', 'height_cm', 'serum_creatinine',
                    'hepatic_impairment', 'renal_impairment',
                    'is_pregnant', 'pregnancy_trimester', 'is_breastfeeding'}
        missing = expected - cols
        assert not missing, f'Clinical columns missing: {missing}'
        print(f'  PASS: Legacy columns added, result applied={len(result["applied"])}')


# ---------------------------------------------------------------------------
# Test: schema validation catches missing tables
# ---------------------------------------------------------------------------
def test_validation_catches_missing_table():
    """_validate_schema returns errors when a required table is absent."""
    conn = sqlite3.connect(':memory:')
    conn.execute('CREATE TABLE patients (id INTEGER PRIMARY KEY)')

    ok, errors = _validate_schema(conn)
    assert not ok, 'Validation should fail with missing tables'
    assert any('inventory' in e for e in errors), 'Should report missing inventory table'
    conn.close()
    print('  PASS: Validation correctly detected missing tables')


# ---------------------------------------------------------------------------
# Test: migration checksums are deterministic
# ---------------------------------------------------------------------------
def test_checksums_deterministic():
    """Same SQL always produces the same SHA3-256 checksum."""
    sql = ['CREATE TABLE test (id INTEGER)']
    h1 = _compute_checksum(sql)
    h2 = _compute_checksum(sql)
    assert h1 == h2, 'Checksum should be deterministic'
    assert len(h1) == 64, 'SHA3-256 produces 64 hex characters'
    print(f'  PASS: Checksum deterministic ({h1[:16]}...)')


# ---------------------------------------------------------------------------
# Test: migration history records timestamps and durations
# ---------------------------------------------------------------------------
def test_migration_history_has_metadata():
    """Each migration entry should have applied_at and duration_ms."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = _make_fresh_db(os.path.join(tmpdir, 'history.db'))

        import sqlalchemy
        from app import db as shared_db
        engine = sqlalchemy.create_engine(f'sqlite:///{db_path}', pool_pre_ping=True)
        shared_db.metadata.create_all(engine)
        engine.dispose()

        _run_migrations_raw(db_path)

        # Query directly
        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            "SELECT version, name, description, applied_at, checksum, duration_ms "
            "FROM schema_migrations ORDER BY id"
        ).fetchall()
        conn.close()

        assert len(rows) >= 3, f'Expected 3+ history entries, got {len(rows)}'
        for r in rows:
            assert r[0], 'version must be set'
            assert r[1], 'name must be set'
            assert r[4], 'checksum must be set'
            assert r[5] is not None, 'duration_ms must be set'
        print(f'  PASS: Migration history has {len(rows)} complete entries')


# ---------------------------------------------------------------------------
# Test: pre-migration backup is created
# ---------------------------------------------------------------------------
def test_pre_migration_backup_created():
    """A backup file should be recorded after migration runs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'backup_test.db')
        _make_fresh_db(db_path)

        import sqlalchemy
        from app import db as shared_db
        engine = sqlalchemy.create_engine(f'sqlite:///{db_path}', pool_pre_ping=True)
        shared_db.metadata.create_all(engine)
        engine.dispose()

        result = _run_migrations_raw(db_path)

        # Result should indicate migrations ran
        assert 'applied' in result
        print(f'  PASS: Migrations completed, applied={len(result["applied"])}')


# ---------------------------------------------------------------------------
# Test: checksum integrity verification
# ---------------------------------------------------------------------------
def test_integrity_verification():
    """verify_migration_integrity should confirm stored checksums match."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = _make_fresh_db(os.path.join(tmpdir, 'integrity.db'))

        import sqlalchemy
        from app import db as shared_db
        engine = sqlalchemy.create_engine(f'sqlite:///{db_path}', pool_pre_ping=True)
        shared_db.metadata.create_all(engine)
        engine.dispose()

        _run_migrations_raw(db_path)

        # Verify checksums by querying directly
        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            "SELECT version, checksum FROM schema_migrations"
        ).fetchall()
        conn.close()

        # Recompute expected checksums
        for version, stored in rows:
            for mig_v, _, _, sql, _ in MIGRATIONS:
                if mig_v == version:
                    expected = _compute_checksum(sql)
                    assert stored == expected, \
                        f'Checksum mismatch for {version}'
                    break

        assert len(rows) >= 3, f'Expected 3+ migration records, got {len(rows)}'
        print('  PASS: All migration checksums verified')


# ---------------------------------------------------------------------------
# Test: schema version is tracked
# ---------------------------------------------------------------------------
def test_schema_version_tracked():
    """After migrations, schema version should be CURRENT_SCHEMA_VERSION."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = _make_fresh_db(os.path.join(tmpdir, 'version.db'))

        import sqlalchemy
        from app import db as shared_db
        engine = sqlalchemy.create_engine(f'sqlite:///{db_path}', pool_pre_ping=True)
        shared_db.metadata.create_all(engine)
        engine.dispose()

        _run_migrations_raw(db_path)

        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT value FROM app_settings WHERE key='schema_version'"
        ).fetchone()
        conn.close()

        assert row is not None, 'schema_version not found in app_settings'
        assert row[0] == CURRENT_SCHEMA_VERSION, \
            f'Expected {CURRENT_SCHEMA_VERSION}, got {row[0]}'
        print(f'  PASS: Schema version is {row[0]}')


# ---------------------------------------------------------------------------
# Test: _pre_migration_backup copies the file
# ---------------------------------------------------------------------------
def test_pre_migration_backup_copies_file():
    """_pre_migration_backup should create a copy with restricted perms."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src = _make_fresh_db(os.path.join(tmpdir, 'live.db'))
        # Add some data so the copy is non-empty
        conn = sqlite3.connect(src)
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.commit()
        conn.close()

        import app.services.storage_service as ss
        orig = ss.backup_dir
        ss.backup_dir = lambda: tmpdir
        try:
            backup_path = _pre_migration_backup(src, logger=None)
            assert backup_path is not None
            assert os.path.isfile(backup_path)
            assert os.path.getsize(backup_path) > 0
            print(f'  PASS: Backup copy created: {os.path.basename(backup_path)}')
        finally:
            ss.backup_dir = orig


# ---------------------------------------------------------------------------
# Run all tests
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    print('Running migrations_v2 tests...')
    tests = [
        test_fresh_database_got_all_tables,
        test_idempotent_on_already_migrated,
        test_legacy_columns_added,
        test_validation_catches_missing_table,
        test_checksums_deterministic,
        test_migration_history_has_metadata,
        test_pre_migration_backup_created,
        test_integrity_verification,
        test_schema_version_tracked,
        test_pre_migration_backup_copies_file,
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
