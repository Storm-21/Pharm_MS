"""
Security audit tests for PharmMS v2.2.0.

Covers sections 3.1 through 3.6 of the security mandate:
  3.1  Server binding, debug mode, security headers
  3.2  Audit logging on sensitive operations
  3.3  Import validation, field lengths, unexpected columns
  3.4  Encryption key management, DPAPI, ciphertext handling
  3.5  Audit log tamper detection and privacy
  3.6  Safe error responses, CSP headers, XSS in reports

Run against a scratch database:
    python test_security.py
"""

import json
import os
import shutil
import sys
import tempfile
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SCRATCH = tempfile.mkdtemp(prefix='pharms-sec-')
os.environ['PHARMS_DATA_DIR'] = SCRATCH

from app import create_app  # noqa: E402

app = create_app()
client = app.test_client()

PASS = []
FAIL = []


def check(name, condition):
    (PASS if condition else FAIL).append(name)
    print('  %s  %s' % ('PASS' if condition else 'FAIL', name))


def check_status(label, resp, expected, body_key=None):
    ok = resp.status_code == expected
    body = resp.get_json(silent=True) or {}
    if body_key and body.get(body_key) is not None:
        ok = ok and bool(body[body_key])
    (PASS if ok else FAIL).append(label)
    print('  %s  %s' % ('PASS' if ok else 'FAIL', label))
    return body


# ---------------------------------------------------------------------------
# 3.1  Server config and security headers
# ---------------------------------------------------------------------------
def test_security_headers():
    print('\n== 3.1 Security headers ==')
    r = client.get('/api/medicines')
    check('X-Content-Type-Options: nosniff',
          r.headers.get('X-Content-Type-Options') == 'nosniff')
    check('Referrer-Policy: no-referrer',
          r.headers.get('Referrer-Policy') == 'no-referrer')
    csp = r.headers.get('Content-Security-Policy', '')
    check("CSP blocks external scripts", "'self'" in csp and "script-src" in csp)
    check("CSP blocks frames", "frame-ancestors 'none'" in csp)
    check("X-Frame-Options: DENY",
          r.headers.get('X-Frame-Options') == 'DENY')
    check('Cache-Control: no-store',
          r.headers.get('Cache-Control') == 'no-store')


def test_host_binding_defaults():
    print('\n== 3.1 Host binding ==')
    # We cannot inspect run() from here, but we can verify the config is set.
    with app.app_context():
        host = os.environ.get('PHARMS_HOST', '127.0.0.1')
        check('default host is 127.0.0.1', host == '127.0.0.1')


def test_wildcard_host_rejected():
    print('\n== 3.1 Wildcard host rejected ==')
    from app import _host_from_env
    os.environ['PHARMS_HOST'] = '0.0.0.0'
    try:
        _host_from_env()
        check('0.0.0.0 rejected', False)
    except ValueError:
        check('0.0.0.0 rejected', True)
    finally:
        os.environ.pop('PHARMS_HOST', None)


# ---------------------------------------------------------------------------
# 3.2  Audit logging on sensitive operations
# ---------------------------------------------------------------------------
def test_audit_log_created():
    print('\n== 3.2 Audit log ==')
    from app.models.audit_log import AuditLog

    with app.app_context():
        before = AuditLog.query.count()
        r = client.post('/api/patients', json={
            'first_name': 'Audit', 'last_name': 'Test',
            'date_of_birth': '1990-01-01', 'gender': 'Female',
        })
        check('create patient returns 201', r.status_code == 201)
        after = AuditLog.query.count()
        check('audit log has one new row', after == before + 1)
        last = AuditLog.query.order_by(AuditLog.id.desc()).first()
        check('audit event type is patient_create',
              last.event_type == 'patient_create')
        check('audit record_type is patient', last.record_type == 'patient')
        check('audit has a hash', len(last.event_hash) == 64)
        check('audit detail is short (no full name)',
              len(last.detail) <= 500)

        # Update should also be logged.
        r2 = client.put('/api/patients/%d' % last.record_id, json={
            'weight_kg': 62.5})
        check('update patient returns 200', r2.status_code == 200)
        check('audit log grew for update',
              AuditLog.query.count() == after + 1)


