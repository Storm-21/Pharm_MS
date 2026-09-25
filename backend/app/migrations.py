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
    ('patients', 'height_cm', 'FLOAT'),
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

    # Medicine images (v2.2). Stored as a file NAME inside the data directory's
    # medicines/ folder, never an absolute path - the data directory differs per
    # machine and per user, so a stored path would break on the next PC and would
    # be a traversal vector when used to serve the file.
    ('medicines', 'image_filename', 'VARCHAR(200)'),
    ('medicines', 'image_source', 'VARCHAR(40)'),
    ('medicines', 'image_attribution', 'VARCHAR(300)'),
    ('medicines', 'image_fetched_at', 'DATETIME'),

    # Prescription items: the dose time-of-day pattern (morning/afternoon/night)
    # and the dispensed quantity, which the printed prescription shows as the
    # M/A/N dosing dots and the receipt uses as the billed line.
    ('prescription_items', 'dose_schedule', 'VARCHAR(40)'),
    ('prescription_items', 'dispensed_units', 'INTEGER'),
]


# Tables that must exist for the app to run, created on a database that predates
# them.
#
# WHY THIS EXISTS: db.create_all() only creates tables that are *absent*, and it
# runs before this migration - so in principle a new model's table would be
# created for free. In practice it is not, because create_all() leaves an
# uncommitted transaction open on a pooled connection (the same defect described
# at length in migrate() below), so the CREATE TABLE is rolled back and the file
# never gains the table. The result was that "activation_tokens" was absent from
# any database created before the model was added, and every request that touched
# it - including GET /api/branding - failed with
#     sqlite3.OperationalError: no such table: activation_tokens
# so the splash screen and the branding page both 500'd on an upgraded install.
#
# These are created over the dedicated autocommit connection for the same reason
# the ALTER TABLEs are, and the DDL is written out in full rather than derived
# from the models, so a future change to a model cannot silently alter the
# shape of an existing database.
ADDED_TABLES = [
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
        'CREATE UNIQUE INDEX IF NOT EXISTS ix_activation_tokens_body '
        'ON activation_tokens (body)',
    ),
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


def _all_columns_present(database_path):
    """True only when every (table, column) in ADDED_COLUMNS already exists.

    A table that is absent counts as NOT migrated, so a brand-new database
    still runs the full path (where the table check safely skips it).

    The tables in ADDED_TABLES are probed too. Without that the fast path would
    report "nothing to do" on a database that is missing one of them and return
    early, which is exactly how a missing activation_tokens table went unnoticed
    on an upgraded install.
    """
    import sqlite3
    probe = sqlite3.connect(database_path, timeout=15)
    try:
        def table_exists(name):
            row = probe.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (name,)).fetchone()
            return row is not None

        present = {}
        for table, column, _type in ADDED_COLUMNS:
            if table not in present:
                rows = probe.execute('PRAGMA table_info(%s)' % table).fetchall()
                # An empty result means either "no such table" or "table with
                # no columns" - both mean there is nothing to skip.
                present[table] = {row[1] for row in rows}
            if column not in present[table]:
                return False
        for table, _create_sql, _index_sql in ADDED_TABLES:
            if not table_exists(table):
                return False
        return True
    finally:
        probe.close()


def apply_migrations(db, logger=None):
    """
    Add any missing columns. Safe to call on every startup.

    Returns a list of 'table.column' strings that were added.
    """
    added = []
    engine = db.engine
    # --- Fast path ---------------------------------------------------------
    # Every startup calls this, so once the schema is current the work should
    # be skipped cheaply.
    #
    # The probe reads the REAL schema, NOT SQLAlchemy's model metadata. An
    # earlier version used sqlalchemy.inspect(engine), which consults the model
    # definition - and the model always declares these columns, so the probe
    # concluded the work was already done and returned immediately.
    #
    # It also checks EVERY entry rather than only the last one. Probing just
    # the final column is wrong: when a new column is inserted into the middle
    # of ADDED_COLUMNS, the last column is still present in an already-migrated
    # database, so the probe reported "nothing to do" and the new column was
    # never created - the app then failed at the first query with
    # "table patients has no column named height_cm". Checking all of them is
    # still cheap (a handful of PRAGMA reads) and cannot miss an insertion.
    try:
        import sqlite3
        probe_path = _database_path(engine)
        if probe_path and _all_columns_present(probe_path):
            return []
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

        # --- Whole tables that predate the current models -------------------
        # Checked before the columns above would ever help: a column cannot be
        # added to a table that does not exist, and the column loop skips such
        # an entry silently (``known[table] is None``), so a missing table was
        # formerly invisible to this migration.
        for table, create_sql, index_sql in ADDED_TABLES:
            if table_present(table):
                continue
            try:
                connection.execute(create_sql)
                if index_sql:
                    connection.execute(index_sql)
                added.append('%s (table)' % table)
            except Exception as exc:
                if logger:
                    logger.warning('Could not create table %s: %s', table, exc)
    finally:
        connection.close()

    if added and logger:
        logger.info('Schema migration added %d column(s): %s',
                    len(added), ', '.join(added))
    return added
