"""Scan the client's logs for the failure signatures mods and themes cause.

Written against the message table in the shipped binary, so each signature
carries the client's own wording plus what actually fixes it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Signature:
    key: str
    pattern: re.Pattern
    what: str
    fix: str
    follow: int = 0        # extra lines of context worth printing


SIGNATURES: list[Signature] = [
    Signature(
        "layout-loop",
        re.compile(r"layout loop detected", re.I),
        "A widget kept invalidating its own layout until the UI toolkit (TWL) "
        "gave up. The client shows 'A UI layout loop issue was detected. You may "
        "experience reduced performance or lag.' -- with the "
        "'this may be an issue with your theme or other mods' wording whenever a "
        "theme or mod is loaded.",
        "The lines printed right after this marker name the widgets caught in the "
        "loop; that name maps to an entry in your theme's ui/*.xml. Usual causes: "
        "a widget whose size depends on a child that depends back on the parent, a "
        "minWidth/minHeight that fights the alignment, or a scrollpane sized to its "
        "content. To confirm it is the theme, run the client with --theme-default "
        "and see if the warning stops.",
        follow=30,
    ),
    Signature(
        "missing-child-theme",
        re.compile(r'Missing child theme "(?P<name>[^"]+)" for "(?P<parent>[^"]+)"'),
        "A theme references a child widget theme that does not exist.",
        "Add the named child theme to your theme's ui/*.xml, or update the theme "
        "for the current client revision -- the client adds widgets between "
        "revisions and older themes stop covering them.",
    ),
    Signature(
        "theme-revision",
        re.compile(r"(Theme|Theme-Extension|String) revision \d+ is above current revision"),
        "The mod declares a newer revision than this client speaks.",
        "Lower theme_revision / string_revision in info.xml to the number the "
        "client logs as 'Client Theme Revision', or update the client.",
    ),
    Signature(
        "theme-outdated",
        re.compile(r"because it is outdated|Could not load theme", re.I),
        "The theme was built for an older client and no longer loads.",
        "Re-base it on the current data/themes/default/ tree: "
        "pmmod theme scaffold <dir>.",
    ),
    Signature(
        "theme-constant",
        re.compile(r"Failed loading constant .* for theme|Could not load theme constant"),
        "A theme constant has a value the client cannot parse or is duplicated.",
        "Check the <constantDef> blocks in theme.xml; the client falls back to "
        "the default value and keeps going.",
    ),
    Signature(
        "mod-apply",
        re.compile(r"failed to apply|Error applying mod|Error loading mod|Error validating mod", re.I),
        "A mod archive failed the loader's checks.",
        "Run pmmod validate on the source; the log line names the file.",
    ),
    Signature(
        "bad-filename",
        re.compile(r"(invalid file name|does not have enough fields|has an invalid \w+ id)", re.I),
        "A file inside a mod does not match the loader's naming grammar.",
        "pmmod validate reports the same thing with the expected grammar; "
        "pmmod sprites rescue can rename a whole legacy sprite mod.",
    ),
    Signature(
        "sound",
        re.compile(r"Error loading sound", re.I),
        "A sound file in a mod could not be decoded.",
        "Only .wav/.mp3/.ogg are accepted, and Android refuses compressed music "
        "mods -- ship those uncompressed.",
    ),
    Signature(
        "overlay-deprecated",
        re.compile(r"tries to overlay the .* directory", re.I),
        "A mod replaces files under data/ without declaring the directory.",
        "Add <overlays><overlay path=\"data/.../\"/></overlays> to info.xml. The "
        "client calls the undeclared form deprecated.",
    ),
]

# Handheld/Android notes worth surfacing when a layout loop shows up there.
HANDHELD_NOTE = """
On a handheld (Retroid, PortMaster builds, phones) the layout loop is most often
a desktop theme running on a small screen:

  * A theme must declare is_mobile="true" to be a mobile theme. A desktop-only
    theme on the Android client is refused outright ("Could not load theme {}
    because it is not a mobile theme"); a theme that claims mobile but was laid
    out for 1080p is the one that loops.
  * Settings > Interface > UI Scaling changes size live, and the client
    regenerates the whole theme and font set when it does ("live UI-scale change
    ... regenerating theme/fonts"). Set the scale once, restart, and see whether
    the warning still appears.
  * High DPI Fonts costs VRAM and CPU on these devices; turning it off is a
    cheap test and often removes the lag the warning is complaining about.
  * The stock mobile theme is data/themes/android/. Compare your theme's
    ui/*.xml against it rather than against default/.

Isolate it in three restarts:
  1. pmmod disable <each theme mod>   -> restart -> still warning?
  2. client with --theme-default      -> restart -> still warning?
  3. all mods off                     -> if it persists it is the client itself,
                                         and string 2925 ("contact support") is
                                         the one you will see instead.
"""


@dataclass
class Hit:
    signature: Signature
    line: str
    context: list[str]


def scan(paths: list[Path]) -> list[Hit]:
    hits: list[Hit] = []
    for path in paths:
        if not Path(path).is_file():
            continue
        lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
        for i, line in enumerate(lines):
            for sig in SIGNATURES:
                if sig.pattern.search(line):
                    ctx = lines[i + 1: i + 1 + sig.follow] if sig.follow else []
                    hits.append(Hit(sig, f"{Path(path).name}: {line.strip()}", ctx))
                    break
    return hits


def render(hits: list[Hit], show_context: bool = False) -> str:
    if not hits:
        return "No known mod/theme failure signatures in the logs."
    out: list[str] = []
    seen: dict[str, int] = {}
    for h in hits:
        seen[h.signature.key] = seen.get(h.signature.key, 0) + 1
    for key, count in seen.items():
        sig = next(h.signature for h in hits if h.signature.key == key)
        examples = [h for h in hits if h.signature.key == key]
        out.append(f"### {key}  ({count} occurrence(s))")
        out.append(f"  {sig.what}")
        out.append(f"  FIX: {sig.fix}")
        out.append(f"  e.g. {examples[0].line}")
        if show_context and examples[0].context:
            out.append("  context:")
            out += [f"    {c}" for c in examples[0].context if c.strip()]
        out.append("")
    if any(h.signature.key == "layout-loop" for h in hits):
        out.append(HANDHELD_NOTE)
    return "\n".join(out)
