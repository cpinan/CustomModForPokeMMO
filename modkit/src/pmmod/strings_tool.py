"""Text tooling: find string ids, extract them, and build an override file.

The client ships data/strings/strings_<lang>.xml with is_primary="1". A mod
supplies a second file with is_primary="0" that redefines only the ids it
cares about. Everything else falls through to the primary file.
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path

RE_STRING = re.compile(
    r'<string\s+(?P<attrs>[^>]*?)\s*>(?P<text>.*?)</string>', re.S)
RE_ATTR = re.compile(r'(\w+)="([^"]*)"')

# Storyline text is keyed by a (block, entry, table) triple instead of an id.
STORY_KEYS = ("block_id", "entry_id", "table_id")


@dataclass
class Entry:
    key: str                 # "id=123" or "block=1,entry=2,table=3"
    attrs: dict
    text: str

    @property
    def is_story(self) -> bool:
        return "id" not in self.attrs

    def as_xml(self, text: str | None = None) -> str:
        body = html.escape(text if text is not None else self.text, quote=False)
        if self.is_story:
            a = " ".join(f'{k}="{self.attrs[k]}"' for k in STORY_KEYS if k in self.attrs)
        else:
            a = f'id="{self.attrs["id"]}"'
            if self.attrs.get("preload"):
                a += f' preload="{self.attrs["preload"]}"'
        return f"  <string {a}>{body}</string>"


def parse_file(path: Path) -> list[Entry]:
    raw = Path(path).read_text(encoding="utf-8", errors="replace")
    out = []
    for m in RE_STRING.finditer(raw):
        attrs = dict(RE_ATTR.findall(m["attrs"]))
        if "id" in attrs:
            key = f"id={attrs['id']}"
        else:
            key = ",".join(f"{k.split('_')[0]}={attrs[k]}" for k in STORY_KEYS if k in attrs)
        out.append(Entry(key, attrs, html.unescape(m["text"])))
    return out


def find(entries: list[Entry], pattern: str, ignore_case: bool = True) -> list[Entry]:
    flags = re.I if ignore_case else 0
    rx = re.compile(pattern, flags)
    return [e for e in entries if rx.search(e.text) or rx.search(e.key)]


def by_ids(entries: list[Entry], ids: list[str]) -> list[Entry]:
    want = set(ids)
    return [e for e in entries if e.attrs.get("id") in want]


def build_override(entries: list[Entry], lang: str = "en",
                   lang_full: str = "English",
                   replacements: dict[str, str] | None = None) -> str:
    replacements = replacements or {}
    body = "\n".join(e.as_xml(replacements.get(e.attrs.get("id", e.key)))
                     for e in entries)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
        f'<strings lang="{lang}" lang_full="{lang_full}" is_primary="0">\n'
        f"{body}\n"
        "</strings>\n")


BLANK = "\\n"   # what the community uses to silence a line of dialogue


def silence(entries: list[Entry], lang: str = "en") -> str:
    """Every matched string replaced with the escaped newline used to make
    dialogue advance instantly -- the trick behind the 'fast text' mods."""
    return build_override(entries, lang=lang,
                          replacements={e.attrs.get("id", e.key): BLANK for e in entries})


def language_files(strings_dir: Path) -> dict[str, Path]:
    out = {}
    for p in sorted(Path(strings_dir).glob("strings_*.xml")):
        code = p.stem.split("_", 1)[1]
        out[code] = p
    return out
