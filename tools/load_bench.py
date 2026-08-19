#!/usr/bin/env python3
"""
load_bench.py — time disc activity at each GAME > FAST LOADING level.

Measures with cdrom_bursts, which records per-burst wall ms and sector counts
straight from the CD device, rather than by timing a screen transition: a
transition also contains guest processing and presentation, so it cannot say
whether an unchanged number means "the drive is already not the bottleneck" or
"the setting did not take". Sectors delivered per burst is the check that the
setting engaged at all.

  bench            summarise disc bursts since boot at the current setting
  level N          set 0 off / 1 fast / 2 instant, then summarise
  window N SECS    zero the reference, wait, and report only what moved
                   (this is the one to use around an in-game load)
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "psxrecomp", "tools"))
from debug_client import query  # noqa: E402

HOST, PORT = "127.0.0.1", 4370
_id = [0]


def cmd(**kw):
    _id[0] += 1
    kw["id"] = _id[0]
    r = query(HOST, PORT, kw)
    if not r.get("ok", True):
        raise SystemExit("failed: %s -> %s" % (kw, r))
    return r


def bursts(count=128):
    return cmd(cmd="cdrom_bursts", count=count)


def summarise(tag, rows, total):
    if not rows:
        print("  %-10s no bursts recorded" % tag)
        return
    ms = sum(b["ms"] for b in rows)
    sec = sum(b["sectors"] for b in rows)
    div = sorted({b["divisor"] for b in rows})
    print("  %-10s %3d bursts  %7d sectors  %7d ms  %6.1f sectors/s  divisor%s %s"
          % (tag, len(rows), sec, ms, (sec / (ms / 1000.0)) if ms else 0.0,
             "" if len(div) == 1 else "s", ",".join(str(d) for d in div)))
    print("             (device burst total since boot: %d)" % total)


def key(b):
    return (b["start_frame"], b["end_frame"], b["sectors"])


def main():
    a = sys.argv[1:]
    if not a or a[0] == "bench":
        r = bursts()
        summarise("current", r["bursts"], r["total"])
    elif a[0] == "level":
        lv = int(a[1])
        r = cmd(cmd="fast_loads", level=lv)
        print("level=%d divisor=%d instant_budget=%d"
              % (r["level"], r["divisor"], r["instant_budget"]))
    elif a[0] == "window":
        lv = int(a[1])
        secs = float(a[2]) if len(a) > 2 else 20.0
        r = cmd(cmd="fast_loads", level=lv)
        print("level=%d divisor=%d budget=%d — measuring %.0fs, do the load NOW"
              % (r["level"], r["divisor"], r["instant_budget"], secs))
        before = {key(b) for b in bursts()["bursts"]}
        t0 = time.time()
        while time.time() - t0 < secs:
            time.sleep(0.5)
        after = bursts()
        fresh = [b for b in after["bursts"] if key(b) not in before]
        summarise("level %d" % lv, fresh, after["total"])
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
