"""Generate a fast-text strings mod from the client's own dumps.

The point of a generator rather than a hand-kept corpus: the text comes from
*your* client, so nothing of anyone else's is redistributed, the same rules
produce every language, and after a client patch you re-run instead of
hand-fixing hundreds of ids.

Three container shapes come out of `Settings > Utilities`:

  dump_strings_<lang>.xml   <strings lang="..">          id="..."
  dump_BPR_en.xml etc.      <strings lang="en">          id="..."   (GBA regions)
  dump_CPU_0_en.xml etc.    <ds_strings_archive ...>     block/entry/table (NDS)

GBA storyline and UI entries share the plain-id shape, so they merge into one
file per language. NDS archives need one file per (archive_type, region_id).

Addressing is not interchangeable between the two. A plain entry has a globally
unique id; an NDS entry is a (table, entry) coordinate that means something
different in every archive. `dump_IRB_0_en.xml` table 15 entry 45 is "Player
beat {00} {01}"; the same coordinate in `dump_IRB_1_en.xml` is the menu label
"Game Sync". Every NDS address therefore carries the archive it belongs to.
"""
from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET

# What a silenced entry is replaced with.
#
# SKIP is an argument placeholder, and the whole trick is that nothing ever
# fills slot 9 in the tables this mod touches, so the message resolves to
# nothing and the client skips its box instead of drawing it. BLANK is two
# escaped newlines: a box that renders empty and still costs a tap.
#
# That difference is the point of this mod. Replacing a run of consecutive
# messages -- the end of a battle, a Pokecenter visit -- with BLANK does not
# make them go away, it makes them unreadable and just as many taps.
#
# The NDS archives are the same story once you look at the right place. Slot 9
# is filled 42 times in Sinnoh and twice in Unova, but never inside the message
# families this mod silences: the widest argument any of them uses is slot 5
# (table 8), 4 (table 15), 2 (tables 14 and 157) and 1 (table 172). The client
# also ships bare `{09}` entries of its own -- Unova table 208 entry 89, Sinnoh
# tables 354 and 671 -- so an empty message written that way is the client's own
# idiom, not an invention of this mod.
SKIP = "{09}"
BLANK = "\\n\\n"
# An override with no text at all. Kept because rules.json can name it, but it
# does NOT silence anything: confirmed on hardware 2026-08-30, the client reads
# an empty element as "no override" and its own text comes back. Use
# `"enabled": false` to say that on purpose -- it is the same result and it
# reads like what it means.
NONE = ""
AUTO = "auto"           # SKIP, unless the rule names another token


@dataclass(frozen=True)
class Entry:
    """One string out of a dump, with everything a rule needs to address it.

    `sid` is set for the plain-id containers and None for the NDS archives;
    `archive`, `table`, `entry` and `block` are the other way round. Nothing
    carries both, which is what keeps a GBA id from matching an NDS coordinate
    that happens to share its number.
    """
    text: str = ""
    sid: str | None = None
    archive: tuple | None = None      # (archive_type, region_id)
    table: str | None = None
    entry: str | None = None
    block: str | None = None

    @property
    def ds_key(self) -> tuple:
        return (self.block, self.entry, self.table)


@dataclass
class Guards:
    """The global vetoes. None of them apply to an address listed by hand: that
    is a decision already made.

    `patterns` are `never` and `never_label` -- text that is read on purpose.

    `ds_tables` are (archive_type, region_id, table) triples belonging to the
    NDS battle engine. A box drawn there cannot be removed by anything the
    strings side has, so silencing one trades a readable line for an empty box
    that costs the same tap and drags the battle out. Patterns written for the
    GBA tables reach them by accident -- `catch-flow` matched Unova 15/65 and
    `evolution` matched all of table 172 -- which is the whole reason this guard
    exists.
    """
    patterns: list = field(default_factory=list)
    ds_tables: set = field(default_factory=set)

    def vetoes(self, e) -> bool:
        if e.sid is None and e.archive is not None \
                and (e.archive[0], e.archive[1], e.table) in self.ds_tables:
            return True
        return any(g.search(e.text) for g in self.patterns)


