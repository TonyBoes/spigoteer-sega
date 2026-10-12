# docs/minigames_bosses.md 4.2: T-SHIRT CANNON (src/ts.c), the stadium's mini-game, on the framework (src/mg.c): the screen (look A, the
# night game, plus the A1 bunting: every row of the approved art as tools/gen_ts.py laid it out, the palettes, the DMG registers), the
# controls (Up / Down steps, repeats, the dot preview), the flight against a Python model of the integer physics for every angle and
# wind (the landing table of tools/cannon_table.py), the wave and its speeds, scoring (300 in the wave, 100 next to it, 0), the reload and
# the wind schedule, the 12 shirts, the 45 s timer, medals, a bot that reads the wind and the wave and wins gold, the sprites per line,
# STORY / ARCADE reaching it in chapter 2, BONUS > MINI GAMES, what is put back when it is left.
import pytest
from conftest import ROOT, check_golden, hold_stage_anim, logic_paused
from test_flow import GS_GOAL, LEVEL_CLEAR, TITLE, run_until, state, tilemap_row
from test_mg import (BLANK, GS_MGLIST, GS_MINI, MEDAL_AT, MEDAL_PTS, MG_COUNT, MG_END, MG_PRACTICE, MG_RESULT, MG_STORY, RESULT_MIN,
                     frames, lines, mg_enter, score, text, to_play, to_result, until)
from test_mg_list import release_built  # noqa: F401  (the fixture: `make release`)
from ts_helpers import (ANGLES, ART, FAN_FIRST, FAN_N, LAYOUT, MG_TSHIRT, SHOTS, STADIUM, STATE_SIZE, TS_BG, TS_OBJ, fly, glyph, look,
                        path, points, poke, top_row, ts, ts_define, wave_interval)

pytestmark = pytest.mark.timeout(600)

MEDAL_NONE, MEDAL_BRONZE, MEDAL_SILVER, MEDAL_GOLD = range(4)
SEED = 0x5A17
OUT = ROOT / "out" / "ts"
S_PALETTE = 0x10
AIM, FLY, RELOAD, SPENT, OUTRO = range(5)
POSE_IDLE, POSE_FIRE, POSE_CHEER, POSE_MISS = range(4)
SFX_LAUNCH, SFX_CATCH, SFX_COIN = 2, 3, 6
(RELOAD_LEN, TIME_S, REPEAT, CHEER_LEN, POSE_LEN, FIRE_POSE, PUFF_LEN, PTS_WAVE, PTS_NEAR) = (ts_define(n) for n in (
    "TS_RELOAD", "TS_TIME_S", "TS_REPEAT", "TS_CHEER", "TS_POSE_LEN", "TS_FIRE_POSE", "TS_PUFF_LEN", "TS_PTS_WAVE", "TS_PTS_NEAR"))
OAM_SPIG, OAM_CANNON, OAM_PUFF, OAM_SHIRT, OAM_DOT = (ts_define(n) for n in ("OAM_SPIG", "OAM_CANNON", "OAM_PUFF", "OAM_SHIRT", "OAM_DOT"))
BT_TILES = 8                                    # the bartender's OBJ tiles a frame (src/game.h)


def game(model, mode=MG_PRACTICE, seed=SEED):
    """A booted rom on the title, then T-Shirt Cannon in practice (or `mode`)."""
    from test_scores import booted
    rom = booted(model)
    hold_stage_anim(rom)
    mg_enter(rom, MG_TSHIRT, mode, seed)
    return rom


def shot(gb, name):
    OUT.mkdir(parents=True, exist_ok=True)
    gb.screenshot(OUT / f"{name}.{gb.model_name}.png", 4)


def oam(gb, i):
    a = 0xFE00 + 4 * i
    return dict(y=gb.mem(a), x=gb.mem(a + 1), tile=gb.mem(a + 2), prop=gb.mem(a + 3))


def tap(gb, key, n=1):
    gb.hold(key)
    frames(gb, n)
    gb.release(key)
    frames(gb, 1)


def snap(gb):
    """The state as of a whole update, read in a paused frame (the VBlank copy and the OAM DMA have caught up there too)."""
    with logic_paused(gb):
        return ts(gb)


def to_aim(gb, extra=2):
    to_play(gb)
    frames(gb, extra)


def tile_bytes(gb, t):
    a = 0x9000 + t * 16 if t < 128 else 0x8000 + t * 16
    return list(gb.read(a, 16))


def bank1(gb, col, row):
    gb.pb.memory[0xFF4F] = 1
    try:
        return gb.pb.memory[0x9800 + row * 32 + col]
    finally:
        gb.pb.memory[0xFF4F] = 0


def map_row(gb, row):
    return tilemap_row(gb, row, 0, 20)


def wave_after(s, n):
    """(wave, direction, frames to the next move) n updates after the state s (the game's wave_step)."""
    w, d, t = s["wave"], s["wdir"], s["wt"]
    for _ in range(n):
        t -= 1
        if t == 0:
            t = wave_interval(s["num"])
            w += d
            if w >= 9:
                d = -1
            elif w <= 1:
                d = 1
    return w, d, t


