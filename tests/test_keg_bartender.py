# The Bistro's shorter keg and the bartender 2 px lower (owner 2026-10-17: "move the grape label down ... make the whole
# barrel shorter by a couple pixels, taking them out of the middle portion, so that it doesn't touch the top of the next
# row ... lower the entire bartender by a couple of pixels in each row, so that he naturally holds the cups a little bit
# lower"). BT_DY (src/layout.h) is the bartender's drop below his bar's top; the Bistro's keg lost 2 px of its red band and
# its top part (cap, boiler, grape label, spout) hangs 2 px lower, so its spout, FILL_DY 2 and the glass follow.
import pytest
from conftest import GAME, LAYOUT, THEMES, bar_top_y, fill_top_y, mug_top_y, title_level
from test_art import goto_group
from test_lift import oam_lines
from test_spigot import VDIR, art_frames, built_frames, nozzle, stream_pixels
from test_venues import GROUP_THEME, GROUPS, at_theme, venue

pytestmark = pytest.mark.timeout(240)

BT_DY = LAYOUT["BT_DY"]
OAM_FILL = GAME["OAM_FILL"]
KEG = range(144, 160)


def bar_rows(t):
    return [r for r in (VDIR / f"{t}_bar.txt").read_text().splitlines() if r and not r.startswith(";")]


def keg_extent(t):
    """(first, last) bar-art row with a pixel in the keg columns (x 144-159)."""
    rows = bar_rows(t)
    used = [y for y in range(24) if any(rows[y][x] != "." for x in KEG)]
    return used[0], used[-1]


def test_the_bistro_keg_is_22_px_with_a_gap_to_the_next_bars_keg():
    first, last = keg_extent("bistro")
    assert (first, last) == (2, 23), "22 px tall: 2 px shorter than the 24 px keg that touched the next bar's"
    rows = bar_rows("bistro")
    gap = first + (24 - 1 - last)                  # blank rows between this keg's last row and the next bar's first
    assert gap == 2
    # the grape label (its frame is a box of 9 rows, x 147-156) is in the vertical middle of the 22 px barrel (rows 2-23)
    frame = [y for y in range(24) if rows[y][147:157] == "#" * 10]
    frame = [y for y in frame if 6 <= y <= 20]
    assert frame == [9, 17], frame
    assert abs((frame[0] + frame[1]) / 2 - (first + last) / 2) <= 0.5
    # the spout: its tip over the glass at SPOUT_X, 2 px lower than before (7 -> 9), FILL_DY 2 under it
    assert max(y for y in range(16) for x in range(136, 144) if rows[y][x] != ".") == 8   # 9 until the stream was made 2 px (thumb 1 row shorter)
    assert venue("bistro")["fill_dy"] == 3, "the glass hangs 3 px lower: 2 px of the stream show above its rim"


def screen_px(gb, x, y):
    return gb.image().convert("RGB").getpixel((x, y))


def test_bistro_kegs_do_not_touch_on_screen(boot):
    """On the running game, both models: between one bar's keg and the next bar's, 2 screen rows show the wall."""
    at_theme(boot, GROUPS.index("chefs"))
    boot.run(30)
    for b in range(3):
        last_row = bar_top_y(b) + 23                 # the lowest pixel row of bar b's keg
        for dy in (1, 2):                            # the next bar's first two rows
            for x in range(146, 158):
                wall = screen_px(boot, 159, last_row + dy)
                assert screen_px(boot, x, last_row + dy) == wall, (b, dy, x)
        for x in range(147, 157):                    # and the keg itself is there on both sides of the gap
            assert screen_px(boot, x, last_row) != screen_px(boot, 159, last_row), (b, x)
            assert screen_px(boot, x, last_row + 3) != screen_px(boot, 159, last_row + 3), (b, x)


