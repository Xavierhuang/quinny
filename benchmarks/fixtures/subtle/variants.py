"""Generators for `subtle_kv.py` impls with narrowly-chosen defects.

Each helper returns the source of a module implementing the SubtleKV spec.
The `flags` dict lets us turn each defect on/off, so we know exactly which
criteria a variant should satisfy — same pattern as `kv_source` in
`verify_usability.py`.

Defects modeled (each maps 1:1 to a criterion in fixtures/subtle/spec.qn):

  off_by_one_capacity : allow N+1 live keys instead of N.
  silent_nan          : sum_values skips NaN silently → wrong total.
  no_unicode_norm     : "café" NFC vs NFD are different keys.
  wrong_exception     : raise Exception (or generic error) instead of KeyError.
  ttl_overflow        : ttl calc wraps for huge values.
  ttl_zero_means_none : ttl=0 treated as "no ttl" instead of "already expired".

The generated module exposes a flat function API — `set`, `get`, `exists`,
`sum_values`, `capacity_of`, `make_store` — so the emitted suite can call
symbols directly by name.
"""
from __future__ import annotations

DEFECTS = (
    "off_by_one_capacity",
    "silent_nan",
    "no_unicode_norm",
    "wrong_exception",
    "ttl_overflow",
    "ttl_zero_means_none",
)


def source(**flags: bool) -> str:
    """Return a subtle_kv.py source with the requested defects enabled."""

    # Capacity slack. Correct: at most `capacity` live keys. Buggy off-by-one:
    # allows `capacity + 1` (one extra) — the classic "evict when we're over"
    # loop with the wrong comparison.
    cap_slack = "1" if flags.get("off_by_one_capacity") else "0"

    # sum_values behavior: strict returns NaN if any NaN present; silent skips.
    if flags.get("silent_nan"):
        sum_body = (
            "        total = 0.0\n"
            "        for v in [x[0] for x in self._d.values()]:\n"
            "            if isinstance(v, (int, float)) and v == v:  # skip NaN\n"
            "                total += v\n"
            "        return total"
        )
    else:
        sum_body = (
            "        import math\n"
            "        total = 0.0\n"
            "        for v in [x[0] for x in self._d.values()]:\n"
            "            if not isinstance(v, (int, float)):\n"
            "                continue\n"
            "            if isinstance(v, float) and math.isnan(v):\n"
            "                return float('nan')\n"
            "            total += v\n"
            "        return total"
        )

    # unicode normalization on the key path
    if flags.get("no_unicode_norm"):
        norm = "        pass"
    else:
        norm = "        import unicodedata\n        key = unicodedata.normalize('NFC', key)"

    # missing-key error path
    if flags.get("wrong_exception"):
        missing = "raise Exception('missing key')"
    else:
        missing = "raise KeyError(key)"

    # ttl deadline calculation
    if flags.get("ttl_overflow"):
        ttl_expr = "(self.time_fn() + ttl) & 0xFFFFFFFF"
    else:
        ttl_expr = "self.time_fn() + ttl"

    # ttl=0 semantics
    if flags.get("ttl_zero_means_none"):
        ttl_normalize = "        if ttl == 0: ttl = None   # bug: 0 is a valid TTL, not 'no ttl'"
    else:
        ttl_normalize = "        # ttl=0 stays 0 (immediately expired) — the correct behavior"

    return f'''import time
from collections import OrderedDict


class Store:
    def __init__(self, capacity=1024, time_fn=time.monotonic):
        self.capacity = capacity
        self.time_fn = time_fn
        self._d = OrderedDict()

    def _norm(self, key):
{norm}
        return key

    def _expired(self, key):
        v = self._d.get(key)
        if v is None:
            return True
        _, dl = v
        return dl is not None and self.time_fn() >= dl

    def set(self, key, value, ttl=None):
{ttl_normalize}
        key = self._norm(key)
        dl = None if ttl is None else {ttl_expr}
        if key in self._d:
            del self._d[key]
        self._d[key] = (value, dl)
        # Evict until we're at or below capacity (correct) or +1 (buggy).
        while (sum(1 for k in self._d if not self._expired(k))
                > self.capacity + {cap_slack}):
            # find first expired, else oldest
            for k in list(self._d):
                if self._expired(k):
                    del self._d[k]
                    break
            else:
                del self._d[next(iter(self._d))]

    def get(self, key):
        key = self._norm(key)
        if self._expired(key):
            self._d.pop(key, None)
            {missing}
        v, dl = self._d.pop(key)
        self._d[key] = (v, dl)
        return v

    def exists(self, key):
        key = self._norm(key)
        return not self._expired(key)

    def sum_values(self):
{sum_body}

    def __len__(self):
        return sum(1 for k in self._d if not self._expired(k))


# Module-level API. Every function takes an explicit store handle as its
# first arg (mirrors what real users write when they instantiate). The
# emitted suite passes the store around as a function argument.

def make_store(capacity=1024, time_fn=None):
    return Store(capacity=capacity, time_fn=(time_fn or time.monotonic))


def set(store, key, value, ttl=None):
    store.set(key, value, ttl=ttl)


def get(store, key):
    return store.get(key)


def exists(store, key):
    return store.exists(key)


def sum_values(store):
    return store.sum_values()


def capacity_of(store):
    return store.capacity


def len_store(store):
    return len(store)
'''


# criterion index (1-based, from fixtures/subtle/spec.qn) -> defect flag it targets
CRIT_FLAG = {
    1: "off_by_one_capacity",
    2: "silent_nan",
    3: "no_unicode_norm",
    4: "wrong_exception",
    5: "ttl_overflow",
    6: "ttl_zero_means_none",
}


def ground_truth(flags: dict) -> dict:
    """For each criterion i, True = should PASS given `flags`.
    A defect being enabled means the criterion it targets should FAIL."""
    return {i: not flags.get(flag, False) for i, flag in CRIT_FLAG.items()}
