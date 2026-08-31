"""Invariants for the FireRed theme mod.

Every one of these encodes a failure that is SILENT in the client: the theme
loads, renders a half-built skin, and says nothing useful in the log. That is
the whole reason they are tests and not eyeballs.

    python3 tools/test_firered_theme.py

Needs the installed client to check absolute includes and stock atlas sizes.
No device, no login, no running client.
"""
import os
import re
import struct
import sys
import unittest
import xml.etree.ElementTree as ET

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOD = os.path.join(REPO, "mods", "vanbobby-firered-theme")
CLIENT = os.environ.get("POKEMMO_HOME") or os.path.expanduser(
    "~/Library/Application Support/com.pokeemu.macos/pokemmo-client-live")
THEMES = os.path.join(CLIENT, "data", "themes")

THEME_ROOTS = ["theme", "theme-mobile"]
# Faces drawn on the theme's two NAVY surfaces: the battle message box and the
# NPC dialogue popup. They must stay LIGHT. Mirrors NAVY_TEXT/KEEP_LIGHT in
# tools/build_firered_fonts.py.
NAVY_FACES = {"battle", "battle-small", "messagebox", "main-battle"}

# Faces drawn over the game world; they keep an outline. Mirrors WORLD_FACES in
# tools/build_firered_fonts.py.
WORLD_FACES = {"pb-dark", "mechabold", "main-border", "main-small",
               "mechabold-large", "listbox-display"}
# An <images> block redefined after these has no effect: TWL binds an <image>
# reference when the widget theme naming it is parsed, so the widget is already
# holding the stock image object. Proven on the P0 spike -- the same override
# did nothing after main-widgets.xml and worked before init.xml.
CONSUMERS = ("init.xml", "main-widgets.xml")


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def strip_comments(text):
    """XML comments are prose. They contain example markup, so any regex that
    scans for tags has to drop them first or it lints the documentation."""
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def png_size(path):
    with open(path, "rb") as fh:
        head = fh.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG: %s" % path)
    return struct.unpack(">II", head[16:24])


def mod_xml_files():
    for root, _, files in os.walk(MOD):
        for f in sorted(files):
            if f.endswith(".xml"):
                yield os.path.join(root, f)


def includes(theme_xml):
    """(order, filename) for every <include> in a theme.xml, in document order."""
    text = strip_comments(read(theme_xml))
    return [(i, m.group(1)) for i, m in
            enumerate(re.finditer(r'<include\s+filename="([^"]+)"\s*/>', text))]


def stock_area_names(atlas_rel):
    """Every <area>/<grid> name the stock theme declares for one atlas."""
    names = set()
    for xml in ("gfx.xml", "gfx_ui.xml"):
        p = os.path.join(THEMES, "default", xml)
        if not os.path.exists(p):
            continue
        text = strip_comments(read(p))
        for blk in re.finditer(
                r'<images\s+file="([^"]+)"[^>]*>(.*?)</images>', text, re.S):
            if os.path.basename(blk.group(1)) != os.path.basename(atlas_rel):
                continue
            names |= set(re.findall(r'name="([^"]+)"', blk.group(2)))
    return names


class XmlHygiene(unittest.TestCase):
    def test_every_xml_file_is_well_formed(self):
        for p in mod_xml_files():
            with self.subTest(file=os.path.relpath(p, MOD)):
                ET.parse(p)

    def test_no_double_hyphen_inside_an_xml_comment(self):
        # "--" is illegal inside an XML comment and makes the whole file
        # unparseable. This repo has already shipped one unloadable mod
        # that way (05c934e). Once is enough.
        for p in mod_xml_files():
            text = read(p)
            for c in re.findall(r"<!--(.*?)-->", text, re.S):
                with self.subTest(file=os.path.relpath(p, MOD)):
                    self.assertNotIn("--", c, "double hyphen inside XML comment")

    def test_no_ds_store_in_the_source_tree(self):
        junk = [os.path.join(r, f)
                for r, _, fs in os.walk(MOD) for f in fs if f == ".DS_Store"]
        self.assertEqual([], junk)


