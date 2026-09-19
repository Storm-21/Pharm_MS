from app import db
from datetime import datetime

class Patient(db.Model):
    __tablename__ = 'patients'
    
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(10), nullable=False)  # Male, Female, Other
    
    # Medical conditions
    chronic_diseases = db.Column(db.Text, nullable=True)  # Comma-separated: Diabetes, Hypertension, etc.
    current_medications = db.Column(db.Text, nullable=True)
    allergies_description = db.Column(db.Text, nullable=True)
    
    # Contact info
    address = db.Column(db.Text, nullable=True)
    city = db.Column(db.String(100), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    allergies = db.relationship('PatientAllergy', backref='patient', lazy=True, cascade='all, delete-orphan')
    prescriptions = db.relationship('Prescription', backref='patient', lazy=True, cascade='all, delete-orphan')
    
    @property
    def age(self):
        from datetime import date
        today = date.today()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
    
    def to_dict(self):
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'phone': self.phone,
            'date_of_birth': self.date_of_birth.isoformat() if self.date_of_birth else None,
            'gender': self.gender,
            'age': self.age,
            'chronic_diseases': self.chronic_diseases,
            'current_medications': self.current_medications,
            'allergies_description': self.allergies_description,
            'address': self.address,
            'city': self.city,
            'country': self.country,
            'allergies': [allergy.to_dict() for allergy in self.allergies],
        }
    
    def __repr__(self):
        return f'<Patient {self.first_name} {self.last_name}>'


class PatientAllergy(db.Model):
    __tablename__ = 'patient_allergies'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    allergen = db.Column(db.String(150), nullable=False)  # Medicine name or ingredient
    reaction = db.Column(db.Text, nullable=False)  # Description of allergic reaction
    severity = db.Column(db.String(20), nullable=False)  # Mild, Moderate, Severe
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'allergen': self.allergen,
            'reaction': self.reaction,
            'severity': self.severity,
        }
    
    def __repr__(self):
        return f'<PatientAllergy {self.allergen}>'
