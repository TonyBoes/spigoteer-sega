# docs/minigames_bosses.md 4.8: ASTEROID DELIVERY (src/ad.c), the space lounge's mini-game, on the framework (src/mg.c): the
# screen (look A's stage with look B's asteroids, the approved art pixel for pixel, its palettes, the DMG sprite palette), the
# thrust / drag / cap / walls model (a Python copy of ad.c's integer arithmetic checked frame by frame against the ROM), the
# rocks (lanes, speeds, steps, spacing), delivery (500 + the time bonus, the next porthole at random), WHOA, a rock hit and
# the tumble, time up, medals, the sprites per line on every frame (a bot that flies a whole game and a forced worst case),
# the level after it, STORY / ARCADE reaching it in chapter 10, BONUS > MINI GAMES.
import pytest
from conftest import ROOT, check_golden, hold_stage_anim, logic_paused, title_level
from ad_helpers import (AD_BG, ART, AS_FLY, AS_GAP, AS_OUT, AS_TUMBLE, LANE_SPEED, LANE_TOP0, LAYOUT, LOOP, MG_ASTEROID,
                        OBJ_BEAKER, PORTHOLE_CX, SPACE, STATE_SIZE, ad, ad_define, art_define, beaker_step, hit, plan,
                        poke, read_model, rocks_step)
from test_flow import GS_GOAL, LEVEL_CLEAR, PLAYING, TITLE, run_until, state, tilemap_row
from test_mg import (BLANK, GLYPH_CH, GS_MGLIST, GS_MINI, MEDAL_PTS, MG_COUNT, MG_END, MG_PLAY, MG_PRACTICE, MG_RESULT,
                     MG_STORY, RESULT_MIN, frames, hud_timer, lines, mg_enter, score, text, to_play, to_result, until)
from test_mg_list import release_built  # noqa: F401  (the fixture: `make release`)

pytestmark = pytest.mark.timeout(600)

MEDAL_NONE, MEDAL_BRONZE, MEDAL_SILVER, MEDAL_GOLD = range(4)
SFX_BREAK, SFX_SERVE, SFX_COIN, SFX_SHAKE = 4, 5, 6, 8
(TIME_S, PAR, PTS, GOLD, SILVER, BRONZE, TUMBLE, SPILL_WAIT, DELIVER_WAIT, WHOA_LEN, START_X, START_Y, OBP1) = (
    ad_define(n) for n in ("AD_TIME_S", "AD_PAR", "AD_PTS", "AD_GOLD", "AD_SILVER", "AD_BRONZE", "AD_TUMBLE", "AD_SPILL_WAIT",
                           "AD_DELIVER_WAIT", "AD_WHOA_LEN", "AD_START_X", "AD_START_Y", "AD_OBP1"))
OAM_BEAKER, OAM_PUFF, OAM_HALO, OAM_ARROW, OAM_SPIG, OAM_ROCK = (ad_define(n) for n in (
    "OAM_BEAKER", "OAM_PUFF", "OAM_HALO", "OAM_ARROW", "OAM_SPIG", "OAM_ROCK"))
STEP1, STEP2, WARN, ZONE_HALF = (ad_define(n) for n in ("AD_STEP1", "AD_STEP2", "AD_WARN", "AD_ZONE_HALF"))
OAM_WARN = ad_define("OAM_WARN")
SEED = 0x5A17
S_PALETTE = 0x10
OUT = ROOT / "out" / "ad"
HUD_PAL = 1


def asteroid(model, mode=MG_PRACTICE, seed=SEED):
    """A booted rom on the title, then Asteroid Delivery in practice (or `mode`)."""
    from test_scores import booted
    rom = booted(model)
    hold_stage_anim(rom)
    mg_enter(rom, MG_ASTEROID, mode, seed)
    return rom


def shot(gb, name):
    OUT.mkdir(parents=True, exist_ok=True)
    gb.screenshot(OUT / f"{name}.{gb.model_name}.png", 4)


def oam(gb, i):
    a = 0xFE00 + 4 * i
    return dict(y=gb.mem(a), x=gb.mem(a + 1), tile=gb.mem(a + 2), prop=gb.mem(a + 3))


def snap(gb):
    """The state as of a whole game frame: read in a paused frame (conftest.logic_paused): a read at PyBoy's frame end can catch
    the game's update half done (a 16-bit field with one byte new)."""
    with logic_paused(gb):
        return ad(gb)


def to_flying(gb, extra=6):
    to_play(gb)
    frames(gb, extra)


def hold_for(gb, keys, n, worst=None, log=None, park=False):
    """Hold `keys` for n game frames (each frame's state is logged when `log` is a list; park: the rocks are put off screen
    before every frame)."""
    for k in keys:
        gb.hold(k)
    for _ in range(n):
        if park:
            park_rocks(gb)
        frames(gb, 1, worst)
        if log is not None:
            log.append(snap(gb))
    for k in keys:
        gb.release(k)


def put_beaker(gb, x, y, vx=0, vy=0):
    poke(gb, x=x << 8, y=y << 8, vx=vx, vy=vy)


def at_dock(gb, x, vx=0, vy=-100):
    """The beaker 30/256 px under the closed-dock line (flask top 28), moving up: the next frame crosses it."""
    poke(gb, x=x << 8, y=(28 << 8) + 30, vx=vx, vy=vy)


