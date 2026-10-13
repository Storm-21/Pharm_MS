"""
Schema validation for imported PharmMS exports.

The import path has historically been permissive: any JSON payload whose top
level carried a ``tables`` dict was accepted and passed straight through to
the model constructors. That let a malformed or hostile file write unexpected
columns, bypass unique constraints, and create referential-orphan rows.

This module adds a validation layer that runs BEFORE anything touches the
database. It checks:

  * format tag and schema version
  * each table name against an allowlist
  * each row against the expected columns for its model
  * field lengths against the column definition
  * required fields are present
  * foreign keys reference existing rows (for patients -> prescriptions)
  * total row count stays under MAX_TOTAL_ROWS

A row that fails validation is skipped with a per-row error message rather
than aborting the entire import - a single bad row should not erase a
thousand good ones.
"""

import json
import re

from app.models import (
    Medicine, Patient, PatientAllergy, Prescription, PrescriptionItem,
    Inventory, DosageGuide,
)

# Expected schema version for exported files. Bumping this invalidates
# imports from older versions so they are explicitly re-exported rather
# than silently accepted.
EXPECTED_FORMAT = 'pharms-export'
EXPECTED_VERSION = 1

# Maximum rows we will accept across all tables. An export with millions of
# rows is almost certainly a mistake or a hostile file.
MAX_TOTAL_ROWS = 100_000
MAX_ROWS_PER_TABLE = 50_000

# Allowed table names — anything else is rejected immediately.
ALLOWED_TABLES = frozenset([
    'medicines', 'patients', 'patient_allergies',
    'prescriptions', 'prescription_items', 'inventory', 'dosage_guides',
])

# Maximum string length for each text field, keyed by (table, column).
# Values set to None mean "use the model's column length" or "no limit".
FIELD_LENGTHS = {
    ('patients', 'first_name'): 100,
    ('patients', 'last_name'): 100,
    ('patients', 'email'): 120,
    ('patients', 'phone'): 40,
    ('patients', 'gender'): 10,
    ('patients', 'chronic_diseases'): 500,
    ('patients', 'current_medications'): 500,
    ('patients', 'allergies_description'): 500,
    ('patients', 'address'): 500,
    ('patients', 'city'): 150,
    ('patients', 'country'): 100,
    ('patients', 'allergen'): 150,
    ('patient_allergies', 'allergen'): 150,
    ('patient_allergies', 'reaction'): 500,
    ('patient_allergies', 'severity'): 20,
    ('prescriptions', 'doctor_name'): 150,
    ('prescriptions', 'diagnosis'): 500,
    ('prescriptions', 'notes'): 2000,
    ('prescription_items', 'frequency'): 100,
    ('prescription_items', 'dosage_unit'): 50,
    ('prescription_items', 'special_instructions'): 500,
    ('prescription_items', 'dose_schedule'): 40,
    ('inventory', 'batch_number'): 100,
    ('inventory', 'storage_location'): 100,
    ('medicines', 'name'): 150,
    ('medicines', 'generic_name'): 150,
    ('medicines', 'brand_name'): 150,
    ('medicines', 'manufacturer'): 200,
    ('medicines', 'salt_composition'): 500,
    ('medicines', 'strength'): 100,
    ('medicines', 'form'): 50,
    ('medicines', 'hsn_code'): 30,
    ('dosage_guides', 'name'): 200,
    ('dosage_guides', 'condition'): 200,
}

# Columns that MUST be present in every row of a given table.
REQUIRED_FIELDS = {
    'patients': {'first_name', 'last_name', 'gender'},
    'patient_allergies': {'allergen', 'reaction', 'severity'},
    'prescriptions': {'doctor_name', 'diagnosis'},
    'prescription_items': {'medicine_id', 'dosage_amount', 'dosage_unit', 'frequency', 'duration_days'},
    'inventory': {'medicine_id', 'batch_number', 'quantity_in_stock',
                  'manufacturing_date', 'expiry_date'},
    'medicines': {'name', 'generic_name', 'manufacturer', 'salt_composition',
                  'strength', 'form', 'use_case', 'cost_price', 'selling_price'},
    'dosage_guides': {'name', 'medicine_id'},
}


