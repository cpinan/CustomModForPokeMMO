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

    out, remapped, kept = [], 0, 0
    for fd in root.findall("fontDef"):
        name = fd.get("name")
        el = ET.Element("fontDef")
        for k, v in fd.attrib.items():
            el.set(k, v)

        if el.get("filename"):
            el.set("filename", FONT_DIR + os.path.basename(el.get("filename")))

        colour = el.get("color")
        if name in KEEP_LIGHT:
            kept += 1
        elif colour:
            rgb = parse_colour(colour)
            if rgb and luminance(rgb) > 140:
                el.set("color", darken(rgb))
                remapped += 1

        # FireRed shadows, never outlines
        if "border_width" in el.attrib:
            del el.attrib["border_width"]
        if "border_color" in el.attrib:
            del el.attrib["border_color"]
        # The shadow tone follows the GLYPH, not the face's name: FireRed pairs
        # a dark glyph with a light shadow and a light glyph with a dark one.
        # Either way it is hard, so the alpha is always FF. Stock ships soft
        # ones (#CC000000 on battle, #20FFFFFF on tooltips) that read as blur.
        if not el.get("ref"):
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
    print("wrote %s: %d fonts, %d darkened, %d left light on purpose"
          % (os.path.relpath(OUT, REPO), len(out), remapped, kept))


if __name__ == "__main__":
    main()
