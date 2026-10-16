# How the bartender changes bars (owner playtest, batch B2). Two behaviours, switched in the debug box (START):
#   B, the default and CLASSIC always: Up/Down snaps him to the new bar's tap; a dust puff (3 frames of 4 video frames,
#      OBJ ids 246..251 in OAM 26, cue_t bit 7) shows where he stood and SFX_SWISH plays.
#   A, KEEP (level_dirs bit 7, KEEP_POS): he keeps his place (mirrored on screen between an L and an R bar, up to the new
#      tap); pouring needs the tap, so he walks back (a fresh A within TAP_GRACE of it still snaps and pours).
# The Pour-Off (src/po.c) keeps its own rules in both modes.
import pytest
from conftest import GAME, K_CLASSIC, K_PLAY, bar_top_y, check_golden, title_pick
from test_classic_mode import classic_at
from test_debug import banner_text, combo, release_combo

pytestmark = pytest.mark.timeout(240)

TAP_X, LEFT_LIMIT, TAP_GRACE = GAME["TAP_X"], GAME["LEFT_LIMIT"], GAME["TAP_GRACE"]
SFX_SWISH = 14
OBJ_DUST = 234                    # (a story's: 246; tiles are shared with mirror.c / pour.c, never in use together)
KEEP_POS = 0x80
DUST_LEN = 12


def dust(gb):
    """The puff's sprite (tile 246..251), or None."""
    d = [s for s in gb.visible_sprites() if OBJ_DUST <= s["tile"] <= OBJ_DUST + 5 or 246 <= s["tile"] <= 251]
    assert len(d) <= 1
    return d[0] if d else None


def start_dirs(gb, lv_dirs):
    """The LEVEL harness at level 1 with level_dirs = lv_dirs (bits 0-3: the bars' directions, bit 7: KEEP_POS)."""
    from conftest import title_level
    gb.write("level_dirs", lv_dirs)
    title_level(gb)
    gb.run(40)
    assert gb.mem("game_state") == 1 and gb.mem("bar_dirs") == lv_dirs & 0xF
    gb.write("tip_chance", 0)
    gb.run(2)
    return gb


def mode_a(gb):
    gb.write("level_dirs", gb.mem("level_dirs") | KEEP_POS)


def test_b_is_the_default_and_snaps_with_a_puff_and_a_whoosh(gb):
    assert gb.mem("level_dirs") & KEEP_POS == 0
    gb.press("left", 30)
    x0 = gb.mem("bartender_x")
    assert x0 == TAP_X - 45
    w0 = gb.read("sfx_count", 15)[SFX_SWISH]
    gb.press("down", 1)
    assert gb.mem("bar") == 1 and gb.mem("bartender_x") == TAP_X and gb.mem("facing") == 0
    assert gb.mem("last_sfx") == SFX_SWISH and gb.read("sfx_count", 15)[SFX_SWISH] == w0 + 1
    gb.run(1)
    seen, d = [], dust(gb)
    assert d is not None, "the puff shows"
    assert d["x"] == x0 + 8 + 4 and d["y"] == bar_top_y(0) + 16 + 8, "where he stood, on the bar he left"
    for _ in range(DUST_LEN + 4):
        d = dust(gb)
        seen.append(d["tile"] if d else None)
        gb.run(1)
    frames = [t for t in seen if t is not None]
    runs = [(t, frames.count(t)) for t in dict.fromkeys(frames)]
    assert [t for t, _ in runs] == [OBJ_DUST, OBJ_DUST + 2, OBJ_DUST + 4], runs      # 3 frames, 4 video frames each
    assert 10 <= len(frames) <= DUST_LEN and all(3 <= n <= 4 for _, n in runs), runs
    assert seen[-1] is None and gb.mem("cue_t") == 0, "and it is gone"


def test_the_puff_golden(gb):
    gb.press("left", 30)
    gb.press("down", 1)
    gb.run(5)
    assert dust(gb) is not None
    check_golden(gb, "dust_puff")


def test_the_puff_is_not_drawn_in_a(gb):
    mode_a(gb)
    gb.press("left", 30)
    w0 = gb.read("sfx_count", 15)[SFX_SWISH]
    gb.press("down", 1)
    for _ in range(DUST_LEN):
        assert dust(gb) is None
        gb.run(1)
    assert gb.read("sfx_count", 15)[SFX_SWISH] == w0, "no swish"


