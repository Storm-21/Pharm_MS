"""
Tamper detection for the PharmMS database and authored medicine data.

WHAT THIS DOES
--------------
Every authored medicine row carries two derived, sealed fields:

    * ``record_hash``    - SHA3-256 over the medicine's clinical fields
    * ``content_seal``   - SHA3-256 over record_hash + the app identity signature

The application never trusts the database on its own. On boot (and on demand via
``/api/security/verify``) each medicine is re-hashed from its live column values
and compared with the stored hash. A mismatch means the row was edited outside
this application (e.g. with a SQLite browser) and is reported as TAMPERED.

WHAT THIS DELIBERATELY DOES NOT DO
----------------------------------
* It does not prevent writes. A local SQLite file can always be edited by
  someone who owns the machine - the honest fix for that is OS file permissions
  or a server-side database, and pretending otherwise would be misleading.
* It is not a digital signature in the cryptographic sense. The sealing key
  lives inside the installed program and can, in principle, be extracted.
* It does not seal *stock quantities*. Quantities are operational data that a
  pharmacist must be free to change; sealing them would make the app unusable.
  The authored clinical data (formula, manufacturer, pharmacopoeia references,
  dosing, pricing basis) is what is sealed.

Net effect: whether a record has been altered without authorisation is
verifiable and reported. That is a real, useful guarantee; "cannot be changed
by anyone" is not a guarantee any locally-installed program can honestly make.
"""

import hashlib
import json

from app.branding import identity_signature

# Bumping this invalidates seals from older releases.
SEAL_VERSION = "1"

# Fields that make up the *authored* clinical record. Treated as sealed content.
SEALED_MEDICINE_FIELDS = (
    "name",
    "generic_name",
    "brand_name",
    "manufacturer",
    "manufacturer_country",
    "country_origin",
    "salt_composition",
    "molecular_formula",
    "chemical_formula_weight",
    "strength",
    "form",
    "route_of_administration",
    "therapeutic_class",
    "pharmacological_class",
    "use_case",
    "mechanism_of_action",
    "side_effects",
    "contraindications",
    "warnings",
    "drug_interactions",
    "food_interactions",
    "pregnancy_category",
    "onset_of_action",
    "half_life",
    "bioavailability",
    "protein_binding",
    "metabolism",
    "excretion",
    "max_daily_dose",
    "indian_pharmacopoeia_ref",
    "global_pharmacopoeia_ref",
    "pharmacopoeia_monograph",
    "ip_status",
    "schedule_classification",
    "storage_temp",
    "requires_prescription",
    "cost_price",
    "selling_price",
    "hsn_code",
    "gst_rate",
    "barcode",
)


def _canonical(value):
    """Normalise a value so hashing is stable across types/whitespace."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        # Avoid 12.0 vs 12.000001 drift.
        return f"{value:.4f}"
    if isinstance(value, str):
        return " ".join(value.split())
    return str(value)


def medicine_fingerprint(medicine):
    """Stable fingerprint of the sealed fields of a Medicine instance."""
    parts = [f"v{SEAL_VERSION}"]
    for field in SEALED_MEDICINE_FIELDS:
        parts.append(f"{field}={_canonical(getattr(medicine, field, None))}")
    return "\n".join(parts)


def compute_record_hash(medicine):
    return hashlib.sha3_256(medicine_fingerprint(medicine).encode("utf-8")).hexdigest()


def compute_content_seal(record_hash):
    payload = f"{SEAL_VERSION}|{record_hash}|{identity_signature()}"
    return hashlib.sha3_256(payload.encode("utf-8")).hexdigest()


def apply_seal(medicine):
    """(Re)compute and attach seal fields to a Medicine. Does not commit."""
    record_hash = compute_record_hash(medicine)
    medicine.record_hash = record_hash
    medicine.content_seal = compute_content_seal(record_hash)
    return record_hash


def verify_medicine(medicine):
    """
    Verify one medicine row.

    Returns a dict describing the verification result.
    """
    stored_hash = medicine.record_hash
    stored_seal = medicine.content_seal

    if not stored_hash or not stored_seal:
        return {
            "id": medicine.id,
            "name": medicine.name,
            "status": "UNSEALED",
            "detail": "Record has no seal - authored outside construction.",
        }

    actual_hash = compute_record_hash(medicine)
    if actual_hash != stored_hash:
        return {
            "id": medicine.id,
            "name": medicine.name,
            "status": "TAMPERED",
            "detail": "Clinical fields differ from the sealed original.",
            "stored_hash": stored_hash,
            "actual_hash": actual_hash,
        }

    expected_seal = compute_content_seal(stored_hash)
    if expected_seal != stored_seal:
        return {
            "id": medicine.id,
            "name": medicine.name,
            "status": "FORGED",
            "detail": "Seal does not match this application's identity.",
        }

    return {"id": medicine.id, "name": medicine.name, "status": "INTACT"}


def verify_all(medicines):
    """Verify an iterable of medicines and summarise."""
    results = [verify_medicine(m) for m in medicines]
    counts = {}
    for result in results:
        counts[result["status"]] = counts.get(result["status"], 0) + 1

    compromised = [r for r in results if r["status"] in ("TAMPERED", "FORGED")]
    return {
        "total": len(results),
        "counts": counts,
        "compromised": compromised,
        "ok": len(compromised) == 0,
    }


def seal_to_json(medicine):
    """Debug helper: the exact canonical payload that was hashed."""
    return json.dumps(medicine_fingerprint(medicine).splitlines(), indent=2)
