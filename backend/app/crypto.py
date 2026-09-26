"""
Encryption at rest for patient and prescription data.

WHY THIS EXISTS
---------------
A pharmacy's database holds identifiable patient data - names, phone numbers,
addresses, diagnoses. If someone copies the .db file off the machine (a stolen
laptop, a backup left in cloud sync, a curious person opening the file), that
data should not read as plain text.

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

WHAT THIS HONESTLY DOES AND DOES NOT PROTECT AGAINST
----------------------------------------------------
The encryption key is stored beside the database, in a file readable only by
the current user. That is a deliberate trade:

  * it protects against casual access - someone opening the .db in a browser
    tool or a SQLite editor sees ciphertext, not names;
  * it protects a stolen backup that is copied WITHOUT the key file;
  * it does NOT protect against a determined attacker who has both the
    database and the key file from the same machine, because there is no
    secret the offline app can keep from the machine it runs on. An app that
    could not read its own data would be useless to the pharmacist.

This is stated plainly rather than overclaimed, in DEVELOPER_NOTES.md and in
the in-app security report.

HOW THE KEY WORKS
-----------------
Generated on first use with Fernet (AES-128-CBC + HMAC, via the `cryptography`
package), stored as `pharmacy.key` beside the database. If the key file is
lost, the ciphertext cannot be decrypted - the data is gone. Back up the key
WITH the database or do not encrypt. A `.key.example` note explains this to
whoever finds the file.
"""

import base64
import os
import secrets

from cryptography.fernet import Fernet, InvalidToken

# Prefix every ciphertext so an encrypted value is distinguishable from a
# plaintext one at a glance - and so a value written before encryption existed,
# or by a version without the package, is read back unchanged rather than
# crashing the app. Encryption must never make the pharmacy's data unreadable
# to its own app.
PREFIX = 'enc1:'

_fernet_instance = None


def key_directory():
    """Where the key lives: beside the database, per-user, not in the repo."""
    from app import get_data_dir
    return get_data_dir()


def key_path():
    return os.path.join(key_directory(), 'pharmacy.key')


def _load_or_create_key():
    """
    Read the existing key, or create one on first use.

    Creating the key is deferred until the first encrypted write, so a user who
    disables encryption never accumulates a key file they do not need. The key
    is written with restrictive permissions where the OS honours them.
    """
    path = key_path()
    if os.path.exists(path):
        with open(path, 'rb') as handle:
            key = handle.read().strip()
        if key:
            return key

    key = Fernet.generate_key()
    os.makedirs(key_directory(), exist_ok=True)
    with open(path, 'wb') as handle:
        handle.write(key)
    try:
        # Best effort: on Windows this sets a DACL that removes broad access.
        os.chmod(path, 0o600)
    except OSError:
        pass

    # A note beside the key, so whoever finds it understands what it is and
    # what losing it means.
    note = os.path.join(key_directory(), 'pharmacy.key.README.txt')
    if not os.path.exists(note):
        with open(note, 'w', encoding='utf-8') as handle:
            handle.write(
                'This is the encryption key for your pharmacy database.\n\n'
                'The patient names, phone numbers and addresses in the app are\n'
                'encrypted with this key. KEEP IT WITH YOUR DATABASE BACKUP.\n\n'
                'If this file is lost, the encrypted data CANNOT be recovered.\n'
                'Do not email it or upload it anywhere. Copy it only when you\n'
                'copy the database itself.\n')
    return key


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


def is_encrypted(value):
    return bool(value) and str(value).startswith(PREFIX)


# --- Transparent column types ----------------------------------------------
#
# A TypeDecorator encrypts on write and decrypts on read, so the rest of the
# application keeps treating these columns as ordinary strings. NOTHING that
# reads a patient's name needs to know encryption exists - and that matters,
# because a security change that requires touching every reader will be
# incomplete somewhere and leak plaintext through the one path that was missed.
#
# SQLite does not enforce column types, so existing databases adopt these types
# with no migration: the next write of each field is encrypted, and values
# written before are read back as plaintext by the pass-through in decrypt().
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
