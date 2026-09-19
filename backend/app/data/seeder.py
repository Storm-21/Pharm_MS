"""
Database bootstrap: creates schema, loads authored medicines, seals them, and
sets up opening inventory.

Idempotent by design - ``ensure_seeded()`` only inserts what is missing, so it
is safe to run on every application start (which is what the packaged .exe
does).

Stock levels below are *opening balances* for a typical community pharmacy. They
are deliberately varied so the dashboard has realistic low-stock and
out-of-stock cases to show; treat them as a starting point, not as a
recommendation of what to order.
"""

from datetime import date, timedelta

from app import db
from app.models import Medicine, DosageGuide, Inventory
# Import the data modules directly rather than through the package __init__:
# app.data.__init__ imports this module, so going through the package would be
# a circular import.
from app.data.seed_medicines import MEDICINES as _BASE_MEDICINES
from app.data.seed_medicines import DOSAGE_GUIDES as _BASE_GUIDES
from app.data.seed_medicines_extra import EXTRA_MEDICINES, EXTRA_DOSAGE_GUIDES
from app.security import apply_seal
MEDICINES = _BASE_MEDICINES + EXTRA_MEDICINES
DOSAGE_GUIDES = _BASE_GUIDES + EXTRA_DOSAGE_GUIDES

# Opening stock per medicine: (quantity, reorder_level, max_stock, storage_location)
# Chosen so that most lines are healthy and a handful trip the reorder alert.
OPENING_STOCK = {
    "Paracetamol 500mg": (480, 100, 1000, "Shelf A1 - Analgesics"),
    "Paracetamol 650mg": (320, 80, 800, "Shelf A1 - Analgesics"),
    "Ibuprofen 400mg": (240, 60, 600, "Shelf A1 - Analgesics"),
    "Aspirin 75mg": (615, 150, 1200, "Shelf A1 - Analgesics"),
    "Amoxicillin 500mg": (185, 50, 500, "Shelf B2 - Antibiotics"),
    "Amoxicillin + Clavulanic Acid 625mg": (140, 40, 400, "Shelf B2 - Antibiotics"),
    "Azithromycin 500mg": (95, 30, 300, "Shelf B2 - Antibiotics"),
    "Ciprofloxacin 500mg": (48, 50, 400, "Shelf B2 - Antibiotics"),          # low stock
    "Metronidazole 400mg": (210, 50, 500, "Shelf B2 - Antibiotics"),
    "Omeprazole 20mg": (275, 60, 600, "Shelf C1 - Gastro"),
    "Pantoprazole 40mg": (190, 50, 500, "Shelf C1 - Gastro"),
    "Ranitidine 150mg": (160, 40, 400, "Shelf C1 - Gastro"),
    "Metformin 500mg": (540, 120, 1200, "Shelf D1 - Diabetes"),
    "Amlodipine 5mg": (425, 100, 1000, "Shelf D2 - Cardiovascular"),
    "Lisinopril 10mg": (310, 80, 800, "Shelf D2 - Cardiovascular"),
    "Atorvastatin 10mg": (365, 90, 900, "Shelf D2 - Cardiovascular"),
    "Cetirizine 10mg": (580, 120, 1200, "Shelf E1 - Antihistamines"),
    "Levocetirizine 5mg": (295, 70, 700, "Shelf E1 - Antihistamines"),
    "Chlorpheniramine Maleate 4mg": (350, 80, 800, "Shelf E1 - Antihistamines"),
    "Montelukast 10mg": (0, 40, 400, "Shelf E2 - Respiratory"),              # out of stock
    "Salbutamol Inhaler 100mcg": (62, 20, 150, "Shelf E2 - Respiratory"),
    "Dextromethorphan Cough Syrup 100ml": (34, 15, 120, "Shelf E3 - Cough & Cold"),
    "ORS Powder (WHO formula)": (410, 100, 1000, "Shelf F1 - Rehydration"),
    "Levothyroxine 50mcg": (230, 60, 600, "Shelf D3 - Hormones"),
    "Vitamin D3 60000 IU": (85, 25, 250, "Shelf G1 - Vitamins"),
    "Iron + Folic Acid": (470, 110, 1000, "Shelf G1 - Vitamins"),
    # Batch 2
    "Glimepiride 2mg": (280, 70, 700, "Shelf D1 - Diabetes"),
    "Sitagliptin 100mg": (95, 25, 250, "Shelf D1 - Diabetes"),
    "Insulin Glargine 100IU/ml": (18, 8, 40, "Cold Chain - Refrigerator 2-8C"),
    "Telmisartan 40mg": (410, 100, 1000, "Shelf D2 - Cardiovascular"),
    "Metoprolol Succinate 25mg": (335, 80, 800, "Shelf D2 - Cardiovascular"),
    "Rosuvastatin 10mg": (290, 70, 700, "Shelf D2 - Cardiovascular"),
    "Warfarin 5mg": (145, 40, 400, "Shelf D2 - Cardiovascular"),
    "Diclofenac 50mg": (330, 80, 800, "Shelf A2 - NSAIDs"),
    "Clopidogrel 75mg": (260, 60, 600, "Shelf D2 - Cardiovascular"),
    "Doxycycline 100mg": (175, 45, 450, "Shelf B3 - Antibiotics"),
    "Ceftriaxone 1g Injection": (28, 15, 100, "Shelf B4 - Injectables"),
    "Fluconazole 150mg": (120, 30, 300, "Shelf B5 - Antifungals"),
    "Acyclovir 400mg": (88, 25, 250, "Shelf B5 - Antivirals"),
    "Artemether + Lumefantrine 20/120mg": (64, 20, 200, "Shelf B6 - Antimalarials"),
}


