"""
Activation-token ledger - GENERATED FILE, DO NOT EDIT.

Written by: python issue_tokens.py --export
Generated:  2026-09-24 17:32 UTC
Contains:   2 token(s) you have issued.

These are the tokens the shipping build will accept. The signing secret is
NOT in this file - only the per-token signatures needed to check that each
entry was really issued by the vendor.

A token is deliberately single-use: it appears here once and is redeemed
once, on one machine. Re-running this export after selling more tokens is
what lets the next build accept them.
"""

ISSUED_TOKENS = {
    'DS54570X50VB4E4Z4Q7M': {
        "token": 'PMS-DS54-570X-50VB-4E4Z-4Q7M',
        "note": 'Sri Balaji Medicals',
        "issued_at": '2026-09-24',
        "signature": 'efe72418ed181afa98145c1b',
    },
    'HPXSST4D2A9X1QJGXQWT': {
        "token": 'PMS-HPXS-ST4D-2A9X-1QJG-XQWT',
        "note": 'Sri Balaji Medicals',
        "issued_at": '2026-09-24',
        "signature": 'a13fa4dfcfa10c941850078c',
    },
}
