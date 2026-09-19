from app.models import Medicine, Patient, Prescription, PatientAllergy, Inventory
from .dosage_service import InteractionChecker, DosageCalculator
from datetime import datetime

class MedicineRecommender:
    """Smart medicine recommendation system based on patient conditions, allergies, and past cases"""

    @staticmethod
    def recommend_medicines(patient_id, condition, severity='mild'):
        """
        Recommend medicines based on patient's condition and medical history
        severity: 'mild', 'moderate', 'severe'
        """
        patient = Patient.query.get(patient_id)

        if not patient:
            return []

        recommendations = []

        # Get condition-specific medicines
        condition_medicines = Medicine.query.filter(
            Medicine.use_case.ilike(f"%{condition}%")
        ).all()

        for medicine in condition_medicines:
            # Check allergies
            allergy_check = InteractionChecker.check_patient_allergies(patient_id, medicine.id)

            if allergy_check['has_allergy']:
                continue

            # Check contraindications
            contraindication_check = InteractionChecker.check_contraindications(patient_id, medicine.id)

            if contraindication_check['has_contraindications']:
                continue

            # Calculate dosage for patient
            dosage = DosageCalculator.calculate_dosage(medicine.id, patient_id, condition)

            # Get drug cycle info
            cycle_info = DosageCalculator.get_drug_cycle_info(medicine)

            # Calculate recommendation score
            score = MedicineRecommender.calculate_recommendation_score(
                patient, medicine, condition, severity
            )

            recommendation = {
                'medicine_id': medicine.id,
                'medicine_name': medicine.name,
                'generic_name': medicine.generic_name,
                'brand_name': medicine.brand_name,
                'manufacturer': medicine.manufacturer,
                'strength': medicine.strength,
                'form': medicine.form,
                'selling_price': medicine.selling_price,
                'use_case': medicine.use_case,
                'dosage': dosage,
                'cycle_info': cycle_info,
                'recommendation_score': score,
                'reason': MedicineRecommender.get_recommendation_reason(medicine, condition, score),
            }

            recommendations.append(recommendation)

        # Sort by recommendation score
        recommendations.sort(key=lambda x: x['recommendation_score'], reverse=True)

        return recommendations[:5]  # Return top 5 recommendations

    @staticmethod
    def calculate_recommendation_score(patient, medicine, condition, severity):
        """
        Calculate recommendation score based on multiple factors
        Score range: 0-100
        """
        score = 0

        # Base score from condition match
        condition_match = 20
        score += condition_match

        # Age appropriateness
        age_group = DosageCalculator.get_age_group(patient.age)
        dosage_guides = medicine.dosage_guides
        if any(guide.age_group == age_group for guide in dosage_guides):
            score += 15

        # Severity match
        if severity == 'mild':
            score += 10
        elif severity == 'moderate':
            score += 15
        elif severity == 'severe':
            score += 20

        # Popularity (based on prescription count - approximate)
        if medicine.prescription_items:
            score += min(20, len(medicine.prescription_items) * 2)

        # Price factor (prefer affordable medicines)
        if medicine.selling_price < 100:
            score += 10
        elif medicine.selling_price < 500:
            score += 5

        # No allergies or contraindications (already filtered out, so +10)
        score += 10

        return min(100, score)

    @staticmethod
    def get_recommendation_reason(medicine, condition, score):
        """Generate human-readable reason for recommendation"""
        if score >= 80:
            return f"Excellent match for {condition}. Highly recommended."
        elif score >= 60:
            return f"Good option for treating {condition}."
        elif score >= 40:
            return f"Suitable for {condition}. Consider other options as well."
        else:
            return f"Basic option for {condition}. Explore better alternatives."

    @staticmethod
    def get_similar_past_cases(patient_id, condition, limit=5):
        """
        Find similar past cases for the patient
        Used to recommend medicines that worked before
        """
        patient = Patient.query.get(patient_id)

        if not patient:
            return []

        # Get patient's past prescriptions
        past_prescriptions = Prescription.query.filter_by(patient_id=patient_id).all()

        # Find prescriptions for similar conditions
        similar_cases = []
        for prescription in past_prescriptions:
            if condition.lower() in prescription.diagnosis.lower():
                case = {
                    'prescription_id': prescription.id,
                    'diagnosis': prescription.diagnosis,
                    'doctor': prescription.doctor_name,
                    'date': prescription.created_at.isoformat(),
                    'medicines': [
                        {
                            'name': item.medicine.name,
                            'dosage': f"{item.dosage_amount} {item.dosage_unit}",
                            'frequency': item.frequency,
                            'duration': f"{item.duration_days} days",
                        }
                        for item in prescription.items
                    ]
                }
                similar_cases.append(case)

        return similar_cases[:limit]

    @staticmethod
    def recommend_alternative_medicines(patient_id, medicine_id):
        """
        Recommend alternative medicines if patient is allergic or has contraindications
        """
        medicine = Medicine.query.get(medicine_id)

        if not medicine:
            return []

        # Get medicines with similar use case
        alternatives = Medicine.query.filter(
            Medicine.id != medicine_id,
            Medicine.use_case.ilike(f"%{medicine.use_case.split()[0]}%")
        ).all()

        valid_alternatives = []

        for alt_medicine in alternatives:
            # Check allergies
            allergy_check = InteractionChecker.check_patient_allergies(patient_id, alt_medicine.id)

            if allergy_check['has_allergy']:
                continue

            # Check contraindications
            contraindication_check = InteractionChecker.check_contraindications(patient_id, alt_medicine.id)

            if contraindication_check['has_contraindications']:
                continue

            valid_alternatives.append({
                'medicine_id': alt_medicine.id,
                'name': alt_medicine.name,
                'generic_name': alt_medicine.generic_name,
                'brand_name': alt_medicine.brand_name,
                'strength': alt_medicine.strength,
                'selling_price': alt_medicine.selling_price,
                'reason': f"Similar use case. Safe for this patient."
            })

        return valid_alternatives[:5]


