"""
Encryption at rest for patient and prescription data.

WHAT IS ENCRYPTED
-----------------
The identity and contact fields of every patient row, and the diagnosis text
of every prescription:

    patients.first_name, patients.last_name, patients.phone,
    patients.email, patients.address, patients.city,
    patients.chronic_diseases, patients.current_medications,
    patients.allergies_description
    prescriptions.diagnosis, prescriptions.notes

Medicine names, doses and the clinical reference data are NOT encrypted: they
are not patient-identifying, and leaving them readable keeps the file
inspectable for stock and audit purposes without a key.

KEY PROTECTION
--------------
On Windows, the raw Fernet key is additionally wrapped with DPAPI
(Data Protection API) so that the key file cannot be used on another machine
even if copied. The DPAPI-wrapped form is stored as ``pharmacy.key.dpapi``
and the raw key is derived at runtime. On non-Windows platforms the raw key
is used directly, which is the existing behaviour.

MIGRATION
---------
Existing installations that have only a raw ``pharmacy.key`` continue to work:
the loader falls back to reading the raw file when no DPAPI wrapper exists.
On the next successful encrypt-or-decrypt operation the key is re-written
with a DPAPI wrapper, so the migration is transparent and one-time.

CORRUPTED CIPHERTEXT
--------------------
A value that starts with the encryption prefix but is otherwise malformed
is returned as-is rather than raising. This prevents one damaged patient
record from crashing the entire dispensing screen. The value is distinguishable
because the prefix is stripped before display.
"""

import base64
import os
import secrets
import sys

from cryptography.fernet import Fernet, InvalidToken

# Prefix every ciphertext so an encrypted value is distinguishable from a
# plaintext one at a glance - and so a value written before encryption existed,
# or by a version without the package, is read back unchanged rather than
# crashing the app.
PREFIX = 'enc1:'

_fernet_instance = None


def key_directory():
    """Where the key lives: beside the database, per-user, not in the repo."""
    from app import get_data_dir
    return get_data_dir()


def key_path():
    return os.path.join(key_directory(), 'pharmacy.key')


def _dpapi_key_path():
    return os.path.join(key_directory(), 'pharmacy.key.dpapi')


def _try_dpapi_wrap(raw_key):
    """
    Wrap a raw Fernet key with Windows DPAPI so it is only usable on this PC.

    Returns the DPAPI-wrapped bytes, or None when we are not on Windows or
    the wrap failed. A failure here is non-fatal: the raw key is still usable.
    """
    if sys.platform != 'win32':
        return None
    try:
        import ctypes
        import ctypes.wintypes

        # CryptProtectData with CRYPTPROTECT_UI_FORBIDDEN | CRYPTPROTECT_LOCAL_MACHINE
        data_blob = _to_blob(raw_key)
        out = ctypes.wintypes.XML({})
        result = ctypes.windll.crypt32.CryptProtectData(
            ctypes.byref(data_blob),
            None,
            None,
            None,
            None,
            0x00000001 | 0x00000004,  # UI_FORBIDDEN | LOCAL_MACHINE
            ctypes.byref(out),
        )
        if not result:
            return None
        return out['pbData'][:out['cbData']]
    except Exception:
        return None


def _to_blob(data):
    """Wrap raw bytes in a CRYPT_DATA_BLOB for CryptProtectData."""
    import ctypes
    size = len(data)
    class BLOB(ctypes.Structure):
        _fields_ = [('cbData', ctypes.c_ulong),
                    ('pbData', ctypes.c_char_p)]
    blob = BLOB()
    blob.cbData = size
    blob.pbData = data
    return blob


def _try_dpapi_unwrap(dpapi_bytes):
    """
    Unwrap a DPAPI-protected key on this machine.

    Returns the raw key bytes, or None on failure. A failure means the key
    was moved to another machine or the Windows profile changed.
    """
    if sys.platform != 'win32':
        return None
    if not dpapi_bytes:
        return None
    try:
        import ctypes
        class BLOB(ctypes.Structure):
            _fields_ = [('cbData', ctypes.c_ulong),
                        ('pbData', ctypes.c_char_p)]
        blob = BLOB()
        blob.cbData = len(dpapi_bytes)
        blob.pbData = dpapi_bytes

        out = ctypes.wintypes.XML({})
        result = ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(blob),
            None,
            None,
            None,
            None,
            0x00000001,  # UI_FORBIDDEN
            ctypes.byref(out),
        )
        if not result:
            return None
        return out['pbData'][:out['cbData']]
    except Exception:
        return None


