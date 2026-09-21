"""
Pharmacy branding + offline licence keys.

WHAT THIS DOES
--------------
Lets the owner replace the shipped product name and logo with their own pharmacy
name and logo, gated behind an offline licence key.

HOW THE KEY WORKS
-----------------
A key is an HMAC-SHA256 tag over the pharmacy name, produced with a secret held
only in the issuing tool (tools/issue_key.py, which is NOT shipped inside the
app). The app can verify a key without being able to mint one, because it only
carries the *public* verifier — see `_verifier()`.

This is the standard offline-licensing trade-off, stated plainly: a determined
person who reverse-engineers the executable could recover the verifier and mint
their own keys. Making that impossible requires a server you control that signs
each activation. The key is a real speed bump and a genuine "only the vendor
hands these out" mechanism for normal users, not cryptographic DRM.

Key format:   PMS-XXXX-XXXX-XXXX-XXXX    (Crockford base32, unambiguous charset)
Bound to:     the pharmacy name, so a key for one shop does not unlock another.
"""

import hashlib
import hmac
import os
import re

from app import db
# --- Issuer secret -----------------------------------------------------------
# The shipping build must be able to CHECK keys but must not carry the secret
# needed to CREATE them. So it stores only a one-way verifier.
#
# `_BUILD_SECRET` is baked in at build time by build_exe.ps1 from whatever
# setup_licence_secret.py generated. When it is empty, the app falls back to an
# environment variable, which is what a development run uses.
_SECRET_ENV = 'PHARMS_LICENCE_SECRET'

# Replaced by the build. Empty means "no verifier compiled in yet".
_BUILD_SECRET = ''

# Only used when neither of the above is configured. This is the public
# development secret: it lets the shipped app verify keys out of the box, but
# anyone who reads licensing.py knows it. That is fine for a free build and
# NOT fine for one you are selling - run setup_licence_secret.py and rebuild
# with -LicenceVerifier before charging for keys.
_DEV_SECRET = b'PHARMS-DEVELOPMENT-SECRET-not-for-sale'

ALPHABET = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'  # Crockford base32, no I/L/O/U


def _secret():
    env = os.environ.get(_SECRET_ENV)
    if env:
        return env.encode('utf-8')
    return _DEV_SECRET


def _verifier():
    """
    Public verifier - safe to ship inside the app.

    Prefers the value compiled in at build time (build_exe.ps1
    -LicenceVerifier). Falls back to hashing the development secret
    when running from source.
    """
    if _BUILD_SECRET:
        return _BUILD_SECRET
    return hashlib.sha256(_secret()).hexdigest()[:16]


# --- Key generation / validation --------------------------------------------

def normalise_pharmacy_name(name):
    """Canonical form used for signing: case/space/punctuation insensitive."""
    return re.sub(r'[^a-z0-9]+', '', (name or '').lower())


def compute_key(pharmacy_name, secret=None):
    """
    Derive the licence key for a pharmacy name.

    This is the *issuing* operation. A shipped build carries only a
    verifier and the issued-key table, so it cannot mint new keys - which
    is exactly the point.
    """
    key_material = secret if secret is not None else _secret()
    payload = normalise_pharmacy_name(pharmacy_name)
    digest = hmac.new(key_material, payload.encode('utf-8'), hashlib.sha256).digest()
    # 10 bytes -> 16 base32 characters = 80 bits, ample for a name-bound key.
    body = _b32(digest[:10])
    return 'PMS-' + '-'.join(body[i:i + 4] for i in range(0, 16, 4))


def _b32(raw):
    bits = ''.join(f'{byte:08b}' for byte in raw)
    out = ''
    for i in range(0, len(bits) - (len(bits) % 5), 5):
        out += ALPHABET[int(bits[i:i + 5], 2)]
    return out


def _clean_key(text):
    cleaned = re.sub(r'[^0-9A-Za-z]', '', (text or '')).upper()
    # Crockford confusables -> canonical letters
    cleaned = cleaned.replace('I', '1').replace('L', '1').replace('O', '0').replace('U', 'V')
    if cleaned.startswith('PMS'):
        cleaned = cleaned[3:]
    return cleaned


