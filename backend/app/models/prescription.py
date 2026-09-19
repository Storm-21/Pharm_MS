from app import db
from datetime import datetime

class Prescription(db.Model):
    __tablename__ = 'prescriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_name = db.Column(db.String(150), nullable=False)
    diagnosis = db.Column(db.Text, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    valid_until = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    items = db.relationship('PrescriptionItem', backref='prescription', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'doctor_name': self.doctor_name,
            'diagnosis': self.diagnosis,
            'notes': self.notes,
            'created_at': self.created_at.isoformat(),
            'valid_until': self.valid_until.isoformat() if self.valid_until else None,
            'items': [item.to_dict() for item in self.items],
        }
    
    def __repr__(self):
        return f'<Prescription {self.id}>'


class PrescriptionItem(db.Model):
    __tablename__ = 'prescription_items'
    
    id = db.Column(db.Integer, primary_key=True)
    prescription_id = db.Column(db.Integer, db.ForeignKey('prescriptions.id'), nullable=False)
    medicine_id = db.Column(db.Integer, db.ForeignKey('medicines.id'), nullable=False)
    
    # Dosage information
    dosage_amount = db.Column(db.Float, nullable=False)  # Amount to take per dose
    dosage_unit = db.Column(db.String(50), nullable=False)  # e.g., mg, ml, units
    frequency = db.Column(db.String(100), nullable=False)  # e.g., "3 times a day", "Twice daily"
    duration_days = db.Column(db.Integer, nullable=False)
    
    # Instructions
    special_instructions = db.Column(db.Text, nullable=True)  # e.g., "Take with food"
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'medicine_id': self.medicine_id,
            'medicine_name': self.medicine.name if self.medicine else None,
            'dosage_amount': self.dosage_amount,
            'dosage_unit': self.dosage_unit,
            'frequency': self.frequency,
            'duration_days': self.duration_days,
            'special_instructions': self.special_instructions,
        }
    
    def __repr__(self):
        return f'<PrescriptionItem {self.id}>'
