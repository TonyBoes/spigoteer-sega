# docs/minigames_bosses.md 4.10: MILK RUN (src/mr.c), The Chrome Cow's mini-game, on the framework (src/mg.c): the screen
# (the approved art, its palettes, the DMG look V1: the rider on OBP0 = 0xC0, the rest on OBP1 = 0xE0), the street that
# scrolls under the HUD (lcd_isr's raster split, mr_vbl's column writer) and follows its seed (a Python model of the
# generator), the throttle (RIGHT / LEFT held), lane changes, A / B tosses from any lane and their landing (PERFECT 500,
# delivered 300, lost), the milk-bottle pickups, bumps (wobble, 2-3 crates spilled, the speed gone, blinking), the course's
# end and the time bonus, medals by score, Practice's HARD, a bot that rides every seed without a crash and takes both
# bottles, the sprites per line on every frame, OBP0 put back when the game is left, STORY / ARCADE reaching it in
# chapter 7, BONUS > MINI GAMES.
import pytest
from conftest import ROOT, check_golden, hold_stage_anim, logic_paused, title_level
from mr_helpers import (ART, BIKER, BOTTOM, BOX, FULL, GATE, LAYOUT, MG_MILKRUN, MR_BG, MR_OBJ, NO_BOX, PICK_COLS, STATE_SIZE, Street,
                        art_define, bot, column_tiles, lane_top, mr, mr_define, next_box, next_pickup, pick_lanes, poke, px_after,
                        speed16)
from test_flow import GS_GOAL, LEVEL_CLEAR, PLAYING, TITLE, run_until, state, tilemap_row
from test_mg import (BLANK, GS_MGLIST, GS_MINI, MEDAL_PTS, MG_COUNT, MG_END, MG_HARD, MG_PLAY, MG_PRACTICE, MG_RESULT,
                     MG_STORY, RESULT_MIN, frames, hud_timer, lines, mg_enter, score, text, to_play, to_result, until)
from test_mg_list import release_built  # noqa: F401  (the fixture: `make release`)

pytestmark = pytest.mark.timeout(300)

MEDAL_NONE, MEDAL_BRONZE, MEDAL_SILVER, MEDAL_GOLD = range(4)
SFX_LAUNCH, SFX_SERVE, SFX_COIN, SFX_BREAK = 2, 5, 6, 4
(TIME_S, CRATES, FLIGHT, PTS_DELIVERED, PTS_PERFECT, PTS_CRATE, WOBBLE, BLINK, POP_LEN, BANNER_OFF, PICK_CRATES, SPD_MIN, SPD_START,
 SPD_MAX, SPD_FAST, DROP, DROP_FAST, HARD_START, HARD_MIN, PTS_SEC, LOST_GAP, GOLD, SILVER, BRONZE) = (mr_define(n) for n in (
    "MR_TIME_S", "MR_CRATES", "MR_FLIGHT", "MR_PTS_DELIVERED", "MR_PTS_PERFECT", "MR_PTS_CRATE", "MR_WOBBLE", "MR_BLINK",
    "MR_POP_LEN", "MR_BANNER_OFF", "MR_PICK_CRATES", "MR_SPD_MIN", "MR_SPD_START", "MR_SPD_MAX", "MR_SPD_FAST", "MR_DROP",
    "MR_DROP_FAST", "MR_HARD_SPD_START", "MR_HARD_SPD_MIN", "MR_PTS_SEC", "MR_LOST_GAP", "MR_MEDAL_GOLD", "MR_MEDAL_SILVER",
    "MR_MEDAL_BRONZE"))
OAM_BIKE, OAM_RIDER, OAM_STARS, OAM_CRATE, OAM_LOST, OAM_POP, OAM_PICK = (mr_define(n) for n in (
    "OAM_BIKE", "OAM_RIDER", "OAM_STARS", "OAM_CRATE", "OAM_LOST", "OAM_POP", "OAM_PICK"))
GAUGE_COL = mr_define("GAUGE_COL")
SEED = 0x5A17
S_PALETTE = 0x10
OUT = ROOT / "out" / "mr"
OBJ_ENTRY = {name: art_define(f"MRO_{name}") for name in ("RIDER_A", "RIDER_B", "RIDER_W", "CRATE_LO", "CRATE_HI",
                                                           "STARS", "POP_L", "POP_R", "BOTTLE")}
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


