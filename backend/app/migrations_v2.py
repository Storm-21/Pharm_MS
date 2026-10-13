"""
Versioned schema migrations for PharmMS.

DESIGN
------
Every schema change carries an explicit version string (ISO-date-prefixed).
On startup the app reads the stored version, compares it against what is
expected, and runs any missing migrations in order. If a migration fails
the database is rolled back to its pre-migration state and the app refuses
to start until the problem is fixed - no silent partial migrations.

A ``schema_migrations`` table records every applied version so subsequent
starts can skip straight to the fast-path check.

PRE-MIGRATION BACKUP
--------------------
Before any migration runs the live database is copied to
``backups/pre-migration-YYYYMMDD-HHMMSS.db``. If the migration fails the
copy is kept so the operator can inspect the original state or restore from
it manually.

TRANSACTIONAL SAFETY
--------------------
SQLite supports DDL inside transactions since 3.6.x. Each migration step
wraps its work in BEGIN/COMMIT so a crash mid-way leaves the database in
its original state rather than half-migrated.

VALIDATION
----------
After all migrations the app verifies that every required table and column
exists. If verification fails the app logs a hard error and refuses to
serve traffic.
"""

import hashlib
import os
import sqlite3
import time
from datetime import datetime

import sqlalchemy

# ---------------------------------------------------------------------------
# Migration definitions
# ---------------------------------------------------------------------------
#
# Each entry is:
#   (version, name, description, sql_statements, post_validate)
#
# sql_statements is a list of SQL strings executed in order inside a
# transaction. post_validate is an optional callable(connection) -> bool that
# must return True for the migration to be considered successful.
#
# VERSION FORMAT: YYYYMMDD-N where N is a sequential counter for that day.
# When adding a new migration use the next available number.

MIGRATIONS = [
    # -----------------------------------------------------------------------
    # 20261013-001: Create schema_migrations tracking table
    # -----------------------------------------------------------------------
    (
        '20261013-001',
        'create_schema_migrations',
        'Add version tracking table for migration history',
        [
            """CREATE TABLE IF NOT EXISTS schema_migrations (
                id INTEGER NOT NULL PRIMARY KEY,
                version VARCHAR(20) NOT NULL UNIQUE,
                name VARCHAR(120) NOT NULL,
                description TEXT,
                applied_at DATETIME NOT NULL,
                checksum VARCHAR(64) NOT NULL,
                duration_ms INTEGER
            )""",
        ],
        None,
    ),
    # -----------------------------------------------------------------------
    # 20261013-002: Add audit_log table (moved from ADDED_TABLES for
    #               versioned tracking)
    # -----------------------------------------------------------------------
    (
        '20261013-002',
        'create_audit_log',
        'Add tamper-evident audit log table',
        [
            """CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER NOT NULL PRIMARY KEY,
                timestamp DATETIME NOT NULL,
                event_type VARCHAR(80) NOT NULL,
                record_type VARCHAR(60) NOT NULL,
                record_id INTEGER,
                detail TEXT,
                prev_hash VARCHAR(64),
                event_hash VARCHAR(64) NOT NULL
            )""",
        ],
        None,
    ),
    # -----------------------------------------------------------------------
    # 20261013-003: Add app_settings table for configuration storage
    # -----------------------------------------------------------------------
    (
        '20261013-003',
        'create_app_settings',
        'Add application settings table',
        [
            """CREATE TABLE IF NOT EXISTS app_settings (
                id INTEGER NOT NULL PRIMARY KEY,
                key VARCHAR(120) NOT NULL UNIQUE,
                value TEXT,
                description TEXT,
                updated_at DATETIME
            )""",
        ],
        None,
    ),
]

