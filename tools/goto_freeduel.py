#!/usr/bin/env python3
"""goto_freeduel.py — cold boot to the FREE DUEL opponent grid.

Uses the memory card save, not a savestate: the framework catch-up changed the
codegen hash, so every .pst is refused (ISSUES #6), while card1.mcd is intact.

Two things about this route are easy to get wrong and both cost a session:
  * the intro must be WAITED OUT, not skipped. Start does skip it, but one
    press too many selects NEW GAME and lands on name entry.
  * once on the opponent grid, presses must be LONG. A 6-frame hold changes
    nothing at all and reads exactly like a soft-lock.
"""
import os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'psxrecomp', 'tools'))
import debug_client

HOST, PORT = '127.0.0.1', 4370
START, CROSS, DOWN = 0x0008, 0x4000, 0x0040


def q(c):
    return debug_client.query(HOST, PORT, c)


def press(mask, frames=12, settle=1.2):
    q({'cmd': 'press', 'buttons': 0xFFFF & ~mask, 'frames': frames})
    time.sleep(0.5)
    q({'cmd': 'clear_input'})
    time.sleep(settle)


def wait_boot():
    t0 = time.time()
    while time.time() - t0 < 60:
        try:
            f = q({'cmd': 'frame'}).get('frame')
            if f and f > 300:
                return f
        except Exception:
            pass
        time.sleep(0.5)
    raise SystemExit('never booted')


def main():
    print('booted at frame %s' % wait_boot(), flush=True)
    print('waiting out the intro (~110 s)', flush=True)
    time.sleep(112)
    press(START, 12, 3.0)          # title -> main menu
    press(DOWN, 12, 1.5)           # NEW GAME -> LOAD
    press(CROSS, 12, 2.0)          # LOAD -> confirm
    press(CROSS, 12, 3.0)          # YES
    press(CROSS, 12, 3.0)          # dismiss LOAD COMPLETE
    press(DOWN, 12, 1.5)           # CAMPAIGN -> FREE DUEL
    press(CROSS, 12, 4.0)
    press(CROSS, 40, 2.0)          # clear the SELECT OPPONENT prompt
    print('frame %s' % q({'cmd': 'frame'}).get('frame'), flush=True)


if __name__ == '__main__':
    main()