def ride(gb, stop, limit=3000, worst=None, deliver=True, hook=None, target=None, collect=True):
    """The bot rides (a lane change it needs, a toss when one is due, RIGHT / LEFT held toward the speed `target` if given)
    frame by frame until stop(state); returns the state."""
    for _ in range(limit):
        s = snap(gb)
        if stop(s):
            return s
        want, toss = bot(s, deliver, collect)
        keys = []
        if want is not None and s["y"] == lane_top(s["lane"]) and want != s["lane"]:
            keys.append("up" if want < s["lane"] else "down")
        if toss:
            keys.append(toss)
        if target is not None and s["inv"] <= BLINK:
            if s["spd"] < target:
                keys.append("right")
            elif s["spd"] > target:
                keys.append("left")
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


def run_clear(gb, n):
    """n frames with no gate or box on the street (a long stretch of the logic's tests: the bike is not to meet what streams in)."""
    for _ in range(n):
        clear_ring(gb)
        frames(gb, 1)


def put_bike(gb, lane):
    poke(gb, lane=lane, y=lane_top(lane))


# ---- the screen ------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_screen_and_its_art(model):
    """The intro: the banner, the HUD (score, the crate icon and 12, the hourglass and 45), the street's first 21 columns as the model builds
    them, the tiles and palettes of the approved art, the sprites (bike entries, the rider), the DMG registers."""
    with milk_run(model) as gb:
        assert gb.mem("mg_id") == MG_MILKRUN and gb.mem("mg_mode") == MG_PRACTICE and gb.mem("mg_phase") == 0
        frames(gb, 30)
        assert text(gb, 2) == "MILK RUN" and text(gb, 3) == "A TOSSES UP B DOWN"
        assert hud_timer(gb) == "70" and score(gb) == 0 and gb.mem16("mg_timer") == 0
        assert tilemap_row(gb, 0, 10, 4) == [BLANK, MR_BG + art_define("MRB_HUDC"), 36 + 1, 36 + 0]   # "10" (glyph 0 is 36)
        g0 = MR_BG + art_define("MRB_GAUGE")
        assert tilemap_row(gb, 0, GAUGE_COL, 2) == [g0 + 2, g0 + 0], "the speed gauge at 1.5 px: one cell full, one empty"
        s = mr(gb)
        assert (s["crates"], s["lane"], s["y"], s["px"], s["spd"], s["time"]) == (CRATES, 1, 64, 0, SPD_START, TIME_S * 60)
        assert s["pk_lane"] == list(pick_lanes(SEED)) and s["pk_got"] == 0
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
        for p, pc in enumerate(PICK_COLS):             # no gate near a bottle blocks its lane: a way to it always exists
            for gc, gk in gates:
                if gc + mr_define("MR_PICK_BEFORE") >= pc and gc <= pc + mr_define("MR_PICK_AFTER"):
                    assert not (gk >> st.pk_lane[p]) & 1, (seed, p, gc)
        assert st.pk_lane[0] != st.pk_lane[1]


