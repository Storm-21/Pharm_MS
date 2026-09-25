"""
Dosage guidance for catalogue entries that had none - batch 6.

WHY THIS FILE EXISTS
--------------------
The fifteen batches that built the medicine list grew the *catalogue*; they did
not always grow the *dosing*. `test_catalogue.py` asserts that every medicine has
at least one age-banded guide, because a medicine you can look up but cannot dose
is only half-present - the dosage calculator reports "no guide" and the
prescriber is back to a paper index.

Nineteen entries from batches 1-4 were in exactly that state. This file supplies
their guidance. It adds no medicines: the catalogue count is unchanged, which is
the point - this closes a coverage gap rather than padding a number.

HOW THE FIGURES WERE CHOSEN
---------------------------
Every dose below is the standard published adult (or paediatric) dose from the
same class of source the rest of the catalogue uses - the manufacturer's own
labelling, the Indian Pharmacopoeia, and the standard reference formularies. None
was interpolated, scaled or invented to fill a row. Where a drug is genuinely
adult-only (oral contraceptives, alendronate, tizanidine-type agents) only an
18+ band is given, because publishing a paediatric band that does not exist
clinically would be worse than publishing none.

Two conventions carried from batch 5:
  * doses that must be titrated say so, with the starting dose and the target;
  * the elderly note is included only where ageing genuinely changes the dose or
    the risk, not as boilerplate on every row.

The clinical disclaimer in DEVELOPER_NOTES.md applies unchanged: this is a
reference for a qualified prescriber, not a substitute for one.
"""

