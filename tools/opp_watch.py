#!/usr/bin/env python3
"""opp_watch.py — catch the opponent's turn without needing reflexes.

The opponent plays on its own and the window where its hand is on screen is
gone long before a human can say "now". pause/step were removed from the debug
server on purpose (query a ring buffer, do not synthesise a snapshot), so this
does the equivalent for something visual: it watches the turn flag and, the
instant the turn flips to the opponent, it

  * saves a savestate of that moment and copies it out of the slot, so the
    turn becomes a standing specimen that can be replayed as often as needed,
  * then burst-captures screenshots plus the opponent's card records for the
    whole turn, so the frame where their hand is drawn can be picked out
    afterwards instead of caught live.

Usage:
    python tools/opp_watch.py                 # wait for the next opponent turn
    python tools/opp_watch.py --rate 5        # captures per second
    python tools/opp_watch.py --max 90        # cap on captures

Leave it running and play. Ctrl-C to stop.
"""
import argparse
import json
import os
import shutil
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'psxrecomp', 'tools'))
sys.path.insert(0, os.path.join(HERE, 'psxrecomp', 'tools'))
try:
    import debug_client
except ImportError:
    sys.exit('could not import debug_client.py — run from the project root')

HOST, PORT = '127.0.0.1', 4370

TURN = 0x8009B1D5           # 0 player, 1 opponent
STATE = 0x8009B23A          # game-state index
RECORDS = 0x801A7AE4
STRIDE = 28
OFF_FLAGS = 10
OPP_HAND = range(15, 20)    # 15 records per side; 15..19 is their hand
SCRATCH_SLOT = 10

# `press` takes the RAW pad word and the PSX pad is ACTIVE LOW: idle is 0xFFFF
# and a PRESSED button is a ZERO bit. So `buttons` is not a "press these" mask
# -- passing 0x0008 means "every button except Start", which mashes the whole
# d-pad. Build words by clearing bits out of PAD_IDLE.
PAD_IDLE = 0xFFFF
PAD_SELECT, PAD_START = PAD_IDLE & ~(1 << 0), PAD_IDLE & ~(1 << 3)
PAD_UP, PAD_RIGHT = PAD_IDLE & ~(1 << 4), PAD_IDLE & ~(1 << 5)
PAD_DOWN, PAD_LEFT = PAD_IDLE & ~(1 << 6), PAD_IDLE & ~(1 << 7)
PAD_TRIANGLE, PAD_CIRCLE = PAD_IDLE & ~(1 << 12), PAD_IDLE & ~(1 << 13)
PAD_CROSS, PAD_SQUARE = PAD_IDLE & ~(1 << 14), PAD_IDLE & ~(1 << 15)


def q(d):
    return debug_client.query(HOST, PORT, d)


def read(addr, n):
    return bytes.fromhex(q({'cmd': 'read_ram', 'addr': '0x%08X' % addr,
                            'len': n}).get('hex', ''))


def u8(a):
    return read(a, 1)[0]


def u16(a):
    return struct.unpack('<H', read(a, 2))[0]


def opp_hand():
    """(id, flags) for each of the opponent's five hand records."""
    blob = read(RECORDS + 15 * STRIDE, STRIDE * 5)
    out = []
    for k in range(5):
        o = k * STRIDE
        out.append((struct.unpack_from('<H', blob, o)[0],
                    struct.unpack_from('<H', blob, o + OFF_FLAGS)[0]))
    return out


def save_specimen(outdir):
    """Save the turn and copy the .pst out, verifying the file actually moved.

    Ask the runtime where states live rather than guessing: they are in the
    player-data dir, and the stale saves/openbios/ copy beside the project
    reads plausibly enough to be copied out and reported as a fresh capture.
    The save ack is staged, so it proves nothing on its own either.
    """
    info = q({'cmd': 'savestate', 'op': 'path', 'slot': SCRATCH_SLOT})
    src = info.get('path')
    if not src:
        return None
    before = os.path.getmtime(src) if os.path.exists(src) else None
    q({'cmd': 'savestate', 'op': 'save', 'slot': SCRATCH_SLOT})
    for _ in range(20):
        time.sleep(0.5)
        if os.path.exists(src) and os.path.getmtime(src) != before:
            break
    else:
        return None
    dst = os.path.join(outdir, 'opponent_turn.pst')
    shutil.copyfile(src, dst)
    return dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rate', type=float, default=5.0)
    ap.add_argument('--max', type=int, default=90)
    ap.add_argument('--replay', type=int, default=None, metavar='SLOT',
                    help='load this savestate and press Start to hand the turn '
                         'over, instead of waiting for a live turn. Save the '
                         'state just BEFORE ending your turn and this replays '
                         'the same opponent turn as often as you like.')
    args = ap.parse_args()

    if not q({'cmd': 'ping'}).get('ok'):
        sys.exit('no debug server on %s:%d — start the DEBUG build' % (HOST, PORT))

    if args.replay is not None:
        print('loading slot %d and ending the turn...' % args.replay)
        q({'cmd': 'savestate', 'op': 'load', 'slot': args.replay})
        time.sleep(3.0)
        q({'cmd': 'press', 'buttons': PAD_START, 'frames': 6})
        deadline = time.time() + 10.0
        while u8(TURN) == 0 and time.time() < deadline:
            time.sleep(0.05)
        if u8(TURN) == 0:
            print('turn never flipped — is the state really at your turn end?')
    else:
        print('waiting for the opponent\'s turn (turn flag at 0x%08X)...' % TURN)
        while u8(TURN) != 0:        # start from a player turn so the flip is real
            time.sleep(0.2)
        while u8(TURN) == 0:
            time.sleep(0.05)

    stamp = time.strftime('%Y-%m-%d_%H%M%S')
    outdir = os.path.abspath(os.path.join(HERE, '..', 'captures',
                                          'opponent-turn-' + stamp))
    os.makedirs(outdir, exist_ok=True)
    print('\n*** opponent turn started — capturing to %s' % outdir)

    pst = save_specimen(outdir)
    print('savestate: %s' % (pst or 'FAILED'))

    frames = []
    period = 1.0 / args.rate
    for i in range(args.max):
        shot = os.path.join(outdir, 'f%03d.png' % i)
        q({'cmd': 'screenshot_file', 'path': shot})
        frames.append({'i': i, 'turn': u8(TURN), 'state': '0x%04X' % u16(STATE),
                       'opp_hand': opp_hand(), 'png': os.path.basename(shot)})
        if frames[-1]['turn'] == 0 and i > 4:
            print('turn returned to the player at capture %d' % i)
            break
        time.sleep(period)

    with open(os.path.join(outdir, 'frames.json'), 'w', encoding='utf-8') as f:
        json.dump(frames, f, indent=1)

    print('\n%d captures. opponent hand over the turn:' % len(frames))
    last = None
    for fr in frames:
        ids = [c[0] for c in fr['opp_hand']]
        if ids != last:
            print('   f%03d state=%s turn=%d  ids=%s' % (fr['i'], fr['state'],
                                                         fr['turn'], ids))
            last = ids
    print('\nReplay the moment any time with: savestate op=load slot=%d'
          % SCRATCH_SLOT)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nstopped.')
