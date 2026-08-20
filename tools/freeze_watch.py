#!/usr/bin/env python3
"""freeze_watch.py — sit alongside a normal play session and capture the duel
soft-lock (ISSUE #1) the moment it happens.

The freeze is rare and the emulator stays healthy through it, so the built-in
freeze watchdog never fires and there is nothing to notice until the screen
stops advancing. By then the evidence that decides the open question is gone
unless it was already being recorded.

The open question: the stuck effect is retired by a CD-ROM interrupt callback
chain that never fires. Either the CD command was issued and its completion
interrupt was dropped (emulator bug), or it was never issued (guest bug).
Those look identical after the fact, which is why this has to be armed BEFORE
the freeze.

Usage:
    python tools/freeze_watch.py                 # watch, capture, exit
    python tools/freeze_watch.py --hold 8        # seconds bit 4 must stay set
    python tools/freeze_watch.py --keep-going    # keep watching after a capture

Leave it running in its own terminal and play normally.
"""
import argparse
import json
import os
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'psxrecomp', 'tools'))
sys.path.insert(0, os.path.join(HERE, 'psxrecomp', 'tools'))
try:
    import debug_client
except ImportError:
    sys.exit('could not import debug_client.py — run this from the project root')

HOST, PORT = '127.0.0.1', 4370

BUSY_MASK = 0x8009B0F4      # effect busy bitmask; bit 4 is what the duel waits on
BUSY_BIT = 0x10
STATE_HALF = 0x8009B23A     # game-state index; low nibble 9 = duel handler
DUEL_STRUCT = 0x800EA000


def q(d):
    return debug_client.query(HOST, PORT, d)


def read(addr, n):
    r = q({'cmd': 'read_ram', 'addr': '0x%08X' % addr, 'len': n})
    return bytes.fromhex(r.get('hex', ''))


def u32(a):
    return struct.unpack('<I', read(a, 4))[0]


def u16(a):
    return struct.unpack('<H', read(a, 2))[0]


def counters():
    st = q({'cmd': 'cdrom_state'})
    return {k: st.get(k) for k in
            ('int_raised', 'int_presented', 'int_clobbered', 'int_lost_unseen',
             'int_acked_unpresented', 'int_last_lost')}


SCRATCH_SLOT = 10   # user confirmed no slot is worth preserving


def save_state_copy(outdir):
    """Save the frozen moment, then copy the .pst out of the slot.

    Slots are a fixed pool of 12 and the runtime reuses them, so a capture that
    only points at a slot number is one savestate away from being lost.

    Two things this deliberately does NOT do, both learned the hard way:

    * It does not guess the savestate directory. States live in the
      player-data dir, while a stale pre-migration copy sits in
      saves/openbios/ beside the project and reads perfectly plausibly. Ask
      the runtime (`savestate op=path`) instead of assuming.
    * It does not trust the save's "ok". The request is staged and serviced on
      the emu thread, so the ack says nothing about the file. Require the
      mtime to actually move, or a stale file gets copied out and reported as
      a fresh capture -- which is exactly how this returned a false pass once.
    """
    import shutil
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
        print('savestate never landed (%s unchanged) — RAM dumps only' % src)
        return None

    dst = os.path.join(outdir, 'frozen_state.pst')
    shutil.copyfile(src, dst)
    thumb = src[:-4] + '.thumb'
    if os.path.exists(thumb):
        shutil.copyfile(thumb, os.path.join(outdir, 'frozen_state.thumb'))
    return dst


def capture(outdir, baseline, held):
    os.makedirs(outdir, exist_ok=True)

    def dump(name, payload):
        with open(os.path.join(outdir, name), 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=1)

    cd = q({'cmd': 'cdrom_state'})
    report = {
        'held_seconds': held,
        'busy_mask': '0x%08X' % u32(BUSY_MASK),
        'game_state': '0x%04X' % u16(STATE_HALF),
        'fast_loads': q({'cmd': 'fast_loads'}),
        'counters_at_freeze': counters(),
        'counters_baseline': baseline,
    }
    dump('report.json', report)
    dump('cdrom_state.json', cd)
    dump('wtrace_busy_mask.json',
         q({'cmd': 'wtrace_dump', 'count': 400,
            'addr_lo': '0x8009B0F4', 'addr_hi': '0x8009B0F8'}))
    dump('cdrom_trace.json', q({'cmd': 'cdrom_trace_dump', 'count': 512}))
    dump('cdrom_command_history.json', q({'cmd': 'cdrom_command_history'}))
    dump('cd_read_log.json', q({'cmd': 'cd_read_log', 'tail': 256}))

    q({'cmd': 'ram_dump_file', 'path': os.path.join(outdir, 'ram_frozen_t0.bin')})

    # A savestate of the frozen moment is what made the 08-16 / 08-19 captures
    # reproducible on demand. Save into the scratch slot, then copy the file
    # into the capture so a later save cannot clobber the evidence.
    saved = save_state_copy(outdir)
    report['savestate'] = saved

    time.sleep(6)
    q({'cmd': 'ram_dump_file', 'path': os.path.join(outdir, 'ram_frozen_t6s.bin')})
    dump('counters_after_6s.json', counters())
    dump('report.json', report)
    return report


