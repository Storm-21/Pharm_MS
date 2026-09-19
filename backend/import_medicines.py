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
    'therapeuticclass': 'therapeutic_class',
    'category': 'therapeutic_class',
    'schedule': 'schedule_classification',
    'hsncode': 'hsn_code',
    'gstrate': 'gst_rate',
    'barcode': 'barcode',
}

REQUIRED = ['name', 'generic_name', 'manufacturer', 'salt_composition',
            'strength', 'form', 'use_case']

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
    supplied = {f for f in REQUIRED if mapped.get(f) not in (None, '')}
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
    added = skipped = invalid = 0

    with app.app_context():
        existing = {m.name for m in Medicine.query.all()}

        for index, raw in enumerate(raw_rows, start=1):
            row = coerce(raw)
            name = row.get('name')
            if not name:
                invalid += 1
                continue
            if name in existing:
                skipped += 1
                continue

            # Validate on what the source supplied, not on what we padded in.
            supplied = row.pop('_supplied_required', set())
            missing = [f for f in REQUIRED if f not in supplied]
            if missing:
                print(f"  row {index}: '{name}' skipped - source did not supply "
                      f"{', '.join(missing)}")
                invalid += 1
                continue

            if args.dry_run:
                added += 1
                continue

            medicine = Medicine(**row)
            apply_seal(medicine)
            db.session.add(medicine)
            existing.add(name)
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
    if args.dry_run:
        print('')
        print('  Dry run - nothing was written.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
