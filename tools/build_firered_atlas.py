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
# The Pokedex, measured off the Pokedex kit at 1:1.
DEX_DARK  = (0x7B, 0x63, 0x39)   # its outlines and the rule under the title
DEX_TAUPE = (0xC6, 0xB5, 0x8C)   # the frame and the title bar
DEX_LIGHT = (0xE7, 0xDE, 0xC6)   # the description band and the inner bevel
# The bag list panel and pocket tabs. Sampled off the Interface & Bag kit,
# which draws the bag screen at 1:1 GBA pixels (the panel is exactly 240x160),
# so these are the game's own values and not an eyeball match. The band stack,
# outer to inner, is grey 2 / cream 1 / light gold 2 / dark gold 2 / fill.
BAG_GREY  = (0x6B, 0x6B, 0x6B)   # its outer ring is grey, not #283030
BAG_BEVEL = (0xEF, 0xE7, 0xAD)
BAG_GOLD  = (0xF7, 0xCE, 0x73)   # the tab face and the panel's light band
BAG_GOLD2 = (0xD6, 0xB5, 0x52)   # the closed-tab face and the dark band
BAG_FILL  = (0xFF, 0xFF, 0xCE)   # the list ground
ORANGE_UL = (0xDE, 0x8C, 0x4A)   # the open-pocket underline
# The trainer card, off the Trainer Card Kit.
CARD_GREY   = (0x60, 0x60, 0x70)
CARD_ACC    = (0xA0, 0xA0, 0xA0)
HEADER_BLUE = (0x68, 0xA0, 0xD8)
CARD_ICE    = (0xE0, 0xF0, 0xF0)
BADGE_BAND  = (0x80, 0xB8, 0xE0)   # the badges band across the card's foot
BAND_EDGE   = (0x38, 0x70, 0x98)   # the ring pixel where a band meets the card
SWOOSH      = (0xC0, 0xD0, 0xE0)   # the card's arc, behind the trainer sprite
SWOOSH_LT   = (0xD0, 0xE0, 0xF0)
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
    # The pocket tabs, off the same kit as bag-list and ringed the same way:
    # grey outer, a cream hairline, then the gold face. The open pocket takes
    # the light gold and a pale ground; a closed one takes the dark gold and a
    # tan ground, so which pocket is open reads from across the window.
    "tab":        ([(BAG_GREY, 2), (BAG_BEVEL, 1), (BAG_GOLD, 2)],
                                                          (PALE, PALE_2),   False),
    "tab-off":    ([(BAG_GREY, 2), (BAG_BEVEL, 1), (BAG_GOLD2, 2)],
                                                          (TAN, TAN),       False),
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
    # The battle command menu -- FIGHT / BAG / POKeMON / RUN. FireRed draws it
    # as a WHITE window with black text, sitting on the navy band beside the
    # message box, and that pairing is the whole reason this can ship: 0.48 and
    # 0.49 tried the other one, white text straight on the navy, and it died on
    # the font set. There is no light face under 18pt and the description line
    # needs about 14. Black on white needs no light face at all.
    # Flat white rather than a scanline pair, like `label` above: the reference
    # window is one flat field, and a stripe at this size reads as dirt.
    "command":    ([(OUTER, 2), (GREY, 1), (BEVEL_G, 1)], (WHITE, WHITE),   False),
    "command-hi": ([(OUTER, 2), (BLUE, 2), (BEVEL_G, 1)], (WHITE, ICE),     False),
    "command-off":([(OUTER, 2), (DISABLED, 2)],           (WHITE, PALE),    False),
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
    # The bag list panel, measured off the Interface & Bag kit at 1:1: grey 2,
    # a one pixel cream hairline, light gold 2, dark gold 2, pale-yellow fill.
    # 0.24 had the cream INNERMOST, which put the lightest band against the
    # fill where it disappeared and left the panel edge reading as one slab.
    "bag-list":   ([(BAG_GREY, 2), (BAG_BEVEL, 1), (BAG_GOLD, 2), (BAG_GOLD2, 2)],
                                                          (BAG_FILL, PALE), False),
    # The Pokedex. Sampled off the Pokedex kit, which like the bag kit draws at
    # 1:1 GBA pixels, so these are the game's own three taupes. It is the one
    # screen FireRed paints earthy rather than gold or blue, and 0.30's guess at
    # it (#283030 over #C0B088 over #E0D8C0) was close in feel and wrong in
    # every value.
    "dex-frame":  ([(DEX_DARK, 2), (DEX_TAUPE, 3), (DEX_LIGHT, 1)],
                                                          (CREAM, WHITE),   False),
    # The dex's own label plates: a title in taupe, its value on white. Both
    # slices are dex-only, which is what makes repainting them safe.
    "dex-title":  ([(DEX_DARK, 1), (DEX_TAUPE, 2)],  (DEX_TAUPE, DEX_TAUPE), False),
    "dex-value":  ([(DEX_DARK, 1)],                  (WHITE, DEX_LIGHT),     False),
    # The entry panel. FireRed's dex draws its Pokemon on a plain WHITE card
    # ringed in dark taupe, with no scanline: the one light surface in the theme
    # that stays flat, because a sprite sits on it.
    "dex-panel":  ([(DEX_DARK, 2), (DEX_LIGHT, 1)],  (WHITE, WHITE),         False),
}