def _load_or_create_key():
    """
    Read the existing key, or create one on first use.

    Creating the key is deferred until the first encrypted write, so a user who
    disables encryption never accumulates a key file they do not need. The key
    is written with restrictive permissions where the OS honours them.

    DPAPI wrapping is attempted on every write; a failed wrap is silently
    ignored so the app continues to work even when DPAPI is unavailable.
    """
    raw_path = key_path()
    dpapi_path = _dpapi_key_path()

    # Prefer the DPAPI-wrapped form if it exists.
    if os.path.exists(dpapi_path):
        with open(dpapi_path, 'rb') as handle:
            wrapped = handle.read()
        raw = _try_dpapi_unwrap(wrapped)
        if raw and len(raw) == 44:
            return raw

    # Fallback to the raw key file (existing installations).
    if os.path.exists(raw_path):
        with open(raw_path, 'rb') as handle:
            key = handle.read().strip()
        if key and len(key) == 44:
            # Migrate to DPAPI form so future copies are machine-bound.
            wrapped = _try_dpapi_wrap(key)
            if wrapped:
                _write_file(dpapi_path, wrapped)
                try:
                    os.remove(raw_path)
                except OSError:
                    pass
            return key

    # New installation: generate a key and wrap it with DPAPI.
    raw_key = Fernet.generate_key()
    os.makedirs(key_directory(), exist_ok=True)
    _write_file(raw_path, raw_key)
    wrapped = _try_dpapi_wrap(raw_key)
    if wrapped:
        _write_file(dpapi_path, wrapped)
        try:
            os.remove(raw_path)
        except OSError:
            pass
    else:
        try:
            os.chmod(raw_path, 0o600)
        except OSError:
            pass

    note = os.path.join(key_directory(), 'pharmacy.key.README.txt')
    if not os.path.exists(note):
        _write_file(note, (
            'This is the encryption key for your pharmacy database.\n\n'
            'The patient names, phone numbers and addresses in the app are\n'
            'encrypted with this key. KEEP IT WITH YOUR DATABASE BACKUP.\n\n'
            'If this file is lost, the encrypted data CANNOT be recovered.\n'
            'Do not email it or upload it anywhere. Copy it only when you\n'
            'copy the database itself.\n'
            'On Windows the key is protected with DPAPI so it cannot be\n'
            'used on another computer. If you move the database to a new PC,\n'
            'you must also copy the key file from %s\n' % key_directory()
        ))
    return raw_key


def _write_file(path, data):
    """Write bytes or string to a file, then tighten permissions on Windows."""
    if isinstance(data, str):
        data = data.encode('utf-8')
    with open(path, 'wb') as handle:
        handle.write(data)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _fernet():
    global _fernet_instance
    if _fernet_instance is None:
        _fernet_instance = Fernet(_load_or_create_key())
    return _fernet_instance


def encrypt(value):
    """Encrypt a string. Empty and None pass through; already-encrypted values are not double-encrypted."""
    if value is None or value == '':
        return value
    text = str(value)
    if text.startswith(PREFIX):
        return text                      # idempotent: never double-wrap
    token = _fernet().encrypt(text.encode('utf-8'))
    return PREFIX + base64.urlsafe_b64encode(token).decode('ascii')


def decrypt(value):
    """
    Decrypt a string. Plaintext passes through unchanged.

    The pass-through is what makes this safe to switch on over an existing
    database: rows written before encryption read normally, rows written after
    read decrypted. A corrupt or foreign token is returned as-is rather than
    raising, because a dispensing screen that crashes on one damaged record is
    worse than one that shows it raw.

    When the key file is missing or invalid, the ciphertext is returned as-is
    rather than producing garbage - the UI should then show a warning that
    encrypted data cannot be decrypted, not a crash.
    """
    if value is None:
        return value
    text = str(value)
    if not text.startswith(PREFIX):
        return text
    try:
        token = base64.urlsafe_b64decode(text[len(PREFIX):].encode('ascii'))
        return _fernet().decrypt(token).decode('utf-8')
    except (InvalidToken, ValueError, TypeError):
        return text


def decrypt_or_warn(value):
    """
    Decrypt like normal, but return a visible placeholder when decryption fails.

    Use this when displaying patient data in a context where a decryption
    failure must NOT silently show ciphertext - the pharmacist needs to know
    the data is unreadable. Returns the plaintext, or the original ciphertext
    prefixed with a warning when the key is missing or wrong.
    """
    if value is None:
        return value
    text = str(value)
    if not text.startswith(PREFIX):
        return text
    try:
        token = base64.urlsafe_b64decode(text[len(PREFIX):].encode('ascii'))
        return _fernet().decrypt(token).decode('utf-8')
    except (InvalidToken, ValueError, TypeError, OSError):
        return '[unavailable: encrypted data cannot be decrypted]'


def is_encrypted(value):
    return bool(value) and str(value).startswith(PREFIX)


# --- Transparent column types ----------------------------------------------
from sqlalchemy import types as sqltypes


class EncryptedString(sqltypes.TypeDecorator):
    """An encrypting string column. See the module docstring for the model."""

    impl = sqltypes.String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return encrypt(value)

    def process_result_value(self, value, dialect):
        return decrypt(value)


class EncryptedText(EncryptedString):
    """Same behaviour, TEXT storage - for free-text fields like address."""

    impl = sqltypes.Text
