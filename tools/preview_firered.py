#!/usr/bin/env python3
"""Render the theme's own art without launching the client.

    tools/preview_firered.py --sheet                  every atlas, one PNG each
    tools/preview_firered.py --slice ui-frame.background@400x260
    tools/preview_firered.py --slice trainer-card.background --scale 2
    tools/preview_firered.py --list gfx_ui            what is in an atlas

WHAT THIS CAN AND CANNOT SHOW is the whole point, so it is stated up front.

CAN: everything the atlas builder decides. Band stacks, painter output, the
9-slice caps we emit, grid cell edges, tints, and how any of it behaves when a
widget stretches it. That is what a screenshot round was being spent on.

CANNOT: layout. Borders, gaps, min/max, alignment and tabPosition are resolved
by TWL against the client's own widget tree, and nothing here models that. A
layout change still needs the game.

So: art iterates here, layout iterates in the client. Roughly half of what this
theme does is art.
"""
import argparse
import os
import re
import sys
import xml.etree.ElementTree as ET

from PIL import Image

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIRERED = os.path.join(REPO, "mods", "vanbobby-firered-theme", "firered")
OUT = os.path.join(REPO, "previews")


def load():
    """name -> (element, source Image). Later files win, as in the theme."""
    table, images = {}, {}
    for f in sorted(os.listdir(FIRERED)):
        if not f.endswith("-firered.xml") or f == "atlases-firered.xml":
            continue
        root = ET.parse(os.path.join(FIRERED, f)).getroot()
        for block in root.iter("images"):
            path = os.path.join(FIRERED, block.get("file"))
            if not os.path.exists(path):
                continue
            if path not in images:
                images[path] = Image.open(path).convert("RGBA")
            for el in block:
                if el.get("name"):
                    table[el.get("name")] = (el, images[path], block)
    return table


def caps(spec, extent):
    """"L7,R7" -> (7, extent-14, 7). No spec means one stretched middle."""
    if not spec:
        return 0, extent, 0
    v = [int(re.sub(r"[^0-9]", "", p) or 0) for p in spec.split(",")]
    a, b = (v + [0, 0])[:2]
    return a, max(0, extent - a - b), b


def draw_area(el, src, w, h):
    """One <area> rendered at w x h, honouring splitx/splity and tiled."""
    x, y, aw, ah = (abs(int(v)) for v in el.get("xywh").split(","))
    tiled = el.get("tiled") == "true" or el.get("repeatX") == "true"
    cx = caps(el.get("splitx"), aw)
    cy = caps(el.get("splity"), ah)
    tw = [cx[0], max(0, w - cx[0] - cx[2]), cx[2]]
    th = [cy[0], max(0, h - cy[0] - cy[2]), cy[2]]
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sy, oy = y, 0
    for r in range(3):
        sx, ox = x, 0
        for c in range(3):
            if cx[c] > 0 and cy[r] > 0 and tw[c] > 0 and th[r] > 0:
                cell = src.crop((sx, sy, sx + cx[c], sy + cy[r]))
                if tiled and (c == 1 or r == 1):
                    tile = Image.new("RGBA", (tw[c], th[r]))
                    for ty in range(0, th[r], cy[r]):
                        for tx in range(0, tw[c], cx[c]):
                            tile.paste(cell, (tx, ty))
                    cell = tile
                else:
                    cell = cell.resize((tw[c], th[r]), Image.NEAREST)
                out.alpha_composite(cell, (ox, oy))
            ox += tw[c]
            sx += cx[c]
        oy += th[r]
        sy += cy[r]
    return tint_of(el, out)


def draw_grid(el, src, block, w, h):
    """A <grid>: fixed rows/cols keep their size, weighted ones take the slack."""
    named = {a.get("name"): a for a in block.iter("area") if a.get("name")}
    cells = [c for c in el if c.tag in ("area", "alias")]
    wx = [int(v) for v in el.get("weightsX", "0,1,0").split(",")]
    wy = [int(v) for v in el.get("weightsY", "0,1,0").split(",")]
    cols, rows = len(wx), len(wy)
    if len(cells) < cols * rows:
        return Image.new("RGBA", (w, h), (0, 0, 0, 0))

    def rect(c):
        # A cell may alias a name that is not a plain <area> in this block --
        # ui-checkbox.checked aliases an <animation>. Nothing to crop, so the
        # cell draws empty; its row and column still take their size from a
        # sibling, so the rest of the grid stays put.
        e = c if c.tag == "area" else named.get(c.get("ref"))
        if e is None or not e.get("xywh"):
            return None
        return [abs(int(v)) for v in e.get("xywh").split(",")], e

    base = [rect(c) for c in cells]

    def span(idxs, axis):
        for i in idxs:
            if base[i]:
                return base[i][0][2 + axis]
        return 0

    cw = [span(range(c, len(base), cols), 0) for c in range(cols)]
    ch = [span(range(r * cols, (r + 1) * cols), 1) for r in range(rows)]
    for sizes, weights, target in ((cw, wx, w), (ch, wy, h)):
        slack, total = target - sum(sizes), sum(weights) or 1
        for i, wt in enumerate(weights):
            if wt:
                sizes[i] += slack * wt // total
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    oy = 0
    for r in range(rows):
        ox = 0
        for c in range(cols):
            cell = base[r * cols + c]
            if cell and cw[c] > 0 and ch[r] > 0:
                (ax, ay, aw, ah), e = cell
                out.alpha_composite(
                    src.crop((ax, ay, ax + aw, ay + ah))
                       .resize((cw[c], ch[r]), Image.NEAREST), (ox, oy))
            ox += cw[c]
        oy += ch[r]
    return out


