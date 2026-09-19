from flask import Blueprint, request, jsonify
from app.models import Medicine, Patient, Prescription, Inventory
from app.services import (
    DosageCalculator, InteractionChecker, MedicineRecommender, AlternativeFinder,
)

recommender_bp = Blueprint('recommender', __name__, url_prefix='/api/recommender')

@recommender_bp.route('/dosage', methods=['POST'])
def calculate_dosage():
    """Calculate dosage for a medicine and patient"""
    try:
        data = request.get_json()
        patient_id = data.get('patient_id')
        medicine_id = data.get('medicine_id')
        condition = data.get('condition')

        dosage = DosageCalculator.calculate_dosage(medicine_id, patient_id, condition)

        if not dosage:
            return jsonify({
                'success': False,
                'error': 'Could not calculate dosage'
            }), 404

        return jsonify({
            'success': True,
            'data': dosage
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@recommender_bp.route('/total-dosage', methods=['POST'])
def calculate_total_dosage():
    """Calculate total medication needed for entire duration"""
    try:
        data = request.get_json()

        total = DosageCalculator.calculate_total_dosage(
            data['dosage_amount'],
            data['frequency'],
            data['duration_days']
        )

        if not total:
            return jsonify({
                'success': False,
                'error': 'Invalid frequency format'
            }), 400

        return jsonify({
            'success': True,
            'data': total
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@recommender_bp.route('/drug-cycle/<int:medicine_id>', methods=['GET'])
def get_drug_cycle(medicine_id):
    """Get drug cycle information"""
    try:
        medicine = Medicine.query.get_or_404(medicine_id)
        cycle_info = DosageCalculator.get_drug_cycle_info(medicine)

        return jsonify({
            'success': True,
            'data': cycle_info
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@recommender_bp.route('/check-allergies', methods=['POST'])
def check_allergies():
    """Check if patient has allergies to medicine"""
    try:
        data = request.get_json()
        patient_id = data.get('patient_id')
        medicine_id = data.get('medicine_id')

        result = InteractionChecker.check_patient_allergies(patient_id, medicine_id)

        return jsonify({
            'success': True,
            'data': result
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@recommender_bp.route('/check-interactions', methods=['POST'])
def check_interactions():
    """Check for drug interactions"""
    try:
        data = request.get_json()
        medicine_id = data.get('medicine_id')
        current_medicines = data.get('current_medicines', '')

        result = InteractionChecker.check_drug_interactions(medicine_id, current_medicines)

        return jsonify({
            'success': True,
            'data': result
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@recommender_bp.route('/check-contraindications', methods=['POST'])
def check_contraindications():
    """Check contraindications"""
    try:
        data = request.get_json()
        patient_id = data.get('patient_id')
        medicine_id = data.get('medicine_id')

        # NOTE: the signature is (medicine_id, patient_id). Passing these in the
        # other order silently returns "no contraindications" for every patient.
        result = InteractionChecker.check_contraindications(medicine_id, patient_id)

        return jsonify({
            'success': True,
            'data': result
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@recommender_bp.route('/alternatives', methods=['GET', 'POST'])
def get_alternatives_for_medicine():
    """
    Other medicines that treat the same condition as a given medicine.

    Accepts medicine_id either as a query parameter or in a JSON body.
    Passing patient_id screens every alternative against that patient.
    """
    try:
        if request.method == 'GET':
            medicine_id = request.args.get('medicine_id', type=int)
            patient_id = request.args.get('patient_id', type=int)
            limit = request.args.get('limit', 10, type=int)
        else:
            data = request.get_json() or {}
            medicine_id = data.get('medicine_id')
            patient_id = data.get('patient_id')
            limit = data.get('limit', 10)

        if not medicine_id:
            return jsonify({'success': False, 'error': 'medicine_id is required'}), 400
        result = AlternativeFinder.find_alternatives(medicine_id, patient_id, limit)
        if result is None:
            return jsonify({'success': False, 'error': 'Medicine not found'}), 404
        return jsonify({'success': True, 'data': result})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400
@recommender_bp.route('/by-condition', methods=['GET'])
def get_medicines_by_condition():
    """
    Every medicine for a named condition, grouped by therapeutic class.

    This is "show me all the options for X" as opposed to starting from a
    particular medicine.
    """
    try:
        condition = request.args.get('condition', '').strip()
        patient_id = request.args.get('patient_id', type=int)
        limit = request.args.get('limit', 20, type=int)

        if not condition:
            return jsonify({'success': False, 'error': 'condition is required'}), 400
        result = AlternativeFinder.find_by_condition(condition, patient_id, limit)
        if result is None:
            return jsonify({'success': False, 'error': 'condition is required'}), 400
        return jsonify({'success': True, 'data': result})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400
@recommender_bp.route('/safety-screen', methods=['POST'])
def safety_screen():
    """
    One-shot safety check for a patient/medicine pair.

    Combines the four individual checks (allergy, contraindication, interaction
    with the patient's own current medications, and stock availability) so the
    dosage calculator and patient panel can present a single verdict.
    """
    try:
        data = request.get_json()
        patient_id = data.get('patient_id')
        medicine_id = data.get('medicine_id')

        patient = Patient.query.get(patient_id)
        medicine = Medicine.query.get(medicine_id)
        if not patient or not medicine:
            return jsonify({
                'success': False,
                'error': 'Patient or medicine not found'
            }), 404
        allergy = InteractionChecker.check_patient_allergies(patient_id, medicine_id)
        contraindication = InteractionChecker.check_contraindications(medicine_id, patient_id)
        # Use the patient's recorded current medications rather than an empty
        # string, which is what made the old dosage calculator always report
        # "no interactions".
        interaction = InteractionChecker.check_drug_interactions(
            medicine_id,
            patient.current_medications or '',
        )

        stock = Inventory.query.filter_by(medicine_id=medicine_id).all()
        total_stock = sum(item.quantity_in_stock for item in stock)

        blockers = []
        warnings = []

        if allergy.get('has_allergy'):
            blockers.append({
                'kind': 'ALLERGY',
                'message': allergy.get('warning') or 'Patient allergy on record.',
                'detail': allergy.get('reaction'),
                'severity': allergy.get('severity'),
            })
        if contraindication.get('has_contraindications'):
            blockers.append({
                'kind': 'CONTRAINDICATION',
                'message': 'Contraindicated for: ' + ', '.join(
                    contraindication.get('contraindicated_for', [])),
                'detail': contraindication.get('details'),
            })
        if interaction.get('has_interactions'):
            warnings.append({
                'kind': 'INTERACTION',
                'message': 'May interact with: ' + ', '.join(
                    interaction.get('interacting_medicines', [])),
                'detail': interaction.get('interaction_details'),
            })
        if total_stock <= 0:
            warnings.append({
                'kind': 'STOCK',
                'message': 'No stock on hand for this medicine.',
                'detail': None,
            })

        return jsonify({
            'success': True,
            'data': {
                'medicine_id': medicine_id,
                'medicine_name': medicine.name,
                'patient_id': patient_id,
                'patient_name': f'{patient.first_name} {patient.last_name}',
                'safe': len(blockers) == 0,
                'blockers': blockers,
                'warnings': warnings,
                'total_stock': total_stock,
                'allergy_check': allergy,
                'contraindication_check': contraindication,
                'interaction_check': interaction,
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
@recommender_bp.route('/recommend-medicines', methods=['POST'])
def recommend_medicines():
    """Get medicine recommendations based on condition"""
    try:
        data = request.get_json()
        patient_id = data.get('patient_id')
        condition = data.get('condition')
        severity = data.get('severity', 'mild')  # mild, moderate, severe
        
        recommendations = MedicineRecommender.recommend_medicines(patient_id, condition, severity)
        
        return jsonify({
            'success': True,
            'data': recommendations,
            'total': len(recommendations)
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@recommender_bp.route('/similar-cases', methods=['GET'])
def get_similar_cases():
    """Get similar past cases for patient"""
    try:
        patient_id = request.args.get('patient_id', type=int)
        condition = request.args.get('condition', '')
        limit = request.args.get('limit', 5, type=int)
        
        cases = MedicineRecommender.get_similar_past_cases(patient_id, condition, limit)
        
        return jsonify({
            'success': True,
            'data': cases
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@recommender_bp.route('/alternative-medicines', methods=['POST'])
def get_alternatives():
    """Get alternative medicines"""
    try:
        data = request.get_json()
        patient_id = data.get('patient_id')
        medicine_id = data.get('medicine_id')
        
        alternatives = MedicineRecommender.recommend_alternative_medicines(patient_id, medicine_id)
        
        return jsonify({
            'success': True,
            'data': alternatives
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@recommender_bp.route('/medicine-details/<int:medicine_id>', methods=['GET'])
def get_medicine_analysis(medicine_id):
    """Get complete medicine analysis including availability, pricing, etc."""
    try:
        medicine = Medicine.query.get_or_404(medicine_id)
        inventory = Inventory.query.filter_by(medicine_id=medicine_id).all()
        
        total_stock = sum(inv.quantity_in_stock for inv in inventory)
        in_stock = any(inv.status == 'in_stock' for inv in inventory)
        
        data = medicine.to_dict()
        data['inventory_summary'] = {
            'total_stock': total_stock,
            'in_stock': in_stock,
            'available_batches': len(inventory),
            'prices': {
                'cost_price': medicine.cost_price,
                'selling_price': medicine.selling_price,
                'profit_margin': ((medicine.selling_price - medicine.cost_price) / medicine.cost_price * 100) if medicine.cost_price > 0 else 0
            }
        }
        
        return jsonify({
            'success': True,
            'data': data
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
