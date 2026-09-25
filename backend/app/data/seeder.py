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
from app.data.seed_medicines_batch3 import BATCH3_MEDICINES, BATCH3_GUIDES
from app.data.seed_medicines_batch4 import BATCH4_MEDICINES, BATCH4_GUIDES
from app.data.seed_medicines_batch5 import BATCH5_MEDICINES, BATCH5_GUIDES
# Batch 6 adds dosage GUIDANCE ONLY, for entries that had a medicine record but
# no dose to open. It deliberately defines no medicines, so the catalogue count
# is unchanged - see the module docstring.
from app.data.seed_medicines_batch6 import BATCH6_GUIDES
from app.data.seed_medicines_batch7 import (BATCH7_MEDICINES, BATCH7_GUIDES)
from app.security import apply_seal
# Batch order is deliberate: later batches extend earlier ones, and the
# duplicate-name guard in ensure_seeded() rejects an accidental re-add rather
# than silently shipping two rows for one medicine.
#
# CAVEAT on that guard, learned the hard way: it *skips* the duplicate silently,
# so a medicine repeated in a later batch is not added and not reported - the
# catalogue ends up one shorter than the data files imply. test_catalogue.py
# asserts the loaded count against the sum of the batches precisely so that
# cannot go unnoticed again.
MEDICINES = (_BASE_MEDICINES + EXTRA_MEDICINES + BATCH3_MEDICINES
             + BATCH4_MEDICINES + BATCH5_MEDICINES + BATCH7_MEDICINES)
