# docs/minigames_bosses.md 4.10: MILK RUN (src/mr.c), The Chrome Cow's mini-game, on the framework (src/mg.c): the screen
# (the approved art, its palettes, the DMG look V1: the rider on OBP0 = 0xC0, the rest on OBP1 = 0xE0), the street that
# scrolls under the HUD (lcd_isr's raster split, mr_vbl's column writer) and follows its seed (a Python model of the
# generator), lane changes, tosses and their landing (PERFECT 500, delivered 300, lost), crashes (wobble, a crate lost,
# blinking), time up, medals, Practice's HARD, a bot that rides every seed without a crash, the sprites per line on
# every frame, OBP0 put back when the game is left, STORY / ARCADE reaching it in chapter 7, BONUS > MINI GAMES.
import pytest
from conftest import ROOT, check_golden, hold_stage_anim, logic_paused, title_level
from mr_helpers import (ART, BIKER, BOTTOM, BOX, FULL, GATE, LAYOUT, MG_MILKRUN, MR_BG, MR_OBJ, STATE_SIZE, Street, art_define,
                        bot, column_tiles, lane_top, mr, mr_define, next_box, poke, px_after, speed16)
from test_flow import GS_GOAL, LEVEL_CLEAR, PLAYING, TITLE, run_until, state, tilemap_row
from test_mg import (BLANK, GS_MGLIST, GS_MINI, MEDAL_PTS, MG_COUNT, MG_END, MG_HARD, MG_PLAY, MG_PRACTICE, MG_RESULT,
                     MG_STORY, RESULT_MIN, frames, hud_timer, lines, mg_enter, score, text, to_play, to_result, until)
from test_mg_list import release_built  # noqa: F401  (the fixture: `make release`)

pytestmark = pytest.mark.timeout(300)

MEDAL_NONE, MEDAL_BRONZE, MEDAL_SILVER, MEDAL_GOLD = range(4)
SFX_LAUNCH, SFX_SERVE, SFX_COIN, SFX_BREAK = 2, 5, 6, 4
(TIME_S, CRATES, STEP_FRAMES, FLIGHT, PTS_DELIVERED, PTS_PERFECT, PTS_CRATE, WOBBLE, BLINK, GOLD, SILVER, BRONZE, POP_LEN,
 BANNER_OFF, HARD_STEPS) = (mr_define(n) for n in (
    "MR_TIME_S", "MR_CRATES", "MR_STEP_FRAMES", "MR_FLIGHT", "MR_PTS_DELIVERED", "MR_PTS_PERFECT", "MR_PTS_CRATE",
    "MR_WOBBLE", "MR_BLINK", "MR_GOLD", "MR_SILVER", "MR_BRONZE", "MR_POP_LEN", "MR_BANNER_OFF", "MR_HARD_STEPS"))
OAM_BIKE, OAM_RIDER, OAM_STARS, OAM_CRATE, OAM_LOST, OAM_POP = (mr_define(n) for n in (
    "OAM_BIKE", "OAM_RIDER", "OAM_STARS", "OAM_CRATE", "OAM_LOST", "OAM_POP"))
SEED = 0x5A17
S_PALETTE = 0x10
OUT = ROOT / "out" / "mr"
OBJ_ENTRY = {name: art_define(f"MRO_{name}") for name in ("RIDER_A", "RIDER_B", "RIDER_W", "CRATE_LO", "CRATE_HI",
                                                           "STARS", "POP_L", "POP_R")}
BIKE_T = ART["bike_t"]                           # ride A, ride B, wobble x 3 entries


def milk_run(model, mode=MG_PRACTICE, seed=SEED):
    """A booted rom on the title, then Milk Run in practice (or `mode`)."""
    from test_scores import booted
    rom = booted(model)
    hold_stage_anim(rom)
    mg_enter(rom, MG_MILKRUN, mode, seed)
    return rom


def shot(gb, name):
    OUT.mkdir(parents=True, exist_ok=True)
    gb.screenshot(OUT / f"{name}.{gb.model_name}.png", 4)


def oam(gb, i):
    a = 0xFE00 + 4 * i
    return dict(y=gb.mem(a), x=gb.mem(a + 1), tile=gb.mem(a + 2), prop=gb.mem(a + 3))


def tap(gb, key, n=2):
    gb.hold(key)
    frames(gb, n)
    gb.release(key)
    frames(gb, 1)


def snap(gb):
    """The state as of a whole game frame: read in a paused frame (conftest.logic_paused), since a read at PyBoy's frame end can
    catch the game's update half done (a 16-bit field with one byte new)."""
    with logic_paused(gb):
        return mr(gb)


settle = snap


def to_riding(gb, extra=2):
    to_play(gb)
    frames(gb, extra)


def ride(gb, stop, limit=3000, worst=None, deliver=True, hook=None):
    """The bot rides (a lane change it needs, a toss when one is due) frame by frame until stop(state); returns the state."""
    for _ in range(limit):
        s = snap(gb)
        if stop(s):
            return s
        want, toss = bot(s, deliver)
        keys = []
        if want is not None and s["y"] == lane_top(s["lane"]) and want != s["lane"]:
            keys.append("up" if want < s["lane"] else "down")
        if toss:
            keys.append("a")
        for k in keys:
            gb.hold(k)
        frames(gb, 2 if keys else 1, worst)
        for k in keys:
            gb.release(k)
        if keys:
            frames(gb, 1, worst)
        if hook:
            hook(gb)
    raise AssertionError("the stop condition was not reached")


def box_ahead(s, side=None):
    """The nearest live box not past the bike: (slot, column) (side 0 top, 1 bottom)."""
    best = None
    for i, (c, k) in enumerate(zip(s["fcol"], s["fkind"])):
        if k & BOX and (side is None or bool(k & BOTTOM) == bool(side)) and c * 8 + 8 > s["px"]:
            if best is None or c < best[1]:
                best = (i, c)
    return best


def free_slot(s):
    return s["fkind"].index(0)


def clear_ring(gb):
    """No live gate or box (the logic's tests place their own; the street's map is not touched)."""
    for slot in range(6):                          # MR_FT
        poke(gb, fkind=(slot, 0))


def put_bike(gb, lane):
    poke(gb, lane=lane, y=lane_top(lane))