def _opening_batch(index):
    """Deterministic batch number, manufacture date and expiry."""
    today = date.today()
    batch = f"PMS{index:04d}"
    manufactured = today - timedelta(days=120)
    # 2 years from manufacture, but never already expired.
    expiry = manufactured + timedelta(days=730)
    if expiry <= today:
        expiry = today + timedelta(days=365)
    return batch, manufactured, expiry


def ensure_seeded(verbose=False):
    """
    Create any missing medicines, dosage guides and inventory rows.

    Returns a summary dict. Existing sealed records are left untouched so a
    user's own edits are never silently overwritten on boot.
    """
    created_medicines = 0
    created_guides = 0
    created_inventory = 0
    resealed = 0

    # --- Medicines ----------------------------------------------------------
    by_name = {}
    for index, data in enumerate(MEDICINES, start=1):
        existing = Medicine.query.filter_by(name=data["name"]).first()
        if existing:
            by_name[data["name"]] = existing
            # Repair only a missing seal; never rewrite authored content.
            if not existing.record_hash or not existing.content_seal:
                apply_seal(existing)
                resealed += 1
            continue

        medicine = Medicine(**data)
        # The seal must be computed from the populated row, before commit.
        apply_seal(medicine)
        db.session.add(medicine)
        by_name[data["name"]] = medicine
        created_medicines += 1

    db.session.flush()

    # --- Dosage guides ------------------------------------------------------
    for guide in DOSAGE_GUIDES:
        medicine = by_name.get(guide["medicine_name"])
        if not medicine:
            continue
        exists = DosageGuide.query.filter_by(
            medicine_id=medicine.id,
            age_group=guide["age_group"],
        ).first()
        if exists:
            continue
        db.session.add(DosageGuide(
            medicine_id=medicine.id,
            age_group=guide["age_group"],
            dosage_amount=guide["dosage_amount"],
            dosage_unit=guide["dosage_unit"],
            frequency=guide["frequency"],
            duration_days=guide["duration_days"],
            indication=guide["indication"],
            special_notes=guide.get("special_notes"),
        ))
        created_guides += 1

    # --- Inventory ----------------------------------------------------------
    for index, (name, (qty, reorder, max_stock, location)) in enumerate(
            OPENING_STOCK.items(), start=1):
        medicine = by_name.get(name)
        if not medicine:
            continue
        if Inventory.query.filter_by(medicine_id=medicine.id).first():
            continue
        batch, manufactured, expiry = _opening_batch(index)
        db.session.add(Inventory(
            medicine_id=medicine.id,
            quantity_in_stock=qty,
            reorder_level=reorder,
            max_stock=max_stock,
            batch_number=batch,
            manufacturing_date=manufactured,
            expiry_date=expiry,
            storage_location=location,
        ))
        created_inventory += 1

    db.session.commit()

    summary = {
        "medicines_created": created_medicines,
        "guides_created": created_guides,
        "inventory_created": created_inventory,
        "resealed": resealed,
        "total_medicines": Medicine.query.count(),
        "total_inventory": Inventory.query.count(),
    }
    if verbose:
        print(f"  medicines created : {created_medicines}")
        print(f"  dosage guides     : {created_guides}")
        print(f"  inventory lines   : {created_inventory}")
        print(f"  seals repaired    : {resealed}")
        print(f"  total medicines   : {summary['total_medicines']}")
    return summary
