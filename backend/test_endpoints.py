"""
End-to-end smoke test of every API endpoint.

Run against a throwaway database so it can never touch a pharmacy's real
records:

    PHARMS_DATA_DIR=<temp> python test_endpoints.py

The point of this file is coverage, not unit precision: every registered route
is called and asserted to return a 2xx with ``success: true`` (or an explicitly
expected status). A route that 500s, or that silently returns success:false, is
a failure - those are exactly the defects that are invisible from the UI.
"""

import os
import sys
import tempfile
import traceback

# A scratch data directory, set BEFORE app import so the resolver picks it up.
SCRATCH = tempfile.mkdtemp(prefix='pharms-smoke-')
os.environ['PHARMS_DATA_DIR'] = SCRATCH

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app  # noqa: E402

app = create_app()
client = app.test_client()

PASSED = []
FAILED = []


def check(label, response, expect=200, expect_failure=False):
    """Assert a route answered with the expected status.

    ``expect_failure`` is for the negative tests: a 400 carrying
    ``success: false`` is the CORRECT answer there and must not be scored as a
    failure, or the harness reports its own assertions as bugs.
    """
    ok = response.status_code == expect
    body = None
    try:
        body = response.get_json()
    except Exception:
        body = None
    if ok and not expect_failure and isinstance(body, dict) and body.get('success') is False:
        ok = False
    if expect_failure and ok and isinstance(body, dict) and body.get('success') is True:
        # Expected a rejection and got a success - that is a real defect.
        ok = False
    if ok:
        PASSED.append(label)
        print('  PASS  %s' % label)
    else:
        detail = ''
        if isinstance(body, dict):
            detail = body.get('error') or body.get('message') or ''
        FAILED.append((label, response.status_code, detail))
        print('  FAIL  %s -> HTTP %s %s' % (label, response.status_code, detail))
    return body


def section(name):
    print('\n== %s ==' % name)


