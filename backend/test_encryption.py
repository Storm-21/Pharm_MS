"""
End-to-end test for encryption at rest.

Checks that patient contact/medical fields and prescription diagnosis are
ciphertext IN THE DATABASE FILE, while the application reads them back as
plaintext through the models - which is the whole design: opaque on disk,
transparent in the app.
"""

import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PASS = []
FAIL = []


def check(name, condition):
    (PASS if condition else FAIL).append(name)
    print('  %s %s' % ('PASS' if condition else 'FAIL', name))


def main():
    temp = tempfile.mkdtemp(prefix='pharms_enc_')
    os.environ['PHARMS_DATA_DIR'] = temp
    os.environ.pop('LOCALAPPDATA', None) and None

    try:
        from app import create_app, db
        from app.models import Patient, Prescription, Medicine

        app = create_app()
        with app.app_context():
            db.create_all()

            patient = Patient(
                first_name='Asha', last_name='Verma',
                date_of_birth=datetime(1990, 5, 14).date(), gender='Female',
                phone='9876543210', address='12 MG Road, Pune',
                city='Pune', chronic_diseases='Diabetes, Hypertension',
                current_medications='Metformin 500mg',
                allergies_description='Penicillin rash',
            )
            db.session.add(patient)
            db.session.flush()

            prescription = Prescription(
                patient_id=patient.id, doctor_name='Dr. A. Sharma',
                diagnosis='Type 2 diabetes mellitus, poorly controlled',
                notes='Review HbA1c in 3 months',
            )
            db.session.add(prescription)
            db.session.commit()
            pid, pres_id = patient.id, prescription.id

        db_path = os.path.join(temp, 'pharmacy.db')
        raw = sqlite3.connect(db_path)
        row = raw.execute(
            'SELECT phone, address, chronic_diseases, first_name '
            'FROM patients WHERE id=?', (pid,)).fetchone()
        pres_row = raw.execute(
            'SELECT diagnosis, notes FROM prescriptions WHERE id=?',
            (pres_id,)).fetchone()
        raw.close()

        check('phone is ciphertext on disk', row[0].startswith('enc1:'))
        check('address is ciphertext on disk', row[1].startswith('enc1:'))
        check('chronic diseases is ciphertext on disk', row[2].startswith('enc1:'))
        check('prescription diagnosis is ciphertext on disk', pres_row[0].startswith('enc1:'))
        check('prescription notes is ciphertext on disk', pres_row[1].startswith('enc1:'))
        check('first_name stays plaintext (searchable)', row[3] == 'Asha')

        with app.app_context():
            p = db.session.get(Patient, pid)
            check('app reads phone as plaintext', p.phone == '9876543210')
            check('app reads address as plaintext', p.address == '12 MG Road, Pune')
            check('app reads chronic diseases as plaintext',
                  p.chronic_diseases == 'Diabetes, Hypertension')
            check('to_dict shows plaintext',
                  p.to_dict()['phone'] == '9876543210')

            pr = db.session.get(Prescription, pres_id)
            check('app reads diagnosis as plaintext',
                  pr.diagnosis == 'Type 2 diabetes mellitus, poorly controlled')

            # A patient saved before encryption existed must still read.
            plain = sqlite3.connect(db_path)
            plain.execute('UPDATE patients SET phone=? WHERE id=?',
                          ('9123456780', pid))
            plain.commit()
            plain.close()
            db.session.expire_all()   # the raw UPDATE bypassed the session cache
            p2 = db.session.get(Patient, pid)
            check('legacy plaintext row still reads',
                  p2.phone == '9123456780')

        key = os.path.join(temp, 'pharmacy.key')
        check('key file created beside database', os.path.exists(key))
        check('key README written',
              os.path.exists(key + '.README.txt'))

        # Key deleted -> ciphertext stays opaque (honest failure, no crash)
        with app.app_context():
            from app import crypto
            crypto._fernet_instance = None
            crypto.key_path = lambda: os.path.join(temp, 'missing.key')
            with open(os.path.join(temp, 'missing.key'), 'wb') as h:
                # A VALID Fernet key of the WRONG value - what a restored
                # backup with a mismatched key looks like. Reads degrade to
                # ciphertext passthrough; writes must not crash the counter.
                h.write(__import__('cryptography').fernet.Fernet.generate_key())
            p3 = db.session.get(Patient, pid)
            check('read with wrong key degrades, does not crash', p3 is not None)
            p3.address = '13 New Road, Mumbai'
            db.session.commit()
        check('writes with a lost key do not crash the app', True)

    finally:
        shutil.rmtree(temp, ignore_errors=True)

    print()
    print('%d passed, %d failed' % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
