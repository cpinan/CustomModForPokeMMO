# VanBobby Fast Strings

**Type:** strings mod · **Languages:** English + Spanish · **Client:** r32920 · **Version:** 1.13

## What it does

Removes the text from the interactions you repeat hundreds of times a day, so
the box goes away instead of making you mash through it.

| rule | entries | what it covers |
|---|---|---|
| `counters-ds-johto` | 72 | Johto archive: HM prompts, Pokecenter, Safari Zone, Day Care, Kurt, shops, league door |
| `mart` | 63 | Shop clerk purchase and sale flow |
| `pokecenter` | 52 | Nurse Joy / healing counter flow |
| `status-battle` | 50 | Per-turn battle status chatter |
| `counters-ds-sinnoh` | 47 | Sinnoh archive: Great Marsh gate and tram, Elite Four door, Pokecenter and shop desk, Day Care, the rest house that heals |
| `battle-frontier` | 44 | Battle Tower / Palace / Arena / Factory reception counters |
| `daycare` | 42 | Day-care deposit, retrieval and egg hand-off |
| `battle-end` | 37 | The end-of-battle run: faint, EXP, level-up, move learned, winnings, capture |
| `shop-extra` | 35 | Remaining shop counter lines |
| `move-tutor-ds-sinnoh` | 30 | Sinnoh archive: move tutor, deleter and TM results |
| `move-tutor-ds-johto` | 29 | Johto archive: move tutor, deleter and TM results |
| `hm-prompts-ds-sinnoh` | 23 | Sinnoh archive: every HM obstacle prompt and the `used <move>` line that follows |
| `hm-field-prompts` | 20 | Every HM obstacle prompt: tree, boulder, rock, waterfall, dive, surf |
| `safari-gate` | 20 | Safari Zone entry, sign-out counter and the PA that ends a run |
| `hm-prompts-ds-unova1` | 19 | Unova storyline archive: the same obstacle prompts plus Flash, Teleport and Dig |
| `field-moves` | 15 | Overworld move use -- Teleport, Sweet Scent, Cut, Fly, Dig, Flash, Headbutt, all of them |
| `fossil-reviver` | 15 | Fossil revival counter, used in every region |
| `move-tutor` | 15 | Move Master, Move Maniac and the Special Move Tutor |
| `move-tutor-ds-unova1` | 12 | Unova1 archive: move tutor, deleter and TM results |
| `stylist` | 10 | Personal stylist and the bike-skin counter |
| `field-move-prompts` | 9 | Cut / Rock Smash / Surf / Dive confirmations before the move fires |
| `berry-farming` | 6 | Soil, planting, watering and picking |
| `ferry` | 6 | The ferry that moves you between regions: the greeting, the boarding line and the cancel |
| `catch-flow` | 5 | Ball throw result -- fires on every encounter you throw at |
| `repel` | 5 | Repel wear-off |
| `breeder` | 4 | Day-care Breeder trade-in and egg hand-off |
| `counters-ds-unova1` | 3 | Unova storyline archive: Day Care and the shop farewell |
| `elite-four-door` | 3 | The Elite Four door guards, re-read on every league run |
| `fishing` | 3 | Rod cast results |
| `move-learn-result-ds` | 3 | Move learned / forgotten / not learned at the end of a battle, live client |
| `move-learned` | 3 | Move learned on level-up (not the forget prompt) |
| `exp-gained-ds` | 2 | EXP gained at the end of a battle, live client |
| `field-moves-ds` | 2 | Overworld move use in the live client -- Teleport, Sweet Scent, every HM |
| `evolution` | 1 | Evolution start, finish and cancel |
| | **705** | |

Everything else is left exactly as it is. Quest directions, trainer dialogue and
story beats still read normally — this is a speed mod, not a mute button.

## The {09} trick

A silenced line is not blanked, it is **erased**. The entry is replaced with
`{09}`, an argument placeholder nothing fills at that address, so the message
resolves to nothing and the client skips its box instead of drawing an empty one.