@dataclass
class Rule:
    name: str
    match: str = ""
    note: str = ""
    exclude: str = ""
    ids: list = field(default_factory=list)
    exclude_ids: list = field(default_factory=list)
    id_match: str = ""
    tables: list = field(default_factory=list)
    archives: list = field(default_factory=list)
    ds_ids: list = field(default_factory=list)
    plain_only: bool = False
    max_len: int = 0
    replace: str = AUTO
    enabled: bool = True
    _rx: object = field(default=None, repr=False)
    _ex: object = field(default=None, repr=False)
    _ids: object = field(default=None, repr=False)
    _idrx: object = field(default=None, repr=False)
    _ds: object = field(default=None, repr=False)
    _arch: object = field(default=None, repr=False)

    def rx(self):
        if self._rx is None:
            # An empty match must never match; re.compile("") matches everything.
            self._rx = re.compile(self.match, re.S) if self.match else None
        return self._rx

    def id_set(self) -> set:
        if self._ids is None:
            self._ids = {str(i) for i in self.ids}
        return self._ids

    def ds_id_set(self) -> set:
        """Hand-picked NDS addresses as (block, entry, table) strings.

        Written in rules.json as `[table, entry]`, or `[table, entry, block]`
        on the day an archive turns up with more than one block. Table first
        because that is how the message families are named -- "table 15 is the
        battle results table" -- and because it is how the client's own dump
        groups them.
        """
        if self._ds is None:
            out = set()
            for a in self.ds_ids:
                table, entry = str(a[0]), str(a[1])
                block = str(a[2]) if len(a) > 2 else "0"
                out.add((block, entry, table))
            self._ds = out
        return self._ds

    def archive_set(self) -> set:
        if self._arch is None:
            self._arch = {(str(t), str(r)) for t, r in self.archives}
        return self._arch

    def in_archive(self, archive: tuple | None) -> bool:
        """A rule with `archives` never leaves those NDS archives.

        Without it, `tables: [15]` would also silence table 15 of every other
        archive, and those hold unrelated text -- menu labels, in the Unova-1
        case. A rule with no `archives` is unrestricted, which is what the
        plain-id rules want.
        """
        return not self.archives or (archive is not None
                                     and archive in self.archive_set())

    def in_family(self, e: Entry) -> bool:
        """Pins a *pattern* to one message family: `id_match`, a regex matched
        against the whole id, for the GBA/UI tables; `tables` for the NDS
        archives, which address by table id instead.

        Battle messages are built from the same {00}/{0F} placeholders as
        ordinary NPC lines, so a pattern written for battle spam will happily
        silence "A TRAINER named {02} is visiting my home." unless it is told
        where to look.
        """
        if not self.id_match and not self.tables:
            return True
        if e.sid is not None:
            if self._idrx is None:
                self._idrx = re.compile(self.id_match or r"(?!)")
            return bool(self._idrx.fullmatch(e.sid))
        return e.table is not None and e.table in {str(t) for t in self.tables}

    def by_hand(self, e: Entry) -> bool:
        """True when this exact entry is listed by hand, plain or NDS.

        A hand-picked address is a decision already made: it beats `exclude`,
        the length cap and both global guards.
        """
        if e.sid is not None:
            return e.sid in self.id_set()
        return bool(self.ds_ids) and self.in_archive(e.archive) \
            and e.ds_key in self.ds_id_set()

    def hits(self, e: Entry) -> bool:
        if self.by_hand(e):
            return True
        # A rule written for the GBA ids has no business in the NDS archives.
        # The families that matter there -- catching, evolving, learning a move
        # -- are state machines, and a pattern cannot tell the tutor's copy of
        # "{00} learned {01}!" from the battle engine's. Blanking the wrong one
        # hangs the game; that is not hypothetical, it happened on 2026-08-30.
        # Where the NDS equivalent is worth silencing it is hand-picked, with
        # evidence, in its own rule.
        if self.plain_only and e.sid is None:
            return False
        # The escape hatch for the handful of NPCs who describe an interaction
        # in flavour text using the same words the counter itself uses.
        if e.sid is not None and e.sid in {str(i) for i in self.exclude_ids}:
            return False
        if not self.in_archive(e.archive) or not self.in_family(e):
            return False
        if self.max_len and len(e.text) > self.max_len:
            return False
        rx = self.rx()
        return bool(rx and rx.search(e.text))

    def excluded(self, text: str) -> bool:
        if not self.exclude:
            return False
        if self._ex is None:
            self._ex = re.compile(self.exclude, re.S)
        return bool(self._ex.search(text))

    def token(self) -> str:
        return SKIP if self.replace == AUTO else self.replace


