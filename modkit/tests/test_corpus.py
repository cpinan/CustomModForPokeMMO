"""Behavioural contract for `strings-work/rules.json` against the real dumps.

Unlike test_rules.py these need the repository's dump folder, so they skip
cleanly on a checkout that does not carry it.

Two address spaces appear here and they are not interchangeable. The GBA and UI
containers give every entry a globally unique id. The NDS archives address by
(table, entry) inside one archive, and the same coordinate means something
different in the next one -- Unova table 15 entry 45 is "Player beat {00} {01}",
the Unova-1 archive's table 15 entry 45 is the menu label "Game Sync". Every NDS
expectation below therefore names its archive.

The live client reads the Unova archive for battle and field text in every
region. That is why the ds groups are the ones that decide whether this mod
works: v1.2 silenced the GBA battle tables perfectly and changed nothing on
screen.
"""
import re
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

from pmmod import fasttext
from pmmod.fasttext import BLANK, NONE, SKIP

ROOT = Path(__file__).resolve().parents[2]
DUMPS = ROOT / "strings-work" / "dumps"
RULES = ROOT / "strings-work" / "rules.json"
MOD = ROOT / "mods" / "vanbobby-fast-strings"

# The archives, by the (archive_type, region_id) the client stamps on them.
UNOVA = ("0", "2")        # dump_IRB_0_en.xml -- battle, field moves, everything
UNOVA_1 = ("1", "2")      # dump_IRB_1_en.xml -- Unova storyline and its counters
SINNOH = ("0", "3")       # dump_CPU_0_en.xml
JOHTO = ("0", "4")        # dump_IPK_0_en.xml -- see DS_JOHTO


def addr(table, entry, block=0):
    """An NDS address in the (block, entry, table) order `scan` keys on."""
    return (str(block), str(entry), str(table))


# --- the NDS battle engine: proven unsilenceable ---------------------------
# Three hardware tests on 2026-08-30 settled this. A box drawn by these tables
# cannot be removed by anything the strings side has: {09} leaves it empty, an
# empty override is read as no override at all and the client's own text comes
# back, and the corpus has no close or skip control code. An empty box costs the
# same tap as a full one, says nothing, and drags the end of a battle out -- so
# every one of these must keep its text.
DS_BATTLE_ENGINE = {
    (UNOVA, addr(14, 0)): "{00} fainted!",
    (UNOVA, addr(14, 234)): "{00} was poisoned!",
    (UNOVA, addr(14, 688)): "{00} learned {01}!  (reached by `move-learned`)",
    (UNOVA, addr(157, 32)): "{00} wants to learn {01} but knows four moves -- "
                            "blanking it leaves an unlabelled Yes/No on a choice "
                            "that costs you a move. The reference blanks it; this "
                            "is the one place the two mods disagree.",
    (UNOVA, addr(172, 0)): "What? {00} is evolving!  (reached by `evolution`)",
    (UNOVA, addr(172, 2)): "Congratulations! Your {00} evolved into {01}!",
}

# Silencing an error leaves the player holding a dead button with no reason why.
# Silencing what you read to play the turn makes the battle unplayable rather
# than fast. Neither is a speed win, so both stay whatever the token allows.
DS_ERRORS_AND_TURN_INFO = {
    (UNOVA, addr(15, 20)): "Will you switch your Pokemon? -- a decision",
    (UNOVA, addr(15, 54)): "{00} is out of usable Pokemon!",
    (UNOVA, addr(15, 55)): "{00} dropped ${01} in panic... -- losing money",
    (UNOVA, addr(15, 57)): "{00} blacked out!",
    (UNOVA, addr(15, 60)): "{00} grew to Lv. {01}!",
    (UNOVA, addr(15, 69)): "What will {00} do? -- the battle menu itself",
    (UNOVA, addr(15, 71)): "But it failed!",
    (UNOVA, addr(15, 73)): "Couldn't get away! -- the flee failed and cost a turn",
    (UNOVA, addr(15, 77)): "Would you like to forfeit the match? -- a decision",
    (UNOVA, addr(15, 78)): "It's super effective!",
    (UNOVA, addr(15, 81)): "A critical hit!",
    (UNOVA, addr(15, 82)): "But there was no PP left for the move!",
    (UNOVA, addr(157, 27)): "If the Mail is removed its message will be lost -- a decision",
    (UNOVA, addr(157, 42)): "{00} and {01} are not compatible -- an error",
    (UNOVA, addr(157, 43)): "{00} already knows {01}. -- an error",
    (UNOVA, addr(157, 56)): "This can't be used until a new Badge is obtained. -- an error",
    (UNOVA, addr(157, 58)): "{00} is already holding {01}. Switch? -- a decision",
    (UNOVA, addr(157, 63)): "The Bag is full. -- an error",
}

