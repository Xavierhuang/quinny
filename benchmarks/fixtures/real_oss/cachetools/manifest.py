"""Per-library test manifest for the real-OSS harness.

Each library under fixtures/real_oss/ has:
  - spec.qn              : the acceptance criteria
  - pristine_wrapper.py  : thin wrapper over the real library (all-PASS)
  - mutated_wrapper.py   : same wrapper with one narrowly-injected bug
  - manifest.py          : this file — declares variants + ground truth

The harness (benchmarks/verify_real_oss.py) is library-agnostic; it
picks up whichever library dir you pass via --library.
"""
from __future__ import annotations


# Optional human-readable metadata for the report header.
LIBRARY = "cachetools"
DESCRIPTION = "in-memory LRU + TTL caches (github.com/tkem/cachetools)"

# What to import at preflight to verify the library is installed.
IMPORT_CHECK = "cachetools"

# variant name -> wrapper source file in this dir
VARIANTS: dict[str, str] = {
    "pristine": "pristine_wrapper.py",
    "mutated_lru_no_recency": "mutated_wrapper.py",
}

# Ground truth: for each variant, which criterion indices should PASS.
# From spec.qn: 1-5 = LRU tests, 6-8 = TTL tests. The mutation targets
# criterion 3 (LRU-order after read).
GROUND_TRUTH: dict[str, dict[int, bool]] = {
    "pristine": {i: True for i in range(1, 9)},
    "mutated_lru_no_recency": {
        1: True, 2: True, 3: False, 4: True, 5: True,
        6: True, 7: True, 8: True,
    },
}
