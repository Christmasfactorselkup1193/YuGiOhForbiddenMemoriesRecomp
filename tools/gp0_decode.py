#!/usr/bin/env python3
"""gp0_decode.py — decode a frame's GP0 stream into drawn sprites.

Finding a sprite by staring at a VRAM dump is guesswork: you cannot see a
texture's bit depth, its CLUT, or which rect the game actually samples. The
command stream states all three. This decodes the textured primitives of one
frame into "screen rect <- VRAM rect at Nbpp through CLUT (x,y)", which is
exactly what an extractor needs.

    gp0_decode.py sprites [frame]     textured rects/polys, screen-sorted
    gp0_decode.py raw [frame] [n]     opcode histogram + first n entries

With no frame, uses the current one from get_registers (which is mid-flight, so
prefer frame-1).
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "psxrecomp", "tools"))
from debug_client import query  # noqa: E402

HOST, PORT = "127.0.0.1", 4370
_id = [0]


def cmd(**kw):
    _id[0] += 1
    kw["id"] = _id[0]
    r = query(HOST, PORT, kw)
    if not r.get("ok", True):
        raise SystemExit("failed: %s -> %s" % (kw, r))
    return r


def s11(v):
    """GP0 packs screen coords as signed 11-bit."""
    v &= 0x7FF
    return v - 0x800 if v & 0x400 else v


def texpage_of(word):
    """0xE1 / poly texpage word -> (base_x, base_y, bpp)."""
    bx = (word & 0x0F) * 64
    by = ((word >> 4) & 1) * 256
    depth = (word >> 7) & 3
    bpp = {0: 4, 1: 8, 2: 16, 3: 16}[depth]
    return bx, by, bpp


def clut_of(word):
    """CLUT attribute halfword -> VRAM (x, y) of palette entry 0."""
    return (word & 0x3F) * 16, (word >> 6) & 0x1FF


def decode(entries):
    """Yield dicts for textured rects and textured polygons."""
    tp = (0, 0, 4)      # last 0xE1 texpage, which rects inherit
    out = []
    for e in entries:
        op = int(e["op"], 16)
        w = [int(x, 16) for x in e["w"]]
        if not w:
            continue
        if op == 0xE1:
            tp = texpage_of(w[0])
            continue
        # ---- textured rectangles: 0x64..0x67, 0x74..0x77, 0x7C..0x7F
        if 0x60 <= op <= 0x7F and (op & 0x04):
            if len(w) < 3:
                continue
            x, y = s11(w[1] & 0xFFFF), s11(w[1] >> 16)
            u, v = w[2] & 0xFF, (w[2] >> 8) & 0xFF
            cx, cy = clut_of(w[2] >> 16)
            size = (op >> 3) & 3
            if size == 0:
                if len(w) < 4:
                    continue
                sw, sh = w[3] & 0xFFFF, (w[3] >> 16) & 0xFFFF
            elif size == 1:
                sw = sh = 1
            elif size == 2:
                sw = sh = 8
            else:
                sw = sh = 16
            out.append({"kind": "rect", "op": op, "x": x, "y": y,
                        "w": sw, "h": sh, "u": u, "v": v,
                        "clut": (cx, cy), "tp": tp,
                        "func": e.get("func"), "seq": e.get("seq")})
            continue
        # ---- textured polygons: bit2 set within 0x20..0x3F
        if 0x20 <= op <= 0x3F and (op & 0x04):
            gouraud = bool(op & 0x10)
            quad = bool(op & 0x08)
            nv = 4 if quad else 3
            step = 3 if gouraud else 2      # words per vertex (xy, uv[, rgb])
            verts, uvs, clut, ptp = [], [], None, None
            idx = 1
            for i in range(nv):
                if gouraud and i > 0:
                    idx += 1              # colour word
                if idx + 1 >= len(w):
                    break
                verts.append((s11(w[idx] & 0xFFFF), s11(w[idx] >> 16)))
                uvw = w[idx + 1]
                uvs.append((uvw & 0xFF, (uvw >> 8) & 0xFF))
                if i == 0:
                    clut = clut_of(uvw >> 16)
                elif i == 1:
                    ptp = texpage_of(uvw >> 16)
                idx += step
            if not verts:
                continue
            xs = [p[0] for p in verts]
            ys = [p[1] for p in verts]
            us = [p[0] for p in uvs]
            vs = [p[1] for p in uvs]
            out.append({"kind": "poly", "op": op,
                        "x": min(xs), "y": min(ys),
                        "w": max(xs) - min(xs), "h": max(ys) - min(ys),
                        "u": min(us), "v": min(vs),
                        "uw": max(us) - min(us), "vh": max(vs) - min(vs),
                        "clut": clut or (0, 0), "tp": ptp or tp,
                        "func": e.get("func"), "seq": e.get("seq")})
    return out


def fetch(frame, count=65536):
    r = cmd(cmd="gpu_frame_dump", frame=frame, count=count)
    return r.get("entries", []), r


def main():
    op = sys.argv[1] if len(sys.argv) > 1 else "sprites"
    if len(sys.argv) > 2:
        frame = int(sys.argv[2])
    else:
        frame = int(cmd(cmd="get_registers")["frame"]) - 1
    entries, raw = fetch(frame)
    print("frame %d: %d entries" % (frame, len(entries)), file=sys.stderr)

    if op == "raw":
        hist = {}
        for e in entries:
            hist[e["op"]] = hist.get(e["op"], 0) + 1
        for k in sorted(hist, key=lambda k: -hist[k]):
            print("op %s  x%d" % (k, hist[k]))
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 0
        for e in entries[:n]:
            print(json.dumps(e))
        return

    sp = decode(entries)
    print("# %d textured primitives" % len(sp), file=sys.stderr)
    sp.sort(key=lambda s: (s["y"], s["x"]))
    for s in sp:
        bx, by, bpp = s["tp"]
        print("%-4s op=%02X screen=(%4d,%4d) %3dx%-3d  uv=(%3d,%3d) "
              "tp=(%d,%d)/%dbpp clut=(%d,%d) func=%s"
              % (s["kind"], s["op"], s["x"], s["y"], s["w"], s["h"],
                 s["u"], s["v"], bx, by, bpp, s["clut"][0], s["clut"][1],
                 s["func"]))


if __name__ == "__main__":
    main()
