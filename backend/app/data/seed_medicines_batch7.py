"""
Extended medicine reference data - batch 7.

WHY THIS BATCH EXISTS
---------------------
Batches 1-6 built a strong dispensing set (141 medicines, 125 ingredients), but
auditing it against what an Indian retail pharmacy is actually asked for showed
whole *classes* still absent. These are not obscure drugs - a counter is asked
for them every day:

  * **cephalosporins beyond cefixime and ceftriaxone** - so an oral
    second-generation agent and a first-generation one were missing entirely
  * **macrolides beyond azithromycin** - no clarithromycin, which is the
    backbone of Helicobacter pylori eradication
  * **antifungals beyond fluconazole and topical clotrimazole** - no
    terbinafine, no itraconazole, no griseofulvin
  * **the urological and prostatic agents** - an entire high-volume category
    with no representative at all
  * **the antithyroid drug and the second thyroid strength**
  * **migraine prophylaxis**, **topical corticosteroids**, and
  * **the first-line antitubercular combination** and the antiparasitics that
    India specifically needs (ivermectin for lymphatic filariasis programmes)

WHAT THIS DELIBERATELY DOES NOT DO
----------------------------------
**It does not claim to be every medicine in India, and it does not pad.**

India approves on the order of a thousand active ingredients and six figures of
brand variants. There is no authoritative machine-readable master file, and a
locally generated list built to reach that number would have to invent the
clinical fields - molecular formula, half-life, pregnancy category, dose ceiling
and contraindications - for hundreds of molecules. At that point the catalogue
would *look* complete and be quietly wrong, which is worse than an obvious gap: a
pharmacist who finds a drug absent will look it up, whereas one who reads a
fabricated contraindication will believe it. An invented figure reads exactly
like a real one.

So every value below is a published figure for a well-established molecule.
Where a figure is not reliably published for a combination, the field is left as
None rather than guessed.

`test_catalogue.py` asserts the properties that *are* verifiable: no duplicate
medicine names across batches, no duplicate (medicine, age band) guide, every
required column populated, every guide resolving to a real medicine, every
medicine carrying at least one dose, and nothing dropped by the seeder on the
way into the database. Those are the guarantees this file is held to.

FOR FULL NATIONAL COVERAGE
--------------------------
Use import_medicines.py with a real source - CDSCO approved-drug lists, the Jan
Aushadhi catalogue, an NPPA ceiling-price list, or a distributor sheet. That path
already exists and is documented, and it is the honest route to six-figure
coverage. See the `Expanding the catalogue` section of DEVELOPER_NOTES.md.

A NOTE ON NAMES
---------------
Names use the "name + strength" form the rest of the catalogue uses. The seeder
keys on the name and silently skips a repeat, so a collision here would ship one
fewer medicine than the count implies - the exact defect two batch-4 entries had
against batch 3. test_catalogue.py now fails on a duplicate name rather than
letting it pass.
"""


def _med(name, generic, therapeutic_class, pharmacological_class, use_case,
         **kw):
    """Build one medicine record with the defaults the other batches use."""
    return {
        "name": name,
        "generic_name": generic,
        "brand_name": kw.get("brand", name.split()[0]),
        "manufacturer": kw.get("manufacturer",
                               "Various - multiple licensed manufacturers"),
        "manufacturer_country": "India",
        "manufacturer_site": kw.get("site", "India"),
        "manufacturer_licence_no": kw.get("licence", "Multiple - see the pack"),
        "marketed_by": kw.get("marketed_by", "Various"),
        "country_origin": "India",
        "salt_composition": kw.get("composition", name),
        "molecular_formula": kw.get("formula"),
        "chemical_formula_weight": kw.get("weight"),
        "strength": kw.get("strength", name.split()[-1]),
        "form": kw.get("form", "tablet"),
        "route_of_administration": kw.get("route", "Oral"),
        "therapeutic_class": therapeutic_class,
        "pharmacological_class": pharmacological_class,
        "use_case": use_case,
        "mechanism_of_action": kw.get("moa"),
        "side_effects": kw.get("side_effects"),
        "contraindications": kw.get("contra"),
        "warnings": kw.get("warnings"),
        "drug_interactions": kw.get("interactions"),
        "pregnancy_category": kw.get("pregnancy"),
        "half_life": kw.get("half_life"),
        "storage_temp": kw.get(
            "storage", "Store below 30C, protected from light and moisture"),
        "max_daily_dose": kw.get("max_dose"),
        "cost_price": kw.get("cost", 0.0),
        "selling_price": kw.get("price", 0.0),
        "requires_prescription": kw.get("rx", True),
        "schedule_classification": kw.get(
            "schedule", "Schedule H - prescription required"),
    }