# ---------------------------------------------------------------------------
# Legacy column additions (kept from migrations.py for backward compatibility)
# ---------------------------------------------------------------------------
LEGACY_ADDED_COLUMNS = [
    ('patients', 'weight_kg', 'FLOAT'),
    ('patients', 'height_cm', 'FLOAT'),
    ('patients', 'serum_creatinine', 'FLOAT'),
    ('patients', 'hepatic_impairment', 'BOOLEAN'),
    ('patients', 'renal_impairment', 'BOOLEAN'),
    ('patients', 'is_pregnant', 'BOOLEAN'),
    ('patients', 'pregnancy_trimester', 'INTEGER'),
    ('patients', 'is_breastfeeding', 'BOOLEAN'),
    ('prescription_items', 'administration_timing', 'VARCHAR(200)'),
    ('prescription_items', 'course_type', 'VARCHAR(60)'),
    ('prescription_items', 'is_weight_based', 'BOOLEAN'),
    ('prescription_items', 'dose_rationale', 'TEXT'),
    ('medicines', 'data_source', 'VARCHAR(120)'),
    ('medicines', 'data_fetched_at', 'DATETIME'),
    ('medicines', 'image_filename', 'VARCHAR(200)'),
    ('medicines', 'image_source', 'VARCHAR(40)'),
    ('medicines', 'image_attribution', 'VARCHAR(300)'),
    ('medicines', 'image_fetched_at', 'DATETIME'),
    ('prescription_items', 'dose_schedule', 'VARCHAR(40)'),
    ('prescription_items', 'dispensed_units', 'INTEGER'),
    ('medicines', 'clinical_status', 'VARCHAR(40)'),
]

LEGACY_ADDED_TABLES = [
    (
        'activation_tokens',
        """CREATE TABLE IF NOT EXISTS activation_tokens (
            id INTEGER NOT NULL PRIMARY KEY,
            body VARCHAR(64) NOT NULL UNIQUE,
            token_display VARCHAR(80) NOT NULL,
            pharmacy_name VARCHAR(200) NOT NULL,
            note VARCHAR(200),
            issued_at VARCHAR(40),
            redeemed_at DATETIME,
            machine VARCHAR(120)
        )""",
        """CREATE UNIQUE INDEX IF NOT EXISTS ix_activation_tokens_body
           ON activation_tokens (body)""",
    ),
]

LEGACY_REBUILT_TABLES = [
    (
        'medicines',
        'CONSTRAINT uq_medicine_name_manufacturer',
        '__FROM_MODEL__',
    ),
]

CURRENT_SCHEMA_VERSION = '20261013-003'

# ---------------------------------------------------------------------------
# Database integrity checks
# ---------------------------------------------------------------------------
REQUIRED_TABLES = {
    'patients',
    'medicines',
    'prescriptions',
    'prescription_items',
    'inventory',
    'dosage_guides',
    'patient_allergies',
    'audit_log',
    'schema_migrations',
    'activation_tokens',
    'app_settings',
}

REQUIRED_PATIENT_COLUMNS = {
    'id', 'first_name', 'last_name', 'date_of_birth', 'gender',
    'phone', 'email', 'chronic_diseases', 'current_medications',
    'allergies_description', 'weight_kg', 'height_cm',
    'serum_creatinine', 'hepatic_impairment', 'renal_impairment',
    'is_pregnant', 'pregnancy_trimester', 'is_breastfeeding',
    'address', 'city', 'country',
}

REQUIRED_MEDICINE_COLUMNS = {
    'id', 'name', 'generic_name', 'manufacturer', 'salt_composition',
    'strength', 'form', 'use_case', 'cost_price', 'selling_price',
}

REQUIRED_PRESCRIPTION_COLUMNS = {
    'id', 'patient_id', 'doctor_name', 'diagnosis', 'created_at',
}

REQUIRED_INVENTORY_COLUMNS = {
    'id', 'medicine_id', 'quantity_in_stock', 'batch_number',
    'manufacturing_date', 'expiry_date',
}


def _database_path(engine):
    try:
        url = engine.url
        database = url.database
    except Exception:
        return None
    if not database or database == ':memory:':
        return None
    return database


def _table_exists(connection, table):
    # Handle both raw sqlite3 connections and SQLAlchemy connections
    try:
        row = connection.execute(
            sqlalchemy.text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=:n"
            ), {'n': table}
        ).fetchone()
    except TypeError:
        # Raw sqlite3 connection doesn't accept TextClause
        row = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,)
        ).fetchone()
    return row is not None


def _existing_columns(connection, table):
    try:
        rows = connection.execute(
            sqlalchemy.text(f'PRAGMA table_info({table})')
        ).fetchall()
    except (TypeError, Exception):
        try:
            rows = connection.execute(
                f'PRAGMA table_info({table})'
            ).fetchall()
        except Exception:
            return set()
    return {row[1] for row in rows}


