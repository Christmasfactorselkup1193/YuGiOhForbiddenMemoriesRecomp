#!/usr/bin/env python3
"""
ram_scan.py — value scanner over guest RAM snapshots.

Finds "which address holds the thing that just changed" by taking whole-RAM
snapshots around a known player action and intersecting candidates across
several of them. This is the standard cheat-engine loop, and it is the
foundation for the rank meter, the drop-table extraction, and every other
RE task in ENHANCEMENTS.md.

Snapshots go to DISK via the `ram_dump_file` debug command, not over the
socket: the debug server is pumped on the emu thread, so a 2 MB response is
emulator time not spent emulating. One command per snapshot, diffing is
host-side and free.

  snap   <name>                  take a snapshot
  find   <name> <value>          u16/u32 cells equal to a KNOWN value
  refine <cands.txt> <name> <v>  keep only candidates now equal to v
  inc    <a> <b> [delta]         u8/u16/u32 that rose by exactly `delta`
  same   <a> <b>                 unchanged (use to eliminate noise)
  diff   <a> <b>                 changed at all
  and    <fileA> <fileB>         intersect two candidate lists
  watch  <addr> [n] [secs]       print a u32 (and u16/u8 view) over time

When the number is ON SCREEN (life points, starchips, hand size), prefer
find/refine — one known-value search beats several "what incremented" rounds:

    ram_scan.py snap a
    ram_scan.py find a 8000 > lp.txt        # LP showing 8000
    <take damage, now showing 7300>
    ram_scan.py snap b
    ram_scan.py refine lp.txt b 7300        # usually down to a handful

Typical hunt for a per-action counter:

    ram_scan.py snap base
    <do the action once>
    ram_scan.py snap after1
    ram_scan.py inc base after1 1 > c1.txt
    <do the action once more>
    ram_scan.py snap after2
    ram_scan.py inc after1 after2 1 > c2.txt
    ram_scan.py and c1.txt c2.txt

Two rounds usually cuts 2 MB of RAM to a handful of addresses. Anything that
survives is then fed to wtrace_range to find the code that writes it.
"""

import os
import struct
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "psxrecomp", "tools"))
from debug_client import query  # noqa: E402

HOST, PORT = "127.0.0.1", 4370
BASE = 0x80000000
# Stable, session-independent by default: the old default pointed inside one
# session's scratchpad directory, which stops existing the moment that session
# ends, so a later `snap` silently wrote somewhere unrelated to `inc`/`and`.
SNAPDIR = os.environ.get(
    "PSX_SNAPDIR",
    os.path.join(os.environ.get("TEMP", os.path.expanduser("~")),
                 "claude", "ygofm-ramsnaps"))
_id = [0]


def cmd(**kw):
    _id[0] += 1
    kw["id"] = _id[0]
    r = query(HOST, PORT, kw)
    if not r.get("ok", True):
        raise SystemExit("failed: %s -> %s" % (kw, r))
    return r


def path_for(name):
    os.makedirs(SNAPDIR, exist_ok=True)
    return os.path.join(SNAPDIR, name + ".bin")


def snap(name):
    p = path_for(name)
    r = cmd(cmd="ram_dump_file", addr="0x80000000", len=0x200000,
            path=p.replace("\\", "/"))
    print("snapshot %-12s %d bytes -> %s" % (name, r["len"], p))


def load(name):
    with open(path_for(name), "rb") as f:
        return f.read()


def scan(a, b, mode, delta=1):
    """Yield (addr, width, old, new) for cells matching the mode."""
    A, B = load(a), load(b)
    n = min(len(A), len(B))
    out = []
    for width, fmt, step in ((1, "B", 1), (2, "<H", 2), (4, "<I", 4)):
        lim = (1 << (8 * width))
        for off in range(0, n - width + 1, step):
            ov = struct.unpack_from(fmt, A, off)[0]
            nv = struct.unpack_from(fmt, B, off)[0]
            if mode == "same":
                ok = ov == nv
            elif mode == "diff":
                ok = ov != nv
            else:  # inc
                ok = nv == ((ov + delta) % lim)
            if ok and mode == "inc":
                out.append((BASE + off, width, ov, nv))
            elif ok and mode != "inc" and width == 4:
                out.append((BASE + off, width, ov, nv))
    return out


def emit(rows, label):
    print("# %s : %d candidates" % (label, len(rows)), file=sys.stderr)
    for addr, w, ov, nv in rows:
        print("0x%08X u%-2d %10d -> %10d" % (addr, w * 8, ov, nv))


def find_value(name, value):
    """Known-value search: every u16/u32 cell equal to `value`.

    Far more selective than a delta scan when the number is on screen (life
    points, starchips, hand size). One search on a displayed value usually
    beats several rounds of 'what incremented'.
    """
    A = load(name)
    out = []
    for width, fmt, step in ((2, "<H", 2), (4, "<I", 4)):
        if value >= (1 << (8 * width)):
            continue
        for off in range(0, len(A) - width + 1, step):
            if struct.unpack_from(fmt, A, off)[0] == value:
                out.append((BASE + off, width, value, value))
    return out


def refine(cands_file, name, value):
    """Keep only candidates whose cell now equals `value`."""
    A = load(name)
    keep = []
    for addr, wtag in sorted(read_list(cands_file)):
        w = int(wtag[1:]) // 8
        off = addr - BASE
        if off < 0 or off + w > len(A):
            continue
        fmt = {1: "B", 2: "<H", 4: "<I"}[w]
        if struct.unpack_from(fmt, A, off)[0] == value:
            keep.append((addr, w, value, value))
    return keep


def read_list(fn):
    s = set()
    for line in open(fn):
        line = line.strip()
        if line.startswith("0x"):
            parts = line.split()
            s.add((int(parts[0], 16), parts[1]))
    return s


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    op = sys.argv[1]
    if op == "snap":
        snap(sys.argv[2])
    elif op in ("inc", "same", "diff"):
        delta = int(sys.argv[4]) if len(sys.argv) > 4 else 1
        rows = scan(sys.argv[2], sys.argv[3], op, delta)
        emit(rows, "%s %s->%s delta=%s" % (op, sys.argv[2], sys.argv[3], delta))
    elif op == "find":
        rows = find_value(sys.argv[2], int(sys.argv[3]))
        emit(rows, "find %s == %s" % (sys.argv[2], sys.argv[3]))
    elif op == "refine":
        rows = refine(sys.argv[2], sys.argv[3], int(sys.argv[4]))
        emit(rows, "refine %s with %s == %s"
             % (sys.argv[2], sys.argv[3], sys.argv[4]))
    elif op == "and":
        a, b = read_list(sys.argv[2]), read_list(sys.argv[3])
        both = sorted(a & b)
        print("# intersect: %d" % len(both), file=sys.stderr)
        for addr, w in both:
            print("0x%08X %s" % (addr, w))
    elif op == "watch":
        addr = int(sys.argv[2], 16)
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        secs = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
        for _ in range(n):
            r = cmd(cmd="read_ram", addr="0x%08X" % addr, len=4)
            h = r.get("hex") or r.get("data") or ""
            b = bytes.fromhex(h)[:4] if h else b"\0\0\0\0"
            print("0x%08X  u32=%-10d u16=%-6d u8=%-4d  raw=%s"
                  % (addr, struct.unpack("<I", b)[0],
                     struct.unpack("<H", b[:2])[0], b[0], h))
            time.sleep(secs)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
