"""Draw the FireRed-styled login plate.

    python3 tools/build_firered_splash.py

Writes mods/vanbobby-firered-theme/firered/res/bg.png, which gfx.xml binds as
"background-image" and main-widgets.xml draws as logingui > logo.

WHY A PLATE AND NOT A TITLE SCREEN
The login screen exposes exactly one image to a theme. There is no widget for
the full-screen backdrop; the checkerboard and the 3D model belong to the client
and to the pokemmo3d mod. So the FireRed title composition lands as a banner
where the POKEMMO wordmark normally sits.

bg.png is declared xywh="*", a whole image with no slice geometry, so this is
the one atlas that may legitimately change size.

WHY THE LETTERING IS DRAWN HERE
The wordmark is original work in FireRed's style: a 5x7 pixel alphabet scaled
up, gold face, navy outline, hard shadow. Nintendo's Pokemon wordmark is not
traced and the Charizard is not reused. The client is PokeMMO, so the plate says
PokeMMO.

LAYOUT
Measured off PokemonFireRedRef/001/splash-login.jpg, which is the real thing at
its native 240x160. Band heights are taken as PERCENTAGES of that and scaled, so
the proportions survive whatever size the plate is drawn at:

    orange rule   5.6%     #E05400
    black        13.1%
    teal field   45.0%     #38A88C, scanlined
    flame row     4.4%     #E0E0A8 over the teal
    black        23.8%
    dark red      6.2%     #700000

Drawn at 3x, 720x480, which is also the largest the login plate can usefully be:
bg.png is xywh="*" and the logo widget sizes itself to the image, so a bigger
plate covers more of the client's 3D backdrop. That backdrop is not reachable
from a theme at all, so covering it is the only lever there is.
"""
import os

from PIL import Image, ImageDraw, ImageFilter

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "mods", "vanbobby-firered-theme", "firered", "res", "bg.png")

ORANGE   = (0xF0, 0x48, 0x00)
BLACK    = (0x18, 0x18, 0x18)
TEAL     = (0x30, 0xA8, 0x90)
TEAL_DK  = (0x28, 0x90, 0x7C)
FLAME    = (0xF0, 0xC0, 0x30)
FLAME_LT = (0xF0, 0xF0, 0xA8)
DARKRED  = (0x78, 0x00, 0x00)
GOLD     = (0xF8, 0xD0, 0x30)
GOLD_DK  = (0xC8, 0x90, 0x10)
NAVY     = (0x28, 0x30, 0x68)
WHITE    = (0xF8, 0xF8, 0xF8)
SHADOW   = (0x28, 0x30, 0x30)

# A 5x7 alphabet, drawn for this plate. Rows are read left to right, MSB first.
GLYPHS = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "C": ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10101", "10011", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    " ": ["00000"] * 7,
}


def glyph_mask(s, scale, spacing):
    """The string as a 1-bit mask at final pixel resolution."""
    step = 5 * scale + spacing
    w, h = max(1, len(s) * step - spacing), 7 * scale
    m = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(m)
    for ci, ch in enumerate(s):
        rows = GLYPHS.get(ch, GLYPHS[" "])
        for ry, row in enumerate(rows):
            for rx, bit in enumerate(row):
                if bit == "1":
                    px, py = ci * step + rx * scale, ry * scale
                    md.rectangle([px, py, px + scale - 1, py + scale - 1], fill=255)
    return m


def dilate(mask, r):
    return mask.filter(ImageFilter.MaxFilter(2 * r + 1))