# ---- the screen ------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_screen_and_its_art(model):
    """The intro: the banner, the HUD (score, the crate icon and 12, T045), the street's first 21 columns as the model builds
    them, the tiles and palettes of the approved art, the sprites (bike entries, the rider), the DMG registers."""
    with milk_run(model) as gb:
        assert gb.mem("mg_id") == MG_MILKRUN and gb.mem("mg_mode") == MG_PRACTICE and gb.mem("mg_phase") == 0
        frames(gb, 30)
        assert text(gb, 2) == "MILK RUN" and text(gb, 3) == "UP DOWN LANE A TOSS"
        assert hud_timer(gb) == "T045" and score(gb) == 0 and gb.mem16("mg_timer") == 0
        assert tilemap_row(gb, 0, 8, 4) == [BLANK, MR_BG + art_define("MRB_HUDC"), 36 + 1, 36 + 2]   # "12" (glyph 0 is 36)
        s = mr(gb)
        assert (s["crates"], s["lane"], s["y"], s["px"], s["steps"], s["time"]) == (CRATES, 1, 64, 0, 0, TIME_S * 60)
        # the tiles of the art
        want = bytes(ART["bg"])
        got = b"".join(bytes(gb.read((0x9000 + t * 16) if t < 128 else (0x8000 + t * 16), 16))
                       for t in range(MR_BG, MR_BG + ART["n_bg"]))
        assert got == want, "BG tiles"
        assert bytes(gb.read(0x8000 + MR_OBJ * 16, ART["n_obj"] * 16)) == bytes(ART["obj"]), "OBJ tiles"
        # the street: columns 0-20 (the banner rows 2-3 hold the framework's text now)
        st = Street(SEED)
        st.stream_to(21)
        tm = gb.bg_tilemap()
        for c in range(21):
            tiles, pals = column_tiles(c, st.feats)
            for r in range(17):
                if r in (1, 2):
                    continue
                assert tm[r + 1][c] & 0xFF == tiles[r], (c, r + 1)
                if model == "cgb":
                    assert gb.pb.memory[1, 0x9800 + (r + 1) * 32 + c] & 7 == (pals[r] if pals[r] else 0), (c, r + 1)
        assert tilemap_row(gb, 0, 20, 12) == [BLANK] * 12, "the HUD row's other columns are blank (the split's last line)"
        # the sprites: the bike's three entries, the rider
        for k in range(3):
            o = oam(gb, OAM_BIKE + k)
            assert (o["y"], o["x"], o["tile"]) == (64 + 16, 24 + 8 * k + 8, MR_OBJ + BIKE_T[k])
        r = oam(gb, OAM_RIDER)
        assert (r["y"], r["x"], r["tile"]) == (62 + 16, 24 + 6 + 8, MR_OBJ + OBJ_ENTRY["RIDER_A"])
        if model == "dmg":
            assert gb.mem(0xFF48) == 0xC0 and gb.mem(0xFF49) == 0xE0 and gb.mem(0xFF47) == 0xE4
            assert all(oam(gb, OAM_BIKE + k)["prop"] & S_PALETTE for k in range(3)), "the bike: OBP1"
            assert not r["prop"] & S_PALETTE, "the rider: OBP0 (a white face)"
        else:
            from test_venues import cgb_palette
            rgb = lambda r_, g, b: (r_ >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10)
            assert cgb_palette(gb, 0) == [rgb(232, 224, 208), rgb(120, 112, 136), rgb(168, 168, 192), rgb(32, 24, 32)]
            assert cgb_palette(gb, 2) == [rgb(240, 224, 184), rgb(120, 184, 72), rgb(192, 80, 56), rgb(32, 24, 32)]
            assert cgb_palette(gb, 6)[2] == rgb(72, 104, 168) and cgb_palette(gb, 5)[2] == rgb(44, 120, 64)
            assert cgb_palette(gb, 3)[1] == rgb(208, 56, 72) and cgb_palette(gb, 7)[2] == rgb(240, 120, 40)
            assert cgb_palette(gb, 4) != cgb_palette(gb, 7), "palette 4 is left to the result's medal"
            assert cgb_palette(gb, 1, obj=True) == [0, rgb(248, 248, 240), rgb(208, 56, 72), rgb(32, 32, 48)]
            assert cgb_palette(gb, 2, obj=True)[2] == rgb(248, 208, 56)
            assert r["prop"] & 7 == 0 and all(oam(gb, OAM_BIKE + k)["prop"] & 7 == 1 for k in range(3))


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_street_follows_the_seed_and_scrolls_under_a_fixed_hud(model):
    """Playing: the live gates and boxes are the model's (mg_rand's xorshift on the seed), every visible map column is what
    the model builds from them, SCX is the scroll, the HUD row does not move (lcd_isr's split)."""
    with milk_run(model) as gb:
        to_riding(gb)
        st = Street(SEED)
        hud0 = gb.image().crop((0, 0, 8 * 8, 7)).tobytes()
        for i in range(240):
            frames(gb, 1)
            if i % 7:
                continue
            s = settle(gb)
            k = s["px"] >> 3
            st.stream_to(s["next_col"] - 1)
            live = sorted((c, kd) for c, kd in zip(s["fcol"], s["fkind"]) if kd)
            want = sorted((c, kd) for c, kd in st.feats if c * 8 + 16 >= s["px"] - 8)
            assert [f for f in live if f[0] * 8 + 16 >= s["px"] + 8] == [f for f in want if f[0] * 8 + 16 >= s["px"] + 8]
            tm = gb.bg_tilemap()
            for c in range(k, min(k + 21, s["next_col"])):
                tiles, pals = column_tiles(c, live)
                for r in range(17):
                    assert tm[r + 1][c & 31] & 0xFF == tiles[r], (i, c, r + 1)
            assert gb.image().crop((0, 0, 8 * 8, 7)).tobytes() == hud0, "the score on the HUD row stays put"
        s = mr(gb)
        assert s["px"] > 300 and s["scx"] == s["px"] & 255 and s["colq"] in (0, 1)
        assert text(gb, 2) == "" and text(gb, 3) == "", "the banner is gone (the street is back under it)"