# ---- driving: the scroll, the lanes --------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_right_speeds_up_left_slows_down_and_letting_go_keeps_the_speed(model):
    """The street's speed is the player's: RIGHT held +1/16 px every 2nd frame up to 2.5 px (40), LEFT held -1/16 down to 1.0 (16);
    no key: it stays; the scroll is the speed (px_after), and the HUD gauge follows."""
    with milk_run(model) as gb:
        to_riding(gb)
        put_bike(gb, 1)
        clear_ring(gb)
        s0 = settle(gb)
        assert s0["spd"] == SPD_START == 24
        run_clear(gb, 60)
        s1 = settle(gb)
        assert s1["spd"] == 24, "no key: the speed stays"
        n = (s1["anim"] - s0["anim"]) & 255                  # (game frames: PyBoy's frame can fall between two of the game's)
        assert s1["px"] == px_after(s0, n) and abs(s1["px"] - s0["px"] - 90 * n // 60) <= 2, "1.5 px a frame"
        gb.hold("right")
        a0 = snap(gb)
        run_clear(gb, 20)
        a1 = snap(gb)
        gained = a1["spd"] - a0["spd"]
        assert gained == ((a1["anim"] - a0["anim"]) & 255) // 2 or abs(gained - ((a1["anim"] - a0["anim"]) & 255) // 2) <= 1, "+1 every 2nd frame"
        run_clear(gb, 60)
        assert snap(gb)["spd"] == SPD_MAX == 40, "2.5 px is the top"
        assert tilemap_row(gb, 0, GAUGE_COL, 2) == [MR_BG + art_define("MRB_GAUGE") + 2] * 2, "both cells full"
        gb.release("right")
        run_clear(gb, 30)
        assert snap(gb)["spd"] == 40, "let go: it keeps its speed"
        s2 = settle(gb)
        run_clear(gb, 60)
        s3 = settle(gb)
        n = (s3["anim"] - s2["anim"]) & 255
        assert abs(s3["px"] - s2["px"] - 150 * n // 60) <= 2, "2.5 px a frame"
        gb.hold("left")
        run_clear(gb, 100)
        assert snap(gb)["spd"] == SPD_MIN == 16, "1.0 px is the floor"
        assert tilemap_row(gb, 0, GAUGE_COL, 2) == [MR_BG + art_define("MRB_GAUGE")] * 2, "both cells empty"
        gb.release("left")
        run_clear(gb, 2)
        s4 = settle(gb)
        run_clear(gb, 60)
        s5 = settle(gb)
        n = (s5["anim"] - s4["anim"]) & 255
        assert s5["px"] == px_after(s4, n) and abs(s5["px"] - s4["px"] - n) <= 2, "1.0 px a frame"


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
def test_a_tosses_up_b_tosses_down_from_any_lane_16_frames_and_costs_a_crate(model):
    with milk_run(model) as gb:
        to_riding(gb)
        clear_ring(gb)
        for lane, key, side in ((1, "a", 0), (1, "b", 1), (0, "b", 1), (2, "a", 0)):
            put_bike(gb, lane)
            frames(gb, 2)
            c0 = snap(gb)["crates"]
            gb.hold(key)
            frames(gb, 2)
            gb.release(key)
            s = snap(gb)
            t = [x for x in s["toss"] if x["t"]]
            assert s["crates"] == c0 - 1 and len(t) == 1 and 1 <= t[0]["t"] <= 3 and t[0]["side"] == side, (lane, key)
            assert gb.mem("last_sfx") == SFX_LAUNCH
            frames(gb, 20)
            assert not any(x["t"] for x in snap(gb)["toss"])
        put_bike(gb, 1)
        frames(gb, 2)
        c0 = snap(gb)["crates"]
        gb.hold("a")
        gb.hold("b")
        frames(gb, 2)
        gb.release("a")
        gb.release("b")
        s = snap(gb)
        assert s["crates"] == c0 - 1 and [x["side"] for x in s["toss"] if x["t"]] == [0], "A and B together: A"
        frames(gb, 20)
        put_bike(gb, 0)
        frames(gb, 2)
        tap(gb, "a")
        c = snap(gb)["crates"]
        assert tilemap_row(gb, 0, 12, 2) == [36 + c // 10, 36 + c % 10], "the HUD counts"
        frames(gb, 20)
        # the flight of a toss up from the top lane: the crate climbs to the top kerb's box
        put_bike(gb, 0)
        frames(gb, 2)
        tap(gb, "a", 2)
        ys, last = [], 0
        for _ in range(20):
            s = snap(gb)
            t = s["toss"][0]["t"] or s["toss"][1]["t"]
            if t == 0:
                break
            slot = 0 if s["toss"][0]["t"] else 1
            t = s["toss"][slot]["t"]
            assert t >= last
            if t != last:
                o = oam(gb, OAM_CRATE + slot)
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
            tap(gb, "b", 2)
        s = snap(gb)
        assert sum(1 for t in s["toss"] if t["t"]) == 2 and s["crates"] == c0 - 2
        # a toss down: the crate goes to the bottom kerb
        frames(gb, 30)
        put_bike(gb, 0)
        frames(gb, 18)
        tap(gb, "b", 2)
        s = snap(gb)
        assert [t["side"] for t in s["toss"] if t["t"]] == [1]
        ys = []
        for _ in range(16):
            frames(gb, 1)
            if snap(gb)["toss"][0]["t"]:
                ys.append(oam(gb, OAM_CRATE)["y"] - 16)
        assert ys[-1] >= 80 and ys == sorted(ys), "it falls to the bottom kerb's box"
        # no crates, no toss
        poke(gb, crates=0)
        frames(gb, 20)
        tap(gb, "a", 2)
        tap(gb, "b", 2)
        assert not any(t["t"] for t in snap(gb)["toss"]), "nothing to throw"


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


def pickup_at(gb, k, lane, ahead_px):
    """Pickup k in `lane`, its left edge `ahead_px` right of the bike's hit box (the scroll is poked; nothing else on the street)."""
    clear_ring(gb)
    px = PICK_COLS[k] * 8 - (28 + ahead_px)
    poke(gb, px=px, frac=0, pk_got=0)
    a = gb.addr("story_scratch") + LAYOUT["pk_lane"][0] + k
    with logic_paused(gb):
        gb.write(a, lane)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_bump_spills_two_crates_three_when_fast_takes_the_speed_and_wobbles(model):
    with milk_run(model) as gb:
        to_riding(gb)
        put_bike(gb, 0)
        frames(gb, 14)
        poke(gb, spd=SPD_FAST - 4)
        # a gate in lane 2 / 3 does not touch a bike in lane 1
        put_gate(gb, 0b110)
        frames(gb, 2)
        assert mr(gb)["inv"] == 0 and mr(gb)["crates"] == CRATES
        put_gate(gb, 0b001)
        frames(gb, 1)
        s = settle(gb)
        assert s["inv"] >= WOBBLE + BLINK - 2 and s["crates"] == CRATES - DROP and s["lost_n"] == DROP, "2 crates below 2.0 px"
        assert s["spd"] == SPD_MIN, "the bump takes the speed away"
        assert s["lost_t"] > 0 and gb.mem("last_sfx") == SFX_BREAK
        c = CRATES - DROP
        assert tilemap_row(gb, 0, 12, 2) == [36 + c // 10, 36 + c % 10], "the HUD shows 8"
        # the wobble: frame 3 of the bike, the rider 1 px left, two stars; no tosses
        o = [oam(gb, OAM_BIKE + k) for k in range(3)]
        assert [x["tile"] for x in o] == [MR_OBJ + BIKE_T[6 + k] for k in range(3)]
        assert oam(gb, OAM_RIDER)["x"] == 24 + 5 + 8 and oam(gb, OAM_RIDER)["tile"] == MR_OBJ + OBJ_ENTRY["RIDER_W"]
        st1, st2 = oam(gb, OAM_STARS), oam(gb, OAM_STARS + 1)
        assert st1["tile"] == st2["tile"] == MR_OBJ + OBJ_ENTRY["STARS"] and not st1["prop"] & 0x20 and st2["prop"] & 0x20
        assert (st1["x"], st1["y"] - 16) == (24 + 6 + 8, 48 - 10) and (st2["x"], st2["y"] - 16) == (24 + 14 + 8, 48 - 6)
        # the crates tumble out one after another and lie on the street, left behind with it
        frames(gb, 8)
        assert oam(gb, OAM_LOST)["y"] != 0 and oam(gb, OAM_LOST)["tile"] in (MR_OBJ + OBJ_ENTRY["CRATE_LO"], MR_OBJ + OBJ_ENTRY["CRATE_HI"])
        assert oam(gb, OAM_LOST + 1)["y"] != 0, "the second is out by now"
        assert oam(gb, OAM_LOST + 2)["y"] == 0, "and the third is not (only 2 spilled)"
        c0 = mr(gb)["crates"]
        tap(gb, "a")
        tap(gb, "b")
        assert mr(gb)["crates"] == c0 and not any(t["t"] for t in mr(gb)["toss"]), "no tosses in a wobble"
        # the throttle is dead in a wobble
        gb.hold("right")
        frames(gb, 12)
        assert mr(gb)["spd"] == SPD_MIN and mr(gb)["inv"] > BLINK, "RIGHT does nothing in the wobble"
        # invulnerable: another gate does nothing
        put_gate(gb, 0b001)
        frames(gb, 3)
        assert mr(gb)["crates"] == c0
        until(gb, lambda: mr(gb)["inv"] <= BLINK, 40)
        frames(gb, 6)
        assert mr(gb)["spd"] > SPD_MIN, "after the wobble RIGHT speeds up again"
        gb.release("right")
        until(gb, lambda: not mr(gb)["inv"], 70)
        frames(gb, 1)
        # a bump at 2.0 px or faster spills 3
        put_bike(gb, 0)
        frames(gb, 14)
        clear_ring(gb)
        poke(gb, spd=SPD_FAST, lost_t=0)
        c0 = mr(gb)["crates"]
        put_gate(gb, 0b001)
        frames(gb, 2)
        s = mr(gb)
        assert s["crates"] == c0 - DROP_FAST and s["lost_n"] == DROP_FAST and s["spd"] == SPD_MIN
        frames(gb, 7)
        assert all(oam(gb, OAM_LOST + k)["y"] != 0 for k in range(2)) and oam(gb, OAM_LOST + 2)["y"] == 0, "the third follows 6 frames after the second"
        frames(gb, LOST_GAP)
        assert all(oam(gb, OAM_LOST + k)["y"] != 0 for k in (1, 2)), "the third is out too"
        # with fewer crates than the bump spills it spills what is left
        until(gb, lambda: not mr(gb)["inv"], 100)
        clear_ring(gb)
        poke(gb, crates=1, spd=SPD_MAX)
        put_gate(gb, 0b001)
        frames(gb, 2)
        s = mr(gb)
        assert s["crates"] == 0 and s["lost_n"] == 1
        poke(gb, inv=0)
        put_gate(gb, 0b001)
        frames(gb, 2)
        s = mr(gb)
        assert s["crates"] == 0 and s["lost_n"] == 0 and s["inv"] > 0 and s["spd"] == SPD_MIN, "a bump with nothing to drop still slows"
        # the blink after the wobble
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


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_milk_bottle_in_the_road_is_picked_up_for_three_crates(model):
    with milk_run(model) as gb:
        to_riding(gb)
        put_bike(gb, 1)
        pickup_at(gb, 0, 0, 70)                     # in the top lane, 70 px ahead of the bike
        frames(gb, 2)
        o = oam(gb, OAM_PICK)
        assert o["y"] != 0 and o["tile"] == MR_OBJ + OBJ_ENTRY["BOTTLE"] and o["prop"] & S_PALETTE
        assert o["y"] - 16 in (lane_top(0), lane_top(0) - 2), "standing (bobbing 2 px) in its lane"
        assert abs(o["x"] - 8 - (PICK_COLS[0] * 8 - snap(gb)["px"])) <= 3
        ys = set()
        for _ in range(24):
            frames(gb, 1)
            ys.add(oam(gb, OAM_PICK)["y"])
        assert len(ys) == 2, "the bottle bobs"
        c0 = snap(gb)["crates"]
        frames(gb, 40)                               # (the bike is in lane 2: it passes the bottle in the top lane)
        s = snap(gb)
        assert s["crates"] == c0 and s["pk_got"] == 0, "the middle lane misses a bottle in the top lane"
        pickup_at(gb, 0, 1, 30)
        poke(gb, spd=24)
        a = gb.mem16("mg_score")
        until(gb, lambda: snap(gb)["pk_got"] == 1, 60)
        s = snap(gb)
        assert s["crates"] == c0 + PICK_CRATES and gb.mem("last_sfx") == SFX_COIN
        assert tilemap_row(gb, 0, 12, 2) == [36 + s["crates"] // 10, 36 + s["crates"] % 10], "the HUD shows 13"
        frames(gb, 2)
        assert oam(gb, OAM_PICK)["y"] == 0, "the bottle is gone"
        assert gb.mem16("mg_score") == a, "(crates, not points)"
        # the second bottle is the other pickup; both in the same game
        pickup_at(gb, 1, 2, 20)
        poke(gb, pk_got=1)
        put_bike(gb, 2)
        until(gb, lambda: snap(gb)["pk_got"] == 3, 60)
        assert snap(gb)["crates"] == c0 + 2 * PICK_CRATES
        # a bike changing lane over a bottle still gets it (the hit box is 12 tall, a lane 16)
        pickup_at(gb, 0, 0, 10)
        put_bike(gb, 1)
        gb.hold("up")
        frames(gb, 2)
        gb.release("up")
        until(gb, lambda: snap(gb)["pk_got"] & 1, 40)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_bottle_is_visible_early_enough_to_steer_for(model):
    """It appears at the right screen edge: at 2.5 px a frame that is 64 frames before the bike reaches it (a lane change is 8)."""
    with milk_run(model) as gb:
        to_riding(gb)
        pickup_at(gb, 0, 0, 160 - 28 - 4)           # just inside the right edge (left edge at screen x 156)
        poke(gb, spd=SPD_MAX)
        frames(gb, 2)
        assert oam(gb, OAM_PICK)["y"] != 0
        s = snap(gb)
        d = PICK_COLS[0] * 8 - (s["px"] + 28)
        assert d / (SPD_MAX / 16) >= 40, "at the top speed there are 40+ frames to steer"
        pickup_at(gb, 0, 0, 160 - 28 + 40)
        frames(gb, 2)
        assert oam(gb, OAM_PICK)["y"] == 0, "not drawn before it is within the screen"


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
        poke(gb, crates=5, time=3, spd=SPD_MAX)
        until(gb, lambda: gb.mem("mg_phase") == MG_END, 10)
        frames(gb, 3)
        assert gb.mem16("mg_score") == 5 * PTS_CRATE and score(gb) == 5 * PTS_CRATE, "no seconds left: no time bonus"
        assert gb.mem("overlay_on") == 1 and text(gb, 1, True) == "TIME UP"
        assert mr(gb)["st"] == 1 and mr(gb)["done"] == 0
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
        assert hud_timer(gb) == "00"
        assert gb.mem(0xFF45) in (7, 64 + 46, 144), "LYC walks lcd_isr's chain"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_course_ends_when_the_last_box_is_out_of_reach_and_the_seconds_left_pay(model):
    """The 12th box made and no box left within reach of a crate: ROUTE DONE, 20 points a whole second left on top of 100 a crate;
    not before (a box still ahead, or a crate in the air)."""
    with milk_run(model) as gb:
        to_riding(gb)
        clear_ring(gb)
        poke(gb, boxes_made=MR_BOXES_N, bcol=NO_BOX, crates=4, time=25 * 60 + 30, spd=SPD_MAX)
        # a box still ahead of the bike: not done
        slot = free_slot(mr(gb))
        poke(gb, fcol=(slot, (snap(gb)["px"] + 34) // 8 + 6), fkind=(slot, BOX))
        frames(gb, 5)
        assert snap(gb)["done"] == 0 and gb.mem("mg_phase") == MG_PLAY
        poke(gb, fkind=(slot, 0))
        a = gb.addr("story_scratch")
        from mr_helpers import TOSS_AT
        with logic_paused(gb):
            gb.write(a + TOSS_AT, 5)                  # a crate in the air: not yet
        frames(gb, 1)
        assert snap(gb)["done"] == 0
        with logic_paused(gb):
            gb.write(a + TOSS_AT, 0)
        until(gb, lambda: gb.mem("mg_phase") == MG_END, 10)
        frames(gb, 3)
        s = mr(gb)
        left = (25 * 60 + 30 - 5 - 3) // 60          # the clock ran a few more frames: still 25 whole seconds
        assert s["done"] == 1 and left == 25
        assert gb.mem16("mg_score") == 4 * PTS_CRATE + 25 * PTS_SEC, gb.mem16("mg_score")
        assert gb.mem("overlay_on") == 1 and text(gb, 1, True) == "ROUTE DONE"


MR_BOXES_N = mr_define("MR_BOXES")


def deliveries(gb, n, perfect=0):
    poke(gb, delivered=n, perfect=perfect)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("pts,medal", [(0, MEDAL_NONE), (BRONZE - 1, MEDAL_NONE), (BRONZE, MEDAL_BRONZE), (SILVER - 1, MEDAL_BRONZE),
                                       (SILVER, MEDAL_SILVER), (GOLD - 1, MEDAL_SILVER), (GOLD, MEDAL_GOLD), (7000, MEDAL_GOLD)])
def test_the_medal_is_by_the_score(model, pts, medal):
    with milk_run(model) as gb:
        to_riding(gb)
        frames(gb, 2)
        to_result(gb, pts)
        assert gb.mem("mg_medal") == medal
        assert score(gb) == MEDAL_PTS[medal]
        assert text(gb, 3, True, x0=4) == ["NO MEDAL", "BRONZE 500", "SILVER 1500", "GOLD 3000"][medal]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_practice_hard_plays_as_normal_for_now(model):
    """Owner 2026-10-15: every difficulty plays the same until the playtest notes come, so HARD is NORMAL (src/mr.c MR_IS_HARD 0; the
    HARD constants stay in the source): it starts at 1.5 px, LEFT stops at the 1.0 floor, a bump slow spills 2."""
    assert HARD_START == 32 and HARD_MIN == 28, "the HARD constants are kept for later"
    for mode in (MG_PRACTICE | MG_HARD, MG_PRACTICE | 4):
        with milk_run(model, mode) as gb:
            to_riding(gb)
            assert mr(gb)["spd"] == SPD_START == 24
            clear_ring(gb)
            gb.hold("left")
            frames(gb, 60)
            gb.release("left")
            assert snap(gb)["spd"] == SPD_MIN == 16, "LEFT stops at 1.0 in every mode"
            put_bike(gb, 0)
            frames(gb, 14)
            poke(gb, inv=0, spd=SPD_MIN)
            c0 = mr(gb)["crates"]
            put_gate(gb, 0b001)
            frames(gb, 2)
            assert mr(gb)["crates"] == c0 - DROP and mr(gb)["lost_n"] == DROP, "a slow bump spills 2, not 3"
    with milk_run(model) as gb:
        to_riding(gb)
        assert mr(gb)["spd"] == SPD_START, "a normal practice starts at 1.5"
        clear_ring(gb)
        poke(gb, spd=SPD_FAST - 4)
        put_bike(gb, 0)
        frames(gb, 14)
        c0 = mr(gb)["crates"]
        put_gate(gb, 0b001)
        frames(gb, 2)
        assert mr(gb)["crates"] == c0 - DROP


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_hud_counts_crates_and_seconds(model):
    """Score, the crates left (icon + 2 digits at columns 11-13), the hourglass and seconds from 70 (the framework's format, own timer)."""
    with milk_run(model) as gb:
        to_riding(gb)
        clear_ring(gb)
        assert hud_timer(gb) == "70"
        put_bike(gb, 0)
        frames(gb, 14)
        for n in range(3):
            tap(gb, "a" if n % 2 == 0 else "b", 2)
            frames(gb, 20)
            crates = snap(gb)["crates"]
            assert crates == CRATES - 1 - n
            assert tilemap_row(gb, 0, 12, 2) == [36 + crates // 10, 36 + crates % 10]
            assert tilemap_row(gb, 0, 11, 1) == [MR_BG + art_define("MRB_HUDC")]
        poke(gb, time=60 * 30 + 59)
        frames(gb, 3)
        assert hud_timer(gb) == "31"
        poke(gb, time=60 * 9 + 5)
        frames(gb, 3)
        assert hud_timer(gb) == "10"
        poke(gb, time=61)
        frames(gb, 3)
        assert hud_timer(gb) == "01"
        until(gb, lambda: gb.mem("mg_phase") == MG_END, 80)
        assert hud_timer(gb) == "00"


# ---- sprites per line, a whole game ------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_whole_game_keeps_to_10_sprites_a_line(model):
    """The bot plays a whole game from the intro to the result, delivering, with a bump dropped in with two crates in the air
    and a PERFECT pop showing: never more than 10 sprites on a line (the design's worst is 10)."""
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
                tap(g, "b", 1)                      # two crates in the air (the bot's own tosses aside)
                put_gate(g, 0b001)
                poke(g, pop_t=POP_LEN)

        ride(gb, lambda s: gb.mem("mg_phase") != MG_PLAY, limit=6000, worst=worst, hook=crash_now, target=SPD_MAX)
        assert done
        until(gb, lambda: gb.mem("mg_phase") == MG_RESULT, 80)
        assert worst[0] <= 10, worst
        assert worst[0] >= 5, "(the crash scene was seen)"
        print("worst sprites on a line:", worst[0])


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("fast", [False, True])
def test_the_worst_case_scene_is_10_a_line_at_most(model, fast):
    """Everything at once on the bike's lines: its 4 entries, the stars, two crates in the air, the crates the bump spills (they come
    out 6 frames apart, so the air ones have landed before the third) and a milk bottle standing in the bike's own lane: never over 10."""
    with milk_run(model) as gb:
        to_riding(gb)
        put_bike(gb, 2)
        frames(gb, 18)
        pickup_at(gb, 0, 2, 120)                    # a bottle in the bike's lane, on the screen
        poke(gb, spd=SPD_MAX if fast else 24)
        tap(gb, "a", 2)
        tap(gb, "b", 2)
        put_gate(gb, 0b100)
        worst = [0]
        frames(gb, 3, worst)
        s = mr(gb)
        assert sum(1 for t in s["toss"] if t["t"]) == 2 and s["inv"] > BLINK and s["lost_t"] and s["lost_n"] >= 2
        frames(gb, 40, worst)
        assert 8 <= worst[0] <= 10, worst
        print("worst sprites on a line:", worst[0])


# ---- the bot: a clean run exists at every seed ------------------------------------------------------------------------------------------
@pytest.mark.parametrize("seed", [SEED, 0x1234, 0xBEEF, 0x2468])
@pytest.mark.parametrize("target", [SPD_MAX, SPD_START])
def test_the_bot_rides_a_whole_game_without_a_bump_takes_both_bottles_and_finishes(seed, target):
    with milk_run("cgb", seed=seed) as gb:
        to_play(gb)
        crashes = []
        last = [0]

        def watch(g):
            inv = mr(g)["inv"]
            if inv > last[0]:
                crashes.append(mr(g)["px"])
            last[0] = inv

        ride(gb, lambda s: gb.mem("mg_phase") != MG_PLAY, limit=7000, hook=watch, target=target)
        s = mr(gb)
        assert crashes == [] and s["pk_got"] == 3, (crashes, s["pk_got"])
        assert s["done"] == 1, "the course was done before the clock"
        assert s["delivered"] >= 10 and s["perfect"] == s["delivered"], s
        assert s["spd"] == target
        print("seed", hex(seed), "speed", target, "delivered", s["delivered"], "score", gb.mem16("mg_score"), "secs left", s["time"] // 60)


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
        run_until(gb, lambda: state(gb) == GS_MINI, 800)
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
        ride(gb, lambda s: s["delivered"] >= 1, limit=1800)
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
    run_until(gb, lambda: state(gb) == GS_MINI, 800)
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
        run_until(gb, lambda: state(gb) == GS_MINI, 800)
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
        run_until(gb, lambda: state(gb) == GS_MINI, 800)
        run_until(gb, lambda: gb.pb.memory[0xFF40] & 0x80, 10)
        assert gb.mem("mg_id") == MG_MILKRUN and gb.mem("mg_mode") == MG_STORY and gb.mem("venue_id") == BIKER
        assert gb.mem("save_lock") == 1 and gb.mem16("mg_unlocked") == 1 << MG_MILKRUN
        assert text(gb, 2) == "MILK RUN"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_bonus_mini_games_lists_and_plays_it(model):
    """BONUS > MINI GAMES (the debug build: all unlocked): MILK RUN on the seventh line (chapter order), its details THE
    CHROME COW; A plays it in practice (score from 0); its result's B comes back to the list on it."""
    from test_mg_list import line, tap as list_tap, to_list
    from test_scores import booted
    with to_list(booted(model)) as gb:
        for _ in range(6):
            list_tap(gb, "down")
        assert gb.mem("ml_sel") == 6
        assert line(gb, 15).strip() == "NORMAL NO MEDAL YET"
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
        assert gb.mem("ml_sel") == 6 and line(gb, 12).strip() == "MILK RUN"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_release_list_unlocks_it_when_reached(model, release_built):
    from test_mg_list import MG_PLANNED, line, pr_block, release_rom, tap as list_tap, to_list, with_block
    from test_scores import v7_image
    best = [0] * MG_PLANNED
    best[MG_MILKRUN] = MEDAL_SILVER
    ram = with_block(v7_image(), pr_block(1 << MG_MILKRUN, best))
    with release_rom(model, ram) as gb:
        to_list(gb)
        assert [line(gb, r).strip() for r in range(2, 13, 2)] == ["? ? ?"] * 6
        for _ in range(6):
            list_tap(gb, "down")
        assert line(gb, 12) == " MILK RUN     SILVER"
        assert line(gb, 15).strip() == "NORMAL BEST SILVER"
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
        ride(gb, lambda s: s["inv"] == 0 and s["px"] > 900, deliver=False, collect=False)
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
        to_result(gb, GOLD)
        frames(gb, 3)
        shot(gb, "result")
        check_golden(gb, "mr_result")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_goldens_the_bottle_ahead_and_the_bump(model):
    """A milk bottle standing in the top lane ahead of the bike (mr_pickup), and a bump at speed with the crates tumbling out (mr_bump)."""
    with milk_run(model) as gb:
        to_riding(gb)
        put_bike(gb, 1)
        pickup_at(gb, 0, 0, 80)
        frames(gb, 3)
        shot(gb, "pickup")
        check_golden(gb, "mr_pickup")
        clear_ring(gb)
        put_bike(gb, 0)
        frames(gb, 14)
        poke(gb, spd=SPD_MAX)
        put_gate(gb, 0b001)
        frames(gb, 14)
        assert mr(gb)["lost_n"] == DROP_FAST
        shot(gb, "bump")
        check_golden(gb, "mr_bump")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_hard_medal_is_saved_apart_from_the_normal_one(model):
    """mg_record keeps bits 0-1 for the normal best and 2-3 for HARD (the Practice list's toggle, owner Q7): a HARD silver
    leaves the normal bronze alone, a worse HARD medal later changes nothing, and the byte survives in the saved block."""
    from test_mg_list import MG_PLANNED, best, pr_block, with_block, parse_block
    from test_scores import booted, v7_image
    from test_sound import save_ram
    ram = with_block(v7_image(), pr_block(1 << MG_MILKRUN, [0] * MG_MILKRUN + [MEDAL_BRONZE]))
    with booted(model, ram) as gb:
        mg_enter(gb, MG_MILKRUN, MG_PRACTICE | MG_HARD)
        to_riding(gb)
        frames(gb, 2)
        to_result(gb, SILVER)
        assert gb.mem("mg_medal") == MEDAL_SILVER and best(gb)[MG_MILKRUN] == MEDAL_BRONZE | MEDAL_SILVER << 2
        mg_enter(gb, MG_MILKRUN, MG_PRACTICE | MG_HARD)
        to_riding(gb)
        frames(gb, 2)
        to_result(gb, BRONZE)
        assert gb.mem("mg_medal") == MEDAL_BRONZE and best(gb)[MG_MILKRUN] == MEDAL_BRONZE | MEDAL_SILVER << 2
        mg_enter(gb, MG_MILKRUN, MG_PRACTICE)
        to_riding(gb)
        frames(gb, 2)
        to_result(gb, GOLD)
        assert best(gb)[MG_MILKRUN] == MEDAL_GOLD | MEDAL_SILVER << 2, "a normal gold leaves the HARD silver"
        assert parse_block(save_ram(gb))[1][MG_MILKRUN] == MEDAL_GOLD | MEDAL_SILVER << 2, "saved in the block"
