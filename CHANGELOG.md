# Changelog

Eight mods share this repository and version independently, so entries are grouped by date
and named by mod. Newest first.

`dist/` carries exactly one artifact per mod: the current build, nothing else. Older
releases are reachable through this file and `git log` — for example
`git show eeebf9a:dist/vanbobby-fast-strings-1-10.mod > 1-10.mod` recovers 1.10, the last
version confirmed on hardware.

---

## 2026-09-01

### VanBobby Fast Strings 1.10 → 1.13

572 silenced entries → **705**, across Kanto, Hoenn, Sinnoh, Johto and both Unova archives.
34 rules. Three releases in one day, each closing a different kind of blind spot.

**1.11 — four counter families the parity test could not see.** The suite scored this mod
against SupersSpeedStrings through `IN_SCOPE`, a hand-written list of the reference's own
section names. A family nobody had named scored as *out of scope* and vanished from the
report, so the run stayed green while the reference silenced text this mod did not.

- Route 209 rest house — the old lady who offers a full heal (Sinnoh `526/0-3`)
- Great Marsh — both Safari game-over calls, the Quick Tram prompt, the cancel no-op
  (Sinnoh `538/0,1,3,4`)
- The Safari PA — time up, out of balls (Kanto `1834011`, `1834067`)
- The inter-region ferry — greeting, boarding, cancel (`16780100/103/104`)

`IN_SCOPE` now names all four. One trap found on the way: a bare `Marsh` also matches
`Marsh`**`al`**, which quietly pulled the whole Elite Four into scope.

**1.12 — Teleport, reported from real play.** Sweet Scent was silent and Teleport still
drew its full box. Sweet Scent goes through the generic `{00} used\n{01}!` at Unova `8/52`
and had been silent since the first build; Teleport has a confirmation prompt that exists
in **Johto's copy of the field-move script alone**, at `211/27`. No sibling table
contradicted it and the reference does not silence it either, so nothing could point at it.
Silenced now — the destination is whichever Pokémon Center you last healed at, and every
other prompt in that table has been skipped since 1.2.

Every region ships the same field-move script, which makes the three copies each other's
oracle. Comparing them found six more lines silenced in one archive and drawing in another:

| line | was drawing in | already silent in |
|---|---|---|
| `Would you like to use Defog?` | Sinnoh `381/15` | Johto `211/17` |
| `{00} used Defog!` | Sinnoh `381/16` | Johto `211/18` |
| `{00} used Flash!` | Sinnoh `381/26` | Johto `211/28`, Unova-1 `280/27` |
| boulder statement | Johto `211/9`, Sinnoh `381/8` | Unova-1 `280/8` |
| `Strength made it possible…` | Unova-1 `280/9` | Sinnoh `381/9`, Johto `211/10` |
| `{00}'s Strength made it…` | Unova-1 `280/11` | Sinnoh `381/11`, Johto `211/12` |

**1.13 — the same idea, applied to all 166,867 entries.** PokeMMO ships its text five times
over: Kanto and Hoenn as plain ids, Sinnoh, Johto and the two Unova archives as NDS
coordinates. Grouping every entry by text and diffing each group against itself found
**thirteen lines silenced in one region and drawing in another, in sixty places** — the shop
and Pokécentre farewell, all four Day Care prompts, the move tutors and deleters, the
ferry, the Safari PA, the Multi Battle Room, the shop greeting.

Eight of those sixty are in **Unova-1, one of the two archives the live client reads**, so
its Day Care lines were boxes real players were tapping.

Run to a fixpoint, not once: closing a gap gives the next one a silenced twin to disagree
with, and two tutor tables only appeared on the second pass.

**Also in 1.13 — the battle engine is fenced in every region.** `never_ds_tables` covered
Unova and only Unova, while Sinnoh and Johto ship the same engine unguarded and Unova table
13 — 1,680 lines of `{00} used {01}!` — was fenced nowhere at all. The twins were derived
from the corpus rather than guessed: Unova 14, 15 and 172 are merged into the single table
Sinnoh 368 / Johto 197; Unova 157 maps to Sinnoh 453 / Johto 300; Unova 13 to Sinnoh 0 and
Johto 3. Nothing was being silenced in any of them, so this cost no coverage — it closes the
hole `catch-flow`, `evolution` and `move-learned` already fell into once, in the one region
that happened to get guarded afterwards.

**One rule was written and withdrawn.** Unova table 204 reads exactly like an NPC counter —
POWER/ACCURACY/PP/TEACH labels, a Heart Scale exchange — and
`test_only_proven_addresses_are_silenced_in_a_battle_engine` refused it. The test was right:
204 is the Move Relearner's copy of the move-learn state machine, and that machine is the
one place hardware already proved `{09}` does not work. Fenced in both places now; see
`docs/OPEN-WORK.md` item 7 for what would unfence it.

**Fixed:** the shipped `rules.json` was a 1.0-era stub still claiming every match becomes an
escaped newline — wrong for three versions. The mod's README claimed v1.6, 490 entries,
`data/strings/` paths and no Johto coverage; all false. The mod icon in this repo was the
pre-rename **BF** art, and 1.10 shipped with it.

### VanBobby FireRed Theme 0.24 → 0.50

