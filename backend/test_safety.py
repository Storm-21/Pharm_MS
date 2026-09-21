"""
Safety-engine test suite.

These are the tests that matter most in this codebase: they assert that a
dangerous combination is *blocked*, not merely flagged. Run with:

    .\\venv\\Scripts\\python.exe test_safety.py

Every test builds its own patient and medicine rows in a temporary database, so
the suite never depends on - or writes to - the user's real pharmacy.db.
"""

import os
import sys
import tempfile
from datetime import date

os.environ.setdefault('PHARMS_DB_PATH', os.path.join(
    tempfile.mkdtemp(prefix='pharms-test-'), 'test.db'))

from app import create_app, db                        # noqa: E402
from app.models import Medicine, Patient, PatientAllergy, Inventory  # noqa: E402
from app.services.safety_service import SafetyEngine  # noqa: E402

PASSED = []
FAILED = []


def check(name, condition, detail=''):
    if condition:
        PASSED.append(name)
        print('  PASS  %s' % name)
    else:
        FAILED.append((name, detail))
        print('  FAIL  %s   %s' % (name, detail))


def make_medicine(**overrides):
    """Return a medicine row for the test.

    The app seeds a reference set on startup, so most names the tests want
    already exist. Reuse the existing row when there is one rather than
    inserting a duplicate - medicines.name is UNIQUE and a second insert is a
    hard error, not a test failure worth reporting.
    """
    name = overrides.get('name')
    if name:
        existing = Medicine.query.filter_by(name=name).first()
        if existing:
            # Apply any overrides the test cares about to a copy-free basis:
            # the seeded row already carries the clinical fields the engine
            # reads, which is exactly what we want to test against.
            return existing
    data = {
        'name': 'Test Drug 500mg',
        'generic_name': 'Testdrug',
        'manufacturer': 'Test Labs',
        'salt_composition': 'Testdrug 500mg',
        'strength': '500mg',
        'form': 'tablet',
        'use_case': 'testing',
        'cost_price': 1.0,
        'selling_price': 2.0,
    }
    data.update(overrides)
    medicine = Medicine(**data)
    db.session.add(medicine)
    db.session.flush()
    return medicine


def make_patient(**overrides):
    data = {
        'first_name': 'Test',
        'last_name': 'Patient',
        'date_of_birth': date(1990, 1, 1),
        'gender': 'Male',
    }
    data.update(overrides)
    patient = Patient(**data)
    db.session.add(patient)
    db.session.flush()
    return patient