# ---- the screen -------------------------------------------------------------------------------------------------------------
def star_hash(c, r):
    h = (c * 7 + r * 13 + (c * r) % 5) % 11
    return {0: 1, 3: 2, 6: 3, 9: 4}.get(h, 0)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_screen_and_its_art(model):
    """The intro: the banner over the portholes, the HUD (score, the beaker icon and 0, the hourglass and 45), the starfield and lane lines
    (the mock-up's star hash), the counter, the lit porthole's tiles, the tiles of the approved art, the sprites (beaker, halo,
    arrow, the Spigoteer's bust, ten rocks), the palettes (CGB) and OBP1 (DMG)."""
    with asteroid(model) as gb:
        assert gb.mem("mg_id") == MG_ASTEROID and gb.mem("mg_mode") == MG_PRACTICE and gb.mem("mg_phase") == 0
        assert gb.mem("venue_id") == SPACE
        frames(gb, 30)
        assert text(gb, 2) == "ASTEROID DELIVERY" and text(gb, 3) == "STEER AND LAND SOFT"
        assert hud_timer(gb) == "45" and score(gb) == 0 and gb.mem16("mg_timer") == 0
        assert tilemap_row(gb, 0, 10, 4) == [BLANK, AD_BG + ART["hudi"], BLANK, 36], "the icon at 11 and the count (no X; glyph 0 is 36)"
        s = ad(gb)
        assert (s["delivered"], s["st"], s["time"], s["x"], s["y"], s["vx"], s["vy"]) == (
            0, AS_FLY, TIME_S * 60, START_X << 8, START_Y << 8, 0, 0)
        assert s["lit"] in (0, 1, 2)
        # the tiles of the art
        got = b"".join(bytes(gb.read((0x9000 + t * 16) if t < 128 else (0x8000 + t * 16), 16))
                       for t in range(AD_BG, AD_BG + ART["n_bg"]))
        assert got == bytes(ART["bg"]), "BG tiles"
        assert bytes(gb.read(0x8000 + 58 * 16, len(ART["obj_a"]))) == bytes(ART["obj_a"]), "OBJ tiles (58..)"
        assert bytes(gb.read(0x8000 + 96 * 16, len(ART["obj_b"]))) == bytes(ART["obj_b"]), "OBJ tiles (96..)"
        # the map: the sky (rows 4-14), the counter (17), the portholes (rows 1 and 3; row 2 holds the framework's text)
        tm = gb.bg_tilemap()
        for r in range(4, 15):
            for c in range(20):
                v = star_hash(c, r)
                want = AD_BG + (ART["sky"][v] if r & 1 else ART["sep"][v])
                assert tm[r][c] & 0xFF == want, (r, c)
        for c in range(20):
            assert tm[17][c] & 0xFF == AD_BG + ART["counter"][(c >> 1) & 1], c
        for p, col in enumerate((1, 8, 15)):
            for k in range(3):
                assert tm[1][col + k] & 0xFF == AD_BG + ART["port"][p][1 if s["lit"] == p else 0][k], (p, k)
        if model == "cgb":
            for r in range(4, 15):
                assert all(gb.pb.memory[1, 0x9800 + r * 32 + c] & 7 == 2 for c in range(20)), r
            assert all(gb.pb.memory[1, 0x9800 + 17 * 32 + c] & 7 == 3 for c in range(20))
            for p, col in enumerate((1, 8, 15)):
                assert [gb.pb.memory[1, 0x9800 + 32 + col + k] & 7 for k in range(3)] == [5 + p] * 3
            from test_venues import cgb_palette
            assert [cgb_palette(gb, i) for i in (2, 3, 5, 6, 7)] == [ART["pal_bg"][0], ART["pal_bg"][1], *ART["pal_bg"][2:]]
            assert [cgb_palette(gb, i, obj=True) for i in (3, 7, 6)] == ART["pal_obj"]
            # colour 0 of each alien's palette is the lounge's wall (the venue's bar palette 0)
            assert ART["pal_bg"][2][0] == ART["pal_bg"][3][0] == ART["pal_bg"][4][0] == cgb_palette(gb, 0)[0]
            assert cgb_palette(gb, 4) != cgb_palette(gb, 7), "palette 4 is left to the result's medal"
        # the sprites
        b = oam(gb, OAM_BEAKER)
        assert (b["y"], b["x"], b["tile"]) == (START_Y + 16, START_X + 4, OBJ_BEAKER)
        a = oam(gb, OAM_ARROW)
        assert (a["y"], a["x"]) == (32 + 16, [20, 76, 132][s["lit"]] - 4 + 8) and a["tile"] == ART["arrow"][0]
        h0, h1 = oam(gb, OAM_HALO), oam(gb, OAM_HALO + 1)
        assert (h0["y"], h0["x"], h1["x"]) == (START_Y + 16, START_X - 8 + 8, START_X + 8)
        sp0, sp1 = oam(gb, OAM_SPIG), oam(gb, OAM_SPIG + 1)
        assert (sp0["y"], sp0["x"], sp0["tile"], sp1["x"], sp1["tile"]) == (136, 52, 0, 60, 2)
        for k in range(10):
            for half in (0, 1):
                o = oam(gb, OAM_ROCK + 2 * k + half)
                if o["y"]:
                    assert o["y"] == LANE_TOP0 + 16 * (k >> 1) + 16
                    shape = (k + (k >> 1)) & 1
                    assert o["tile"] == ART["rock"][2 * shape + half]
        if model == "dmg":
            assert gb.mem(0xFF49) == OBP1 and gb.mem(0xFF48) == 0xD0 and gb.mem(0xFF47) == 0xE4
            assert all(oam(gb, i)["prop"] & S_PALETTE for i in (OAM_BEAKER, OAM_HALO, OAM_ARROW, OAM_ROCK))
            assert not sp0["prop"] & S_PALETTE, "the Spigoteer: OBP0"
        else:
            assert b["prop"] & 7 == 1 and oam(gb, OAM_ARROW)["prop"] & 7 == 7 and h0["prop"] & 7 == 6
            assert oam(gb, OAM_ROCK)["prop"] & 7 == 3 and sp0["prop"] & 7 == 0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_banner_rows_become_portholes_again_when_play_starts(model):
    """The framework's name and instruction are written over map rows 2-3 (the portholes' middle and foot); the first play
    frame puts the portholes' tiles (and, CGB, their palettes and the wall's) back."""
    with asteroid(model) as gb:
        to_flying(gb)
        s = ad(gb)
        tm = gb.bg_tilemap()
        for p, col in enumerate((1, 8, 15)):
            for r in (1, 2):
                for k in range(3):
                    assert tm[1 + r][col + k] & 0xFF == AD_BG + ART["port"][p][1 if s["lit"] == p else 0][3 * r + k], (p, r, k)
        assert text(gb, 2) == "" and text(gb, 3) == ""
        if model == "cgb":
            for r in (2, 3):
                pals = [gb.pb.memory[1, 0x9800 + r * 32 + c] & 7 for c in range(20)]
                assert HUD_PAL not in pals, (r, pals)
                for p, col in enumerate((1, 8, 15)):
                    assert pals[col:col + 3] == [5 + p] * 3
        assert s["started"] == 1


