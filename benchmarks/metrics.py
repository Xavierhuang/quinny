"""The full scorecard: tokens, time, and correctness — with and without Quinny.

A (no Quinny)  = one-shot: write the module, stop.
B (with Quinny) = the verify loop: write it, `quinny verify`, fix the failures, repeat.

Both graded by an INDEPENDENT held-out suite. Every model call (generation, fixes,
AND verify's own test generation) is metered, so the token cost is the TRUE total.
Set the model via QUINNY_MODEL + the matching credentials env.
"""
import os
import sys
import time
import statistics
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks"))
sys.path.insert(0, str(ROOT / "scripts"))

from quinny._capabilities import make_client as _real_make_client  # noqa: E402
import quinny.contract as QC  # noqa: E402
import verify_loop as V  # noqa: E402

RUNS = int(os.environ.get("QUINNY_RUNS", "2"))
_METER = {"in": 0, "out": 0}


def _meter(usage):
    _METER["in"] += getattr(usage, "input_tokens", 0)
    _METER["out"] += getattr(usage, "output_tokens", 0)


class _MStream:
    def __init__(self, s): self._s = s
    @property
    def text_stream(self): return self._s.text_stream
    def get_final_message(self):
        m = self._s.get_final_message(); _meter(m.usage); return m


class _MStreamCM:
    def __init__(self, cm): self._cm = cm
    def __enter__(self): return _MStream(self._cm.__enter__())
    def __exit__(self, *a): return self._cm.__exit__(*a)


def _metered_stream(it):
    out = 0
    for ev in it:
        if ev.type == "message_start":
            _METER["in"] += ev.message.usage.input_tokens
        elif ev.type == "message_delta" and getattr(ev, "usage", None) is not None:
            out = ev.usage.output_tokens          # cumulative; last one is the total
        yield ev
    _METER["out"] += out


class _MMsg:
    def __init__(self, r): self._r = r
    def create(self, **k):
        if k.get("stream"):
            return _metered_stream(self._r.create(**k))
        resp = self._r.create(**k); _meter(resp.usage); return resp
    def stream(self, **k):
        return _MStreamCM(self._r.stream(**k))


class _MClient:
    def __init__(self, r): self.messages = _MMsg(r.messages)


def _factory():
    return _MClient(_real_make_client())


# Route every quinny model call through the meter.
QC.make_client = _factory
V.make_client = _factory


def _reset():
    _METER["in"] = 0; _METER["out"] = 0


def measure_A():
    _reset(); t = time.time()
    d = Path(tempfile.mkdtemp(prefix="mA_"))
    V.generate(d)
    dt = time.time() - t
    p, tot = V.bench.grade_holdout(d, V.TASK)
    return dict(tok_in=_METER["in"], tok_out=_METER["out"], secs=dt, passed=p, total=tot)


def measure_B():
    _reset(); t = time.time()
    (p, tot), rounds = V.loop()
    dt = time.time() - t
    return dict(tok_in=_METER["in"], tok_out=_METER["out"], secs=dt,
                passed=p, total=tot, rounds=rounds)


def main() -> int:
    print(f"Task: {V.TASK}  ·  model: {V.MODEL}  ·  {RUNS} runs each\n", flush=True)
    A = []
    for i in range(RUNS):
        r = measure_A(); A.append(r)
        print(f"  A run {i}: {r['passed']}/{r['total']}  "
              f"{r['tok_in']+r['tok_out']:,} tok  {r['secs']:.0f}s", flush=True)
    B = []
    for i in range(RUNS):
        r = measure_B(); B.append(r)
        print(f"  B run {i}: {r['passed']}/{r['total']}  "
              f"{r['tok_in']+r['tok_out']:,} tok  {r['secs']:.0f}s  "
              f"({r['rounds']} fix round(s))", flush=True)

    def agg(rows, key): return statistics.mean(r[key] for r in rows)
    tot = A[0]["total"]

    print(f"{'':26} {'tokens (in+out)':>18} {'time':>8} {'correctness':>13}")
    print("-" * 68)
    for label, rows in [("A  one-shot (no Quinny)", A), ("B  verify-loop (Quinny)", B)]:
        ti, to = agg(rows, "tok_in"), agg(rows, "tok_out")
        print(f"{label:26} {int(ti+to):>10,} ({int(ti):,}+{int(to):,})"
              f" {agg(rows,'secs'):>6.0f}s {agg(rows,'passed'):>6.1f}/{tot} "
              f"= {100*agg(rows,'passed')/tot:>3.0f}%")
    ta = agg(A, "tok_in") + agg(A, "tok_out")
    tb = agg(B, "tok_in") + agg(B, "tok_out")
    print("-" * 68)
    print(f"cost of Quinny: {tb/ta:.1f}x tokens, {agg(B,'secs')/agg(A,'secs'):.1f}x time  "
          f"→  correctness {100*agg(A,'passed')/tot:.0f}% → {100*agg(B,'passed')/tot:.0f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
