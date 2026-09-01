"""Static checks on TWL theme XML that catch layout-loop generators.

Found the hard way: the stock Android theme declares, on one widget,
minWidth 1080 together with maxWidth 800. Contradictory bounds are exactly
what makes TWL re-run layout until it gives up and logs
"layout loop detected - printing".
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

PAIRS = [("minWidth", "maxWidth"), ("minHeight", "maxHeight")]


@dataclass
class ThemeFinding:
    file: str
    theme: str
    message: str
    hint: str

    def __str__(self) -> str:
        return (f"ERROR {self.file}: <theme name=\"{self.theme}\"> {self.message}"
                f"\n        -> {self.hint}")


def _int_params(elem) -> dict[str, int]:
    """The <param name="X"><int>N</int></param> children of this element only.

    Walking the tree rather than scanning text matters: a self-closing
    <theme name="hscrollbar"/> sits between a widget and its own params, and a
    regex scan blames the wrong widget for the defect.
    """
    out: dict[str, int] = {}
    for param in elem.findall("param"):
        name = param.get("name")
        node = param.find("int")
        if name and node is not None and node.text:
            try:
                out[name] = int(node.text.strip())
            except ValueError:
                pass
    return out


def _walk(elem, path: str, acc: list, filename: str) -> None:
    for child in elem:
        if child.tag != "theme":
            continue
        name = child.get("name") or "(unnamed)"
        params = _int_params(child)
        for lo_key, hi_key in PAIRS:
            if lo_key in params and hi_key in params and params[lo_key] > params[hi_key]:
                acc.append(ThemeFinding(
                    filename, f"{path}{name}" if path else name,
                    f"{lo_key}={params[lo_key]} is greater than "
                    f"{hi_key}={params[hi_key]}",
                    "Contradictory bounds make the layout pass oscillate; TWL "
                    "eventually logs 'layout loop detected'. Raise the max or "
                    "lower the min."))
        _walk(child, f"{path}{name} > ", acc, filename)


def lint_file(path: Path) -> list[ThemeFinding]:
    from xml.etree import ElementTree as ET

    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return []
    acc: list[ThemeFinding] = []
    _walk(root, "", acc, str(path))
    return acc


def lint_tree(root: Path) -> list[ThemeFinding]:
    out: list[ThemeFinding] = []
    for p in sorted(Path(root).rglob("*.xml")):
        out += lint_file(p)
    return out
