# A boss fight borrows variant C's BG tile ids (162-203 shifted, 214-217 shift-0, 218-229 back views: src/boss.h BOSS_BG_A / BOSS_BG_B)
# for his body, so no regular may be drawn from them: the regulars are variants A and B and the Color-only looks (VRAM bank 1), never the
# C slot (src/mirror.c spawn_variant, show.c place_start_patrons, the generated boss tables). This holds for every boss, DMG and Color.
#
# The cells: the old Duke goldens show half his GULP pose on bar 4. That is not a patron the game drew. The test setup empties the bars
# by poking patron_state = 0 (test_story.clear_bars); remove_patron would also mark the patron's columns dirty (patrons.c), the poke does
# not, so the cells of the Last call's patrons stay on the screen, and when his tiles load over variant C's ids a bank-0 look-C patron
# turns into pieces of him. In the game the bars are empty by real removals, and nothing of the kind is on screen.
# repaint_bars() below does what remove_patron's mark_dirty_attrs does; the shared helpers are left alone (their goldens carry the old cells).
import pytest
from boss_common import fight, play, row
from test_flow import tilemap_row

pytestmark = pytest.mark.timeout(300)

BOSS_IDS = set(range(162, 204)) | set(range(214, 230))
FRAMES, STEP = 900, 15


def arr(gb, name):
    return list(gb.read(gb.addr(name), 16))


def repaint_bars(gb):
    """Every bar's columns dirty, as remove_patron leaves them: the next frame composes the wall back over a poked-out patron's cells."""
    for b in range(4):
        for name, v in (("dirty_x0", 0), ("dirty_x1", 20), ("attr_x0", 0), ("attr_x1", 20)):
            gb.write(gb.addr(name) + b, v)
    gb.write("vram_pending", 1)


def bank1_attrs(gb, y):
    gb.write(0xFF4F, 1)
    try:
        return [gb.pb.memory[0x9800 + y * 32 + k] for k in range(20)]
    finally:
        gb.write(0xFF4F, 0)


@pytest.mark.parametrize("c", range(10))
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_no_patron_is_drawn_from_the_bosss_tiles(model, c):
    """Every live patron's cells, 900 frames of every boss's fight: none is a bank-0 id of his body (his own columns apart: a jump or a ride
    may cover a patron's edge)."""
    gb = fight(model, c)
    w = row(c)["width"]
    repaint_bars(gb)
    play(gb)
    seen, bad = 0, []
    for f in range(FRAMES // STEP):
        gb.run(STEP)
        st, bar, dr = arr(gb, "patron_state"), arr(gb, "patron_bar"), arr(gb, "patron_draw")
        bb, bx = gb.mem("boss_bar"), gb.mem("boss_x") >> 3
        for p in range(16):
            if st[p] == 0 or dr[p] == 255:
                continue
            b, col = bar[p] & 3, (dr[p] & 0x7F) >> 3
            for dy in (0, 1):
                y = 5 + 3 * b + dy
                ids = tilemap_row(gb, y, 0, 20)
                at = bank1_attrs(gb, y) if model == "cgb" else [0] * 20
                for k in range(col, min(col + 3, 20)):
                    if b == bb and bx <= k <= bx + w:
                        continue
                    seen += 1
                    if ids[k] in BOSS_IDS and not at[k] & 8:     # (Color: bank 1 is the Color-only looks' own tiles)
                        bad.append((f * STEP, p, b, k, ids[k]))
    assert seen > 100, "patrons were on the bars"
    assert not bad, f"live patrons drawn from his tile ids (frame, patron, bar, column, id): {bad[:6]}"