# The exceptions, and the only battle-engine addresses this mod touches. A blank
# line here is NOT the same as {09}: {09} is an argument placeholder the battle
# engine never resolves and it left a box that visibly dragged the fight out,
# while an escaped newline pair is a well-formed empty message the engine moves
# through. SupersSpeedStrings writes a blank at exactly these addresses and is
# run by thousands of people. That is production evidence and it outranks
# anything derivable from the dumps -- reasoning from the dumps is how 1.3
# through 1.6 got this wrong three times in a row.
DS_BLANKED = {
    (UNOVA, addr(15, 42)): "{00} gained {01} Exp. Points!",
    (UNOVA, addr(15, 43)): "{00} gained a boosted {01} Exp. Points!",
    (UNOVA, addr(157, 38)): "{00} did not learn {01}.",
    (UNOVA, addr(157, 40)): "1, 2, and... Ta-da! {00} forgot how to use {01}.",
    (UNOVA, addr(157, 41)): "{00} learned {01}!",
}

# Blanking any of these HANGS a wild encounter -- the battle never loads and the
# session has to be restarted. Reported on hardware 2026-08-30, the same day
# they shipped, and reverted immediately.
#
# They were added by reasoning that 15/42 is proven safe, so table 15 is safe.
# That is wrong, and it is the same mistake that cost four cycles earlier: a
# table is not a call site. 15/42 fires as a battle ends; 15/1 fires as one
# begins, inside a state machine that does not complete without it. The
# reference mod touches none of them, which should have been the warning.
DS_HANGS_THE_BATTLE = {
    (UNOVA, addr(15, 1)): "A wild {00} appeared!",
    (UNOVA, addr(15, 11)): "Go! {00}!",
    (UNOVA, addr(15, 26)): "{00}, come back!",
    (UNOVA, addr(15, 44)): "Player defeated {00} {01}!",
    (UNOVA, addr(15, 58)): "{00} got ${01} for winning!",
    (UNOVA, addr(15, 65)): "Gotcha! {00} was caught!",
    (UNOVA, addr(15, 72)): "Got away safely!",
    (UNOVA, addr(157, 44)): "{00}'s HP was restored by {01} point(s).",
    (UNOVA, addr(157, 55)): "{00}'s base {01} rose!",
}

# --- what the mod exists to remove, in the archive the client reads ---------
# One generic "{00} used\n{01}!" plus its duplicate is every overworld move in
# the game: Teleport, Sweet Scent and all eight HMs. Missing this is why v1.1
# and v1.2 still printed the whole line.
DS_FIELD_MOVES = {
    (UNOVA, addr(8, 52)): "{00} used {01}!  (every field move)",
    (UNOVA, addr(8, 53)): "{00} used {01}!  (second copy)",
}

# --- what must never be silenced, in the same archive ----------------------
# Choices where an unlabelled Yes/No is not enough to decide. The first three
# are the move-learn prompts: you have to see which move you are replacing.
DS_DECISIONS = {
    (UNOVA, addr(157, 32)): "{00} wants to learn {01} but knows four moves",
    (UNOVA, addr(157, 35)): "Give up on learning the move {01}?",
    (UNOVA, addr(157, 39)): "Which move should be forgotten?",
    (UNOVA, addr(71, 24)): "Held items will be put in the Bag. Is that OK?",
    (UNOVA, addr(88, 0)): "It will forget the saying it knows now. Is that OK?",
    (UNOVA, addr(157, 27)): "If the Mail is removed, its message will be lost.",
    (UNOVA, addr(159, 140)): "The trade will be ended. Is that OK?",
    (UNOVA, addr(27, 33)): "If the leader drops out, the group will be disbanded.",
    (UNOVA_1, addr(301, 102)): "Not adding {01} to your party... Is that OK?",
    (UNOVA_1, addr(301, 104)): "Sending {02} back to your Box... Is that OK?",
}
# Menu entries. Silencing one blanks the menu rather than skipping a box, and
# these live at coordinates the battle rules use in the *other* archive.
DS_LABELS = {
    (UNOVA_1, addr(15, 45)): "Game Sync",
    (UNOVA_1, addr(15, 47)): "Cancel",
    (UNOVA_1, addr(15, 44)): "Read which topic?",
}
# Story dialogue that borrows a counter's words.
DS_STORY = {
    (UNOVA_1, addr(101, 18)): "Gym Leader Clay is busy -- 'Please come again later.'",
    (UNOVA_1, addr(138, 0)): "Opelucid route announcer -- 'Please come again!'",
    (UNOVA_1, addr(322, 96)): "Black City recruiter -- 'Thank you.'",
    (UNOVA_1, addr(322, 240)): "Black City recruiter -- 'Thank you.'",
    (UNOVA_1, addr(135, 22)): "Dreamyard gift -- 'Thank you. This is my thank-you gift'",
}

