#!/usr/bin/env python3
"""
cpu_clock_test.py — is FM's 30fps bounded by its own workload?

`frame_gate` already ruled out the obvious mechanism: FM's VSync counter can be
driven at 5x and the loop does not speed up at all, so the frame rate is not
gated on that wait. The remaining likely cause is that one iteration of the
game's loop simply costs more than one vblank of PS1 CPU time.

`cpu_clock mult=K` charges fewer device-cycles per executed instruction, so the
CPU fits K times as much work into each frame while vblank, the root counters,
the CD and the SPU all keep their existing cadence. If the loop is workload-
bound, this unbinds it; if it is not, nothing moves.

Bracketed off -> on -> off, measuring:

  3D redraws/s    did the loop actually accelerate?
  guest frames/s  CONTROL. Must stay ~60. If it moves, host pacing is being
                  affected and the run says nothing about the CPU.
  SPU events/s    noisy proxy for audio activity; judge tempo by ear.

  python tools/cpu_clock_test.py [mult] [secs]
"""

import os
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "psxrecomp", "tools"))
from debug_client import query  # noqa: E402

HOST, PORT = "127.0.0.1", 4370
_id = [0]


def cmd(**kw):
    _id[0] += 1
    kw["id"] = _id[0]
    return query(HOST, PORT, kw)


def spu_total():
    r = cmd(cmd="audio_stats")
    return r.get("events_total")


def window(secs, label):
    t0 = time.time()
    s0 = spu_total()
    rows = []
    while time.time() - t0 < secs:
        ws = cmd(cmd="gpu_state").get("ws", {})
        rows.append((ws.get("cur_frame"), ws.get("last_3d_frame")))
    dt = time.time() - t0
    s1 = spu_total()

    frames = [r[0] for r in rows if r[0] is not None]
    seq, last = [], None
    for _, t in rows:
        if t is not None and t != last:
            seq.append(t)
            last = t
    gf = (frames[-1] - frames[0]) / dt if len(frames) > 1 else float("nan")
    r3 = len(seq) / dt
    steps = Counter(b - a for a, b in zip(seq, seq[1:]) if b > a)
    dom = steps.most_common(1)[0][0] if steps else None
    spu = ((s1 - s0) / dt) if (s0 is not None and s1 is not None) else float("nan")
    print("  %-10s guest %5.1f/s   3D redraws %5.1f/s (step +%s)   SPU %6.1f/s"
          % (label, gf, r3, dom, spu))
    return gf, r3, dom, spu


def main():
    mult = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    secs = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0

    cmd(cmd="cpu_clock", mult=1)
    print("BEFORE  (stock clock)")
    a = window(secs, "1x")

    print("\nOVERCLOCK x%d" % mult)
    print("  set ->", cmd(cmd="cpu_clock", mult=mult))
    b = window(secs, "%dx" % mult)

    cmd(cmd="cpu_clock", mult=1)
    print("\nAFTER   (back to stock) - validity check")
    c = window(secs, "1x")

    print("\n--- read it ---")
    print("guest frames  %.1f -> %.1f -> %.1f/s" % (a[0], b[0], c[0]))
    if abs(b[0] - a[0]) > 6:
        print("  ** guest frame rate MOVED - host pacing was affected, run INVALID **")
    print("3D redraws    %.1f -> %.1f -> %.1f/s   (%.2fx)"
          % (a[1], b[1], c[1], (b[1] / a[1]) if a[1] else float("nan")))
    print("step          +%s -> +%s -> +%s" % (a[2], b[2], c[2]))
    print("\nNow YOU judge, because no counter can:")
    print("  is the game PLAYING faster, or just drawing more often?")
    print("  is the music at the right tempo?")


if __name__ == "__main__":
    main()
