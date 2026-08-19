#!/usr/bin/env python3
"""rank_watch.py - live duel-rank meter for Yu-Gi-Oh! Forbidden Memories.

The duel rank is a single 0-99 score. It is NOT computed at duel end from
hidden state: the game keeps every input counter live in a per-player block,
and the end-of-duel routine just sums them. So the rank can be shown live.

Mechanism (recompiled at 0x80021598, helper at 0x80021558):

    score = 50 + victory_modifier
    for kind in 0..9:
        score += lookup(kind, counter[kind])

    lookup(kind, v):                       # func_80021558
        p = 0x801798A8 + kind * 20         # 5 x (s16 threshold, s16 delta)
        while v >= p.threshold: p += 4
        return p.delta

The counter block is the duel-state struct at PLAYER_BLOCK, stride 0x20.
Player 0 is the human; its score lands at 0x80179A04 at duel end, player 1's
at 0x80179A08 (the routine writes word[base+44] and advances base by 4).

    rank_watch.py table            dump the coefficient table out of RAM
    rank_watch.py once             both players' counters, score and rank
    rank_watch.py watch [hz] [s]   live meter
    rank_watch.py check            recompute vs the duel-end oracle
    rank_watch.py log <file> [hz]  append CSV samples (for offline checking)

`check` is the self-test: after a duel ends, the oracle at 0x80179A04/08
holds the game's own score. If a recomputed score disagrees, the counter
mapping is wrong.
"""

import os
import struct
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "psxrecomp", "tools"))
from debug_client import query  # noqa: E402

HOST, PORT = "127.0.0.1", 4370

PLAYER_BLOCK = 0x800E9FF0     # player 0; player 1 at +0x20
BLOCK_STRIDE = 0x20
COEFF_TABLE = 0x801798A8      # 10 kinds x 5 x (s16 threshold, s16 delta)
RESULT_STRUCT = 0x801799D8    # +44 = player 0 score, +48 = player 1 score
SCORE_BASE = 50

# (kind, offset in block, width, signed, label)  -- kind None = display only.
# Labels are the game's own, read off the RESULTS OF DUEL screen: the same
# routine fills a 16-row display array at 0x801D5608 (stride 8, you/com), and
# every row's value matched its counter exactly.  Note +0x10 is AVERAGE DFD
# FACTOR, not the "duelist/deck id" the older RAM map called it.
FIELDS = [
    (None, 0x00, 1, True,  "victory bonus"),
    (0,    0x01, 1, False, "turns"),
    (1,    0x02, 1, False, "effective attacks"),
    (2,    0x03, 1, False, "defensive wins"),
    (3,    0x04, 1, False, "face-down plays"),
    (4,    0x05, 1, False, "pure magic"),
    (5,    0x06, 1, False, "trigger trap"),
    (None, 0x07, 1, False, "combo plays"),
    (8,    0x08, 1, False, "initiate fusion"),
    (9,    0x09, 1, False, "equip magic"),
    (None, 0x0A, 1, False, "change field"),
    (None, 0x0B, 1, False, "card destruction"),
    (None, 0x0C, 1, False, "defensive losses"),
    (None, 0x0E, 2, True,  "average atk factor"),
    (None, 0x10, 2, True,  "average dfd factor"),
    (7,    0x14, 2, True,  "remaining LP"),
    (6,    0x18, 1, True,  "cards used"),
]

KIND_NAME = {k: lab for k, _o, _w, _s, lab in FIELDS if k is not None}

_id = [0]


def cmd(**kw):
    _id[0] += 1
    kw["id"] = _id[0]
    r = query(HOST, PORT, kw)
    if not r.get("ok", True):
        raise SystemExit("debug server refused %s -> %s" % (kw, r))
    return r


def read(addr, length):
    r = cmd(cmd="read_ram", addr="0x%08X" % addr, len=length)
    return bytes.fromhex(r["hex"])


def read_table():
    """Return {kind: [(threshold, delta) x5]} or None if not resident.

    The table is not in the EXE image - it arrives with a disc load - so it
    reads as zeros outside a duel. Validate rather than trust.
    """
    raw = read(COEFF_TABLE, 200)
    tbl = {}
    for kind in range(10):
        pairs = [struct.unpack_from("<hh", raw, kind * 20 + i * 4)
                 for i in range(5)]
        thr = [t for t, _d in pairs]
        if thr[-1] != 32767 or thr != sorted(thr):
            return None
        tbl[kind] = pairs
    return tbl