def verdict(report):
    base = report['counters_baseline'].get('int_lost_unseen') or [0] * 6
    now = report['counters_at_freeze'].get('int_lost_unseen') or [0] * 6
    delta = [now[i] - base[i] for i in range(len(now))]
    print('\n' + '=' * 66)
    if any(delta[1:]):
        print('  A CD INTERRUPT WAS DROPPED during this session.')
        print('  int_lost_unseen delta by INT type: %s' % delta[1:])
        print('  int_last_lost: %s' % report['counters_at_freeze'].get('int_last_lost'))
        print('  => emulator side. Look at the CD-ROM command/response state')
        print('     machine, and at the L entries in cdrom_trace.json.')
    else:
        print('  NO CD interrupt was dropped (int_lost_unseen unchanged).')
        print('  => the completion the effect waited on was most likely never')
        print('     REQUESTED. Walk upstream from the claim site 0x800291D4.')
    print('  Check cdrom_command_history.json for the last command issued')
    print('  before the freeze, and wtrace_busy_mask.json for the claim with')
    print('  no matching release.')
    print('=' * 66)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--hold', type=float, default=8.0,
                    help='seconds the busy bit must stay set (default 8)')
    ap.add_argument('--interval', type=float, default=1.0)
    ap.add_argument('--keep-going', action='store_true')
    ap.add_argument('--disc', choices=('instant', 'fast', 'authentic'),
                    default='instant',
                    help='disc mode to hold for this session (default instant)')
    ap.add_argument('--force-disc', action='store_true',
                    help='set the disc mode instead of aborting on a mismatch '
                         '(may persist to your menu_settings.ini)')
    args = ap.parse_args()

    if not q({'cmd': 'ping'}).get('ok'):
        sys.exit('no debug server on %s:%d — start the DEBUG build (PlayDebug.bat)' % (HOST, PORT))
    if q({'cmd': 'cdrom_state'}).get('int_lost_unseen') is None:
        sys.exit('this build has no INT-loss counters — rebuild build-dbg')

    # Both known freezes happened under instant, so a session spent at
    # authentic tests the wrong thing. CHECK rather than change: setting the
    # level at runtime can persist into the player's real menu_settings.ini
    # (which lives in the player-data dir, NOT beside the exe), and silently
    # rewriting someone's settings to run a test is not this tool's business.
    fl = q({'cmd': 'fast_loads'})
    if fl.get('mode') != args.disc:
        if not args.force_disc:
            print('disc mode is %r, expected %r.' % (fl.get('mode'), args.disc))
            print('Set FAST LOADING in the F10 menu (it persists), or re-run')
            print('with --force-disc to set it for this session only.')
            print('Refusing to change your settings on my own — aborting.')
            return
        was = fl.get('mode')
        fl = q({'cmd': 'fast_loads',
                'level': {'authentic': 0, 'fast': 1, 'instant': 2}[args.disc]})
        print('disc mode %r -> %r (--force-disc; this MAY persist to your'
              % (was, fl.get('mode')))
        print(' menu_settings.ini in the player-data dir)')

    q({'cmd': 'wtrace_arm', 'lo': '0x8009B0F4', 'hi': '0x8009B0F8'})
    q({'cmd': 'wtrace_reset'})
    print('freeze_watch armed. disc mode=%s (divisor %s, active_now=%s)'
          % (fl.get('mode'), fl.get('divisor'), fl.get('active_now')))
    if fl.get('mode') != 'instant':
        print('NOTE: not running instant — both known freezes occurred under')
        print('      instant, so this session may not exercise the suspect path.')
    print('watching bit 4 of 0x8009B0F4; trigger = held %.0fs while in game state 9.'
          % args.hold)
    print('play normally — Ctrl-C to stop.\n')

    baseline = counters()
    since = None
    last_note = 0.0

    while True:
        try:
            busy = u32(BUSY_MASK) & BUSY_BIT
            state = u16(STATE_HALF) & 0xF
        except Exception as e:
            print('lost the debug server (%s) — did the game exit?' % e)
            return
        now = time.time()
        if busy and state == 9:
            if since is None:
                since = now
            held = now - since
            if held >= args.hold:
                stamp = time.strftime('%Y-%m-%d_%H%M%S')
                outdir = os.path.join(HERE, '..', 'bugs', 'duel-freeze-' + stamp)
                outdir = os.path.abspath(outdir)
                print('\n*** SOFT-LOCK DETECTED (busy bit held %.1fs) ***' % held)
                print('capturing to %s' % outdir)
                rep = capture(outdir, baseline, held)
                verdict(rep)
                if rep.get('savestate'):
                    print('\nsavestate of the frozen moment: %s' % rep['savestate'])
                    print('(written via slot %d and copied out, so it survives'
                          % SCRATCH_SLOT)
                    print(' any later save to that slot)')
                else:
                    print('\nWARNING: savestate capture failed — RAM dumps only.')
                if not args.keep_going:
                    return
                since = None
                baseline = counters()
            elif now - last_note > 2.0:
                print('  busy bit held %.0fs...' % held)
                last_note = now
        else:
            if since is not None and (now - since) > 2.0:
                print('  (cleared after %.0fs — normal effect, still watching)'
                      % (now - since))
            since = None
        time.sleep(args.interval)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nstopped.')
