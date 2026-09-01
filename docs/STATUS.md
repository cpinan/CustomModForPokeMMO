# STATUS — CustomModForPokeMMO

_Last updated: 2026-09-01 · branch `main`, pushed · everything below is committed_

## Next action

**Play with `vanbobby-fast-strings-1-13.mod` installed and report what still talks.**
1.13 silences 705 entries, up from 572 at 1.10, and none of the 133 new ones has
been seen in game. The two worth watching first are the Day Care lines in the
Unova-1 archive (`426/17`, `426/26`) and the move tutors, because that archive is
one of the two the live client actually reads.

Behind that: the FireRed theme is at 0.50 and its bag, trainer card, dex and
summary read like FireRed's. The battle menu is the next screen and it is
blocked on the font.

## State

- **`vanbobby-fast-strings` is 1.13.** 705 entries across 34 rules, covering
  Kanto, Hoenn, Sinnoh, Johto and both Unova archives. 1.10 is kept in `dist/`
  as the last version confirmed on hardware.
- **`modkit/` ships now** (OPEN-WORK 5, closed). A reader can regenerate the mod
  and run all 110 tests. `strings-work/dumps/` deliberately does not ship — it is
  the game's own text, and generating from your own dumps is the whole design.
  `MODEXAMPLES/` does not ship either; it is someone else's mod.
- **The regions are each other's oracle.** The same text ships five times over,
  so a line silenced in one region and drawing in another is a bug no comparison
  against another mod can find. `tools/region_parity.py` reports them,
  `test_region_parity.py` fails the build on one. This is what finally caught
  Teleport, which had drawn a full box for six releases with a green suite.
- **The battle-engine guard covers every region now**, not just Unova, and Unova
  table 13 — 1,680 `{00} used {01}!` lines — is fenced for the first time.
  Nothing was being silenced there, so it cost no coverage.
- **The FireRed theme is 0.50 and shipped.** Its 26 intermediate builds stay on
  disk and out of git; `.gitignore` keeps `dist/vanbobby-firered-theme-0-*.mod`
  except the released one.
- **110 tests**, stdlib only, no client and no device. They skip cleanly without
  the dumps.
- **What changed when is in `CHANGELOG.md`**, grouped by date and named by mod. Record
  releases there rather than starting a second history in a mod's own README.

## In flight

Nothing half-finished. Open questions are enumerated in **`docs/OPEN-WORK.md`**,
written for someone arriving cold. The two that matter:

- **Item 7 — the Move Relearner (Unova 204) is fenced, not decided.** A tutor
  rule was written for it on 2026-09-01 and the invariant test refused it,
  correctly: it is the relearner's copy of the move-learn state machine, the one
  place hardware already proved `{09}` does not work. Closing it needs one
  build and one relearned move.
- **Item 8 — Elite Four and Gym Leader dialogue stays out of scope.** 162 NDS
  entries the reference silences and this mod does not. Reconsidered and kept
  out on 2026-09-01, but it is the one worth revisiting: PokeMMO's Elite Four is
  re-run daily.

## Verify

```bash
tools/verify-strings.sh   # every mod source + 110 tests (needs no client)
tools/verify.sh           # the FireRed theme's own generators and invariants
```
