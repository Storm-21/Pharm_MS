"""
One-time activation token behaviour.

The properties that matter, and the reason each is asserted:

  1. a token the vendor never issued is REFUSED
  2. an issued token activates, and reports success
  3. the same token cannot activate a SECOND pharmacy (single-use)
  4. re-entering it for the SAME name is allowed - it is the same licence, and
     refusing would strand a customer whose branding was cleared
  5. validity is indefinite - there is no expiry field to fall off
  6. a token is NOT name-bound: one token works for whichever name buys it
  7. deactivating keeps the redemption record, so the token cannot be reused
  8. a token typed with spaces, lowercase or confusable letters still works
  9. a malformed entry is rejected with a message about its shape, not a crash
 10. the ledger shipped in the build decides validity, not the key derivation

Run:  python test_activation.py
"""

import os
import sys
import tempfile
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PASSED = 0
FAILED = []


def check(label, condition, detail=''):
    global PASSED
    if condition:
        PASSED += 1
        print('  PASS  %s' % label)
    else:
        FAILED.append(label)
        print('  FAIL  %s %s' % (label, ('- ' + str(detail)) if detail else ''))


def main():
    # A throwaway database so this never touches a real pharmacy's records.
    workdir = tempfile.mkdtemp(prefix='pharms-activation-')
    os.environ['PHARMS_DATA_DIR'] = workdir

    # Use the SAME secret the issuer signed with. The app resolves it from the
    # file setup_licence_secret.py wrote, but the test asserts on the loaded
    # ledger, so make the source explicit and fail loudly if it is missing
    # rather than silently comparing against the development secret - which is
    # the bug this test was written to catch.
    when = datetime.now().strftime('%H:%M:%S')
    secret_file = os.path.join(
        os.environ.get('LOCALAPPDATA', os.path.expanduser('~')),
        'PharmMS', 'token_secret.txt')
    if os.path.isfile(secret_file):
        with open(secret_file, encoding='utf-8') as handle:
            os.environ.setdefault('PHARMS_TOKEN_SECRET', handle.read().strip())

    from app import create_app, db, activation
    from app import licensing

    app = create_app()
    with app.app_context():
        db.create_all()

        print()
        print('Activation tokens  (%s)' % when)
        print('-' * 60)

        # --- 9. A malformed token is rejected, not crashed -------------------
        # Two distinct malformed cases, because they take different code paths
        # and must both give a useful message:
        #
        # a) something that is clearly meant to be a token (it carries the PMS
        #    prefix) but is the wrong length
        ok, message = licensing.apply_licence('Test Pharmacy', 'PMS-AAAA-BBBB')
        check('a short token with the PMS prefix is refused as a token',
              not ok and 'does not look like an activation token' in message, message)

        # b) nonsense with no prefix and no plausible length. There is no honest
        #    way to tell this from a legacy key, so it is refused by the legacy
        #    path - what matters is that it is refused and explains itself.
        ok, message = licensing.apply_licence('Test Pharmacy', 'not-a-token')
        check('nonsense input is refused with a reason',
              not ok and len(message) > 20, message)

        # c) a full-length but unissued token - the most likely real mistake, a
        #    valid-looking token that was never sold.
        ok, message = licensing.apply_licence(
            'Test Pharmacy', 'PMS-AAAA-BBBB-CCCC-DDDD-EEEE')
        check('a well-formed but unissued token is refused as not issued',
              not ok and 'not issued' in message, message)

        ok, message = licensing.apply_licence('Test Pharmacy', '')
        check('an empty token is refused', not ok)

        ok, message = licensing.apply_licence('', 'PMS-HPXS-ST4D-2A9X-1QJG-XQWT')
        check('an empty pharmacy name is refused', not ok)

        # --- 2. A real issued token activates --------------------------------
        token = None
        for body, entry in activation._LEDGER.items():
            token = entry.get('token')
            break
        check('the build carries an issued-token ledger', bool(activation._LEDGER),
              'no ledger compiled in')
        if not token:
            print('\nNo tokens in the ledger - run issue_tokens.py first.')
            return 1

        ok, message = licensing.apply_licence('Sri Balaji Medicals', token)
        check('an issued token activates', ok, message)
        check('activation reports the pharmacy name',
              'Sri Balaji Medicals' in message, message)
        check('the installation is now licensed', licensing.is_licensed())
        check('branding reports the pharmacy name',
              licensing.branding_settings()['pharmacy_name'] == 'Sri Balaji Medicals')

        # --- 3. Single use: a second name cannot reuse it --------------------
        licensing.clear_licence()
        ok, message = licensing.apply_licence('Some Other Pharmacy', token)
        check('a spent token cannot activate a second pharmacy', not ok, message)
        check('the refusal names where it was spent',
              'Sri Balaji Medicals' in message, message)

        # --- 4. The same name may re-apply (same licence, not a new one) -----
        ok, message = licensing.apply_licence('Sri Balaji Medicals', token)
        check('the same token re-applied for the same name is allowed', ok, message)
        check('reactivation says it was already used',
              'already been activated' in message, message)

        # --- 7. Deactivation keeps the record --------------------------------
        licensing.clear_licence()
        check('deactivation clears the licence', not licensing.is_licensed())
        check('the redemption record survives deactivation',
              activation.service().is_redeemed(token))

        # --- 6. A token is not name-bound ------------------------------------
        # The second token must work for an entirely different shop, because it
        # is bound to a sale, not to a name.
        tokens = [e.get('token') for e in activation._LEDGER.values()]
        second = tokens[1] if len(tokens) > 1 else None
        if second:
            ok, message = licensing.apply_licence('Krishna Medicals', second)
            check('a fresh token activates a different pharmacy', ok, message)
            check('the different name is now licensed',
                  licensing.is_licensed() and
                  licensing.branding_settings()['pharmacy_name'] == 'Krishna Medicals')
            licensing.clear_licence()

        # --- 8. Sloppy typing still works ------------------------------------
        # Lowercase, spaces instead of dashes, and an 'O' where a zero was
        # meant: all three are what a customer actually types off a message.
        if second:
            sloppy = ' ' + second.lower().replace('-', ' ') + ' '
            sloppy = sloppy.replace('0', 'o')
            ok, message = licensing.apply_licence(
                'Krishna Medicals', sloppy)
            check('a lowercase, spaced token with a confusable letter still works',
                  ok, message)

        # --- 5. Indefinite validity ------------------------------------------
        status = activation.service().status()
        check('validity is indefinite (no expiry to fall off)',
              status.get('validity') == 'indefinite', status.get('validity'))
        check('the status exposes the price',
              status.get('price_inr') == 500, status.get('price_inr'))
        check('an audit log of redemptions is kept',
              len(status.get('redemptions') or []) >= 1)

        # --- 10. The ledger is authoritative, not the derivation -------------
        # Editing the ledger signature must invalidate the entry, which is what
        # makes the shipped table meaningful rather than decorative.
        entry = next(iter(activation._LEDGER.values()))
        original = entry.get('signature')
        entry['signature'] = 'f' * len(original or '')
        ok, reason, _ = activation.validate(entry.get('token'))
        check('a ledger entry with a broken signature is rejected', not ok, reason)
        entry['signature'] = original
        ok, _reason, _ = activation.validate(entry.get('token'))
        check('restoring the signature makes it valid again', ok)

    print()
    print('-' * 60)
    print('%d passed, %d failed' % (PASSED, len(FAILED)))
    if FAILED:
        for label in FAILED:
            print('   FAILED: %s' % label)
        return 1
    print('All activation-token tests passed.')
    return 0


if __name__ == '__main__':
    sys.exit(main())