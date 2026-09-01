"""pmmod -- a PokeMMO mod workbench: scaffold, validate, build, install, test."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import zipfile
from pathlib import Path

from . import build as build_mod
from . import install as installer
from . import diagnose, fasttext, logs, props, pull, release, scaffold, spec, themelint
from . import sprites_tool, strings_tool
from .paths import find_client
from .validate import Source, summarize, validate

BOLD, DIM, RED, YEL, GRN, OFF = "\033[1m", "\033[2m", "\033[31m", "\033[33m", "\033[32m", "\033[0m"


def _color(enabled: bool):
    if enabled:
        return BOLD, DIM, RED, YEL, GRN, OFF
    return ("",) * 6


# --- commands --------------------------------------------------------------
def cmd_doctor(a) -> int:
    c = find_client(a.client)
    cfg = props.load(c.config)
    rep = logs.parse(c.mods_log)
    print(f"client root       : {c.root}")
    print(f"client revision   : {c.revision}")
    print(f"theme revision    : {rep.theme_revision or 'unknown (start the client once)'}")
    print(f"mods folder       : {c.mods_dir}  ({'exists' if c.mods_dir.is_dir() else 'MISSING'})")
    print(f"config            : {c.config}")
    print(f"verbose mod log   : {cfg.get(props.VERBOSE_KEY, 'false')}")
    print(f"active theme      : {cfg.get(props.THEME_KEY, 'default')}")
    print(f"enabled mods      : {', '.join(props.enabled_mods(c.config)) or '-'}")
    print(f"client running    : {'yes' if c.is_running() else 'no'}")
    print(f"dump folder       : {c.dump_dir}  ({'present' if c.dump_dir.is_dir() else 'not created yet'})")
    try:
        import PIL  # noqa: F401
        print("Pillow            : available (image tools enabled)")
    except Exception:
        print("Pillow            : MISSING -- `pip install Pillow` for image tools")
    return 0


def cmd_list(a) -> int:
    c = find_client(a.client)
    mods = installer.list_mods(c)
    if not mods:
        print("No mods installed.")
        return 0
    width = max(len(m.file.name) for m in mods)
    for m in mods:
        flag = "ON " if m.enabled else "off"
        tag = " (official, cannot be disabled)" if m.official else ""
        print(f"[{flag}] {m.file.name:<{width}}  {m.name} v{m.version}"
              f"{' by ' + m.author if m.author else ''}{tag}")
    return 0


def cmd_new(a) -> int:
    theme_rev = spec.DEFAULT_THEME_REVISION
    try:
        rev = logs.parse(find_client(a.client).mods_log).theme_revision
        theme_rev = int(rev) if rev else theme_rev
    except SystemExit:
        pass
    target = Path(a.path or (Path.cwd() / build_mod.slug(a.name)))
    scaffold.new_mod(target, a.name, a.kind, a.mod_version, a.author,
                     a.description, a.weblink, theme_rev, a.string_revision)
    print(f"created {target}")
    print(f"  kind    : {a.kind}")
    print(f"  next    : drop files in, then `pmmod test {target}`")
    return 0


def cmd_validate(a) -> int:
    BOLD_, DIM_, RED_, YEL_, GRN_, OFF_ = _color(sys.stdout.isatty() and not a.no_color)
    worst = 0
    for target in a.paths:
        src = Source.open(Path(target))
        findings = validate(src)
        errors, warns = summarize(findings)
        print(f"{BOLD_}{target}{OFF_}  ({len(src.files)} files)")
        for f in findings:
            if f.level == "warn" and a.errors_only:
                continue
            col = RED_ if f.level == "error" else YEL_
            print(f"  {col}{f}{OFF_}")
        verdict = (f"{RED_}{errors} error(s){OFF_}" if errors
                   else f"{GRN_}valid{OFF_}")
        print(f"  -> {verdict}, {warns} warning(s)\n")
        worst = max(worst, 1 if errors else 0)
    return worst


def cmd_build(a) -> int:
    src = Path(a.path)
    findings = validate(Source.open(src))
    errors, warns = summarize(findings)
    if errors and not a.force:
        for f in findings:
            if f.level == "error":
                print(f"  {f}")
        print(f"\n{errors} error(s); refusing to build. Use --force to build anyway.")
        return 1
    out = build_mod.build(src, Path(a.out) if a.out else None, compress=not a.store)
    size = out.stat().st_size
    print(f"built {out}  ({size/1024:.1f} KiB, {warns} warning(s))")
    return 0


def cmd_install(a) -> int:
    c = find_client(a.client)
    art = Path(a.path)
    if art.is_dir() and not a.raw:
        art = build_mod.build(art)
        print(f"built {art}")
    mod = installer.install(c, art, enable=a.enable)
    print(f"installed {mod.file.name} -> {c.mods_dir}")
    if a.enable:
        print(f"enabled   {mod.file.name}")
    print("restart the client for the change to take effect")
    return 0


def cmd_enable(a) -> int:
    c = find_client(a.client)
    installer.set_enabled(c, a.name, True)
    print(f"enabled: {', '.join(props.enabled_mods(c.config))}")
    print("restart the client for the change to take effect")
    return 0


def cmd_disable(a) -> int:
    c = find_client(a.client)
    installer.set_enabled(c, a.name, False)
    print(f"enabled: {', '.join(props.enabled_mods(c.config)) or '-'}")
    return 0


def cmd_uninstall(a) -> int:
    c = find_client(a.client)
    mod = installer._resolve(c, a.name)
    if not a.yes:
        print(f"Would delete {mod.file}. Re-run with --yes to confirm.")
        return 1
    installer.uninstall(c, a.name)
    print(f"deleted {mod.file}")
    return 0


def cmd_verbose(a) -> int:
    c = find_client(a.client)
    installer.set_verbose(c, a.state == "on")
    print(f"{props.VERBOSE_KEY}={a.state == 'on'}")
    return 0


def cmd_log(a) -> int:
    c = find_client(a.client)
    rep = logs.parse(c.mods_log)
    print(logs.render(rep, verbose=a.verbose))
    if a.grep:
        import re
        rx = re.compile(a.grep, re.I)
        print(f"\nlines matching {a.grep!r}:")
        for line in c.mods_log.read_text(errors="replace").splitlines():
            if rx.search(line):
                print("  " + line)
    return 0


def cmd_test(a) -> int:
    """validate -> build -> install -> enable -> verbose on -> tell me to restart."""
    c = find_client(a.client)
    src = Path(a.path)
    findings = validate(Source.open(src))
    errors, _ = summarize(findings)
    for f in findings:
        print(f"  {f}")
    if errors and not a.force:
        print(f"\n{errors} error(s); not installing. Fix them or pass --force.")
        return 1
    art = build_mod.build(src)
    mod = installer.install(c, art, enable=True)
    installer.set_verbose(c, True)
    print(f"\nbuilt     {art}")
    print(f"installed {mod.file.name}")
    print(f"enabled   {', '.join(props.enabled_mods(c.config))}")
    print("verbose mod logging is on")
    if c.is_running():
        print("\nThe client is running -- restart it, then: pmmod log")
    else:
        print(f"\nStart the client ({c.launcher}), then: pmmod log")
    return 0


def cmd_run(a) -> int:
    c = find_client(a.client)
    args: list[str] = []
    if a.mobile:
        args.append("--theme-mobile")
    if a.default_theme:
        args.append("--theme-default")
    if a.theme:
        args.append(f"--theme={a.theme}")

    # PokeMMO.sh execs the binary without forwarding "$@", so any flag has to
    # go to the native binary directly -- and it must run with cwd = client root.
    exe = c.native_binary if args else c.launcher
    if not exe.exists():
        print(f"executable not found: {exe}")
        return 1
    print(f"launching {exe.name} {' '.join(args)}".rstrip())
    subprocess.Popen([str(exe)] + args, cwd=str(c.root),
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if a.mobile:
        print("running the Android UI on the desktop -- the same theme the "
              "handheld uses, but with readable logs")
    print("client started; after it reaches the login screen run: pmmod log")
    return 0


def cmd_probe_revisions(a) -> int:
    """Make the client tell us which strings/theme revisions it accepts."""
    c = find_client(a.client)
    target = c.mods_dir / "_pmmod_probe.mod"
    info = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<resource name="pmmod revision probe" version="1.0" '
        'description="Deliberately out-of-range revisions so the client logs the ones it wants." '
        f'author="pmmod" weblink="{spec.WEBLINK_PREFIX}/">\n'
        '    <strings string_revision="99999">\n'
        '        <string path="data/strings/probe.xml"/>\n'
        "    </strings>\n"
        "</resource>\n")
    probe_xml = ('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
                 '<strings lang="en" lang_full="English" is_primary="0">\n'
                 '  <string id="999999999">probe</string>\n</strings>\n')
    with zipfile.ZipFile(target, "w") as zf:
        zf.writestr("info.xml", info)
        zf.writestr("data/strings/probe.xml", probe_xml)
        zf.writestr("icon.png", scaffold._FALLBACK_ICON)
    installer.set_enabled(c, target.name, True)
    installer.set_verbose(c, True)
    print(f"wrote {target} and enabled it.")
    print("Start the client, let it reach the login screen, then run:")
    print("  pmmod log --grep revision")
    print("The client will log 'Expected string revision: N'.")
    print(f"Remove it afterwards with: pmmod uninstall {target.name} --yes")
    return 0


def cmd_dump(a) -> int:
    c = find_client(a.client)
    print("The client dumps its own moddable assets for you. In game:")
    print("  Settings > Utilities >")
    print("    'Dump Moddable Resources'  -> dump/resources/  (sprites, icons, sounds)")
    print("    'Dump Strings to XML'      -> dump/strings/    (UI text)")
    print("    'Dump Storyline Strings'   -> dump/strings/    (NPC dialogue)")
    print(f"\nOn this machine that lands in: {c.dump_dir}")
    if c.dump_dir.is_dir():
        for p in sorted(c.dump_dir.iterdir()):
            n = sum(1 for _ in p.rglob('*')) if p.is_dir() else 1
            print(f"  present: {p.name}  ({n} entries)")
    else:
        print("  (not created yet -- run the utility once)")
    print("\nNote: the utility does not dump assets that a mod already replaced.")
    return 0


def cmd_diagnose(a) -> int:
    c = find_client(a.client)
    hits = diagnose.scan([c.console_log, c.mods_log]
                         + [Path(p) for p in (a.extra_logs or [])])
    print(diagnose.render(hits, show_context=a.context))
    return 0


def cmd_pull_logs(a) -> int:
    dest = Path(a.out).expanduser()
    if a.ssh:
        dest, got = pull.pull_ssh(dest, a.ssh, a.port, a.key, a.remote_root)
    else:
        devices = pull.adb_devices()
        if not devices:
            print("No adb device found.\n"
                  "  1. Plug the handheld in with a DATA usb cable.\n"
                  "  2. Settings > About > tap Build number 7x, then\n"
                  "     Settings > Developer options > USB debugging.\n"
                  "  3. Accept the 'Allow USB debugging' prompt on the device.\n"
                  "  4. Re-run: pmmod pull-logs\n\n"
                  "If the handheld runs a Linux CFW with the PortMaster port "
                  "instead of Android, use:\n"
                  "  pmmod pull-logs --ssh ark@<device-ip>")
            return 1
        if len(devices) > 1 and not a.serial:
            print("Several devices attached; pick one with --serial:")
            for d in devices:
                print(f"  {d.serial}  {d.label}")
            return 1
        serial = a.serial or devices[0].serial
        print(f"pulling from {serial}")
        if a.downloads:
            dest, got = pull.pull_downloads(dest, serial)
        elif a.logcat:
            dest, got = pull.pull_logcat(dest, serial)
        else:
            try:
                dest, got = pull.pull_adb(dest, serial, a.remote_root)
            except SystemExit as e:
                # Stock Android keeps the client tree in private storage.
                # logcat carries the same messages, so fall back to it.
                print(str(e))
                print("\nfalling back to logcat, which carries the same lines\n")
                dest, got = pull.pull_logcat(dest, serial)

    print(f"saved to {dest}")
    for g in got:
        print(f"  {g}")
    file_based = not (a.downloads or a.logcat) and any("logcat" not in g for g in got) \
        and not any("logcat" in g for g in got)
    missing = [w for w in pull.WANTED
               if not any(g.startswith(w) for g in got)] if file_based else []
    for m in missing:
        print(f"  (missing) {m}")

    logfiles = [dest / "console.log", dest / "mods.log",
                dest / "logcat-pokemmo.log"]
    rep = logs.parse(dest / "mods.log") if (dest / "mods.log").is_file() else logs.LogReport()
    print()
    print(logs.render(rep))
    print()
    hits = diagnose.scan([p for p in logfiles if p.is_file()])
    print(diagnose.render(hits, show_context=not a.no_context))
    return 0


def cmd_release(a) -> int:
    try:
        c = find_client(a.client)
        rev = c.revision
        theme_rev = logs.parse(c.mods_log).theme_revision
    except SystemExit:
        rev, theme_rev = "?", None
    info = release.release(Path(a.path), Path(a.out), rev, theme_rev,
                           changes=a.changes or "")
    print(f"artifact  {info['artifact']}")
    print(f"sha256    {info['sha256']}")
    print(f"post      {info['post']}")
    print(f"checklist {info['checklist']}")
    return 0


def cmd_spec(a) -> int:
    B, _, _, _, _, O = _color(sys.stdout.isatty())
    print(f"{B}Mod archive layout{O}  (.mod or .zip; a plain folder also works)")
    print("  info.xml            required, at the archive ROOT")
    print("  icon.png            48x48, shown in Mod Management")
    print()
    print(f"{B}Content directories the loader reads{O}")
    for rule in spec.CONTENT_DIRS:
        loc = f"{rule.path}/<region>/" if rule.regioned else f"{rule.path}/"
        print(f"  {loc:<34} {'/'.join(rule.exts):<16} {rule.describe}")
        for n in rule.notes:
            print(f"      - {n}")
    print()
    print(f"{B}Regions{O}: " + ", ".join(f"{k}={v}" for k, v in spec.REGIONS.items()))
    print(f"{B}Battle sprite name{O}: ID-(front|back)-(n|s)[-(m|f)][-FRAME].png|gif")
    print("  GIF = animated and must NOT carry a frame id.")
    print()
    print(f"{B}Battle sprite tables{O} (in sprites/battlesprites/)")
    for k, v in spec.BATTLE_TABLES.items():
        print(f"  {k:<28} {v}")
    print()
    print(f"{B}info.xml sections{O}: " + ", ".join(spec.INFO_XML_SECTIONS))
    print(f"  weblink must start with {spec.WEBLINK_PREFIX}")
    print()
    print(f"{B}Overlay targets{O} (declare in <overlays>)")
    for k, v in spec.COMMON_OVERLAYS.items():
        print(f"  {k:<26} {v}")
    return 0


# --- strings ---------------------------------------------------------------
def _strings_source(a) -> Path:
    if a.file:
        return Path(a.file).expanduser()
    return find_client(a.client).strings_dir / f"strings_{a.lang}.xml"


def cmd_strings_find(a) -> int:
    entries = strings_tool.parse_file(_strings_source(a))
    hits = strings_tool.find(entries, a.pattern)
    for e in hits[: a.limit]:
        text = e.text.replace("\n", "\\n")
        print(f"{e.key:<24} {text[:110]}")
    print(f"\n{len(hits)} match(es)"
          + (f", showing {a.limit}" if len(hits) > a.limit else ""))
    return 0


LANG_NAMES = {"en": "English", "es": "Espanol", "de": "Deutsch", "fr": "Francais",
              "it": "Italiano", "pt-BR": "Portugues (Brasil)", "pl": "Polski"}


def cmd_strings_fasttext(a) -> int:
    dumps = Path(a.dumps).expanduser() if a.dumps else find_client(a.client).dump_dir / "strings"
    if not dumps.is_dir():
        print(f"no dumps at {dumps}\n"
              "Run Settings > Utilities > 'Dump Strings to XML' and "
              "'Dump Storyline Strings' first (pmmod dump explains it).")
        return 1
    rules, guards = fasttext.load_rules(Path(a.rules))
    plain, ds, counts = fasttext.scan(dumps, rules, guards)
    guarded = counts.pop("_guarded", 0)
    for name, n in counts.items():
        print(f"  {name:<18} {n:>5} entries")
    total = sum(counts.values())
    if guarded:
        print(f"  {'(guarded)':<18} {guarded:>5} skipped as read-on-purpose text")
    print(f"  {'TOTAL':<18} {total:>5}")
    if not total:
        print("nothing matched -- check the rules against the dumps")
        return 1
    if a.dry_run:
        return 0

    out = Path(a.out).expanduser()
    langs = [l.strip() for l in a.langs.split(",") if l.strip()]
    files = fasttext.write_mod(out, plain, ds, langs, rules, LANG_NAMES)
    scaffold.make_icon(out / "icon.png", a.name)
    fasttext.write_info(out, files, a.name, a.mod_version, a.author,
                        a.description or "Faster text, generated from the client's own strings.",
                        a.weblink or spec.WEBLINK_PREFIX + "/")
    print(f"\nwrote {len(files)} string file(s) into {out}")
    for f in files:
        print(f"  {f}")
    return 0


def cmd_strings_extract(a) -> int:
    entries = strings_tool.parse_file(_strings_source(a))
    if a.ids:
        picked = strings_tool.by_ids(entries, a.ids)
    elif a.pattern:
        picked = strings_tool.find(entries, a.pattern)
    else:
        print("Give --ids or --pattern")
        return 1
    xml = (strings_tool.silence(picked, a.lang) if a.silence
           else strings_tool.build_override(picked, a.lang))
    if a.out:
        Path(a.out).expanduser().parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).expanduser().write_text(xml, encoding="utf-8")
        print(f"wrote {a.out} ({len(picked)} strings)")
    else:
        print(xml)
    return 0


# --- sprites ---------------------------------------------------------------
def cmd_sprites_inspect(a) -> int:
    paths = []
    for t in a.paths:
        p = Path(t).expanduser()
        paths += sorted(p.rglob("*.png")) + sorted(p.rglob("*.gif")) if p.is_dir() else [p]
    for info in sprites_tool.inspect(paths):
        size = f"{info.size[0]}x{info.size[1]}" if info.size else "?"
        print(f"{size:>10}  {info.frames:>3}f  {info.mode:<5} {info.bytes:>8}B  {info.path}")
    return 0


def cmd_sprites_blank(a) -> int:
    ids = sprites_tool.parse_id_ranges(a.ids)
    sides = tuple(a.sides.split(","))
    n = sprites_tool.write_blank_battlesprites(
        Path(a.out), ids, shiny=a.shiny, sides=sides, size=a.size)
    print(f"wrote {n} transparent overrides for {len(ids)} ids "
          f"into {Path(a.out) / 'sprites' / 'battlesprites'}")
    print(f"  shiny flag: {a.shiny!r}  (n = hide normals, s = hide shinies)")
    print(f"  sides: {', '.join(sides)}  (front = enemy, back = yours)")
    return 0


def cmd_sprites_rescue(a) -> int:
    out = Path(a.out).expanduser()
    _, moves, unmatched = sprites_tool.rescue(
        Path(a.path), out, a.name, a.author, a.mod_version, a.weblink)
    print(f"rescued {len(moves)} file(s) into {out}")
    for mv in moves[:10]:
        print(f"  {mv.src}  ->  {mv.dst}")
    if len(moves) > 10:
        print(f"  ... {len(moves)-10} more")
    if unmatched:
        print(f"\n{len(unmatched)} file(s) had no rule and were skipped:")
        for u in unmatched[:10]:
            print(f"  {u}")
    findings = validate(Source.open(out))
    errors, warns = summarize(findings)
    print(f"\nvalidation: {errors} error(s), {warns} warning(s)")
    for f in findings[:10]:
        print(f"  {f}")
    return 0


# --- theme -----------------------------------------------------------------
def cmd_theme_scaffold(a) -> int:
    c = find_client(a.client)
    src = c.themes_dir / a.base
    if not src.is_dir():
        print(f"no such base theme: {src}")
        return 1
    dst = Path(a.out).expanduser()
    if dst.exists() and any(dst.iterdir()) and not a.force:
        print(f"{dst} exists and is not empty; pass --force")
        return 1
    import shutil
    shutil.copytree(src, dst, dirs_exist_ok=True)
    for junk in list(dst.rglob(".DS_Store")):
        junk.unlink()
    print(f"copied {src} -> {dst}")
    print("Edit theme.xml and the ui/*.xml files, then reference the folder from")
    print('info.xml:  <themes theme_revision="%s"><theme path="%s/" name="My Theme" '
          'is_mobile="false"/></themes>' % (spec.DEFAULT_THEME_REVISION, dst.name))
    return 0


def cmd_theme_lint(a) -> int:
    roots = [Path(p).expanduser() for p in a.paths] if a.paths else \
        [find_client(a.client).themes_dir]
    total = 0
    for root in roots:
        findings = themelint.lint_tree(root) if root.is_dir() else themelint.lint_file(root)
        print(f"{root}  ({len(findings)} problem(s))")
        for f in findings:
            print(f"  {f}")
        total += len(findings)
    if not total:
        print("no contradictory min/max bounds found")
    return 1 if total else 0


# --- parser ----------------------------------------------------------------
def make_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pmmod", description=__doc__)
    p.add_argument("--client", help="path to pokemmo-client-live (else auto-detected)")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add(name, fn, help_):
        sp = sub.add_parser(name, help=help_)
        sp.set_defaults(func=fn)
        return sp

    add("doctor", cmd_doctor, "show the client, its revisions and mod state")
    add("spec", cmd_spec, "print the mod format reference")
    add("list", cmd_list, "list installed mods and whether they are enabled")
    add("dump", cmd_dump, "how to make the client dump its moddable assets")
    sp = add("diagnose", cmd_diagnose,
             "scan the client logs for known theme/mod failures and name the fix")
    sp.add_argument("--context", action="store_true",
                    help="print the widget dump after a layout loop")
    sp.add_argument("--extra-logs", nargs="*",
                    help="extra log files (e.g. one copied off an Android device)")

    sp = add("pull-logs", cmd_pull_logs,
             "copy a handheld's PokeMMO logs here and diagnose them")
    sp.add_argument("-o", "--out", default="device-logs",
                    help="local folder to write into")
    sp.add_argument("--serial", help="adb serial, when several devices are attached")
    sp.add_argument("--ssh", help="user@host for a PortMaster/Linux handheld")
    sp.add_argument("--port", type=int, default=22)
    sp.add_argument("--key", help="ssh private key")
    sp.add_argument("--remote-root", help="client folder on the device, if not auto-found")
    sp.add_argument("--logcat", action="store_true",
                    help="read the client's logcat output instead of its log files")
    sp.add_argument("--downloads", action="store_true",
                    help="pull exported logs out of the device's Downloads folder")
    sp.add_argument("--no-context", action="store_true",
                    help="skip the widget dump after a layout loop")

    sp = add("release", cmd_release, "build + checksum + forum post draft")
    sp.add_argument("path")
    sp.add_argument("-o", "--out", default="dist")
    sp.add_argument("--changes", help="bullet list for the post body")

    add("probe-revisions", cmd_probe_revisions,
        "install a probe mod that makes the client log the revisions it wants")

    sp = add("new", cmd_new, "scaffold a new mod source tree")
    sp.add_argument("name")
    sp.add_argument("path", nargs="?", help="target directory (default: ./<slug>)")
    sp.add_argument("--kind", default="empty", choices=sorted(scaffold.KINDS))
    sp.add_argument("--mod-version", default="1.0")
    sp.add_argument("--author", default=os.environ.get("USER", ""))
    sp.add_argument("--description", default="")
    sp.add_argument("--weblink", default="")
    sp.add_argument("--string-revision", type=int, default=1)

    sp = add("validate", cmd_validate, "lint a mod folder or .mod against the loader rules")
    sp.add_argument("paths", nargs="+")
    sp.add_argument("--errors-only", action="store_true")
    sp.add_argument("--no-color", action="store_true")

    sp = add("build", cmd_build, "pack a mod source folder into a .mod")
    sp.add_argument("path")
    sp.add_argument("-o", "--out")
    sp.add_argument("--store", action="store_true", help="store without compressing")
    sp.add_argument("--force", action="store_true", help="build even with errors")

    sp = add("install", cmd_install, "copy a mod into the client (building it first if needed)")
    sp.add_argument("path")
    sp.add_argument("--enable", action="store_true")
    sp.add_argument("--raw", action="store_true", help="copy a folder as-is instead of zipping")

    sp = add("enable", cmd_enable, "enable an installed mod")
    sp.add_argument("name")
    sp = add("disable", cmd_disable, "disable an installed mod")
    sp.add_argument("name")
    sp = add("uninstall", cmd_uninstall, "delete an installed mod")
    sp.add_argument("name")
    sp.add_argument("--yes", action="store_true")

    sp = add("verbose", cmd_verbose, "toggle per-file mod logging")
    sp.add_argument("state", choices=["on", "off"])

    sp = add("log", cmd_log, "summarise log/mods.log: what loaded, what broke")
    sp.add_argument("-v", "--verbose", action="store_true")
    sp.add_argument("--grep")

    sp = add("test", cmd_test, "validate + build + install + enable, ready for a restart")
    sp.add_argument("path")
    sp.add_argument("--force", action="store_true")

    sp = add("run", cmd_run, "launch the client")
    sp.add_argument("--mobile", action="store_true",
                    help="force the Android theme (reproduce handheld UI bugs here)")
    sp.add_argument("--default-theme", action="store_true",
                    help="force the stock desktop theme, ignoring the selected one")
    sp.add_argument("--theme", help="force a named theme")

    sp = add("strings", None, "text tools")
    ssub = sp.add_subparsers(dest="scmd", required=True)
    f = ssub.add_parser("find", help="search the client's strings for text -> ids")
    f.set_defaults(func=cmd_strings_find)
    f.add_argument("pattern")
    f.add_argument("--lang", default="en")
    f.add_argument("--file", help="a dumped xml instead of the client's own")
    f.add_argument("--limit", type=int, default=40)
    ft = ssub.add_parser("fasttext",
                         help="generate a fast-text mod from the client's dumps")
    ft.set_defaults(func=cmd_strings_fasttext)
    ft.add_argument("out", help="mod source directory to write")
    ft.add_argument("--dumps", help="dump/strings folder (default: the client's)")
    ft.add_argument("--rules", default="strings-work/rules.json")
    ft.add_argument("--langs", default="en,es")
    ft.add_argument("--name", default="Fast Text")
    ft.add_argument("--mod-version", default="1.0")
    ft.add_argument("--author", default=os.environ.get("USER", ""))
    ft.add_argument("--description", default="")
    ft.add_argument("--weblink", default="")
    ft.add_argument("--dry-run", action="store_true", help="just report the counts")

    e = ssub.add_parser("extract", help="build an override xml from ids or a search")
    e.set_defaults(func=cmd_strings_extract)
    e.add_argument("--ids", nargs="*")
    e.add_argument("--pattern")
    e.add_argument("--lang", default="en")
    e.add_argument("--file")
    e.add_argument("--silence", action="store_true",
                   help="replace every matched line with \\n (the 'fast text' trick)")
    e.add_argument("-o", "--out")

    sp = add("sprites", None, "sprite tools")
    psub = sp.add_subparsers(dest="scmd", required=True)
    i = psub.add_parser("inspect", help="report size/frames/mode for images")
    i.set_defaults(func=cmd_sprites_inspect)
    i.add_argument("paths", nargs="+")
    b = psub.add_parser("blank",
                        help="write transparent battle sprites to hide a set of ids")
    b.set_defaults(func=cmd_sprites_blank)
    b.add_argument("out", help="mod source directory")
    b.add_argument("--ids", default="1-649", help="e.g. 1-649,1000-1010")
    b.add_argument("--shiny", default="n", choices=["n", "s"],
                   help="n hides normal sprites, s hides shinies")
    b.add_argument("--sides", default="front,back",
                   help="front is the enemy sprite, back is your own")
    b.add_argument("--size", type=int, default=64)

    r = psub.add_parser("rescue", help="convert a legacy sprite mod to the current layout")
    r.set_defaults(func=cmd_sprites_rescue)
    r.add_argument("path")
    r.add_argument("out")
    r.add_argument("--name", default="Rescued Mod")
    r.add_argument("--author", default=os.environ.get("USER", ""))
    r.add_argument("--mod-version", default="1.0")
    r.add_argument("--weblink", default="")

    sp = add("theme", None, "theme tools")
    tsub = sp.add_subparsers(dest="scmd", required=True)
    tl = tsub.add_parser("lint", help="find contradictory min/max bounds that cause layout loops")
    tl.set_defaults(func=cmd_theme_lint)
    tl.add_argument("paths", nargs="*", help="theme dirs or xml files (default: the client's themes)")

    t = tsub.add_parser("scaffold", help="copy a stock theme as a starting point")
    t.set_defaults(func=cmd_theme_scaffold)
    t.add_argument("out")
    t.add_argument("--base", default="default", help="default or android")
    t.add_argument("--force", action="store_true")
    return p


def main(argv=None) -> int:
    args = make_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
