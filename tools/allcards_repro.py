#!/usr/bin/env python3
"""allcards_repro.py — fire CHEATS -> ALL CARDS at a chosen point in the boot
and report whether the emu thread survives.

The io thread answers `ping` even when the emu thread is wedged, so both are
polled: ping alive + frame dead is the freeze signature.
"""
import os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'psxrecomp', 'tools'))
import debug_client

HOST, PORT = '127.0.0.1', 4370
SHOT = os.environ.get('SHOTDIR', '.')


def q(c):
    return debug_client.query(HOST, PORT, c)


def shot(name):
    try:
        q({'cmd': 'screenshot_present', 'path': '%s/%s.png' % (SHOT, name)})
        return name
    except Exception as e:
        return 'shot failed: %s' % e


def alive():
    """(emu_ok, frame, io_ok)"""
    fr, emu, io = None, False, False
    try:
        r = q({'cmd': 'frame'}); fr = r.get('frame'); emu = True
    except Exception:
        pass
    try:
        q({'cmd': 'ping'}); io = True
    except Exception:
        pass
    return emu, fr, io


def main():
    fire_at = float(sys.argv[1]) if len(sys.argv) > 1 else 12.0
    watch = float(sys.argv[2]) if len(sys.argv) > 2 else 25.0
    t0 = time.time()
    while time.time() - t0 < fire_at:
        time.sleep(0.2)
    emu, fr, io = alive()
    print('before: emu=%s frame=%s io=%s' % (emu, fr, io), flush=True)
    print('shot  : %s' % shot('repro_before'), flush=True)
    time.sleep(0.5)
    q({'cmd': 'menu_move', 'x': 1047, 'y': 31})
    q({'cmd': 'menu_click', 'x': 1047, 'y': 31})
    time.sleep(0.3)
    print('menu  : %s' % q({'cmd': 'menu_state'}), flush=True)
    q({'cmd': 'menu_move', 'x': 1400, 'y': 400})
    print('CLICK ALL CARDS at t=%.1f' % (time.time() - t0), flush=True)
    try:
        print('click : %s' % q({'cmd': 'menu_click', 'x': 1400, 'y': 400}), flush=True)
    except Exception as e:
        print('click : failed %s' % e, flush=True)
    t1 = time.time()
    n = 0
    while time.time() - t1 < watch:
        emu, fr, io = alive()
        print('  +%4.1fs emu=%-5s frame=%-8s io=%s' %
              (time.time() - t1, emu, fr, io), flush=True)
        if n in (2, 6, 14):
            print('        shot: %s' % shot('repro_after_%d' % n), flush=True)
        n += 1
        time.sleep(1.0)


if __name__ == '__main__':
    main()
