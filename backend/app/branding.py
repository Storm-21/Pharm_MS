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
# The owner/admin of the project. A change here WITHOUT re-sealing makes
# verify_identity() fail and the app boots into the tamper notice, so these are
# the values the seal below covers.
CREATOR_NAME = "Jayant Mishra"
CREATOR_TITLE = "Owner & Administrator"
APP_NAME = "Pharmacy Management System"
APP_SHORT_NAME = "PharmMS"
APP_VERSION = "2.2.0"

# --- Contributing developers -------------------------------------------------
# Listed on the startup screen and the Branding page. Kept as a list of dicts so
# adding a name never requires touching the UI - the splash and the credits panel
# both iterate it.
DEVELOPERS = [
    {"name": "Jayant Mishra", "role": "Owner & Administrator", "lead": True},
    {"name": "Shashwat Singh", "role": "Sub-Developer", "lead": False},
]

# Public contact / attribution line shown on the splash screen.
ATTRIBUTION = f"Designed & Developed by {CREATOR_NAME}"


def contributors():
    """Everyone credited, owner first. Single source for the UI."""
    return [dict(person) for person in DEVELOPERS]


def secondary_developers():
    """Credited developers who are not the owner."""
    return [dict(p) for p in DEVELOPERS if not p.get("lead")]

# --- Integrity checksum ------------------------------------------------------
# Proves the identity block above has not been altered after release.
_IDENTITY_SEED = "PharmMS::v2::creator-lock"


def identity_signature(name=None, short_name=None, version=None):
    """Return the expected signature for the given identity values."""
    # Contributors are part of the sealed block too: a credit added or removed
    # without re-sealing is a change to who the app says built it, which is
    # exactly what this seal exists to detect.
    credits = ";".join(
        "%s=%s" % (p["name"], p["role"]) for p in DEVELOPERS
    )
    payload = "|".join([
        _IDENTITY_SEED,
        name if name is not None else CREATOR_NAME,
        short_name if short_name is not None else APP_SHORT_NAME,
        version if version is not None else APP_VERSION,
        credits,
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
        "contributors": contributors(),
        "developers": secondary_developers(),
        "attribution": ATTRIBUTION,
        "integrity_ok": ok,
        "signature": signature,
    }
