"""Original 320x240 card-shop interior for the Card Shop mod.

Drawn from primitives rather than sourced, so it is ours to ship. Composition is
dictated by the UI that sits on top: the shopkeeper stands lower-left, the pack
list occupies the right third, and the starchip readout sits top-right, so those
regions are deliberately kept quiet - busy art behind text is what makes a
320x240 UI unreadable.

PS1-era discipline: a small warm palette, hard edges, dithering instead of
blends, and a lamp glow built from a real radial mask rather than a stack of
rectangles.
"""
from PIL import Image, ImageDraw, ImageFilter
import random

W, H = 320, 240
random.seed(0xCA5D)          # deterministic: art must rebuild byte-identical

WALL_D  = (74, 50, 38);  WALL_M = (100, 68, 48); WALL_L = (124, 88, 60)
WOOD_D  = (74, 46, 26);  WOOD_M = (112, 72, 38); WOOD_L = (150, 100, 54)
WOOD_HI = (186, 132, 74)
SHELF_D = (52, 34, 22)
GOLD    = (238, 198, 92);  GOLD_D = (162, 122, 44)
GLASS   = (108, 148, 168); GLASS_L = (156, 196, 210)
INK     = (30, 22, 16)

PACKS = [(190, 62, 58), (62, 104, 182), (94, 162, 78), (162, 84, 170),
         (218, 152, 56), (74, 152, 160), (200, 108, 68), (122, 106, 188)]

img = Image.new("RGB", (W, H), WALL_M)
d = ImageDraw.Draw(img)

# --- back wall: alternating planks with grain --------------------------------
for x in range(0, W, 16):
    d.rectangle([x, 0, x + 15, H], fill=WALL_M if (x // 16) % 2 else WALL_D)
    d.line([(x, 0), (x, H)], fill=WALL_D)
for _ in range(320):
    gx, gy = random.randrange(W), random.randrange(0, 170)
    d.point((gx, gy), WALL_L if random.random() < 0.5 else WALL_D)

# --- shelving, left two-thirds ----------------------------------------------
for sy in (74, 112, 150):
    x = 14
    while x < 150:
        w = random.choice((8, 10, 12)); h = random.choice((22, 26, 30))
        col = PACKS[random.randrange(len(PACKS))]
        d.rectangle([x, sy - h, x + w, sy - 1], fill=col)
        d.line([(x, sy - h), (x, sy - 1)], fill=tuple(min(255, c + 45) for c in col))
        d.line([(x + w, sy - h), (x + w, sy - 1)], fill=tuple(int(c * .58) for c in col))
        d.line([(x + 2, sy - h + 4), (x + w - 2, sy - h + 4)], fill=GOLD_D)
        x += w + random.choice((3, 4, 5))
    d.rectangle([10, sy, 156, sy + 5], fill=WOOD_L)
    d.rectangle([10, sy + 5, 156, sy + 8], fill=WOOD_D)
d.rectangle([8, 40, 11, 158], fill=SHELF_D)
d.rectangle([155, 40, 158, 158], fill=SHELF_D)

# --- window, upper right (the room's light source) ---------------------------
d.rectangle([238, 44, 308, 112], fill=WOOD_D)
d.rectangle([242, 48, 304, 108], fill=GLASS)
for y in range(48, 80):                      # dithered daylight falloff
    for x in range(242, 304):
        if (x + y) % 2 == 0:
            d.point((x, y), GLASS_L)
d.line([(273, 48), (273, 108)], fill=WOOD_D)
d.line([(242, 78), (304, 78)], fill=WOOD_D)

# --- hanging sign ------------------------------------------------------------
d.line([(120, 0), (120, 14)], fill=INK)
d.line([(200, 0), (200, 14)], fill=INK)
d.rectangle([86, 14, 234, 46], fill=WOOD_D)
d.rectangle([88, 16, 232, 44], fill=WOOD_M)
d.rectangle([90, 18, 230, 42], outline=GOLD, width=1)

GLYPHS = {
    "C": ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    " ": ["00000"] * 7,
}
def text(s, ox, oy, col, scale=2, shadow=None):
    for pass_col, dx, dy in (((shadow, 1, 1) if shadow else (None, 0, 0)),
                             (col, 0, 0)):
        if pass_col is None:
            continue
        cx = ox
        for ch in s:
            g = GLYPHS[ch]
            for ry, row in enumerate(g):
                for rx, bit in enumerate(row):
                    if bit == "1":
                        d.rectangle([cx + rx * scale + dx, oy + ry * scale + dy,
                                     cx + rx * scale + scale - 1 + dx,
                                     oy + ry * scale + scale - 1 + dy],
                                    fill=pass_col)
            cx += (len(g[0]) + 1) * scale
text("CARD SHOP", 104, 23, GOLD, 2, INK)

# --- counter across the bottom ----------------------------------------------
d.rectangle([0, 176, W, 185], fill=WOOD_HI)
d.rectangle([0, 185, W, H], fill=WOOD_M)
for x in range(0, W, 26):
    d.line([(x, 186), (x, H)], fill=WOOD_D)
d.line([(0, 176), (W, 176)], fill=GOLD_D)
for _ in range(240):
    gx, gy = random.randrange(W), random.randrange(187, H)
    d.point((gx, gy), WOOD_L if random.random() < 0.5 else WOOD_D)
for i, x in enumerate((16, 38, 58)):          # loose packs, left of the UI
    col = PACKS[i]
    d.rectangle([x, 156, x + 15, 176], fill=col)
    d.line([(x, 156), (x + 15, 156)], fill=tuple(min(255, c + 55) for c in col))
    d.line([(x + 2, 161), (x + 13, 161)], fill=GOLD_D)

# --- lamp glow: a real radial mask, warm, from the top-left -------------------
glow = Image.new("L", (W, H), 0)
gd = ImageDraw.Draw(glow)
for r, v in ((190, 26), (140, 34), (96, 42), (56, 52)):
    gd.ellipse([64 - r, 8 - r, 64 + r, 8 + r], fill=v)
glow = glow.filter(ImageFilter.GaussianBlur(18))
warm = Image.new("RGB", (W, H), (255, 214, 140))
img = Image.composite(Image.blend(img, warm, 0.30), img, glow)

# --- gentle corner falloff so overlaid text stays legible --------------------
vig = Image.new("L", (W, H), 0)
vd = ImageDraw.Draw(vig)
vd.ellipse([-70, -52, W + 70, H + 52], fill=255)
vig = vig.filter(ImageFilter.GaussianBlur(34))
dark = Image.new("RGB", (W, H), (10, 6, 4))
img = Image.composite(img, Image.blend(img, dark, 0.45), vig)

out = r"C:\dev\memories\YuGiOhForbiddenMemoriesRecomp\assets\shop_bg.png"
img.save(out)
print("wrote", out, img.size)