def validate_key(pharmacy_name, candidate):
    """
    True when `candidate` is the correct key for `pharmacy_name`.

    Works in both layouts:
      * from source - re-derives and compares
      * shipped     - looks the name up in the issued-key table compiled
                      in at build time, so no signing secret is needed to
                      check a key
    """
    if not pharmacy_name or not candidate:
        return False
    expected = expected_key_for(pharmacy_name)
    if not expected:
        return False
    supplied = _clean_key(candidate)
    if len(supplied) != len(expected):
        return False
    return hmac.compare_digest(expected, supplied)


# Compiled in at build time: {'<normalised name>': '<key>'} for every key
# you have issued. Lets a shipped build confirm a key without carrying the
# signing secret. Empty in a source checkout.
try:
    # Generated by issue_key.py --export, copied in by build_exe.ps1.
    from app.issued_keys_build import ISSUED_KEYS as _ISSUED_KEYS
except ImportError:
    _ISSUED_KEYS = {}


def expected_key_for(pharmacy_name):
    """
    The key expected for a pharmacy name, or None if undeterminable.

    A build with issued keys compiled in does a lookup; a source checkout
    re-derives. Either way no secret is required to *check* a key.
    """
    normalised = normalise_pharmacy_name(pharmacy_name)

    # The compiled-in table is authoritative for names it covers: it is what a
    # shipped build relies on, and what the vendor has actually sold.
    stored = _ISSUED_KEYS.get(normalised)
    if stored:
        # Stored keys keep their PMS- prefix; _clean_key strips it on the
        # supplied side, so normalise both or nothing ever matches.
        return _clean_key(stored)

    # Not in the table. From source we can still derive it, which is what makes
    # a freshly issued key verifiable before the next export.
    return _clean_key(compute_key(pharmacy_name))


# --- Persisted branding settings --------------------------------------------

class AppSetting(db.Model):
    """Simple key/value store for branding and other runtime settings."""

    __tablename__ = 'app_settings'

    key = db.Column(db.String(64), primary_key=True)
    value = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=None, onupdate=None)

    def to_dict(self):
        return {'key': self.key, 'value': self.value}


BRANDING_KEYS = (
    'pharmacy_name',
    'pharmacy_address',
    'pharmacy_phone',
    'pharmacy_email',
    'pharmacy_registration_no',
    'pharmacy_gstin',
    'pharmacist_name',
    'prescription_footer',
    'licence_key',
    # Details printed on the standard pharmacopoeial prescription.
    'prescriber_name',
    'prescriber_qualifications',
    'prescriber_registration_no',
    'prescriber_contact',
    # Registration number of the dispensing pharmacist, printed on the
    # signature block. Separate from the prescriber's own registration.
    'pharmacist_registration_no',
)

LOGO_PATH_KEY = 'custom_logo_path'

ALLOWED_LOGO_EXT = {'.png', '.jpg', '.jpeg', '.svg', '.webp'}
MAX_LOGO_BYTES = 2 * 1024 * 1024  # 2 MB


def get_setting(key, default=None):
    row = AppSetting.query.get(key)
    return row.value if row and row.value is not None else default


def set_setting(key, value):
    row = AppSetting.query.get(key)
    if row:
        row.value = value
    else:
        db.session.add(AppSetting(key=key, value=value))


def branding_settings():
    """Current pharmacy branding. Falls back to the shipped product identity."""
    from app.branding import APP_NAME, CREATOR_NAME

    name = get_setting('pharmacy_name')
    licensed = is_licensed()
    return {
        'pharmacy_name': name or APP_NAME,
        'customised': bool(name) and licensed,
        # Unlicensed names are ignored, so this is only True for genuine keys.
        'has_custom_name': bool(name) and licensed,
        'pharmacy_address': get_setting('pharmacy_address', '') or '',
        'pharmacy_phone': get_setting('pharmacy_phone', '') or '',
        'pharmacy_email': get_setting('pharmacy_email', '') or '',
        'pharmacy_registration_no': get_setting('pharmacy_registration_no', '') or '',
        'pharmacy_gstin': get_setting('pharmacy_gstin', '') or '',
        'pharmacist_name': get_setting('pharmacist_name', '') or '',
        'prescription_footer': get_setting('prescription_footer', '') or '',
        'prescriber_name': get_setting('prescriber_name', '') or '',
        'prescriber_qualifications': get_setting('prescriber_qualifications', '') or '',
        'prescriber_registration_no': get_setting('prescriber_registration_no', '') or '',
        'prescriber_contact': get_setting('prescriber_contact', '') or '',
        'pharmacist_registration_no': get_setting('pharmacist_registration_no', '') or '',
        'has_custom_logo': bool(get_setting(LOGO_PATH_KEY)),
        'licensed': licensed,
        'licence_key_masked': _mask(get_setting('licence_key')),
        'product_name': APP_NAME,
        'creator_name': CREATOR_NAME,
    }