That is the difference between v1.1 and everything after it. v1.1 wrote a bare
newline, which is still a message: a run of empty boxes you tap through one by
one. Same taps, less information.

### Where that works, and where it does not

The right replacement is a property of the **call site**, and none of it is
visible in the dumps. This was settled on hardware over four
build-install-play cycles on 2026-08-30:

| call site | what works |
|---|---|
| Unova table 8 — every field move | `{09}` — the box is removed outright |
| Unova 15/42-43, 157/38-41 — EXP and move-learn | `\n\n` — a blank line |
| Unova tables 14, 172 and the rest of 15 | nothing; the text is left alone |

`{09}` and a blank line are **not** interchangeable. `{09}` is an argument
placeholder; where the engine never resolves it, the box sits there and visibly
drags the end of a battle out. An escaped newline pair is a well-formed empty
message that the engine moves straight through. Trying `{09}` everywhere is
exactly the mistake versions 1.3 to 1.6 made, three times.

Where SupersStrings has an opinion, this mod now follows it byte for byte —
`{09}` at 8/52-53, a blank at 15/42-43 and 157/38, 40, 41. That mod is run by
thousands of people, which makes it better evidence than anything derivable from
the dumps.

The one deliberate difference: Supers also blanks **157/32**, *"{00} wants to
learn {01}. However, it already knows four moves. Should a move be deleted?"*
Blanking that leaves an unlabelled Yes/No on a choice that costs you a move, so
it is left readable here. Add `[157, 32]` to `move-learn-result-ds` in
`rules.json` for exact parity.

Faint, the battle result, the level-up, the capture line and evolution are left
alone on purpose: nothing removes those boxes, so an empty one would cost the
same tap while telling you nothing. A `never_ds_tables` guard keeps the rules
written for the GBA ids from reaching them by accident — `catch-flow`,
`evolution` and `move-learned` all did.

### What it deliberately will not touch

`rules.json` carries a global `never` guard that no pattern can override:

* **Item and move descriptions** — 966 entries and ~96,000 characters in this
  corpus. They look like an enormous saving if you rank text by volume, but you
  *read* them on purpose; you never mash through them. Silencing them would gut
  the game while showing a big number.

  v1.1 silenced seven of them anyway. `status-battle` matched on the bare words
  `hurt by` and `is confused`, which appear in *"An attack move that inflicts
  double the damage if the user has been hurt by the target"* and in *"Raises
  evasion if the Pokémon is confused."* The battle rules are now pinned to the
  battle tables themselves — ids `200xxx` / `205xxx` on GBA, table 368 in the
  NDS archives — so a battle pattern cannot reach a description at all.
* **The nickname prompt** — carved out of `catch-flow` by an `exclude`.
  Silencing it leaves an unlabelled Yes/No on a decision that is annoying to
  undo.
* **Move learn / forget prompts** — you have to see which move you are
  replacing. Only the *"learned X"* confirmation is silenced.
* **The Repel re-apply prompt** (`{00} has worn off.\nUse another?`) — same
  reasoning. Only the older bare *"REPEL's effect wore off..."* lines go.
* **Story dialogue that happens to use counter words.** Mr. Fuji, Lorelei,
  Wally, the Day Care gossips and the Blend Master all say *"Thank you."* or
  talk about the Day Care. They are read once, not hundreds of times, so the
  prose rules are capped by length and a short `exclude_ids` list keeps the
  named offenders visible.

## It is generated, not hand-written

The mod is produced by `pmmod strings fasttext` from **your own client's**
`Settings → Utilities` dumps, driven by the 34 rules in `rules.json`:

```bash
pmmod strings fasttext mods/vanbobby-fast-strings \
    --dumps <client>/dump/strings \
    --rules ../../strings-work/rules.json \
    --langs en,es
```

That matters for three reasons:

* **Nothing is copied from anyone.** The text comes out of your install.
* **It survives client patches.** Re-run it instead of hand-fixing ids one by
  one. String ids move between updates; the rules do not.