def test_the_generator_keeps_its_rules():
    """Whatever the seed: every gate leaves a lane free, the next gate is far enough for the lanes to cross at 2.5 px a frame
    (v x (8 L + 32) px), boxes keep 34+ columns apart (>= 64 px) on a side, 12 of them, and no gate near a box blocks its
    kerb's lane (src/mr.c gen_gate / gen_box)."""
    from mr_helpers import crossing
    for seed in range(1, 200):
        st = Street(seed)
        st.stream_to(900)
        gates, boxes = st.gates(), st.boxes()
        assert len(boxes) == mr_define("MR_BOXES") and gates
        assert all(k & 7 != 7 for _, k in gates)
        for (c0, k0), (c1, k1) in zip(gates, gates[1:]):
            assert (c1 - c0) * 8 >= 2.5 * (8 * crossing(k0 & 7, k1 & 7) + 32), (seed, c0, c1)
        for (c0, k0), (c1, k1) in zip(boxes, boxes[1:]):
            assert c1 - c0 >= 34 > 8
        for bc, bk in boxes:
            lane = 2 if bk & BOTTOM else 0
            for gc, gk in gates:
                if gc + mr_define("GATE_BEFORE") >= bc and gc <= bc + mr_define("GATE_AFTER"):
                    assert not (gk >> lane) & 1, (seed, bc, gc)
        assert boxes[0][0] >= 30 and gates[0][0] >= 34