# ---- the rocks ----------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_rocks_drift_in_five_lanes_at_the_spec_speeds_and_keep_their_gaps(model):
    """2 rocks a lane, lane speeds 0.25 / 0.375 / 0.5 / 0.375 / 0.25 px a frame in alternating directions (lane 1 right), a
    176 px loop, the two rocks of a lane 56..120 px apart, never out of their lane's 16 px."""
    with asteroid(model) as gb:
        s0 = ad(gb)
        for k in range(5):
            gap = (s0["rx"][2 * k + 1] - s0["rx"][2 * k]) % LOOP >> 8
            assert 56 <= gap <= 120, (k, gap)
        to_flying(gb)
        a = snap(gb)
        frames(gb, 50)
        b = snap(gb)
        n = b["anim"] - a["anim"]
        assert n >= 50
        for k in range(10):
            d = (b["rx"][k] - a["rx"][k]) % LOOP
            lane = k >> 1
            sp = LANE_SPEED[0][lane] * n
            want = sp if lane % 2 == 0 else (LOOP - sp) % LOOP
            assert d == want, (k, d, want)
        for i in range(10):
            for half in (0, 1):
                o = oam(gb, OAM_ROCK + 2 * i + half)
                if o["y"]:
                    assert o["y"] == LANE_TOP0 + 16 * (i >> 1) + 16, "a rock stays in its lane"


def test_the_rocks_loop_over_176_px_and_the_model_agrees():
    """The Python model of the rocks' step is the ROM's, wrap included (both directions)."""
    with asteroid("dmg") as gb:
        to_flying(gb)
        poke(gb, rx=(0, LOOP - 10), **{})
        poke(gb, rx=(2, 10))
        a = snap(gb)
        frames(gb, 1)
        b = snap(gb)
        assert b["anim"] == a["anim"] + 1
        assert b["rx"] == rocks_step(a["rx"], a["spd"])
        assert b["rx"][0] < 1000 and b["rx"][2] > LOOP - 1000