* **Languages are free.** The same rules produce any language the client ships —
  add `--langs en,es,fr,pt-BR` and you get them all.

## About the Spanish support

PokeMMO translates its **UI** into eleven languages but not the **storyline** —
only 8 of Kanto's 3,607 storyline ids exist in the translated set, so Spanish
players read the English ROM text like everyone else.

That works in our favour: silencing is language-neutral, so one storyline file
covers every player, and Spanish only needs its own UI file. The mod ships six
files:

```
strings/strings_en_fasttext.xml     UI + GBA storyline, English
strings/strings_es_fasttext.xml     UI + GBA storyline, Spanish
strings/ds_fasttext_0_2.xml         storyline, Unova
strings/ds_fasttext_1_2.xml         storyline, Unova
strings/ds_fasttext_0_3.xml         storyline, Sinnoh
strings/ds_fasttext_0_4.xml         storyline, Johto
```

Not `data/strings/`: anything a mod ships under `data/` is a directory overlay,
and the client logs the undeclared form as deprecated even when `info.xml` lists
every file. That was v1.1's shape and it drew a dialog on startup.

Kanto and Hoenn are GBA regions whose storyline uses plain string ids, so their
entries are merged into the two UI files rather than needing archives of their
own.

## What 1.13 closed — every region, compared against itself

1.12 compared the three copies of the field-move script. 1.13 does it to the
whole corpus.

PokeMMO ships the same game text five times over: Kanto and Hoenn as plain ids,
Sinnoh, Johto and the two Unova archives as NDS coordinates. Group all 166,867
entries by text and ask where this mod silences a line in one region and leaves
it drawing in another. **Thirteen lines disagreed, in 60 places.**

| family | was drawing in | already silent in |
|---|---|---|
| shop and Pokécentre farewell | Sinnoh 217 ×11, 304/113, 310/10, 379/18, 430/20; Johto 96/113, 107/10, 108/10, 209/20, 267/21; Unova-1 348/4; Hoenn 271342245 | Hoenn 270896069 |
| Day Care, all four prompts | Unova-1 426/17, 426/26; Johto 439/22, 439/34, 439/41; Sinnoh 547/36; Kanto 1833017; Hoenn 271131465 | Sinnoh 547/16, 547/29 |
| move tutors, deleters, Rotom motors | Sinnoh 181/494/529/595/645/96; Johto 538/747/748/115; Unova-1 347/421/425 | UI 200003, Unova 157/41 |
| ferry boarding | Hoenn ×3 | UI 16780103 |
| Safari game over | Hoenn 271207462 | Sinnoh 538/0, Johto 427/0 |
| Safari Balls handed over | Johto 135/57 | Johto 135/4, Sinnoh 136/2 |
| shop greeting | Johto 40/38 | Sinnoh 213/37 |
| Multi Battle Room | Johto 96/21, Sinnoh 304/21 | Hoenn 270797574 |

**Unova-1 is one of the two archives the live client reads**, so its Day Care
lines were boxes real players were tapping.

Run it to a fixpoint. Closing a gap gives the next one a silenced twin to
disagree with — Johto's BP tutor (748) and the Ilex Forest Headbutt tutor (115)
only appeared on the second pass.

### The battle engine was guarded in one region out of three

`never_ds_tables` fenced Unova 14, 15, 157, 172 and 184 and nothing else. The
other regions ship the same engine unfenced, and Unova 13 — the per-move
`{00} used {01}!` announce, 1,680 entries — was never fenced anywhere. The
comparison derived the twins from the corpus rather than guessing: Unova 14, 15
and 172 are merged into the single table Sinnoh 368 / Johto 197, Unova 157 maps
to Sinnoh 453 / Johto 300, Unova 13 to Sinnoh 0 and Johto 3.

Nothing was being silenced in any of them, so this costs no coverage. It closes
the hole `catch-flow`, `evolution` and `move-learned` already fell into once, in
the one region that happened to be guarded afterwards.

