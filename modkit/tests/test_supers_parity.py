"""Parity against SupersSpeedStrings, the mod this one is measured against.

SupersSpeedStrings removes NPC text wholesale -- its own description says so.
This mod only removes the interactions you repeat, so full parity is not the
goal and never was. What these tests pin down is the part where the two mods
*do* claim the same thing: the counters, the field moves, the battle flow.

Until 1.3 the comparison only ever read the plain-id sections, so the "100%
parity" figure never covered the NDS archives -- which is exactly where the
live client reads its battle and field text. These now compare both address
spaces, and record the two places the mods deliberately disagree.

They read MODEXAMPLES/SupersSpeedStrings-*.mod, a local reference copy that is
not redistributed, and skip when it is absent.
"""
import re
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from pmmod import fasttext
from pmmod.fasttext import BLANK, NONE, SKIP

ROOT = Path(__file__).resolve().parents[2]
DUMPS = ROOT / "strings-work" / "dumps"
RULES = ROOT / "strings-work" / "rules.json"
REFS = sorted((ROOT / "MODEXAMPLES").glob("SupersSpeedStrings-*.mod"))

UNOVA = ("0", "2")
SINNOH = ("0", "3")
JOHTO = ("0", "4")

# Supers' own section comments, kept verbatim. Sections whose text is an
# interaction you repeat -- these we must match.
# The Johto archive names its sections differently from every other file in the
# reference -- "HM CUT" rather than "HMs in Johto", "Healing from NJ" rather than
# "Pokemon Center" -- so a regex written for the plain-id sections silently
# scored that whole archive as out of scope. Those spellings are included here.
#
# This is a whitelist, and its gaps are the real risk in this file: a family the
# regex does not name scores as out of scope, so the suite reports parity while
# the reference silences something this mod does not. Four families hid there
# until 2026-09-01 -- the rest house that heals ("Old Lady in house who heals
# HP"), the Great Marsh interior ("inside Marsh"), the Safari PA ("PA
# Announcement") and the inter-region ferry ("Pirate"). None of them shares a
# word with anything above, all four are interactions you repeat, and the mod
# now covers all four. When adding a rule, add the reference's spelling of its
# section here too, or the next reader is told the gap does not exist.
IN_SCOPE = re.compile(
    r"Pok[eé]mon Center|Nurse|Pokemart|Shop Npc|clerk|Clerk|Fossil reviver"
    r"|Move Maniac|Move Master|Move tutor|Daycare|DayCare|Day Care|Berry Farming"
    r"|Stylist|Door Guard|Safari|Battle Factory|HMs in"
    r"|^HM |Healing from|Thanks for waiting|^Waiting|^Come back$|Herb shop"
    r"|barber shop|breeders|Apricorn|Ball Made$"
    # `\bMarsh\b` and not `Marsh`: the reference has a Marshal, and the loose
    # spelling pulled his Elite Four dialogue into scope by accident.
    r"|who heals|heals HP|\bMarsh\b|Quick Tram|PA Announcement|Pirate|Ferry", re.I)

# Sections that are story, event or one-off dialogue. Supers silences them
# because it is a "NPC text removed" build; this mod deliberately does not.
# Anything matching IN_SCOPE and listed here is a considered exception.
DELIBERATE_EXCEPTIONS = {
    # a Yes/No where the two options lead to different places
    "16779022": "Do you want to relearn or forget a move?",
    "16779034": "Do you want to relearn or forget another move?",
    "16779031": "OK. Which move should {00} forget?",
    "16779082": "You won't get these back. Are you sure? -- destroys Pokemon",
    "16780172": "It'll cost $x for your makeover. -- the number is the message",
    "16779043": "I need {00} Battle Points to teach that. Is that OK? -- price",
}

# The NDS addresses SupersSpeedStrings silences and this mod deliberately does
# not, keyed by (archive, (block, entry, table)).
DS_DELIBERATE_EXCEPTIONS = {
    (UNOVA, ("0", "32", "157")):
        "{00} wants to learn {01}, however it knows four moves -- the reference "
        "blanks it, which leaves an unlabelled Yes/No on a choice that costs you "
        "a move. The one place the two mods disagree in the battle engine.",
    (JOHTO, ("0", "16", "211")):
        "Surf can't be used if you have someone with you. -- an error; it "
        "explains why the move did nothing",
    (JOHTO, ("0", "23", "211")):
        "Rock Climb can't be used if you have someone with you. -- an error",
    (SINNOH, ("0", "9", "136")):
        "You still have time left. Are you sure you want to exit the Great "
        "Marsh? -- ending a Safari run early is a decision",
}

