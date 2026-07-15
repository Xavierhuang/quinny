"""Cross-language evidence for `quinny verify`.

The SAME `.qn` contract, applied to JavaScript instead of Python. If verify
reliably passes a correct JS implementation and fails broken ones — with zero
false-passes, just like the Python benchmark — then a `.qn` acceptance contract
is genuinely language-agnostic, not a Python testing helper.

Same 5 variants as verify_usability.py (correct + one-axis-broken), but the
implementation is JavaScript and verify targets Node's built-in test runner.
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
RUNS = 1


def kv_source_js(lru: bool, ttl: bool, txn: bool) -> str:
    cap = "capacity" if lru else "1e9"
    dl = ("ttl === null || ttl === undefined ? null : this.timeFn() + ttl"
          if ttl else "null")
    if txn:
        tx = '''
  begin() { if (this._snap !== null) throw new Error("txn active"); this._snap = new Map(this._d); }
  commit() { if (this._snap === null) throw new Error("no txn"); this._snap = null; }
  rollback() { if (this._snap === null) throw new Error("no txn"); this._d = this._snap; this._snap = null; }'''
    else:
        tx = '''
  begin() {}
  commit() {}
  rollback() {}'''
    return f'''class MiniKV {{
  constructor(capacity, timeFn) {{
    this.capacity = {cap};
    this.timeFn = timeFn || (() => Date.now() / 1000);
    this._d = new Map();
    this._snap = null;
  }}
  _expired(k) {{
    if (!this._d.has(k)) return true;
    const dl = this._d.get(k)[1];
    return dl !== null && this.timeFn() > dl;
  }}
  set(key, value, ttl = null) {{
    const dl = {dl};
    if (this._d.has(key)) this._d.delete(key);
    this._d.set(key, [value, dl]);
    while ([...this._d.keys()].filter(k => !this._expired(k)).length > this.capacity) {{
      let evicted = false;
      for (const k of this._d.keys()) {{ if (this._expired(k)) {{ this._d.delete(k); evicted = true; break; }} }}
      if (!evicted) this._d.delete(this._d.keys().next().value);
    }}
  }}
  get(key) {{
    if (this._expired(key)) {{ this._d.delete(key); throw new Error("KeyError"); }}
    const [v, dl] = this._d.get(key); this._d.delete(key); this._d.set(key, [v, dl]); return v;
  }}
  delete(key) {{ if (this._expired(key)) {{ this._d.delete(key); return false; }} if (this._d.has(key)) {{ this._d.delete(key); return true; }} return false; }}
  exists(key) {{ if (this._expired(key)) {{ this._d.delete(key); return false; }} return this._d.has(key); }}{tx}
}}
module.exports = {{ MiniKV }};
'''


VARIANTS = {
    "correct": (True,  True,  True),
    "no_lru":  (False, True,  True),
    "no_ttl":  (True,  False, True),
    "no_txn":  (True,  True,  False),
    "stub":    (False, False, False),
}
CRIT_FEATURE = {1: "lru", 2: "lru", 3: "ttl", 4: "txn", 5: "txn", 6: "txn"}


def truth(flags):
    return {i: flags[f] for i, f in CRIT_FEATURE.items()}


def main() -> int:
    false_pass = false_fail = total = 0
    print(f"{'variant':10}  gating (JS)     verdict vs truth")
    print("-" * 50)
    for name, (lru, ttl, txn) in VARIANTS.items():
        flags = {"lru": lru, "ttl": ttl, "txn": txn}
        want = truth(flags)
        d = Path(tempfile.mkdtemp(prefix=f"js_{name}_"))
        (d / "mini_kv.js").write_text(kv_source_js(lru, ttl, txn))
        res = [r for r in verify(PLAN, d, MODEL, lang="js")
               if r.criterion.kind == "test"]
        got = {r.criterion.index: (r.status == "PASS") for r in res}
        idxs = sorted(want)
        row = "".join("P" if got.get(i) else "." for i in idxs)
        trow = "".join("P" if want[i] else "." for i in idxs)
        for i in idxs:
            total += 1
            if got.get(i) and not want[i]: false_pass += 1
            if not got.get(i) and want[i]: false_fail += 1
        print(f"{name:10}  got={row}     truth={trow}")
    print("-" * 50)
    print(f"\nLanguage: JavaScript (Node's built-in test runner)")
    print(f"False-PASS (missed a real defect): {false_pass}/{total}")
    print(f"False-FAIL (cried wolf on correct): {false_fail}/{total}")
    print(f"Accuracy: {total - false_pass - false_fail}/{total} "
          f"= {100*(total-false_pass-false_fail)/total:.0f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