class Includes(unittest.TestCase):
    def test_every_absolute_include_exists_in_the_client(self):
        for root in THEME_ROOTS:
            for _, f in includes(os.path.join(MOD, root, "theme.xml")):
                if not f.startswith("/data/themes/"):
                    continue
                target = os.path.join(THEMES, f[len("/data/themes/"):])
                with self.subTest(theme=root, include=f):
                    self.assertTrue(os.path.exists(target), "missing in client")

    def test_every_relative_include_resolves_inside_the_archive(self):
        # The classic mobile-theme trap is "../default/...", which escapes the
        # archive entirely. Every one of those fails and the client says nothing.
        for root in THEME_ROOTS:
            base = os.path.join(MOD, root)
            for _, f in includes(os.path.join(base, "theme.xml")):
                if f.startswith("/data/themes/"):
                    continue
                target = os.path.normpath(os.path.join(base, f))
                with self.subTest(theme=root, include=f):
                    self.assertTrue(
                        target.startswith(MOD + os.sep), "escapes the archive")
                    self.assertTrue(os.path.exists(target), "no such file in mod")

    def test_art_overrides_are_included_before_anything_consumes_them(self):
        # ART must precede init.xml/main-widgets.xml: TWL binds an <image> when
        # the widget theme naming it is parsed, so an atlas redeclared later is
        # a no-op.
        #
        # WIDGET overrides are the exact opposite. Widget themes are last wins,
        # so a <theme> override has to come AFTER the stock ones or it is the
        # override that gets ignored. The two rules pull in opposite directions,
        # which is why each of our includes is classified by what it contains
        # rather than by being ours.
        for root in THEME_ROOTS:
            base = os.path.join(MOD, root)
            inc = includes(os.path.join(base, "theme.xml"))
            consumers = [i for i, f in inc if f.endswith(CONSUMERS)]
            self.assertTrue(consumers, "%s: no consumer include found" % root)

            art, widgets = [], []
            for i, f in inc:
                if f.startswith("/data/themes/"):
                    continue
                target = os.path.normpath(os.path.join(base, f))
                if not os.path.exists(target):
                    continue
                body = strip_comments(read(target))
                if "<images" in body:
                    art.append((i, f))
                elif "<theme " in body or "<theme>" in body:
                    widgets.append((i, f))

            self.assertTrue(art, "%s: no art override included" % root)
            with self.subTest(theme=root, kind="art"):
                self.assertLess(max(i for i, _ in art), min(consumers),
                                "art override lands after init/main-widgets "
                                "and is a no-op")
            for i, f in widgets:
                with self.subTest(theme=root, widget_override=f):
                    self.assertGreater(i, max(consumers),
                                       "widget override lands before the stock "
                                       "widget themes and is overwritten")

    def test_fonts_are_included_before_fontgen(self):
        # A font declared after <fontGen/> is silently ignored.
        for root in THEME_ROOTS:
            text = strip_comments(read(os.path.join(MOD, root, "theme.xml")))
            gen = text.index("<fontGen/>")
            for m in re.finditer(r'<include\s+filename="([^"]*fonts[^"]*)"\s*/>', text):
                with self.subTest(theme=root, font_include=m.group(1)):
                    self.assertLess(m.start(), gen, "font include after <fontGen/>")


