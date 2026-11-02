"""The end of a show (owner's playtest 2026-11-01: a flicker of font glyphs in front of HANK as he resumed walking).

A patron watching the show is in his back view (2 columns; the 3rd column of his footprint is plain wall). When another patron's redraw
composed that span WITH attributes, the 3rd column's attribute became the wall's (bank 0). Turning round again redrew tiles only, so the
Color-only look's 3rd-column tile (VRAM bank 1) was shown from bank 0: a font or HUD tile in front of him until his next change of columns.
Every venue, every look: after a show ends, each BG-drawn patron's footprint cells carry his own VRAM bank.
"""
import pytest
from conftest import bar_top_row, logic_paused
from test_art import goto_group
from test_lift import boot_play
from test_tips import w16

pytestmark = [pytest.mark.only_model("cgb"), pytest.mark.timeout(240)]

PATRON_BANK1 = 0x40
DRAW_BACK = 0x80
WALL = (0x18, 0x19)


@pytest.fixture(params=["cgb"])
def model(request):
    return request.param


def variant(look, inst):
    return look | (((look ^ inst) & 7) << 3) | (PATRON_BANK1 if look > 2 else 0)


def footprint_cells(gb, p):
    """(row0 address, columns) of a BG patron's cells, None when not on the BG, mirrored (R bar) or not drawn."""
    b = gb.read("patron_bar", 16)[p] & 3
    if gb.mem("bar_dirs") & (1 << b):
        return None
    d = gb.read("patron_draw", 16)[p]
    if d == 255 or gb.read("patron_lift", 16)[p] != 0:
        return None
    c = (d & ~DRAW_BACK) >> 3
    n = 2 if d & DRAW_BACK else 3
    addr = 0x9800 + 32 * bar_top_row(b)
    return addr, range(c, c + n)


def wrong_cells(gb):
    bad = []
    mem = gb.pb.memory
    st = gb.read("patron_state", 16)
    var = gb.read("patron_variant", 16)
    place = {p: footprint_cells(gb, p) for p in range(16) if st[p]}
    bars = gb.read("patron_bar", 16)
    for p in range(16):
        cells = place.get(p)
        if not cells:
            continue
        addr, cols = cells
        # (patrons overlap and pass each other: a cell another patron of the bar also covers is his as well)
        mine = {c for q, o in place.items() if o and q != p and (bars[q] & 3) == (bars[p] & 3) for c in o[1]}
        cols = [c for c in cols if c not in mine]
        want = 8 if var[p] & PATRON_BANK1 else 0
        for r in (0, 32):
            for c in cols:
                if mem[addr + r + c] in WALL:       # (a plain-wall cell, a shift-0 patron's empty 3rd column: either bank shows nothing)
                    continue
                if (mem[1, addr + r + c] & 8) != want:
                    bad.append((p, var[p], addr + r + c))
    return bad


@pytest.mark.parametrize("group", range(10))
def test_patrons_resuming_after_a_show_keep_their_vram_bank(model, group):
    gb = boot_play(model)
    try:
        goto_group(gb, group)
        gb.write("tip_chance", 0)
        gb.write("intro_timer", 0)
        gb.write("quota", 200)
        w16(gb, "spawn_interval", 20)      # the game's own spawns: only the (look, palette) pairs the venue really has
        for _ in range(900):
            if gb.mem("patrons_live") >= 10:
                break
            gb.run(1)
        assert gb.mem("patrons_live") >= 3
        streak = {}
        for _ in range(2):
            with logic_paused(gb):
                gb.write("tip_bar", gb.mem("bar"))
                gb.write("tip_x", gb.mem("bartender_x") + 4)
                w16(gb, "tip_timer", 200)
            gb.run(3)
            gb.run(90)
            with logic_paused(gb):
                w16(gb, "show_timer", 1)
            for f in range(70):
                gb.run(1)
                now = {x[2] for x in wrong_cells(gb)}
                streak = {a: streak.get(a, 0) + 1 for a in now}
                assert not any(n >= 12 for n in streak.values()), ("a patron's cell is drawn from the wrong VRAM bank", f, sorted(streak), wrong_cells(gb), [(gb.read("patron_draw", 16)[x[0]], gb.read("patron_x", 16)[x[0]], gb.read("patron_dist", 16)[x[0]], gb.read("patron_state", 16)[x[0]]) for x in wrong_cells(gb)])
    finally:
        gb.stop()
