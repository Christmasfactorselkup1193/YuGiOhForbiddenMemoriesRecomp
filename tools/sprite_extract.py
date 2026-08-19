#!/usr/bin/env python3
"""sprite_extract.py — lift sprites out of a VRAM snapshot into C source.

The rank meter has to draw the game's own POW/TEC badge, rank letters and card
digits at times when the game has not loaded them (the badge is a results-screen
asset; the meter runs during the duel). So the sprites are extracted ONCE here
and baked into the runtime rather than read from VRAM live — which also means
the meter never has to track a CLUT or care what the guest happens to have
resident.

Transparency follows the PS1 rule: a CLUT entry whose 16-bit value is exactly
0x0000 is fully transparent, whatever its index.

    sprite_extract.py preview <snap> <x> <y> <w> <h> <bpp> <cx,cy> [scale]
    sprite_extract.py emit <snap> <out.c> <spec.json>

spec.json keys are the sprite groups psx_rank_sprites.h declares — "digit",
"pow", "tec", "rank" — each {"x":..,"y":..,"w":..,"h":..,"bpp":8,
"clut":[cx,cy]}. `cells`:[n, cw, ch] slices a strip into n glyphs of cw x ch
left-to-right, which is how the digit strip becomes ten sprites. A group the
snapshot does not cover is emitted as {NULL,0,0} so the runtime still links.
"""

import json
import os
import struct
import sys

VRAM_W = 1024
OUTDIR = os.environ.get(
    "PSX_VRAMDIR",
    os.path.join(os.environ.get("TEMP", "."), "claude", "ygofm-vram"))


def load(name):
    with open(os.path.join(OUTDIR, name + ".bin"), "rb") as f:
        return f.read()


def px16(v):
    r = (v & 0x1F) << 3
    g = ((v >> 5) & 0x1F) << 3
    b = ((v >> 10) & 0x1F) << 3
    return r | (r >> 5), g | (g >> 5), b | (b >> 5)


def palette(data, cx, cy, n):
    """Returns [(a,r,g,b)], alpha 0 for the transparent entry."""
    pal = []
    for i in range(n):
        v = struct.unpack_from("<H", data, (cy * VRAM_W + cx + i) * 2)[0]
        r, g, b = px16(v)
        pal.append((0 if v == 0 else 255, r, g, b))
    return pal