def load_rules(path: Path) -> tuple[list[Rule], Guards]:
    """Returns (rules, guards).

    They exist so one careless rule cannot wipe out text nobody mashes through.
    `never` covers item and move descriptions, which you read on purpose.
    `never_label` covers UI labels -- a short entry with no sentence-ending
    punctuation is a menu entry, not a message, and silencing one blanks the
    menu rather than skipping a box.

    Neither applies to an address listed by hand: that is a decision already
    made.
    """
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if "blank_archives" in raw:
        # Removed in 1.3. It forced one replacement token across a whole
        # archive, and the archive it named holds both kinds: the reference mod
        # skips the field-move entries and blanks the EXP ones in the same file.
        # A rule's own `replace` says which, per message family.
        raise ValueError("blank_archives was removed; set `replace` on the rule "
                         "that wants a blank line instead")
    tokens = {"skip": SKIP, "blank": BLANK, "none": NONE, "auto": AUTO}
    rules = []
    for r in raw["rules"]:
        if not r.get("enabled", True):
            continue
        kw = {k: v for k, v in r.items() if not k.startswith("_")}
        raw_rep = kw.get("replace", AUTO)
        kw["replace"] = tokens[raw_rep] if raw_rep in tokens else raw_rep
        name = kw.get("name")
        if not kw.get("match") and not kw.get("ids") and not kw.get("ds_ids"):
            raise ValueError(f"rule {name!r} has neither match nor ids nor ds_ids")
        if kw.get("ds_ids") and not kw.get("archives"):
            # (table, entry) means something different in every archive, so an
            # unscoped NDS address is not an address at all.
            raise ValueError(f"rule {name!r} has ds_ids but no archives to scope them")
        if kw.get("tables") and not kw.get("archives"):
            raise ValueError(f"rule {name!r} has tables but no archives to scope them")
        if kw.get("plain_only") and (kw.get("archives") or kw.get("ds_ids")):
            raise ValueError(f"rule {name!r} is plain_only but also addresses NDS archives")
        for a in kw.get("ds_ids", []):
            if not 2 <= len(a) <= 3:
                raise ValueError(f"rule {name!r}: ds_ids entry {a!r} is not "
                                 "[table, entry] or [table, entry, block]")
        rules.append(Rule(**kw))
    guards = Guards(
        patterns=[re.compile(raw[k], re.S)
                  for k in ("never", "never_label") if raw.get(k)],
        ds_tables={(str(a), str(r), str(t))
                   for a, r, t in raw.get("never_ds_tables", [])})
    return rules, guards


def _entries(root: ET.Element):
    if root.tag == "ds_strings_archive":
        archive = (root.get("archive_type", "0"), root.get("region_id", "0"))
        for el in root.findall("string"):
            yield Entry(text=el.text or "", archive=archive,
                        table=el.get("table_id"), entry=el.get("entry_id"),
                        block=el.get("block_id"))
    else:
        for el in root.findall("string"):
            yield Entry(text=el.text or "", sid=el.get("id"))


