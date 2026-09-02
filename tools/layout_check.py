"""Check a themed widget block's geometry WITHOUT launching the client.

    python3 tools/layout_check.py                 # the client's own window size
    python3 tools/layout_check.py --window 1920x1080
    python3 tools/layout_check.py --solve         # what padding right-aligns it

WHY THIS EXISTS
Every layout number in this theme so far was read off a screenshot, which costs
a client restart, a login and a wild encounter per guess -- and three of those
guesses were wrong in a way arithmetic would have caught: 0.51 put 300 in the
TOP slot and the menu left the screen, 0.53 put 860 in the LEFT slot and it left
the screen the other way, with its text overlapping because the rows were 8px
short. None of that needed the game. A button's width is its text's width plus
its border, the text's width is a TTF metric, and both are on this disk.

WHAT IT MODELS
One thing, deliberately: the battle command block -- FIGHT / BAG / POKeMON / RUN
laid out 2x2 inside `battle-panel`, which spans the window. That is the block
this theme is moving, and a model of exactly it is worth more than a general
layout engine that is wrong in its own way.

  button width  = max(minWidth, longest line + left border + right border)
  button height = max(minHeight, line1 + line2 + top border + bottom border)
  block         = 2 buttons + defaultGap, both axes
  content box   = panel width - (left border + right border)

TWL's <border> is (top, left, bottom, right) -- proven on hardware 2026-09-02
by putting 300 in slot one and watching the menu drop off the bottom.

WHAT IT CANNOT SEE
Whether the client anchors the block left or centres it in the content box, and
whether the band's height is fixed or grows. Both are assumptions here, marked
ANCHOR and BAND_H, and both are falsifiable from one screenshot each. It reports
what it assumed rather than hiding it.
"""
import argparse
import os
import re
import sys
import xml.etree.ElementTree as ET

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOD = os.path.join(REPO, "mods", "vanbobby-firered-theme")
CLIENT = os.environ.get("POKEMMO_HOME") or os.path.expanduser(
    "~/Library/Application Support/com.pokeemu.macos/pokemmo-client-live")
THEMES = os.path.join(CLIENT, "data", "themes", "default")
CONFIG = os.path.join(CLIENT, "config", "main.properties")

# The block is laid out from the LEFT of the content box: 0.52 moved it right by
# adding left padding, which is what a left anchor does and a centred one would
# have moved by half. Falsified the moment a padding change moves it by anything
# other than 1:1.
ANCHOR = "left"

# The client's OWN content to the left of the command block -- the message
# column. Our padding adds to it rather than replacing it, which is why 0.53's
# first model said "fits" while the screen showed the block hanging off the
# right edge.
#
# Solved from the two screenshots that cost a restart each, at a 1356px window:
#   left=300 -> block sat around mid-band, well short of the right edge
#   left=860 -> block sat ON the right edge and spilled
# 860 + OFFSET + 420 ~= 1356 puts OFFSET near 76; 300 + 76 + 420 = 796, about
# 58% across, which is where the mid-band shot puts it. Anything between 70 and
# 120 fits both observations, so this takes the middle and says so.
OFFSET = 95

# The navy band's height. The client sizes it, and it is the one number here
# that cannot be derived: it comes from the stock layout, not the theme. What
# matters is that the block must not GROW it -- stock rows are exactly minHeight
# 52, so any top/bottom border on a button pushes the band taller than the
# client budgeted and the second row clips off the bottom of the window. That is
# what 0.53's `4,10,4,10` did.
BAND_H = 52 * 2 + 2

# The four buttons the command menu actually shows, and the second line each
# carries. Text comes from the client's own strings, not from guesswork.
BUTTONS = [
    ("FIGHT",    "Select your attack move."),
    ("BAG",      "Use an item."),
    ("POKEMON",  "Switch current Pokemon."),
    ("RUN",      "Escape from battle."),
]


def window_size():
    w = h = None
    try:
        for line in open(CONFIG, encoding="utf-8", errors="replace"):
            if line.startswith("client.graphics.width="):
                w = int(line.split("=", 1)[1])
            elif line.startswith("client.graphics.height="):
                h = int(line.split("=", 1)[1])
    except OSError:
        pass
    return (w or 1356, h or 946)


def font_table():
    """face name -> (ttf path, pixel size)."""
    out = {}
    root = ET.parse(os.path.join(THEMES, "fonts.xml")).getroot()
    for el in root.iter("fontDef"):
        name, fn = el.get("name"), el.get("filename")
        if not name or not fn:
            continue
        out[name] = (os.path.join(THEMES, fn), int(el.get("size", "12")))
    return out


def parse_border(text):
    """TWL: 1 value = all sides, 4 values = top, left, bottom, right."""
    v = [int(x) for x in text.split(",")]
    if len(v) == 1:
        return dict(top=v[0], left=v[0], bottom=v[0], right=v[0])
    if len(v) == 2:                       # TWL reads this as horizontal, vertical
        return dict(top=v[1], left=v[0], bottom=v[1], right=v[0])
    return dict(top=v[0], left=v[1], bottom=v[2], right=v[3])