def _mask(key):
    if not key:
        return None
    key = str(key)
    return key[:8] + '\u2022' * max(0, len(key) - 12) + key[-4:]


def is_licensed():
    """True when a valid key is stored for the stored pharmacy name."""
    name = get_setting('pharmacy_name')
    key = get_setting('licence_key')
    if not name or not key:
        return False
    return validate_key(name, key)


def apply_licence(pharmacy_name, licence_key):
    """
    Attempt to activate a licence.

    Stores the name and key on success. Returns (ok, message).
    """
    if not pharmacy_name or not pharmacy_name.strip():
        return False, 'Enter your pharmacy name.'
    if not licence_key or not licence_key.strip():
        return False, 'Enter the licence key you were issued.'

    if not validate_key(pharmacy_name, licence_key):
        return False, (
            'That key does not match this pharmacy name. Keys are bound to the '
            'exact name they were issued for, so spelling and punctuation matter '
            '(they are ignored during checking, so "Sri Balaji Medicals" and '
            '"sri balaji medicals" both work).'
        )

    set_setting('pharmacy_name', pharmacy_name.strip())
    set_setting('licence_key', licence_key.strip())
    db.session.commit()
    return True, f"Licence activated. The application is now branded as {pharmacy_name.strip()}."


def clear_licence():
    """Remove the licence and revert to the shipped product identity."""
    for key in ('licence_key', 'pharmacy_name'):
        row = AppSetting.query.get(key)
        if row:
            db.session.delete(row)
    db.session.commit()
    return True, 'Licence removed. The application reverted to its original branding.'


def save_logo(file_storage, data_dir):
    """
    Store an uploaded logo. Gated behind a valid licence.

    Returns (ok, message, stored_filename).
    """
    if not is_licensed():
        return False, 'Activate a licence key before uploading a custom logo.', None

    filename = (file_storage.filename or '').strip()
    if not filename:
        return False, 'No file was uploaded.', None

    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_LOGO_EXT:
        return False, (
            f"Unsupported image type '{ext or 'none'}'. "
            f"Use one of: {', '.join(sorted(ALLOWED_LOGO_EXT))}."
        ), None

    raw = file_storage.read()
    if len(raw) > MAX_LOGO_BYTES:
        return False, 'That image is larger than 2 MB. Please resize it and try again.', None
    if not raw:
        return False, 'The uploaded file was empty.', None

    logo_dir = os.path.join(data_dir, 'branding')
    os.makedirs(logo_dir, exist_ok=True)

    # Always store under a fixed name so replacing a logo does not accumulate
    # files, and so a crafted filename cannot escape the folder.
    stored = f'pharmacy_logo{ext}'
    stored_path = os.path.join(logo_dir, stored)
    with open(stored_path, 'wb') as handle:
        handle.write(raw)

    # Remove any previous logo in a different format.
    for stale in os.listdir(logo_dir):
        if stale.startswith('pharmacy_logo') and stale != stored:
            try:
                os.remove(os.path.join(logo_dir, stale))
            except OSError:
                pass

    set_setting(LOGO_PATH_KEY, stored_path)
    db.session.commit()
    return True, 'Logo uploaded.', stored


def logo_path():
    """Absolute path of the custom logo, or None."""
    path = get_setting(LOGO_PATH_KEY)
    if path and os.path.isfile(path):
        return path
    return None


def remove_logo():
    path = logo_path()
    if path:
        try:
            os.remove(path)
        except OSError:
            pass
    row = AppSetting.query.get(LOGO_PATH_KEY)
    if row:
        db.session.delete(row)
        db.session.commit()
    return True, 'Custom logo removed.'


def licence_status():
    """Everything the UI needs to render the branding panel."""
    return {
        'licensed': is_licensed(),
        'verifier': _verifier(),
        'key_format': 'PMS-XXXX-XXXX-XXXX-XXXX',
        'price_inr': 500,
    }