class Fonts(unittest.TestCase):
    """Font overrides. Every failure here is silent: a font that never appears
    looks exactly like a font you forgot to apply."""

    def our_fontdefs(self):
        for p in mod_xml_files():
            text = strip_comments(read(p))
            for m in re.finditer(r"<fontDef\b[^>]*>", text):
                tag = m.group(0)
                name = re.search(r'name="([^"]+)"', tag)
                if name:
                    yield p, name.group(1), tag

    def stock_fontdef_names(self):
        p = os.path.join(THEMES, "default", "fonts.xml")
        return set(re.findall(r'<fontDef\s+name="([^"]+)"', strip_comments(read(p))))

    def test_every_font_we_redefine_exists_in_the_stock_theme(self):
        # A typo'd name does not override anything. It declares a brand new font
        # that no widget asks for, while every widget keeps the stock face.
        stock = self.stock_fontdef_names()
        if not stock:
            self.skipTest("could not read stock fonts.xml")
        for xml, name, _ in self.our_fontdefs():
            with self.subTest(font=name):
                self.assertIn(name, stock, "not a font the stock theme declares")

    def test_every_font_file_we_reference_resolves(self):
        # The stock fonts.xml writes "res/fonts/x.ttf" and gets away with it
        # because it lives in default/. Ours does not live there, so the same
        # relative string would point at nothing and the face would never load.
        for xml, name, tag in self.our_fontdefs():
            m = re.search(r'filename="([^"]+)"', tag)
            if not m:
                continue          # ref= clone, inherits the file
            f = m.group(1)
            target = (os.path.join(THEMES, f[len("/data/themes/"):])
                      if f.startswith("/data/themes/")
                      else os.path.normpath(os.path.join(os.path.dirname(xml), f)))
            with self.subTest(font=name, filename=f):
                self.assertTrue(os.path.exists(target), "font file does not resolve")

    def test_shadowed_faces_use_a_hard_opaque_shadow_and_no_border(self):
        # FireRed's text treatment is a 1px HARD drop shadow at (+1,+1): fully
        # opaque, one flat colour, right and below only. Two ways to lose it
        # without any error appearing:
        #   a shadow_color with alpha < FF renders as a soft blur, which is what
        #   the client defaults to (#BF000000) and what stock title-font ships
        #   (#55000000);
        #   a leftover border_width draws a full surround instead, which is what
        #   stock main-border and mechabold do.
        for xml, name, tag in self.our_fontdefs():
            if 'filename="' not in tag:
                continue                      # ref= clone, shares the base atlas
            with self.subTest(font=name):
                if name in WORLD_FACES:
                    # outline instead of shadow: never both, or every glyph
                    # gets two rings and the text reads as fringing
                    self.assertNotIn("shadow_offset_x", tag,
                                     "outlined face must not also carry a shadow")
                    # These are drawn straight onto the game world, where the
                    # ground is not ours to control. An outline is the only
                    # thing that reads on both the dark overworld and a cream
                    # panel, which is why stock ships main-border.
                    self.assertIn("border_width", tag,
                                  "world face must keep an outline")
                else:
                    self.assertNotIn("border_width", tag,
                                     "surround outline; FireRed uses a drop shadow")
                if name in WORLD_FACES:
                    continue
                for axis in ("x", "y"):
                    m = re.search(r'shadow_offset_%s="([^"]+)"' % axis, tag)
                    self.assertIsNotNone(m, "no shadow_offset_%s" % axis)
                    self.assertEqual("1", m.group(1), "shadow must be offset by 1px")
                col = re.search(r'shadow_color="#([0-9A-Fa-f]{8})"', tag)
                self.assertIsNotNone(col, "shadow_color must be 8 hex digits (ARGB)")
                self.assertEqual("FF", col.group(1)[:2].upper(),
                                 "shadow alpha must be FF; anything less is a blur")

    def test_faces_on_the_navy_surfaces_stay_light(self):
        # The battle message box and the NPC popup are deliberately dark, so
        # their text has to be light. This is easy to break from a distance: a
        # refactor of the colour branches silently darkened "battle" to #404040
        # once, which puts dark text on a navy box and reads as nothing at all.
        for xml, name, tag in self.our_fontdefs():
            if name not in NAVY_FACES:
                continue
            m = re.search(r'color="#?([0-9A-Fa-f]{6})"', tag)
            if not m:
                continue          # a ref= clone inherits its base
            v = m.group(1)
            r, g, b = int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)
            lum = (r * 299 + g * 587 + b * 114) // 1000
            with self.subTest(font=name, color="#" + v):
                self.assertGreater(lum, 140,
                                   "face on a navy surface must stay light")

    def test_theme_includes_exactly_one_font_entry_point_before_fontgen(self):
        for root in THEME_ROOTS:
            text = strip_comments(read(os.path.join(MOD, root, "theme.xml")))
            gen = text.index("<fontGen/>")
            fonts = [(m.start(), m.group(1)) for m in
                     re.finditer(r'<include filename="([^"]*fonts[^"]*\.xml)"/>', text)]
            with self.subTest(theme=root):
                self.assertEqual(1, len(fonts), "expected one fonts include, got %r" % (fonts,))
                self.assertLess(fonts[0][0], gen, "fonts include lands after <fontGen/>")
                self.assertNotIn("/data/themes/", fonts[0][1],
                                 "theme includes the stock fonts directly; it must include "
                                 "ours, which layers over the stock set")

    def test_each_font_entry_point_layers_over_the_right_stock_set(self):
        # Mobile must layer over android/fonts.xml, not default/fonts.xml. The
        # android set adds battle-small, level, mechabold-large and the symbol
        # faces, and the android UI files reference them by name. Layering over
        # default silently drops all of them.
        want = {"theme": "default", "theme-mobile": "android"}
        for root in THEME_ROOTS:
            theme_txt = strip_comments(read(os.path.join(MOD, root, "theme.xml")))
            entry = re.search(r'<include filename="([^"]*fonts[^"]*\.xml)"/>', theme_txt).group(1)
            entry_path = os.path.normpath(os.path.join(MOD, root, entry))
            text = strip_comments(read(entry_path))
            incs = re.findall(r'<include filename="([^"]+)"/>', text)
            with self.subTest(theme=root):
                self.assertEqual(["/data/themes/%s/fonts.xml" % want[root], "fonts-common.xml"],
                                 incs, "wrong base set or wrong order")

