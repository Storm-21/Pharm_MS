from datetime import datetime, timedelta
from app.models import Medicine, Patient, PatientAllergy, DosageGuide

# Adult reference doses, and the mg/kg figure for paediatric use.
#
# Both are needed. A calculator that knows only the adult dose cannot dose a
# child properly except by an age-based formula, and those ignore weight
# entirely. Where a published per-kilogram figure exists it is always preferred,
# because it is the actual basis of paediatric prescribing.
#
#   adult_mg   standard adult dose for a single dose
#   mg_per_kg  paediatric dose per kilogram per single dose (None where the
#              medicine is not used in children at all, e.g. statins)
#   max_mg     cap applied after the weight calculation, because mg/kg
#              extrapolates into unsafe territory as body weight rises
ADULT_REFERENCE_DOSE = {
    'paracetamol': {'adult_mg': 1000, 'mg_per_kg': 15, 'max_mg': 1000},
    'acetaminophen': {'adult_mg': 1000, 'mg_per_kg': 15, 'max_mg': 1000},
    'ibuprofen': {'adult_mg': 400, 'mg_per_kg': 10, 'max_mg': 400},
    'aspirin': {'adult_mg': 325, 'mg_per_kg': 10, 'max_mg': 325},
    'amoxicillin': {'adult_mg': 500, 'mg_per_kg': 15, 'max_mg': 500},
    'amoxycillin': {'adult_mg': 500, 'mg_per_kg': 15, 'max_mg': 500},
    'metformin': {'adult_mg': 500, 'mg_per_kg': None, 'max_mg': 500},
    'omeprazole': {'adult_mg': 20, 'mg_per_kg': 1, 'max_mg': 20},
    'lisinopril': {'adult_mg': 10, 'mg_per_kg': None, 'max_mg': 10},
    'atorvastatin': {'adult_mg': 20, 'mg_per_kg': None, 'max_mg': 20},
    'cetirizine': {'adult_mg': 10, 'mg_per_kg': 0.25, 'max_mg': 10},
    'azithromycin': {'adult_mg': 500, 'mg_per_kg': 10, 'max_mg': 500},
    'ciprofloxacin': {'adult_mg': 500, 'mg_per_kg': 15, 'max_mg': 750},
    'diclofenac': {'adult_mg': 50, 'mg_per_kg': 1, 'max_mg': 50},
    'pantoprazole': {'adult_mg': 40, 'mg_per_kg': 1, 'max_mg': 40},
    'montelukast': {'adult_mg': 10, 'mg_per_kg': None, 'max_mg': 10},
    'amlodipine': {'adult_mg': 5, 'mg_per_kg': None, 'max_mg': 10},
    'prednisolone': {'adult_mg': 40, 'mg_per_kg': 2, 'max_mg': 40},
    'sertraline': {'adult_mg': 50, 'mg_per_kg': None, 'max_mg': 200},
    'gabapentin': {'adult_mg': 300, 'mg_per_kg': None, 'max_mg': 3600},
    'cefixime': {'adult_mg': 200, 'mg_per_kg': 8, 'max_mg': 400},
    'metronidazole': {'adult_mg': 400, 'mg_per_kg': 7.5, 'max_mg': 500},
    'doxycycline': {'adult_mg': 100, 'mg_per_kg': 2.2, 'max_mg': 100},
    'nitrofurantoin': {'adult_mg': 100, 'mg_per_kg': None, 'max_mg': 100},
    'albendazole': {'adult_mg': 400, 'mg_per_kg': 15, 'max_mg': 400},
    'ondansetron': {'adult_mg': 4, 'mg_per_kg': 0.15, 'max_mg': 8},
    'fluconazole': {'adult_mg': 150, 'mg_per_kg': 6, 'max_mg': 400},
    'acyclovir': {'adult_mg': 400, 'mg_per_kg': 20, 'max_mg': 800},
    'aciclovir': {'adult_mg': 400, 'mg_per_kg': 20, 'max_mg': 800},
    'chlorpheniramine': {'adult_mg': 4, 'mg_per_kg': 0.09, 'max_mg': 4},
    'levocetirizine': {'adult_mg': 5, 'mg_per_kg': None, 'max_mg': 5},
    'salbutamol': {'adult_mg': 4, 'mg_per_kg': 0.15, 'max_mg': 8},
    'allopurinol': {'adult_mg': 100, 'mg_per_kg': None, 'max_mg': 900},
    'colchicine': {'adult_mg': 0.5, 'mg_per_kg': None, 'max_mg': 1.0},
    'tramadol': {'adult_mg': 50, 'mg_per_kg': None, 'max_mg': 100},
    'warfarin': {'adult_mg': 5, 'mg_per_kg': None, 'max_mg': 10},
    'levothyroxine': {'adult_mg': 0.05, 'mg_per_kg': None, 'max_mg': 0.2},
    'digoxin': {'adult_mg': 0.125, 'mg_per_kg': None, 'max_mg': 0.25},
}


