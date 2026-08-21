#!/usr/bin/env python3
"""trunk_copies.py — how the three ALL CARDS destinations relate to each other
in every reachable state.  ALL CARDS writes all three unconditionally; this
measures which of them is actually the trunk at any given moment.
"""
import os, sys, time, struct

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'psxrecomp', 'tools'))
import debug_client

HOST, PORT = '127.0.0.1', 4370
LIVE, MIRROR, UI = 0x801D0250, 0x801D3250, 0x80105D98


def q(c):
    return debug_client.query(HOST, PORT, c)


def read(a, n):
    return bytes.fromhex(q({'cmd': 'read_ram', 'addr': '0x%08X' % a, 'len': n})['hex'])


def deck(a):
    ids = struct.unpack('<40H', read(a, 80))
    return all(1 <= i <= 722 for i in ids)


def diff(x, y):
    return sum(1 for i in range(722) if x[i] != y[i])


def main():
    for s in [int(v) for v in sys.argv[1:]] or list(range(12)):
        if not q({'cmd': 'savestate', 'op': 'load', 'slot': s}).get('ok'):
            continue
        time.sleep(2.5)
        live, mir, ui = read(LIVE, 722), read(MIRROR, 722), read(UI, 722)
        print('slot %2d  deck@1D0200=%d deck@1D3200=%d | '
              'live(max %3d)  mirror diff=%3d(max %3d)  ui diff=%3d(max %3d)' %
              (s, deck(0x801D0200), deck(0x801D3200), max(live),
               diff(live, mir), max(mir), diff(live, ui), max(ui)), flush=True)


if __name__ == '__main__':
    main()
