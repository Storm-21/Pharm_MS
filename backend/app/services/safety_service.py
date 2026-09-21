"""
Safety engine - the single gate every recommendation passes through.

DESIGN PRINCIPLE
----------------
This module is deliberately pessimistic. When it cannot prove a medicine is
safe for a patient it returns UNKNOWN, and UNKNOWN is treated as unsafe for the
purposes of automatic recommendation. A missed sale costs the pharmacy money;
a missed contraindication harms a patient. The asymmetry is intentional and is
enforced here rather than left to each caller to remember.

SEVERITY GRADING
----------------
Findings are graded on the same three-level scale used by clinical decision
support (contraindicated / serious / moderate), plus an explicit 'unknown'.

    CONTRAINDICATED  do not dispense. No override path exists in this module.
    SERIOUS          do not recommend automatically; flag for the pharmacist.
    MODERATE         safe to recommend, must be shown to the prescriber.
    MINOR            informational only.
    UNKNOWN          a required check could not be completed.

The engine never returns "safe" by default. `assess()` starts from a state of
not-proven-safe and only relaxes when a check actively passes.
"""

from app.models import Medicine, Patient, PatientAllergy

# Severity ordering, most severe first. Used to pick the headline verdict.
SEVERITY_ORDER = {
    'CONTRAINDICATED': 0,
    'SERIOUS': 1,
    'MODERATE': 2,
    'MINOR': 3,
    'UNKNOWN': 4,
}


class Finding:
    """One safety finding about a patient/medicine pair."""

    def __init__(self, kind, severity, message, detail=None, source=None):
        self.kind = kind
        self.severity = severity
        self.message = message
        self.detail = detail
        self.source = source

    def to_dict(self):
        return {
            'kind': self.kind,
            'severity': self.severity,
            'message': self.message,
            'detail': self.detail,
            'source': self.source,
        }


# ---------------------------------------------------------------------------
# Clinical rule tables
# ---------------------------------------------------------------------------

# Drugs that must not be used at all in pregnancy - the classic teratogens and
# abortifacients. Compiled from standard labelling (FDA pregnancy category X /
# current contraindication wording) and WHO guidance. This gates the
# recommendation path entirely.
PREGNANCY_ABSOLUTE = {
    'warfarin': 'anticoagulant with teratogenic risk (fetal warfarin syndrome)',
    'methotrexate': 'antimetabolite - abortifacient and teratogenic',
    'isotretinoin': 'severe teratogen',
    'thalidomide': 'severe teratogen',
    'finasteride': 'antiandrogen - risk to male fetus',
    'misoprostol': 'uterine stimulant - causes abortion',
    'doxycycline': 'tetracycline - dental staining and bone effects after 15 weeks',
    'tetracycline': 'dental staining and bone effects after 15 weeks',
    'ciprofloxacin': 'fluoroquinolone - cartilage and joint risk',
    'levofloxacin': 'fluoroquinolone - cartilage and joint risk',
    'ofloxacin': 'fluoroquinolone - cartilage and joint risk',
    'moxifloxacin': 'fluoroquinolone - cartilage and joint risk',
    'atorvastatin': 'statins withdrawn in pregnancy - cholesterol needed for fetal development',
    'simvastatin': 'statins withdrawn in pregnancy',
    'rosuvastatin': 'statins withdrawn in pregnancy',
    'pravastatin': 'statins withdrawn in pregnancy',
    'ramipril': 'ACE inhibitor - fetal renal damage',
    'lisinopril': 'ACE inhibitor - fetal renal damage',
    'enalapril': 'ACE inhibitor - fetal renal damage',
    'perindopril': 'ACE inhibitor - fetal renal damage',
    'captopril': 'ACE inhibitor - fetal renal damage',
    'telmisartan': 'ARB - fetal renal damage',
    'losartan': 'ARB - fetal renal damage',
    'valsartan': 'ARB - fetal renal damage',
    'ibandronic': 'bisphosphonate - retained in bone, fetal harm',
    'alendronate': 'bisphosphonate - fetal harm',
}

# Drugs that should be *intensified* rather than stopped in pregnancy - the
# omission here is as dangerous as a contraindication.
PREGNANCY_REQUIRES_REVIEW = {
    'metformin': 'usually continued in gestational diabetes - needs prescriber review',
    'insulin': 'insulin requirements change substantially during pregnancy',
    'metoprolol': 'may be continued for hypertension - specialised review required',
    'levothyroxine': 'dose often needs increasing in pregnancy',
    'salbutamol': 'asthma control must not lapse in pregnancy',
    'warfarin': None,  # handled by the absolute table above
}