# Where the two mods write a different token at the same address. Supers blanks
# these, which still draws a box you dismiss; this mod skips them outright.
# Nothing fills argument slot 9 in tables 15 or 157 -- the widest either uses is
# slot 4 -- and the client ships bare {09} entries of its own in this archive
# (table 208 entry 89), so the skip token is the client's own idiom here.
# The battle-engine addresses the reference blanks and this mod blanks too, with
# the same token. Reached after {09} was tried there and made the end of a fight
# drag: the two are not interchangeable, and the reference is the only evidence
# that survives contact with hardware.
DS_BLANKED_LIKE_THE_REFERENCE = {
    ("0", "42", "15"): "{00} gained {01} Exp. Points!",
    ("0", "43", "15"): "{00} gained a boosted {01} Exp. Points!",
    ("0", "38", "157"): "{00} did not learn {01}.",
    ("0", "40", "157"): "1, 2, and... Ta-da! {00} forgot how to use {01}.",
    ("0", "41", "157"): "{00} learned {01}!",
}


def _is_silencing(value: str) -> bool:
    return value == SKIP or not value.strip() or set(value) <= set("\\n \n")


def silenced_in(mod: Path) -> tuple[dict, dict]:
    """Return (plain, ds) for the reference mod.

    plain: id -> (section comment, replacement token)
    ds:    (archive_type, region_id) -> (block, entry, table) -> (section, token)
    """
    plain: dict = {}
    ds: dict = {}
    with zipfile.ZipFile(mod) as z:
        for name in z.namelist():
            if not name.lower().endswith(".xml") or "info" in name.lower():
                continue
            text = z.read(name).decode("utf-8", "replace")
            archive = None
            m = re.search(r'<ds_strings_archive[^>]*>', text)
            if m:
                archive = (re.search(r'archive_type="(\d+)"', m.group(0)).group(1),
                           re.search(r'region_id="(\d+)"', m.group(0)).group(1))
            section = "(none)"
            for line in text.splitlines():
                c = re.search(r"<!--\s*(?!=)(.+?)\s*-->", line)
                if c and "<string" not in line:
                    section = c.group(1)
                    continue
                e = re.search(r'<string ([^>]*)>(.*?)</string>', line)
                if not e or not _is_silencing(e.group(2)):
                    continue
                attrs, value = e.group(1), e.group(2)
                coord = [re.search(f'{k}="(\\d+)"', attrs)
                         for k in ("block_id", "entry_id", "table_id")]
                if archive is None or not all(coord):
                    # The reference's Johto archive carries one stray plain-id
                    # line, `<string id="16777274">`, which the NDS container
                    # cannot address. Read it as what it is rather than
                    # crashing on it.
                    sid = re.search(r'(?<![a-z_])id="(\d+)"', attrs)
                    if sid:
                        plain[sid.group(1)] = (section, value)
                    continue
                ds.setdefault(archive, {})[tuple(m.group(1) for m in coord)] = (section, value)
    return plain, ds


