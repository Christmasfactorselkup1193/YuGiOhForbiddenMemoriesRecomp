#!/usr/bin/env python3
"""allcards_boot_watch.py — timeline of the three ALL CARDS trunk buffers
from launch, alongside the game-state halfword, so "what is 0x80105D98 during
the intro" is measured rather than assumed.

  python tools/allcards_boot_watch.py [seconds] [gap] [--fire AT_SECONDS]

--fire clicks CHEATS -> ALL CARDS at the given elapsed time, which is the
repro: the row's only guard is psx_mod_game_started(), true from the game
EXE's first instruction.
"""
import os, sys, time, hashlib, struct

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'psxrecomp', 'tools'))
import debug_client

HOST, PORT = '127.0.0.1', 4370
BASES = [0x801D0250, 0x801D3250, 0x80105D98]
STATE_HALF = 0x8009B23A

CHEATS_XY = (1047, 31)
ALLCARDS_XY = (1400, 400)


def q(d):
    return debug_client.query(HOST, PORT, d)


def read(addr, n):
    r = q({'cmd': 'read_ram', 'addr': '0x%08X' % addr, 'len': n})
    h = r.get('hex')
    return bytes.fromhex(h) if h else None


def tag(b):
    if b is None:
        return '   --                      '
    return '%s nz=%3d max=%3d' % (hashlib.sha1(b).hexdigest()[:8],
                                  sum(1 for x in b if x), max(b))


def fire():
    q({'cmd': 'menu_move', 'x': CHEATS_XY[0], 'y': CHEATS_XY[1]})
    q({'cmd': 'menu_click', 'x': CHEATS_XY[0], 'y': CHEATS_XY[1]})
    time.sleep(0.3)
    q({'cmd': 'menu_move', 'x': ALLCARDS_XY[0], 'y': ALLCARDS_XY[1]})
    q({'cmd': 'menu_click', 'x': ALLCARDS_XY[0], 'y': ALLCARDS_XY[1]})
    time.sleep(0.3)
    return q({'cmd': 'menu_state'})


def main():
    secs = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
    gap = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5
    fire_at = None
    if '--fire' in sys.argv:
        fire_at = float(sys.argv[sys.argv.index('--fire') + 1])

    t0 = time.time()
    fired = False
    while True:
        el = time.time() - t0
        if el > secs:
            break
        if fire_at is not None and not fired and el >= fire_at:
            print('--- firing ALL CARDS at t=%.1f ---' % el, flush=True)
            try:
                print('    menu_state after: %s' % fire(), flush=True)
            except Exception as e:
                print('    fire failed: %s' % e, flush=True)
            fired = True
        try:
            fr = q({'cmd': 'frame'}).get('frame')
        except Exception as e:
            print('t=%5.1f  EMU THREAD UNRESPONSIVE (%s)' % (el, e), flush=True)
            try:
                print('        io ping: %s' % q({'cmd': 'ping'}), flush=True)
            except Exception as e2:
                print('        io ping also failed: %s' % e2, flush=True)
            time.sleep(gap)
            continue
        try:
            st = read(STATE_HALF, 2)
            st = struct.unpack('<H', st)[0] if st else None
        except Exception:
            st = None
        cols = []
        for b in BASES:
            try:
                cols.append(tag(read(b, 722)))
            except Exception:
                cols.append('   ERR                    ')
        print('t=%5.1f f=%-7s st=%s | %s' %
              (el, fr, ('0x%04X' % st) if st is not None else '----',
               ' | '.join(cols)), flush=True)
        time.sleep(gap)


if __name__ == '__main__':
    main()