# Beers Criteria (AGS 2023) - medicines to avoid in adults aged 65 and over.
# These are not automatically unsafe, but they carry a clear risk/benefit
# penalty in this age group and should not be surfaced as a first choice.
BEERS_AVOID_65 = {
    'chlorpheniramine': 'anticholinergic - confusion, dry mouth, urinary retention',
    'diphenhydramine': 'anticholinergic - falls and confusion risk',
    'hydroxyzine': 'anticholinergic burden in older adults',
    'promethazine': 'anticholinergic and sedating',
    'diclofenac': 'NSAID - GI bleeding and renal risk without gastroprotection',
    'ibuprofen': 'NSAID - GI bleeding and renal risk without gastroprotection',
    'indomethacin': 'NSAID - highest CNS and GI risk of the class',
    'naproxen': 'NSAID - GI bleeding risk',
    'ketorolac': 'NSAID - avoid for more than 5 days at any age',
    'diazepam': 'long-acting benzodiazepine - falls and fractures',
    'lorazepam': 'benzodiazepine - falls and cognitive impairment',
    'alprazolam': 'benzodiazepine - falls and cognitive impairment',
    'zolpidem': 'sedative - falls and delirium; avoid for insomnia in older adults',
    'amitriptyline': 'highly anticholinergic tricyclic',
    'nitrofurantoin': 'renal function declines with age; ineffective and risky below eGFR 30',
    'glyburide': 'long-acting sulfonylurea - prolonged hypoglycaemia',
    'glibenclamide': 'long-acting sulfonylurea - prolonged hypoglycaemia',
}

# Dose ceilings. The safety engine refuses to emit a dose above these, however
# the calculation was arrived at. Values are the standard maximum adult daily
# dose from the label; paracetamol's 4 g limit is the most commonly exceeded
# and the most dangerous when it is.
MAX_DAILY_DOSE_MG = {
    'paracetamol': 4000,
    'acetaminophen': 4000,
    'ibuprofen': 2400,
    'aspirin': 4000,
    'diclofenac': 150,
    'naproxen': 1000,
    'amoxicillin': 3000,
    'azithromycin': 500,
    'ciprofloxacin': 1500,
    'metronidazole': 2000,
    'doxycycline': 200,
    'metformin': 2550,
    'glimepiride': 8,
    'sitagliptin': 100,
    'amlodipine': 10,
    'lisinopril': 40,
    'telmisartan': 80,
    'metoprolol': 400,
    'atorvastatin': 80,
    'rosuvastatin': 40,
    'omeprazole': 40,
    'pantoprazole': 80,
    'cetirizine': 20,
    'levocetirizine': 5,
    'montelukast': 10,
    'warfarin': 10,
    'clopidogrel': 75,
    'levothyroxine': 0.2,
    'diazepam': 30,
    'prednisolone': 60,
}

# Drugs needing a renal dose reduction. The value is the eGFR below which the
# medicine must not be recommended without a pharmacist's review.
RENAL_CAUTION_EGFR = {
    'metformin': 30,        # lactic acidosis risk; stop below 30
    'nitrofurantoin': 30,   # ineffective and toxic below 30
    'ciprofloxacin': 30,
    'levofloxacin': 30,
    'ofloxacin': 30,
    'fluconazole': 50,
    'acyclovir': 25,
    'aciclovir': 25,
    'atenol': 35,
    'bisoprolol': 30,
    'metoprolol': 25,
    'sitagliptin': 30,
    'glimepiride': 30,
    'enalapril': 30,
    'lisinopril': 30,
    'telmisartan': 30,
    'rosuvastatin': 30,
    'colchicine': 30,
    'ranitidine': 50,
}

# Hepatotoxic drugs. Combined with a recorded hepatic impairment flag these
# become contraindications rather than cautions.
HEPATOTOXIC = {
    'paracetamol': 'dose-limited in liver disease; toxic metabolite accumulates',
    'acetaminophen': 'dose-limited in liver disease',
    'isoniazid': 'hepatitis risk',
    'methotrexate': 'hepatic fibrosis with long-term use',
    'ketoconazole': 'hepatotoxicity',
    'valproate': 'hepatotoxicity, particularly in young children',
    'diclofenac': 'transaminase elevation',
    'atorvastatin': 'transaminase elevation',
    'simvastatin': 'transaminase elevation',
    'rosuvastatin': 'transaminase elevation',
}