# Imported by seeder.py alongside the other batches. Naming matches the pattern
# used by batch3/4/5 so the loader needs no special case.
BATCH6_GUIDES = [

    # =================================================================== #
    # CARDIOVASCULAR - the ARB, the antiarrhythmic and the nitrate.
    # =================================================================== #
    {"medicine_name": 'Valsartan 80mg', "age_group": '18+',
     "dosage_amount": 80, "dosage_unit": 'mg',
     "frequency": 'Once daily', "duration_days": 30,
     "indication": 'Hypertension, heart failure, post-myocardial infarction',
     "special_notes": 'Hypertension: 80-160 mg once daily, with or without food. Heart failure: start at 40 mg twice daily and titrate to the highest tolerated dose - do not start at the antihypertensive dose in heart failure. Post-MI: start as early as 12 hours after the event, usually 20 mg twice daily, then titrate. Check potassium and creatinine 1-2 weeks after any dose change and after starting a potassium-sparing diuretic. Do not use with an ACE inhibitor without specialist supervision. Contraindicated in pregnancy - stop immediately if pregnancy is suspected. Elderly: Start at 40 mg once daily; monitor potassium and creatinine more closely and check for postural hypotension.'},

    {"medicine_name": 'Amiodarone 200mg', "age_group": '18+',
     "dosage_amount": 200, "dosage_unit": 'mg',
     "frequency": 'Once daily', "duration_days": 30,
     "indication": 'Ventricular tachycardia, atrial fibrillation, refractory arrhythmias',
     "special_notes": 'A LOADING REGIMEN IS REQUIRED - this maintenance dose is not a starting dose. Loading is typically 200 mg three times daily for one week, then 200 mg twice daily for a second week, then 200 mg once daily. Amiodarone has a very long half-life (weeks), so the loading phase is what reaches therapeutic levels and the maintenance dose is deliberately low. Baseline and periodic checks: thyroid function (it causes both hypo- and hyperthyroidism), liver function, chest X-ray or lung function (pulmonary fibrosis is dose- and duration-related), and an ECG for QT prolongation and bradycardia. It potentiates warfarin markedly - reduce the warfarin dose and monitor INR closely when amiodarone is started. Photosensitivity and blue-grey skin discolouration are expected with long-term use; advise sun protection. Elderly: No specific starting-dose reduction, but the monitoring above matters more - thyroid and pulmonary toxicity rise steeply with age and cumulative dose.'},

    {"medicine_name": 'Isosorbide Mononitrate 20mg', "age_group": '18+',
     "dosage_amount": 20, "dosage_unit": 'mg',
     "frequency": 'Twice daily', "duration_days": 30,
     "indication": 'Angina prophylaxis, heart failure adjunct',
     "special_notes": 'This is prophylaxis, NOT a treatment for an acute attack - sublingual nitroglycerin is used for that. The twice-daily doses must be at least 7 hours apart and the second dose is usually taken in the late afternoon/early evening so that a nitrate-free interval overnight preserves the response; taken at even 12-hour intervals the effect is lost to tolerance within days. Expect headache on starting - it usually settles in a week and does not mean the dose is wrong. Do not use with a PDE5 inhibitor (sildenafil, tadalafil) - severe hypotension. Warn about postural hypotension, especially with alcohol. Elderly: Start at the lower end and rise slowly; postural hypotension and falls are the main risk.'},

    # =================================================================== #
    # NEUROLOGY - epilepsy, migraine and pain.
    # =================================================================== #
    {"medicine_name": 'Carbamazepine 200mg', "age_group": '18+',
     "dosage_amount": 200, "dosage_unit": 'mg',
     "frequency": 'Twice daily', "duration_days": 30,
     "indication": 'Focal seizures, trigeminal neuralgia, generalised tonic-clonic seizures',
     "special_notes": 'Start at 100 mg once or twice daily and increase slowly - typically by 100-200 mg every one to two weeks - to a usual maintenance of 400-1200 mg daily in divided doses. Never start at the full adult dose. Carbamazepine induces its own metabolism, so levels fall over the first weeks and the dose often needs raising again; measuring the plasma level is worthwhile. Check sodium before starting and periodically - hyponatraemia (SIADH) is common and easily missed. Fatal Stevens-Johnson syndrome is associated with HLA-B*1502, which is prevalent in some Indian populations - be alert to any rash and stop immediately if one appears. Many interactions, including with oral contraceptives (they fail) and warfarin. Elderly: Start at 100 mg once daily; sedation, ataxia and hyponatraemia are all more likely.'},

    {"medicine_name": 'Carbamazepine 200mg', "age_group": '6-12',
     "dosage_amount": 5, "dosage_unit": 'mg/kg',
     "frequency": 'Twice daily', "duration_days": 30,
     "indication": 'Focal seizures, generalised tonic-clonic seizures',
     "special_notes": 'Children are dosed by weight, typically starting at 5 mg/kg/day in two divided doses and increased slowly. Check the sodium and the blood count during titration. The HLA-B*1502 rash warning above applies to children too, and children are also more prone to the cognitive and behavioural effects. Measure the plasma level if seizures are not controlled, before assuming the drug has failed.'},

    {"medicine_name": 'Sumatriptan 50mg', "age_group": '18+',
     "dosage_amount": 50, "dosage_unit": 'mg',
     "frequency": 'When required', "duration_days": 30,
     "indication": 'Acute migraine with or without aura; cluster headache',
     "special_notes": 'Take at the FIRST sign of the headache, not once it is established - it works far better early. A second dose may be taken after at least 2 hours if the headache recurs, to a maximum of 300 mg in 24 hours. It does not prevent migraine and it does not work for tension headache; taking it on more than about 10 days a month causes medication-overuse headache, which is a common trap. Contraindicated in ischaemic heart disease, uncontrolled hypertension, previous stroke and peripheral vascular disease - it is a vasoconstrictor, so ask about cardiac history before the first supply. Do not use within 24 hours of an ergot or another triptan. Elderly: Migraine is uncommon in the elderly and new-onset headache at this age needs assessment rather than a triptan.'},

    {"medicine_name": 'Morphine Sulphate 10mg', "age_group": '18+',
     "dosage_amount": 10, "dosage_unit": 'mg',
     "frequency": 'Every 4 hours as required', "duration_days": 7,
     "indication": 'Severe pain, cancer pain, myocardial infarction pain, palliative care',
     "special_notes": 'CONTROLLED DRUG: a Schedule H1 register entry is required and the quantity dispensed must be recorded. Start low and titrate to effect - in an opioid-naive adult, 5-10 mg every 4 hours is usually the starting range, and half that in the elderly. The sustained-release form must NEVER be crushed or broken; crushing releases the whole day\'s dose at once and has killed patients. Prescribe a laxative from the outset with every regular opioid - constipation does not develop tolerance. Nausea typically settles in a few days; sedation and respiratory depression do not, and are the signs to watch. Prescribe naloxone availability for the patient on a high dose. Elderly: Start at half the adult dose and extend the interval - renal clearance falls with age and the active metabolite accumulates.'},

    # =================================================================== #
    # RESPIRATORY
    # =================================================================== #
    {"medicine_name": 'Ipratropium Inhaler', "age_group": '18+',
     "dosage_amount": 40, "dosage_unit": 'mcg',
     "frequency": 'Four times daily', "duration_days": 30,
     "indication": 'COPD maintenance, acute asthma adjunct',
     "special_notes": 'Usually 2 puffs (40 mcg) four times daily, up to a maximum of 12 puffs in 24 hours. RINSE THE MOUTH after each dose - this is the main practical point and omitting it invites oral candidiasis. It is a maintenance bronchodilator and not a reliever: a short-acting beta-2 agonist (salbutamol) is what the patient reaches for in an acute attack. Avoid contact with the eyes - the aerosol can precipitate acute angle-closure glaucoma and worsen urinary retention. It is less effective than a beta-2 agonist in asthma and is used there as an adjunct, not alone. Elderly: Watch for urinary retention in prostatic disease and for glaucoma; the systemic anticholinergic burden is real even though absorption is low.'},

    {"medicine_name": 'Ipratropium Inhaler', "age_group": '6-12',
     "dosage_amount": 20, "dosage_unit": 'mcg',
     "frequency": 'Three times daily', "duration_days": 14,
     "indication": 'Asthma adjunct',
     "special_notes": 'In children, 1 puff (20 mcg) three to four times daily, usually alongside a beta-2 agonist rather than instead of one. Use a spacer with a face mask in younger children - without one most of the dose lands in the mouth. Rinse the mouth afterwards. Nebulised ipratropium is used in acute severe asthma in hospital, but that is a different presentation from this metered-dose inhaler.'},

    # =================================================================== #
    # GASTROINTESTINAL - the antiemetic and the antispasmodic.
    # =================================================================== #
    {"medicine_name": 'Metoclopramide 10mg', "age_group": '18+',
     "dosage_amount": 10, "dosage_unit": 'mg',
     "frequency": 'Three times daily', "duration_days": 5,
     "indication": 'Nausea, gastroparesis, gastro-oesophageal reflux, migraine-associated nausea',
     "special_notes": 'Take 30 minutes before meals. MAXIMUM 5 DAYS at this dose - this is a hard limit, not a guideline. Prolonged use causes tardive dyskinesia, which is often irreversible, and the risk rises steeply with duration and with age. Keep the maximum to 30 mg in 24 hours. Contraindicated in Parkinson\'s disease (it blocks dopamine and worsens it), in bowel obstruction and in phaeochromocytoma. Do not use with another dopamine antagonist or with an antipsychotic. It is a useful antiemetic in migraine because it also aids gastric emptying, which is why oral analgesics often fail in migraine. Elderly: Use for no more than 5 days and at the lowest dose; the extrapyramidal risk is substantially higher, and it is a Beers Criteria drug in this age group. Consider an alternative antiemetic first.'},

    {"medicine_name": 'Dicyclomine 10mg', "age_group": '18+',
     "dosage_amount": 10, "dosage_unit": 'mg',
     "frequency": 'Three times daily', "duration_days": 14,
     "indication": 'Irritable bowel syndrome, smooth muscle spasm',
     "special_notes": 'Take before meals. It relieves the spasm of irritable bowel syndrome but does not treat the underlying condition, so it is symptomatic and should be reviewed if there is no benefit in a few weeks. The anticholinergic effects are the whole profile: dry mouth, blurred vision, constipation, urinary hesitancy and confusion. Avoid in narrow-angle glaucoma, myasthenia gravis, prostatic hypertrophy with retention and paralytic ileus, and use with caution in significant reflux. The paediatric and infant use for colic has been withdrawn in many countries because of serious respiratory and neurological reactions in infants - do not recommend it for an infant. Elderly: Anticholinergic burden is high at this age; avoid where possible, especially in dementia.'},

    # =================================================================== #
    # MUSCULOSKELETAL AND HORMONAL.
    # =================================================================== #
    {"medicine_name": 'Alendronate 70mg', "age_group": '18+',
     "dosage_amount": 70, "dosage_unit": 'mg',
     "frequency": 'Once weekly', "duration_days": 28,
     "indication": 'Osteoporosis, Paget disease of bone',
     "special_notes": 'The administration is the safety profile, so it must be explained, not just dispensed: take on the SAME DAY each week, on waking, on an EMPTY stomach, with a full glass of PLAIN WATER only (not tea, coffee, juice or mineral water), then stay fully upright - sitting or standing - and take nothing by mouth for at least 30 minutes. Lying down or taking it with anything else causes severe oesophagitis and ulceration. A missed dose is taken the next morning, not doubled. Ensure adequate calcium and vitamin D. Tell the patient to report jaw pain or a non-healing extraction site - osteonecrosis of the jaw is rare but serious. Consider a drug holiday after 3-5 years. Dose adjustment if creatinine clearance is below 35. Elderly: The standing rule is what is most often got wrong in practice, because of mobility problems - check that the patient can actually stay upright for 30 minutes before prescribing it, and give a different agent if not.'},

    {"medicine_name": 'Ethinylestradiol + Levonorgestrel', "age_group": '18+',
     "dosage_amount": 1, "dosage_unit": 'tablet',
     "frequency": 'Once daily', "duration_days": 28,
     "indication": 'Contraception, menstrual cycle regulation, endometriosis',
     "special_notes": 'One tablet daily at the same time each day, for 21 days, then a 7-day tablet-free interval (or 7 inactive tablets in a 28-day pack). Starting: day 1-5 of the cycle for immediate cover, or any day with additional precautions for the first 7 days. If a pill is missed by more than 12 hours (or 24 for a low-dose progestogen-only product), take it as soon as remembered and use condoms for 7 days. Efficacy is reduced by enzyme inducers - rifampicin, carbamazepine, phenytoin, St John\'s wort and some HIV medicines - so additional contraception is needed during and for 28 days after that course. Contraindicated: migraine WITH aura at any age, a history of venous thromboembolism, smokers over 35, breast cancer, severe hypertension, and within 6 weeks of childbirth if breastfeeding - the venous thromboembolism risk is the one that kills young women and it is not rare. Check blood pressure before the first supply and annually. Does not protect against sexually transmitted infection.'},

    {"medicine_name": 'Medroxyprogesterone 10mg', "age_group": '18+',
     "dosage_amount": 10, "dosage_unit": 'mg',
     "frequency": 'Once daily', "duration_days": 10,
     "indication": 'Secondary amenorrhoea, dysfunctional uterine bleeding, hormone replacement therapy',
     "special_notes": 'For a withdrawal bleed in secondary amenorrhoea: 10 mg daily for 10 days, with bleeding usually 2-7 days after the last tablet. For dysfunctional uterine bleeding the regimen depends on whether the aim is to stop bleeding or to regulate cycles, and it differs; confirm the intended regimen rather than assuming 10 days. It is a progestogen, so the main caution is thromboembolism, though less than with an oestrogen. Report abnormal bleeding that continues after treatment - postmenopausal bleeding needs investigation, not another course of a progestogen. Contraindicated in pregnancy and in undiagnosed vaginal bleeding. Elderly: Use with caution; prolonged use in the elderly is not established.'},

    # =================================================================== #
    # ANTI-INFECTIVES.
    # =================================================================== #
    {"medicine_name": 'Levofloxacin 500mg', "age_group": '18+',
     "dosage_amount": 500, "dosage_unit": 'mg',
     "frequency": 'Once daily', "duration_days": 7,
     "indication": 'Community-acquired pneumonia, urinary tract infection, pyelonephritis',
     "special_notes": '500 mg once daily, with the duration by indication - 7 days for community-acquired pneumonia is typical, 5 days for uncomplicated urinary tract infection, and longer for pyelonephritis. The prolonged half-life is why once daily works, and it is also why renal impairment needs an interval extension rather than a smaller dose: at a creatinine clearance below 50 the same 500 mg is usually given every 48 hours, and below 20 every 48 hours at a reduced dose. TENDON RUPTURE (Achilles, and sometimes the shoulder) is the signature risk, it occurs with this class as with others, it is much more common over 60 and on a corticosteroid, and it can happen after the course has finished - stop the drug and report any tendon pain. Also: QT prolongation (avoid with other QT-prolonging drugs), peripheral neuropathy, CNS reactions including seizures, and aortic aneurysm/dissection with prolonged use. Separate from antacids, iron, calcium, zinc and sucralfate by at least 2 hours - they bind it and it is not absorbed. Reserve it: fluoroquinolones are not first-line for uncomplicated infection where another agent will do. Elderly: The tendon, QT and renal considerations all converge at this age - check the creatinine clearance and prefer another class where one is available.'},

    {"medicine_name": 'Ampicillin + Cloxacillin', "age_group": '18+',
     "dosage_amount": 500, "dosage_unit": 'mg',
     "frequency": 'Four times daily', "duration_days": 7,
     "indication": 'Respiratory infection, skin and soft tissue infection, urinary tract infection',
     "special_notes": 'Usually one capsule (250 + 250 mg) four to six times daily, or 500 mg of the combination four times daily; take on an EMPTY stomach, an hour before or two hours after food, because food reduces absorption. The two components cover different organisms - ampicillin for the Gram-negatives and streptococci, cloxacillin for penicillinase-producing staphylococci - which is the whole reason for the combination in skin and soft tissue infection. Ask about penicillin allergy before every supply, and remember the cross-reactivity in beta-lactams. Causes diarrhoea; if it is severe with fever and bloody stool, suspect Clostridioides difficile and stop the drug rather than treating through it. Beware with infectious mononucleosis - a florid maculopapular rash is near-universal and is not a true allergy. Elderly: The four-times-daily interval is demanding; check adherence, and reduce the dose in significant renal impairment (the cloxacillin component does not need it, the ampicillin does).'},

    {"medicine_name": 'Ampicillin + Cloxacillin', "age_group": '6-12',
     "dosage_amount": 250, "dosage_unit": 'mg',
     "frequency": 'Four times daily', "duration_days": 7,
     "indication": 'Respiratory infection, skin and soft tissue infection',
     "special_notes": 'Children are dosed by weight and age and the capsule is often unsuitable - a suspension is used in practice. Given by weight, roughly 25-50 mg/kg/day of the combination in four divided doses. Take on an empty stomach. The same penicillin-allergy question applies, and children with infectious mononucleosis must not receive ampicillin. If the child cannot swallow a capsule, do not open it onto food - ask for the oral suspension instead.'},

    {"medicine_name": 'Amikacin 500mg Injection', "age_group": '18+',
     "dosage_amount": 15, "dosage_unit": 'mg/kg',
     "frequency": 'Once daily', "duration_days": 7,
     "indication": 'Serious Gram-negative infection, hospital-acquired infection, septicaemia',
     "special_notes": 'Dosed by weight: 15 mg/kg ONCE DAILY is now the standard regimen for most indications (a single large dose is as effective and less nephrotoxic than divided doses). Monitor in practice, not just on paper - PEAK and TROUGH levels, serum creatinine every few days, and an audiogram for prolonged courses. The two toxicities are kidney injury and irreversible deafness, and both are cumulative and dose-related, so the course should be the shortest that will work. Ensure the patient is well hydrated. It is not absorbed orally and there is no oral form - the injection is the only route. It is often given with a beta-lactam, and must not be mixed in the same syringe or infusion line with a penicillin (they inactivate each other). Elderly: Renal function declines with age even when the creatinine looks normal, so doses and intervals get calculated from the measured creatinine clearance, and monitoring is more frequent. Avoid combination with other nephrotoxins such as a loop diuretic or amphotericin B if at all possible.'},

    {"medicine_name": 'Praziquantel 600mg', "age_group": '18+',
     "dosage_amount": 40, "dosage_unit": 'mg/kg',
     "frequency": 'Once daily', "duration_days": 1,
     "indication": 'Schistosomiasis, tapeworm infestation, cysticercosis',
     "special_notes": 'The dose is by weight and the DURATION DIFFERS BY INFECTION, so do not assume one day: 40 mg/kg as a single dose for schistosomiasis, 40 mg/kg as a SINGLE day for most tapeworms, but 50 mg/kg daily in three divided doses for 14 days for neurocysticercosis. Take with food and water, and swallow the tablet whole unless a smaller dose is needed. The most important practical point is the timing in schistosomiasis: for a patient who has been exposed to Schistosoma mansoni, treatment should be deferred until the parasites have matured (typically 4-6 weeks after exposure), because the drug acts on the adult worm and a course given too early misses them. For neurocysticercosis it must be given with a corticosteroid and an anticonvulsant under specialist direction, because the inflammatory reaction to dying cysts can cause seizures and raised intracranial pressure. Do not drive on the day of treatment. Avoid in the first trimester of pregnancy and use with caution while breastfeeding - breastfeed after the dose, not before. Elderly: Generally well tolerated; no specific reduction, but check the renal function.'},

    {"medicine_name": 'Timol 0.5% Eye Drops', "age_group": '18+',
     "dosage_amount": 1, "dosage_unit": 'drop',
     "frequency": 'Twice daily', "duration_days": 30,
     "indication": 'Open-angle glaucoma, ocular hypertension',
     "special_notes": 'One drop twice daily, morning and evening. Press on the inner corner of the eye for a minute or two after instilling (punctal occlusion), and close the eye briefly - this is what keeps the drug out of the circulation and it is the single most useful instruction for this medicine. It is SYSTEMICALLY ABSORBED even as an eye drop: it can cause bronchospasm in asthma and COPD, bradycardia, heart block and hypotension, and it can mask the warning signs of hypoglycaemia in a diabetic and of hyperthyroidism. Ask about asthma and heart block before the first supply, because it is contraindicated in both. It is a beta-blocker, so do not use it with an oral beta-blocker without checking. Do not stop it abruptly - that can precipitate a rebound rise in eye pressure. The bottle must not be shared between patients. Elderly: Respiratory and cardiac comorbidity are common at this age, so the asthma and heart-block questions matter more, and falls from changes in blood pressure should be watched for.'},

    # =================================================================== #
    # ANTIMALARIAL AND IMMUNISATION.
    # =================================================================== #
    {"medicine_name": 'Chloroquine 250mg', "age_group": '18+',
     "dosage_amount": 600, "dosage_unit": 'mg',
     "frequency": 'Once daily', "duration_days": 1,
     "indication": 'Plasmodium vivax malaria (blood stage), extraintestinal amoebiasis, rheumatoid arthritis',
     "special_notes": 'The dose is expressed in BASE, and the 250 mg tablet is 150 mg of base - this is the classic source of a tenfold error, so check which figure is on the prescription before dispensing. For P. vivax malaria in an adult: 600 mg base immediately, then 300 mg base at 6, 24 and 48 hours (a total of 1500 mg base), and it must be followed by PRIMAQUINE because chloroquine does not touch the liver-stage hypnozoites that cause relapse. Chloroquine alone cures the attack and not the infection. It is no longer used for P. falciparum in most of the world, including India, because of resistance. Retinal toxicity is the serious long-term risk with cumulative exposure - it is a real consideration for the rheumatological use, where an annual ophthalmic examination is expected, and much less so for a single malaria course. May worsen psoriasis and porphyria. Elderly: Check renal function; in significant impairment the dose accumulates.'},

    {"medicine_name": 'Chloroquine 250mg', "age_group": '6-12',
     "dosage_amount": 10, "dosage_unit": 'mg/kg',
     "frequency": 'Once daily', "duration_days": 1,
     "indication": 'Plasmodium vivax malaria (blood stage)',
     "special_notes": 'Children are dosed by weight in base: 10 mg base/kg immediately, then 5 mg base/kg at 6, 24 and 48 hours. The tablet is 150 mg base, so the arithmetic must be done on the base figure, not on the 250 mg on the pack. The paediatric dose is close to the toxic one, so measure the weight rather than estimating, and never dispense a loose quantity without a written instruction. Stick to the malaria regimen - the high-dose rheumatological regimen is not to be used in children outside specialist care. Follow with primaquine to prevent relapse, at a paediatric dose and after checking for glucose-6-phosphate dehydrogenase deficiency. Seek advice or admit a child who is drowsy, fitting or unable to drink - that is severe malaria and oral treatment is not appropriate.'},

    {"medicine_name": 'Tetanus Toxoid Injection', "age_group": '18+',
     "dosage_amount": 0.5, "dosage_unit": 'ml',
     "frequency": 'Single dose', "duration_days": 1,
     "indication": 'Tetanus prophylaxis, wound management, antenatal immunisation',
     "special_notes": '0.5 ml by intramuscular injection into the deltoid (or the anterolateral thigh in an infant), NOT into the buttock. It is a TOXOID, so it is a vaccine and not a treatment: it does not treat an established wound infection and it does not neutralise toxin already present, so a dirty, deep or devitalised wound needs wound care and, in the unimmunised, human tetanus immunoglobulin as well - the toxoid alone is not sufficient. In an immunised patient, a booster is given if the wound is dirty and more than 5 years have elapsed since the last, or for a clean wound more than 10 years. Store at 2-8C; a vaccine that has been frozen is discarded. Antenatal schedule in India is usually two doses four weeks apart, the second at least four weeks before delivery, with a booster if the previous dose was more than three years earlier. Common reactions: local soreness, mild fever, and they are not reasons to withhold future doses. Elderly: Offer the booster - immunity wanes and older adults are the group most likely to have neither protection nor a documented history.'},

    {"medicine_name": 'Tetanus Toxoid Injection', "age_group": '6-12',
     "dosage_amount": 0.5, "dosage_unit": 'ml',
     "frequency": 'Single dose', "duration_days": 1,
     "indication": 'Tetanus prophylaxis, routine immunisation',
     "special_notes": 'The same 0.5 ml intramuscular dose as the adult - this is one of the few vaccines that is not scaled down for a child. Give in the deltoid in a school-age child, or the anterolateral thigh in an infant. The wound-care point from the adult entry applies unchanged in children, and a child who is incompletely immunised with a tetanus-prone wound needs immunoglobulin, not just a toxoid dose. Anxiety-related fainting is common in this age group - have the child seated or lying during the injection and keep them under observation for 15 minutes afterwards.'},

]