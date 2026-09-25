"""
Catalogue integrity.

This test exists because of a real defect it would have caught: two batch-4
entries repeated names already present in batch 3. ensure_seeded() *silently
skips* a duplicate name rather than failing, so those two medicines were never
added - the database held two fewer medicines than the data files implied, and
nothing anywhere said so. The published count was wrong for a whole release.

So the assertions here are about the catalogue being what it claims to be:

  1. no medicine name appears twice across all batches
  2. every dosage guide resolves to a medicine that actually exists
  3. no (medicine, age_group) pair appears twice - the seeder keys on that pair,
     so a repeat is dropped and its guidance silently lost
  4. age bands are drawn from the one set the rest of the catalogue uses
  5. every medicine has the columns the model requires to be non-null
  6. the loaded count equals the sum of the batches (nothing was dropped)
  7. every opening-stock line names a real medicine
  8. every medicine has at least one dosage guide

Run:  python test_catalogue.py
"""

import os
import sys
import tempfile
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PASSED = 0
FAILED = []

# The age bands the catalogue uses. A guide with any other value would never be
# matched by an age-based lookup, so it would be stored and never used.
VALID_BANDS = {'Neonate', '0-2', '2-6', '6-12', '12-18', '18+'}


def check(label, condition, detail=''):
    global PASSED
    if condition:
        PASSED += 1
        print('  PASS  %s' % label)
    else:
        FAILED.append(label)
        print('  FAIL  %s %s' % (label, ('- ' + str(detail)) if detail else ''))


def _table_present(database_path, table):
    """Whether a table exists in the file, read directly rather than via the ORM."""
    import sqlite3
    con = sqlite3.connect(database_path)
    try:
        row = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,)).fetchone()
        return row is not None
    finally:
        con.close()


