#!/usr/bin/env python3
"""starchips_check.py — drive the STARCHIPS number row from the keyboard.

It is a type-a-value row, not a cycler, so a mouse click cannot exercise it:
select the row, Enter to open the editor, type, Enter to commit.
"""
import os, sys, time, struct

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'psxrecomp', 'tools'))
import debug_client

HOST, PORT = '127.0.0.1', 4370
STARCHIPS_ADDR = 0x801D07E0
ROW = 3                      # LIFE POINTS, SHOW OPP HAND, FORCE FACE UP, STARCHIPS
DOWN, UP, RET, ESC = 0x40000051, 0x40000052, 13, 27


def q(c):
    return debug_client.query(HOST, PORT, c)


def key(k, wait=0.25):
    q({'cmd': 'menu_key', 'key': k})
    time.sleep(wait)


def word(a):
    return struct.unpack('<I', bytes.fromhex(
        q({'cmd': 'read_ram', 'addr': '0x%08X' % a, 'len': 4})['hex']))[0]


def main():
    value = sys.argv[1] if len(sys.argv) > 1 else '500'
    while q({'cmd': 'menu_state'}).get('expanded'):
        key(ESC)
    q({'cmd': 'menu_move', 'x': 1047, 'y': 31})
    q({'cmd': 'menu_click', 'x': 1047, 'y': 31})
    time.sleep(0.4)
    st = q({'cmd': 'menu_state'})
    if not st.get('expanded'):
        sys.exit('CHEATS did not open')
    while q({'cmd': 'menu_state'}).get('item') != ROW:
        key(DOWN)
    print('before: starchips=%d row=%d' % (word(STARCHIPS_ADDR),
                                           q({'cmd': 'menu_state'})['item']), flush=True)
    key(RET, 0.4)
    for ch in value:
        key(ord(ch), 0.15)
    key(RET, 0.8)
    print('after : starchips=%d' % word(STARCHIPS_ADDR), flush=True)


if __name__ == '__main__':
    main()