@pytest.mark.parametrize("group", range(len(GROUPS)), ids=[GROUP_THEME[g] for g in GROUPS])
def test_the_glass_hangs_under_the_spout_and_the_stream_joins_both(boot, group):
    """Every venue, both models, while A fills the glass: the glass is at SPOUT_X, FILL_DY below a sliding mug; the stream
    starts on the pixel row right under the spout's tip, runs without a break, and ends in the glass (on the drink)."""
    t = THEMES[group]
    at_theme(boot, group)
    boot.run(30)
    boot.write("intro_timer", 255)
    boot.hold("a")
    boot.run(3)
    o = boot.oam()[OAM_FILL]
    assert o["x"] - 8 == GAME["SPOUT_X"] and o["y"] - 16 == fill_top_y(0, group) == mug_top_y(0) + venue(t)["fill_dy"]
    rows = bar_rows(t)
    tip = max(y for y in range(16) for x in range(136, 144) if rows[y][x] != ".")
    xs = nozzle(t)
    for k in range(3):
        d = stream_pixels(t, k)
        top, bottom = min(r for r, _ in d), max(r for r, _ in d)
        assert o["y"] - 16 + top == bar_top_y(0) + tip + 1, (t, k, "the stream starts right under the spout's tip")
        cols = sorted({c for _, c in d})
        art = art_frames(t)[k]
        for c in cols:                               # no break: every row from the first to the last is the stream or the glass's own pixel in front of it
            assert all((r, c) in d or art[r][c] != "." for r in range(top, bottom + 1)), (t, k, c, "no break in the stream")
        assert any(xs[0] <= GAME["SPOUT_X"] + c <= xs[-1] for c in cols), (t, k, "under the spout")
        full = built_frames(t)[3]
        assert any(full[bottom + 1][c] != 0 for c in cols), (t, k, "the stream ends on the glass / the drink")
    boot.release("a")


@pytest.mark.parametrize("group", range(len(GROUPS)), ids=[GROUP_THEME[g] for g in GROUPS])
def test_the_spout_is_over_the_glass_on_screen(boot, group):
    """The stream's first pixel on the screen has a spout pixel of the bar art right above it."""
    t = THEMES[group]
    at_theme(boot, group)
    boot.run(30)
    boot.write("intro_timer", 255)
    boot.hold("a")
    boot.run(3)
    o = boot.oam()[OAM_FILL]
    d = stream_pixels(t, 0)
    r0 = min(r for r, _ in d)
    c = min(c for r, c in d if r == r0)
    x, y = o["x"] - 8 + c, o["y"] - 16 + r0
    spout = bar_rows(t)[y - 1 - bar_top_y(0)][x]
    assert spout != ".", (t, "a spout pixel over the stream's first pixel")
    boot.release("a")


@pytest.mark.parametrize("bar", range(4))
def test_the_bartender_is_2_px_lower_in_every_row(boot, bar):
    title_level(boot, 1)
    boot.run(40)
    boot.write("tip_chance", 0)
    boot.write("intro_timer", 255)
    boot.run(20)
    for _ in range(bar):
        boot.press("down", 2)
        boot.run(10)
    assert boot.mem("bar") == bar
    o = boot.oam()
    assert BT_DY == 2
    assert [o[i]["y"] - 16 for i in (0, 1, 2, 3)] == [bar_top_y(bar) + BT_DY] * 2 + [bar_top_y(bar) + BT_DY + 16] * 2


SAMPLE_FRAMES = 600


def sample_run(gb, group):
    """perf_helpers.realistic_run's play (the RealisticPeak crowd on the level-8 script: fills, launches, catches, bar changes,
    lifted patrons, tips), but in the venue of `group` instead of level 10's; returns the worst line count of any frame."""
    from perf_helpers import SCRIPT, RealisticPeak
    at_theme(gb, group)
    gb.write("intro_timer", 0)
    gb.write("tip_chance", 0)
    rp = RealisticPeak(gb, 10)
    rp.seed()
    gb.run(2)
    worst, held, bars = 0, None, set()
    for i in range(SAMPLE_FRAMES):
        want = SCRIPT[i % len(SCRIPT)]
        if want != held:
            if held:
                gb.release(held)
            if want:
                gb.hold(want)
            held = want
        rp.tick()
        gb.run(1)
        worst = max(worst, max(oam_lines(gb)))
        bars.add(gb.mem("bar"))
    return worst, bars


@pytest.mark.parametrize("group", range(len(GROUPS)), ids=[GROUP_THEME[g] for g in GROUPS])
def test_ten_objects_a_line_on_every_frame_of_a_play_sample(boot, group):
    """Every venue, both models: patrons, mugs, tips and the bartender (2 px lower) on every bar, 600 frames, never an 11th
    object on a line."""
    worst, bars = sample_run(boot, group)
    assert len(bars) >= 2, "the script changed bars"
    assert worst <= GAME["LINE_OBJ_MAX"], worst