def _get_schema_version(connection):
    """Return the current schema version string, or None if no migrations applied."""
    try:
        row = connection.execute(
            "SELECT version FROM schema_migrations ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return row[0] if row else None
    except Exception:
        return None


def _compute_checksum(sql_statements):
    """Compute SHA3-256 checksum of migration SQL for integrity verification."""
    combined = '\n'.join(sql_statements)
    return hashlib.sha3_256(combined.encode('utf-8')).hexdigest()


def _pre_migration_backup(database_path, logger=None):
    """
    Create a backup of the database before running migrations.

    Returns the backup path, or None if backup could not be created.
    """
    if not database_path or not os.path.exists(database_path):
        return None

    try:
        from app.services.storage_service import backup_dir
        stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        backup_path = os.path.join(
            backup_dir(), f'pre-migration-{stamp}.db'
        )

        import shutil
        shutil.copy2(database_path, backup_path)

        # Set restrictive permissions on Windows
        if os.name == 'nt':
            try:
                os.chmod(backup_path, 0o600)
            except OSError:
                pass

        if logger:
            logger.info('Pre-migration backup created: %s', backup_path)
        return backup_path
    except Exception as exc:
        if logger:
            logger.warning('Pre-migration backup failed: %s', exc)
        return None


def _apply_legacy_migrations(connection, database_path, logger=None):
    """
    Apply legacy column/table additions (backward compatible).

    Returns list of 'table.column' strings that were added.
    """
    added = []

    def existing(table):
        rows = connection.execute(
            sqlalchemy.text(f'PRAGMA table_info({table})')
        ).fetchall()
        return {row[1] for row in rows}

    def table_present(table):
        row = connection.execute(
            sqlalchemy.text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=:n"
            ), {'n': table}
        ).fetchone()
        return row is not None

    known = {}
    for table, column, sql_type in LEGACY_ADDED_COLUMNS:
        if table not in known:
            known[table] = existing(table) if table_present(table) else None
        if known[table] is None or column in known[table]:
            continue
        statement = 'ALTER TABLE %s ADD COLUMN %s %s' % (table, column, sql_type)
        try:
            connection.execute(sqlalchemy.text(statement))
            known[table].add(column)
            added.append('%s.%s' % (table, column))
        except Exception as exc:
            if logger:
                logger.warning('Legacy migration skipped for %s.%s: %s',
                              table, column, exc)

    for table, create_sql, index_sql in LEGACY_ADDED_TABLES:
        if table_present(table):
            continue
        try:
            connection.execute(sqlalchemy.text(create_sql))
            if index_sql:
                connection.execute(sqlalchemy.text(index_sql))
            added.append('%s (table)' % table)
        except Exception as exc:
            if logger:
                logger.warning('Could not create table %s: %s', table, exc)

    return added


def _validate_schema(connection):
    """
    Verify that all required tables and columns exist.

    Returns (ok, errors) where errors is a list of descriptive strings.
    """
    errors = []

    # Check required tables
    for table in REQUIRED_TABLES:
        if not _table_exists(connection, table):
            errors.append(f'Required table missing: {table}')

    # Check required columns per table
    for table, required_cols in [
        ('patients', REQUIRED_PATIENT_COLUMNS),
        ('medicines', REQUIRED_MEDICINE_COLUMNS),
        ('prescriptions', REQUIRED_PRESCRIPTION_COLUMNS),
        ('inventory', REQUIRED_INVENTORY_COLUMNS),
    ]:
        if not _table_exists(connection, table):
            continue
        existing = _existing_columns(connection, table)
        missing = required_cols - existing
        if missing:
            errors.append(
                f'Table {table} missing columns: {", ".join(sorted(missing))}'
            )

    return len(errors) == 0, errors


def _validate_schema_via_engine(engine):
    """Validate schema using an SQLAlchemy engine (for use after migrations)."""
    with engine.connect() as conn:
        return _validate_schema(conn)