def test_a_keeps_his_place_and_walks_back_to_pour(gb):
    mode_a(gb)
    gb.press("left", 30)
    x0 = gb.mem("bartender_x")
    gb.press("down", 1)
    assert gb.mem("bar") == 1 and gb.mem("bartender_x") == x0 and gb.mem("at_tap") == 0 and gb.mem("facing") == 0
    gb.press("down", 2)
    gb.press("up", 2)
    assert gb.mem("bar") == 1 and gb.mem("bartender_x") == x0, "up and down keep it"
    gb.press("a", 5)                                  # away from the tap (further than TAP_GRACE): nothing to pour with
    assert gb.mem("fill_timer") == 0 and gb.mem("bartender_x") == x0
    gb.press("right", 40)
    assert gb.mem("bartender_x") == TAP_X and gb.mem("at_tap") == 1
    gb.hold("a")
    gb.run(5)
    assert gb.mem("fill_timer") > 0, "at the tap he pours"
    gb.release("a")


def test_a_within_the_grace_of_the_tap_snaps_and_pours_as_ever(gb):
    mode_a(gb)
    gb.press("left", 10)
    gb.press("down", 1)
    assert 0 < TAP_X - gb.mem("bartender_x") < TAP_GRACE
    gb.hold("a")
    gb.run(3)
    assert gb.mem("bartender_x") == TAP_X and gb.mem("fill_timer") > 0
    gb.release("a")


def test_a_a_full_drink_is_carried_to_the_next_bar_at_the_tap(gb):
    mode_a(gb)
    gb.hold("a")
    gb.run(40)
    assert gb.mem("fill_timer") >= GAME["FILL_FRAMES"]
    gb.press("down", 1)
    assert gb.mem("bar") == 1 and gb.mem("bartender_x") == TAP_X and gb.mem("fill_timer") >= GAME["FILL_FRAMES"], "carried"
    gb.release("a")


def test_a_away_from_the_tap_a_bar_change_drops_the_fill(gb):
    mode_a(gb)
    gb.hold("a")
    gb.run(40)
    gb.press("left", 1)                               # (still holding A: walking ends the fill)
    gb.release("a")
    assert gb.mem("fill_timer") == 0


def test_a_the_walk_limits_hold_after_a_change(gb):
    mode_a(gb)
    gb.press("left", 100)
    assert gb.mem("bartender_x") == LEFT_LIMIT
    gb.press("down", 1)
    assert gb.mem("bartender_x") == LEFT_LIMIT
    gb.press("left", 5)
    assert gb.mem("bartender_x") == LEFT_LIMIT


@pytest.mark.parametrize("dirs,x_after", [(0x2, None), (0x0, None)])
def test_a_between_mirrored_bars_he_keeps_his_place_on_the_screen(boot, dirs, x_after):
    """Bar 1 an R bar (the tap on the left): his left edge on the screen stays; bar-local x is 144 - x on an R bar."""
    gb = start_dirs(boot, KEEP_POS | dirs)
    gb.press("left", 10)
    x0 = gb.mem("bartender_x")
    gb.press("down", 1)
    want = 144 - x0 if dirs else x0
    assert gb.mem("bartender_x") == want, (x0, want)
    gb.press("up", 2)
    assert gb.mem("bartender_x") == x0, "and back"


def test_b_between_mirrored_bars_the_puff_is_mirrored_too(boot):
    gb = start_dirs(boot, 0x1)                             # bar 0 R: the puff is drawn mirrored
    gb.press("left", 10)
    x0 = gb.mem("bartender_x")
    gb.press("down", 1)
    gb.run(1)
    d = dust(gb)
    assert d and d["x"] == 168 - (x0 + 12) and d["y"] == bar_top_y(0) + 16 + 8


# ---- the debug box -------------------------------------------------------------------------------------------------
def box_word(gb):
    from test_flow import tile_id
    txt = banner_text(gb)
    keep = [tile_id("GLYPH_" + c) for c in "KEEP"]
    snap = [tile_id("GLYPH_" + c) for c in "SNAP"]
    for i in range(len(txt) - 3):
        if txt[i:i + 4] == keep:
            return "KEEP"
        if txt[i:i + 4] == snap:
            return "SNAP"
    return None