Twenty-six build-and-look rounds. The bag, trainer card, Pokédex and summary now read like
FireRed's — their own screens and their own layouts, with the atlas and fonts regenerated
from source each round rather than hand-patched. The battle menu is next and is blocked on
the font.

Tooling that made it tractable instead of another speculative build: `tools/theme_lint.py`
resolves every declared path and reports what nothing reaches, `tools/preview_firered.py`
renders the art offline, and `tools/probe_paths.py` paints six candidate theme paths in six
colours so one screenshot answers six questions — it found the battle name widget after four
single guesses had missed.

`docs/reference-shots/battle/` records what the real game looks like, so the next round
compares against something fixed.

### The toolkit ships

`modkit/` and `strings-work/rules.json` are in the repository now, closing `docs/OPEN-WORK.md`
item 5. A reader can regenerate the strings mod and run all 110 tests.

Deliberately still absent, both in `.gitignore`:

- **`strings-work/dumps/`** — about 166,000 entries of the game's own text. Generating the
  mod from *your* install's dumps instead of shipping a corpus is the entire design.
  Produce them with `Settings → Utilities`. Without them the corpus, cross-region and
  parity suites skip and say so; the rule-engine tests, validation and every build still run.
- **`MODEXAMPLES/`** — SupersSpeedStrings, kept locally as a reference to measure against.
  It is someone else's mod.

New checks, both wired into `tools/verify-strings.sh`:

```bash
tools/fieldmove_parity.py   # the three copies of the field-move script, against each other
tools/region_parity.py      # all 166,867 entries, against their duplicates in other regions
```

Test count 99 → **110**. `test_fieldmove_parity.py` (4) and `test_region_parity.py` (6) are
new. Both were checked against deliberate regressions rather than trusted for passing.

### `dist/` holds one artifact per mod

Fifty-three superseded artifacts removed in two passes: six built before every mod took
the `vanbobby-` prefix, the FireRed theme's 0.2 through 0.49, and Fast Strings 1.10.

`theme-iterate.sh` writes every build here, so `.gitignore` keeps
`dist/vanbobby-firered-theme-0-*.mod` out of git with an exception for the released
version — **bump that exception when the theme ships a new one.** The intermediate builds
accumulate silently and are worth pruning again when they do.

---

## 2026-08-31

### VanBobby FireRed Theme 0.25 → 0.49

Bag, trainer card and Pokédex layout work, iterating against real FireRed screenshots.
Unreleased at the time; folded into 0.50.

---

## 2026-08-30

### VanBobby Fast Strings 1.7 → 1.10

- **1.7** — target the archive the client actually reads. 1.2 had silenced the GBA battle
  tables perfectly and changed nothing on screen.
- **1.9** — Johto coverage, and two silent coverage holes closed. **Pulled the same day:**
  blanking Unova `15/1` meant a wild battle never loaded and the session had to be
  restarted. `15/42` accepts a blank and `15/1` does not — same table, same archive, same
  token, opposite outcome. That is why a table is not a call site.
- **1.10** — `never_ds_tables` added, keeping every rule out of the NDS battle engines.
  Confirmed on hardware: singles load, field moves print nothing, EXP is an empty box, move
  learn is silent.

Which replacement token works at which call site is written up in
`docs/FINDING-string-call-sites.html`. `{09}` and `\n\n` are not interchangeable, and an
empty `<string/>` is read as *no override* — the client's own text comes back.

### VanBobby Region Label Unpad 1.1, VanBobby Demo Strings 1.1

Stopped shipping strings under `data/`. Anything a mod ships there is a directory overlay and
the client logs the undeclared form as deprecated even when `info.xml` lists every file.

A global `sed` during that bump corrupted both `info.xml` declarations to
`<?xml version="1.1"?>`; fixed the same day, and `pmmod validate` now warns on any non-1.0
declaration.

### Every mod renamed

All eight carry the `vanbobby-` prefix — directory, `info.xml` display name and built
artifact. **Anyone with an older build installed must re-import:** the client keys enabled
mods by filename.

### VanBobby FireRed Theme 0.0 → 0.24

From an empty archive to the login screen, in-game surfaces, battle HP plate, NPC dialogue
and the first three of its own screens. Along the way: the 3D login backdrop, which had been
called impossible here and was not; a painted-scene backdrop; generated font overrides
instead of hand-listed ones; and the rule that a face gets an outline or a shadow, never both.

---

## 2026-08-29

Repository opened.

- **VanBobby Android Layout Fix 1.0** — stops the UI layout loop. The stock Android theme
  ships `settings-scrollpane minWidth 1080 / maxWidth 800`, which loops the settings screen
  on handhelds. Written up in `docs/FINDING-layout-loop.md`.
- **VanBobby Region Label Unpad 1.0** — fixes the Pokédex loop on Sinnoh and Unova.
- **VanBobby Stadium 2 Battle Sprites 1.0** — Pokémon Stadium 2 battle sprites.
- **VanBobby Only Shiny Sprites 1.0** — hides every non-shiny in battle, enemy side only.
- **VanBobby Shiny Scale Probe 1.0** — a throwaway diagnostic.
- **VanBobby Demo Strings 1.0** — a worked example.
- **Fast Strings 1.1** — 186 → 463 entries, with the first `never` guard. Its generated XML
  comment made the mod unloadable; fixed the same day. A `--` inside an XML comment is fatal
  and the client says nothing useful about it.
