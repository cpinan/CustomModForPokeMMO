#!/bin/sh
# Rebuild the FireRed theme, reinstall it, restart the macOS client, and prove
# from the client's own log whether the theme loaded. Then screenshot the login
# screen, which is the deepest UI reachable without logging in.
#
#   tools/theme-iterate.sh [MOD_DIR] [OUT_PNG]
#
# Never touches the LOGIN button or gameplay -- login is manual, always.
set -e
cd "$(dirname "$0")/.."

MOD="${1:-mods/vanbobby-firered-theme}"
OUT="${2:-/tmp/firered-login.png}"
CLIENT="$HOME/Library/Application Support/com.pokeemu.macos/pokemmo-client-live"
NAME="$(basename "$MOD")"
VER="$(sed -n 's/.*<resource [^>]*version="\([^"]*\)".*/\1/p' "$MOD/info.xml" | tr '.' '-')"
ARCHIVE="$NAME-$VER.mod"

echo "== build =="
find "$MOD" -name '.DS_Store' -delete
rm -f "dist/$ARCHIVE"
( cd "$MOD" && zip -qr "$OLDPWD/dist/$ARCHIVE" . -x '.*' -x '*/.*' )
echo "   dist/$ARCHIVE  $(du -h "dist/$ARCHIVE" | cut -f1)"

echo "== install =="
rm -f "$CLIENT/data/mods/$NAME"-*.mod
cp "dist/$ARCHIVE" "$CLIENT/data/mods/"
echo "   -> data/mods/$ARCHIVE"

# The client keys enabled mods by FILENAME, and the filename carries the version.
# Bump the version without rewriting this line and the new archive ships disabled,
# which looks exactly like a theme that stopped working.
PROPS="$CLIENT/config/main.properties"
python3 - "$PROPS" "$NAME" "$ARCHIVE" <<'PYEOF'
import re, sys
props, name, archive = sys.argv[1], sys.argv[2], sys.argv[3]
text = open(props).read()
line = re.search(r'^client\.mods\.enabled_mods=(.*)$', text, re.M)
mods = [m for m in (line.group(1).split('/') if line else []) if m and not m.startswith(name)]
mods.append(archive)
new = 'client.mods.enabled_mods=' + '/'.join(mods)
text = re.sub(r'^client\.mods\.enabled_mods=.*$', new.replace('\\', '\\\\'), text, flags=re.M)
open(props, 'w').write(text)
print("   enabled: " + '/'.join(mods))
PYEOF

echo "== restart client =="
# PokeMMO.sh does `cd "$(dirname "$0")"` then `exec bin/macos/<arch>/PokeMMO`, so
# the process argv is that RELATIVE path. Two patterns that look right and are not:
#   pkill -f PokeMMO                -> also matches this script's own invocation,
#                                      because the repo path contains PokeMMO. It
#                                      kills the caller and the run dies silently.
#   pkill -f pokemmo-client-live    -> never matches; the argv is relative, so the
#                                      install directory does not appear in it. The
#                                      old instance survives and they pile up.
CLIENT_PAT="bin/macos/[a-z0-9]*/PokeMMO"
pkill -f "$CLIENT_PAT" 2>/dev/null || true
n=0
while pgrep -f "$CLIENT_PAT" >/dev/null 2>&1; do
    n=$((n+1))
    [ "$n" -eq 20 ] && pkill -9 -f "$CLIENT_PAT" 2>/dev/null
    [ "$n" -gt 40 ] && { echo "   ERROR: could not kill running client"; exit 1; }
    sleep 0.25
done
echo "   no client running"
: > "$CLIENT/log/console.log"
( cd "$CLIENT" && nohup ./PokeMMO.sh >/dev/null 2>&1 & )
# One instance, always. Piling them up makes every screenshot ambiguous.
sleep 2
# BSD pgrep has no -c. Count with wc, or this silently reports nothing at all.
RUNNING=$(pgrep -f "$CLIENT_PAT" | wc -l | tr -d ' ')
[ "$RUNNING" -eq 1 ] || echo "   WARNING: $RUNNING client instances running"

echo "== wait for theme load =="
n=0
until grep -q 'Loaded theme' "$CLIENT/log/console.log" 2>/dev/null; do
    n=$((n+1)); [ "$n" -gt 120 ] && { echo "   TIMEOUT waiting for theme"; break; }
    sleep 0.5
done
grep -E 'Loading theme|Theme url|Loaded theme|not a mobile|revision .* is above|outdated' \
    "$CLIENT/log/console.log" | sed 's/^/   /' || true

echo "== screenshot =="
sleep 3
"$HOME/.claude/skills/macos-app-screenshot/shot.sh" PokeMMO "$OUT" >/dev/null
echo "   $OUT"
