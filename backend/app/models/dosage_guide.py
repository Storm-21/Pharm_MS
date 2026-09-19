from app import db
from datetime import datetime

class DosageGuide(db.Model):
    __tablename__ = 'dosage_guides'
    
    id = db.Column(db.Integer, primary_key=True)
    medicine_id = db.Column(db.Integer, db.ForeignKey('medicines.id'), nullable=False)
    
    # Age groups
    age_group = db.Column(db.String(50), nullable=False)  # e.g., "0-2", "2-6", "6-12", "12-18", "18+"
    
    # Dosage information
    dosage_amount = db.Column(db.Float, nullable=False)
    dosage_unit = db.Column(db.String(50), nullable=False)  # mg, ml, etc.
    frequency = db.Column(db.String(100), nullable=False)  # times per day
    
    # Duration
    duration_days = db.Column(db.Integer, nullable=False)
    
    # Additional info
    indication = db.Column(db.String(200), nullable=False)  # What condition it's for
    special_notes = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'medicine_id': self.medicine_id,
            'age_group': self.age_group,
            'dosage_amount': self.dosage_amount,
            'dosage_unit': self.dosage_unit,
            'frequency': self.frequency,
            'duration_days': self.duration_days,
            'indication': self.indication,
            'special_notes': self.special_notes,
        }
    
    def __repr__(self):
        return f'<DosageGuide {self.id}>'
