from flask import Blueprint, request, jsonify
from app import db
from app.models import Patient, PatientAllergy
from datetime import datetime

patient_bp = Blueprint('patients', __name__, url_prefix='/api/patients')

# --- Field handling -------------------------------------------------------
#
# WHY THIS EXISTS
# ---------------
# The patient edit form is populated by spreading the whole record returned by
# the API over the blank form, so it submits computed values the server cannot
# store - ``age``, ``egfr``, ``ckd_stage``, ``bsa_m2``, ``age_months`` and the
# nested ``allergies`` list. Those are read-only @property attributes, and the
# old update loop did:
#
#     if hasattr(patient, key):
#         setattr(patient, key, value)
#
# ``hasattr`` is True for a property, so ``setattr`` ran and raised
# "property 'age' of 'Patient' object has no setter". The whole request 400'd,
# which is why editing an existing patient silently failed.
#
# The fix is to write only real, writable columns, to convert incoming values
# to the right Python type, and to treat an empty string as "not recorded".

# Columns a client may set. Everything else on the request body is ignored.
WRITABLE_TEXT_FIELDS = (
    'first_name', 'last_name', 'email', 'phone', 'gender',
    'chronic_diseases', 'current_medications', 'allergies_description',
    'address', 'city', 'country',
)
WRITABLE_FLOAT_FIELDS = ('weight_kg', 'height_cm', 'serum_creatinine')
WRITABLE_BOOL_FIELDS = (
    'hepatic_impairment', 'renal_impairment', 'is_pregnant', 'is_breastfeeding',
)


def _clean_text(value):
    """Trim strings; an all-whitespace field is stored as SQL NULL."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_float(value, field):
    """Parse a clinical number, or None when blank.

    A blank weight is *not* zero - the dosage calculator distinguishes "no
    weight recorded" from "0 kg" and falls back to an age formula, so an empty
    box must never become a 0 that would dose every child at nothing.
    """
    if value is None or value == '':
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError('%s must be a number.' % field)
    if number <= 0:
        raise ValueError('%s must be greater than zero.' % field)
    return number


def _parse_bool(value):
    """Accept real booleans, plus the string forms a form/JSON body sends."""
    if isinstance(value, bool):
        return value
    if value is None or value == '':
        return False
    return str(value).strip().lower() in ('1', 'true', 'yes', 'on')


def _parse_date(value, field='date_of_birth'):
    """Parse an ISO date, or raise a message the UI can show directly."""
    if value is None or str(value).strip() == '':
        raise ValueError('%s is required.' % field)
    if hasattr(value, 'date') and not isinstance(value, str):
        return value
    try:
        return datetime.strptime(str(value).strip()[:10], '%Y-%m-%d').date()
    except ValueError:
        raise ValueError('%s must be a date in YYYY-MM-DD format.' % field)


def _apply_patient_fields(patient, data):
    """Write the request body onto a Patient instance, field by field.

    Only whitelisted, writable columns are touched, so computed properties and
    unknown keys can never reach ``setattr``.
    """
    for field in WRITABLE_TEXT_FIELDS:
        if field in data:
            setattr(patient, field, _clean_text(data[field]))
    for field in WRITABLE_FLOAT_FIELDS:
        if field in data:
            setattr(patient, field, _parse_float(data[field], field))
    for field in WRITABLE_BOOL_FIELDS:
        if field in data:
            setattr(patient, field, _parse_bool(data[field]))
    if 'pregnancy_trimester' in data:
        value = data['pregnancy_trimester']
        if value is None or value == '':
            patient.pregnancy_trimester = None
        else:
            try:
                trimester = int(value)
            except (TypeError, ValueError):
                raise ValueError('pregnancy_trimester must be 1, 2 or 3.')
            if trimester not in (1, 2, 3):
                raise ValueError('pregnancy_trimester must be 1, 2 or 3.')
            patient.pregnancy_trimester = trimester
    if 'date_of_birth' in data:
        patient.date_of_birth = _parse_date(data['date_of_birth'])

@patient_bp.route('', methods=['GET'])
def get_patients():
    """Get all patients"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '')
    
    query = Patient.query
    
    if search:
        query = query.filter(
            (Patient.first_name.ilike(f"%{search}%")) |
            (Patient.last_name.ilike(f"%{search}%")) |
            (Patient.email.ilike(f"%{search}%")) |
            (Patient.phone.ilike(f"%{search}%"))
        )
    
    paginated = query.paginate(page=page, per_page=per_page)
    
    return jsonify({
        'success': True,
        'data': [patient.to_dict() for patient in paginated.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': paginated.total,
            'pages': paginated.pages
        }
    })

@patient_bp.route('/<int:patient_id>', methods=['GET'])
def get_patient(patient_id):
    """Get patient details"""
    patient = Patient.query.get_or_404(patient_id)
    
    return jsonify({
        'success': True,
        'data': patient.to_dict()
    })