class AlternativeFinder:
    """
    Find other medicines that treat the same condition as a given medicine.

    Answers "what else could be given for this disease?" with a side-by-side
    comparison, so the choice can be judged on cost, availability, class and
    safety for a specific patient rather than on name alone.
    """


    # Conditions are matched on these shared vocabulary terms. A medicine's
    # indications text is tokenised and compared against the source medicine's
    # tokens, weighted so that the therapeutic class counts for more than a
    # passing word match.
    STOPWORDS = {
        'and', 'or', 'the', 'for', 'with', 'of', 'in', 'to', 'a', 'an',
        'mild', 'moderate', 'severe', 'acute', 'chronic', 'pain', 'relief',
        'treatment', 'used', 'use', 'cases', 'case', 'adults', 'children',
    }

    @staticmethod
    def _tokens(text):
        if not text:
            return set()
        SQ = ' '
        cleaned = ''.join(
            ch if ch.isalnum() or ch.isspace() else SQ for ch in text.lower()
        )
        return {t for t in cleaned.split() if len(t) > 2 and t not in AlternativeFinder.STOPWORDS}

    @staticmethod
    def _similarity(source, candidate):
        """Weighted overlap score between two medicines' clinical purpose."""
        score = 0.0
        src_use = AlternativeFinder._tokens(source.use_case)
        cand_use = AlternativeFinder._tokens(candidate.use_case)
        if src_use and cand_use:
            overlap = len(src_use & cand_use) / len(src_use | cand_use)
            score += overlap * 60
        # Same therapeutic class is the strongest single signal.
        if source.therapeutic_class and candidate.therapeutic_class:
            if source.therapeutic_class.strip().lower() == candidate.therapeutic_class.strip().lower():
                score += 25
            else:
                src_class = AlternativeFinder._tokens(source.therapeutic_class)
                cand_class = AlternativeFinder._tokens(candidate.therapeutic_class)
                if src_class & cand_class:
                    score += 15
        # Same route and form means a practical substitution.
        if source.form and candidate.form and source.form == candidate.form:
            score += 8
        if source.route_of_administration and candidate.route_of_administration:
            if source.route_of_administration == candidate.route_of_administration:
                score += 4
        return round(min(score, 100.0), 1)

    @staticmethod
    def find_alternatives(medicine_id, patient_id=None, limit=10):
        """
        Return other medicines for the same condition, ranked by similarity.

        When patient_id is supplied each candidate is screened for allergies and
        contraindications, and the result is annotated with stock and price so
        the comparison is actionable.
        """
        source = Medicine.query.get(medicine_id)
        if not source:
            return None
        candidates = Medicine.query.filter(Medicine.id != medicine_id).all()

        results = []
        for candidate in candidates:
            similarity = AlternativeFinder._similarity(source, candidate)
            if similarity < 25:
                continue
            stock = Inventory.query.filter_by(medicine_id=candidate.id).all()
            total_stock = sum(item.quantity_in_stock for item in stock)

            entry = {
                'medicine_id': candidate.id,
                'name': candidate.name,
                'generic_name': candidate.generic_name,
                'brand_name': candidate.brand_name,
                'manufacturer': candidate.manufacturer,
                'strength': candidate.strength,
                'form': candidate.form,
                'molecular_formula': candidate.molecular_formula,
                'therapeutic_class': candidate.therapeutic_class,
                'pharmacological_class': candidate.pharmacological_class,
                'use_case': candidate.use_case,
                'selling_price': candidate.selling_price,
                'cost_price': candidate.cost_price,
                'requires_prescription': candidate.requires_prescription,
                'schedule_classification': candidate.schedule_classification,
                'total_stock': total_stock,
                'in_stock': total_stock > 0,
                'similarity_score': similarity,
                'same_class': bool(
                    source.therapeutic_class and candidate.therapeutic_class
                    and source.therapeutic_class.strip().lower()
                    == candidate.therapeutic_class.strip().lower()
                ),
                'price_difference': round(
                    (candidate.selling_price or 0) - (source.selling_price or 0), 2
                ),
            }

            if patient_id:
                try:
                    allergy = InteractionChecker.check_patient_allergies(
                        patient_id, candidate.id)
                    contra = InteractionChecker.check_contraindications(
                        candidate.id, patient_id)
                    entry['safe_for_patient'] = not (
                        (allergy or {}).get('has_allergy')
                        or (contra or {}).get('has_contraindications')
                    )
                    entry['safety_note'] = (
                        (allergy or {}).get('warning')
                        or (', '.join((contra or {}).get('contraindicated_for', [])) or None)
                    )
                except Exception:
                    entry['safe_for_patient'] = None
                    entry['safety_note'] = 'Safety check unavailable.'
            else:
                entry['safe_for_patient'] = None
                entry['safety_note'] = None
            results.append(entry)

        # Prefer safe options, then closest match, then cheapest.
        results.sort(key=lambda x: (
            x['safe_for_patient'] is False,
            -x['similarity_score'],
            x['selling_price'] or 0,
        ))

        return {
            'source': {
                'medicine_id': source.id,
                'name': source.name,
                'generic_name': source.generic_name,
                'therapeutic_class': source.therapeutic_class,
                'use_case': source.use_case,
                'selling_price': source.selling_price,
            },
            'alternatives': results[:limit],
            'total_considered': len(candidates),
            'total_matched': len(results),
        }

    @staticmethod
    def find_by_condition(condition, patient_id=None, limit=20):
        """
        All medicines for a named condition, grouped by therapeutic class.

        This is the direct "show me everything available for X" query, as
        opposed to find_alternatives which starts from a specific medicine.
        """
        if not condition or not condition.strip():
            return None
        matches = Medicine.query.filter(
            (Medicine.use_case.ilike(f'%{condition}%'))
            | (Medicine.therapeutic_class.ilike(f'%{condition}%'))
            | (Medicine.generic_name.ilike(f'%{condition}%'))
        ).all()

        grouped = {}
        for medicine in matches:
            group = medicine.therapeutic_class or 'Unclassified'
            inventory = Inventory.query.filter_by(medicine_id=medicine.id).all()
            total_stock = sum(i.quantity_in_stock for i in inventory)

            entry = {
                'medicine_id': medicine.id,
                'name': medicine.name,
                'generic_name': medicine.generic_name,
                'brand_name': medicine.brand_name,
                'strength': medicine.strength,
                'form': medicine.form,
                'manufacturer': medicine.manufacturer,
                'molecular_formula': medicine.molecular_formula,
                'selling_price': medicine.selling_price,
                'requires_prescription': medicine.requires_prescription,
                'total_stock': total_stock,
                'in_stock': total_stock > 0,
                'safe_for_patient': None,
                'safety_note': None,
            }

            if patient_id:
                try:
                    allergy = InteractionChecker.check_patient_allergies(
                        patient_id, medicine.id)
                    contra = InteractionChecker.check_contraindications(
                        medicine.id, patient_id)
                    entry['safe_for_patient'] = not (
                        (allergy or {}).get('has_allergy')
                        or (contra or {}).get('has_contraindications')
                    )
                    entry['safety_note'] = (
                        (allergy or {}).get('warning')
                        or (', '.join((contra or {}).get('contraindicated_for', [])) or None)
                    )
                except Exception:
                    pass
            grouped.setdefault(group, []).append(entry)

        for entries in grouped.values():
            entries.sort(key=lambda x: (x['safe_for_patient'] is False, x['selling_price'] or 0))

        return {
            'condition': condition,
            'total_found': len(matches),
            'groups': [
                {'therapeutic_class': name, 'medicines': items}
                for name, items in sorted(grouped.items())
            ][:limit],
        }

