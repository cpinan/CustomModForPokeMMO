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
ATLAS = "res/pokemmo_ui.png"

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

# Shapes, not panels. Redrawing these as frames destroys them, so their stock
# pixels are kept and only recoloured.
GLYPH_PREFIXES = (
    "ui-status-", "ui-sort-", "ui-table-sort-", "ui-c-menu", "ui-color.",
    "ui-spacer", "ui-button-picker", "button-npc-dark", "ui-checkbox.f",
)


def role_for(name):
    if name.startswith(GLYPH_PREFIXES):
        return None
    best = None
    for prefix, role in ROLE_BY_PREFIX:
        if name.startswith(prefix) and (best is None or len(prefix) > len(best[0])):
            best = (prefix, role)
    return best[1] if best else None



# ------------------------------------------------------------------ parse ---
def load_block(path):
    """The <images> element for our atlas, as XML. Regexes miss attribute
    orderings; there are plenty of them in this file."""
    root = ET.parse(path).getroot()
    for images in root.iter("images"):
        if images.get("file") == ATLAS:
            return images
    sys.exit("no <images> block for %s in %s" % (ATLAS, path))


def rect_of(el):
    return tuple(int(v) for v in el.get("xywh").split(","))


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
    """Arrows, ticks and status icons are shapes, not panels. Redrawing them as
    frames destroys them, so keep the stock pixels and move the tones onto the
    FireRed ramp."""
    sx, sy, w, h = rect
    dx, dy = dest[0], dest[1]
    ramp = [OUTER, NAVY, GREY, BEVEL_C, CREAM, WHITE]
    for yy in range(h):
        for xx in range(w):
            r, g, b, a = src.getpixel((sx + xx, sy + yy))
            if a < 40:
                dst_px[dx + xx, dy + yy] = (0, 0, 0, 0)
                continue
            lum = (r * 299 + g * 587 + b * 114) // 1000
            dst_px[dx + xx, dy + yy] = ramp[min(len(ramp) - 1,
                                                lum * len(ramp) // 256)] + (a,)


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()

    stock = load_block(os.path.join(STOCK, "gfx_ui.xml"))
    src = Image.open(os.path.join(STOCK, ATLAS)).convert("RGBA")
    W, _ = src.size

    out_el = copy.deepcopy(stock)
    packer = Packer(W)
    jobs = []          # (kind, dst, payload)

    # --- grid cells: each gets its own slot, even if two grids shared a rect ---
    for grid in out_el.findall("grid"):
        role = role_for(grid.get("name").split(".")[0]) or "frame"
        wx = grid.get("weightsX", "0,1,0").split(",")
        cols = len(wx)
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
            w, h = rect_of(area)[2:]
            dst = packer.place(w, h)
            area.set("xywh", "%d,%d,%d,%d" % dst)
            jobs.append(("panel", dst, (edges, role)))

    # --- named areas: one slot per (rect, role); aliases share ---
    clamped = []
    named = [a for a in out_el.findall("area") if a.get("name")]
    groups = defaultdict(list)
    for a in named:
        groups[(rect_of(a), role_for(a.get("name")))].append(a)

    for (rect, role), els in sorted(groups.items(), key=lambda kv: -kv[0][0][3]):
        dst = packer.place(rect[2], rect[3])
        for a in els:
            a.set("xywh", "%d,%d,%d,%d" % dst)
            if role is not None and (a.get("splitx") or a.get("splity")):
                # keep the 9-slice split on the band we actually painted
                b = min(band_total(role), max(1, min(dst[2], dst[3]) // 2 - 1))
                a.set("splitx", "L%d,R%d" % (b, b))
                a.set("splity", "T%d,B%d" % (b, b))
            else:
                clamp_split(a, dst, clamped)
        if role is None:
            jobs.append(("glyph", dst, rect))
        else:
            jobs.append(("panel", dst, ({"L", "R", "T", "B"}, role)))

    # ------------------------------------------------------------- paint ----
    H = packer.height() + 1
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    px = out.load()
    panels = glyphs = 0
    for kind, dst, payload in jobs:
        if kind == "glyph":
            recolour_glyph(px, src, payload, dst)
            glyphs += 1
        else:
            edges, role = payload
            spec, stripe, chamfer = ROLES[role]
            paint_cell(px, dst, edges, spec, stripe, chamfer)
            panels += 1

    res = os.path.join(MOD, "firered", "res")
    os.makedirs(res, exist_ok=True)
    out.save(os.path.join(res, "pokemmo_ui.png"))
    emit_xml(out_el)

    print("atlas %dx%d (stock %dx%d) -- %d panels, %d glyphs, %d slots"
          % (W, H, src.size[0], src.size[1], panels, glyphs, len(jobs)))
    for name, attr, was, now, extent in clamped:
        print("   clamped inherited bad split: %s %s=%s -> %s (rect is %d px)"
              % (name, attr, was, now, extent))
    if args.report:
        for grid in out_el.findall("grid"):
            print("   grid %-40s %s" % (grid.get("name"),
                                        role_for(grid.get("name").split(".")[0])))
        for a in named:
            print("   area %-40s %-12s %s" % (a.get("name"),
                                              role_for(a.get("name")) or "GLYPH",
                                              a.get("xywh")))


def emit_xml(images_el):
    ET.indent(images_el, space="    ", level=1)
    inner = ET.tostring(images_el, encoding="unicode").rstrip()
    text = """<?xml version="1.0" encoding="UTF-8"?>
<!--
  Generated by tools/build_firered_atlas.py. Do not hand edit.

  Slice NAMES match the stock theme exactly: names are what widgets bind to, and
  a typo defines art nothing reads. The xywh deliberately do NOT match. The stock
  atlas overlaps itself in 129 places, which no repaint can survive, so every
  slice is repacked into its own rectangle and splitx/splity are rewritten to the
  band thickness actually painted. Shipping our own slice table is what makes
  that legal.
-->
<themes>
    %s
</themes>
""" % inner
    with open(os.path.join(MOD, "firered", "gfx_ui-firered.xml"), "w") as fh:
        fh.write(text)


if __name__ == "__main__":
    main()