def test_the_debug_box_switches_the_mode_with_start(boot):
    combo(boot)
    release_combo(boot)
    boot.run(3)
    assert boot.mem("level_dirs") & KEEP_POS == 0 and box_word(boot) == "SNAP", "SNAP (mode B) by default"
    boot.press("start", 2)
    boot.run(3)
    assert boot.mem("level_dirs") & KEEP_POS and box_word(boot) == "KEEP"
    boot.press("select", 2)                           # (SELECT's own job, the bars' directions, keeps the mode)
    boot.run(3)
    assert boot.mem("level_dirs") == (KEEP_POS | 0xF) and box_word(boot) == "KEEP"
    boot.press("start", 2)
    boot.run(3)
    assert boot.mem("level_dirs") == 0xF and box_word(boot) == "SNAP"
    boot.press("start", 2)
    boot.press("a", 2)
    boot.run(30)
    assert boot.mem("game_state") == 1 and boot.mem("level_dirs") & KEEP_POS, "the game runs in A"
    boot.press("right", 20)                           # (every bar is R after SELECT: the keys swap)
    boot.press("down", 2)
    assert boot.mem("bar") == 1 and boot.mem("bartender_x") != TAP_X and boot.mem("level_dirs") & KEEP_POS


def test_the_mode_survives_a_trip_to_the_title(boot):
    boot.write("level_dirs", KEEP_POS)
    from conftest import title_level
    title_level(boot)
    boot.run(40)
    assert boot.mem("level_dirs") & KEEP_POS


def test_the_classic_box_always_reads_snap_and_start_does_nothing(boot):
    title_pick(boot, K_PLAY, K_CLASSIC, press=False)
    combo(boot)
    release_combo(boot)
    boot.run(3)
    assert boot.mem("debug_classic") == 1 and box_word(boot) == "SNAP"
    boot.press("start", 2)
    boot.run(3)
    assert boot.mem("level_dirs") & KEEP_POS == 0 and box_word(boot) == "SNAP"


def test_classic_always_snaps_with_the_dust_even_if_the_flag_is_set(boot):
    boot.write("level_dirs", KEEP_POS)
    classic_at(boot, 1)
    assert boot.mem("play_mode") == 2
    boot.write("tip_chance", 0)
    boot.press("left", 30)
    w0 = boot.read("sfx_count", 15)[SFX_SWISH]
    boot.press("down", 1)
    assert boot.mem("bartender_x") == boot.read("bar_tap", 4)[boot.mem("bar")]
    assert boot.read("sfx_count", 15)[SFX_SWISH] == w0 + 1
    boot.run(2)
    assert dust(boot) is not None


# ---- interactions ----------------------------------------------------------------------------------------------------
def count_lines(gb):
    counts = [0] * 160
    for s in gb.visible_sprites():
        top = s["y"] - 16
        for line in range(max(top, 0), min(top + 16, 144)):
            counts[line] += 1
    return max(counts)


@pytest.mark.parametrize("mode", ["B", "A"])
def test_never_more_than_ten_sprites_on_a_line_with_the_puff(boot, mode):
    from perf_helpers import realistic_run
    seen = {"max": 0, "dust": 0}

    def check(gb, i):
        seen["max"] = max(seen["max"], count_lines(gb))
        seen["dust"] += dust(gb) is not None
    if mode == "A":
        boot.write("level_dirs", KEEP_POS)
    realistic_run(boot, 600, check)
    assert seen["max"] <= 10, seen
    assert (seen["dust"] > 0) == (mode == "B"), seen


def quiet_bars(gb):
    for i in range(16):
        gb.write(gb.addr("patron_state") + i, 0)
    gb.write("patrons_live", 0)


def inject(gb, bar, x, state):
    from test_mugs import inject as inj
    inj(gb, bar, x, state)


EMPTY, EMPTY_SCORE, TIP_SCORE = 2, 100, 1500


def score(gb):
    return int.from_bytes(gb.read("score", 4), "little")


