from app import db
from datetime import datetime

class Inventory(db.Model):
    __tablename__ = 'inventory'
    
    id = db.Column(db.Integer, primary_key=True)
    medicine_id = db.Column(db.Integer, db.ForeignKey('medicines.id'), nullable=False)
    
    # Stock information
    quantity_in_stock = db.Column(db.Integer, nullable=False, default=0)
    reorder_level = db.Column(db.Integer, nullable=False, default=20)
    max_stock = db.Column(db.Integer, nullable=False, default=500)
    
    # Batch information
    batch_number = db.Column(db.String(100), nullable=False)
    manufacturing_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    
    # Location
    storage_location = db.Column(db.String(100), nullable=True)  # e.g., "Shelf A1"
    
    # Tracking
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'medicine_id': self.medicine_id,
            'medicine_name': self.medicine.name if self.medicine else None,
            'quantity_in_stock': self.quantity_in_stock,
            'reorder_level': self.reorder_level,
            'max_stock': self.max_stock,
            'batch_number': self.batch_number,
            'manufacturing_date': self.manufacturing_date.isoformat() if self.manufacturing_date else None,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'storage_location': self.storage_location,
            'status': self.status,
        }
    
    @property
    def status(self):
        from datetime import date
        if self.quantity_in_stock <= 0:
            return 'out_of_stock'
        elif self.quantity_in_stock <= self.reorder_level:
            return 'low_stock'
        elif self.expiry_date and self.expiry_date <= date.today():
            return 'expired'
        else:
            return 'in_stock'
    
    def __repr__(self):
        return f'<Inventory {self.id}>'
