"""
Persistent local storage ("memory") for PharmMS patient and clinical data.

DESIGN
------
All data lives in a single SQLite file on this machine. Nothing is sent
anywhere: there is no remote API, no cloud sync and no telemetry, so the
application is fully functional with networking disabled.

This module adds the operational layer around that file:

  * automatic timestamped snapshots taken on each successful startup, so a bad
    edit or an accidental delete can be rolled back
  * manual backup, restore and export/import endpoints, so data can be moved to
    another machine or kept as an offline archive
  * a data-location report shown in the UI, so it is never a mystery where the
    records actually are

BACKUP FORMAT
-------------
A backup is a *logical* export (rows as JSON), not a copy of the SQLite file.
Same-machine snapshots use SQLite's own online backup API, which is safe to run
while the app is serving requests - copying the file directly is not, because
SQLite may be mid-write.
"""

import json
import os
import shutil
import sqlite3
from datetime import datetime

from app import db
from app.models import (
    Medicine, Patient, PatientAllergy, Prescription, PrescriptionItem,
    Inventory, DosageGuide,
)

# Tables included in a logical export, in dependency order (parents first).
EXPORT_TABLES = [
    ('medicines', Medicine),
    ('patients', Patient),
    ('patient_allergies', PatientAllergy),
    ('prescriptions', Prescription),
    ('prescription_items', PrescriptionItem),
    ('inventory', Inventory),
    ('dosage_guides', DosageGuide),
]

# Kept small on purpose: snapshots are a safety net, not an archive.
MAX_SNAPSHOTS = 10


def _database_path():
    """Absolute path of the live SQLite file, from the configured engine URI."""
    uri = db.engine.url
    return os.path.abspath(uri.database)


def backup_dir():
    """Where snapshots and exports are written - beside the live database."""
    path = os.path.join(os.path.dirname(_database_path()), 'backups')
    os.makedirs(path, exist_ok=True)
    return path


def database_info():
    """Report where data lives and how much of it there is."""
    path = _database_path()
    size = os.path.getsize(path) if os.path.exists(path) else 0
    return {
        'database_path': path,
        'data_directory': os.path.dirname(path),
        'backup_directory': backup_dir(),
        'database_size_bytes': size,
        'database_size_readable': _human_size(size),
        'counts': {
            'medicines': Medicine.query.count(),
            'patients': Patient.query.count(),
            'prescriptions': Prescription.query.count(),
            'inventory_lines': Inventory.query.count(),
            'dosage_guides': DosageGuide.query.count(),
        },
    }


def _human_size(num_bytes):
    for unit in ('B', 'KB', 'MB', 'GB'):
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} TB"


# --- Snapshots (same-machine safety net) -------------------------------------

def create_snapshot(label='auto'):
    """
    Snapshot the live database using SQLite's online backup API.

    Safe to call while the application is running. Returns the file path.
    """
    source_path = _database_path()
    if not os.path.exists(source_path):
        return None

    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    filename = f"pharmacy-{label}-{stamp}.db"
    target_path = os.path.join(backup_dir(), filename)

    source = sqlite3.connect(source_path)
    try:
        target = sqlite3.connect(target_path)
        try:
            source.backup(target)
        finally:
            target.close()
    finally:
        source.close()

    prune_snapshots()
    return target_path


