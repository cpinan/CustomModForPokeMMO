"""Unit tests for the fast-text rule engine.

These run on hand-written fixtures, not on the client's dumps, so they keep
working on a machine that has never had PokeMMO installed.
"""
import json
import re
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

from pmmod import fasttext
from pmmod.fasttext import BLANK, NONE, SKIP, Entry, Guards, Rule

UNOVA = ("0", "2")
SINNOH = ("0", "3")


def rule(**kw):
    return Rule(**kw)


def plain(sid, text):
    return Entry(text=text, sid=str(sid))


def ds(archive, table, entry, text, block="0"):
    return Entry(text=text, archive=archive, table=str(table),
                 entry=str(entry), block=str(block))


class TestReplacementTokens(unittest.TestCase):
    def test_skip_is_an_argument_slot_the_client_never_fills(self):
        # The whole mod rests on this: {09} resolves to nothing, so the client
        # skips the box. A newline would render an empty box you still tap.
        self.assertEqual(SKIP, "{09}")
        self.assertNotIn("\\n", SKIP)

    def test_blank_still_draws_a_box(self):
        self.assertEqual(BLANK, "\\n\\n")

    def test_an_empty_override_is_its_own_token_and_does_not_silence(self):
        # Distinct from both other tokens, but not a way to remove text: the
        # client reads an empty element as "no override" and shows its own.
        # Kept expressible so rules.json can be read back, not so it is used.
        self.assertEqual(NONE, "")
        self.assertNotEqual(NONE, BLANK)
        self.assertNotEqual(NONE, SKIP)

    def test_a_rule_defaults_to_skip_and_says_so(self):
        self.assertEqual(rule(name="r", match="x").token(), SKIP)
        self.assertEqual(rule(name="r", match="x", replace=BLANK).token(), BLANK)
        self.assertEqual(rule(name="r", match="x", replace=NONE).token(), NONE)


class TestRuleMatching(unittest.TestCase):
    def test_a_rule_with_neither_match_nor_ids_is_rejected(self):
        # re.compile("") matches every string; an empty rule must not silence
        # the entire corpus.
        self.assertIsNone(rule(name="empty").rx())
        self.assertFalse(rule(name="empty").hits(plain(1, "anything")))

    def test_explicit_id_beats_everything(self):
        r = rule(name="r", ids=[42], match="never matches this")
        self.assertTrue(r.hits(plain(42, "unrelated text")))

    def test_exclude_ids_wins_over_the_pattern(self):
        r = rule(name="r", match="Thank you", exclude_ids=[7])
        self.assertTrue(r.hits(plain(8, "Thank you.")))
        self.assertFalse(r.hits(plain(7, "Thank you.")))

    def test_id_match_pins_a_rule_to_one_table(self):
        r = rule(name="battle", id_match=r"20[05][0-9]{3}", match="fainted!")
        self.assertTrue(r.hits(plain(200016, "{0F}\\nfainted!")))
        # Same words, an NPC id: must not match.
        self.assertFalse(r.hits(plain(271142722, "looks darling even when fainted!")))
        # A longer id that merely starts with 200 is a different family.
        self.assertFalse(r.hits(plain(2001234, "{0F}\\nfainted!")))

    def test_max_len_keeps_a_prose_rule_off_story_dialogue(self):
        r = rule(name="shop", match="Come again", max_len=40)
        self.assertTrue(r.hits(plain(1, "Come again!")))
        self.assertFalse(r.hits(plain(1, "Come again! " + "x" * 60)))

    def test_unrestricted_rule_matches_any_container(self):
        r = rule(name="r", match="Gotcha")
        self.assertTrue(r.hits(plain(1, "Gotcha!")))
        self.assertTrue(r.hits(ds(UNOVA, 999, 1, "Gotcha!")))


