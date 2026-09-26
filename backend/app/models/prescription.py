from app import db
from app.crypto import EncryptedText
from datetime import datetime

class Prescription(db.Model):
    __tablename__ = 'prescriptions'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_name = db.Column(db.String(150), nullable=False)
    # Diagnosis and notes are the clinical story of a named patient, so they
    # are encrypted at rest. doctor_name stays readable: it is a practitioner's
    # public registration detail, printed on every prescription.
    diagnosis = db.Column(EncryptedText, nullable=False)
    notes = db.Column(EncryptedText, nullable=True)
    
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


# The three dosing slots a '0-0-1' pattern refers to. The notation is the one
# Indian prescribers write on a pad: three numbers separated by hyphens, in the
# order morning, midday, night.
DOSING_SLOTS = ('Morning', 'Midday', 'Night')

# How a fraction is written back out. '1/2' has to read as "half", because a
# leaflet that says "0.5" is not what a patient was told at the counter.
FRACTIONS = {
    '1/2': 'half', '0.5': 'half', '½': 'half',
    '1/4': 'quarter', '0.25': 'quarter', '¼': 'quarter',
    '3/4': 'three quarters', '0.75': 'three quarters', '¾': 'three quarters',
    '1 1/2': 'one and a half', '1.5': 'one and a half',
    '2': 'two', '3': 'three', '4': 'four',
    '1': 'one',
}


def parse_dose_schedule(value):
    """
    Validate a dosing pattern and return its three slots, or None.

    Accepts '0-0-1', '1-1/2-0', '1/2-0-1/2', and the same with spaces. A value
    that is not three hyphen-separated parts is rejected rather than guessed at,
    because a mis-read pattern is a mis-taken dose.
    """
    if not value:
        return None
    parts = [p.strip() for p in str(value).split('-')]
    if len(parts) != 3:
        return None
    return parts


def describe_dose_schedule(value):
    """
    Expand '1-0-1' into 'Morning: 1, Night: 1'.

    Returns None when the pattern is absent or malformed, so a caller shows the
    frequency text instead of printing something nonsensical.
    """
    parts = parse_dose_schedule(value)
    if not parts:
        return None
    taken = []
    for slot, amount in zip(DOSING_SLOTS, parts):
        if amount in ('', '0', '0.0', '-'):
            continue
        taken.append('%s: %s' % (slot, FRACTIONS.get(amount, amount)))
    if not taken:
        return None
    return ', '.join(taken)


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
    
    # --- The dosing pattern, as a prescriber writes it ---------------------
    # '0-0-1' is one dose at night; '1-0-1' is morning and night; '1-1/2-0' is
    # one in the morning and half at midday; '1/2-0-1/2' is half twice daily.
    #
    # This is the notation Indian prescribers actually use, and it is NOT
    # derivable from the frequency text: "twice daily" cannot tell you whether
    # the doses are morning-and-night or midday-and-night, and for a drug taken
    # at a specific time that difference matters. It is a separate field for
    # that reason, and it is what the printed sheet shows.
    dose_schedule = db.Column(db.String(40), nullable=True)

    # The quantity actually handed over, which is not always what the calculated
    # course implies - a part pack, a substitution - so it is recorded rather
    # than recomputed for the receipt.
    dispensed_units = db.Column(db.Integer, nullable=True)

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
            'dose_schedule': self.dose_schedule,
            'dispensed_units': self.dispensed_units,
            # The pattern expanded into words, so a caller does not have to
            # know the notation to display it.
            'dose_schedule_text': describe_dose_schedule(self.dose_schedule),
        }
    
    def __repr__(self):
        return f'<PrescriptionItem {self.id}>'
