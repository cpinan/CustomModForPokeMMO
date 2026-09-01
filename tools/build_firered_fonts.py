"""Generate the FireRed font overrides from the stock font set.

    python3 tools/build_firered_fonts.py

Writes mods/vanbobby-firered-theme/firered/fonts-common.xml, which
fonts-desktop.xml and fonts-mobile.xml layer over the stock set.

WHY GENERATED
The stock theme declares about 65 fonts and 51 of them are LIGHT, because the
stock UI is dark. Once the panels are cream, every one of those is low contrast
or invisible: the Settings tab labels vanish outright. Hand-listing the ones you
happen to notice is how you end up fixing seven and shipping forty-four broken,
so the whole set is remapped by rule.

THE RULE
  * A light colour is darkened to about a third brightness, keeping its hue and
    saturation, so main-red stays red and main-green stays green while both
    become readable on cream.
  * Greys and whites, having no hue to keep, go to FireRed's body-text #404040.
  * Colours that are already dark are left alone.
  * Every face gains FireRed's 1px hard drop shadow at (+1,+1), light #D8D8C0,
    which is the pairing FireRed uses on light panels.
  * border_width is dropped. FireRed outlines nothing; it shadows.

WHAT IS DELIBERATELY LEFT LIGHT
The battle faces. FireRed's battle message box is dark navy with white text, so
those keep the other pairing. They are listed in KEEP_LIGHT.
"""
import colorsys
import os
import re
import xml.etree.ElementTree as ET

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOD = os.path.join(REPO, "mods", "vanbobby-firered-theme")
CLIENT = os.environ.get("POKEMMO_HOME") or os.path.expanduser(
    "~/Library/Application Support/com.pokeemu.macos/pokemmo-client-live")
STOCK_FONTS = os.path.join(CLIENT, "data", "themes", "default", "fonts.xml")
OUT = os.path.join(MOD, "firered", "fonts-common.xml")

BODY = "#404040"            # FireRed body text on cream
SHADOW_LIGHT = "#FFD8D8C0"  # under DARK glyphs, on cream panels
SHADOW_DARK = "#FF283030"   # under LIGHT glyphs, on the navy battle box
FONT_DIR = "/data/themes/default/res/fonts/"

# Faces that sit on a DARK surface and must stay light. FireRed's battle box is
# navy with white text; that is the other half of the same grammar.
KEEP_LIGHT = {"battle", "battle-small", "braille", "marquee",
              "main-battle", "tooltip-font", "tooltip-font-markup"}

# Faces drawn on one of the theme's two NAVY surfaces: the battle message box
# (battle-area) and the NPC dialogue popup (text-bubble). Both are deliberately
# dark, because that is the FireRed window, so their text must be white.
#
# "battle" was already white and needed nothing. "messagebox" was NOT: stock's
# text-bubble is a LIGHT box, so its face is dark, and painting the box navy
# without touching the face left dark text on navy.
NAVY_TEXT = {"messagebox"}
NAVY_GLYPH = "#F8F8F8"

# Faces drawn straight onto the game world, with no panel behind them: the
# overworld HUD (route, money, clock) and the battle name and HP labels. They
# are the SAME faces the cream panels use, so no single colour serves both -- a
# dark glyph vanishes on the dark world, a light one vanishes on cream.
#
# An outline is the tool for text on an unknown ground, which is exactly why
# stock ships main-border. A dark glyph with a LIGHT surround reads on the world
# and disappears into cream, so both contexts work from one definition.
#
# A ref= clone shares its base's atlas and cannot carry its own border, so these
# are expanded to an explicit filename first.
WORLD_FACES = {"pb-dark", "mechabold", "main-border", "main-small",
               "mechabold-large", "listbox-display"}
WORLD_OUTLINE = "#F8F0E8"

# Faces whose colour FireRed itself sets, on a surface THIS theme paints and so
# controls the contrast of. Only the trainer card so far: its header is a
# #68A0D8 blue band and the game writes the name across it in gold. Stock's
# #434343 on that blue reads as a placeholder, and the ordinary "darken anything
# light" rule would undo the gold, so the exception has to be explicit.
#
# trainer-name is safe to redefine outright: main-widgets.xml uses the FACE in
# exactly one place, the card header. Its other trainer-name THEME, on the
# battle nameplate, points at the battle font instead.
CARD_FACES = {"trainer-name": "#F0D088"}

