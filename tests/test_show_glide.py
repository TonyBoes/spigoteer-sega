# The Igloo's Color show "Waddle wave" I1c (owner Q57, 2026-11-04: "the slower igloo slides are great. We can use those.") and the engine's glide block
# (src/show_ext.c show_ext_draw, tools/gen_art.py show_block: Color only, venue.show_band bit 6): a row every 3 frames, 4 a beat, a signed x shift per row.
#   - the data: 80 rows = 20 beats, a glide period byte, three performers on the same rows, each ending on a spot;
#   - the engine on Color: the 20-beat loop runs, the penguins are back on their spots at the wrap, and no line of 24-39 has more than 8 sprites;
#   - the DMG keeps today's igloo show (no glide bit).
import pytest

from conftest import THEMES, venue as venue_art
from test_show_ext import boot_at, dancer_oam, BEAT
from test_show_three import DANCER_X

IGLOO = THEMES.index("igloo")


def rows_of(block):
    size, period = block[0] | block[1] << 8, block[2]
    assert size == len(block)
    beats = period & 0x7F
    return period, [[(block[3 + 9 * s + 3 * k] | block[4 + 9 * s + 3 * k] << 8,
                      (block[5 + 9 * s + 3 * k] ^ 128) - 128) for k in range(3)] for s in range(4 * beats)]


def test_the_igloo_color_block_is_a_20_beat_glide_block():
    c = venue_art("igloo")["show_ext"]["c_block"]
    period, rows = rows_of(c)
    assert period & 0x80 and period & 0x7F == 20 and len(rows) == 80
    # every performer ends on a spot: the set of the three places on the last row is the set on the first row (the penguins are identical)
    place = lambda r: sorted(DANCER_X[k] + r[k][1] for k in range(3))
    assert place(rows[-1]) == place(rows[0]) == sorted(DANCER_X[k] + rows[0][k][1] for k in range(3))
    assert len({DANCER_X[k] + rows[0][k][1] for k in range(3)}) == 3


def test_the_dmg_block_is_not_a_glide_block():
    d = venue_art("igloo")["show_ext"]["d_block"]
    assert not d[2] & 0x80 and d[2] == 4, "the DMG block: today's 4-beat dance, read as ever"


def test_the_igloo_color_show_runs_its_loop_and_the_penguins_end_on_their_spots():
    gb = boot_at(IGLOO, "cgb")
    try:
        steps, starts, worst = [], [], 0
        for f in range(20 * BEAT * 2 + 30):
            gb.run(1)
            step = gb.read("story_scratch", 228)[227]
            if not steps or steps[-1] != step:
                steps.append(step)
            oam = gb.oam()
            for line in range(24, 40):
                n = len([s for s in oam if 0 < s["y"] < 160 and s["y"] - 16 <= line < s["y"]])
                worst = max(worst, n)
            if step == 0 and gb.mem("dance_tick") == 6:
                d = dancer_oam(gb)
                starts.append(sorted(min(s["x"] for s in d[4 * k:4 * k + 4] if s["y"]) for k in range(3)))
        assert worst <= 8, f"sprites per line on 24-39: {worst}"
        loop = steps[steps.index(0):]
        assert loop[:21] == list(range(20)) + [0], f"the 20-beat loop: {loop[:22]}"
        assert len(starts) >= 2 and all(s == starts[0] for s in starts), f"the penguins are back on their spots at each wrap: {starts}"
    finally:
        gb.stop()


# ---- the Lodge's Color show "Log roll" L4 (owner Q66, 2026-11-04: "The log roll is probably best when the lights are fixed."): the same glide block, 16 beats.
#   - the data: 64 rows = 16 beats, each performer (two birlers, the cheerer) back on its own place at the wrap, which is the place of beat 0;
#   - the engine on Color: the 16-beat loop runs, every performer is back where it started at each wrap, no line of 8-39 has more than 8 sprites
#     (the show band; the patrons start at line 40) and no line of the screen more than 10;
#   - the DMG keeps today's lodge dance.
LODGE = THEMES.index("lodge")


def test_the_lodge_color_block_is_a_16_beat_glide_block():
    c = venue_art("lodge")["show_ext"]["c_block"]
    period, rows = rows_of(c)
    assert period & 0x80 and period & 0x7F == 16 and len(rows) == 64
    for k in range(3):
        assert rows[-1][k][1] == rows[0][k][1], f"performer {k} ends where it starts"
    assert len({DANCER_X[k] + rows[0][k][1] for k in range(3)}) == 3


def test_the_lodge_dmg_block_is_today_s_4_beat_dance():
    d = venue_art("lodge")["show_ext"]["d_block"]
    assert not d[2] & 0x80 and d[2] == 4


def test_the_lodge_color_show_runs_its_loop_with_at_most_8_sprites_a_line_on_the_stage():
    gb = boot_at(LODGE, "cgb")
    try:
        steps, starts, band, screen = [], [], 0, 0
        for f in range(16 * BEAT * 2 + 30):
            gb.run(1)
            step = gb.read("story_scratch", 228)[227]
            if not steps or steps[-1] != step:
                steps.append(step)
            vis = [s for s in gb.oam() if 0 < s["y"] < 160]
            for line in range(144):
                n = len([s for s in vis if s["y"] - 16 <= line < s["y"]])
                screen = max(screen, n)
                if 8 <= line < 40:
                    band = max(band, n)
            if step == 0 and gb.mem("dance_tick") == 6:
                d = dancer_oam(gb)
                starts.append([min([s["x"] for s in d[4 * k:4 * k + 4] if s["y"]] or [0]) for k in range(3)])
        assert band <= 8, f"sprites per line on 8-39: {band}"
        assert screen <= 10, f"sprites per line on the screen: {screen}"
        loop = steps[steps.index(0):]
        assert loop[:17] == list(range(16)) + [0], f"the 16-beat loop: {loop[:18]}"
        assert len(starts) >= 2 and all(s == starts[0] for s in starts), f"every performer is back on its place at each wrap: {starts}"
    finally:
        gb.stop()