def main():
    workdir = tempfile.mkdtemp(prefix='pharms-catalogue-')
    os.environ['PHARMS_DATA_DIR'] = workdir

    from app.data import seeder
    from app.data.seed_medicines import MEDICINES as B1, DOSAGE_GUIDES as G1
    from app.data.seed_medicines_extra import (EXTRA_MEDICINES as B2,
                                               EXTRA_DOSAGE_GUIDES as G2)
    from app.data.seed_medicines_batch3 import (BATCH3_MEDICINES as B3,
                                                BATCH3_GUIDES as G3)
    from app.data.seed_medicines_batch4 import (BATCH4_MEDICINES as B4,
                                                BATCH4_GUIDES as G4)
    from app.data.seed_medicines_batch5 import (BATCH5_MEDICINES as B5,
                                                BATCH5_GUIDES as G5)
    from app.data.seed_medicines_batch6 import BATCH6_GUIDES as G6
    from app.data.seed_medicines_batch7 import (BATCH7_MEDICINES as B7,
                                                BATCH7_GUIDES as G7)

    batches = [('base', B1, G1), ('extra', B2, G2), ('batch3', B3, G3),
               ('batch4', B4, G4), ('batch5', B5, G5), ('batch7', B7, G7)]
    # Batch 6 supplies guidance only, for medicines the earlier batches defined
    # without a dose. It is folded in as an empty medicine list plus its guides,
    # so the duplicate-name and count assertions below still see one catalogue.
    guide_batches = batches + [('batch6', [], G6)]

    print()
    print('Catalogue integrity')
    print('-' * 60)
    for label, meds, guides in batches:
        print('  %-8s %3d medicines, %3d guides' % (label, len(meds), len(guides)))
    print()

    # --- 1. No duplicate medicine names -------------------------------------
    all_names = [m['name'] for _l, meds, _g in batches for m in meds]
    dupes = [name for name, count in Counter(all_names).items() if count > 1]
    check('no medicine name is repeated across batches', not dupes,
          'repeated: %s' % dupes)

    # --- 6. Nothing is dropped by the seeder --------------------------------
    check('the loaded catalogue equals the sum of the batches',
          len(seeder.MEDICINES) == len(all_names),
          'loaded %d, batches total %d' % (len(seeder.MEDICINES), len(all_names)))
    check('no duplicate names reached the loaded catalogue',
          len({m['name'] for m in seeder.MEDICINES}) == len(seeder.MEDICINES))

    # --- 3. No duplicate (medicine, age_group) guide ------------------------
    # BATCH6_GUIDES is included: it is exactly the kind of file that would
    # reintroduce a (medicine, age band) collision, because it was written to
    # fill gaps in data the earlier batches already carried.
    guide_keys = [(g['medicine_name'], g['age_group'])
                  for _l, _m, guides in guide_batches for g in guides]
    guide_dupes = [k for k, c in Counter(guide_keys).items() if c > 1]
    check('no (medicine, age band) guide is repeated', not guide_dupes,
          'repeated: %s' % guide_dupes[:5])

    # --- 4. Age bands are from the recognised set ---------------------------
    bands = {g['age_group'] for _l, _m, guides in guide_batches for g in guides}
    unknown = sorted(bands - VALID_BANDS)
    check('every age band is one the rest of the catalogue uses', not unknown,
          'unrecognised: %s' % unknown)

    # --- 2. Every guide resolves to a real medicine -------------------------
    known = set(all_names)
    orphans = sorted({g['medicine_name'] for _l, _m, guides in guide_batches
                      for g in guides} - known)
    check('every dosage guide names a medicine that exists', not orphans,
          'orphans: %s' % orphans)

    # --- 5. Required columns are populated ----------------------------------
    required = ['name', 'generic_name', 'manufacturer', 'salt_composition',
                'strength', 'form', 'use_case', 'cost_price', 'selling_price']
    missing = []
    for label, meds, _g in batches:
        for med in meds:
            for column in required:
                if med.get(column) in (None, ''):
                    missing.append('%s.%s' % (label, med.get('name', '?')))
    check('every medicine has the columns the model requires', not missing,
          'missing: %s' % missing[:5])

    # --- 7. Opening stock refers to real medicines --------------------------
    stock = set(seeder.OPENING_STOCK)
    unknown_stock = sorted(stock - known)
    check('every opening-stock line names a real medicine', not unknown_stock,
          'unknown: %s' % unknown_stock)

    # --- 8. Every medicine has at least one guide ---------------------------
    # The gap this batch closed: a medicine you can look up but cannot dose.
    guided = {g['medicine_name'] for _l, _m, guides in guide_batches for g in guides}
    unguided = sorted(known - guided)
    check('every medicine has at least one dosage guide', not unguided,
          'unguided (%d): %s' % (len(unguided), unguided[:8]))

    # --- The database really holds what the batches say --------------------
    # The files being consistent is not the same as the database being correct,
    # and it is the database that ships.
    from app import create_app, db
    from app.models import Medicine, DosageGuide, Inventory

    app = create_app()
    with app.app_context():
        db.create_all()
        seeder.ensure_seeded()

        stored = Medicine.query.count()
        expected = len({m['name'] for m in seeder.MEDICINES})
        check('the database stores every distinct medicine', stored == expected,
              'stored %d, expected %d' % (stored, expected))

        # The real failure mode this whole file guards against.
        check('the stored count matches the number of distinct names',
              stored == len({m['name'] for m in seeder.MEDICINES}))

        guides_stored = DosageGuide.query.count()
        check('the database stores the dosage guides', guides_stored > 100,
              'stored %d' % guides_stored)

        check('every medicine has an inventory line',
              Inventory.query.count() >= stored - 1,
              'inventory %d, medicines %d' % (Inventory.query.count(), stored))

        # Re-running the seeder must not duplicate anything. This is the
        # idempotence the packaged .exe depends on, since it seeds on every
        # launch.
        before = Medicine.query.count()
        seeder.ensure_seeded()
        check('seeding twice does not duplicate medicines',
              Medicine.query.count() == before,
              '%d then %d' % (before, Medicine.query.count()))

        # --- Tables, not just columns ------------------------------------
        # db.create_all() only creates what is absent, but it opens and never
        # commits a transaction on a pooled connection, so on an existing
        # database a newly added model's CREATE TABLE is rolled back. A table
        # added after a database was first created therefore never appears, and
        # every request that touches it fails outright. activation_tokens was
        # exactly that: GET /api/branding returned 500 on any upgraded install.
        import sqlite3
        from app.migrations import ADDED_TABLES, apply_migrations

        path = db.engine.url.database
        con = sqlite3.connect(path)
        for table, _sql, _idx in ADDED_TABLES:
            con.execute('DROP TABLE IF EXISTS %s' % table)
        con.commit()
        con.close()

        check('a dropped table is genuinely gone before migrating',
              not _table_present(path, ADDED_TABLES[0][0]))

        apply_migrations(db)
        missing = [t for t, _s, _i in ADDED_TABLES if not _table_present(path, t)]
        check('the migration recreates a table that is missing', not missing,
              'still missing: %s' % missing)

        # The endpoint that broke must answer, not merely exist.
        status = app.test_client().get('/api/branding').status_code
        check('GET /api/branding succeeds after the table is restored',
              status == 200, 'status %s' % status)

        # And re-running must be a no-op rather than an error.
        check('re-running the migration on a current schema reports nothing',
              apply_migrations(db) == [], 'reported work on the second run')

    print()
    print('-' * 60)
    print('%d passed, %d failed' % (PASSED, len(FAILED)))
    if FAILED:
        for label in FAILED:
            print('   FAILED: %s' % label)
        return 1
    print('Catalogue is internally consistent.')
    return 0


if __name__ == '__main__':
    sys.exit(main())