# Faces moved onto the client's OWN pixel font. battle.ttf ships with the
# client, is already what the battle face uses, and maps 42,893 glyphs, so
# accents and CJK all survive the swap. Nothing is downloaded and nothing new is
# licensed: this is the same font directory the theme already references by
# absolute path.
#
# Its pixel grid only lands on multiples of 8. At 12 to 20 it is mush and at 24
# it is thin on navy; 32 is the first size that reads, and it happens to set the
# same line width as the Noto 24 it replaces, so the dialogue box does not
# reflow. That size floor is why this is the dialogue face and not the whole UI:
# body text is 12pt and there is no version of 12pt that is crisp here.
PIXEL_FACES = {"messagebox": 32}
PIXEL_FONT = "battle.ttf"

NAMED = {"white": "#FFFFFF", "black": "#000000", "red": "#FF0000"}


def parse_colour(v):
    v = NAMED.get(v.strip().lower(), v.strip())
    if not v.startswith("#"):
        return None
    h = v[1:]
    if len(h) == 4:            # ARGB shorthand
        h = h[1:]
    if len(h) == 3:            # RGB shorthand: #999 is a real value in this file
        h = "".join(c * 2 for c in h)
    if len(h) == 8:            # ARGB
        h = h[2:]
    if len(h) != 6:
        return None
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def luminance(rgb):
    r, g, b = rgb
    return (r * 299 + g * 587 + b * 114) // 1000


def darken(rgb):
    """Keep the hue, drop the brightness until it reads on cream.

    Greys are INVERTED rather than flattened. On a dark UI, white is the primary
    text and a dimmer grey is the secondary; flattening every grey to one value
    destroys that ranking, which is what made the Settings tabs indistinguishable
    from their labels. Mapping brightest to darkest preserves the order: white
    becomes body #404040, and #999 becomes a lighter grey that still reads as
    subdued against cream."""
    r, g, b = (c / 255.0 for c in rgb)
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    if s < 0.12:
        lum = luminance(rgb)
        out = int(0x40 + (255 - lum) * 0.45)
        out = max(0x40, min(0x96, out))
        return "#%02X%02X%02X" % (out, out, out)
    v = 0.42
    s = min(1.0, s * 1.35)             # compensate: dark low-sat reads muddy
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return "#%02X%02X%02X" % (int(r * 255), int(g * 255), int(b * 255))


