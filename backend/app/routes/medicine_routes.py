import os

from flask import Blueprint, request, jsonify, send_file
from app import db
from app.models import Medicine, Inventory
from app.services import DosageCalculator, InteractionChecker
from app.services import medicine_image_service

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
    # Image state travels with the record so the detail view can render the
    # pack shot, its credit line and whether fetching is even allowed, in one
    # round trip rather than three.
    data['image'] = medicine_image_service.image_status(medicine, _data_dir())

    return jsonify({
        'success': True,
        'data': data
    })


def _data_dir():
    """Directory holding the database, used for storing medicine images."""
    return os.path.dirname(os.path.abspath(db.engine.url.database))


@medicine_bp.route('/<int:medicine_id>/image', methods=['GET'])
def get_medicine_image(medicine_id):
    """
    Serve a medicine's stored image.

    Falls back to 404 rather than a placeholder so the UI can tell "no image on
    file" apart from "image failed to load" - the first is normal and gets a
    tidy empty state, the second is a bug worth seeing.
    """
    medicine = Medicine.query.get_or_404(medicine_id)
    path = medicine_image_service.image_path(_data_dir(), medicine.image_filename)
    if not path:
        return jsonify({'success': False, 'error': 'No image on file.'}), 404
    return send_file(path, max_age=0)


@medicine_bp.route('/<int:medicine_id>/image', methods=['POST'])
def upload_medicine_image(medicine_id):
    """Upload a pack shot for a medicine."""
    try:
        medicine = Medicine.query.get_or_404(medicine_id)
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file was uploaded.'}), 400
        ok, message, stored = medicine_image_service.save_upload(
            medicine, request.files['file'], _data_dir())
        if ok:
            db.session.commit()
        else:
            db.session.rollback()
        return jsonify({
            'success': ok,
            'message': message,
            'error': None if ok else message,
            'data': medicine_image_service.image_status(medicine, _data_dir()),
        }), (200 if ok else 400)
    except Exception as exc:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(exc)}), 400


@medicine_bp.route('/<int:medicine_id>/image', methods=['DELETE'])
def delete_medicine_image(medicine_id):
    """Remove a medicine's pack shot."""
    try:
        medicine = Medicine.query.get_or_404(medicine_id)
        ok, message = medicine_image_service.remove_image(medicine, _data_dir())
        db.session.commit()
        return jsonify({'success': ok, 'message': message})
    except Exception as exc:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(exc)}), 400


@medicine_bp.route('/<int:medicine_id>/image/fetch', methods=['POST'])
def fetch_medicine_image(medicine_id):
    """
    Look the medicine up on the web and store the result locally.

    Opt-in and one-off: it runs when asked, writes the image to this machine, and
    every later view reads from disk. Only the drug's generic name is sent.
    """
    try:
        medicine = Medicine.query.get_or_404(medicine_id)
        payload = request.get_json(silent=True) or {}
        ok, message, stored = medicine_image_service.fetch_from_web(
            medicine, _data_dir(), query=payload.get('query'))
        if ok:
            db.session.commit()
        else:
            db.session.rollback()
        return jsonify({
            'success': ok,
            'message': message,
            'error': None if ok else message,
            'data': medicine_image_service.image_status(medicine, _data_dir()),
        }), (200 if ok else 400)
    except Exception as exc:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(exc)}), 400

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
