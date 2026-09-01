"""The field-move script, checked against its own copies in the other archives.

Every region ships the same script -- Unova-1 table 280, Sinnoh 381, Johto 211 --
so a line silenced in one and drawing in another is an oversight, not a decision.

This is the check that would have caught Teleport. Reported from hardware on
2026-09-01: Sweet Scent was silent and Teleport still drew its full box. Sweet
Scent goes through the generic `{00} used\\n{01}!` at Unova 8/52 and had been
silent since the first build; Teleport has a confirmation prompt that exists in
Johto's copy alone. SupersSpeedStrings does not silence it either, so
`test_supers_parity` scored a clean run for six releases.

The reference cannot be the only oracle. These archives are each other's.
"""
import unittest
from pathlib import Path

from pmmod import fasttext, fieldmoves

ROOT = Path(__file__).resolve().parents[2]
DUMPS = ROOT / "strings-work" / "dumps"
RULES = ROOT / "strings-work" / "rules.json"


@unittest.skipUnless(DUMPS.is_dir(), "no dumps here")
class TestFieldMoveParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rules, guards = fasttext.load_rules(RULES)
        _, cls.ds, _ = fasttext.scan(DUMPS, rules, guards)
        from tests.test_corpus import load_ds_dumps
        cls.text = load_ds_dumps()

    def test_no_field_move_line_is_silenced_in_one_archive_and_not_another(self):
        found = fieldmoves.gaps(self.text, self.ds)
        self.assertEqual(
            [(k, {fieldmoves.NAMES[a]: v[:2] for a, v in hits.items()})
             for k, hits in found], [],
            "a field-move line is silenced in one archive and still draws in "
            "another; run tools/fieldmove_parity.py for the addresses")

    def test_every_field_move_line_is_accounted_for(self):
        """No line in these three tables is left unexplained.

        A line either has a twin that agrees with it, or it is in `KEEP` with a
        reason. Teleport's prompt sat outside both for six releases because
        nothing forced the question.
        """
        odd = fieldmoves.unpaired(self.text, self.ds)
        self.assertEqual(
            [f"{fieldmoves.NAMES[a]} {fieldmoves.TABLES[a]}/{v[0]}: {v[2][:60]}"
             for _, hits in odd for a, v in hits.items()], [],
            "this field-move line has no twin and no recorded reason to stay; "
            "silence it, or add it to fieldmoves.KEEP with why")

    def test_the_teleport_prompt_is_silenced(self):
        """The line the bug was reported against, pinned by hand.

        It is the only field-move prompt with no twin in another archive, so the
        two tests above cannot protect it once it is covered -- `unpaired` only
        looks at lines that are *not* silenced.
        """
        self.assertEqual(self.ds[("0", "4")].get(("0", "27", "211")),
                         ("counters-ds-johto", fasttext.SKIP))

    def test_the_keep_list_still_describes_real_entries(self):
        """A reason for keeping something that no longer exists is a lie."""
        present = {fieldmoves.normalise(t)
                   for (a, trip), t in self.text.items()
                   if fieldmoves.TABLES.get(a) == trip[2]}
        for key in fieldmoves.KEEP:
            with self.subTest(line=key):
                self.assertIn(key, present)


if __name__ == "__main__":
    unittest.main()