BATCH7_MEDICINES = [

    # =================================================================== #
    # ANTIBIOTICS
    # =================================================================== #
    _med(
        "Cefuroxime Axetil 500mg", "Cefuroxime",
        "Antibiotic - second generation cephalosporin",
        "Beta-lactam; inhibits cell wall synthesis",
        "Upper and lower respiratory tract infection, otitis media, sinusitis, urinary tract infection, skin infection",
        strength="500mg", form="tablet", brand="Ceftin",
        formula="C20H22N4O10S", weight="510.47 g/mol",
        half_life="1-2 hours",
        moa="Binds penicillin-binding proteins and inhibits the transpeptidation step of peptidoglycan cross-linking, so the cell wall cannot form and the bacterium lyses. It resists many of the beta-lactamases that inactivate first-generation cephalosporins.",
        side_effects="Diarrhoea, nausea, abdominal pain, headache, candidiasis, rash.",
        contra="Hypersensitivity to cephalosporins. Caution with a history of penicillin anaphylaxis.",
        warnings="TAKE WITH FOOD. Absorption of the axetil ester rises substantially with a meal and much of an empty-stomach dose is lost, so this is not a detail to omit. Complete the full course. A new rash may be sensitivity rather than the infection; stop and review. Reduce the dose when the creatinine clearance is below 30, because it is renally cleared.",
        interactions="Antacids and H2 blockers reduce absorption, proton pump inhibitors reduce it modestly, probenecid raises levels, may raise the INR with warfarin",
        pregnancy="B - considered acceptable",
        max_dose="500 mg twice daily",
        cost=34.0, price=88.0),

    _med(
        "Cefixime Dry Syrup 100mg/5ml", "Cefixime",
        "Antibiotic - third generation cephalosporin",
        "Beta-lactam; inhibits cell wall synthesis",
        "Paediatric respiratory infection, otitis media, urinary tract infection, typhoid",
        strength="100mg/5ml", form="suspension", brand="Taxim-O",
        formula="C16H15N5O7S2", weight="453.45 g/mol",
        half_life="3-4 hours",
        moa="Inhibits cell wall synthesis by binding penicillin-binding proteins. As a third-generation agent it is more active against Gram-negative organisms than cefuroxime, which is why it is used for enteric fever.",
        side_effects="Diarrhoea, loose stools, nausea, abdominal pain, rash, thrush.",
        contra="Hypersensitivity to cephalosporins.",
        warnings="THIS IS A PAEDIATRIC SUSPENSION AND THE DOSE IS BY WEIGHT, so it must be measured with the supplied spoon or an oral syringe - a household teaspoon varies from 3 to 7 ml and that range is a real dosing error. Shake well before every dose. Once reconstituted it keeps 7 days at room temperature or 14 days refrigerated; discard what remains rather than saving it for the next illness. Complete the course.",
        interactions="May increase the anticoagulant effect of warfarin; carbamazepine levels can rise",
        pregnancy="B - considered acceptable",
        max_dose="8 mg/kg/day in children",
        cost=78.0, price=168.0),

    _med(
        "Cefadroxil 500mg", "Cefadroxil",
        "Antibiotic - first generation cephalosporin",
        "Beta-lactam; inhibits cell wall synthesis",
        "Skin and soft tissue infection, urinary tract infection, pharyngitis, tonsillitis, dental infection",
        strength="500mg", form="capsule", brand="Droxyl",
        formula="C16H17N3O5S", weight="363.39 g/mol",
        half_life="1.5 hours",
        moa="Inhibits bacterial cell wall synthesis. It is well absorbed orally, which is why it is used for outpatient skin and throat infections that a first-generation agent can cover.",
        side_effects="Diarrhoea, nausea, rash, pruritus, candidiasis.",
        contra="Hypersensitivity to cephalosporins.",
        warnings="For streptococcal pharyngitis a full 10-day course is needed to prevent rheumatic fever, not the 5 days that suffices for many other infections - shortening it is the common error. Rash is more common than with later generations. Renal dosing applies below a creatinine clearance of 50.",
        interactions="Probenecid raises levels; may potentiate warfarin",
        pregnancy="B - considered acceptable",
        max_dose="2 g/day",
        cost=52.0, price=118.0),

    _med(
        "Clarithromycin 250mg", "Clarithromycin", "Antibiotic - macrolide",
        "Semi-synthetic macrolide; 50S ribosomal inhibitor",
        "Respiratory tract infection, Helicobacter pylori eradication, atypical mycobacterial infection, skin infection",
        strength="250mg", form="tablet", brand="Claribid",
        formula="C38H69NO13", weight="747.95 g/mol",
        half_life="3-4 hours, longer in renal impairment",
        moa="Binds the 50S ribosomal subunit and blocks translocation of the nascent peptide chain, so protein synthesis stops. It is the macrolide of choice in H. pylori regimens because it is acid-stable and reaches high gastric mucosal concentrations.",
        side_effects="Nausea, a metallic taste (dysgeusia), diarrhoea, abdominal pain, headache, rarely QT prolongation.",
        contra="Concurrent ergot alkaloids, cisapride, pimozide or terfenadine. Severe hepatic impairment.",
        warnings="THE INTERACTION PROFILE IS THE MAIN RISK. It is a strong CYP3A4 inhibitor, so it raises statin levels - simvastatin and atorvastatin in particular, risking rhabdomyolysis - as well as colchicine, carbamazepine and some benzodiazepines, and it markedly raises the INR with warfarin. Ask what else the patient takes before dispensing. QT prolongation is real; avoid with another QT-prolonging drug. The metallic taste is expected, and mentioning it in advance prevents it being mistaken for a new symptom.",
        interactions="Statins (rhabdomyolysis), warfarin (INR rises), carbamazepine, digoxin, colchicine, QT-prolonging drugs, rifabutin",
        pregnancy="C - avoid in the first trimester",
        max_dose="500 mg twice daily",
        cost=96.0, price=205.0),

    _med(
        "Erythromycin 250mg", "Erythromycin", "Antibiotic - macrolide",
        "Macrolide; 50S ribosomal inhibitor",
        "Upper respiratory infection, whooping cough, acne, chlamydial infection, penicillin alternative",
        strength="250mg", form="tablet", brand="Erythrocin",
        formula="C37H67NO13", weight="733.93 g/mol",
        half_life="1.5-2 hours",
        moa="Binds the 50S ribosomal subunit and inhibits translocation, halting bacterial protein synthesis. Bacteriostatic at usual concentrations and bactericidal at high ones.",
        side_effects="Abdominal cramps, nausea, vomiting, diarrhoea, rash. It is the most prokinetic macrolide, so gastrointestinal effects are more common than with clarithromycin.",
        contra="Hepatic impairment, porphyria, concurrent ergot alkaloids or terfenadine.",
        warnings="The gastrointestinal upset is genuinely worse than with the alternatives and is a common reason a course is abandoned - take it with food. It is a potent CYP3A4 inhibitor with the same interaction burden as clarithromycin, including statins and warfarin. The estolate salt causes cholestatic hepatitis and is avoided in adults.",
        interactions="Statins, warfarin, carbamazepine, digoxin, theophylline, QT-prolonging drugs, ergot alkaloids",
        pregnancy="B - considered acceptable",
        max_dose="2 g/day",
        cost=42.0, price=98.0),

    _med(
        "Tetracycline 500mg", "Tetracycline", "Antibiotic - tetracycline",
        "Broad-spectrum bacteriostatic; 30S ribosomal inhibitor",
        "Acne, chlamydial infection, mycoplasma infection, rickettsial infection, cholera, brucellosis",
        strength="500mg", form="capsule", brand="Tetracyn",
        formula="C22H24N2O8", weight="444.43 g/mol",
        half_life="6-12 hours",
        moa="Binds the 30S ribosomal subunit and blocks attachment of aminoacyl-tRNA, preventing addition of amino acids to the growing peptide chain.",
        side_effects="Nausea, diarrhoea, photosensitivity, oesophageal irritation, permanent tooth discolouration in children, fungal overgrowth.",
        contra="Children under 8 years, pregnancy, breastfeeding. Caution in hepatic or renal impairment.",
        warnings="DO NOT GIVE TO A CHILD UNDER 8 OR IN PREGNANCY - it chelates calcium in developing teeth and bone and causes permanent yellow-grey staining. TAKE WITH A FULL GLASS OF WATER ON AN EMPTY STOMACH and remain upright for at least 30 minutes; taking it lying down causes oesophageal ulceration. Separate it from milk, antacids, iron, calcium and zinc by at least 2 hours, because they bind it and it is then not absorbed at all. Photosensitivity is marked.",
        interactions="Antacids, iron, calcium, zinc, magnesium salts and milk all reduce absorption; warfarin; antagonises penicillins",
        pregnancy="D - avoid",
        max_dose="2 g/day",
        cost=28.0, price=72.0),

    _med(
        "Cotrimoxazole 960mg", "Sulfamethoxazole + Trimethoprim",
        "Antibiotic - sulfonamide combination",
        "Sequential blockade of bacterial folate synthesis",
        "Urinary tract infection, respiratory infection, Pneumocystis jirovecii pneumonia, toxoplasmosis, shigellosis",
        strength="800mg + 160mg", form="tablet", brand="Septran",
        formula="C10H11N3O3S + C14H18N4O3",
        weight="253.28 + 290.32 g/mol",
        half_life="10 hours",
        moa="A two-step blockade of the same pathway: sulfamethoxazole inhibits dihydropteroate synthase and trimethoprim inhibits dihydrofolate reductase. Using both gives a synergistic bactericidal effect that neither achieves alone.",
        side_effects="Nausea, rash, photosensitivity, hyperkalaemia, blood dyscrasias, and rarely Stevens-Johnson syndrome.",
        contra="Sulfonamide allergy, severe renal or hepatic impairment, glucose-6-phosphate dehydrogenase deficiency, porphyria, megaloblastic anaemia, late pregnancy, infants under 6 weeks.",
        warnings="STEVENS-JOHNSON SYNDROME IS THE SERIOUS RISK. The patient must be told to stop and report any rash or mouth ulcer immediately, particularly in the first weeks. It raises potassium, which matters most in a patient already on an ACE inhibitor, an ARB or a potassium-sparing diuretic - the combination can cause dangerous hyperkalaemia. It causes haemolysis in glucose-6-phosphate dehydrogenase deficiency, which is common in India, so check before a course. Take with plenty of water.",
        interactions="Warfarin (INR rises sharply), ACE inhibitors and ARBs and potassium-sparing diuretics (hyperkalaemia), methotrexate, phenytoin, sulfonylureas",
        pregnancy="D - avoid in the first trimester and near term",
        max_dose="Two tablets twice daily",
        cost=22.0, price=58.0),

    _med(
        "Clindamycin 300mg", "Clindamycin", "Antibiotic - lincosamide",
        "50S ribosomal inhibitor",
        "Skin and soft tissue infection, MRSA skin infection, dental and anaerobic infection, bone and joint infection",
        strength="300mg", form="capsule", brand="Dalacin C",
        formula="C18H33ClN2O5S", weight="424.98 g/mol",
        half_life="2-3 hours",
        moa="Binds the 50S ribosomal subunit and blocks peptide bond formation. Its practical value is reliable activity against most Staphylococcus aureus, including many community MRSA strains, and against anaerobes including Bacteroides.",
        side_effects="Diarrhoea (the commonest reason for stopping), nausea, abdominal pain, rash, antibiotics-associated colitis.",
        contra="Previous pseudomembranous colitis, hypersensitivity to lincosamides.",
        warnings="CLOSTRIDIOIDES DIFFICILE COLITIS IS THE DEFINING RISK and it can begin weeks after the course ends - tell the patient that diarrhoea starting up to a month later must be reported and must not be self-treated with an antidiarrhoeal. Take with a full glass of water, because it causes oesophageal irritation if it lodges. It does not cover Gram-negative organisms, so it is not a substitute for broad-spectrum cover in an undifferentiated serious infection.",
        interactions="Neuromuscular blockers (enhanced blockade), erythromycin (antagonism at the same ribosomal site), warfarin",
        pregnancy="B - considered acceptable",
        max_dose="1.8 g/day orally",
        cost=88.0, price=186.0),

    # =================================================================== #
    # ANTIFUNGALS
    # =================================================================== #
    _med(
        "Terbinafine 250mg", "Terbinafine", "Antifungal - allylamine",
        "Squalene epoxidase inhibitor",
        "Onychomycosis, tinea capitis, tinea corporis and cruris, dermatophyte skin infection",
        strength="250mg", form="tablet", brand="Terbicip",
        formula="C21H25N", weight="291.43 g/mol",
        half_life="About 36 hours; terminal tissue half-life up to 200 hours",
        moa="Inhibits fungal squalene epoxidase, blocking ergosterol synthesis. Unlike the imidazoles, the resulting squalene accumulation is directly toxic to the fungal cell, which makes terbinafine fungicidal against dermatophytes rather than merely fungistatic.",
        side_effects="Headache, gastrointestinal upset, altered taste that may persist for weeks, rash, and rarely hepatic injury, neutropenia or severe skin reaction.",
        contra="Chronic or active liver disease, severe renal impairment.",
        warnings="LIVER FUNCTION IS THE SAFETY ISSUE. It uncommonly causes serious hepatic injury, so check baseline liver function before a course for onychomycosis and tell the patient to report jaundice, dark urine, nausea or right upper abdominal pain at once. A taste disturbance is a distinctive effect that can last weeks after stopping. Fingernail infection needs about 6 weeks and toenail infection about 12, because the drug must reach the growing nail - and that long course is exactly why the liver check matters.",
        interactions="Rifampicin reduces levels, cimetidine raises them, MAO inhibitors, and it inhibits CYP2D6 so it raises levels of tricyclics, some SSRIs and beta blockers",
        pregnancy="B - use only if clearly needed",
        max_dose="250 mg once daily",
        cost=168.0, price=342.0),

    _med(
        "Itraconazole 100mg", "Itraconazole", "Antifungal - triazole",
        "Ergosterol synthesis inhibitor (14-alpha demethylase)",
        "Dermatophytosis, onychomycosis, systemic and deep mycosis, vulvovaginal candidiasis, aspergillosis",
        strength="100mg", form="capsule", brand="Itrasys",
        formula="C35H38Cl2N8O4", weight="705.63 g/mol",
        half_life="20-36 hours, considerably longer in tissue",
        moa="Inhibits cytochrome P450-dependent 14-alpha demethylase, blocking conversion of lanosterol to ergosterol and disrupting the fungal cell membrane. It has a broader spectrum than fluconazole and is active against Aspergillus.",
        side_effects="Nausea, abdominal pain, headache, rash, and with prolonged use hypokalaemia, oedema, and rarely hepatic injury or heart failure.",
        contra="Ventricular dysfunction or heart failure, pregnancy except for life-threatening mycosis, and concurrent cisapride, midazolam, pimozide, quinidine or ergot alkaloids.",
        warnings="ABSORPTION DEPENDS ENTIRELY ON THE FORMULATION. The ordinary capsule must be taken with a full meal and with something acidic, because stomach acid is needed to dissolve it. A patient on a proton pump inhibitor or an antacid absorbs very little, and that is a common and silent cause of treatment failure. It is a potent CYP3A4 inhibitor with a long interaction list including statins and warfarin, and it can precipitate heart failure, so ask about cardiac history.",
        interactions="Statins (rhabdomyolysis), warfarin, digoxin, midazolam, phenytoin, rifampicin, antacids and proton pump inhibitors (reduce absorption), cisapride",
        pregnancy="C - avoid except for life-threatening infection",
        max_dose="400 mg/day",
        cost=142.0, price=298.0),

    _med(
        "Griseofulvin 250mg", "Griseofulvin", "Antifungal - grisan",
        "Fungal microtubule disruption",
        "Tinea capitis, particularly in children; dermatophyte infection of skin and nails not responding to topical treatment",
        strength="250mg", form="tablet", brand="Grisovin",
        formula="C17H17ClO6", weight="352.77 g/mol",
        half_life="9-24 hours",
        moa="Disrupts fungal microtubule function, interfering with mitosis and new cell wall synthesis. It is taken up by keratin-forming cells and incorporated into keratin itself, so the fungus meets the drug as skin and nail grow - which is why it works only where new keratin is being laid down.",
        side_effects="Headache, gastrointestinal upset, photosensitivity, dizziness, rarely blood dyscrasias or hepatic injury.",
        contra="Porphyria, severe liver disease, systemic lupus erythematosus, pregnancy.",
        warnings="The mechanism explains the duration: because it works only through growing keratin, treatment must continue until the infected skin or nail has grown out completely - weeks for skin, months for nails. TAKE WITH A FATTY MEAL, which greatly improves absorption. It remains the most reliable agent for Microsporum tinea capitis in children. Avoid in pregnancy, as it is teratogenic, and do not drink alcohol, which causes a disulfiram-like reaction.",
        interactions="Warfarin (effect reduced), phenobarbital (griseofulvin levels fall), oral contraceptives (may fail), alcohol (disulfiram reaction)",
        pregnancy="D - contraindicated; effective contraception required",
        max_dose="1 g/day in adults",
        cost=64.0, price=142.0),

    # =================================================================== #
    # UROLOGICAL - a high-volume category that had no representative at all.
    # =================================================================== #
    _med(
        "Tamsulosin 0.4mg", "Tamsulosin",
        "Urological - alpha-1 blocker",
        "Selective alpha-1A adrenergic antagonist",
        "Benign prostatic hyperplasia, lower urinary tract symptoms",
        strength="0.4mg", form="modified-release capsule", brand="Urimax",
        formula="C20H28N2O5S", weight="408.51 g/mol",
        half_life="9-15 hours",
        moa="Relaxes the smooth muscle of the prostate and bladder neck by blocking alpha-1A adrenergic receptors, which improves urine flow without shrinking the prostate. Symptom relief begins within days, unlike finasteride which takes months.",
        side_effects="Dizziness, postural hypotension, retrograde or absent ejaculation, headache, rhinitis.",
        contra="Postural hypotension, severe hepatic impairment. Caution with cataract surgery, since it causes intraoperative floppy iris syndrome.",
        warnings="TAKE AFTER THE SAME MEAL EACH DAY and swallow the modified-release capsule whole - crushing or chewing it releases the dose at once and causes a sharp fall in blood pressure. Dizziness is worst in the first weeks, so rise slowly and avoid driving until the effect is known. RETROGRADE EJACULATION IS COMMON and men are often not warned, which is a genuine reason they stop taking it. TELL ANY EYE SURGEON BEFORE CATARACT SURGERY, because of intraoperative floppy iris syndrome. It relieves symptoms but does not treat progression, so it continues rather than cures.",
        interactions="Other alpha blockers and antihypertensives (additive hypotension), PDE5 inhibitors (caution with the first dose), ketoconazole and other strong CYP3A4 inhibitors raise levels",
        pregnancy="Not applicable",
        max_dose="0.8 mg once daily",
        cost=142.0, price=286.0),

    _med(
        "Finasteride 5mg", "Finasteride", "Urological - 5-alpha reductase inhibitor",
        "Type 2 5-alpha reductase inhibitor",
        "Benign prostatic hyperplasia",
        strength="5mg", form="tablet", brand="Finast",
        formula="C23H36N2O2", weight="372.55 g/mol",
        half_life="6-8 hours, with tissue effects lasting much longer",
        moa="Inhibits type 2 5-alpha reductase, blocking conversion of testosterone to dihydrotestosterone. The prostate then shrinks over months rather than relaxing within days, which is the opposite timescale to an alpha blocker.",
        side_effects="Reduced libido, erectile dysfunction, reduced ejaculate volume, depression, rarely gynaecomastia.",
        contra="Women of childbearing potential; pregnancy. Children.",
        warnings="IT TAKES ABOUT SIX MONTHS TO SHOW BENEFIT - do not judge it after weeks, and tell the patient that at the outset or adherence fails. IT ROUGHLY HALVES THE PSA, so the measured value must be DOUBLED before interpretation, and any RISE on treatment needs urological assessment rather than reassurance. PREGNANT WOMEN MUST NOT HANDLE CRUSHED OR BROKEN TABLETS - it is a teratogen absorbed through intact skin, and a male fetus exposed can have abnormal genitalia. Sexual side effects usually reverse on stopping, but occasionally persist.",
        interactions="Minimal; it is not a significant enzyme inducer or inhibitor",
        pregnancy="X - contraindicated; women must not handle crushed tablets",
        max_dose="5 mg once daily",
        cost=168.0, price=328.0),

    _med(
        "Oxybutynin 5mg", "Oxybutynin", "Urological - antimuscarinic",
        "Non-selective muscarinic receptor antagonist",
        "Overactive bladder, urgency and urge incontinence",
        strength="5mg", form="tablet", brand="Ditropan",
        formula="C22H31NO3", weight="357.49 g/mol",
        half_life="2-3 hours, longer in the elderly",
        moa="Blocks muscarinic receptors on the detrusor muscle, reducing the involuntary contractions that cause urgency and urge incontinence.",
        side_effects="Dry mouth (very common), constipation, blurred vision, urinary retention, confusion and cognitive impairment in the elderly.",
        contra="Urinary retention, gastric retention, uncontrolled narrow-angle glaucoma, myasthenia gravis.",
        warnings="DRY MOUTH AFFECTS MOST PATIENTS and is the usual reason for stopping - sugar-free gum, sips of water and oral care help, and it does tend to lessen. It carries one of the highest anticholinergic burdens of any commonly used drug, so ask about glaucoma, constipation and urinary retention before each supply, and review whether the benefit is worth it. It is a Beers Criteria drug in the elderly, where the cognitive and fall risks are substantial.",
        interactions="Other anticholinergics (additive burden), potassium chloride (ulceration with an insoluble form), and it is a substrate of CYP3A4",
        pregnancy="B - use with caution",
        max_dose="20 mg/day",
        cost=86.0, price=178.0),

    _med(
        "Tadalafil 10mg", "Tadalafil", "Urological - PDE5 inhibitor",
        "Phosphodiesterase type 5 inhibitor",
        "Erectile dysfunction, lower urinary tract symptoms of benign prostatic hyperplasia",
        strength="10mg", form="tablet", brand="Tadalis",
        formula="C22H19N3O4", weight="389.40 g/mol",
        half_life="17.5 hours",
        moa="Inhibits phosphodiesterase type 5, so cyclic GMP is not broken down and the smooth muscle of the corpus cavernosum relaxes. Nitric oxide from sexual stimulation is therefore required for it to work, which is why it is not effective without arousal.",
        side_effects="Headache, flushing, dyspepsia, nasal congestion, back and muscle pain, dizziness.",
        contra="ABSOLUTE: any nitrate or nicorandil. Non-arteritic ischaemic optic neuropathy. Severe cardiovascular disease unsuitable for sexual activity.",
        warnings="IT MUST NEVER BE TAKEN WITH A NITRATE OR NICORANDIL - the combination causes profound, refractory hypotension and has been fatal. ASK SPECIFICALLY ABOUT GLYCERYL TRINITRATE FOR ANGINA BEFORE EVERY SUPPLY. Tell the patient that if they develop chest pain they must tell the attending clinician they have taken this, because a nitrate cannot then safely be given - the long half-life leaves an interaction window of about 48 hours. Priapism, though rare, is a surgical emergency and needs immediate attendance. It requires sexual stimulation to work.",
        interactions="Nitrates and nicorandil (absolutely contraindicated), alpha blockers (hypotension), strong CYP3A4 inhibitors such as clarithromycin and itraconazole raise levels, grapefruit juice",
        pregnancy="Not applicable",
        max_dose="20 mg per dose, or 5 mg daily for continuous use",
        cost=124.0, price=252.0),

    # =================================================================== #
    # ENDOCRINE - the antithyroid drug and the low levothyroxine strength.
    # =================================================================== #
    _med(
        "Carbimazole 10mg", "Carbimazole", "Antithyroid agent",
        "Thionamide; inhibits thyroid peroxidase",
        "Hyperthyroidism, Graves disease, preparation for thyroid surgery or radioiodine",
        strength="10mg", form="tablet", brand="Neomercazole",
        formula="C7H10N2O2S", weight="186.23 g/mol",
        half_life="The drug is a prodrug of methimazole; methimazole half-life is 4-6 hours",
        moa="Inhibits thyroid peroxidase, blocking iodination of tyrosine residues and the coupling of iodotyrosines, so new thyroid hormone cannot be made. It does not affect hormone already stored, which is why the response takes two to four weeks - the store must run down first.",
        side_effects="Rash, pruritus, nausea, altered taste, and rarely agranulocytosis, aplastic anaemia, cholestatic jaundice and vasculitis.",
        contra="Severe blood dyscrasia, previous agranulocytosis with a thionamide, severe hepatic impairment.",
        warnings="AGRANULOCYTOSIS IS THE SERIOUS AND DOSE-INDEPENDENT RISK. TELL EVERY PATIENT TO STOP THE DRUG AND SEEK IMMEDIATE CARE FOR A SORE THROAT, FEVER OR MOUTH ULCER WITHOUT WAITING FOR THE NEXT APPOINTMENT - it is reversible if the drug is stopped and a full blood count is taken at once, and fatal if it is not. A blood count should be checked at the start and if any infection appears. Report jaundice or dark urine urgently. Because the effect takes weeks, do not increase the dose on symptoms alone - monitor thyroid function. It is teratogenic in the first trimester, so a pregnancy must be managed with propylthiouracil instead and specialist advice sought early.",
        interactions="Warfarin (anticoagulant effect altered), digoxin, theophylline, and thyroid function tests need interpreting on treatment rather than against normal ranges",
        pregnancy="D in the first trimester - switch to propylthiouracil under specialist care",
        max_dose="60 mg/day",
        cost=42.0, price=94.0),

    _med(
        "Levothyroxine 25mcg", "Levothyroxine", "Thyroid hormone",
        "Synthetic thyroxine (T4) sodium",
        "Hypothyroidism, myxoedema, goitre, thyroid suppression after thyroidectomy",
        strength="25mcg", form="tablet", brand="Thyronorm 25",
        formula="C15H10I4NNaO4", weight="798.85 g/mol",
        half_life="6-7 days",
        moa="A synthetic form of thyroxine that is converted peripherally to the active triiodothyronine, replacing the hormone the thyroid is not producing. Because it is converted rather than acting directly, the response is slow and the long half-life means the dose is adjusted only after weeks.",
        side_effects="At replacement dose, none. Excess causes palpitations, tremor, insomnia, sweating, weight loss and, in the elderly or those with ischaemic heart disease, angina and atrial fibrillation.",
        contra="Untreated thyrotoxicosis, untreated adrenal insufficiency (which must be corrected first), acute myocardial infarction.",
        warnings="THIS IS THE 25 MICROGRAM STRENGTH AND IT IS ONE OF SEVERAL IDENTICAL-LOOKING TABLETS - the strengths differ only by the number on the pack, so the pack must be read every time and the strength never assumed. TAKE ON AN EMPTY STOMACH 30-60 MINUTES BEFORE FOOD, at the same time daily. SEPARATE IT FROM IRON, CALCIUM, ANTACIDS AND PROTON PUMP INHIBITORS BY AT LEAST FOUR HOURS - they bind it and prevent absorption, which is one of the commonest reasons a TSH stays high on a dose that looks adequate on paper. This low strength is used to START treatment, especially in the elderly and in ischaemic heart disease, where a full replacement dose can precipitate angina. Thyroid function is rechecked 6-8 weeks after any change, never sooner, because of the long half-life.",
        interactions="Iron, calcium, antacids, proton pump inhibitors and sucralfate reduce absorption; warfarin (effect altered); it raises requirements for insulin and oral hypoglycaemics",
        pregnancy="A - safe and usually the dose must be INCREASED, not stopped",
        max_dose="Usually titrated to effect; typical full replacement is 1.6 mcg/kg/day",
        cost=26.0, price=58.0),

    # =================================================================== #
    # GASTROINTESTINAL, OBSTETRIC AND SUPPORTIVE.
    # =================================================================== #
    _med(
        "Ondansetron Mouth Dissolving 4mg", "Ondansetron",
        "Antiemetic",
        "5-HT3 serotonin receptor antagonist",
        "Nausea and vomiting from chemotherapy, radiotherapy, surgery or acute gastroenteritis",
        strength="4mg", form="mouth dissolving tablet", brand="Emeset MD",
        formula="C18H19N3O", weight="293.36 g/mol",
        half_life="3-6 hours",
        moa="Blocks 5-HT3 receptors on vagal afferents and in the chemoreceptor trigger zone, blocking the serotonin signal that triggers the vomiting reflex. Serotonin released from the gut is the main driver of chemotherapy-induced and gastroenteritis nausea, which is why it works so well there.",
        side_effects="Headache, constipation, flushing, and rarely QT prolongation or a transient rise in liver enzymes.",
        contra="Concurrent apomorphine. Caution in congenital long QT syndrome.",
        warnings="THE MOUTH-DISSOLVING FORM IS DELIBERATE: place the tablet on the tongue and let it dissolve without water, because a patient who is vomiting may not keep a tablet and a glass of water down. Constipation is a common consequence of a regular course. Do not exceed 16 mg in 24 hours, and avoid other QT-prolonging drugs. It works poorly for motion sickness, which is a different mechanism (histamine and acetylcholine, not serotonin), so it is the wrong choice there. Correct any magnesium or potassium abnormality before use, since that raises the arrhythmia risk.",
        interactions="Apomorphine (severe hypotension - contraindicated), other QT-prolonging drugs, tramadol (reduced analgesia), phenytoin and rifampicin reduce levels",
        pregnancy="B - considered acceptable; best established antiemetic safety data after doxylamine/pyridoxine",
        max_dose="16 mg/day",
        cost=48.0, price=106.0),

    _med(
        "Doxylamine + Pyridoxine", "Doxylamine + Pyridoxine",
        "Antiemetic - antihistamine with vitamin B6",
        "H1 antihistamine (doxylamine) with pyridoxine",
        "Nausea and vomiting of pregnancy (morning sickness)",
        strength="10mg + 10mg", form="delayed-release tablet", brand="Doxinate",
        formula="C17H22N2O + C8H11NO3",
        weight="270.37 + 169.18 g/mol",
        half_life="Doxylamine about 10 hours",
        moa="Doxylamine blocks histamine H1 receptors in the chemoreceptor trigger zone and vestibular pathways, while pyridoxine corrects the relative vitamin B6 deficiency associated with pregnancy nausea. The combination is the one actually tested for this indication.",
        side_effects="Drowsiness (the main effect), dizziness, dry mouth, constipation.",
        contra="Uncontrolled asthma, narrow-angle glaucoma, urinary retention, concurrent MAO inhibitor.",
        warnings="DROWSINESS IS MARKED AND IS THE MAIN LIMITATION - taking the larger dose at bedtime and a smaller one in the day is often better tolerated, and the patient must not drive or operate machinery until the effect is known. It is the first-line treatment for nausea of pregnancy and the combination specifically studied for it. If vomiting is so severe that nothing is kept down, that is hyperemesis gravidarum and needs assessment and possibly admission, not a stronger antiemetic.",
        interactions="MAO inhibitors (contraindicated), other central nervous system depressants including alcohol, and it may potentiate anticholinergics",
        pregnancy="A - the first-line choice for nausea and vomiting of pregnancy",
        max_dose="Usually two tablets at bedtime and one in the morning",
        cost=68.0, price=148.0),

    # NOTE: "Domperidone 10mg" is NOT defined here. Batch 5 already carries it
    # with fuller detail, so a second definition would be dropped by the seeder
    # and would inflate the published count. The seeder keys on the medicine
    # NAME, and test_catalogue.py now fails on a repeat rather than letting it
    # pass silently - which is how this was caught.

    _med(
        "Ursodeoxycholic Acid 300mg", "Ursodeoxycholic Acid",
        "Hepatobiliary - bile acid",
        "Hydrophilic bile acid; reduces cholesterol saturation",
        "Primary biliary cholangitis, cholestatic liver disease, gallstone dissolution",
        strength="300mg", form="tablet", brand="Ursocol",
        formula="C24H40O4", weight="392.57 g/mol",
        half_life="3-5 days",
        moa="Replaces hydrophobic bile acids in the bile pool with a hydrophilic one, which reduces cholesterol saturation and protects hepatocytes from bile-acid-induced injury. In primary biliary cholangitis it improves liver biochemistry and slows histological progression.",
        side_effects="Diarrhoea or loose stools (dose-related and the commonest effect), nausea, abdominal pain, rarely pruritus.",
        contra="Acute inflammation of the gall bladder or biliary tract, complete biliary obstruction, calcified gallstones.",
        warnings="A PATIENT WHO DEVELOPS DIARRHOEA ON A HIGHER DOSE USUALLY NEEDS THE DOSE REDUCED, NOT THE DRUG STOPPED - it is dose-related and manageable. In primary biliary cholangitis the dose is calculated by body weight rather than the fixed 300 mg, and the treatment is long-term, often life-long. It is not a substitute for gallbladder surgery in symptomatic gallstones.",
        interactions="Aluminium-based antacids and colestyramine reduce absorption - separate them by at least 2 hours; oestrogens increase cholesterol saturation and oppose it",
        pregnancy="B - use with caution; specialist advice in cholestasis of pregnancy",
        max_dose="Usually 13-15 mg/kg/day in primary biliary cholangitis",
        cost=186.0, price=372.0),

    _med(
        "Methotrexate 2.5mg", "Methotrexate", "Antirheumatic - DMARD",
        "Dihydrofolate reductase inhibitor; folic acid antagonist",
        "Rheumatoid arthritis, psoriasis, psoriatic arthritis",
        strength="2.5mg", form="tablet", brand="Folitrax",
        formula="C20H22N8O5", weight="454.44 g/mol",
        half_life="3-10 hours at low dose, longer at high dose",
        moa="Inhibits dihydrofolate reductase and, at the low weekly doses used in rheumatology, also increases extracellular adenosine - which is the effect that actually suppresses inflammation. The folate antagonism is the source of most of its toxicity, which is why folic acid is given alongside.",
        side_effects="Nausea, mouth ulcers, fatigue, raised liver enzymes, bone marrow suppression, hair thinning, and rarely pneumonitis or hepatic fibrosis.",
        contra="Pregnancy and breastfeeding, significant hepatic or renal impairment, active infection, blood dyscrasia, alcohol dependence.",
        warnings="ONCE A WEEK, NEVER DAILY. THIS IS THE SINGLE MOST DANGEROUS DISPENSING ERROR IN ROUTINE PHARMACY PRACTICE AND IT HAS KILLED PATIENTS: daily dosing causes marrow aplasia and mucositis. WRITE THE DAY OF THE WEEK ON THE LABEL and ask the patient to repeat the schedule back. FOLIC ACID 5 MG IS TAKEN ON THE OTHER DAYS, NOT THE SAME DAY, to reduce mouth ulcers and nausea. Baseline and periodic blood counts and liver function are mandatory. A NEW BREATHLESSNESS OR DRY COUGH NEEDS URGENT REVIEW - pneumonitis is uncommon but can be fatal. It is teratogenic, so effective contraception is needed by both partners, and it must be stopped well before conception. Avoid alcohol entirely.",
        interactions="NSAIDs and cotrimoxazole increase toxicity sharply, trimethoprim is contraindicated, penicillins raise levels, and it is antagonised by folic acid supplements taken on the same day",
        pregnancy="X - contraindicated; effective contraception for both partners",
        max_dose="Usually up to 25 mg once weekly in rheumatology",
        cost=58.0, price=126.0),

    _med(
        "Hydroxychloroquine 200mg", "Hydroxychloroquine", "Antirheumatic - DMARD",
        "4-aminoquinoline; immunomodulator",
        "Rheumatoid arthritis, systemic lupus erythematosus, discoid lupus, malaria",
        strength="200mg", form="tablet", brand="HCQS",
        formula="C18H26ClN3O", weight="335.87 g/mol",
        half_life="About 40 days, with tissue accumulation over months",
        moa="Raises the pH within lysosomes and interferes with antigen processing in antigen-presenting cells, damping the autoimmune response. It also has mild antithrombotic and lipid-lowering effects, which is part of why it improves survival in lupus rather than merely symptoms.",
        side_effects="Nausea, abdominal discomfort, skin pigmentation, hair lightening, and with long-term use retinal toxicity and corneal deposits.",
        contra="Pre-existing retinopathy, maculopathy.",
        warnings="AN ANNUAL OPHTHALMIC EXAMINATION IS REQUIRED, and the daily dose should be capped at 5 mg per kilogram of ACTUAL body weight rather than a blanket 400 mg - retinal toxicity is dose-per-weight and duration related, and it is irreversible once established. IT TAKES 6 TO 12 WEEKS TO WORK, so neither patient nor prescriber should judge it early. Take with food or milk to reduce nausea. It is generally the SAFEST systemic antirheumatic in pregnancy and is continued in lupus rather than stopped, which is the opposite of methotrexate. It can worsen psoriasis.",
        interactions="Antacids and kaolin reduce absorption (separate by 4 hours), amiodarone and moxifloxacin raise the cardiac risk, it may increase digoxin levels, and it reduces the antibody response to rabies and some other vaccines",
        pregnancy="B - considered acceptable and usually continued in lupus",
        max_dose="5 mg/kg of body weight per day",
        cost=88.0, price=184.0),

    _med(
        "Dexamethasone 0.5mg", "Dexamethasone", "Corticosteroid",
        "Long-acting synthetic glucocorticoid",
        "Inflammatory and allergic conditions, cerebral oedema, antiemetic adjunct with chemotherapy",
        strength="0.5mg", form="tablet", brand="Decadron",
        formula="C22H29FO5", weight="392.46 g/mol",
        half_life="Biological half-life 36-54 hours, considerably longer than the plasma half-life",
        moa="Binds the intracellular glucocorticoid receptor and modifies gene transcription, suppressing inflammatory mediators and the immune response. Its long biological half-life means the effect outlasts the drug in plasma, which is why it can be given once daily.",
        side_effects="Insomnia, mood change including euphoria or hypomania, raised blood glucose, increased appetite, fluid retention, and with prolonged use osteoporosis, cataract and adrenal suppression.",
        contra="Systemic fungal infection, live vaccines in immunosuppressed patients, concurrent use in undiagnosed infection.",
        warnings="NEVER STOP ABRUPTLY AFTER MORE THAN ABOUT THREE WEEKS - it suppresses the adrenal axis and abrupt withdrawal can precipitate an adrenal crisis, so the dose must be tapered. IT RAISES BLOOD GLUCOSE MARKEDLY, so a diabetic needs closer monitoring and possibly a dose change. INSOMNIA AND MOOD CHANGE ARE COMMON - take it in the morning with food to reduce both, and warn about the possibility of a hypomanic reaction. This is not interchangeable with hydrocortisone in adrenal insufficiency, where the dose and timing are entirely different.",
        interactions="NSAIDs (gastrointestinal ulceration), live vaccines, insulin and oral hypoglycaemics (effect opposed), rifampicin and phenytoin reduce the effect, it lowers potassium and so adds to the arrhythmia risk with digoxin",
        pregnancy="C - use only if clearly needed",
        max_dose="Dependent on indication; widely variable",
        cost=18.0, price=46.0),

    _med(
        "Clobetasol Propionate 0.05% Cream", "Clobetasol Propionate",
        "Topical corticosteroid - superpotent",
        "Very potent topical glucocorticoid",
        "Severe eczema, psoriasis, lichen planus, discoid lupus",
        strength="0.05%", form="cream", brand="Tenovate",
        formula="C25H32ClFO5", weight="466.97 g/mol",
        half_life="Not applicable for topical use; systemic absorption is limited but real over large areas",
        moa="Binds the glucocorticoid receptor in the skin and suppresses the inflammatory cascade locally, reducing erythema, scaling and itching. It is a superpotent (class I) steroid, around 500 times as potent as hydrocortisone.",
        side_effects="Skin atrophy, striae, telangiectasia, hypopigmentation, acneiform eruption, perioral dermatitis, and with occlusion or large areas, adrenal suppression.",
        contra="Untreated bacterial, fungal or viral skin infection, rosacea, perioral dermatitis, acne vulgaris, and application to the face, groin or axillae.",
        warnings="THIS IS A SUPERPOTENT STEROID AND THE RULES ARE NOT ADMINISTRATIVE DETAIL: use SHORT courses, usually no more than two weeks, and no more than 50 g a week. DO NOT APPLY IT TO THE FACE, GROIN OR AXILLAE, where absorption is high and atrophy, telangiectasia and permanent striae develop quickly. NEVER USE IT ALONE ON A FUNGAL INFECTION - a steroid applied to ringworm suppresses the inflammation and makes the rash spread while changing its appearance, which frequently delays diagnosis. Do not use on an undiagnosed rash or on a child without specific medical advice. Atrophy from prolonged use is permanent and does not recover.",
        interactions="None significant by the topical route, but it adds to the systemic steroid burden if used over large areas",
        pregnancy="C - use the minimum amount for the shortest time",
        max_dose="Maximum 50 g per week",
        cost=52.0, price=118.0),

    # =================================================================== #
    # NEUROLOGY, VESTIBULAR AND ANTI-INFECTIVE.
    # =================================================================== #
    _med(
        "Amitriptyline 10mg", "Amitriptyline", "Tricyclic antidepressant",
        "Tertiary amine tricyclic; serotonin and noradrenaline reuptake inhibitor",
        "Neuropathic pain, migraine prophylaxis, depression",
        strength="10mg", form="tablet", brand="Tryptomer",
        formula="C20H23N", weight="277.40 g/mol",
        half_life="10-28 hours including the active metabolite nortriptyline",
        moa="Inhibits reuptake of serotonin and noradrenaline and blocks sodium channels. At the low doses used for pain and migraine it is the sodium channel blockade and the descending pain-pathway modulation that matter, not the antidepressant effect - which is why it works for nerve pain at doses far below those used for depression.",
        side_effects="Drowsiness, dry mouth, constipation, blurred vision, urinary hesitancy, weight gain, and rarely arrhythmia.",
        contra="Concurrent or recent MAO inhibitor, recent myocardial infarction, arrhythmia, severe liver disease, narrow-angle glaucoma.",
        warnings="AT THIS DOSE IT IS A PAIN AND SLEEP DRUG, NOT AN ANTIDEPRESSANT - say so plainly, or a patient given 10 mg for nerve pain and told it is an antidepressant will reasonably object that their depression is not being treated. TAKE IT AT BEDTIME and use the sedation deliberately. The anticholinergic effects are the usual reason for stopping and do tend to lessen. It must never be combined with an MAO inhibitor. It prolongs the QT interval, so review other cardiac-risk drugs.",
        interactions="MAO inhibitors (contraindicated - hypertensive crisis), other serotonergic drugs, other anticholinergics (additive burden), tramadol and St John's wort (serotonin syndrome risk)",
        pregnancy="C - use only if clearly needed",
        max_dose="150 mg/day in depression; 10-25 mg nightly for neuropathic pain",
        cost=32.0, price=72.0),

    _med(
        "Flunarizine 10mg", "Flunarizine", "Antimigraine - calcium channel blocker",
        "Selective calcium channel blocker with antihistamine activity",
        "Migraine prophylaxis, vertigo",
        strength="10mg", form="tablet", brand="Flunarin",
        formula="C26H26F2N2", weight="404.50 g/mol",
        half_life="About 18 days - the key fact about this drug",
        moa="Blocks calcium channels in cerebrovascular smooth muscle and stabilises neuronal membranes, preventing the cortical spreading depression thought to underlie migraine aura. It also blocks histamine and dopamine receptors, which accounts for the sedation and the extrapyramidal effects.",
        side_effects="Drowsiness, weight gain, dry mouth, and importantly depression and extrapyramidal effects including a parkinsonism-like syndrome.",
        contra="History of depression, extrapyramidal disease including parkinsonism, pregnancy and breastfeeding, and children under 12.",
        warnings="THE HALF-LIFE IS ABOUT 18 DAYS, so it accumulates steadily over the first weeks - keep the dose low, take it at night to use the sedation, and expect any adverse effect to take WEEKS to resolve after stopping. DO NOT USE IT IN ANYONE WITH DEPRESSION OR A HISTORY OF IT, and stop it at once if mood falls. WEIGHT GAIN IS VERY COMMON - warn the patient in advance, because it is a frequent reason for stopping. It is normally used for a limited period rather than indefinitely, because of accumulation. In the elderly the extrapyramidal and sedative risks make it a poor choice.",
        interactions="Central nervous system depressants including alcohol (additive sedation), and it adds to the sedative burden of antihistamines and benzodiazepines",
        pregnancy="D - avoid; effective contraception while taking it",
        max_dose="10 mg nightly; usually limited to about 6 months",
        cost=72.0, price=158.0),

    _med(
        "Propranolol 20mg", "Propranolol", "Beta blocker",
        "Non-selective beta-adrenergic antagonist",
        "Migraine prophylaxis, tremor, anxiety, thyrotoxicosis adjunct, angina",
        strength="20mg", form="tablet", brand="Ciplar",
        formula="C16H21NO2", weight="259.34 g/mol",
        half_life="3-6 hours",
        moa="Blocks beta-1 and beta-2 adrenergic receptors. In migraine prophylaxis it is thought to act centrally, reducing cortical excitability and the noradrenergic drive to the cranial vasculature - the mechanism is not fully established, but the efficacy is.",
        side_effects="Fatigue, cold extremities, bradycardia, vivid dreams and nightmares, bronchospasm, masking of hypoglycaemia symptoms.",
        contra="Asthma, COPD with bronchospasm, sinus bradycardia, second or third degree heart block, cardiogenic shock, decompensated heart failure.",
        warnings="DO NOT USE IT IN ASTHMA OR COPD - it is the least selective beta blocker and causes bronchospasm. NEVER STOP IT ABRUPTLY after a long course: withdrawal can precipitate angina, arrhythmia or a myocardial infarction, so taper over weeks. IT MASKS THE WARNING SIGNS OF HYPOGLYCAEMIA in a diabetic - sweating is preserved but tremor and palpitations are not, so the patient cannot rely on their usual symptoms. Vivid dreams and nightmares are common and improve if the dose is taken earlier in the day. Prophylaxis takes several weeks to work and is usually continued for months.",
        interactions="Verapamil and diltiazem (bradycardia and heart block), insulin and oral hypoglycaemics (masked hypoglycaemia), NSAIDs (reduced antihypertensive effect), adrenaline (hypertensive response), other antiarrhythmics",
        pregnancy="C - use only if clearly needed; specialist advice in the third trimester",
        max_dose="For migraine prophylaxis usually 80-160 mg/day in divided doses",
        cost=26.0, price=62.0),

    _med(
        "Betahistine 8mg", "Betahistine", "Antivertigo agent",
        "Histamine H1 agonist and H3 antagonist",
        "Meniere disease, vertigo of vestibular origin",
        strength="8mg", form="tablet", brand="Vertin",
        formula="C8H12N2", weight="136.19 g/mol",
        half_life="3-4 hours",
        moa="A histamine analogue that improves the microcirculation of the inner ear and reduces endolymphatic pressure, which is the mechanism held to relieve Meniere attacks. It is a symptomatic treatment and does not cure the underlying disorder.",
        side_effects="Mild nausea, dyspepsia, headache, and rarely rash or pruritus.",
        contra="Phaeochromocytoma. Caution in asthma and peptic ulcer disease, where histamine effects may aggravate them.",
        warnings="TAKE WITH FOOD to reduce dyspepsia. IT IS SYMPTOMATIC AND SLOW - improvement takes weeks, so tell the patient at the outset that no benefit in the first week is not failure and does not justify stopping. Meniere disease also requires salt restriction and usually specialist assessment. It does not work for vertigo of central origin, so persistent, atypical or progressive vertigo needs assessment to find the cause rather than another course.",
        interactions="Antihistamines (may oppose its effect), and it should be used with care alongside other histamine-related medicines",
        pregnancy="Not recommended - insufficient safety data",
        max_dose="48 mg/day",
        cost=48.0, price=106.0),

    _med(
        "Ivermectin 12mg", "Ivermectin", "Antiparasitic",
        "Avermectin; glutamate-gated chloride channel activator",
        "Strongyloidiasis, scabies, onchocerciasis, lymphatic filariasis",
        strength="12mg", form="tablet", brand="Ivermec",
        formula="C48H74O14", weight="875.09 g/mol",
        half_life="16-18 hours",
        moa="Opens glutamate-gated chloride channels in invertebrate nerve and muscle cells, causing hyperpolarisation and paralysis of the parasite. These channels are absent in humans, which is the basis of its selectivity and its wide margin of safety.",
        side_effects="Dizziness, nausea, diarrhoea, pruritus, and with microfilarial infection a Mazzotti reaction of fever, rash, dizziness and hypotension as the parasites die.",
        contra="Concurrent Loa loa infection with high microfilaraemia (risk of encephalopathy), children under 5 kg, pregnancy.",
        warnings="TAKE ON AN EMPTY STOMACH WITH WATER - food, and especially a fatty meal, markedly raises absorption and therefore the risk of neurotoxicity. IN ONCHOCERCIASIS, WARN ABOUT THE MAZZOTTI REACTION: fever, rash and dizziness as the microfilariae die, which can be severe and need hospital care. For scabies it is used when a topical agent is unsuitable or in crusted scabies alongside topical treatment, and all close contacts must be treated at the same time or reinfection follows. It is NOT a treatment or preventive for COVID-19 - controlled trials did not support that, and using it so squanders a drug with real value in parasitic disease.",
        interactions="Central nervous system depressants (additive), diazepam, barbiturates, and caution with warfarin",
        pregnancy="C - avoid in pregnancy; effective contraception during treatment",
        max_dose="Usually a single dose of 200 mcg/kg",
        cost=88.0, price=196.0),

    _med(
        "Calcium Carbonate + Cholecalciferol", "Calcium Carbonate + Cholecalciferol",
        "Mineral and vitamin supplement",
        "Calcium salt with vitamin D3",
        "Calcium and vitamin D deficiency, osteoporosis adjunct, rickets, osteomalacia",
        strength="500mg + 250 IU", form="tablet", brand="Shelcal",
        formula="CaCO3 + C27H44O",
        weight="100.09 + 384.64 g/mol",
        half_life="Not applicable; calcium is regulated by parathyroid hormone and vitamin D",
        moa="Calcium carbonate provides elemental calcium for bone mineralisation, and cholecalciferol (vitamin D3) increases intestinal calcium absorption and is required for that calcium to be used. Neither works adequately without the other.",
        side_effects="Constipation, bloating, nausea, and with excess, hypercalcaemia and kidney stones.",
        contra="Hypercalcaemia, hypercalciuria, severe renal impairment, sarcoidosis.",
        warnings="TAKE WITH FOOD - calcium carbonate needs stomach acid to dissolve, so it is poorly absorbed on an empty stomach, which matters particularly in a patient on a proton pump inhibitor. THE 500 MG ON THE PACK IS SALT WEIGHT AND SUPPLIES ONLY ABOUT 200 MG OF ELEMENTAL CALCIUM - check the elemental content when judging whether a dose is adequate. SEPARATE IT FROM LEVOTHYROXINE, IRON, TETRACYCLINES AND FLUOROQUINOLONES BY AT LEAST 2 HOURS, because it binds them and they are then not absorbed. More is not better: excess causes hypercalcaemia, constipation and renal stones.",
        interactions="Levothyroxine, iron, tetracyclines, fluoroquinolones and bisphosphonates are all bound by calcium and must be separated by at least 2 hours; thiazide diuretics raise calcium by reducing its excretion",
        pregnancy="A - safe and often required; the requirement rises in pregnancy",
        max_dose="Usually 1000-1200 mg of elemental calcium daily, taken in divided doses",
        cost=34.0, price=76.0),

    _med(
        "Rifampicin + Isoniazid + Pyrazinamide + Ethambutol",
        "Rifampicin + Isoniazid + Pyrazinamide + Ethambutol",
        "Antitubercular - fixed dose combination",
        "Combined first-line antitubercular regimen",
        "New pulmonary tuberculosis - intensive phase",
        strength="150mg + 75mg + 400mg + 275mg", form="tablet",
        brand="Akurit-4",
        formula="C43H58N4O12 + C6H7N3O + C5H5N3O + C10H24N2O2",
        weight="822.94 + 137.14 + 123.11 + 204.31 g/mol",
        half_life="Rifampicin 3 hours, isoniazid 1-4 hours, pyrazinamide 9-10 hours, ethambutol 3-4 hours",
        moa="Four drugs acting on different targets, which is the entire point of the combination: rifampicin inhibits DNA-dependent RNA polymerase, isoniazid inhibits mycolic acid synthesis, pyrazinamide is active against the intracellular organisms in an acidic environment, and ethambutol inhibits arabinosyl transferase in the cell wall. Using them together prevents the selection of resistant mutants, which arises readily with any single agent.",
        side_effects="Nausea, vomiting, abdominal pain, rash, hepatitis, peripheral neuropathy from isoniazid, optic neuritis from ethambutol, and hyperuricaemia from pyrazinamide.",
        contra="Severe hepatic impairment, acute liver disease, known hypersensitivity, optic neuritis (ethambutol component).",
        warnings="TAKE AS A SINGLE DAILY DOSE ON AN EMPTY STOMACH, EVERY DAY WITHOUT INTERRUPTION for the full intensive phase, usually two months. THE ORANGE-RED COLOURING OF URINE, SWEAT, TEARS AND SPUTUM IS AN EXPECTED EFFECT OF RIFAMPICIN - explain it in advance or it is mistaken for blood or for a new symptom, and it permanently stains contact lenses. INTERRUPTED TREATMENT IS THE PRINCIPAL CAUSE OF DRUG-RESISTANT TUBERCULOSIS, so adherence is a safety matter and not merely compliance. PYRIDOXINE IS CO-PRESCRIBED TO PREVENT ISONIAZID NEUROPATHY, particularly in diabetes, pregnancy, alcohol dependence, HIV and malnutrition. REPORT JAUNDICE, DARK URINE, PERSISTENT VOMITING OR UNEXPLAINED FEVER IMMEDIATELY. Rifampicin is a potent enzyme inducer with extensive interactions. Blurred vision or reduced colour vision needs urgent review - it may be ethambutol optic neuritis, which is dose-related and usually reversible if the drug is stopped promptly.",
        interactions="RIFAMPICIN INDUCES CYP450: oral contraceptives fail, antiretrovirals and warfarin and corticosteroids and oral hypoglycaemics and phenytoin all have reduced effect. Isoniazid raises phenytoin levels. Antacids reduce isoniazid absorption. Alcohol increases the hepatitis risk.",
        pregnancy="Combination is used in pregnancy; pyridoxine supplementation is essential",
        max_dose="By weight band, as the national programme specifies",
        cost=186.0, price=384.0),
]