# Substrings in a patient's recorded condition text that indicate a problem.
# Matching is deliberately loose (case-insensitive substring) because the field
# is free text and a missed match is worse than an extra warning.
CONDITION_CONFLICTS = {
    'asthma': [
        (('propranolol', 'atenol', 'bisoprolol', 'metoprolol', 'carvedilol',
          'timol'), 'beta-blocker can precipitate bronchospasm in asthma'),
        (('aspirin', 'ibuprofen', 'diclofenac', 'naproxen', 'ketorolac'),
         'NSAID use is associated with asthma exacerbation in sensitive patients'),
    ],
    'peptic ulcer': [
        (('ibuprofen', 'diclofenac', 'naproxen', 'aspirin', 'ketorolac',
          'indomethacin', 'aceclofenac', 'etoricoxib'),
         'NSAID increases the risk of GI bleeding and perforation'),
    ],
    'gastric ulcer': [
        (('ibuprofen', 'diclofenac', 'naproxen', 'aspirin', 'ketorolac',
          'etoricoxib'), 'NSAID increases the risk of GI bleeding'),
    ],
    'heart failure': [
        (('ibuprofen', 'diclofenac', 'naproxen', 'pioglitazone'),
         'causes fluid retention and can decompensate heart failure'),
        (('verapamil',), 'negative inotropic effect - avoid in systolic dysfunction'),
    ],
    'kidney': [
        (('ibuprofen', 'diclofenac', 'naproxen', 'ketorolac', 'gentamicin'),
         'nephrotoxic - further reduces renal function'),
    ],
    'renal': [
        (('ibuprofen', 'diclofenac', 'naproxen', 'ketorolac', 'gentamicin'),
         'nephrotoxic - further reduces renal function'),
    ],
    'diabetes': [
        (('prednisolone', 'prednisone', 'dexamethasone', 'hydrocortisone'),
         'corticosteroid raises blood glucose and destabilises control'),
    ],
    'epilepsy': [
        (('ciprofloxacin', 'levofloxacin', 'tramadol'),
         'lowers the seizure threshold'),
    ],
    'glaucoma': [
        (('chlorpheniramine', 'diphenhydramine', 'promethazine', 'amitriptyline'),
         'anticholinergic - can raise intraocular pressure'),
    ],
    'prostate': [
        (('chlorpheniramine', 'diphenhydramine', 'promethazine'),
         'anticholinergic - risk of urinary retention'),
    ],
}

# Interaction pairs that are clinically serious, keyed as a sorted tuple so the
# lookup is order-independent. This supplements the free-text interaction field
# with the specific combinations that matter most, because substring matching
# against label prose is not reliable enough to gate a recommendation on.
SERIOUS_INTERACTIONS = [
    (('warfarin', 'aspirin'), 'bleeding risk - additive haemostatic impairment'),
    (('warfarin', 'ibuprofen'), 'bleeding risk - NSAID plus anticoagulant'),
    (('warfarin', 'diclofenac'), 'bleeding risk - NSAID plus anticoagulant'),
    (('warfarin', 'ciprofloxacin'), 'INR rise - antibiotic potentiation'),
    (('warfarin', 'metronidazole'), 'INR rise - potent CYP2C9 inhibition'),
    (('warfarin', 'fluconazole'), 'INR rise - potent CYP2C9 inhibition'),
    (('warfarin', 'erythromycin'), 'INR rise'),
    (('warfarin', 'clarithromycin'), 'INR rise'),
    (('warfarin', 'clopidogrel'), 'dual antithrombotic - major bleeding risk'),
    (('clopidogrel', 'omeprazole'), 'PPI reduces clopidogrel activation'),
    (('methotrexate', 'ibuprofen'), 'NSAID reduces methotrexate clearance - toxicity'),
    (('methotrexate', 'aspirin'), 'reduced methotrexate clearance - toxicity'),
    (('tramadol', 'sertraline'), 'serotonin syndrome risk'),
    (('tramadol', 'fluoxetine'), 'serotonin syndrome risk'),
    (('metformin', 'prednisolone'), 'corticosteroid antagonises glycaemic control'),
    (('simvastatin', 'clarithromycin'), 'rhabdomyolysis risk - CYP3A4 inhibition'),
    (('atorvastatin', 'clarithromycin'), 'myopathy and rhabdomyolysis risk'),
    (('simvastatin', 'erythromycin'), 'myopathy risk'),
    (('atorvastatin', 'erythromycin'), 'myopathy risk'),
    (('lisinopril', 'spironolactone'), 'hyperkalaemia risk'),
    (('lisinopril', 'potassium'), 'hyperkalaemia risk'),
    (('lisinopril', 'ibuprofen'), 'NSAID reduces antihypertensive effect and raises renal risk'),
    (('telmisartan', 'spironolactone'), 'hyperkalaemia risk'),
    (('ciprofloxacin', 'tizanidine'), 'potent CYP1A2 inhibition - profound hypotension'),
    (('fluconazole', 'simvastatin'), 'myopathy risk'),
    (('digoxin', 'amiodarone'), 'digoxin toxicity - reduced clearance'),
    (('digoxin', 'verapamil'), 'digoxin toxicity risk'),
    (('metoclopramide', 'levodopa'), 'antagonises dopaminergic therapy'),
    (('allopurinol', 'azathioprine'), 'severe myelosuppression - reduce azathioprine dose'),
]

