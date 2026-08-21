#!/usr/bin/env python3
"""allcards_attribute.py — which of the three ALL CARDS trunk addresses breaks
the intro?  fill_ram each one on its own, screenshotting between, so the
distortion is attributed to an address instead of to the row as a whole.

Timing is gated on the movie itself, not on wall clock: boot speed varies
enough run-to-run that a fixed delay lands after the FMV has finished.
"""
import os, sys, time, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'psxrecomp', 'tools'))
import debug_client

HOST, PORT = '127.0.0.1', 4370
SHOT = os.environ['SHOTDIR']
UI = 0x80105D98


def q(c):
    return debug_client.query(HOST, PORT, c)


def shot(name):
    p = '%s/%s.png' % (SHOT, name)
    q({'cmd': 'screenshot_present', 'path': p})
    time.sleep(1.0)
    with open(p, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()[:12]


def fill(addr):
    q({'cmd': 'fill_ram', 'addr': '0x%08X' % addr, 'len': 722, 'val': '01'})
    return '0x%08X filled' % addr


def read(a, n):
    return bytes.fromhex(q({'cmd': 'read_ram', 'addr': '0x%08X' % a, 'len': n})['hex'])


def wait_for_ui_buffer():
    """The FMV is in flight once 0x80105D98 stops being zero — that is the
    window the bug lives in."""
    t0 = time.time()
    while time.time() - t0 < 60:
        try:
            if any(read(UI, 722)):
                return time.time() - t0
        except Exception:
            pass
        time.sleep(0.2)
    return None


def main():
    which = sys.argv[1]                       # 'save' | 'ui' | 'both'
    delay = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
    el = wait_for_ui_buffer()
    print('0x%08X non-zero at t=%.1f (frame %s)' %
          (UI, el, q({'cmd': 'frame'}).get('frame')), flush=True)
    time.sleep(delay)
    print('pre   a=%s' % shot('at_%s_pre_a' % which), flush=True)
    print('pre   b=%s   (differs => movie live)' % shot('at_%s_pre_b' % which), flush=True)
    if which in ('save', 'both'):
        print(fill(0x801D0250), flush=True)
        print(fill(0x801D3250), flush=True)
    if which in ('ui', 'both'):
        print(fill(UI), flush=True)
    time.sleep(1.0)
    for k in 'abc':
        print('post  %s=%s' % (k, shot('at_%s_post_%s' % (which, k))), flush=True)
        time.sleep(2.0)
    print('frame=%s' % q({'cmd': 'frame'}).get('frame'), flush=True)


if __name__ == '__main__':
    main()