def draw_text(im, s, x, y, scale, face, outline=None, outline_px=0,
              shadow=None, shadow_px=0, spacing=0):
    """Draw the wordmark.

    The outline is a DILATION IN PIXEL SPACE, not a square drawn around each
    scaled-up cell. Per-cell outlining is one cell thick, which on a glyph only
    five cells wide swallows the counters: the holes in O, P and R fill solid
    and the wordmark reads as a slab."""
    mask = glyph_mask(s, scale, spacing)
    pad = max(outline_px, shadow_px) + scale
    canvas = Image.new("L", (mask.width + 2 * pad, mask.height + 2 * pad), 0)
    canvas.paste(mask, (pad, pad))

    if shadow and shadow_px:
        sh = dilate(canvas, outline_px) if outline_px else canvas
        im.paste(Image.new("RGBA", canvas.size, shadow + (255,)),
                 (x - pad + shadow_px, y - pad + shadow_px), sh)
    if outline and outline_px:
        im.paste(Image.new("RGBA", canvas.size, outline + (255,)),
                 (x - pad, y - pad), dilate(canvas, outline_px))
    im.paste(Image.new("RGBA", canvas.size, face + (255,)), (x - pad, y - pad), canvas)
    return mask.width


def text_width(s, scale, spacing):
    return max(1, len(s) * (5 * scale + spacing) - spacing)


def flame_row(d, y, width, height):
    """Flames along the bottom of the teal field: widest at the base, tapering
    to a tip, with a paler inner tongue. Drawn bottom up, because a flame that
    is widest at the top reads as a row of funnels."""
    step = 28
    for x in range(0, width + step, step):
        for i in range(height):
            t = i / float(height - 1)              # 0 at the tip, 1 at the base
            half = max(0, int(t * 8))
            lean = int((1.0 - t) * 2)
            d.rectangle([x - half + lean, y + i, x + half + lean, y + i], fill=FLAME)
        for i in range(height // 2, height):
            t = (i - height // 2) / float(max(height - height // 2 - 1, 1))
            half = max(0, int(t * 4))
            d.rectangle([x - half, y + i, x + half, y + i], fill=FLAME_LT)


def main():
    W, H = 720, 384
    im = Image.new("RGBA", (W, H), TEAL + (255,))
    d = ImageDraw.Draw(im)

    def band(frac_from, frac_to):
        return int(H * frac_from), int(H * frac_to)

    # Reference proportions, with ONE deliberate change: its lower black band is
    # 24% because that is where Charizard stands. We are not reusing the
    # Charizard, so a quarter of the plate would be dead space -- and the plate
    # pushes the login window down the screen, so dead space costs twice. That
    # band is trimmed and the teal field takes the room.
    o0, o1 = band(0.000, 0.056)      # orange rule
    b0, b1 = band(0.056, 0.187)      # black
    t0, t1 = band(0.187, 0.740)      # teal field
    f0, f1 = band(0.740, 0.810)      # flame row
    k0, k1 = band(0.810, 0.920)      # black
    r0, r1 = band(0.920, 1.000)      # dark red rule

    d.rectangle([0, o0, W, o1], fill=ORANGE)
    d.rectangle([0, b0, W, b1], fill=BLACK)
    d.rectangle([0, t0, W, f1], fill=TEAL)
    for y in range(t0, f1, 2):
        d.rectangle([0, y, W, y], fill=TEAL_DK)
    flame_row(d, f0 - 6, W, (f1 - f0) + 6)
    d.rectangle([0, k0, W, k1], fill=BLACK)
    d.rectangle([0, r0, W, H], fill=DARKRED)

    title, scale, spacing = "POKEMMO", 11, 13
    tw = text_width(title, scale, spacing)
    draw_text(im, title, (W - tw) // 2, t0 + 34, scale, face=GOLD,
              outline=NAVY, outline_px=4, shadow=SHADOW, shadow_px=4,
              spacing=spacing)

    sub, s2, sp2 = "FIRERED VERSION", 4, 5
    sw = text_width(sub, s2, sp2)
    draw_text(im, sub, (W - sw) // 2, t0 + 136, s2, face=WHITE,
              outline=SHADOW, outline_px=3, spacing=sp2)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    im.save(OUT)
    print("wrote %s  %dx%d" % (os.path.relpath(OUT, REPO), W, H))


if __name__ == "__main__":
    main()
