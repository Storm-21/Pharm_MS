"""Verify the dosing pattern: parsing, storage, printing and rejection."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['PHARMS_DATA_DIR'] = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'app')

from app import create_app, db
from app.models import Medicine, Patient, Prescription, PrescriptionItem
from app.models.prescription import parse_dose_schedule, describe_dose_schedule

PASSED, FAILED = 0, []


def check(label, ok, detail=''):
    global PASSED
    if ok:
        PASSED += 1
        print('  PASS  %s' % label)
    else:
        FAILED.append(label)
        print('  FAIL  %s %s' % (label, detail))


print('PARSING (the notation an Indian prescriber writes)')
cases = [
    ('0-0-1', True, 'one at night'),
    ('1-0-1', True, 'morning and night'),
    ('1-1/2-0', True, 'one morning, half midday'),
    ('1/2-0-1/2', True, 'half twice daily'),
    ('1-1-1', True, 'three times daily'),
    ('0-0-0', True, 'valid but nothing taken'),
    ('1-0', False, 'only two slots'),
    ('1-0-1-0', False, 'four slots'),
    ('', False, 'empty'),
    (None, False, 'absent'),
]
for value, valid, note in cases:
    got = parse_dose_schedule(value)
    ok = (got is not None) == valid
    check('%-12s -> %-22s (%s)' % (
        value or 'None', 'valid' if got else 'refused', note), ok,
        'parsed as %s' % got)

print()
print('EXPANSION (what the patient reads)')
for value, expected in (('0-0-1', 'Night: one'),
                        ('1-0-1', 'Morning: one, Night: one'),
                        ('1-1/2-0', 'Morning: one, Midday: half'),
                        ('1/2-0-1/2', 'Morning: half, Night: half')):
    got = describe_dose_schedule(value)
    check('%-10s -> %s' % (value, got), got == expected,
          'expected %s' % expected)
check('0-0-0 expands to nothing taken',
      describe_dose_schedule('0-0-0') is None)

app = create_app()
with app.app_context():
    client = app.test_client()

    patient = Patient.query.first()
    if not patient:
        patient = Patient(first_name='Test', last_name='Pattern',
                          email='pattern@test.local', phone='0000000000',
                          date_of_birth=__import__('datetime').date(1990, 1, 1),
                          gender='Male', weight_kg=70)
        db.session.add(patient)
        db.session.commit()

    medicines = Medicine.query.limit(2).all()

    print()
    print('STORAGE AND PRINT')

    payload = {
        'patient_id': patient.id,
        'doctor_name': 'Dr. Pattern Test',
        'diagnosis': 'Dose pattern check',
        'items': [
            {
                'medicine_id': medicines[0].id,
                'dosage_amount': 1, 'dosage_unit': 'tablet',
                'frequency': 'Once daily', 'duration_days': 5,
                'dose_schedule': '0-0-1',
                'special_instructions': 'Take after food',
            },
            {
                'medicine_id': medicines[1].id,
                'dosage_amount': 0.5, 'dosage_unit': 'tablet',
                'frequency': 'Twice daily', 'duration_days': 5,
                'dose_schedule': '1-0-1',
            },
        ],
    }
    response = client.post('/api/prescriptions', json=payload)
    check('a prescription with dose patterns is accepted',
          response.status_code == 201, 'status %s' % response.status_code)

    if response.status_code == 201:
        rx_id = response.get_json()['data']['id']
        stored = PrescriptionItem.query.filter_by(prescription_id=rx_id).all()
        patterns = [i.dose_schedule for i in stored]
        check('the patterns were stored, not discarded',
              patterns == ['0-0-1', '1-0-1'], 'stored %s' % patterns)

        # The bug this guards against: dose_schedule was in the migration's
        # column list but never on the model, so it was silently dropped on
        # write - exactly as data_source was.
        check('the API returns the pattern',
              stored[0].to_dict().get('dose_schedule') == '0-0-1')
        check('the API returns the expanded text',
              stored[0].to_dict().get('dose_schedule_text') == 'Night: one')

        report = client.get('/api/reports/prescription/%d' % rx_id)
        html = report.get_data(as_text=True)
        check('the printed sheet shows 0-0-1', '0-0-1' in html)
        check('the printed sheet shows 1-0-1', '1-0-1' in html)
        check('the printed sheet expands the pattern',
              'Night: one' in html)

    # A malformed pattern must be refused rather than stored and printed.
    bad = dict(payload)
    bad['items'] = [dict(payload['items'][0], dose_schedule='1-0')]
    bad_response = client.post('/api/prescriptions', json=bad)
    check('a malformed pattern is refused, not stored',
          bad_response.status_code == 400,
          'status %s' % bad_response.status_code)
    if bad_response.status_code == 400:
        message = bad_response.get_json().get('error', '')
        check('and the refusal explains the expected format',
              '0-0-1' in message or 'morning-midday-night' in message,
              message[:90])

print()
print('%d passed, %d failed' % (PASSED, len(FAILED)))
for label in FAILED:
    print('   FAILED: %s' % label)
sys.exit(1 if FAILED else 0)