def tint_of(el, img):
    v = (el.get("tint") or "").lstrip("#")
    if len(v) not in (6, 8):
        return img
    a = int(v[:2], 16) if len(v) == 8 else 255
    r, g, b = (int(v[-6:][i:i + 2], 16) for i in (0, 2, 4))
    px = img.load()
    for yy in range(img.height):
        for xx in range(img.width):
            pr, pg, pb, pa = px[xx, yy]
            px[xx, yy] = (pr * r // 255, pg * g // 255, pb * b // 255, pa * a // 255)
    return img


def render(table, name, w=None, h=None):
    """Resolve a name through select/alias/animation and draw it."""
    seen = set()
    while name in table and name not in seen:
        seen.add(name)
        el, src, block = table[name]
        if el.tag in ("select", "animation"):
            kids = [k for k in el if k.tag in ("alias", "frame")]
            pick = next((k for k in kids if not k.get("if")), kids[0] if kids else None)
            if pick is None or not pick.get("ref"):
                return None
            name = pick.get("ref")
            continue
        if el.tag == "alias":
            name = el.get("ref")
            continue
        if el.tag == "grid":
            return draw_grid(el, src, block, w or 240, h or 160)
        if el.get("xywh"):
            aw, ah = (abs(int(v)) for v in el.get("xywh").split(",")[2:])
            return draw_area(el, src, w or aw, h or ah)
        return None
    return None


def checker(w, h, s=8):
    img = Image.new("RGBA", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            px[x, y] = (90, 90, 90, 255) if (x // s + y // s) % 2 else (70, 70, 70, 255)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slice", action="append", default=[],
                    help="NAME or NAME@WxH; repeatable")
    ap.add_argument("--sheet", action="store_true", help="one contact sheet per atlas")
    ap.add_argument("--list", metavar="ATLAS", help="print the names in an atlas")
    ap.add_argument("--scale", type=int, default=2)
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()
    table = load()

    if args.list:
        for n, (el, _, block) in sorted(table.items()):
            if args.list in block.get("file"):
                print("%-42s %s" % (n, el.tag))
        return

    os.makedirs(args.out, exist_ok=True)
    wrote = []

    for spec in args.slice:
        name, _, size = spec.partition("@")
        w = h = None
        if size:
            w, h = (int(v) for v in size.lower().split("x"))
        img = render(table, name, w, h)
        if img is None:
            sys.exit("no drawable slice named %r" % name)
        bg = checker(img.width, img.height)
        bg.alpha_composite(img)
        bg = bg.resize((bg.width * args.scale, bg.height * args.scale), Image.NEAREST)
        p = os.path.join(args.out, re.sub(r"[^\w.-]", "_", name) + ".png")
        bg.save(p)
        wrote.append((p, "%dx%d" % (img.width, img.height)))

    if args.sheet:
        by_atlas = {}
        for n, (el, src, block) in table.items():
            if el.tag == "area" and not el.get("xywh"):
                continue
            by_atlas.setdefault(block.get("file"), []).append(n)
        for atlas, names in sorted(by_atlas.items()):
            tiles = []
            for n in sorted(names):
                img = render(table, n, 150, 44)
                if img:
                    tiles.append((n, img))
            if not tiles:
                continue
            cols = 4
            cw, chh = 150, 44
            pad, lab = 10, 14
            rows = (len(tiles) + cols - 1) // cols
            sheet = Image.new("RGBA", (cols * (cw + pad) + pad,
                                       rows * (chh + lab + pad) + pad), (48, 48, 48, 255))
            from PIL import ImageDraw
            d = ImageDraw.Draw(sheet)
            for i, (n, img) in enumerate(tiles):
                x = pad + (i % cols) * (cw + pad)
                y = pad + (i // cols) * (chh + lab + pad)
                sheet.alpha_composite(checker(cw, chh), (x, y))
                sheet.alpha_composite(img, (x, y))
                d.text((x, y + chh + 2), n[:30], fill=(210, 210, 210, 255))
            p = os.path.join(args.out, "sheet-%s.png"
                             % os.path.basename(atlas).replace(".png", ""))
            sheet.save(p)
            wrote.append((p, "%d slices" % len(tiles)))

    for p, note in wrote:
        print("%-60s %s" % (os.path.relpath(p, REPO), note))
    if not wrote:
        print("nothing asked for; try --sheet or --slice NAME")


if __name__ == "__main__":
    main()