class LoginPlate(unittest.TestCase):
    """The animated login plate. Only bg.png: every area there IS a frame, which
    is not true of the other atlases, so the strict rule applies only here."""

    def test_the_animation_is_wired_up(self):
        # Two silent failures. The bound name "background-image" disappears and
        # the widget quietly falls back to stock art; or a frame area is declared
        # that nothing plays, so part of the loop never shows.
        import xml.etree.ElementTree as ETree
        for xml in mod_xml_files():
            for images in ETree.parse(xml).getroot().iter("images"):
                if os.path.basename(images.get("file") or "") != "bg.png":
                    continue
                anims = list(images.iter("animation"))
                if not anims:
                    continue            # a still plate is a valid choice
                names = {a.get("name") for a in anims}
                refs = {f.get("ref") for a in anims for f in a.iter("frame")}
                refs.discard("none")    # stock idiom for a blank frame
                declared = {a.get("name") for a in images.iter("area") if a.get("name")}
                with self.subTest(atlas="bg.png"):
                    self.assertIn("background-image", names,
                                  "the name the login widget binds to is gone")
                    self.assertEqual(refs, declared,
                                     "frame areas and animation refs disagree")
                    for a in anims:
                        self.assertEqual("enabled", a.get("timeSource"),
                                         "a looping animation needs timeSource=enabled")


