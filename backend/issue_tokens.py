"""
Vendor tool: mint, track and export single-use activation tokens.

This is the *selling* side of the ₹500 branding unlock. It is NOT shipped inside
the application - it holds the signing secret, and a build that carried it could
mint its own tokens.

SETUP, ONCE
-----------
    python setup_licence_secret.py          # generates the secret, once

The secret is stored outside the project (in %LOCALAPPDATA%\\PharmMS) so it can
never be committed by accident.

PER SALE
--------
    python issue_tokens.py --note "Sri Balaji Medicals" --count 1
    python issue_tokens.py --note "Bulk - medical camp" --count 20

The token is printed and appended to the token TABLE (an atomically-written JSON
file beside the secret). Nothing is emailed anywhere and no network is used.

BEFORE YOUR NEXT BUILD
----------------------
    python issue_tokens.py --export

This rewrites app/data/issued_tokens.py with everything you have sold, so the
build you ship can verify those tokens offline. It is the only step that couples
selling to releasing.

WHY THE TABLE AND NOT THE SECRET
--------------------------------
A shipped build contains the *signed token table*, never the signing secret. It
can therefore check a token without being able to create one - which means a
customer cannot mint an extra activation for a friend. The honest limit is that a
determined attacker who reverse-engineers the executable can extract the table
and re-enable a spent token in their own copy; that needs a server to prevent
(see app/activation.py, SERVER MODE).
"""

import argparse
import json
import os
import secrets
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import activation  # noqa: E402


def _secret_dir():
    """
    Where the signing secret and the token table live.

    Deliberately outside the project tree: .gitignore covers the project, but the
    safest place for the one thing that must never leak is somewhere no VCS is
    watching at all.
    """
    base = os.environ.get('LOCALAPPDATA') or os.path.expanduser('~')
    path = os.path.join(base, 'PharmMS')
    os.makedirs(path, exist_ok=True)
    return path


SECRET_PATH = os.path.join(_secret_dir(), 'token_secret.txt')
TABLE_PATH = os.path.join(_secret_dir(), 'issued_tokens.json')
EXPORT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'app', 'data', 'issued_tokens.py')


def _require_secret():
    """
    Load the signing secret, refusing to invent one silently.

    Generating a secret on demand would be worse than failing: a token minted
    against a fresh secret would not verify against a build sealed with the old
    one, and the customer would be told their key is wrong when the fault is here.
    """
    if os.environ.get(activation._TOKEN_SECRET_ENV):
        return

    if not os.path.exists(SECRET_PATH):
        print('No signing secret found at:')
        print('   ' + SECRET_PATH)
        print()
        print('Set this up once with:')
        print('   python setup_licence_secret.py')
        sys.exit(1)

    with open(SECRET_PATH, 'r', encoding='utf-8') as handle:
        secret = handle.read().strip()
    if not secret:
        print('The signing secret file is empty. Re-run setup_licence_secret.py.')
        sys.exit(1)
    os.environ[activation._TOKEN_SECRET_ENV] = secret


def load_table():
    if not os.path.exists(TABLE_PATH):
        return {}
    try:
        with open(TABLE_PATH, 'r', encoding='utf-8') as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError) as exc:
        print('Could not read the token table (%s). Starting a new one would '
              'orphan every token already sold, so this is fatal.' % exc)
        sys.exit(1)


def save_table(table):
    """
    Write the table atomically.

    A half-written token table is a customer whose paid key stopped working, so
    the new file is written to a temporary name and then moved into place - a
    crash mid-write leaves the previous table intact.
    """
    tmp = TABLE_PATH + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as handle:
        json.dump(table, handle, indent=2, sort_keys=True)
    os.replace(tmp, TABLE_PATH)


