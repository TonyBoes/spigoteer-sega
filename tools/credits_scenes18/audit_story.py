"""The story portrait's pixel grids (from the art branch's audit_story.py, unchanged): -> (hex[y][x] with the Color-only accents at their own colours, DMG shade[y][x], accent positions, bg char, rows)."""
from scenes_lib import PORT      # noqa: E402


def story_grids(owner):
    """-> (hex[y][x] with the accents at their own colours, shade[y][x], accent positions {(x,y): char}, bg char)"""
    key, rows, mode = {}, [], None
    acc = {}
    for ln in (PORT / f"{owner}.txt").read_text().splitlines():
        if ln.startswith("@key"):
            mode = "k"
        elif ln.startswith("@pixels"):
            mode = "p"
        elif ln.startswith(";") or ln.startswith("@") or not ln.strip():
            continue
        elif mode == "k":
            p = ln.split()
            key[p[0]] = (int(p[1]), p[2])
            if len(p) > 4 and p[4].startswith("obj="):
                acc[p[0]] = p[4][4:]
        elif mode == "p":
            rows.append(ln)
    hx = [[key[c][1] for c in r] for r in rows]
    sh = [[key[acc.get(c, c)][0] for c in r] for r in rows]       # DMG shade: an accent shows its BG replacement's shade on DMG
    accpos = {(x, y): rows[y][x] for y in range(56) for x in range(56) if rows[y][x] in acc}
    return hx, sh, accpos, rows[0][0], rows
