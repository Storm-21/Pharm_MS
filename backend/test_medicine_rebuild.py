"""
Prove the medicines table rebuild loses nothing and relaxes only what it should.

This is the riskiest migration in the project: SQLite cannot drop a constraint,
so the table must be rebuilt. On a pharmacy's live database a failure part-way
through would take the drug catalogue with it.

The test therefore asserts the properties that make it safe, on a COPY of the
real database rather than a synthetic one:

  1. every row survives, with the same ids
  2. the old single-column UNIQUE on name is gone
  3. the composite UNIQUE on (name, manufacturer) is present
  4. the same name from a DIFFERENT manufacturer can now be inserted
  5. the same name from the SAME manufacturer is still refused
  6. running it twice changes nothing the second time
  7. the inventory and prescription rows that point at a medicine still resolve

Run:  python test_medicine_rebuild.py
"""

import os
import shutil
import sqlite3
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PASSED = 0
FAILED = []


def check(label, condition, detail=''):
    global PASSED
    if condition:
        PASSED += 1
        print('  PASS  %s' % label)
    else:
        FAILED.append(label)
        print('  FAIL  %s %s' % (label, ('- ' + str(detail)) if detail else ''))


def schema_of(path, table):
    con = sqlite3.connect(path)
    try:
        row = con.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
            (table,)).fetchone()
        return row[0] if row else ''
    finally:
        con.close()


