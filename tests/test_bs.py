# docs/minigames_bosses.md 4.6: BATTERY SORT (src/bs.c), the robot factory's mini-game, on the framework (src/mg.c):
# the screen (the approved art), the rules (each type to its bin, the diverter's window shrinking and the belt speeding
# up, a wrong bin and a timeout as strikes, the SCRAP chute open from the first battery (one of each kind first, no banner, no pause),
# a strike never eating the next battery's time, three strikes, time up), the points and medals, the seeded batteries, STORY / ARCADE reaching it in the
# factory, BONUS > MINI GAMES, and everything put back for the level after. Sprites per line <= 10 on every frame.
import json
import re

import pytest
from conftest import ROOT, check_golden, hold_stage_anim, logic_paused, title_level
from test_flow import GS_GOAL, LEVEL_CLEAR, PLAYING, TITLE, run_until, state, tilemap_row
from test_mg_list import release_built  # noqa: F401  (the fixture: `make release`)
from test_mg import (BLANK, HOURGLASS, GS_MGLIST, GS_MINI, MEDAL_PTS, MG_COUNT, MG_END, MG_PLAY, MG_PRACTICE, MG_RESULT, MG_STORY,
                     RESULT_MIN, define, frames, lines, mg_enter, score, text, to_play, to_result, until)

pytestmark = pytest.mark.timeout(300)

BS_C = (ROOT / "src" / "bs.c").read_text()
BS_H = (ROOT / "build" / "bs_art.h").read_text()
ART = json.loads((ROOT / "build" / "bs.json").read_text())
ART_H = (ROOT / "build" / "art.h").read_text()
MG_BATTERY = 5
FACTORY = 5
MEDAL_NONE, MEDAL_BRONZE, MEDAL_SILVER, MEDAL_GOLD = range(4)
SFX_LAUNCH, SFX_CATCH, SFX_BREAK, SFX_LIFE = 2, 3, 4, 7
BH = {m[0]: int(m[1]) for m in re.findall(r"#define (BS\w+) (\d+)", BS_H)}
(TIME_S, WIN0, WIN_STEP, WIN_EVERY, WIN_MIN, SPEED0, SPEED_EVERY, SPEED_MAX, GAP_IN, GAP, START_N, ONE_EACH, BROKEN_P,
 PTS, STREAK_PTS, STREAK_MAX, STRIKES, FLY_DROP, FLY_ARC, FLY_LEN, SCREEN_LEN, SPARK_LEN, CROSS_LEN, SPIT_ARC,
 BAND_OFF, POSE_FAIL) = (define(n, BS_C) for n in (
    "BS_TIME_S", "BS_WIN0", "BS_WIN_STEP", "BS_WIN_EVERY", "BS_WIN_MIN", "BS_SPEED0", "BS_SPEED_EVERY", "BS_SPEED_MAX",
    "BS_GAP_IN", "BS_GAP", "BS_START_N", "BS_ONE_EACH", "BS_BROKEN_P", "BS_PTS", "BS_STREAK_PTS", "BS_STREAK_MAX",
    "BS_STRIKES", "BS_FLY_DROP", "BS_FLY_ARC", "BS_FLY_LEN", "BS_SCREEN_LEN", "BS_SPARK_LEN",
    "BS_CROSS_LEN", "BS_SPIT_ARC", "BS_BAND_OFF", "BS_POSE_FAIL"))
(BELT_ROW, BELT_N, DIV_COL, DIV_ROW, BIN_ROW, CHARGE_COL, CHUTE_COL, RECYCLE_COL, STRIKE_COL, FRONT_X, BAT_Y, SPIG_X,
 SPIG_Y, CROSS_Y, CROSS_DIV_X, CROSS_DIV_Y, SPARK_Y, LIE_Y, DIV_PAL, CHARGE_PAL, RECYCLE_PAL, PAL_BROKEN, PAL_SPARK,
 PAL_CROSS, OAM_SPIG, OAM_CROSS, OAM_SPARKS, OAM_SPIT, OAM_FLY, OAM_BELT_SPARK, OAM_QUEUE, OAM_N) = (
    define(n, BS_C) for n in (
        "BELT_ROW", "BELT_N", "DIV_COL", "DIV_ROW", "BIN_ROW", "CHARGE_COL", "CHUTE_COL", "RECYCLE_COL", "STRIKE_COL",
        "FRONT_X", "BAT_Y", "SPIG_X", "SPIG_Y", "CROSS_Y", "CROSS_DIV_X", "CROSS_DIV_Y", "SPARK_Y", "LIE_Y", "DIV_PAL",
        "CHARGE_PAL", "RECYCLE_PAL", "PAL_BROKEN", "PAL_SPARK", "PAL_CROSS", "OAM_SPIG", "OAM_CROSS", "OAM_SPARKS",
        "OAM_SPIT", "OAM_FLY", "OAM_BELT_SPARK", "OAM_QUEUE", "OAM_N"))
BS_RUN, BS_SCRAP, BS_OVER = range(3)
BT_CHARGED, BT_DEAD, BT_BROKEN = range(3)
DIR_NONE, DIR_LEFT, DIR_RIGHT, DIR_DOWN, DIR_DROP = range(5)
BR_NONE, BR_RIGHT, BR_WRONG, BR_LATE = range(4)
BT_IDLE, BT_FILL, BT_SLIDE, BT_CATCH, BT_FAIL = 0, 3, 4, 5, 6      # game.h's bartender frames
KEY = {DIR_LEFT: "left", DIR_RIGHT: "right", DIR_DOWN: "down"}
BS_BG = 77 + 48                                 # MG_GAME_BG
BS_OBJ = 60                                     # OBJ_GLASS
OBJ_MUG, OBJ_MUG_DRINK = 56, 84
BIN_X = {DIR_LEFT: 16, DIR_RIGHT: 128, DIR_DOWN: 72}
SPIT_X1 = {DIR_LEFT: 48, DIR_RIGHT: 104, DIR_DOWN: 96}
SEED = 0x5A17
OUT = ROOT / "out" / "bs"


