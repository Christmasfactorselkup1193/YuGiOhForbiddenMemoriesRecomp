#!/usr/bin/env python3
"""vram_dump.py — snapshot PS1 VRAM and render it so sprites can be FOUND.

VRAM is 1024x512 16-bit words holding a mix of 16bpp framebuffers, 8bpp and
4bpp texture pages and CLUTs. Rendering it one way only hides most of it: a
4bpp sprite sheet viewed as 16bpp is noise, and a 16bpp framebuffer viewed as
4bpp indices is mush. So this writes three views of the same snapshot and lets
the eye pick the one where the art appears.

    vram_dump.py snap <name>          32 vram_peek tiles -> <name>.bin + PNGs
    vram_dump.py render <name>        re-render an existing .bin
    vram_dump.py crop <name> x y w h [--bpp 4|8|16] [--clut X,Y]
                                      decode one rect, optionally through a CLUT

PNG is written by hand (zlib is stdlib) because this machine's python has no
PIL and the runtime's own screenshot commands cannot see raw texture memory.
"""

import os
import struct
import sys
import zlib

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "psxrecomp", "tools"))
from debug_client import query  # noqa: E402

HOST, PORT = "127.0.0.1", 4370
VRAM_W, VRAM_H = 1024, 512
TILE = 128
OUTDIR = os.environ.get(
    "PSX_VRAMDIR",
    os.path.join(os.environ.get("TEMP", "."), "claude", "ygofm-vram"))
_id = [0]


def cmd(**kw):
    _id[0] += 1
    kw["id"] = _id[0]
    r = query(HOST, PORT, kw)
    if not r.get("ok", True):
        raise SystemExit("failed: %s -> %s" % (kw, r))
    return r


def path_for(name, ext):
    os.makedirs(OUTDIR, exist_ok=True)
    return os.path.join(OUTDIR, name + ext)


def snap(name):
    """Whole VRAM as a little-endian u16 array, row-major."""
    buf = bytearray(VRAM_W * VRAM_H * 2)
    for ty in range(0, VRAM_H, TILE):
        for tx in range(0, VRAM_W, TILE):
            r = cmd(cmd="vram_peek", x=tx, y=ty, w=TILE, h=TILE)
            raw = bytes.fromhex(r["hex"])
            for row in range(TILE):
                src = row * TILE * 2
                dst = ((ty + row) * VRAM_W + tx) * 2
                # vram_peek emits each pixel as %04x = big-endian nibbles;
                # byte-swap into the little-endian layout everything else uses.
                for col in range(TILE):
                    hi = raw[src + col * 2]
                    lo = raw[src + col * 2 + 1]
                    buf[dst + col * 2] = lo
                    buf[dst + col * 2 + 1] = hi
    p = path_for(name, ".bin")
    with open(p, "wb") as f:
        f.write(buf)
    print("snapshot %s -> %s (%d bytes)" % (name, p, len(buf)))
    return bytes(buf)


def load(name):
    with open(path_for(name, ".bin"), "rb") as f:
        return f.read()


def png(path, w, h, rgb):
    """rgb: bytes, 3 per pixel, row-major."""
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        raw += rgb[y * w * 3:(y + 1) * w * 3]

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)))
        f.write(chunk(b"IDAT", zlib.compress(bytes(raw), 6)))
        f.write(chunk(b"IEND", b""))


def px16(v):
    """PS1 BGR555 -> RGB888."""
    r = (v & 0x1F) << 3
    g = ((v >> 5) & 0x1F) << 3
    b = ((v >> 10) & 0x1F) << 3
    return r | (r >> 5), g | (g >> 5), b | (b >> 5)


def view_16(data, w=VRAM_W, h=VRAM_H, x0=0, y0=0):
    out = bytearray(w * h * 3)
    for y in range(h):
        for x in range(w):
            v = struct.unpack_from("<H", data, ((y0 + y) * VRAM_W + x0 + x) * 2)[0]
            r, g, b = px16(v)
            i = (y * w + x) * 3
            out[i], out[i + 1], out[i + 2] = r, g, b
    return bytes(out)


