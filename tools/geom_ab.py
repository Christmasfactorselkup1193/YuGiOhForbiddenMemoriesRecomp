#!/usr/bin/env python3
"""
geom_ab.py — A/B harness for [video] geometry_correction / perspective_texturing.

ENHANCEMENTS.md G1 records three conclusions about these two knobs that were
later retracted (G1.5 retracted by G1.6, G1.6's mechanism questioned by G1.7,
settled only by G1.8's isolation runs). Every one of them failed the same way:
a verdict drawn from a single observation, or from an instrument that could not
see the thing being judged. G1.6 therefore lays down a method rule — same
frame, same scene, off vs on — and G1.7 adds that the OFF control must actually
be run rather than assumed.

This script exists to make that protocol cheap enough that there is no reason
to shortcut it:

  * it drives the knobs through the debug server, so all four combinations hit
    ONE scene with no restart and no re-navigation;
  * it captures with screenshot_hires, because geometry correction lives only
    in the supersampled mirror and the plain `screenshot` resolves native
    15-bit VRAM — that blindness is what produced G1.5's wrong verdict;
  * it brackets the run with two OFF controls. If those two differ, the scene
    was moving and no comparison between the middle captures means anything.
    Read that first; it is the validity check for everything else.

Subcommands:
  census [seconds]   geometry_correction coverage over time (the G1.9 gate)
  ab <outdir>        the four-way capture matrix, control-bracketed
  state              read the knobs and free-running counters
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "psxrecomp", "tools"))
from debug_client import query  # noqa: E402

HOST = "127.0.0.1"
PORT = 4370
_id = [0]


def cmd(**kw):
    _id[0] += 1
    kw["id"] = _id[0]
    r = query(HOST, PORT, kw)
    if not r.get("ok", True):
        raise SystemExit("command failed: %s -> %s" % (kw, r))
    return r


def geom(geometry=None, perspective=None):
    """Read the census; optionally flip either knob first."""
    kw = {"cmd": "geom_correction"}
    if geometry is not None:
        kw["geometry"] = 1 if geometry else 0
    if perspective is not None:
        kw["perspective"] = 1 if perspective else 0
    return cmd(**kw)


def frame():
    # Not `ping`: that is answered lock-free on the debug server's IO thread and
    # carries no frame number. `frame` goes to the emu thread, like every other
    # command here, so the counter and the knobs move on the same timeline.
    return cmd(cmd="frame")["frame"]


def shot(path):
    """Hi-res capture. The native `screenshot` cannot see either enhancement."""
    cmd(cmd="screenshot_hires", path=path)
    return path


def pct(n, d):
    return (100.0 * n / d) if d else 0.0


def show(tag, s):
    lk = s["lookups"]
    print("  %-10s lookups %9d   hit %6.2f%%   unrecorded %6.2f%%   "
          "ambiguous %6.2f%%   persp_tris %d"
          % (tag, lk, pct(s["hits"], lk), pct(s["miss_unrecorded"], lk),
             pct(s["miss_ambiguous"], lk), s["perspective_triangles"]))


def snap():
    r = geom()
    return {"lookups": r["lookups"], "hits": r["geometry_vertex_hits"],
            "miss_unrecorded": r["miss_unrecorded"],
            "miss_ambiguous": r["miss_ambiguous"],
            "perspective_triangles": r["perspective_triangles"],
            "frame": frame()}


def delta(a, b):
    return {k: b[k] - a[k] for k in
            ("lookups", "hits", "miss_unrecorded", "miss_ambiguous",
             "perspective_triangles", "frame")}


def do_census(seconds):
    """Coverage over time.

    Sampled as deltas per window, not as one cumulative total. The cache marks
    a screen position ambiguous permanently (the generation only advances on a
    savestate-style invalidate), so a cumulative figure taken minutes in
    describes the accumulation as much as the scene. Per-window rates say what
    the feature is actually achieving right now; a share that climbs window
    over window on a still scene is the accumulation, not the geometry.
    """
    print("enabling geometry_correction (resets census, advances generation)")
    geom(geometry=True)
    marks = [1, 2, 5, 10, 20, 40, 60]
    marks = [m for m in marks if m <= seconds] or [seconds]
    prev = snap()
    t0 = time.time()
    print("\nper-window (delta between samples):")
    for m in marks:
        while time.time() - t0 < m:
            time.sleep(0.2)
        cur = snap()
        d = delta(prev, cur)
        show("t=%ds" % m, d)
        print("             %d frames in window" % d["frame"])
        prev = cur
    print("\ncumulative since enable:")
    show("total", snap())


def do_ab(outdir):
    os.makedirs(outdir, exist_ok=True)
    outdir = os.path.abspath(outdir)
    combos = [
        ("control_a", False, False),
        ("persp",     False, True),
        ("geom",      True,  False),
        ("both",      True,  True),
        ("control_b", False, False),
    ]
    results = []
    for tag, g, p in combos:
        geom(geometry=g, perspective=p)
        # Let the scene redraw with the new setting before capturing. The geom
        # cache is repopulated by the next frames' projections; capturing
        # immediately would photograph a cold cache.
        f0 = frame()
        while frame() < f0 + 8:
            time.sleep(0.05)
        before = snap()
        time.sleep(1.0)
        after = snap()
        path = os.path.join(outdir, "%s.png" % tag)
        shot(path)
        d = delta(before, after)
        print("[%s] geometry=%d perspective=%d" % (tag, g, p))
        show("1s", d)
        print("       -> %s" % path)
        results.append((tag, d))
    geom(geometry=False, perspective=False)
    print("\nknobs returned to off/off.")
    print("VALIDITY CHECK: compare control_a.png and control_b.png. If they "
          "differ, the scene moved during the run and the middle captures are "
          "not comparable — re-run on a still scene.")
    with open(os.path.join(outdir, "census.json"), "w") as fh:
        json.dump({t: d for t, d in results}, fh, indent=2)


def main():
    argv = sys.argv[1:]
    if not argv or argv[0] == "state":
        r = geom()
        print("geometry_correction  : %d" % r["geometry_correction"])
        print("perspective_texturing: %d" % r["perspective_texturing"])
        show("cumulative", {"lookups": r["lookups"],
                            "hits": r["geometry_vertex_hits"],
                            "miss_unrecorded": r["miss_unrecorded"],
                            "miss_ambiguous": r["miss_ambiguous"],
                            "perspective_triangles":
                                r["perspective_triangles"]})
    elif argv[0] == "census":
        do_census(int(argv[1]) if len(argv) > 1 else 20)
    elif argv[0] == "ab":
        do_ab(argv[1] if len(argv) > 1 else "geom_ab_out")
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
