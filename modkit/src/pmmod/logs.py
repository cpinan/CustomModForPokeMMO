"""Read log/mods.log -- the client's own account of what it loaded.

Turn on Settings > Other > Verbose Mod Debugs (or `pmmod verbose on`) and the
client logs one line per file it takes from each archive. That log is the only
ground truth for whether a mod actually applied.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

RE_LINE = re.compile(r"^\[(?P<level>\w+)\s+(?P<ts>[^\]]+)\]\s+-\s+(?P<msg>.*)$")
RE_LOADED_FILE = re.compile(r"^Loaded (?P<file>\S+) from (?P<src>\S+)$")
RE_AVAILABLE = re.compile(r"^Loaded available mod '(?P<name>.*)'$")
RE_POSSIBLE = re.compile(r"^Possible mod (?P<file>.+)$")
RE_APPLYING = re.compile(r"^(?P<file>.+) is enabled, applying\.$")
RE_APPLIED = re.compile(r"^(?P<file>.+) applied\.$")
RE_SKIPPED = re.compile(r"^(?P<file>.+) is disabled, skipping\.$")
RE_THEME_REV = re.compile(r"^Client Theme Revision: (?P<rev>\d+)$")

PROBLEM_HINTS = ("invalid", "error", "failed", "not valid", "corrupt",
                 "does not have enough fields", "cannot be modified",
                 "is above current revision", "is not a number")
# "Only .png files supported for /sprites/itemicons/" is a format notice the
# client prints once at start, not a fault -- don't report it as a problem.
RE_FORMAT_NOTICE = re.compile(r"^Only \S+ files supported for /")


@dataclass
class LogReport:
    theme_revision: str | None = None
    discovered: list[str] = field(default_factory=list)
    available: list[str] = field(default_factory=list)
    applying: list[str] = field(default_factory=list)
    applied: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    files_by_source: Counter = field(default_factory=Counter)
    started: str | None = None

    @property
    def failed(self) -> list[str]:
        return [m for m in self.applying if m not in self.applied]


def parse(path: Path) -> LogReport:
    rep = LogReport()
    if not Path(path).is_file():
        return rep
    for raw in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        m = RE_LINE.match(raw.strip())
        if not m:
            continue
        msg, level, ts = m["msg"].strip(), m["level"], m["ts"]
        if rep.started is None:
            rep.started = ts

        if (t := RE_THEME_REV.match(msg)):
            rep.theme_revision = t["rev"]
        elif (t := RE_LOADED_FILE.match(msg)):
            rep.files_by_source[t["src"]] += 1
        elif (t := RE_AVAILABLE.match(msg)):
            rep.available.append(t["name"])
        elif (t := RE_POSSIBLE.match(msg)):
            rep.discovered.append(t["file"])
        elif (t := RE_APPLYING.match(msg)):
            rep.applying.append(t["file"])
        elif (t := RE_APPLIED.match(msg)):
            rep.applied.append(t["file"])
        elif (t := RE_SKIPPED.match(msg)):
            rep.skipped.append(t["file"])
        elif RE_FORMAT_NOTICE.match(msg):
            pass
        elif level in ("WARN", "ERROR") or any(
                h in msg.lower() for h in PROBLEM_HINTS):
            rep.problems.append(f"[{level}] {msg}")
    return rep


def render(rep: LogReport, verbose: bool = False) -> str:
    lines = []
    if rep.started:
        lines.append(f"last client start : {rep.started}")
    lines.append(f"theme revision    : {rep.theme_revision or 'not logged'}")
    lines.append(f"discovered        : {', '.join(rep.discovered) or '-'}")
    lines.append(f"applied           : {', '.join(rep.applied) or '-'}")
    if rep.skipped:
        lines.append(f"present, disabled : {', '.join(rep.skipped)}")
    if rep.failed:
        lines.append(f"APPLY DID NOT FINISH: {', '.join(rep.failed)}")
    if rep.files_by_source:
        lines.append("files taken from each archive:")
        for src, n in rep.files_by_source.most_common():
            lines.append(f"  {n:>6}  {src}")
    elif rep.applied:
        lines.append("no per-file lines -- enable verbose logging: pmmod verbose on")
    if rep.problems:
        lines.append(f"problems ({len(rep.problems)}):")
        shown = rep.problems if verbose else rep.problems[:20]
        lines += [f"  {p}" for p in shown]
        if len(shown) < len(rep.problems):
            lines.append(f"  ... {len(rep.problems) - len(shown)} more (use -v)")
    return "\n".join(lines)
