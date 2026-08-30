# Bobby Fast Strings

**Type:** strings mod · **Languages:** English + Spanish · **Client:** r32920

## What it does

Removes the text from the interactions you repeat hundreds of times a day, so
the box advances instantly instead of making you mash through it.

| rule | entries | what it covers |
|---|---|---|
| `status-battle` | 113 | faint, paralysis, burn, sleep, confusion, recoil — the most repeated text in the game |
| `shop-extra` | 111 | remaining shop counter lines |
| `mart` | 70 | shop purchase and sale flow |
| `pokecenter` | 47 | Nurse Joy / healing counter |
| `daycare` | 28 | deposit, retrieval, egg hand-off |
| `exp-messages` | 27 | experience and level-up chatter |
| `catch-flow` | 17 | *Gotcha!* / *broke free* — fires on every ball you throw |
| `evolution` | 16 | evolution start, finish and cancel |
| `repel` | 14 | wear-off and re-apply prompt |
| `hm-field-moves` | 10 | Cut / Surf / Strength / Rock Smash prompts |
| `move-learned` | 6 | move learned on level-up |
| `fishing` | 4 | rod cast results |
| | **463** | |

Everything else is left exactly as it is. Quest directions, trainer dialogue and
story beats still read normally — this is a speed mod, not a mute button.

### What it deliberately will not touch

`rules.json` carries a global `never` guard that no rule can override:

* **Item and move descriptions** — 966 entries and ~96,000 characters in this
  corpus. They look like an enormous saving if you rank text by volume, but you
  *read* them on purpose; you never mash through them. Silencing them would gut
  the game while showing a big number.
* **The nickname prompt** — carved out of `catch-flow` by an `exclude`.
  Silencing it leaves an unlabelled Yes/No on a decision that is annoying to
  undo.
* **Move learn / forget prompts** — you have to see which move you are
  replacing. Only the *"learned X"* confirmation is silenced.

## It is generated, not hand-written

The mod is produced by `pmmod strings fasttext` from **your own client's**
`Settings → Utilities` dumps, driven by the six regexes in `rules.json`:

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

## Install

1. Mod Management → **Import Mod** → pick `bobby-fast-strings-1-0.mod`.
2. Enable it, save, restart.
3. Heal at a Pokémon Center — the counter dialogue should be gone.

Works alongside other strings mods. If two mods override the same id, the one
lower in the Mod Management list wins, so order accordingly.

## Known limits

* **No Johto coverage.** PokeMMO's own dump utility aborts partway through with
  `An invalid XML character (Unicode: 0x0)` on Sinnoh, and never reaches Johto.
  Sinnoh was recovered by repairing the truncated file; Johto simply is not in
  the dump. Unloading the Sinnoh ROM before dumping may let the run get there.
* **Prompts still show their box.** Silencing the text of a yes/no question
  leaves an empty box with the buttons intact. That is deliberate for things
  like "would you like to use Cut", but it is why move learn/forget is left
  alone in v1.
* Built against client r32920. After a big patch, re-run the generator.
