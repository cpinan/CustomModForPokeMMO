"""Repaint pokemmo_ui.png in FireRed's window grammar.

    python3 tools/build_firered_atlas.py [--report]

Reads the stock atlas and its slice table out of the installed client, redraws
every panel, and writes:

    mods/vanbobby-firered-theme/firered/res/pokemmo_ui.png
    mods/vanbobby-firered-theme/firered/gfx_ui-firered.xml

Re-run it after a client update; it is the source of the art, not the PNG.

WHY THIS IS GENERATED AND NOT DRAWN BY HAND
FireRed has one window construction with a swappable accent:

    outer #283030 x2 | ACCENT x1-3 | light bevel x1-2 | scanlined fill

That is a function, so 142 slices are a role table plus a loop rather than 142
pieces of art. See docs/SPEC-firered-style.md for the measurements.

TWO THINGS THAT ARE EASY TO GET WRONG
  * THE STOCK ATLAS OVERLAPS ITSELF, so nothing can be repainted in place.
    ui-box.default is 64x15 at 326,8 while ui-inputbox.default is 16x16 at the
    same origin, and whole grids sit one pixel apart: ui-inner-frame's row starts
    at y=82 and ui-inner-frame-floating's at y=83. Stock gets away with this
    because the shared pixels happen to read acceptably for both; a repaint does
    not, and 129 pairs collide.

    So this repacks. Every slice is assigned a fresh, non-overlapping rectangle
    and the emitted table says where it went. That is legitimate because the mod
    ships the slice table as well as the atlas: only the NAMES have to match
    stock, since names are what widgets bind to.

  * Aliases -- several names on one rect with one role, like the six
    ui-button.tinted.* -- collapse to a single packed slot and stay identical.
    Two names on the same rect wanting DIFFERENT roles get separate slots.

  * splitx/splity are the 9-slice split points, and they must agree with the
    band thickness we actually paint. Stock ui-button.default is 29x29 split
    L4,R4/T4,B4; paint a 5px border under a 4px split and the stretch smears the
    outermost band across the middle. Repainted panels get their splits rewritten
    to the band total. Glyphs keep whatever stock said.

  * The block is parsed as XML, not with regexes over the text. Attributes appear
    in any order -- <area name=".." tint=".." xywh=".."> is common -- and a
    positional regex silently skips those, leaving stock coordinates pointing
    into a repacked atlas.
"""
import argparse
import os
import copy
import re
import xml.etree.ElementTree as ET
import sys
from collections import defaultdict

from PIL import Image

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOD = os.path.join(REPO, "mods", "vanbobby-firered-theme")
CLIENT = os.environ.get("POKEMMO_HOME") or os.path.expanduser(
    "~/Library/Application Support/com.pokeemu.macos/pokemmo-client-live")
STOCK = os.path.join(CLIENT, "data", "themes", "default")
ATLAS = "res/pokemmo_ui.png"   # kept for load_block's default

# ---------------------------------------------------------------- palette ---
# Measured off PokemonFireRedRef/. docs/SPEC-firered-style.md carries the table.
OUTER    = (0x28, 0x30, 0x30)
GOLD     = (0xC8, 0xA8, 0x48)
GOLD_LT  = (0xF0, 0xC8, 0x70)
GOLD_DK  = (0xD0, 0xB0, 0x50)
LAV_LT   = (0x88, 0x88, 0xC8)
LAV_DK   = (0x70, 0x68, 0x80)
BEVEL_W  = (0xE0, 0xD8, 0xE0)
BEVEL_C  = (0xD8, 0xD0, 0xB0)
BEVEL_G  = (0xD8, 0xD0, 0xD8)
NAVY     = (0x28, 0x50, 0x68)
BLUE     = (0x00, 0x78, 0xC0)
BLUE_DK  = (0x00, 0x50, 0x70)
OLIVE    = (0x20, 0x38, 0x00)
GREY     = (0x78, 0x80, 0x90)
RED      = (0xF8, 0x50, 0x00)
RED_DK   = (0x80, 0x20, 0x00)
CREAM    = (0xF8, 0xF0, 0xE8)
WHITE    = (0xF8, 0xF8, 0xF8)
PALE     = (0xF8, 0xF8, 0xC8)
PALE_2   = (0xF8, 0xF8, 0xD8)
ICE      = (0xE0, 0xF0, 0xF0)
TAN      = (0xE0, 0xD8, 0xC0)
TEAL     = (0x30, 0x98, 0x90)
TEAL_LT  = (0x50, 0xC8, 0xB0)
DISABLED = (0xC0, 0xB0, 0x88)
# Read straight off the HP Bars kit in PokemonFireRedRef/001/, which agrees
# pixel for pixel with what was measured from the screenshots earlier.
HP_SHADOW = (0x50, 0x68, 0x60)   # the plate's drop shadow
HP_OLIVE  = (0x20, 0x38, 0x00)   # its dark outline
HP_BEVEL  = (0xD8, 0xD0, 0xB0)
HP_FILL   = (0xF8, 0xF8, 0xD8)
HP_TRACK  = (0x50, 0x68, 0x58)   # the bar capsule
HP_GREEN  = (0x58, 0xD0, 0x80)
HP_GREEN2 = (0x70, 0xF8, 0xA8)
HP_GOLD   = (0xF8, 0xD0, 0x50)   # the "HP" label