def bs(gb):
    b = gb.read("story_scratch", 64)
    n = b[1]
    return dict(st=b[0], n=n, wait=b[2], window=b[3], speed=b[4], strikes=b[5], sorted=b[6], streak=b[7], made=b[8],
                chute=b[9], banner=b[10], last=b[11], screen_t=b[12], pose=b[13], pose_t=b[14], flip=b[15],
                queue=list(b[18:18 + n]),
                qx=[int.from_bytes(bytes(b[26 + 2 * i:28 + 2 * i]), "little", signed=True) for i in range(n)],
                belt=b[42], belt_f=b[43], fly=[dict(type=b[44 + 3 * k], dir=b[45 + 3 * k], t=b[46 + 3 * k]) for k in range(3)],
                spark_t=b[53], spark_x=b[54], cross_t=b[55], cross_x=b[56], cross_y=b[57], spit_t=b[58], spit_type=b[59],
                spit_dir=b[60])


def poke(gb, **kw):
    """Fields of the game's state, between two whole game frames."""
    off = dict(st=0, wait=2, window=3, speed=4, strikes=5, sorted=6, streak=7, made=8, chute=9)
    a = gb.addr("story_scratch")
    with logic_paused(gb):
        for k, v in kw.items():
            if k == "front":
                gb.write(a + 18, v)
            else:
                gb.write(a + off[k], v)


def battery_sort(model, mode=MG_PRACTICE, seed=SEED):
    """A booted rom on the title, then Battery Sort in practice (or `mode`)."""
    from test_scores import booted
    rom = booted(model)
    hold_stage_anim(rom)
    mg_enter(rom, MG_BATTERY, mode, seed)
    return rom


def shot(gb, name):
    OUT.mkdir(parents=True, exist_ok=True)
    gb.screenshot(OUT / f"{name}.{gb.model_name}.png", 4)


def oam(gb, i):
    a = 0xFE00 + 4 * i
    return dict(y=gb.mem(a), x=gb.mem(a + 1), tile=gb.mem(a + 2), prop=gb.mem(a + 3))


def tap(gb, b):
    gb.hold(b)
    frames(gb, 1)
    gb.release(b)
    frames(gb, 1)


def to_waiting(gb, limit=300):
    """Play until the front battery waits on the flap (the belt running)."""
    until(gb, lambda: gb.mem("mg_phase") == MG_PLAY and bs(gb)["st"] == BS_RUN and bs(gb)["wait"] > 0, limit)


def flying(gb):
    return [f for f in bs(gb)["fly"] if f["dir"]]


def sort(gb, d):
    """The front battery sent `d` (DIR_*): returns its type."""
    to_waiting(gb)
    t = bs(gb)["queue"][0]
    tap(gb, KEY[d])
    return t


def landed(gb):
    """Until nothing is in the air, and one frame more (a read right at PyBoy's frame end can catch the game's update
    half done: conftest.logic_paused)."""
    until(gb, lambda: not flying(gb), FLY_LEN + 4)
    frames(gb, 1)


def right_dir(t):
    return {BT_CHARGED: DIR_LEFT, BT_DEAD: DIR_RIGHT, BT_BROKEN: DIR_DOWN}[t]


def sort_right(gb):
    to_waiting(gb)
    return sort(gb, right_dir(bs(gb)["queue"][0]))


