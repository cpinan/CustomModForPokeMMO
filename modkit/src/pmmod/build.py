"""Pack a mod source directory into a .mod archive."""
from __future__ import annotations

import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from .validate import IGNORED, JUNK, JUNK_DIRS


def read_meta(src: Path) -> dict:
    info = src / "info.xml"
    if not info.is_file():
        raise SystemExit(f"{src}: no info.xml -- not a mod source directory")
    root = ET.fromstring(info.read_text(encoding="utf-8"))
    return {k: root.get(k, "") for k in ("name", "version", "description", "author", "weblink")}


def slug(text: str) -> str:
    out = "".join(c.lower() if c.isalnum() else "-" for c in text)
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-") or "mod"


def default_output_name(src: Path) -> str:
    meta = read_meta(src)
    ver = slug(meta["version"]) or "0"
    return f"{slug(meta['name'])}-{ver}.mod"


def build(src: Path, out: Path | None = None, compress: bool = True) -> Path:
    """Zip the *contents* of src (never src itself) into a .mod file."""
    src = Path(src).expanduser().resolve()
    if not src.is_dir():
        raise SystemExit(f"{src} is not a directory")
    if out is None:
        out = src.parent / "dist" / default_output_name(src)
    out = Path(out).expanduser()
    if out.is_dir():
        out = out / default_output_name(src)
    out.parent.mkdir(parents=True, exist_ok=True)

    mode = zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED
    count = 0
    with zipfile.ZipFile(out, "w", mode) as zf:
        for path in sorted(src.rglob("*")):
            rel = path.relative_to(src)
            if any(part in JUNK_DIRS for part in rel.parts):
                continue
            if path.name in JUNK or path.name in IGNORED or path.name.startswith("._"):
                continue
            if not path.is_file():
                continue
            zf.write(path, rel.as_posix())
            count += 1
    return out
