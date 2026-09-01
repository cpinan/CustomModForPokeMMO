"""Create a new mod source tree that is valid on the first build."""
from __future__ import annotations

import base64
from pathlib import Path

from . import spec

# 48x48 transparent PNG with a filled rounded square, used when Pillow is
# unavailable. Replace it with real art before publishing.
_FALLBACK_ICON = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAYAAABXAvmHAAAAXklEQVRoge3QMQ0AMAzAsPIn"
    "3ZHoIYskC3xnZ+bcQ6zXAV8ZUGZAmQFlBpQZUGZAmQFlBpQZUGZAmQFlBpQZUGZAmQFlBpQZ"
    "UGZAmQFlBpQZUGZAmQFlBpQZUPYAoQIB9c3s2ZcAAAAASUVORK5CYII=")

KINDS = {
    "battlesprites": ["sprites/battlesprites"],
    "monstericons": ["sprites/monstericons"],
    "itemicons": ["sprites/itemicons"],
    "overworld": ["sprites/overworldsprites/0"],
    "trainers": ["sprites/trainersprites/0"],
    "cries": ["cries"],
    "sounds": ["sounds/0"],
    "strings": ["data/strings"],
    "theme": ["theme"],
    "overlay": ["data/sprites/atlas"],
    "empty": [],
}

_TABLE_HEADER = """;Table which determines {what} for battle sprites.
;Lines starting with ; will be ignored
;Please only include values for overriden sprites!
"""

TABLE_TEMPLATES = {
    "table-front-scale.txt": _TABLE_HEADER.format(what="scales") +
        ';Each entry should be a separate line and contain ID=SCALE, like "1=3" without quotes.\n',
    "table-back-scale.txt": _TABLE_HEADER.format(what="scales") +
        ';Each entry should be a separate line and contain ID=SCALE, like "1=3" without quotes.\n',
    "table-summary-scale.txt": _TABLE_HEADER.format(what="scales") +
        ';Each entry should be a separate line and contain ID=SCALE, like "1=3" without quotes.\n',
    "table-coordinate-mods.txt": _TABLE_HEADER.format(what="coordinate modifications") +
        ";Each entry should be a separate line and contain ID,(FRONT/BACK)=X,Y,Z.\n"
        ";Scale is clamped from -1 to 1. Default values for all fields are 0.\n"
        ";X: Negative values push left, positive values push right.\n"
        ";Y: Higher values push up, lower values push down.\n"
        ";Z: Higher values push away from the camera, lower values push towards the camera.\n"
        ";Example (Altitude mod only, increasing Y by 0.31): 1,front=0,0.31,0\n",
}


def _info_xml(name, version, description, author, weblink, kind,
              theme_revision, string_revision) -> str:
    sections = ""
    if kind == "theme":
        sections = (
            f'    <themes theme_revision="{theme_revision}">\n'
            f'        <theme path="theme/" name="{name}" is_mobile="false"/>\n'
            f"    </themes>\n")
    elif kind == "strings":
        sections = (
            f'    <strings string_revision="{string_revision}">\n'
            f'        <string path="data/strings/strings_en_{_slug(name)}.xml"/>\n'
            f"    </strings>\n")
    elif kind == "overlay":
        sections = (
            "    <overlays>\n"
            '        <overlay path="data/sprites/atlas/"/>\n'
            "    </overlays>\n")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<resource name="{_x(name)}" version="{_x(version)}" '
        f'description="{_x(description)}" author="{_x(author)}" '
        f'weblink="{_x(weblink)}">\n'
        f"{sections}</resource>\n")


def _x(s: str) -> str:
    return (s.replace("&", "&amp;").replace('"', "&quot;")
             .replace("<", "&lt;").replace(">", "&gt;").replace("\n", "&#10;"))


def _slug(text: str) -> str:
    out = "".join(c.lower() if c.isalnum() else "_" for c in text)
    while "__" in out:
        out = out.replace("__", "_")
    return out.strip("_") or "mod"


def make_icon(dest: Path, label: str) -> None:
    try:
        from PIL import Image, ImageDraw  # type: ignore
    except Exception:
        dest.write_bytes(_FALLBACK_ICON)
        return
    img = Image.new("RGBA", (48, 48), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([2, 2, 45, 45], radius=8, fill=(38, 52, 70, 255),
                        outline=(106, 136, 155, 255), width=2)
    initials = "".join(w[0] for w in label.split()[:2]).upper() or "M"
    d.text((24, 24), initials, fill=(220, 230, 240, 255), anchor="mm")
    img.save(dest)


def new_mod(target: Path, name: str, kind: str = "empty", version: str = "1.0",
            author: str = "", description: str = "", weblink: str = "",
            theme_revision: int = spec.DEFAULT_THEME_REVISION,
            string_revision: int = 1) -> Path:
    if kind not in KINDS:
        raise SystemExit(f"Unknown kind {kind!r}. Choose from: {', '.join(KINDS)}")
    target = Path(target).expanduser()
    if target.exists() and any(target.iterdir()):
        raise SystemExit(f"{target} already exists and is not empty")
    target.mkdir(parents=True, exist_ok=True)

    weblink = weblink or spec.WEBLINK_PREFIX + "/"
    (target / "info.xml").write_text(
        _info_xml(name, version, description or f"{name} for PokeMMO.",
                  author, weblink, kind, theme_revision, string_revision),
        encoding="utf-8")
    make_icon(target / "icon.png", name)

    for folder in KINDS[kind]:
        (target / folder).mkdir(parents=True, exist_ok=True)
        (target / folder / ".gitkeep").touch()

    if kind == "battlesprites":
        for fname, body in TABLE_TEMPLATES.items():
            (target / "sprites/battlesprites" / fname).write_text(body, encoding="utf-8")
    if kind == "strings":
        f = target / "data/strings" / f"strings_en_{_slug(name)}.xml"
        f.write_text(
            '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
            '<strings lang="en" lang_full="English" is_primary="0">\n'
            "  <!-- Override any id from data/strings/strings_en.xml.\n"
            "       Find ids with: pmmod strings find \"Nurse Joy\" -->\n"
            "</strings>\n", encoding="utf-8")
    if kind == "theme":
        (target / "theme").mkdir(exist_ok=True)
        (target / "theme" / "theme.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            "<themes>\n"
            "    <!-- Start from the client's data/themes/default/ tree:\n"
            "         pmmod theme scaffold to copy it here. -->\n"
            "</themes>\n", encoding="utf-8")
    return target