# Every archive has a battle engine, and a pattern written for the GBA ids finds
# them all by accident. Unova 14/15 are the live one; 157 and 172 and 204 are the
# move-learn and evolution state machines beside it; 184 is 942 entries of
# trainer dialogue.
#
# The other regions' copies were added on 2026-09-01, derived from the corpus by
# shared text rather than guessed -- `tools/region_parity.py` groups all 166,867
# entries and reports which tables hold the same lines. Unova 14, 15 and 172 are
# merged into the single table Sinnoh 368 / Johto 197; Unova 157 maps to Sinnoh
# 453 / Johto 300; Unova 13, the per-move `{00} used {01}!` announce, maps to
# Sinnoh 0 and Johto 3 and had never been fenced in any region, including Unova.
# Nothing was being silenced in any of them, so this cost no coverage -- it
# closes the hole the next careless pattern would fall into.
DS_BATTLE_ENGINES = {
    UNOVA: {"13", "14", "15", "157", "172", "184", "204"},
    SINNOH: {"0", "368", "453"},
    JOHTO: {"3", "197", "300"},
}
# The ONLY addresses allowed inside one, each with what proved it. Adding to this
# list is a deliberate act: without an entry here the invariant test below fails,
# which is the whole point. A wrong guess here does not cost a tap, it costs the
# session -- see DS_HANGS_THE_BATTLE.
DS_PROVEN_IN_ENGINE = {
    (UNOVA, addr(15, 42)): "EXP gained -- blanked by the reference, confirmed on "
                           "hardware 2026-08-30",
    (UNOVA, addr(15, 43)): "boosted EXP -- same",
    (UNOVA, addr(157, 38)): "did not learn -- blanked by the reference",
    (UNOVA, addr(157, 40)): "forget animation -- blanked by the reference",
    (UNOVA, addr(157, 41)): "learned -- blanked by the reference",
}

# The Johto archive went uncovered until 2026-08-30 because this client could
# never dump it: the utility aborts on Sinnoh with a NUL byte in the string data
# and never reaches region 4. Recovered by moving the Sinnoh ROM out of the
# client's roms folder and repairing the truncated output. If the dump is ever
# regenerated without that workaround these all vanish, which is the point of
# asserting they are here.
DS_JOHTO = {
    (JOHTO, addr(211, 1)): "{00} used Cut!",
    (JOHTO, addr(211, 15)): "{00} used Surf!",
    (JOHTO, addr(211, 33)): "{00} used Headbutt.",
    (JOHTO, addr(40, 0)): "Hello, and welcome to the Pokemon Center.",
    (JOHTO, addr(40, 3)): "Please, come back again any time!",
    (JOHTO, addr(135, 4)): "Here are your Safari Balls!",
    (JOHTO, addr(439, 21)): "I'm the Day-Care Lady.",
    (JOHTO, addr(571, 8)): "Kurt: I just finished your Poke Ball.",
    (JOHTO, addr(522, 5)): "Once you enter this door -- the league door guard",
}
# Errors, in the archive the reference silences them in.
DS_JOHTO_KEPT = {
    (JOHTO, addr(211, 16)): "Surf can't be used if you have someone with you.",
    (JOHTO, addr(211, 23)): "Rock Climb can't be used if you have someone with you.",
}

