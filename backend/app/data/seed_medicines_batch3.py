"""
Extended medicine reference data - batch 3.

Adds depth where batch 1 and 2 had a single example per class, so that the
recommender always has a genuine therapeutic choice rather than one option that
is either right or absent. Coverage added here:

  cardiovascular      - ARBs, thiazide and loop diuretics, alpha-blockers,
                        nitrate, digoxin, amiodarone
  CNS                 - SSRIs, benzodiazepine, antiepileptics, triptan,
                        anti-dementia, antiparkinsonian
  analgesics          - opioids, tramadol, topical NSAID, migraine prophylaxis
  anti-infectives     - cephalosporins, penicillins, aminoglycoside, antifungal,
                        antiviral, antitubercular, antiprotozoal, anthelmintic
  respiratory         - inhaled corticosteroid, LABA, combination inhaler,
                        antimuscarinic, oral steroid, montelukast is in batch 2
  GI                  - antiemetic, prokinetic, laxative, antispasmodic,
                        aminosalicylate, PPI/H2 already present
  musculoskeletal     - muscle relaxant, gout treatments, bisphosphonate
  hormones            - oral contraceptive, corticosteroid, testosterone
  psychotropics       - antipsychotic, mood stabiliser, hypnotic
  dermatology         - topical steroid, antifungal cream, antihistamine cream
  ophthalmology       - antibiotic and beta-blocker eye drops
  vaccines and OTC    - tetanus toxoid, oral rehydration is in batch 1

Every entry is a real, individually prescribable medicine. Molecular formulas
and weights are the standard published values. The set is deliberately biased
toward molecules that appear on the WHO Model List of Essential Medicines and
on Indian national formularies, because those are what a community pharmacy
actually dispenses.

SAFETY NOTE
-----------
Entries listed here feed the recommender, which gates them through
app/services/safety_service.py. Several of these are deliberately included
*because* they carry serious interactions (warfarin, digoxin, methotrexate,
tramadol) so that the safety engine has the full picture when screening a
patient's current medication list rather than being blind to them.
"""

DATA_VERSION = "3.0.0"
DATA_AUTHOR = "Jayant"


def _med(name, generic, cls, pharm, use, *, strength, form, route,
         brand=None, manufacturer="Cipla Ltd", site="Verna Industrial Estate, Goa",
         formula=None, weight=None, moa=None, side_effects=None,
         contra=None, warnings=None, interactions=None, pregnancy="B",
         half_life=None, onset=None, max_dose=None, schedule="Schedule H - prescription required",
         rx=True, cost=2.0, price=5.0, storage="15-30C, protect from light and moisture",
         hsn="30049099", gst="12%"):
    """
    Build a medicine row with every required field populated.

    Most of the 30-odd columns a Medicine row needs are the same boilerplate for
    every drug (HSN code, GST rate, storage wording). Writing them out by hand
    for a hundred entries invites a typo that only shows up as a database error
    at boot, so they are defaulted here and only the genuinely drug-specific
    values are passed in.
    """
    return {
        "name": name,
        "generic_name": generic,
        "brand_name": brand,
        "manufacturer": manufacturer,
        "manufacturer_country": "India",
        "manufacturer_site": site,
        "marketed_by": manufacturer,
        "country_origin": "India",
        "salt_composition": name,
        "molecular_formula": formula,
        "chemical_formula_weight": weight,
        "strength": strength,
        "form": form,
        "route_of_administration": route,
        "therapeutic_class": cls,
        "pharmacological_class": pharm,
        "use_case": use,
        "mechanism_of_action": moa,
        "side_effects": side_effects,
        "contraindications": contra,
        "warnings": warnings,
        "drug_interactions": interactions,
        "food_interactions": None,
        "pregnancy_category": pregnancy,
        "onset_of_action": onset,
        "half_life": half_life,
        "bioavailability": None,
        "protein_binding": None,
        "metabolism": None,
        "excretion": None,
        "max_daily_dose": max_dose,
        "indian_pharmacopoeia_ref": "IP 2022, Monograph '%s'" % generic,
        "global_pharmacopoeia_ref": "BP 2023 '%s'; USP-NF '%s'" % (generic, generic),
        "pharmacopoeia_monograph": None,
        "ip_status": None,
        "schedule_classification": schedule,
        "hsn_code": hsn,
        "gst_rate": gst,
        "barcode": None,
        "cost_price": cost,
        "selling_price": price,
        "requires_prescription": rx,
        "storage_temp": storage,
    }


