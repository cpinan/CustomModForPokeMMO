"""The PokeMMO mod format, as enforced by the client.

Every rule here was read out of the shipped client binary's message table
(`strings bin/<os>/<arch>/PokeMMO`) and cross-checked against
`data/resources.zip`, which is itself a mod in the same format.
Rules marked UNVERIFIED are inferred and should be treated as best-effort.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Region folders. The client rejects anything else for the sprite trees:
#   "Invalid file: trainersprites/{}/{} has an invalid region ID.
#    Valid region IDs are: 0 / 1 / 2 / 3 / 10"
REGIONS = {0: "Kanto", 1: "Hoenn", 2: "Unova", 3: "Sinnoh", 10: "Johto"}
LEGACY_REGIONS = {4: "Johto (old id; community guides still say 4)"}

# Theme revision the installed client speaks. Printed on every start as
# "Client Theme Revision: N" in log/mods.log -- read it from there, don't
# trust this constant if the client has updated.
DEFAULT_THEME_REVISION = 8


@dataclass(frozen=True)
class DirRule:
    path: str                      # path inside the mod archive
    exts: tuple[str, ...]          # allowed file extensions (lowercase)
    pattern: re.Pattern | None     # filename stem must match
    describe: str
    regioned: bool = False         # files live one level deeper, in <region>/
    notes: tuple[str, ...] = field(default_factory=tuple)


# --- filename grammars -----------------------------------------------------
# battlesprites: "Expected name format is ID-back-shiny-gender-frame.png where:
#   'back' is either 'back' or 'front' (Ally/Enemy)
#   's' is 's' or 'n' (Shiny/Normal)
#   gender is 'm' or 'f'
#   F is frame id"
# Minimum accepted form is ID-front-n. GIFs must NOT carry a frame id:
#   "GIF format does not support frame ids. Remove frame id"
RE_BATTLE = re.compile(r"^(?P<id>\d+)-(?P<side>front|back)-(?P<shiny>[ns])(?:-(?P<gender>[mfb]))?(?:-(?P<frame>\d+))?$")
RE_ID = re.compile(r"^-?\d+$")
RE_ID_FRAME = re.compile(r"^(?P<id>\d+)-(?P<frame>\d+)(?P<suffix>-glowoverlay)?$")
RE_COMPOSITE = re.compile(r"^composite-\d+-\d+-\d+(-s)?$")
RE_EGG = re.compile(r"^egg_\d+_\d+$")
# Names the official resource pack uses inside battlesprites that are not
# ID-keyed sprites; accepted, but not something a mod normally ships.
RE_BATTLE_SPECIAL = re.compile(r"^(dummy|egg_preview_\d+)$")
RE_ICON_SPECIAL = re.compile(r"^egg_icon_\d+$")
RE_COSTUME = re.compile(r"^\d+-\d+$")
RE_MAP_FOOTER = re.compile(r"^\d+-\d+$")
RE_MAP_HEADER = re.compile(r"^\d+\.\d+$")

BATTLE_TABLES = {
    "table-front-scale.txt": "ID=SCALE for the enemy-facing sprite",
    "table-back-scale.txt": "ID=SCALE for your own sprite",
    "table-summary-scale.txt": "ID=SCALE in the summary/dex view",
    "table-coordinate-mods.txt": "ID,front=X,Y,Z  (each clamped -1..1)",
    "table-sprite-timings.txt": "per-sprite animation timings (UNVERIFIED format)",
}

CONTENT_DIRS: tuple[DirRule, ...] = (
    DirRule(
        "sprites/battlesprites", (".png", ".gif"), RE_BATTLE,
        "in-battle Pokemon sprites",
        notes=(
            "ID is the dex number for base forms (1 = Bulbasaur), or an internal "
            "sprite id for costumes/alt forms.",
            "GIF = animated, PNG = static. A GIF must not carry a frame id.",
            "Also accepts the table-*.txt scale/position files.",
        ),
    ),
    DirRule("sprites/monstericons", (".png",), RE_ID_FRAME,
            "party / PC box icons; frames 0..2 form the bob animation",
            notes=("`composite-A-B-C.png` and `composite-A-B-C-s.png` are also accepted.",)),
    DirRule("sprites/itemicons", (".png",), RE_ID, "bag and shop item icons"),
    DirRule("sprites/trainersprites", (".png", ".gif"), RE_ID,
            "NPC/trainer battle sprites", regioned=True),
    DirRule("sprites/overworldsprites", (".png",), RE_ID_FRAME,
            "everything drawn on the map: players, NPCs, followers, objects",
            regioned=True,
            notes=("`ID-FRAME-glowoverlay.png` adds the shiny/glow pass.",)),
    DirRule("sprites/followcostumes", (".png",), RE_ID_FRAME,
            "follower costume frames (8 per costume)"),
    DirRule("sprites/followsprites", (".png",), RE_ID_FRAME,
            "follower sprites (UNVERIFIED naming)"),
    DirRule("sprites/eggsprites", (".png",), RE_EGG,
            "egg sprites; the client wants exactly 6 PNGs per set"),
    DirRule("costumes", (".costume",), RE_COSTUME,
            "costume definitions, named spriteId-baseSpriteId.costume"),
    DirRule("cries", (".wav",), RE_ID, "Pokemon cries, named by dex id"),
    DirRule("sounds", (".wav", ".mp3", ".ogg"), RE_ID,
            "music and SFX by id (use /bgm in game to read the current id)",
            regioned=True),
    DirRule("maps", (".tmx",), None, "Tiled maps"),
    DirRule("world_map_footers", (".bin",), RE_MAP_FOOTER, "world map footers"),
    DirRule("world_map_headers", (".bin",), RE_MAP_HEADER, "world map headers"),
)

CONTENT_BY_PATH = {d.path: d for d in CONTENT_DIRS}

# Directories a mod may declare in <overlays>. An overlay is a raw file
# replacement inside the client's own data/ tree -- no id parsing happens.
COMMON_OVERLAYS = {
    "data/sprites/atlas/": "the libGDX UI atlas (main.png / main.atlas): every UI icon",
    "data/sprites/textures/": "battle backgrounds and misc textures",
    "data/shaders/": "GLSL shaders",
    "data/buttons/": "on-screen controller art",
}

INFO_XML_SECTIONS = ("themes", "theme_extensions", "strings", "overlays")

# info.xml <resource> attributes. name/version are what Mod Management shows.
RESOURCE_ATTRS = ("name", "version", "description", "author", "weblink")

# "weblink must start with https://forums.pokemmo.com; {}"
WEBLINK_PREFIX = "https://forums.pokemmo.com"


def region_of(part: str) -> int | None:
    try:
        return int(part)
    except ValueError:
        return None


def match_content_dir(rel_posix: str) -> DirRule | None:
    """Longest-prefix match of an archive path against the content dirs."""
    best = None
    for rule in CONTENT_DIRS:
        if rel_posix == rule.path or rel_posix.startswith(rule.path + "/"):
            if best is None or len(rule.path) > len(best.path):
                best = rule
    return best