# ---------------------------------------------------------------------------
# DOSAGE GUIDANCE for the medicines above.
#
# One guide per (medicine, age band). The seeder keys on that pair, so a second
# entry for the same pair would be dropped and its guidance silently lost;
# test_catalogue.py asserts that no pair is repeated and that every guide names
# a medicine that actually exists.
# ---------------------------------------------------------------------------
BATCH7_GUIDES = [
    {"medicine_name": 'Cefuroxime Axetil 500mg', "age_group": '18+',
     "dosage_amount": 500, "dosage_unit": 'mg',
     "frequency": 'Twice daily', "duration_days": 7,
     "indication": 'Respiratory, urinary or skin infection',
     "special_notes": 'Take with food - absorption of the axetil ester is substantially better with a meal, so an empty-stomach dose wastes much of it. Complete the course. Reduce the dose if the creatinine clearance is below 30. Elderly: Check renal function before prescribing, since it is cleared renally and accumulates otherwise.'},

    {"medicine_name": 'Cefuroxime Axetil 500mg', "age_group": '12-18',
     "dosage_amount": 250, "dosage_unit": 'mg',
     "frequency": 'Twice daily', "duration_days": 7,
     "indication": 'Respiratory or skin infection',
     "special_notes": 'Take with food. 250 mg twice daily is the usual adolescent dose for most indications; higher doses are used for severe infection. Complete the course, and do not stop when the fever settles.'},

    {"medicine_name": 'Cefixime Dry Syrup 100mg/5ml', "age_group": '2-6',
     "dosage_amount": 5, "dosage_unit": 'mg/kg',
     "frequency": 'Twice daily', "duration_days": 7,
     "indication": 'Respiratory, urinary or ear infection',
     "special_notes": 'Measure with the supplied spoon or an oral syringe, never a household teaspoon, which varies from 3 to 7 ml. Shake well before every dose. Reconstituted syrup keeps 7 days at room temperature or 14 days refrigerated; discard the remainder. Children over 50 kg take the adult dose.'},

    {"medicine_name": 'Cefixime Dry Syrup 100mg/5ml', "age_group": '6-12',
     "dosage_amount": 100, "dosage_unit": 'mg',
     "frequency": 'Twice daily', "duration_days": 7,
     "indication": 'Respiratory, urinary or ear infection',
     "special_notes": '5 ml (100 mg) twice daily for a child of average weight in this band; adjust by weight using 8 mg/kg/day in two divided doses. Measure with the supplied spoon. Complete the course.'},

    {"medicine_name": 'Cefadroxil 500mg', "age_group": '18+',
     "dosage_amount": 500, "dosage_unit": 'mg',
     "frequency": 'Twice daily', "duration_days": 10,
     "indication": 'Skin infection, streptococcal pharyngitis, urinary tract infection',
     "special_notes": 'For streptococcal sore throat the course must be 10 days to prevent rheumatic fever - shortening it to 5 days is the common error and loses the protection. Reduce the dose if the creatinine clearance is below 50. Elderly: Check renal function.'},

    {"medicine_name": 'Clarithromycin 250mg', "age_group": '18+',
     "dosage_amount": 250, "dosage_unit": 'mg',
     "frequency": 'Twice daily', "duration_days": 10,
     "indication": 'Respiratory infection; part of Helicobacter pylori eradication',
     "special_notes": 'ASK WHAT ELSE THE PATIENT TAKES BEFORE DISPENSING - it is a strong CYP3A4 inhibitor and raises statin levels (rhabdomyolysis risk), warfarin INR, carbamazepine and colchicine. A metallic taste is expected; mention it in advance so it is not mistaken for a new symptom. Avoid with other QT-prolonging drugs. Elderly: Higher risk from the interactions and from QT prolongation, so the medication review matters more.'},

    {"medicine_name": 'Erythromycin 250mg', "age_group": '18+',
     "dosage_amount": 250, "dosage_unit": 'mg',
     "frequency": 'Four times daily', "duration_days": 7,
     "indication": 'Respiratory infection, acne, penicillin alternative',
     "special_notes": 'Take with food - the gastrointestinal upset is genuinely worse than with other macrolides and is the usual reason a course is abandoned. The same CYP3A4 interactions as clarithromycin apply, including statins and warfarin. Elderly: GI intolerance and interactions are both more likely; consider an alternative macrolide.'},

    {"medicine_name": 'Tetracycline 500mg', "age_group": '18+',
     "dosage_amount": 500, "dosage_unit": 'mg',
     "frequency": 'Four times daily', "duration_days": 7,
     "indication": 'Acne, chlamydial or rickettsial infection',
     "special_notes": 'Take with a full glass of water on an empty stomach and stay upright for 30 minutes - taking it lying down causes oesophageal ulceration. Separate from milk, antacids, iron and calcium by at least 2 hours or it is not absorbed at all. Photosensitivity is marked, so advise sun protection. NOT for children under 8 or in pregnancy - it permanently stains developing teeth.'},

    {"medicine_name": 'Cotrimoxazole 960mg', "age_group": '18+',
     "dosage_amount": 960, "dosage_unit": 'mg',
     "frequency": 'Twice daily', "duration_days": 5,
     "indication": 'Urinary tract infection, respiratory infection',
     "special_notes": 'STOP AND REPORT ANY RASH OR MOUTH ULCER IMMEDIATELY - Stevens-Johnson syndrome is rare but serious and usually begins in the first weeks. It raises potassium, so it is hazardous with an ACE inhibitor, an ARB or a potassium-sparing diuretic. It causes haemolysis in glucose-6-phosphate dehydrogenase deficiency, which is common in India - check before a course. Take with plenty of water. Elderly: Check renal function and review the patient\u2019s other medicines for the potassium interaction.'},

    {"medicine_name": 'Clindamycin 300mg', "age_group": '18+',
     "dosage_amount": 300, "dosage_unit": 'mg',
     "frequency": 'Four times daily', "duration_days": 7,
     "indication": 'Skin and soft tissue infection, dental or anaerobic infection',
     "special_notes": 'Tell the patient that diarrhoea starting up to a month AFTER finishing must be reported and must not be self-treated with an antidiarrhoeal - that is the pattern of Clostridioides difficile colitis. Take with a full glass of water to avoid oesophageal irritation. It does not cover Gram-negative organisms. Elderly: Higher risk of C. difficile colitis and of dehydration from diarrhoea.'},

    {"medicine_name": 'Terbinafine 250mg', "age_group": '18+',
     "dosage_amount": 250, "dosage_unit": 'mg',
     "frequency": 'Once daily', "duration_days": 42,
     "indication": 'Onychomycosis (fingernail); dermatophyte skin infection',
     "special_notes": 'The duration is set by nail growth, not by symptoms: about 6 weeks for fingernails and 12 for toenails, because the drug must reach the growing nail. CHECK LIVER FUNCTION BEFORE A LONG COURSE and tell the patient to report jaundice, dark urine or right upper abdominal pain at once. A taste disturbance is common and can persist for weeks after stopping. Confirm the organism first - it is less effective against candidal nail infection. Elderly: Liver function and the interaction check matter more; review other medicines for CYP2D6 interactions.'},

    {"medicine_name": 'Itraconazole 100mg', "age_group": '18+',
     "dosage_amount": 100, "dosage_unit": 'mg',
     "frequency": 'Twice daily', "duration_days": 7,
     "indication": 'Dermatophytosis; systemic mycosis',
     "special_notes": 'TAKE WITH A FULL MEAL AND SOMETHING ACIDIC - the capsule needs stomach acid to dissolve, so a patient on a proton pump inhibitor or an antacid absorbs very little and the treatment silently fails. It is a potent CYP3A4 inhibitor (statins, warfarin) with a long interaction list, and it can precipitate heart failure, so ask about cardiac history. Elderly: Review all other medicines and the cardiac history before prescribing.'},

    {"medicine_name": 'Griseofulvin 250mg', "age_group": '6-12',
     "dosage_amount": 10, "dosage_unit": 'mg/kg',
     "frequency": 'Once daily', "duration_days": 42,
     "indication": 'Tinea capitis (ringworm of the scalp)',
     "special_notes": 'Take with a fatty meal, which greatly improves absorption. Because it works only through newly formed keratin, the course must continue until the infected hair and skin have grown out - weeks, not days. It remains the most reliable agent for Microsporum scalp ringworm in children. Do not give with alcohol. If a girl of childbearing age is treated, contraception must be discussed - it is teratogenic.'},

    {"medicine_name": 'Ondansetron Mouth Dissolving 4mg', "age_group": '18+',
     "dosage_amount": 4, "dosage_unit": 'mg',
     "frequency": 'Twice daily', "duration_days": 3,
     "indication": 'Nausea and vomiting',
     "special_notes": 'Place the tablet ON THE TONGUE and let it dissolve without water - this formulation exists precisely because a vomiting patient may not keep a tablet down. Constipation is a common consequence of a regular course. Do not exceed 16 mg in 24 hours, and avoid with other QT-prolonging drugs. It works poorly for motion sickness, which is not 5-HT3 mediated. Elderly: Correct any electrolyte abnormality first and review for QT-prolonging co-medication.'},

    {"medicine_name": 'Doxylamine + Pyridoxine', "age_group": '18+',
     "dosage_amount": 1, "dosage_unit": 'tablet',
     "frequency": 'Three times daily', "duration_days": 14,
     "indication": 'Nausea and vomiting of pregnancy',
     "special_notes": 'The first-line treatment for morning sickness and the combination specifically studied for it. DROWSINESS IS MARKED - take the larger dose at bedtime and do not drive until the effect is known; a reduced daytime dose is often better tolerated. If vomiting is so severe that nothing is kept down, that is hyperemesis gravidarum and needs assessment, not a stronger antiemetic.'},

    # Domperidone already exists in batch 5, so no guide is defined here for it
    # either - a second (Domperidone, 18+) row would be dropped by the seeder and
    # its text lost. Batch 5 carries its guidance.

    {"medicine_name": 'Tamsulosin 0.4mg', "age_group": '18+',
     "dosage_amount": 0.4, "dosage_unit": 'mg',
     "frequency": 'Once daily', "duration_days": 30,
     "indication": 'Benign prostatic hyperplasia, lower urinary tract symptoms',
     "special_notes": 'TAKE AFTER THE SAME MEAL EACH DAY and swallow the modified-release capsule whole - never crush or chew it. Dizziness and postural hypotension are worst in the first weeks, so stand up slowly and avoid driving until the effect is known. RETROGRADE EJACULATION is common and men are often not warned - mention it, because it is a real reason men stop treatment. Tell any eye surgeon before cataract surgery: alpha blockers cause intraoperative floppy iris syndrome. It relieves symptoms but does not shrink the prostate. Elderly: Falls from postural hypotension are the main risk - review other antihypertensives.'},

    {"medicine_name": 'Finasteride 5mg', "age_group": '18+',
     "dosage_amount": 5, "dosage_unit": 'mg',
     "frequency": 'Once daily', "duration_days": 30,
     "indication": 'Benign prostatic hyperplasia',
     "special_notes": 'IT TAKES ABOUT SIX MONTHS TO WORK, so do not judge it after a few weeks. It roughly halves the PSA - a PSA on treatment must be doubled before interpretation, and any RISE needs urological assessment rather than being dismissed. Sexual side effects usually reverse on stopping, though occasionally they persist. PREGNANT WOMEN MUST NOT HANDLE CRUSHED TABLETS - it is a teratogen absorbed through the skin. Elderly: Continue it even once symptoms settle, because it prevents progression and the need for surgery.'},

    {"medicine_name": 'Oxybutynin 5mg', "age_group": '18+',
     "dosage_amount": 5, "dosage_unit": 'mg',
     "frequency": 'Twice daily', "duration_days": 30,
     "indication": 'Overactive bladder, urgency and urge incontinence',
     "special_notes": 'DRY MOUTH AFFECTS MOST PATIENTS and is the usual reason for stopping - sugar-free gum, sips of water and oral care help, and it tends to lessen. It carries one of the highest anticholinergic burdens in common use, so ask about glaucoma, constipation and urinary retention before prescribing. It is a Beers Criteria drug in the elderly. The modified-release form is better tolerated for dry mouth.'},

    {"medicine_name": 'Tadalafil 10mg', "age_group": '18+',
     "dosage_amount": 10, "dosage_unit": 'mg',
     "frequency": 'Once daily as required', "duration_days": 30,
     "indication": 'Erectile dysfunction; lower urinary tract symptoms',
     "special_notes": 'ABSOLUTE CONTRAINDICATION WITH NITRATES OR NICORANDIL - the combination causes profound hypotension and has been fatal. Ask specifically about glyceryl trinitrate for angina before every supply, and tell the patient that if they develop chest pain they must tell the attending clinician, because nitrates cannot then be given. The 17.5-hour half-life means the interaction window is about 48 hours. It requires sexual stimulation to work. Priapism, though rare, is a surgical emergency. Elderly: Review cardiac status and all nitrates, including any prescribed since the last supply.'},

    {"medicine_name": 'Carbimazole 10mg', "age_group": '18+',
     "dosage_amount": 10, "dosage_unit": 'mg',
     "frequency": 'Three times daily', "duration_days": 30,
     "indication": 'Hyperthyroidism, Graves disease',
     "special_notes": 'AGRANULOCYTOSIS IS THE SERIOUS RISK: tell every patient to report a SORE THROAT OR FEVER IMMEDIATELY and not to wait for the next appointment - it is reversible if the drug is stopped and a blood count checked at once. Jaundice and dark urine also need urgent review. Take with or after food. The starting dose is usually reduced once thyroid function improves; do not adjust on symptoms alone. Review the dose early if a woman of childbearing age becomes pregnant.'},

    {"medicine_name": 'Levothyroxine 25mcg', "age_group": '18+',
     "dosage_amount": 25, "dosage_unit": 'mcg',
     "frequency": 'Once daily', "duration_days": 30,
     "indication": 'Hypothyroidism - the low starting strength',
     "special_notes": 'THIS IS THE 25 MICROGRAM STRENGTH - the tablets look alike across strengths, so check the pack strength every time and dispense exactly what is prescribed. Take on an empty stomach 30-60 minutes before food at the same time daily. SEPARATE FROM IRON, CALCIUM, ANTACIDS AND PROTON PUMP INHIBITORS BY FOUR HOURS - they bind it, and that is one of the commonest reasons a TSH stays high on an adequate-looking dose. This strength is used to START treatment, especially in the elderly and in ischaemic heart disease where a full replacement dose can precipitate angina. Elderly: Start low and increase slowly, with thyroid function checked 6-8 weeks after each change.'},

    {"medicine_name": 'Calcium Carbonate + Cholecalciferol', "age_group": '18+',
     "dosage_amount": 1, "dosage_unit": 'tablet',
     "frequency": 'Twice daily', "duration_days": 30,
     "indication": 'Calcium and vitamin D supplementation, osteoporosis adjunct',
     "special_notes": 'TAKE WITH FOOD - calcium carbonate needs stomach acid to dissolve, so it is poorly absorbed on an empty stomach, which matters especially on a proton pump inhibitor. THE 500 MG ON THE PACK IS SALT WEIGHT, supplying only about 200 mg of elemental calcium - check the elemental content when judging whether the dose is adequate. Separate from levothyroxine, iron, tetracyclines and fluoroquinolones by 2 hours. Excess is not harmless: it causes hypercalcaemia and, with vitamin D, kidney stones. Elderly: The separation rule from levothyroxine matters especially, since both are commonly prescribed together at this age.'},

    {"medicine_name": 'Propranolol 20mg', "age_group": '18+',
     "dosage_amount": 20, "dosage_unit": 'mg',
     "frequency": 'Twice daily', "duration_days": 30,
     "indication": 'Migraine prophylaxis',
     "special_notes": 'DO NOT USE IN ASTHMA OR COPD - it is the least selective beta blocker and causes bronchospasm. NEVER STOP ABRUPTLY after a long course; withdrawal can precipitate angina or an arrhythmia, so taper over weeks. It masks the warning signs of hypoglycaemia in a diabetic. Vivid dreams and nightmares are common and improve if the dose is moved earlier in the day. Prophylaxis takes several weeks to work and is usually continued for months. Elderly: Start lower and check pulse and blood pressure; falls and bradycardia are the main risks.'},

    {"medicine_name": 'Flunarizine 10mg', "age_group": '18+',
     "dosage_amount": 10, "dosage_unit": 'mg',
     "frequency": 'At bedtime', "duration_days": 30,
     "indication": 'Migraine prophylaxis',
     "special_notes": 'THE HALF-LIFE IS ABOUT 18 DAYS, so it accumulates - keep the dose low, take it at night to use the sedation, and expect any side effect to take weeks to resolve after stopping. DO NOT USE IN ANYONE WITH DEPRESSION or a history of it, and stop it if mood falls. Weight gain is very common; warn the patient. Extrapyramidal effects are why it is used for a limited period rather than indefinitely. Elderly: Avoid where possible - the extrapyramidal and sedative effects, and the long half-life, all make it a poor choice at this age.'},

    {"medicine_name": 'Dexamethasone 0.5mg', "age_group": '18+',
     "dosage_amount": 0.5, "dosage_unit": 'mg',
     "frequency": 'Once daily', "duration_days": 5,
     "indication": 'Inflammatory and allergic conditions; antiemetic adjunct',
     "special_notes": 'NEVER STOP ABRUPTLY AFTER MORE THAN ABOUT THREE WEEKS - it suppresses the adrenal axis and withdrawal can cause an adrenal crisis, so taper. It raises blood glucose markedly, so a diabetic needs closer monitoring. Insomnia and mood change, including a hypomanic reaction, are common. This is not a substitute for hydrocortisone in adrenal insufficiency, where the dose is entirely different. Take in the morning with food to reduce insomnia and gastric upset. Elderly: Watch glucose, blood pressure and bone health, and use the lowest dose for the shortest time.'},

    {"medicine_name": 'Clobetasol Propionate 0.05% Cream', "age_group": '18+',
     "dosage_amount": 1, "dosage_unit": 'application',
     "frequency": 'Twice daily', "duration_days": 14,
     "indication": 'Severe eczema, psoriasis, lichen planus',
     "special_notes": 'THIS IS A SUPERPOTENT STEROID - use SHORT courses, usually no more than 2 weeks, maximum 50 g a week. DO NOT APPLY TO THE FACE, GROIN OR AXILLAE, where absorption is high and atrophy, telangiectasia and permanent striae develop. NEVER USE IT ON A FUNGAL INFECTION - a steroid alone makes ringworm spread and change appearance, which is a frequent error. Do not use on an undiagnosed rash or on a child without specific advice. Continued use thins the skin permanently.'},

    {"medicine_name": 'Ivermectin 12mg', "age_group": '18+',
     "dosage_amount": 12, "dosage_unit": 'mg',
     "frequency": 'Single dose', "duration_days": 1,
     "indication": 'Strongyloidiasis, scabies, lymphatic filariasis',
     "special_notes": 'TAKE ON AN EMPTY STOMACH WITH WATER - food, and a fatty meal in particular, markedly raises absorption and the risk of toxicity. For scabies it is used when a topical agent is unavailable or for crusted scabies alongside topical treatment. In onchocerciasis, warn about a Mazzotti reaction of fever, rash and dizziness as the microfilariae die, which can need hospital care. It is not a COVID-19 preventive - trials did not support that, and using it so wastes a drug with real benefit in parasitic disease.'},

    {"medicine_name": 'Ursodeoxycholic Acid 300mg', "age_group": '18+',
     "dosage_amount": 300, "dosage_unit": 'mg',
     "frequency": 'Twice daily', "duration_days": 30,
     "indication": 'Cholestatic liver disease, primary biliary cholangitis',
     "special_notes": 'A PATIENT WITH DIARRHOEA ON A HIGHER DOSE USUALLY NEEDS THE DOSE REDUCING rather than the drug stopping. Take with food. For gallstone dissolution the stone must be small and radiolucent and it takes months - surgery remains definitive, so this is for a patient who cannot have it. In primary biliary cholangitis the dose is by weight rather than the fixed 300 mg, and it is a long-term treatment. Elderly: Monitor liver function; the dose is by weight, which matters more with a low body weight.'},

    {"medicine_name": 'Methotrexate 2.5mg', "age_group": '18+',
     "dosage_amount": 10, "dosage_unit": 'mg',
     "frequency": 'ONCE WEEKLY - NOT DAILY', "duration_days": 30,
     "indication": 'Rheumatoid arthritis, psoriasis',
     "special_notes": 'ONCE A WEEK, NEVER DAILY, and take it on the same day each week. DAILY DOSING HAS KILLED PATIENTS and it remains the most dangerous routine dispensing error in a pharmacy - write the day of the week on the label and ask the patient to repeat the schedule back to you. Folic acid 5 mg is taken on the other days to reduce toxicity. Baseline and periodic blood counts and liver function are mandatory. Report breathlessness or a new cough at once - pneumonitis is uncommon but serious. It is teratogenic, so pregnancy must be avoided by both partners. NSAIDs and cotrimoxazole raise the risk of toxicity.'},

    {"medicine_name": 'Hydroxychloroquine 200mg', "age_group": '18+',
     "dosage_amount": 200, "dosage_unit": 'mg',
     "frequency": 'Twice daily', "duration_days": 30,
     "indication": 'Rheumatoid arthritis, systemic lupus erythematosus',
     "special_notes": 'AN ANNUAL EYE EXAMINATION IS REQUIRED because of retinal toxicity, which is related to the daily dose per kilogram and to duration beyond five years - the dose is capped at 5 mg/kg of actual body weight per day, not a blanket 400 mg. IT TAKES 6-12 WEEKS TO WORK, so neither patient nor prescriber should judge it early. It is generally the safest systemic antirheumatic in pregnancy and is continued in lupus rather than stopped. It can worsen psoriasis. Take with food or milk to reduce nausea.'},

    {"medicine_name": 'Rifampicin + Isoniazid + Pyrazinamide + Ethambutol', "age_group": '18+',
     "dosage_amount": 4, "dosage_unit": 'tablet',
     "frequency": 'Once daily', "duration_days": 60,
     "indication": 'New pulmonary tuberculosis - intensive phase',
     "special_notes": 'TAKE AS A SINGLE DAILY DOSE ON AN EMPTY STOMACH, EVERY DAY WITHOUT INTERRUPTION for the full intensive phase, usually two months. Interrupted treatment is the main cause of resistance, so adherence is a safety issue and not merely a compliance one. THE ORANGE-RED URINE, SWEAT AND TEARS ARE EXPECTED - explain this or it is mistaken for blood. PYRIDOXINE (vitamin B6) IS CO-PRESCRIBED TO PREVENT ISONIAZID NEUROPATHY, especially in diabetes, pregnancy, alcohol dependence and HIV. RIFAMPICIN IS A POTENT ENZYME INDUCER: it makes oral contraceptives fail and reduces antiretrovirals, warfarin, steroids and oral hypoglycaemics. Report jaundice, dark urine, vomiting or unexplained fever immediately. Elderly: Same regimen, but check liver function and vision (ethambutol) more closely and review every interacting medicine.'},

    {"medicine_name": 'Betahistine 8mg', "age_group": '18+',
     "dosage_amount": 8, "dosage_unit": 'mg',
     "frequency": 'Three times daily', "duration_days": 30,
     "indication": 'Meniere disease, vertigo',
     "special_notes": 'TAKE WITH FOOD to reduce dyspepsia. It is a symptomatic treatment, not a cure, and improvement takes weeks - tell the patient that early, because a week with no benefit is not failure. Meniere disease also needs salt restriction and specialist assessment. It does not work for vertigo of central origin, so persistent or atypical vertigo needs assessment rather than another course. Elderly: Review the cause of vertigo rather than treating symptomatically, since central causes are commoner at this age.'},

    {"medicine_name": 'Amitriptyline 10mg', "age_group": '18+',
     "dosage_amount": 10, "dosage_unit": 'mg',
     "frequency": 'At bedtime', "duration_days": 30,
     "indication": 'Neuropathic pain, migraine prophylaxis',
     "special_notes": 'AT THIS DOSE IT IS A PAIN AND SLEEP DRUG, NOT AN ANTIDEPRESSANT - say so, or a patient given 10 mg for nerve pain and told it is an antidepressant will reasonably object. TAKE IT AT BEDTIME, using the sedation deliberately. The anticholinergic effects (dry mouth, constipation, blurred vision) are the usual reason for stopping and tend to lessen. It must never be combined with an MAO inhibitor. Elderly: Avoid where possible - it is a Beers Criteria drug at this age because of the anticholinergic burden, confusion and falls. If it is used, start at the lowest dose and review.'},
]