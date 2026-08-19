#!/usr/bin/env python3
"""
interp_probe.py — diagnose the frame-interpolation "missing background layer".

The interpolated present runs on a SECOND GL context, and that context is
touched by exactly two things: the interpolated quad and the OSD compositor.
gl_draw_osd_image_ex(blend=1) — the F10 menu bar — enables GL_BLEND and nothing
restores it. The main thread is accidentally immune (hr_end() disables blend
every guest frame); the presentation thread has no such reset, so the leak is
permanent once armed.

That matters because alpha on this path is the PSX MASK BIT, not coverage. A
blended quad therefore erases every VRAM pixel with mask 0 (a plain background
image) and keeps every mask-set draw (sprites/text) — one layer of the frame
disappears and the rest looks perfect.

  state       gl_interp once
  dump [pfx]  interp_dump — src / prev / curr + their alpha planes
  arm         open and close the F10 menu bar, reporting draw_blend around it
              (this is what arms the leak; run it to reproduce from clean)
  ab          full protocol: arm, then A/B state_fix 1 vs 0 with the dumps
  fix N       set state_fix 0|1
  alpha X     pin the crossfade factor (-1 = follow the frame clock)
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "psxrecomp", "tools"))
from debug_client import query  # noqa: E402

HOST, PORT = "127.0.0.1", 4370
K_F10 = 0x40000043
_id = [0]


def cmd(**kw):
    _id[0] += 1
    kw["id"] = _id[0]
    r = query(HOST, PORT, kw)
    if not r.get("ok", True):
        raise SystemExit("failed: %s -> %s" % (kw, r))
    return r


def state(**kw):
    return cmd(cmd="gl_interp", **kw)


def show(s, label=""):
    print("%-14s enabled=%d suspended=%d history=%d  %.1f/%.1f Hz  swaps=%s "
          "captures=%s" % (label, s["enabled"], s["suspended"], s["history"],
                           s["host_hz"], s["target_hz"], s["swaps"],
                           s.get("captures", "?")))
    print("%-14s tex=%dx%d scale=%d  src=(%d,%d %dx%d) path=%d force43=%d"
          % ("", s.get("tex_w", 0), s.get("tex_h", 0), s.get("scale", 0),
             s.get("src_x", 0), s.get("src_y", 0), s.get("src_w", 0),
             s.get("src_h", 0), s.get("source_path", -1),
             s.get("force_4_3", 0)))
    print("%-14s draw_blend=%s (src=%s dst=%s)  state_fix=%s alpha=%s"
          % ("", s.get("draw_blend"), s.get("draw_blend_src"),
             s.get("draw_blend_dst"), s.get("state_fix"),
             s.get("alpha_override")))
    return s


def dump(prefix):
    r = cmd(cmd="interp_dump", prefix=prefix)
    print("  wrote %d PNG (%dx%d) at %s_*"
          % (r["files"], r["width"], r["height"], r["prefix"]))
    print("  alpha>=128:  src %5.2f%%   prev %5.2f%%   curr %5.2f%%"
          % (r["src_alpha_hi_pct"], r["prev_alpha_hi_pct"],
             r["curr_alpha_hi_pct"]))
    print("  mean RGB:    src %6.2f    prev %6.2f    curr %6.2f"
          % (r["src_mean"], r["prev_mean"], r["curr_mean"]))
    return r


def arm():
    """Open then close the menu bar — the OSD draw that arms the blend leak."""
    print("before menu:")
    show(state(), "  ")
    cmd(cmd="menu_key", key=K_F10)
    time.sleep(0.6)
    print("menu open:")
    show(state(), "  ")
    cmd(cmd="menu_key", key=K_F10)
    time.sleep(0.6)
    print("menu closed:")
    return show(state(), "  ")


def main():
    argv = sys.argv[1:] or ["state"]
    op = argv[0]
    if op == "state":
        show(state(), "interp")
    elif op == "dump":
        show(state(), "interp")
        dump(argv[1] if len(argv) > 1 else "psx_interp")
    elif op == "arm":
        arm()
    elif op == "fix":
        show(state(state_fix=int(argv[1])), "interp")
    elif op == "alpha":
        show(state(alpha=float(argv[1])), "interp")
    elif op == "ab":
        print("=== 1. arm the OSD blend leak (open + close the F10 bar) ===")
        arm()
        print("\n=== 2. guard ON (state_fix=1) — expect a correct frame ===")
        state(state_fix=1)
        time.sleep(0.5)
        dump("psx_interp_fix1")
        input("    LOOK AT THE SCREEN. Background present? [enter] ")
        print("\n=== 3. guard OFF (state_fix=0) — the unguarded draw ===")
        state(state_fix=0)
        time.sleep(0.5)
        s = show(state(), "  ")
        dump("psx_interp_fix0")
        input("    LOOK AT THE SCREEN. Background gone? [enter] ")
        print("\n=== 4. guard back ON ===")
        state(state_fix=1)
        time.sleep(0.5)
        show(state(), "  ")
        print("\ndraw_blend at step 3 was %s — 1 means the presentation context "
              "inherited an armed GL_BLEND." % s.get("draw_blend"))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