# --- the GBA tables -------------------------------------------------------
# Kept because the dumps still carry them and a future client may read them
# again. They are not evidence that the mod works: v1.2 silenced all of these
# and the messages still appeared on screen.
GBA_FIELD_MOVES = {
    "1826775": "{02} used {03}!  (Kanto/Johto overworld, every move)",
    "271124337": "{02} used {03}!  (Hoenn overworld, every move)",
    "16804105": "{00} used {01}! (PP Remaining: ...)",
    "6060": "You have used {00}.",
}
GBA_BATTLE_END = {
    "200001": "gained EXP. Points",
    "200002": "grew to LV.",
    "200003": "learned <move>",
    "200016": "<own> fainted!",
    "200017": "<foe> fainted!",
    "200018": "got $ for winning",
    "200255": "Gotcha! ... was caught!",
    "205001": "gained EXP. Points  (second battle table)",
    "205002": "grew to LV.        (second battle table)",
    "205016": "<own> fainted!     (second battle table)",
}
HM_PROMPTS = {
    "1826708": "This tree looks like it can be CUT down!",
    "1826973": "This rock appears to be breakable.",
    "1827226": "It's a big boulder ... use STRENGTH?",
    "1827647": "It's a large waterfall.",
    "1827945": "The sea is deep here ... use DIVE?",
    "271124780": "big boulder / STRENGTH  (Hoenn)",
    "271125614": "Light is filtering down ... DIVE?  (Hoenn)",
}
COUNTERS = {
    "1725571": "Welcome to our POKeMON CENTER!",
    "1832932": "I'm the DAY-CARE LADY.",
    "1833605": "took back <mon> from the DAY-CARE LADY",
    "16807104": "<mon> was revived from the <fossil>!",
    "16779024": "<mon> now knows <move>!  (Move Maniac)",
    "16780326": "It's soft fertile soil.  (berry farming)",
    "16780175": "Wow! You look amazing!  (stylist)",
    "1670480": "received 30 SAFARI BALLS",
    "270702575": "Elite Four door guard",
    "270796211": "Battle Tower single-battle clerk",
}

# --- what must never be silenced, plain ids -------------------------------
DESCRIPTIONS = {
    "120279": "An attack move that inflicts double the damage ... hurt by",
    "220077": "Raises evasion if the Pokemon is confused.",
    "967153": "same description, Hoenn copy",
    "973220": "same description, Sinnoh copy",
}
DECISIONS = {
    "200004": "<mon> is trying to learn <move>.",
    "200006": "Delete a move to make room for <move>?",
    "200008": "Stop learning <move>?",
    "6012": "<item> has worn off. Use another?",
    "16779082": "You won't get these back. Are you sure?  (breeder trade-in)",
    "16779022": "Do you want to relearn or forget a move?",
    "16779031": "OK. Which move should <mon> forget?",
    "16780172": "It'll cost $<n> for your makeover. Is that okay?",
    "16779043": "I need <n> Battle Points to teach that. Is that OK?",
    "200332": "The BOX is full! You can't catch any more!",
    "200243": "There's no PP left for this move!",
}
LABELS = {"240086": "Repel", "110230": "Sweet Scent", "310025": "BATTLE FACTORY"}
STORY = {
    "1549609": "MR. FUJI",
    "1718540": "LORELEI",
    "271274240": "WALLY",
    "270482556": "an NPC reminiscing about the Day Care",
    "1582023": "Biker Conflict",
    "1539052": "an NPC whose EEVEE evolved into FLAREON",
}

BATTLE_TABLE = re.compile(r"20[05][0-9]{3}")


def load_dumps():
    """Every plain-id entry, id -> text."""
    out = {}
    for f in sorted(DUMPS.glob("dump_*.xml")):
        try:
            root = ET.parse(f).getroot()
        except ET.ParseError:
            continue
        if root.tag == "ds_strings_archive":
            continue
        for el in root.findall("string"):
            sid = el.get("id")
            if sid and sid not in out:
                out[sid] = el.text or ""
    return out


def load_ds_dumps():
    """Every NDS entry, (archive, (block, entry, table)) -> text."""
    out = {}
    for f in sorted(DUMPS.glob("dump_*.xml")):
        try:
            root = ET.parse(f).getroot()
        except ET.ParseError:
            continue
        if root.tag != "ds_strings_archive":
            continue
        archive = (root.get("archive_type", "0"), root.get("region_id", "0"))
        for el in root.findall("string"):
            key = (archive, (el.get("block_id"), el.get("entry_id"),
                             el.get("table_id")))
            out.setdefault(key, el.text or "")
    return out


