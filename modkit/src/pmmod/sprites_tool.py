"""Sprite tooling: inspect, rename to spec, and rescue legacy mod layouts."""
from __future__ import annotations

import re
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path

from . import spec

IMG_EXTS = {".png", ".gif"}

# Layouts that community scripts (and older guides) produced, none of which
# the current loader reads. Each entry maps an old path to the modern one.
LEGACY_PATTERNS = [
    # sprites/front/25.gif  -> sprites/battlesprites/25-front-n.gif
    (re.compile(r"^sprites/(?P<side>front|back)/(?P<id>\d+)(?P<shiny>s?)\.(?P<ext>gif|png)$"),
     "side_dir"),
    # sprites/25_back.gif / sprites/25s.gif / sprites/25.gif
    (re.compile(r"^sprites/(?P<id>\d+)(?P<shiny>s?)(?P<back>_back)?\.(?P<ext>gif|png)$"),
     "flat"),
    # battlesprites/25.gif (right folder, no descriptors)
    (re.compile(r"^sprites/battlesprites/(?P<id>\d+)\.(?P<ext>gif|png)$"), "bare"),
]

LEGACY_TABLES = {
    "sprites/scale.txt": "sprites/battlesprites/table-front-scale.txt",
    "sprites/scale_back.txt": "sprites/battlesprites/table-back-scale.txt",
    "scale.txt": "sprites/battlesprites/table-front-scale.txt",
}


@dataclass
class Move:
    src: str
    dst: str
    why: str


def plan_moves(names: list[str]) -> tuple[list[Move], list[str]]:
    """Map legacy names onto the loader's grammar. Returns (moves, unmatched)."""
    moves: list[Move] = []
    unmatched: list[str] = []
    for name in names:
        if name in LEGACY_TABLES:
            moves.append(Move(name, LEGACY_TABLES[name], "legacy scale table"))
            continue
        if name in ("info.xml", "icon.png") or name.startswith("data/"):
            continue
        hit = None
        for rx, kind in LEGACY_PATTERNS:
            m = rx.match(name)
            if m:
                hit = (m, kind)
                break
        if not hit:
            if Path(name).suffix.lower() in IMG_EXTS:
                unmatched.append(name)
            continue
        m, kind = hit
        g = m.groupdict()
        side = g.get("side") or ("back" if g.get("back") else "front")
        shiny = "s" if g.get("shiny") else "n"
        dst = f"sprites/battlesprites/{g['id']}-{side}-{shiny}.{g['ext']}"
        moves.append(Move(name, dst, f"{kind} layout -> battlesprites grammar"))
    return moves, unmatched


def rescue(source: Path, out_dir: Path, name: str, author: str = "",
           version: str = "1.0", weblink: str = "",
           description: str = "") -> tuple[Path, list[Move], list[str]]:
    """Rebuild a legacy .mod/zip/folder as a valid mod source tree."""
    from .scaffold import make_icon, _info_xml

    source = Path(source).expanduser()
    out_dir = Path(out_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    if source.is_dir():
        names = [p.relative_to(source).as_posix()
                 for p in sorted(source.rglob("*")) if p.is_file()]
        read = lambda rel: (source / rel).read_bytes()
    else:
        zf = zipfile.ZipFile(source)
        names = [i.filename for i in zf.infolist() if not i.is_dir()]
        read = zf.read

    moves, unmatched = plan_moves(names)
    for mv in moves:
        dst = out_dir / mv.dst
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(read(mv.src))

    # carry over an existing info.xml/icon.png, otherwise write fresh ones
    if "info.xml" in names:
        (out_dir / "info.xml").write_bytes(read("info.xml"))
    else:
        (out_dir / "info.xml").write_text(
            _info_xml(name, version, description or f"{name} for PokeMMO.",
                      author, weblink or spec.WEBLINK_PREFIX + "/", "empty",
                      spec.DEFAULT_THEME_REVISION, 1), encoding="utf-8")
    if "icon.png" in names:
        (out_dir / "icon.png").write_bytes(read("icon.png"))
    else:
        make_icon(out_dir / "icon.png", name)
    return out_dir, moves, unmatched


@dataclass
class ImageInfo:
    path: str
    size: tuple[int, int] | None
    frames: int
    mode: str
    bytes: int


def inspect(paths: list[Path]) -> list[ImageInfo]:
    try:
        from PIL import Image, ImageSequence  # type: ignore
    except Exception:
        return [ImageInfo(str(p), None, 0, "?", p.stat().st_size) for p in paths]
    out = []
    for p in paths:
        try:
            with Image.open(p) as im:
                frames = sum(1 for _ in ImageSequence.Iterator(im))
                out.append(ImageInfo(str(p), im.size, frames, im.mode, p.stat().st_size))
        except Exception as e:
            out.append(ImageInfo(f"{p} ({e})", None, 0, "?", p.stat().st_size))
    return out


def write_scale_table(path: Path, values: dict[int, float], back: bool = False) -> Path:
    from .scaffold import TABLE_TEMPLATES

    fname = "table-back-scale.txt" if back else "table-front-scale.txt"
    header = TABLE_TEMPLATES[fname]
    body = "".join(f"{k}={v:g}\n" for k, v in sorted(values.items()))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(header + body, encoding="utf-8")
    return path


def parse_scale_table(text: str) -> dict[int, float]:
    out: dict[int, float] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(";") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        try:
            out[int(k.strip())] = float(v.strip())
        except ValueError:
            continue
    return out


def parse_id_ranges(spec: str) -> list[int]:
    """"1-649,1000,1005-1010" -> a sorted list of ids."""
    out: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part[1:]:
            lo, hi = part.split("-", 1)
            out.update(range(int(lo), int(hi) + 1))
        else:
            out.add(int(part))
    return sorted(out)


def blank_png(size: int = 64) -> bytes:
    """A fully transparent PNG. Written once and reused for every file."""
    from io import BytesIO

    try:
        from PIL import Image  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise SystemExit("Pillow is required to generate blank sprites") from exc
    buf = BytesIO()
    Image.new("RGBA", (size, size), (0, 0, 0, 0)).save(buf, "PNG", optimize=True)
    return buf.getvalue()


def write_blank_battlesprites(out_dir: Path, ids: list[int],
                              shiny: str = "n",
                              sides: tuple[str, ...] = ("front", "back"),
                              genders: tuple[str, ...] = ("", "-m", "-f"),
                              size: int = 64) -> int:
    """Override battle sprites with a transparent image.

    Writing the plain `ID-side-n` plus both gendered variants covers species
    whose ROM sprite is gender-specific, where a bare override might not be the
    file the client looks for.
    """
    target = Path(out_dir) / "sprites" / "battlesprites"
    target.mkdir(parents=True, exist_ok=True)
    blob = blank_png(size)
    count = 0
    for i in ids:
        for side in sides:
            for g in genders:
                (target / f"{i}-{side}-{shiny}{g}.png").write_bytes(blob)
                count += 1
    return count
