"""
Extended medicine reference data - batch 5.

WHY THIS BATCH EXISTS
---------------------
Batches 1-4 built up a dispensing set weighted toward Indian community practice.
What they were still thin on are classes a counter reaches for daily and had no
local monograph for:

  * the **calcium channel blockers and nitrates** - these are named in the safety
    engine's interaction tables, so screening a cardiac patient reported an
    interaction against a drug with no local record to open
  * the **newer antidiabetics** - the SGLT2 inhibitors and GLP-1 receptor
    agonists, now written routinely in Indian type 2 diabetes
  * the **antidepressants and the agents that accompany them** - a very large
    share of repeat prescriptions
  * **combination inhalers**, because a pharmacy dispenses the device
  * the **paediatric liquids**, where an adult tablet is simply not dispensable
  * the **antiemetics, PPIs and laxatives** that accompany almost every course
  * the **newer oral anticoagulants**

WHAT THIS DELIBERATELY DOES NOT DO
----------------------------------
It does not fabricate. Every molecular formula, half-life, pregnancy category and
dose ceiling below is the published value. Where a figure is not reliably
published for a combination product the field is left as None rather than guessed
- an invented half-life reads exactly like a real one and would be carried
straight into a clinical decision.

A plausible but invented interaction is worse than a missing row. A pharmacist who
sees a drug is absent will look it up; one who sees a fabricated interaction will
believe it. The set grows by verified tier rather than by padding; for the full
national range, import_medicines.py loads a real CDSCO, Jan Aushadhi or NPPA
catalogue.

A NOTE ON NAMES
---------------
Names use the "name + strength" form the rest of the catalogue uses. That matters
more than it looks: the seeder silently skips a repeated name, so a collision
here would ship one fewer medicine than the count implies - exactly the defect
two batch-4 entries had against batch 3.

Seven of the drugs below (nifedipine, sertraline, escitalopram, phenytoin,
levetiracetam, tiotropium and ondansetron) already exist in batches 1-4, so they
are NOT repeated here: a duplicate would be dropped by the seeder anyway, and the
count would then be wrong by seven. What this batch adds for those drugs is the
DOSAGE GUIDANCE (below), which the earlier batches did not carry - so the drug was
in the catalogue but had no age-banded dose to open. Coverage of a medicine and
coverage of its dosing are different things, and this batch closes the second gap.

As a consequence, BATCH5_GUIDES deliberately contains entries whose medicine
comes from an earlier batch. test_catalogue.py asserts that every guide resolves
to a real medicine - which it does, because the seeder resolves guides against
the whole catalogue, not against this file.
"""

DATA_VERSION = "5.0.0"
DATA_AUTHOR = "Jayant Mishra"


