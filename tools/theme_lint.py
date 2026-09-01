#!/usr/bin/env python3
"""Resolve the theme include chain statically and answer the questions that
otherwise cost a build, a client restart and one of the user's screenshots.

    tools/theme_lint.py --unreachable        # our blocks that name nothing real
    tools/theme_lint.py --where editfield-search
    tools/theme_lint.py --image ui-frame-red.background
    tools/theme_lint.py --images inventory-tabbedframe

WHAT IT CAN AND CANNOT SETTLE, because guessing past that line is what cost the
rounds this exists to prevent.

CAN: whether a theme name exists at all; every path it is declared at; whether
an override we ship lands on a path the stock tree actually declares; which
widgets draw a given image, which is the blast radius before repainting a slice;
which images a widget draws.

CANNOT: which widgets the CLIENT instantiates, what it names them at runtime, or
whether it honours a param once resolved. `battlegui > label` is declared by
stock and still is not the battle name; `inventory-button` declares minHeight
and the client ignores it. Those need the game, or a live widget inspector this
build of the client does not ship.
"""
import argparse
import os
import sys
import xml.etree.ElementTree as ET

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOD = os.path.join(REPO, "mods", "vanbobby-firered-theme")
CLIENT = os.environ.get("POKEMMO_HOME") or os.path.expanduser(
    "~/Library/Application Support/com.pokeemu.macos/pokemmo-client-live")
ENTRY = os.path.join(MOD, "theme", "theme.xml")


def resolve(inc, base):
    if inc.startswith("/"):
        return os.path.normpath(CLIENT + inc)
    return os.path.normpath(os.path.join(os.path.dirname(base), inc))


def chain(path, seen=None, out=None):
    """Every theme file the entry point pulls in, in include order."""
    seen = seen if seen is not None else set()
    out = out if out is not None else []
    path = os.path.normpath(path)
    if path in seen or not os.path.exists(path):
        return out
    seen.add(path)
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as e:
        print("  ! unparseable: %s (%s)" % (path, e), file=sys.stderr)
        return out
    # Every child, not just up to the first non-include: theme.xml interleaves
    # its includes with constantDefs and fontGen, and stopping at the first of
    # those walked exactly one file.
    out.append((path, root))
    for el in root:
        if el.tag == "include" and el.get("filename"):
            chain(resolve(el.get("filename"), path), seen, out)
    return out


def walk(el, prefix, path, decls, images, refs=None):
    """Record every <theme> path, its ref, and every image a param names."""
    for child in el:
        if child.tag == "theme" and child.get("name"):
            here = prefix + (child.get("name"),)
            decls.setdefault(here, []).append(path)
            if refs is not None and child.get("ref"):
                refs.setdefault(here, set()).add(child.get("ref"))
            for p in child.findall("param"):
                for img in p.findall("image"):
                    if img.text and img.text != "none":
                        images.setdefault(img.text.strip(), []).append(here)
            walk(child, here, path, decls, images, refs)
        elif child.tag == "param":
            for img in child.findall("image"):
                if img.text and img.text != "none":
                    images.setdefault(img.text.strip(), []).append(prefix)


def build():
    decls, images, ours, refs = {}, {}, set(), {}
    files = chain(ENTRY)
    for path, root in files:
        d = {}
        walk(root, (), path, d, images, refs)
        for k, v in d.items():
            decls.setdefault(k, []).extend(v)
            if os.path.join(MOD, "firered") in path:
                ours.add(k)
    return decls, images, ours, refs, files


def reachable(path, decls, refs):
    """Is there any stock declaration a block at this path could land on?

    Directly, or through the parent's ref chain. monsterdex-frame declares no
    "title" of its own, but it refs base-tabbed-frame which refs resizableframe
    which does, so a title override there is perfectly live. Ignoring refs
    reported that as dead, which would have sent the next session chasing a
    working override."""
    def stock_has(p):
        return any(os.path.join(MOD, "firered") not in f
                   for f in decls.get(p, ()))

    if stock_has(path):
        return True
    if len(path) < 2:
        return False
    parent, leaf = path[:-1], path[-1]
    # Only STOCK declarations count, and never the path under test: checking
    # decls alone let our own block satisfy the question it was being asked.
    seen, queue = set(), [parent]
    while queue:
        cur = queue.pop()
        if cur in seen:
            continue
        seen.add(cur)
        if cur != parent and stock_has(cur + (leaf,)):
            return True
        for r in refs.get(cur, ()):
            queue.append((r,))          # a ref names a TOP-LEVEL theme
            if len(cur) > 1:
                queue.append(cur[:-1] + (r,))
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--unreachable", action="store_true")
    ap.add_argument("--where", metavar="NAME")
    ap.add_argument("--image", metavar="NAME")
    ap.add_argument("--images", metavar="PATH")
    ap.add_argument("--files", action="store_true")
    a = ap.parse_args()
    decls, images, ours, refs, files = build()

    if a.files:
        for p, _ in files:
            print(" ", os.path.relpath(p, REPO if p.startswith(REPO) else CLIENT))
        print("%d theme files in the chain" % len(files))

    if a.unreachable:
        bad = [p for p in sorted(ours) if not reachable(p, decls, refs)]
        for path in bad:
            print("UNREACHABLE  %s" % " > ".join(path))
            leaf = path[-1]
            elsewhere = [p for p in decls if p[-1] == leaf and p != path]
            for p in elsewhere[:4]:
                print("             stock declares %r at: %s"
                      % (leaf, " > ".join(p)))
            if not elsewhere:
                print("             stock declares %r nowhere at all" % leaf)
        print("\n%d of our %d blocks name a path stock never declares"
              % (len(bad), len(ours)))

    if a.where:
        # A path can be declared by BOTH, and that is the interesting case: it
        # means our override lands on something real. Reporting it as just
        # "OURS" hid that, and led to reading "stock declares only
        # battlegui > battle-text" off a screen where stock also declared
        # battlegui > label.
        hits = [p for p in decls if a.where in p]
        for p in sorted(hits):
            files = decls[p]
            mine = any(os.path.join(MOD, "firered") in f for f in files)
            theirs = any(os.path.join(MOD, "firered") not in f for f in files)
            tag = "BOTH" if mine and theirs else ("OURS" if mine else "stock")
            print("%-6s %s" % (tag, " > ".join(p)))
        if not hits:
            print("no theme named %r anywhere in the chain" % a.where)

    if a.image:
        users = images.get(a.image, [])
        for p in sorted(set(users)):
            print("  ", " > ".join(p) or "(root)")
        print("%d widget(s) draw %s" % (len(set(users)), a.image))

    if a.images:
        for img, paths in sorted(images.items()):
            for p in paths:
                if a.images in p:
                    print("  %-40s %s" % (img, " > ".join(p)))
                    break


if __name__ == "__main__":
    main()