def list_snapshots():
    """Available snapshots, newest first."""
    directory = backup_dir()
    if not os.path.isdir(directory):
        return []
    items = []
    for name in os.listdir(directory):
        if not (name.startswith('pharmacy-') and name.endswith('.db')):
            continue
        full = os.path.join(directory, name)
        stat = os.stat(full)
        items.append({
            'filename': name,
            'path': full,
            'size_bytes': stat.st_size,
            'size_readable': _human_size(stat.st_size),
            'created_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })
    items.sort(key=lambda x: x['created_at'], reverse=True)
    return items


def prune_snapshots():
    """Keep only the most recent MAX_SNAPSHOTS automatic snapshots."""
    snapshots = list_snapshots()
    for stale in snapshots[MAX_SNAPSHOTS:]:
        try:
            os.remove(stale['path'])
        except OSError:
            pass


def restore_snapshot(filename):
    """
    Roll the live database back to a snapshot.

    Take a snapshot of the *current* state first, so a restore is itself
    undoable. Returns a report dict.
    """
    directory = backup_dir()
    source_path = os.path.join(directory, os.path.basename(filename))

    if not os.path.isfile(source_path):
        return {'restored': False, 'error': f'Snapshot not found: {filename}'}

    safety = create_snapshot('pre-restore')
    target_path = _database_path()

    # Close pooled connections so the file is not locked mid-replace.
    db.session.remove()
    db.engine.dispose()

    shutil.copyfile(source_path, target_path)

    return {
        'restored': True,
        'from': filename,
        'safety_snapshot': os.path.basename(safety) if safety else None,
        'note': 'Restart the application to be certain all data is reloaded.',
    }


# --- Logical export / import (portable archive) ------------------------------

def _row_to_dict(instance):
    """Serialise a model instance to JSON-safe primitives."""
    out = {}
    for column in instance.__table__.columns:
        value = getattr(instance, column.name)
        if isinstance(value, (datetime,)):
            value = value.isoformat()
        elif hasattr(value, 'isoformat'):
            value = value.isoformat()
        out[column.name] = value
    return out


def export_data(include_medicines=True):
    """
    Full logical export as a dict.

    Clinical and operational tables are always included. The sealed medicine
    reference set is optional so a clinic can export only patient data.
    """
    payload = {
        'format': 'pharms-export',
        'format_version': 1,
        'exported_at': datetime.now().isoformat(),
        'tables': {},
    }
    for name, model in EXPORT_TABLES:
        if name == 'medicines' and not include_medicines:
            continue
        payload['tables'][name] = [_row_to_dict(row) for row in model.query.all()]
    payload['record_count'] = sum(len(rows) for rows in payload['tables'].values())
    return payload


def export_to_file(include_medicines=True):
    """Write an export to the backups folder and return its path."""
    payload = export_data(include_medicines=include_medicines)
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    filename = f"pharms-export-{stamp}.json"
    path = os.path.join(backup_dir(), filename)
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(payload, handle, indent=2)
    return path, payload


def import_data(payload, replace_patients=False):
    """
    Load a logical export into the database.

    Medicines are matched by name and skipped if already present, so importing
    never silently overwrites the sealed reference data.

    replace_patients=False (default) is additive: existing patients are kept and
    only records with new IDs/emails are added. Setting it True deletes current
    patient, prescription and allergy rows first - this is destructive and the
    caller is expected to have confirmed with the user.
    """
    if payload.get('format') != 'pharms-export':
        return {'imported': False, 'error': 'Not a PharmS export file.'}

    tables = payload.get('tables', {})
    stats = {}

    if replace_patients:
        PrescriptionItem.query.delete()
        Prescription.query.delete()
        PatientAllergy.query.delete()
        Patient.query.delete()
        db.session.commit()
        stats['patients_deleted'] = True

    existing_medicine_names = {m.name for m in Medicine.query.all()}
    existing_patient_ids = {p.id for p in Patient.query.all()}
    existing_prescription_ids = {p.id for p in Prescription.query.all()}

    for row in tables.get('medicines', []):
        if row.get('name') in existing_medicine_names:
            continue
        row.pop('id', None)
        db.session.add(Medicine(**row))
        stats.setdefault('medicines_added', 0)
        stats['medicines_added'] += 1
    db.session.commit()

    for row in tables.get('patients', []):
        if row.get('id') in existing_patient_ids:
            continue
        row.setdefault('created_at', datetime.utcnow())
        db.session.add(Patient(**row))
        stats.setdefault('patients_added', 0)
        stats['patients_added'] += 1
    db.session.commit()

    for row in tables.get('patient_allergies', []):
        row.pop('id', None)
        db.session.add(PatientAllergy(**row))
        stats.setdefault('allergies_added', 0)
        stats['allergies_added'] += 1
    db.session.commit()

    for row in tables.get('prescriptions', []):
        if row.get('id') in existing_prescription_ids:
            continue
        db.session.add(Prescription(**row))
        stats.setdefault('prescriptions_added', 0)
        stats['prescriptions_added'] += 1
    db.session.commit()

    for row in tables.get('inventory', []):
        if Inventory.query.filter_by(
                medicine_id=row.get('medicine_id'),
                batch_number=row.get('batch_number')).first():
            continue
        row.pop('id', None)
        db.session.add(Inventory(**row))
        stats.setdefault('inventory_added', 0)
        stats['inventory_added'] += 1
    db.session.commit()

    for row in tables.get('dosage_guides', []):
        row.pop('id', None)
        db.session.add(DosageGuide(**row))
        stats.setdefault('guides_added', 0)
        stats['guides_added'] += 1
    db.session.commit()

    return {'imported': True, 'stats': stats}