def _fmt_mg(value):
    # Render a milligram figure without a trailing .0, so 500.0 shows as 500.
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number == int(number):
        return str(int(number))
    return str(number)


class DosageCalculator:
    """Service for calculating dosage based on patient conditions, age, and weight"""
    
    @staticmethod
    def calculate_dosage(medicine_id, patient_id, condition=None):
        """
        Calculate a dose for a patient.

        Order of preference:

          1. Weight-based (mg/kg) - when the medicine has a published per-kg
             figure and the patient's weight is on file. This is the actual
             basis of paediatric prescribing and is more precise than any age
             band: a 24 kg and a 34 kg eight-year-old are not the same patient,
             but an age table doses them identically.
          2. The stored age-band DosageGuide, when there is no weight to work
             from.
          3. The reference-dose fallback in calculate_default_dosage().

        Whichever route is used is named in the result, and the age-band dose
        is returned alongside a weight-based one so the two can be compared.
        """
        patient = Patient.query.get(patient_id)
        medicine = Medicine.query.get(medicine_id)

        if not patient or not medicine:
            return None

        # Get dosage guide for patient's age group
        age_group = DosageCalculator.get_age_group(patient.age)
        dosage_guide = DosageGuide.query.filter_by(
            medicine_id=medicine_id,
            age_group=age_group
        ).first()

        guide_snapshot = None
        if dosage_guide:
            guide_snapshot = {
                'age_group': dosage_guide.age_group,
                'dosage_amount': dosage_guide.dosage_amount,
                'dosage_unit': dosage_guide.dosage_unit,
                'frequency': dosage_guide.frequency,
                'duration_days': dosage_guide.duration_days,
            }

        # --- Weight-based takes precedence over the age band -----------------
        reference = ADULT_REFERENCE_DOSE.get(
            (medicine.generic_name or '').strip().lower())
        has_mg_per_kg = bool(reference and reference.get('mg_per_kg'))

        if patient.weight_kg and has_mg_per_kg and patient.age < 18:
            weight_based = DosageCalculator.calculate_default_dosage(
                medicine, patient, condition)
            if weight_based:
                weight_based['dose_source'] = 'weight-based'
                if guide_snapshot:
                    # The age band is coarser by construction, so it is kept as
                    # a visible comparison rather than a disagreement to hide.
                    weight_based['age_band_guide'] = guide_snapshot
                    if (guide_snapshot['dosage_amount']
                            and abs(guide_snapshot['dosage_amount']
                                    - weight_based['dosage_amount'])
                            > 0.05 * guide_snapshot['dosage_amount']):
                        weight_based['special_notes'] = (
                            (weight_based.get('special_notes') or '')
                            + ' The stored age-band guide for %s is %s %s; the '
                              'weight-based figure above is more precise for '
                              'this patient.'
                            % (guide_snapshot['age_group'],
                               _fmt_mg(guide_snapshot['dosage_amount']),
                               guide_snapshot['dosage_unit'])
                        ).strip()
                return weight_based

        if not dosage_guide:
            # If no specific guide and no weight to use, fall back to the
            # reference-dose estimate.
            result = DosageCalculator.calculate_default_dosage(
                medicine, patient, condition)
            if result:
                result['dose_source'] = 'reference-estimate'
            return result

        result = {
            'medicine_id': medicine_id,
            'medicine_name': medicine.name,
            'patient_id': patient_id,
            'patient_age': patient.age,
            'patient_weight_kg': patient.weight_kg,
            'patient_height_cm': patient.height_cm,
            'patient_bsa_m2': patient.bsa_m2,
            'dosage_amount': dosage_guide.dosage_amount,
            'dosage_unit': dosage_guide.dosage_unit,
            'frequency': dosage_guide.frequency,
            'duration_days': dosage_guide.duration_days,
            'special_notes': dosage_guide.special_notes,
            'indication': dosage_guide.indication,
            'calculation_method': 'Stored age-band guide (%s years)'
                                  % dosage_guide.age_group,
            'confidence': 'documented',
            'is_weight_based': False,
            'dose_source': 'age-band-guide',
            'source': 'Dosage guide stored for the %s age band'
                      % dosage_guide.age_group,
        }
        if not patient.weight_kg and has_mg_per_kg:
            # The guide is being used only because no weight is on file. Said
            # plainly, so nobody mistakes this for a weight-based dose.
            result['special_notes'] = (
                (result['special_notes'] or '')
                + ' No weight is recorded for this patient, so the age-band dose '
                  'was used. Recording the weight enables a weight-based dose.'
            ).strip()
        return result
    
    @staticmethod
    def get_age_group(age):
        """Determine age group based on patient age"""
        if age < 2:
            return "0-2"
        elif age < 6:
            return "2-6"
        elif age < 12:
            return "6-12"
        elif age < 18:
            return "12-18"
        else:
            return "18+"
    
    @staticmethod
    def calculate_default_dosage(medicine, patient, condition):
        """
        Estimate a dose when no stored DosageGuide row exists.

        Method, in order of preference:

          1. Weight-based (mg/kg) where a published paediatric figure exists and
             the patient's weight is on file. This is the standard basis of
             paediatric prescribing.
          2. Young's rule (child dose = adult dose x age / (age + 12)), which is
             a published formula but ignores weight, so it is labelled weaker.
          3. The adult reference dose for an adult patient.

        Whatever the route, the result is capped at the medicine's maximum
        single dose and checked against its maximum daily dose. The method and
        a confidence level are reported, so the prescriber can see how the
        number was reached instead of being handed an unexplained figure.
        """
        key = (medicine.generic_name or '').strip().lower()
        reference = ADULT_REFERENCE_DOSE.get(key)
        known_drug = reference is not None
        if reference is None:
            # No published figure on file. A 500 mg baseline for an unknown
            # drug is a guess, and the confidence flag says so plainly rather
            # than dressing it up as a calculation.
            reference = {'adult_mg': 500, 'mg_per_kg': None, 'max_mg': 500}

        base_dose = reference['adult_mg']
        max_single = reference.get('max_mg') or base_dose
        mg_per_kg = reference.get('mg_per_kg')

        caveats = []

        # Frequency first, so the daily ceiling can be applied inside the
        # weight-based calculation rather than patched on afterwards.
        if patient.age < 1:
            frequency = 'Every 6-8 hours as needed'
            doses_per_day = 4
        elif patient.age < 12:
            frequency = '3 times a day'
            doses_per_day = 3
        else:
            frequency = '2-3 times a day'
            doses_per_day = 3

        # Daily ceiling from the safety engine, used by the weight-based route
        # so a mg/kg figure cannot produce an over-limit daily total.
        daily_ceiling = None
        try:
            from app.services.safety_service import SafetyEngine
            daily_ceiling = SafetyEngine.max_daily_dose(medicine)
        except Exception:
            daily_ceiling = None

        # --- Weight-based route ---------------------------------------------
        # The single most important calculation in the application. Where a
        # published mg/kg figure exists AND a weight is on file, the dose is
        # weight-based; this is how paediatric prescribing actually works. The
        # remaining age-formula branches are only fallbacks.
        if patient.age < 18 and patient.weight_kg and (mg_per_kg or base_dose):
            from app.services.weight_dosing_service import WeightDoser
            weight_result = WeightDoser.calculate(
                patient,
                reference,
                doses_per_day=doses_per_day,
                max_daily_dose_mg=daily_ceiling,
            )
            if weight_result:
                dose = weight_result['dose']
                method = weight_result['method']
                caveats.extend(weight_result['warnings'])
                steps = weight_result['steps']
                if weight_result['route'] == 'weight':
                    caveats.insert(0, 'Dosed on the recorded weight of %s kg.'
                                   % patient.weight_kg)

                confidence = 'documented' if known_drug else 'low'
                if not known_drug:
                    confidence = 'low'

                caveats = [c for c in caveats if c]
                note = 'Estimated using %s. Verify with a prescriber before use.' % method
                if caveats:
                    note = note + ' + ' + ' '.join(caveats)
                if not known_drug:
                    note += (' No reference dose on file for this medicine, so a '
                             'generic baseline was used.')

                result = {
                    'medicine_id': medicine.id,
                    'medicine_name': medicine.name,
                    'patient_id': patient.id,
                    'patient_age': patient.age,
                    'patient_weight_kg': patient.weight_kg,
                    'patient_height_cm': patient.height_cm,
                    'patient_bsa_m2': patient.bsa_m2,
                    'dosage_amount': dose,
                    'dosage_unit': 'mg',
                    'frequency': frequency,
                    'duration_days': 5,
                    'special_notes': note,
                    'indication': condition or 'General use',
                    'calculation_method': method,
                    'formula': weight_result['formula'],
                    'calculation_steps': steps,
                    'confidence': confidence,
                    'is_weight_based': weight_result['is_weight_based'],
                    'dose_capped': weight_result['capped'],
                    'caps_applied': weight_result['caps_applied'],
                    'caveats': caveats,
                    'daily_total_mg': weight_result['daily_total_mg'],
                    'max_single_dose_mg': weight_result['max_single_dose_mg'],
                    'max_daily_dose_mg': weight_result['max_daily_dose_mg'],
                    'source': 'Weight-based calculation from the recorded weight',
                }
                return result

        if patient.age >= 18:
            dose = base_dose
            method = 'Adult reference dose'
        elif mg_per_kg and patient.weight_kg:
            # Weight-based is the preferred route for children. The per-kg
            # figure is per single dose, which is how these are published.
            dose = mg_per_kg * patient.weight_kg
            method = 'Weight-based (%s mg/kg)' % mg_per_kg
            caveats.append(
                'Dosed on the recorded weight of %s kg.' % patient.weight_kg)
        elif mg_per_kg and not patient.weight_kg:
            # The drug has a proper mg/kg dose but no weight is recorded.
            # Falling back to an age formula is legitimate practice, but the
            # missing weight is stated so this is never mistaken for a
            # weight-based calculation.
            dose = base_dose * patient.age / (patient.age + 12)
            method = "Young's rule (weight not recorded)"
            caveats.append(
                'No weight on file, so an age-based formula was used. Record '
                'the weight for an accurate paediatric dose.')
        else:
            # Not used in children, or no paediatric figure published.
            dose = base_dose * patient.age / (patient.age + 12)
            method = "Young's rule"
            caveats.append(
                'No published paediatric mg/kg dose for this medicine, so this '
                'is an estimate only.')

        # Cap at the maximum single dose. mg/kg extrapolates badly for a heavy
        # child: 15 mg/kg for a 45 kg twelve-year-old gives 675 mg, above what
        # an adult would take for a single dose.
        capped = False
        if dose > max_single:
            dose = max_single
            capped = True
            caveats.append('Capped at the %s maximum single dose.'
                           % _fmt_mg(max_single))

        dose = round(dose, 3) if dose < 1 else round(dose, 2)

        # Verify the resulting daily total against the ceiling. This is the one
        # arithmetic error that actually harms people, so it is checked rather
        # than assumed correct.
        ceiling_finding = None
        try:
            from app.services.safety_service import SafetyEngine
            daily = dose * doses_per_day
            finding = SafetyEngine.check_dose_ceiling(medicine, daily)
            if finding:
                ceiling_finding = finding.to_dict()
                ceiling = SafetyEngine.max_daily_dose(medicine)
                if ceiling:
                    allowed_single = ceiling / float(doses_per_day)
                    if allowed_single < dose:
                        dose = round(allowed_single, 2)
                        caveats.append(
                            'Reduced to keep the daily total within the %s '
                            'mg/day maximum.' % ceiling)
        except Exception:
            # The safety layer is the authority here. If it cannot run, say so
            # rather than silently presenting an unchecked dose.
            caveats.append('Daily maximum could not be verified - check manually.')

        confidence = 'documented' if known_drug else 'low'
        if known_drug and patient.age < 18 and not patient.weight_kg:
            confidence = 'moderate'

        note = 'Estimated using %s. Verify with a prescriber before use.' % method
        if caveats:
            note = note + ' + ' + ' '.join(caveats)
        if not known_drug:
            note += (' No reference dose on file for this medicine, so a '
                     'generic baseline was used.')

        result = {
            'medicine_id': medicine.id,
            'medicine_name': medicine.name,
            'patient_id': patient.id,
            'patient_age': patient.age,
            'patient_weight_kg': patient.weight_kg,
            'patient_height_cm': patient.height_cm,
            'patient_bsa_m2': patient.bsa_m2,
            'dosage_amount': dose,
            'dosage_unit': 'mg',
            'frequency': frequency,
            'duration_days': 5,
            'special_notes': note,
            'indication': condition or 'General use',
            'calculation_method': method,
            'confidence': confidence,
            'is_weight_based': False,
            'dose_capped': capped,
            'caveats': caveats,
            'daily_total_mg': round(dose * doses_per_day, 2),
            'max_single_dose_mg': max_single,
            'source': 'Estimated from reference dose - no stored dosage guide',
        }
        if ceiling_finding:
            result['dose_ceiling_warning'] = ceiling_finding
        return result
    
    @staticmethod
    def calculate_total_dosage(dosage_amount, frequency_str, duration_days):
        """
        Calculate total amount of medicine needed for entire duration
        frequency_str example: "2 times a day", "3 times daily"
        """
        try:
            # Extract frequency number
            frequency = int(frequency_str.split()[0])
            total_doses = frequency * duration_days
            total_amount = dosage_amount * total_doses
            
            return {
                'total_amount': total_amount,
                'total_doses': total_doses,
                'total_amount_per_day': dosage_amount * frequency,
            }
        except:
            return None
    
    @staticmethod
    def get_drug_cycle_info(medicine):
        """
        Get information about drug cycle (how long before tolerance builds, etc.)
        Returns recommended dosage cycle and break periods
        """
        antibiotic_classes = ['Amoxicillin', 'Azithromycin', 'Ciprofloxacin']
        steroid_classes = ['Prednisone', 'Dexamethasone', 'Hydrocortisone']
        
        # NOTE: these previously read `5-7` and `7-14`, which Python evaluates
        # as arithmetic (5 - 7 == -2 days). They must be strings.
        if medicine.generic_name in antibiotic_classes:
            return {
                'type': 'Antibiotic',
                'standard_cycle': '5-7',
                'break_required': False,
                'notes': 'Complete full course even if symptoms improve'
            }
        elif medicine.generic_name in steroid_classes:
            return {
                'type': 'Steroid',
                'standard_cycle': '7-14',
                'break_required': True,
                'tapering_required': True,
                'notes': 'Gradual tapering needed. Do not stop abruptly.'
            }
        else:
            return {
                'type': 'General',
                'standard_cycle': '7',
                'break_required': False,
                'notes': 'Standard dosing as per doctor recommendation'
            }