@unittest.skipUnless(REFS and DUMPS.is_dir(), "no SupersSpeedStrings reference here")
class TestParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.theirs, cls.their_ds = silenced_in(REFS[-1])
        rules, guards = fasttext.load_rules(RULES)
        cls.plain, cls.ds, _ = fasttext.scan(DUMPS, rules, guards)
        from tests.test_corpus import load_dumps, load_ds_dumps
        cls.text = load_dumps()
        cls.ds_text = load_ds_dumps()

    # -- plain ids ---------------------------------------------------------
    def test_we_cover_every_repeated_interaction_supers_covers(self):
        missing = {}
        for sid, (section, _) in self.theirs.items():
            if not IN_SCOPE.search(section) or sid in DELIBERATE_EXCEPTIONS:
                continue
            if sid not in self.text or sid in self.plain:
                continue
            missing[sid] = f"{section}: {self.text[sid][:60]}"
        self.assertEqual(missing, {},
                         "SupersSpeedStrings silences these repeated-interaction "
                         "lines and this mod does not")

    def test_every_deliberate_exception_is_still_a_real_entry(self):
        for sid, why in DELIBERATE_EXCEPTIONS.items():
            with self.subTest(id=sid, reason=why):
                self.assertIn(sid, self.text)
                self.assertNotIn(sid, self.plain, "exception is being silenced anyway")

    def test_we_do_not_silence_story_dialogue_supers_removes(self):
        # Supers is a "NPC text removed" build. If this mod ever matched most of
        # what it strips, it has stopped being a speed mod.
        story = [s for s, (sec, _) in self.theirs.items() if not IN_SCOPE.search(sec)]
        overlap = [s for s in story if s in self.plain]
        self.assertLess(len(overlap), len(story) * 0.2,
                        f"{len(overlap)} of {len(story)} story lines silenced; "
                        "a rule has grown past its scope")

    # -- the NDS archives --------------------------------------------------
    def test_the_reference_actually_edits_the_nds_archives(self):
        """Guards the rest of this file. If the reference stops shipping NDS
        overrides, the comparisons below would pass vacuously."""
        self.assertIn(UNOVA, self.their_ds)
        self.assertTrue(self.their_ds[UNOVA])

    def test_we_cover_every_repeated_nds_interaction_supers_covers(self):
        """The comparison that was missing until 1.3.

        Same in-scope filter as the plain ids, on the reference's own section
        comments: the NDS files are where it strips Gym Leader introductions,
        Elite Four speeches and the Team Galactic cutscenes, none of which this
        mod touches. What is left is the counters, the HM prompts and the field
        moves, and a miss there is a message the player still taps through.
        """
        missing = {}
        for archive, hits in self.their_ds.items():
            for trip, (section, _) in hits.items():
                if not IN_SCOPE.search(section):
                    continue
                if (archive, trip) in DS_DELIBERATE_EXCEPTIONS:
                    continue
                if (archive, trip) not in self.ds_text:
                    continue        # an archive this client did not dump
                if trip in self.ds.get(archive, {}):
                    continue
                missing[f"{archive}{trip}"] = \
                    f"{section}: {self.ds_text[(archive, trip)][:60]}"
        self.assertEqual(missing, {},
                         "SupersSpeedStrings silences these repeated-interaction "
                         "NDS entries and this mod does not")

    def test_every_nds_exception_is_still_a_real_entry_and_still_visible(self):
        for (archive, trip), why in DS_DELIBERATE_EXCEPTIONS.items():
            with self.subTest(archive=archive, addr=trip, reason=why):
                self.assertIn((archive, trip), self.ds_text)
                self.assertIn(trip, self.their_ds[archive],
                              "the reference no longer silences this; the "
                              "exception has nothing to except")
                self.assertNotIn(trip, self.ds.get(archive, {}),
                                 "exception is being silenced anyway")

    def test_we_do_not_silence_the_nds_story_dialogue_supers_removes(self):
        story = [(a, t) for a, hits in self.their_ds.items()
                 for t, (sec, _) in hits.items() if not IN_SCOPE.search(sec)]
        overlap = [(a, t) for a, t in story if t in self.ds.get(a, {})]
        self.assertLess(len(overlap), len(story) * 0.2,
                        f"{len(overlap)} of {len(story)} NDS story entries "
                        "silenced; a rule has grown past its scope")

    def test_the_field_move_entries_prove_the_skip_token_works_in_an_archive(self):
        """The only hard evidence that {09} is safe inside an NDS archive.

        SupersSpeedStrings is run by thousands of people and writes {09} at
        exactly these two addresses. Both mods silence them; if the reference
        ever changes its mind, this mod's whole NDS strategy needs rechecking.
        """
        for trip in (("0", "52", "8"), ("0", "53", "8")):
            with self.subTest(addr=trip):
                self.assertEqual(self.their_ds[UNOVA][trip][1], SKIP,
                                 "the reference no longer skips the field-move "
                                 "entries; the {09} evidence is gone")
                self.assertEqual(self.ds[UNOVA].get(trip), ("field-moves-ds", SKIP))

    def test_the_reference_mixes_both_tokens_inside_one_archive(self):
        """Why `blank_archives` was removed in 1.3.

        It forced one replacement token across a whole archive. The reference
        writes {09} at table 8 and a blank line at table 15 in the same file, so
        no per-archive setting can describe even the mod it was copied from. The
        choice belongs to the message family, which is a rule's own `replace`.
        """
        tokens = {v for _, v in self.their_ds[UNOVA].values()}
        self.assertIn(SKIP, tokens)
        self.assertIn(BLANK, tokens)


    def test_we_blank_the_battle_engine_exactly_where_the_reference_does(self):
        """The token matters as much as the address.

        {09} and a blank line are not interchangeable here: {09} is an argument
        the battle engine never resolves and it left a box that dragged the end
        of the fight out. The reference has written a blank at these addresses
        for years. If it ever stops, or this mod drifts back to {09}, that is a
        regression and this fails.
        """
        for trip, why in DS_BLANKED_LIKE_THE_REFERENCE.items():
            with self.subTest(addr=trip, text=why):
                self.assertEqual(self.their_ds[UNOVA][trip][1], BLANK)
                self.assertIn(trip, self.ds.get(UNOVA, {}),
                              "this mod stopped covering an EXP / move-learn line")
                self.assertEqual(self.ds[UNOVA][trip][1], BLANK)

    def test_the_field_moves_are_where_both_mods_agree(self):
        """The one NDS call site where {09} genuinely removes the box. Both mods
        write it, and it is the whole reason this one works at all."""
        for trip in (("0", "52", "8"), ("0", "53", "8")):
            with self.subTest(addr=trip):
                self.assertEqual(self.their_ds[UNOVA][trip][1], SKIP)
                self.assertEqual(self.ds[UNOVA][trip], ("field-moves-ds", SKIP))


if __name__ == "__main__":
    unittest.main()
