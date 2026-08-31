#!/bin/sh
# Proves the FireRed theme still builds and still holds its invariants.
# No client run, no device, no login.
set -e
cd "$(dirname "$0")/.."

echo "== regenerate every asset from source =="
python3 tools/build_firered_fonts.py
python3 tools/build_firered_atlas.py
python3 tools/build_firered_splash.py
python3 tools/build_firered_loginbg.py --scene

echo
echo "== invariants =="
python3 tools/test_firered_theme.py 2>&1 | tail -3

echo
echo "== nothing drifted =="
git diff --stat -- mods/vanbobby-firered-theme || true
echo "(a non-empty diff above means a generator no longer reproduces what is committed)"