def expected_map(s):
    """The 17 map rows (rows 1-17) as the game has them: the generator's map with each fan sitting or standing."""
    rows = [[TS_BG + t for t in ART["map"][r * 20:(r + 1) * 20]] for r in range(17)]
    for i in range(FAN_N):
        up = (s["shown"] >> i) & 1
        base = 2 * ((2 if i & 1 else 0) + up)
        rt = 11 - (i >> 1)
        rows[rt - 1][FAN_FIRST + i] = TS_BG + ART["fan"][base]
        rows[rt][FAN_FIRST + i] = TS_BG + ART["fan"][base + 1]
    return rows


def fire(gb):
    """A pressed for one update; the state after it (the shirt in the air)."""
    gb.hold("a")
    frames(gb, 1)
    gb.release("a")
    for _ in range(4):
        s = snap(gb)
        if s["st"] == FLY:
            return s
        frames(gb, 1)
    raise AssertionError("no shot")


def land(gb, limit=200):
    """Frames until the flight is over; returns the state at the landing."""
    for _ in range(limit):
        s = snap(gb)
        if s["st"] != FLY:
            return s
        frames(gb, 1)
    raise AssertionError("no landing")


def reset_aim(gb, angle, wind, wave=5, num=1, shots=0):
    """Between two updates: the state of an aim (the wave held still where it is wanted)."""
    poke(gb, st=AIM, angle=angle, wind=wind, wave=wave, wdir=1, wt=250, num=num, shots=shots, pose=POSE_IDLE, pose_t=0)


# ---- the screen ------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_screen_and_its_art(model):
    """The intro: the banner, the HUD (the shirt icon and 12, the wind), every row of the approved art as the generator laid it out
    (the stage, the bunting, the windsock, the fans), the tiles and palettes, the sprites, the DMG registers."""
    with game(model) as gb:
        assert gb.mem("mg_id") == MG_TSHIRT and gb.mem("mg_mode") == MG_PRACTICE and gb.mem("mg_phase") == 0
        assert gb.mem("venue_id") == STADIUM
        frames(gb, 30)
        assert text(gb, 2) == "SHIRT CANNON" and text(gb, 3) == "UP DOWN AIM A FIRE"
        hud = ART["hud"]
        assert tilemap_row(gb, 0, 8, 4) == [TS_BG + hud[0], glyph("1"), glyph("2"), BLANK]
        assert tilemap_row(gb, 0, 13, 2) == [TS_BG + hud[3], glyph("0")]
        assert hud_timer_ok(gb)
        got = [b for t in range(TS_BG, TS_BG + ART["n_bg"]) for b in tile_bytes(gb, t)]
        assert got == ART["bg"], "BG tiles"
        got = [b for t in range(TS_OBJ, TS_OBJ + ART["obj_tiles"]) for b in gb.read(0x8000 + t * 16, 16)]
        assert got == ART["obj"], "OBJ tiles"
        to_play(gb)
        frames(gb, 3)
        s = snap(gb)
        assert s["shown"] == 0b111 and s["wave"] == 1 and s["angle"] == 7 and s["wind"] == 0 and s["num"] == 1
        want = expected_map(s)
        for r in range(17):
            assert map_row(gb, r + 1) == want[r], f"map row {r + 1}"
        assert text(gb, 2) == "" and text(gb, 3) == ""
        if model == "cgb":
            for r in range(17):
                assert [bank1(gb, c, r + 1) for c in range(20)] == ART["attr"][r * 20:(r + 1) * 20], f"attributes of row {r + 1}"
            assert all(bank1(gb, c, 0) == 1 for c in range(20)), "the HUD's palette"
            from test_lift import cgb_obj_palette
            from test_venues import cgb_palette
            for i, p in enumerate((0, 2, 3, 5, 6, 7)):
                assert cgb_palette(gb, p) == ART["pal_bg"][i], f"BG palette {p}"
            for i, p in enumerate((1, 2, 3)):
                assert cgb_palette(gb, p, obj=True) == ART["pal_obj"][i], f"OBJ palette {p}"
        else:
            assert gb.mem(0xFF47) == 0xE4 and gb.mem(0xFF48) == 0xD0 and gb.mem(0xFF49) == 0xE4
        # the sprites: the Spigoteer idle, the 45 degree barrel, three dots, no shirt, no puff
        sp = oam(gb, OAM_SPIG)
        assert (sp["x"], sp["y"], sp["tile"]) == (12 + 8, 96 + 16, 0)
        c0, c1 = oam(gb, OAM_CANNON), oam(gb, OAM_CANNON + 1)
        l = look(7)
        assert (c0["x"], c0["y"], c0["tile"]) == (32 + 8, 104 + 16, ART["cannon"][2 * l])
        assert (c1["x"], c1["y"], c1["tile"]) == (40 + 8, 104 + 16, ART["cannon"][2 * l + 1])
        assert oam(gb, OAM_SHIRT)["y"] == 0 and oam(gb, OAM_PUFF)["y"] == 0
        for k in range(3):
            d = oam(gb, OAM_DOT + k)
            assert d["tile"] == ART["dot"] and d["y"] and d["x"]
        if model == "cgb":
            assert c0["prop"] & 7 == 3 and d["prop"] & 7 == 1
        else:
            assert c0["prop"] & S_PALETTE and not d["prop"] & S_PALETTE