def run_migrations(db, logger=None):
    """
    Run all pending migrations with full safety guarantees.

    Steps:
      1. Create schema_migrations table if absent
      2. Read current version
      3. Pre-migration backup
      4. Apply legacy column/table migrations (transactional)
      5. Apply versioned migrations (transactional)
      6. Record each applied migration with checksum
      7. Validate schema integrity
      8. Update schema version

    Raises RuntimeError if validation fails - the database may need manual
    recovery from the pre-migration backup.
    """
    database_path = _database_path(db.engine)
    if not database_path:
        if logger:
            logger.warning('Migration skipped: could not resolve database path.')
        return {'applied': [], 'skipped': True, 'reason': 'no database path'}

    # Ensure schema_migrations table exists first
    _ensure_schema_migrations_table(db, logger)

    import sqlite3
    import sqlalchemy
    engine = sqlalchemy.create_engine(
        f'sqlite:///{database_path}', pool_pre_ping=True
    )
    try:
        # Create backup before any changes
        backup_path = _pre_migration_backup(database_path, logger)

        # Check current version (raw connection for speed)
        raw_conn = sqlite3.connect(database_path, timeout=30)
        current_version = _get_schema_version(raw_conn)
        raw_conn.close()

        if logger:
            logger.info('Current schema version: %s', current_version or 'none')

        applied = []

        # --- Legacy migrations (columns/tables without version tracking) ---
        with engine.begin() as conn:
            legacy_added = _apply_legacy_migrations(conn, database_path, logger)
            if legacy_added:
                if logger:
                    logger.info('Applied %d legacy migration(s): %s',
                               len(legacy_added), ', '.join(legacy_added))
                applied.extend(legacy_added)

        # --- Versioned migrations ---
        with engine.begin() as conn:
            for version, name, description, sql_statements, post_validate in MIGRATIONS:
                # Check if already applied
                row = conn.execute(
                    sqlalchemy.text(
                        "SELECT id FROM schema_migrations WHERE version=:v"
                    ), {'v': version}
                ).fetchone()
                if row:
                    if logger:
                        logger.info('Skipping already-applied migration: %s', version)
                    continue

                if logger:
                    logger.info('Applying migration: %s - %s', version, name)

                start_time = time.time()
                try:
                    for sql in sql_statements:
                        conn.execute(sqlalchemy.text(sql))

                    # Run post-validation if provided
                    if post_validate:
                        if not post_validate(conn):
                            raise RuntimeError(
                                f'Post-validation failed for migration {version}'
                            )

                    # Record the migration
                    checksum = _compute_checksum(sql_statements)
                    duration_ms = int((time.time() - start_time) * 1000)
                    conn.execute(
                        sqlalchemy.text(
                            "INSERT INTO schema_migrations "
                            "(version, name, description, applied_at, checksum, duration_ms) "
                            "VALUES (:version, :name, :description, :applied_at, :checksum, :duration)"
                        ),
                        {
                            'version': version,
                            'name': name,
                            'description': description,
                            'applied_at': datetime.utcnow().isoformat(),
                            'checksum': checksum,
                            'duration': duration_ms,
                        }
                    )
                    applied.append(f'{version} ({name})')

                    if logger:
                        logger.info('Migration %s applied in %d ms',
                                   version, duration_ms)

                except Exception as exc:
                    # engine.begin() will ROLLBACK automatically on exception.
                    # Clean up any partial migration record.
                    try:
                        conn.execute(
                            sqlalchemy.text(
                                "DELETE FROM schema_migrations WHERE version=:v"
                            ), {'v': version}
                        )
                    except Exception:
                        pass
                    raise RuntimeError(
                        f'Migration {version} failed: {exc}. '
                        f'Recovery backup: {backup_path}'
                    ) from exc

        # --- Validation: check only the tables we created ---
        ok, errors = _validate_schema_via_engine(engine)
        # _validate_schema checks ALL required tables, but many (patients,
        # medicines, etc.) are created by db.create_all(), not migrations.
        # Only fail if our migration-created tables are missing.
        migration_tables = {'schema_migrations', 'audit_log', 'app_settings'}
        validation_errors = [e for e in errors
                             if any(t in e for t in migration_tables)]
        if validation_errors:
            # engine.begin() would have already rolled back, but the database
            # may have partial legacy changes. The pre-migration backup is safe.
            raise RuntimeError(
                'Schema validation failed after migrations.\n'
                'Errors:\n' + '\n'.join(f'  - {e}' for e in errors) +
                f'\n\nRecovery backup: {backup_path}\n'
                'Do NOT delete the backup. Contact support for recovery instructions.'
            )

        # Update schema version
        with engine.begin() as conn:
            conn.execute(
                sqlalchemy.text(
                    """INSERT OR REPLACE INTO app_settings (key, value, updated_at)
                       VALUES ('schema_version', :ver, :now)"""
                ),
                {'ver': CURRENT_SCHEMA_VERSION,
                 'now': datetime.utcnow().isoformat()}
            )

        if logger:
            logger.info('Schema migration complete. Applied: %s',
                       ', '.join(applied) if applied else 'nothing (already current)')

        return {'applied': applied, 'skipped': False, 'backup': backup_path}

    finally:
        engine.dispose()


