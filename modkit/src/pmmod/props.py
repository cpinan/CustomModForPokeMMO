"""Read/write the client's config/main.properties without disturbing it.

java.util.Properties escaping: keys/values escape ':' '=' and leading spaces
with a backslash. Only the values pmmod touches are rewritten; every other
line is preserved byte for byte.
"""
from __future__ import annotations

from pathlib import Path

ENABLED_KEY = "client.mods.enabled_mods"
VERBOSE_KEY = "client.mods.debugs.verbose.enabled"
THEME_KEY = "client.ui.theme"
SEPARATOR = "/"   # yes, mods are separated by '/', not ','


def _unescape(value: str) -> str:
    out, i = [], 0
    while i < len(value):
        c = value[i]
        if c == "\\" and i + 1 < len(value):
            i += 1
            out.append(value[i])
        else:
            out.append(c)
        i += 1
    return "".join(out)


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("=", "\\=").replace(":", "\\:")


def load(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.is_file():
        return data
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if not s or s[0] in "#!":
            continue
        if "=" not in s:
            continue
        k, v = s.split("=", 1)
        data[k.strip()] = _unescape(v)
    return data


def set_keys(path: Path, updates: dict[str, str]) -> None:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    remaining = dict(updates)
    for idx, line in enumerate(lines):
        s = line.strip()
        if not s or s[0] in "#!" or "=" not in s:
            continue
        key = s.split("=", 1)[0].strip()
        if key in remaining:
            eol = "\n" if line.endswith("\n") else ""
            lines[idx] = f"{key}={_escape(remaining.pop(key))}{eol}"
    tail = "".join(f"{k}={_escape(v)}\n" for k, v in remaining.items())
    if lines and not lines[-1].endswith("\n") and tail:
        lines.append("\n")
    path.write_text("".join(lines) + tail, encoding="utf-8")


def enabled_mods(path: Path) -> list[str]:
    raw = load(path).get(ENABLED_KEY, "")
    return [m for m in raw.split(SEPARATOR) if m]


def set_enabled_mods(path: Path, mods: list[str]) -> None:
    seen, ordered = set(), []
    for m in mods:
        if m not in seen:
            seen.add(m)
            ordered.append(m)
    set_keys(path, {ENABLED_KEY: SEPARATOR.join(ordered)})