def lookup(tbl, kind, value):
    for thr, delta in tbl[kind]:
        if value < thr:
            return delta
    return tbl[kind][-1][1]


def read_counters(player):
    base = PLAYER_BLOCK + player * BLOCK_STRIDE
    raw = read(base, 0x1A)
    out = {}
    for kind, off, w, sg, lab in FIELDS:
        fmt = {(1, False): "B", (1, True): "b",
               (2, False): "<H", (2, True): "<h"}[(w, sg)]
        out[lab] = (kind, struct.unpack_from(fmt, raw, off)[0])
    return out


def score_of(tbl, counters):
    total = SCORE_BASE
    parts = []
    for lab, (kind, val) in counters.items():
        if kind is None:
            continue
        d = lookup(tbl, kind, val)
        total += d
        parts.append((lab, val, d))
    vb = counters["victory bonus"][1]
    total += vb
    parts.insert(0, ("victory bonus", vb, vb))
    return total, parts


def rank_of(score):
    """0-99 score -> rank label. High is POWER, low is TECHNIQUE."""
    s = max(0, min(99, score))
    letters = "DCBAS"
    if s >= 50:
        return "%s-POW" % letters[(s - 50) // 10]
    return "%s-TEC" % letters[(49 - s) // 10]


def show(tbl, verbose=True):
    lines = []
    for p in (0, 1):
        c = read_counters(p)
        total, parts = score_of(tbl, c)
        who = "YOU " if p == 0 else "OPP "
        lines.append("%s score %3d  ->  %s   (clamped %d)"
                     % (who, total, rank_of(total), max(0, min(99, total))))
        if verbose:
            for lab, val, d in parts:
                if val or d:
                    lines.append("       %-20s %6d  %+4d" % (lab, val, d))
    return "\n".join(lines)


def oracle():
    raw = read(RESULT_STRUCT + 44, 8)
    return struct.unpack_from("<i", raw, 0)[0], struct.unpack_from("<i", raw, 4)[0]


def main():
    op = sys.argv[1] if len(sys.argv) > 1 else "once"

    if op == "table":
        tbl = read_table()
        if tbl is None:
            raise SystemExit("coefficient table not resident "
                             "(zeros outside a duel) - start a duel first")
        for kind in range(10):
            print("kind %d  %-18s %s" % (
                kind, KIND_NAME.get(kind, "?"),
                "  ".join("<%6d:%+3d>" % pr for pr in tbl[kind])))
        return

    tbl = read_table()
    if tbl is None:
        raise SystemExit("coefficient table not resident - not in a duel")

    if op == "once":
        print(show(tbl))
    elif op == "watch":
        hz = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
        secs = float(sys.argv[3]) if len(sys.argv) > 3 else 60.0
        end = time.time() + secs
        last = None
        while time.time() < end:
            s = show(tbl, verbose=False)
            if s != last:
                print("[%7.1fs] %s" % (secs - (end - time.time()),
                                       s.replace("\n", " | ")))
                last = s
            time.sleep(1.0 / hz)
    elif op == "check":
        o0, o1 = oracle()
        c0, c1 = read_counters(0), read_counters(1)
        s0, _ = score_of(tbl, c0)
        s1, _ = score_of(tbl, c1)
        print("player 0: recomputed %3d   oracle %3d   %s"
              % (s0, o0, "MATCH" if s0 == o0 else "*** MISMATCH ***"))
        print("player 1: recomputed %3d   oracle %3d   %s"
              % (s1, o1, "MATCH" if s1 == o1 else "*** MISMATCH ***"))
        print("\nrank for player 0: %s" % rank_of(o0))
        print(show(tbl))
    elif op == "log":
        path = sys.argv[2]
        hz = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
        new = not os.path.exists(path)
        with open(path, "a") as f:
            if new:
                f.write("t,player," + ",".join(
                    lab for _k, _o, _w, _s, lab in FIELDS) + ",score\n")
            t0 = time.time()
            while True:
                for p in (0, 1):
                    c = read_counters(p)
                    tot, _ = score_of(tbl, c)
                    f.write("%.2f,%d,%s,%d\n" % (
                        time.time() - t0, p,
                        ",".join(str(c[lab][1])
                                 for _k, _o, _w, _s, lab in FIELDS), tot))
                f.flush()
                time.sleep(1.0 / hz)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
