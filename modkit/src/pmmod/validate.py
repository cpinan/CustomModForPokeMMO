"""Lint a mod source tree or packed .mod against the client's own rules."""
from __future__ import annotations

import posixpath
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

from . import spec

JUNK = {".DS_Store", "Thumbs.db", "desktop.ini"}
# Files that are for humans, not the loader: never shipped, never flagged.
IGNORED = {".gitkeep", "README.md", "readme.md", "LICENSE", "LICENSE.md",
           "CHANGELOG.md", ".gitignore", "rules.json"}
JUNK_DIRS = {"__MACOSX", ".git", ".idea", "__pycache__"}


@dataclass
class Finding:
    level: str          # "error" | "warn" | "info"
    code: str
    where: str
    message: str
    hint: str = ""

    def __str__(self) -> str:
        tag = {"error": "ERROR", "warn": "warn ", "info": "info "}[self.level]
        line = f"{tag} [{self.code}] {self.where}: {self.message}"
        if self.hint:
            line += f"\n        -> {self.hint}"
        return line


@dataclass
class Source:
    """A mod being inspected, either a directory or a zip/.mod archive."""
    label: str
    files: dict[str, int]            # archive-relative posix path -> size
    read: object                     # callable(path) -> bytes

    @classmethod
    def open(cls, path: Path) -> "Source":
        path = Path(path).expanduser()
        if path.is_dir():
            files = {}
            for p in sorted(path.rglob("*")):
                if p.is_file():
                    files[p.relative_to(path).as_posix()] = p.stat().st_size
            return cls(str(path), files, lambda rel: (path / rel).read_bytes())
        if path.is_file():
            zf = zipfile.ZipFile(path)
            files = {i.filename: i.file_size for i in zf.infolist() if not i.is_dir()}
            return cls(str(path), files, lambda rel: zf.read(rel))
        raise SystemExit(f"No such mod source: {path}")

    def has(self, rel: str) -> bool:
        return rel in self.files

    def has_dir(self, rel: str) -> bool:
        rel = rel.rstrip("/") + "/"
        return any(f.startswith(rel) for f in self.files)


def validate(source: Source) -> list[Finding]:
    out: list[Finding] = []
    out += _check_layout(source)
    info = _check_info_xml(source, out)
    out += _check_content(source, _declared_prefixes(info))
    if info is not None:
        out += _check_sections(source, info)
    return out


def _declared_prefixes(info) -> tuple[str, ...]:
    """Paths info.xml claims for themes/extensions/strings/overlays.

    Files under these are the mod's business, not the loader's content tree,
    so the content checks must leave them alone.
    """
    if info is None:
        return ()
    out: list[str] = []
    for section, tag in (("themes", "theme"),
                         ("theme_extensions", "theme_extension"),
                         ("overlays", "overlay")):
        node = info.find(section)
        if node is None:
            continue
        for child in node.findall(tag):
            p = child.get("path")
            if p:
                out.append(p.rstrip("/") + "/")
    node = info.find("strings")
    if node is not None:
        for child in node.findall("string"):
            p = child.get("path")
            if p:
                out.append(p)
    return tuple(out)


# --- layout ----------------------------------------------------------------
def _check_layout(s: Source) -> list[Finding]:
    out = []
    if not s.has("info.xml"):
        nested = [f for f in s.files if f.endswith("/info.xml") and f.count("/") == 1]
        if nested:
            out.append(Finding(
                "error", "NESTED", nested[0],
                "info.xml is one folder deep, so the client will not see this mod",
                "Zip the *contents* of the mod folder, not the folder itself."))
        else:
            out.append(Finding(
                "error", "NOINFO", "info.xml",
                "missing info.xml at the archive root",
                "Every mod needs info.xml -- it is what Mod Management lists."))
    if not s.has("icon.png"):
        out.append(Finding("warn", "NOICON", "icon.png",
                           "no icon.png; the mod list will show a blank tile",
                           "48x48 PNG at the archive root."))
    for f in s.files:
        base = posixpath.basename(f)
        if base in IGNORED:
            continue
        parts = f.split("/")
        if base in JUNK or base.startswith("._"):
            out.append(Finding("warn", "JUNK", f, "editor/OS junk file, strip it before shipping"))
        if any(p in JUNK_DIRS for p in parts):
            out.append(Finding("warn", "JUNKDIR", f, "junk directory inside the archive"))
        if s.files[f] == 0:
            out.append(Finding("warn", "EMPTY", f, "zero-byte file"))
        ext = posixpath.splitext(base)[1]
        if ext and ext != ext.lower():
            out.append(Finding("warn", "CASE", f,
                               f"uppercase extension '{ext}'",
                               "The loader matches lowercase extensions."))
    return out


