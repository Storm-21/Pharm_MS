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

@recommender_bp.route('/weight-dose', methods=['POST'])
def weight_dose():
    """
    Show the weight-based dose calculation in full for a patient/medicine pair.

    The calculator's job is to be checkable, not just correct. This endpoint
    returns the formula, the inputs, the arithmetic steps and the result, so a
    pharmacist can see 15 mg/kg x 24.5 kg = 367.5 mg on screen and verify it,
    rather than being asked to trust a single number.

    Body:
        patient_id          required
        medicine_id         optional - used to find a mg/kg reference dose
        mg_per_kg           explicit per-kilogram figure (overrides the table)
        adult_mg            explicit adult dose for the Clark/Young fallbacks
        max_mg              explicit single-dose ceiling
        dose_per_m2         explicit per-m2 figure to force the BSA route
        doses_per_day       used for the daily ceiling check
        method              optional - which formula the prescriber chose:
                            'mg/kg' | 'bsa' | 'clark' | 'young' | 'age-band'
                            Defaults to the automatic (evidence-ranked) route.
    """
    try:
        from app.services.weight_dosing_service import WeightDoser
        data = request.get_json() or {}

        patient = Patient.query.get(data.get('patient_id'))
        if not patient:
            return jsonify({'success': False,
                            'error': 'Patient not found.'}), 404

        reference = {}
        medicine = None
        if data.get('medicine_id'):
            medicine = Medicine.query.get(data.get('medicine_id'))
            if not medicine:
                return jsonify({'success': False,
                                'error': 'Medicine not found.'}), 404
            from app.services.dosage_service import ADULT_REFERENCE_DOSE
            key = (medicine.generic_name or '').strip().lower()
            reference = dict(ADULT_REFERENCE_DOSE.get(key) or {})

        # Explicit values from the request win over the built-in table, so a
        # prescriber who knows the local dose is not overridden by our data.
        for field in ('mg_per_kg', 'adult_mg', 'max_mg', 'dose_per_m2'):
            if data.get(field) not in (None, ''):
                reference[field] = float(data[field])

        if not reference:
            return jsonify({
                'success': False,
                'error': ('No reference dose is available for this medicine. '
                          'Supply mg_per_kg or adult_mg explicitly.'),
            }), 400

        doses_per_day = int(data.get('doses_per_day') or 1)
        daily_ceiling = None
        if medicine:
            try:
                from app.services.safety_service import SafetyEngine
                daily_ceiling = SafetyEngine.max_daily_dose(medicine)
            except Exception:
                daily_ceiling = None

        result = WeightDoser.calculate(
            patient,
            reference,
            medicine=medicine,
            prefer_bsa=bool(reference.get('dose_per_m2')),
            bsa_dose_per_m2=reference.get('dose_per_m2'),
            doses_per_day=doses_per_day,
            max_daily_dose_mg=daily_ceiling,
            method=(data.get('method') or None),
        )
        if not result:
            return jsonify({
                'success': False,
                'error': 'A weight-based dose could not be calculated.',
            }), 400

        result['medicine_name'] = medicine.name if medicine else None
        result['patient_name'] = '%s %s' % (patient.first_name, patient.last_name)
        result['summary'] = WeightDoser.describe(result)
        return jsonify({'success': True, 'data': result})

    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400