class TestArchiveScoping(unittest.TestCase):
    """(table, entry) is only an address once you say which archive.

    The same coordinate is "Player beat {00} {01}" in the Unova archive and the
    menu label "Game Sync" in the next one, so an unscoped NDS rule is the bug,
    not a convenience.
    """

    def test_tables_are_scoped_to_the_declared_archives(self):
        r = rule(name="battle", archives=[[0, 2]], tables=[14], match="fainted!")
        self.assertTrue(r.hits(ds(UNOVA, 14, 0, "{00} fainted!")))
        self.assertFalse(r.hits(ds(SINNOH, 14, 0, "{00} fainted!")))

    def test_a_scoped_rule_never_reaches_the_plain_id_containers(self):
        r = rule(name="battle", archives=[[0, 2]], tables=[14], match="fainted!")
        self.assertFalse(r.hits(plain(200016, "{0F}\\nfainted!")))

    def test_a_hand_picked_nds_address_is_scoped_too(self):
        r = rule(name="exp", archives=[[0, 2]], ds_ids=[[15, 42]])
        self.assertTrue(r.hits(ds(UNOVA, 15, 42, "{00} gained {01} Exp. Points!")))
        self.assertFalse(r.hits(ds(SINNOH, 15, 42, "something else entirely")))

    def test_a_hand_picked_nds_address_beats_the_guards(self):
        # by_hand is what `scan` consults before applying `never`/`never_label`.
        r = rule(name="exp", archives=[[0, 2]], ds_ids=[[15, 42]])
        self.assertTrue(r.by_hand(ds(UNOVA, 15, 42, "text")))
        self.assertFalse(r.by_hand(ds(UNOVA, 15, 43, "text")))

    def test_an_nds_address_may_name_its_block(self):
        r = rule(name="r", archives=[[0, 2]], ds_ids=[[15, 42, 3]])
        self.assertTrue(r.hits(ds(UNOVA, 15, 42, "t", block="3")))
        self.assertFalse(r.hits(ds(UNOVA, 15, 42, "t", block="0")))

    def test_block_defaults_to_zero(self):
        self.assertEqual(rule(name="r", archives=[[0, 2]],
                              ds_ids=[[15, 42]]).ds_id_set(), {("0", "42", "15")})

    def test_plain_only_keeps_a_gba_pattern_out_of_the_nds_archives(self):
        r = rule(name="learn", match="learned", plain_only=True)
        self.assertTrue(r.hits(plain(200003, "{00} learned {01}!")))
        self.assertFalse(r.hits(ds(UNOVA, 204, 3, "{00} learned\\n{01}!")))
        self.assertFalse(r.hits(ds(SINNOH, 368, 836, "{00} learned\\n{01}!")))

    def test_a_plain_id_and_an_nds_coordinate_never_collide(self):
        # 15 is a table id in one space and a string id in the other.
        r = rule(name="r", archives=[[0, 2]], ds_ids=[[15, 42]])
        self.assertFalse(r.hits(plain(15, "anything")))
        self.assertFalse(r.hits(plain(42, "anything")))