# Stock slice GEOMETRY we deliberately override, name -> {attribute: value}.
# Rare, and every entry has to earn itself: the emitted table otherwise mirrors
# stock, which is what keeps a client update from silently breaking us.
GEOMETRY = {
    # Settings' vertical tabs. Stock draws the SELECTED tab 18px wider on the
    # left (inset="0,-18,0,0") and leaves the rest flush, so an unselected tab's
    # background starts 18px right of the tab's own left edge -- and its label,
    # which tabbutton pads by 0 on the left, hangs outside its box. Stock hides
    # that because its tab art is a soft left-pinned shape; ours is a complete
    # ringed box, so an unselected tab reads as a small floating box with the
    # text spilling out of it. Give every tab the same inset. Which one is open
    # is already legible from the colour: light gold on pale versus dark on tan.
    "ui-tab-vertical.default": {"inset": "0,-18,0,0"},
    # A translucent plate for the overworld HUD, and label4 is the slice that
    # can carry it: nothing in the stock theme tree references it, so a tint
    # here reaches the HUD and nothing else. Painted slices normally lose their
    # tint outright, colour and alpha together; this one is put back by hand
    # with the colour neutralised to white, so the multiply is the identity and
    # only the 0xB4 alpha survives.
    "label4.background": {"tint": "#B4FFFFFF"},
    # FireRed's battle HUD is ONE cream box holding the name and the bar
    # together. PokeMMO splits them: battle-gui-enemy/self draw the bar, and the
    # name is a separate redlabel above it. A theme cannot merge two widgets,
    # but it CAN draw one widget's background outside its own bounds, which is
    # the same trick the dex entry card uses.
    #
    # 26 is measured off a battle screenshot: the name plate's top sits 50
    # screenshot pixels above the bar, and the shot is 2x. Expanding the bar's
    # plate up by that much puts the name inside it, so the pair reads as the
    # single box the reference draws.
    "battle-ui-enemy": {"inset": "-26,0,0,0"},
    "battle-ui-self": {"inset": "-26,0,0,0"},
    "battle-ui-self-slim": {"inset": "-26,0,0,0"},
}

# Extra band edges for grid cells whose POSITION does not earn them one.
GRID_EDGES = {
    # The Summary frame's bottom band is where "Item Held" lives, and stock
    # gives that widget background "none": the dark grid cell behind it WAS the
    # box. On a cream frame there is no box at all. Handing the widget a plate
    # of its own is not the answer either -- the client sizes and places it in
    # code, so the plate overhung the frame's bottom edge and still stopped
    # short of its right. Band the TOP of both bottom cells instead. The rule
    # spans the full width by construction and lands exactly on the frame's own
    # edge, because it IS the frame's own edge.
    # Right cell only. Banding the LEFT one too drew a rule straight through
    # "What are EVs?" and "What are IVs?", which the client lays out just above
    # the band on those tabs. The rule exists to box the held item, and the held
    # item is on the right.
    ("mi-frame-grid", 2, 1): "T",
}

# Roles that keep the stock SHAPE and stamp it in ONE flat colour, alpha
# preserved. See stamp_glyph for why the ordinary glyph recolour cannot serve.
STAMPS = {
    "stamp-dark": OUTER,
    "stamp-grey": GREY,
}