# A role is (accent bands outer->in, fill stripe pair, chamfer).
# Fill is a 1:1 horizontal scanline: FireRed never uses a flat fill.
ROLES = {
    "frame":      ([(OUTER, 2), (GOLD, 3), (BEVEL_W, 2)], (CREAM, WHITE),   True),
    "frame-red":  ([(OUTER, 2), (RED, 3), (BEVEL_W, 2)],  (CREAM, WHITE),   True),
    "frame-green":([(OUTER, 2), (TEAL, 3), (BEVEL_W, 2)], (CREAM, WHITE),   True),
    "inner":      ([(OUTER, 2), (GOLD_LT, 2), (GOLD_DK, 1)], (PALE, PALE_2), False),
    "inverted":   ([(OUTER, 2), (GOLD, 2), (BEVEL_C, 1)], (NAVY, NAVY),     False),
    "tab":        ([(OUTER, 2), (GOLD_LT, 2)],            (PALE, PALE_2),   False),
    "tab-off":    ([(OUTER, 2), (GOLD_DK, 2)],            (TAN, TAN),       False),
    "button":     ([(OUTER, 2), (GOLD, 2), (BEVEL_W, 1)], (PALE, PALE_2),   False),
    "button-hi":  ([(OUTER, 2), (GOLD_LT, 2), (BEVEL_W, 1)], (WHITE, PALE), False),
    "button-down":([(OUTER, 2), (GOLD_DK, 2), (BEVEL_C, 1)], (TAN, TAN),    False),
    "button-off": ([(OUTER, 2), (DISABLED, 2)],           (TAN, TAN),       False),
    "popup":      ([(OUTER, 2), (LAV_LT, 1), (LAV_DK, 2), (BEVEL_G, 1)], (WHITE, ICE), False),
    "popup-warn": ([(OUTER, 2), (RED, 2), (BEVEL_W, 1)],  (WHITE, ICE),     False),
    "input":      ([(OUTER, 2), (GREY, 1), (BEVEL_G, 1)], (WHITE, ICE),     False),
    "input-on":   ([(OUTER, 2), (BLUE, 2), (BEVEL_G, 1)], (WHITE, ICE),     False),
    "input-red":  ([(OUTER, 2), (RED, 2), (BEVEL_G, 1)],  (WHITE, ICE),     False),
    "box":        ([(OUTER, 2), (GREY, 1), (BEVEL_G, 1)], (CREAM, WHITE),   False),
    "box-on":     ([(OUTER, 2), (BLUE, 2), (BEVEL_G, 1)], (ICE, WHITE),     False),
    "box-red":    ([(OUTER, 2), (RED, 2), (BEVEL_G, 1)],  (CREAM, WHITE),   False),
    "label":      ([(OUTER, 1), (GREY, 1)],               (WHITE, WHITE),   False),
    "close":      ([(OUTER, 2), (RED, 2), (BEVEL_W, 1)],  (CREAM, WHITE),   False),
    "header":     ([(OUTER, 2), (GOLD, 3), (BEVEL_W, 1)], (GOLD_LT, GOLD_LT), False),
    # list rows: a hairline so rows read as rows, and a light scanlined ground
    # so the dark #404040 glyph has something to sit on.
    "row":        ([(GOLD_DK, 1)],                        (CREAM, WHITE),   False),
    "row-header": ([(OUTER, 1), (GOLD, 2)],               (GOLD_LT, GOLD_LT), False),
    # speech bubbles and tooltips are the one place FireRed goes dark
    "dialogue":   ([(OUTER, 2), (GOLD, 3), (BEVEL_W, 2)], (NAVY, NAVY),     True),
    "pill":       ([(OUTER, 1), (GREY, 1)],               (TAN, TAN),       False),
    "scrollbar":  ([(OUTER, 1), (GOLD_DK, 1)],            (PALE, PALE_2),   False),
    "bar":        ([],                                    (GOLD_LT, GOLD),  False),
    "bar-green":  ([],                                    (TEAL_LT, TEAL),  False),
    "solid-cream":([],                                    (CREAM, CREAM),   False),
    # The battle HP plate, exactly as the kit builds it: a one pixel shadow, a
    # one pixel dark olive outline, a one pixel warm bevel, then pale fill. Much
    # thinner than the window frames because the plate itself is only ~26px tall.
    "hpbox":      ([(HP_SHADOW, 1), (HP_OLIVE, 1), (HP_BEVEL, 1)],
                                                          (HP_FILL, HP_FILL), False),
    "hpbar":      ([(HP_TRACK, 1)],                       (HP_GREEN, HP_GREEN2), False),
    "hpbar-gold": ([(HP_TRACK, 1)],                       (HP_GOLD, HP_GOLD), False),
}

