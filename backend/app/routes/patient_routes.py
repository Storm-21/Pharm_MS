from flask import Blueprint, request, jsonify
from app import db
from app.models import Patient, PatientAllergy
from datetime import datetime

patient_bp = Blueprint('patients', __name__, url_prefix='/api/patients')

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
    """Create new patient"""
    try:
        data = request.get_json()
        
        patient = Patient(
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data.get('email'),
            phone=data.get('phone'),
            date_of_birth=datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date(),
            gender=data['gender'],
            chronic_diseases=data.get('chronic_diseases'),
            current_medications=data.get('current_medications'),
            allergies_description=data.get('allergies_description'),
            address=data.get('address'),
            city=data.get('city'),
            country=data.get('country'),
        )
        
        db.session.add(patient)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Patient created successfully',
            'data': patient.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@patient_bp.route('/<int:patient_id>', methods=['PUT'])
def update_patient(patient_id):
    """Update patient details"""
    try:
        patient = Patient.query.get_or_404(patient_id)
        data = request.get_json()
        
        for key, value in data.items():
            if key == 'date_of_birth' and value:
                value = datetime.strptime(value, '%Y-%m-%d').date()
            if hasattr(patient, key):
                setattr(patient, key, value)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Patient updated successfully',
            'data': patient.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
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