def hud_timer_ok(gb):
    from test_mg import hud_timer
    return hud_timer(gb) == "T045"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_colours_are_the_approved_ones(model):
    """CGB: the sky, grass, stands and the two teams' fans on the screen are the mock-up's colours; DMG: the four greys only."""
    from PIL import Image
    with game(model) as gb:
        to_aim(gb)
        OUT.mkdir(parents=True, exist_ok=True)
        gb.screenshot(OUT / f"colours.{model}.png", 1)
    px = Image.open(OUT / f"colours.{model}.png").convert("RGB")
    if model == "dmg":
        assert len({px.getpixel((x, y)) for x in range(160) for y in range(144)}) <= 4
        return
    near = lambda a, b: all(abs(x - y) <= 8 for x, y in zip(a, b))
    assert near(px.getpixel((10, 60)), (0x38, 0x40, 0x58)), "the night sky"
    assert near(px.getpixel((10, 130)), (0x3C, 0x94, 0x48)) or near(px.getpixel((10, 130)), (0x2C, 0x70, 0x38)), "the grass"
    assert near(px.getpixel((100, 100)), (0x78, 0x80, 0xA0)) or near(px.getpixel((100, 100)), (0xC8, 0xD0, 0xE8)), "the stands"


# ---- the controls -------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_up_and_down_step_once_a_press_and_repeat_every_8_frames(model):
    with game(model) as gb:
        to_aim(gb)
        assert snap(gb)["angle"] == 7
        tap(gb, "up")
        assert snap(gb)["angle"] == 8
        tap(gb, "down")
        tap(gb, "down")
        assert snap(gb)["angle"] == 6
        reset_aim(gb, 0, 0)
        tap(gb, "down")
        assert snap(gb)["angle"] == 0, "no angle below 10 degrees"
        reset_aim(gb, 10, 0)
        tap(gb, "up")
        assert snap(gb)["angle"] == 10, "no angle above 60 degrees"
        # held: the press, then a step every 8 frames
        reset_aim(gb, 0, 0)
        poke(gb, rep=REPEAT)
        gb.hold("up")
        seen = []
        for _ in range(40):
            frames(gb, 1)
            a = snap(gb)["angle"]
            if not seen or a != seen[-1][1]:
                seen.append((len(seen), a))
        gb.release("up")
        assert [a for _, a in seen] == [1, 2, 3, 4, 5], seen
        # a release resets the repeat: one tap is one step
        reset_aim(gb, 3, 0)
        tap(gb, "up")
        frames(gb, 12)
        assert snap(gb)["angle"] == 4


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_hold_repeat_period_is_8_frames(model):
    with game(model) as gb:
        to_aim(gb)
        reset_aim(gb, 0, 0)
        poke(gb, rep=REPEAT)
        gb.hold("up")
        changes = []
        last = 0
        for f in range(60):
            frames(gb, 1)
            a = snap(gb)["angle"]
            if a != last:
                changes.append(f)
                last = a
        gb.release("up")
        gaps = [b - a for a, b in zip(changes, changes[1:])]
        assert len(changes) >= 6 and all(g == REPEAT for g in gaps), (changes, gaps)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_barrel_look_and_the_preview_dots_follow_the_angle(model):
    """The cannon's entries show the look of the angle (<= 20, <= 35, <= 50, else); the three dots are the arc's frames 6, 12, 18 without wind."""
    with game(model) as gb:
        to_aim(gb)
        for a in range(11):
            reset_aim(gb, a, 2)                     # (the wind does not bend the preview)
            poke(gb, st=AIM)
            frames(gb, 2)
            l = look(a)
            assert oam(gb, OAM_CANNON)["tile"] == ART["cannon"][2 * l] and oam(gb, OAM_CANNON + 1)["tile"] == ART["cannon"][2 * l + 1]
            mx, my = ART["muzzle"][l]
            vx, vy = ART["vel"][a]
            for k, t in enumerate((6, 12, 18)):
                d = oam(gb, OAM_DOT + k)
                x, y = mx + ((t * vx) >> 8), my + ((t * vy + 8 * t * (t - 1)) >> 8)
                assert (d["x"] - 8, d["y"] - 16) == (x - 3, y - 3), (a, k)
            if a in (0, 10):
                tap(gb, "down" if a == 0 else "up")
        # the dots are the flight's own positions without wind
        reset_aim(gb, 8, 0)
        poke(gb, st=AIM)
        pa = path(8, 0)
        frames(gb, 2)
        for k, t in enumerate((6, 12, 18)):
            d = oam(gb, OAM_DOT + k)
            assert (d["x"] - 8 + 3, d["y"] - 16 + 3) == pa[t - 1]


