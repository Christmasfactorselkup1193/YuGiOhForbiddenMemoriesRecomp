#!/usr/bin/env python3
"""allcards_verify.py — the fix, checked against the bug it is for.

1. During the intro, click CHEATS -> ALL CARDS. The row must refuse: the movie
   keeps playing, the three destinations are untouched, and the row goes back
   to OFF instead of showing a value the player never got.
2. In a state where the chest's copy IS the trunk, the row must still work on
   all three.
3. In a state where it is NOT, the row must write the two save structs and
   leave the foreign buffer alone.
"""
import os, sys, time, struct, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'psxrecomp', 'tools'))
import debug_client

HOST, PORT = '127.0.0.1', 4370
SHOT = os.environ['SHOTDIR']
LIVE, MIRROR, UI = 0x801D0250, 0x801D3250, 0x80105D98


def q(c):
    return debug_client.query(HOST, PORT, c)


def read(a, n):
    return bytes.fromhex(q({'cmd': 'read_ram', 'addr': '0x%08X' % a, 'len': n})['hex'])


def shot(name):
    p = '%s/%s.png' % (SHOT, name)
    q({'cmd': 'screenshot_present', 'path': p})
    time.sleep(1.0)
    return hashlib.md5(open(p, 'rb').read()).hexdigest()[:12]


def click_all_cards():
    # Clicking the bar title TOGGLES the dropdown, so an already-open menu is
    # closed by the "open" click and the row click then lands on the game.
    # Collapse first; a blind sequence that skips this silently does nothing.
    while q({'cmd': 'menu_state'}).get('expanded'):
        q({'cmd': 'menu_key', 'key': 27})
        time.sleep(0.3)
    q({'cmd': 'menu_move', 'x': 1047, 'y': 31})
    q({'cmd': 'menu_click', 'x': 1047, 'y': 31})
    time.sleep(0.4)
    if not q({'cmd': 'menu_state'}).get('expanded'):
        print('    !! CHEATS did not open', flush=True)
    q({'cmd': 'menu_move', 'x': 1400, 'y': 400})
    q({'cmd': 'menu_click', 'x': 1400, 'y': 400})
    time.sleep(0.6)


def regions(tag):
    l, m, u = read(LIVE, 722), read(MIRROR, 722), read(UI, 722)
    print('    %-8s live nz=%3d max=%3d | mirror nz=%3d max=%3d | ui nz=%3d max=%3d'
          % (tag, sum(1 for x in l if x), max(l), sum(1 for x in m if x), max(m),
             sum(1 for x in u if x), max(u)), flush=True)
    return l, m, u


def wait_for_ui_buffer():
    t0 = time.time()
    while time.time() - t0 < 60:
        if any(read(UI, 722)):
            return time.time() - t0
        time.sleep(0.2)
    return None


def test_intro():
    print('== 1. ALL CARDS during the intro ==', flush=True)
    print('    ui buffer populated at t=%.1f' % wait_for_ui_buffer(), flush=True)
    time.sleep(1.0)
    before = regions('before')
    a = shot('fix_intro_a')
    b = shot('fix_intro_b')
    print('    movie live before: %s' % (a != b), flush=True)
    click_all_cards()
    after = regions('after')
    print('    untouched: %s' % (before == after), flush=True)
    c, d = shot('fix_intro_c'), shot('fix_intro_d')
    print('    movie live after : %s   (this is the freeze test)' % (c != d), flush=True)
    time.sleep(4)
    e, f = shot('fix_intro_e'), shot('fix_intro_f')
    print('    still live +4s   : %s' % (e != f), flush=True)


def test_slot(slot, expect_ui):
    print('== ALL CARDS in slot %d (ui is trunk: %s) ==' % (slot, expect_ui), flush=True)
    q({'cmd': 'savestate', 'op': 'load', 'slot': slot})
    time.sleep(3.0)
    before = regions('before')
    click_all_cards()
    time.sleep(0.5)
    l, m, u = regions('after')
    # The row cycles OFF -> 1 -> 2 -> 3, so which count lands depends on where
    # the row already was; what matters is that every byte got the same one.
    filled = lambda x: len(set(x)) == 1 and 1 <= x[0] <= 3
    print('    live filled   : %s (%d)' % (filled(l), l[0]), flush=True)
    print('    mirror filled : %s (%d)' % (filled(m), m[0]), flush=True)
    if expect_ui:
        print('    ui   filled   : %s (%d)' % (filled(u), u[0]), flush=True)
    else:
        print('    ui   untouched: %s' % (u == before[2]), flush=True)
    print('    frame advancing: %s' % (q({'cmd': 'frame'}).get('frame')), flush=True)


if __name__ == '__main__':
    what = sys.argv[1]
    if what == 'intro':
        test_intro()
    else:
        test_slot(int(sys.argv[1]), sys.argv[2] == 'yes')