# --- info.xml --------------------------------------------------------------
def _check_info_xml(s: Source, out: list[Finding]):
    if not s.has("info.xml"):
        return None
    raw = s.read("info.xml")
    m = re.search(rb'<\?xml[^>]*\bversion="([^"]+)"', raw[:200])
    if m and m.group(1) != b"1.0":
        out.append(Finding(
            "warn", "XMLDECL", "info.xml",
            f'XML declaration says version="{m.group(1).decode()}", expected "1.0"',
            "A version bump edited the XML declaration instead of only "
            '<resource version="...">. The declaration always stays 1.0.'))
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        out.append(Finding("error", "XML", "info.xml", f"not valid XML: {e}"))
        return None
    if root.tag != "resource":
        out.append(Finding("error", "XMLROOT", "info.xml",
                           f"root element is <{root.tag}>, expected <resource>"))
    for attr in ("name", "version"):
        if not root.get(attr):
            out.append(Finding("error", "XMLATTR", "info.xml",
                               f"<resource> is missing the '{attr}' attribute"))
    link = root.get("weblink", "")
    if link and not link.startswith(spec.WEBLINK_PREFIX):
        out.append(Finding(
            "warn", "WEBLINK", "info.xml",
            f"weblink must start with {spec.WEBLINK_PREFIX} (got {link!r})",
            "The client rejects any other host: "
            "'weblink must start with https://forums.pokemmo.com'."))
    for child in root:
        if child.tag not in spec.INFO_XML_SECTIONS:
            out.append(Finding("warn", "XMLSECTION", "info.xml",
                               f"unknown section <{child.tag}>",
                               f"Known sections: {', '.join(spec.INFO_XML_SECTIONS)}"))
        if sum(1 for c in root if c.tag == child.tag) > 1:
            out.append(Finding("error", "XMLDUP", "info.xml",
                               f"<{child.tag}> appears more than once",
                               "The client allows exactly one of each section."))
    return root