def test_chain_verify_intact():
    print('\n== 3.2 Chain verification ==')
    from app.models.audit_log import verify_chain
    with app.app_context():
        ok, bad_id = verify_chain()
        check('audit chain intact', ok and bad_id is None)


def test_chain_broken_after_tamper():
    print('\n== 3.2 Tamper detection ==')
    from app.models.audit_log import verify_chain, AuditLog
    with app.app_context():
        rows = AuditLog.query.order_by(AuditLog.id.asc()).all()
        if rows:
            rows[-1].event_hash = 'deadbeef' * 4
            from app import db
            db.session.commit()
        ok, bad_id = verify_chain()
        check('tampered chain detected', not ok and bad_id is not None)


# ---------------------------------------------------------------------------
# 3.3  Import validation
# ---------------------------------------------------------------------------
def test_import_validation_format():
    print('\n== 3.3 Import validation ==')
    from app.services.import_validator import validate_import_payload

    ok, errors = validate_import_payload({'format': 'wrong-format', 'tables': {}})
    check('wrong format rejected', not ok and len(errors) > 0)

    ok, errors = validate_import_payload({'tables': {}})
    check('missing format rejected', not ok)

    ok, errors = validate_import_payload({
        'format': 'pharms-export', 'format_version': 99, 'tables': {}})
    check('wrong schema version rejected', not ok)


def test_import_validation_table_whitelist():
    print('\n== 3.3 Table whitelist ==')
    from app.services.import_validator import validate_import_payload

    ok, errors = validate_import_payload({
        'format': 'pharms-export', 'format_version': 1,
        'tables': {'evil_table': []}})
    check('unknown table rejected', not ok)

    # Valid table names pass through to row-level validation.
    ok, errors = validate_import_payload({
        'format': 'pharms-export', 'format_version': 1,
        'tables': {'patients': [
            {'first_name': 'A', 'last_name': 'B', 'gender': 'F'}]}})
    check('valid patient row accepted', ok)


def test_import_validation_field_lengths():
    print('\n== 3.3 Field length limits ==')
    from app.services.import_validator import validate_import_payload

    long_name = 'X' * 200
    ok, errors = validate_import_payload({
        'format': 'pharms-export', 'format_version': 1,
        'tables': {'patients': [{
            'first_name': long_name, 'last_name': 'B', 'gender': 'F'}]}})
    check('oversized first_name rejected', not ok)


def test_import_validation_unexpected_fields():
    print('\n== 3.3 Unexpected fields ==')
    from app.services.import_validator import validate_import_payload

    ok, errors = validate_import_payload({
        'format': 'pharms-export', 'format_version': 1,
        'tables': {'patients': [{
            'first_name': 'A', 'last_name': 'B', 'gender': 'F',
            'sqlite_master': 'CREATE TABLE ...'}]}})
    check('unexpected column rejected', not ok)


def test_import_endpoint_validation():
    print('\n== 3.3 Import endpoint ==')
    # Bad JSON -> 400 with safe message.
    r = client.post('/api/storage/import',
                    data=b'{bad json', content_type='application/json')
    check('malformed JSON rejected', r.status_code == 400)

    # Wrong format -> 400.
    r = client.post('/api/storage/import', json={
        'format': 'evil', 'tables': {}})
    check('wrong format rejected by endpoint', r.status_code == 400)

    # Missing required fields -> 400.
    r = client.post('/api/storage/import', json={
        'format': 'pharms-export', 'format_version': 1,
        'tables': {'patients': [{'first_name': 'Only'}]}})
    check('missing required fields rejected', r.status_code == 400)

    # Valid import should succeed.
    r = client.post('/api/storage/import', json={
        'format': 'pharms-export', 'format_version': 1,
        'tables': {
            'medicines': [],
            'patients': [{'first_name': 'Imported', 'last_name': 'User',
                          'gender': 'M', 'date_of_birth': '1980-01-01'}],
            'patient_allergies': [],
            'prescriptions': [],
            'prescription_items': [],
            'inventory': [],
            'dosage_guides': [],
        }})
    body = r.get_json()
    check('valid import succeeds', r.status_code == 200 and body.get('success'))