# name prefix -> role. Longest prefix wins, so specific beats general.
ROLE_BY_PREFIX = [
    ("ui-frame-red",              "frame-red"),
    ("ui-frame-green",            "frame-green"),
    ("ui-frame",                  "frame"),
    ("ui-inner-frame-inverted",   "inverted"),
    ("ui-inner-frame-tabbed-dex", "dex-frame"),
    ("ui-inner-frame-tabbed",     "inner"),
    ("ui-inner-frame-tab2",       "bag-list"),
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
    # inner-area backs monsterdex-box and nothing else in the whole stock theme,
    # which is what makes it safe to give the dex its own panel. It is NOT the
    # sprite box, which is monstergear-pic.background; 0.32 and 0.33 both aimed
    # here by mistake.
    ("inner-area",             "dex-panel"),
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
    # Longest prefix wins, so these two beat the generic label-bg- below.
    ("label-bg-title-dex",     "dex-title"),
    ("label-bg-value-dex",     "dex-value"),
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
    # The nine Summary page tabs. They are ICONS on transparent -- a monitor, a
    # ruler, a bar chart, a DNA helix -- not panels, and the "tab" rule below
    # would swallow them on the name alone. 0.24 did exactly that and painted
    # nine opaque boxes over nine icons, which is the blank strip in the top
    # left of the Summary screen. Selected is the dark glyph, default the grey.
    if n.startswith("mi-tab"):
        return "stamp-dark" if "selected" in n else "stamp-grey"
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
    # The battle command menu. These four 209x52 slices are the only battle-hud
    # art the FIGHT / BAG / POKeMON / RUN buttons can take -- stock points them
    # at the GLOBAL `button.*` family, which is every button in the client, so
    # painting the menu there would repaint the whole UI. Named before the
    # generic `button` rule below, which would otherwise claim them for cream.
    if n.startswith("battle-button-switch"):
        if ".disabled" in n:
            return "command-off"
        if ".hover" in n or ".selected" in n:
            return "command-hi"
        return "command"
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


def paint_bag_tab(px, rect, src=None, srect=None):
    """The bag's OPEN pocket tab, off the Interface & Bag kit.

    The kit draws it grey-ringed with a one pixel cream hairline inside, a flat
    light-gold face, and the orange bar FireRed slides under the pocket name.
    That bar sits three pixels clear of the bottom edge, not flush on it: flush
    reads as a shadow, inset reads as an underline. Flat is correct here --
    accent bars are the one surface the spec leaves unstriped.

    Stock splits are L12,R12 with no splity, so the middle stretches
    horizontally and the underline has to span the full width to survive it."""
    x0, y0, w, h = rect
    ul_lo, ul_hi = h - 6, h - 3          # the underline, inset from the bottom
    for yy in range(h):
        for xx in range(w):
            d = min(xx, w - 1 - xx, yy, h - 1 - yy)
            if d < 2:
                c = BAG_GREY
            elif d < 3:
                c = BAG_BEVEL
            elif ul_lo <= yy < ul_hi:
                c = ORANGE_UL
            else:
                c = BAG_GOLD
            px[x0 + xx, y0 + yy] = c + (255,)


def _rounded_depth(xx, yy, x0, y0, x1, y1, r):
    """How many pixels inside a rounded rect (>=1), or 0 if outside."""
    if xx < x0 or xx > x1 or yy < y0 or yy > y1:
        return 0
    dx = min(xx - x0, x1 - xx)
    dy = min(yy - y0, y1 - yy)
    if dx >= r or dy >= r:
        return min(dx, dy) + 1
    ex, ey = r - dx, r - dy
    d = r - (ex * ex + ey * ey) ** 0.5
    return max(0, int(d) + 1)


# The eight badge slots in the stock 454x287 card texture, measured off it:
# first slot at x=39, 48 apart, 38 wide, y=233 and 35 tall.
#
# These are NOT free geometry. The client lays its badge sprites out in code
# against the stock texture, and the texture carries no splitx/splity, so it is
# drawn whole and any slot pitch but the stock one drifts. 0.24 spaced its slots
# evenly across the card instead, 53 apart starting at x=23; by the eighth badge
# the sprite had walked 35px clear of the slot painted for it, which is the
# misalignment on the card. Positions are kept as fractions of the stock size so
# a differently sized rect still lands them right.
TC_REF_W, TC_REF_H = 454, 287
TC_BADGE = (39, 233, 38, 35, 48)   # x0, y0, w, h, pitch


def paint_trainer_card(px, rect, src=None, srect=None):
    """The whole trainer card in one texture, as the kit draws it: the teal
    1:3 striped ground, a rounded white card with a grey double ring, the
    #68A0D8 header band, a 1:1 scanlined body and a row of eight rounded badge
    slots along the bottom. Stock is a single 454x287 area with no splits, so
    the widget stretches it whole and every band scales with it."""
    x0, y0, w, h = rect
    inset, r = 4, 10
    cx0, cy0, cx1, cy1 = inset, inset, w - 1 - inset, h - 1 - inset
    # FireRed's header does NOT cap the card. Five of the reference's 160 rows
    # of white body sit above it, so the blue band floats inside the card, and
    # the badges band leaves the same five rows under it at the foot. That gap
    # is most of what separated this from the real card.
    #
    # Its height does not scale as cleanly: 20 of 160 rows comes to 36 here, and
    # 36 collides, because the client draws "Issued" at texture row 52 and the
    # band would end exactly on it. 26 keeps the float and keeps the date's air.
    # The trainer name occupies rows 22 to 37, which 26 still contains.
    gap = max(1, int(round(5 / 160.0 * h)))
    header_h = 26
    hdr_lo = inset + 3 + gap
    hdr_hi = hdr_lo + header_h
    fx, fy = w / float(TC_REF_W), h / float(TC_REF_H)
    bx0, by0, bw, bh, pitch = TC_BADGE
    slots = [(int(round((bx0 + i * pitch) * fx)), int(round(by0 * fy)),
              max(1, int(round(bw * fx))), max(1, int(round(bh * fy))))
             for i in range(8)]
    # FireRed stands its badges on their own light blue band across the foot of
    # the card -- 26 of that card's 160 rows -- not loose on the body, and its
    # slots are circles rather than rounded squares. The band is derived from
    # the slots so it stays centred on positions the client fixes, and the slot
    # radius is half the short side, which turns a 38x35 rect into an ellipse
    # that reads as FireRed's circle.
    band_y0 = min(s[1] for s in slots) - 4
    band_y1 = max(s[1] + s[3] for s in slots) + 4
    # The pale arc behind the trainer. Fitting its left boundary row by row in
    # the reference gives a circle, centre (0.95w, 0.72h) and radius 0.47h, with
    # everything inside it painted #C0D0E0/#D0E0F0 instead of the white body.
    # MIRRORED here: FireRed stands its trainer on the right and PokeMMO stands
    # ours on the left, and the arc belongs behind the sprite, not behind the
    # stats. The badges band and the header both paint over it, as they do
    # there.
    sw_cx, sw_cy, sw_r2 = 0.05 * w, 0.72 * h, (0.47 * h) ** 2
    for yy in range(h):
        # Neither band carries an edge line: the reference is flat #68A0D8 and
        # flat #80B8E0 top to bottom. Where a band reaches the card's inner ring
        # that one grey pixel takes the band's own dark shade instead, which is
        # the only place the ring is not grey.
        in_header = hdr_lo <= yy < hdr_hi
        in_band = band_y0 <= yy < band_y1
        for xx in range(w):
            d = _rounded_depth(xx, yy, cx0, cy0, cx1, cy1, r)
            if d == 0:                       # the striped ground outside
                c = TEAL if yy % 4 == 0 else TEAL_LT
            elif d <= 2:
                c = CARD_GREY
            elif d == 3:
                c = BAND_EDGE if (in_header or in_band) else CARD_ACC
            elif in_header:
                c = HEADER_BLUE
            else:
                # The band is a GROUND, not a branch of its own: the slot loop
                # below still has to run over it, or the eight badge slots
                # vanish into flat blue.
                if in_band:
                    c = BADGE_BAND
                elif (xx - sw_cx) ** 2 + (yy - sw_cy) ** 2 <= sw_r2:
                    c = SWOOSH_LT if yy % 2 else SWOOSH
                else:
                    c = WHITE if yy % 2 else CARD_ICE
                for sx, sy, sw, sh in slots:
                    if sx <= xx < sx + sw and sy <= yy < sy + sh:
                        sd = _rounded_depth(xx, yy, sx, sy, sx + sw - 1,
                                            sy + sh - 1, min(sw, sh) // 2)
                        if sd == 1:
                            c = CARD_GREY
                        elif sd > 1:
                            c = WHITE if yy % 2 else CARD_ICE
                        break
            px[x0 + xx, y0 + yy] = c + (255,)


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
         table=None, glyphs=GLYPH_PREFIXES, keep=(),
         special={"ui-tab.active.color": paint_bag_tab}),
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
        ("res/contestgui.png",    "contest-firered.xml"),
        ("res/caught-window.png", "caught-firered.xml"),
        ("res/breedwindow.png",   "breed-firered.xml"),
        ("res/preview-field.png", "preview-firered.xml"),
    ]
] + [
    # The trainer card is one 454x287 texture, so it gets a bespoke painter
    # rather than a role: the glyph recolour that handled it through 0.23 kept
    # the stock composition, which is not FireRed's card at all.
    dict(file="res/MainTCTexture.png", source="gfx.xml", out="traincard-firered.xml",
         table=None, glyphs=(), keep=(), resolver=role_ingame,
         special={"trainer-card.background": paint_trainer_card}),
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


def grid_cells(grid):
    """Every POSITIONAL child of a <grid>, areas and aliases alike.

    A cell may be an <alias> reusing a slice declared elsewhere. Enumerating
    only the areas slides every later cell one position back and the builder
    bands them from the wrong edges. Named so a test can hold the builder to it.
    """
    return [c for c in grid if c.tag in ("area", "alias")]


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
def bands_for(w, h, spec, edges=()):
    """Shrink the band stack so a small slice still shows every band.

    Room is needed PER AXIS, and only on the axes the cell actually bands from.
    A standalone slice bands left and right, so it needs twice the stack across
    with fill between, or it comes out pure border. A grid's left-edge cell
    bands from one side only, so the stack alone is enough -- and its HEIGHT
    does not constrain a vertical band at all.

    Measuring one number against min(w, h) got both wrong and is what flattened
    the bag. bag-list is a seven pixel FireRed border, ui-inner-frame-tab2 is a
    grid of 10px cells, and the cell that carries most of the panel's height is
    10 wide by 4 tall: min() called that 4, shrank the stack to a two pixel
    hairline, and the panel shipped with no visible edge at all."""
    total = sum(bw for _, bw in spec)

    def need(a, b):
        if a in edges and b in edges:
            return total * 2        # bands from both sides, plus fill between
        if a in edges or b in edges:
            return total            # one side only; the rest of the axis fills
        return 0                    # this axis is not banded

    if w >= need("L", "R") and h >= need("T", "B"):
        return spec
    if max(w, h) >= len(spec) * 2 + 2:
        return [(c, max(1, bw // 2)) for c, bw in spec]
    return [(c, 1) for c, bw in spec]


def paint_cell(px, rect, edges, spec, stripe, chamfer):
    """One panel or one frame cell.

    The band index is the distance to the nearest OUTSIDE edge, which makes
    corners mitre correctly with no corner special case. A grid cell is only
    "outside" on the edges it actually sits on, so a middle cell is pure fill
    and a top-left cell bands from both left and top."""
    x0, y0, w, h = rect
    spec = bands_for(w, h, spec, edges)
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


def stamp_glyph(dst_px, src, rect, dest, colour):
    """Keep the stock SHAPE, paint every opaque pixel one flat colour, and keep
    the transparency around it.

    recolour_glyph INVERTS luminance, which is right for art drawn for a dark UI
    where the light pixels are the foreground. A slice that is ALREADY a dark
    glyph on transparent is the opposite case: inverting it paints the glyph
    white, and white on cream is nothing at all. Stamping keeps the icon and
    keeps the hole around it, so whatever the widget sits on shows through."""
    sx, sy, w, h = rect
    dx, dy = dest[0], dest[1]
    for yy in range(h):
        for xx in range(w):
            a = src.getpixel((sx + xx, sy + yy))[3]
            dst_px[dx + xx, dy + yy] = colour + (255,) if a >= 90 else (0, 0, 0, 0)


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
        if role in ("keep", None) or role in STAMPS:
            role = "frame"
        cols = len(grid.get("weightsX", "0,1,0").split(","))
        # EVERY positional child, not just the <area>s. A grid cell may be an
        # <alias> where it reuses a slice declared elsewhere: mi-frame-grid
        # aliases mi-bg for its middle-right cell, ui-checkbox.checked does the
        # same. findall("area") skipped those and slid every later cell one
        # place back, so the Summary frame painted its bottom-LEFT cell as if it
        # were middle-right -- that corner shipped with no left and no bottom
        # border at all, and the panel simply ended against the world.
        cells = grid_cells(grid)
        rows = (len(cells) + cols - 1) // cols
        for i, area in enumerate(cells):
            col, row = i % cols, i // cols
            if area.tag != "area":
                continue          # an alias owns a cell but no pixels of its own
            edges = set()
            if col == 0:
                edges.add("L")
            if col == cols - 1:
                edges.add("R")
            if row == 0:
                edges.add("T")
            if row == rows - 1:
                edges.add("B")
            edges |= set(GRID_EDGES.get((grid.get("name"), row, col), ""))
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
    special = spec.get("special") or {}

    def key_of(name):
        # A bespoke painter beats any role. The tuple key keeps two specials
        # sharing a rect from collapsing into one slot.
        if name in special:
            return ("special", name)
        return role_of(name)

    groups = defaultdict(list)
    for a in named:
        groups[(rect_of(a), key_of(owning_name(a)))].append(a)

    for (rect, role), els in sorted(groups.items(), key=lambda kv: -kv[0][0][3]):
        for a in els:
            if "-" in a.get("xywh"):
                flipped.append(a.get("name") or owning_name(a))
        dst = packer.place(rect[2], rect[3])
        if isinstance(role, tuple):
            for a in els:
                a.set("xywh", "%d,%d,%d,%d" % dst)
                if a.get("tint"):
                    del a.attrib["tint"]   # painted outright, same as panels
                clamp_split(a, dst, clamped)
            # the stock rect rides along so a painter can read stock pixels
            jobs.append(("special", dst, (special[role[1]], rect)))
            continue
        painted = role not in (None, "keep") and role not in STAMPS
        for a in els:
            a.set("xywh", "%d,%d,%d,%d" % dst)
            if painted and a.get("tint"):
                # A tint MULTIPLIES the art. label2.background ships
                # tint="#99949494", 60% grey, which is what kept the login
                # announcements dark and unreadable after the repaint.
                #
                # The tint's ALPHA goes with it, and that is deliberate. 0.28
                # tried keeping the alpha and neutralising only the colour, to
                # rescue the sheet behind the quit prompt: label1..7 and
                # table-row are ONE 5x5 stock slice told apart purely by tint,
                # and label1's 0x95 is what made that sheet a dim rather than a
                # wall. It worked, and it also made the login announcements 58%
                # transparent, because they are the same slice. The sheet has
                # its own widget -- confirm-widget, in widgets-firered.xml --
                # so it is fixed there instead and the plates stay opaque.
                del a.attrib["tint"]
            if painted and band_total(role) \
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
                     "keep" if role == "keep" else
                     "stamp" if role in STAMPS else "panel",
                     dst,
                     rect if role in (None, "keep") else
                     (rect, STAMPS[role]) if role in STAMPS else
                     ({"L", "R", "T", "B"}, role)))

    for a in named:
        for attr, val in GEOMETRY.get(a.get("name") or "", {}).items():
            a.set(attr, val)

    H = packer.height() + 1
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    px = out.load()
    if flipped:
        print("   normalised %d mirrored slices (negative extents): %s"
              % (len(flipped), ", ".join(sorted(set(flipped))[:4])))
    counts = defaultdict(int)
    for kind, dst, payload in jobs:
        counts[kind] += 1
        if kind == "special":
            payload[0](px, dst, src, payload[1])
        elif kind == "glyph":
            recolour_glyph(px, src, payload, dst)
        elif kind == "stamp":
            stamp_glyph(px, src, payload[0], dst, payload[1])
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

    print("%-26s %dx%d (stock %dx%d)  %d panels, %d glyphs, %d stamped, %d kept"
          % (os.path.basename(atlas), W, H, src.size[0], src.size[1],
             counts["panel"], counts["glyph"], counts["stamp"], counts["keep"]))
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