def view_nbpp(data, bpp, w=VRAM_W, h=VRAM_H, x0=0, y0=0):
    """Indices as grayscale, so sprite SHAPES show without knowing the CLUT.

    One VRAM word holds 4 nibbles at 4bpp / 2 bytes at 8bpp, so the image is
    that many times wider than the word rect it covers.
    """
    per = 16 // bpp
    ow = w * per
    out = bytearray(ow * h * 3)
    mask = (1 << bpp) - 1
    scale = 255 // mask
    for y in range(h):
        for x in range(w):
            v = struct.unpack_from("<H", data, ((y0 + y) * VRAM_W + x0 + x) * 2)[0]
            for k in range(per):
                g = ((v >> (k * bpp)) & mask) * scale
                i = (y * ow + x * per + k) * 3
                out[i] = out[i + 1] = out[i + 2] = g
    return bytes(out), ow, h


def render(name, data=None):
    if data is None:
        data = load(name)
    png(path_for(name + "_16bpp", ".png"), VRAM_W, VRAM_H, view_16(data))
    for bpp in (8, 4):
        rgb, ow, oh = view_nbpp(data, bpp)
        png(path_for("%s_%dbpp" % (name, bpp), ".png"), ow, oh, rgb)
    print("rendered %s_16bpp.png, %s_8bpp.png, %s_4bpp.png in %s"
          % (name, name, name, OUTDIR))


def upscale(rgb, w, h, s):
    """Nearest-neighbour zoom. Sprite hunting is done by eye, and a 16x16
    glyph shown at 1:1 is unreadable."""
    if s <= 1:
        return rgb, w, h
    ow, oh = w * s, h * s
    out = bytearray(ow * oh * 3)
    for y in range(h):
        row = rgb[y * w * 3:(y + 1) * w * 3]
        wide = bytearray()
        for x in range(w):
            wide += row[x * 3:x * 3 + 3] * s
        for k in range(s):
            o = ((y * s + k) * ow) * 3
            out[o:o + ow * 3] = wide
    return bytes(out), ow, oh


def crop(name, x, y, w, h, bpp=16, clut=None, scale=1):
    """Decode one rect. x/w are in PIXELS of the given bpp, not VRAM words."""
    data = load(name)
    pal = None
    if clut:
        cx, cy = clut
        n = 16 if bpp == 4 else 256
        pal = []
        for i in range(n):
            v = struct.unpack_from("<H", data, (cy * VRAM_W + cx + i) * 2)[0]
            pal.append(px16(v))
    per = 16 // bpp if bpp < 16 else 1
    out = bytearray(w * h * 3)
    for row in range(h):
        for col in range(w):
            px = x + col
            word = struct.unpack_from(
                "<H", data, ((y + row) * VRAM_W + px // per) * 2)[0]
            if bpp == 16:
                r, g, b = px16(word)
            else:
                mask = (1 << bpp) - 1
                idx = (word >> ((px % per) * bpp)) & mask
                r, g, b = pal[idx] if pal else ((idx * (255 // mask),) * 3)
            i = (row * w + col) * 3
            out[i], out[i + 1], out[i + 2] = r, g, b
    rgb, ow, oh = upscale(bytes(out), w, h, scale)
    tag = "%s_crop_%d_%d_%dx%d_%dbpp" % (name, x, y, w, h, bpp)
    png(path_for(tag, ".png"), ow, oh, rgb)
    print("wrote %s.png (%dx%d)" % (path_for(tag, ""), ow, oh))


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    op = sys.argv[1]
    if op == "snap":
        render(sys.argv[2], snap(sys.argv[2]))
    elif op == "render":
        render(sys.argv[2])
    elif op == "crop":
        name = sys.argv[2]
        x, y, w, h = (int(a, 0) for a in sys.argv[3:7])
        bpp, clut, scale = 16, None, 1
        rest = sys.argv[7:]
        for i, a in enumerate(rest):
            if a == "--bpp":
                bpp = int(rest[i + 1])
            elif a == "--scale":
                scale = int(rest[i + 1])
            elif a == "--clut":
                cx, cy = rest[i + 1].split(",")
                clut = (int(cx, 0), int(cy, 0))
        crop(name, x, y, w, h, bpp, clut, scale)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
