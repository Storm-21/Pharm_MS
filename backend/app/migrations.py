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
    # (Superseded by the block at the end of this list, which also declares
    # clinical_status. Kept here because ADDED_COLUMNS is applied in order and
    # an installation may already have these two; the probe skips what exists.)
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

    # Medicines: provenance and completeness.
    #
    # data_source and data_fetched_at were in this list from the start but were
    # never declared on the Medicine MODEL, so SQLAlchemy discarded them on
    # write and every imported row was indistinguishable from a curated one.
    # The model now declares all three. clinical_status records 'partial' when
    # the source supplied the product's identity but none of its clinical
    # fields, so the gap is queryable rather than buried in free text.
    ('medicines', 'data_source', 'VARCHAR(120)'),
    ('medicines', 'data_fetched_at', 'DATETIME'),
    ('medicines', 'clinical_status', 'VARCHAR(40)'),
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


# ---------------------------------------------------------------------------
# CONSTRAINTS THAT MUST BE RELAXED ON AN EXISTING DATABASE.
# ---------------------------------------------------------------------------
# medicines.name carried UNIQUE from the first release. That is wrong for a
# retail pharmacy: two manufacturers legitimately make "Paracetamol 500mg", the
# pharmacy stocks whichever it holds, and the second one must be storable. A
# pharmacy importing its own supplier list otherwise loses every line whose name
# it already stocks, silently.
#
# WHY THIS IS THE MOST DANGEROUS MIGRATION IN THIS FILE
# SQLite cannot drop a constraint. The only way is to rebuild the table: create
# a replacement, copy every row, drop the original, and rename. A pharmacy's
# live database may hold thousands of medicines and inventory rows pointing at
# them, so a failure part-way through would lose the drug catalogue.
#
# So the rebuild is written to be recoverable rather than merely correct:
#   * the whole operation runs inside ONE transaction, so a failure rolls back
#     and leaves the original table exactly as it was;
#   * foreign keys are disabled for the duration, because dropping the original
#     table would otherwise cascade into inventory and prescription items;
#   * the row count is compared before and after, and a mismatch aborts;
#   * the result is verified by asking the schema whether the old single-column
#     UNIQUE is gone and the composite one is present;
#   * it is idempotent - a database that has already been rebuilt reports
#     nothing to do and is not touched again.
#
# Each entry is (table, marker, rebuild_sql, verify_sql). 'marker' is a string
# that must appear in the CREATE TABLE statement when the migration is ALREADY
# done, so the check is a read of the real schema rather than a version guess.
REBUILT_TABLES = [
    (
        'medicines',
        # Present in the rebuilt schema, absent in the original.
        'CONSTRAINT uq_medicine_name_manufacturer',
        # The rebuild DDL is GENERATED from the model at run time rather than
        # written out by hand.
        #
        # A hand-written column list was the first attempt and it was wrong: it
        # drifted from the model, leaving out `brand_name` and `expiry_date` and
        # inventing `data_source`, so every query after the rebuild failed with
        # "no such column". A 50-column list duplicated by hand will always
        # eventually disagree with the model it is meant to mirror.
        #
        # Generating it from Medicine.__table__ means the replacement is by
        # construction in step with the model, and the only thing this file
        # states is the CONSTRAINT, which is the deliberate change.
        '__FROM_MODEL__',
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


def _rebuild_ddl_from_model(table):
    """
    Build CREATE TABLE for the replacement, straight from the SQLAlchemy model.

    Deriving the statement rather than hand-writing it is what keeps the rebuilt
    table in step with the model. The first attempt wrote the ~50 columns out by
    hand and promptly disagreed with `Medicine` - leaving out `brand_name` and
    `expiry_date` and inventing `data_source` - so every query after the rebuild
    failed with "no such column".

    SQLAlchemy's own DDL compiler is used, so types, nullability, defaults and
    the model's __table_args__ (including the composite unique constraint this
    migration exists to introduce) all come across faithfully.
    """
    from sqlalchemy.schema import CreateTable
    from app import db
    from app import models  # noqa: F401 - ensures every model is registered

    model_table = db.metadata.tables.get(table)
    if model_table is None:
        raise RuntimeError('no model registered for table %s' % table)

    statement = str(CreateTable(model_table)
                    .compile(dialect=db.engine.dialect))
    # Point it at the staging name; the final rename puts it back.
    return statement.replace('CREATE TABLE %s' % table,
                             'CREATE TABLE %s_rebuilt' % table, 1)


def _rebuild_table(connection, table, marker, logger=None):
    """
    Rebuild a table to change a constraint, without losing a single row.

    SQLite has no ALTER TABLE ... DROP CONSTRAINT, so the only route is: make a
    replacement, copy every row, drop the original, rename. That is four
    statements on live data, and the danger is a failure between them - a
    crash, a full disk, a constraint violation on copy - which would leave the
    pharmacy with no medicines table at all.

    The protections here are deliberate:

    1. **One transaction.** Everything runs inside BEGIN/COMMIT, so any failure
       rolls back to the original table complete with its rows. The connection
       is switched out of autocommit for this step only.
    2. **Foreign keys off.** Dropping the original table would otherwise fire
       ON DELETE rules and remove the inventory and prescription rows that
       point at it. Foreign keys are disabled for the duration and re-enabled
       after, which is what SQLite's own documented procedure prescribes.
    3. **Row count checked.** The rows before and after must agree. A silent
       partial copy is the failure that would otherwise go unnoticed.
    4. **Result verified against the schema.** The marker is re-read from
       sqlite_master afterwards, so success is proven rather than assumed.
    5. **Indexes recreated.** They belonged to the dropped table.

    The columns to copy are intersected at run time between the old table and
    the new one, so this works whether the source database is from the first
    release or the most recent one - a database that predates several columns
    simply copies the ones it has.
    """
    previous_isolation = connection.isolation_level
    had_foreign_keys = connection.execute('PRAGMA foreign_keys').fetchone()[0]

    before = connection.execute('SELECT COUNT(*) FROM %s' % table).fetchone()[0]
    old_columns = {row[1] for row in
                   connection.execute('PRAGMA table_info(%s)' % table).fetchall()}

    # The replacement is created first, outside the transaction, so its name is
    # free. IF NOT EXISTS guards a previous failed attempt having left one.
    connection.execute('DROP TABLE IF EXISTS %s_rebuilt' % table)
    connection.execute(_rebuild_ddl_from_model(table))
    new_columns = {row[1] for row in connection.execute(
        'PRAGMA table_info(%s_rebuilt)' % table).fetchall()}
    shared = [c for c in new_columns if c in old_columns]
    if not shared:
        raise RuntimeError('no columns in common between %s and its replacement'
                           % table)

    try:
        connection.isolation_level = ''      # defer writes; explicit BEGIN below
        connection.execute('PRAGMA foreign_keys = OFF')
        connection.execute('BEGIN')

        column_list = ', '.join(shared)
        connection.execute(
            'INSERT INTO %s_rebuilt (%s) SELECT %s FROM %s'
            % (table, column_list, column_list, table))

        copied = connection.execute(
            'SELECT COUNT(*) FROM %s_rebuilt' % table).fetchone()[0]
        if copied != before:
            raise RuntimeError(
                'row count mismatch rebuilding %s: %d before, %d copied'
                % (table, before, copied))

        connection.execute('DROP TABLE %s' % table)
        connection.execute('ALTER TABLE %s_rebuilt RENAME TO %s' % (table, table))

        # Recreate the indexes the dropped table owned. They are declared on the
        # model, so they are read from there for the same reason the columns are.
        from app import db as _db
        model_table = _db.metadata.tables.get(table)
        if model_table is not None:
            for index in model_table.indexes:
                columns = ', '.join(c.name for c in index.columns)
                connection.execute(
                    'CREATE INDEX IF NOT EXISTS %s ON %s (%s)'
                    % (index.name, table, columns))

        connection.execute('COMMIT')
    except Exception:
        connection.execute('ROLLBACK')
        # Leave no half-built table behind either.
        connection.execute('DROP TABLE IF EXISTS %s_rebuilt' % table)
        raise
    finally:
        connection.isolation_level = previous_isolation
        try:
            connection.execute('PRAGMA foreign_keys = %d' % had_foreign_keys)
        except Exception:
            pass

    # Prove it, rather than trust the statements above.
    row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
        (table,)).fetchone()
    if not row or marker not in (row[0] or ''):
        raise RuntimeError('rebuilt table %s does not carry the new constraint'
                           % table)

    after = connection.execute('SELECT COUNT(*) FROM %s' % table).fetchone()[0]
    if after != before:
        raise RuntimeError('row count changed rebuilding %s: %d then %d'
                           % (table, before, after))

    if logger:
        logger.info('Rebuilt %s: %d rows preserved, constraint relaxed',
                    table, after)


def _needs_table_rebuild(database_path):
    """
    Names of tables whose constraints still need rebuilding.

    Read from the REAL schema: sqlite_master holds the literal CREATE TABLE
    statement, so looking for the composite constraint by name is a direct
    question about what the file contains rather than a guess from a version
    number. A table that does not exist at all is not "needing a rebuild" -
    create_all() makes it in its current shape.
    """
    import sqlite3
    probe = sqlite3.connect(database_path, timeout=15)
    try:
        pending = []
        for table, marker, _steps in REBUILT_TABLES:
            row = probe.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                (table,)).fetchone()
            if row is None:
                continue                      # absent: create_all() handles it
            if marker not in (row[0] or ''):
                pending.append(table)
        return pending
    finally:
        probe.close()


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
        # A table whose constraints have not been rebuilt counts as not
        # migrated, so the fast path cannot skip past a pending rebuild.
        if _needs_table_rebuild(database_path):
            return False
        return True
    finally:
        probe.close()


def apply_migrations(db, logger=None):
    """
    Add any missing columns, and rebuild tables whose constraints changed.

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

        # --- Tables whose constraints must be relaxed -----------------------
        # See REBUILT_TABLES above for why this is the riskiest step in the
        # file. It runs LAST, so any column or table this migration adds has
        # already landed and the rebuilt table can copy it.
        for table, marker, _steps in REBUILT_TABLES:
            if not table_present(table):
                continue
            row = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                (table,)).fetchone()
            if row and marker in (row[0] or ''):
                continue                      # already rebuilt

            try:
                _rebuild_table(connection, table, marker, logger)
                added.append('%s (constraint rebuilt)' % table)
            except Exception as exc:
                # A rebuild that fails must leave the ORIGINAL table in place.
                # _rebuild_table wraps its work in a transaction for exactly
                # that reason; this catch is the second line of defence, so one
                # unexpected schema difference cannot brick an install.
                if logger:
                    logger.warning('Could not rebuild table %s: %s', table, exc)
    finally:
        connection.close()

    if added and logger:
        logger.info('Schema migration added %d column(s): %s',
                    len(added), ', '.join(added))
    return added