class InteractionChecker:
    """Check for drug interactions and allergies"""
    
    # Documented cross-reactivity groups.
    # Substring matching alone misses these: a patient recorded as allergic to
    # "Penicillin" must be flagged for Amoxicillin, which shares the beta-lactam
    # ring and carries a real, clinically significant cross-reaction risk.
    ALLERGY_GROUPS = {
        'penicillin': [
            'penicillin', 'amoxicillin', 'amoxycillin', 'ampicillin', 'piperacillin',
            'cloxacillin', 'flucloxacillin', 'ticarcillin', 'carbenicillin',
            'co-amoxiclav', 'clavulanic', 'beta-lactam',
        ],
        'cephalosporin': [
            'cephalosporin', 'cefalexin', 'cephalexin', 'cefixime', 'ceftriaxone',
            'cefotaxime', 'cefuroxime', 'ceftazidime', 'cefpodoxime', 'cefadroxil',
        ],
        'sulfa': ['sulfa', 'sulfamethoxazole', 'sulfadiazine', 'co-trimoxazole', 'cotrimoxazole'],
        'nsaid': ['nsaid', 'ibuprofen', 'diclofenac', 'naproxen', 'aspirin', 'ketorolac',
                  'indomethacin', 'aceclofenac', 'etoricoxib', 'nimesulide'],
        'macrolide': ['macrolide', 'azithromycin', 'erythromycin', 'clarithromycin', 'roxithromycin'],
        'quinolone': ['quinolone', 'ciprofloxacin', 'levofloxacin', 'ofloxacin', 'moxifloxacin'],
        'statin': ['statin', 'atorvastatin', 'simvastatin', 'rosuvastatin', 'pravastatin'],
        'ace inhibitor': ['ace inhibitor', 'lisinopril', 'enalapril', 'ramipril', 'perindopril',
                          'captopril', 'quinapril'],
        'proton pump inhibitor': ['proton pump', 'omeprazole', 'pantoprazole', 'esomeprazole',
                                  'rabeprazole', 'lansoprazole'],
        'anticonvulsant': ['carbamazepine', 'phenytoin', 'valproate', 'lamotrigine', 'phenobarbital'],
    }

    @staticmethod
    def check_patient_allergies(patient_id, medicine_id):
        """
        Check whether a recorded allergy applies to this medicine, including
        within-group cross-reactivity.
        """
        patient = Patient.query.get(patient_id)
        medicine = Medicine.query.get(medicine_id)

        if not patient or not medicine:
            return None
        allergies = PatientAllergy.query.filter_by(patient_id=patient_id).all()
        if not allergies:
            return {'has_allergy': False, 'warning': None, 'checked_allergens': 0}

        clinical_text = ' '.join(filter(None, [
            medicine.name,
            medicine.generic_name,
            medicine.brand_name,
            medicine.salt_composition,
            medicine.pharmacological_class,
            medicine.therapeutic_class,
        ])).lower()

        for allergy in allergies:
            allergen = (allergy.allergen or '').strip().lower()
            if not allergen:
                continue
            direct = allergen in clinical_text
            cross_group = None
            if not direct:
                for group, members in InteractionChecker.ALLERGY_GROUPS.items():
                    allergen_references_group = allergen == group or group in allergen
                    if not allergen_references_group:
                        continue
                    if any(member in clinical_text for member in members):
                        cross_group = group
                        break
            if not direct and not cross_group:
                continue
            if cross_group:
                reason = (f"recorded allergy to {allergy.allergen} - cross-reactivity "
                          f"risk with the {cross_group} group")
            else:
                reason = f"recorded allergy to {allergy.allergen}"
            return {
                'has_allergy': True,
                'allergen': allergy.allergen,
                'reaction': allergy.reaction,
                'severity': allergy.severity,
                'cross_reactivity_group': cross_group,
                'match_type': 'cross-reactivity' if cross_group else 'direct',
                'warning': f"CAUTION: patient has a {allergy.severity.lower()} {reason}.",
                'checked_allergens': len(allergies),
            }

        return {
            'has_allergy': False,
            'warning': None,
            'checked_allergens': len(allergies),
        }

    @staticmethod
    def check_drug_interactions(medicine_id, patient_current_medicines):
        """Check for interactions with patient's current medications"""
        medicine = Medicine.query.get(medicine_id)
        
        if not medicine or not medicine.drug_interactions:
            return {'has_interactions': False}
        
        interactions_found = []
        current_meds = [m.strip() for m in patient_current_medicines.split(',') if m.strip()]
        
        for current_med in current_meds:
            if current_med.lower() in medicine.drug_interactions.lower():
                interactions_found.append(current_med)
        
        return {
            'has_interactions': len(interactions_found) > 0,
            'interacting_medicines': interactions_found,
            'interaction_details': medicine.drug_interactions if interactions_found else None
        }
    
    @staticmethod
    def check_contraindications(medicine_id, patient_id):
        """Check if medicine is contraindicated for patient's conditions"""
        patient = Patient.query.get(patient_id)
        medicine = Medicine.query.get(medicine_id)
        
        if not patient or not medicine or not medicine.contraindications:
            return {'has_contraindications': False}
        
        contraindications_found = []
        
        if patient.chronic_diseases:
            diseases = [d.strip() for d in patient.chronic_diseases.split(',')]
            for disease in diseases:
                if disease.lower() in medicine.contraindications.lower():
                    contraindications_found.append(disease)
        
        return {
            'has_contraindications': len(contraindications_found) > 0,
            'contraindicated_for': contraindications_found,
            'details': medicine.contraindications if contraindications_found else None
        }
