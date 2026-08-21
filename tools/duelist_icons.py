#!/usr/bin/env python3
"""duelist_icons.py — lift the FREE DUEL portraits out of a VRAM snapshot.

    duelist_icons.py <vram.bin> <out_dir>

WHAT IS SOLVED
--------------
Where the art is, and how to decode it. Both were measured, not guessed:

  atlas   8bpp, byte-x 256, y 256, cells on a 48px pitch. 43 cells carry
          content — rows 0-2 are eleven across, rows 3-4 are five — which is
          about one per duelist, so the WHOLE roster is resident even though
          only fifteen are on screen at a time.
  CLUT    256 entries at (128, 496 + slot), one per VISIBLE slot, slot being
          the position in the 5x3 grid. Only the fifteen on screen have a
          palette resident; scrolling the list re-uploads them.

The palette was found by decoding a tile with every 256-entry run in VRAM and
scoring it against the copy the game had already drawn on screen, allowing one
global scale to absorb the blend the screen applies. The winner scored 0.985
where the next candidate scored 0.81. Scoring WITHOUT that scale, or after
subtracting per-channel means, both pick a green palette that is wrong — the
mean subtraction hides hue error completely and scored the wrong answer 0.9997.

WHAT IS NOT SOLVED, AND WHY THIS DOES NOT PRETEND OTHERWISE
-----------------------------------------------------------
Which duelist each cell belongs to. The FREE DUEL list is NOT in the drop-table
roster order — cell 0 is Simon Muran (confirmed off the name bar), but cell 1
is a masked figure where that order would want Teana. So this writes the cells
out by INDEX and stops there. A portrait shown beside the wrong name is worse
than no portrait, which is why psx_drop_viewer.c still draws an empty plate.

To finish it: on the FREE DUEL screen the name bar names the highlighted
duelist, so walking the cursor and reading that bar gives the order directly.
Note the screen needs LONG presses — a 6-frame hold does nothing at all there,
40 frames works — which is what made it look frozen for half an hour.
"""

import os
import struct
import sys
import zlib

VRAM_W, VRAM_H = 1024, 512
ATLAS_BX, ATLAS_Y, PITCH = 256, 256, 48
CLUT_X, CLUT_Y = 128, 496
CLUT_SLOTS = 16


def load(path):
    b = open(path, 'rb').read()
    if len(b) != VRAM_W * VRAM_H * 2:
        raise SystemExit('%s is %d bytes, expected %d'
                         % (path, len(b), VRAM_W * VRAM_H * 2))
    return b


def word(v, x, y):
    o = (y * VRAM_W + x) * 2
    return v[o] | (v[o + 1] << 8)


def texel(v, bx, y):
    """One 8bpp index. VRAM rows are 2048 bytes; bx is a BYTE column."""
    return v[y * VRAM_W * 2 + bx]


def rgb555(c):
    r = (c & 31) << 3
    g = ((c >> 5) & 31) << 3
    b = ((c >> 10) & 31) << 3
    return r | (r >> 5), g | (g >> 5), b | (b >> 5), (0 if c == 0 else 255)


# The screen shows a 5x3 page, and the resident palettes are that page's.
# Walking the atlas eleven-wide instead pairs slot 5 with row 0 column 5, which
# decodes to a real portrait with a real palette and is simply the wrong one —
# the kind of mistake that looks right until you compare it with the screen.
PAGE_COLS, PAGE_ROWS = 5, 3


def cells():
    """Atlas cells in SCREEN order for the page whose palettes are resident."""
    return [(ATLAS_BX + c * PITCH, ATLAS_Y + r * PITCH)
            for r in range(PAGE_ROWS) for c in range(PAGE_COLS)]


def png(path, w, h, rows_rgba):
    """Minimal RGBA PNG; no PIL dependency, same as the other tools here."""
    raw = b''.join(b'\x00' + bytes(r) for r in rows_rgba)

    def chunk(tag, data):
        c = tag + data
        return (struct.pack('>I', len(data)) + c
                + struct.pack('>I', zlib.crc32(c) & 0xFFFFFFFF))

    out = [b'\x89PNG\r\n\x1a\n',
           chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)),
           chunk(b'IDAT', zlib.compress(raw, 9)),
           chunk(b'IEND', b'')]
    open(path, 'wb').write(b''.join(out))


def main():
    if len(sys.argv) < 3:
        raise SystemExit('usage: duelist_icons.py <vram.bin> <out_dir>')
    v = load(sys.argv[1])
    out_dir = sys.argv[2]
    os.makedirs(out_dir, exist_ok=True)

    grid = cells()
    used = 0
    for slot in range(CLUT_SLOTS):
        pal = [word(v, CLUT_X + i, CLUT_Y + slot) for i in range(256)]
        if len(set(pal)) < 16:
            continue                      # no palette uploaded for this slot
        if slot >= len(grid):
            break
        bx, y = grid[slot]
        rows = []
        for row in range(PITCH):
            line = []
            for col in range(PITCH):
                r, g, b, a = rgb555(pal[texel(v, bx + col, y + row)])
                line += [r, g, b, a]
            rows.append(line)
        png(os.path.join(out_dir, 'duelist_%02d.png' % slot), PITCH, PITCH, rows)
        used += 1
    print('wrote %d portraits to %s' % (used, out_dir))
    print('atlas cells with a resident palette: %d of %d' % (used, len(grid)))
    print('NOTE: these are indexed by SCREEN SLOT, not by duelist — see the '
          'module docstring before wiring them to names.')


if __name__ == '__main__':
    main()
