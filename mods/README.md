# Mod sources

Each folder is a mod **source tree**: the files exactly as they sit inside the
`.mod` archive. Zip the *contents* of a folder (not the folder itself) to build
one, or use `pmmod build <folder>`.

| Folder | What it is |
|---|---|
| `android-layout-fix/` | Theme mod. Fixes the "UI layout loop" on Android/handhelds. |
| `region-label-unpad/` | Strings mod. Restores plain region names. |
| `only-shiny-sprites/` | Battle sprites. Hides every non-shiny so a shiny is unmissable. |
| `shiny-scale-probe/` | Throwaway test mod. Answers whether the scale tables work on ROM sprites. |
| `stadium-battlesprites/` | Battle sprites rendered from Pokémon Stadium 2 models. |
| `demo-strings/` | Two-line example showing how a strings mod is put together. |

Every folder has its own README with the full write-up.