class TestLoadRules(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self._dir.name)

    def tearDown(self):
        self._dir.cleanup()

    def _load(self, raw):
        p = self.tmp / "rules.json"
        p.write_text(json.dumps(raw), encoding="utf-8")
        return fasttext.load_rules(p)

    def test_replace_defaults_to_auto(self):
        rules, _ = self._load({"rules": [{"name": "a", "match": "x"}]})
        self.assertEqual(rules[0].replace, fasttext.AUTO)

    def test_symbolic_replace_tokens(self):
        rules, _ = self._load({"rules": [
            {"name": "a", "match": "x", "replace": "skip"},
            {"name": "b", "match": "y", "replace": "blank"},
            {"name": "c", "match": "z", "replace": "none"},
        ]})
        self.assertEqual(rules[0].replace, SKIP)
        self.assertEqual(rules[1].replace, BLANK)
        self.assertEqual(rules[2].replace, NONE)
        # "none" is falsy; it must not fall back to the skip default.
        self.assertEqual(rules[2].token(), NONE)

    def test_disabled_rules_are_dropped(self):
        rules, _ = self._load({"rules": [
            {"name": "a", "match": "x", "enabled": False},
            {"name": "b", "match": "y"},
        ]})
        self.assertEqual([r.name for r in rules], ["b"])

    def test_a_rule_with_no_match_no_ids_and_no_ds_ids_raises(self):
        with self.assertRaises(ValueError):
            self._load({"rules": [{"name": "oops"}]})

    def test_ds_ids_alone_are_enough_to_define_a_rule(self):
        rules, _ = self._load({"rules": [
            {"name": "a", "archives": [[0, 2]], "ds_ids": [[15, 42]]}]})
        self.assertEqual(rules[0].ds_id_set(), {("0", "42", "15")})

    def test_unscoped_ds_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            self._load({"rules": [{"name": "a", "ds_ids": [[15, 42]]}]})

    def test_unscoped_tables_are_rejected(self):
        with self.assertRaises(ValueError):
            self._load({"rules": [{"name": "a", "match": "x", "tables": [14]}]})

    def test_plain_only_with_an_nds_scope_is_rejected(self):
        # Contradictory: the rule would claim to be GBA-only and NDS-scoped.
        with self.assertRaises(ValueError):
            self._load({"rules": [{"name": "a", "match": "x", "plain_only": True,
                                   "archives": [[0, 2]], "ds_ids": [[15, 42]]}]})

    def test_a_malformed_ds_address_is_rejected(self):
        with self.assertRaises(ValueError):
            self._load({"rules": [{"name": "a", "archives": [[0, 2]],
                                   "ds_ids": [[15]]}]})
        with self.assertRaises(ValueError):
            self._load({"rules": [{"name": "a", "archives": [[0, 2]],
                                   "ds_ids": [[15, 42, 0, 9]]}]})

    def test_blank_archives_is_rejected_rather_than_ignored(self):
        # Removed in 1.3. Silently dropping it would change every NDS token in
        # the mod without anyone noticing.
        with self.assertRaises(ValueError) as cm:
            self._load({"rules": [{"name": "a", "match": "x"}],
                        "blank_archives": [[0, 2]]})
        self.assertIn("blank_archives", str(cm.exception))

    def test_both_global_pattern_guards_are_compiled(self):
        _, guards = self._load({"rules": [{"name": "a", "match": "x"}],
                                "never": "The user ",
                                "never_label": "^[^.!?]{0,34}$"})
        self.assertEqual(len(guards.patterns), 2)

    def test_the_nds_battle_table_guard_is_read_as_string_triples(self):
        _, guards = self._load({"rules": [{"name": "a", "match": "x"}],
                                "never_ds_tables": [[0, 2, 15], [0, 2, 172]]})
        self.assertEqual(guards.ds_tables, {("0", "2", "15"), ("0", "2", "172")})