# ---- the flight, the wave, the score ---------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_every_angle_and_wind_flies_as_the_model_says(model):
    """The landing table: 11 angles x 5 winds, each shot fired in the game and compared with the integer model (the fan caught, the
    frames of flight), the shirt's centre on every frame against the model's path, the spin frame, then the puff and the pose."""
    with game(model) as gb:
        to_aim(gb)
        for wind in (-2, -1, 0, 1, 2):
            for a in range(11):
                reset_aim(gb, a, wind)
                poke(gb, cheer=0)
                frames(gb, 1)
                reset_aim(gb, a, wind)
                s = fire(gb)
                want_col, want_t = fly(a, wind)
                p = path(a, wind)
                assert len(p) == want_t
                while s["st"] == FLY:
                    t = s["t"]
                    if t >= 1:
                        assert (s["x"] >> 8, s["y"] >> 8) == p[t - 1], (a, wind, t)
                        if s["st"] == FLY and t < want_t:
                            o = oam(gb, OAM_SHIRT)
                            assert (o["x"] - 8 + 4, o["y"] - 16 + 4) in (p[t - 1], p[min(t, want_t) - 1]), (a, wind, t, o)
                    frames(gb, 1)
                    s = snap(gb)
                assert s["t"] == want_t, (a, wind, s["t"], want_t)
                assert s["last"] == (255 if want_col is None else want_col), (a, wind)
                assert s["st"] in (RELOAD, SPENT)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_firing_puffs_poses_and_counts_the_shirt(model):
    with game(model) as gb:
        to_aim(gb)
        reset_aim(gb, 7, 0)
        before = snap(gb)
        assert before["shots"] == 0
        gb.hold("a")
        frames(gb, 1)
        gb.release("a")
        s = snap(gb)
        assert s["st"] == FLY and s["shots"] == 1 and s["pose"] == POSE_FIRE and s["puff"] == PUFF_LEN
        assert tilemap_row(gb, 0, 8, 4)[2] in (glyph("1"), glyph("0"))
        frames(gb, 1)
        s = snap(gb)
        assert tilemap_row(gb, 0, 8, 3) == [TS_BG + ART["hud"][0], glyph("1"), glyph("1")], "11 shirts left"
        sp = oam(gb, OAM_SPIG)
        assert sp["prop"] & 0x20 and sp["tile"] == 3 * BT_TILES, "the fill pose, mirrored"
        assert oam(gb, OAM_PUFF)["y"] and oam(gb, OAM_PUFF)["tile"] == ART["puff"][0]
        assert oam(gb, OAM_DOT)["y"] == 0, "no preview in the air"
        frames(gb, PUFF_LEN // 2 + 1)
        assert oam(gb, OAM_PUFF)["tile"] == ART["puff"][1]
        frames(gb, PUFF_LEN)
        assert oam(gb, OAM_PUFF)["y"] == 0
        # a shot is not fired in the air or in the reload
        poke(gb, st=FLY)
        n = snap(gb)["shots"]
        tap(gb, "a")
        assert snap(gb)["shots"] == n


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_wave_moves_on_its_beat_and_bounces(model):
    """3 fans stand, centred on S.wave (1..9), moving a column every 20 frames (shots 1-4), 16 (5-8), 12 (9-12), up and back."""
    with game(model) as gb:
        to_aim(gb)
        for num in (1, 5, 9, 12):
            poke(gb, st=AIM, num=num, wave=1, wdir=1, wt=wave_interval(num))
            frames(gb, 1)
            seen, prev = [], snap(gb)["wave"]
            moves = []
            for f in range(40 + 18 * wave_interval(num)):
                frames(gb, 1)
                s = snap(gb)
                if s["wave"] != prev:
                    seen.append(s["wave"])
                    moves.append(f)
                    prev = s["wave"]
            gaps = [b - a for a, b in zip(moves, moves[1:])]
            assert all(g == wave_interval(num) for g in gaps), (num, gaps)
            assert seen[:10] == [2, 3, 4, 5, 6, 7, 8, 9, 8, 7][:len(seen[:10])] or seen[:8] == [2, 3, 4, 5, 6, 7, 8, 9], seen
            assert 1 <= min(seen) and max(seen) == 9
            frames(gb, 3)
            s = snap(gb)
            assert s["shown"] == sum(1 << i for i in range(FAN_N) if s["wave"] - 1 <= i <= s["wave"] + 1)
            want = expected_map(s)
            for r in range(5, 13):
                assert map_row(gb, r + 1) == want[r], (num, r + 1)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_catch_scores_300_in_the_wave_100_next_to_it_and_nothing_elsewhere(model):
    with game(model) as gb:
        to_aim(gb)
        # angle index 3 (25 degrees) with no wind lands on fan 0 (column 9)
        a = 3
        col, T = fly(a, 0)
        assert col == 0
        for wave, want, lastpts in ((1, PTS_WAVE, 3), (2, PTS_NEAR, 1), (3, 0, 0), (4, 0, 0), (9, 0, 0)):
            reset_aim(gb, a, 0, wave=wave)
            before = gb.mem16("mg_score")
            hud_before = score(gb)
            fire(gb)
            s = land(gb)
            assert s["last"] == 0 and s["lastpts"] == lastpts, (wave, s["last"], s["lastpts"])
            assert gb.mem16("mg_score") - before == want and score(gb) - hud_before == want, wave
            assert s["cheer"][0] == CHEER_LEN, "the catching fan cheers"
            assert s["pose"] == (POSE_CHEER if want else POSE_MISS) and s["pose_t"] == POSE_LEN
            frames(gb, 2)
            sp = oam(gb, OAM_SPIG)
            f = 5 if want else 6
            assert sp["tile"] == f * BT_TILES and bool(sp["prop"] & 0x20) == bool(want)
            assert snap(gb)["shown"] & 1, "the fan stands while it cheers"
            assert oam(gb, OAM_SHIRT)["y"] == 0, "the shirt is gone"
            reset_aim(gb, a, 0, wave=wave)
            poke(gb, st=AIM)
        # a shot that is lost: nothing, the failing pose, the lost column 255
        reset_aim(gb, 0, 0, wave=5)
        fire(gb)
        s = land(gb)
        assert s["last"] == 255 and s["lastpts"] == 0 and s["pose"] == POSE_MISS


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_cheer_lasts_30_frames_then_the_fan_sits_down(model):
    with game(model) as gb:
        to_aim(gb)
        reset_aim(gb, 3, 0, wave=6)
        fire(gb)
        s = land(gb)
        assert s["last"] == 0 and s["cheer"][0] == CHEER_LEN
        frames(gb, 2)
        assert snap(gb)["shown"] & 1
        for _ in range(CHEER_LEN - 3):
            frames(gb, 1)
        frames(gb, 3)
        s = snap(gb)
        assert s["cheer"][0] == 0 and not s["shown"] & 1
        rows = tilemap_row(gb, 11, 9, 1) + tilemap_row(gb, 12, 9, 1)
        assert rows == [TS_BG + ART["fan"][4], TS_BG + ART["fan"][5]] or rows == [TS_BG + ART["fan"][0], TS_BG + ART["fan"][1]]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_reload_is_40_frames_and_the_new_wind_shows_at_its_end(model):
    with game(model) as gb:
        to_aim(gb)
        reset_aim(gb, 3, 0, wave=6, num=4)             # shot 4: the wind may be -1, 0 or 1
        fire(gb)
        s = land(gb)
        assert s["st"] == RELOAD and s["reload"] == RELOAD_LEN and s["num"] == 4
        calm = tilemap_row(gb, 3, 1, 3) + tilemap_row(gb, 4, 1, 3)
        for _ in range(RELOAD_LEN - 2):
            frames(gb, 1)
            assert snap(gb)["st"] == RELOAD
        frames(gb, 3)
        s = snap(gb)
        assert s["st"] == AIM and s["num"] == 5 and s["shots"] == 1
        k = s["wind"]
        assert -1 <= k <= 1
        sock = ART["sock"][k if k >= 0 else 2 - k]
        assert tilemap_row(gb, 3, 1, 3) + tilemap_row(gb, 4, 1, 3) == [TS_BG + t for t in sock]
        assert tilemap_row(gb, 0, 13, 2) == [TS_BG + ART["hud"][3 + k], glyph(str(abs(k)))]
        assert calm == [TS_BG + t for t in ART["sock"][0]]


@pytest.mark.parametrize("seed", [SEED, 0x1234, 0xBEEF])
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_wind_schedule(model, seed):
    """Shots 1-3 calm; 4-8 k in -1..1; 9-12 k in -2..2 (and the windsock and the HUD show it); 12 shots end the round."""
    with game(model, seed=seed) as gb:
        to_aim(gb)
        winds = {}
        for n in range(1, SHOTS + 1):
            s = snap(gb)
            while s["st"] != AIM:
                frames(gb, 1)
                s = snap(gb)
            assert s["num"] == n and s["shots"] == n - 1
            winds[n] = s["wind"]
            sock = ART["sock"][s["wind"] if s["wind"] >= 0 else 2 - s["wind"]]
            assert tilemap_row(gb, 3, 1, 3) + tilemap_row(gb, 4, 1, 3) == [TS_BG + t for t in sock], n
            poke(gb, angle=0, wave=5, wt=250)
            fire(gb)
            land(gb)
        assert [winds[n] for n in (1, 2, 3)] == [0, 0, 0]
        assert all(-1 <= winds[n] <= 1 for n in range(4, 9)) and all(-2 <= winds[n] <= 2 for n in range(9, 13))
        until(gb, lambda: gb.mem("mg_phase") == MG_END, 100)
        assert snap(gb)["shots"] == SHOTS


def test_the_winds_vary_over_seeds():
    """(a model of mg_rand is not needed: over three seeds each range shows more than one wind) -- a quick sanity check on the real game."""
    seen = {4: set(), 9: set()}
    for seed in (SEED, 0x1234, 0xBEEF, 0x4321):
        with game("cgb", seed=seed) as gb:
            to_aim(gb)
            for n in range(1, 10):
                s = snap(gb)
                while s["st"] != AIM:
                    frames(gb, 1)
                    s = snap(gb)
                if n >= 4:
                    seen[4 if n < 9 else 9].add(s["wind"])
                poke(gb, angle=0, wave=5, wt=250)
                fire(gb)
                land(gb)
    assert len(seen[4]) >= 2 and len(seen[9]) >= 2, seen


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_twelfth_shirt_ends_the_round(model):
    with game(model) as gb:
        to_aim(gb)
        for n in range(SHOTS):
            s = snap(gb)
            while s["st"] != AIM:
                frames(gb, 1)
                s = snap(gb)
            assert tilemap_row(gb, 0, 9, 2) == [glyph(str((SHOTS - n) // 10)), glyph(str((SHOTS - n) % 10))], n
            poke(gb, angle=0, wave=5, wt=250)
            fire(gb)
            land(gb)
        s = snap(gb)
        assert s["st"] == SPENT and s["shots"] == SHOTS and gb.mem("mg_phase") == 2
        frames(gb, 3)
        assert tilemap_row(gb, 0, 9, 2) == [glyph("0"), glyph("0")]
        tap(gb, "a")
        assert snap(gb)["shots"] == SHOTS
        until(gb, lambda: gb.mem("mg_phase") == MG_END, RELOAD_LEN + 5)
        frames(gb, 2)
        assert snap(gb)["st"] == OUTRO and oam(gb, OAM_SHIRT)["y"] == 0 and oam(gb, OAM_DOT)["y"] == 0
        until(gb, lambda: gb.mem("mg_phase") == MG_RESULT, 80)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_45_second_timer_ends_a_stalling_round(model):
    with game(model) as gb:
        to_play(gb)
        frames(gb, 2)
        assert gb.mem16("mg_timer") >= TIME_S * 60 - 4 and TIME_S == 45
        gb.write("mg_timer", 3)
        gb.write(gb.addr("mg_timer") + 1, 0)
        until(gb, lambda: gb.mem("mg_phase") == MG_END, 10)
        assert text(gb, 2) == "TIME UP"
        frames(gb, 2)
        s = snap(gb)
        assert s["st"] == OUTRO and s["shots"] == 0 and gb.mem16("mg_score") == 0
        until(gb, lambda: gb.mem("mg_phase") == MG_RESULT, 80)
        assert gb.mem("mg_medal") == MEDAL_NONE


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_time_up_with_a_shirt_in_the_air_scores_nothing_for_it(model):
    with game(model) as gb:
        to_aim(gb)
        reset_aim(gb, 3, 0, wave=1)
        fire(gb)
        frames(gb, 3)
        gb.write("mg_timer", 1)
        gb.write(gb.addr("mg_timer") + 1, 0)
        until(gb, lambda: gb.mem("mg_phase") == MG_END, 10)
        frames(gb, 30)
        assert gb.mem16("mg_score") == 0 and oam(gb, OAM_SHIRT)["y"] == 0


# ---- medals -------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("points", [0, 999, 1000, 1900, 2000, 2900, 3000, 3600])
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_medals_by_score(model, points):
    """BRONZE 1000, SILVER 2000, GOLD 3000 (the framework's table on mg_score), the result's name, score and medal word."""
    with game(model) as gb:
        to_play(gb)
        to_result(gb, points)
        m = sum(points >= t for t in (1000, 2000, 3000))
        assert gb.mem("mg_medal") == m
        assert text(gb, 1, True, x0=4) == "SHIRT CANNON" and text(gb, 2, True, x0=4) == f"SCORE {points}"
        assert text(gb, 3, True, x0=4).startswith(("NO MEDAL", "BRONZE", "SILVER", "GOLD")[m])


# ---- a bot that plays whole games ----------------------------------------------------------------------------------------------
def landing_wave(s, a, f):
    """The wave's centre when a shot of angle index a, fired by the update f updates after the state s, lands."""
    col, T = fly(a, s["wind"])
    if col is None:
        return None, T
    w, _, _ = wave_after(s, f + T)
    return (col, w), T


def robust_300(s, a, f):
    col, T = fly(a, s["wind"])
    if col is None:
        return False
    return all(points(col, wave_after(s, f + T + d)[0]) == 300 for d in (-1, 0, 1))


def play_bot(gb, worst=None, limit=4000, mash=False):
    """The bot plays a whole round: in an aim it picks the angle whose shot (its landing column, the model's flight time) arrives in the
    wave soonest (counting 2 frames a step), steps to it with taps, and fires when that landing is in the wave for the frames around it."""
    target = None
    for _ in range(limit):
        s = snap(gb)
        if gb.mem("mg_phase") != 2:
            break
        if s["st"] != AIM:
            frames(gb, 1, worst)
            continue
        if mash:
            tap(gb, "a")
            continue
        best = None
        for a in range(11):
            steps = abs(a - s["angle"])
            for f in range(2 * steps + 1, 2 * steps + 400):
                if robust_300(s, a, f):
                    if best is None or f < best[0]:
                        best = (f, a)
                    break
        if best is None:
            frames(gb, 1, worst)
            continue
        f, a = best
        if target is not None and target != a and target in range(11):
            tf = next((ff for ff in range(2 * abs(target - s["angle"]) + 1, 2 * abs(target - s["angle"]) + 400)
                       if robust_300(s, target, ff)), None)
            if tf is not None and tf <= f + 12:
                a, f = target, tf
        target = a
        if s["angle"] < a:
            gb.hold("up")
            frames(gb, 1, worst)
            gb.release("up")
            frames(gb, 1, worst)
        elif s["angle"] > a:
            gb.hold("down")
            frames(gb, 1, worst)
            gb.release("down")
            frames(gb, 1, worst)
        elif robust_300(s, a, 1):
            gb.hold("a")
            frames(gb, 1, worst)
            gb.release("a")
            frames(gb, 1, worst)
        else:
            frames(gb, 1, worst)
    return snap(gb)


@pytest.mark.parametrize("seed", [SEED, 0x1234])
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_bot_that_reads_the_wind_and_the_wave_wins_gold(model, seed):
    """12 shots in under 45 s: the bot lands most in the wave (300 each): GOLD (>= 3000), every frame at most 10 sprites a line."""
    with game(model, seed=seed) as gb:
        worst = [0]
        to_play(gb)
        s = play_bot(gb, worst)
        assert s["shots"] == SHOTS, s["shots"]
        sc = gb.mem16("mg_score")
        assert sc >= 3000, sc
        until(gb, lambda: gb.mem("mg_phase") == MG_RESULT, 200)
        assert gb.mem("mg_medal") == MEDAL_GOLD
        assert worst[0] <= 9, worst


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_firing_blind_is_not_a_medal(model):
    """Mashing A at the starting angle for all 12 shots: far from gold."""
    with game(model) as gb:
        to_play(gb)
        play_bot(gb, mash=True)
        until(gb, lambda: gb.mem("mg_phase") == MG_RESULT, 300)
        assert gb.mem16("mg_score") < 3000 and gb.mem("mg_medal") < MEDAL_GOLD


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_at_most_10_sprites_a_line_in_the_worst_frames(model):
    """The aim shows the Spigoteer 2 + cannon 2 + 3 dots (+ the puff); a flight the Spigoteer, the cannon, the puff and the shirt: forced
    worst frames (every state's sprites on the cannon's lines) never pass 9."""
    with game(model) as gb:
        to_aim(gb)
        worst = [0]
        for st in (AIM, FLY):
            for a in range(11):
                reset_aim(gb, a, 0)
                poke(gb, st=st, puff=PUFF_LEN, x=(46 << 8), y=(110 << 8), vx=0, vy=0, t=3)
                frames(gb, 2, worst)
        assert worst[0] <= 9, worst


# ---- flow: practice, story, arcade, the list, what is put back ---------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_practice_retry_and_menu(model):
    """Practice: A on the result retries (the score from 0, the state fresh), B comes back to the list."""
    with game(model) as gb:
        to_aim(gb)
        reset_aim(gb, 3, 0, wave=1)
        fire(gb)
        land(gb)
        assert gb.mem16("mg_score") == PTS_WAVE
        to_result(gb)
        assert text(gb, 4, True, x0=4) == "A RETRY B MENU"
        gb.press("a", 2)
        run_until(gb, lambda: gb.mem("mg_phase") == 0 and gb.pb.memory[0xFF40] & 0x80, 30)
        s = ts(gb)
        assert state(gb) == GS_MINI and score(gb) == 0 and (s["shots"], s["num"], s["angle"], s["wave"]) == (0, 1, 7, 1)
        assert text(gb, 2) == "SHIRT CANNON"
        to_play(gb)
        to_result(gb)
        gb.press("b", 2)
        run_until(gb, lambda: state(gb) == GS_MGLIST and gb.pb.memory[0xFF40] & 0x80, 30)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_story_plays_it_in_chapter_2_and_the_last_call_has_everything_back(model):
    """Chapter 2 (the stadium): after the Happy hour, T-Shirt Cannon in MG_STORY (the score carried, the count not skippable, unlocked for
    Practice at once); the result's A CONTINUE leads to the Last call, whose VRAM and palettes are those of the Last call reached without it."""
    from test_bs import level_vram, palettes
    from test_story import to_goal, to_shift, win
    with to_shift(model, STADIUM, 2) as gb:
        gb.run(2)
        fresh, pals = level_vram(gb), palettes(gb)
    with to_shift(model, STADIUM, 1) as gb:
        assert gb.mem16("mg_unlocked") == 0
        win(gb, STADIUM, 1)
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 20)
        run_until(gb, lambda: state(gb) == GS_MINI, 300)
        run_until(gb, lambda: gb.pb.memory[0xFF40] & 0x80, 10)
        assert gb.mem("mg_id") == MG_TSHIRT and gb.mem("mg_mode") == MG_STORY and gb.mem("venue_id") == STADIUM
        assert text(gb, 2) == "SHIRT CANNON" and score(gb) > 0
        assert gb.mem16("mg_unlocked") == 1 << MG_TSHIRT
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
        assert gb.mem("story_chapter") == STADIUM and gb.mem("story_shift") == 2 and gb.mem("story_step") == 3
        to_goal(gb)
        gb.run(2)
        assert level_vram(gb) == fresh
        assert palettes(gb) == pals


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_level_after_t_shirt_cannon_has_everything_back(model):
    """A game (a catch, a miss) -> B to the list -> the title -> a level: the level's OBJ tiles, BG 77-255, OBP0 / OBP1 and every palette
    are byte for byte those of a level started from a fresh boot."""
    from conftest import title_level
    from test_bs import level_vram, palettes
    from test_flow import PLAYING
    from test_scores import booted
    with booted(model) as gb:
        hold_stage_anim(gb)
        title_level(gb)
        run_until(gb, lambda: state(gb) == PLAYING, 60)
        gb.run(2)
        fresh, pals = level_vram(gb), palettes(gb)
    with game(model) as gb:
        to_aim(gb)
        reset_aim(gb, 3, 0, wave=1)
        fire(gb)
        land(gb)
        reset_aim(gb, 0, 0)
        fire(gb)
        land(gb)
        to_result(gb)
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
        assert level_vram(gb) == fresh
        assert palettes(gb) == pals


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_arcade_plays_it_in_chapter_2(model):
    """ARCADE plays the story's steps: the stadium's mini slot is T-Shirt Cannon, in MG_STORY; reaching it unlocks it."""
    from test_arcade import start_arcade
    from test_story import to_goal, win
    with start_arcade(model) as gb:
        to_goal(gb)
        gb.write("story_chapter", STADIUM)
        gb.write("story_step", 1)
        win(gb, 0, 0)
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 20)
        run_until(gb, lambda: state(gb) == GS_MINI, 400)
        run_until(gb, lambda: gb.pb.memory[0xFF40] & 0x80, 10)
        assert gb.mem("mg_id") == MG_TSHIRT and gb.mem("mg_mode") == MG_STORY and gb.mem("venue_id") == STADIUM
        assert gb.mem("save_lock") == 1 and gb.mem16("mg_unlocked") == 1 << MG_TSHIRT
        assert text(gb, 2) == "SHIRT CANNON"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_bonus_mini_games_lists_and_plays_it(model):
    """BONUS > MINI GAMES (the debug build: all unlocked): SHIRT CANNON on the eighth line (after TAIKO POUR), its details THE STADIUM; A plays it in
    practice (score from 0); its result's B comes back to the list on it."""
    from test_mg_list import line, tap as list_tap, to_list
    from test_scores import booted
    with to_list(booted(model)) as gb:
        assert line(gb, 9).strip() == "SHIRT CANNON"
        for _ in range(7):
            list_tap(gb, "down")
        assert gb.mem("ml_sel") == 7
        assert [line(gb, r).strip() for r in range(13, 17)] == ["SHIRT CANNON", "THE STADIUM", "NO MEDAL YET", "A PLAY  B BACK"]
        list_tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_MINI and gb.pb.memory[0xFF40] & 0x80, 30)
        assert gb.mem("mg_id") == MG_TSHIRT and gb.mem("mg_mode") == MG_PRACTICE and score(gb) == 0
        assert text(gb, 2) == "SHIRT CANNON"
        gb.write("mg_phase", MG_RESULT)
        run_until(gb, lambda: gb.mem("overlay_on") == 1, 10)
        frames(gb, 3)
        gb.press("b", 2)
        run_until(gb, lambda: state(gb) == GS_MGLIST and gb.pb.memory[0xFF40] & 0x80, 30)
        gb.run(3)
        assert gb.mem("ml_sel") == 7 and line(gb, 9).strip() == "SHIRT CANNON"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_release_list_unlocks_it_when_reached(model, release_built):
    from test_mg_list import MG_PLANNED, line, pr_block, release_rom, tap as list_tap, to_list, with_block
    from test_scores import v7_image
    best = [0] * MG_PLANNED
    best[MG_TSHIRT] = MEDAL_SILVER
    ram = with_block(v7_image(), pr_block(1 << MG_TSHIRT, best))
    with release_rom(model, ram) as gb:
        to_list(gb)
        assert line(gb, 9) == " SHIRT CANNON SILVER" or line(gb, 9).startswith(" SHIRT CANNON")
        assert [line(gb, r).strip() for r in (2, 3, 4, 5, 6, 7, 8)] == ["? ? ?"] * 7
        for _ in range(7):
            list_tap(gb, "down")
        assert [line(gb, r).strip() for r in range(13, 16)] == ["SHIRT CANNON", "THE STADIUM", "BEST SILVER"]
        list_tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_MINI, 30)
        assert gb.mem("mg_id") == MG_TSHIRT and gb.mem("mg_mode") == MG_PRACTICE