# ---- driving: the scroll, the lanes --------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_speed_steps_up_every_10_seconds_and_a_crash_drops_a_step(model):
    """1.5 px a frame (90 px in 60 frames), +0.25 every 600 frames to 2.5 (150 px in 60); a crash drops one step, never
    below 1.5."""
    with milk_run(model) as gb:
        to_riding(gb)
        put_bike(gb, 1)
        for steps, per60 in ((0, 90), (1, 105), (2, 120), (3, 135), (4, 150)):
            clear_ring(gb)
            poke(gb, steps=steps, clk=0)
            s0 = settle(gb)
            frames(gb, 60)
            s1 = settle(gb)
            assert s1["steps"] == steps
            n = (s1["anim"] - s0["anim"]) & 255          # (game frames: PyBoy's frame can fall between two of the game's)
            assert 58 <= n <= 62
            assert s1["px"] == px_after(s0, n), steps
            assert abs(s1["px"] - s0["px"] - per60 * n // 60) <= 2
        poke(gb, steps=0, clk=STEP_FRAMES - 3)
        until_steps = []
        for _ in range(6):
            frames(gb, 1)
            until_steps.append(mr(gb)["steps"])
        assert until_steps[-1] == 1 and until_steps[0] == 0, "one step at 600 frames"
        poke(gb, steps=mr_define("MR_STEPS_MAX"), clk=STEP_FRAMES - 1)
        frames(gb, 3)
        assert mr(gb)["steps"] == mr_define("MR_STEPS_MAX"), "2.5 is the top"


def lane_now(gb):
    s = snap(gb)
    return s["lane"], s["y"]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_up_and_down_change_lane_in_8_frames_and_one_press_is_queued(model):
    with milk_run(model) as gb:
        to_riding(gb)
        assert lane_now(gb) == (1, 64)
        a0 = snap(gb)["anim"]
        gb.hold("up")
        seen = {}
        for _ in range(14):
            frames(gb, 1)
            s = snap(gb)
            seen[(s["anim"] - a0) & 255] = s["y"]
        gb.release("up")
        frames(gb, 2)
        # frame n of the change (n = 1 is the one that saw the press): 2 px a frame, 8 frames, nothing again while held
        assert all(y == max(48, 64 - 2 * n) for n, y in seen.items() if n >= 1), seen
        assert 8 in seen or 9 in seen or 10 in seen
        assert lane_now(gb) == (0, 48)
        tap(gb, "up")
        assert lane_now(gb) == (0, 48), "no lane above the top one"
        tap(gb, "down")
        frames(gb, 12)
        assert lane_now(gb) == (1, 64)
        tap(gb, "down")
        frames(gb, 12)
        assert lane_now(gb) == (2, 80)
        tap(gb, "down")
        assert lane_now(gb) == (2, 80)
        # a press during a change is queued, and only one (the last)
        put_bike(gb, 0)
        frames(gb, 2)
        tap(gb, "down", 1)                          # the change to lane 2 starts
        frames(gb, 2)
        assert snap(gb)["y"] not in (48, 64)
        tap(gb, "down", 1)                          # queued during it
        assert snap(gb)["queued"] == 1
        frames(gb, 24)
        assert lane_now(gb) == (2, 80), "the queued press took it on to the bottom lane"
        tap(gb, "up", 1)                            # 3 -> 2 starts
        frames(gb, 1)
        tap(gb, "up", 1)                            # queued: on to the top lane
        assert snap(gb)["queued"] == -1
        tap(gb, "down", 1)                          # replaces it: back down
        assert snap(gb)["queued"] == 1
        frames(gb, 30)
        assert lane_now(gb) == (2, 80) and snap(gb)["queued"] == 0


# ---- tosses and landings -------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_toss_flies_16_frames_and_costs_a_crate(model):
    with milk_run(model) as gb:
        to_riding(gb)
        clear_ring(gb)
        tap(gb, "a")
        s = snap(gb)
        assert s["crates"] == CRATES and not any(t["t"] for t in s["toss"]), "lane 2: he shrugs, nothing lost"
        put_bike(gb, 0)
        frames(gb, 2)
        gb.hold("a")
        frames(gb, 2)
        gb.release("a")
        s = snap(gb)
        assert s["crates"] == CRATES - 1 and 1 <= s["toss"][0]["t"] <= 3 and s["toss"][0]["side"] == 0
        assert gb.mem("last_sfx") == SFX_LAUNCH
        assert tilemap_row(gb, 0, 10, 2) == [36 + 1, 36 + 1], "the HUD shows 11"
        ys, last = [], 0
        for _ in range(20):
            s = snap(gb)
            t = s["toss"][0]["t"]
            if t == 0:
                break
            assert t >= last
            if t != last:
                o = oam(gb, OAM_CRATE)
                ys.append(o["y"] - 16)
                assert o["x"] == 24 + 6 + 8
                assert o["tile"] == MR_OBJ + (OBJ_ENTRY["CRATE_HI"] if 4 <= t <= 11 else OBJ_ENTRY["CRATE_LO"]), t
                assert o["prop"] & S_PALETTE and (model == "dmg" or o["prop"] & 7 == 1)
            last = t
            frames(gb, 1)
        assert last == FLIGHT, "16 frames in the air"
        assert ys == sorted(ys, reverse=True) and ys[0] > ys[-1] and ys[-1] <= 28, "it climbs to the top kerb's box"
        frames(gb, 2)
        assert not any(t["t"] for t in snap(gb)["toss"]), "landed after 16 frames"
        # two in the air at most; the third press is ignored (nothing lost)
        c0 = snap(gb)["crates"]
        for _ in range(3):
            tap(gb, "a", 2)
        s = snap(gb)
        assert sum(1 for t in s["toss"] if t["t"]) == 2 and s["crates"] == c0 - 2
        # lane 3's crates go down to the bottom kerb
        frames(gb, 30)
        put_bike(gb, 2)
        frames(gb, 18)
        tap(gb, "a", 2)
        s = snap(gb)
        assert [t["side"] for t in s["toss"] if t["t"]] == [1]


def align_toss(gb, side, off, d_land=None):
    """Poke the scroll so that a crate landing now would be `off` px right of the centre of the next box of `side`, with the
    bike in that kerb's lane and a crate on its last frame: the next frame judges it. Returns the box's slot."""
    s = mr(gb)
    box = box_ahead(s, side)
    assert box is not None
    slot, col = box
    lane = 2 if side else 0
    put_bike(gb, lane)
    inc = speed16(s) >> 4                           # the next frame's scroll (the sub-pixel part poked to 0)
    px = col * 8 + 8 + off - 34 - inc
    poke(gb, px=px, frac=0)
    a = gb.addr("story_scratch")
    from mr_helpers import TOSS_AT
    with logic_paused(gb):
        gb.write(a + TOSS_AT, FLIGHT)               # t = 16: the next frame makes it 17 and lands it
        gb.write(a + TOSS_AT + 1, side)
        gb.write(a + TOSS_AT + 2, lane_top(lane))
    return slot, col


def reach_box(gb, side):
    to_riding(gb)
    ride(gb, lambda s: box_ahead(s, side) is not None and box_ahead(s, side)[1] * 8 < s["px"] + 150, deliver=False)
    clear_other_gates(gb)


def clear_other_gates(gb):
    """(The poked scroll jumps over gates: the bike is not to crash on their account.)"""
    s = snap(gb)
    for slot, k in enumerate(s["fkind"]):
        if k & GATE:
            poke(gb, fkind=(slot, 0))


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("side", [0, 1])
@pytest.mark.parametrize("off,kind", [(-17, "lost"), (17, "lost"), (-9, "delivered"), (9, "delivered"), (-16, "delivered"),
                                      (16, "delivered"), (-8, "perfect"), (8, "perfect"), (0, "perfect")])
def test_a_crate_within_8_px_of_a_box_is_perfect_16_delivered_else_lost(model, side, off, kind):
    """PERFECT: 500, the pop over the box, its two top tiles full; delivered: 300, no pop; further away: lost on the pavement."""
    with milk_run(model) as gb:
        reach_box(gb, side)
        s0 = snap(gb)
        a = gb.mem16("mg_score")
        slot, col = align_toss(gb, side, off)
        frames(gb, 1)
        s1 = snap(gb)
        d = s1["delivered"] - s0["delivered"]
        pts = gb.mem16("mg_score") - a
        row = 12 if side else 4
        full = MR_BG + art_define("MRB_BOX") + 4 * (side * 2 + 1)
        empty = full - 4
        if kind == "lost":
            assert d == 0 and pts == 0 and not s1["fkind"][slot] & FULL and s1["pop_t"] == 0
            frames(gb, 2)
            assert tilemap_row(gb, row, col & 31, 2) == [empty, empty + 1]
            return
        assert d == 1 and s1["fkind"][slot] & FULL
        assert pts == (PTS_PERFECT if kind == "perfect" else PTS_DELIVERED) and s1["perfect"] - s0["perfect"] == (kind == "perfect")
        frames(gb, 2)
        assert tilemap_row(gb, row, col & 31, 2) == [full, full + 1], "the box's top tiles: a crate in it"
        assert tilemap_row(gb, row + 1, col & 31, 2) == [empty + 2, empty + 3], "its lower tiles are the empty box's"
        bgb = ART["bg"]
        assert bgb[(full + 2 - MR_BG) * 16:(full + 4 - MR_BG) * 16] == bgb[(empty + 2 - MR_BG) * 16:(empty + 4 - MR_BG) * 16], \
            "(the same tiles: only the top two change when a crate lands)"
        if kind == "perfect":
            assert snap(gb)["pop_t"] > 0 and gb.mem("last_sfx") == SFX_SERVE
            o = oam(gb, OAM_POP)
            assert o["tile"] == MR_OBJ + OBJ_ENTRY["POP_L"] and oam(gb, OAM_POP + 1)["tile"] == MR_OBJ + OBJ_ENTRY["POP_R"]
            assert oam(gb, OAM_POP + 1)["x"] == o["x"] + 8 and o["y"] - 16 in (28, 27, 116, 115)
            assert o["x"] == (col * 8 - snap(gb)["px"]) + 8
        else:
            assert snap(gb)["pop_t"] == 0 and gb.mem("last_sfx") == SFX_COIN
        # a full box takes no second crate
        s2 = snap(gb)
        align_toss(gb, side, 0)
        frames(gb, 2)
        assert snap(gb)["delivered"] == s2["delivered"]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_perfect_and_delivered_points(model):
    with milk_run(model) as gb:
        to_riding(gb)
        ride(gb, lambda s: box_ahead(s, 0) is not None and box_ahead(s, 0)[1] * 8 < s["px"] + 150, deliver=False)
        a = gb.mem16("mg_score")
        align_toss(gb, 0, 14)
        frames(gb, 2)
        assert gb.mem16("mg_score") - a == PTS_DELIVERED and score(gb) == PTS_DELIVERED and gb.mem("last_sfx") == SFX_COIN
        ride(gb, lambda s: box_ahead(s, 1) is not None and box_ahead(s, 1)[1] * 8 < s["px"] + 150, deliver=False)
        a = gb.mem16("mg_score")
        align_toss(gb, 1, 0)
        frames(gb, 2)
        assert gb.mem16("mg_score") - a == PTS_PERFECT and gb.mem("last_sfx") == SFX_SERVE
        s = mr(gb)
        assert s["delivered"] == 2 and s["perfect"] == 1


# ---- crashes ----------------------------------------------------------------------------------------------------------------------------
def put_gate(gb, lanes, ahead=0):
    """A gate (lane bits) over the bike's hit box right now (the map is not drawn: the logic's only)."""
    s = mr(gb)
    slot = free_slot(s)
    poke(gb, fcol=(slot, (s["px"] + 28) // 8 + ahead), fkind=(slot, GATE | lanes))
    return slot


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_crash_wobbles_loses_a_crate_slows_the_street_then_blinks(model):
    with milk_run(model) as gb:
        to_riding(gb)
        put_bike(gb, 0)
        frames(gb, 14)
        poke(gb, steps=2)
        # a gate in lane 2 / 3 does not touch a bike in lane 1
        put_gate(gb, 0b110)
        frames(gb, 2)
        assert mr(gb)["inv"] == 0 and mr(gb)["crates"] == CRATES
        put_gate(gb, 0b001)
        frames(gb, 1)
        s = settle(gb)
        assert s["inv"] >= WOBBLE + BLINK - 2 and s["crates"] == CRATES - 1 and s["steps"] == 1
        assert s["lost_t"] > 0 and gb.mem("last_sfx") == SFX_BREAK
        assert tilemap_row(gb, 0, 10, 2) == [36 + 1, 36 + 1], "the HUD shows 11"
        # the wobble: frame 3 of the bike, the rider 1 px left, two stars; no tosses
        o = [oam(gb, OAM_BIKE + k) for k in range(3)]
        assert [x["tile"] for x in o] == [MR_OBJ + BIKE_T[6 + k] for k in range(3)]
        assert oam(gb, OAM_RIDER)["x"] == 24 + 5 + 8 and oam(gb, OAM_RIDER)["tile"] == MR_OBJ + OBJ_ENTRY["RIDER_W"]
        st1, st2 = oam(gb, OAM_STARS), oam(gb, OAM_STARS + 1)
        assert st1["tile"] == st2["tile"] == MR_OBJ + OBJ_ENTRY["STARS"] and not st1["prop"] & 0x20 and st2["prop"] & 0x20
        assert (st1["x"], st1["y"] - 16) == (24 + 6 + 8, 48 - 10) and (st2["x"], st2["y"] - 16) == (24 + 14 + 8, 48 - 6)
        c0 = mr(gb)["crates"]
        tap(gb, "a")
        assert mr(gb)["crates"] == c0 and not any(t["t"] for t in mr(gb)["toss"]), "no tosses in a wobble"
        # the lost crate is on the street, left behind with it
        lost = oam(gb, OAM_LOST)
        assert lost["tile"] == MR_OBJ + OBJ_ENTRY["CRATE_LO"]
        x0 = lost["x"]
        frames(gb, 6)
        assert oam(gb, OAM_LOST)["x"] < x0 or oam(gb, OAM_LOST)["y"] == 0
        # invulnerable: another gate does nothing
        put_gate(gb, 0b001)
        frames(gb, 3)
        assert mr(gb)["crates"] == c0
        until(gb, lambda: mr(gb)["inv"] <= BLINK, 40)
        frames(gb, 1)
        shown = []
        for _ in range(BLINK):
            frames(gb, 1)
            shown.append(oam(gb, OAM_BIKE)["y"] != 0)
            if mr(gb)["inv"] == 0:
                break
        assert True in shown and False in shown, "blinking"
        runs = "".join("1" if v else "0" for v in shown)
        assert "1111" in runs and "0000" in runs, runs
        frames(gb, 4)
        assert mr(gb)["inv"] == 0
        # a toss is allowed again, a crash again
        c0 = mr(gb)["crates"]
        put_gate(gb, 0b001)
        frames(gb, 2)
        assert mr(gb)["crates"] == c0 - 1 and mr(gb)["steps"] == 0, "the second crash: down to 1.5, the floor"
        poke(gb, inv=0)
        put_gate(gb, 0b001)
        frames(gb, 3)
        assert mr(gb)["steps"] == 0, "never below 1.5"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_gate_between_lanes_hits_a_bike_changing_lane(model):
    """The hit box is 12 px tall: a bike changing lanes touches both the lanes it overlaps."""
    with milk_run(model) as gb:
        to_riding(gb)
        clear_ring(gb)
        put_gate(gb, 0b100, ahead=40)               # lane 3 only, far ahead: not touched yet
        frames(gb, 2)
        assert mr(gb)["inv"] == 0
        clear_ring(gb)
        put_bike(gb, 2)
        frames(gb, 14)
        put_gate(gb, 0b100)
        frames(gb, 2)
        assert mr(gb)["inv"] > 0, "in lane 3 over a lane 3 gate"
        clear_ring(gb)
        poke(gb, inv=0, lane=1, y=64)
        frames(gb, 2)
        put_gate(gb, 0b100)
        frames(gb, 2)
        assert snap(gb)["inv"] == 0, "lane 2 and lane 3 do not overlap: the hit box is y + 2 .. y + 14"
        gb.hold("down")
        frames(gb, 2)
        gb.release("down")
        seen = []
        for _ in range(6):
            s = snap(gb)
            seen.append((s["y"], s["inv"]))
            frames(gb, 1)
        crashed = [y for y, inv in seen if inv]
        assert crashed and min(crashed) == 68 and all(y <= 66 for y, inv in seen if not inv), seen
        # (hit box y + 2 .. y + 14 touches lane 3, y 80 .., from y 67)


# ---- the end ----------------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_time_up_gives_100_a_crate_a_banner_and_the_street_stops(model):
    with milk_run(model) as gb:
        to_riding(gb)
        poke(gb, crates=5, time=3, steps=4)
        until(gb, lambda: gb.mem("mg_phase") == MG_END, 10)
        frames(gb, 3)
        assert gb.mem16("mg_score") == 5 * PTS_CRATE and score(gb) == 5 * PTS_CRATE
        assert gb.mem("overlay_on") == 1 and text(gb, 1, True) == "TIME UP"
        assert mr(gb)["st"] == 1
        px = [mr(gb)["px"]]
        for _ in range(50):
            frames(gb, 1)
            px.append(mr(gb)["px"])
        assert px[-1] == px[-2] == px[-3], "the street has come to a stop"
        assert px[3] - px[2] >= 1 and px[3] - px[2] > px[-12] - px[-13], "slowing down first"
        until(gb, lambda: gb.mem("overlay_on") == 0, 60)
        assert gb.mem("mg_t") >= BANNER_OFF - 1 and gb.mem("mg_phase") == MG_END
        until(gb, lambda: gb.mem("mg_phase") == MG_RESULT, 20)
        until(gb, lambda: gb.mem("overlay_on") == 1, 10)
        frames(gb, 3)
        assert text(gb, 2, True, x0=4) == f"SCORE {5 * PTS_CRATE}" and text(gb, 4, True, x0=4) == "A RETRY B MENU"
        assert hud_timer(gb) == "T000"
        assert gb.mem(0xFF45) in (7, 64 + 46, 144), "LYC walks lcd_isr's chain"


def deliveries(gb, n, perfect=0):
    poke(gb, delivered=n, perfect=perfect)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("n,medal", [(0, MEDAL_NONE), (3, MEDAL_NONE), (4, MEDAL_BRONZE), (6, MEDAL_BRONZE),
                                     (7, MEDAL_SILVER), (9, MEDAL_SILVER), (10, MEDAL_GOLD), (12, MEDAL_GOLD)])
def test_the_medal_is_by_deliveries_4_7_10(model, n, medal):
    with milk_run(model) as gb:
        to_riding(gb)
        deliveries(gb, n)
        frames(gb, 2)
        to_result(gb)
        assert gb.mem("mg_medal") == medal
        assert score(gb) == MEDAL_PTS[medal]
        assert text(gb, 3, True, x0=4) == ["NO MEDAL", "BRONZE 500", "SILVER 1500", "GOLD 3000"][medal]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_practice_hard_starts_at_2_px_and_does_not_slow_below_it(model):
    with milk_run(model, MG_PRACTICE | MG_HARD) as gb:
        to_riding(gb)
        assert mr(gb)["steps"] == HARD_STEPS
        a = settle(gb)["px"]
        frames(gb, 60)
        assert abs(settle(gb)["px"] - a - 120) <= 3, "2.0 px a frame"
        put_bike(gb, 0)
        frames(gb, 14)
        put_gate(gb, 0b001)
        frames(gb, 2)
        s = mr(gb)
        assert s["inv"] > 0 and s["steps"] == HARD_STEPS, "HARD: the floor is 2.0"
        poke(gb, inv=0, steps=3)
        put_gate(gb, 0b001)
        frames(gb, 2)
        assert mr(gb)["steps"] == 2, "a crash drops a step"
        poke(gb, inv=0)
        put_gate(gb, 0b001)
        frames(gb, 2)
        assert mr(gb)["steps"] == HARD_STEPS, "but not below 2.0"
    with milk_run(model) as gb:
        to_riding(gb)
        assert mr(gb)["steps"] == 0, "a normal practice starts at 1.5"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_hud_counts_crates_and_seconds(model):
    """Score, the crates left (icon + 2 digits at columns 9-11), T + seconds from 45 (the framework's format, own timer)."""
    with milk_run(model) as gb:
        to_riding(gb)
        clear_ring(gb)
        assert hud_timer(gb) == "T045"
        put_bike(gb, 0)
        frames(gb, 14)
        for n in range(3):
            tap(gb, "a", 2)
            frames(gb, 20)
            crates = snap(gb)["crates"]
            assert crates == CRATES - 1 - n
            assert tilemap_row(gb, 0, 10, 2) == [36 + crates // 10, 36 + crates % 10]
            assert tilemap_row(gb, 0, 9, 1) == [MR_BG + art_define("MRB_HUDC")]
        poke(gb, time=60 * 30 + 59)
        frames(gb, 3)
        assert hud_timer(gb) == "T031"
        poke(gb, time=60 * 9 + 5)
        frames(gb, 3)
        assert hud_timer(gb) == "T010"
        poke(gb, time=61)
        frames(gb, 3)
        assert hud_timer(gb) == "T001"
        until(gb, lambda: gb.mem("mg_phase") == MG_END, 80)
        assert hud_timer(gb) == "T000"


# ---- sprites per line, a whole game ------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_whole_game_keeps_to_10_sprites_a_line(model):
    """The bot plays a whole game from the intro to the result, delivering, with a crash dropped in with two crates in the air
    and a PERFECT pop showing: never more than 10 sprites on a line (the design's worst is 9)."""
    with milk_run(model, seed=0x2468) as gb:
        worst = [0]
        to_play(gb)
        done = []

        def crash_now(g):
            s = mr(g)
            if not done and s["px"] > 1500 and s["delivered"] >= 2 and s["inv"] == 0:
                done.append(1)
                put_bike(g, 0)
                frames(g, 1, worst)
                tap(g, "a", 1)
                tap(g, "a", 1)                      # two crates in the air (the bot's own tosses aside)
                put_gate(g, 0b001)
                poke(g, pop_t=POP_LEN)

        ride(gb, lambda s: gb.mem("mg_phase") != MG_PLAY, limit=6000, worst=worst, hook=crash_now)
        assert done
        until(gb, lambda: gb.mem("mg_phase") == MG_RESULT, 80)
        assert worst[0] <= 10, worst
        assert worst[0] >= 5, "(the crash scene was seen)"
        print("worst sprites on a line:", worst[0])


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_worst_case_scene_is_9_a_line(model):
    """Everything at once on the bike's lines: its 4 entries, two crates in the air, the lost crate, the stars: 9 on a line."""
    with milk_run(model) as gb:
        to_riding(gb)
        put_bike(gb, 2)
        frames(gb, 18)
        tap(gb, "a", 1)
        tap(gb, "a", 1)
        put_gate(gb, 0b100)
        worst = [0]
        frames(gb, 3, worst)
        s = mr(gb)
        assert sum(1 for t in s["toss"] if t["t"]) == 2 and s["inv"] > BLINK and s["lost_t"]
        frames(gb, 8, worst)
        assert 8 <= worst[0] <= 10, worst


# ---- the bot: a clean run exists at every seed ------------------------------------------------------------------------------------------
@pytest.mark.parametrize("seed", [SEED, 0x1234, 0xBEEF, 0x2468])
def test_the_bot_rides_a_whole_game_without_a_crash_and_delivers(seed):
    with milk_run("cgb", seed=seed) as gb:
        to_play(gb)
        crashes = []
        last = [0]

        def watch(g):
            inv = mr(g)["inv"]
            if inv > last[0]:
                crashes.append(mr(g)["px"])
            last[0] = inv

        ride(gb, lambda s: gb.mem("mg_phase") != MG_PLAY, limit=6000, hook=watch)
        s = mr(gb)
        assert crashes == [] and s["steps"] == 4
        assert s["delivered"] >= 8 and s["perfect"] == s["delivered"], s
        assert s["px"] > 5000, "the whole street (656 columns) went by"


# ---- leaving: OBP0, VRAM, STORY, ARCADE, the list ---------------------------------------------------------------------------------------------
def test_obp0_is_put_back_when_milk_run_is_left_whichever_way():
    """DMG: the rider's OBP0 = 0xC0 is Milk Run's alone; leaving (the result's B to the list, then the title and a level, a
    retry, STORY's A CONTINUE) puts the boot's 0xD0 back or the bartender's face goes white everywhere else."""
    from test_scores import booted
    with milk_run("dmg") as gb:
        to_riding(gb)
        assert gb.mem(0xFF48) == 0xC0 and gb.mem(0xFF49) == 0xE0
        to_result(gb)
        assert gb.mem(0xFF48) == 0xC0, "still Milk Run's while the result shows"
        gb.press("a", 2)                            # RETRY: Milk Run again
        run_until(gb, lambda: state(gb) == GS_MINI and gb.pb.memory[0xFF40] & 0x80, 30)
        frames(gb, 3)
        assert gb.mem(0xFF48) == 0xC0 and gb.mem("mg_phase") == 0
        to_result(gb)
        gb.press("b", 2)                            # MENU: the practice list
        run_until(gb, lambda: state(gb) == GS_MGLIST and gb.pb.memory[0xFF40] & 0x80, 30)
        gb.run(3)
        assert gb.mem(0xFF48) == 0xD0, "Practice back: OBP0 as at boot"
        gb.press("b", 2)
        run_until(gb, lambda: state(gb) == TITLE and gb.pb.memory[0xFF40] & 0x80, 30)
        gb.run(10)
        assert gb.mem(0xFF48) == 0xD0 and gb.mem(0xFF43) == 0
    # another game after Milk Run starts from the boot's OBP0 too (a retry of a game that is not Milk Run)
    with milk_run("dmg") as gb:
        to_riding(gb)
        mg_enter(gb, 16, MG_PRACTICE)
        frames(gb, 3)
        assert gb.mem(0xFF48) == 0xD0, "the stub: not Milk Run's"
    # STORY: the chapter's mini slot, A CONTINUE
    from test_story import to_shift, win
    with to_shift("dmg", BIKER, 1) as gb:
        win(gb, BIKER, 1)
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 20)
        run_until(gb, lambda: state(gb) == GS_MINI, 300)
        run_until(gb, lambda: gb.pb.memory[0xFF40] & 0x80, 10)
        frames(gb, 3)
        assert gb.mem(0xFF48) == 0xC0
        to_result(gb)
        until(gb, lambda: gb.mem("mg_t") >= RESULT_MIN, RESULT_MIN)
        gb.press("a", 2)
        run_until(gb, lambda: state(gb) == GS_GOAL, 60)
        gb.run(3)
        assert gb.mem(0xFF48) == 0xD0, "the Last call: the bartender's palette is the boot's"
        assert gb.mem(0xFF43) == 0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_level_after_milk_run_has_everything_back(model):
    """Milk Run (a perfect delivery, a crash) -> B to the list -> the title -> a level: the level's OBJ tiles, BG 77-255,
    OBP0 / OBP1 and every palette are byte for byte those of a level started from a fresh boot; SCX is 0."""
    from test_bs import level_vram, palettes
    from test_scores import booted
    with booted(model) as gb:
        hold_stage_anim(gb)
        title_level(gb)
        run_until(gb, lambda: state(gb) == PLAYING, 60)
        gb.run(2)
        fresh, pals = level_vram(gb), palettes(gb)
    with milk_run(model) as gb:
        to_riding(gb)
        ride(gb, lambda s: s["delivered"] >= 1, limit=1200)
        put_bike(gb, 0)
        frames(gb, 14)
        put_gate(gb, 0b001)
        frames(gb, 3)
        with logic_paused(gb):
            gb.write("mg_phase", MG_RESULT)
        until(gb, lambda: gb.mem("overlay_on") == 1, 10)
        frames(gb, 2)
        gb.press("b", 2)
        run_until(gb, lambda: state(gb) == GS_MGLIST and gb.pb.memory[0xFF40] & 0x80, 30)
        gb.run(3)
        assert gb.mem(0xFF43) == 0
        gb.press("b", 2)
        run_until(gb, lambda: state(gb) == TITLE and gb.pb.memory[0xFF40] & 0x80, 30)
        gb.run(10)
        gb.press("b", 2)
        gb.run(10)
        title_level(gb)
        run_until(gb, lambda: state(gb) == PLAYING, 60)
        gb.run(60)
        assert gb.mem(0xFF43) == 0
        gb.run(2)
        assert level_vram(gb) == fresh
        assert palettes(gb) == pals


def to_mini_slot(model, mode_arcade=False):
    from test_story import to_shift, win
    gb = to_shift(model, BIKER, 1)
    win(gb, BIKER, 1)
    run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 20)
    run_until(gb, lambda: state(gb) == GS_MINI, 300)
    run_until(gb, lambda: gb.pb.memory[0xFF40] & 0x80, 10)
    return gb


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_story_plays_it_in_chapter_7_and_the_last_call_has_everything_back(model):
    """Chapter 7 (The Chrome Cow): after the Happy hour, Milk Run in MG_STORY (the score carried, the count not skippable,
    unlocked for Practice at once); its result's A CONTINUE leads to the Last call, whose VRAM and palettes are those of the
    Last call reached without it."""
    from test_bs import level_vram, palettes
    from test_story import to_goal, to_shift, win
    with to_shift(model, BIKER, 2) as gb:
        gb.run(2)
        fresh, pals = level_vram(gb), palettes(gb)
    with to_shift(model, BIKER, 1) as gb:
        assert gb.mem16("mg_unlocked") == 0
        win(gb, BIKER, 1)
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 20)
        run_until(gb, lambda: state(gb) == GS_MINI, 300)
        run_until(gb, lambda: gb.pb.memory[0xFF40] & 0x80, 10)
        assert gb.mem("mg_id") == MG_MILKRUN and gb.mem("mg_mode") == MG_STORY and gb.mem("venue_id") == BIKER
        assert text(gb, 2) == "MILK RUN" and score(gb) > 0
        assert gb.mem16("mg_unlocked") == 1 << MG_MILKRUN
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
        assert gb.mem("story_chapter") == BIKER and gb.mem("story_shift") == 2 and gb.mem("story_step") == 3
        to_goal(gb)
        gb.run(2)
        assert level_vram(gb) == fresh
        assert palettes(gb) == pals


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_arcade_plays_it_in_chapter_7(model):
    """ARCADE plays the story's steps: the Chrome Cow's mini slot is Milk Run, in MG_STORY; reaching it unlocks it."""
    from test_arcade import start_arcade
    from test_story import to_goal, win
    with start_arcade(model) as gb:
        to_goal(gb)
        gb.write("story_chapter", BIKER)
        gb.write("story_step", 1)
        win(gb, 0, 0)
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 20)
        run_until(gb, lambda: state(gb) == GS_MINI, 400)
        run_until(gb, lambda: gb.pb.memory[0xFF40] & 0x80, 10)
        assert gb.mem("mg_id") == MG_MILKRUN and gb.mem("mg_mode") == MG_STORY and gb.mem("venue_id") == BIKER
        assert gb.mem("save_lock") == 1 and gb.mem16("mg_unlocked") == 1 << MG_MILKRUN
        assert text(gb, 2) == "MILK RUN"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_bonus_mini_games_lists_and_plays_it(model):
    """BONUS > MINI GAMES (the debug build: all unlocked): MILK RUN on the fourth line (the chapters' order), its details THE
    CHROME COW; A plays it in practice (score from 0); its result's B comes back to the list on it."""
    from test_mg_list import line, tap as list_tap, to_list
    from test_scores import booted
    with to_list(booted(model)) as gb:
        assert line(gb, 5).strip() == "MILK RUN"
        for _ in range(3):
            list_tap(gb, "down")
        assert gb.mem("ml_sel") == 3
        assert [line(gb, r).strip() for r in range(13, 17)] == ["MILK RUN", "THE CHROME COW", "NO MEDAL YET", "A PLAY  B BACK"]
        list_tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_MINI and gb.pb.memory[0xFF40] & 0x80, 30)
        assert gb.mem("mg_id") == MG_MILKRUN and gb.mem("mg_mode") == MG_PRACTICE and score(gb) == 0
        assert text(gb, 2) == "MILK RUN"
        gb.write("mg_phase", MG_RESULT)
        run_until(gb, lambda: gb.mem("overlay_on") == 1, 10)
        frames(gb, 3)
        gb.press("b", 2)
        run_until(gb, lambda: state(gb) == GS_MGLIST and gb.pb.memory[0xFF40] & 0x80, 30)
        gb.run(3)
        assert gb.mem("ml_sel") == 3 and line(gb, 5).strip() == "MILK RUN"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_release_list_unlocks_it_when_reached(model, release_built):
    from test_mg_list import MG_PLANNED, line, pr_block, release_rom, tap as list_tap, to_list, with_block
    from test_scores import v7_image
    best = [0] * MG_PLANNED
    best[MG_MILKRUN] = MEDAL_SILVER
    ram = with_block(v7_image(), pr_block(1 << MG_MILKRUN, best))
    with release_rom(model, ram) as gb:
        to_list(gb)
        assert [line(gb, r).strip() for r in (2, 3, 4)] == ["? ? ?"] * 3 and line(gb, 5) == " MILK RUN     SILVER"
        for _ in range(3):
            list_tap(gb, "down")
        assert [line(gb, r).strip() for r in range(13, 16)] == ["MILK RUN", "THE CHROME COW", "BEST SILVER"]
        list_tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_MINI, 30)
        assert gb.mem("mg_id") == MG_MILKRUN and gb.mem("mg_mode") == MG_PRACTICE