# ---- the beaker's thrust and drag ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_every_frame_the_beaker_follows_the_model(model):
    """A script of held D-pad keys (single axes, both, opposite keys): each frame the state is the model's step from the last
    frame's, with the thrust the game says it used (tx, ty)."""
    with asteroid(model) as gb:
        to_flying(gb)
        put_beaker(gb, 80, 90)
        poke(gb, rx=(0, 0))
        log = []
        script = [(["right"], 40), ([], 25), (["up", "left"], 35), (["left", "right"], 10), (["down"], 30), (["up"], 60),
                  ([], 30), (["left"], 70), (["right", "down"], 40)]
        prev = snap(gb)
        used, compared = set(), 0
        for keys, n in script:
            log = []
            hold_for(gb, keys, n, log=log, park=True)
            for s in log:
                if s["st"] != AS_FLY:
                    break
                x, y, vx, vy, ev = beaker_step(prev["x"], prev["y"], prev["vx"], prev["vy"], s["tx"], s["ty"], s["lit"])
                if s["anim"] == prev["anim"] + 1 and ev is None and not hit(x, y, s["rx"]):
                    assert (s["x"], s["y"], s["vx"], s["vy"]) == (x, y, vx, vy), (keys, s["anim"])
                    used.add((s["tx"], s["ty"])); compared += 1
                prev = s
            if log and log[-1]["st"] != AS_FLY:
                break
        assert compared >= 300 and {(1, 0), (-1, -1), (0, 0), (0, 1), (0, -1), (1, 1)} <= used, (compared, used)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_thrust_is_1_32_px_per_frame_squared_drag_1_32_and_a_cap(model):
    """From rest, the first frame of Right holds vx at 8 - 1 = 7 (8.8: thrust 8, a speed under 1/8 px loses 1 a frame), it climbs towards
    about 0.97 px a frame (never over the cap of 1.25), and released it falls to exactly 0 (the drag rounds up, so the beaker
    stops); Left and Right together give nothing."""
    with asteroid(model) as gb:
        to_flying(gb)
        put_beaker(gb, 20, 80)
        poke(gb, rx=(0, 0))
        log = []
        hold_for(gb, ["right"], 120, log=log)
        vs = [s["vx"] for s in log if s["st"] == AS_FLY]
        first = next(i for i, v in enumerate(vs) if v)
        assert vs[first] == 7 and vs[first + 1] == 14
        assert all(a < b for a, b in zip(vs[:50], vs[1:51])), "it keeps speeding up"
        assert 180 <= max(vs) <= 320, "(the wall at x 156 comes before the top speed)"
        from ad_helpers import axis
        v = 0
        for _ in range(600):
            v = axis(v, 1)
        assert v == 248, "the thrust's own limit: 0.97 px a frame, under the 1.25 cap"
        log = []
        hold_for(gb, [], 400, log=log)
        assert log[-1]["vx"] == 0 and log[-1]["vy"] == 0
        i = next(i for i, s in enumerate(log) if s["vx"] <= max(vs) // 2)
        assert 18 <= i <= 28, "half speed in about 22 frames (v -= v / 32)"
        before = snap(gb)
        hold_for(gb, ["left", "right"], 20, log=[])
        after = snap(gb)
        assert (after["x"], after["vx"]) == (before["x"], 0), "opposite keys cancel"
        hold_for(gb, ["up", "right"], 80, log=(log := []))
        assert all(abs(s["vx"]) <= 320 and abs(s["vy"]) <= 320 for s in log)
        assert max(abs(s["vy"]) for s in log) >= 150 and max(abs(s["vx"]) for s in log) >= 150, "both axes at once"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_walls_stop_the_beaker_at_the_sides_the_bar_and_closed_docks(model):
    """x stays within 4..156, y within the bar (120) and, away from the lit dock, the flask's top row 28; a wall zeroes that
    axis; over the lit dock the way up is open to y 24 (then a delivery)."""
    with asteroid(model) as gb:
        to_flying(gb)
        lit = ad(gb)["lit"]
        hold_for(gb, ["left", "down"], 200, park=True)
        s = snap(gb)
        assert s["x"] == 4 << 8 and s["y"] == 120 << 8 and s["vx"] == 0 and s["vy"] == 0
        put_beaker(gb, 150, 118)
        hold_for(gb, ["right"], 120, park=True)
        s = snap(gb)
        assert s["x"] == 156 << 8 and s["vx"] == 0
        # up, away from the lit dock: stops at 28 (the closed docks are walls)
        other = [p for p in range(3) if p != lit][0]
        put_beaker(gb, PORTHOLE_CX[other], 50)
        hold_for(gb, ["up"], 60, park=True)
        s = snap(gb)
        assert s["y"] == 28 << 8 and s["vy"] == 0 and s["delivered"] == 0 and s["bounced"] == 0, "a closed dock is a wall"
        # between two docks it is a wall too (the beaker would be inside the porthole)
        put_beaker(gb, 48, 50)
        hold_for(gb, ["up"], 60, park=True)
        assert snap(gb)["y"] == 28 << 8
        # over the lit dock the way is open: it goes up and the touch is a delivery or a WHOA, never a wall at 28
        put_beaker(gb, PORTHOLE_CX[lit], 50)
        hold_for(gb, ["up"], 60, park=True)
        s = snap(gb)
        assert s["delivered"] + s["bounced"] >= 1


# ---- delivery -------------------------------------------------------------------------------------------------------------------
def park_rocks(gb):
    """All ten rocks at x = -16 (off screen) in one paused frame: a long hold keeps calling it so no rock comes near."""
    a = gb.addr("story_scratch") + LAYOUT["rx"][0]
    with logic_paused(gb):
        for i in range(20):
            gb.write(a + i, 0)


def clear_rocks(gb):
    """Park every rock where no beaker is near the dock (the lanes' left end is far from the docks 20 / 76 / 132: put them at x 0..)."""
    for i in range(10):
        poke(gb, rx=(i, 0))


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_soft_touch_delivers_500_plus_the_time_bonus_and_lights_another_porthole(model):
    """The beaker touches the lit dock at <= 0.75 px a frame on both axes: 500 + (600 - frames) / 10, delivered 1 (the HUD's
    X1), the porthole goes dark and another lights (tiles swapped), the arrow follows, no beaker for 30 frames and then a new
    one on the bar."""
    with asteroid(model) as gb:
        to_flying(gb)
        s = ad(gb)
        lit = s["lit"]
        clear_rocks(gb)
        poke(gb, clk=200)
        at_dock(gb, PORTHOLE_CX[lit] + 3, vy=-150, vx=100)
        before = score(gb)
        frames(gb, 2)
        s = snap(gb)
        assert s["delivered"] == 1 and s["st"] == AS_GAP and s["lit"] != lit
        bonus = (PAR - (200 + 1)) // 10
        assert gb.mem16("mg_score") == PTS + bonus and score(gb) - before == PTS + bonus, (gb.mem16("mg_score"), bonus)
        assert s["clk"] <= 2, "the next porthole's clock starts again"
        tm = gb.bg_tilemap()
        for p, col in enumerate((1, 8, 15)):
            for r in range(3):
                for k in range(3):
                    assert tm[1 + r][col + k] & 0xFF == AD_BG + ART["port"][p][1 if s["lit"] == p else 0][3 * r + k]
        assert tilemap_row(gb, 0, 10, 4)[3] == 36 + 1 and tilemap_row(gb, 0, 10, 4)[2] == BLANK
        assert gb.mem("last_sfx") == SFX_COIN and gb.mem(gb.addr("sfx_count") + SFX_SERVE) >= 1
        assert oam(gb, OAM_BEAKER)["y"] == 0 and oam(gb, OAM_HALO)["y"] == 0, "the beaker is gone"
        a = oam(gb, OAM_ARROW)
        assert a["x"] == [20, 76, 132][s["lit"]] - 4 + 8, "the arrow moved with the light"
        a0 = s["anim"]
        until(gb, lambda: snap(gb)["st"] == AS_FLY, 40)
        s = snap(gb)
        assert s["anim"] - a0 in range(DELIVER_WAIT - 2, DELIVER_WAIT + 2), s["anim"] - a0
        assert (s["x"], s["y"], s["vx"], s["vy"]) == (START_X << 8, START_Y << 8, 0, 0)
        assert oam(gb, OAM_BEAKER)["y"] == START_Y + 16


@pytest.mark.parametrize("clk,bonus", [(0, 59), (300, 29), (590, 0), (600, 0), (5000, 0)])
def test_the_time_bonus_is_600_minus_the_frames_over_10(clk, bonus):
    with asteroid("dmg") as gb:
        to_flying(gb)
        lit = ad(gb)["lit"]
        clear_rocks(gb)
        poke(gb, clk=clk)
        at_dock(gb, PORTHOLE_CX[lit], vy=-100)
        frames(gb, 2)
        assert snap(gb)["delivered"] == 1
        assert gb.mem16("mg_score") == PTS + bonus + 0 or gb.mem16("mg_score") == PTS + bonus + (1 if clk == 0 else 0), \
            (gb.mem16("mg_score"), bonus)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_any_touch_of_the_ledge_delivers_anywhere_along_it_and_at_any_speed(model):
    """D6c (owner: "if your drink hits the line under the alien, it should be delivered"): the beaker's body touching the lit
    porthole's ledge anywhere along its 24 px (its left edge to its right edge, the body 6 px wide: from 14 px left of the
    dock's centre to 14 px right) and at any speed delivers: no WHOA, no bounce, nothing lost. Just outside that, and under an
    unlit porthole, the ledge is still a wall."""
    with asteroid(model) as gb:
        to_flying(gb)
        lit = ad(gb)["lit"]
        cx = PORTHOLE_CX[lit]
        n = 0
        for dx, vx, vy in ((-14, 0, -100), (-11, 150, -250), (-8, -100, -320), (0, 0, -250), (8, 200, -100), (11, 0, -320), (14, -150, -320)):
            s = snap(gb)
            lit = s["lit"]
            cx = PORTHOLE_CX[lit]
            clear_rocks(gb)
            at_dock(gb, cx + dx, vx=vx, vy=vy)
            frames(gb, 2)
            s = snap(gb)
            n += 1
            assert s["delivered"] == n and s["bounced"] == 0 and s["spills"] == 0 and s["st"] == AS_GAP, (dx, vx, vy, s["delivered"])
            poke(gb, st=AS_FLY)
        # just outside the ledge it is a wall (the beaker's body is 6 px: 15 px from the centre is clear of the 24 px porthole)
        lit = snap(gb)["lit"]
        cx = PORTHOLE_CX[lit]
        for dx in (-16, 16):
            if not (4 <= cx + dx <= 156):
                continue
            clear_rocks(gb)
            at_dock(gb, cx + dx, vy=-250)
            frames(gb, 2)
            s = snap(gb)
            assert s["delivered"] == n and s["bounced"] == 0 and s["y"] == 28 << 8, (dx, s["delivered"], s["y"])


def test_the_next_porthole_is_never_the_same_twice_and_all_three_come():
    """40 deliveries (by poking the beaker to the dock): the lit porthole always changes; every one is lit sometimes."""
    with asteroid("dmg") as gb:
        to_flying(gb)
        seen, last = set(), ad(gb)["lit"]
        seen.add(last)
        for _ in range(40):
            clear_rocks(gb)
            at_dock(gb, PORTHOLE_CX[last], vy=-100)
            frames(gb, 2)
            s = snap(gb)
            assert s["lit"] != last
            seen.add(s["lit"])
            last = s["lit"]
            poke(gb, st=AS_FLY)
        assert seen == {0, 1, 2} and snap(gb)["delivered"] == 40


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_rocks_speed_up_after_the_4th_and_the_8th_delivery(model):
    """NORMAL: x1 up to 3 deliveries, x1.25 from the 4th (AD_STEP1), x1.5 from the 8th (AD_STEP2); HARD was 3 / 6 at x1.5 / x2."""
    with asteroid(model) as gb:
        to_flying(gb)
        for n in range(1, STEP2 + 2):
            lit = ad(gb)["lit"]
            clear_rocks(gb)
            at_dock(gb, PORTHOLE_CX[lit], vy=-100)
            frames(gb, 2)
            s = snap(gb)
            assert s["delivered"] == n and s["spd"] == (0 if n < STEP1 else 1 if n < STEP2 else 2), n
            poke(gb, st=AS_FLY)
            a = snap(gb)
            frames(gb, 10)
            b = snap(gb)
            d = b["anim"] - a["anim"]
            for k in range(10):
                sp = LANE_SPEED[s["spd"]][k >> 1] * d
                want = sp if (k >> 1) % 2 == 0 else (LOOP - sp) % LOOP
                assert (b["rx"][k] - a["rx"][k]) % LOOP == want, (n, k)


# ---- a rock hit -------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_rock_spills_the_beaker_it_tumbles_30_frames_and_a_new_one_comes_at_60(model):
    """The beaker's body inside a rock's core: AS_TUMBLE (the three turns, falling), BREAK, nothing lost, no thrust works, a
    new beaker on the bar 60 frames after the hit; touching only the rock's outer rim does not spill."""
    with asteroid(model) as gb:
        to_flying(gb)
        clear_rocks(gb)
        poke(gb, rx=(4, 90 + 16 << 8))               # lane 2's first rock (lane top y 64): screen x 90 (the core 92..104)
        put_beaker(gb, 88, 64, 0, 0)                 # the body x 85..91: beside it
        frames(gb, 1)
        s = snap(gb)
        assert s["st"] == AS_FLY, "in the lane but beside the rock's core: no spill"
        put_beaker(gb, 98, 64)
        n0 = gb.mem(gb.addr("sfx_count") + SFX_BREAK)
        frames(gb, 1)
        s = snap(gb)
        assert s["st"] == AS_TUMBLE and s["spills"] == 1
        assert gb.mem(gb.addr("sfx_count") + SFX_BREAK) == n0 + 1
        pts, dl = gb.mem16("mg_score"), s["delivered"]
        t0 = s["anim"]
        xy = (s["x"], s["y"])
        hold_for(gb, ["up", "right"], 27)                   # no thrust works during the tumble
        s = snap(gb)
        assert s["st"] == AS_TUMBLE and (s["x"], s["y"]) == xy and s["vx"] == 0 and s["vy"] == 0
        shot(gb, "tumble")
        assert oam(gb, OAM_BEAKER)["tile"] in ART["tumble"] and oam(gb, OAM_BEAKER + 1)["tile"] in ART["tumble"] + [255]
        frames(gb, 4)
        s = snap(gb)
        assert s["st"] == AS_GAP and oam(gb, OAM_BEAKER)["y"] == 0
        until(gb, lambda: snap(gb)["st"] == AS_FLY, 60)
        s = snap(gb)
        assert s["anim"] - t0 in range(58, 63), s["anim"] - t0
        assert (s["x"], s["y"], s["vx"], s["vy"]) == (START_X << 8, START_Y << 8, 0, 0)
        assert gb.mem16("mg_score") == pts and s["delivered"] == dl, "nothing lost but time"


def test_the_tumble_shows_three_turns_falling():
    with asteroid("cgb") as gb:
        to_flying(gb)
        clear_rocks(gb)
        poke(gb, rx=(0, 96 + 16 << 8))
        put_beaker(gb, 100, 33)
        frames(gb, 1)
        y0, ts = None, []
        for _ in range(30):
            frames(gb, 1)
            o = oam(gb, OAM_BEAKER)
            if y0 is None:
                y0 = o["y"]
            ts.append((o["tile"], o["y"]))
        frames_seen = []
        for t, _ in ts:
            if t not in frames_seen:
                frames_seen.append(t)
        assert len(frames_seen) == 3 and set(frames_seen) <= set(ART["tumble"])
        assert ts[-1][1] - ts[0][1] >= 15, "it falls"


# ---- time up, medals ----------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_time_up_shows_a_banner_on_row_14_and_ends_the_play(model):
    with asteroid(model) as gb:
        to_flying(gb)
        poke(gb, time=2)
        frames(gb, 3)
        assert gb.mem("mg_phase") == MG_END and snap(gb)["st"] == AS_OUT
        frames(gb, 2)
        assert text(gb, 14) == "TIME UP"
        assert hud_timer(gb) == "00"
        # the beaker coasts to a stop, nothing else is scored
        put_beaker(gb, 60, 60, vx=100, vy=-100)
        frames(gb, 5)
        assert snap(gb)["delivered"] == 0 and gb.mem16("mg_score") == 0
        until(gb, lambda: gb.mem("mg_phase") == MG_RESULT, 70)


@pytest.mark.parametrize("n,medal", [(0, MEDAL_NONE), (BRONZE - 1, MEDAL_NONE), (BRONZE, MEDAL_BRONZE), (SILVER - 1, MEDAL_BRONZE),
                                     (SILVER, MEDAL_SILVER), (GOLD - 1, MEDAL_SILVER), (GOLD, MEDAL_GOLD), (GOLD + 4, MEDAL_GOLD)])
def test_the_medal_is_by_deliveries_4_6_8(n, medal):
    with asteroid("dmg") as gb:
        to_flying(gb)
        poke(gb, delivered=n)
        to_result(gb)
        assert gb.mem("mg_medal") == medal
        frames(gb, 3)
        assert text(gb, 3, True, x0=4).split()[0] in ("NO", "BRONZE", "SILVER", "GOLD")
        assert text(gb, 1, True, x0=4) == "ASTEROIDS", "the window holds 16 letters: the long name is shortened there"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_hud_counts_deliveries_and_seconds(model):
    with asteroid(model) as gb:
        to_flying(gb)
        assert hud_timer(gb) == "45"
        frames(gb, 62)
        assert hud_timer(gb) == "44"
        poke(gb, delivered=9)
        lit = ad(gb)["lit"]
        clear_rocks(gb)
        at_dock(gb, PORTHOLE_CX[lit], vy=-100)
        frames(gb, 3)
        assert snap(gb)["delivered"] == 10
        assert tilemap_row(gb, 0, 11, 3) == [AD_BG + ART["hudi"], 36 + 1, 36]


# ---- sprites per line -----------------------------------------------------------------------------------------------------------------
# ---- the edge warning (D6c) ----------------------------------------------------------------------------------------------------------
LANE_ROCKS = (1, 2, 1, 2, 1)
EDGE_TILE = ART["edge"][0]


def to_entry(lane, u):
    """ad.c's warn_lane: 8.8 px a rock still has to go before it comes in at its lane's edge (u: the rock's rx)."""
    if lane % 2 == 0:
        return (2 << 8) - u if u < (2 << 8) else (178 << 8) - u
    return u - (174 << 8) if u > (174 << 8) else u + (2 << 8)


def marker(gb, lane):
    snap(gb)                                      # (a paused frame: the OAM DMA has caught up with the update)
    o = oam(gb, OAM_WARN + lane)
    return o if o["y"] else None


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_blinking_arrow_shows_the_edge_a_rock_comes_in_at_before_it_does(model):
    """The edge arrow of a lane: right-moving lanes (0, 2, 4) at the left edge pointing right, left-moving ones at the right edge
    X-flipped, in the lane's 16 px, the arrow's OBJ palette; it blinks (4 frames on, 4 off) from AD_WARN frames before the rock comes
    in and is off earlier, after it, and for the second rock of a lane that has only one."""
    with asteroid(model) as gb:
        to_flying(gb)
        put_beaker(gb, 80, 120)
        for lane in range(5):
            for i in range(10):
                poke(gb, rx=(i, 80 << 8))                       # every rock mid screen: no marker anywhere
        frames(gb, 9)
        assert all(marker(gb, k) is None for k in range(5)), "nothing is about to come in"
        for lane in range(5):
            sp = LANE_SPEED[0][lane]
            for frames_left, want in ((WARN + 6, False), (WARN - 6, True)):
                u_edge = (2 << 8) if lane % 2 == 0 else (174 << 8)
                # a rock `frames_left` frames before it comes in: lane even moves up to 178 px then wraps, odd moves down to 0
                d = frames_left * sp
                k = 2 * lane
                u = (178 << 8) - d if lane % 2 == 0 else d - (2 << 8)
                assert to_entry(lane, u) == d
                poke(gb, rx=(k, u))
                seen = []
                for _ in range(8):
                    poke(gb, rx=(k, u))                         # (held there: the blink is what is measured)
                    frames(gb, 1)
                    seen.append(marker(gb, lane))
                on = [m for m in seen if m]
                if not want:
                    assert not on, (lane, frames_left)
                    continue
                assert 3 <= len(on) <= 5, (lane, len(on))        # 4 on, 4 off
                m = on[0]
                assert m["x"] == (0 if lane % 2 == 0 else 152) + 8 and m["y"] == LANE_TOP0 + 16 * lane + 16, (lane, m)
                assert m["tile"] == EDGE_TILE and (m["prop"] & 0x20 != 0) == (lane % 2 == 1)
                if model == "cgb":
                    assert m["prop"] & 7 == 7
                poke(gb, rx=(k, 80 << 8))
            if LANE_ROCKS[lane] == 1:                           # the lane's second rock does not exist: it warns of nothing
                k = 2 * lane + 1
                u = (178 << 8) - 5 * sp if lane % 2 == 0 else 5 * sp - (2 << 8)
                for _ in range(8):
                    poke(gb, rx=(k, u))
                    frames(gb, 1)
                    assert marker(gb, lane) is None
                poke(gb, rx=(k, 80 << 8))


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_no_rock_comes_in_unannounced_over_a_whole_game(model):
    """Over 2600 frames (the rocks at all three speed steps, the beaker parked on the bar) every time a rock is within
    AD_WARN - 8 .. 1 frames of coming in at its lane's edge, its lane's arrow shows in every window of 8 frames (it blinks)."""
    with asteroid(model) as gb:
        to_flying(gb)
        put_beaker(gb, 80, 120)
        log = {lane: [] for lane in range(5)}                   # (frames to the next entry, arrow showing)
        for f in range(2600):
            if f in (800, 1700):
                poke(gb, spd=1 if f == 800 else 2)
            put_beaker(gb, 80, 120)
            frames(gb, 1)
            s = snap(gb)
            for lane in range(5):
                sp = LANE_SPEED[s["spd"]][lane]
                tt = min((to_entry(lane, s["rx"][2 * lane + j]) / sp for j in range(LANE_ROCKS[lane])))
                log[lane].append((tt, marker(gb, lane) is not None))
        for lane in range(5):
            run, worst_gap, due = 0, 0, 0
            for tt, on in log[lane]:
                if 1 <= tt <= WARN - 8:
                    due += 1
                    run = 0 if on else run + 1
                    worst_gap = max(worst_gap, run)
                else:
                    run = 0
            assert due > 20 and worst_gap <= 4, (lane, due, worst_gap)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_worst_case_scene_is_10_a_line_at_most(model):
    """Lane 1 with both its rocks on screen, its edge arrow blinking, the lit porthole's arrow over the same lines, the beaker,
    its halo and the thrust puff: 4 + 1 + 1 + 1 + 2 + 1 = 10 (the limit is 10)."""
    with asteroid(model) as gb:
        to_flying(gb)
        for i in range(10):
            poke(gb, rx=(i, 0))
        poke(gb, rx=(2, 60 << 8))                  # lane 1 (left-moving): both rocks on screen, one about to come in at the right edge
        poke(gb, rx=(3, 8 << 8))
        poke(gb, lit=0)
        put_beaker(gb, 20, 40)
        gb.hold("right")
        worst = [0]
        seen_marker = False
        for _ in range(16):
            park = snap(gb)
            frames(gb, 1, worst)
            seen_marker |= oam(gb, OAM_WARN + 1)["y"] != 0
            poke(gb, rx=(2, 60 << 8))
            poke(gb, rx=(3, 8 << 8))
            put_beaker(gb, 20, 40)
        gb.release("right")
        assert seen_marker
        assert 9 <= worst[0] <= 10, worst
        assert snap(gb)["st"] == AS_FLY


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_bot_flies_a_whole_game_without_a_hit_and_keeps_to_10_sprites_a_line(model):
    """A search over the Python model picks the keys (4 frames a choice); the ROM's state must agree with the model all game,
    so no hit, no WHOA, and every frame <= 10 sprites a line. Whatever it delivers, the medal follows ad_medal."""
    worst = [0]
    with asteroid(model) as gb:
        to_flying(gb)
        route, waits = [], 0
        for _ in range(TIME_S * 60):
            if snap(gb)["st"] == AS_OUT or gb.mem("mg_phase") != MG_PLAY:
                break
            s = snap(gb)
            if s["st"] != AS_FLY:
                frames(gb, 1, worst)
                route = []
                continue
            p = plan(read_model(s)) or plan(read_model(s), margin=0)     # (a rock coming in at the edge may leave only the exact path)
            if p:
                route = p
            elif not route:                      # no safe route now (the rocks' gaps do not line up): wait on the bar
                waits += 1
                assert s["y"] == 120 << 8 and waits < 60, f"no plan at frame {s['anim']}"
                hold_for(gb, [], 8, worst)
                continue
            for tx, ty in route[:3]:
                keys = [k for k, on in (("right", tx > 0), ("left", tx < 0), ("down", ty > 0), ("up", ty < 0)) if on]
                st = snap(gb)
                if st["st"] != AS_FLY or st["delivered"] != s["delivered"]:
                    break
                hold_for(gb, keys, 4, worst)
            route = route[3:]
            s2 = snap(gb)
            assert s2["spills"] == 0 and s2["bounced"] == 0, (s2["spills"], s2["bounced"])
        s = snap(gb)
        assert s["spills"] == 0 and s["bounced"] == 0
        assert s["delivered"] >= 3, f"the bot delivered {s['delivered']}"
        assert worst[0] <= 10
        print(f"{model}: bot delivered {s['delivered']}, worst line {worst[0]}")


# ---- leaving it ------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_level_after_asteroid_delivery_has_everything_back(model):
    """Asteroid Delivery (a delivery, a spill) -> B to the list -> the title -> a level: the level's OBJ tiles, BG 77-255, OBP0 /
    OBP1 and every palette are byte for byte those of a level started from a fresh boot."""
    from test_bs import level_vram, palettes
    from test_scores import booted
    with booted(model) as gb:
        hold_stage_anim(gb)
        title_level(gb)
        run_until(gb, lambda: state(gb) == PLAYING, 60)
        gb.run(2)
        fresh, pals = level_vram(gb), palettes(gb)
    with asteroid(model) as gb:
        to_flying(gb)
        lit = ad(gb)["lit"]
        clear_rocks(gb)
        at_dock(gb, PORTHOLE_CX[lit], vy=-100)
        frames(gb, 3)
        poke(gb, st=AS_FLY)
        put_beaker(gb, 100, 33)
        poke(gb, rx=(0, 100 + 16 << 8))
        frames(gb, 3)
        with logic_paused(gb):
            gb.write("mg_phase", MG_RESULT)
        until(gb, lambda: gb.mem("overlay_on") == 1, 10)
        frames(gb, 2)
        gb.press("b", 2)
        run_until(gb, lambda: state(gb) == GS_MGLIST and gb.pb.memory[0xFF40] & 0x80, 30)
        gb.run(3)
        gb.press("b", 2)
        run_until(gb, lambda: state(gb) == TITLE and gb.pb.memory[0xFF40] & 0x80, 30)
        gb.run(10)
        gb.press("b", 2)
        gb.run(10)
        title_level(gb)
        run_until(gb, lambda: state(gb) == PLAYING, 60)
        gb.run(62)
        gb.run(2)
        assert level_vram(gb) == fresh
        assert palettes(gb) == pals


def story_to_mini(model, arcade=False):
    from test_story import to_shift, win
    gb = to_shift(model, SPACE, 1)
    win(gb, SPACE, 1)
    run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 20)
    run_until(gb, lambda: state(gb) == GS_MINI, 800)
    run_until(gb, lambda: gb.pb.memory[0xFF40] & 0x80, 10)
    return gb


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_story_plays_it_in_chapter_10_and_the_last_call_has_everything_back(model):
    """Chapter 10 (the space lounge): after the Happy hour, Asteroid Delivery in MG_STORY (the score carried, the count not
    skippable, unlocked for Practice at once); its result's A CONTINUE leads to the Last call, whose VRAM and palettes are those
    of the Last call reached without it."""
    from test_bs import level_vram, palettes
    from test_story import to_goal, to_shift, win
    with to_shift(model, SPACE, 2) as gb:
        gb.run(2)
        fresh, pals = level_vram(gb), palettes(gb)
    with to_shift(model, SPACE, 1) as gb:
        assert gb.mem16("mg_unlocked") == 0
        win(gb, SPACE, 1)
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 20)
        run_until(gb, lambda: state(gb) == GS_MINI, 800)
        run_until(gb, lambda: gb.pb.memory[0xFF40] & 0x80, 10)
        assert gb.mem("mg_id") == MG_ASTEROID and gb.mem("mg_mode") == MG_STORY and gb.mem("venue_id") == SPACE
        assert text(gb, 2) == "ASTEROID DELIVERY" and score(gb) > 0
        assert gb.mem16("mg_unlocked") == 1 << MG_ASTEROID
        until(gb, lambda: gb.mem("mg_phase") == MG_COUNT, 100)
        frames(gb, 3)
        gb.press("a", 1)
        assert gb.mem("mg_phase") == MG_COUNT, "no skipping in the story"
        to_play(gb)
        frames(gb, 30)
        to_result(gb)
        assert text(gb, 4, True, x0=4) == "A CONTINUE"
        until(gb, lambda: gb.mem("mg_t") >= RESULT_MIN, RESULT_MIN)
        gb.press("a", 2)
        run_until(gb, lambda: state(gb) == GS_GOAL, 60)
        gb.run(3)
        assert gb.mem("story_chapter") == SPACE and gb.mem("story_shift") == 2 and gb.mem("story_step") == 3
        to_goal(gb)
        gb.run(2)
        assert level_vram(gb) == fresh
        assert palettes(gb) == pals


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_arcade_plays_it_in_chapter_10(model):
    from test_arcade import start_arcade
    from test_story import to_goal, win
    with start_arcade(model) as gb:
        to_goal(gb)
        gb.write("story_chapter", SPACE)
        gb.write("story_step", 1)
        win(gb, 0, 0)
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 20)
        run_until(gb, lambda: state(gb) == GS_MINI, 800)
        run_until(gb, lambda: gb.pb.memory[0xFF40] & 0x80, 10)
        assert gb.mem("mg_id") == MG_ASTEROID and gb.mem("mg_mode") == MG_STORY and gb.mem("venue_id") == SPACE
        assert gb.mem("save_lock") == 1 and gb.mem16("mg_unlocked") == 1 << MG_ASTEROID
        assert text(gb, 2) == "ASTEROID DELIVERY"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_bonus_mini_games_lists_and_plays_it(model):
    """BONUS > MINI GAMES (the debug build: all unlocked): ASTEROIDS on the tenth line (chapter order), its details THE
    SPACE LOUNGE; A plays it in practice (score from 0); the result's B comes back to the list on it."""
    from test_mg_list import line, medal_word, selection, tap as list_tap, to_game, to_list
    from test_scores import booted
    with to_list(booted(model)) as gb:
        to_game(gb, 9)
        assert gb.mem("ml_sel") == 9
        list_tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_MINI and gb.pb.memory[0xFF40] & 0x80, 30)
        assert gb.mem("mg_id") == MG_ASTEROID and gb.mem("mg_mode") == MG_PRACTICE and score(gb) == 0
        assert text(gb, 2) == "ASTEROID DELIVERY"
        gb.write("mg_phase", MG_RESULT)
        run_until(gb, lambda: gb.mem("overlay_on") == 1, 10)
        frames(gb, 3)
        gb.press("b", 2)
        run_until(gb, lambda: state(gb) == GS_MGLIST and gb.pb.memory[0xFF40] & 0x80, 30)
        gb.run(3)
        assert gb.mem("ml_sel") == 9 and selection(gb) == "ASTEROIDS"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_release_list_unlocks_it_when_reached(model, release_built):
    from test_mg_list import MG_PLANNED, line, pr_block, release_rom, medal_word, selection, tap as list_tap, to_game, to_list, with_block
    from test_scores import v7_image
    best = [0] * MG_PLANNED
    best[MG_ASTEROID] = MEDAL_SILVER
    ram = with_block(v7_image(), pr_block(1 << MG_ASTEROID, best))
    with release_rom(model, ram) as gb:
        to_list(gb)
        assert selection(gb) == "? ? ?"
        to_game(gb, 9)
        assert (selection(gb), medal_word(gb)) == ("ASTEROIDS", "SILVER")
        list_tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_MINI, 30)
        assert gb.mem("mg_id") == MG_ASTEROID and gb.mem("mg_mode") == MG_PRACTICE


