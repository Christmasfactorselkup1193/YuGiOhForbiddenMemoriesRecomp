#!/usr/bin/env python3
"""nav.py — drive the game with the pad and look at where it went.

    python tools/nav.py <press> [<press> ...]

Each press is NAME[:frames], e.g. start, cross, down:8. PSX pad words are
ACTIVE LOW, so a press is the complement of the button's bit; getting that
backwards presses everything except the button you meant.
"""
import os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'psxrecomp', 'tools'))
import debug_client

HOST, PORT = '127.0.0.1', 4370
SHOT = os.environ.get('SHOTDIR', '.')

# The digital pad word, LSB first. Getting this wrong is silent and looks like
# the game ignoring you: an early version had down=0x4000 and cross=0x0040,
# which is CROSS and RIGHT, so every "move down" confirmed the highlighted menu
# item instead and three navigation attempts started a new game.
BUTTONS = {
    'select': 0x0001, 'l3': 0x0002, 'r3': 0x0004, 'start': 0x0008,
    'up': 0x0010, 'right': 0x0020, 'down': 0x0040, 'left': 0x0080,
    'l2': 0x0100, 'r2': 0x0200, 'l1': 0x0400, 'r1': 0x0800,
    'triangle': 0x1000, 'circle': 0x2000, 'cross': 0x4000, 'square': 0x8000,
}


def q(c):
    return debug_client.query(HOST, PORT, c)


def press(name, frames=6):
    mask = BUTTONS[name]
    q({'cmd': 'press', 'buttons': 0xFFFF & ~mask, 'frames': frames})
    time.sleep(0.45)
    q({'cmd': 'clear_input'})
    time.sleep(0.55)


def shot(tag):
    p = '%s/nav_%s.png' % (SHOT, tag)
    q({'cmd': 'screenshot_present', 'path': p})
    time.sleep(1.2)
    return p


def main():
    for i, spec in enumerate(sys.argv[1:]):
        name, _, fr = spec.partition(':')
        press(name, int(fr) if fr else 6)
        print('%2d %-9s frame=%s' % (i, name, q({'cmd': 'frame'}).get('frame')),
              flush=True)
    print(shot('now'))


if __name__ == '__main__':
    main()