def _check_sections(s: Source, root: ET.Element) -> list[Finding]:
    out: list[Finding] = []

    themes = root.find("themes")
    if themes is not None:
        if not themes.get("theme_revision"):
            out.append(Finding("error", "THEMEREV", "info.xml",
                               "<themes> has no theme_revision attribute",
                               f"Current client speaks revision "
                               f"{spec.DEFAULT_THEME_REVISION} "
                               "(check 'Client Theme Revision' in log/mods.log)."))
        for t in themes.findall("theme"):
            out += _check_theme_entry(s, t, "theme")
    exts = root.find("theme_extensions")
    if exts is not None:
        if not exts.get("theme_extension_revision"):
            out.append(Finding("error", "TEXTREV", "info.xml",
                               "<theme_extensions> has no theme_extension_revision attribute"))
        for t in exts.findall("theme_extension"):
            out += _check_theme_entry(s, t, "theme_extension")

    strings = root.find("strings")
    if strings is not None:
        if not strings.get("string_revision"):
            out.append(Finding("error", "STRREV", "info.xml",
                               "<strings> has no string_revision attribute",
                               "Run `pmmod probe-revisions` to make the client "
                               "log the revision it expects."))
        for st in strings.findall("string"):
            p = st.get("path")
            if not p:
                out.append(Finding("error", "STRPATH", "info.xml",
                                   "<string> has no path attribute"))
            elif not p.lower().endswith(".xml"):
                out.append(Finding("error", "STRXML", "info.xml",
                                   f"string path {p!r} does not point to an xml file"))
            elif not s.has(p):
                out.append(Finding("error", "STRMISS", "info.xml",
                                   f"string path {p!r} is not in the archive"))
            else:
                # The client parses every declared strings file at load time and
                # refuses the whole mod if one is malformed, so parse them here.
                try:
                    ET.fromstring(s.read(p))
                except ET.ParseError as e:
                    out.append(Finding(
                        "error", "STRPARSE", p,
                        f"not well-formed XML: {e}",
                        "The client rejects the entire mod when a declared "
                        "strings file fails to parse. Note that XML forbids "
                        "'--' inside comments."))

    overlays = root.find("overlays")
    declared = set()
    if overlays is not None:
        for o in overlays.findall("overlay"):
            p = o.get("path")
            if not p:
                out.append(Finding("error", "OVLPATH", "info.xml",
                                   "<overlay> has no path attribute"))
                continue
            declared.add(p.rstrip("/") + "/")
            if not s.has_dir(p):
                out.append(Finding("error", "OVLMISS", "info.xml",
                                   f"declared overlay {p!r} does not exist in the archive",
                                   "'Path {} does not exist in mod {}'"))
    # Undeclared data/ overlays still work today but the client logs them as
    # deprecated (string 1207) and says they will be removed.
    shipped = {f.rsplit("/", 1)[0] + "/" for f in s.files if f.startswith("data/")}
    for d in sorted(shipped):
        if not any(d.startswith(dec) for dec in declared):
            # data/strings/ used to be exempted here on the assumption that
            # declaring the files in <strings> was enough. It is not: the live
            # client logs string 1207 for a strings mod that ships under data/,
            # naming the directory, however completely info.xml lists the files.
            # Shipping them outside data/ -- as the reference mods do -- avoids
            # the overlay entirely.
            out.append(Finding(
                "warn", "OVLUNDECLARED", d,
                "overlays a client directory without declaring it in info.xml",
                "Add <overlays><overlay path=\"%s\"/></overlays>; the client "
                "calls the undeclared form deprecated." % d))
    return out


def _check_theme_entry(s: Source, t: ET.Element, tag: str) -> list[Finding]:
    out = []
    name, path = t.get("name"), t.get("path")
    for attr in ("name", "path", "is_mobile"):
        if t.get(attr) is None:
            out.append(Finding("error", "THEMEATTR", "info.xml",
                               f"<{tag}> has no {attr} attribute"))
    if name and name.lower() in ("default", "android"):
        out.append(Finding("error", "THEMENAME", "info.xml",
                           f"theme name {name!r} is reserved",
                           "Themes named `default` or `android` are refused."))
    if name and ("/" in name[1:] or "." in name):
        out.append(Finding("warn", "THEMECHARS", "info.xml",
                           f"theme name {name!r} uses '/' or '.'",
                           "'/' is only allowed as first character; '.' only for "
                           "absolute theme paths."))
    if path:
        if not s.has_dir(path):
            out.append(Finding("error", "THEMEDIR", "info.xml",
                               f"theme path {path!r} is not a directory in the archive"))
        elif not s.has(path.rstrip("/") + "/theme.xml"):
            out.append(Finding("error", "THEMEXML", "info.xml",
                               f"{path}theme.xml is missing",
                               "A theme folder must contain theme.xml."))
    return out


