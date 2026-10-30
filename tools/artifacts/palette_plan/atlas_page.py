#!/usr/bin/env python3
"""`make atlas-page`: the one command that makes the Graphics Atlas page publishable.

1. Rebuilds the atlas capture (out/atlas, `make atlas`, about 70 s) only when it is missing or src/ assets/ tools/gen_art.py tools/gfx_atlas
   changed since the commit the capture was made from (or are dirty now).
2. Runs build.py, which runs the self-check and exits non-zero on any error: this command then fails too.
3. Checks the built page as the owner sees it (page_check.py: 360 px layout, every image).
4. Writes out/atlas_page/pub.json: the files to publish (index.html + the img/ files that changed or are new since the HEAD
   index.html, with the ?v= hashes stripped for the names) and the img/ files that were removed.
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
PAGE = os.path.join(HERE, "index.html")
CAP = os.path.join(ROOT, "out/atlas/data/index.js")
GAME_PATHS = ["src", "assets", "tools/gen_art.py", "tools/gfx_atlas"]
IMG_RE = re.compile(r"(img/[\w.\-]+\.png)(?:\?v=(\w+))?")
FILE_LIMIT = 512


def git(*a):
    r = subprocess.run(["git", "-C", ROOT] + list(a), capture_output=True, text=True)
    return r.returncode, r.stdout.strip()


def capture_commit():
    try:
        t = open(CAP).read()
    except OSError:
        return None
    m = re.search(r'"commit":"([^"]*)"', t)
    return m.group(1) if m else None


def capture_stale():
    """(stale?, why)."""
    c = capture_commit()
    if not c:
        return True, "no capture in out/atlas"
    if "+" in c or c == "unknown":
        return True, "the capture was made from a dirty tree (%s)" % c
    rc, _ = git("cat-file", "-e", c + "^{commit}")
    if rc:
        return True, "the capture's commit %s is not in this repository" % c
    rc, out = git("diff", "--name-only", c, "HEAD", "--", *GAME_PATHS)
    if out:
        return True, "%d game files changed since the capture's commit %s (first: %s)" % (len(out.splitlines()), c, out.splitlines()[0])
    rc, out = git("status", "--porcelain", "--", *GAME_PATHS)
    if out:
        return True, "uncommitted changes in src/ or assets/"
    return False, "the capture (%s) is current" % c


def img_refs(html):
    return {m.group(1): m.group(2) or "" for m in IMG_RE.finditer(html)}


def publish_list(new_html, old_html):
    new, old = img_refs(new_html), img_refs(old_html)
    changed = sorted(p for p, h in new.items() if old.get(p) != h)
    removed = sorted(p for p in old if p not in new)
    return new, changed, removed


def main():
    stale, why = capture_stale()
    print("atlas-page: " + why)
    if stale:
        print("atlas-page: running make atlas")
        if subprocess.call(["make", "-C", ROOT, "atlas"]) != 0:
            sys.exit("atlas-page: make atlas failed")
        stale, why = capture_stale()
        if stale and "no capture" in why:
            sys.exit("atlas-page: " + why)
    rc = subprocess.call([sys.executable, os.path.join(HERE, "build.py")])
    if rc != 0:
        sys.exit("atlas-page: build.py / the self-check failed (exit %d); nothing to publish" % rc)
    new_html = open(PAGE).read()
    rc = subprocess.call([sys.executable, os.path.join(HERE, "page_check.py"), PAGE])
    if rc != 0:
        sys.exit("atlas-page: the page check failed; nothing to publish")
    rel = os.path.relpath(PAGE, ROOT)
    rc, old_html = git("show", "HEAD:" + rel)
    if rc:
        old_html = ""
    new, changed, removed = publish_list(new_html, old_html)
    n_files = len(new) + 1
    out = os.path.join(ROOT, "out/atlas_page")
    os.makedirs(out, exist_ok=True)
    pub = dict(page=PAGE, img_dir=os.path.join(HERE, "img"), game_commit=capture_commit(), publish=["index.html"] + changed, removed=removed,
               files_total=n_files, unchanged=len(new) - len(changed))
    json.dump(pub, open(os.path.join(out, "pub.json"), "w"), indent=1)
    print("atlas-page: %d files on the page (limit %d); publish index.html + %d changed images, %d removed -> out/atlas_page/pub.json"
          % (n_files, FILE_LIMIT, len(changed), len(removed)))
    if n_files > FILE_LIMIT:
        sys.exit("atlas-page: %d files, over the artifact's %d file limit" % (n_files, FILE_LIMIT))


if __name__ == "__main__":
    main()
