"""Cross-region comparison of the whole corpus, not one table family.

PokeMMO ships the same game text five times over. Kanto and Hoenn carry it as
plain ids; Sinnoh, Johto and the two Unova archives carry it as NDS
(table, entry) coordinates. The wording drifts a little between them -- a line
wraps at a different word, a full stop becomes an exclamation mark -- but the
message is the same message.

That redundancy is an oracle no external mod can give you. If a line is silenced
in Johto and drawing in Sinnoh, one of the two is wrong, and no comparison
against SupersSpeedStrings will say so: the reference has its own holes in its
own places. `pmmod.fieldmoves` applies this to the three copies of the
field-move script. This module applies it to all 166,867 entries.

Most disagreements are not bugs, and saying which is the whole job:

  battle-engine  the twin sits in a table the NDS battle engine draws. Silencing
                 it leaves an empty box that costs the same tap -- settled on
                 hardware, see `never_ds_tables`.
  read-on-purpose  a `never` / `never_label` guard holds it: item and move
                 descriptions, and menu labels.
  plain-only     the rule that silenced the twin is `plain_only`, so it is
                 forbidden from reaching the NDS archives on purpose. The
                 families that matter there are state machines and a pattern
                 cannot tell the tutor's copy of a line from the engine's.
  capped         the twin is longer than the rule's `max_len`, which is how the
                 prose rules keep out of story dialogue.

What is left over is a real disagreement with no recorded reason, and that is
what `gaps()` returns.
"""
from __future__ import annotations

import re
from pathlib import Path
from xml.etree import ElementTree as ET

from pmmod import fasttext

# region label -> how to recognise it. NDS archives are keyed by the
# (archive_type, region_id) the client stamps on the file.
DS_REGIONS = {
    ("0", "2"): "Unova",        # dump_IRB_0 -- battle and field text, every region
    ("1", "2"): "Unova-1",      # dump_IRB_1 -- Unova storyline and its counters
    ("0", "3"): "Sinnoh",       # dump_CPU_0
    ("0", "4"): "Johto",        # dump_IPK_0
}
PLAIN_REGIONS = {
    "dump_BPR_en.xml": "Kanto",
    "dump_BPE_en.xml": "Hoenn",
    "dump_strings_en.xml": "UI",
    "dump_strings_es.xml": "UI-es",
}

# A location's verdict when it is not silenced but its twin is.
BATTLE_ENGINE = "battle-engine"
READ_ON_PURPOSE = "read-on-purpose"
PLAIN_ONLY = "plain-only"
CAPPED = "capped"
UNEXPLAINED = "unexplained"


class Loc:
    """One place a line appears, and what this mod does about it."""

    __slots__ = ("region", "address", "silenced", "rule", "text",
                 "archive", "table", "sid")

    def __init__(self, region, address, text, archive=None, table=None, sid=None):
        self.region = region
        self.address = address
        self.text = text
        self.archive = archive
        self.table = table
        self.sid = sid
        self.silenced = False
        self.rule = None

    def __repr__(self):
        state = f"silenced by {self.rule}" if self.silenced else "draws"
        return f"<{self.region} {self.address} {state}>"


