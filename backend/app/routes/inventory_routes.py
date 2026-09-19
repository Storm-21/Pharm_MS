from flask import Blueprint, request, jsonify
from app import db
from app.models import Inventory, Medicine
from datetime import date

inventory_bp = Blueprint('inventory', __name__, url_prefix='/api/inventory')

@inventory_bp.route('', methods=['GET'])
def get_inventory():
    """Get all inventory items"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status')  # in_stock, low_stock, out_of_stock, expired
    
    query = Inventory.query
    
    if status:
        if status == 'low_stock':
            query = query.filter(Inventory.quantity_in_stock <= Inventory.reorder_level)
        elif status == 'out_of_stock':
            query = query.filter(Inventory.quantity_in_stock == 0)
        elif status == 'expired':
            query = query.filter(Inventory.expiry_date <= date.today())
    
    paginated = query.paginate(page=page, per_page=per_page)
    
    return jsonify({
        'success': True,
        'data': [inv.to_dict() for inv in paginated.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': paginated.total,
            'pages': paginated.pages
        }
    })

@inventory_bp.route('/<int:inventory_id>', methods=['GET'])
def get_inventory_item(inventory_id):
    """Get specific inventory item"""
    item = Inventory.query.get_or_404(inventory_id)
    
    return jsonify({
        'success': True,
        'data': item.to_dict()
    })

@inventory_bp.route('', methods=['POST'])
def create_inventory():
    """Add new inventory item"""
    try:
        data = request.get_json()
        medicine = Medicine.query.get_or_404(data['medicine_id'])
        
        # Check if inventory already exists for this medicine and batch
        existing = Inventory.query.filter_by(
            medicine_id=data['medicine_id'],
            batch_number=data['batch_number']
        ).first()
        
        if existing:
            return jsonify({
                'success': False,
                'error': 'Inventory item with this batch number already exists'
            }), 400
        
        from datetime import datetime
        inventory = Inventory(
            medicine_id=data['medicine_id'],
            quantity_in_stock=data['quantity_in_stock'],
            reorder_level=data.get('reorder_level', 20),
            max_stock=data.get('max_stock', 500),
            batch_number=data['batch_number'],
            manufacturing_date=datetime.strptime(data['manufacturing_date'], '%Y-%m-%d').date(),
            expiry_date=datetime.strptime(data['expiry_date'], '%Y-%m-%d').date(),
            storage_location=data.get('storage_location'),
        )
        
        db.session.add(inventory)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Inventory item created successfully',
            'data': inventory.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@inventory_bp.route('/<int:inventory_id>', methods=['PUT'])
def update_inventory(inventory_id):
    """Update inventory item"""
    try:
        item = Inventory.query.get_or_404(inventory_id)
        data = request.get_json()
        
        if 'quantity_in_stock' in data:
            item.quantity_in_stock = data['quantity_in_stock']
        if 'reorder_level' in data:
            item.reorder_level = data['reorder_level']
        if 'max_stock' in data:
            item.max_stock = data['max_stock']
        if 'storage_location' in data:
            item.storage_location = data['storage_location']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Inventory updated successfully',
            'data': item.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@inventory_bp.route('/<int:inventory_id>/update-stock', methods=['PUT'])
def update_stock(inventory_id):
    """Update stock quantity (add or remove)"""
    try:
        item = Inventory.query.get_or_404(inventory_id)
        data = request.get_json()
        
        quantity_change = data.get('quantity_change', 0)
        item.quantity_in_stock += quantity_change
        
        if item.quantity_in_stock < 0:
            item.quantity_in_stock = 0
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Stock updated by {quantity_change}',
            'data': item.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@inventory_bp.route('/summary', methods=['GET'])
def get_inventory_summary():
    """Aggregate stock position: counts by status plus stock value."""
    items = Inventory.query.all()

    counts = {'in_stock': 0, 'low_stock': 0, 'out_of_stock': 0, 'expired': 0}
    cost_value = 0.0
    retail_value = 0.0
    for item in items:
        status = item.status
        if status in counts:
            counts[status] += 1
        # Value uses the quantity on hand at that batch's medicine pricing.
        if item.medicine:
            cost_value += item.quantity_in_stock * (item.medicine.cost_price or 0)
            retail_value += item.quantity_in_stock * (item.medicine.selling_price or 0)

    return jsonify({
        'success': True,
        'data': {
            'total_lines': len(items),
            'counts': counts,
            'total_units': sum(i.quantity_in_stock for i in items),
            'stock_value_at_cost': round(cost_value, 2),
            'stock_value_at_retail': round(retail_value, 2),
            'potential_margin': round(retail_value - cost_value, 2),
        }
    })

@inventory_bp.route('/alerts', methods=['GET'])
def get_stock_alerts():
    """Get low stock and expired medicine alerts"""
    from app.services import InventoryOptimizer
    
    alerts = InventoryOptimizer.get_stock_alerts()
    
    return jsonify({
        'success': True,
        'data': alerts
    })

@inventory_bp.route('/medicine/<int:medicine_id>', methods=['GET'])
def get_medicine_inventory(medicine_id):
    """Get all inventory for a specific medicine"""
    medicine = Medicine.query.get_or_404(medicine_id)
    
    inventory_items = Inventory.query.filter_by(medicine_id=medicine_id).all()
    
    return jsonify({
        'success': True,
        'medicine_name': medicine.name,
        'total_stock': sum(inv.quantity_in_stock for inv in inventory_items),
        'data': [inv.to_dict() for inv in inventory_items]
    })

@inventory_bp.route('/<int:inventory_id>', methods=['DELETE'])
def delete_inventory(inventory_id):
    """Delete inventory item"""
    try:
        item = Inventory.query.get_or_404(inventory_id)
        db.session.delete(item)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Inventory item deleted successfully'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
