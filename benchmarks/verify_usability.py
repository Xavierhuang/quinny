"""Usability benchmark for `quinny verify`.

A verification tool is only useful if its verdicts match reality: it must PASS
correct code and FAIL broken code. We construct implementations of mini_kv with
KNOWN, exact defects (one axis broken at a time), run `quinny verify` against
each (twice, for consistency), and score its verdicts against ground truth.

Metrics:
  - false-PASS: verify said PASS on a criterion the impl genuinely fails
    (DANGEROUS — a gate that misses bugs is worse than useless).
  - false-FAIL: verify said FAIL on a criterion the impl satisfies
    (annoying — cries wolf on correct code).
  - consistency: same verdict across two independent generations.
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from quinny.contract import verify  # noqa: E402

PLAN = ROOT / "benchmarks" / "plans" / "mini_kv.good.qn"
MODEL = os.environ.get("QUINNY_MODEL", "claude-haiku-4-5")
RUNS = 2


def kv_source(lru: bool, ttl: bool, txn: bool) -> str:
    """A mini_kv.py whose LRU / TTL / transaction features can each be disabled,
    so we know exactly which acceptance criteria it should satisfy."""
    cap = "self.capacity = capacity" if lru else "self.capacity = 10**9"
    deadline = ("None if ttl is None else self.time_fn() + ttl" if ttl else "None")
    if txn:
        tx = '''
    def begin(self):
        if self._snap is not None: raise RuntimeError("txn active")
        self._snap = OrderedDict(self._d)
    def commit(self):
        if self._snap is None: raise RuntimeError("no txn")
        self._snap = None
    def rollback(self):
        if self._snap is None: raise RuntimeError("no txn")
        self._d = self._snap; self._snap = None'''
    else:
        tx = '''
    def begin(self): pass
    def commit(self): pass
    def rollback(self): pass'''
    return f'''import time
from collections import OrderedDict

class MiniKV:
    def __init__(self, capacity, time_fn=time.monotonic):
        {cap}
        self.time_fn = time_fn
        self._d = OrderedDict()
        self._snap = None
    def _expired(self, k):
        v = self._d.get(k)
        if v is None: return True
        _, dl = v
        return dl is not None and self.time_fn() > dl
    def set(self, key, value, ttl=None):
        dl = {deadline}
        if key in self._d: del self._d[key]
        self._d[key] = (value, dl)
        while sum(1 for k in self._d if not self._expired(k)) > self.capacity:
            for k in list(self._d):
                if self._expired(k): del self._d[k]; break
            else:
                del self._d[next(iter(self._d))]
    def get(self, key):
        if self._expired(key): self._d.pop(key, None); raise KeyError(key)
        v, dl = self._d.pop(key); self._d[key] = (v, dl); return v
    def delete(self, key):
        if self._expired(key): self._d.pop(key, None); return False
        if key in self._d: del self._d[key]; return True
        return False
    def exists(self, key):
        if self._expired(key): self._d.pop(key, None); return False
        return key in self._d
    def __len__(self):
        for k in list(self._d):
            if self._expired(k): del self._d[k]
        return len(self._d){tx}
'''


# variant -> (lru, ttl, txn)
VARIANTS = {
    "correct": (True,  True,  True),
    "no_lru":  (False, True,  True),
    "no_ttl":  (True,  False, True),
    "no_txn":  (True,  True,  False),
    "stub":    (False, False, False),
}
# criterion index (1-based, from mini_kv.good.qn) -> feature it needs
CRIT_FEATURE = {1: "lru", 2: "lru", 3: "ttl", 4: "txn", 5: "txn", 6: "txn", 7: "all"}


def ground_truth(flags: dict) -> dict:
    return {i: (all(flags.values()) if feat == "all" else flags[feat])
            for i, feat in CRIT_FEATURE.items()}


def main() -> int:
    false_pass = false_fail = total = 0
    inconsistent = 0
    print(f"{'variant':10} {'run':>3}  gating test criteria           verdict vs truth")
    print("-" * 74)
    for name, (lru, ttl, txn) in VARIANTS.items():
        flags = {"lru": lru, "ttl": ttl, "txn": txn}
        truth = ground_truth(flags)
        d = Path(tempfile.mkdtemp(prefix=f"vb_{name}_"))
        (d / "mini_kv.py").write_text(kv_source(lru, ttl, txn))
        run_verdicts = []
        for r in range(RUNS):
            results = verify(PLAN, d, MODEL)
            # Only concrete `test` criteria gate the build (mirrors `quinny
            # verify`); `success` summary lines are advisory, not scored.
            gating = [res for res in results if res.criterion.kind == "test"]
            verdict = {res.criterion.index: (res.status == "PASS") for res in gating}
            run_verdicts.append(verdict)
            idxs = sorted(verdict)
            row = "".join("P" if verdict[i] else "." for i in idxs)
            truthrow = "".join("P" if truth[i] else "." for i in idxs)
            for i in idxs:
                total += 1
                got, want = verdict[i], truth[i]
                if got and not want: false_pass += 1
                if not got and want: false_fail += 1
            print(f"{name:10} {r:>3}  got={row}      truth={truthrow}")
        for i in run_verdicts[0]:
            if run_verdicts[0].get(i) != run_verdicts[1].get(i):
                inconsistent += 1
    print("-" * 74)
    cells = total
    print(f"\nFalse-PASS (missed a real defect): {false_pass}/{cells}  "
          f"<- the dangerous one")
    print(f"False-FAIL (cried wolf on correct): {false_fail}/{cells}")
    print(f"Accuracy: {(cells - false_pass - false_fail)}/{cells} "
          f"= {100*(cells-false_pass-false_fail)/cells:.0f}%")
    print(f"Inconsistent verdicts across 2 runs: {inconsistent}/{cells//RUNS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
