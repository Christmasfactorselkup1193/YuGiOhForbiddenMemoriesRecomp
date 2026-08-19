#!/usr/bin/env python3
"""
frame_gate_test.py — does unlocking FM's self-imposed 30fps cap keep the music?

Yu-Gi-Oh! FM caps ITSELF at 30: its main loop waits for two vblanks on the
counter at 0x80092AC8, and every second guest frame issues zero draw commands.
`frame_gate` injects extra ticks into that counter so the wait is satisfied
sooner and the loop runs faster — WITHOUT speeding host pacing, so the emulated
machine still runs at real time.

That distinction is the whole experiment. Three things can happen, and they
point in completely different directions:

  loop faster + music tempo unchanged
      the loop clock and the audio clock are separable. This is the result the
      "duel speed" feature needs, and it means the groundwork is done.
  loop faster + music faster
      the sound driver is ticked from the main loop and has to be found and
      isolated before any speed feature is safe.
  loop unchanged
      the cap is not (only) this counter; the wait has another gate.

Measured, not eyeballed:
  3D redraws/s   from ws.last_3d_frame  — did the loop actually accelerate?
  guest frames/s from ws.cur_frame      — CONTROL: host pacing must NOT move
  SPU key-ons/s  from audio_stats       — proxy for musical tempo

Key-on rate is a proxy, not a tempo readout: a busier passage raises it on its
own. So the run brackets the change with two OFF samples and reports all three,
rather than quoting a single before/after ratio. Compare like for like and
trust your ears over the number if they disagree.

  python tools/frame_gate_test.py [extra] [secs]
"""

import os
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "psxrecomp", "tools"))
from debug_client import query  # noqa: E402

HOST, PORT = "127.0.0.1", 4370
FM_VBLANK_COUNTER = "0x80092AC8"
_id = [0]


def cmd(**kw):
    _id[0] += 1
    kw["id"] = _id[0]
    return query(HOST, PORT, kw)


def kon_total():
    """Cumulative SPU activity, however this build spells it. events_total is
    the one this runtime actually exposes; the others are fallbacks so the
    harness survives a rename rather than silently reporting nothing."""
    r = cmd(cmd="audio_stats")
    for k in ("events_total", "kon", "key_ons", "keyons", "voice_keyons"):
        if isinstance(r.get(k), int):
            return r[k], k
    return None, None


def window(secs, label):
    """Sample for `secs`, return the three rates."""
    t0 = time.time()
    k0, kname = kon_total()
    rows = []
    while time.time() - t0 < secs:
        g = cmd(cmd="gpu_state")
        ws = g.get("ws", {})
        rows.append((ws.get("cur_frame"), ws.get("last_3d_frame")))
    dt = time.time() - t0
    k1, _ = kon_total()

    frames = [r[0] for r in rows if r[0] is not None]
    d3 = []
    last = None
    for _, t in rows:
        if t is not None and t != last:
            d3.append(t)
            last = t
    gf = (frames[-1] - frames[0]) / dt if len(frames) > 1 else float("nan")
    r3 = len(d3) / dt
    steps = Counter(b - a for a, b in zip(d3, d3[1:]) if b > a)
    dom = steps.most_common(1)[0][0] if steps else None
    kon = ((k1 - k0) / dt) if (k0 is not None and k1 is not None) else None

    print("  %-12s guest %.1f/s   3D redraws %.1f/s (dominant step +%s)%s"
          % (label, gf, r3, dom,
             ("   SPU key-ons %.1f/s [%s]" % (kon, kname)) if kon is not None else ""))
    return gf, r3, kon


def main():
    extra = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    secs = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0

    print("BEFORE (gate off) - control")
    cmd(cmd="frame_gate", extra=0)
    a = window(secs, "off")

    print("\nGATE ON  (extra=%d ticks per vblank)" % extra)
    r = cmd(cmd="frame_gate", addr=FM_VBLANK_COUNTER, extra=extra)
    print("  %s" % {k: r.get(k) for k in ("addr", "extra", "counter")})
    b = window(secs, "on")

    print("\nAFTER (gate off again) - the run's validity check")
    cmd(cmd="frame_gate", extra=0)
    c = window(secs, "off")

    print("\n--- read it ---")
    if a[1] and b[1]:
        print("3D redraw rate   %.1f -> %.1f/s  (%.2fx)" % (a[1], b[1], b[1] / a[1]))
    print("guest frame rate %.1f -> %.1f/s   <- must stay ~60; if it moved, host"
          " pacing changed and the run is invalid" % (a[0], b[0]))
    if a[2] and b[2]:
        print("SPU key-on rate  %.1f -> %.1f/s  (%.2fx)  [off-again: %.1f/s]"
              % (a[2], b[2], b[2] / a[2], c[2] if c[2] else float('nan')))
        print("   ~1.0x  -> audio clock is INDEPENDENT of the loop (what we want)")
        print("   ~2.0x  -> sound driver rides the main loop")
    print("\nAlso judge by ear and eye: is the game playing faster, and is the"
          "\nmusic at the right pitch/tempo? The counter cannot tell you that.")


if __name__ == "__main__":
    main()
