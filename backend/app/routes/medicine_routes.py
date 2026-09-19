from flask import Blueprint, request, jsonify
from app import db
from app.models import Medicine, Inventory
from app.services import DosageCalculator, InteractionChecker

medicine_bp = Blueprint('medicines', __name__, url_prefix='/api/medicines')

@medicine_bp.route('', methods=['GET'])
def get_medicines():
    """Get all medicines with optional search"""
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = Medicine.query
    
    if search:
        query = query.filter(
            (Medicine.name.ilike(f"%{search}%")) |
            (Medicine.generic_name.ilike(f"%{search}%")) |
            (Medicine.brand_name.ilike(f"%{search}%"))
        )
    
    paginated = query.paginate(page=page, per_page=per_page)
    
    return jsonify({
        'success': True,
        'data': [med.to_dict() for med in paginated.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': paginated.total,
            'pages': paginated.pages
        }
    })

@medicine_bp.route('/<int:medicine_id>', methods=['GET'])
def get_medicine(medicine_id):
    """Get medicine details"""
    medicine = Medicine.query.get_or_404(medicine_id)
    
    data = medicine.to_dict()
    data['inventory'] = [inv.to_dict() for inv in medicine.inventory]
    data['dosage_guides'] = [guide.to_dict() for guide in medicine.dosage_guides]
    
    return jsonify({
        'success': True,
        'data': data
    })

@medicine_bp.route('', methods=['POST'])
def create_medicine():
    """Create new medicine"""
    try:
        data = request.get_json()
        
        medicine = Medicine(
            name=data['name'],
            generic_name=data['generic_name'],
            brand_name=data.get('brand_name'),
            manufacturer=data['manufacturer'],
            country_origin=data.get('country_origin'),
            salt_composition=data['salt_composition'],
            strength=data['strength'],
            form=data['form'],
            use_case=data['use_case'],
            side_effects=data.get('side_effects'),
            contraindications=data.get('contraindications'),
            drug_interactions=data.get('drug_interactions'),
            cost_price=data['cost_price'],
            selling_price=data['selling_price'],
            requires_prescription=data.get('requires_prescription', True),
            storage_temp=data.get('storage_temp'),
        )
        
        db.session.add(medicine)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Medicine created successfully',
            'data': medicine.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@medicine_bp.route('/<int:medicine_id>', methods=['PUT'])
def update_medicine(medicine_id):
    """Update medicine details"""
    try:
        medicine = Medicine.query.get_or_404(medicine_id)
        data = request.get_json()
        
        for key, value in data.items():
            if hasattr(medicine, key):
                setattr(medicine, key, value)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Medicine updated successfully',
            'data': medicine.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@medicine_bp.route('/<int:medicine_id>', methods=['DELETE'])
def delete_medicine(medicine_id):
    """Delete medicine"""
    try:
        medicine = Medicine.query.get_or_404(medicine_id)
        db.session.delete(medicine)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Medicine deleted successfully'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@medicine_bp.route('/search/by-condition', methods=['GET'])
def search_by_condition():
    """Search medicines by condition/use case"""
    condition = request.args.get('condition', '')
    
    medicines = Medicine.query.filter(
        Medicine.use_case.ilike(f"%{condition}%")
    ).all()
    
    return jsonify({
        'success': True,
        'data': [med.to_dict() for med in medicines]
    })
