# STATUS — CustomModForPokeMMO

_Last updated: 2026-09-02 · branch `main`, pushed · 1.16 confirmed on the Retroid_

## Next action

**Install the staged battle probe and answer one question: does a blank line
work at the end of a battle?**

`vanbobby-fast-strings-1-17-probe.mod` is already on the SD card at
`/storage/EAFF-F713/Download/`. It is 1.16 plus eight blanked addresses in
Unova-0 table 15 — `44-50`, the battle-result lines, and `65`, `Gotcha! {00}
was caught!`. Same table, same call site and same token as `15/42-43`, the EXP
lines that already work, which is the whole argument for trying it.

Import it, delete the 1.16 entry, save, restart, then:
1. Win a trainer battle — no `Player defeated X!` box.
2. Catch something — no `Gotcha!` box.
3. **The battle still loads.** That is the failure mode that matters: blanking
   table 15's *start* entries hung a wild encounter on 2026-08-30 and cost the
   session.

If it holds, the probe becomes 1.17: move the rule into `rules.json` and add the
eight addresses to `DS_PROVEN_IN_ENGINE` in `test_corpus.py` with hardware as the
reason. If it hangs, reinstall `vanbobby-fast-strings-1-16.mod` from the same
folder and record the answer in `docs/OPEN-WORK.md` — a no is worth as much as a
yes here, and nobody has to ask again.

Table 14 — the per-turn faint and status chatter — stays unknown either way, and
`probe-faint-ds` in `rules.json` is the one-address experiment that would answer
it. It is the riskier of the two: table 14 is the in-battle state machine.

**Confirmed on hardware 2026-09-02, nothing left to check here:** every HM acts
with no box (Strength, Rock Smash, Cut, Flash, Rock Climb, Whirlpool, Defog,
Headbutt, Surf, Waterfall, Dive), Sweet Scent, Fly and Teleport are silent, a
Repel reports itself, and the Secret Power obstacles are quiet.

Install on this device goes through the **SD card**: the Import picker browses
`/storage/EAFF-F713/Download`, not `/sdcard/Download`. Pushing to internal
storage puts the file somewhere the picker never shows.

Behind that: 1.13's 133 new entries have still never been seen in game — the Day
Care lines in the Unova-1 archive (`426/17`, `426/26`) and the move tutors are the
ones worth watching, that archive being one of the two the live client reads.

Behind that: the FireRed theme is at 0.50 and its bag, trainer card, dex and
summary read like FireRed's. The battle menu is the next screen and it is
blocked on the font.

## State

- **`vanbobby-fast-strings` is 1.16.** 709 entries across 35 rules, covering
  Kanto, Hoenn, Sinnoh, Johto and both Unova archives. `dist/` holds one artifact
  per mod and nothing else; recover an older one from git, e.g.
  `git show eeebf9a:dist/vanbobby-fast-strings-1-10.mod > 1-10.mod` for the last
  build confirmed on hardware.
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
- **Client-written text is its own address space, and `{STRING_nnnnnn}` is how you
  find it.** No dumped ROM line carries that slot, so every entry that does is one
  PokeMMO wrote — the field-move box, the Secret Power obstacles, the breakable
  rock. Grep for it before reaching for another archive rule.
- **A field move's box is `16780155`, not a ROM address.** PokeMMO writes
  `{00}'s summoned {02} used {03}!` itself. Three releases of archive-level work
  could not remove it because no archive holds it; the reference silences exactly
  this id. When a message survives full parity with the reference, look in the
  plain ids for a line PokeMMO wrote.
- **The three ids 1.14 gave back are the client's own toasts**, not ROM boxes:
  `You have used {00}.`, its stacked twin, and `{00} used {01}! (PP Remaining…)`.
  SupersSpeedStrings silences none of them. `test_the_clients_own_notices_are_left_alone`
  keeps them visible.
- **113 tests**, stdlib only, no client and no device. They skip cleanly without
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