# --- content trees ---------------------------------------------------------
def _check_content(s: Source, declared: tuple[str, ...] = ()) -> list[Finding]:
    out: list[Finding] = []
    egg_count = 0
    for f in sorted(s.files):
        if f in ("info.xml", "icon.png") or f.startswith("data/"):
            continue
        if any(f == d or f.startswith(d) for d in declared):
            continue
        base = posixpath.basename(f)
        if base in JUNK or base in IGNORED or base.startswith("._"):
            continue
        rule = spec.match_content_dir(posixpath.dirname(f))
        if rule is None:
            top = f.split("/")[0]
            if top not in {r.path.split("/")[0] for r in spec.CONTENT_DIRS}:
                out.append(Finding("warn", "UNKNOWNDIR", f,
                                   "not under any directory the loader reads",
                                   "Loader reads: " +
                                   ", ".join(r.path for r in spec.CONTENT_DIRS)))
            continue

        stem, ext = posixpath.splitext(base)
        ext = ext.lower()
        if rule.path == "sprites/battlesprites" and base in spec.BATTLE_TABLES:
            continue
        if ext not in rule.exts:
            out.append(Finding("error", "EXT", f,
                               f"{ext or 'no extension'} is not allowed in {rule.path}",
                               f"Only {'/'.join(rule.exts)} files supported for /{rule.path}/"))
            continue

        rel_inside = posixpath.relpath(posixpath.dirname(f), rule.path)
        if rule.regioned:
            if rel_inside in (".", ""):
                out.append(Finding("error", "NOREGION", f,
                                   f"{rule.path} files must sit in a region folder",
                                   "Valid region ids: " +
                                   " / ".join(str(k) for k in spec.REGIONS)))
                continue
            reg = spec.region_of(rel_inside.split("/")[0])
            if reg is None or (reg not in spec.REGIONS and reg not in spec.LEGACY_REGIONS):
                out.append(Finding("error", "REGION", f,
                                   f"'{rel_inside}' is not a valid region id",
                                   "Valid region IDs are: 0 / 1 / 2 / 3 / 10"))
                continue
            if reg in spec.LEGACY_REGIONS:
                out.append(Finding("warn", "REGIONOLD", f,
                                   f"region {reg} is not in the client's accepted list",
                                   "Client message lists 0 / 1 / 2 / 3 / 10 only."))
        elif rel_inside not in (".", ""):
            out.append(Finding("warn", "SUBDIR", f,
                               f"unexpected sub-folder under {rule.path}"))

        if rule.path == "sprites/monstericons" and spec.RE_COMPOSITE.match(stem):
            continue
        if rule.path == "sprites/battlesprites" and spec.RE_BATTLE_SPECIAL.match(stem):
            continue
        if rule.path == "sprites/monstericons" and spec.RE_ICON_SPECIAL.match(stem):
            continue
        if rule.path == "sprites/eggsprites":
            egg_count += 1

        if rule.pattern and not rule.pattern.match(stem):
            out.append(Finding("error", "NAME", f,
                               f"filename does not match the {rule.path} grammar",
                               _grammar_hint(rule)))
            continue

        if rule.path == "sprites/battlesprites":
            m = spec.RE_BATTLE.match(stem)
            if m and ext == ".gif" and m.group("frame"):
                out.append(Finding("error", "GIFFRAME", f,
                                   "GIF format does not support frame ids",
                                   "Drop the trailing -N; an animated GIF carries "
                                   "its own frames."))

    if egg_count and egg_count % 6:
        out.append(Finding("warn", "EGGCOUNT", "sprites/eggsprites",
                           f"{egg_count} egg PNGs found",
                           "The client wants exactly 6 PNG images per egg set."))
    return out


def _grammar_hint(rule) -> str:
    return {
        "sprites/battlesprites":
            "ID-{front|back}-{n|s}[-{m|f}][-FRAME].png  e.g. 1-front-n.gif",
        "sprites/monstericons": "ID-FRAME.png  e.g. 1-0.png (frames 0..2)",
        "sprites/itemicons": "ID.png  e.g. 27.png",
        "sprites/trainersprites": "<region>/ID.png  e.g. 0/200.png",
        "sprites/overworldsprites": "<region>/ID-FRAME.png  e.g. 0/1062-0.png",
        "sprites/followcostumes": "ID-FRAME.png, 8 frames per costume",
        "sprites/eggsprites": "egg_SET_FRAME.png, 6 per set",
        "costumes": "spriteId-baseSpriteId.costume",
        "cries": "ID.wav",
        "sounds": "<region>/ID.ogg",
        "world_map_footers": "REGION-ID.bin",
        "world_map_headers": "ID.N.bin",
    }.get(rule.path, "")


def summarize(findings: list[Finding]) -> tuple[int, int]:
    errors = sum(1 for f in findings if f.level == "error")
    warns = sum(1 for f in findings if f.level == "warn")
    return errors, warns