@unittest.skipUnless(DUMPS.is_dir() and RULES.is_file(), "no dumps in this checkout")
class TestCorpus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules, cls.guards = fasttext.load_rules(RULES)
        cls.plain, cls.ds, cls.counts = fasttext.scan(DUMPS, cls.rules, cls.guards)
        cls.text = load_dumps()
        cls.ds_text = load_ds_dumps()

    # -- helpers -----------------------------------------------------------
    def assert_silenced(self, group, label):
        for sid, why in group.items():
            with self.subTest(id=sid, text=why):
                self.assertIn(sid, self.text, f"{sid} is not in the dumps any more")
                self.assertIn(sid, self.plain, f"{label}: {sid} ({why}) is not silenced")

    def assert_visible(self, group, label):
        for sid, why in group.items():
            with self.subTest(id=sid, text=why):
                self.assertNotIn(sid, self.plain,
                                 f"{label}: {sid} ({why}) must stay readable")

    def assert_ds_silenced(self, group, label):
        for (archive, key), why in group.items():
            with self.subTest(archive=archive, addr=key, text=why):
                self.assertIn((archive, key), self.ds_text,
                              f"{key} is not in archive {archive} any more")
                self.assertIn(key, self.ds.get(archive, {}),
                              f"{label}: {archive} {key} ({why}) is not silenced")

    def assert_ds_visible(self, group, label):
        for (archive, key), why in group.items():
            with self.subTest(archive=archive, addr=key, text=why):
                self.assertIn((archive, key), self.ds_text,
                              f"{key} is not in archive {archive} any more")
                self.assertNotIn(key, self.ds.get(archive, {}),
                                 f"{label}: {archive} {key} ({why}) must stay readable")

    # -- coverage in the archive the client actually reads ------------------
    def test_only_proven_addresses_are_silenced_in_a_battle_engine(self):
        """The guard that exists because reasoning was not enough.

        Twice now a plausible argument put entries into a battle engine that
        should not have been there: once by pattern rules drifting in from the
        GBA ids, once by assuming a whole table was safe because one address in
        it was. Both shipped. This makes the third time fail here instead.
        """
        offenders = {}
        for archive, hits in self.ds.items():
            engines = DS_BATTLE_ENGINES.get(archive, set())
            for key, (name, _) in hits.items():
                if key[2] not in engines:
                    continue
                if (archive, key) in DS_PROVEN_IN_ENGINE:
                    continue
                offenders[f"{archive}{key}"] = name
        self.assertEqual(offenders, {},
                         "silencing a battle-engine address with no evidence "
                         "for that exact address; add it to DS_PROVEN_IN_ENGINE "
                         "with what proved it, or do not silence it")

    def test_every_proven_engine_address_is_still_silenced(self):
        """The other direction: the list must not rot into fiction."""
        for (archive, key), why in DS_PROVEN_IN_ENGINE.items():
            with self.subTest(archive=archive, addr=key, reason=why):
                self.assertIn(key, self.ds.get(archive, {}))

    def test_the_gba_pattern_rules_cannot_reach_the_nds_archives(self):
        """`move-learned`, `catch-flow` and `evolution` were written against the
        GBA ids. They were reaching Sinnoh 368 and Johto 197 -- those archives'
        battle engines -- and writing {09} into a state machine."""
        for name in ("move-learned", "catch-flow", "evolution"):
            r = next(x for x in self.rules if x.name == name)
            with self.subTest(rule=name):
                self.assertTrue(r.plain_only, f"{name} can reach the NDS archives")

    def test_nothing_that_hangs_a_battle_is_silenced(self):
        """The most expensive regression this mod has produced.

        A blanked start-of-battle message stops the encounter loading at all.
        Cosmetic mistakes cost a tap; this one costs the session. Nothing goes
        back into this group without hardware evidence for that exact address.
        """
        self.assert_ds_visible(DS_HANGS_THE_BATTLE, "hangs the battle")

    def test_the_rules_that_hung_a_battle_stay_disabled(self):
        live = {r.name for r in self.rules}
        for name in ("battle-flow-ds", "party-menu-ds", "probe-faint-ds"):
            with self.subTest(rule=name):
                self.assertNotIn(name, live)

    def test_the_johto_archive_is_covered(self):
        """It was invisible until the dump workaround; do not lose it again."""
        self.assertTrue(any(a == JOHTO for a, _ in self.ds_text),
                        "dump_IPK_0_en.xml is missing from strings-work/dumps/")
        self.assert_ds_silenced(DS_JOHTO, "johto")

    def test_the_johto_errors_are_left_alone(self):
        self.assert_ds_visible(DS_JOHTO_KEPT, "johto errors")

    def test_no_error_or_turn_information_is_silenced(self):
        """Speed is not the only axis.

        An error explains why a button did nothing; silencing one leaves the
        player stuck with no reason. Turn information is what the battle is
        played on. Neither is a speed win.
        """
        self.assert_ds_visible(DS_ERRORS_AND_TURN_INFO, "errors and turn info")

    def test_the_nds_battle_engine_is_left_alone_entirely(self):
        """The finding that cost three build-install-play cycles.

        Not just the battle rules: `catch-flow`, `evolution` and `move-learned`
        were written for the GBA ids and reached these same addresses by
        accident, so disabling the `-ds` rules was not enough on its own. The
        `never_ds_tables` guard is what actually holds the line.
        """
        self.assert_ds_visible(DS_BATTLE_ENGINE, "battle engine")

    def test_no_pattern_reaches_a_guarded_nds_table(self):
        """A hand-picked address still gets through -- that is a decision already
        made, and it is how the EXP lines are blanked. What must never happen is
        a *pattern* written for the GBA ids finding these tables by accident,
        which is what `catch-flow`, `evolution` and `move-learned` all did."""
        guarded = self.guards.ds_tables
        self.assertTrue(guarded, "the battle-engine guard is empty")
        by_name = {r.name: r for r in self.rules}
        leaked = {}
        for archive, hits in self.ds.items():
            for key, (name, _) in hits.items():
                if (archive[0], archive[1], key[2]) not in guarded:
                    continue
                if key not in by_name[name].ds_id_set():
                    leaked[f"{archive}{key}"] = name
        self.assertEqual(leaked, {}, "a pattern reached the NDS battle engine")

    def test_the_blanked_battle_lines_use_a_blank_and_never_the_skip_token(self):
        """{09} at these addresses is what made the end of a battle drag."""
        self.assert_ds_silenced(DS_BLANKED, "blanked")
        for (archive, key) in DS_BLANKED:
            with self.subTest(addr=key):
                self.assertEqual(self.ds[archive][key][1], BLANK)

    def test_the_field_move_table_is_deliberately_not_guarded(self):
        """Table 8 is the one call site where {09} removes the box, so it stays
        reachable. Guarding it would disable the only thing that works."""
        self.assertNotIn((UNOVA[0], UNOVA[1], "8"), self.guards.ds_tables)
        self.assert_ds_silenced(DS_FIELD_MOVES, "field moves")

    # -- restraint in the same archive -------------------------------------
    def test_no_nds_decision_prompt_is_silenced(self):
        self.assert_ds_visible(DS_DECISIONS, "ds decisions")

    def test_no_nds_menu_label_is_silenced(self):
        self.assert_ds_visible(DS_LABELS, "ds labels")

    def test_nds_story_dialogue_is_left_alone(self):
        self.assert_ds_visible(DS_STORY, "ds story")

    def test_no_is_that_ok_confirmation_is_silenced_anywhere(self):
        """`Is that OK?` is a confirmation, not a shop phrase.

        It closes 44 entries across the dumps and almost all of them are the
        last chance to back out of something destructive: a disbanded group, a
        lost Mail message, a forgotten move. A rule that reaches them again has
        the same defect `shop-extra` carried until 1.3.
        """
        rx = re.compile(r"Is that OK\?")
        leaked = [sid for sid in self.plain if rx.search(self.text.get(sid, ""))]
        for archive, hits in self.ds.items():
            leaked += [f"{archive}{k}" for k in hits
                       if rx.search(self.ds_text.get((archive, k), ""))]
        self.assertEqual(leaked, [], "a rule silenced a Yes/No confirmation")

    # -- the GBA tables ----------------------------------------------------
    def test_the_gba_field_move_entries_are_still_silenced(self):
        self.assert_silenced(GBA_FIELD_MOVES, "GBA field moves")

    def test_the_gba_battle_tables_are_still_silenced(self):
        self.assert_silenced(GBA_BATTLE_END, "GBA battle end")

    def test_every_hm_obstacle_prompt_is_silenced(self):
        self.assert_silenced(HM_PROMPTS, "HM prompts")

    def test_the_repeated_counters_are_silenced(self):
        self.assert_silenced(COUNTERS, "counters")

    # -- restraint, plain ids ----------------------------------------------
    def test_no_move_or_item_description_is_silenced(self):
        self.assert_visible(DESCRIPTIONS, "descriptions")
        rx = re.compile(r"An attack move|The user |A move that|Raises |Lowers "
                        r"|An item to be held|inflicts ")
        leaked = [k for k in self.plain if rx.search(self.text.get(k, ""))]
        leaked += [f"{a}{k}" for a, hits in self.ds.items() for k in hits
                   if rx.search(self.ds_text.get((a, k), ""))]
        self.assertEqual(leaked, [], "a rule reached into a description")

    def test_no_decision_prompt_is_silenced(self):
        self.assert_visible(DECISIONS, "decisions")

    def test_no_ui_label_is_silenced(self):
        self.assert_visible(LABELS, "labels")
        label = re.compile(r"[^.!?]{0,34}")
        leaked = [k for k in self.plain if label.fullmatch(self.text.get(k, ""))]
        self.assertEqual(leaked, [], "a rule blanked a menu label")

    def test_story_dialogue_is_left_alone(self):
        self.assert_visible(STORY, "story")

    def test_every_prose_rule_declares_a_length_cap(self):
        # A rule matching free text with no cap is how v1.1 silenced Mr. Fuji.
        # Rules pinned to a table, or driven by hand-picked addresses, do not
        # need one.
        uncapped = [r.name for r in self.rules
                    if r.match and not r.max_len and not r.id_match and not r.tables]
        self.assertEqual(uncapped, [], "an uncapped pattern can reach story dialogue")

    def test_no_pattern_match_exceeds_its_own_rules_cap(self):
        by_rule = {r.name: r for r in self.rules}
        over = {}
        for sid, (name, _) in self.plain.items():
            r = by_rule[name]
            if sid in r.id_set() or not r.max_len:
                continue
            if len(self.text.get(sid, "")) > r.max_len:
                over[sid] = f"{name} cap={r.max_len}"
        for archive, hits in self.ds.items():
            for key, (name, _) in hits.items():
                r = by_rule[name]
                if key in r.ds_id_set() or not r.max_len:
                    continue
                if len(self.ds_text.get((archive, key), "")) > r.max_len:
                    over[f"{archive}{key}"] = f"{name} cap={r.max_len}"
        self.assertEqual(over, {}, "a rule silenced text longer than it declares")

    # -- structural invariants --------------------------------------------
    def test_battle_rules_only_reach_the_battle_tables(self):
        for sid, (rule_name, _) in self.plain.items():
            if rule_name == "status-battle":
                with self.subTest(id=sid):
                    self.assertRegex(sid, BATTLE_TABLE)

    def test_every_nds_rule_is_scoped_to_its_archive(self):
        """An NDS coordinate without an archive is not an address.

        `tables: [15]` unscoped means table 15 of Sinnoh and of Unova-1 as well,
        and those hold unrelated text.
        """
        for r in self.rules:
            with self.subTest(rule=r.name):
                if r.ds_ids or r.tables:
                    self.assertTrue(r.archives,
                                    f"{r.name} addresses NDS tables with no archives")

    def test_every_hand_picked_nds_address_lands_in_its_archive(self):
        for r in self.rules:
            for key in r.ds_id_set():
                for archive in r.archive_set():
                    with self.subTest(rule=r.name, archive=archive, addr=key):
                        self.assertIn((archive, key), self.ds_text,
                                      "the dump moved under a hand-picked address")

    def test_every_entry_carries_the_token_its_own_rule_declares(self):
        want = {r.name: r.token() for r in self.rules}
        self.assertTrue(self.plain and self.ds)
        for sid, (name, token) in self.plain.items():
            with self.subTest(id=sid):
                self.assertEqual(token, want[name])
        for archive, hits in self.ds.items():
            for key, (name, token) in hits.items():
                with self.subTest(archive=archive, addr=key):
                    self.assertEqual(token, want[name])

    def test_the_field_move_rule_uses_the_skip_token(self):
        """The one call site where {09} is proven to remove the box, on
        hardware, 2026-08-30. Field moves are the whole reason this mod works."""
        r = next(x for x in self.rules if x.name == "field-moves-ds")
        self.assertEqual(r.token(), SKIP)

    def test_the_table_14_probe_is_a_single_address(self):
        """`probe-faint-ds` exists to answer one question with one battle: does
        table 14 accept a blank line? It must never quietly grow into a rule --
        if the answer comes back yes, write a real rule and delete the probe.
        """
        probe = [r for r in self.rules if r.name == "probe-faint-ds"]
        if not probe:
            self.skipTest("probe already resolved and removed")
        self.assertEqual(probe[0].ds_id_set(), {("0", "1", "14")})
        self.assertEqual(probe[0].token(), BLANK)

    def test_the_battle_flow_rules_stay_disabled(self):
        """Kept in rules.json, disabled, so the addresses stay recorded. If one
        is switched back on the empty boxes come back -- and no token avoids
        that, so re-enabling is not a fix to try again."""
        live = {r.name for r in self.rules}
        for name in ("battle-end-ds", "move-learned-ds", "evolution-ds",
                     "status-battle-ds"):
            with self.subTest(rule=name):
                self.assertNotIn(name, live)

    def test_no_rule_tries_to_silence_with_an_empty_override(self):
        """`none` is not a silencing token.

        Confirmed on hardware 2026-08-30: the client reads an empty element as
        no override at all and its own text comes back. A rule that reaches for
        it is asking for vanilla text without saying so -- use
        `"enabled": false`, which is the same result and reads like what it
        means.
        """
        using = [r.name for r in self.rules if r.token() == NONE]
        self.assertEqual(using, [], "a rule expects `none` to silence something")

    def test_every_rule_still_matches_something(self):
        dead = [n for n, c in self.counts.items() if n != "_guarded" and c == 0]
        self.assertEqual(dead, [], "a rule matches nothing; the dump moved under it")

    def test_every_hand_picked_id_still_exists_in_the_dumps(self):
        for r in self.rules:
            for i in list(r.ids) + list(r.exclude_ids):
                with self.subTest(rule=r.name, id=i):
                    self.assertIn(str(i), self.text)