# name prefix -> role. Longest prefix wins, so specific beats general.
ROLE_BY_PREFIX = [
    ("ui-frame-red",              "frame-red"),
    ("ui-frame-green",            "frame-green"),
    ("ui-frame",                  "frame"),
    ("ui-inner-frame-inverted",   "inverted"),
    ("ui-inner-frame-tabbed",     "inner"),
    ("ui-inner-frame-tab",        "tab"),
    ("ui-inner-tab",              "tab"),
    ("ui-inner-roundedframe",     "inner"),
    ("ui-inner-frame",            "inner"),
    ("ui-tab-vertical.active",    "tab"),
    ("ui-tab-vertical",           "tab-off"),
    ("ui-tab.active",             "tab"),
    ("ui-tab",                    "tab-off"),
    ("ui-popup-warning",          "popup-warn"),
    ("ui-popup-button.selected",  "button-hi"),
    ("ui-popup-button",           "button"),
    ("ui-popup",                  "popup"),
    ("ui-button.pressed",         "button-down"),
    ("ui-button.hover",           "button-hi"),
    ("ui-button.disabled",        "button-off"),
    ("ui-button",                 "button"),
    ("ui-misc-btn.selected",      "button-hi"),
    ("ui-misc-btn",               "button"),
    ("ui-colorpicker",            "button"),
    ("ui-close",                  "close"),
    ("ui-inputbox-2px.red",       "input-red"),
    ("ui-inputbox-2px.selected",  "input-on"),
    ("ui-inputbox-2px",           "input"),
    ("ui-inputbox.selected",      "input-on"),
    ("ui-inputbox.red",           "input-red"),
    ("ui-inputbox",               "input"),
    ("ui-box.selected-red",       "box-red"),
    ("ui-box.selected",           "box-on"),
    ("ui-box",                    "box"),
    ("label-white",               "label"),
    ("ui-checkbox",               "input"),
]