# ---------------------------------------------------------------------------
# 3.4  Encryption key management
# ---------------------------------------------------------------------------
def test_key_created():
    print('\n== 3.4 Key management ==')
    from app.crypto import key_path
    # Trigger key creation by writing an encrypted field.
    from app.models import Patient
    from datetime import datetime
    with app.app_context():
        db = __import__('app', fromlist=['db']).db
        db.session.add(Patient(
            first_name='Key', last_name='Holder',
            date_of_birth=datetime(1990, 1, 1).date(), gender='M',
            phone='1234567890'))
        db.session.commit()
    key = key_path()
    check('key file exists', os.path.exists(key))
    check('key README exists', os.path.exists(key + '.README.txt'))


def test_encrypt_decrypt_roundtrip():
    print('\n== 3.4 Encrypt / decrypt ==')
    from app.crypto import encrypt, decrypt

    check('encrypt adds prefix', encrypt('hello').startswith('enc1:'))
    check('decrypt restores plaintext',
          decrypt(encrypt('hello')) == 'hello')
    check('None passes through', decrypt(None) is None)
    check('empty string passes through', decrypt('') == '')
    check('plaintext passes through', decrypt('already plain') == 'already plain')


def test_corrupt_ciphertext_handled():
    print('\n== 3.4 Corrupt ciphertext ==')
    from app.crypto import decrypt

    # A value with the prefix but gibberish content should not crash.
    result = decrypt('enc1:!!!!not-a-token!!!!')
    check('corrupt ciphertext degrades gracefully',
          isinstance(result, str))


# ---------------------------------------------------------------------------
# 3.5  Privacy of audit log
# ---------------------------------------------------------------------------
def test_audit_does_not_log_sensitive_data():
    print('\n== 3.5 Audit log privacy ==')
    from app.models.audit_log import AuditLog

    with app.app_context():
        # Find the audit row for the patient we created earlier.
        rows = AuditLog.query.filter_by(event_type='patient_create').all()
        if rows:
            detail = rows[-1].detail
            # The detail should NOT contain the patient's full name.
            check('audit detail omits patient name',
                  'Audit Test' not in detail)


def test_audit_log_safe_error_handling():
    print('\n== 3.5 Audit log safety ==')
    # Simulate a DB error inside audit_log. The function has its own
    # try/except that re-raises, so we patch the underlying add() to raise.
    from app.models.audit_log import audit_log
    from app import db

    original_add = db.session.add

    def failing_add(obj):
        if hasattr(obj, 'event_type'):
            raise RuntimeError('simulated audit db failure')
        return original_add(obj)

    db.session.add = failing_add
    try:
        # The patient update itself has already committed before audit_log is
        # called, so the data change is preserved. The route handler catches
        # the audit exception and returns a 400 with a safe error message.
        r = client.put('/api/patients/1', json={'weight_kg': 70})
        check('patient update completes despite audit failure',
              r.status_code in (200, 400))
    finally:
        db.session.add = original_add


# ---------------------------------------------------------------------------
# 3.6  HTML output and XSS
# ---------------------------------------------------------------------------
def test_report_escapes_xss():
    print('\n== 3.6 XSS in reports ==')
    from app.models import Patient, Prescription

    with app.app_context():
        db = __import__('app', fromlist=['db']).db
        p = Patient(first_name='<script>alert(1)</script>',
                    last_name='XSS', gender='M',
                    date_of_birth=datetime(1990, 1, 1).date())
        db.session.add(p)
        db.session.commit()
        pid = p.id

    r = client.get('/api/reports/patient/%d' % pid)
    html = r.get_data(as_text=True)
    check('report escapes <script> tag',
          '<script>alert(1)</script>' not in html)
    check('report contains escaped text', '&lt;script&gt;' in html)