def main():
    src = re.sub(r"<!--.*?-->", "", open(STOCK_FONTS, encoding="utf-8").read(), flags=re.S)
    root = ET.fromstring(src)

    by_name = {fd.get("name"): fd for fd in root.findall("fontDef")}

    def resolve_filename(fd, seen=()):
        """Walk the ref chain until something names a file."""
        if fd.get("filename"):
            return fd.get("filename"), fd
        ref = fd.get("ref")
        if not ref or ref in seen or ref not in by_name:
            return None, fd
        return resolve_filename(by_name[ref], seen + (ref,))

    out, remapped, kept, outlined = [], 0, 0, 0
    for fd in root.findall("fontDef"):
        name = fd.get("name")
        el = ET.Element("fontDef")
        for k, v in fd.attrib.items():
            el.set(k, v)

        if name in WORLD_FACES and not el.get("filename"):
            # expand the clone so it can carry its own outline
            fn, base = resolve_filename(fd)
            if fn:
                el.set("filename", fn)
                del el.attrib["ref"]
                # default="true" and unique_atlas belong to the BASE face only.
                # Copying default onto a clone gives the theme two default fonts.
                for k, v in base.attrib.items():
                    if k in ("name", "ref", "color", "default", "unique_atlas"):
                        continue
                    if k not in el.attrib:
                        el.set(k, v)
                el.attrib.pop("default", None)
                el.attrib.pop("unique_atlas", None)

        if name in PIXEL_FACES and el.get("filename"):
            el.set("filename", FONT_DIR + PIXEL_FONT)
            el.set("size", str(PIXEL_FACES[name]))
            # battle.ttf is a plain TTF, not the CJK collection, so the face
            # selector that picks sc/tc/jp out of a .ttc has nothing to pick.
            el.attrib.pop("size_cjk", None)
            el.attrib.pop("faces", None)
        if el.get("filename"):
            el.set("filename", FONT_DIR + os.path.basename(el.get("filename")))

        colour = el.get("color")
        if name in CARD_FACES:
            el.set("color", CARD_FACES[name])
            kept += 1
        elif name in NAVY_TEXT:
            el.set("color", NAVY_GLYPH)
            kept += 1
        elif name in KEEP_LIGHT:
            kept += 1
        elif colour:
            rgb = parse_colour(colour)
            if rgb and luminance(rgb) > 140:
                el.set("color", darken(rgb))
                remapped += 1

        # FireRed shadows rather than outlines, except where a face has to
        # survive on a ground we do not control.
        if "border_width" in el.attrib:
            del el.attrib["border_width"]
        if "border_color" in el.attrib:
            del el.attrib["border_color"]
        outline_face = name in WORLD_FACES and el.get("filename")
        if outline_face:
            el.set("border_width", "1")
            el.set("border_color", WORLD_OUTLINE)
            outlined += 1
        # The shadow tone follows the GLYPH, not the face's name: FireRed pairs
        # a dark glyph with a light shadow and a light glyph with a dark one.
        # Either way it is hard, so the alpha is always FF. Stock ships soft
        # ones (#CC000000 on battle, #20FFFFFF on tooltips) that read as blur.
        # A face gets EITHER an outline OR a shadow, never both. Stacking them
        # puts two rings around every antialiased glyph and the text reads as
        # noisy fringing rather than as crisp pixel text. FireRed never stacks
        # them either.
        if outline_face:
            for k in ("shadow_offset_x", "shadow_offset_y", "shadow_color"):
                el.attrib.pop(k, None)
        elif not el.get("ref"):
            final = parse_colour(el.get("color") or "#FFFFFF")
            dark_glyph = final is not None and luminance(final) <= 140
            el.set("shadow_offset_x", "1")
            el.set("shadow_offset_y", "1")
            el.set("shadow_color", SHADOW_LIGHT if dark_glyph else SHADOW_DARK)

        for child in fd:
            c = ET.SubElement(el, child.tag)
            for k, v in child.attrib.items():
                if k == "color":
                    rgb = parse_colour(v)
                    if rgb and luminance(rgb) > 140 and name not in KEEP_LIGHT:
                        v = darken(rgb)
                c.set(k, v)
        out.append(el)

    body = "\n".join("    " + ET.tostring(e, encoding="unicode").strip() for e in out)
    text = '''<?xml version="1.0" encoding="UTF-8"?>
<!--
  Generated by tools/build_firered_fonts.py. Do not hand edit.

  The stock theme declares about 65 fonts and 51 of them are light, because the
  stock UI is dark. On FireRed's cream panels every one of those is low contrast
  or invisible. Each is remapped here: hue and saturation kept, brightness
  dropped, so main-red stays red while becoming readable; greys and whites, with
  no hue to keep, go to FireRed's body #404040.

  Every face gains the 1px hard drop shadow at (+1,+1) in light #D8D8C0, which
  is the pairing FireRed uses on light panels. border_width is dropped
  throughout: FireRed shadows, it does not outline.

  The battle faces stay light on purpose. FireRed's battle message box is dark
  navy with white text, which is the other half of the same grammar.

  filename is absolute. The stock file writes "res/fonts/..." and gets away with
  it by living in default/; from firered/ that resolves to nothing, and a
  missing font produces no error, just a face that never appears.
-->
<themes>
%s
</themes>
''' % body
    with open(OUT, "w") as fh:
        fh.write(text)
    print("wrote %s: %d fonts, %d darkened, %d outlined for the world, "
          "%d left light on purpose"
          % (os.path.relpath(OUT, REPO), len(out), remapped, outlined, kept))


if __name__ == "__main__":
    main()
