"""
Lightweight schema migration.

WHY THIS EXISTS
---------------
SQLAlchemy's ``create_all()`` creates tables that do not exist but never alters
tables that do. When the clinical columns (weight, creatinine, pregnancy) were
added to ``patients``, every existing database - including a pharmacy's live
one - would have failed at the first query with:

    sqlite3.OperationalError: no such column: patients.weight_kg

A pharmacy cannot be asked to delete and re-create its patient records to pick
up a schema change, so the columns are added in place instead.

HOW IT WORKS
------------
Each entry lists (table, column, SQL type). On startup every entry is compared
against the live schema with PRAGMA table_info, and only the missing ones are
added. Adding a nullable column is safe and instant in SQLite; existing rows
keep their data and read as NULL, which the safety engine treats as "not
recorded" rather than as a negative finding.

This is deliberately not Alembic. The project ships as a single .exe with no
migration step and no developer present to run one, so the migration has to be
automatic, idempotent and impossible to get wrong. For a schema this size that
is a better trade than a migration framework.
"""

import sqlalchemy

# (table, column, SQL type) - applied in order, only when missing.
ADDED_COLUMNS = [
    # Patient clinical measurements, needed for weight-based and renal dosing.
    ('patients', 'weight_kg', 'FLOAT'),
    ('patients', 'serum_creatinine', 'FLOAT'),
    ('patients', 'hepatic_impairment', 'BOOLEAN'),
    ('patients', 'renal_impairment', 'BOOLEAN'),
    ('patients', 'is_pregnant', 'BOOLEAN'),
    ('patients', 'pregnancy_trimester', 'INTEGER'),
    ('patients', 'is_breastfeeding', 'BOOLEAN'),

    # Prescription items: the cycle/timing fields the administration engine
    # fills in. Kept on the item because the instructions are per medicine.
    ('prescription_items', 'administration_timing', 'VARCHAR(200)'),
    ('prescription_items', 'course_type', 'VARCHAR(60)'),
    ('prescription_items', 'is_weight_based', 'BOOLEAN'),
    ('prescription_items', 'dose_rationale', 'TEXT'),

    # Medicine: provenance for anything pulled from the live source, so a
    # fetched record is distinguishable from the authored reference set.
    ('medicines', 'data_source', 'VARCHAR(120)'),
    ('medicines', 'data_fetched_at', 'DATETIME'),
]


def _existing_columns(connection, table):
    """Column names present in a table, via PRAGMA. Empty set if absent."""
    try:
        rows = connection.execute(
            sqlalchemy.text('PRAGMA table_info(%s)' % table)
        ).fetchall()
    except Exception:
        return set()
    return {row[1] for row in rows}


def _database_path(engine):
    # Filesystem path of the SQLite database behind a SQLAlchemy engine.
    # Returns None when the URL is not a plain file path, which would mean the
    # migration cannot safely open its own connection to it.
    try:
        url = engine.url
        database = url.database
    except Exception:
        return None
    if not database or database == ':memory:':
        return None
    return database

def _table_exists(connection, table):
    row = connection.execute(
        sqlalchemy.text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=:n"
        ), {'n': table}
    ).fetchone()
    return row is not None


def apply_migrations(db, logger=None):
    """
    Add any missing columns. Safe to call on every startup.

    Returns a list of 'table.column' strings that were added.
    """
    added = []
    engine = db.engine
    # --- Fast path ---------------------------------------------------------
    # Every startup calls this, so once the schema is current the work should
    # be skipped cheaply. The probe reads the LAST column in the list from the
    # real database: if it is present, the migration completed in full on a
    # previous run.
    #
    # This must reflect the live schema, NOT SQLAlchemy's model metadata. An
    # earlier version used sqlalchemy.inspect(engine), which consults the
    # model definition - and the model always declares these columns, so the
    # probe concluded the work was already done and returned immediately. The
    # migration then silently did nothing on every database, while reporting
    # success. PRAGMA reads the actual file, which is the only thing that can
    # tell whether an upgrade is genuinely needed.
    last_table, last_column, _type = ADDED_COLUMNS[-1]
    try:
        import sqlite3
        probe_path = _database_path(engine)
        if probe_path:
            probe = sqlite3.connect(probe_path, timeout=15)
            try:
                rows = probe.execute(
                    'PRAGMA table_info(%s)' % last_table).fetchall()
                if last_column in {row[1] for row in rows}:
                    return []
            finally:
                probe.close()
    except Exception:
        # If the probe cannot run, fall through to the full migration rather
        # than skipping it on a guess.
        pass
    # --- Real migration ----------------------------------------------------
    # The DDL runs on its OWN sqlite3 connection, deliberately bypassing
    # SQLAlchemy's engine and session entirely.
    #
    # This is not a stylistic choice; it is the fix for a bug that made every
    # earlier version of this migration a silent no-op. app startup calls
    # db.create_all() before this function. create_all() opens a transaction on
    # a pooled connection and leaves it open. Anything issued through that same
    # engine joins the already-open transaction, and because nothing ever
    # commits it, exiting the context manager rolls the ALTER TABLE statements
    # back. The result was that the columns appeared to exist for the life of
    # the process and were absent from the file immediately afterwards - a
    # migration reporting success while changing nothing.
    #
    # A dedicated connection with its own autocommit behaviour cannot be
    # swallowed by SQLAlchemy's transaction, so the ALTER TABLE statements are
    # really persisted. Verified by reading the file back over a separate
    # connection in test_migration.py, which is the assertion that caught it.
    database_path = _database_path(engine)
    if not database_path:
        if logger:
            logger.warning('Migration skipped: could not resolve the database path.')
        return []

    import sqlite3
    connection = sqlite3.connect(database_path, timeout=30)
    try:
        # Isolation level None puts pysqlite in autocommit mode, so each
        # ALTER TABLE is committed by sqlite itself as it executes.
        connection.isolation_level = None
        def existing(table):
            rows = connection.execute('PRAGMA table_info(%s)' % table).fetchall()
            return {row[1] for row in rows}

        def table_present(table):
            row = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,)).fetchone()
            return row is not None
        known = {}
        for table, column, sql_type in ADDED_COLUMNS:
            if table not in known:
                known[table] = existing(table) if table_present(table) else None
            if known[table] is None or column in known[table]:
                continue
            statement = 'ALTER TABLE %s ADD COLUMN %s %s' % (table, column, sql_type)
            try:
                connection.execute(statement)
                known[table].add(column)
                added.append('%s.%s' % (table, column))
            except Exception as exc:
                # A failed migration must not stop the app booting - report and
                # continue, so one unexpected schema difference does not brick
                # an installation that is otherwise fine.
                if logger:
                    logger.warning(
                        'Migration skipped for %s.%s: %s', table, column, exc)
    finally:
        connection.close()

    if added and logger:
        logger.info('Schema migration added %d column(s): %s',
                    len(added), ', '.join(added))
    return added