def test_the_state_fits_the_union_and_the_tile_budget():
    assert STATE_SIZE <= 520 and LAYOUT["cheer"][1] == FAN_N
    free = 256 - TS_BG                                # the framework's free BG ids: MG_GAME_BG..255
    assert ART["n_bg"] <= free - 16, (ART["n_bg"], free)   # (240-255 stay clear, as the other games)
    assert TS_OBJ + ART["obj_tiles"] <= 92, "the coin sits at OBJ 92-95"
    # the muzzles are the barrel tips of the art: inside the cannon's 16x16 box, the tips one pixel past the barrel
    for (mx, my), l in zip(ART["muzzle"], range(4)):
        assert 32 <= mx < 48 and 104 <= my < 120


# ---- goldens ---------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_goldens(model):
    """The intro banner, an aim with the dots, a shirt in the air in a headwind, a catch in the wave (the cheer), the result: from a seeded
    game, each shot taken a fixed number of frames after a press."""
    with game(model) as gb:
        frames(gb, 40)
        shot(gb, "intro")
        check_golden(gb, "ts_intro")
        to_play(gb)
        frames(gb, 4)
        reset_aim(gb, 4, 0, wave=3)
        frames(gb, 3)
        shot(gb, "aim")
        check_golden(gb, "ts_aim")
        for _ in range(30):                             # the game's own wind (the windsock and the HUD show it): a headwind
            poke(gb, st=RELOAD, reload=1, num=8, wave=7, wt=250, shots=2)
            frames(gb, 2)
            if snap(gb)["wind"] < 0:
                break
        assert snap(gb)["wind"] < 0
        poke(gb, angle=9, wave=7, wt=250)
        fire(gb)
        frames(gb, 24)
        s = snap(gb)
        assert s["st"] == FLY
        shot(gb, "flight")
        check_golden(gb, "ts_flight")
        # a catch in the wave: 25 degrees lands on the first fan
        land(gb)
        reset_aim(gb, 3, 0, wave=1)
        fire(gb)
        s = land(gb)
        assert s["lastpts"] == 3
        frames(gb, 6)
        shot(gb, "cheer")
        check_golden(gb, "ts_cheer")
        to_result(gb, 2300)
        shot(gb, "result")
        check_golden(gb, "ts_result")
