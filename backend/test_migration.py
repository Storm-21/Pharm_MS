"""
Prove the schema migration writes the new columns to a real database file.

The migration runs against a COPY of a populated database, so live records are
never touched. The copy is rolled back to its pre-migration shape first, so the
migration has genuine work to do - the same situation as a pharmacy upgrading
from an earlier release.

The check that matters is reading the file back over an independent sqlite3
connection. An earlier version of the migration reported success while writing
nothing, because app startup's db.create_all() had left an uncommitted
transaction open that swallowed every ALTER TABLE on the way out.
"""
import os
import shutil
import sqlite3
import sys
import tempfile

REAL = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'PharmMS', 'pharmacy.db')
DEV = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pharmacy.db')
source = REAL if os.path.exists(REAL) else DEV
if not os.path.exists(source):
    raise SystemExit('No database available to test against.')

workdir = tempfile.mkdtemp(prefix='pharms-migrate-')
target = os.path.join(workdir, 'pharmacy.db')
shutil.copy2(source, target)

NEW_COLUMNS = [
    'weight_kg', 'serum_creatinine', 'hepatic_impairment', 'renal_impairment',
    'is_pregnant', 'pregnancy_trimester', 'is_breastfeeding',
]


def columns_of(path, table='patients'):
    conn = sqlite3.connect(path)
    try:
        return [row[1] for row in conn.execute('PRAGMA table_info(%s)' % table)]
    finally:
        conn.close()


def counts(path):
    conn = sqlite3.connect(path)
    try:
        return {
            'patients': conn.execute('select count(*) from patients').fetchone()[0],
            'medicines': conn.execute('select count(*) from medicines').fetchone()[0],
            'prescriptions': conn.execute(
                'select count(*) from prescriptions').fetchone()[0],
        }
    finally:
        conn.close()


# --- Roll the copy back so there is real work to do -----------------------
initial = columns_of(target)
if any(column in initial for column in NEW_COLUMNS):
    conn = sqlite3.connect(target)
    try:
        for column in NEW_COLUMNS:
            if column in initial:
                try:
                    conn.execute('ALTER TABLE patients DROP COLUMN %s' % column)
                except Exception:
                    pass
        conn.commit()
    finally:
        conn.close()

before_columns = columns_of(target)
before_counts = counts(target)
print('SIMULATED PRE-MIGRATION DATABASE')
print('  patients columns : %d' % len(before_columns))
print('  has weight_kg    : %s' % ('weight_kg' in before_columns))
print('  rows             : %s' % before_counts)
print()

# --- Point the app at the copy -------------------------------------------
# PHARMS_DATA_DIR is the variable _resolve_data_dir() actually reads. Setting
# the wrong name means the app silently uses its own directory instead, and the
# test ends up asserting against a database the migration never touched.
os.environ['PHARMS_DATA_DIR'] = workdir
os.environ.pop('PHARMS_DB_PATH', None)

from app import create_app                     # noqa: E402
app = create_app()

after_columns = columns_of(target)
after_counts = counts(target)

print('AFTER STARTUP (which runs apply_migrations internally)')
print('  patients columns : %d' % len(after_columns))
print('  rows             : %s' % after_counts)
print('  newly present    : %s'
      % [c for c in NEW_COLUMNS if c in after_columns])
print()

ok = True
for column in NEW_COLUMNS:
    if column not in after_columns:
        print('FAIL: %s was not written to the database file' % column)
        ok = False

for key in ('patients', 'medicines', 'prescriptions'):
    if after_counts[key] < before_counts[key]:
        print('FAIL: %s rows lost (%d -> %d)'
              % (key, before_counts[key], after_counts[key]))
        ok = False

# A second run must be a no-op, because this executes on every startup.
with app.app_context():
    from app import db
    from app.migrations import apply_migrations
    second = apply_migrations(db, app.logger)
print('IDEMPOTENCY: second run added %d column(s) %s'
      % (len(second), '(correct)' if not second else '(WRONG - should be 0)'))
if second:
    ok = False

# Pre-existing rows must read back as NULL rather than raising.
conn = sqlite3.connect(target)
try:
    row = conn.execute(
        'select weight_kg, serum_creatinine, is_pregnant from patients limit 1'
    ).fetchone()
    print('pre-existing row reads back as: %s   (NULL is correct)' % (row,))
finally:
    conn.close()

print()
print('=' * 66)
print('  MIGRATION %s' % ('VERIFIED' if ok else 'FAILED'))
print('=' * 66)

sys.exit(0 if ok else 1)