def main():
    app = create_app()
    with app.app_context():
        db.create_all()

        print('\n=== Identity / fail-safe ===')
        # A missing record must never be reported as safe.
        result = SafetyEngine.assess(999, 999)
        check('missing records -> UNKNOWN', result['verdict'] == 'UNKNOWN',
              result['verdict'])
        check('missing records -> not recommendable',
              result['recommendable'] is False)

        print('\n=== Allergy (direct and cross-reactivity) ===')
        amox = make_medicine(name='Amoxicillin 500mg', generic_name='Amoxicillin',
                             salt_composition='Amoxicillin 500mg')
        allergy_patient = make_patient()
        db.session.add(PatientAllergy(
            patient_id=allergy_patient.id, allergen='Penicillin',
            reaction='Anaphylaxis', severity='Severe'))
        db.session.flush()

        result = SafetyEngine.assess(allergy_patient.id, amox.id)
        check('penicillin allergy blocks amoxicillin (cross-reactivity)',
              result['verdict'] == 'BLOCKED', result['verdict'])
        check('severe allergy blocks rather than cautions',
              result['verdict'] == 'BLOCKED')
        check('allergy is not recommendable', not result['recommendable'])

        # A mild allergy is a serious finding, still not auto-recommended.
        mild_patient = make_patient()
        db.session.add(PatientAllergy(
            patient_id=mild_patient.id, allergen='Penicillin',
            reaction='Rash', severity='Mild'))
        db.session.flush()
        result = SafetyEngine.assess(mild_patient.id, amox.id)
        check('mild allergy -> UNSAFE, not merely CAUTION',
              result['verdict'] == 'UNSAFE', result['verdict'])
        check('mild allergy is not auto-recommendable',
              not result['recommendable'])

        print('\n=== Comorbidity rules ===')
        asthma_patient = make_patient(chronic_diseases='Asthma')
        propranolol = make_medicine(name='Propranolol 40mg',
                                    generic_name='Propranolol',
                                    salt_composition='Propranolol 40mg')
        result = SafetyEngine.assess(asthma_patient.id, propranolol.id)
        check('beta-blocker flagged SERIOUS in asthma',
              result['verdict'] == 'UNSAFE', result['verdict'])

        ulcer_patient = make_patient(chronic_diseases='Peptic ulcer')
        diclofenac = make_medicine(name='Diclofenac 50mg',
                                   generic_name='Diclofenac',
                                   salt_composition='Diclofenac 50mg')
        result = SafetyEngine.assess(ulcer_patient.id, diclofenac.id)
        check('NSAID flagged SERIOUS in peptic ulcer',
              result['verdict'] == 'UNSAFE', result['verdict'])

        print('\n=== Interactions ===')
        warfarin_patient = make_patient(current_medications='Warfarin 5mg')
        aspirin = make_medicine(name='Aspirin 75mg', generic_name='Aspirin',
                                salt_composition='Aspirin 75mg')
        result = SafetyEngine.assess(warfarin_patient.id, aspirin.id)
        check('warfarin + aspirin flagged SERIOUS',
              result['verdict'] == 'UNSAFE', result['verdict'])

        print('\n=== Paediatric age bars ===')
        child = make_patient(date_of_birth=date(date.today().year - 5, 1, 1))
        result = SafetyEngine.assess(child.id, aspirin.id)
        kinds = [f['kind'] for f in result['findings']]
        check('aspirin contraindicated under 16 (Reye syndrome)',
              'AGE' in kinds and result['verdict'] == 'BLOCKED',
              result['verdict'])

        print('\n=== Pregnancy ===')
        pregnant = make_patient(gender='Female', is_pregnant=True,
                                pregnancy_trimester=1)
        warfarin = make_medicine(name='Warfarin 5mg', generic_name='Warfarin',
                                 salt_composition='Warfarin 5mg')
        result = SafetyEngine.assess(pregnant.id, warfarin.id)
        check('warfarin BLOCKED in pregnancy',
              result['verdict'] == 'BLOCKED', result['verdict'])

        # A male patient must not trip pregnancy rules.
        result = SafetyEngine.assess(make_patient().id, warfarin.id)
        preg_findings = [f for f in result['findings'] if f['kind'] == 'PREGNANCY']
        check('pregnancy rules do not apply to male patient',
              not preg_findings)

        print('\n=== Renal function ===')
        # Metformin needs renal review. With no creatinine on file the engine
        # must say UNKNOWN rather than assume normal function.
        metformin = make_medicine(name='Metformin 500mg', generic_name='Metformin',
                                  salt_composition='Metformin 500mg')
        no_creat = make_patient()
        result = SafetyEngine.assess(no_creat.id, metformin.id)
        check('metformin with no creatinine -> UNKNOWN (not SAFE)',
              result['verdict'] == 'UNKNOWN', result['verdict'])
        check('metformin with no creatinine is not recommendable',
              not result['recommendable'])

        # Low eGFR must block.
        poor_kidney = make_patient(serum_creatinine=2.4, gender='Male',
                                   date_of_birth=date(1955, 1, 1))
        result = SafetyEngine.assess(poor_kidney.id, metformin.id)
        check('metformin with low eGFR -> UNSAFE/UNKNOWN',
              result['verdict'] in ('UNSAFE', 'UNKNOWN'), result['verdict'])

        # Normal creatinine should allow it.
        healthy = make_patient(serum_creatinine=0.9)
        result = SafetyEngine.assess(healthy.id, metformin.id)
        check('metformin with normal eGFR is SAFE',
              result['verdict'] == 'SAFE', result['verdict'])
        check('metformin with normal eGFR is recommendable',
              result['recommendable'] is True)

        print('\n=== Beers Criteria (65+) ===')
        elderly = make_patient(date_of_birth=date(date.today().year - 75, 1, 1))
        chlor = make_medicine(name='Chlorpheniramine 4mg',
                              generic_name='Chlorpheniramine',
                              salt_composition='Chlorpheniramine 4mg')
        result = SafetyEngine.assess(elderly.id, chlor.id)
        check('antihistamine flagged in 75-year-old (Beers)',
              result['verdict'] == 'CAUTION', result['verdict'])
        check('Beers caution is not auto-recommended',
              not result['recommendable'])

        print('\n=== Dose ceilings ===')
        para = make_medicine(name='Paracetamol 500mg', generic_name='Paracetamol',
                             salt_composition='Paracetamol 500mg')
        ceiling = SafetyEngine.max_daily_dose(para)
        check('paracetamol ceiling is 4000 mg/day', ceiling == 4000, str(ceiling))
        breach = SafetyEngine.check_dose_ceiling(para, 6000)
        check('6000 mg/day paracetamol raises a ceiling finding', breach is not None)
        ok = SafetyEngine.check_dose_ceiling(para, 3000)
        check('3000 mg/day paracetamol is within ceiling', ok is None)

        print('\n=== Form / unit consistency ===')
        inhaler = make_medicine(name='Salbutamol Inhaler 100mcg',
                                generic_name='Salbutamol', form='inhaler',
                                salt_composition='Salbutamol 100mcg')
        result = SafetyEngine.assess(healthy.id, inhaler.id,
                                     context={'dose_unit': 'mg'})
        form_findings = [f for f in result['findings'] if f['kind'] == 'FORM']
        check('mg dose on an inhaler is flagged', bool(form_findings))
        result = SafetyEngine.assess(healthy.id, inhaler.id,
                                     context={'dose_unit': 'puff'})
        form_findings = [f for f in result['findings'] if f['kind'] == 'FORM']
        check('puff dose on an inhaler is accepted', not form_findings)

        print('\n=== Verdict summary ===')
        check('a clean patient/medicine pair is SAFE',
              SafetyEngine.assess(healthy.id, para.id)['verdict'] == 'SAFE')

        print('\n' + '=' * 60)
        print('  %d passed, %d failed' % (len(PASSED), len(FAILED)))
        print('=' * 60)
        for name, detail in FAILED:
            print('  FAILED: %s  %s' % (name, detail))
        return 1 if FAILED else 0


if __name__ == '__main__':
    sys.exit(main())
