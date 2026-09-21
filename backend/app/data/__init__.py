"""Data package for PharmacyMS reference data."""

from .seed_medicines import (
    MEDICINES as _BASE,
    DOSAGE_GUIDES as _BASE_GUIDES,
    DATA_VERSION,
    DATA_AUTHOR,
)
from .seed_medicines_extra import (
    EXTRA_MEDICINES as _EXTRA,
    EXTRA_DOSAGE_GUIDES as _EXTRA_GUIDES,
)
from .seed_medicines_batch3 import (
    BATCH3_MEDICINES as _BATCH3,
    BATCH3_GUIDES as _BATCH3_GUIDES,
)
from .seeder import ensure_seeded, OPENING_STOCK
# Single merged reference set used by the seeder and the importer.
MEDICINES = _BASE + _EXTRA + _BATCH3
DOSAGE_GUIDES = _BASE_GUIDES + _EXTRA_GUIDES + _BATCH3_GUIDES
__all__ = [
    "MEDICINES",
    "DOSAGE_GUIDES",
    "DATA_VERSION",
    "DATA_AUTHOR",
    "ensure_seeded",
    "OPENING_STOCK",
]
