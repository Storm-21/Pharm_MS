"""
Bulk medicine catalogue importer.

WHY THIS EXISTS
---------------
India markets a very large number of drug formulations (six figures of brand
variants across roughly two thousand active ingredients). There is no single
authoritative machine-readable file, and inventing entries to pad the count
would mean fabricating dosages and risk data for a clinical tool - which is not
something this project will do.

So the reference set shipped in the application is a curated, verified
*dispensing* set, and this importer is the supported route to national coverage.

WHERE TO GET REAL DATA
----------------------
Any CSV or JSON file works. Useful public sources:

  * CDSCO approved drug lists
        https://cdsco.gov.in  (Drugs > Approved Drugs)
  * Jan Aushadhi product catalogue
        https://janaushadhi.gov.in
  * NPPA ceiling price lists (good for cost_price / selling_price)
        https://nppa.gov.in
  * Your own distributor or supplier price list

USAGE
-----
    python import_medicines.py --file catalogue.csv
    python import_medicines.py --file catalogue.csv --dry-run
    python import_medicines.py --file catalogue.json --reseal

CSV must have a header row. Recognised column names (case-insensitive, spaces
and underscores ignored):

    name, generic_name, brand_name, manufacturer, salt_composition, strength,
    form, use_case, molecular_formula, side_effects, contraindications,
    drug_interactions, selling_price, cost_price, requires_prescription

Only `name`, `generic_name`, `manufacturer`, `salt_composition`, `strength`,
`form`, `use_case`, `cost_price` and `selling_price` are required by the schema;
anything missing gets a clearly-marked placeholder so the row is still usable
and obviously incomplete rather than silently wrong.

SECURITY
--------
Imported rows are sealed like any other record, so `init_db.py --verify` will
report them as INTACT. Rows are matched on `name` and skipped if already
present, so an import never overwrites the curated reference data.
"""

import argparse
import csv
import json
import sys
from datetime import datetime

from app import create_app, db
from app.models import Medicine
from app.security import apply_seal

# Maps normalised input headers -> Medicine column names.
COLUMN_ALIASES = {
    'name': 'name',
    'medicinename': 'name',
    'productname': 'name',
    'genericname': 'generic_name',
    'generic': 'generic_name',
    'brandname': 'brand_name',
    'brand': 'brand_name',
    'manufacturer': 'manufacturer',
    'manufacturername': 'manufacturer',
    'company': 'manufacturer',
    'marketedby': 'marketed_by',
    'saltcomposition': 'salt_composition',
    'composition': 'salt_composition',
    'salt': 'salt_composition',
    'molecularformula': 'molecular_formula',
    'formula': 'molecular_formula',
    'chemicalformula': 'molecular_formula',
    'molecularweight': 'chemical_formula_weight',
    'formulaweight': 'chemical_formula_weight',
    'strength': 'strength',
    'dosage': 'strength',
    'form': 'form',
    'dosageform': 'form',
    'use_case': 'use_case',
    'indication': 'use_case',
    'indications': 'use_case',
    'uses': 'use_case',
    'sideeffects': 'side_effects',
    'adverseeffects': 'side_effects',
    'contraindications': 'contraindications',
    'warnings': 'warnings',
    'druginteractions': 'drug_interactions',
    'interactions': 'drug_interactions',
    'sellingprice': 'selling_price',
    'mrp': 'selling_price',
    'price': 'selling_price',
    'costprice': 'cost_price',
    'purchaseprice': 'cost_price',
    'requiresprescription': 'requires_prescription',
    'prescriptionrequired': 'requires_prescription',
    'rx': 'requires_prescription',
    # Provenance. The fetcher writes a data_source column naming the origin, and
    # without this alias the importer fell back to the generic 'imported' - so
    # a row could be traced to "an import" but not to WHICH catalogue, which is
    # the part that matters when someone questions a figure six months later.
    'datasource': 'data_source',
    'source': 'data_source',
    'catalogue': 'data_source',
    'therapeuticclass': 'therapeutic_class',
    'category': 'therapeutic_class',
    'schedule': 'schedule_classification',
    'hsncode': 'hsn_code',
    'gstrate': 'gst_rate',
    'barcode': 'barcode',
}

REQUIRED = ['name', 'manufacturer', 'salt_composition', 'strength', 'form']

