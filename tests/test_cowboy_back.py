# The saloon cowboy's back view (variant A, drawn while the dancers' show plays) has a symmetric hat (owner 2026-10-15: "the
# first cowboy's hat is lopsided and strange when watching the dancing girls"): its crown, brim and head are mirror images
# about column 8, where the neck and the shoulders are centred.
import re

from conftest import ROOT


def first_block(name):
    txt = (ROOT / "assets" / "art" / "patrons" / name).read_text()
    rows = [r for r in re.split(r"\n\s*\n", txt.strip())[0].splitlines() if r and not r.startswith(";")]
    assert len(rows) == 16 and all(len(r) == 16 for r in rows)
    return rows


def test_back_hat_is_symmetric_about_the_head():
    rows = first_block("cowboys_back.txt")
    for y in range(0, 10):                          # crown 0-4, brim 5-6, the brim's underside and the head 7-9
        r = rows[y]
        assert r[0] == "." and all(r[c] == r[16 - c] for c in range(1, 16)), f"row {y} {r!r} is not symmetric about column 8"
    for y in (10, 11):                              # the neck below it is centred on the same column
        r = rows[y]
        cols = [c for c in range(16) if r[c] != "."]
        assert cols[0] + cols[-1] == 16, (y, r)