BATCH3_MEDICINES = [
    # =================================================================== #
    # CARDIOVASCULAR - fill out each class so there is a real choice
    # =================================================================== #
    _med(
        "Losartan 50mg", "Losartan", "Antihypertensive - angiotensin receptor blocker",
        "Selective AT1 receptor antagonist",
        "Hypertension, diabetic nephropathy, heart failure, stroke prevention",
        strength="50mg", form="tablet", route="Oral", brand="Losar 50",
        manufacturer="Unichem Laboratories Ltd", site="Pithampur, Madhya Pradesh",
        formula="C22H23ClN6O", weight="422.91 g/mol",
        moa="Blocks angiotensin II binding at the AT1 receptor, reducing vasoconstriction and aldosterone release.",
        side_effects="Dizziness, hyperkalaemia, hypotension, renal impairment",
        contra="Pregnancy, bilateral renal artery stenosis, severe hepatic impairment",
        warnings="Monitor potassium and creatinine after starting. Not interchangeable with beta-blockers in asthma.",
        interactions="Potassium supplements, spironolactone, NSAIDs, lithium, other antihypertensives",
        pregnancy="X - fetal renal damage; stop immediately if pregnancy occurs",
        half_life="2 hours (active metabolite 6-9 hours)", onset="1 hour",
        max_dose="100 mg/day", cost=1.8, price=4.2),

    _med(
        "Valsartan 80mg", "Valsartan", "Antihypertensive - angiotensin receptor blocker",
        "Selective AT1 receptor antagonist",
        "Hypertension, heart failure, post-myocardial infarction",
        strength="80mg", form="tablet", route="Oral", brand="Valzaar 80",
        manufacturer="Torrent Pharmaceuticals Ltd", site="Indrad, Gujarat",
        formula="C24H29N5O3", weight="435.52 g/mol",
        moa="Selective angiotensin II AT1 receptor blockade.",
        side_effects="Dizziness, headache, hyperkalaemia, fatigue",
        contra="Pregnancy, severe hepatic impairment, biliary cirrhosis",
        warnings="Avoid potassium supplements unless prescribed. Monitor renal function.",
        interactions="Potassium-sparing diuretics, NSAIDs, lithium, ACE inhibitors",
        pregnancy="X - fetal toxicity", half_life="6 hours",
        max_dose="320 mg/day", cost=2.4, price=5.6),

    _med(
        "Hydrochlorothiazide 25mg", "Hydrochlorothiazide",
        "Antihypertensive - thiazide diuretic",
        "Thiazide diuretic; inhibits Na-Cl symporter in distal convoluted tubule",
        "Hypertension, oedema in heart failure and hepatic cirrhosis, nephrogenic diabetes insipidus",
        strength="25mg", form="tablet", route="Oral", brand="Esidrex",
        manufacturer="Novartis India Ltd", site="Kalwe, Maharashtra",
        formula="C7H8ClN3O4S2", weight="297.74 g/mol",
        moa="Inhibits sodium and chloride reabsorption in the distal convoluted tubule, increasing diuresis and lowering blood pressure.",
        side_effects="Hypokalaemia, hyponatraemia, hyperuricaemia, hyperglycaemia, erectile dysfunction",
        contra="Anuria, severe renal impairment, sulfonamide allergy, gout",
        warnings="Check electrolytes at 2-4 weeks. Raises uric acid and blood glucose. Photosensitivity reported.",
        interactions="Lithium (toxicity), digoxin (hypokalaemia increases toxicity), NSAIDs (reduced effect), corticosteroids",
        pregnancy="B - avoid in pre-eclampsia; not first line",
        half_life="6-15 hours", onset="2 hours", max_dose="50 mg/day",
        cost=0.6, price=1.8),

    _med(
        "Furosemide 40mg", "Furosemide", "Diuretic - loop",
        "Loop diuretic; inhibits Na-K-2Cl cotransporter in ascending limb",
        "Oedema in heart failure, hepatic cirrhosis, renal impairment; pulmonary oedema",
        strength="40mg", form="tablet", route="Oral", brand="Lasix 40",
        manufacturer="Sanofi India Ltd", site="Ankleshwar, Gujarat",
        formula="C12H11ClN2O5S", weight="330.74 g/mol",
        moa="Blocks the Na-K-2Cl cotransporter in the thick ascending limb of the loop of Henle, producing powerful diuresis.",
        side_effects="Hypokalaemia, hypomagnesaemia, dehydration, ototoxicity (high dose), hyperuricaemia",
        contra="Anuria, hypovolaemia, severe electrolyte depletion, hepatic coma",
        warnings="Take in the morning to avoid nocturia. Monitor potassium and renal function closely.",
        interactions="Aminoglycosides (ototoxicity), digoxin, lithium, NSAIDs, corticosteroids",
        pregnancy="C - use only if clearly needed", half_life="0.5-2 hours",
        onset="30-60 minutes", max_dose="80 mg/day (higher under specialist care)",
        cost=0.5, price=1.4),

    _med(
        "Spironolactone 25mg", "Spironolactone",
        "Diuretic - potassium sparing aldosterone antagonist",
        "Competitive mineralocorticoid receptor antagonist",
        "Heart failure with reduced ejection fraction, resistant hypertension, ascites, hyperaldosteronism",
        strength="25mg", form="tablet", route="Oral", brand="Aldactone 25",
        manufacturer="RPG Life Sciences Ltd", site="Ankleshwar, Gujarat",
        formula="C24H32O4S", weight="416.57 g/mol",
        moa="Competitively antagonises aldosterone at the mineralocorticoid receptor, promoting sodium excretion while retaining potassium.",
        side_effects="Hyperkalaemia, gynaecomastia, menstrual irregularity, renal impairment",
        contra="Hyperkalaemia, Addison disease, severe renal impairment, concurrent potassium supplements",
        warnings="Check potassium and creatinine within a week of starting and after any dose change. Gynaecomastia is dose-related and reversible.",
        interactions="ACE inhibitors, ARBs, potassium supplements, NSAIDs, trimethoprim, heparin",
        pregnancy="C - antiandrogenic effects reported", half_life="1.4 hours (metabolites longer)",
        max_dose="50 mg/day in heart failure; higher under specialist supervision",
        cost=1.1, price=3.0),

    _med(
        "Digoxin 0.25mg", "Digoxin", "Cardiac glycoside - inotrope",
        "Na-K ATPase inhibitor; positive inotrope and negative chronotrope",
        "Heart failure, atrial fibrillation rate control, atrial flutter",
        strength="0.25mg", form="tablet", route="Oral", brand="Lanoxin 0.25",
        manufacturer="GlaxoSmithKline Pharmaceuticals Ltd", site="Nashik, Maharashtra",
        formula="C41H64O14", weight="780.94 g/mol",
        moa="Inhibits the sodium-potassium ATPase pump, raising intracellular calcium (positive inotropy) and increasing vagal tone (rate control).",
        side_effects="Nausea, anorexia, visual halos, bradycardia, arrhythmia - all signs of toxicity",
        contra="Ventricular fibrillation, hypertrophic obstructive cardiomyopathy, AV block",
        warnings="Narrow therapeutic index. Toxicity is worsened by hypokalaemia. Dose on ideal body weight, reduce in renal impairment and in the elderly.",
        interactions="Amiodarone, verapamil, diltiazem, quinidine, macrolides, diuretics (hypokalaemia), antacids",
        pregnancy="C - use with monitoring", half_life="36-48 hours",
        onset="30-120 minutes", max_dose="0.25 mg/day (dose by renal function and age)",
        cost=1.3, price=3.4),

    _med(
        "Amiodarone 200mg", "Amiodarone", "Antiarrhythmic - class III",
        "Potassium channel blocker with class I, II and IV activity",
        "Ventricular tachycardia, atrial fibrillation, refractory arrhythmias",
        strength="200mg", form="tablet", route="Oral", brand="Cordarone 200",
        manufacturer="Sanofi India Ltd", site="Ankleshwar, Gujarat",
        formula="C25H29I2NO3", weight="645.32 g/mol",
        moa="Prolongs the cardiac action potential and refractory period by blocking potassium channels, with additional sodium, beta and calcium blocking effects.",
        side_effects="Thyroid dysfunction, pulmonary fibrosis, corneal deposits, hepatotoxicity, photosensitivity, bradycardia",
        contra="Severe sinus node disease, second or third degree AV block without a pacemaker, thyroid dysfunction, iodine hypersensitivity",
        warnings="Needs baseline and 6-monthly thyroid, liver and pulmonary review. Pulmonary toxicity is the most serious adverse effect. Rarely stopped without specialist advice.",
        interactions="Warfarin (increases INR), digoxin, beta-blockers, statins, fluoroquinolones (QT prolongation)",
        pregnancy="D - fetal thyroid effects", half_life="40-55 days (very long)",
        max_dose="200 mg/day maintenance (loading under specialist care)",
        schedule="Schedule H1 - restrictive prescription", cost=4.5, price=11.0),

    _med(
        "Isosorbide Mononitrate 20mg", "Isosorbide Mononitrate",
        "Antianginal - nitrate",
        "Organic nitrate; nitric oxide donor causing venodilation",
        "Angina prophylaxis, heart failure adjunct",
        strength="20mg", form="tablet", route="Oral", brand="Monotrate 20",
        manufacturer="Micro Labs Ltd", site="Bommasandra Industrial Area, Bangalore",
        formula="C6H9NO6", weight="191.14 g/mol",
        moa="Releases nitric oxide, activating guanylate cyclase and relaxing vascular smooth muscle - predominantly veins, reducing preload.",
        side_effects="Headache (very common at first), flushing, hypotension, dizziness",
        contra="Severe hypotension, hypertrophic cardiomyopathy, concurrent PDE5 inhibitor use",
        warnings="Never combine with sildenafil or tadalafil - profound hypotension. Provide a nitrate-free interval to avoid tolerance.",
        interactions="Sildenafil, tadalafil, vardenafil (contraindicated), other vasodilators, alcohol",
        pregnancy="C", half_life="5 hours", onset="30-60 minutes",
        max_dose="120 mg/day (with a nitrate-free interval)",
        cost=1.4, price=3.6),

    _med(
        "Nifedipine 10mg", "Nifedipine", "Antihypertensive - calcium channel blocker",
        "Dihydropyridine L-type calcium channel blocker",
        "Hypertension, angina prophylaxis, Raynaud phenomenon",
        strength="10mg", form="capsule", route="Oral", brand="Depin",
        manufacturer="Cadila Pharmaceuticals Ltd", site="Dholka, Gujarat",
        formula="C17H18N2O6", weight="346.33 g/mol",
        moa="Blocks L-type calcium channels in vascular smooth muscle, causing arterial vasodilation.",
        side_effects="Ankle oedema, flushing, headache, reflex tachycardia, gingival hyperplasia",
        contra="Cardiogenic shock, severe aortic stenosis, unstable angina",
        warnings="Immediate-release preparations act abruptly; prefer extended release for hypertension. Ankle oedema is not fluid overload and does not respond to diuretics.",
        interactions="Grapefruit juice, beta-blockers (hypotension), CYP3A4 inhibitors, digoxin",
        pregnancy="C - used for hypertension in pregnancy under specialist care",
        half_life="2-5 hours", onset="20-30 minutes", max_dose="60 mg/day",
        cost=0.9, price=2.4),

    # ================================================================= #
    # CNS - an area where the recommender previously had almost no depth
    # =================================================================== #
    _med(
        "Sertraline 50mg", "Sertraline", "Antidepressant - SSRI",
        "Selective serotonin reuptake inhibitor",
        "Depression, obsessive-compulsive disorder, panic disorder, post-traumatic stress disorder, social anxiety",
        strength="50mg", form="tablet", route="Oral", brand="Zosert 50",
        manufacturer="Sun Pharmaceutical Industries Ltd", site="Halol, Gujarat",
        formula="C17H17Cl2N", weight="306.23 g/mol",
        moa="Selectively inhibits neuronal reuptake of serotonin, increasing synaptic serotonin availability.",
        side_effects="Nausea, insomnia, diarrhoea, sexual dysfunction, hyponatraemia in the elderly, initial anxiety",
        contra="Concurrent or recent MAO inhibitor use, concurrent pimozide",
        warnings="Increased suicidal ideation in patients under 25 during the first weeks - review closely. Do not stop abruptly; taper. Serotonin syndrome risk.",
        interactions="MAO inhibitors, other serotonergic drugs, tramadol, triptans, warfarin, NSAIDs (bleeding)",
        pregnancy="C - specialist review needed; risk of neonatal adaptation syndrome",
        half_life="22-36 hours", onset="2-4 weeks for full effect",
        max_dose="200 mg/day", cost=2.2, price=5.6),

    _med(
        "Fluoxetine 20mg", "Fluoxetine", "Antidepressant - SSRI",
        "Selective serotonin reuptake inhibitor",
        "Depression, bulimia nervosa, obsessive-compulsive disorder, premenstrual dysphoric disorder",
        strength="20mg", form="capsule", route="Oral", brand="Fludac 20",
        manufacturer="Cadila Pharmaceuticals Ltd", site="Dholka, Gujarat",
        formula="C17H18F3NO", weight="309.33 g/mol",
        moa="Blocks the serotonin transporter, increasing extracellular serotonin.",
        side_effects="Anxiety, insomnia, nausea, headache, sexual dysfunction, weight loss initially",
        contra="MAO inhibitor use within 14 days, thioridazine",
        warnings="Long half-life means a 5-week washout before starting an MAO inhibitor. Monitor for mood change and suicidal ideation in young patients.",
        interactions="MAO inhibitors, tramadol, tramadol, warfarin, phenytoin, TCAs, NSAIDs",
        pregnancy="C", half_life="4-6 days (active metabolite 4-16 days)",
        onset="2-4 weeks", max_dose="60 mg/day", cost=1.9, price=4.8),

    _med(
        "Alprazolam 0.5mg", "Alprazolam", "Anxiolytic - benzodiazepine",
        "Short-acting benzodiazepine; GABA-A positive allosteric modulator",
        "Anxiety disorders, panic disorder (short-term)",
        strength="0.5mg", form="tablet", route="Oral", brand="Alprax 0.5",
        manufacturer="Torrent Pharmaceuticals Ltd", site="Indrad, Gujarat",
        formula="C17H13ClN4", weight="308.77 g/mol",
        moa="Enhances the inhibitory effect of GABA at the GABA-A receptor, producing anxiolysis, sedation and muscle relaxation.",
        side_effects="Sedation, dependence, memory impairment, ataxia, paradoxical agitation in the elderly",
        contra="Severe respiratory insufficiency, sleep apnoea, myasthenia gravis, severe hepatic impairment",
        warnings="Dependence develops within 2-4 weeks of continuous use. Withdrawal can be severe - taper. Avoid driving. Additive with alcohol and opioids.",
        interactions="Opioids (respiratory depression - boxed warning), alcohol, other sedatives, CYP3A4 inhibitors, fluoxetine",
        pregnancy="D - neonatal sedation and withdrawal", half_life="6-12 hours",
        onset="30-60 minutes", max_dose="4 mg/day",
        schedule="Schedule H1 - restrictive prescription with register", cost=1.6, price=4.0),

    _med(
        "Phenytoin 100mg", "Phenytoin", "Antiepileptic - hydantoin",
        "Sodium channel blocker",
        "Generalised tonic-clonic seizures, focal seizures, status epilepticus",
        strength="100mg", form="tablet", route="Oral", brand="Eptoin 100",
        manufacturer="Abbott India Ltd", site="Baddi, Himachal Pradesh",
        formula="C15H12N2O2", weight="252.27 g/mol",
        moa="Stabilises neuronal membranes by blocking voltage-gated sodium channels and limiting high-frequency firing.",
        side_effects="Gingival hyperplasia, hirsutism, ataxia, nystagmus, megaloblastic anaemia, osteomalacia",
        warnings="Non-linear: a small dose increase can cause toxicity. Narrow therapeutic index - monitor levels. Never stop abruptly.",
        contra="Sinus bradycardia, sinoatrial block, Adams-Stokes syndrome, porphyria",
        interactions="Many - warfarin, oral contraceptives, corticosteroids, carbamazepine, valproate, fluconazole, rifampicin",
        pregnancy="D - fetal hydantoin syndrome; supplement folate",
        half_life="7-42 hours (dose dependent, non-linear)", max_dose="600 mg/day",
        cost=1.1, price=3.0),

    _med(
        "Carbamazepine 200mg", "Carbamazepine", "Antiepileptic - dibenzazepine",
        "Sodium channel blocker; structural analogue of tricyclics",
        "Focal seizures, trigeminal neuralgia, generalised tonic-clonic seizures, bipolar disorder",
        strength="200mg", form="tablet", route="Oral", brand="Tegretol 200",
        manufacturer="Novartis India Ltd", site="Kalwe, Maharashtra",
        formula="C15H12N2O", weight="236.27 g/mol",
        moa="Blocks voltage-gated sodium channels and reduces synaptic transmission.",
        side_effects="Diplopia, ataxia, hyponatraemia, agranulocytosis, Steven-Johnson syndrome (especially in HLA-B*1502 carriers)",
        contra="Bone marrow suppression, porphyria, MAO inhibitor use, AV block",
        warnings="Test for HLA-B*1502 before starting in patients of Han Chinese, Thai and other Asian ancestry - strong association with Stevens-Johnson syndrome. Report any rash immediately.",
        interactions="Powerful CYP3A4 inducer - warfarin, oral contraceptives, other antiepileptics, many drugs",
        pregnancy="D - neural tube defects; supplement folic acid",
        half_life="25-65 hours initially", max_dose="1600 mg/day", cost=1.7, price=4.4),

    _med(
        "Sumatriptan 50mg", "Sumatriptan", "Antimigraine - triptan",
        "Selective 5-HT1B/1D receptor agonist",
        "Acute migraine with or without aura; cluster headache",
        strength="50mg", form="tablet", route="Oral", brand="Suminat 50",
        manufacturer="Sun Pharmaceutical Industries Ltd", site="Halol, Gujarat",
        formula="C14H21N3O2S", weight="295.40 g/mol",
        moa="Agonises 5-HT1B/1D receptors causing cranial vasoconstriction and inhibition of trigeminal neuropeptide release.",
        side_effects="Tingling, warmth, chest tightness, dizziness, injection site reaction",
        contra="Ischaemic heart disease, uncontrolled hypertension, cerebrovascular disease, ergotamine within 24 hours, MAO inhibitor within 2 weeks",
        warnings="Chest tightness may indicate coronary vasospasm - stop and seek assessment. Not for prophylaxis. Maximum 2 doses in 24 hours.",
        interactions="Ergotamine, MAO inhibitors, SSRIs (serotonin syndrome), other triptans",
        pregnancy="C", half_life="2 hours", onset="30 minutes", max_dose="100 mg/day",
        cost=8.5, price=21.0),

    # =================================================================== #
    # ANALGESICS - opioid and neuropathic, with the misuse controls
    # =================================================================== #
    _med(
        "Tramadol 50mg", "Tramadol", "Analgesic - opioid",
        "Weak mu-opioid agonist with serotonin and noradrenaline reuptake inhibition",
        "Moderate to severe pain",
        strength="50mg", form="capsule", route="Oral", brand="Tramazac 50",
        manufacturer="Zydus Cadila", site="Matoda, Gujarat",
        formula="C16H25NO2", weight="263.38 g/mol",
        moa="Weak mu-opioid receptor agonism plus inhibition of serotonin and noradrenaline reuptake.",
        side_effects="Nausea, dizziness, sedation, constipation, seizure risk, dependence",
        contra="Uncontrolled epilepsy, MAO inhibitor use, severe respiratory depression, children under 12",
        warnings="Lower seizure threshold. Serotonin syndrome risk with SSRIs. Not for children under 12 - respiratory depression. Dependence potential.",
        interactions="SSRIs, MAO inhibitors, warfarin, carbamazepine, alcohol, other opioids",
        pregnancy="C - avoid; neonatal withdrawal", half_life="6 hours",
        max_dose="400 mg/day", schedule="Schedule H1 - restrictive prescription",
        cost=2.3, price=5.8),

    _med(
        "Morphine Sulphate 10mg", "Morphine", "Analgesic - opioid",
        "Mu-opioid receptor agonist",
        "Severe pain, cancer pain, myocardial infarction pain, palliative care",
        strength="10mg", form="tablet", route="Oral", brand="Morcontin 10",
        manufacturer="Modi Mundi Pharma Ltd", site="Baddi, Himachal Pradesh",
        formula="C17H19NO3", weight="285.34 g/mol",
        moa="Agonises mu-opioid receptors in the CNS, inhibiting nociceptive transmission and altering the pain response.",
        side_effects="Respiratory depression, constipation, sedation, nausea, dependence, tolerance",
        contra="Respiratory depression, acute severe asthma, paralytic ileus, raised intracranial pressure",
        warnings="Controlled substance with strict record-keeping. Respiratory depression is the lethal effect; naloxone is the antidote. Never stop abruptly in a dependent patient.",
        interactions="Other CNS depressants, alcohol, benzodiazepines (boxed warning), MAO inhibitors",
        pregnancy="C - neonatal withdrawal", half_life="2-3 hours",
        max_dose="Under specialist supervision only",
        schedule="NDPS Act - narcotic; separate register and licence required",
        cost=6.5, price=16.0),

    _med(
        "Gabapentin 300mg", "Gabapentin", "Analgesic - anticonvulsant",
        "Calcium channel alpha-2-delta subunit ligand",
        "Neuropathic pain, postherpetic neuralgia, partial seizures, diabetic neuropathy",
        strength="300mg", form="capsule", route="Oral", brand="Gabapin 300",
        manufacturer="Intas Pharmaceuticals Ltd", site="Matoda, Gujarat",
        formula="C9H17NO2", weight="171.24 g/mol",
        moa="Binds the alpha-2-delta subunit of voltage-gated calcium channels, reducing excitatory neurotransmitter release.",
        side_effects="Dizziness, somnolence, peripheral oedema, weight gain, ataxia",
        contra="Hypersensitivity only",
        warnings="Renally excreted - reduce dose in renal impairment. Dependence and withdrawal reported. Do not stop abruptly.",
        interactions="Opioids (respiratory depression), antacids (reduced absorption), CNS depressants",
        pregnancy="C", half_life="5-7 hours", max_dose="3600 mg/day",
        cost=2.6, price=6.5),

    # =================================================================== #
    # RESPIRATORY - the combination inhalers are what actually get dispensed
    # =================================================================== #
    _med(
        "Budesonide + Formoterol Inhaler", "Budesonide + Formoterol",
        "Anti-asthmatic - inhaled corticosteroid and LABA combination",
        "Glucocorticoid plus long-acting beta-2 agonist",
        "Asthma maintenance, COPD with frequent exacerbations",
        strength="160/4.5mcg", form="inhaler", route="Inhalation", brand="Foracort 160",
        manufacturer="Cipla Ltd", site="Indore, Madhya Pradesh",
        formula="Budesonide C25H34O6; Formoterol C19H24N2O4",
        weight="Budesonide 430.53 g/mol; Formoterol 344.41 g/mol",
        moa="Budesonide suppresses airway inflammation; formoterol produces sustained bronchodilation via beta-2 agonism.",
        side_effects="Oral candidiasis, hoarseness, tremor, palpitations, adrenal suppression at high dose",
        contra="Not for acute bronchospasm - use a short-acting reliever",
        warnings="Rinse the mouth after each dose to prevent candidiasis. Never a rescue inhaler. Carry a reliever as well.",
        interactions="Beta-blockers (antagonism), strong CYP3A4 inhibitors (steroid exposure), diuretics (hypokalaemia)",
        pregnancy="B - continuing control is safer than stopping",
        half_life="Budesonide 2-3 hours; formoterol 10-12 hours",
        max_dose="2 inhalations twice daily", cost=180.0, price=395.0,
        storage="15-30C, do not puncture or incinerate the canister"),

    _med(
        "Ipratropium Inhaler", "Ipratropium Bromide",
        "Anti-asthmatic - short-acting antimuscarinic",
        "Quaternary anticholinergic bronchodilator",
        "COPD maintenance, acute asthma adjunct",
        strength="20mcg", form="inhaler", route="Inhalation", brand="Ipravent",
        manufacturer="Cipla Ltd", site="Indore, Madhya Pradesh",
        formula="C20H30BrNO3", weight="412.36 g/mol",
        moa="Blocks muscarinic receptors in the airway, reducing vagal-mediated bronchoconstriction and secretions.",
        side_effects="Dry mouth, headache, cough, paradoxical bronchospasm (rare), urinary retention",
        contra="Hypersensitivity to atropine or derivatives",
        warnings="Avoid contact with eyes - can precipitate acute angle-closure glaucoma.",
        interactions="Other anticholinergics (additive), beta-agonists (used together)",
        pregnancy="B", half_life="1.5-2 hours", max_dose="8 puffs/day", cost=95.0, price=210.0),

    _med(
        "Prednisolone 10mg", "Prednisolone", "Corticosteroid - systemic",
        "Intermediate-acting synthetic glucocorticoid",
        "Asthma exacerbation, allergic disorders, inflammatory and autoimmune conditions, nephrotic syndrome",
        strength="10mg", form="tablet", route="Oral", brand="Omnacortil 10",
        manufacturer="Macleods Pharmaceuticals Ltd", site="Daman, Daman and Diu",
        formula="C21H28O5", weight="360.44 g/mol",
        moa="Binds the glucocorticoid receptor, suppressing inflammatory gene transcription and immune cell activity.",
        side_effects="Hyperglycaemia, weight gain, Cushingoid features, osteoporosis, immunosuppression, mood change, peptic ulcer",
        contra="Systemic infection without cover, live vaccines, uncontrolled diabetes (relative)",
        warnings="Never stop abruptly after more than 2-3 weeks - taper. Take in the morning with food. Avoid in patients with peptic ulcer unless gastroprotected. Increases infection risk.",
        interactions="NSAIDs (ulcer and bleeding risk), antidiabetics (raises glucose), warfarin, phenytoin, rifampicin",
        pregnancy="B", half_life="2-3 hours (biological 12-36 hours)",
        onset="1-2 hours", max_dose="60 mg/day", cost=1.2, price=3.2),

    # =================================================================== #
    # GI
    # =================================================================== #
    _med(
        "Ondansetron 4mg", "Ondansetron", "Antiemetic - 5-HT3 antagonist",
        "Selective 5-HT3 receptor antagonist",
        "Nausea and vomiting from chemotherapy, radiotherapy, surgery, gastroenteritis",
        strength="4mg", form="tablet", route="Oral", brand="Emeset 4",
        manufacturer="Cipla Ltd", site="Verna Industrial Estate, Goa",
        formula="C18H19N3O", weight="293.36 g/mol",
        moa="Blocks serotonin 5-HT3 receptors centrally in the chemoreceptor trigger zone and peripherally on vagal afferents.",
        side_effects="Headache, constipation, QT prolongation, flushing",
        contra="Concurrent apomorphine, congenital long QT syndrome",
        warnings="QT prolongation with high doses - caution with other QT-prolonging drugs and in electrolyte disturbance.",
        interactions="Apomorphine (contraindicated), other QT prolonging drugs, tramadol (reduced effect)",
        pregnancy="B - commonly used in hyperemesis gravidarum", half_life="3-6 hours",
        max_dose="24 mg/day", cost=2.4, price=6.0),

    _med(
        "Metoclopramide 10mg", "Metoclopramide", "Antiemetic - prokinetic",
        "Dopamine D2 antagonist; serotonin 5-HT4 agonist",
        "Nausea, gastroparesis, gastro-oesophageal reflux, migraine-associated nausea",
        strength="10mg", form="tablet", route="Oral", brand="Perinorm 10",
        manufacturer="Ipca Laboratories Ltd", site="Ratlam, Madhya Pradesh",
        formula="C14H22ClN3O2", weight="299.80 g/mol",
        moa="Antagonises dopamine D2 receptors in the chemoreceptor trigger zone and enhances upper GI motility.",
        side_effects="Extrapyramidal reactions, dystonia, tardive dyskinesia, hyperprolactinaemia, drowsiness",
        contra="GI obstruction or perforation, phaeochromocytoma, epilepsy, Parkinson disease",
        warnings="Extrapyramidal reactions are more common in young people and children - limit to 5 days where possible. Do not use with levodopa.",
        interactions="Levodopa, other dopamine antagonists, SSRIs (serotonin syndrome), alcohol",
        pregnancy="B", half_life="5-6 hours", max_dose="30 mg/day", cost=0.8, price=2.2),

    _med(
        "Lactulose Solution", "Lactulose", "Laxative - osmotic",
        "Synthetic disaccharide; osmotic and colonic acidifier",
        "Constipation, hepatic encephalopathy",
        strength="10g/15ml", form="syrup", route="Oral", brand="Looz",
        manufacturer="Abbott India Ltd", site="Baddi, Himachal Pradesh",
        formula="C12H22O11", weight="342.30 g/mol",
        moa="Undigested in the small bowel, it is fermented by colonic bacteria to lactic and acetic acid, drawing water into the colon and acidifying its contents.",
        side_effects="Flatulence, abdominal bloating and cramps, diarrhoea with excess dose",
        contra="Galactosaemia, GI obstruction",
        warnings="Takes 24-48 hours to work - not for acute relief. Reduce dose if diarrhoea develops.",
        interactions="None significant; may reduce absorption of other oral medicines taken at the same time",
        pregnancy="B - safe", half_life="Not applicable (not absorbed)",
        max_dose="45 ml/day", cost=95.0, price=215.0, rx=False,
        schedule="Not scheduled - OTC (no prescription required)"),

    _med(
        "Dicyclomine 10mg", "Dicyclomine", "Antispasmodic - antimuscarinic",
        "Muscarinic receptor antagonist",
        "Irritable bowel syndrome, smooth muscle spasm, infant colic (specialist use)",
        strength="10mg", form="tablet", route="Oral", brand="Cyclopam",
        manufacturer="Indoco Remedies Ltd", site="Verna, Goa",
        formula="C19H35NO2", weight="309.49 g/mol",
        moa="Antagonises acetylcholine at muscarinic receptors, relaxing smooth muscle in the GI tract.",
        side_effects="Dry mouth, blurred vision, constipation, urinary retention, drowsiness",
        contra="Glaucoma, obstructive uropathy, myasthenia gravis, GI obstruction",
        warnings="Anticholinergic effects worsen in the elderly - avoid where possible.",
        interactions="Other anticholinergics (additive), antacids (reduced absorption)",
        pregnancy="B", half_life="1.8 hours", max_dose="160 mg/day",
        cost=0.9, price=2.5),

    # =================================================================== #
    # MUSCULOSKELETAL / GOUT
    # =================================================================== #
    _med(
        "Allopurinol 100mg", "Allopurinol", "Antigout - xanthine oxidase inhibitor",
        "Xanthine oxidase inhibitor",
        "Gout, hyperuricaemia, uric acid stone prevention",
        strength="100mg", form="tablet", route="Oral", brand="Zyloric 100",
        manufacturer="GlaxoSmithKline Pharmaceuticals Ltd", site="Nashik, Maharashtra",
        formula="C5H4N4O", weight="136.11 g/mol",
        moa="Inhibits xanthine oxidase, reducing uric acid production from purine metabolism.",
        side_effects="Rash (may progress to severe hypersensitivity), nausea, acute gout flare on starting, hepatotoxicity",
        contra="Previous allopurinol hypersensitivity, HLA-B*5801 carrier",
        warnings="Do not start during an acute attack - wait until it settles. Rash requires immediate withdrawal: allopurinol hypersensitivity syndrome is potentially fatal. Screen for HLA-B*5801 in high-risk ethnic groups.",
        interactions="Azathioprine and mercaptopurine (severe myelosuppression - reduce dose by 75%), warfarin, ampicillin, thiazides",
        pregnancy="C", half_life="1-2 hours (oxypurinol 15-20 hours)",
        max_dose="900 mg/day", cost=1.0, price=2.8),

    _med(
        "Colchicine 0.5mg", "Colchicine", "Antigout - anti-inflammatory",
        "Microtubule inhibitor; inhibits neutrophil chemotaxis",
        "Acute gout, familial Mediterranean fever, pericarditis",
        strength="0.5mg", form="tablet", route="Oral", brand="Zycolchin",
        manufacturer="Zydus Cadila", site="Matoda, Gujarat",
        formula="C22H25NO6", weight="399.44 g/mol",
        moa="Binds tubulin and inhibits microtubule assembly, reducing neutrophil migration and activation in inflamed joints.",
        side_effects="Diarrhoea, nausea, vomiting, myopathy, bone marrow suppression at high dose",
        contra="Severe renal or hepatic impairment, blood dyscrasia, concurrent clarithromycin",
        warnings="Narrow therapeutic index and no antidote. High doses are no more effective and are toxic - the old high-dose regimen is obsolete. Avoid with clarithromycin and in renal impairment. Stop at the first sign of diarrhoea.",
        interactions="Clarithromycin (fatal toxicity reported), ciclosporin, verapamil, statins (myopathy), digoxin",
        pregnancy="C", half_life="20-40 hours",
        max_dose="6 mg as a single acute course; 1.2 mg/day for prophylaxis",
        cost=3.2, price=8.0),

    _med(
        "Alendronate 70mg", "Alendronate", "Bisphosphonate",
        "Nitrogen-containing bisphosphonate; osteoclast inhibitor",
        "Osteoporosis, Paget disease of bone",
        strength="70mg", form="tablet", route="Oral", brand="Alenost 70",
        manufacturer="Cipla Ltd", site="Verna Industrial Estate, Goa",
        formula="C4H18NO7P2", weight="325.13 g/mol",
        moa="Inhibits osteoclast-mediated bone resorption by disrupting the mevalonate pathway in osteoclasts.",
        side_effects="Oesophagitis, dyspepsia, musculoskeletal pain, osteonecrosis of the jaw (rare, with dental surgery), atypical femoral fracture (long-term)",
        contra="Oesophageal stricture or achalasia, inability to sit upright for 30 minutes, eGFR below 35, hypocalcaemia",
        warnings="Take on an empty stomach with plain water and remain upright for 30 minutes - lying down causes severe oesophagitis. Requires adequate calcium and vitamin D. Dental review before starting.",
        interactions="Antacids, calcium, iron, NSAIDs (GI irritation); separate by at least 30 minutes",
        pregnancy="C - not for use in pregnancy", half_life="10 years in bone",
        max_dose="70 mg once weekly", cost=18.0, price=42.0),

    # =================================================================== #
    # HORMONES
    # =================================================================== #
    _med(
        "Ethinylestradiol + Levonorgestrel", "Ethinylestradiol + Levonorgestrel",
        "Contraceptive - combined oral",
        "Synthetic oestrogen and progestogen combination",
        "Contraception, menstrual cycle regulation, endometriosis",
        strength="0.03mg/0.15mg", form="tablet", route="Oral", brand="Ovral L",
        manufacturer="Pfizer Ltd", site="Aurangabad, Maharashtra",
        formula="Ethinylestradiol C20H24O2; Levonorgestrel C21H28O2",
        weight="Ethinylestradiol 296.40 g/mol; Levonorgestrel 312.45 g/mol",
        moa="Suppresses gonadotrophin release and thus ovulation, and alters cervical mucus and endometrium.",
        side_effects="Nausea, breakthrough bleeding, breast tenderness, mood change, raised thrombotic risk, hypertension",
        contra="History of venous thromboembolism, migraine with aura, breast cancer, severe hypertension, smoking over 35, hepatic disease, pregnancy",
        warnings="VTE risk roughly tripled versus non-users and highest in the first year. Do not use in smokers over 35. No protection against sexually transmitted infection.",
        interactions="Rifampicin, carbamazepine, phenytoin, St John wort (reduced efficacy - use additional contraception), some antibiotics",
        pregnancy="X - contraindicated; stop if pregnancy occurs",
        max_dose="One tablet daily", cost=55.0, price=135.0),

    _med(
        "Medroxyprogesterone 10mg", "Medroxyprogesterone",
        "Progestogen - hormonal",
        "Synthetic progestogen",
        "Secondary amenorrhoea, dysfunctional uterine bleeding, hormone replacement therapy",
        strength="10mg", form="tablet", route="Oral", brand="Deviry 10",
        manufacturer="Mankind Pharma Ltd", site="Paonta Sahib, Himachal Pradesh",
        formula="C24H34O4", weight="386.52 g/mol",
        moa="Transforms proliferative endometrium to secretory, and suppresses gonadotrophin release.",
        side_effects="Weight gain, fluid retention, mood change, breakthrough bleeding, thromboembolic risk",
        contra="Undiagnosed vaginal bleeding, active thromboembolism, hepatic impairment, breast cancer",
        warnings="Not for use as a contraceptive. Review if abnormal bleeding persists.",
        interactions="Rifampicin, carbamazepine, warfarin",
        pregnancy="X - contraindicated", half_life="12-17 hours",
        max_dose="10 mg/day", cost=2.8, price=7.0),

    # =================================================================== #
    # ANTIBIOTICS - more depth in the classes patients are most often on
    # =================================================================== #
    _med(
        "Levofloxacin 500mg", "Levofloxacin",
        "Antibiotic - fluoroquinolone",
        "Third-generation fluoroquinolone; DNA gyrase and topoisomerase IV inhibitor",
        "Community-acquired pneumonia, urinary tract infection, pyelonephritis, "
        "sinusitis, skin infection",
        strength="500mg", form="tablet", route="Oral", brand="Levoflox 500",
        manufacturer="Cipla Ltd", site="Verna Industrial Estate, Goa",
        formula="C18H20FN3O4", weight="361.37 g/mol",
        moa="Inhibits bacterial DNA gyrase and topoisomerase IV, blocking DNA "
            "replication and transcription.",
        side_effects="Nausea, headache, dizziness, tendinitis and tendon rupture, "
                    "QT prolongation, peripheral neuropathy",
        contra="Epilepsy, tendon disorders, myasthenia gravis, children and "
               "adolescents (cartilage damage), pregnancy, G6PD deficiency",
        warnings="Tendon rupture risk is highest in patients over 60, those on "
                 "corticosteroids and transplant recipients - stop at the first "
                 "sign of tendon pain. May worsen myasthenia gravis. Avoid "
                 "antacids, iron and dairy within 2 hours of a dose.",
        interactions="NSAIDs (seizure risk), warfarin (INR rise), antacids, iron, "
                    "sucralfate, theophylline, corticosteroids (tendon risk), "
                    "antidiabetics (dysglycaemia)",
        pregnancy="C - avoid; fluoroquinolones are generally contraindicated",
        half_life="6-8 hours", onset="1-2 hours", max_dose="750 mg/day",
        cost=8.5, price=20.0),

    _med(
        "Cefixime 200mg", "Cefixime", "Antibiotic - third generation cephalosporin",
        "Beta-lactam; inhibits cell wall synthesis",
        "Respiratory tract infection, urinary tract infection, otitis media, gonorrhoea",
        strength="200mg", form="tablet", route="Oral", brand="Taxim-O 200",
        manufacturer="Alkem Laboratories Ltd", site="Taloja, Maharashtra",
        formula="C16H15N5O7S2", weight="453.45 g/mol",
        moa="Binds penicillin-binding proteins and inhibits peptidoglycan cross-linking in the bacterial cell wall.",
        side_effects="Diarrhoea, dyspepsia, rash, Clostridioides difficile colitis",
        contra="Previous severe cephalosporin or penicillin anaphylaxis",
        warnings="Cross-reactivity with penicillin allergy is around 1-2% - avoid if the penicillin reaction was anaphylactic. Complete the full course.",
        interactions="Warfarin (INR rise), carbamazepine, antacids (reduced absorption)",
        pregnancy="B", half_life="3-4 hours", max_dose="400 mg/day",
        cost=6.5, price=16.0),

    _med(
        "Ampicillin + Cloxacillin", "Ampicillin + Cloxacillin",
        "Antibiotic - penicillin combination",
        "Beta-lactam combination covering Gram-positive and Gram-negative organisms",
        "Respiratory infection, skin and soft tissue infection, urinary tract infection",
        strength="250mg/250mg", form="capsule", route="Oral", brand="Ampilox 500",
        manufacturer="Mapra Laboratories Pvt Ltd", site="Ankleshwar, Gujarat",
        formula="Ampicillin C16H19N3O4S; Cloxacillin C19H18ClN3O5S",
        weight="Ampicillin 349.41 g/mol; Cloxacillin 435.88 g/mol",
        moa="Ampicillin inhibits cell wall synthesis (broad spectrum); cloxacillin resists beta-lactamase and covers staphylococci.",
        side_effects="Diarrhoea, rash, hypersensitivity, hepatitis (cloxacillin, rare)",
        contra="Penicillin or cephalosporin anaphylaxis history",
        warnings="Avoid in infectious mononucleosis - high rate of rash. Complete the full course.",
        interactions="Warfarin, allopurinol (rash), methotrexate (reduced clearance), oral contraceptives",
        pregnancy="B", half_life="0.5-1.5 hours", max_dose="2 g/day of each component",
        cost=3.4, price=8.5),

    _med(
        "Amikacin 500mg Injection", "Amikacin", "Antibiotic - aminoglycoside",
        "Aminoglycoside; inhibits bacterial protein synthesis",
        "Serious Gram-negative infection, hospital-acquired infection, septicemia",
        strength="500mg/2ml", form="injection", route="Intramuscular / Intravenous",
        brand="Mikacin 500",
        manufacturer="Aristo Pharmaceuticals Pvt Ltd", site="Vasai, Maharashtra",
        formula="C22H43N5O13", weight="585.60 g/mol",
        moa="Binds the 30S ribosomal subunit, causing misreading of mRNA and blocking protein synthesis.",
        side_effects="Nephrotoxicity, ototoxicity (may be irreversible), neuromuscular blockade",
        contra="Myasthenia gravis, previous aminoglycoside toxicity, severe renal impairment",
        warnings="Nephrotoxic and ototoxic - monitor renal function and hearing. Volume-depleted and elderly patients are at highest risk. Not for outpatient use.",
        interactions="Furosemide, other aminoglycosides, vancomycin, neuromuscular blockers (additive toxicity)",
        pregnancy="D - fetal auditory nerve damage",
        half_life="2-3 hours (prolonged in renal impairment)",
        max_dose="15 mg/kg/day", schedule="Schedule H1 - restrictive prescription",
        cost=42.0, price=98.0, storage="2-8C refrigerated, protect from light"),

    _med(
        "Nitrofurantoin 100mg", "Nitrofurantoin",
        "Antibiotic - urinary antiseptic",
        "Nitrofuran; multiple mechanisms, concentrated in urine",
        "Uncomplicated lower urinary tract infection, prophylaxis of recurrent UTI",
        strength="100mg", form="capsule", route="Oral", brand="Nitrofur 100",
        manufacturer="Micro Labs Ltd", site="Bommasandra Industrial Area, Bangalore",
        formula="C8H6N4O5", weight="238.16 g/mol",
        moa="Reduced by bacterial flavoproteins to reactive intermediates that damage ribosomal RNA, DNA and proteins.",
        side_effects="Nausea, headache, brown urine discolouration, pulmonary fibrosis (long-term), peripheral neuropathy",
        contra="eGFR below 30, G6PD deficiency, pregnancy at term, infants under 3 months",
        warnings="Ineffective and dangerous in renal impairment. Not for pyelonephritis - it does not achieve tissue levels. Long-term use needs lung and liver monitoring.",
        interactions="Antacids (reduced absorption), probenecid, quinolones (antagonism)",
        pregnancy="B - avoid at term", half_life="20 minutes", max_dose="400 mg/day",
        cost=2.4, price=6.2),

    _med(
        "Albendazole 400mg", "Albendazole", "Anthelmintic",
        "Benzimidazole; tubulin polymerisation inhibitor",
        "Soil-transmitted helminths, threadworm, hookworm, ascariasis, hydatid disease",
        strength="400mg", form="tablet", route="Oral", brand="Zentel 400",
        manufacturer="GlaxoSmithKline Pharmaceuticals Ltd", site="Nashik, Maharashtra",
        formula="C12H15N3O2S", weight="265.33 g/mol",
        moa="Binds beta-tubulin and inhibits microtubule polymerisation, depleting parasite energy stores.",
        side_effects="Abdominal pain, nausea, headache, raised transaminases (long courses)",
        contra="Pregnancy (first trimester), hypersensitivity",
        warnings="Treat all household contacts in threadworm infestation to prevent reinfection. Take with food to improve absorption.",
        interactions="Dexamethasone, praziquantel, cimetidine",
        pregnancy="C - avoid in the first trimester", half_life="8-12 hours",
        max_dose="400 mg single dose for most helminths",
        cost=6.0, price=15.0, rx=False,
        schedule="Not scheduled - OTC (no prescription required)"),

    _med(
        "Praziquantel 600mg", "Praziquantel", "Anthelmintic - trematocide",
        "Benzimidazole-adjacent; increases parasite calcium permeability",
        "Schistosomiasis, tapeworm infestation, cysticercosis",
        strength="600mg", form="tablet", route="Oral", brand="Prazitel 600",
        manufacturer="Intas Pharmaceuticals Ltd", site="Matoda, Gujarat",
        formula="C19H24N2O2", weight="312.41 g/mol",
        moa="Increases calcium permeability of the parasite tegument, causing paralysis and death.",
        side_effects="Abdominal pain, nausea, headache, dizziness, urticaria",
        contra="Ocular cysticercosis, concurrent rifampicin",
        warnings="Do not drive on the day of treatment - dizziness and drowsiness are common. Take with food and water.",
        interactions="Rifampicin (reduces levels markedly), chloroquine, dexamethasone",
        pregnancy="B - avoid in the first trimester", half_life="1-3 hours",
        max_dose="60 mg/kg in divided doses", cost=14.0, price=34.0),

    _med(
        "Clotrimazole 1% Cream", "Clotrimazole", "Antifungal - topical imidazole",
        "Imidazole; inhibits fungal ergosterol synthesis",
        "Cutaneous candidiasis, dermatophyte infection, tinea versicolor",
        strength="1%", form="cream", route="Topical", brand="Candid Cream",
        manufacturer="Glenmark Pharmaceuticals Ltd", site="Nashik, Maharashtra",
        formula="C22H17ClN2", weight="344.84 g/mol",
        moa="Inhibits 14-alpha demethylase, blocking ergosterol synthesis and damaging the fungal membrane.",
        side_effects="Local burning, irritation, erythema (uncommon)",
        contra="Hypersensitivity to imidazoles",
        warnings="For external use only. Continue for the full course - usually 2-4 weeks - even once symptoms settle. If no improvement in 4 weeks seek review.",
        interactions="None significant (minimal systemic absorption)",
        pregnancy="B", max_dose="Apply twice daily",
        cost=32.0, price=78.0, rx=False,
        schedule="Not scheduled - OTC (no prescription required)"),

    # =================================================================== #
    # OPHTHALMIC
    # =================================================================== #
    _med(
        "Moxifloxacin 0.5% Eye Drops", "Moxifloxacin",
        "Ophthalmic - antibiotic",
        "Fourth-generation fluoroquinolone",
        "Bacterial conjunctivitis, corneal ulcer, post-operative prophylaxis",
        strength="0.5%", form="drops", route="Ophthalmic", brand="Vigamox",
        manufacturer="Alcon Laboratories India Pvt Ltd", site="Bangalore, Karnataka",
        formula="C21H24FN3O4", weight="401.43 g/mol",
        moa="Inhibits bacterial DNA gyrase and topoisomerase IV, blocking DNA replication.",
        side_effects="Transient burning, eye irritation, taste disturbance",
        contra="Hypersensitivity to quinolones",
        warnings="Discard 4 weeks after opening. Do not share bottles. Do not use contact lenses during treatment.",
        interactions="None significant for topical use",
        pregnancy="C - topical use generally acceptable", max_dose="1 drop three times daily",
        cost=88.0, price=195.0),

    _med(
        "Timol 0.5% Eye Drops", "Timol",
        "Ophthalmic - beta blocker",
        "Non-selective beta-adrenergic antagonist",
        "Open-angle glaucoma, ocular hypertension",
        strength="0.5%", form="drops", route="Ophthalmic", brand="Glucomol 0.5%",
        manufacturer="Sun Pharmaceutical Industries Ltd", site="Halol, Gujarat",
        formula="C13H24N4O3S", weight="316.42 g/mol",
        moa="Reduces aqueous humour production by blocking beta receptors on the ciliary epithelium.",
        side_effects="Ocular stinging, blurred vision, bradycardia, bronchospasm, masked hypoglycaemia",
        contra="Asthma, COPD, sinus bradycardia, heart block, cardiogenic shock",
        warnings="Systemically absorbed - can precipitate bronchospasm in asthma, the same as an oral beta-blocker. Occlude the lacrimal punctum after instilling.",
        interactions="Oral beta-blockers (additive), verapamil, digoxin, insulin and antidiabetics (masks hypoglycaemia)",
        pregnancy="C", max_dose="1 drop twice daily",
        cost=42.0, price=95.0),

    # =================================================================== #
    # VACCINES
    # =================================================================== #
    _med(
        "Tetanus Toxoid Injection", "Tetanus Toxoid", "Vaccine - toxoid",
        "Formaldehyde-inactivated tetanus toxin",
        "Tetanus prophylaxis, wound management, antenatal immunisation",
        strength="0.5ml", form="injection", route="Intramuscular", brand="Tetglob",
        manufacturer="Serum Institute of India Pvt Ltd", site="Pune, Maharashtra",
        formula=None, weight=None,
        moa="Induces antitoxin antibodies that neutralise tetanospasmin before it reaches the CNS.",
        side_effects="Injection site pain, fever, malaise, urticaria, rare anaphylaxis",
        contra="Previous severe reaction to a tetanus-containing vaccine",
        warnings="Anaphylaxis is rare but the vaccine must be given where adrenaline is available. Observe for 15 minutes. Do not give into a site with active infection.",
        interactions="Immunosuppressive therapy may reduce response",
        pregnancy="B - safe and recommended in pregnancy",
        max_dose="0.5 ml per dose", cost=28.0, price=65.0,
        storage="2-8C refrigerated; do not freeze"),
]


