"""The Graphics Atlas page (tools/artifacts/palette_plan): the plan against the game, with no emulator.

Always runs: the hand-kept plan data (plan_data.py) against the owner's picks and the game's own tables (game_truth.py reads build/palettes.c,
src/game.h, src/mirror.c), the page checks on synthetic pages, the publish list. Runs when the capture in out/atlas is current (`make atlas-page`
makes it): the full build.py self-check against the capture. Without a current capture that last test skips: it needs the emulator capture
(about 70 s), which `make test` does not make.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PP = ROOT / "tools/artifacts/palette_plan"
sys.path.insert(0, str(PP))

import atlas_page  # noqa: E402
import page_check  # noqa: E402
import plan_data  # noqa: E402
import self_check  # noqa: E402


def test_plan_carries_qn_and_every_pick_has_a_row():
    assert self_check.check_plan(plan_data, str(ROOT)) == []


def test_picks_file_is_parsed():
    names = self_check.picks_names(str(ROOT))
    assert len(names) >= 30 and "FRANK" in names and "GLOP" in names and "DJ" in names     # 32 accepted looks + the Space / Factory ones
    assert "BIGWIG" not in names                                                             # held, not accepted


def test_missing_pick_row_is_caught(monkeypatch):
    monkeypatch.setitem(plan_data.NEW_PATRONS, "sports", [x for x in plan_data.NEW_PATRONS["sports"] if x[0] != "FRANK"])
    monkeypatch.setitem(plan_data.PLANS["sports"], "join", {})
    monkeypatch.setitem(plan_data.PLANS["sports"], "extras", [])
    monkeypatch.setitem(plan_data.EXTRA_LOOKS, "sports", [])
    assert any("FRANK" in e for e in self_check.check_plan(plan_data, str(ROOT)))


def test_plan_without_qn_is_caught(monkeypatch):
    monkeypatch.setitem(plan_data.PLANS["zoo"], "q", [])
    assert any("PLANS[zoo]" in e for e in self_check.check_plan(plan_data, str(ROOT)))


def test_page_check_catches_the_known_bugs(tmp_path):
    (tmp_path / "img").mkdir()
    from PIL import Image
    Image.new("P", (16, 16)).save(tmp_path / "img/a.png")
    Image.new("P", (600, 40)).save(tmp_path / "img/wide.png")
    css = "<style>.x{max-width:none}.w{width:400px}</style>"
    bad = css + '<table><tr><td><img src="img/a.png"></td></tr></table><img class="x" src="img/wide.png" width="600" height="40"><div class="w"></div>'
    (tmp_path / "bad.html").write_text(bad)
    errs, _ = page_check.check(str(tmp_path / "bad.html"))
    assert len(errs) == 3, errs                                  # collapsing unsized cell image, a 600 px image, a 400 px box
    good = "<style>.p{max-width:none}</style>" + '<table><tr><td><img class="p" src="img/a.png" width="48" height="48"></td></tr></table>'
    (tmp_path / "good.html").write_text(good)
    assert page_check.check(str(tmp_path / "good.html"))[0] == []


def test_the_committed_page_passes_the_360_px_check():
    errs, n = page_check.check(str(PP / "index.html"))
    assert errs == [] and n > 100


def test_publish_list_names_changed_and_removed_images():
    old = '<img src="img/a.png?v=111"><img src="img/b.png?v=222"><img src="img/c.png?v=333">'
    new = '<img src="img/a.png?v=111"><img src="img/b.png?v=999"><img src="img/d.png?v=444">'
    refs, changed, removed = atlas_page.publish_list(new, old)
    assert changed == ["img/b.png", "img/d.png"] and removed == ["img/c.png"] and set(refs) == {"img/a.png", "img/b.png", "img/d.png"}


def test_full_self_check_against_the_capture(tmp_path):
    stale, why = atlas_page.capture_stale()
    if stale:
        pytest.skip("needs the emulator capture (`make atlas-page`): " + why)
    r = subprocess.run([sys.executable, str(PP / "build.py"), str(ROOT / "out/atlas/data"), str(tmp_path / "index.html")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-3000:]


def _fig(row14="..#++++++++++#..", row15="..#++++++++++#.."):
    rows = ["." * 16] + ["..#++++++++++#.."] * 14 + [row15]
    rows[14] = row14
    return rows


def test_patron_rules_catch_x15_bottom_outline_and_holes():
    ok = _fig()
    assert self_check.patron_rule_errors(ok) == []
    assert any("x=15" in e for e in self_check.patron_rule_errors([r[:15] + "#" for r in ok]))
    assert any("bottom row" in e for e in self_check.patron_rule_errors(_fig(row15="..############..")))
    assert self_check.patron_rule_errors(_fig(row14="..############..", row15="..############..")) == []     # a dark garment is not an outline
    holey = list(ok)
    holey[5] = "..#+++..++++++#."
    assert any("enclosed" in e for e in self_check.patron_rule_errors(holey))
    assert self_check.patron_rule_errors(holey, gaps={(6, 5), (7, 5)}) == []


def test_gus_plane_swap_helper():
    assert self_check.swap12(["-+#."]) == ["+-#."]
