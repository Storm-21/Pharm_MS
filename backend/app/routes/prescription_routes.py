from flask import Blueprint, request, jsonify
from app import db
from app.models import Prescription, PrescriptionItem, Medicine, Patient
from app.models.prescription import parse_dose_schedule
from datetime import datetime

prescription_bp = Blueprint('prescriptions', __name__, url_prefix='/api/prescriptions')

@prescription_bp.route('', methods=['GET'])
def get_prescriptions():
    """Get all prescriptions"""
    patient_id = request.args.get('patient_id', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = Prescription.query
    
    if patient_id:
        query = query.filter_by(patient_id=patient_id)
    
    paginated = query.order_by(Prescription.created_at.desc()).paginate(page=page, per_page=per_page)
    
    return jsonify({
        'success': True,
        'data': [prescription.to_dict() for prescription in paginated.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': paginated.total,
            'pages': paginated.pages
        }
    })

@prescription_bp.route('/<int:prescription_id>', methods=['GET'])
def get_prescription(prescription_id):
    """Get prescription details"""
    prescription = Prescription.query.get_or_404(prescription_id)
    
    return jsonify({
        'success': True,
        'data': prescription.to_dict()
    })

@prescription_bp.route('', methods=['POST'])
def create_prescription():
    """Create new prescription"""
    try:
        data = request.get_json()
        patient = Patient.query.get_or_404(data['patient_id'])
        
        prescription = Prescription(
            patient_id=data['patient_id'],
            doctor_name=data['doctor_name'],
            diagnosis=data['diagnosis'],
            notes=data.get('notes'),
            valid_until=datetime.strptime(data['valid_until'], '%Y-%m-%d') if data.get('valid_until') else None,
        )
        
        db.session.add(prescription)
        db.session.flush()
        
        # Add prescription items
        for item_data in data.get('items', []):
            medicine = Medicine.query.get_or_404(item_data['medicine_id'])
            
            # The dosing pattern is validated before it is stored. A pattern
            # that is not three hyphen-separated slots is refused rather than
            # saved, because a malformed pattern printed on a sheet is a
            # mis-read dose - and it would be the patient who acts on it.
            schedule = item_data.get('dose_schedule')
            if schedule and not parse_dose_schedule(schedule):
                return jsonify({
                    'success': False,
                    'error': ('Dose schedule "%s" is not a valid pattern. Use '
                              'three hyphen-separated values in the order '
                              'morning-midday-night, for example 0-0-1 or '
                              '1-1/2-0.' % schedule),
                }), 400

            item = PrescriptionItem(
                prescription_id=prescription.id,
                medicine_id=item_data['medicine_id'],
                dosage_amount=item_data['dosage_amount'],
                dosage_unit=item_data['dosage_unit'],
                frequency=item_data['frequency'],
                duration_days=item_data['duration_days'],
                special_instructions=item_data.get('special_instructions'),
                dose_schedule=schedule,
                dispensed_units=item_data.get('dispensed_units'),
            )

            db.session.add(item)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Prescription created successfully',
            'data': prescription.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@prescription_bp.route('/<int:prescription_id>', methods=['PUT'])
def update_prescription(prescription_id):
    """Update prescription"""
    try:
        prescription = Prescription.query.get_or_404(prescription_id)
        data = request.get_json()

        prescription.doctor_name = data.get('doctor_name', prescription.doctor_name)
        prescription.diagnosis = data.get('diagnosis', prescription.diagnosis)
        prescription.notes = data.get('notes', prescription.notes)

        if data.get('valid_until'):
            prescription.valid_until = datetime.strptime(data['valid_until'], '%Y-%m-%d')

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Prescription updated successfully',
            'data': prescription.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@prescription_bp.route('/<int:prescription_id>', methods=['DELETE'])
def delete_prescription(prescription_id):
    """Delete prescription"""
    try:
        prescription = Prescription.query.get_or_404(prescription_id)
        db.session.delete(prescription)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Prescription deleted successfully'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@prescription_bp.route('/<int:prescription_id>/items', methods=['POST'])
def add_prescription_item(prescription_id):
    """Add item to prescription"""
    try:
        prescription = Prescription.query.get_or_404(prescription_id)
        data = request.get_json()

        item = PrescriptionItem(
            prescription_id=prescription_id,
            medicine_id=data['medicine_id'],
            dosage_amount=data['dosage_amount'],
            dosage_unit=data['dosage_unit'],
            frequency=data['frequency'],
            duration_days=data['duration_days'],
            special_instructions=data.get('special_instructions'),
            dose_schedule=data.get('dose_schedule'),
            dispensed_units=data.get('dispensed_units'),
        )
        
        db.session.add(item)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Item added to prescription',
            'data': item.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@prescription_bp.route('/items/<int:item_id>', methods=['DELETE'])
def remove_prescription_item(item_id):
    """Remove item from prescription"""
    try:
        item = PrescriptionItem.query.get_or_404(item_id)
        db.session.delete(item)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Item removed from prescription'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