def decode(data, x, y, w, h, bpp, clut):
    """-> list of ARGB rows (each a list of 0xAARRGGBB)."""
    pal = palette(data, clut[0], clut[1], 16 if bpp == 4 else 256) if bpp < 16 else None
    per = 16 // bpp if bpp < 16 else 1
    rows = []
    for row in range(h):
        out = []
        for col in range(w):
            p = x + col
            word = struct.unpack_from("<H", data, ((y + row) * VRAM_W + p // per) * 2)[0]
            if bpp == 16:
                r, g, b = px16(word)
                a = 0 if word == 0 else 255
            else:
                idx = (word >> ((p % per) * bpp)) & ((1 << bpp) - 1)
                a, r, g, b = pal[idx]
            out.append((a << 24) | (r << 16) | (g << 8) | b)
        rows.append(out)
    return rows


def png(path, rows):
    """Checkerboard behind alpha so transparency is visible in a preview."""
    import zlib
    h = len(rows)
    w = len(rows[0]) if h else 0
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        for x in range(w):
            v = rows[y][x]
            a = (v >> 24) & 0xFF
            r, g, b = (v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF
            if a == 0:
                c = 0x60 if ((x // 4) + (y // 4)) & 1 else 0x30
                r = g = b = c
            raw += bytes((r, g, b))

    def chunk(tag, d):
        c = struct.pack(">I", len(d)) + tag + d
        return c + struct.pack(">I", zlib.crc32(tag + d) & 0xFFFFFFFF)

    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)))
        f.write(chunk(b"IDAT", zlib.compress(bytes(raw), 6)))
        f.write(chunk(b"IEND", b""))


def upscale(rows, s):
    out = []
    for r in rows:
        wide = []
        for v in r:
            wide += [v] * s
        for _ in range(s):
            out.append(wide)
    return out


def resize_area(rows, tw, th, alpha_cut=0):
    """Area-average down to tw x th, premultiplied so edges do not halo.

    The rank letters are 40x40 in VRAM but have to sit in a 24-tall strip
    beside the FIELD box, and 40->24 is not an integer ratio. Nearest-neighbour
    at that factor eats whole stems out of an S; averaging keeps the glyph
    readable at the cost of soft alpha, which the meter's blit handles.

    alpha_cut restores HARD edges afterwards: PS1 4bpp art is 1-bit alpha, so a
    downscaled sprite with partial coverage does not match the game's own look —
    the glyph's near-black outline averages against the transparent surround and
    reads as a grey haze wherever the background is dark. Snapping alpha back to
    0/255 keeps the area-averaged COLOUR (so the shape still benefits from the
    filtering) while removing the halo.
    """
    sh = len(rows)
    sw = len(rows[0])
    out = []
    for ty in range(th):
        y0, y1 = ty * sh // th, max(ty * sh // th + 1, (ty + 1) * sh // th)
        line = []
        for tx in range(tw):
            x0, x1 = tx * sw // tw, max(tx * sw // tw + 1, (tx + 1) * sw // tw)
            a = r = g = b = n = 0
            for y in range(y0, y1):
                for x in range(x0, x1):
                    v = rows[y][x]
                    va = (v >> 24) & 0xFF
                    a += va
                    r += ((v >> 16) & 0xFF) * va
                    g += ((v >> 8) & 0xFF) * va
                    b += (v & 0xFF) * va
                    n += 1
            if not n or a == 0:
                line.append(0)
                continue
            av = a // n
            if alpha_cut:
                av = 255 if av >= alpha_cut else 0
            if av == 0:
                line.append(0)
                continue
            line.append((av << 24) | ((r // a) << 16) |
                        ((g // a) << 8) | (b // a))
        out.append(line)
    return out


def sprites_for(name, spec, data):
    """-> list of (symbol, rows).

    A group may be a single rect, a `cells` strip, or an explicit LIST of rects
    — the rank letters need the last form because they are not contiguous:
    S/A/B sit on one VRAM row and C/D on the next.
    """
    if spec is None:
        return []
    out = []
    items = spec if isinstance(spec, list) else [spec]
    for i, s in enumerate(items):
        bpp = s.get("bpp", 8)
        clut = tuple(s["clut"])
        cells = s.get("cells")
        if cells:
            n, cw, ch = cells
            for k in range(n):
                out.append(("%s_%d" % (name, k),
                            decode(data, s["x"] + k * cw, s["y"],
                                   cw, ch, bpp, clut)))
        else:
            sym = ("%s_%d" % (name, i)) if isinstance(spec, list) else name
            rows = decode(data, s["x"], s["y"], s["w"], s["h"], bpp, clut)
            if s.get("scale_to"):
                rows = resize_area(rows, s["scale_to"][0], s["scale_to"][1],
                                   s.get("alpha_cut", 0))
            out.append((sym, rows))
    return out


def emit_rank_sprites(specs, data, out_path):
    """Emit exactly the contract psx_rank_sprites.h declares.

    A sprite the snapshot did not cover is emitted as {NULL,0,0} rather than
    omitted, so the runtime still links and simply draws without that piece —
    which is what lets the meter be built and tested before the results-screen
    assets have been captured.
    """
    body, tables = [], []
    for group in ("digit", "pow", "tec", "rank", "plate"):
        got = sprites_for(group, specs.get(group), data)
        for sym, rows in got:
            body += emit_one(sym, rows)
        if group == "digit":
            n = 10
        elif group == "rank":
            n = 5
        else:
            n = 0
        if n:
            ents = []
            for i in range(n):
                sym = "%s_%d" % (group, i)
                r = dict(got).get(sym)
                ents.append("    { psx_spr_%s_px, %d, %d }," % (sym, len(r[0]), len(r))
                            if r else "    { 0, 0, 0 },")
            tables.append("const PsxSprite psx_spr_%s[%d] = {\n%s\n};\n"
                          % (group, n, "\n".join(ents)))
        else:
            r = dict(got).get(group)
            tables.append("const PsxSprite psx_spr_%s = %s;\n"
                          % (group,
                             "{ psx_spr_%s_px, %d, %d }" % (group, len(r[0]), len(r))
                             if r else "{ 0, 0, 0 }"))
    hdr = [
        "/* Generated by tools/sprite_extract.py - DO NOT EDIT BY HAND.",
        " *",
        " * Sprites lifted from the game's own VRAM. See psx_rank_sprites.h for why",
        " * they are baked rather than read live, and for the pixel format.",
        " */",
        "",
        '#include "psx_rank_sprites.h"',
        "",
    ]
    with open(out_path, "w") as f:
        f.write("\n".join(hdr + body) + "\n" + "\n".join(tables))
    print("wrote %s" % out_path)
    for group in ("digit", "pow", "tec", "rank", "plate"):
        s = specs.get(group)
        print("   %-6s %s" % (group, "baked" if s else "MISSING -> {0,0,0}"))


def emit_one(sym, rows):
    h = len(rows)
    w = len(rows[0])
    out = ["static const uint32_t psx_spr_%s_px[%d * %d] = {" % (sym, w, h)]
    for r in rows:
        out.append("    " + " ".join("0x%08Xu," % v for v in r))
    out.append("};")
    out.append("")
    return out


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    op = sys.argv[1]
    if op == "preview":
        snap = sys.argv[2]
        x, y, w, h, bpp = (int(a, 0) for a in sys.argv[3:8])
        cx, cy = (int(v, 0) for v in sys.argv[8].split(","))
        scale = int(sys.argv[9]) if len(sys.argv) > 9 else 4
        rows = decode(load(snap), x, y, w, h, bpp, (cx, cy))
        p = os.path.join(OUTDIR, "spr_%s_%d_%d_%dx%d.png" % (snap, x, y, w, h))
        png(p, upscale(rows, scale))
        print("wrote %s" % p)
    elif op == "emit":
        snap, out_path, spec_path = sys.argv[2], sys.argv[3], sys.argv[4]
        with open(spec_path) as f:
            specs = json.load(f)
        emit_rank_sprites(specs, load(snap), out_path)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