class InventoryOptimizer:
    """Optimize inventory based on recommendations and trends"""

    @staticmethod
    def get_stock_alerts():
        """Get inventory alerts for low stock or expired medicines"""
        # NOTE: this method previously did `from app.models import Inventory`
        # here AND `from app.models import Inventory, Medicine` further down.
        # Because both are imports of the same name inside one function body,
        # Python treated Inventory as a local and raised UnboundLocalError on
        # the first use - so /api/inventory/alerts was dead. Import once at
        # module level and do not re-import inside the body.
        alerts = []
        inventory_items = Inventory.query.all()
        
        for item in inventory_items:
            if item.status == 'out_of_stock':
                alerts.append({
                    'type': 'OUT_OF_STOCK',
                    'medicine_name': item.medicine.name,
                    'current_stock': item.quantity_in_stock,
                    'reorder_level': item.reorder_level,
                    'urgency': 'HIGH'
                })
            elif item.status == 'low_stock':
                alerts.append({
                    'type': 'LOW_STOCK',
                    'medicine_name': item.medicine.name,
                    'current_stock': item.quantity_in_stock,
                    'reorder_level': item.reorder_level,
                    'urgency': 'MEDIUM'
                })
            elif item.status == 'expired':
                alerts.append({
                    'type': 'EXPIRED',
                    'medicine_name': item.medicine.name,
                    'expiry_date': item.expiry_date.isoformat(),
                    'urgency': 'HIGH'
                })
        
        return sorted(alerts, key=lambda x: {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}[x['urgency']])
