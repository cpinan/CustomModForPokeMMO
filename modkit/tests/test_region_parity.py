"""The whole corpus, checked against its own duplicates in the other regions.

PokeMMO ships the same game text five times over: Kanto and Hoenn carry it as
plain ids, Sinnoh, Johto and the two Unova archives as NDS coordinates. If a
line is silenced in one region and drawing in another, one of the two is wrong.

This is the check `test_supers_parity` cannot be. The reference has its own
holes in its own places, so comparing against it proves nothing where both mods
miss -- which is exactly how Teleport's prompt drew a box for six releases with
a green suite. The regions are each other's oracle and owe nothing to any mod.

`test_no_line_is_silenced_in_one_region_and_drawing_in_another` is the whole
point. The rest pin the classification down so that test cannot be made to pass
by widening what counts as explained.
"""
import unittest
from pathlib import Path

from pmmod import fasttext, regions


def ds_for(case):
    _, ds, _ = fasttext.scan(DUMPS, case.rules, case.guards)
    return ds

ROOT = Path(__file__).resolve().parents[2]
DUMPS = ROOT / "strings-work" / "dumps"
RULES = ROOT / "strings-work" / "rules.json"

# Every region's copy of the tables the NDS battle engine draws. Derived from
# the corpus by shared text, not guessed: Unova 14, 15 and 172 are merged into
# the single table Sinnoh 368 / Johto 197, Unova 157 maps to Sinnoh 453 / Johto
# 300, and Unova 13 -- the per-move `{00} used {01}!` announce, 1,680 entries --
# maps to Sinnoh 0 and Johto 3.
BATTLE_TWINS = {
    ("0", "2"): {"13", "14", "15", "157", "172", "184", "204"},
    ("0", "3"): {"0", "368", "453"},
    ("0", "4"): {"3", "197", "300"},
}


@unittest.skipUnless(DUMPS.is_dir() and RULES.is_file(), "no dumps in this checkout")
class TestRegionParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.split = regions.compare(DUMPS, RULES)
        cls.rules, cls.guards = fasttext.load_rules(RULES)

    def test_no_line_is_silenced_in_one_region_and_drawing_in_another(self):
        bad = regions.gaps(self.split)
        self.assertEqual(
            {silent[0].text[:60]: sorted(f"{d.region} {d.address}" for d in drawing)
             for silent, drawing in bad.values()}, {},
            "these lines are silenced in one region and still draw in another; "
            "run tools/region_parity.py, and run it again after fixing -- closing "
            "a gap gives the next one a silenced twin to disagree with")

    def test_the_comparison_actually_finds_the_duplicates(self):
        """Guards the test above from passing because nothing was compared.

        If `normalise` ever over-collapses or the dumps stop loading, the gap set
        goes empty for the wrong reason. The corpus really does hold every one of
        these lines in at least four places.
        """
        locs = regions.load(DUMPS)
        self.assertGreater(len(locs), 150_000)
        seen = {}
        for loc in locs:
            if loc.text.strip():
                seen.setdefault(regions.normalise(loc.text), set()).add(loc.region)
        for line in ("{00} used\\nCut!", "we look forward to your next visit",
                     "which pokémon should we raise for\\nyou?"):
            with self.subTest(line=line):
                self.assertGreaterEqual(len(seen.get(regions.normalise(line), ())), 3)

    def test_every_remaining_disagreement_is_the_battle_engine(self):
        """The only reason left for a region to disagree with itself.

        Today all 81 of them are battle-engine, and that is the honest state: a
        box those tables draw cannot be removed, so a silenced GBA twin and a
        drawing NDS one is the correct outcome, not a gap. If another category
        appears here, someone widened `explain` instead of fixing a rule.
        """
        verdicts = {v for _, _, why in self.split.values() for v in why.values()}
        self.assertEqual(verdicts - {regions.BATTLE_ENGINE}, set())

    def test_the_battle_engine_is_guarded_in_every_region(self):
        """The guard was Unova-only until 2026-09-01.

        Sinnoh and Johto ship the same engine and nothing stopped a pattern from
        reaching it there. Nothing had -- but `catch-flow`, `evolution` and
        `move-learned` all reached Unova's copy by accident before the guard
        existed, and there is no reason the next one picks the same region.
        """
        for archive, tables in BATTLE_TWINS.items():
            for table in tables:
                with self.subTest(archive=archive, table=table):
                    self.assertIn((archive[0], archive[1], table),
                                  self.guards.ds_tables)

    def test_the_field_move_table_is_not_guarded(self):
        """Table 8 must stay reachable: it is the one call site where {09} works.

        Guarding the battle engine region by region is one careless line away
        from taking the field moves with it, and that is the whole mod.
        """
        for archive in (("0", "2"),):
            self.assertNotIn((archive[0], archive[1], "8"), self.guards.ds_tables)

    def test_the_tutor_results_are_silenced_and_their_prompts_are_not(self):
        """The distinction the tutor rules exist to make.

        The move relearner prints `{00} learned {01}!` exactly like the battle
        engine, so these addresses are hand-listed. A result goes; a prompt that
        names the move you are about to lose stays.
        """
        _, ds, _ = fasttext.scan(DUMPS, self.rules, self.guards)
        unova, johto = ("0", "2"), ("0", "4")
        sinnoh = ("0", "3")
        for archive, table, entry in ((johto, "748", "14"), (johto, "115", "25"),
                                      (johto, "747", "3"), (sinnoh, "645", "17")):
            with self.subTest(silenced=f"{table}/{entry}"):
                self.assertIn(("0", entry, table), ds.get(archive, {}))
        for archive, table, entry in ((johto, "748", "9"), (johto, "748", "18"),
                                      (johto, "115", "18"), (sinnoh, "645", "1")):
            with self.subTest(readable=f"{table}/{entry}"):
                self.assertNotIn(("0", entry, table), ds.get(archive, {}))

    def test_the_move_relearner_stays_fenced(self):
        """Unova 204 reads like an NPC counter and is not treated as one.

        It has POWER/ACCURACY/PP/TEACH menu labels and a Heart Scale exchange, and
        a tutor rule was written for it on 2026-09-01 on exactly that reasoning.
        It is the move relearner's copy of the move-learn state machine, and that
        machine is the one place hardware already proved {09} does not work:
        157/38, 40 and 41 all had to become a blank line. Fenced until somebody
        relearns a move with a build that touches it.
        """
        self.assertIn(("0", "2", "204"), self.guards.ds_tables)
        self.assertEqual(
            [k for k in ds_for(self).get(("0", "2"), {}) if k[2] == "204"], [])


if __name__ == "__main__":
    unittest.main()