# --- The clinical fields, and why they are treated differently -------------
#
# A real government catalogue states what a product IS: its name, its salt
# composition, its strength and its dosage form. It does NOT state what the drug
# is FOR, nor its side effects or contraindications. Those are clinical
# judgements that a product list has never carried.
#
# So there are two classes of required field, and the importer treats them
# differently rather than lumping them together:
#
#   REQUIRED        the product identity. A row lacking one of these is not a
#                   record of anything and is rejected outright.
#   CLINICAL        use_case, side_effects, contraindications. These CANNOT be
#                   invented, and must not be. But their absence in the SOURCE
#                   is not a reason to refuse a genuine government product:
#                   refusing it would mean the app holds no record of a real
#                   medicine that a pharmacy may stock.
#
# The resolution is that a missing clinical field is imported as an explicit
# "not supplied" marker and the record is tagged `partial_clinical_data`. The
# row is then visibly incomplete in the app, the detail screen says so, and the
# printed prescription carries the marker rather than a plausible blank. That
# keeps both guarantees: no invented clinical data, and no real medicine missing
# (see import_medicines.py --allow-partial-clinical).
CLINICAL = ['use_case', 'side_effects', 'contraindications']

# Placeholders make an incomplete import visible rather than plausible.
PLACEHOLDERS = {
    'generic_name': 'NOT SPECIFIED',
    'manufacturer': 'NOT SPECIFIED',
    'salt_composition': 'NOT SPECIFIED',
    'strength': 'NOT SPECIFIED',
    'form': 'tablet',
    'use_case': 'Imported record - indications not supplied',
    'side_effects': 'Not supplied by the source catalogue - verify before dispensing',
    'contraindications': 'Not supplied by the source catalogue - verify before dispensing',
}


def normalise(header):
    return ''.join(ch for ch in header.lower() if ch.isalnum())


def coerce(row):
    """Map a raw dict onto Medicine columns, applying types and placeholders."""
    mapped = {}
    for raw_key, value in row.items():
        if raw_key is None:
            continue
        target = COLUMN_ALIASES.get(normalise(raw_key))
        if not target:
            continue
        if isinstance(value, str):
            value = value.strip()
        if value == '':
            continue
        mapped[target] = value

    # Record which required fields the source actually supplied BEFORE filling
    # placeholders. Otherwise a row with no manufacturer or composition would
    # be padded into looking complete and would enter the database as a
    # half-empty clinical record.
    supplied = {f for f in (REQUIRED + CLINICAL) if mapped.get(f) not in (None, '')}
    mapped['_supplied_required'] = supplied
    for field, placeholder in PLACEHOLDERS.items():
        if field not in mapped or mapped[field] in ('', None):
            mapped[field] = placeholder

    for numeric in ('cost_price', 'selling_price'):
        if numeric in mapped:
            try:
                mapped[numeric] = float(str(mapped[numeric]).replace(',', '').replace('Rs', '').replace('INR', '').strip())
            except (TypeError, ValueError):
                mapped.pop(numeric)
        mapped.setdefault(numeric, 0.0)

    if 'requires_prescription' in mapped:
        raw = str(mapped['requires_prescription']).strip().lower()
        mapped['requires_prescription'] = raw in ('1', 'true', 'yes', 'y', 'schedule h', 'rx')

    # Drop anything that is not a real column, so odd source files cannot crash.
    # The private _supplied_required marker is preserved for the caller.
    valid = {c.name for c in Medicine.__table__.columns}
    out = {k: v for k, v in mapped.items() if k in valid}
    out['_supplied_required'] = supplied
    return out


