#!/usr/bin/env python3
"""hud_probe.py — sample candidate "is the duel HUD on screen?" signals.

The rank meter is anchored to the FIELD box and must disappear whenever the
duel HUD does — attack animations, card views, the 3D monster fight, the
results screen. Rather than guess a signal, this records several candidates
once per sample alongside a screenshot, so the right one can be chosen by
correlating against what was actually on screen.

IMPORTANT: only run this against a HEALTHY duel. A soft-locked duel's frames
are degenerate (its main loop spins doing no work), so any signal derived from
one describes the bug, not the game.

    hud_probe.py watch [seconds] [interval]

Writes shot_NNN.png + probe.csv into $PSX_VRAMDIR/hudprobe.
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "psxrecomp", "tools"))
import gp0_decode as g  # noqa: E402

OUT = os.path.join(os.environ.get(
    "PSX_VRAMDIR",
    os.path.join(os.environ.get("TEMP", "."), "claude", "ygofm-vram")),
    "hudprobe")

# Candidate fingerprints, evaluated per frame over the decoded primitives.
# Kept plural on purpose: the first one that looks right in isolation is often
# the one that breaks on a screen nobody sampled.
CANDIDATES = {
    # The FIELD box itself: five rects out of texpage (704,0) via CLUT
    # (720,252), at x 12..68 / y 24..48.
    "fieldbox_clut":  lambda s: s["clut"] == (720, 252),
    "fieldbox_rect":  lambda s: (s["kind"] == "rect" and s["tp"][:2] == (704, 0)
                                 and s["clut"] == (720, 252)),
    "fieldbox_at_xy": lambda s: (s["kind"] == "rect" and 10 <= s["x"] <= 14
                                 and 22 <= s["y"] <= 26),
    # The LP panel to the right of it.
    "lp_panel":       lambda s: s["clut"] == (736, 252),
    # A hand card: 52x60 from the HUD page.
    "hand_card":      lambda s: (s["kind"] == "rect" and s["w"] == 52
                                 and s["h"] == 60),
    # Any card-stat digit — present on the HUD and on card views alike, so it
    # is expected to be a POOR signal. Recorded to prove that.
    "stat_digit":     lambda s: (s["kind"] == "rect" and s["w"] == 8
                                 and s["h"] == 8 and s["clut"] == (256, 241)),
}


def main():
    secs = float(sys.argv[2]) if len(sys.argv) > 2 else 180.0
    interval = float(sys.argv[3]) if len(sys.argv) > 3 else 0.8
    os.makedirs(OUT, exist_ok=True)
    csv = open(os.path.join(OUT, "probe.csv"), "w")
    csv.write("i,frame,nprims," + ",".join(CANDIDATES) + "\n")
    t0 = time.time()
    i = 0
    print("sampling for %.0fs — play normally and pass through each state"
          % secs, flush=True)
    while time.time() - t0 < secs:
        try:
            frame = int(g.cmd(cmd="get_registers")["frame"]) - 1
            ents, _ = g.fetch(frame)
            sp = g.decode(ents)
            counts = [sum(1 for s in sp if fn(s)) for fn in CANDIDATES.values()]
            shot = os.path.join(OUT, "shot_%03d.png" % i)
            g.cmd(cmd="screenshot", path=shot.replace("\\", "/"))
            csv.write("%d,%d,%d,%s\n"
                      % (i, frame, len(sp), ",".join(str(c) for c in counts)))
            csv.flush()
            if i % 10 == 0:
                print("  %3d  prims=%-4d %s" % (
                    i, len(sp),
                    " ".join("%s=%d" % (k, c)
                             for k, c in zip(CANDIDATES, counts))), flush=True)
        except Exception as e:
            print("  sample %d failed: %s" % (i, e), flush=True)
        i += 1
        time.sleep(interval)
    csv.close()
    print("done — %d samples in %s" % (i, OUT), flush=True)


if __name__ == "__main__":
    main()