@unittest.skipUnless(MOD.is_dir() and DUMPS.is_dir(), "no dumps in this checkout")
class TestShippedMod(unittest.TestCase):
    """The files in mods/ must be what the current rules produce."""

    @classmethod
    def setUpClass(cls):
        import tempfile
        cls._dir = tempfile.TemporaryDirectory()
        rules, guards = fasttext.load_rules(RULES)
        plain, ds, _ = fasttext.scan(DUMPS, rules, guards)
        cls.fresh = Path(cls._dir.name)
        cls.files = fasttext.write_mod(cls.fresh, plain, ds, ["en", "es"], rules,
                                       {"en": "English", "es": "Espanol"})

    @classmethod
    def tearDownClass(cls):
        cls._dir.cleanup()

    def test_shipped_strings_match_a_fresh_generation(self):
        for rel in self.files:
            with self.subTest(file=rel):
                shipped = MOD / rel
                self.assertTrue(shipped.is_file(), f"{rel} is not in the mod")
                self.assertEqual(shipped.read_text(encoding="utf-8"),
                                 (self.fresh / rel).read_text(encoding="utf-8"),
                                 f"{rel} is stale -- re-run `pmmod strings fasttext`")

    def test_info_xml_declares_every_strings_file_and_no_others(self):
        root = ET.parse(MOD / "info.xml").getroot()
        declared = sorted(e.get("path") for e in root.find("strings"))
        self.assertEqual(declared, sorted(self.files))

    def test_the_unova_archive_file_is_shipped(self):
        """Without it the mod changes nothing the player can see."""
        self.assertIn("strings/ds_fasttext_0_2.xml", self.files)

    def test_no_shipped_file_uses_the_v1_1_bare_newline(self):
        # v1.1 wrote "\n", which renders an empty box you still have to dismiss.
        for rel in self.files:
            text = (MOD / rel).read_text(encoding="utf-8")
            body = text.split("-->", 1)[1]
            self.assertNotIn(">\\n<", body, f"{rel} still uses the v1.1 blank")


if __name__ == "__main__":
    unittest.main()