def load_rows(path):
    if path.lower().endswith('.json'):
        with open(path, encoding='utf-8') as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            data = data.get('medicines') or data.get('data') or []
        return data
    with open(path, encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def main():
    parser = argparse.ArgumentParser(description='Import a medicine catalogue into PharmMS.')
    parser.add_argument('--file', required=True, help='CSV or JSON catalogue file')
    parser.add_argument('--dry-run', action='store_true',
                        help='Report what would be imported without writing')
    parser.add_argument('--reseal', action='store_true',
                        help='Re-seal every medicine after import')
    parser.add_argument('--allow-partial-clinical', action='store_true',
                        help=('Import rows from a source that supplies the '
                              'product identity but not indications, side '
                              'effects or contraindications - a government '
                              'product list, for example. Each such record is '
                              'marked PARTIAL CLINICAL DATA so the gap is '
                              'visible rather than filled with invented text.'))
    args = parser.parse_args()

    try:
        raw_rows = load_rows(args.file)
    except Exception as exc:
        print(f"Could not read {args.file}: {exc}")
        return 1

    if not raw_rows:
        print('No rows found.')
        return 1

    app = create_app()
    added = skipped = invalid = partial = 0

    with app.app_context():
        # --- What counts as a duplicate --------------------------------------
        # A medicine is identified by its NAME AND ITS MANUFACTURER together,
        # not by name alone.
        #
        # Matching on the name alone was wrong for a retail pharmacy: two
        # manufacturers legitimately make "Paracetamol 500mg" - one at 1.20 and
        # one at 1.35 - and both belong on the shelf, because the pharmacy
        # dispenses whichever it holds. Under the old rule the second was
        # silently skipped as a duplicate, so a pharmacy importing its own
        # supplier list lost every line whose name it already stocked.
        #
        # The same drug from two manufacturers is therefore allowed and is
        # expected. What is still refused is the SAME name from the SAME
        # manufacturer, because that is a genuine repeat and re-importing a
        # sheet must not duplicate the shelf.
        def identity(record):
            return (str(record.name or '').strip().lower(),
                    str(record.manufacturer or '').strip().lower())

        existing = {identity(m) for m in Medicine.query.all()}

        for index, raw in enumerate(raw_rows, start=1):
            row = coerce(raw)
            name = row.get('name')
            if not name:
                invalid += 1
                continue

            key = (str(name).strip().lower(),
                   str(row.get('manufacturer', '')).strip().lower())
            if key in existing:
                skipped += 1
                continue

            # Validate on what the source supplied, not on what we padded in.
            supplied = row.pop('_supplied_required', set())
            missing = [f for f in REQUIRED if f not in supplied]

            # Clinical fields missing from the SOURCE are handled differently
            # from identity fields: see the CLINICAL constant for why. Either
            # they are refused (the default, strictest) or the row is imported
            # with an explicit marker and flagged as partial.
            missing_clinical = [f for f in CLINICAL if f not in supplied]
            if missing_clinical and not args.allow_partial_clinical:
                missing = missing + missing_clinical

            if missing:
                print(f"  row {index}: '{name}' skipped - source did not supply "
                      f"{', '.join(missing)}")
                invalid += 1
                continue

            if missing_clinical:
                partial += 1
                # Say so on the record itself, so the gap travels with the row
                # and is visible wherever it is read - not only in this run's
                # output, which nobody will see in six months. clinical_status
                # makes it QUERYABLE as well as readable, so the app can filter
                # "show me only records with verified clinical detail".
                marker = ('PARTIAL CLINICAL DATA: the source catalogue supplied '
                          'this product\u2019s identity but not its '
                          'indications, side effects or contraindications. '
                          'Verify against the manufacturer\u2019s labelling '
                          'before dispensing.')
                for field in missing_clinical:
                    row[field] = row.get(field) or 'Not supplied by the source'
                row['warnings'] = (marker if not row.get('warnings')
                                   else row['warnings'] + ' ' + marker)
                row['clinical_status'] = 'partial'
            else:
                row.setdefault('clinical_status', 'complete')

            # Provenance is recorded on every imported row, so an imported
            # medicine is never mistaken for one of the curated, verified set.
            # The source's own name for itself is kept when the file supplies
            # one, because "imported" is not traceable to a catalogue.
            row.setdefault('data_source', 'imported')
            row['data_fetched_at'] = datetime.utcnow()

            if args.dry_run:
                added += 1
                existing.add(key)
                continue

            medicine = Medicine(**row)
            apply_seal(medicine)
            db.session.add(medicine)
            existing.add(key)
            added += 1

        if not args.dry_run:
            db.session.commit()

            if args.reseal:
                for medicine in Medicine.query.all():
                    apply_seal(medicine)
                db.session.commit()
                print('  re-sealed all medicine records')

    print('')
    print(f"  source rows      : {len(raw_rows)}")
    print(f"  {'would add' if args.dry_run else 'added':<17}: {added}")
    print(f"  already present  : {skipped}")
    print(f"  unusable rows    : {invalid}")
    if partial:
        # Stated separately and prominently. An imported row whose clinical
        # fields came from a partial source must not be counted silently among
        # the additions, because "added 324" would read as "324 fully detailed
        # medicines" when a number of them carry only their identity.
        print(f"  PARTIAL CLINICAL : {partial} of the added rows carry no "
              f"indications, side effects or contraindications")
        print('                     from the source, and are marked as such.')
    if args.dry_run:
        print('')
        print('  Dry run - nothing was written.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
