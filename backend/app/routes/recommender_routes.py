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

        # Run the full engine as well, so the prescription writer gets the
        # comorbidity, renal, hepatic, age and pregnancy findings and not just
        # the three checks this route performed historically. The template is
        # kept so existing callers continue to work unchanged.
        try:
            from app.services.safety_service import SafetyEngine
            full = SafetyEngine.assess(
                patient_id, medicine_id,
                context={'dose_unit': (data.get('dose_unit') or '')})
        except Exception:
            full = None
        return jsonify({
            'success': True,
            'data': {
                'medicine_id': medicine_id,
                'medicine_name': medicine.name,
                'patient_id': patient_id,
                'patient_name': f'{patient.first_name} {patient.last_name}',
                # `safe` historically meant "no hard blockers". The engine's
                # `recommendable` is stricter and is what new code should use,
                # so both are reported rather than one silently changing
                # meaning under existing callers.
                'safe': len(blockers) == 0,
                'recommendable': (full or {}).get('recommendable', len(blockers) == 0),
                'verdict': (full or {}).get('verdict'),
                'blockers': blockers,
                'warnings': warnings,
                'findings': (full or {}).get('findings', []),
                'checks_run': (full or {}).get('checks_run', []),
                'checks_failed': (full or {}).get('checks_failed', []),
                'unknown_reason': (full or {}).get('unknown_reason'),
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


# ===================================================================== #
# Full safety assessment
# ===================================================================== #

@recommender_bp.route('/assess', methods=['POST'])
def assess_safety():
    """
    The complete safety assessment for a patient/medicine pair.

    This is the authoritative endpoint. The older /safety-screen route is kept
    because the prescription writer calls it, but anything new should use this
    one: it runs the comorbidity, renal, hepatic, age, pregnancy and form checks
    as well as allergy and interaction, and it reports a graded verdict rather
    than a yes/no.

    GET vs POST: POST because a dose unit may be supplied so the form/unit
    consistency check can run.
    """
    try:
        from app.services.safety_service import SafetyEngine
        data = request.get_json() or {}
        patient_id = data.get('patient_id')
        medicine_id = data.get('medicine_id')

        if not patient_id or not medicine_id:
            return jsonify({
                'success': False,
                'error': 'Both patient_id and medicine_id are required.',
            }), 400

        context = {}
        if data.get('dose_unit'):
            context['dose_unit'] = data['dose_unit']

        result = SafetyEngine.assess(patient_id, medicine_id, context=context)
        return jsonify({'success': True, 'data': result})

    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400


@recommender_bp.route('/administration-plan', methods=['POST'])
def administration_plan():
    """
    Course length, timing, tapering and missed-dose advice for a medicine.

    Optionally takes frequency and duration so a prescriber's explicit
    instruction overrides the class default - the plan must never silently
    replace what has actually been written.
    """
    try:
        from app.services.administration_service import AdministrationCycle
        data = request.get_json() or {}
        medicine_id = data.get('medicine_id')
        if not medicine_id:
            return jsonify({'success': False,
                            'error': 'medicine_id is required.'}), 400

        medicine = Medicine.query.get(medicine_id)
        if not medicine:
            return jsonify({'success': False,
                            'error': 'Medicine not found.'}), 404

        plan = AdministrationCycle.build(
            medicine,
            frequency=data.get('frequency'),
            duration_days=data.get('duration_days'),
            indication=data.get('indication'),
        )
        plan['summary'] = AdministrationCycle.summary_line(plan)
        plan['medicine_name'] = medicine.name
        return jsonify({'success': True, 'data': plan})

    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400


# ===================================================================== #
# Substitution - what to dispense when the first choice is unavailable
# ===================================================================== #

@recommender_bp.route('/substitutes/<int:medicine_id>', methods=['GET'])
def get_substitutes(medicine_id):
    """
    Closest safe substitutes for a medicine, ranked by how much clinical
    substitution is actually required.

    Query parameters:
      patient_id              screen each candidate against this patient
      include_different_class 1 to also surface cross-class options
      require_stock           0 to include items with no stock on hand
    """
    try:
        from app.services.substitution_service import SubstitutionEngine

        patient_id = request.args.get('patient_id', type=int)
        include_different = request.args.get('include_different_class') == '1'
        require_stock = request.args.get('require_stock', '1') != '0'

        result = SubstitutionEngine.find_substitutes(
            medicine_id,
            patient_id=patient_id,
            include_different_class=include_different,
            require_stock=require_stock,
        )
        if not result:
            return jsonify({'success': False,
                            'error': 'Medicine not found.'}), 404
        return jsonify({'success': True, 'data': result})

    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400


@recommender_bp.route('/dispense-plan', methods=['POST'])
def dispense_plan():
    """
    A concrete answer for one medicine: can it be dispensed now, and if not,
    what is the closest thing that can be.

    This is the endpoint the counter actually needs. It reports stock, runs the
    safety assessment, and - crucially - treats a contraindicated medicine as
    undispensable even when it is sitting on the shelf.
    """
    try:
        from app.services.substitution_service import SubstitutionEngine
        data = request.get_json() or {}
        medicine_id = data.get('medicine_id')
        if not medicine_id:
            return jsonify({'success': False,
                            'error': 'medicine_id is required.'}), 400

        plan = SubstitutionEngine.dispense_plan(
            medicine_id,
            patient_id=data.get('patient_id'),
            quantity_needed=data.get('quantity_needed', 1),
        )
        if not plan:
            return jsonify({'success': False,
                            'error': 'Medicine not found.'}), 404
        return jsonify({'success': True, 'data': plan})

    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400


@recommender_bp.route('/resolve', methods=['GET'])
def resolve_condition():
    """
    "The patient needs something for X" - answered end to end.

    Returns what is in stock and safe, what is out of stock with a closest
    substitute for each, and what was reviewed and set aside, with the reason.
    Nothing is hidden, but only verified-safe options are presented as choices.

    Query parameters:
      condition   required
      patient_id  optional but strongly recommended
      limit       maximum entries per list (default 8)
    """
    try:
        from app.services.substitution_service import SubstitutionEngine

        condition = request.args.get('condition')
        if not condition:
            return jsonify({'success': False,
                            'error': 'condition is required.'}), 400

        result = SubstitutionEngine.resolve_for_condition(
            condition,
            patient_id=request.args.get('patient_id', type=int),
            limit=request.args.get('limit', 8, type=int),
        )
        if not result:
            return jsonify({'success': False,
                            'error': 'No condition supplied.'}), 400
        return jsonify({'success': True, 'data': result})

    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400


# ===================================================================== #
# Live reference lookup (optional, offline-first)
# ===================================================================== #

@recommender_bp.route('/reference/<path:drug_name>', methods=['GET'])
def live_reference(drug_name):
    """
    Look up a drug in the openFDA labelling database.

    Served from the on-disk cache when possible, so this works offline for any
    drug fetched before. Only the drug name is ever sent - no patient data
    leaves the machine.

    Returns the monograph plus its source. This is reference material, never a
    recommendation, and it is deliberately not fed into the ranking engine.
    """
    try:
        from app.services.live_reference_service import LiveReference

        force = request.args.get('refresh') == '1'
        payload, error = LiveReference.fetch_monograph(drug_name, force=force)
        if error:
            return jsonify({
                'success': False,
                'error': error,
                'offline_note': ('The application works fully offline. This '
                                 'optional lookup is the only feature that '
                                 'uses the network.'),
            }), 503
        return jsonify({'success': True, 'data': payload})

    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400


@recommender_bp.route('/reference-cache', methods=['GET'])
def reference_cache_stats():
    """How many monographs are cached locally, and where they live."""
    try:
        from app.services.live_reference_service import LiveReference
        return jsonify({'success': True, 'data': LiveReference.cache_stats()})
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400


@recommender_bp.route('/reference-cache', methods=['DELETE'])
def clear_reference_cache():
    """Delete every cached monograph."""
    try:
        from app.services.live_reference_service import LiveReference
        removed = LiveReference.clear_cache()
        return jsonify({
            'success': True,
            'message': 'Removed %d cached monograph(s).' % removed,
        })
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400


@recommender_bp.route('/enrich/<int:medicine_id>', methods=['POST'])
def enrich_medicine(medicine_id):
    """
    Fill gaps in a local medicine record from the live reference source.

    Only ever adds to fields that are empty. An authored value is never
    overwritten: the local set is curated and safety-reviewed, the fetched text
    is not, so the curated value wins every conflict.
    """
    try:
        from app.services.live_reference_service import LiveReference

        medicine = Medicine.query.get(medicine_id)
        if not medicine:
            return jsonify({'success': False,
                            'error': 'Medicine not found.'}), 404

        result, error = LiveReference.enrich_medicine(medicine)
        if error:
            return jsonify({'success': False, 'error': error}), 503

        return jsonify({
            'success': True,
            'message': ('Filled %d field(s) from FDA labelling.'
                        % len(result['filled_fields'])),
            'data': {
                'filled_fields': result['filled_fields'],
                'source': result['payload'].get('source'),
                'medicine': medicine.to_dict(),
            },
        })

    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
