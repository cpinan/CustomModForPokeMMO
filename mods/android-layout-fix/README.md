# Android Layout Fix

**Type:** theme mod · **Platform:** Android / handhelds · **Client:** r32920, theme revision 8

## What it does

Stops the client warning *"A UI layout loop issue was detected. You may
experience reduced performance or lag."* from firing every time you open
**Settings** on the Android client.

## The bug

PokeMMO's own Android theme, in `data/themes/android/ui/android-settings.xml`,
gives the settings scroll pane two width bounds that contradict each other:

```xml
<theme name="settings-scrollpane" ref="scrollpane">
    <param name="minWidth"><int>1080</int></param>
    <param name="maxWidth"><int>800</int></param>
```

They look transposed. The **minimum** is what actually breaks it: 1080px is
wider than that widget can ever be given once the left tab strip and the borders
are taken out of the screen. The layout pass therefore never settles — TWL (the
UI toolkit) retries a fixed number of times, gives up, and logs
`layout loop detected - printing`. The client turns that into the warning, and
you feel it as lag.

The desktop theme has sane values for the same widget: `minWidth 500`,
`maxWidth 32767`.

## The fix

One file replaced, bounds swapped back:

```xml
<param name="minWidth"><int>800</int></param>
<param name="maxWidth"><int>1080</int></param>
```

`theme/theme.xml` pulls the other 51 stock theme files straight from
`/data/themes/android/` by absolute path, so this mod only ever owns the one
file it needs to change and client updates to everything else still apply.

## How it was verified

On a Retroid Pocket G2 (Android 15), reading logcat before and after:

| `settings-scrollpane` | result |
|---|---|
| `min 1080 / max 800` (stock) | loops |
| `min 1080 / max 32767` | still loops — so `min > max` was not the cause |
| `min 500 / max 32767` | no loop, but the controls are visibly squeezed |
| **`min 800 / max 1080`** | **no loop, layout renders correctly** |

The loop was also reproduced with every other mod disabled, which is what proves
it belongs to the client's theme and not to anything the player installed.

## Install

1. Mod Management → **Import Mod** → pick `android-layout-fix-1-0.mod`.
2. Enable it, save, restart.
3. **Settings → Interface → Theme → Android Layout Fix**, then restart once more.

A theme only takes effect once it is selected — enabling the mod alone does
nothing.

## Notes

* Declares `is_mobile="true"`. The Android client refuses a desktop-only theme.
* If a client update changes the theme revision, this mod stops loading until
  `theme_revision` in `info.xml` is bumped to match `Client Theme Revision` at
  the top of `log/mods.log`.
* Ideally this mod becomes unnecessary — it is a two-number change on PokeMMO's
  side.