@recommender_bp.route('/dose-formulas', methods=['POST'])
def dose_formulas():
    """
    Compute *every* published formula for a patient/medicine pair at once.

    Why a separate endpoint: the prescriber often wants to see the alternatives
    side by side rather than accept the automatic choice - a per-kg dose, the
    BSA working, the Clark scaled adult dose and the age band disagree, and that
    disagreement is clinically useful. Crucially, a formula that cannot be
    applied (Clark with no weight, for example) is returned with a ``usable``
    flag and an explicit reason rather than being omitted, so the UI can disable
    it and say why instead of silently hiding an option.

    Body:
        patient_id          required
        medicine_id         must exist
        mg_per_kg / adult_mg / max_mg / dose_per_m2   optional overrides
        doses_per_day       for the daily ceiling check
        combine             when true, add a 'combined' block reporting the
                            agreement between every usable formula
    """
    try:
        from app.services.weight_dosing_service import WeightDoser
        data = request.get_json() or {}

        patient = Patient.query.get(data.get('patient_id'))
        if not patient:
            return jsonify({'success': False,
                            'error': 'Patient not found.'}), 404

        medicine = Medicine.query.get(data.get('medicine_id'))
        if not medicine:
            return jsonify({'success': False,
                            'error': 'Medicine not found.'}), 404

        from app.services.dosage_service import ADULT_REFERENCE_DOSE
        key = (medicine.generic_name or '').strip().lower()
        reference = dict(ADULT_REFERENCE_DOSE.get(key) or {})
        for field in ('mg_per_kg', 'adult_mg', 'max_mg', 'dose_per_m2'):
            if data.get(field) not in (None, ''):
                reference[field] = float(data[field])

        doses_per_day = int(data.get('doses_per_day') or 1)
        daily_ceiling = None
        try:
            from app.services.safety_service import SafetyEngine
            daily_ceiling = SafetyEngine.max_daily_dose(medicine)
        except Exception:
            daily_ceiling = None

        formulas = WeightDoser.all_formulas(
            patient,
            reference,
            bsa_dose_per_m2=reference.get('dose_per_m2'),
            doses_per_day=doses_per_day,
            max_daily_dose_mg=daily_ceiling,
        )

        payload = {
            'patient_id': patient.id,
            'patient_name': '%s %s' % (patient.first_name, patient.last_name),
            'medicine_id': medicine.id,
            'medicine_name': medicine.name,
            'weight_kg': getattr(patient, 'weight_kg', None),
            'height_cm': getattr(patient, 'height_cm', None),
            'bsa_m2': patient.bsa_m2,
            'age_years': patient.age,
            'age_months': getattr(patient, 'age_months', None),
            'doses_per_day': doses_per_day,
            'total_stock': 0,
            'formulas': formulas,
        }

        if data.get('combine'):
            payload['combined'] = WeightDoser.combine(
                formulas, doses_per_day=doses_per_day
            )

        return jsonify({'success': True, 'data': payload})

    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400


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

    The response also carries whatever the local formulary already holds for
    the same ingredient. That matters for an Indian pharmacy: openFDA covers
    FDA-approved products, so a molecule marketed here but not in the United
    States simply has no label to fetch. Returning the local monograph alongside
    means the screen is never empty for a drug the application already knows
    about, and the pharmacist can see the two side by side rather than being
    told "not found" about a medicine sitting in their own database.

    Returns the monograph plus its source. This is reference material, never a
    recommendation, and it is deliberately not fed into the ranking engine.
    """
    try:
        from app.services.live_reference_service import LiveReference

        force = request.args.get('refresh') == '1'
        payload, error = LiveReference.fetch_monograph(drug_name, force=force)

        # Whatever is authored locally for this ingredient, matched on the
        # generic name so a brand search still finds the local row.
        local = Medicine.query.filter(
            (Medicine.generic_name.ilike('%' + drug_name + '%'))
            | (Medicine.name.ilike('%' + drug_name + '%'))
        ).first()
        local_summary = None
        if local:
            local_summary = {
                'medicine_id': local.id,
                'name': local.name,
                'generic_name': local.generic_name,
                'use_case': local.use_case,
                'contraindications': local.contraindications,
                'warnings': local.warnings,
                'drug_interactions': local.drug_interactions,
                'side_effects': local.side_effects,
                'max_daily_dose': local.max_daily_dose,
                'schedule_classification': local.schedule_classification,
            }

        if error:
            # A local monograph is still a genuine answer even when the network
            # is unreachable, so it is returned with the error rather than
            # discarded. The caller can show what is known and say the optional
            # part failed - which is not the same as "no information".
            return jsonify({
                'success': False,
                'error': error,
                'local_monograph': local_summary,
                'offline_note': ('The application works fully offline. This '
                                 'optional lookup is the only feature that '
                                 'uses the network.'),
            }), 503

        if isinstance(payload, dict):
            payload['local_monograph'] = local_summary
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
