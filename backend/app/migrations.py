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
    with engine.connect() as connection:
        for table, column, sql_type in ADDED_COLUMNS:
            if not _table_exists(connection, table):
                # create_all() has not made this table yet (fresh database);
                # the model definition already includes the column.
                continue
            if column in _existing_columns(connection, table):
                continue
            statement = 'ALTER TABLE %s ADD COLUMN %s %s' % (table, column, sql_type)
            try:
                connection.execute(sqlalchemy.text(statement))
                connection.commit()
                added.append('%s.%s' % (table, column))
            except Exception as exc:
                # A failed migration must not stop the app booting - report and
                # continue, so one unexpected schema difference does not brick
                # an installation that is otherwise fine.
                if logger:
                    logger.warning(
                        'Migration skipped for %s.%s: %s', table, column, exc)
    if added and logger:
        logger.info('Schema migration added %d column(s): %s',
                    len(added), ', '.join(added))
    return added
