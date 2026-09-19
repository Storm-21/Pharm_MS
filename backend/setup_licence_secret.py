"""
Licence secret provisioning.

The signing secret must NOT be the placeholder in licensing.py when the app is
shipped for sale. Anyone who knows it can mint their own keys, which defeats
the whole point.

This script generates a strong secret and writes it to a file OUTSIDE the
project tree, so it is never committed and never ends up in the repository.
The build then bakes the sha256 verifier of that secret into the app, which is
enough to *check* keys without being able to *create* them.
"""

import hashlib
import os
import secrets
import stat
import sys

# Where the secret lives. Outside the project on purpose, and overridable.
DEFAULT_DIR = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')),
                           'PharmMS-Licensing')
SECRET_FILE = os.path.join(DEFAULT_DIR, 'issuer-secret.txt')

SECRET_BYTES = 32


def load_secret():
    """Read the issuer secret, or None if it has not been created yet."""
    env = os.environ.get('PHARMS_LICENCE_SECRET')
    if env:
        return env.encode('utf-8')
    if os.path.isfile(SECRET_FILE):
        with open(SECRET_FILE, encoding='utf-8') as handle:
            value = handle.read().strip()
        if value:
            return value.encode('utf-8')
    return None


def create_secret(force=False):
    """
    Generate and store a new issuer secret.

    Returns (path, created_bool). Refuses to overwrite an existing secret unless
    forced, because doing so would invalidate every key already issued.
    """
    os.makedirs(DEFAULT_DIR, exist_ok=True)

    if os.path.exists(SECRET_FILE) and not force:
        return SECRET_FILE, False

    value = secrets.token_urlsafe(SECRET_BYTES)
    with open(SECRET_FILE, 'w', encoding='utf-8') as handle:
        handle.write(value)

    # Best effort: restrict to the current user on Windows.
    try:
        os.chmod(SECRET_FILE, stat.S_IREAD | stat.S_IWRITE)
    except OSError:
        pass

    return SECRET_FILE, True


def verifier_for(secret_bytes):
    """The value that gets compiled into the shipping app."""
    return hashlib.sha256(secret_bytes).hexdigest()[:16]


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Provision the PharmMS licence-signing secret.')
    parser.add_argument('--force', action='store_true',
                        help='Overwrite an existing secret. INVALIDATES every key already issued.')
    parser.add_argument('--show', action='store_true',
                        help='Print the current secret and its verifier.')
    args = parser.parse_args()

    if args.show:
        secret = load_secret()
        if not secret:
            print(f'No secret found. Run this script without arguments first.')
            print(f'Expected location: {SECRET_FILE}')
            return 1
        print(f'Secret file : {SECRET_FILE}')
        print(f'Verifier    : {verifier_for(secret)}')
        print('')
        print('Pass this verifier to the build:')
        print(f'    .\\build_exe.ps1 -LicenceVerifier {verifier_for(secret)}')
        return 0

    path, created = create_secret(force=args.force)
    secret = load_secret()

    if not created:
        print(f'A secret already exists at:')
        print(f'    {path}')
        print('')
        print('Leaving it alone - replacing it would invalidate every key you')
        print('have already issued. Use --force only if that is what you want.')
        return 0

    print('=' * 62)
    print('  Licence signing secret created')
    print('=' * 62)
    print(f'  Location : {path}')
    print(f'  Verifier : {verifier_for(secret)}')
    print('')
    print('  KEEP THIS FILE PRIVATE. It is stored outside the project so it')
    print('  cannot be committed. Anyone holding it can mint licence keys.')
    print('')
    print('  Next: build the app with the verifier baked in -')
    print(f'      .\\build_exe.ps1 -LicenceVerifier {verifier_for(secret)}')
    print('=' * 62)
    return 0


if __name__ == '__main__':
    sys.exit(main())