def test_a_an_empty_is_caught_by_standing_on_it_not_only_at_the_tap(gb):
    """Interaction: catching empties. In A he stands mid-bar after a change: an empty that reaches his 16 px is caught
    (mugs.c empty_step); one that slips past him (he is not at the tap) is missed and breaks at the end of the bar."""
    mode_a(gb)
    quiet_bars(gb)
    gb.press("left", 30)
    gb.press("down", 1)
    x0, s0 = gb.mem("bartender_x"), score(gb)
    inject(gb, 1, x0 + 4, EMPTY)
    gb.run(3)
    assert score(gb) == s0 + EMPTY_SCORE and gb.mem("catch_pose") > 0, "caught where he stands"
    inject(gb, 1, x0 + 40, EMPTY)                      # behind him (nearer the tap): he is not at the tap: not his
    lives = gb.mem("lives")
    gb.run(200)
    assert score(gb) == s0 + EMPTY_SCORE and gb.mem("lives") == lives - 1, "missed: it broke at the tap end"


def test_b_an_empty_at_the_end_of_the_bar_is_caught_at_the_tap_as_ever(gb):
    quiet_bars(gb)
    gb.press("left", 30)
    gb.press("down", 1)
    s0 = score(gb)
    inject(gb, 1, TAP_X + 4, EMPTY)
    gb.run(3)
    assert score(gb) == s0 + EMPTY_SCORE


@pytest.mark.parametrize("mode", ["A", "B"])
def test_tips_are_picked_up_where_he_lands(gb, mode):
    """Interaction: collecting tips (overlap, no tap needed). A: a coin where he keeps standing on the next bar is his
    on the change; B: he lands at the tap, so a coin there is his and one where he stood is not."""
    if mode == "A":
        mode_a(gb)
    gb.press("left", 30)
    x0 = gb.mem("bartender_x")
    gb.write("tip_bar", 1)
    gb.write("tip_x", x0 + 4 if mode == "A" else TAP_X + 4)
    gb.write("tip_timer", 400)
    gb.write("tip_timer", 400)
    s0 = score(gb)
    gb.press("down", 2)
    gb.run(2)
    assert score(gb) == s0 + TIP_SCORE and gb.mem("tip_timer") == 0
    gb.write("tip_bar", 2)
    gb.write("tip_x", x0 + 4)
    gb.write("tip_timer", 400)
    s0 = score(gb)
    gb.press("down", 2)
    gb.run(2)
    assert (score(gb) == s0 + TIP_SCORE) == (mode == "A")


@pytest.mark.parametrize("mode", ["A", "B"])
def test_a_boss_fight_with_either_mode(mode):
    """Interaction: the boss fights. His topper (OAM 'dancers' entry) counts the lines after the cue / puff entry, so a
    puff never makes an 11th object; the mode behaves as everywhere."""
    from test_boss import to_fight, still_regulars
    for model in ("dmg", "cgb"):
        with to_fight(model) as gb:
            still_regulars(gb)
            if mode == "A":
                mode_a(gb)
            gb.run(80)
            assert gb.mem("boss_on") == 1
            gb.press("left", 30)
            x0 = gb.mem("bartender_x")
            gb.press("down", 1)
            if mode == "A":
                assert gb.mem("bartender_x") == x0
            else:
                assert gb.mem("bartender_x") == TAP_X
            worst = 0
            for _ in range(40):
                worst = max(worst, count_lines(gb))
                gb.run(1)
            assert worst <= 10


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_pour_off_keeps_its_own_rules_in_both_modes(model):
    """Interaction: the Pour-Off (src/po.c). Your Spigoteer snaps to his tap as ever, no swish and no puff, whatever the
    mode; Dregs does not use the keys."""
    from test_pouroff import start
    from po_helpers import po
    gb = start(model)
    try:
        for flag in (0, KEEP_POS):
            gb.write("level_dirs", flag)
            w0 = gb.read("sfx_count", 15)[SFX_SWISH]
            gb.press("left", 20)
            assert po(gb)["y"]["x"] < TAP_X
            gb.press("down", 2)
            assert po(gb)["y"]["x"] == TAP_X, "snaps"
            assert gb.read("sfx_count", 15)[SFX_SWISH] == w0 and dust(gb) is None
    finally:
        gb.stop()