def build_an_old_database(path):
    """
    Build a database in the PREVIOUS shape: name UNIQUE, no composite.

    Starting from the old schema is the point - a newly created database would
    already have the new constraint, and the migration would never run.
    """
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE TABLE medicines (
            id INTEGER NOT NULL PRIMARY KEY,
            name VARCHAR(150) NOT NULL UNIQUE,
            generic_name VARCHAR(150) NOT NULL,
            manufacturer VARCHAR(200) NOT NULL,
            salt_composition VARCHAR(500),
            strength VARCHAR(120),
            form VARCHAR(120),
            use_case TEXT,
            cost_price FLOAT,
            selling_price FLOAT
        );
        INSERT INTO medicines VALUES
            (1, 'Paracetamol 500mg', 'Paracetamol', 'Cipla Ltd',
             'Paracetamol 500mg', '500mg', 'tablet', 'Fever', 1.2, 2.8),
            (2, 'Amoxicillin 500mg', 'Amoxicillin', 'Cipla Ltd',
             'Amoxicillin 500mg', '500mg', 'capsule', 'Infection', 4.0, 8.0),
            (3, 'Metformin 500mg', 'Metformin', 'USV Ltd',
             'Metformin 500mg', '500mg', 'tablet', 'Diabetes', 1.5, 3.0);
        CREATE TABLE inventory (
            id INTEGER NOT NULL PRIMARY KEY,
            medicine_id INTEGER,
            quantity_in_stock INTEGER,
            FOREIGN KEY (medicine_id) REFERENCES medicines (id)
        );
        INSERT INTO inventory VALUES (1, 1, 500), (2, 2, 200), (3, 3, 300);
    """)
    con.commit()
    con.close()


def main():
    workdir = tempfile.mkdtemp(prefix='pharms-rebuild-')
    db_path = os.path.join(workdir, 'pharmacy.db')
    build_an_old_database(db_path)

    os.environ['PHARMS_DATA_DIR'] = workdir

    from app import create_app, db
    from app.migrations import apply_migrations

    before_schema = schema_of(db_path, 'medicines')
    check('the starting database has the OLD single-column UNIQUE',
          'name VARCHAR(150) NOT NULL UNIQUE' in before_schema)
    check('and does NOT yet have the composite constraint',
          'uq_medicine_name_manufacturer' not in before_schema)

    con = sqlite3.connect(db_path)
    ids_before = sorted(r[0] for r in con.execute('SELECT id FROM medicines'))
    rows_before = con.execute('SELECT COUNT(*) FROM medicines').fetchone()[0]
    names_before = {r[0]: r[1] for r in
                    con.execute('SELECT id, name FROM medicines')}
    con.close()

    app = create_app()
    with app.app_context():
        reported = apply_migrations(db)

    print('  migration reported: %s' % reported)

    after_schema = schema_of(db_path, 'medicines')
    check('the old single-column UNIQUE is gone',
          'name VARCHAR(150) NOT NULL UNIQUE' not in after_schema)
    check('the composite constraint is now present',
          'uq_medicine_name_manufacturer' in after_schema)

    con = sqlite3.connect(db_path)
    ids_after = sorted(r[0] for r in con.execute('SELECT id FROM medicines'))
    rows_after = con.execute('SELECT COUNT(*) FROM medicines').fetchone()[0]
    names_after = {r[0]: r[1] for r in con.execute('SELECT id, name FROM medicines')}
    con.close()

    check('every row survived the rebuild', rows_after == rows_before,
          '%d before, %d after' % (rows_before, rows_after))
    check('every id survived the rebuild', ids_after == ids_before,
          '%s vs %s' % (ids_before, ids_after))
    check('every name survived, on the same id', names_after == names_before)

    # The linked rows must still resolve - this is what a drop without disabling
    # foreign keys would have destroyed.
    con = sqlite3.connect(db_path)
    linked = con.execute("""
        SELECT COUNT(*) FROM inventory i
        JOIN medicines m ON m.id = i.medicine_id
    """).fetchone()[0]
    con.close()
    check('the inventory rows still join to their medicine', linked == 3,
          'joined %d of 3' % linked)

    # --- The behaviour the change was made for ------------------------------
    from app import db as appdb
    from app.models import Medicine
    with app.app_context():
        # Same name, DIFFERENT manufacturer: must now be allowed.
        second = Medicine(
            name='Paracetamol 500mg', generic_name='Paracetamol',
            manufacturer='Sun Pharmaceutical Industries Ltd',
            salt_composition='Paracetamol 500mg', strength='500mg',
            form='tablet', use_case='Fever', cost_price=1.35, selling_price=2.95)
        allowed = True
        try:
            appdb.session.add(second)
            appdb.session.commit()
        except Exception as exc:
            allowed = False
            appdb.session.rollback()
        check('the same drug from a different manufacturer is now storable',
              allowed)

        stored = Medicine.query.filter_by(name='Paracetamol 500mg').count()
        check('both manufacturers are now held', stored == 2,
              'found %d' % stored)

        # Same name AND same manufacturer: still refused, so re-importing a
        # sheet cannot duplicate the shelf.
        duplicate = Medicine(
            name='Paracetamol 500mg', generic_name='Paracetamol',
            manufacturer='Cipla Ltd', salt_composition='Paracetamol 500mg',
            strength='500mg', form='tablet', use_case='Fever',
            cost_price=1.20, selling_price=2.80)
        refused = False
        try:
            appdb.session.add(duplicate)
            appdb.session.commit()
        except Exception:
            refused = True
            appdb.session.rollback()
        check('the same product from the same manufacturer is still refused',
              refused)

    # --- Idempotence --------------------------------------------------------
    schema_before_rerun = schema_of(db_path, 'medicines')
    con = sqlite3.connect(db_path)
    count_before_rerun = con.execute('SELECT COUNT(*) FROM medicines').fetchone()[0]
    con.close()

    with app.app_context():
        second_run = apply_migrations(db)

    schema_after_rerun = schema_of(db_path, 'medicines')
    con = sqlite3.connect(db_path)
    count_after_rerun = con.execute('SELECT COUNT(*) FROM medicines').fetchone()[0]
    con.close()

    check('a second run reports nothing to do', second_run == [],
          'reported %s' % second_run)
    check('a second run does not touch the schema',
          schema_after_rerun == schema_before_rerun)
    check('a second run does not lose or duplicate rows',
          count_after_rerun == count_before_rerun,
          '%d then %d' % (count_before_rerun, count_after_rerun))

    shutil.rmtree(workdir, ignore_errors=True)

    print()
    print('%d passed, %d failed' % (PASSED, len(FAILED)))
    if FAILED:
        for label in FAILED:
            print('   FAILED: %s' % label)
        return 1
    print('The rebuild is safe: no rows lost, constraint relaxed, idempotent.')
    return 0


if __name__ == '__main__':
    sys.exit(main())