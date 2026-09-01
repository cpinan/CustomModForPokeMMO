"""Cross-check the field-move tables against each other.

Every region ships the same field-move script in its own NDS archive: Unova-1
table 280, Sinnoh 381, Johto 211. The wording is near-identical across the
three, so a line silenced in one archive and left alone in another is almost
always an oversight rather than a decision -- and the parity suite cannot see
it, because SupersSpeedStrings has the same holes in the same places.

That is how Teleport survived to 1.11. Its confirmation prompt exists only in
Johto's copy of the script, so no sibling table could shame it into coverage,
and the reference does not silence it either. Sweet Scent goes through the
generic `{00} used\\n{01}!` at Unova 8/52 and was silent from the first build,
which is what made the pair look arbitrary from inside the game.

`gaps()` reports lines covered in one archive and drawing in another.
`unpaired()` reports lines with no twin, which have to be read by a person.
"""
from __future__ import annotations

import re
from pathlib import Path

# (archive_type, region_id) -> the table holding that region's field-move script.
TABLES = {
    ("1", "2"): "280",      # Unova storyline archive -- what the live client reads
    ("0", "3"): "381",      # Sinnoh
    ("0", "4"): "211",      # Johto
}
NAMES = {("0", "2"): "Unova", ("0", "3"): "Sinnoh",
         ("0", "4"): "Johto", ("1", "2"): "Unova-1"}

# Left drawing on purpose, keyed by normalised text so one entry covers every
# archive's spelling. These are not gaps and must not be reported as such.
KEEP = {
    "surf can't be used if you have someone with you":
        "an error: it explains why the move did nothing",
    "rock climb can't be used if you have someone with you":
        "an error: it explains why the move did nothing",
    "{01} was in the rubble":
        "names the item you just found",
    "the boulder fell down":
        "feedback on a Strength puzzle you are still solving",
}


def normalise(text: str) -> str:
    """Collapse the differences that are only line-wrapping or final punctuation.

    The same line is wrapped at a different word in each archive -- Sinnoh says
    `deep blue color...`, Johto `deep blue...` -- so comparing raw text finds
    almost no twins at all.
    """
    text = text.replace("\\n", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", text).strip().lower().rstrip(" .!?")


def index(ds_text: dict, silenced: dict) -> dict:
    """normalised text -> {archive: (entry_id, is_silenced, raw text)}."""
    out: dict = {}
    for (archive, trip), text in ds_text.items():
        if TABLES.get(archive) != trip[2] or not text.strip():
            continue
        out.setdefault(normalise(text), {})[archive] = (
            trip[1], trip in silenced.get(archive, {}), text)
    return out


def gaps(ds_text: dict, silenced: dict) -> list:
    """Lines with a twin in another archive that disagree about being silenced."""
    found = []
    for key, hits in sorted(index(ds_text, silenced).items()):
        if len(hits) < 2 or key in KEEP:
            continue
        covered = {a for a, (_, c, _) in hits.items() if c}
        if covered and len(covered) != len(hits):
            found.append((key, hits))
    return found


def unpaired(ds_text: dict, silenced: dict) -> list:
    """Lines that exist in one archive only and are not silenced.

    No twin can vouch for them, so they are a reading task, not a test failure.
    """
    out = []
    for key, hits in sorted(index(ds_text, silenced).items()):
        if len(hits) == 1 and key not in KEEP and not next(iter(hits.values()))[1]:
            out.append((key, hits))
    return out


def report(ds_text: dict, silenced: dict) -> str:
    lines = []
    found = gaps(ds_text, silenced)
    if found:
        lines.append("GAPS -- covered in one archive, left drawing in another:\n")
        for _, hits in found:
            lines.append(f"  {next(iter(hits.values()))[2][:70]!r}")
            for a, (entry, c, _) in sorted(hits.items(), key=lambda x: NAMES[x[0]]):
                lines.append(f"      {NAMES[a]:8} {TABLES[a]}/{entry:<4} "
                             f"{'silenced' if c else 'STILL DRAWS'}")
            lines.append("")
    odd = unpaired(ds_text, silenced)
    if odd:
        lines.append("ONLY IN ONE ARCHIVE and never silenced -- read each one yourself:\n")
        for _, hits in odd:
            for a, (entry, _, text) in hits.items():
                lines.append(f"  {NAMES[a]:8} {TABLES[a]}/{entry:<4} {text[:70]!r}")
        lines.append("")
    lines.append(f"{len(found)} gap(s), {len(odd)} unpaired line(s).")
    return "\n".join(lines)