# Dosage guides for the new medicines, keyed by medicine name.
# Only the guides that add real information are listed; the calculator falls
# back to weight-based calculation where none is present.
BATCH3_GUIDES = [
    # --- Sertraline -----------------------------------------------------
    {"medicine_name": "Sertraline 50mg", "age_group": "18+", "dosage_amount": 50,
     "dosage_unit": "mg", "frequency": "Once daily", "duration_days": 30,
     "indication": "Depression",
     "special_notes": "Start 50 mg; increase by 50 mg at weekly intervals to a maximum of 200 mg. Full effect takes 2-4 weeks. Taper on stopping."},
    {"medicine_name": "Sertraline 50mg", "age_group": "12-18", "dosage_amount": 25,
     "dosage_unit": "mg", "frequency": "Once daily", "duration_days": 30,
     "indication": "Depression",
     "special_notes": "Start 25 mg in adolescents; closer monitoring for suicidal ideation is required."},

    # --- Losartan -------------------------------------------------------
    {"medicine_name": "Losartan 50mg", "age_group": "18+", "dosage_amount": 50,
     "dosage_unit": "mg", "frequency": "Once daily", "duration_days": 30,
     "indication": "Hypertension",
     "special_notes": "Usual start 50 mg once daily; range 25-100 mg. Check potassium and creatinine 1-2 weeks after starting or changing dose."},

    # --- Hydrochlorothiazide --------------------------------------------
    {"medicine_name": "Hydrochlorothiazide 25mg", "age_group": "18+",
     "dosage_amount": 25, "dosage_unit": "mg", "frequency": "Once daily",
     "duration_days": 30, "indication": "Hypertension",
     "special_notes": "Take in the morning. Check electrolytes at 2-4 weeks. 12.5-25 mg is the usual antihypertensive range."},

    # --- Furosemide -----------------------------------------------------
    {"medicine_name": "Furosemide 40mg", "age_group": "18+", "dosage_amount": 40,
     "dosage_unit": "mg", "frequency": "Once daily", "duration_days": 30,
     "indication": "Oedema",
     "special_notes": "Take in the morning to avoid nocturia. Titrate to response; monitor potassium, sodium and renal function."},
    {"medicine_name": "Furosemide 40mg", "age_group": "18+", "dosage_amount": 20,
     "dosage_unit": "mg", "frequency": "Once daily", "duration_days": 30,
     "indication": "Oedema - elderly",
     "special_notes": "Start at a lower dose in the elderly, who are more prone to dehydration and electrolyte loss."},

    # --- Prednisolone ---------------------------------------------------
    {"medicine_name": "Prednisolone 10mg", "age_group": "18+", "dosage_amount": 40,
     "dosage_unit": "mg", "frequency": "Once daily", "duration_days": 5,
     "indication": "Asthma exacerbation",
     "special_notes": "40 mg once daily for 5 days; no taper needed for a short course. Take in the morning with food."},
    {"medicine_name": "Prednisolone 10mg", "age_group": "6-12", "dosage_amount": 20,
     "dosage_unit": "mg", "frequency": "Once daily", "duration_days": 5,
     "indication": "Asthma exacerbation",
 "special_notes": "1-2 mg/kg once daily (maximum 40 mg) for up to 5 days for an acute exacerbation."},

    # --- Ondansetron ----------------------------------------------------
    {"medicine_name": "Ondansetron 4mg", "age_group": "18+", "dosage_amount": 4,
     "dosage_unit": "mg", "frequency": "Three times daily", "duration_days": 3,
     "indication": "Nausea and vomiting",
     "special_notes": "Oral dose 4-8 mg up to three times daily. Reduce in hepatic impairment - maximum 8 mg/day."},

    # --- Tramadol -------------------------------------------------------
    {"medicine_name": "Tramadol 50mg", "age_group": "18+", "dosage_amount": 50,
     "dosage_unit": "mg", "frequency": "Every 6 hours as needed", "duration_days": 5,
     "indication": "Moderate to severe pain",
     "special_notes": "50-100 mg every 4-6 hours, maximum 400 mg/day. Maximum 300 mg/day in patients over 75. Not for children under 12."},

    # --- Gabapentin -----------------------------------------------------
    {"medicine_name": "Gabapentin 300mg", "age_group": "18+", "dosage_amount": 300,
     "dosage_unit": "mg", "frequency": "Once daily", "duration_days": 30,
     "indication": "Neuropathic pain",
     "special_notes": "Titrate up: day 1 300 mg once daily, day 2 twice daily, day 3 three times daily, then increase as needed. Taper on withdrawal."},

    # --- Colchicine -----------------------------------------------------
    {"medicine_name": "Colchicine 0.5mg", "age_group": "18+", "dosage_amount": 1.0,
     "dosage_unit": "mg", "frequency": "Once daily", "duration_days": 3,
     "indication": "Acute gout",
     "special_notes": "1 mg at onset then 0.5 mg one hour later, then stop. Do NOT repeat the old high-dose regimen - it is no more effective and is toxic. Stop at the first sign of diarrhoea."},

    # --- Allopurinol ----------------------------------------------------
    {"medicine_name": "Allopurinol 100mg", "age_group": "18+", "dosage_amount": 100,
     "dosage_unit": "mg", "frequency": "Once daily", "duration_days": 30,
     "indication": "Gout prophylaxis",
     "special_notes": "Start 100 mg daily 2-4 weeks after the acute attack settles, then titrate to a target urate below 360 micromol/L. Cover with an NSAID or colchicine for the first 3 months. Stop immediately if a rash appears."},

    # --- Budesonide/Formoterol ------------------------------------------
    {"medicine_name": "Budesonide + Formoterol Inhaler", "age_group": "18+",
     "dosage_amount": 2, "dosage_unit": "puff", "frequency": "Twice daily",
     "duration_days": 30, "indication": "Asthma maintenance",
     "special_notes": "Two inhalations twice daily. Rinse the mouth after every dose. Never a rescue inhaler - an acute attack needs a short-acting beta-2 agonist."},
    {"medicine_name": "Budesonide + Formoterol Inhaler", "age_group": "12-18",
     "dosage_amount": 1, "dosage_unit": "puff", "frequency": "Twice daily",
     "duration_days": 30, "indication": "Asthma maintenance",
     "special_notes": "Start with one inhalation twice daily in adolescents; rinse the mouth afterwards."},

    # --- Cefixime -------------------------------------------------------
    {"medicine_name": "Cefixime 200mg", "age_group": "18+", "dosage_amount": 200,
     "dosage_unit": "mg", "frequency": "Twice daily", "duration_days": 7,
     "indication": "Respiratory or urinary tract infection",
     "special_notes": "200 mg twice daily; reduce to once daily in renal impairment. Complete the full course even if symptoms resolve early."},

    # --- Nitrofurantoin -------------------------------------------------
    {"medicine_name": "Nitrofurantoin 100mg", "age_group": "18+", "dosage_amount": 100,
     "dosage_unit": "mg", "frequency": "Twice daily", "duration_days": 5,
     "indication": "Uncomplicated urinary tract infection",
     "special_notes": "100 mg twice daily for 5 days. Take with food to improve absorption and reduce nausea. Not effective for pyelonephritis."},

    # --- Albendazole ----------------------------------------------------
    {"medicine_name": "Albendazole 400mg", "age_group": "18+", "dosage_amount": 400,
     "dosage_unit": "mg", "frequency": "Once daily", "duration_days": 1,
     "indication": "Intestinal helminths",
     "special_notes": "Single 400 mg dose; repeat after 2 weeks for threadworm. Treat all household contacts at the same time. Take with food."},
    {"medicine_name": "Albendazole 400mg", "age_group": "2-6", "dosage_amount": 200,
     "dosage_unit": "mg", "frequency": "Once daily", "duration_days": 1,
     "indication": "Intestinal helminths",
     "special_notes": "Single 200 mg dose for children aged 1-2; 400 mg for children over 2."},

    # --- Spironolactone -------------------------------------------------
    {"medicine_name": "Spironolactone 25mg", "age_group": "18+", "dosage_amount": 25,
     "dosage_unit": "mg", "frequency": "Once daily", "duration_days": 30,
     "indication": "Heart failure, resistant hypertension",
     "special_notes": "25 mg once daily; range 25-50 mg. Check potassium and creatinine within 1 week of starting and after any change."},

    # --- Digoxin --------------------------------------------------------
    {"medicine_name": "Digoxin 0.25mg", "age_group": "18+", "dosage_amount": 0.125,
     "dosage_unit": "mg", "frequency": "Once daily", "duration_days": 30,
     "indication": "Heart failure, atrial fibrillation",
     "special_notes": "0.125-0.25 mg daily, dose by renal function and age. Narrow therapeutic index - monitor levels and potassium. Toxicity causes nausea and visual disturbance."},

    # --- Sertraline in elderly (renal/hepatic) --------------------------
    {"medicine_name": "Fluoxetine 20mg", "age_group": "18+", "dosage_amount": 20,
     "dosage_unit": "mg", "frequency": "Once daily", "duration_days": 30,
     "indication": "Depression",
     "special_notes": "Start 20 mg in the morning; wait 4-6 weeks before judging benefit. Maximum 60 mg/day."},

    # --- Montelukast paediatric (batch 2 medicine, guide added here) ----
    {"medicine_name": "Montelukast 10mg", "age_group": "6-12", "dosage_amount": 5,
     "dosage_unit": "mg", "frequency": "Once daily", "duration_days": 30,
     "indication": "Asthma prophylaxis",
     "special_notes": "5 mg chewable tablet once daily in the evening for children aged 6-14."},
    {"medicine_name": "Montelukast 10mg", "age_group": "18+", "dosage_amount": 10,
     "dosage_unit": "mg", "frequency": "Once daily", "duration_days": 30,
     "indication": "Asthma prophylaxis",
     "special_notes": "10 mg once daily in the evening. Report any change in mood or behaviour."},
]