### What was refused

A tutor rule was written for **Unova 204** — the Move Relearner and Deleter. It
reads like an NPC counter: POWER/ACCURACY/PP/TEACH menu labels, a Heart Scale
exchange. `test_only_proven_addresses_are_silenced_in_a_battle_engine` rejected
it, and the test is right. 204 is the relearner's copy of the move-learn state
machine, and that machine is the one place hardware already proved `{09}` does
not work — 157/38, 40 and 41 all had to become a blank line instead. The
reasoning that looks sound there is the reasoning that shipped 1.9.

It is now fenced in `never_ds_tables` too, so the rule engine and the test agree
about it. Unfencing needs someone to relearn a move with a build that touches it.

## What 1.12 closed — Teleport, and the check that finds the next one

Reported from hardware: **Sweet Scent was silent and Teleport still drew its
full box.** Both are field moves; from inside the game the difference looks
arbitrary.

It is not. Sweet Scent goes through the generic `{00} used\n{01}!` at Unova
8/52, silent since the first build. Teleport has a confirmation prompt —
*"Teleport to {00}, the last place you or your Pokémon rested?"* — and that line
exists in **Johto's** copy of the field-move script alone, at `211/27`. Nothing
pointed at it: no other archive has a twin to compare against, and
SupersSpeedStrings does not silence it either, so the parity suite scored a
clean run for six releases.

It is silenced now. This mod goes past the reference here: the destination is
whichever Pokémon Center you last healed at, you chose it, and every other
prompt in that table — Surf and Waterfall included — has been skipped since 1.2.

Every region ships the same field-move script in its own archive, which makes
the three copies each other's oracle. Comparing them found six more lines
silenced in one archive and still drawing in another:

| line | was drawing in | already silent in |
|---|---|---|
| `A deep fog drapes the area... Would you like to use Defog?` | Sinnoh 381/15 | Johto 211/17 |
| `{00} used Defog!` | Sinnoh 381/16 | Johto 211/18 |
| `{00} used Flash!` | Sinnoh 381/26 | Johto 211/28, Unova-1 280/27 |
| `It's a big boulder, but a Pokémon may be able to push it aside.` | Johto 211/9, Sinnoh 381/8 | Unova-1 280/8 |
| `Strength made it possible to move boulders around.` | Unova-1 280/9 | Sinnoh 381/9, Johto 211/10 |
| `{00}'s Strength made it possible to move boulders around!` | Unova-1 280/11 | Sinnoh 381/11, Johto 211/12 |

Plus two Defog statements (`211/19`, `381/17`) that match the Rock Climb ones
already silenced, and Johto `211/8`, the combined Strength line whose split
halves were both covered.

`tools/fieldmove_parity.py` is that comparison, and
`test_fieldmove_parity.py` fails the build on a new one. The reference cannot be
the only oracle — these archives are each other's.

The four errors in those tables still read normally: *"Surf can't be used if you
have someone with you."*, its Rock Climb twin, *"{01} was in the rubble!"* and
*"The boulder fell down!"* Each explains why something did or did not happen.

## What 1.11 closed

The parity suite scores this mod against SupersSpeedStrings by that mod's own
section comments, through a hand-written list of section names. That list is a
whitelist, and four repeated interactions were never on it — so the suite read
green while the reference silenced text this mod did not:

| where | what | now |
|---|---|---|
| Sinnoh 526/0-3 | the rest house on Route 209 — an old lady who offers a full heal | skipped |
| Sinnoh 538/0,1,3,4 | Great Marsh: the two Safari game-over calls, the Quick Tram prompt, the no-op after backing out | skipped |
| Kanto 1834011, 1834067 | the Safari PA — time up, out of balls | skipped |
| Kanto 16780100/103/104 | the inter-region ferry: greeting, boarding, cancel | skipped |

Four entries in those same families stay readable on purpose, and the reference
leaves three of them alone too:

* Sinnoh 538/2 — *"You're out of room for more Pokémon. Your Safari Game is
  over!"* explains why the run ended.
* Sinnoh 538/5 — *"Would you like to exit the Great Marsh right now?"* is the
  same decision as 136/9, which was already a deliberate keep.
* Kanto 16780102 — *"Your {STRING_0} will be sent to the PC. Is that okay?"* is
  a consequence you agree to.
* Kanto 16780105 — the PC-full refusal explains why the crossing did not happen.

The whitelist itself now names all four families, so the next gap of this shape
fails the suite instead of hiding in it. Adding a rule means adding the
reference's spelling of its section name there too.

## Tests

```bash
tools/verify-strings.sh                            # everything, including these
PYTHONPATH=modkit/src python3 -m unittest discover -s modkit/tests -t modkit
```

110 tests, stdlib only, no client and no device.

* `test_rules.py` — the rule engine on fixtures: token choice, id vs pattern
  precedence, the family and length guards, XML well-formedness, and the `--`
  in a comment that silently kills a mod.
* `test_corpus.py` — the behavioural contract against the real dumps. Named ids
  that must be silenced (every field move, the whole battle-end run, every HM
  prompt, the counters) and named ids that must not be (move descriptions,
  decision prompts, menu labels, story dialogue). Also that the shipped files
  in `data/strings/` are what the current rules produce, so a stale mod fails.
* `test_fieldmove_parity.py` — checks the field-move script against its own
  copies in the other archives. Unova-1 table 280, Sinnoh 381 and Johto 211 hold
  the same script, so a line silenced in one and drawing in another is an
  oversight. `tools/fieldmove_parity.py` prints the same report by hand.
* `test_region_parity.py` — the whole corpus against its own duplicates in the
  other regions. Six tests: no line silenced in one region and drawing in
  another, the comparison really finds the duplicates, every remaining
  disagreement is the battle engine, the engine is guarded in every region, the
  field-move table is *not* guarded, and the move relearner stays fenced.
  `tools/region_parity.py` prints the same report by hand.
* `test_supers_parity.py` — reads the local SupersSpeedStrings reference and
  asserts we cover every repeated-interaction line it covers, with an explicit,
  commented exception list for the handful we skip on purpose.

## Install

1. Mod Management → **Import Mod** → pick `vanbobby-fast-strings-1-13.mod`.
2. Enable it, save, restart.
3. Heal at a Pokémon Center — the counter dialogue should be gone.

Works alongside other strings mods. If two mods override the same id, the one
lower in the Mod Management list wins, so order accordingly.

## Known limits

* **Johto needs a workaround to regenerate.** PokeMMO's own dump utility aborts
  partway through with `An invalid XML character (Unicode: 0x0)` and never
  reaches region 4 on its own. Move `roms/3.nds` out of the client's roms folder
  first — it scans the folder and identifies ROMs by content, so neither the
  config key nor the extension controls what it loads — then repair the
  truncated output. Johto has been covered since 2026-08-30; it is the *dump*
  that is awkward, not the mod.
* **Prompts still show their box.** Erasing the text of a yes/no question
  leaves a box with the buttons intact and nothing above them. That is
  deliberate for things like "would you like to use Cut", and it is why move
  learn/forget, the nickname prompt and the Repel re-apply prompt are left
  alone.
* **The main Unova storyline archive still blanks rather than skips.** See
  "The {09} trick" above. Nothing published solves this today; the reference
  mod has the same limit in the same place.
* **Not everything SupersSpeedStrings removes.** That mod's own description is
  *"this build has NPC text removed"* — it silences the Bikers on Three Island,
  Celio, Oak, the school kids and several hundred other one-time story lines.
  This one covers the repeated interactions and leaves the story readable. The
  parity test in `modkit/tests/test_supers_parity.py` asserts we match it on
  every counter, field move and battle line, and that we stay well clear of the
  story set.
* Built against client r32920. After a big patch, re-run the generator.