class InfoXml(unittest.TestCase):
    def setUp(self):
        self.root = ET.parse(os.path.join(MOD, "info.xml")).getroot()
        self.themes = self.root.find("themes")

    def test_theme_revision_matches_the_client(self):
        log = os.path.join(CLIENT, "log", "mods.log")
        if not os.path.exists(log):
            self.skipTest("no client log to read the revision from")
        with open(log, encoding="utf-8", errors="replace") as fh:
            found = re.findall(r"Client Theme Revision:\s*(\d+)", fh.read())
        if not found:
            self.skipTest("client log has no theme revision line")
        self.assertEqual(found[-1], self.themes.get("theme_revision"))

    def test_ships_one_desktop_theme_and_one_mobile_theme(self):
        # A desktop client refuses is_mobile="true" outright, so a mod that
        # wants to cover both has to declare both.
        flags = sorted(t.get("is_mobile") for t in self.themes.findall("theme"))
        self.assertEqual(["false", "true"], flags)

    def test_theme_names_are_unique_and_not_reserved(self):
        names = [t.get("name") for t in self.themes.findall("theme")]
        self.assertEqual(len(names), len(set(names)), "duplicate theme name")
        for n in names:
            self.assertNotIn(n.lower(), ("default", "android"), "reserved name")

    def test_every_declared_theme_path_has_a_theme_xml(self):
        for t in self.themes.findall("theme"):
            p = os.path.join(MOD, t.get("path"), "theme.xml")
            with self.subTest(theme=t.get("name")):
                self.assertTrue(os.path.exists(p), "no theme.xml at %s" % t.get("path"))


