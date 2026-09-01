# pmmod — PokeMMO mod workbench

One command line for the whole loop: scaffold → validate → build → install →
enable → restart → read the log → package for the forum.

```bash
export PATH="$PWD/modkit/bin:$PATH"      # or symlink modkit/bin/pmmod into ~/bin
pmmod doctor
```

Python 3.9+. Pillow is optional and only used by the image commands.
The client is auto-detected; override with `--client <path>` or `POKEMMO_HOME`.

## The loop

```bash
pmmod new "My Sprites" mods/my-sprites --kind battlesprites
# ... drop files in ...
pmmod validate mods/my-sprites          # every rule the loader enforces
pmmod test     mods/my-sprites          # build + install + enable + verbose log
pmmod run                               # launch the client
pmmod log                               # "my-sprites-1-0.mod applied."
pmmod release  mods/my-sprites -o dist  # .mod + sha256 + forum post draft
```

## Commands

| Command | Does |
|---|---|
| `doctor` | client path, revisions, enabled mods, verbose flag, Pillow |
| `spec` | the whole mod format reference, printed |
| `new NAME [DIR] --kind K` | scaffold a valid mod (`battlesprites`, `monstericons`, `itemicons`, `overworld`, `trainers`, `cries`, `sounds`, `strings`, `theme`, `overlay`, `empty`) |
| `validate PATH…` | lint a folder or a `.mod`; non-zero exit on errors |
| `build PATH` | pack to `.mod`, refusing to ship a broken archive |
| `install PATH [--enable]` | copy into `data/mods/`, optionally flip it on |
| `enable/disable/uninstall NAME` | edit `client.mods.enabled_mods` for you |
| `test PATH` | validate + build + install + enable + verbose logging |
| `run [--mobile] [--theme X]` | launch the client; `--mobile` forces the Android theme so handheld UI bugs reproduce here |
| `log [--grep RX] [-v]` | what the client discovered, applied, and choked on |
| `diagnose [--context]` | match the logs against known theme/mod failures and name the fix |
| `pull-logs [--ssh user@host] [--downloads]` | copy a handheld's logs here over adb or ssh, then diagnose them |
| `release PATH -o dist` | archive + SHA-256 + forum post + release checklist |
| `dump` | how to make the client dump its own moddable assets |
| `probe-revisions` | make the client log the string/theme revisions it accepts |
| `strings find RX` | search the client's text for a phrase → string ids |
| `strings extract --ids … [--silence] -o F` | build an override xml (`--silence` = the "fast text" trick) |
| `sprites inspect PATH…` | size / frame count / mode per image |
| `sprites rescue OLD NEW` | rename a legacy sprite mod into the current layout |
| `theme scaffold DIR [--base android]` | copy a stock theme as a starting point |
| `theme lint [PATH…]` | find contradictory min/max bounds — the thing that makes TWL loop |

## What `validate` catches

The rules come from the client binary's own message table, so the linter and the
loader agree. Representative codes:

`NESTED` info.xml one folder deep · `NOINFO` no info.xml · `EXT` extension not
allowed in that directory · `NAME` filename does not match the grammar ·
`GIFFRAME` animated GIF carrying a frame id · `REGION` region id outside
`0/1/2/3/10` · `THEMEREV` missing `theme_revision` · `THEMENAME` theme called
`default`/`android` · `OVLMISS` declared overlay not in the archive ·
`OVLUNDECLARED` overlays `data/` without saying so · `WEBLINK` link is not on
forums.pokemmo.com · `EGGCOUNT` egg set is not a multiple of 6.

Sanity check: it reports the shipped `data/resources.zip` and `example_mod.zip`
as clean.

## Notes

* `client.mods.enabled_mods` separates entries with `/`, not commas. `pmmod`
  handles the escaping; back the file up before hand-editing it.
* Battle sprites are resolved lazily, so verbose logging shows per-file lines for
  preloaded content (icons, overworld, sounds) but not for battle sprites. For
  those, `<mod> applied.` plus seeing them in a battle is the confirmation.
* An unzipped folder in `data/mods/` loads too — handy while iterating.
* The Android client is package `eu.pokemmo.client` and keeps its whole tree in
  internal private storage, so `adb pull` cannot reach its logs on a stock
  device. `pmmod run --mobile` renders the same Android theme on the desktop,
  where the logs are readable — that is usually the faster way to chase a
  handheld UI bug.
* `PokeMMO.sh` execs the binary **without forwarding arguments**, so `pmmod run`
  calls `bin/<os>/<arch>/PokeMMO` directly whenever a flag is passed.

See `../docs/MODDING.md` for the format itself and where every rule came from.
