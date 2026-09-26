from app import db
from app.crypto import EncryptedString, EncryptedText
from datetime import datetime

class Patient(db.Model):
    __tablename__ = 'patients'

    id = db.Column(db.Integer, primary_key=True)
    # first_name and last_name deliberately stay plaintext: the app searches
    # patients BY NAME with SQL LIKE, and a printed prescription needs to find
    # a patient by name without decrypting every row. Names are also what the
    # unique email constraint and every report join on. The sensitive contact
    # and medical fields below ARE encrypted - see app/crypto.py.
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    # Encrypted at rest. Note: SQL LIKE search no longer matches these fields,
    # because the database sees ciphertext; that is the point.
    phone = db.Column(EncryptedString(40), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(10), nullable=False)  # Male, Female, Other

    # Medical conditions - encrypted, these are the most sensitive fields here
    chronic_diseases = db.Column(EncryptedText, nullable=True)  # Comma-separated: Diabetes, Hypertension, etc.
    current_medications = db.Column(EncryptedText, nullable=True)
    allergies_description = db.Column(EncryptedText, nullable=True)

    # --- Clinical measurements needed for safe dosing -----------------------
    # Weight is the basis of every paediatric mg/kg calculation, so a dose
    # cannot be called "weight-based" without it. Stored in kilograms; the
    # app never guesses a value it does not have.
    weight_kg = db.Column(db.Float, nullable=True)
    # Height in cm. Optional, but when supplied it makes BSA (Mosteller) and BMI
    # exact instead of estimated, and lets mg/m2 chemotherapy-style dosing be
    # computed properly.
    height_cm = db.Column(db.Float, nullable=True)
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

    # Contact info - encrypted
    address = db.Column(EncryptedText, nullable=True)
    city = db.Column(EncryptedString(150), nullable=True)
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

        BSA = sqrt(height_cm x weight_kg / 3600). When no height is recorded an
        average is assumed so the figure is still usable; callers must label the
        result as an estimate in that case. Returns None when there is no weight
        at all - a missing BSA means "cannot calculate", never zero.
        """
        if not self.weight_kg or self.weight_kg <= 0:
            return None
        import math
        return round(
            math.sqrt(self.assumed_height_cm * self.weight_kg / 3600.0), 3)

    @property
    def bmi(self):
        """Body mass index, or None when weight or height cannot be established.

        BMI is not used for dosing - doses are per kg of body weight - but it is
        a recognised flag for weight extremes, and an adult at either end of the
        scale often needs a dose adjusted for actual or ideal body weight rather
        than the raw number. Reporting it keeps that judgement visible.
        """
        if not self.weight_kg or self.weight_kg <= 0:
            return None
        height_m = self.assumed_height_cm / 100.0
        if height_m <= 0:
            return None
        return round(self.weight_kg / (height_m ** 2), 1)

    @property
    def assumed_height_cm(self):
        """Height in cm - the recorded value when present, else an estimate.

        Height is not captured on the form, so this falls back to an average
        adult height (or a rough age-based figure for a child) purely so BSA and
        BMI can be produced. Callers that clinically depend on height must say
        the value is estimated rather than measured.
        """
        if self.height_cm and self.height_cm > 0:
            return self.height_cm
        if self.age >= 18:
            return 165.0
        # Child height grows roughly linearly with age until the pubertal
        # spurt; this is a deliberate approximation, flagged as such.
        return 100.0 + self.age * 6

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
            'height_cm': self.height_cm,
            'bmi': self.bmi,
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