def main():
    # ---------------------------------------------------------------- health --
    section('Patients')
    child = check('POST /api/patients (paediatric, with weight)', client.post(
        '/api/patients', json={
            'first_name': 'Smoke', 'last_name': 'Child',
            'date_of_birth': '2018-01-10', 'gender': 'Male',
            'weight_kg': 24.5, 'height_cm': 132,
            'chronic_diseases': 'Asthma', 'current_medications': 'Salbutamol',
        }), expect=201)
    child_id = child['data']['id']
    assert child['data']['weight_kg'] == 24.5
    assert child['data']['bmi'] is not None
    assert child['data']['bsa_m2'] is not None

    adult = check('POST /api/patients (adult)', client.post(
        '/api/patients', json={
            'first_name': 'Smoke', 'last_name': 'Adult',
            'date_of_birth': '1985-06-06', 'gender': 'Female',
            'weight_kg': 62, 'is_pregnant': True, 'pregnancy_trimester': 2,
            'serum_creatinine': 0.8,
        }), expect=201)
    adult_id = adult['data']['id']
    assert adult['data']['egfr'] is not None, 'eGFR should compute from creatinine'
    assert adult['data']['is_pregnant'] is True
    assert adult['data']['pregnancy_trimester'] == 2

    check('GET  /api/patients', client.get('/api/patients'))
    check('GET  /api/patients?search=', client.get('/api/patients?search=Smoke'))
    check('GET  /api/patients/<id>', client.get('/api/patients/%d' % child_id))
    check('GET  /api/patients/<id>/profile',
          client.get('/api/patients/%d/profile' % child_id))
    check('PUT  /api/patients/<id> (edit echo-back)', client.put(
        '/api/patients/%d' % child_id,
        json=dict(child['data'], last_name='Child2', weight_kg=26)))
    check('PUT  /api/patients/<id> rejects blank name', client.put(
        '/api/patients/%d' % child_id, json={'first_name': ''}),
        expect=400, expect_failure=True)
    check('PUT  /api/patients/<id> rejects bad weight', client.put(
        '/api/patients/%d' % child_id, json={'weight_kg': 'heavy'}),
        expect=400, expect_failure=True)
    check('GET  /api/patients/999 -> 404',
          client.get('/api/patients/999'), expect=404)

    section('Allergies')
    check('POST /api/patients/<id>/allergies', client.post(
        '/api/patients/%d/allergies' % child_id,
        json={'allergen': 'Penicillin', 'reaction': 'Rash', 'severity': 'Moderate'}),
        expect=201)
    allergies = check('GET  /api/patients/<id>/allergies',
                      client.get('/api/patients/%d/allergies' % child_id))
    allergy_id = allergies['data'][0]['id']
    check('DELETE /api/patients/<id>/allergies/<aid>', client.delete(
        '/api/patients/%d/allergies/%d' % (child_id, allergy_id)))

    section('Medicines')
    meds = check('GET  /api/medicines', client.get('/api/medicines?per_page=200'))
    medicines = meds['data']
    assert medicines, 'the seeded catalogue should not be empty'
    paracetamol = next(
        (m for m in medicines
         if (m.get('generic_name') or '').lower().startswith('paracetamol')), None)
    assert paracetamol, 'Paracetamol must exist in the seeded set'
    medicine_id = paracetamol['id']

    check('GET  /api/medicines/<id>', client.get('/api/medicines/%d' % medicine_id))
    check('GET  /api/medicines/search/by-condition',
          client.get('/api/medicines/search/by-condition?condition=Fever'))

    section('Recommender / dosing')
    dosage = check('POST /api/recommender/dosage', client.post(
        '/api/recommender/dosage',
        json={'patient_id': child_id, 'medicine_id': medicine_id,
              'condition': 'Fever'}))
    assert dosage['data']['is_weight_based'] is True, \
        'a child with a weight must get a weight-based dose'
    # 15 mg/kg x 26 kg = 390 mg (the weight was updated to 26 kg above).
    assert abs(dosage['data']['dosage_amount'] - 390.0) < 0.01, dosage['data']

    check('POST /api/recommender/total-dosage', client.post(
        '/api/recommender/total-dosage',
        json={'dosage_amount': 390.0, 'frequency': '3 times a day',
              'duration_days': 5}))

    weight = check('POST /api/recommender/weight-dose', client.post(
        '/api/recommender/weight-dose',
        json={'patient_id': child_id, 'medicine_id': medicine_id,
              'doses_per_day': 4}))
    assert weight['data']['steps'], 'the working must be reported'
    assert weight['data']['is_weight_based'] is True

    check('POST /api/recommender/weight-dose (explicit mg/kg)', client.post(
        '/api/recommender/weight-dose',
        json={'patient_id': adult_id, 'mg_per_kg': 10, 'max_mg': 800,
              'doses_per_day': 2}))

    check('GET  /api/recommender/drug-cycle/<id>',
          client.get('/api/recommender/drug-cycle/%d' % medicine_id))
    check('POST /api/recommender/check-allergies', client.post(
        '/api/recommender/check-allergies',
        json={'patient_id': child_id, 'medicine_id': medicine_id}))
    check('POST /api/recommender/check-interactions', client.post(
        '/api/recommender/check-interactions',
        json={'medicine_id': medicine_id, 'current_medicines': 'Warfarin'}))
    check('POST /api/recommender/check-contraindications', client.post(
        '/api/recommender/check-contraindications',
        json={'patient_id': child_id, 'medicine_id': medicine_id}))
    check('POST /api/recommender/safety-screen', client.post(
        '/api/recommender/safety-screen',
        json={'patient_id': child_id, 'medicine_id': medicine_id}))
    check('POST /api/recommender/assess', client.post(
        '/api/recommender/assess',
        json={'patient_id': adult_id, 'medicine_id': medicine_id}))
    check('POST /api/recommender/recommend-medicines', client.post(
        '/api/recommender/recommend-medicines',
        json={'patient_id': child_id, 'condition': 'Fever', 'severity': 'mild'}))
    check('POST /api/recommender/alternative-medicines', client.post(
        '/api/recommender/alternative-medicines',
        json={'patient_id': child_id, 'medicine_id': medicine_id}))
    check('GET  /api/recommender/similar-cases',
          client.get('/api/recommender/similar-cases?patient_id=%d&condition=Fever'
                     % child_id))
    check('GET  /api/recommender/alternatives',
          client.get('/api/recommender/alternatives?medicine_id=%d' % medicine_id))
    check('GET  /api/recommender/by-condition',
          client.get('/api/recommender/by-condition?condition=Fever'))
    check('GET  /api/recommender/medicine-details/<id>',
          client.get('/api/recommender/medicine-details/%d' % medicine_id))
    check('POST /api/recommender/administration-plan', client.post(
        '/api/recommender/administration-plan',
        json={'medicine_id': medicine_id}))
    check('GET  /api/recommender/substitutes/<id>',
          client.get('/api/recommender/substitutes/%d?patient_id=%d'
                     % (medicine_id, child_id)))
    check('POST /api/recommender/dispense-plan', client.post(
        '/api/recommender/dispense-plan',
        json={'medicine_id': medicine_id, 'patient_id': child_id,
              'quantity_needed': 10}))
    check('GET  /api/recommender/resolve',
          client.get('/api/recommender/resolve?condition=Fever&patient_id=%d'
                     % child_id))

    section('Inventory')
    inv = check('GET  /api/inventory', client.get('/api/inventory?per_page=200'))
    items = inv['data']
    if items:
        check('GET  /api/inventory/<id>', client.get('/api/inventory/%d' % items[0]['id']))
    check('GET  /api/inventory/summary', client.get('/api/inventory/summary'))
    check('GET  /api/inventory/alerts', client.get('/api/inventory/alerts'))

    section('Prescriptions')
    prescription = check('POST /api/prescriptions', client.post(
        '/api/prescriptions', json={
            'patient_id': child_id, 'doctor_name': 'Dr Smoke',
            'diagnosis': 'Fever', 'notes': 'Smoke test',
        }), expect=201)
    prescription_id = prescription['data']['id']
    check('GET  /api/prescriptions', client.get('/api/prescriptions'))
    check('GET  /api/prescriptions/<id>',
          client.get('/api/prescriptions/%d' % prescription_id))
    check('POST /api/prescriptions/<id>/items', client.post(
        '/api/prescriptions/%d/items' % prescription_id, json={
            'medicine_id': medicine_id, 'dosage_amount': 390.0,
            'dosage_unit': 'mg', 'frequency': '3 times a day',
            'duration_days': 5,
        }), expect=201)
    check('PUT  /api/prescriptions/<id>', client.put(
        '/api/prescriptions/%d' % prescription_id,
        json={'diagnosis': 'Fever (updated)'}))

    section('Storage / security / branding')
    check('GET  /api/storage/info', client.get('/api/storage/info'))
    check('GET  /api/storage/snapshots', client.get('/api/storage/snapshots'))
    check('POST /api/storage/export', client.post(
        '/api/storage/export', json={'include_medicines': False}))
    check('GET  /api/security/branding', client.get('/api/security/branding'))
    check('GET  /api/security/verify', client.get('/api/security/verify'))
    check('GET  /api/branding', client.get('/api/branding'))

    section('Reports (HTML, served for printing)')
    for label, url in (
        ('GET  /api/reports/prescription/<id>',
         '/api/reports/prescription/%d' % prescription_id),
        ('GET  /api/reports/patient/<id>', '/api/reports/patient/%d' % child_id),
        ('GET  /api/reports/inventory', '/api/reports/inventory'),
    ):
        response = client.get(url)
        if response.status_code == 200 and response.data:
            PASSED.append(label)
            print('  PASS  %s' % label)
        else:
            FAILED.append((label, response.status_code, 'empty or non-200'))
            print('  FAIL  %s -> HTTP %s' % (label, response.status_code))

    section('Frontend bundle')
    index = client.get('/')
    if index.status_code == 200:
        PASSED.append('GET  / (React bundle)')
        print('  PASS  GET  / (React bundle)')
    else:
        # Acceptable in a backend-only checkout, but worth stating.
        print('  SKIP  GET  / -> HTTP %s (no frontend build present)'
              % index.status_code)

    section('Cleanup')
    check('DELETE /api/prescriptions/<id>',
          client.delete('/api/prescriptions/%d' % prescription_id))
    check('DELETE /api/patients/<id>', client.delete('/api/patients/%d' % child_id))
    check('DELETE /api/patients/<id>', client.delete('/api/patients/%d' % adult_id))

    # ----------------------------------------------------------------- report --
    print('\n' + '=' * 62)
    print('  %d passed, %d failed' % (len(PASSED), len(FAILED)))
    print('=' * 62)
    if FAILED:
        for label, status, detail in FAILED:
            print('  FAILED: %s (HTTP %s) %s' % (label, status, detail))
        return 1
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(2)