# res/user-interface.png, declared in gfx.xml. 148 more slices, and the ones
# that back Settings and every list: interface.background, row.background,
# the scrollbars and all the button families. P2 shipped without these, so
# those surfaces kept their stock dark art while the text went dark on top.
ROLE_BY_PREFIX_IF = [
    ("interface.background",   "frame"),
    ("friends-list-bg",        "inner"),
    ("hud.background",         "inner"),
    ("popup.background",       "inner"),
    ("chatframe",              "inner"),
    ("inner-dialog-text",      "inner"),
    ("inner-area",             "inner"),
    ("game-shop-area",         "inner"),
    ("movetutor-area",         "inner"),
    ("tab-area",               "inner"),
    ("row-header.background",  "row-header"),
    ("row.background",         "row"),
    # These were navy "dialogue". Their text is drawn with main/tooltip faces,
    # which are dark now, so a dark ground made them unreadable. FireRed's one
    # genuinely navy surface is the battle message box (text-bubble.png), whose
    # text uses the battle face and stays light. Everything else goes light.
    ("chat-bubble",            "inner"),
    ("chat-npc-bubble",        "inner"),
    ("bubble",                 "inner"),
    ("tooltip-left",           "inner"),
    ("label-bg-",              "pill"),
    ("label-hbg-",             "pill"),
    ("label-area",             "pill"),
    ("vscrollbar",             "scrollbar"),
    ("hscrollbar",             "scrollbar"),
    ("progressbar-green",      "bar-green"),
    ("progressbar",            "bar"),
    ("xp-monster-frame",       "bar-green"),
    ("inventory-slot",         "box"),
    ("trade-slot",             "box"),
    ("monster-slot",           "box"),
    ("monster-preview-bg",     "box"),
    ("monstergear-pic",        "box"),
    ("color-picker",           "box"),
    ("input-black",            "input"),
    ("input.background",       "input"),
    ("chat-input",             "input"),
    ("monster-frame-tab-empty", "tab-off"),
    ("ui-tab-button.disabled", "tab-off"),
    ("ui-tab-button",          "tab"),
    ("inner-tab",              "tab"),
    ("console.background",     "solid-cream"),
]

# 1x1 and tiny slices the client TINTS at draw time, or shapes that only make
# sense as stock pixels. Repainting a 1x1 white fill gold breaks every widget
# that tints it.
KEEP_PREFIXES_IF = (
    "white.background", "editfield.", "-editfield.", "-console.cursor",
    "icon-", "close-handle", "minimize-handle", "maximize-handle",
    "combobox-picker", "monster-frame-nameplate",
)

# Shapes, not panels. Redrawing these as frames destroys them, so their stock
# pixels are kept and only recoloured.
GLYPH_PREFIXES = (
    "ui-status-", "ui-sort-", "ui-table-sort-", "ui-c-menu", "ui-color.",
    "ui-spacer", "ui-button-picker", "button-npc-dark", "ui-checkbox.f",
)


def role_for(name, table=None, glyphs=GLYPH_PREFIXES, keep=()):
    """None means recolour the stock shape; "keep" means do not touch it."""
    if name.startswith(keep):
        return "keep"
    if name.startswith(glyphs):
        return None
    best = None
    for prefix, role in (table if table is not None else ROLE_BY_PREFIX):
        if name.startswith(prefix) and (best is None or len(prefix) > len(best[0])):
            best = (prefix, role)
    return best[1] if best else None


def role_dialogue(name):
    """res/text-bubble.png: THE FireRed window, the navy battle message box with
    a gold chamfered frame.

    It is the one surface in the theme that stays dark, because the text drawn on
    it uses the battle face, which is white. Leaving this atlas stock shipped
    white text on a light bubble, which is invisible. The little advance arrow is
    kept as stock pixels: it sits ON the navy box, so inverting it to dark would
    hide it."""
    if "arrow" in name:
        return "keep"
    return "dialogue"


