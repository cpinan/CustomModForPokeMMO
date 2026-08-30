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
        for root in THEME_ROOTS:
            inc = includes(os.path.join(MOD, root, "theme.xml"))
            ours = [i for i, f in inc if not f.startswith("/data/themes/")]
            consumers = [i for i, f in inc if f.endswith(CONSUMERS)]
            self.assertTrue(ours, "%s: no FireRed override included" % root)
            self.assertTrue(consumers, "%s: no consumer include found" % root)
            with self.subTest(theme=root):
                self.assertLess(max(ours), min(consumers),
                                "override lands after init/main-widgets and is a no-op")

    def test_fonts_are_included_before_fontgen(self):
        # A font declared after <fontGen/> is silently ignored.
        for root in THEME_ROOTS:
            text = strip_comments(read(os.path.join(MOD, root, "theme.xml")))
            gen = text.index("<fontGen/>")
            for m in re.finditer(r'<include\s+filename="([^"]*fonts[^"]*)"\s*/>', text):
                with self.subTest(theme=root, font_include=m.group(1)):
                    self.assertLess(m.start(), gen, "font include after <fontGen/>")


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

    def test_replacement_atlases_keep_the_stock_pixel_dimensions(self):
        # Every xywh in the stock block is measured against the stock size.
        # Ship a differently sized PNG and every slice silently shifts.
        for xml, ref, _ in self.override_blocks():
            stock = os.path.join(THEMES, "default", "res", os.path.basename(ref))
            if not os.path.exists(stock):
                continue
            ours = os.path.normpath(os.path.join(os.path.dirname(xml), ref))
            with self.subTest(atlas=os.path.basename(ref)):
                self.assertEqual(png_size(stock), png_size(ours),
                                 "dimensions differ from stock")

    def test_every_slice_name_we_declare_exists_in_the_stock_block(self):
        # A typo'd name does not error. It defines a slice nothing reads,
        # while the real widget keeps the stock art. Worst failure mode in TWL.
        for xml, ref, body in self.override_blocks():
            stock = stock_area_names(ref)
            if not stock:
                continue
            for name in re.findall(r'name="([^"]+)"', body):
                with self.subTest(atlas=os.path.basename(ref), slice=name):
                    self.assertIn(name, stock, "not a slice the stock theme defines")


if __name__ == "__main__":
    if not os.path.isdir(CLIENT):
        sys.exit("client not found at %s (set POKEMMO_HOME)" % CLIENT)
    unittest.main(verbosity=2)