def scan(dumps: Path, rules: list[Rule], guards=None) -> tuple[dict, dict, dict]:
    """Return (plain_hits, ds_hits, per_rule_counts).

    Each hit maps to (rule_name, replacement) so one rule can skip a box outright
    while another leaves an empty one behind.
    """
    guards = guards or Guards()
    plain: dict[str, tuple] = {}
    ds: dict[tuple, dict] = {}
    counts: dict[str, int] = {r.name: 0 for r in rules}
    counts["_guarded"] = 0
    for f in sorted(Path(dumps).glob("dump_*.xml")):
        try:
            root = ET.parse(f).getroot()
        except ET.ParseError:
            continue
        for e in _entries(root):
            for rule in rules:
                by_hand = rule.by_hand(e)
                if not by_hand and not rule.hits(e):
                    continue
                # The guards exist to stop a careless *pattern* wiping out text
                # that is read on purpose. An address listed by hand is a
                # decision already made, so it is not second-guessed here.
                if not by_hand and (rule.excluded(e.text) or guards.vetoes(e)):
                    counts["_guarded"] += 1
                    break
                if e.sid is not None:
                    if e.sid not in plain:
                        plain[e.sid] = (rule.name, rule.token())
                        counts[rule.name] += 1
                elif all(e.ds_key):
                    hits = ds.setdefault(e.archive, {})
                    if e.ds_key not in hits:
                        hits[e.ds_key] = (rule.name, rule.token())
                        counts[rule.name] += 1
                break
    return plain, ds, counts


def _header(comment: str) -> str:
    # XML forbids "--" inside a comment and the client's pull parser enforces it
    # strictly: one stray double dash in a rule note and the whole mod is
    # rejected with "Comments may not contain --".
    safe = re.sub(r"-{2,}", "-", comment)
    return f'<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n<!--\n{safe}\n-->\n'


def write_mod(out: Path, plain: dict, ds: dict, langs: list[str],
              rules: list[Rule], lang_names: dict) -> list[str]:
    # Deliberately not data/strings/: anything a mod ships under data/ is a
    # directory overlay to the client, and it logs the undeclared form as
    # deprecated even when info.xml lists every file. The reference mods ship
    # their strings outside data/ for the same reason.
    strings_dir = Path(out) / "strings"
    strings_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    summary = "\n".join(f"    {r.name}: {r.note or r.match}" for r in rules)
    head = "  Generated by `pmmod strings fasttext` from this client's own\n" \
           "  Settings > Utilities dumps.\n\n"
    why = (f"  Entries here are replaced with {SKIP}, an argument slot nothing\n"
           "  fills in the tables this mod touches, so the message resolves to\n"
           "  nothing and the client skips its box instead of drawing an empty\n"
           "  one. A rule that wants a visible beat asks for a blank line by\n"
           "  name; those entries render an empty box you still dismiss.\n\n")
    comment = head + why + "  Rules applied:\n" + summary

    for lang in langs:
        body = "\n".join(f'  <string id="{i}">{plain[i][1]}</string>'
                         for i in sorted(plain, key=int))
        f = strings_dir / f"strings_{lang}_fasttext.xml"
        f.write_text(_header(comment) +
                     f'<strings lang="{lang}" lang_full="{lang_names.get(lang, lang)}" '
                     f'is_primary="0">\n{body}\n</strings>\n', encoding="utf-8")
        written.append(f"strings/{f.name}")

    # NDS storyline is English in every client, so one copy covers all players.
    for (atype, region), hits in sorted(ds.items()):
        body = "\n".join(
            f'  <string block_id="{b}" entry_id="{e}" table_id="{t}">'
            f'{hits[(b, e, t)][1]}</string>'
            for (b, e, t) in sorted(hits, key=lambda k: tuple(int(x) for x in k)))
        f = strings_dir / f"ds_fasttext_{atype}_{region}.xml"
        f.write_text(_header(comment) +
                     f'<ds_strings_archive archive_type="{atype}" lang="en" '
                     f'region_id="{region}" is_primary="0">\n{body}\n</ds_strings_archive>\n',
                     encoding="utf-8")
        written.append(f"strings/{f.name}")
    return written


def write_info(out: Path, files: list[str], name: str, version: str,
               author: str, description: str, weblink: str,
               string_revision: int = 1) -> None:
    def esc(s: str) -> str:
        return html.escape(s, quote=True).replace("\n", "&#10;")

    entries = "\n".join(f'        <string path="{p}"/>' for p in files)
    (Path(out) / "info.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<resource name="{esc(name)}" version="{esc(version)}" '
        f'description="{esc(description)}" author="{esc(author)}" '
        f'weblink="{esc(weblink)}">\n'
        f'    <strings string_revision="{string_revision}">\n{entries}\n'
        '    </strings>\n</resource>\n', encoding="utf-8")