# ---- goldens: the intro, flying, the edge arrows, a delivery, the tumble, the result -------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_goldens(model):
    """The count-in, a flight (a seeded game: the lit porthole and the rocks follow the seed), the edge arrows, a delivery, a tumble, the result."""
    with asteroid(model) as gb:
        until(gb, lambda: gb.mem("mg_phase") == MG_COUNT and gb.mem("mg_t") >= 10, 200)
        shot(gb, "intro")
        until(gb, lambda: gb.mem("mg_phase") == MG_PLAY, 100)
        frames(gb, 2)
        s = ad(gb)
        lit = s["lit"]
        # flying: out in the lanes, thrusting up and to the right
        put_beaker(gb, 80, 100)
        hold_for(gb, ["up", "right"], 6)
        frames(gb, 1)
        shot(gb, "flying")
        check_golden(gb, "ad_flying")
        # the edge arrows (D6c): lane 1's second rock about to come in at the right edge, lane 2's at the left one; the frame is
        # taken when the blink is on
        clear_rocks(gb)
        put_beaker(gb, 80, 100)
        poke(gb, rx=(3, 8 << 8))
        poke(gb, rx=(4, (178 << 8) - 30 * 128))
        for _ in range(16):
            poke(gb, rx=(3, 8 << 8))
            poke(gb, rx=(4, (178 << 8) - 30 * 128))
            frames(gb, 1)
            if marker(gb, 1) is not None and marker(gb, 2) is not None:
                break
        frames(gb, 0)
        shot(gb, "edge")
        check_golden(gb, "ad_edge")
        # a delivery
        lit = snap(gb)["lit"]
        at_dock(gb, PORTHOLE_CX[lit], vy=-100)
        frames(gb, 3)
        shot(gb, "delivered")
        check_golden(gb, "ad_delivered")
        poke(gb, st=AS_FLY)
        # a tumble
        poke(gb, rx=(2, 60 + 16 << 8))
        put_beaker(gb, 64, 48)
        frames(gb, 14)
        shot(gb, "tumble")
        check_golden(gb, "ad_tumble")
        # the result
        poke(gb, delivered=GOLD)
        to_result(gb)
        frames(gb, 3)
        shot(gb, "result")
        check_golden(gb, "ad_result")
