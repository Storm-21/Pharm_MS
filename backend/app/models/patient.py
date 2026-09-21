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
    
    # --- Clinical measurements needed for safe dosing -----------------------
    # Weight is the basis of every paediatric mg/kg calculation, so a dose
    # cannot be called "weight-based" without it. Stored in kilograms; the
    # app never guesses a value it does not have.
    weight_kg = db.Column(db.Float, nullable=True)
    # Serum creatinine in mg/dL, used to estimate eGFR (CKD-EPI 2021).
    serum_creatinine = db.Column(db.Float, nullable=True)
    # Hepatic impairment flag - many drugs are contraindicated in severe
    # liver disease and the label wording alone rarely captures the degree.
    hepatic_impairment = db.Column(db.Boolean, default=False, nullable=True)
    # Renal impairment flag, set automatically when eGFR is low and available
    # for clinicians who only know the diagnosis, not the exact creatinine.
    renal_impairment = db.Column(db.Boolean, default=False, nullable=True)
    # Pregnancy / lactation. These gate a large number of contraindications
    # that would otherwise be missed entirely.
    is_pregnant = db.Column(db.Boolean, default=False, nullable=True)
    pregnancy_trimester = db.Column(db.Integer, nullable=True)  # 1, 2 or 3
    is_breastfeeding = db.Column(db.Boolean, default=False, nullable=True)

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

    @property
    def age_months(self):
        """Completed months of age - needed for infant dosing, where a rounded
        year count would be clinically useless (a 1-month-old and a 1-year-old
        are not the same patient)."""
        from datetime import date
        today = date.today()
        months = (today.year - self.date_of_birth.year) * 12 \
            + (today.month - self.date_of_birth.month)
        if today.day < self.date_of_birth.day:
            months -= 1
        return max(0, months)

    @property
    def bsa_m2(self):
        """Body surface area in m^2 (Mosteller formula).

        BSA = sqrt(height_cm x weight_kg / 3600). Height is not captured, so
        this returns None unless a weight is on file; callers must treat a
        missing BSA as "cannot calculate", never as zero.
        """
        if not self.weight_kg or self.weight_kg <= 0:
            return None
        # Without a recorded height, fall back to an average adult height so
        # BSA remains usable; the caller labels the result as an estimate.
        assumed_height = 165.0 if self.age >= 18 else (100.0 + self.age * 6)
        import math
        return round(math.sqrt(assumed_height * self.weight_kg / 3600.0), 3)

    @property
    def egfr(self):
        """Estimated glomerular filtration rate (CKD-EPI 2021, creatinine).

        Returns None when the inputs are missing. A drug whose dose depends on
        renal function must be refused rather than dosed blindly when this is
        None - see the safety engine.
        """
        if not self.serum_creatinine or self.serum_creatinine <= 0:
            return None
        import math
        female = (self.gender or '').strip().lower().startswith('f')
        scr = self.serum_creatinine
        k = 0.7 if female else 0.9
        a = -0.241 if female else -0.302
        age = self.age
        ratio = scr / k
        return round(
            142 * (min(ratio, 1) ** a) * (max(ratio, 1) ** -1.200)
            * (0.9938 ** age) * (1.012 if female else 1.0),
            1,
        )

    @property
    def ckd_stage(self):
        """KDIGO GFR category, or None when eGFR cannot be computed."""
        gfr = self.egfr
        if gfr is None:
            return None
        if gfr >= 90:
            return 'G1 (normal or high)'
        if gfr >= 60:
            return 'G2 (mildly decreased)'
        if gfr >= 45:
            return 'G3a (mild to moderately decreased)'
        if gfr >= 30:
            return 'G3b (moderately to severely decreased)'
        if gfr >= 15:
            return 'G4 (severely decreased)'
        return 'G5 (kidney failure)'
    
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
            'weight_kg': self.weight_kg,
            'serum_creatinine': self.serum_creatinine,
            'hepatic_impairment': bool(self.hepatic_impairment),
            'renal_impairment': bool(self.renal_impairment),
            'is_pregnant': bool(self.is_pregnant),
            'pregnancy_trimester': self.pregnancy_trimester,
            'is_breastfeeding': bool(self.is_breastfeeding),
            'egfr': self.egfr,
            'ckd_stage': self.ckd_stage,
            'bsa_m2': self.bsa_m2,
            'age_months': self.age_months,
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
