#!/usr/bin/env python3
"""Assemble assets/art/patrons/<venue>_x.txt (+ _back) from tools/artifacts/palette_plan/art/<venue>_<name>(_back).txt, in plan order
(plan_data NEW_PATRONS order: the venue's five Color-only looks, looks 3-7). The files are the committed source; this is how they were made.

  python3 tools/dev/make_x_art.py sports lumberjacks chefs
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools/artifacts/palette_plan"))
import plan_data as P  # noqa: E402

NAMES = {"sports": "Stadium", "lumberjacks": "Lumber Lodge", "chefs": "Bistro"}
for v in sys.argv[1:]:
    names = [n for n, _ in P.NEW_PATRONS[v]]
    assert len(names) == 5, (v, names)
    for suffix in ("", "_back"):
        out = ["; The %s's five Color-only looks, VRAM bank 1; tools/gen_art.py x_looks: %s (plan order: NEW_PATRONS)." % (NAMES[v], ", ".join(names)),
               "; Sources: tools/artifacts/palette_plan/art/%s_<name>%s.txt (tools/dev/make_x_art.py).\n" % (v, suffix)]
        for n in names:
            rows = [l.rstrip() for l in open(os.path.join(ROOT, "tools/artifacts/palette_plan/art/%s_%s%s.txt" % (v, n.lower(), suffix))) if l.strip() and not l.startswith(";")]
            assert len(rows) == 16 and all(len(r) == 16 for r in rows), (v, n, suffix)
            if not suffix:
                assert all(r[15] == "." for r in rows), (v, n, "right column x=15 not clear")
            out += ["; " + n] + rows + [""]
        open(os.path.join(ROOT, "assets/art/patrons/%s_x%s.txt" % (v, suffix)), "w").write("\n".join(out))