# Every venue's keg (owner 2026-10-17: "look at the kegs, all that are so tall they leave no headroom, fix them like the juice keg").
# Each lost 1-2 px of a plain middle section (the saloon 1, the others 2), the top part hangs lower and the bottom stays on the counter's
# last row; labels, lids, spouts, lightning and the star are untouched. The spouts that sit below the cut hang lower with it: the lodge's
# 2 px (FILL_DY 0 -> 3, a 2 px stream), the teahouse's 1 px (FILL_DY 2 -> 3), the factory's 2 px (FILL_DY 0, its stream just gets shorter).
GAP_MIN = 2


@pytest.mark.parametrize("theme", THEMES)
def test_every_keg_leaves_a_gap_to_the_next_bars_keg_in_the_art(theme):
    first, last = keg_extent(theme)
    assert last == 23, (theme, "the keg stands on the bar's last row")
    assert first + (24 - 1 - last) >= GAP_MIN, (theme, first, last)


def screen_gap(gb, b, wall_x):
    """Blank screen rows between the lowest row of bar b's keg (x 144-158) and the first keg row of the bar below."""
    gap, y = 0, bar_top_y(b) + 24
    while gap < 6 and all(screen_px(gb, x, y) == screen_px(gb, wall_x, y) for x in range(144, 159)):
        gap, y = gap + 1, y + 1
    return gap


@pytest.mark.parametrize("group", range(len(GROUPS)), ids=[GROUP_THEME[g] for g in GROUPS])
def test_every_keg_leaves_a_gap_on_screen(boot, group):
    """Both models, every venue: the rows right under a bar's keg show the wall for at least GAP_MIN rows before the next keg."""
    t = THEMES[group]
    at_theme(boot, group)
    boot.run(30)
    rows = bar_rows(t)
    wall_x = next(x for x in range(100, 136) if all(rows[y][x] == "." for y in range(0, 4)))
    for b in range(3):
        assert screen_px(boot, 152, bar_top_y(b) + 23) != screen_px(boot, 152, bar_top_y(b) + 24), (t, b, "keg's last row, then wall")
        assert screen_gap(boot, b, wall_x) >= GAP_MIN, (t, b)


@pytest.mark.parametrize("group", range(len(GROUPS)), ids=[GROUP_THEME[g] for g in GROUPS])
def test_the_stream_shows_2_to_3_px_above_the_glass(boot, group):
    """Owner 2026-10-17 ("can you see the stream?"): on screen, both models, every venue: the rows between the spout's tip and the
    rim of the empty glass (the first row of the glass sprite that has a pixel) show the stream, 2 or 3 of them."""
    t = THEMES[group]
    at_theme(boot, group)
    boot.run(30)
    boot.write("intro_timer", 255)
    boot.hold("a")
    boot.run(3)
    o = boot.oam()[OAM_FILL]
    top = o["y"] - 16
    d = stream_pixels(t, 0)
    r0 = min(r for r, _ in d)
    art = art_frames(t)[0]
    rim = min(r for r in range(16) if any(art[r][c] != "." for c in range(8)))
    c = min(c for r, c in d if r == r0)
    wall = screen_px(boot, o["x"] - 8 + c, top + r0)
    visible = rim - r0
    assert 2 <= visible <= 3, (t, visible)
    for r in range(r0, rim):                         # the screen shows the stream's pixels on those rows, not the wall
        assert any(screen_px(boot, o["x"] - 8 + cc, top + r) != screen_px(boot, 100, top + r) for cc in {cc for rr, cc in d if rr == r}), (t, r)
    boot.release("a")


def test_the_factory_bolt_is_centred_in_its_box_and_the_saloon_star_is_whole():
    rows = bar_rows("factory")
    bolt = [y for y in range(4, 13) if any(rows[y][x] == "-" for x in range(150, 158))]
    assert bolt and bolt[0] - 4 == 12 - bolt[-1], ("the same blank rows above and below the bolt in its box (rows 4-12)", bolt)
    star = {(x, y) for y in range(13, 19) for x in range(148, 155) if bar_rows("saloon")[y][x] == "-"}
    assert len(star) >= 8