class Art(unittest.TestCase):
    """Our <images> blocks against the stock ones they replace."""

    def override_blocks(self):
        for p in mod_xml_files():
            if os.path.basename(p) == "theme.xml":
                continue
            text = strip_comments(read(p))
            for m in re.finditer(
                    r'<images\s+file="([^"]+)"[^>]*>(.*?)</images>', text, re.S):
                yield p, m.group(1), m.group(2)

    def test_every_referenced_atlas_exists_in_the_mod(self):
        for xml, ref, _ in self.override_blocks():
            target = os.path.normpath(os.path.join(os.path.dirname(xml), ref))
            with self.subTest(xml=os.path.relpath(xml, MOD), file=ref):
                self.assertTrue(os.path.exists(target), "referenced art is missing")

    def test_generated_tables_own_their_geometry_and_do_not_collide(self):
        # Once a mod ships its own slice table, stock dimensions stop being the
        # invariant. These two are: every rect inside the PNG, and no two rects
        # partially overlapping. The stock atlas fails the second in 129 places,
        # which is why the builder repacks rather than repainting in place.
        import xml.etree.ElementTree as ETree
        for xml in mod_xml_files():
            root = ETree.parse(xml).getroot()
            for images in root.iter("images"):
                ref = images.get("file")
                png = os.path.normpath(os.path.join(os.path.dirname(xml), ref))
                if not os.path.exists(png):
                    continue
                pw, ph = png_size(png)
                rects = sorted({tuple(int(v) for v in el.get("xywh").split(","))
                                for el in images.iter() if el.get("xywh")
                                and el.get("xywh").strip() != "*"})
                for r in rects:
                    with self.subTest(atlas=os.path.basename(ref), rect=r):
                        self.assertLessEqual(r[0] + r[2], pw, "rect runs off the right")
                        self.assertLessEqual(r[1] + r[3], ph, "rect runs off the bottom")
                for i, a in enumerate(rects):
                    for b in rects[i + 1:]:
                        if (a[0] < b[0] + b[2] and b[0] < a[0] + a[2]
                                and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]):
                            self.fail("%s: %s partially overlaps %s"
                                      % (os.path.basename(ref), a, b))

    def test_no_emitted_slice_has_a_negative_extent(self):
        # Stock uses a negative extent as "mirror this slice". Ours are painted
        # per slice, so a mirrored duplicate buys nothing -- and a negative width
        # fed to a packer walks the cursor backwards, which silently piles later
        # slices on top of earlier ones.
        import xml.etree.ElementTree as ETree
        for xml in mod_xml_files():
            for el in ETree.parse(xml).getroot().iter():
                v = el.get("xywh")
                if not v or v.strip() == "*":
                    continue
                x, y, w, h = (int(n) for n in v.split(","))
                with self.subTest(name=el.get("name"), xywh=v):
                    self.assertGreater(w, 0, "negative or zero width")
                    self.assertGreater(h, 0, "negative or zero height")

    def test_nine_slice_splits_fit_inside_their_rect(self):
        # splitx/splity say where a 9-slice stops stretching. A split wider than
        # half the rect makes the middle band negative and the art smears.
        import xml.etree.ElementTree as ETree
        for xml in mod_xml_files():
            for el in ETree.parse(xml).getroot().iter("area"):
                if not el.get("xywh") or el.get("xywh").strip() == "*":
                    continue
                x, y, w, h = (int(v) for v in el.get("xywh").split(","))
                for attr, extent in (("splitx", w), ("splity", h)):
                    spec = el.get(attr)
                    if not spec:
                        continue
                    edges = sum(int(re.sub(r"[^0-9]", "", part) or 0)
                                for part in spec.split(","))
                    with self.subTest(name=el.get("name"), attr=attr):
                        # A zero middle is a legal idiom: "L0,R9" on a 9px rect
                        # means do not stretch, pin to the right. A NEGATIVE
                        # middle is the bug -- the caps overrun the rect and the
                        # art smears. Stock ships one, button-npc-dark.selected,
                        # 8x9 with splitx="L20,R7"; the builder clamps it.
                        self.assertLessEqual(edges, extent,
                                             "%s=%s overruns %d px" % (attr, spec, extent))

    def test_generated_slice_names_match_stock_exactly(self):
        # Both directions. A missing name means a widget silently keeps stock
        # art; an extra one means art nothing reads.
        import xml.etree.ElementTree as ETree
        gen = os.path.join(MOD, "firered", "gfx_ui-firered.xml")
        if not os.path.exists(gen):
            self.skipTest("atlas not generated")
        ours = {el.get("name") for el in ETree.parse(gen).getroot().iter()
                if el.get("name")}
        stock_root = ETree.parse(os.path.join(THEMES, "default", "gfx_ui.xml")).getroot()
        block = [i for i in stock_root.iter("images")
                 if i.get("file") == "res/pokemmo_ui.png"][0]
        stock = {el.get("name") for el in block.iter() if el.get("name")}
        self.assertEqual(set(), stock - ours, "names dropped from the stock table")
        self.assertEqual(set(), ours - stock, "names invented that stock does not define")

    def test_whole_image_blocks_declare_no_rectangles(self):
        # xywh="*" and an explicit rectangle in the same block means one of them
        # is a mistake, and the freedom to resize depends on telling them apart.
        for xml, ref, body in self.override_blocks():
            rects = [r.strip() for r in re.findall(r'xywh="([^"]+)"', body)]
            with self.subTest(atlas=os.path.basename(ref)):
                if "*" in rects:
                    self.assertEqual(["*"] * len(rects), rects,
                                     "mixes whole-image and sliced areas")

    def test_every_slice_name_we_declare_exists_in_the_stock_block(self):
        # A typo'd name does not error. It defines a slice nothing reads,
        # while the real widget keeps the stock art. Worst failure mode in TWL.
        for xml, ref, body in self.override_blocks():
            stock = stock_area_names(ref)
            if not stock:
                continue
            # A name we invent is fine IF nothing outside this file binds to it.
            # The animated login plate declares bg-frame-NN areas purely so an
            # <animation> can reference them; the name widgets bind to is still
            # the stock "background-image".
            internal = set(re.findall(r'ref="([^"]+)"', body))
            for name in re.findall(r'name="([^"]+)"', body):
                if name in internal:
                    continue
                with self.subTest(atlas=os.path.basename(ref), slice=name):
                    self.assertIn(name, stock, "not a slice the stock theme defines")


if __name__ == "__main__":
    if not os.path.isdir(CLIENT):
        sys.exit("client not found at %s (set POKEMMO_HOME)" % CLIENT)
    unittest.main(verbosity=2)