class TestScan(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self._dir.name)
        self.dumps = self.tmp / "dumps"
        self.dumps.mkdir()

    def tearDown(self):
        self._dir.cleanup()

    def write_plain(self, entries, name="dump_strings_en.xml"):
        body = "\n".join(f'<string id="{i}">{t}</string>' for i, t in entries)
        (self.dumps / name).write_text(
            f'<?xml version="1.0" encoding="UTF-8"?>\n<strings lang="en">\n{body}\n</strings>\n',
            encoding="utf-8")

    def write_ds(self, entries, name="dump_CPU_0_en.xml", region="3", atype="0"):
        body = "\n".join(
            f'<string block_id="0" entry_id="{e}" table_id="{tb}">{t}</string>'
            for e, tb, t in entries)
        (self.dumps / name).write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<ds_strings_archive archive_type="{atype}" region_id="{region}" lang="en">\n'
            f'{body}\n</ds_strings_archive>\n', encoding="utf-8")

    def test_skip_is_the_default_everywhere(self):
        self.write_plain([("100", "Gotcha!")])
        self.write_ds([("5", "368", "Gotcha!")], region="3")
        p, d, _ = fasttext.scan(self.dumps, [rule(name="catch", match="Gotcha")])
        self.assertEqual(p["100"], ("catch", SKIP))
        self.assertEqual(d[SINNOH][("0", "5", "368")], ("catch", SKIP))

    def test_a_rule_may_ask_for_a_blank_line_in_one_archive(self):
        self.write_ds([("42", "15", "gained Exp"), ("52", "8", "used move")],
                      name="dump_IRB_0_en.xml", region="2")
        rules = [rule(name="exp", archives=[[0, 2]], ds_ids=[[15, 42]], replace=BLANK),
                 rule(name="field", archives=[[0, 2]], ds_ids=[[8, 52]])]
        _, d, _ = fasttext.scan(self.dumps, rules)
        self.assertEqual(d[UNOVA][("0", "42", "15")], ("exp", BLANK))
        self.assertEqual(d[UNOVA][("0", "52", "8")], ("field", SKIP))

    def test_a_scoped_rule_leaves_the_same_address_in_another_archive_alone(self):
        self.write_ds([("45", "15", "Player beat {00} {01}!")],
                      name="dump_IRB_0_en.xml", region="2")
        self.write_ds([("45", "15", "Game Sync")],
                      name="dump_IRB_1_en.xml", region="2", atype="1")
        rules = [rule(name="battle", archives=[[0, 2]], ds_ids=[[15, 45]])]
        _, d, counts = fasttext.scan(self.dumps, rules)
        self.assertEqual(list(d), [UNOVA])
        self.assertEqual(counts["battle"], 1)

    def test_guards_block_a_pattern_but_not_an_explicit_id(self):
        self.write_plain([("1", "The user faints."), ("2", "The user faints.")])
        guards = Guards(patterns=[re.compile("The user ")])
        p, _, counts = fasttext.scan(self.dumps, [rule(name="p", match="faints")],
                                     guards)
        self.assertEqual(p, {})
        self.assertEqual(counts["_guarded"], 2)

        p, _, _ = fasttext.scan(self.dumps, [rule(name="i", ids=[1])], guards)
        self.assertIn("1", p)

    def test_guards_block_a_pattern_but_not_a_hand_picked_nds_address(self):
        self.write_ds([("42", "15", "The user gained Exp.")],
                      name="dump_IRB_0_en.xml", region="2")
        guards = Guards(patterns=[re.compile("The user ")])
        _, d, counts = fasttext.scan(
            self.dumps,
            [rule(name="p", archives=[[0, 2]], tables=[15], match="gained")], guards)
        self.assertEqual(d, {})
        self.assertEqual(counts["_guarded"], 1)

        _, d, _ = fasttext.scan(
            self.dumps,
            [rule(name="i", archives=[[0, 2]], ds_ids=[[15, 42]])], guards)
        self.assertIn(("0", "42", "15"), d[UNOVA])

    def test_a_guarded_nds_table_is_unreachable_by_pattern(self):
        """A box in the NDS battle engine cannot be removed, so a pattern must
        never silence one. Hand-picked addresses still get through -- that is a
        decision already made."""
        self.write_ds([("65", "15", "Gotcha!\\n{00} was caught!")],
                      name="dump_IRB_0_en.xml", region="2")
        guards = Guards(ds_tables={("0", "2", "15")})
        _, d, counts = fasttext.scan(
            self.dumps, [rule(name="catch", match="Gotcha")], guards)
        self.assertEqual(d, {})
        self.assertEqual(counts["_guarded"], 1)

        _, d, _ = fasttext.scan(
            self.dumps,
            [rule(name="c", archives=[[0, 2]], ds_ids=[[15, 65]])], guards)
        self.assertIn(("0", "65", "15"), d[UNOVA])

    def test_the_nds_table_guard_does_not_touch_the_plain_containers(self):
        self.write_plain([("200255", "Gotcha! {00} was caught!")])
        guards = Guards(ds_tables={("0", "2", "15")})
        p, _, _ = fasttext.scan(self.dumps, [rule(name="c", match="Gotcha")], guards)
        self.assertIn("200255", p)

    def test_first_matching_rule_owns_the_entry(self):
        self.write_plain([("1", "Gotcha! It was caught!")])
        rules = [rule(name="first", match="Gotcha"), rule(name="second", match="caught")]
        p, _, counts = fasttext.scan(self.dumps, rules)
        self.assertEqual(p["1"][0], "first")
        self.assertEqual(counts["second"], 0)

    def test_per_rule_replace_overrides_the_default(self):
        self.write_plain([("1", "Gotcha!")])
        p, _, _ = fasttext.scan(self.dumps, [rule(name="c", match="Gotcha",
                                                  replace=BLANK)])
        self.assertEqual(p["1"][1], BLANK)

    def test_an_unparseable_dump_is_skipped_not_fatal(self):
        self.write_plain([("1", "Gotcha!")])
        (self.dumps / "dump_broken_en.xml").write_text("<strings><oops", encoding="utf-8")
        p, _, _ = fasttext.scan(self.dumps, [rule(name="c", match="Gotcha")])
        self.assertIn("1", p)