def normalise(text: str) -> str:
    """Collapse the differences that are only wrapping, case or final punctuation.

    The same sentence is wrapped at a different word in every archive, so
    comparing raw text finds almost no twins at all. Placeholders are left
    alone: `{00}` and `{01}` are not interchangeable and a line that swaps them
    is a different line.
    """
    text = text.replace("\\n", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text.rstrip(" .!?…")


def load(dumps: Path) -> list:
    """Every entry in the corpus as a Loc, with the region it came from."""
    out = []
    for f in sorted(Path(dumps).glob("dump_*.xml")):
        try:
            root = ET.parse(f).getroot()
        except ET.ParseError:
            continue
        if root.tag == "ds_strings_archive":
            archive = (root.get("archive_type", "0"), root.get("region_id", "0"))
            region = DS_REGIONS.get(archive, f"ds{archive}")
            for el in root.findall("string"):
                block, entry, table = (el.get("block_id"), el.get("entry_id"),
                                       el.get("table_id"))
                out.append(Loc(region, f"{table}/{entry}", el.text or "",
                               archive=archive, table=table))
        else:
            region = PLAIN_REGIONS.get(f.name, f.name)
            for el in root.findall("string"):
                sid = el.get("id")
                if sid:
                    out.append(Loc(region, sid, el.text or "", sid=sid))
    return out


def annotate(locs: list, plain: dict, ds: dict) -> None:
    """Mark which Locs this mod silences, from `fasttext.scan`'s own output.

    Flattened first: the corpus is 188,195 locations and walking the scan result
    per location turned a two-second job into minutes.
    """
    flat = {}
    for archive, hits in ds.items():
        for (block, entry, table), hit in hits.items():
            flat[(archive, f"{table}/{entry}")] = hit
    for loc in locs:
        hit = (plain.get(loc.sid) if loc.sid is not None
               else flat.get((loc.archive, loc.address)))
        if hit:
            loc.silenced, loc.rule = True, hit[0]


def explain(loc: Loc, silencer: Loc, rules: dict, guards) -> str:
    """Why this location is not silenced although its twin is."""
    if loc.archive is not None and \
            (loc.archive[0], loc.archive[1], loc.table) in guards.ds_tables:
        return BATTLE_ENGINE
    if any(g.search(loc.text) for g in guards.patterns):
        return READ_ON_PURPOSE
    rule = rules.get(silencer.rule)
    if rule is not None:
        if rule.plain_only and loc.sid is None:
            return PLAIN_ONLY
        if rule.max_len and len(loc.text) > rule.max_len:
            return CAPPED
    return UNEXPLAINED


def compare(dumps: Path, rules_path: Path) -> dict:
    """Group the whole corpus by text and diff each group against itself.

    Returns {normalised text: [Loc, ...]} for every line this mod silences in
    one place and leaves drawing in another.
    """
    rules, guards = fasttext.load_rules(rules_path)
    plain, ds, _ = fasttext.scan(dumps, rules, guards)
    locs = load(dumps)
    annotate(locs, plain, ds)

    groups: dict = {}
    for loc in locs:
        if loc.text.strip():
            groups.setdefault(normalise(loc.text), []).append(loc)

    by_name = {r.name: r for r in rules}
    split = {}
    for key, hits in groups.items():
        silent = [h for h in hits if h.silenced]
        drawing = [h for h in hits if not h.silenced]
        if not silent or not drawing:
            continue
        # One region can hold the same line twice; only a disagreement that
        # crosses regions says anything.
        if {h.region for h in silent} == {h.region for h in drawing} \
                and len({h.region for h in hits}) == 1:
            continue
        split[key] = (silent, drawing,
                      {id(d): explain(d, silent[0], by_name, guards)
                       for d in drawing})
    return split


def gaps(split: dict) -> dict:
    """Only the disagreements with no recorded reason."""
    out = {}
    for key, (silent, drawing, why) in split.items():
        unexplained = [d for d in drawing if why[id(d)] == UNEXPLAINED]
        if unexplained:
            out[key] = (silent, unexplained)
    return out


def report(dumps: Path, rules_path: Path) -> str:
    """Human-readable version of `compare`, grouped by what explains each miss."""
    split = compare(dumps, rules_path)
    lines, bad = [], gaps(split)
    if bad:
        lines.append("GAPS -- silenced in one region, still drawing in another:\n")
        for key, (silent, drawing) in sorted(bad.items()):
            lines.append(f"  {silent[0].text[:72]!r}")
            lines.append("      silenced: " + ", ".join(
                sorted({f"{s.region} {s.address}" for s in silent})[:6]))
            for d in sorted(drawing, key=lambda d: (d.region, d.address)):
                lines.append(f"      DRAWS     {d.region:8} {d.address}")
            lines.append("")
    counts = {}
    for _, (_, _, why) in split.items():
        for verdict in why.values():
            counts[verdict] = counts.get(verdict, 0) + 1
    explained = ", ".join(f"{v} {k}" for k, v in sorted(counts.items())
                          if k != UNEXPLAINED) or "none"
    lines.append(f"{len(bad)} unexplained line(s). Explained: {explained}.")
    return "\n".join(lines)
