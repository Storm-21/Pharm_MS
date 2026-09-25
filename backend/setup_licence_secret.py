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


# --- Activation-token secret -------------------------------------------------
# The one-time activation tokens (app/activation.py) use their own secret and
# verifier, so that changing one scheme never invalidates licences issued under
# the other. Provisioned here too, because "run setup twice" is a step that gets
# forgotten and then a paid token cannot be verified.
TOKEN_DIR = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')),
                         'PharmMS')
TOKEN_FILE = os.path.join(TOKEN_DIR, 'token_secret.txt')


def load_token_secret():
    env = os.environ.get('PHARMS_TOKEN_SECRET')
    if env:
        return env.encode('utf-8')
    if os.path.isfile(TOKEN_FILE):
        with open(TOKEN_FILE, encoding='utf-8') as handle:
            value = handle.read().strip()
        if value:
            return value.encode('utf-8')
    return None


def create_token_secret(force=False):
    os.makedirs(TOKEN_DIR, exist_ok=True)
    if os.path.exists(TOKEN_FILE) and not force:
        return TOKEN_FILE, False
    value = secrets.token_urlsafe(SECRET_BYTES)
    with open(TOKEN_FILE, 'w', encoding='utf-8') as handle:
        handle.write(value)
    try:
        os.chmod(TOKEN_FILE, stat.S_IREAD | stat.S_IWRITE)
    except OSError:
        pass
    return TOKEN_FILE, True


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
        token_secret = load_token_secret()
        if token_secret:
            print('')
            print(f'Token file  : {TOKEN_FILE}')
            print(f'Token verify: {verifier_for(token_secret)}')
            print(f'    .\\build_exe.ps1 -TokenVerifier {verifier_for(token_secret)}')
        return 0

    path, created = create_secret(force=args.force)
    secret = load_secret()
    token_path, token_created = create_token_secret(force=args.force)
    token_secret = load_token_secret()

    if not created:
        print(f'A secret already exists at:')
        print(f'    {path}')
        print('')
        print('Leaving it alone - replacing it would invalidate every key you')
        print('have already issued. Use --force only if that is what you want.')
        if token_secret:
            print('')
            print(f'Activation tokens  : {TOKEN_FILE}')
            print(f'Token verifier     : {verifier_for(token_secret)}')
            if token_created:
                print('   (created now - pass it to the build with -TokenVerifier)')
        return 0

    print('=' * 62)
    print('  Licence + activation-token secrets created')
    print('=' * 62)
    print(f'  Key secret   : {path}')
    print(f'  Key verifier : {verifier_for(secret)}')
    print(f'  Token secret : {token_path}')
    print(f'  Token verify : {verifier_for(token_secret) if token_secret else "-"}')
    print('')
    print('  KEEP THESE FILES PRIVATE. They are stored outside the project so')
    print('  they cannot be committed. Anyone holding them can mint keys.')
    print('')
    print('  Next: build the app with the verifiers baked in -')
    print(f'      .\\build_exe.ps1 -LicenceVerifier {verifier_for(secret)} `')
    print(f'                      -TokenVerifier {verifier_for(token_secret) if token_secret else "<verifier>"}')
    print('=' * 62)
    return 0


if __name__ == '__main__':
    sys.exit(main())