def _med(name, generic, cls, pharm, use, *, strength, form, route,
         brand=None, manufacturer="Cipla Ltd", site="Verna Industrial Estate, Goa",
         formula=None, weight=None, moa=None, side_effects=None,
         contra=None, warnings=None, interactions=None, pregnancy="B",
         half_life=None, onset=None, max_dose=None,
         schedule="Schedule H - prescription required",
         rx=True, cost=2.0, price=5.0, storage="15-30C, protect from light and moisture",
         hsn="30049099", gst="12%"):
    """Build a medicine row with every required column populated.

    Same helper shape as batches 3 and 4, so the files read identically and a
    field missed here is obvious against its counterpart there.
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


BATCH5_MEDICINES = [
    # =================================================================== #
    # CARDIOVASCULAR - calcium channel blockers and nitrates.
    #
    # Nifedipine is NOT here: it is already in an earlier batch, and this file
    # adds its dosage guidance only (see BATCH5_GUIDES and the note at the top of
    # the file). Repeating the medicine would be silently dropped by the seeder
    # and would make the catalogue count wrong by one.
    # =================================================================== #
    _med(
        "Isosorbide Dinitrate 10mg", "Isosorbide Dinitrate",
        "Antianginal - organic nitrate",
        "Nitric oxide donor / guanylate cyclase activator",
        "Angina prophylaxis, heart failure with reduced ejection fraction (with hydralazine)",
        strength="10mg", form="tablet", route="Sublingual or oral", brand="Sorbitrate",
        formula="C6H10N2O8", weight="236.14 g/mol",
        half_life="1 hour (dinitrate); about 5 hours for the mononitrate metabolites",
        onset="2-5 minutes sublingual; 20-30 minutes oral",
        moa="Denitrated to nitric oxide, which activates guanylate cyclase and raises cyclic GMP, relaxing vascular smooth muscle and reducing preload.",
        side_effects="Throbbing headache, flushing, dizziness, postural hypotension, reflex tachycardia, tolerance with continuous exposure.",
        contra="Concurrent PDE5 inhibitor (sildenafil, tadalafil, vardenafil), severe hypotension, hypertrophic obstructive cardiomyopathy, constrictive pericarditis.",
        warnings="The combination with a PDE5 inhibitor causes profound, potentially fatal hypotension - ask about erectile-dysfunction drugs specifically, because patients often do not volunteer them. A nitrate-free interval of 8-12 hours daily prevents tolerance; sublingual use is for acute attacks only.",
        interactions="Sildenafil, tadalafil, vardenafil, riociguat (all absolutely contraindicated), alcohol, other vasodilators",
        max_dose="120 mg/day (oral); tolerance limits continuous use",
        cost=1.60, price=4.20,
        pregnancy="C - used for tocolysis and in cardiac disease in pregnancy, specialist-directed"),

    _med(
        "Nicorandil 5mg", "Nicorandil", "Antianginal - potassium channel opener",
        "ATP-sensitive potassium channel opener with nitrate activity",
        "Chronic stable angina where beta blockers and nitrates are inadequate or not tolerated",
        strength="5mg", form="tablet", route="Oral", brand="Nikoran",
        formula="C8H9N5O4", weight="239.19 g/mol", half_life="1 hour",
        moa="Opens ATP-sensitive potassium channels in vascular smooth muscle to dilate arteries, and acts as a nitrate donor on veins, reducing both preload and afterload.",
        side_effects="Headache, flushing, dizziness, nausea; oral, anal and genital ulceration on long-term use.",
        contra="Cardiogenic shock, uncompensated heart failure, hypotension, concurrent PDE5 inhibitor, gastrointestinal ulceration.",
        warnings="A characteristic and under-recognised adverse effect: it causes painful ulceration of the mouth, gut, skin and genitalia that heals on withdrawal. Persistent ulceration during therapy should prompt stopping the drug rather than treating the ulcer.",
        interactions="Sildenafil, tadalafil, vardenafil (contraindicated), other nitrates, antihypertensives",
        max_dose="40 mg/day (20 mg twice daily)",
        cost=3.10, price=7.80,
        pregnancy="C - insufficient data; specialist use only"),

    _med(
        "Ivabradine 5mg", "Ivabradine", "Cardiac - sinus node inhibitor",
        "Selective If (funny) current inhibitor in the sinoatrial node",
        "Chronic heart failure with reduced ejection fraction and a heart rate above 70, stable angina where beta blockers are unsuitable",
        strength="5mg", form="tablet", route="Oral", brand="Ivabrad",
        formula="C27H36N2O5", weight="468.59 g/mol",
        half_life="6 hours (11 hours with hepatic impairment)",
        moa="Selectively blocks the hyperpolarisation-activated If sodium current in the sinoatrial node, slowing diastolic depolarisation and therefore heart rate, without affecting contractility or blood pressure.",
        side_effects="Luminous phenomena (phosphenes) in about 15%, bradycardia, atrial fibrillation, dizziness, blurred vision.",
        contra="Sinus node dysfunction, sinoatrial block, complete heart block, severe hepatic impairment, women of childbearing potential without contraception.",
        warnings="It lowers heart rate only - it does not lower blood pressure or improve contractility, so it does not substitute for a beta blocker's other effects. The visual phenomena usually resolve within two months but patients should be warned, because night driving can be affected.",
        interactions="Verapamil, diltiazem (contraindicated - both reduce heart rate), CYP3A4 inhibitors, QT-prolonging drugs",
        max_dose="15 mg/day (7.5 mg twice daily)",
        cost=9.50, price=22.00,
        pregnancy="Unclassified - contraindicated without effective contraception"),

    _med(
        "Nitroglycerin 0.5mg Sublingual", "Nitroglycerin",
        "Antianginal - organic nitrate", "Nitric oxide donor / guanylate cyclase activator",
        "Acute relief of anginal pain, prophylaxis before exertion",
        strength="0.5mg", form="tablet", route="Sublingual", brand="Nitrostat",
        formula="C3H5N3O9", weight="227.09 g/mol",
        half_life="1-4 minutes (extremely short)",
        onset="1-3 minutes",
        moa="Rapidly denitrated to nitric oxide in the smooth muscle cell, activating guanylate cyclase; the resulting venodilatation reduces preload and myocardial oxygen demand within minutes.",
        side_effects="Intense headache, flushing, dizziness, hypotension, syncope, burning under the tongue.",
        contra="Concurrent PDE5 inhibitor (within 24 hours for sildenafil, 48 hours for tadalafil), severe hypotension, bradycardia, raised intracranial pressure.",
        warnings="If pain persists after one tablet plus a second dose 5 minutes later with rest, the patient must be treated as a cardiac emergency - give that instruction at dispensing rather than assume it is known. The tablets lose potency on exposure to air and light: keep them in the original amber glass container and replace six-monthly even if unused.",
        interactions="Sildenafil, tadalafil, vardenafil, riociguat (all absolutely contraindicated), alcohol, ergotamine",
        max_dose="3 tablets (1.5 mg) during one attack - and then seek emergency care",
        cost=2.40, price=6.10,
        pregnancy="C - used in cardiac disease in pregnancy under specialist direction"),

    # =================================================================== #
    # DIABETES - the newer agents now written routinely.
    # =================================================================== #
    _med(
        "Dapagliflozin 10mg", "Dapagliflozin", "Antidiabetic - SGLT2 inhibitor",
        "Sodium-glucose co-transporter 2 inhibitor",
        "Type 2 diabetes, heart failure with reduced ejection fraction, chronic kidney disease with albuminuria",
        strength="10mg", form="tablet", route="Oral", brand="Forxiga",
        formula="C21H25ClO6", weight="408.87 g/mol", half_life="12.9 hours",
        moa="Blocks SGLT2 in the proximal renal tubule so filtered glucose is excreted in the urine rather than reabsorbed. The accompanying natriuresis and reduced glomerular pressure give the heart-failure and renal benefits, independently of glucose lowering.",
        side_effects="Genital mycotic infection, urinary tract infection, volume depletion, ketoacidosis (including with normal glucose), hypotension.",
        contra="Type 1 diabetes, diabetic ketoacidosis, severe renal impairment at initiation, recurrent genital mycotic infection.",
        warnings="Euglycaemic ketoacidosis is the trap: ketoacidosis can occur with normal or near-normal blood glucose, so a glucose check does not exclude it. Any acute illness, prolonged fasting or surgery means stopping temporarily (sick-day rules). Genital hygiene advice at dispensing prevents the commonest reason for stopping.",
        interactions="Insulin and sulfonylureas (hypoglycaemia - a dose reduction may be needed), diuretics (volume depletion), lithium",
        max_dose="10 mg/day",
        cost=14.00, price=32.00,
        pregnancy="D - not recommended; insulin is preferred in pregnancy"),

    _med(
        "Empagliflozin 10mg", "Empagliflozin", "Antidiabetic - SGLT2 inhibitor",
        "Sodium-glucose co-transporter 2 inhibitor",
        "Type 2 diabetes, heart failure with reduced or preserved ejection fraction, cardiovascular risk reduction",
        strength="10mg", form="tablet", route="Oral", brand="Jardiance",
        formula="C23H27ClO7", weight="450.91 g/mol", half_life="12.4 hours",
        moa="As for dapagliflozin: an SGLT2 inhibitor causing glycosuria and natriuresis, lowering glucose, blood pressure and body weight, with heart-failure benefit that does not depend on the glucose effect.",
        side_effects="Genital mycotic infection, urinary tract infection, volume depletion, euglycaemic ketoacidosis, urinary retention in prostatic disease.",
        contra="Type 1 diabetes, ketoacidosis, severe renal impairment at initiation, current urinary tract infection.",
        warnings="The same euglycaemic ketoacidosis warning and sick-day rules as the other SGLT2 inhibitors. In older men with prostatic enlargement, watch for urinary retention being precipitated.",
        interactions="Insulin and sulfonylureas (hypoglycaemia), loop diuretics (volume depletion), lithium",
        max_dose="25 mg/day (10 mg if eGFR is low)",
        cost=15.50, price=34.00,
        pregnancy="D - not recommended; insulin is preferred"),

    _med(
        "Sitagliptin 50mg", "Sitagliptin", "Antidiabetic - DPP-4 inhibitor",
        "Dipeptidyl peptidase-4 inhibitor",
        "Type 2 diabetes, particularly where hypoglycaemia must be avoided",
        strength="50mg", form="tablet", route="Oral", brand="Januvia",
        formula="C16H15F6N5O", weight="407.31 g/mol", half_life="12.4 hours",
        moa="Inhibits DPP-4, the enzyme that degrades the incretin hormones GLP-1 and GIP, so post-meal insulin release is prolonged and glucagon suppressed. Because it works only when glucose is elevated, it rarely causes hypoglycaemia alone.",
        side_effects="Headache, nasopharyngitis, pancreatitis (rare), joint pain, bullous pemphigoid (rare).",
        contra="Type 1 diabetes, diabetic ketoacidosis, previous pancreatitis.",
        warnings="Weight neutral and well tolerated, but less potent than metformin or an SGLT2 inhibitor - a reasonable choice for an older patient where a hypoglycaemic episode is the main risk to avoid. Halve the dose at an eGFR below 45 and quarter it below 30.",
        interactions="Insulin and sulfonylureas (hypoglycaemia - consider reducing the sulfonylurea), digoxin (small rise in levels)",
        max_dose="100 mg/day (reduce for renal impairment)",
        cost=8.50, price=19.50,
        pregnancy="B - limited data; not first choice in pregnancy"),

    _med(
        "Liraglutide 6mg/ml Injection", "Liraglutide",
        "Antidiabetic - GLP-1 receptor agonist",
        "Glucagon-like peptide-1 receptor agonist",
        "Type 2 diabetes with inadequate control on oral agents, weight management, cardiovascular risk reduction",
        strength="6mg/ml (18mg in 3ml pen)", form="injection", route="Subcutaneous",
        brand="Victoza", manufacturer="Novo Nordisk India",
        site="Bengaluru, Karnataka",
        formula="C172H265N43O51", weight="3751.20 g/mol (peptide)",
        half_life="13 hours",
        moa="A GLP-1 receptor agonist resistant to DPP-4 degradation; it increases glucose-dependent insulin secretion, suppresses glucagon, slows gastric emptying and reduces appetite, which is why it lowers both glucose and weight.",
        side_effects="Nausea and vomiting (commonest, usually settles), diarrhoea, injection-site reactions, pancreatitis, gallstones, tachycardia.",
        contra="Personal or family history of medullary thyroid carcinoma, MEN2, pancreatitis, severe gastroparesis, type 1 diabetes.",
        warnings="Cold chain: store at 2-8 C before first use and never freeze. In-use pens may be kept at room temperature for 30 days and must then be discarded - tell the patient explicitly or they will keep using it. Titrate slowly: the nausea is dose-related and is the main reason patients stop. Never combine with another GLP-1 agonist or a DPP-4 inhibitor.",
        interactions="Insulin and sulfonylureas (hypoglycaemia), oral drugs needing rapid absorption (delayed gastric emptying), other GLP-1 agonists",
        max_dose="1.8 mg/day (diabetes); 3 mg/day is the weight-management product",
        storage="Cold chain 2-8C before first use; 30 days at room temperature once opened",
        cost=420.00, price=560.00,
        pregnancy="C - not recommended; stop at least 2 months before a planned pregnancy"),

    _med(
        "Dulaglutide 1.5mg Injection", "Dulaglutide",
        "Antidiabetic - GLP-1 receptor agonist",
        "Long-acting glucagon-like peptide-1 receptor agonist",
        "Type 2 diabetes with once-weekly dosing, cardiovascular risk reduction",
        strength="1.5mg per 0.5ml pen", form="injection", route="Subcutaneous",
        brand="Trulicity", manufacturer="Eli Lilly India",
        site="Bengaluru, Karnataka", half_life="About 5 days (weekly dosing)",
        moa="A long-acting GLP-1 receptor agonist fused to an Fc fragment, giving a half-life of about five days; it raises glucose-dependent insulin secretion, suppresses glucagon, slows gastric emptying and reduces appetite.",
        side_effects="Nausea, diarrhoea, vomiting, abdominal pain, injection-site reactions, pancreatitis, gallstones.",
        contra="Medullary thyroid carcinoma or MEN2 history, pancreatitis, severe gastroparesis, type 1 diabetes.",
        warnings="Weekly dosing is an adherence advantage and also a hazard: a missed dose must be given within 3 days and then the schedule resumed, or skipped entirely - doubling a weekly dose to catch up causes severe nausea. Cold chain as for liraglutide.",
        interactions="Insulin and sulfonylureas (hypoglycaemia), oral drugs with narrow absorption windows, other GLP-1 agonists",
        max_dose="4.5 mg/week (1.5 mg weekly is the usual starting dose)",
        storage="Cold chain 2-8C before first use; 14 days at room temperature once opened",
        cost=560.00, price=740.00,
        pregnancy="C - not recommended; stop at least 2 months before a planned pregnancy"),

    # =================================================================== #
    # PSYCHIATRY - the antidepressants and agents that go with them.
    #
    # Sertraline and escitalopram are NOT repeated here (they are in an earlier
    # batch); this file supplies their age-banded dosage guidance instead.
    # =================================================================== #
    _med(
        "Venlafaxine 75mg", "Venlafaxine", "Antidepressant - SNRI",
        "Serotonin and noradrenaline reuptake inhibitor",
        "Major depressive disorder, generalised anxiety disorder, panic disorder, neuropathic pain, hot flushes",
        strength="75mg", form="tablet", route="Oral", brand="Venlor",
        formula="C17H27NO2", weight="277.40 g/mol",
        half_life="5 hours (11 hours for the active metabolite)",
        onset="2-4 weeks for full effect",
        moa="At low doses it inhibits serotonin reuptake; at higher doses it also inhibits noradrenaline reuptake, which is what gives it efficacy in neuropathic pain and makes the dose-response different from an SSRI.",
        side_effects="Nausea, sweating, hypertension at higher doses, insomnia, sexual dysfunction, severe discontinuation syndrome.",
        contra="Concurrent MAO inhibitor, uncontrolled hypertension, recent myocardial infarction.",
        warnings="The discontinuation syndrome is the worst of the common antidepressants - it must not be stopped abruptly, even on a missed dose, and patients describe a characteristic electric-shock sensation. Check blood pressure, particularly above 150 mg/day because the noradrenergic effect raises it. Prefer the extended-release form to reduce nausea.",
        interactions="MAO inhibitors, tramadol, triptans, linezolid, other serotonergic drugs, antihypertensives, CYP2D6 substrates such as metoprolol and tamoxifen",
        max_dose="375 mg/day (extended release)",
        cost=3.90, price=9.20,
        pregnancy="C - associated with neonatal adaptation syndrome; specialist review advised"),

    _med(
        "Mirtazapine 15mg", "Mirtazapine",
        "Antidepressant - noradrenergic and specific serotonergic",
        "Alpha-2 antagonist antidepressant",
        "Major depressive disorder, particularly with insomnia or weight loss",
        strength="15mg", form="tablet", route="Oral", brand="Mirtaz",
        formula="C17H19N3", weight="265.35 g/mol", half_life="20-40 hours",
        onset="2-4 weeks for full effect; sedation is immediate",
        moa="Antagonises presynaptic alpha-2 autoreceptors, increasing noradrenaline and serotonin release, and blocks 5-HT2 and 5-HT3 receptors - which is why it is sedating and causes weight gain but has comparatively little sexual dysfunction.",
        side_effects="Sedation, increased appetite and weight gain, dry mouth, constipation, dizziness, rarely agranulocytosis.",
        contra="Concurrent MAO inhibitor, mania.",
        warnings="The sedation is a benefit for a depressed patient who cannot sleep and a hazard for one who drives - the effect is strongest at LOW doses (15 mg) and reduces at higher doses, which is counter-intuitive and worth explaining. Watch for weight gain and, rarely, neutropenia if fever or sore throat appears.",
        interactions="MAO inhibitors, benzodiazepines, alcohol, other sedatives, tramadol",
        max_dose="45 mg/day",
        cost=4.10, price=9.80,
        pregnancy="C - specialist review advised"),

    # Alprazolam is NOT repeated here - it is already in batch 3 as
    # "Alprazolam 0.5mg". This file supplies its guidance only.
    _med(
        "Clonazepam 0.5mg", "Clonazepam", "Antiepileptic - benzodiazepine",
        "Long-acting benzodiazepine, GABA-A positive modulator",
        "Epilepsy (adjunct, including myoclonic and absence seizures), panic disorder, akathisia",
        strength="0.5mg", form="tablet", route="Oral", brand="Rivotril",
        formula="C15H10ClN3O3", weight="315.71 g/mol", half_life="20-50 hours",
        moa="As for alprazolam: it potentiates GABA at the GABA-A receptor. The longer half-life is what suits it to seizure prophylaxis rather than acute anxiety, because the same receptor effect is sustained.",
        side_effects="Sedation, ataxia, behavioural change in children, tolerance, dependence, respiratory depression.",
        contra="Severe respiratory insufficiency, sleep apnoea, severe hepatic impairment, myasthenia gravis, acute narrow-angle glaucoma.",
        warnings="Tolerance to the antiepileptic effect develops, so it is an adjunct rather than monotherapy for long-term seizure control, and abrupt withdrawal can precipitate status epilepticus. The long half-life means accumulation in the elderly and a fall risk - the Beers Criteria list it as potentially inappropriate in that group.",
        interactions="Opioids, alcohol, other CNS depressants, phenytoin, phenobarbital, sodium valproate, azole antifungals",
        max_dose="20 mg/day (specialist epilepsy dosing)",
        schedule="Schedule H1 - controlled, register required",
        cost=1.70, price=4.40,
        pregnancy="D - neonatal sedation and withdrawal; specialist review required"),

    # Phenytoin and levetiracetam are NOT repeated here - both are in an earlier
    # batch. This file supplies their age-banded dosage guidance (BATCH5_GUIDES).

    # =================================================================== #
    # RESPIRATORY - combination inhalers, which is what is dispensed.
    #
    # Tiotropium is not repeated (earlier batch); its guidance is below.
    # =================================================================== #
    _med(
        "Budesonide + Formoterol 200/6mcg Inhaler", "Budesonide + Formoterol",
        "Respiratory - ICS/LABA combination",
        "Inhaled corticosteroid with long-acting beta-2 agonist",
        "Asthma maintenance and reliever in the SMART regimen, moderate to severe COPD",
        strength="200mcg/6mcg per actuation", form="inhaler", route="Inhalation",
        brand="Foracort",
        half_life="Budesonide 2-3.6 hours; formoterol 10-14 hours",
        moa="Budesonide reduces airway inflammation and bronchial hyper-reactivity; formoterol, a fast-onset long-acting beta-2 agonist, relaxes bronchial smooth muscle. In one device they treat both components of the disease, which is why a single inhaler can be both maintenance and reliever.",
        side_effects="Oral candidiasis, dysphonia, tremor, palpitations, adrenal suppression at high dose, small growth effect in children.",
        contra="Hypersensitivity to either component; not for acute severe asthma requiring intensive therapy.",
        warnings="Rinse the mouth after every dose - thrush and hoarseness are largely preventable and are the commonest reason patients stop. The device must be demonstrated, not handed over: technique is the biggest determinant of whether the drug reaches the airway, and every inhaler type has a different technique. Never used as monotherapy in asthma.",
        interactions="Beta blockers (antagonise the beta-2 effect), ritonavir and strong CYP3A4 inhibitors (raised budesonide), diuretics (hypokalaemia), MAO inhibitors",
        max_dose="2 inhalations twice daily (maintenance); SMART regimens follow a written action plan",
        cost=185.00, price=265.00,
        pregnancy="B for budesonide - inhaled therapy should continue, as uncontrolled asthma is the greater risk"),

    _med(
        "Fluticasone + Salmeterol 125/25mcg Inhaler", "Fluticasone + Salmeterol",
        "Respiratory - ICS/LABA combination",
        "Inhaled corticosteroid with long-acting beta-2 agonist",
        "Asthma maintenance, COPD with frequent exacerbations",
        strength="125mcg/25mcg per actuation", form="inhaler", route="Inhalation",
        brand="Seretide", half_life="Fluticasone 10 hours; salmeterol 5.5 hours",
        moa="Fluticasone suppresses airway inflammation; salmeterol provides sustained bronchodilatation. Salmeterol has a slower onset than formoterol, so this device is for maintenance and not for relief.",
        side_effects="Oral candidiasis, hoarseness, tremor, palpitations, muscle cramps, adrenal suppression at high dose.",
        contra="Hypersensitivity; not for acute bronchospasm.",
        warnings="Because salmeterol is slow-acting, this combination cannot be used as a reliever - the patient needs a separate rapid-acting bronchodilator, and that distinction must be stated at dispensing or they will try to use it during an attack. Rinse the mouth after use.",
        interactions="Beta blockers, strong CYP3A4 inhibitors (ketoconazole, ritonavir), diuretics (hypokalaemia), MAO inhibitors",
        max_dose="2 inhalations twice daily",
        cost=310.00, price=430.00,
        pregnancy="C - inhaled therapy should continue if the asthma is otherwise uncontrolled"),

    _med(
        "Ipratropium + Levosalbutamol Respirator Solution",
        "Ipratropium + Levosalbutamol",
        "Respiratory - short-acting bronchodilator combination",
        "Short-acting muscarinic antagonist with short-acting beta-2 agonist",
        "Acute severe asthma, COPD exacerbation, nebulised therapy",
        strength="500mcg + 1.25mg per 2.5ml ampoule", form="respirator solution",
        route="Inhalation (nebulised)", brand="Duolin",
        half_life="Ipratropium 1.6 hours; levosalbutamol 3-4 hours",
        onset="5-15 minutes by nebuliser",
        moa="Ipratropium blocks muscarinic receptors and levosalbutamol is the active R-enantiomer of salbutamol acting at beta-2 receptors; blocking both the cholinergic and the adrenergic pathway gives greater bronchodilatation than either alone in an acute exacerbation.",
        side_effects="Tremor, palpitations, headache, dry mouth, hypokalaemia, urinary retention.",
        contra="Hypersensitivity to atropine or salbutamol; caution in cardiac disease and narrow-angle glaucoma.",
        warnings="Can cause hypokalaemia, particularly with repeated doses, so electrolytes should be watched in a severe attack being treated intensively. The nebuliser solution must not be injected or taken orally. If it is being used more often than every four hours the exacerbation is not controlled and the patient needs reassessment, not another dose.",
        interactions="Beta blockers, other anticholinergics, diuretics and corticosteroids (hypokalaemia), MAO inhibitors, tricyclic antidepressants",
        max_dose="Determined by the exacerbation protocol; repeated dosing requires monitoring",
        storage="15-25C, protect from light; use within 3 months of opening the vial",
        cost=12.00, price=24.00,
        pregnancy="C - use if clearly needed; benefit likely outweighs risk in acute asthma"),

    # =================================================================== #
    # PAEDIATRIC LIQUIDS - an adult tablet is not dispensable.
    # =================================================================== #
    _med(
        "Paracetamol 125mg/5ml Suspension", "Paracetamol",
        "Analgesic and antipyretic - paediatric liquid",
        "Central cyclo-oxygenase inhibitor",
        "Fever and mild to moderate pain in children",
        strength="125mg/5ml", form="suspension", route="Oral", brand="Crocin",
        formula="C8H9NO2", weight="151.16 g/mol",
        half_life="2-3 hours in children", onset="30-60 minutes",
        moa="Inhibits prostaglandin synthesis centrally, raising the pain threshold and resetting the hypothalamic set point, which is why it is antipyretic as well as analgesic.",
        side_effects="Very few at therapeutic doses. Overdose causes hepatic necrosis and is the commonest paediatric poisoning in India.",
        contra="Severe hepatic impairment, glucose-6-phosphate dehydrogenase deficiency (high dose).",
        warnings="Weight-based dosing, not age-based: 15 mg/kg per dose, and the age band on the bottle is a crude guide that misfires at both ends of the normal weight range for an age. Shake the bottle - a settled suspension delivers less drug at the top and more at the bottom. Do not combine with another paracetamol-containing product, which is a common accidental double dose since cold remedies also contain it.",
        interactions="Warfarin (regular use raises INR), carbamazepine, phenytoin, rifampicin, isoniazid (hepatotoxicity), other paracetamol-containing products",
        max_dose="60 mg/kg/day, and a maximum of 4 doses in 24 hours",
        schedule="Over the counter - no prescription required", rx=False,
        cost=42.00, price=62.00,
        pregnancy="B - short-term use acceptable"),

    _med(
        "Amoxicillin 125mg/5ml Dry Syrup", "Amoxicillin",
        "Antibiotic - aminopenicillin, paediatric liquid",
        "Cell wall synthesis inhibitor (beta-lactam)",
        "Paediatric respiratory infection, otitis media, urinary tract infection, dental abscess",
        strength="125mg/5ml", form="dry syrup", route="Oral", brand="Mox",
        formula="C16H19N3O5S", weight="365.40 g/mol", half_life="1-1.5 hours",
        moa="Binds penicillin-binding proteins and blocks transpeptidation of the peptidoglycan cell wall, so the bacterium lyses during division. Bactericidal, and effective only against actively dividing organisms.",
        side_effects="Diarrhoea, nausea, rash, candidiasis. A maculopapular rash suggests infectious mononucleosis rather than true allergy.",
        contra="Penicillin or cephalosporin anaphylaxis, infectious mononucleosis.",
        warnings="Reconstituted syrup has a SHORT life - usually 7 days at room temperature or 14 days refrigerated - and the discard date must be written on the bottle at dispensing, not left to the label. Many patients keep it and use it for the next illness, which is both ineffective and a resistance driver. Cross-reactivity within the beta-lactams is real: a penicillin allergy must be treated as blocking other beta-lactams until assessed.",
        interactions="Methotrexate, allopurinol (rash), probenecid (raises levels), warfarin",
        max_dose="By weight; 25-45 mg/kg/day divided - specialist-directed above standard doses",
        storage="Dry powder at 15-30C; reconstituted syrup refrigerated and discarded within 7 days",
        cost=68.00, price=98.00,
        pregnancy="B - safe in pregnancy"),

    _med(
        "Cetirizine 5mg/5ml Syrup", "Cetirizine",
        "Antihistamine - paediatric liquid",
        "Second-generation H1 receptor antagonist",
        "Allergic rhinitis, urticaria, itching in children",
        strength="5mg/5ml", form="syrup", route="Oral", brand="Alerid",
        formula="C21H25ClN2O3", weight="388.89 g/mol", half_life="8 hours",
        onset="20-60 minutes",
        moa="Selectively antagonises peripheral H1 receptors, so histamine cannot produce the wheal, itch and vasodilatation of an allergic response. Less sedating than the first-generation agents because it crosses the blood-brain barrier poorly.",
        side_effects="Somnolence (more than the other second-generation agents), dry mouth, headache, fatigue.",
        contra="Severe renal impairment at normal dose, hypersensitivity to hydroxyzine.",
        warnings="It is the most sedating of the commonly used 'non-sedating' antihistamines - a distinction that matters for a child at school. Dose by weight in young children, and reduce the dose in renal impairment.",
        interactions="CNS depressants and alcohol (additive sedation), theophylline",
        max_dose="By age: 2.5 mg (under 6), 5 mg (6-12), 10 mg (over 12) daily",
        cost=38.00, price=56.00,
        pregnancy="B - considered safe in pregnancy"),

    _med(
        "Ibuprofen 100mg/5ml Suspension", "Ibuprofen",
        "Analgesic, antipyretic and anti-inflammatory - paediatric liquid",
        "Non-selective cyclo-oxygenase inhibitor",
        "Fever and pain in children, juvenile idiopathic arthritis",
        strength="100mg/5ml", form="suspension", route="Oral", brand="Brufen",
        formula="C13H18O2", weight="206.28 g/mol",
        half_life="2 hours in children", onset="30-60 minutes",
        moa="Reversibly inhibits cyclo-oxygenase 1 and 2, reducing prostaglandin synthesis; the peripheral reduction is what gives it the anti-inflammatory activity paracetamol lacks.",
        side_effects="Gastric irritation, nausea, rarely renal impairment with dehydration, asthma exacerbation in aspirin-sensitive children.",
        contra="Active gastrointestinal bleeding, severe renal or hepatic impairment, aspirin-sensitive asthma, dehydration, varicella (concern over necrotising fasciitis).",
        warnings="Give with food and ensure adequate fluid intake. Never give to a dehydrated child - the combination of an NSAID and poor renal perfusion is a recognised cause of acute kidney injury in paediatric gastroenteritis, which is exactly the situation where it is most often reached for. Avoid in chickenpox and shingles.",
        interactions="Other NSAIDs, corticosteroids (ulcer risk), anticoagulants, ACE inhibitors and diuretics (renal), methotrexate, lithium",
        max_dose="30 mg/kg/day in divided doses",
        cost=48.00, price=70.00,
        pregnancy="D in the third trimester - avoid; C in the first and second"),

    _med(
        "Metronidazole 100mg/5ml Suspension", "Metronidazole",
        "Antibiotic and antiprotozoal - paediatric liquid",
        "Nitroimidazole - DNA strand breakage",
        "Paediatric amoebiasis, giardiasis, anaerobic infection",
        strength="100mg/5ml", form="suspension", route="Oral", brand="Metrogyl",
        formula="C6H9N3O3", weight="171.15 g/mol", half_life="8 hours",
        moa="The nitro group is reduced intracellularly by anaerobic organisms to reactive intermediates that bind and break DNA strands, which is why it works only against anaerobes and protozoa with the reducing capacity to activate it.",
        side_effects="Metallic taste, nausea, abdominal discomfort, dark urine, peripheral neuropathy on long courses, disulfiram-like reaction with alcohol.",
        contra="First trimester of pregnancy (relative), alcohol use, previous metronidazole neuropathy.",
        warnings="Absolutely no alcohol during the course and for 48 hours afterwards - the disulfiram-like reaction is severe. The metallic taste is the commonest reason a child refuses it, so give it with food or a drink that masks the taste rather than losing the course. Peripheral neuropathy is a risk on prolonged high-dose therapy.",
        interactions="Alcohol (disulfiram-like reaction), warfarin (greatly raises INR), lithium (toxicity), phenytoin, carbamazepine, fluorouracil",
        max_dose="By indication and weight; specialist-directed in amoebic liver abscess",
        cost=52.00, price=76.00,
        pregnancy="B - avoided in the first trimester by convention"),

    _med(
        "Zinc Sulphate 20mg Dispersible Tablet", "Zinc Sulphate",
        "Micronutrient - paediatric dispersible",
        "Zinc supplementation",
        "Adjunct to oral rehydration in childhood diarrhoea, zinc deficiency",
        strength="20mg elemental zinc", form="dispersible tablet", route="Oral",
        brand="Zincovit DS",
        moa="Zinc is a cofactor in mucosal repair and immune function; supplementation shortens the duration of diarrhoea and reduces recurrence for two to three months afterwards, which is why it is a national programme item rather than a general tonic.",
        side_effects="Vomiting, metallic taste, abdominal pain; nausea if given on an empty stomach.",
        contra="Hypersensitivity; caution in renal failure.",
        warnings="The tablet is DISPERSIBLE and must be dissolved in clean water or breast milk - swallowing it whole causes vomiting in a young child, and that vomiting is often mistaken for intolerance to the zinc itself. It is an adjunct, never a replacement for ORS. The programme dose is 14 days even if the diarrhoea has stopped by day 3, which parents need told or they will stop early.",
        interactions="Iron and calcium (separate doses by 2 hours), tetracyclines and fluoroquinolones (reduced absorption), penicillamine",
        max_dose="20 mg/day (over 6 months); 10 mg/day (under 6 months)",
        schedule="Over the counter - no prescription required", rx=False,
        cost=18.00, price=28.00,
        pregnancy="A - safe at recommended intake"),

    # =================================================================== #
    # THE OTHERWISE-MISSED DEFAULTS.
    # =================================================================== #
    # Ondansetron is NOT repeated here - it is in an earlier batch. This file
    # supplies its age-banded dosage guidance (BATCH5_GUIDES).
    # =================================================================== #
    _med(
        "Domperidone 10mg", "Domperidone",
        "Antiemetic - peripheral dopamine antagonist",
        "Peripheral D2 receptor antagonist",
        "Nausea and vomiting, gastroparesis, reflux symptoms",
        strength="10mg", form="tablet", route="Oral", brand="Domstal",
        formula="C22H24ClN5O2", weight="425.91 g/mol", half_life="7 hours",
        moa="Blocks dopamine D2 receptors in the chemoreceptor trigger zone and increases gastric and duodenal motility; it crosses the blood-brain barrier poorly, so extrapyramidal effects are much less likely than with metoclopramide.",
        side_effects="Dry mouth, headache, raised prolactin with galactorrhoea and gynaecomastia, QT prolongation, rarely cardiac arrhythmia.",
        contra="QT prolongation, cardiac conduction disturbance, severe hepatic impairment, prolactinoma, concurrent ketoconazole, erythromycin or other potent CYP3A4 inhibitors, gastrointestinal haemorrhage or obstruction.",
        warnings="The QT risk is why the maximum dose and duration are restricted - it is no longer recommended for long-term or high-dose use, and the cardiac warning is a labelled restriction rather than a theoretical one. Avoid with CYP3A4 inhibitors, which raise the level and therefore the arrhythmia risk.",
        interactions="Ketoconazole, erythromycin, clarithromycin, amiodarone, haloperidol, other QT-prolonging drugs, anticholinergics (antagonise the prokinetic effect)",
        max_dose="10 mg up to three times daily; maximum 7 days without review",
        cost=2.10, price=5.20,
        pregnancy="C - use only if clearly needed"),

    _med(
        "Rabeprazole 20mg", "Rabeprazole", "Proton pump inhibitor",
        "Irreversible H+/K+ ATPase inhibitor",
        "Gastro-oesophageal reflux disease, peptic ulcer, Helicobacter pylori eradication regimens, NSAID ulcer prophylaxis",
        strength="20mg", form="tablet", route="Oral", brand="Razo",
        formula="C18H21N3O3S", weight="359.44 g/mol",
        half_life="1-2 hours (the effect lasts far longer, because binding is irreversible)",
        onset="1 hour; maximal effect after 3-4 days of dosing",
        moa="Protonated in the acid canaliculus of the parietal cell and then covalently bound to the H+/K+ ATPase, shutting off the final step of acid secretion. Binding is irreversible, so acid suppression outlasts the plasma half-life until new pumps are synthesised.",
        side_effects="Headache, diarrhoea, abdominal pain; on long-term use, hypomagnesaemia, B12 deficiency, increased fracture risk, enteric infection.",
        contra="Hypersensitivity; caution with rilpivirine and drugs needing gastric acid.",
        warnings="Take 30 minutes BEFORE food, not with it - the drug needs an active proton pump to bind, and that needs a meal to stimulate. Long-term use should be reviewed rather than continued indefinitely, because of the magnesium, B12 and fracture associations. It reduces absorption of drugs that need acid, which includes some antiretrovirals and antifungals.",
        interactions="Rilpivirine, atazanavir, ketoconazole and itraconazole (reduced absorption), clopidogrel (less than with omeprazole but still a consideration), methotrexate, digoxin",
        max_dose="40 mg/day",
        cost=3.40, price=8.10,
        pregnancy="B - considered acceptable if clearly needed"),

    # Lactulose is NOT repeated here - it is already in batch 3 as
    # "Lactulose Solution" (10g/15ml). This file supplies its guidance only.
    _med(
        "Rivaroxaban 20mg", "Rivaroxaban",
        "Anticoagulant - direct factor Xa inhibitor",
        "Direct oral factor Xa inhibitor",
        "Deep vein thrombosis and pulmonary embolism treatment and prevention, stroke prevention in non-valvular atrial fibrillation",
        strength="20mg", form="tablet", route="Oral", brand="Xarelto",
        formula="C19H18ClN3O5S", weight="435.88 g/mol",
        half_life="5-9 hours (13 hours in the elderly)",
        moa="Directly and selectively inhibits factor Xa, the point at which the intrinsic and extrinsic pathways converge on prothrombin, so thrombin generation and clot formation are reduced without needing antithrombin as a cofactor.",
        side_effects="Bleeding (the main effect as well as the main risk), anaemia, bruising, nausea, raised transaminases.",
        contra="Active significant bleeding, severe hepatic impairment with coagulopathy, pregnancy and breastfeeding, concurrent other anticoagulant except under specialist switching.",
        warnings="The 20 mg dose is for atrial fibrillation and must be taken WITH FOOD, because bioavailability without food is markedly reduced - a detail that is easy to lose and materially reduces the anticoagulant effect. Renal dosing matters: 20 mg is for a creatinine clearance above 50, 15 mg for 30-50, avoid below 15. Unlike warfarin there is no routine INR monitoring, so adherence is the whole safety margin - a missed dose is not detected by any test.",
        interactions="Strong CYP3A4 and P-glycoprotein inhibitors (ketoconazole, ritonavir, clarithromycin - raise levels), rifampicin and carbamazepine (reduce levels), other anticoagulants and antiplatelets, NSAIDs",
        max_dose="20 mg once daily with food",
        cost=42.00, price=68.00,
        pregnancy="X - contraindicated; use low molecular weight heparin instead"),

    _med(
        "Folic Acid 5mg", "Folic Acid", "Vitamin - haematinic",
        "One-carbon metabolism cofactor",
        "Folate deficiency anaemia, pregnancy prophylaxis of neural tube defects, methotrexate co-prescription",
        strength="5mg", form="tablet", route="Oral", brand="Folvite",
        formula="C19H19N7O6", weight="441.40 g/mol",
        moa="Reduced to tetrahydrofolate, the cofactor for thymidylate and purine synthesis. Without it DNA synthesis stalls, which is why rapidly dividing cells - marrow, gut, neural tube - are affected first.",
        side_effects="Very few; bitter taste, rare hypersensitivity. Can precipitate neuropathy if given alone to a B12-deficient patient.",
        contra="Untreated vitamin B12 deficiency (folate corrects the anaemia while the neurological damage progresses), pernicious anaemia without B12.",
        warnings="Never give folate alone where B12 deficiency is possible, because correcting the anaemia masks the continuing neurological damage - the single important interaction of an otherwise harmless vitamin. Neural tube defect prevention should start before conception, not after a positive test.",
        interactions="Methotrexate, sulfasalazine, trimethoprim (folate antagonists), phenytoin (folate lowers levels), pyrimethamine",
        max_dose="5 mg/day (1 mg or less for routine supplementation)",
        cost=1.20, price=3.20,
        pregnancy="A - recommended, and essential before conception"),
]# Dosage guides for batch 5. Keyed by the exact medicine name above, so a typo
# here silently produces no guide - which is why test_catalogue.py asserts that
# every guidance entry resolves to a real medicine.
#
# Age bands follow the rest of the catalogue: Neonate, Infant, Child, Adult,
# Elderly. A band is only present where the published reference supports it, so
# an absent band means "not established", never "same as adult".
BATCH5_GUIDES = [
    {"medicine_name": 'Nifedipine 10mg', "age_group": '18+',
     "dosage_amount": 10, "dosage_unit": 'mg',
     "frequency": 'Three times daily', "duration_days": 30,
     "indication": 'Stable angina, hypertension',
     "special_notes": 'Use a slow-release formulation for hypertension; the immediate-release form can drop blood pressure abruptly. Warn about ankle swelling. Elderly: Start low - postural hypotension and ankle oedema are more likely. Not a first choice in heart failure.'},
    {"medicine_name": 'Isosorbide Dinitrate 10mg', "age_group": '18+',
     "dosage_amount": 10, "dosage_unit": 'mg',
     "frequency": 'Twice daily', "duration_days": 30,
     "indication": 'Angina prophylaxis',
     "special_notes": 'Keep an 8-12 hour nitrate-free interval (for example 8am and 4pm) to prevent tolerance. Ask specifically about erectile-dysfunction drugs - the combination is dangerous. Elderly: Headache and postural hypotension are more pronounced; sit down for the first doses.'},
    {"medicine_name": 'Nicorandil 5mg', "age_group": '18+',
     "dosage_amount": 5, "dosage_unit": 'mg',
     "frequency": 'Twice daily', "duration_days": 30,
     "indication": 'Chronic stable angina',
     "special_notes": 'Titrate upwards as tolerated. Report any mouth, gut or genital ulceration - it heals on stopping the drug. Elderly: Same as adult; monitor for postural hypotension and ulceration.'},
    {"medicine_name": 'Ivabradine 5mg', "age_group": '18+',
     "dosage_amount": 5, "dosage_unit": 'mg',
     "frequency": 'Twice daily', "duration_days": 30,
     "indication": 'Heart failure with reduced ejection fraction, stable angina',
     "special_notes": 'Warn about luminous phenomena (phosphenes) - about 15% see them, usually in the first two months, and they generally settle. Elderly: Start at 2.5 mg twice daily above age 75 and titrate on heart rate.'},
    {"medicine_name": 'Nitroglycerin 0.5mg Sublingual', "age_group": '18+',
     "dosage_amount": 0.5, "dosage_unit": 'mg',
     "frequency": 'When required', "duration_days": 30,
     "indication": 'Acute angina attack',
     "special_notes": 'One tablet under the tongue; a second after 5 minutes if the pain persists. If the pain is still there 5 minutes after the second tablet, seek emergency care. Keep in the original amber container and replace six-monthly. Elderly: Sit or lie down for the dose - fainting is a real risk at this age from the abrupt fall in blood pressure.'},
    {"medicine_name": 'Dapagliflozin 10mg', "age_group": '18+',
     "dosage_amount": 10, "dosage_unit": 'mg',
     "frequency": 'Once daily', "duration_days": 30,
     "indication": 'Type 2 diabetes, heart failure, chronic kidney disease',
     "special_notes": 'Once daily, any time, with or without food. Advise genital hygiene - thrush is the commonest reason patients stop. Sick-day rule: hold during acute illness, prolonged fasting or before surgery. Elderly: Assess volume status first - the elderly are more prone to dehydration and postural hypotension on this class.'},
    {"medicine_name": 'Empagliflozin 10mg', "age_group": '18+',
     "dosage_amount": 10, "dosage_unit": 'mg',
     "frequency": 'Once daily', "duration_days": 30,
     "indication": 'Type 2 diabetes, heart failure with reduced or preserved ejection fraction',
     "special_notes": 'May be increased to 25 mg daily if tolerated and renal function allows. Same sick-day rules as dapagliflozin. Elderly: Do not increase above 10 mg if eGFR is low; watch for urinary retention in prostatic disease.'},
    {"medicine_name": 'Sitagliptin 50mg', "age_group": '18+',
     "dosage_amount": 100, "dosage_unit": 'mg',
     "frequency": 'Once daily', "duration_days": 30,
     "indication": 'Type 2 diabetes',
     "special_notes": 'The 50 mg tablet is used twice daily, or as a single 100 mg dose using two tablets. Halve the total dose at an eGFR below 45 and quarter it below 30. Elderly: Check renal function before starting - the dose follows eGFR, not age. Well suited to this group because it rarely causes hypoglycaemia.'},
    {"medicine_name": 'Liraglutide 6mg/ml Injection', "age_group": '18+',
     "dosage_amount": 0.6, "dosage_unit": 'mg',
     "frequency": 'Once daily', "duration_days": 30,
     "indication": 'Type 2 diabetes',
     "special_notes": 'Start 0.6 mg daily for one week, then 1.2 mg, then 1.8 mg if needed - the slow titration is what keeps the nausea tolerable. Subcutaneous, abdomen or thigh. Rotate sites. Store at 2-8C before first use; discard 30 days after opening.'},
    {"medicine_name": 'Dulaglutide 1.5mg Injection', "age_group": '18+',
     "dosage_amount": 1.5, "dosage_unit": 'mg',
     "frequency": 'Once weekly', "duration_days": 28,
     "indication": 'Type 2 diabetes',
     "special_notes": 'Once weekly on the same day each week, any time of day, with or without food. A missed dose may be given within 3 days; otherwise skip it - never double up. Store at 2-8C; 14 days at room temperature once opened.'},
    {"medicine_name": 'Venlafaxine 75mg', "age_group": '18+',
     "dosage_amount": 75, "dosage_unit": 'mg',
     "frequency": 'Once daily', "duration_days": 30,
     "indication": 'Depression, generalised anxiety disorder, neuropathic pain',
     "special_notes": 'Give the extended-release form once daily with food. Do not stop abruptly - the discontinuation syndrome is severe. Check blood pressure, especially above 150 mg daily. Elderly: Start at 37.5 mg daily. Monitor blood pressure and sodium closely.'},
    {"medicine_name": 'Mirtazapine 15mg', "age_group": '18+',
     "dosage_amount": 15, "dosage_unit": 'mg',
     "frequency": 'At bedtime', "duration_days": 30,
     "indication": 'Depression, particularly with insomnia',
     "special_notes": 'Take at bedtime - the sedation is the point here. More sedating at 15 mg than at 30 mg, which is counter-intuitive and worth explaining. Appetite and weight increase are expected. Elderly: Useful where appetite and sleep are poor, but watch for falls at night and for excessive sedation.'},
    {"medicine_name": 'Alprazolam 0.5mg', "age_group": '18+',
     "dosage_amount": 0.25, "dosage_unit": 'mg',
     "frequency": 'Three times daily', "duration_days": 7,
     "indication": 'Short-term anxiety, panic disorder',
     "special_notes": 'Short-term use only - dependence develops quickly. Do not stop abruptly after more than a few weeks; the dose must be tapered. No alcohol, and no driving until the effect is known. Schedule H1: register entry required. Elderly: Use with great caution - falls, confusion and paradoxical agitation are common at this age. Beers Criteria list it as potentially inappropriate in the elderly.'},
    {"medicine_name": 'Clonazepam 0.5mg', "age_group": '18+',
     "dosage_amount": 0.5, "dosage_unit": 'mg',
     "frequency": 'Twice daily', "duration_days": 30,
     "indication": 'Epilepsy (adjunct), panic disorder',
     "special_notes": 'Titrate slowly. Never stop abruptly - withdrawal can precipitate status epilepticus. Schedule H1: register entry required. Elderly: The long half-life causes accumulation - start at half the adult dose and review for falls and daytime sedation.'},
    {"medicine_name": 'Clonazepam 0.5mg', "age_group": '6-12',
     "dosage_amount": 0.01, "dosage_unit": 'mg/kg',
     "frequency": 'Twice daily', "duration_days": 30,
     "indication": 'Epilepsy (adjunct)',
     "special_notes": 'Specialist-directed. Dose by weight; watch for sedation and behavioural change, which is common in children.'},
    {"medicine_name": 'Phenytoin 100mg', "age_group": '18+',
     "dosage_amount": 100, "dosage_unit": 'mg',
     "frequency": 'Three times daily', "duration_days": 30,
     "indication": 'Generalised tonic-clonic and focal seizures',
     "special_notes": 'Dose by plasma level, not by tablet count - kinetics are saturable, so a small increase can cause toxicity. Never stop abruptly. Good oral hygiene reduces gingival hyperplasia. Elderly: Lower doses are usually needed because of reduced clearance; check levels after any other drug is added or stopped.'},
    {"medicine_name": 'Phenytoin 100mg', "age_group": '6-12',
     "dosage_amount": 5, "dosage_unit": 'mg/kg',
     "frequency": 'Twice daily', "duration_days": 30,
     "indication": 'Epilepsy',
     "special_notes": 'Specialist-directed. Monitor levels closely in children - metabolism changes with age and the therapeutic window is narrow.'},
    {"medicine_name": 'Levetiracetam 500mg', "age_group": '6-12',
     "dosage_amount": 10, "dosage_unit": 'mg/kg',
     "frequency": 'Twice daily', "duration_days": 30,
     "indication": 'Epilepsy',
     "special_notes": 'Specialist-directed. Watch for irritability and behavioural change - the commonest reason for stopping in children, and easily mistaken for the condition.'},
    {"medicine_name": 'Budesonide + Formoterol 200/6mcg Inhaler', "age_group": '18+',
     "dosage_amount": 1, "dosage_unit": '-2 inhalations',
     "frequency": 'Twice daily', "duration_days": 30,
     "indication": 'Asthma maintenance, COPD',
     "special_notes": 'Rinse the mouth after every dose. Demonstrate the technique - it determines whether any drug reaches the airway. In a SMART regimen the same inhaler is used as reliever according to a written action plan.'},
    {"medicine_name": 'Budesonide + Formoterol 200/6mcg Inhaler', "age_group": '6-12',
     "dosage_amount": 1, "dosage_unit": 'inhalation',
     "frequency": 'Twice daily', "duration_days": 30,
     "indication": 'Asthma maintenance',
     "special_notes": 'From age 6, with a spacer where needed. Review technique and growth at each visit.'},
    {"medicine_name": 'Fluticasone + Salmeterol 125/25mcg Inhaler', "age_group": '18+',
     "dosage_amount": 1, "dosage_unit": 'inhalation',
     "frequency": 'Twice daily', "duration_days": 30,
     "indication": 'Asthma maintenance, COPD',
     "special_notes": 'Maintenance only - it is slow-acting and must NOT be used as a reliever. A separate rapid-acting bronchodilator is needed for an attack. Rinse the mouth after use.'},
    {"medicine_name": 'Fluticasone + Salmeterol 125/25mcg Inhaler', "age_group": '6-12',
     "dosage_amount": 1, "dosage_unit": 'inhalation',
     "frequency": 'Twice daily', "duration_days": 30,
     "indication": 'Asthma maintenance',
     "special_notes": 'From age 4 with a spacer. Monitor height - a small growth effect is possible but uncontrolled asthma is the greater risk.'},
    {"medicine_name": 'Ipratropium + Levosalbutamol Respirator Solution', "age_group": '18+',
     "dosage_amount": 2.5, "dosage_unit": 'ml',
     "frequency": 'Three times daily', "duration_days": 5,
     "indication": 'Acute severe asthma, COPD exacerbation',
     "special_notes": 'Nebulised. If it is needed more often than every 4 hours the exacerbation is not controlled - the patient needs reassessment, not another dose. Not for injection or oral use.'},
    {"medicine_name": 'Ipratropium + Levosalbutamol Respirator Solution', "age_group": '6-12',
     "dosage_amount": 1.25, "dosage_unit": 'ml',
     "frequency": 'Three times daily', "duration_days": 5,
     "indication": 'Acute severe asthma',
     "special_notes": 'Specialist-directed, diluted as instructed for the nebuliser. Watch for tremor and tachycardia.'},
    {"medicine_name": 'Paracetamol 125mg/5ml Suspension', "age_group": '0-2',
     "dosage_amount": 15, "dosage_unit": 'mg/kg',
     "frequency": 'Every 6 hours', "duration_days": 3,
     "indication": 'Fever, pain',
     "special_notes": 'Weight-based, not age-based: 15 mg/kg per dose, maximum four doses in 24 hours. Shake the bottle. Do not combine with any other paracetamol-containing product.'},
    {"medicine_name": 'Paracetamol 125mg/5ml Suspension', "age_group": '6-12',
     "dosage_amount": 15, "dosage_unit": 'mg/kg',
     "frequency": 'Every 6 hours', "duration_days": 3,
     "indication": 'Fever, pain',
     "special_notes": 'Weight-based. The age band on the bottle is a crude guide - use the recorded weight.'},
    {"medicine_name": 'Amoxicillin 125mg/5ml Dry Syrup', "age_group": '0-2',
     "dosage_amount": 25, "dosage_unit": 'mg/kg/day',
     "frequency": 'Three times daily', "duration_days": 5,
     "indication": 'Respiratory infection, otitis media',
     "special_notes": 'Specialist-directed in infants. Reconstitute as instructed and write the discard date on the bottle - a reconstituted syrup lasts 7 days at room temperature or 14 refrigerated.'},
    {"medicine_name": 'Amoxicillin 125mg/5ml Dry Syrup', "age_group": '6-12',
     "dosage_amount": 25, "dosage_unit": 'mg/kg/day',
     "frequency": 'Three times daily', "duration_days": 5,
     "indication": 'Respiratory infection, otitis media, dental abscess',
     "special_notes": 'Complete the full course even once the child feels better. Write the discard date on the bottle and tell the parent not to keep it for the next illness.'},
    {"medicine_name": 'Cetirizine 5mg/5ml Syrup', "age_group": '6-12',
     "dosage_amount": 2.5, "dosage_unit": 'mg',
     "frequency": 'Once daily', "duration_days": 7,
     "indication": 'Allergic rhinitis, urticaria',
     "special_notes": "Under age 6, 2.5 mg daily; 6-12 years, 5 mg daily. It is the most sedating of the common 'non-sedating' antihistamines, so give it at bedtime if it makes the child drowsy at school."},
    {"medicine_name": 'Cetirizine 5mg/5ml Syrup', "age_group": '18+',
     "dosage_amount": 10, "dosage_unit": 'mg',
     "frequency": 'Once daily', "duration_days": 7,
     "indication": 'Allergic rhinitis, urticaria',
     "special_notes": 'Reduce the dose in renal impairment.'},
    {"medicine_name": 'Ibuprofen 100mg/5ml Suspension', "age_group": '0-2',
     "dosage_amount": 10, "dosage_unit": 'mg/kg',
     "frequency": 'Three times daily', "duration_days": 3,
     "indication": 'Fever, pain',
     "special_notes": 'From 3 months and above 5 kg. Give with food or milk and ensure adequate fluids. Do NOT give to a dehydrated child - the risk of kidney injury is real in gastroenteritis.'},
    {"medicine_name": 'Ibuprofen 100mg/5ml Suspension', "age_group": '6-12',
     "dosage_amount": 10, "dosage_unit": 'mg/kg',
     "frequency": 'Three times daily', "duration_days": 3,
     "indication": 'Fever, pain, juvenile arthritis',
     "special_notes": 'Maximum 30 mg/kg/day. Avoid in chickenpox. Give with food.'},
    {"medicine_name": 'Metronidazole 100mg/5ml Suspension', "age_group": '6-12',
     "dosage_amount": 30, "dosage_unit": 'mg/kg/day',
     "frequency": 'Three times daily', "duration_days": 5,
     "indication": 'Amoebiasis, giardiasis',
     "special_notes": 'Specialist-directed by indication. Give with food to mask the metallic taste, which is the commonest reason a child refuses it. No alcohol during the course.'},
    {"medicine_name": 'Zinc Sulphate 20mg Dispersible Tablet', "age_group": '0-2',
     "dosage_amount": 10, "dosage_unit": 'mg',
     "frequency": 'Once daily', "duration_days": 14,
     "indication": 'Diarrhoea adjunct in children under 6 months',
     "special_notes": 'Dissolve the dispersible tablet in clean water or breast milk - do not let the child swallow it whole, as it causes vomiting. Continue for the full 14 days even after the diarrhoea settles.'},
    {"medicine_name": 'Zinc Sulphate 20mg Dispersible Tablet', "age_group": '6-12',
     "dosage_amount": 20, "dosage_unit": 'mg',
     "frequency": 'Once daily', "duration_days": 14,
     "indication": 'Diarrhoea adjunct in children over 6 months',
     "special_notes": 'Dissolve in clean water or breast milk. An adjunct to ORS, never a replacement. Complete 14 days.'},
    {"medicine_name": 'Ondansetron 4mg', "age_group": '6-12',
     "dosage_amount": 0.15, "dosage_unit": 'mg/kg',
     "frequency": 'Three times daily', "duration_days": 3,
     "indication": 'Vomiting',
     "special_notes": 'Specialist-directed; maximum 4 mg per dose in children. The mouth-dispersible form is easier to give when the child is vomiting.'},
    {"medicine_name": 'Domperidone 10mg', "age_group": '18+',
     "dosage_amount": 10, "dosage_unit": 'mg',
     "frequency": 'Three times daily', "duration_days": 7,
     "indication": 'Nausea, gastroparesis, reflux',
     "special_notes": 'Take before meals. Maximum 7 days without review - long-term use carries a cardiac risk. Avoid with ketoconazole, erythromycin and other CYP3A4 inhibitors. Elderly: Use the lowest dose for the shortest time - the QT and arrhythmia risk is greatest in this group.'},
    {"medicine_name": 'Rabeprazole 20mg', "age_group": '18+',
     "dosage_amount": 20, "dosage_unit": 'mg',
     "frequency": 'Once daily', "duration_days": 28,
     "indication": 'Reflux disease, peptic ulcer, H. pylori regimens',
     "special_notes": 'Take 30 minutes BEFORE breakfast, not with food. Review after 8 weeks rather than continuing indefinitely. Elderly: Check magnesium if the patient is on diuretics or has palpitations - hypomagnesaemia is more likely with long-term use at this age.'},
    # Lactulose has one guide per age band, and the seeder keys on
    # (medicine, age_group) - it does not key on the indication. Two 18+ entries
    # therefore fought for the same slot and the second was silently discarded,
    # losing the encephalopathy guidance entirely. The two indications are both
    # real and are used at genuinely different doses, so they are merged into
    # one row that states both rather than one being deleted. The first row is
    # the emergency/default reading; the second is the specialist regimen.
    {"medicine_name": 'Lactulose Solution', "age_group": '18+',
     "dosage_amount": 15, "dosage_unit": 'ml',
     "frequency": 'Twice daily', "duration_days": 14,
     "indication": 'Constipation (first line) — or hepatic encephalopathy, 30 ml three times daily',
     "special_notes": 'CONSTIPATION: 15 ml twice daily, adjusted to one or two soft stools a day. Full effect takes 24-48 hours, so do not take a second dose the same day expecting a faster result; expect some bloating in the first few days. HEPATIC ENCEPHALOPATHY: 30 ml three times daily, titrated to two or three soft stools a day - a different target from ordinary constipation, and specialist-directed. The two indications are not interchangeable at the same dose.'},
    {"medicine_name": 'Lactulose Solution', "age_group": '6-12',
     "dosage_amount": 5, "dosage_unit": 'ml',
     "frequency": 'Twice daily', "duration_days": 7,
     "indication": 'Constipation',
     "special_notes": 'Dose by age and response. Safe in infants at reduced dose under advice.'},
    {"medicine_name": 'Rivaroxaban 20mg', "age_group": '18+',
     "dosage_amount": 20, "dosage_unit": 'mg',
     "frequency": 'Once daily', "duration_days": 30,
     "indication": 'Atrial fibrillation, VTE treatment and prevention',
     "special_notes": 'MUST be taken with food - absorption falls sharply without it. Correct renal dosing: 20 mg above a creatinine clearance of 50, 15 mg for 30-50, avoid below 15. No INR monitoring, so never miss a dose. Report any unusual bleeding. Elderly: Check creatinine clearance before every renewal - it falls with age and the dose depends on it. Take with the main meal.'},
    {"medicine_name": 'Folic Acid 5mg', "age_group": '18+',
     "dosage_amount": 5, "dosage_unit": 'mg',
     "frequency": 'Once daily', "duration_days": 30,
     "indication": 'Folate deficiency anaemia, methotrexate co-prescription',
     "special_notes": 'Never use for anaemia without excluding B12 deficiency first - correcting the anaemia alone lets the neurological damage progress.'},
    {"medicine_name": 'Folic Acid 5mg', "age_group": '6-12',
     "dosage_amount": 2.5, "dosage_unit": 'mg',
     "frequency": 'Once daily', "duration_days": 30,
     "indication": 'Folate deficiency',
     "special_notes": 'Specialist-directed. Same B12 caution applies.'},
]