def theme_params(path, name):
    """The params one <theme name="..."> block sets, as plain strings."""
    root = ET.parse(path).getroot()
    for th in root.iter("theme"):
        if th.get("name") != name:
            continue
        out = {}
        for p in th.findall("param"):
            key = p.get("name") or "_image"
            child = list(p)
            out[key] = child[0].text if child else p.text
        return out
    return {}


def text_width(path, size, s):
    from PIL import ImageFont
    try:
        f = ImageFont.truetype(path, size)
    except OSError:
        # .ttc collections need an index; face 0 is the Latin one here.
        f = ImageFont.truetype(path, size, index=0)
    return int(round(f.getlength(s)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", help="WIDTHxHEIGHT, default: the client's own")
    ap.add_argument("--solve", action="store_true",
                    help="print the left padding that right-aligns the block")
    a = ap.parse_args()

    if a.window:
        w, h = (int(x) for x in a.window.lower().split("x"))
    else:
        w, h = window_size()

    widgets = os.path.join(MOD, "firered", "widgets-firered.xml")
    fonts = font_table()

    panel = theme_params(widgets, "battle-panel")
    button = theme_params(widgets, "battle-fight")
    pb = parse_border(panel.get("border", "0"))
    bb = parse_border(button.get("border", "0"))

    face1 = button.get("font", "mechabold")
    face2 = button.get("font2", "main-small")
    if face1 not in fonts or face2 not in fonts:
        sys.exit("unknown face: %s / %s" % (face1, face2))
    p1, s1 = fonts[face1]
    p2, s2 = fonts[face2]

    # rbattle-big, the stock base these buttons carry.
    MIN_W, MIN_H, GAP = 209, 52, 2

    rows = []
    for label, desc in BUTTONS:
        tw = max(text_width(p1, s1, label), text_width(p2, s2, desc))
        bw = max(MIN_W, tw + bb["left"] + bb["right"])
        bh = max(MIN_H, s1 + s2 + bb["top"] + bb["bottom"] + 6)
        rows.append((label, tw, bw, bh))

    col_w = max(r[2] for r in rows)
    row_h = max(r[3] for r in rows)
    block_w = col_w * 2 + GAP
    block_h = row_h * 2 + GAP
    content_w = w - pb["left"] - pb["right"]
    content_h = BAND_H - pb["top"] - pb["bottom"]
    left_edge = pb["left"] + OFFSET
    if ANCHOR != "left":
        left_edge += max(0, (content_w - block_w) // 2)
    right_edge = left_edge + block_w

    print("window            %dx%d   (%s)" % (w, h, "given" if a.window else "client config"))
    print("battle-panel      border top=%(top)d left=%(left)d bottom=%(bottom)d right=%(right)d" % pb)
    print("button            border top=%(top)d left=%(left)d bottom=%(bottom)d right=%(right)d" % bb)
    print("fonts             %s %dpx / %s %dpx" % (face1, s1, face2, s2))
    print()
    for label, tw, bw, bh in rows:
        note = "" if bw <= MIN_W else "  <- wider than the stock 209 because of its text"
        print("  %-9s text %4dpx  ->  button %dx%d%s" % (label, tw, bw, bh, note))
    print()
    print("block             %dx%d at x=%d..%d  (anchor=%s, message column %d)"
          % (block_w, block_h, left_edge, right_edge, ANCHOR, OFFSET))
    print("content box       %dx%d  (band height %d, the stock two rows)"
          % (content_w, content_h, BAND_H))

    problems = []
    if right_edge > w:
        problems.append("block runs %dpx off the right edge of the window" % (right_edge - w))
    if block_w > content_w:
        problems.append("block is %dpx wider than the content box" % (block_w - content_w))
    if block_h > content_h:
        problems.append("block is %dpx taller than the band, so the second row clips"
                        % (block_h - content_h))
    if row_h < s1 + s2 + 8:
        problems.append("row height %d leaves the two lines under 8px apart; they will touch"
                        % row_h)
    if bb["top"] or bb["bottom"]:
        problems.append("button border adds %dpx of height per row; the band is the client's "
                        "and does not grow, so the second row clips. Keep top and bottom at 0."
                        % (bb["top"] + bb["bottom"]))

    fit_left = w - pb["right"] - block_w - OFFSET
    if a.solve or problems:
        print()
        print("to sit against the right edge:  battle-panel border top=%d left=%d bottom=%d right=%d"
              % (pb["top"], fit_left, pb["bottom"], pb["right"]))
        print("to stop the rows clipping:      button border top/bottom <= %d"
              % max(0, (content_h - GAP) // 2 - (s1 + s2 + 6) // 2))

    slack = w - pb["right"] - right_edge
    if not problems and slack > 40:
        print("WARN  block sits %dpx short of the right edge at this window size."
              % slack)
        print("      A fixed left padding right-aligns at ONE resolution. This theme is")
        print("      tuned for the client's own %dx%d; on a wider window the menu drifts"
              % window_size())
        print("      left rather than breaking, which is the safe direction.")
        print()
    if problems:
        for p in problems:
            print("FAIL  " + p)
        return 1
    print("OK    the command block fits its band and the window")
    return 0


if __name__ == "__main__":
    sys.exit(main())
