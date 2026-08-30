# Bobby Fast Strings

**Type:** strings mod · **Languages:** English + Spanish · **Client:** r32920 · **Version:** 1.6

## What it does

Removes the text from the interactions you repeat hundreds of times a day, so
the box goes away instead of making you mash through it.

| rule | entries | what it covers |
|---|---|---|
| `status-battle` | 50 | faint, paralysis, burn, sleep (GBA tables, inert on the live client) |
| `mart` | 45 | shop purchase and sale flow |
| `battle-frontier` | 43 | Battle Tower / Palace / Arena / Factory reception |
| `battle-end` | 37 | the end-of-battle run (GBA tables, inert on the live client) |
| `pokecenter` | 37 | Nurse Joy / healing counter |
| `daycare` | 31 | deposit, retrieval, egg hand-off |
| `shop-extra` | 29 | remaining shop counter lines |
| `move-learned` | 26 | move learned on level-up |
| `counters-ds-sinnoh` | 22 | Sinnoh archive: Great Marsh gate, league door, Pokecenter, shop, Day Care |
| `hm-field-prompts` | 20 | every HM obstacle: tree, boulder, rock, waterfall, dive, surf |
| `hm-prompts-ds-sinnoh` | 18 | Sinnoh archive: HM obstacle prompts and their `used <move>` line |
| `hm-prompts-ds-unova1` | 17 | Unova storyline archive: same prompts plus Flash, Teleport, Dig |
| `safari-gate` | 17 | Safari Zone entry and sign-out |
| `field-moves` | 15 | every overworld move (GBA tables, inert on the live client) |
| `fossil-reviver` | 15 | fossil revival counter |
| `move-tutor` | 15 | Move Master, Move Maniac, Special Move Tutor |
| `stylist` | 10 | personal stylist and the bike-skin counter |
| `field-move-prompts` | 9 | the "would you like to use Cut?" confirmations |
| `catch-flow` | 8 | Gotcha! / broke free |
| `berry-farming` | 6 | soil, planting, watering, picking |
| `evolution` | 5 | evolution start, finish and cancel |
| `breeder` | 4 | Day-care Breeder trade-in |
| `repel` | 4 | wear-off |
| `elite-four-door` | 3 | the league door guards |
| `field-moves-ds` | 2 | Teleport, Sweet Scent and every HM — the box is removed outright |
| `fishing` | 2 | rod cast results |
| | **490** | |

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
`Settings → Utilities` dumps, driven by the twenty-two rules in `rules.json`:

```bash
pmmod strings fasttext mods/bobby-fast-strings \
    --dumps <client>/dump/strings \
    --rules rules.json \
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
covers every player, and Spanish only needs its own UI file. The mod ships five
files:

```
data/strings/strings_en_fasttext.xml     UI, English
data/strings/strings_es_fasttext.xml     UI, Spanish
data/strings/ds_fasttext_0_2.xml         storyline, Unova
data/strings/ds_fasttext_1_2.xml         storyline, Unova
data/strings/ds_fasttext_0_3.xml         storyline, Sinnoh
```

Kanto and Hoenn are GBA regions whose storyline uses plain string ids, so their
entries are merged into the two UI files rather than needing archives of their
own. Johto is missing because the client's dump utility crashes before reaching
it — see below.

## Tests

```bash
tools/verify.sh                                    # everything, including these
PYTHONPATH=modkit/src python3 -m unittest discover -s modkit/tests -t modkit
```

48 tests, stdlib only, no client and no device.

* `test_rules.py` — the rule engine on fixtures: token choice, id vs pattern
  precedence, the family and length guards, XML well-formedness, and the `--`
  in a comment that silently kills a mod.
* `test_corpus.py` — the behavioural contract against the real dumps. Named ids
  that must be silenced (every field move, the whole battle-end run, every HM
  prompt, the counters) and named ids that must not be (move descriptions,
  decision prompts, menu labels, story dialogue). Also that the shipped files
  in `data/strings/` are what the current rules produce, so a stale mod fails.
* `test_supers_parity.py` — reads the local SupersSpeedStrings reference and
  asserts we cover every repeated-interaction line it covers, with an explicit,
  commented exception list for the handful we skip on purpose.

## Install

1. Mod Management → **Import Mod** → pick `bobby-fast-strings-1-2.mod`.
2. Enable it, save, restart.
3. Heal at a Pokémon Center — the counter dialogue should be gone.

Works alongside other strings mods. If two mods override the same id, the one
lower in the Mod Management list wins, so order accordingly.

## Known limits

* **No Johto coverage.** PokeMMO's own dump utility aborts partway through with
  `An invalid XML character (Unicode: 0x0)` on Sinnoh, and never reaches Johto.
  Sinnoh was recovered by repairing the truncated file; Johto simply is not in
  the dump. Unloading the Sinnoh ROM before dumping may let the run get there.
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