def cmd_mint(args):
    _require_secret()
    table = load_table()

    minted = []
    for _ in range(args.count):
        # Re-mint rather than loop: a collision in a 100-bit space is not a real
        # risk, but checking costs nothing and means the table can never contain
        # a duplicate that would silently overwrite a previous sale.
        while True:
            entry = activation.mint(note=args.note)
            if entry['body'] not in table:
                break
        table[entry['body']] = entry
        minted.append(entry)

    save_table(table)

    print()
    print('=' * 62)
    print('  Activation token%s issued%s' % (
        's' if len(minted) != 1 else '',
        ' - ' + args.note if args.note else ''))
    print('=' * 62)
    for entry in minted:
        print()
        print('   ' + entry['token'])
    print()
    print('-' * 62)
    print('Each token activates ONE installation, once, indefinitely.')
    print('Send the token to the customer; they enter it under Branding.')
    print()
    print('Before your next build, run:  python issue_tokens.py --export')
    print('=' * 62)
    print()


def cmd_list(args):
    table = load_table()
    if not table:
        print('No tokens have been issued yet.')
        return

    print()
    print('%-30s  %-12s  %s' % ('TOKEN', 'ISSUED', 'NOTE'))
    print('-' * 78)
    for body in sorted(table, key=lambda b: table[b].get('issued_at', '')):
        entry = table[body]
        print('%-30s  %-12s  %s' % (
            entry.get('token', 'PMS-' + body),
            entry.get('issued_at', ''),
            entry.get('note', '')))
    print('-' * 78)
    print('%d token(s) issued.' % len(table))
    print()
    print('At the current price that is a total of Rs.%s.' % (len(table) * 500))


def cmd_export(args):
    table = load_table()

    # The export is generated Python rather than JSON so the app can import it
    # without opening a file at runtime, which keeps the packaged build to a
    # single artefact and works read-only from the PyInstaller bundle.
    lines = [
        '"""',
        'Activation-token ledger - GENERATED FILE, DO NOT EDIT.',
        '',
        'Written by: python issue_tokens.py --export',
        'Generated:  %s' % datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
        'Contains:   %d token(s) you have issued.' % len(table),
        '',
        'These are the tokens the shipping build will accept. The signing secret is',
        'NOT in this file - only the per-token signatures needed to check that each',
        'entry was really issued by the vendor.',
        '',
        'A token is deliberately single-use: it appears here once and is redeemed',
        'once, on one machine. Re-running this export after selling more tokens is',
        'what lets the next build accept them.',
        '"""',
        '',
        'ISSUED_TOKENS = {',
    ]
    for body in sorted(table):
        entry = table[body]
        lines.append('    %r: {' % body)
        lines.append('        "token": %r,' % entry.get('token', ''))
        lines.append('        "note": %r,' % entry.get('note', ''))
        lines.append('        "issued_at": %r,' % entry.get('issued_at', ''))
        lines.append('        "signature": %r,' % entry.get('signature', ''))
        lines.append('    },')
    lines.append('}')
    lines.append('')

    with open(EXPORT_PATH, 'w', encoding='utf-8') as handle:
        handle.write('\n'.join(lines))

    print('Exported %d token(s) to:' % len(table))
    print('   ' + EXPORT_PATH)
    print()
    print('Build with this in place and the shipped app will accept those tokens:')
    print('   .\\build_exe.ps1')


def main():
    parser = argparse.ArgumentParser(
        description='Issue single-use PharmMS activation tokens.')
    parser.add_argument('--note', default='',
                        help='Who the token is for, e.g. the pharmacy name')
    parser.add_argument('--count', type=int, default=1,
                        help='How many tokens to mint (default 1)')
    parser.add_argument('--list', action='store_true',
                        help='List every token issued so far')
    parser.add_argument('--export', action='store_true',
                        help='Write the token table the shipping build needs')
    args = parser.parse_args()

    if args.export:
        cmd_export(args)
    elif args.list:
        cmd_list(args)
    else:
        if args.count < 1:
            print('--count must be at least 1.')
            sys.exit(1)
        cmd_mint(args)


if __name__ == '__main__':
    main()