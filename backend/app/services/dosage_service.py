from datetime import datetime, timedelta
from app.models import Medicine, Patient, PatientAllergy, DosageGuide

class DosageCalculator:
    """Service for calculating dosage based on patient conditions, age, and weight"""
    
    @staticmethod
    def calculate_dosage(medicine_id, patient_id, condition=None):
        """
        Calculate dosage for a patient based on their age and condition
        Returns dosage amount, frequency, and duration
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
        
        if not dosage_guide:
            # If no specific guide, calculate based on standard pediatric/adult dose
            return DosageCalculator.calculate_default_dosage(medicine, patient, condition)
        
        return {
            'medicine_id': medicine_id,
            'medicine_name': medicine.name,
            'patient_id': patient_id,
            'patient_age': patient.age,
            'dosage_amount': dosage_guide.dosage_amount,
            'dosage_unit': dosage_guide.dosage_unit,
            'frequency': dosage_guide.frequency,
            'duration_days': dosage_guide.duration_days,
            'special_notes': dosage_guide.special_notes,
            'indication': dosage_guide.indication,
        }
    
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
        Fallback dose estimation when no stored DosageGuide row exists.

        Applies Young's rule (child dose = adult dose x age / (age + 12)) rather
        than a fixed percentage of a guessed adult dose. The result is a
        starting estimate and is labelled as such in special_notes, together
        with the rule applied and a confidence flag.
        """""
        # Adult reference doses (mg), keyed lowercase so matching is reliable.
        # Medicines absent from this table fall back to a generic 500 mg
        # baseline and are reported as 'low' confidence.
        adult_dose = {
            'paracetamol': 1000,
            'acetaminophen': 1000,
            'ibuprofen': 400,
            'amoxicillin': 500,
            'aspirin': 325,
            'metformin': 500,
            'omeprazole': 20,
            'lisinopril': 10,
            'atorvastatin': 20,
            'cetirizine': 10,
            'azithromycin': 500,
            'ciprofloxacin': 500,
            'diclofenac': 50,
            'pantoprazole': 40,
            'montelukast': 10,
            'amlodipine': 5,
        }

        key = (medicine.generic_name or '').strip().lower()
        base_dose = adult_dose.get(key)
        known_drug = base_dose is not None
        if base_dose is None:
            base_dose = 500
        # Young's rule: child dose = adult dose x age / (age + 12).
        # Used instead of the previous fixed percentages, which ignored weight
        # and were not traceable to any published method.
        if patient.age < 18:
            dose = base_dose * patient.age / (patient.age + 12)
            method = "Young's rule"
        else:
            dose = base_dose
            method = 'Adult dose'

        if patient.age < 1:
            frequency = 'Every 6-8 hours as needed'
        elif patient.age < 12:
            frequency = '3 times a day'
        else:
            frequency = '2-3 times a day'

        dose = round(dose, 2)
        note = f"Estimated using {method}. Verify with a prescriber before use."
        if not known_drug:
            note += ' No adult reference dose on file; a generic 500 mg baseline was used.'

        return {
            'medicine_id': medicine.id,
            'medicine_name': medicine.name,
            'patient_id': patient.id,
            'patient_age': patient.age,
            'dosage_amount': dose,
            'dosage_unit': 'mg',
            'frequency': frequency,
            'duration_days': 5,
            'special_notes': note,
            'indication': condition or 'General use',
            'calculation_method': method,
            'confidence': 'documented' if known_drug else 'low',
            'source': 'Estimated from adult reference dose - no stored dosage guide',
        }
    
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