# Route/form compatibility: a dose written as 'mg' for an inhaler is meaningless
# and printing it would be a dispensing hazard.
UNIT_FOR_FORM = {
    'tablet': 'mg', 'capsule': 'mg', 'syrup': 'ml', 'suspension': 'ml',
    'injection': 'mg', 'inhaler': 'puff', 'cream': 'g', 'ointment': 'g',
    'gel': 'g', 'drops': 'drop', 'sachet': 'sachet', 'suppository': 'unit',
    'patch': 'patch',
}


class SafetyEngine:
    """Assess a patient/medicine pair. The only entry point callers should use."""

    @staticmethod
    def assess(patient_id, medicine_id, context=None):
        """
        Full safety assessment.

        Returns a dict with:
            verdict        SAFE | CAUTION | UNSAFE | BLOCKED | UNKNOWN
            safe           bool - True only for SAFE and (opt-in) CAUTION
            recommendable  bool - True only for SAFE. The recommender uses this.
            findings       list of Finding dicts
            checks_run     list of check names that completed
            checks_failed  list of check names that could not complete
            unknown_reason human-readable explanation when checks failed

        `safe` and `recommendable` are separate on purpose: a CAUTION may be
        dispensed with pharmacist awareness, but must never be auto-recommended.
        """
        context = context or {}
        findings = []
        checks_run = []
        checks_failed = []

        patient = Patient.query.get(patient_id)
        medicine = Medicine.query.get(medicine_id)

        # --- Identity gate ---------------------------------------------------
        # Without both records there is nothing to assess, and returning 'safe'
        # here would be exactly the misjudgement this module exists to prevent.
        if not patient or not medicine:
            return {
                'verdict': 'UNKNOWN',
                'safe': False,
                'recommendable': False,
                'findings': [Finding(
                    'MISSING_DATA', 'UNKNOWN',
                    'Patient or medicine record not found - cannot assess safety.'
                ).to_dict()],
                'checks_run': [],
                'checks_failed': ['identity'],
                'unknown_reason': 'Patient or medicine record missing.',
            }

        # --- 1. Allergy ------------------------------------------------------
        try:
            allergy = SafetyEngine._check_allergy(patient, medicine)
            checks_run.append('allergy')
            if allergy:
                findings.append(allergy)
        except Exception as exc:
            checks_failed.append('allergy')
            findings.append(Finding(
                'ALLERGY', 'UNKNOWN',
                'Allergy check could not be completed.', detail=str(exc)
            ))

        # --- 2. Chronic condition conflicts ----------------------------------
        try:
            condition_findings = SafetyEngine._check_conditions(patient, medicine)
            checks_run.append('conditions')
            findings.extend(condition_findings)
        except Exception as exc:
            checks_failed.append('conditions')
            findings.append(Finding(
                'CONDITION', 'UNKNOWN',
                'Condition check could not be completed.', detail=str(exc)
            ))

        # --- 3. Current medications (interactions) ---------------------------
        try:
            interaction_findings = SafetyEngine._check_interactions(patient, medicine)
            checks_run.append('interactions')
            findings.extend(interaction_findings)
        except Exception as exc:
            checks_failed.append('interactions')
            findings.append(Finding(
                'INTERACTION', 'UNKNOWN',
                'Interaction check could not be completed.', detail=str(exc)
            ))

        # --- 4. Age-specific rules -------------------------------------------
        try:
            age_findings = SafetyEngine._check_age(patient, medicine)
            checks_run.append('age')
            findings.extend(age_findings)
        except Exception as exc:
            checks_failed.append('age')
            findings.append(Finding(
                'AGE', 'UNKNOWN', 'Age check could not be completed.', detail=str(exc)
            ))

        # --- 5. Pregnancy / lactation ----------------------------------------
        try:
            preg_findings = SafetyEngine._check_pregnancy(patient, medicine)
            checks_run.append('pregnancy')
            findings.extend(preg_findings)
        except Exception as exc:
            checks_failed.append('pregnancy')
            findings.append(Finding(
                'PREGNANCY', 'UNKNOWN',
                'Pregnancy check could not be completed.', detail=str(exc)
            ))

        # --- 6. Renal function ----------------------------------------------
        try:
            renal_findings = SafetyEngine._check_renal(patient, medicine)
            checks_run.append('renal')
            findings.extend(renal_findings)
        except Exception as exc:
            checks_failed.append('renal')
            findings.append(Finding(
                'RENAL', 'UNKNOWN', 'Renal check could not be completed.', detail=str(exc)
            ))

        # --- 7. Hepatic function --------------------------------------------
        try:
            hepatic_findings = SafetyEngine._check_hepatic(patient, medicine)
            checks_run.append('hepatic')
            findings.extend(hepatic_findings)
        except Exception as exc:
            checks_failed.append('hepatic')
            findings.append(Finding(
                'HEPATIC', 'UNKNOWN', 'Hepatic check could not be completed.', detail=str(exc)
            ))

        # --- 8. Form/route sanity -------------------------------------------
        try:
            form_findings = SafetyEngine._check_form(medicine, context)
            checks_run.append('form')
            findings.extend(form_findings)
        except Exception as exc:
            checks_failed.append('form')
            findings.append(Finding(
                'FORM', 'UNKNOWN', 'Form check could not be completed.', detail=str(exc)
            ))

        return SafetyEngine._verdict(findings, checks_run, checks_failed)

    # -- individual checks ---------------------------------------------------

    @staticmethod
    def _check_allergy(patient, medicine):
        allergies = PatientAllergy.query.filter_by(patient_id=patient.id).all()
        if not allergies:
            return None
        # Reuse the grouped cross-reactivity logic rather than reimplementing it,
        # so the two paths can never disagree.
        from app.services.dosage_service import InteractionChecker
        result = InteractionChecker.check_patient_allergies(patient.id, medicine.id)
        if not result or not result.get('has_allergy'):
            return None
        # A recorded anaphylaxis is never merely a caution.
        severity_text = (result.get('severity') or '').lower()
        graded = 'CONTRAINDICATED' if severity_text in ('severe', 'anaphylaxis', 'anaphylactic') \
            else 'SERIOUS'
        return Finding(
            'ALLERGY', graded,
            result.get('warning') or 'Allergy on record for this patient.',
            detail='%s - %s (%s)' % (
                result.get('allergen'), result.get('reaction'),
                result.get('match_type')),
            source='Patient allergy record',
        )

    @staticmethod
    def _check_conditions(patient, medicine):
        findings = []
        diseases = (patient.chronic_diseases or '').lower()
        if not diseases:
            return findings
        haystack = ' '.join(filter(None, [
            medicine.name, medicine.generic_name, medicine.brand_name,
            medicine.salt_composition,
        ])).lower()
        for condition, rules in CONDITION_CONFLICTS.items():
            if condition not in diseases:
                continue
            for drugs, reason in rules:
                if any(d in haystack for d in drugs):
                    findings.append(Finding(
                        'CONDITION', 'SERIOUS',
                        'Patient has recorded %s: %s' % (condition, reason),
                        detail=medicine.name,
                        source='Comorbidity rule',
                    ))
        return findings

    @staticmethod
    def _check_interactions(patient, medicine):
        findings = []
        current = (patient.current_medications or '').strip().lower()
        if not current:
            return findings

        new_terms = SafetyEngine._drug_terms(medicine)

        # (a) Curated serious-pair table - the reliable, specific check.
        for pair, reason in SERIOUS_INTERACTIONS:
            first, second = pair
            if first in new_terms:
                other = second
            elif second in new_terms:
                other = first
            else:
                continue
            if other in current:
                findings.append(Finding(
                    'INTERACTION', 'SERIOUS',
                    'Serious interaction with %s already being taken: %s'
                    % (other, reason),
                    detail='%s + %s' % (medicine.name, other),
                    source='Curated interaction table',
                ))

        # (b) Label prose, as a catch-all for pairs not in the table.
        label_text = (medicine.drug_interactions or '').lower()
        if label_text:
            for med in [m.strip() for m in current.split(',') if m.strip()]:
                # Only report a prose match when the medicine is named in the
                # interaction field AND the current medicine is also named, to
                # avoid flagging on a generic word like 'alcohol'.
                if len(med) > 3 and med in label_text:
                    findings.append(Finding(
                        'INTERACTION', 'MODERATE',
                        'Possible interaction with %s (listed on this medicine\'s '
                        'interaction data).' % med,
                        detail=medicine.drug_interactions,
                        source='Medicine interaction data',
                    ))
        return findings

    @staticmethod
    def _check_age(patient, medicine):
        findings = []
        haystack = ' '.join(filter(None, [
            medicine.name, medicine.generic_name, medicine.brand_name,
        ])).lower()

        if patient.age >= 65:
            for drug, reason in BEERS_AVOID_65.items():
                if drug in haystack:
                    findings.append(Finding(
                        'AGE', 'MODERATE',
                        'Avoid in patients 65 and over (Beers Criteria): %s' % reason,
                        detail=medicine.name,
                        source='AGS Beers Criteria 2023',
                    ))
                    break

        # Paediatric exclusions that are absolute, not dose-dependent.
        if patient.age < 18:
            paediatric_bar = {
                'aspirin': (16, 'Reye\'s syndrome risk in children and teenagers'),
                'tetracycline': (8, 'permanent dental staining'),
                'doxycycline': (8, 'dental staining under 8 years'),
                'ciprofloxacin': (18, 'fluoroquinolone - cartilage damage in growing children'),
                'levofloxacin': (18, 'fluoroquinolone - cartilage damage'),
                'codeine': (12, 'CYP2D6 ultra-rapid metaboliser risk - respiratory depression'),
            }
            for drug, (min_age, reason) in paediatric_bar.items():
                if drug in haystack and patient.age < min_age:
                    findings.append(Finding(
                        'AGE', 'CONTRAINDICATED',
                        'Not to be given under %d years: %s' % (min_age, reason),
                        detail=medicine.name,
                        source='Paediatric age restriction',
                    ))
                    break
        return findings

    @staticmethod
    def _check_pregnancy(patient, medicine):
        findings = []
        # Pregnancy rules apply only to a patient recorded as pregnant. The
        # flag is explicit rather than inferred from sex: inferring it would be
        # both medically wrong (a woman who is not pregnant is not a
        # contraindication case) and intrusive.
        if not patient.is_pregnant:
            return findings

        haystack = ' '.join(filter(None, [
            medicine.name, medicine.generic_name, medicine.brand_name,
            medicine.salt_composition,
        ])).lower()

        for drug, reason in PREGNANCY_ABSOLUTE.items():
            if drug in haystack:
                trimester = patient.pregnancy_trimester
                findings.append(Finding(
                    'PREGNANCY', 'CONTRAINDICATED',
                    'Contraindicated in pregnancy: %s' % reason,
                    detail='%s%s' % (
                        medicine.name,
                        ' (trimester %s)' % trimester if trimester else ''),
                    source='Pregnancy contraindication table',
                ))
                break

        if patient.is_breastfeeding:
            # A small set of clear lactation concerns. Kept short because
            # over-flagging here would block ordinary safe prescribing.
            lactation_caution = {
                'codeine': 'neonatal respiratory depression via breast milk',
                'tramadol': 'neonatal sedation and respiratory depression',
                'methotrexate': 'excreted in milk - immunosuppression',
                'warfarin': 'monitor infant - small milk transfer',
            }
            for drug, reason in lactation_caution.items():
                if drug in haystack:
                    findings.append(Finding(
                        'LACTATION', 'SERIOUS',
                        'Caution while breastfeeding: %s' % reason,
                        detail=medicine.name,
                        source='Lactation caution table',
                    ))
                    break

            # Also surface whatever the label says, if it says anything.
            if 'lactation' in (medicine.warnings or '').lower():
                findings.append(Finding(
                    'LACTATION', 'MODERATE',
                    'Manufacturer labelling contains lactation advice - read before '
                    'recommending.',
                    detail=medicine.warnings,
                    source='Medicine labelling',
                ))
        return findings

    @staticmethod
    def _check_renal(patient, medicine):
        findings = []
        haystack = ' '.join(filter(None, [
            medicine.name, medicine.generic_name, medicine.brand_name,
        ])).lower()

        drug_key = None
        for drug in RENAL_CAUTION_EGFR:
            if drug in haystack:
                drug_key = drug
                break
        if not drug_key:
            return findings

        threshold = RENAL_CAUTION_EGFR[drug_key]
        egfr = patient.egfr

        if egfr is None:
            # The drug needs renal review and we cannot do it. This is the
            # UNKNOWN case that must not silently pass.
            if patient.renal_impairment:
                findings.append(Finding(
                    'RENAL', 'SERIOUS',
                    'Patient is flagged with renal impairment and %s needs a dose '
                    'review for renal function, but no serum creatinine is on file.'
                    % medicine.name,
                    detail='Record serum creatinine to enable eGFR calculation.',
                    source='Renal dosing rule',
                ))
            else:
                findings.append(Finding(
                    'RENAL', 'UNKNOWN',
                    '%s requires renal dose adjustment, but no serum creatinine is '
                    'recorded so eGFR cannot be calculated.' % medicine.name,
                    detail='Record serum creatinine, or confirm normal renal function.',
                    source='Renal dosing rule',
                ))
            return findings

        if egfr < threshold:
            findings.append(Finding(
                'RENAL', 'SERIOUS',
                'eGFR %s mL/min is below the safe threshold (%s) for %s - dose '
                'reduction or an alternative is required.'
                % (egfr, threshold, medicine.name),
                detail='CKD stage: %s' % (patient.ckd_stage or 'unknown'),
                source='Renal dosing rule',
            ))
        elif egfr < threshold + 15:
            findings.append(Finding(
                'RENAL', 'MODERATE',
                'eGFR %s mL/min - %s may need a dose reduction as renal function '
                'declines further.' % (egfr, medicine.name),
                detail='CKD stage: %s' % (patient.ckd_stage or 'unknown'),
                source='Renal dosing rule',
            ))
        return findings

    @staticmethod
    def _check_hepatic(patient, medicine):
        findings = []
        if not patient.hepatic_impairment:
            return findings
        haystack = ' '.join(filter(None, [
            medicine.name, medicine.generic_name, medicine.brand_name,
        ])).lower()
        for drug, reason in HEPATOTOXIC.items():
            if drug in haystack:
                findings.append(Finding(
                    'HEPATIC', 'SERIOUS',
                    'Patient has hepatic impairment: %s' % reason,
                    detail=medicine.name,
                    source='Hepatic caution table',
                ))
                break
        return findings

    @staticmethod
    def _check_form(medicine, context):
        findings = []
        dose_unit = (context.get('dose_unit') or '').strip().lower()
        form = (medicine.form or '').strip().lower()
        if not dose_unit or not form:
            return findings
        expected = None
        for key, unit in UNIT_FOR_FORM.items():
            if key in form:
                expected = unit
                break
        if expected and dose_unit != expected:
            # An inhaler dosed in 'mg' is not dispensed as written, so this is
            # a transcription error rather than a clinical warning.
            findings.append(Finding(
                'FORM', 'SERIOUS',
                'Dose unit "%s" does not match the %s form (expected "%s"). '
                'Check the prescription before dispensing.'
                % (dose_unit, medicine.form, expected),
                detail=medicine.name,
                source='Form/unit consistency',
            ))
        return findings

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def _drug_terms(medicine):
        """Lower-cased identifier set for a medicine, used for interaction lookup.

        The generic name is the clinically meaningful key - brand names vary
        by market, and two brands of the same molecule must match the same
        rules. The leading word is also indexed so that a combination product
        (Amoxicillin + Clavulanic Acid, Co-amoxiclav) still matches rules
        written against its first active ingredient.
        """
        terms = set()
        for value in (medicine.generic_name, medicine.name,
                      medicine.salt_composition):
            if not value:
                continue
            lowered = str(value).lower()
            terms.add(lowered)
            # Replace every non-alphanumeric character with a space, then take
            # the first token. Written with chr() so no quote or space literal
            # has to survive an editor round-trip.
            cleaned = ''.join(
                ch if ch.isalnum() else chr(32) for ch in lowered
            )
            head = cleaned.split()
            if head:
                terms.add(head[0])
        return terms

    @staticmethod
    def _verdict(findings, checks_run, checks_failed):
        severities = [f.severity for f in findings]

        if 'CONTRAINDICATED' in severities:
            verdict = 'BLOCKED'
        elif 'SERIOUS' in severities:
            verdict = 'UNSAFE'
        elif 'UNKNOWN' in severities or checks_failed:
            verdict = 'UNKNOWN'
        elif 'MODERATE' in severities:
            verdict = 'CAUTION'
        else:
            verdict = 'SAFE'

        # Only SAFE is auto-recommendable. CAUTION requires a human to look at
        # the specific finding; UNKNOWN requires the missing data to be filled.
        recommendable = (verdict == 'SAFE')

        headline = None
        if findings:
            worst = sorted(findings, key=lambda f: SEVERITY_ORDER.get(f.severity, 9))[0]
            headline = worst.message

        # The explanation for an UNKNOWN verdict must name the actual cause.
        # "A required check could not complete" is useless at a counter - the
        # pharmacist needs to know whether to fetch a creatinine result, confirm
        # a pregnancy status, or simply fill in something that was left blank,
        # so the specific findings are quoted rather than a generic phrase.
        unknown_reason = None
        if checks_failed:
            unknown_reason = ('These checks could not run: %s. Treat the medicine '
                              'as unverified until they complete.'
                              % ', '.join(checks_failed))
        elif 'UNKNOWN' in severities:
            unknown_findings = [f for f in findings if f.severity == 'UNKNOWN']
            unknown_reason = ' '.join(
                f.message for f in unknown_findings) or \
                'A required check could not be completed.'

        return {
            'verdict': verdict,
            'safe': verdict in ('SAFE', 'CAUTION'),
            'recommendable': recommendable,
            'findings': [f.to_dict() for f in findings],
            'checks_run': checks_run,
            'checks_failed': checks_failed,
            'headline': headline,
            'unknown_reason': unknown_reason,
            # A concrete list of what to supply so the verdict can be resolved,
            # rather than leaving the user to infer it from the findings.
            'missing_data': SafetyEngine._missing_data(findings),
        }

    @staticmethod
    def _missing_data(findings):
        """What would have to be recorded to resolve an UNKNOWN verdict."""
        wanted = []
        for finding in findings:
            if finding.kind == 'RENAL' and finding.severity == 'UNKNOWN':
                wanted.append('Record serum creatinine so eGFR can be calculated.')
            elif finding.kind == 'PREGNANCY' and finding.severity == 'UNKNOWN':
                wanted.append('Record pregnancy status.')
            elif finding.kind == 'ALLERGY' and finding.severity == 'UNKNOWN':
                wanted.append('Review the allergy record.')
            elif finding.kind == 'MISSING_DATA':
                wanted.append('Select a valid patient and medicine.')
        # Preserve order, drop duplicates.
        seen = set()
        unique = []
        for item in wanted:
            if item not in seen:
                seen.add(item)
                unique.append(item)
        return unique

    @staticmethod
    def check_dose_ceiling(medicine, daily_dose_mg):
        """
        Return a Finding when a calculated daily dose exceeds the ceiling.

        Called by the dosage calculator, so a ceiling breach cannot be printed
        even if the underlying dose arithmetic is wrong.
        """
        haystack = ' '.join(filter(None, [
            medicine.generic_name, medicine.name,
        ])).lower()
        for drug, ceiling in MAX_DAILY_DOSE_MG.items():
            if drug in haystack:
                if daily_dose_mg and daily_dose_mg > ceiling:
                    return Finding(
                        'DOSE_CEILING', 'SERIOUS',
                        'Calculated %s mg/day exceeds the %s mg/day maximum for %s. '
                        'Dose capped; verify with the prescriber.'
                        % (round(daily_dose_mg, 1), ceiling, medicine.name),
                        detail='Maximum daily dose ceiling applied.',
                        source='Maximum daily dose table',
                    )
                return None
        # No ceiling on file: not an error, but the caller should say so.
        return None

    @staticmethod
    def max_daily_dose(medicine):
        """Ceiling in mg for this medicine, or None when not tabulated."""
        haystack = ' '.join(filter(None, [
            medicine.generic_name, medicine.name,
        ])).lower()
        for drug, ceiling in MAX_DAILY_DOSE_MG.items():
            if drug in haystack:
                return ceiling
        return None