DOSAGE_GUIDES = (_BASE_GUIDES + EXTRA_DOSAGE_GUIDES + BATCH3_GUIDES
                 + BATCH4_GUIDES + BATCH5_GUIDES + BATCH6_GUIDES
                 + BATCH7_GUIDES)

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

    # --- Batch 3: depth across classes so the recommender has a choice ---
    # Deliberately varied. Several lines are out of stock on purpose, so the
    # "no stock - suggest the closest safe alternative" path has real cases to
    # exercise rather than being dead code.
    "Losartan 50mg": (380, 90, 900, "Shelf D2 - Cardiovascular"),
    "Valsartan 80mg": (210, 50, 500, "Shelf D2 - Cardiovascular"),
    "Hydrochlorothiazide 25mg": (455, 110, 1000, "Shelf D2 - Cardiovascular"),
    "Furosemide 40mg": (520, 120, 1100, "Shelf D2 - Cardiovascular"),
    "Spironolactone 25mg": (300, 75, 700, "Shelf D2 - Cardiovascular"),
    "Digoxin 0.25mg": (165, 40, 400, "Shelf D2 - Cardiovascular"),
    "Amiodarone 200mg": (72, 20, 200, "Shelf D2 - Cardiovascular"),
    "Isosorbide Mononitrate 20mg": (240, 60, 600, "Shelf D2 - Cardiovascular"),
    "Nifedipine 10mg": (285, 70, 700, "Shelf D2 - Cardiovascular"),

    "Sertraline 50mg": (195, 50, 500, "Shelf H1 - Psychotropics"),
    "Fluoxetine 20mg": (170, 45, 450, "Shelf H1 - Psychotropics"),
    "Alprazolam 0.5mg": (88, 25, 250, "Shelf H1 - Psychotropics - CD register"),
    "Phenytoin 100mg": (140, 35, 350, "Shelf H2 - Antiepileptics"),
    "Carbamazepine 200mg": (125, 30, 300, "Shelf H2 - Antiepileptics"),
    "Sumatriptan 50mg": (48, 15, 150, "Shelf H1 - Antimigraine"),

    "Tramadol 50mg": (0, 25, 250, "Shelf A3 - Controlled - H1 register"),   # out of stock
    "Morphine Sulphate 10mg": (12, 6, 30, "CD Cabinet - double locked"),
    "Gabapentin 300mg": (230, 60, 600, "Shelf A3 - Neuropathic"),

    "Budesonide + Formoterol Inhaler": (54, 15, 150, "Shelf E2 - Respiratory"),
    "Ipratropium Inhaler": (41, 12, 120, "Shelf E2 - Respiratory"),
    "Prednisolone 10mg": (360, 90, 800, "Shelf E4 - Corticosteroids"),

    "Ondansetron 4mg": (290, 70, 700, "Shelf C2 - Antiemetics"),
    "Metoclopramide 10mg": (315, 80, 800, "Shelf C2 - Antiemetics"),
    "Lactulose Solution": (125, 30, 300, "Shelf C3 - Laxatives"),
    "Dicyclomine 10mg": (275, 70, 700, "Shelf C3 - Antispasmodics"),

    "Allopurinol 100mg": (340, 85, 800, "Shelf A4 - Antigout"),
    "Colchicine 0.5mg": (155, 40, 400, "Shelf A4 - Antigout"),
    "Alendronate 70mg": (95, 25, 250, "Shelf A5 - Bone health"),

    "Ethinylestradiol + Levonorgestrel": (180, 45, 450, "Shelf G2 - Hormonal"),
    "Medroxyprogesterone 10mg": (145, 35, 350, "Shelf G2 - Hormonal"),

    "Levofloxacin 500mg": (155, 40, 400, "Shelf B2 - Antibiotics"),
    "Cefixime 200mg": (205, 50, 500, "Shelf B2 - Antibiotics"),
    "Ampicillin + Cloxacillin": (190, 50, 500, "Shelf B2 - Antibiotics"),
    "Amikacin 500mg Injection": (34, 12, 100, "Shelf B4 - Injectables"),
    "Nitrofurantoin 100mg": (175, 45, 450, "Shelf B2 - Antibiotics"),
    "Albendazole 400mg": (290, 70, 700, "Shelf B7 - Anthelmintics"),
    "Praziquantel 600mg": (42, 12, 120, "Shelf B7 - Anthelmintics"),
    "Clotrimazole 1% Cream": (88, 22, 220, "Shelf B5 - Antifungals"),

    "Moxifloxacin 0.5% Eye Drops": (36, 12, 120, "Shelf I1 - Ophthalmic"),
    "Timol 0.5% Eye Drops": (44, 12, 120, "Shelf I1 - Ophthalmic"),

    "Tetanus Toxoid Injection": (58, 20, 200, "Cold Chain - Refrigerator 2-8C"),

    # --- Batch 4: TB programme, antimalarials, national child-health items,
    # fixed-dose combinations and the high-volume OTC and topical lines.
    "Isoniazid 300mg": (140, 40, 300, "Shelf K1 - Antitubercular (Schedule H1)"),
    "Rifampicin 450mg": (120, 40, 300, "Shelf K1 - Antitubercular (Schedule H1)"),
    "Pyrazinamide 750mg": (110, 30, 250, "Shelf K1 - Antitubercular (Schedule H1)"),
    "Ethambutol 400mg": (110, 30, 250, "Shelf K1 - Antitubercular (Schedule H1)"),

    "Artemether 20mg + Lumefantrine 120mg": (60, 20, 150, "Shelf K2 - Antimalarial"),
    "Artesunate 60mg Injection": (28, 10, 80, "Shelf K2 - Antimalarial"),
    "Primaquine 15mg": (90, 25, 200, "Shelf K2 - Antimalarial"),
    "Chloroquine 250mg": (85, 25, 200, "Shelf K2 - Antimalarial"),

    "ORS Low Osmolarity Sachet": (520, 150, 1000, "Shelf D1 - Child Health"),
    "Zinc Sulphate 20mg Dispersible": (410, 120, 800, "Shelf D1 - Child Health"),
    "Albendazole 400mg Tablet": (260, 80, 500, "Shelf D1 - Child Health"),

    "Amlodipine 5mg + Atenolol 50mg": (200, 60, 400, "Shelf B2 - Cardiovascular"),
    "Telmisartan 40mg + Amlodipine 5mg": (185, 60, 400, "Shelf B2 - Cardiovascular"),
    "Metformin 500mg + Glimepiride 2mg": (175, 50, 400, "Shelf B2 - Cardiovascular"),
    "Hydrochlorothiazide 12.5mg + Losartan 50mg": (160, 50, 350, "Shelf B2 - Cardiovascular"),

    "Amoxicillin 500mg + Clavulanic Acid 125mg": (145, 40, 300, "Shelf E1 - Antibiotics (Schedule H1)"),
    "Cefixime 200mg + Ofloxacin 200mg": (95, 30, 200, "Shelf E1 - Antibiotics (Schedule H1)"),

    "Paracetamol 500mg + Ibuprofen 400mg": (310, 90, 600, "Shelf A1 - Analgesics"),
    "Aceclofenac 100mg + Paracetamol 325mg": (240, 70, 500, "Shelf A1 - Analgesics"),
    "Diclofenac 1% Gel": (68, 20, 150, "Shelf A2 - Topical"),
    "Febuxostat 40mg": (72, 25, 180, "Shelf A3 - Musculoskeletal"),

    "Budesonide 200mcg + Formoterol 6mcg Inhaler": (34, 12, 90, "Shelf F1 - Respiratory"),
    "Tiotropium 18mcg Inhaler": (26, 10, 70, "Shelf F1 - Respiratory"),
    "Ipratropium 20mcg + Salbutamol 100mcg Inhaler": (38, 12, 90, "Shelf F1 - Respiratory"),
    "Montelukast 5mg Chewable": (140, 40, 300, "Shelf F1 - Respiratory"),

    "Pantoprazole 40mg + Domperidone 30mg": (195, 60, 400, "Shelf C1 - Gastrointestinal"),
    "Loperamide 2mg Capsule": (120, 35, 250, "Shelf C1 - Gastrointestinal"),
    "Rifaximin 550mg": (44, 15, 110, "Shelf C1 - Gastrointestinal"),

    "Carboxymethylcellulose 0.5% Eye Drops": (78, 25, 180, "Shelf I1 - Ophthalmic"),

    "Clotrimazole 1% Cream": (92, 30, 200, "Shelf H1 - Dermatology"),
    "Betamethasone 0.1% + Clotrimazole 1% Cream": (64, 20, 150, "Shelf H1 - Dermatology"),

    "Levonorgestrel 0.75mg Tablet": (56, 20, 140, "Shelf G1 - Reproductive Health"),
    "Tranexamic Acid 500mg": (88, 25, 200, "Shelf G1 - Reproductive Health"),

    "Levetiracetam 500mg": (96, 30, 220, "Shelf J1 - Neurology"),
    "Escitalopram 10mg": (108, 30, 250, "Shelf J1 - Neurology"),
    "Fexofenadine 120mg": (165, 50, 350, "Shelf A4 - Antihistamines"),

    # --- Batch 5: cardiac, newer antidiabetics, psychiatry, combination
    # inhalers, paediatric liquids and the accompanying drugs. Varied on
    # purpose, and the cold-chain and inhaler lines are set low so the
    # reorder alerting has realistic cases rather than decorative ones.
    "Isosorbide Dinitrate 10mg": (240, 60, 600, "Shelf D2 - Cardiovascular"),
    "Nicorandil 5mg": (85, 25, 220, "Shelf D2 - Cardiovascular"),
    "Ivabradine 5mg": (48, 20, 140, "Shelf D2 - Cardiovascular"),
    "Nitroglycerin 0.5mg Sublingual": (110, 30, 250, "Shelf D2 - Cardiovascular"),

    "Dapagliflozin 10mg": (175, 45, 450, "Shelf D1 - Diabetes"),
    "Empagliflozin 10mg": (150, 40, 400, "Shelf D1 - Diabetes"),
    "Sitagliptin 50mg": (130, 35, 350, "Shelf D1 - Diabetes"),
    "Liraglutide 6mg/ml Injection": (14, 6, 30, "Cold Chain - Refrigerator 2-8C"),
    "Dulaglutide 1.5mg Injection": (11, 5, 25, "Cold Chain - Refrigerator 2-8C"),

    "Venlafaxine 75mg": (115, 30, 300, "Shelf J1 - Neurology"),
    "Mirtazapine 15mg": (92, 25, 240, "Shelf J1 - Neurology"),
    # Batch 3 defines this as "Alprazolam 0.5mg", and batch 5 deliberately does
    # not repeat it. A stock line for "Alprazolam 0.25mg" therefore named a
    # medicine that does not exist in the catalogue and was silently dropped on
    # seed - so the controlled-drug shelf showed one fewer line than the opening
    # stock block implies, and this out-of-stock demo case was never created.
    "Alprazolam 0.5mg": (0, 40, 300, "Shelf J2 - Controlled Drugs"),          # out of stock
    "Clonazepam 0.5mg": (68, 25, 200, "Shelf J2 - Controlled Drugs"),

    # --- Batch 7 additions --------------------------------------------------
    # Opening stock for the classes batch 7 introduced. As with the rest of this
    # block these are a starting point for a stock take, not a purchasing
    # recommendation, and a few deliberate zeros keep the low-stock and
    # out-of-stock alerting visibly working.
    "Cefuroxime Axetil 500mg": (96, 30, 220, "Shelf A2 - Antibiotics"),
    "Cefixime Dry Syrup 100mg/5ml": (74, 24, 160, "Shelf A2 - Antibiotics"),
    "Cefadroxil 500mg": (88, 30, 200, "Shelf A2 - Antibiotics"),
    "Clarithromycin 250mg": (62, 20, 150, "Shelf A2 - Antibiotics"),
    "Erythromycin 250mg": (58, 20, 140, "Shelf A2 - Antibiotics"),
    "Tetracycline 500mg": (44, 20, 120, "Shelf A3 - Antibiotics"),
    "Cotrimoxazole 960mg": (132, 40, 300, "Shelf A3 - Antibiotics"),
    "Clindamycin 300mg": (0, 20, 120, "Shelf A3 - Antibiotics"),           # out of stock
    "Terbinafine 250mg": (48, 15, 110, "Shelf B2 - Antifungals"),
    "Itraconazole 100mg": (26, 12, 80, "Shelf B2 - Antifungals"),          # low
    "Griseofulvin 250mg": (54, 18, 120, "Shelf B2 - Antifungals"),

    "Tamsulosin 0.4mg": (78, 25, 190, "Shelf H1 - Urology"),
    "Finasteride 5mg": (64, 20, 160, "Shelf H1 - Urology"),
    "Oxybutynin 5mg": (72, 25, 170, "Shelf H1 - Urology"),
    "Tadalafil 10mg": (48, 15, 120, "Shelf H1 - Urology"),

    "Carbimazole 10mg": (56, 20, 140, "Shelf F2 - Endocrine"),
    "Levothyroxine 25mcg": (0, 30, 200, "Shelf F2 - Endocrine"),           # out of stock

    "Ondansetron Mouth Dissolving 4mg": (84, 25, 200, "Shelf C2 - Gastro"),
    "Doxylamine + Pyridoxine": (62, 20, 150, "Shelf M1 - Obstetric"),
    "Ursodeoxycholic Acid 300mg": (34, 15, 100, "Shelf C2 - Gastro"),

    "Methotrexate 2.5mg": (28, 12, 90, "Shelf I1 - Rheumatology"),
    "Hydroxychloroquine 200mg": (52, 20, 130, "Shelf I1 - Rheumatology"),
    "Dexamethasone 0.5mg": (118, 35, 260, "Shelf I2 - Corticosteroids"),
    "Clobetasol Propionate 0.05% Cream": (58, 18, 140, "Shelf B3 - Dermatology"),
    "Amitriptyline 10mg": (92, 30, 210, "Shelf J1 - Neurology"),
    "Flunarizine 10mg": (44, 18, 120, "Shelf J1 - Neurology"),
    "Propranolol 20mg": (86, 30, 200, "Shelf D2 - Cardiovascular"),
    "Betahistine 8mg": (68, 22, 160, "Shelf J3 - Vestibular"),
    "Ivermectin 12mg": (36, 15, 110, "Shelf G2 - Antiparasitics"),
    "Calcium Carbonate + Cholecalciferol": (216, 60, 480, "Shelf F3 - Supplements"),
    "Rifampicin + Isoniazid + Pyrazinamide + Ethambutol": (0, 20, 120,
                                                          "Shelf K1 - Antitubercular"),  # out of stock

    "Budesonide + Formoterol 200/6mcg Inhaler": (58, 20, 150, "Shelf E2 - Respiratory"),
    "Tiotropium 18mcg Inhaler": (32, 12, 90, "Shelf E2 - Respiratory"),
    "Fluticasone + Salmeterol 125/25mcg Inhaler": (26, 10, 80, "Shelf E2 - Respiratory"),
    "Ipratropium + Levosalbutamol Respirator Solution": (74, 25, 180,
                                                         "Shelf E2 - Respiratory"),

    "Paracetamol 125mg/5ml Suspension": (190, 50, 450, "Shelf F2 - Paediatric"),
    "Amoxicillin 125mg/5ml Dry Syrup": (135, 40, 350, "Shelf B2 - Antibiotics"),
    "Cetirizine 5mg/5ml Syrup": (170, 45, 400, "Shelf E1 - Antihistamines"),
    "Ibuprofen 100mg/5ml Suspension": (155, 45, 380, "Shelf F2 - Paediatric"),
    "Metronidazole 100mg/5ml Suspension": (105, 30, 260, "Shelf B2 - Antibiotics"),
    "Zinc Sulphate 20mg Dispersible Tablet": (330, 90, 700, "Shelf F1 - Rehydration"),

    "Domperidone 10mg": (210, 55, 500, "Shelf C1 - Gastro"),
    "Rabeprazole 20mg": (250, 60, 600, "Shelf C1 - Gastro"),
    # Batch 3 defines this as "Lactulose Solution" with the strength (10g/15ml)
    # carried in the strength field, not appended to the name. The name here
    # included the strength, which no medicine is ever called, so this line was
    # dropped on seed for the same reason as the Alprazolam line above.
    "Lactulose Solution": (96, 30, 220, "Shelf C1 - Gastro"),
    "Rivaroxaban 20mg": (62, 20, 160, "Shelf D2 - Cardiovascular"),
    "Folic Acid 5mg": (520, 120, 1100, "Shelf G1 - Vitamins"),
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
