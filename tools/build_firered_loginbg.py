"""Draw the full-screen FireRed field behind the login screen.

    python3 tools/build_firered_loginbg.py

Writes firered/res/login-bg.png and firered/login-bg-firered.xml.

WHY THIS EXISTS
The client's 3D login scene looked unreachable for a long time. It is not: the
login ROOT container, `logingui`, takes a `background` param, and stock simply
never sets one, so the 3D scene shows through. PARAGON sets it in its
android.xml, which is where the trick came from. Setting it covers the backdrop
completely.

WHY IT IS A 9-SLICE AND NOT ONE STRETCHED IMAGE
A container background is stretched to the container, and the container is the
whole window. One flat image would smear the bands and the Charizard as the
window changed shape. A 3x3 grid pins the four corners at their pixel size,
stretches the middle, and tiles the edges:

    weightsX="0,1,0"   left corner | tiled middle | RIGHT CORNER
    weightsY="0,1,0"   top bands   | stretchy teal | bottom bands

The Charizard lives in the bottom-right CORNER cell, which is the only kind of
cell that never scales, so it stays crisp and anchored to the corner at any
window size. It cannot go in a tiled or stretched cell: a tiled cell would
repeat it across the screen.
"""
import os

from PIL import Image, ImageDraw

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOD = os.path.join(REPO, "mods", "vanbobby-firered-theme", "firered")
PNG = os.path.join(MOD, "res", "login-bg.png")
XML = os.path.join(MOD, "login-bg-firered.xml")

ORANGE = (0xE0, 0x54, 0x00)
BLACK = (0x18, 0x18, 0x18)
TEAL = (0x30, 0xA8, 0x90)
TEAL_DK = (0x28, 0x90, 0x7C)
FLAME = (0xF0, 0xC0, 0x30)
FLAME_LT = (0xF0, 0xF0, 0xA8)
DARKRED = (0x70, 0x00, 0x00)

# Proportions from PokemonFireRedRef/001/splash-login.jpg: a thin orange rule,
# black under it, and a deep black footer above the dark red rule.
TOP = [(ORANGE, 12), (BLACK, 34)]
FOOT = [(BLACK, 76), (DARKRED, 20)]
FLAME_H = 22
MID_H = 2                 # ONE scanline pair, TILED rather than stretched
EDGE_W = 28               # one flame's worth, tiled across
CHARI_H = 300


def scanlined(d, x0, y0, w, h):
    d.rectangle([x0, y0, x0 + w - 1, y0 + h - 1], fill=TEAL)
    for y in range(y0, y0 + h, 2):
        d.rectangle([x0, y, x0 + w - 1, y], fill=TEAL_DK)


def flames(d, x0, y0, w, h):
    for x in range(x0 + EDGE_W // 2, x0 + w + EDGE_W, EDGE_W):
        for i in range(h):
            t = i / float(h - 1)
            half = max(0, int(t * 8))
            lean = int((1.0 - t) * 2)
            d.rectangle([x - half + lean, y0 + i, x + half + lean, y0 + i], fill=FLAME)
        for i in range(h // 2, h):
            t = (i - h // 2) / float(max(h - h // 2 - 1, 1))
            half = max(0, int(t * 4))
            d.rectangle([x - half, y0 + i, x + half, y0 + i], fill=FLAME_LT)


def main():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "sp", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "build_firered_splash.py"))
    sp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sp)
    chari = None   # the Charizard is centred and animated, so it lives in the
                   # logo widget, not here. See the note above main().

    top_h = sum(h for _, h in TOP)
    foot_h = sum(h for _, h in FOOT)
    bot_h = (CHARI_H + FLAME_H + foot_h) if chari else (FLAME_H + foot_h)
    corner_w = (chari.width + 40) if chari else EDGE_W

    W = EDGE_W + EDGE_W + corner_w
    H = top_h + MID_H + bot_h
    im = Image.new("RGBA", (W, H), TEAL + (255,))
    d = ImageDraw.Draw(im)

    # top row: the rules, full width
    y = 0
    for c, h in TOP:
        d.rectangle([0, y, W, y + h - 1], fill=c)
        y += h
    # middle row: the one stretchable slice
    scanlined(d, 0, y, W, MID_H)
    y += MID_H
    # bottom row: teal, then flames, then the footer rules
    bot0 = y
    scanlined(d, 0, bot0, W, bot_h)
    flames(d, 0, bot0 + bot_h - foot_h - FLAME_H, W, FLAME_H)
    y = bot0 + bot_h - foot_h
    for c, h in FOOT:
        d.rectangle([0, y, W, y + h - 1], fill=c)
        y += h

    os.makedirs(os.path.dirname(PNG), exist_ok=True)
    im.save(PNG)

    cols = [(0, EDGE_W), (EDGE_W, EDGE_W), (EDGE_W * 2, corner_w)]
    rows = [(0, top_h), (top_h, MID_H), (bot0, bot_h)]
    areas = []
    for ry, (ry0, rh) in enumerate(rows):
        for cx, (cx0, cw) in enumerate(cols):
            # only the middle COLUMN tiles; the corner column carries the
            # Charizard and must never repeat
            # The middle ROW is tiled too, not stretched. Stretching a 2px
            # scanline pair over hundreds of pixels turns the stripes into two
            # enormous bands, which is exactly what the first attempt did.
            tiled = ' tiled="true"' if (cx == 1 or ry == 1) else ""
            areas.append('            <area xywh="%d,%d,%d,%d"%s/>'
                         % (cx0, ry0, cw, rh, tiled))
    open(XML, "w").write('''<?xml version="1.0" encoding="UTF-8"?>
<!--
  Generated by tools/build_firered_loginbg.py. Do not hand edit.

  The FireRed field behind the WHOLE login screen, set as the background of the
  logingui container. Stock leaves that param unset, which is the only reason
  the client's 3D scene is visible at all.

  A 3x3 grid, weightsX and weightsY both "0,1,0". Corners keep their pixel size;
  the middle column and the middle row both TILE rather than stretch, because
  the field is scanlined and stretching a 2px stripe pair over half a screen
  turns it into two huge bands.

  No Charizard here. It has to be centred and animated, and this grid can offer
  neither: a corner cell cannot centre, and the centre cell tiles, which would
  march copies of it across the screen. It lives in the logo widget instead,
  which is already centred and already animates.
-->
<themes>
    <images file="res/login-bg.png" filter="nearest">
        <grid name="firered-login.background" weightsX="0,1,0" weightsY="0,1,0">
%s
        </grid>
    </images>
</themes>
''' % "\n".join(areas))
    print("login-bg.png %dx%d  cols %s  rows %s  charizard %s"
          % (W, H, [c[1] for c in cols], [r[1] for r in rows],
             "%dx%d" % chari.size if chari else "none"))


if __name__ == "__main__":
    main()