# ---- goldens: riding, a toss, a crash, the result -----------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_goldens(model):
    """The riding, toss, crash and result screens of a seeded game (the bot's, so they follow the street)."""
    with milk_run(model) as gb:
        to_play(gb)
        # riding: the first pothole and the first box in view
        ride(gb, lambda s: s["px"] >= 330, deliver=True)
        frames(gb, 1)
        shot(gb, "riding")
        check_golden(gb, "mr_riding")
        # a toss: the crate at the top of its arc over its box
        ride(gb, lambda s: any(t["t"] == 8 for t in s["toss"]), deliver=True)
        shot(gb, "toss")
        check_golden(gb, "mr_toss")
        # PERFECT: the pop over the box, 500 on the score
        ride(gb, lambda s: s["pop_t"] == POP_LEN - 12, deliver=True)
        shot(gb, "perfect")
        check_golden(gb, "mr_perfect")
        # a crash: the bike stays in its lane into the next gate that blocks it
        ride(gb, lambda s: s["inv"] == 0 and s["px"] > 900, deliver=False)
        s = mr(gb)
        gates = sorted((c, k) for c, k in zip(s["fcol"], s["fkind"]) if k & GATE)
        for _ in range(400):
            s = mr(gb)
            if s["inv"] > BLINK + 14:
                break
            frames(gb, 1)
            gates = sorted((c, k) for c, k in zip(s["fcol"], s["fkind"]) if k & GATE and c * 8 + 16 > s["px"] + 28)
            if s["y"] == lane_top(s["lane"]) and gates and not (gates[0][1] >> s["lane"]) & 1 and gates[0][0] * 8 < s["px"] + 120:
                want = [l for l in range(3) if (gates[0][1] >> l) & 1][0]
                if want != s["lane"]:
                    tap(gb, "up" if want < s["lane"] else "down", 1)
        assert mr(gb)["inv"] > BLINK
        shot(gb, "crash")
        check_golden(gb, "mr_crash")
        # the result
        poke(gb, delivered=10)
        to_result(gb)
        frames(gb, 3)
        shot(gb, "result")
        check_golden(gb, "mr_result")