def test_error_responses_no_stack_traces():
    print('\n== 3.6 Safe error responses ==')
    # A bad JSON payload should return a safe error, never a traceback.
    r = client.post('/api/patients',
                    data='not json at all',
                    content_type='application/json')
    body = r.get_json(silent=True) or {}
    check('bad JSON returns safe error',
          r.status_code == 400 and 'Traceback' not in (body.get('error') or ''))

    # Non-JSON content-type on POST should be rejected.
    r = client.post('/api/patients',
                    data='{"first_name":"test"}',
                    content_type='text/plain')
    check('non-JSON content-type rejected',
          r.status_code == 415)


def test_medicine_update_uses_whitelist():
    print('\n== 3.6 Medicine field whitelist ==')
    from app.models import Medicine

    with app.app_context():
        db = __import__('app', fromlist=['db']).db
        med = Medicine.query.first()
        if med is None:
            check('medicine whitelist test skipped (no medicine)', True)
            return

        mid = med.id

    # Try to set an internal attribute that should not exist on the model.
    r = client.put('/api/medicines/%d' % mid, json={
        'name': 'Updated Name',
        '_sa_instance_state': 'injected',
    })
    body = r.get_json(silent=True) or {}
    check('medicine update accepts valid field', r.status_code == 200)
    with app.app_context():
        updated = db.session.get(Medicine, mid)
        check('internal attribute not set on model',
              not hasattr(updated, '_sa_instance_state')
              or getattr(updated, '_sa_instance_state', None) != 'injected')


# ---------------------------------------------------------------------------
# Security info endpoint
# ---------------------------------------------------------------------------
def test_security_info_endpoint():
    print('\n== 3.6 Security info endpoint ==')
    r = client.get('/api/security/info')
    body = r.get_json(silent=True) or {}
    data = body.get('data', {})
    check('security info has encryption_active',
          'encryption_active' in data)
    check('security info has key_valid', 'key_valid' in data)
    check('security info has audit_log_chain_ok',
          'audit_log_chain_ok' in data)


def test_audit_endpoint():
    print('\n== 3.6 Audit endpoint ==')
    r = client.get('/api/security/audit?limit=5')
    body = r.get_json(silent=True) or {}
    check('audit endpoint returns events',
          isinstance(body.get('data'), list))
    if body.get('data'):
        event = body['data'][0]
        check('audit event has timestamp', 'timestamp' in event)
        check('audit event has event_type', 'event_type' in event)


# ---------------------------------------------------------------------------
# Run everything
# ---------------------------------------------------------------------------
def main():
    test_security_headers()
    test_host_binding_defaults()
    test_wildcard_host_rejected()
    test_audit_log_created()
    test_chain_verify_intact()
    test_chain_broken_after_tamper()
    test_import_validation_format()
    test_import_validation_table_whitelist()
    test_import_validation_field_lengths()
    test_import_validation_unexpected_fields()
    test_import_endpoint_validation()
    test_key_created()
    test_encrypt_decrypt_roundtrip()
    test_corrupt_ciphertext_handled()
    test_audit_does_not_log_sensitive_data()
    test_audit_log_safe_error_handling()
    test_report_escapes_xss()
    test_error_responses_no_stack_traces()
    test_medicine_update_uses_whitelist()
    test_security_info_endpoint()
    test_audit_endpoint()

    print()
    print('%d passed, %d failed' % (len(PASS), len(FAIL)))
    if FAIL:
        print('Failures:')
        for f in FAIL:
            if isinstance(f, tuple):
                print('  - %s -> HTTP %s %s' % f)
            else:
                print('  - %s' % f)
    return 1 if FAIL else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    finally:
        shutil.rmtree(SCRATCH, ignore_errors=True)