def window_of(n):
    return max(WIN_MIN, WIN0 - WIN_STEP * (n // WIN_EVERY))


def speed_of(n):
    return min(SPEED_MAX, SPEED0 + n // SPEED_EVERY)


def streak_pts(k):
    return PTS + min(STREAK_PTS * k, STREAK_MAX)


def bin_tiles(sign):
    """The bin's 5 rows of 4 tiles as the game draws them."""
    rows = []
    for r in range(5):
        row = []
        for c in range(4):
            m = ART["bin_map"][r * 4 + c]
            if m == 255:
                row.append(BS_BG + BH["BSB_SIGN"] + sign * 4 + (r - 1) * 2 + (c - 1))
            else:
                row.append(BS_BG + BH["BSB_BIN"] + m)
        rows.append(row)
    return rows


def bin_on_screen(gb, col):
    return [tilemap_row(gb, BIN_ROW + r, col, 4) for r in range(5)]


def attr(gb, r, c):
    return gb.pb.memory[1, 0x9800 + r * 32 + c] & 7


def lamps(gb):
    return [t - BS_BG - BH["BSB_STRIKE"] for t in tilemap_row(gb, 0, STRIKE_COL, 3)]


def screen_state(gb):
    return (tilemap_row(gb, DIV_ROW + 1, DIV_COL, 1)[0] - BS_BG - BH["BSB_SCREEN"]) // 2


# ---- the seeded batteries: src/bs.c new_type on mg.c's xorshift --------------------------------------------------------
class Rng:
    def __init__(self, seed):
        self.s = seed

    def __call__(self):
        s = self.s
        s ^= (s << 7) & 0xFFFF
        s ^= s >> 9
        s ^= (s << 8) & 0xFFFF
        self.s = s
        return s & 0xFF


def batteries(seed, n):
    """The types of batteries 1..n as the game makes them."""
    r, out = Rng(seed), []
    for made in range(1, n + 1):
        if made <= ONE_EACH:
            out.append(made - 1)
        elif r() < BROKEN_P:
            out.append(BT_BROKEN)
        else:
            out.append(r() & 1)
    return out


# ---- the screen ----------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_screen(model):
    """The intro: the banner, the hourglass and 45, the strike lamps beside the lives (column 8 keeps the lives number); the belt, the diverter, the three bins (the
    chute open, no lid), the counter row turned to wall; the art in VRAM; three batteries on the belt and the
    Spigoteer beside the machine; CGB attributes and palettes (RECYCLE in palette 5: 4 is the result's medal);
    DMG OBP1 0xE4 (the title leaves 0xC4)."""
    with battery_sort(model) as gb:
        frames(gb, 30)
        assert gb.mem("mg_id") == MG_BATTERY and gb.mem("venue_id") == FACTORY and gb.mem("mg_phase") == 0
        assert text(gb, 2) == "BATTERY SORT" and text(gb, 3) == "L FULL R DEAD D BAD"
        assert gb.mem16("mg_timer") == TIME_S * 60
        glyph = {int(m[1]): m[0] for m in re.findall(r"#define TILE_GLYPH_(\w) (\d+)", ART_H)}
        assert tilemap_row(gb, 0, 16, 2) == [BLANK, HOURGLASS] and "".join(glyph[t] for t in tilemap_row(gb, 0, 18, 2)) == "45"   # blank, hourglass, 4 5
        assert tilemap_row(gb, 0, 8, 1) == [36 + 3] and lamps(gb) == [0, 0, 0]
        assert tilemap_row(gb, BELT_ROW, 0, BELT_N) == [BS_BG + BH["BSB_BELT"]] * BELT_N
        assert tilemap_row(gb, DIV_ROW, DIV_COL, 2) == [BS_BG + BH["BSB_FLAP"] + k for k in range(2)]
        assert tilemap_row(gb, DIV_ROW + 1, DIV_COL, 2) == [BS_BG + BH["BSB_SCREEN"] + k for k in range(2)], "idle"
        assert tilemap_row(gb, DIV_ROW + 2, DIV_COL, 2) == [BS_BG + BH["BSB_BASE"] + k for k in range(2)]
        assert bin_on_screen(gb, CHARGE_COL) == bin_tiles(0)
        assert bin_on_screen(gb, CHUTE_COL) == bin_tiles(2), "the chute is open from the start"
        assert bin_on_screen(gb, RECYCLE_COL) == bin_tiles(1)
        assert tilemap_row(gb, 11, 0, 20) == tilemap_row(gb, 5, 0, 20), "the counter row is wall (an odd wall row)"
        bg = b"".join(bytes(gb.read((0x9000 if t < 128 else 0x8000) + t * 16, 16))
                      for t in range(BS_BG, BS_BG + BH["BS_BG_TILES"]))
        assert bg == bytes(ART["bg"]) and BS_BG + BH["BS_BG_TILES"] == 169
        assert bytes(gb.read(0x8000 + BS_OBJ * 16, BH["BS_OBJ_TILES"] * 16)) == bytes(ART["obj"])
        s = bs(gb)
        assert s["n"] == START_N and s["qx"] == [(FRONT_X - GAP * k) * 8 for k in range(START_N)]
        assert s["queue"] == batteries(SEED, START_N) and s["made"] == START_N and s["wait"] == 0
        for k in range(START_N):
            o = oam(gb, OAM_QUEUE + k)
            assert (o["x"], o["y"]) == (FRONT_X - GAP * k + 8, BAT_Y + 16)
        assert all(oam(gb, i)["y"] == 0 for i in range(OAM_CROSS, OAM_QUEUE) if i != OAM_BELT_SPARK), "(the broken one sparks on the belt)"
        assert all(oam(gb, i)["y"] == 0 for i in range(OAM_QUEUE + START_N, 40))
        sp = oam(gb, OAM_SPIG)
        assert (sp["x"], sp["y"], sp["tile"]) == (SPIG_X + 8, SPIG_Y + 16, BT_IDLE * 8)
        if model == "cgb":
            from test_lift import cgb_bg_palette, cgb_obj_palette
            assert all(attr(gb, DIV_ROW + r, DIV_COL + c) == DIV_PAL for r in range(3) for c in range(2))
            for col, pal in ((CHARGE_COL, CHARGE_PAL), (CHUTE_COL, DIV_PAL), (RECYCLE_COL, RECYCLE_PAL)):
                assert all(attr(gb, BIN_ROW + r, col + c) == pal for r in range(5) for c in range(4))
            assert attr(gb, 2, 0) == 1 and attr(gb, 3, 19) == 1, "the banner in the HUD's colours"
            assert RECYCLE_PAL != 4, "palette 4 is the result window's medal"
            assert len({tuple(cgb_bg_palette(gb, p)) for p in (DIV_PAL, CHARGE_PAL, RECYCLE_PAL)}) == 3
            assert cgb_bg_palette(gb, CHARGE_PAL)[0] == cgb_bg_palette(gb, 0)[0], "the bins' outline on the wall"
            assert len({tuple(cgb_obj_palette(gb, p)[1:]) for p in (PAL_BROKEN, PAL_SPARK, PAL_CROSS)}) == 3
            assert [oam(gb, OAM_QUEUE + k)["prop"] & 7 for k in range(START_N)] == [
                {BT_CHARGED: 1, BT_DEAD: 2, BT_BROKEN: PAL_BROKEN}[t] for t in s["queue"]], "the factory drink's palettes, the broken one's"
        else:
            assert gb.mem(0xFF49) == 0xE4 and all(oam(gb, OAM_QUEUE + k)["prop"] & 0x10 == (0x10 if s["queue"][k] == BT_BROKEN else 0) for k in range(START_N))
        shot(gb, "intro")
        check_golden(gb, "bs_intro")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_in_play_the_belt_runs_and_the_banner_rows_are_wall(model):
    """GO: the banner rows go back to the wall (a row a frame, tiles and colours); the belt steps its tile with its
    sub-pixel position; each battery moves `speed` 1/8 px a frame up to its place 16 px behind the one ahead, new ones
    come in 24 px apart from off the screen (parked at y 0 until x > -8); the front one gets D frames on the flap."""
    with battery_sort(model) as gb:
        wall = [tilemap_row(gb, 4, 0, 20), tilemap_row(gb, 5, 0, 20)]
        to_play(gb)
        frames(gb, 3)
        assert [tilemap_row(gb, 2, 0, 20), tilemap_row(gb, 3, 0, 20)] == wall
        if model == "cgb":
            assert all(attr(gb, r, c) == 0 for r in (2, 3) for c in range(20))
        s = bs(gb)
        assert s["wait"] > 0 and s["window"] == WIN0 and s["speed"] == SPEED0
        assert s["n"] == START_N + 1 and (s["qx"][-1] + 64) % SPEED0 == 0, "the 4th came in at once, from x -8"
        before = bs(gb)
        frames(gb, 1)
        after = bs(gb)
        assert after["qx"][3] - before["qx"][3] == SPEED0 and after["qx"][:3] == before["qx"][:3]
        assert after["belt_f"] == (after["belt"] >> 3) & 3
        assert tilemap_row(gb, BELT_ROW, 0, BELT_N) == [BS_BG + BH["BSB_BELT"] + bs(gb)["belt_f"]] * BELT_N
        seen, last = set(), bs(gb)
        for _ in range(60):
            frames(gb, 1)
            s = bs(gb)
            seen.add(s["belt_f"])
            if s["n"] > last["n"]:                      # a new one: at x -8, the one ahead >= 16 px in (24 px apart)
                assert s["qx"][-1] == -64 and s["qx"][-2] >= (GAP_IN - 8) * 8
            last = s
            for k in range(1, s["n"]):
                assert s["qx"][k - 1] - s["qx"][k] >= GAP * 8
            for k in range(s["n"]):
                o = oam(gb, OAM_QUEUE + k)
                assert (o["y"] == 0) == (s["qx"][k] <= -64)
        assert seen == {0, 1, 2, 3}
        assert bs(gb)["n"] >= 5
        shot(gb, "play")
        check_golden(gb, "bs_play")


# ---- sorting ----------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("kind", [BT_CHARGED, BT_DEAD, BT_BROKEN], ids=["charged", "dead", "broken"])
def test_each_type_goes_to_its_bin(model, kind):
    """Left sends a charged battery to CHARGE, Right a dead one to RECYCLE, Down a broken one into the SCRAP chute: it
    drops into the diverter (behind its tiles), the screen shows the arrow, the Spigoteer points; it comes out of the
    port and arcs into the bin, or falls through the mouth; on landing 100 + 10 x streak points, the sparks over the
    bin, the Spigoteer's catch pose."""
    d = right_dir(kind)
    with battery_sort(model) as gb:
        to_play(gb)
        to_waiting(gb)
        poke(gb, front=kind)
        to_waiting(gb)
        before = gb.mem16("mg_score")
        s0 = bs(gb)
        assert sort(gb, d) == kind
        s = bs(gb)
        f = [f for f in s["fly"] if f["dir"]]
        assert len(f) == 1 and f[0]["dir"] == d and f[0]["type"] == kind and s["n"] == s0["n"] - 1 and s["wait"] == 0
        assert screen_state(gb) == d and s["pose"] == (BT_SLIDE if d == DIR_DOWN else BT_FILL)
        assert s["flip"] == (d == DIR_RIGHT) and gb.mem("last_sfx") == SFX_LAUNCH
        k = next(k for k, f in enumerate(bs(gb)["fly"]) if f["dir"])
        path = []
        for _ in range(FLY_LEN - 1):                    # (the tap's two frames drew t = 0 and 1)
            o = oam(gb, OAM_FLY + k)
            path.append((o["x"] - 8, o["y"] - 16, bool(o["prop"] & 0x80)))
            frames(gb, 1)
        frames(gb, 1)
        assert not flying(gb) and oam(gb, OAM_FLY + k)["y"] == 0
        assert all(p[0] == FRONT_X and p[2] for p in path[:FLY_DROP - 1]), "into the diverter, behind it"
        if d == DIR_DOWN:
            assert all(p[0] == FRONT_X and p[2] for p in path)
        else:
            xs = [p[0] for p in path[FLY_DROP:]]
            assert xs == sorted(xs, reverse=d == DIR_LEFT) and abs(xs[-1] + 4 - (BIN_X[d] + 8)) <= 4
            assert not path[FLY_DROP][2] and path[-1][2], "in front of the bins, then behind the rim"
        s = bs(gb)
        assert s["sorted"] == 1 and s["streak"] == 1 and s["last"] == BR_RIGHT and s["strikes"] == 0
        assert gb.mem16("mg_score") == before + streak_pts(1)
        assert s["pose"] == BT_CATCH and gb.mem("last_sfx") == SFX_CATCH
        a, b = oam(gb, OAM_SPARKS), oam(gb, OAM_SPARKS + 1)
        assert (a["x"] - 8, a["y"] - 16) == (BIN_X[d] - 2, SPARK_Y) and (b["x"] - 8, b["y"] - 16) == (BIN_X[d] + 10, SPARK_Y + 4)
        assert {a["tile"], b["tile"]} == {BS_OBJ + BH["BSO_SPARK"], BS_OBJ + BH["BSO_SPARK"] + 2}
        if kind == BT_CHARGED:
            frames(gb, 2)
            shot(gb, "correct")
            check_golden(gb, "bs_correct")
        until(gb, lambda: oam(gb, OAM_SPARKS)["y"] == 0, SPARK_LEN + 2)
        until(gb, lambda: screen_state(gb) == DIR_NONE, SCREEN_LEN)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_wrong_bin_is_a_strike(model):
    """A dead battery sent Left: on landing a strike (the first lamp lit, the buzzer), the streak back to 0, no points;
    the WRONG cross blinks over the CHARGE bin, the battery is spat out and lies on the floor (the drink's lying empty
    frame); the Spigoteer's fail pose."""
    with battery_sort(model) as gb:
        to_play(gb)
        to_waiting(gb)
        poke(gb, front=BT_DEAD, streak=5)
        to_waiting(gb)
        before = gb.mem16("mg_score")
        sort(gb, DIR_LEFT)
        landed(gb)
        s = bs(gb)
        assert s["strikes"] == 1 and s["streak"] == 0 and s["sorted"] == 0 and s["last"] == BR_WRONG
        assert gb.mem16("mg_score") == before and gb.mem("last_sfx") == SFX_BREAK and s["pose"] == BT_FAIL
        frames(gb, 1)
        assert lamps(gb) == [1, 0, 0]
        crosses, spit = [], []
        for _ in range(CROSS_LEN):
            a, b = oam(gb, OAM_CROSS), oam(gb, OAM_CROSS + 1)
            crosses.append(a["y"] != 0)
            if a["y"]:
                assert (a["x"] - 8, a["y"] - 16, b["x"] - 8) == (BIN_X[DIR_LEFT], CROSS_Y, BIN_X[DIR_LEFT] + 8)
                assert a["tile"] == b["tile"] == BS_OBJ + BH["BSO_CROSS"] and b["prop"] & 0x20 and not a["prop"] & 0x20
            o = oam(gb, OAM_SPIT)
            spit.append((o["x"] - 8, o["y"] - 16, o["tile"]))
            if bs(gb)["cross_t"] == 25:
                shot(gb, "wrong")
                check_golden(gb, "bs_wrong")
            frames(gb, 1)
        assert True in crosses and False in crosses, "it blinks"
        assert spit[SPIT_ARC + 2] == (SPIT_X1[DIR_LEFT], LIE_Y, OBJ_MUG_DRINK + 4), "lying: the drink's empty frame"
        assert oam(gb, OAM_CROSS)["y"] == 0 and oam(gb, OAM_SPIT)["y"] == 0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("sorted_n", [0, 40, 254], ids=["D120", "D40", "Dmin_fast"])
def test_a_strike_does_not_eat_the_next_batterys_time(model, sorted_n):
    """Owner 2026-10-15: after the wrong-bin strike the next battery's timer seemed to expire at once. A wrong bin is judged
    when the battery lands (FLY_LEN frames after the sort) while the next battery already waits on the flap. At the strike
    the waiting battery's wait is the full D again, so from the moment the strike shows the player has D frames (D >= 40,
    more than the FAIL pose's 30) to sort it, and sorting it right after the strike counts. The numbers are printed (-s)."""
    with battery_sort(model) as gb:
        to_play(gb)
        poke(gb, sorted=sorted_n, streak=0, window=window_of(sorted_n), speed=speed_of(sorted_n))
        to_waiting(gb)
        win = bs(gb)["window"]
        t = bs(gb)["queue"][0]
        tap(gb, KEY[DIR_RIGHT if t == BT_CHARGED else DIR_LEFT])       # the wrong bin for a charged / dead one
        until(gb, lambda: bs(gb)["strikes"] == 1, FLY_LEN + 2)
        frames(gb, 1)
        s = bs(gb)
        assert s["n"] and s["wait"], "the next battery is waiting on the flap when the strike shows"
        print("BS lockout", model, "sorted", sorted_n, "D", win, "wait at the strike", s["wait"])
        assert s["wait"] >= win - 2, "the next battery has its whole window from the strike on"
        until(gb, lambda: bs(gb)["pose_t"] == 0, POSE_FAIL + 2)      # sort it when the FAIL pose ends: still in time
        s = bs(gb)
        assert s["wait"] > 0 and s["strikes"] == 1, "the pose is over and the battery still has time"
        print("BS lockout", model, "D", win, "wait left when the FAIL pose ends", s["wait"])
        tap(gb, KEY[right_dir(s["queue"][0])])
        landed(gb)
        assert bs(gb)["strikes"] == 1 and bs(gb)["last"] == BR_RIGHT


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_running_out_of_time_on_the_flap_is_a_strike(model):
    """The front battery waits D frames: on the last a strike, the cross over the diverter, the battery drops into it
    and is gone; the next one rolls up and gets its own D."""
    with battery_sort(model) as gb:
        to_play(gb)
        to_waiting(gb)
        poke(gb, streak=3)
        w = bs(gb)["wait"]
        n = bs(gb)["n"]
        t0 = gb.mem16("mg_timer")
        until(gb, lambda: bs(gb)["strikes"] == 1, w + 3)
        assert w - 2 <= t0 - gb.mem16("mg_timer") <= w + 2, "D frames"
        frames(gb, 1)                                # (reads at PyBoy's frame end can catch an update half done)
        s = bs(gb)
        assert s["strikes"] == 1 and s["last"] == BR_LATE and s["streak"] == 0 and s["wait"] == 0
        assert [f["dir"] for f in s["fly"] if f["dir"]] == [DIR_DROP]
        assert (s["cross_x"], s["cross_y"]) == (CROSS_DIV_X, CROSS_DIV_Y)
        a = oam(gb, OAM_CROSS)
        assert (a["x"] - 8, a["y"] - 16) == (CROSS_DIV_X, CROSS_DIV_Y) and lamps(gb) == [1, 0, 0]
        until(gb, lambda: not flying(gb), FLY_DROP + 1)
        to_waiting(gb)
        assert bs(gb)["wait"] == bs(gb)["window"] - 1 or bs(gb)["wait"] == bs(gb)["window"]
        assert bs(gb)["n"] >= n - 1


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_window_shrinks_and_the_belt_speeds_up(model):
    """D = 120 - 8 every 4 right sorts, never under 40; the belt 0.75 px a frame + 0.125 every 6, at most 2.0 (in
    1/8 px); a battery reaching the flap gets the D of that moment."""
    with battery_sort(model) as gb:
        to_play(gb)
        for n in (0, 1, 2, 3, 4, 5, 6, 7, 11, 23, 39, 40, 59, 60, 61, 120, 200, 254):
            poke(gb, sorted=n, streak=0)
            sort_right(gb)
            s = bs(gb)
            assert s["sorted"] == n + 1, "a right sort counts when it is made"
            assert s["window"] == window_of(n + 1) and s["speed"] == speed_of(n + 1), n
            assert s["window"] >= WIN_MIN and s["speed"] <= SPEED_MAX
            until(gb, lambda: bs(gb)["wait"] > 0, 200)
            assert s["window"] - 2 <= bs(gb)["wait"] <= s["window"], "the front's wait is the window of its arrival"
            q = bs(gb)                              # the belt's speed: a battery far from its place, over 6 frames
            k = q["n"] - 1
            if q["qx"][k] + 8 * q["speed"] <= min((FRONT_X - GAP * k) * 8, q["qx"][k - 1] - GAP * 8) and q["n"] < 8:
                frames(gb, 6)
                assert abs(bs(gb)["qx"][k] - q["qx"][k] - 6 * q["speed"]) <= q["speed"], n
            landed(gb)
        assert (window_of(4), window_of(39), window_of(40), window_of(255)) == (112, 48, 40, 40)
        assert (speed_of(5), speed_of(6), speed_of(59), speed_of(60), speed_of(255)) == (6, 7, 15, 16, 16)


# ---- the SCRAP chute (open from the first battery) -------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_scrap_chute_is_in_play_from_the_start(model):
    """Owner 2026-10-15: no mid-game pause. The first three batteries are one of each kind (charged, dead, broken); the
    chute is open from the intro (no lid), Down sends the third into it at once, nothing pauses (no banner: the belt,
    the wait and the timer run all the time) and the banner rows are wall."""
    with battery_sort(model) as gb:
        assert bs(gb)["queue"] == [BT_CHARGED, BT_DEAD, BT_BROKEN] and bs(gb)["chute"] == 1
        to_play(gb)
        frames(gb, 3)
        assert text(gb, 2) == "" and tilemap_row(gb, 2, 0, 20) == tilemap_row(gb, 4, 0, 20)
        assert tilemap_row(gb, 3, 0, 20) == tilemap_row(gb, 5, 0, 20)
        got = []
        for _ in range(3):
            to_waiting(gb)
            timer, wait = gb.mem16("mg_timer"), bs(gb)["wait"]
            frames(gb, 5)
            assert bs(gb)["st"] == BS_RUN and abs(bs(gb)["wait"] - (wait - 5)) <= 1 and abs(gb.mem16("mg_timer") - (timer - 5)) <= 1, "never paused"
            got.append(sort_right(gb))
            landed(gb)
        assert got == [BT_CHARGED, BT_DEAD, BT_BROKEN]
        s = bs(gb)
        assert s["sorted"] == 3 and s["strikes"] == 0 and s["last"] == BR_RIGHT and s["spark_x"] == BIN_X[DIR_DOWN]
        assert gb.mem16("mg_score") == streak_pts(1) + streak_pts(2) + streak_pts(3)
        assert bs(gb)["made"] >= ONE_EACH


@pytest.mark.parametrize("seed", [SEED, 0x1234, 0xBEEF, 0x0001])
def test_the_batteries_follow_the_seed(seed):
    """The types are the seed's (mg_rand): the first three one of each kind, then about 30% broken and the rest charged / dead
    half each (so about a third of each kind). The game makes exactly the model's sequence."""
    seq = batteries(seed, 300)
    assert seq[:ONE_EACH] == [BT_CHARGED, BT_DEAD, BT_BROKEN]
    later = seq[ONE_EACH:]
    assert 0.2 < later.count(BT_BROKEN) / len(later) < 0.4
    assert 0.35 < later.count(BT_CHARGED) / (len(later) - later.count(BT_BROKEN)) < 0.65
    with battery_sort("dmg", seed=seed) as gb:
        to_play(gb)
        got = list(bs(gb)["queue"])
        while len(got) < 24:
            s = bs(gb)
            if s["n"] > 0 and s["made"] > len(got):
                got.append(s["queue"][s["n"] - 1])
            if s["wait"] and not flying(gb):
                tap(gb, KEY[right_dir(s["queue"][0])])
            else:
                frames(gb, 1)
        assert got == seq[:len(got)]


# ---- the end -------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_three_strikes_end_it(model):
    """The third strike: THREE STRIKES on the banner row (in the HUD's colours), the lamps all lit, the play over
    (MG_END: the Spigoteer dazed in his fail pose), the rows wall again before the result."""
    with battery_sort(model) as gb:
        to_play(gb)
        for k in range(STRIKES):
            to_waiting(gb)
            t = bs(gb)["queue"][0]
            sort(gb, DIR_RIGHT if t == BT_CHARGED else DIR_LEFT)
            landed(gb)
            assert bs(gb)["strikes"] == k + 1
        assert gb.mem("mg_phase") == MG_END and bs(gb)["st"] == BS_OVER and gb.mem("last_sfx") == SFX_LIFE
        frames(gb, 2)
        assert text(gb, 2) == "THREE STRIKES" and lamps(gb) == [1, 1, 1]
        if model == "cgb":
            assert all(attr(gb, 2, c) == 1 for c in range(20)) and all(attr(gb, 3, c) == 0 for c in range(20))
        until(gb, lambda: gb.mem("mg_t") >= BAND_OFF + 3, 60)
        assert bs(gb)["pose"] == BT_FAIL and oam(gb, OAM_SPIG)["tile"] == BT_FAIL * 8
        assert tilemap_row(gb, 2, 0, 20) == tilemap_row(gb, 4, 0, 20)
        until(gb, lambda: gb.mem("mg_phase") == MG_RESULT, 60)
        frames(gb, 4)
        assert gb.mem("mg_medal") == MEDAL_NONE


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_time_up(model):
    """45 seconds: TIME UP on row 2 in the HUD's colours, no more sorting; the Spigoteer cheers; the rows go back."""
    with battery_sort(model) as gb:
        to_play(gb)
        sort_right(gb)
        with logic_paused(gb):
            gb.write("mg_timer", 3)
            gb.write(gb.addr("mg_timer") + 1, 0)
        until(gb, lambda: gb.mem("mg_phase") == MG_END, 10)
        frames(gb, 1)
        assert text(gb, 2) == "TIME UP"
        if model == "cgb":
            assert all(attr(gb, 2, c) == 1 for c in range(20))
        landed(gb)
        q = bs(gb)
        tap(gb, "left")
        assert bs(gb)["n"] == q["n"] and bs(gb)["qx"] == q["qx"], "the belt stopped, nothing sorted"
        until(gb, lambda: bs(gb)["pose"] == BT_CATCH and bs(gb)["pose_t"] == 0, 40)
        until(gb, lambda: gb.mem("mg_t") >= BAND_OFF + 3, 60)
        assert tilemap_row(gb, 2, 0, 20) == tilemap_row(gb, 4, 0, 20)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_points_streaks_and_medals(model):
    """100 + 10 x the streak, the bonus capped at 200; medals on mg_score: BRONZE 2000, SILVER 4000, GOLD 6000."""
    with battery_sort(model) as gb:
        to_play(gb)
        for streak in (0, 9, 18, 19, 20, 40, 254):
            poke(gb, streak=streak)
            before = gb.mem16("mg_score")
            sort_right(gb)
            landed(gb)
            assert gb.mem16("mg_score") - before == streak_pts(streak + 1), streak
        assert streak_pts(20) == PTS + STREAK_MAX and streak_pts(30) == PTS + STREAK_MAX
    assert MEDAL_PTS == [0, 500, 1500, 3000]
    for points, medal in ((1999, MEDAL_NONE), (2000, MEDAL_BRONZE), (3999, MEDAL_BRONZE), (4000, MEDAL_SILVER),
                          (5999, MEDAL_SILVER), (6000, MEDAL_GOLD), (6420, MEDAL_GOLD)):
        with battery_sort(model) as gb:
            to_play(gb)
            frames(gb, 10)                              # (the banner rows back to the wall)
            to_result(gb, points)
            assert gb.mem("mg_medal") == medal, points
            assert score(gb) == MEDAL_PTS[medal], "the medal's points (mg_score was poked: the HUD score had none)"
            if points == 6420:
                frames(gb, 2)
                assert text(gb, 1, True, x0=4) == "BATTERY SORT" and text(gb, 4, True, x0=4) == "A RETRY B MENU"
                shot(gb, "result")
                check_golden(gb, "bs_result")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_whole_game_keeps_to_10_sprites_a_line(model):
    """A whole game frame by frame from the intro to the result, the player quick (sorting as soon as he can, the 7th
    one wrong, the 13th left to time out), with the chute in play from the start: never more than 10 sprites on a line (the
    belt's worst is 8)."""
    with battery_sort(model, seed=0x2468) as gb:
        worst, k, late = [0], 0, False
        while gb.mem("mg_phase") != MG_RESULT:
            s = bs(gb)
            if gb.mem("mg_phase") == MG_PLAY and s["st"] == BS_RUN and s["wait"] and len(flying(gb)) < 3:
                if k == 12 and not late:
                    late = s["wait"] == 1           # (let this one time out)
                    frames(gb, 1, worst)
                    continue
                d = right_dir(s["queue"][0])
                if k == 6:
                    d = DIR_RIGHT if d == DIR_LEFT else DIR_LEFT
                k += 1
                gb.hold(KEY[d])
                frames(gb, 1, worst)
                gb.release(KEY[d])
            frames(gb, 1, worst)
        assert bs(gb)["chute"] == 1 and late and bs(gb)["sorted"] >= 30
        assert worst[0] <= 8, worst


# ---- after Battery Sort: everything it borrowed is back -------------------------------------------------------------------------
def level_vram(gb):
    """OBJ / BG 0-255 at 0x8000 and BG 78-127 (77, MG_BG, is no level's tile: the medal icon's first stays there)."""
    return bytes(gb.read(0x8000, 0x1000)) + bytes(gb.read(0x9000 + 78 * 16, (128 - 78) * 16))


def palettes(gb):
    if gb.model_name != "cgb":
        return [gb.mem(0xFF47), gb.mem(0xFF48), gb.mem(0xFF49)]
    from test_lift import cgb_bg_palette, cgb_obj_palette
    return [cgb_bg_palette(gb, p) for p in range(8)] + [cgb_obj_palette(gb, p) for p in range(8)]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_level_after_battery_sort_has_everything_back(model):
    """Battery Sort (a sort, a strike, the chute open) -> B to the list -> the title -> a level: the level's OBJ tiles
    (the crash frames under OBJ 60-67 too), BG 77-255, OBP1 and every palette are byte for byte those of a level
    started from a fresh boot."""
    from test_mg import restored
    from test_scores import booted
    with booted(model) as gb:
        hold_stage_anim(gb)
        title_level(gb)
        run_until(gb, lambda: state(gb) == PLAYING, 60)
        gb.run(2)
        fresh, pals = level_vram(gb), palettes(gb)
    with battery_sort(model) as gb:
        to_play(gb)
        sort_right(gb)
        landed(gb)
        poke(gb, front=BT_BROKEN)
        sort(gb, DIR_DOWN)
        landed(gb)
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
        gb.run(2)
        restored(gb, "saloon")
        assert level_vram(gb) == fresh
        assert palettes(gb) == pals


# ---- STORY, ARCADE and the list -------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_story_plays_it_in_the_factory_and_the_last_call_has_everything_back(model):
    """Chapter 6 (the robot factory): after the Happy hour, Battery Sort in MG_STORY (the score carried, the count not
    skippable, unlocked for Practice at once); its result's A CONTINUE leads to the Last call, whose screen, tiles and
    palettes are those of the Last call reached without it."""
    from test_story import to_shift, to_goal, win
    from test_mg import restored
    with to_shift(model, FACTORY, 2) as gb:
        gb.run(2)
        fresh, pals = level_vram(gb), palettes(gb)
    with to_shift(model, FACTORY, 1) as gb:
        assert gb.mem16("mg_unlocked") == 0
        win(gb, FACTORY, 1)
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 20)
        run_until(gb, lambda: state(gb) == GS_MINI, 300)
        run_until(gb, lambda: gb.pb.memory[0xFF40] & 0x80, 10)
        assert gb.mem("mg_id") == MG_BATTERY and gb.mem("mg_mode") == MG_STORY and gb.mem("venue_id") == FACTORY
        assert text(gb, 2) == "BATTERY SORT" and score(gb) > 0
        assert gb.mem16("mg_unlocked") == 1 << MG_BATTERY
        until(gb, lambda: gb.mem("mg_phase") == MG_COUNT, 100)
        frames(gb, 3)
        gb.press("a", 1)
        assert gb.mem("mg_phase") == MG_COUNT, "no skipping in the story"
        to_play(gb)
        sort_right(gb)
        landed(gb)
        to_result(gb)
        assert text(gb, 4, True, x0=4) == "A CONTINUE"
        until(gb, lambda: gb.mem("mg_t") >= RESULT_MIN, RESULT_MIN)
        gb.press("a", 2)
        run_until(gb, lambda: state(gb) == GS_GOAL, 60)
        gb.run(3)
        assert gb.mem("story_chapter") == FACTORY and gb.mem("story_shift") == 2 and gb.mem("story_step") == 3
        to_goal(gb)
        gb.run(2)
        restored(gb, "factory")
        assert level_vram(gb) == fresh
        assert palettes(gb) == pals


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_arcade_plays_it_in_the_factory(model):
    """ARCADE plays the story's steps: the factory's mini slot is Battery Sort, in MG_STORY, and reaching it unlocks it
    (the owner's rule: STORY or ARCADE)."""
    from test_arcade import start_arcade
    from test_story import to_goal, win
    with start_arcade(model) as gb:
        to_goal(gb)
        gb.write("story_chapter", FACTORY)          # (the factory's Happy hour: its next step is the mini slot)
        gb.write("story_step", 1)
        win(gb, 0, 0)
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 20)
        run_until(gb, lambda: state(gb) == GS_MINI, 400)
        run_until(gb, lambda: gb.pb.memory[0xFF40] & 0x80, 10)
        assert gb.mem("mg_id") == MG_BATTERY and gb.mem("mg_mode") == MG_STORY and gb.mem("venue_id") == FACTORY
        assert gb.mem("save_lock") == 1 and gb.mem16("mg_unlocked") == 1 << MG_BATTERY
        assert text(gb, 2) == "BATTERY SORT"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_bonus_mini_games_lists_and_plays_it(model):
    """BONUS > MINI GAMES (the debug build: all unlocked): BATTERY SORT on the sixth line (the chapters' order), its details THE ROBOT FACTORY; A plays it in practice (score from 0); its result's B
    comes back to the list on it."""
    from test_mg_list import line, tap as list_tap, to_list
    from test_scores import booted
    with to_list(booted(model)) as gb:
        assert line(gb, 7).strip() == "BATTERY SORT"
        for _ in range(5):
            list_tap(gb, "down")
        assert gb.mem("ml_sel") == 5
        assert [line(gb, r).strip() for r in range(14, 16)] == ["THE ROBOT FACTORY", "NO MEDAL YET"]
        list_tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_MINI and gb.pb.memory[0xFF40] & 0x80, 30)
        assert gb.mem("mg_id") == MG_BATTERY and gb.mem("mg_mode") == MG_PRACTICE and score(gb) == 0
        assert text(gb, 2) == "BATTERY SORT"
        gb.write("mg_phase", MG_RESULT)
        run_until(gb, lambda: gb.mem("overlay_on") == 1, 10)
        frames(gb, 3)
        gb.press("b", 2)
        run_until(gb, lambda: state(gb) == GS_MGLIST and gb.pb.memory[0xFF40] & 0x80, 30)
        gb.run(3)
        assert gb.mem("ml_sel") == 5 and line(gb, 7).strip() == "BATTERY SORT"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_release_list_unlocks_it_when_reached(model, release_built):
    """`make release`: Battery Sort is "? ? ?" until STORY or ARCADE reached it; with its bit (and a gold best) in
    Practice's block it lists by name with GOLD and plays."""
    from test_mg_list import MG_PLANNED, line, pr_block, release_rom, tap as list_tap, to_list, with_block
    from test_scores import v7_image
    best = [0] * MG_PLANNED
    best[MG_BATTERY] = MEDAL_GOLD
    ram = with_block(v7_image(), pr_block(1 << MG_BATTERY, best))
    with release_rom(model, ram) as gb:
        to_list(gb)
        assert [line(gb, r).strip() for r in range(2, 7)] == ["? ? ?"] * 5 and line(gb, 7) == " BATTERY SORT GOLD"
        for _ in range(5):
            list_tap(gb, "down")
        assert [line(gb, r).strip() for r in range(14, 16)] == ["THE ROBOT FACTORY", "BEST GOLD"]
        list_tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_MINI, 30)
        assert gb.mem("mg_id") == MG_BATTERY and gb.mem("mg_mode") == MG_PRACTICE
