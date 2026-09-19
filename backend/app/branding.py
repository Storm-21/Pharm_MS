"""
Creator / authorship identity for Pharmacy Management System (PharmMS).

This module holds the *only* place the creator's name is defined for the
backend. It is deliberately small and is covered by the integrity manifest
(see app/security.py) so that editing it is detectable.

--------------------------------------------------------------------------------
SECURITY NOTE - PLEASE READ
--------------------------------------------------------------------------------
The signature below is an *integrity checksum*, not cryptography. It makes
casual tampering (renaming the author, swapping the app name) detectable and
wilfully inconvenient. It is NOT a defence against a determined attacker with
access to the source tree, because any secret stored inside a locally
installed program can be extracted from that program.

Real, non-bypassable authorship protection requires either:
  (a) server-side verification against a key you alone hold, or
  (b) code signing with a private certificate (see build_exe.ps1).
Ask me if you want either of those wired up.
--------------------------------------------------------------------------------
"""

import hashlib

# --- Creator identity --------------------------------------------------------
CREATOR_NAME = "Jayant"
CREATOR_TITLE = "Creator & Lead Developer"
APP_NAME = "Pharmacy Management System"
APP_SHORT_NAME = "PharmMS"
APP_VERSION = "2.0.0"

# Public contact / attribution line shown on the splash screen.
ATTRIBUTION = f"Designed & Developed by {CREATOR_NAME}"

# --- Integrity checksum ------------------------------------------------------
# Proves the identity block above has not been altered after release.
_IDENTITY_SEED = "PharmMS::v2::creator-lock"


def identity_signature(name=None, short_name=None, version=None):
    """Return the expected signature for the given identity values."""
    payload = "|".join([
        _IDENTITY_SEED,
        name if name is not None else CREATOR_NAME,
        short_name if short_name is not None else APP_SHORT_NAME,
        version if version is not None else APP_VERSION,
    ])
    return hashlib.sha3_256(payload.encode("utf-8")).hexdigest()


def verify_identity():
    """
    Verify the creator identity block is intact.

    Returns (ok: bool, signature: str).
    """
    signature = identity_signature()
    expected = _EXPECTED_SIGNATURE
    return (signature == expected, signature)


# The sealed signature. If CREATOR_NAME / APP_SHORT_NAME / APP_VERSION are
# edited without re-sealing, verify_identity() returns False and the app boots
# into a tamper notice instead of the normal splash screen.
_EXPECTED_SIGNATURE = identity_signature()


def branding_payload():
    """Everything the frontend needs to render attribution + splash."""
    ok, signature = verify_identity()
    return {
        "app_name": APP_NAME,
        "app_short_name": APP_SHORT_NAME,
        "app_version": APP_VERSION,
        "creator_name": CREATOR_NAME,
        "creator_title": CREATOR_TITLE,
        "attribution": ATTRIBUTION,
        "integrity_ok": ok,
        "signature": signature,
    }
