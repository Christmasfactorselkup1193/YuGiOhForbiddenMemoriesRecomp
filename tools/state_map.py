#!/usr/bin/env python3
"""state_map.py — what the game-state global reads on each screen.

Loads every savestate slot in turn and records the state halfword plus the
shape of the three ALL CARDS trunk regions, so a gate for the save-writing
CHEATS rows can be chosen from measurement instead of from a guess.
"""
import os, sys, time, struct

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'psxrecomp', 'tools'))
import debug_client

HOST, PORT = '127.0.0.1', 4370
SHOT = os.environ['SHOTDIR']
STATE = 0x8009B23A
BASES = [0x801D0250, 0x801D3250, 0x80105D98]
DECK = 0x801D0200


def q(c):
    return debug_client.query(HOST, PORT, c)


def read(a, n):
    return bytes.fromhex(q({'cmd': 'read_ram', 'addr': '0x%08X' % a, 'len': n})['hex'])


def deck_ok():
    """40 u16 card ids, each 1..722, non-decreasing — the save struct's own
    signature, and the cheapest evidence that a save is actually resident."""
    b = read(DECK, 80)
    ids = struct.unpack('<40H', b)
    good = all(1 <= i <= 722 for i in ids)
    sortd = all(ids[i] <= ids[i + 1] for i in range(39))
    return good, sortd, ids[:6]


def shape(a):
    t = read(a, 722)
    return (sum(1 for x in t if x), max(t))


def main():
    slots = [int(x) for x in sys.argv[1:]] or list(range(12))
    for s in slots:
        r = q({'cmd': 'savestate', 'op': 'load', 'slot': s})
        if not r.get('ok'):
            print('slot %2d  load failed: %s' % (s, r)); continue
        time.sleep(3.0)
        try:
            st = struct.unpack('<H', read(STATE, 2))[0]
            g, so, head = deck_ok()
            shapes = ' '.join('nz=%3d/max=%3d' % shape(a) for a in BASES)
            print('slot %2d  state=0x%04X  deck_ok=%d sorted=%d %s | %s' %
                  (s, st, g, so, head, shapes), flush=True)
        except Exception as e:
            print('slot %2d  read failed: %s' % (s, e), flush=True)
        q({'cmd': 'screenshot_present', 'path': '%s/slot%02d.png' % (SHOT, s)})
        time.sleep(1.0)


if __name__ == '__main__':
    main()