def role_ingame(name):
    """The in-game atlases: monster-info, battle-hud, pc_slots and the smaller
    windows. Shipped stock-dark through 0.7 while the fonts went dark globally,
    which is what made the Summary, Trainer Card and battle HP labels unreadable.

    Anything not recognised falls through to a glyph recolour, which preserves
    the shape. That is the safe default for an atlas full of icons."""
    n = name.lower()
    base = n.split(".")[0]
    if any(k in n for k in ("icon", "sprite", "marking", "shiny", "gender",
                            "arrow", "star", "particle", "cursor")):
        return None
    if "progressimage" in n:
        return "hpbar" if ("hp" in n or "green" in n) else "bar"
    if "hpbar" in n or "health" in n:
        return "hpbar"
    if "expbar" in n or "exp" in n:
        return "hpbar-gold"
    if n.endswith("-bar"):
        return "bar"
    # the battle name/level plates and the HUD floats are all the same object
    if n.startswith("battle-ui-") or "float" in n or "enemy" in n or "boss" in n:
        return "hpbox"
    # battle-area is the battle MESSAGE BOX, the 800x115 panel across the bottom
    # that battle-panel-dark draws. Its text uses the battle face, which is
    # white, so it has to be the navy window: painted pale, "A wild Poochyena
    # appeared!" was white on cream. This is the FireRed dialogue box, and the
    # one place in the theme where the dark pairing is correct.
    if n.startswith("battle-area"):
        return "dialogue"
    if "label-title" in n or "nameplate" in n:
        return "row-header"
    if "label" in n:
        return "row"
    if base.endswith(("-bg",)) or "background" in n and "overlay" in n:
        return "inner"
    if "slot" in n or "inner" in n:
        return "box"
    if "border" in n:
        return "box"
    if "tab" in n:
        return "tab-off" if ".default" in n or "empty" in n else "tab"
    if "button" in n:
        if ".disabled" in n:
            return "button-off"
        if ".hover" in n or ".selected" in n:
            return "button-hi"
        return "button"
    if "frame" in n or base.endswith("-bg") or base.endswith("bg"):
        return "frame"
    if "area" in n or "window" in n or "panel" in n or "skill" in n:
        return "inner"
    return None


def role_generic(name):
    """res/main-hud.png is misnamed: it is the primary generic widget atlas.
    frame.background, 38 button.* states, table-row, table-header, label1..7 and
    tabbed-area all live here, which is why Settings and every list stayed stock
    dark when only pokemmo_ui.png was repainted.

    Resolved by suffix because the button families are combinatorial."""
    if name.startswith(("chaticon", "gmicon", "trainer", "hotbar")):
        return "keep"
    base = name.split(".")[0]
    if base.startswith("label"):
        return "row"
    if base in ("table-header",):
        return "row-header"
    if base.startswith("table"):
        return "row"
    if base.startswith("frame") or base == "tabbed-area":
        return "inner" if "split" in base or "alpha" in base else "frame"
    if base.startswith("button"):
        if name.endswith((".disabled", ".disabled-hover")):
            return "button-off"
        if ".hover" in name or ".selected" in name or name.endswith(".ok"):
            return "button-hi"
        return "button"
    return None


ATLASES = [
    dict(file="res/pokemmo_ui.png", source="gfx_ui.xml", out="gfx_ui-firered.xml",
         table=None, glyphs=GLYPH_PREFIXES, keep=()),
    dict(file="res/user-interface.png", source="gfx.xml", out="gfx-firered.xml",
         table=ROLE_BY_PREFIX_IF, glyphs=("progressbar.progressImage_never",),
         keep=KEEP_PREFIXES_IF),
    dict(file="res/main-hud.png", source="gfx.xml", out="mainhud-firered.xml",
         table=None, glyphs=(), keep=(), resolver=role_generic),
] + [
    # Everything else the UI draws from. Unrecognised names fall through to a
    # glyph recolour, so an atlas of icons survives being listed here.
    dict(file=f, source="gfx.xml", out=out, table=None, glyphs=(), keep=(),
         resolver=role_ingame)
    for f, out in [
        ("res/monster-info.png",  "monsterinfo-firered.xml"),
        ("res/battle-hud.png",    "battlehud-firered.xml"),
        ("res/pc_slots.png",      "pcslots-firered.xml"),
        ("res/pc-window.png",     "pcwindow-firered.xml"),
        ("res/MainTCTexture.png", "traincard-firered.xml"),
        ("res/contestgui.png",    "contest-firered.xml"),
        ("res/caught-window.png", "caught-firered.xml"),
        ("res/breedwindow.png",   "breed-firered.xml"),
        ("res/preview-field.png", "preview-firered.xml"),
    ]
] + [
    dict(file="res/text-bubble.png", source="gfx.xml", out="textbubble-firered.xml",
         table=None, glyphs=(), keep=(), resolver=role_dialogue),
]



# ------------------------------------------------------------------ parse ---
def load_block(path, atlas):
    """The <images> element for one atlas, as XML. Regexes miss attribute
    orderings, and there are plenty of them in these files."""
    root = ET.parse(path).getroot()
    for images in root.iter("images"):
        if images.get("file") == atlas:
            return images
    sys.exit("no <images> block for %s in %s" % (atlas, path))