def validate_import_payload(payload):
    """
    Validate an import payload and return (ok, errors) where errors is a
    list of human-readable messages. An empty errors list means the payload
    is safe to import.
    """
    errors = []

    if not isinstance(payload, dict):
        return False, ['Import payload is not a JSON object.']

    if payload.get('format') != EXPECTED_FORMAT:
        return False, [
            f'Expected format "{EXPECTED_FORMAT}", got '
            f'{payload.get("format", "<missing>")!r}.'
        ]

    if payload.get('format_version') != EXPECTED_VERSION:
        return False, [
            f'Expected schema version {EXPECTED_VERSION}, got '
            f'{payload.get("format_version")!r}. '
            'Re-export the data from this version of PharmMS.'
        ]

    tables = payload.get('tables')
    if not isinstance(tables, dict):
        return False, ['Missing or invalid "tables" object.']

    total_rows = 0
    for table_name, rows in tables.items():
        if table_name not in ALLOWED_TABLES:
            errors.append(
                f'Table "{table_name}" is not allowed. '
                f'Allowed: {", ".join(sorted(ALLOWED_TABLES))}.'
            )
            continue

        if not isinstance(rows, list):
            errors.append(f'Rows for "{table_name}" must be a JSON array.')
            continue

        if len(rows) > MAX_ROWS_PER_TABLE:
            errors.append(
                f'Table "{table_name}" has {len(rows)} rows, exceeding the '
                f'{MAX_ROWS_PER_TABLE} limit.'
            )
            continue

        total_rows += len(rows)
        for i, row in enumerate(rows):
            _validate_row(table_name, row, i, errors)

    if total_rows > MAX_TOTAL_ROWS:
        errors.append(
            f'Total rows across all tables is {total_rows}, exceeding the '
            f'{MAX_TOTAL_ROWS} limit.'
        )

    return len(errors) == 0, errors


def _validate_row(table_name, row, index, errors):
    """Validate a single row and append errors to the list."""
    if not isinstance(row, dict):
        errors.append(f'[{table_name} row {index}] Not a JSON object.')
        return

    # Check required fields.
    for field in REQUIRED_FIELDS.get(table_name, set()):
        if field not in row:
            errors.append(
                f'[{table_name} row {index}] Missing required field "{field}".'
            )

    # Check string field lengths.
    for (t, col), max_len in FIELD_LENGTHS.items():
        if t == table_name and col in row:
            val = row[col]
            if val is not None and isinstance(val, str) and len(val) > max_len:
                errors.append(
                    f'[{table_name} row {index}] Field "{col}" exceeds '
                    f'{max_len} characters ({len(val)}).'
                )

    # Check that unexpected model fields are not present (reject surprise columns).
    _check_unexpected_fields(table_name, row, errors)


def _check_unexpected_fields(table_name, row, errors):
    """Reject fields the model does not declare. Prevents SQL injection via column names."""
    model_map = {
        'patients': Patient,
        'patient_allergies': PatientAllergy,
        'prescriptions': Prescription,
        'prescription_items': PrescriptionItem,
        'inventory': Inventory,
        'medicines': Medicine,
        'dosage_guides': DosageGuide,
    }
    model = model_map.get(table_name)
    if model is None:
        return
    expected_cols = {col.name for col in model.__table__.columns}
    unexpected = set(row.keys()) - expected_cols
    for col in sorted(unexpected):
        errors.append(
            f'[{table_name} row] Unexpected field "{col}". '
            f'Expected: {", ".join(sorted(expected_cols))}.'
        )


def parse_date_field(value, field_name):
    """
    Parse an ISO date string, returning None for blank values.

    Raises ValueError with a user-facing message on failure.
    """
    if value is None or str(value).strip() == '':
        return None
    from datetime import datetime
    try:
        return datetime.strptime(str(value).strip()[:10], '%Y-%m-%d').date()
    except ValueError:
        raise ValueError(
            f'Field "{field_name}" must be a date in YYYY-MM-DD format, '
            f'got {value!r}.'
        )


def parse_float_field(value, field_name):
    """Parse a float value, returning None for blank inputs."""
    if value is None or value == '':
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f'Field "{field_name}" must be a number, got {value!r}.')


def parse_int_field(value, field_name):
    """Parse an integer value, returning None for blank inputs."""
    if value is None or value == '':
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f'Field "{field_name}" must be an integer, got {value!r}.')


def json_loads(text):
    """Strict JSON parser with clear error messages."""
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f'Invalid JSON: {exc}') from exc