class TestWriteMod(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.out = Path(self._dir.name) / "mod"

    def tearDown(self):
        self._dir.cleanup()

    def _write(self, plain=None, ds=None, rules=None):
        return fasttext.write_mod(
            self.out, plain or {}, ds or {}, ["en"],
            rules or [rule(name="r", match="x", note="a note")], {"en": "English"})

    def test_every_written_file_is_wellformed_xml(self):
        files = self._write({"1": ("r", SKIP)},
                            {SINNOH: {("0", "5", "368"): ("r", BLANK)}})
        self.assertEqual(len(files), 2)
        for rel in files:
            ET.parse(self.out / rel)          # raises on malformed output

    def test_no_double_dash_reaches_an_xml_comment(self):
        # The client's pull parser rejects the whole mod, silently, on "--".
        files = self._write({"1": ("r", SKIP)},
                            rules=[rule(name="r", match="x", note="a -- b --- c")])
        head = (self.out / files[0]).read_text(encoding="utf-8").split("-->")[0]
        self.assertNotIn("--", head[head.index("<!--") + 4:])

    def test_an_nds_file_carries_whichever_token_each_entry_asked_for(self):
        files = self._write(ds={UNOVA: {("0", "52", "8"): ("field", SKIP),
                                        ("0", "42", "15"): ("exp", BLANK),
                                        ("0", "0", "14"): ("faint", NONE)}})
        ds_file = next(f for f in files if "ds_fasttext" in f)
        root = ET.parse(self.out / ds_file).getroot()
        got = {(e.get("table_id"), e.get("entry_id")): e.text for e in root}
        self.assertEqual(got, {("8", "52"): SKIP, ("15", "42"): BLANK,
                               ("14", "0"): None})

    def test_an_empty_override_round_trips_as_an_empty_element(self):
        files = self._write(ds={UNOVA: {("0", "0", "14"): ("faint", NONE)}})
        ds_file = next(f for f in files if "ds_fasttext" in f)
        text = (self.out / ds_file).read_text(encoding="utf-8")
        self.assertIn('table_id="14"></string>', text)
        ET.parse(self.out / ds_file)

    def test_strings_are_not_shipped_under_data(self):
        """Anything under data/ is a directory overlay to the client, which
        logs the undeclared form as deprecated even when info.xml lists every
        file. The live client says so out loud on startup."""
        files = self._write({"1": ("r", SKIP)},
                            {UNOVA: {("0", "1", "8"): ("r", SKIP)}})
        for f in files:
            self.assertFalse(f.startswith("data/"), f)

    def test_one_file_per_archive(self):
        files = self._write(ds={UNOVA: {("0", "1", "8"): ("r", SKIP)},
                                SINNOH: {("0", "1", "8"): ("r", SKIP)}})
        self.assertEqual([f for f in files if "ds_fasttext" in f],
                         ["strings/ds_fasttext_0_2.xml",
                          "strings/ds_fasttext_0_3.xml"])

    def test_entries_are_written_in_numeric_id_order(self):
        files = self._write({"200016": ("r", SKIP), "1826775": ("r", SKIP),
                             "6060": ("r", SKIP)})
        ids = [el.get("id") for el in ET.parse(self.out / files[0]).getroot()]
        self.assertEqual(ids, ["6060", "200016", "1826775"])


class TestWriteInfo(unittest.TestCase):
    def test_info_xml_escapes_the_apostrophe_in_a_description(self):
        with tempfile.TemporaryDirectory() as t:
            out = Path(t)
            fasttext.write_info(out, ["data/strings/a.xml"], "N", "1.0", "me",
                                "the client's own strings", "https://example.test/")
            root = ET.parse(out / "info.xml").getroot()
            self.assertEqual(root.get("description"), "the client's own strings")
            self.assertEqual([e.get("path") for e in root.find("strings")],
                             ["data/strings/a.xml"])


if __name__ == "__main__":
    unittest.main()
