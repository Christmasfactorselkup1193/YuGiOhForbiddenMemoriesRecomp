#!/usr/bin/env python3
"""
anim_rate.py — how many DISTINCT images per second does the game actually make?

The question behind "can this game look smoother": the presenter runs at 60,
but that says nothing about how often the game redraws. A title that animates
its 3D every other frame is a 30 fps game being presented 60 times a second,
and no amount of presentation work can add the missing images.

Measured without a new instrument, from counters gpu.c already keeps:

  ws.cur_frame        guest frame counter          -> guest frame rate
  ws.last_3d_frame    last frame that submitted 3D -> 3D REDRAW rate
  ws.gte_verts        vertices transformed         -> model size per redraw
  gp0_draw            cumulative draw commands     -> draws per guest frame

The number that answers the question is the STEP between successive
last_3d_frame values: 1 means the 3D is redrawn every guest frame (60), 2 means
every other one (30). The histogram is printed rather than an average, because
an average of 1s and 3s is a meaningless 2.

Sampling is best-effort over TCP (one command per connection), so frames can be
missed; a missed sample inflates a step. Steps are therefore reported as a
distribution and the run states its own sample coverage, rather than quoting a
single rate the sampling cannot support.

  python tools/anim_rate.py [seconds]
"""

import os
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "psxrecomp", "tools"))
from debug_client import query  # noqa: E402

HOST, PORT = "127.0.0.1", 4370


def sample():
    g = query(HOST, PORT, {"id": 1, "cmd": "gpu_state"})
    ws = g.get("ws", {})
    return (time.time(), ws.get("cur_frame"), ws.get("last_3d_frame"),
            ws.get("gte_verts"), g.get("gp0_draw"), g.get("depth24"),
            ws.get("last_world3d_frame"))


def main():
    secs = float(sys.argv[1]) if len(sys.argv) > 1 else 6.0
    rows = []
    t_end = time.time() + secs
    while time.time() < t_end:
        try:
            rows.append(sample())
        except Exception as e:
            print("sample failed:", type(e).__name__, e)
            break
    if len(rows) < 8:
        raise SystemExit("not enough samples (%d) - is the game running?" % len(rows))

    span = rows[-1][0] - rows[0][0]
    f0, f1 = rows[0][1], rows[-1][1]
    d0, d1 = rows[0][4], rows[-1][4]
    print("samples %d over %.2fs  (%.0f samples/s)" % (len(rows), span, len(rows) / span))
    print("depth24 during run: %s" % sorted({r[5] for r in rows}))

    if f0 is not None and f1 is not None:
        gf = (f1 - f0) / span
        print("guest frames      %.2f/s   (%d -> %d)" % (gf, f0, f1))
    if d0 is not None and d1 is not None:
        print("gp0 draw cmds     %.0f/s" % ((d1 - d0) / span))
        if f1 != f0:
            print("draws per frame   %.1f" % ((d1 - d0) / float(f1 - f0)))

    # 3D redraw cadence: unique last_3d_frame values and the step between them.
    seq, last = [], None
    for r in rows:
        v = r[2]
        if v is not None and v != last:
            seq.append((r[0], v))
            last = v
    if len(seq) < 3:
        print("\n3D redraws        NONE seen - this scene submits no 3D at all.")
        print("                  (a 2D screen cannot answer the question; try the")
        print("                   card library with a rotating model, or a duel)")
        return
    steps = Counter(b[1] - a[1] for a, b in zip(seq, seq[1:]) if b[1] > a[1])
    total = sum(steps.values())
    print("\n3D redraws        %.2f/s   (%d distinct 3D frames over %.2fs)"
          % (len(seq) / span, len(seq), span))
    print("step between consecutive 3D frames (guest frames):")
    for step, n in sorted(steps.items()):
        print("   +%-3d %6d  %5.1f%%   %s" % (step, n, 100.0 * n / total,
                                              "#" * int(40.0 * n / total)))
    verts = [r[3] for r in rows if r[3]]
    if verts:
        print("gte verts/redraw  min %d  max %d" % (min(verts), max(verts)))
    dom = steps.most_common(1)[0][0]
    print("\nreading: step 1 = 3D redrawn EVERY guest frame (60 fps animation);")
    print("         step 2 = every other frame (30 fps animation).")
    print("dominant step here: +%d" % dom)


if __name__ == "__main__":
    main()