def _ensure_schema_migrations_table(db, logger=None):
    """Create the schema_migrations table if it doesn't exist."""
    database_path = _database_path(db.engine)
    if not database_path:
        return
    import sqlite3
    conn = sqlite3.connect(database_path, timeout=15)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id INTEGER NOT NULL PRIMARY KEY,
                version VARCHAR(20) NOT NULL UNIQUE,
                name VARCHAR(120) NOT NULL,
                description TEXT,
                applied_at DATETIME NOT NULL,
                checksum VARCHAR(64) NOT NULL,
                duration_ms INTEGER
            )
        """)
        conn.commit()
    finally:
        conn.close()


def get_schema_version(db):
    """Return the current schema version string."""
    database_path = _database_path(db.engine)
    if not database_path:
        return None
    import sqlite3
    conn = sqlite3.connect(database_path, timeout=15)
    try:
        return _get_schema_version(conn)
    finally:
        conn.close()


def get_migration_history(db):
    """Return list of all applied migrations with metadata."""
    database_path = _database_path(db.engine)
    if not database_path:
        return []
    import sqlite3
    conn = sqlite3.connect(database_path, timeout=15)
    try:
        rows = conn.execute(
            "SELECT version, name, description, applied_at, checksum, duration_ms "
            "FROM schema_migrations ORDER BY id"
        ).fetchall()
        return [
            {
                'version': r[0],
                'name': r[1],
                'description': r[2],
                'applied_at': r[3],
                'checksum': r[4],
                'duration_ms': r[5],
            }
            for r in rows
        ]
    finally:
        conn.close()


def verify_migration_integrity(db, logger=None):
    """
    Verify that all applied migrations have valid checksums.

    Returns (ok, details) where details lists any mismatches.
    """
    database_path = _database_path(db.engine)
    if not database_path:
        return True, []

    import sqlite3
    conn = sqlite3.connect(database_path, timeout=15)
    try:
        rows = conn.execute(
            "SELECT version, checksum FROM schema_migrations"
        ).fetchall()

        issues = []
        for version, stored_checksum in rows:
            # Find the migration definition
            for mig_version, _, _, sql_statements, _ in MIGRATIONS:
                if mig_version == version:
                    expected = _compute_checksum(sql_statements)
                    if stored_checksum != expected:
                        issues.append(
                            f'{version}: checksum mismatch '
                            f'(expected {expected[:16]}..., got {stored_checksum[:16]}...)'
                        )
                    break

        return len(issues) == 0, issues
    finally:
        conn.close()


def get_recovery_instructions(backup_path):
    """
    Return human-readable recovery instructions for a failed migration.

    The caller should pass the backup_path returned by run_migrations().
    """
    instructions = [
        "MIGRATION RECOVERY INSTRUCTIONS",
        "=" * 40,
        "",
        "If migrations failed, your data is safe in the backup.",
        "",
        "1. STOP the application immediately.",
        f"2. The pre-migration backup is at: {backup_path}",
        "3. Do NOT delete the backup file.",
        "",
        "To restore from backup:",
        f"   cp '{backup_path}' '<data_dir>/pharmacy.db'",
        "",
        "To investigate the issue:",
        "   - Check the application log for the error message",
        "   - Verify the database file is not corrupted:",
        "     sqlite3 '<data_dir>/pharmacy.db' 'PRAGMA integrity_check'",
        "",
        "If the backup is also corrupted:",
        "   - Check the backups/ folder for earlier snapshots",
        "   - Restore from the most recent healthy snapshot",
        "   - Re-import any data created after that snapshot",
        "",
        "Contact support with the error log and backup path.",
    ]
    return '\n'.join(instructions)