def rect_of(el):
    """Stock uses a NEGATIVE extent to mean "mirror this slice" -- battle-hud's
    battle-ability-flip is 136 wide as -136. Fed to a packer unnoticed, a
    negative width walks the cursor BACKWARDS and every later slice lands on top
    of an earlier one.

    We generate art per slice, so a mirrored duplicate buys nothing: the flipped
    copy is painted the same as its twin. Extents are normalised to positive
    here and stay positive in the emitted table."""
    x, y, w, h = (int(v) for v in el.get("xywh").split(","))
    return x, y, abs(w), abs(h)


def band_total(role):
    return sum(w for _, w in ROLES[role][0])


def clamp_split(el, rect, log):
    """A 9-slice whose caps are wider than the rect has a negative middle and
    smears. Stock ships one: button-npc-dark.selected is 8x9 with
    splitx="L20,R7". Inherited, not caused, but we emit the table so we fix it.

    A ZERO middle is left alone -- "L0,R9" on a 9px rect is the legal idiom for
    do not stretch, pin right."""
    for attr, extent in (("splitx", rect[2]), ("splity", rect[3])):
        spec = el.get(attr)
        if not spec:
            continue
        parts = spec.split(",")
        vals = [int(re.sub(r"[^0-9]", "", p) or 0) for p in parts]
        if sum(vals) <= extent:
            continue
        scale = extent / float(sum(vals))
        fixed = [int(v * scale) for v in vals]
        while sum(fixed) > extent:
            fixed[fixed.index(max(fixed))] -= 1
        new = ",".join(re.sub(r"[0-9]+", str(f), p) for p, f in zip(parts, fixed))
        log.append((el.get("name"), attr, spec, new, extent))
        el.set(attr, new)