@patient_bp.route('', methods=['POST'])
def create_patient():
    """Create new patient.

    Validates first, then writes only whitelisted columns. The previous version
    read required keys directly from the body, so a missing field raised a bare
    KeyError that surfaced as an opaque 400 in the UI.
    """
    try:
        data = request.get_json(silent=True) or {}

        first_name = _clean_text(data.get('first_name'))
        last_name = _clean_text(data.get('last_name'))
        gender = _clean_text(data.get('gender'))
        if not first_name:
            raise ValueError('First name is required.')
        if not last_name:
            raise ValueError('Last name is required.')
        if not gender:
            raise ValueError('Gender is required.')

        email = _clean_text(data.get('email'))
        # Email is UNIQUE in the schema. Catching this here turns a raw
        # IntegrityError into a sentence the pharmacist can act on.
        if email and Patient.query.filter(Patient.email == email).first():
            raise ValueError('A patient with the email %s already exists.' % email)

        patient = Patient()
        _apply_patient_fields(patient, data)

        db.session.add(patient)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Patient created successfully',
            'data': patient.to_dict()
        }), 201

    except ValueError as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Could not create the patient record: %s' % e
        }), 400

@patient_bp.route('/<int:patient_id>', methods=['PUT'])
def update_patient(patient_id):
    """Update patient details.

    This is the path the edit form uses. It used to iterate every key in the
    request body and setattr() anything the object had, which crashed with
    "property 'age' has no setter" because the form echoes back the computed
    age/egfr/bsa fields. Only whitelisted writable columns are applied now.
    """
    try:
        patient = Patient.query.get_or_404(patient_id)
        data = request.get_json(silent=True) or {}

        if 'email' in data:
            email = _clean_text(data['email'])
            if email:
                clash = Patient.query.filter(
                    Patient.email == email, Patient.id != patient_id).first()
                if clash:
                    raise ValueError(
                        'Another patient already uses the email %s.' % email)

        _apply_patient_fields(patient, data)

        # An update must leave a valid record behind, not blank out a name.
        if not _clean_text(patient.first_name):
            raise ValueError('First name is required.')
        if not _clean_text(patient.last_name):
            raise ValueError('Last name is required.')

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Patient updated successfully',
            'data': patient.to_dict()
        })

    except ValueError as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Could not update the patient record: %s' % e
        }), 400

@patient_bp.route('/<int:patient_id>', methods=['DELETE'])
def delete_patient(patient_id):
    """Delete patient and their cascading allergies/prescriptions."""
    try:
        patient = Patient.query.get_or_404(patient_id)
        db.session.delete(patient)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Patient deleted successfully'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
@patient_bp.route('/<int:patient_id>/profile', methods=['GET'])
def get_patient_profile(patient_id):
    """
    Everything the patient detail panel needs in one call: demographics,
    allergies, prescription history and condition-based suggestions.
    """
    from app.models import Prescription
    from app.services import MedicineRecommender
    patient = Patient.query.get_or_404(patient_id)

    prescriptions = (Prescription.query
                     .filter_by(patient_id=patient_id)
                     .order_by(Prescription.created_at.desc())
                     .all())

    # Suggest medicines for each recorded chronic condition the patient has no
    # known allergy to. Failures here must not break the profile response.
    condition_suggestions = []
    if patient.chronic_diseases:
        for condition in [c.strip() for c in patient.chronic_diseases.split(',') if c.strip()]:
            try:
                matches = MedicineRecommender.recommend_medicines(patient_id, condition, 'mild')
            except Exception:
                matches = []
            condition_suggestions.append({
                'condition': condition,
                'recommendations': matches[:3],
            })

    return jsonify({
        'success': True,
        'data': {
            'patient': patient.to_dict(),
            'allergies': [a.to_dict() for a in patient.allergies],
            'prescriptions': [p.to_dict() for p in prescriptions],
            'condition_suggestions': condition_suggestions,
            'stats': {
                'prescription_count': len(prescriptions),
                'allergy_count': len(patient.allergies),
                'condition_count': len([c for c in (patient.chronic_diseases or '').split(',') if c.strip()]),
            },
        }
    })

@patient_bp.route('/<int:patient_id>/allergies', methods=['GET'])
def get_patient_allergies(patient_id):
    """Get patient allergies"""
    patient = Patient.query.get_or_404(patient_id)
    
    return jsonify({
        'success': True,
        'data': [allergy.to_dict() for allergy in patient.allergies]
    })

@patient_bp.route('/<int:patient_id>/allergies', methods=['POST'])
def add_allergy(patient_id):
    """Add allergy to patient"""
    try:
        patient = Patient.query.get_or_404(patient_id)
        data = request.get_json()
        
        allergy = PatientAllergy(
            patient_id=patient_id,
            allergen=data['allergen'],
            reaction=data['reaction'],
            severity=data['severity']
        )
        
        db.session.add(allergy)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Allergy added successfully',
            'data': allergy.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@patient_bp.route('/<int:patient_id>/allergies/<int:allergy_id>', methods=['DELETE'])
def remove_allergy(patient_id, allergy_id):
    """Remove allergy from patient"""
    try:
        allergy = PatientAllergy.query.get_or_404(allergy_id)
        
        if allergy.patient_id != patient_id:
            return jsonify({
                'success': False,
                'error': 'Allergy does not belong to this patient'
            }), 403
        
        db.session.delete(allergy)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Allergy removed successfully'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