# ---------------------------------------------------------------- painting --
def bands_for(size, spec):
    """Shrink the band stack so a small slice still shows every band."""
    total = sum(w for _, w in spec)
    if size >= total * 2:
        return spec
    if size >= len(spec) * 2 + 2:
        return [(c, max(1, w // 2)) for c, w in spec]
    return [(c, 1) for c, w in spec]


def paint_cell(px, rect, edges, spec, stripe, chamfer):
    """One panel or one frame cell.

    The band index is the distance to the nearest OUTSIDE edge, which makes
    corners mitre correctly with no corner special case. A grid cell is only
    "outside" on the edges it actually sits on, so a middle cell is pure fill
    and a top-left cell bands from both left and top."""
    x0, y0, w, h = rect
    spec = bands_for(min(w, h) if edges else max(w, h), spec)
    ramp = []
    for colour, width in spec:
        ramp.extend([colour] * width)
    for yy in range(h):
        for xx in range(w):
            d = 10 ** 6
            if "L" in edges:
                d = min(d, xx)
            if "R" in edges:
                d = min(d, w - 1 - xx)
            if "T" in edges:
                d = min(d, yy)
            if "B" in edges:
                d = min(d, h - 1 - yy)
            if chamfer and len(edges) >= 2:
                cx = xx if "L" in edges else (w - 1 - xx)
                cy = yy if "T" in edges else (h - 1 - yy)
                if ("L" in edges or "R" in edges) and ("T" in edges or "B" in edges) \
                        and cx + cy < 3:
                    px[x0 + xx, y0 + yy] = (0, 0, 0, 0)
                    continue
            if d < len(ramp):
                px[x0 + xx, y0 + yy] = ramp[d] + (255,)
            else:
                px[x0 + xx, y0 + yy] = stripe[(y0 + yy) % 2] + (255,)


def recolour_glyph(dst_px, src, rect, dest):
    """Arrows, ticks, icons and any slice no rule recognised.

    INVERTED, and opaque. Two reasons, both learned from screenshots:

      * The stock art is built for a DARK UI, so its light pixels are the
        foreground and its dark pixels are the panel. Mapping light to light
        kept the Trainer Card dark and its labels unreadable, and left every
        white arrow invisible on cream. Inverting puts the foreground dark on a
        light ground, which is what the rest of the theme now is.
      * Stock leans on partial alpha for depth. Carried onto a cream panel that
        reads as a grey haze, which is the "too much opacity" in the report. A
        pixel is either there or it is not here: below the threshold it is fully
        transparent, above it fully opaque. FireRed has no antialiasing either,
        so this is on-theme rather than a compromise."""
    sx, sy, w, h = rect
    dx, dy = dest[0], dest[1]
    ramp = [OUTER, NAVY, GREY, BEVEL_C, CREAM, WHITE]
    for yy in range(h):
        for xx in range(w):
            r, g, b, a = src.getpixel((sx + xx, sy + yy))
            if a < 90:
                dst_px[dx + xx, dy + yy] = (0, 0, 0, 0)
                continue
            lum = (r * 299 + g * 587 + b * 114) // 1000
            idx = (255 - lum) * len(ramp) // 256
            dst_px[dx + xx, dy + yy] = ramp[min(len(ramp) - 1, idx)] + (255,)


# ----------------------------------------------------------------- packing --
class Packer:
    """Shelf packer: rows of slots, one pixel of gutter so no two slices touch."""

    def __init__(self, width, pad=1):
        self.w, self.pad = width, pad
        self.x = self.y = self.row_h = 0

    def place(self, w, h):
        if self.x + w > self.w:
            self.x = 0
            self.y += self.row_h + self.pad
            self.row_h = 0
        rect = (self.x, self.y, w, h)
        self.x += w + self.pad
        self.row_h = max(self.row_h, h)
        return rect

    def height(self):
        return self.y + self.row_h


def build(spec, report=False):
    atlas = spec["file"]
    stock = load_block(os.path.join(STOCK, spec["source"]), atlas)
    src = Image.open(os.path.join(STOCK, atlas)).convert("RGBA")
    W, _ = src.size

    resolver = spec.get("resolver")

    def role_of(name):
        if resolver:
            return resolver(name)
        return role_for(name, spec["table"], spec["glyphs"], spec["keep"])

    out_el = copy.deepcopy(stock)
    packer = Packer(W)
    jobs, clamped, splits_added, flipped = [], [], [], []

    for grid in out_el.findall("grid"):
        role = role_of(grid.get("name").split(".")[0]) or "frame"
        if role in ("keep", None):
            role = "frame"
        cols = len(grid.get("weightsX", "0,1,0").split(","))
        areas = grid.findall("area")
        rows = (len(areas) + cols - 1) // cols
        for i, area in enumerate(areas):
            col, row = i % cols, i // cols
            edges = set()
            if col == 0:
                edges.add("L")
            if col == cols - 1:
                edges.add("R")
            if row == 0:
                edges.add("T")
            if row == rows - 1:
                edges.add("B")
            raw = area.get("xywh")
            if "-" in raw:
                flipped.append(grid.get("name"))
            w, h = rect_of(area)[2:]
            dst = packer.place(w, h)
            area.set("xywh", "%d,%d,%d,%d" % dst)
            jobs.append(("panel", dst, (edges, role)))

    # Every <area> that is not inside a <grid>, wherever it lives. Several sit
    # inside <select> blocks -- the scrollbars do -- carrying their own xywh and
    # no name of their own. findall("area") returns direct children only, so
    # those kept stock coordinates and collided with the repacked slices.
    parent = {child: el for el in out_el.iter() for child in el}
    in_grid = {id(a) for g in out_el.findall("grid") for a in g.iter("area")}

    def owning_name(el):
        while el is not None:
            if el.get("name"):
                return el.get("name")
            el = parent.get(el)
        return ""

    named = [a for a in out_el.iter("area")
             if a.get("xywh") and id(a) not in in_grid]
    groups = defaultdict(list)
    for a in named:
        groups[(rect_of(a), role_of(owning_name(a)))].append(a)

    for (rect, role), els in sorted(groups.items(), key=lambda kv: -kv[0][0][3]):
        for a in els:
            if "-" in a.get("xywh"):
                flipped.append(a.get("name") or owning_name(a))
        dst = packer.place(rect[2], rect[3])
        for a in els:
            a.set("xywh", "%d,%d,%d,%d" % dst)
            if role not in (None, "keep") and a.get("tint"):
                # A tint MULTIPLIES the art. label2.background ships
                # tint="#99949494", 60% grey, which is what kept the login
                # announcements dark and unreadable after the repaint. Anything
                # we paint outright must lose its tint; glyphs keep theirs,
                # since being tinted is the whole point of them.
                del a.attrib["tint"]
            if role not in (None, "keep") and band_total(role) \
                    and min(dst[2], dst[3]) >= 2 * band_total(role) + 1:
                # EMIT the 9-slice split, do not merely correct an existing one.
                # A painted panel with no splitx/splity is stretched whole, so
                # its border scales with the widget instead of staying put: the
                # fill ends up a floating inset rather than covering the row.
                # label2.background is a 5x5 with no splits at all, which is
                # exactly what left the announcement rows looking unfilled.
                b = band_total(role)
                a.set("splitx", "L%d,R%d" % (b, b))
                a.set("splity", "T%d,B%d" % (b, b))
                splits_added.append(a.get("name") or "")
            else:
                # too small to hold a border and a middle, or not ours to paint:
                # leave it stretching whole, but never with overrunning caps
                clamp_split(a, dst, clamped)
        jobs.append(("glyph" if role is None else
                     "keep" if role == "keep" else "panel",
                     dst, rect if role in (None, "keep") else ({"L", "R", "T", "B"}, role)))

    H = packer.height() + 1
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    px = out.load()
    if flipped:
        print("   normalised %d mirrored slices (negative extents): %s"
              % (len(flipped), ", ".join(sorted(set(flipped))[:4])))
    counts = defaultdict(int)
    for kind, dst, payload in jobs:
        counts[kind] += 1
        if kind == "glyph":
            recolour_glyph(px, src, payload, dst)
        elif kind == "keep":
            out.paste(src.crop((payload[0], payload[1],
                                payload[0] + payload[2], payload[1] + payload[3])),
                      (dst[0], dst[1]))
        else:
            edges, role = payload
            bands, stripe, chamfer = ROLES[role]
            paint_cell(px, dst, edges, bands, stripe, chamfer)

    res = os.path.join(MOD, "firered", "res")
    os.makedirs(res, exist_ok=True)
    out.save(os.path.join(res, os.path.basename(atlas)))
    emit_xml(out_el, spec["out"])

    print("%-26s %dx%d (stock %dx%d)  %d panels, %d glyphs, %d kept"
          % (os.path.basename(atlas), W, H, src.size[0], src.size[1],
             counts["panel"], counts["glyph"], counts["keep"]))
    if splits_added:
        print("   emitted 9-slice splits on %d painted slices" % len(splits_added))
    for name, attr, was, now, extent in clamped:
        print("   clamped inherited bad split: %s %s=%s -> %s (rect is %d px)"
              % (name, attr, was, now, extent))
    if report:
        for a in named:
            print("   %-40s %-12s %s"
                  % (owning_name(a), role_of(owning_name(a)) or "GLYPH", a.get("xywh")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    for spec in ATLASES:
        build(spec, args.report)
    emit_index()


def emit_index():
    """One include for theme.xml to carry, so adding an atlas here does not mean
    remembering to edit two theme files as well. Forgetting that is how an atlas
    gets generated and then never loaded."""
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<!--",
             "  Generated by tools/build_firered_atlas.py. Do not hand edit.",
             "  Every repainted atlas, in one include.",
             "-->", "<themes>"]
    for spec in ATLASES:
        lines.append('    <include filename="%s"/>' % spec["out"])
    lines += ["</themes>", ""]
    with open(os.path.join(MOD, "firered", "atlases-firered.xml"), "w") as fh:
        fh.write("\n".join(lines))
    print("index: %d atlases" % len(ATLASES))


def emit_xml(images_el, filename):
    ET.indent(images_el, space="    ", level=1)
    inner = ET.tostring(images_el, encoding="unicode").rstrip()
    text = """<?xml version="1.0" encoding="UTF-8"?>
<!--
  Generated by tools/build_firered_atlas.py. Do not hand edit.

  Slice NAMES match the stock theme exactly: names are what widgets bind to, and
  a typo defines art nothing reads. The xywh deliberately do NOT match. The stock
  atlases overlap themselves, which no repaint can survive, so every slice is
  repacked into its own rectangle and splitx/splity are rewritten to the band
  thickness actually painted. Shipping our own slice table is what makes that
  legal.
-->
<themes>
    %s
</themes>
""" % inner
    with open(os.path.join(MOD, "firered", filename), "w") as fh:
        fh.write(text)


if __name__ == "__main__":
    main()
