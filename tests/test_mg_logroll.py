# docs/minigames_bosses.md 4.3: LOG ROLL (src/lr.c), the lumber lodge's mini-game, on the framework (src/mg.c): the screen (the
# approved look A, its tiles, palettes and sprites), the physics (a Python model of the lean, the push and its ramps, the
# flips and the seed), a tap's 15 px, the told flip (the bark turns 30 frames before the push), falls and the 180 frames in
# the water, scoring (100 a second on the log, 1000 with no fall), medals by seconds on the log, the outro (the partner
# topples in), the banner rows put back, the streamed bark and ripple tiles, a bot that balances a whole game, the
# sprites per line on every frame, the level after it, STORY / ARCADE in chapter 3, BONUS > MINI GAMES.
import json
import re

import pytest
from conftest import ROOT, check_golden, hold_stage_anim, logic_paused, title_level
from test_flow import GS_GOAL, LEVEL_CLEAR, PLAYING, TITLE, run_until, state, tilemap_row
from test_mg import (BLANK, GS_MGLIST, GS_MINI, MG_COUNT, MG_END, MG_GAME_BG, MG_PLAY, MG_PRACTICE, MG_RESULT, MG_STORY,
                     RESULT_MIN, frames, hud_timer, lines, mg_enter, score, text, to_play, to_result, until)

pytestmark = pytest.mark.timeout(300)

MG_LOGROLL = 2
LUMBER = 2                                       # the venue / chapter
MEDAL_NONE, MEDAL_BRONZE, MEDAL_SILVER, MEDAL_GOLD = range(4)
LS_RUN, LS_WATER, LS_OVER = range(3)
LR_C = (ROOT / "src" / "lr.c").read_text()
MG_H = (ROOT / "src" / "mg.h").read_text()
ART_H = (ROOT / "build" / "lr_art.h").read_text()
ART = json.loads((ROOT / "build" / "lr.json").read_text())
OUT = ROOT / "out" / "lr"
SEED = 0x5A17


def define(name):
    return int(re.search(rf"#define {name}\s+\(?(-?\d+)", LR_C).group(1))


def art_define(name):
    return int(re.search(rf"#define {name} (\d+)", ART_H).group(1))


(TIME_S, RAMP, FLIP_MIN, FLIP_RANGE, FALL_LEN, SPLASH_LEN, TOPPLE, DROPS, PTS_SEC, PTS_CLEAN, GOLD, SILVER, BRONZE, BAND_OFF,
 DRIFT0, ONE, FALL_PX, HOP_AT) = (define(n) for n in (
    "LR_TIME_S", "LR_RAMP_FRAMES", "LR_FLIP_MIN", "LR_FLIP_RANGE", "LR_FALL_LEN", "LR_SPLASH_LEN", "LR_TOPPLE", "LR_DROPS",
    "LR_PTS_SEC", "LR_PTS_CLEAN", "LR_GOLD", "LR_SILVER", "LR_BRONZE", "LR_BAND_OFF", "LR_DRIFT0", "LR_ONE", "LR_FALL_PX",
    "LR_HOP_AT"))
(WARN, FLY, LAND, HALF, HIT_W, CLEAR, KICK, STUN, HOP_LEN, HOP_END, FISH_FIRST, GAP0, FISH_LAST, PTS_DODGE, BASE_Y, SQ_SWIM, SQ_UP_LEN,
 SPIG_CX, SQ_CX) = (define(n) for n in (
    "LR_WARN", "LR_FLY", "LR_LAND", "LR_HALF", "LR_HIT_W", "LR_CLEAR", "LR_KICK", "LR_STUN", "LR_HOP_LEN", "LR_HOP_END",
    "LR_FISH_FIRST", "LR_GAP0", "LR_FISH_LAST", "LR_PTS_DODGE", "LR_FISH_BASE_Y", "LR_SQ_SWIM", "LR_SQ_UP_LEN", "LR_SPIG_CX", "LR_SQ_CX"))
OAM_MARK, OAM_DROPS, OAM_SPIG, OAM_SQ, OAM_FISH, OAM_RING = (define(f"OAM_{n}") for n in ("MARK", "DROPS", "SPIG", "SQ", "FISH", "RING"))
SQ_LOG, SQ_SWIM_ST, SQ_END = range(3)
LR_BG = MG_GAME_BG
LR_OBJ_HI = (LR_BG + ART["n_bg"] + 1) & ~1
SLOT = ART["slot_entries"]
S_FLIPX, S_PALETTE = 0x20, 0x10
OBJ_DANCER = 96
SFX_CATCH, SFX_BREAK, SFX_SHAKE, SFX_LAUNCH = 3, 4, 8, 2
HUD_ATTR_PAL, SQ_PAL = 1, 5


HI_A = (220 - LR_OBJ_HI) // 2                    # the entries below the HUD hourglass (BG 220); the rest start at 222


def otile(e):
    if e < SLOT:
        return 56 + 2 * e
    e -= SLOT
    return LR_OBJ_HI + 2 * e if e < HI_A else 222 + 2 * (e - HI_A)


# ---- the state in the mg union (offsets parsed from struct lr_state in src/mg.h) -------------------------------------------
def _layout():
    body = re.search(r"struct lr_state \{(.*?)\n\};", MG_H, re.S).group(1)
    out, off = {}, 0
    for line in body.splitlines():
        line = line.split("//")[0].strip()
        if not line:
            continue
        m = re.match(r"(int32_t|int16_t|uint16_t|uint8_t|int8_t)\s+(.*);", line)
        if m is None:                       # (the `struct xx_tune tn` at the end: the difficulty's tuning row, not read by the tests)
            continue
        width, signed = {"int32_t": (4, 1), "int16_t": (2, 1), "uint16_t": (2, 0), "uint8_t": (1, 0), "int8_t": (1, 1)}[m[1]]
        for decl in m[2].split(","):
            decl = decl.strip()
            n = int(re.search(r"\[(\d+)\]", decl)[1]) if "[" in decl else 1
            out[re.match(r"\w+", decl)[0]] = (off, n, width, signed)
            off += n * width
    return out, off


LAYOUT, STATE_SIZE = _layout()


def lr(gb):
    raw = bytes(gb.read(gb.addr("story_scratch"), STATE_SIZE))
    s = {}
    for name, (off, n, w, sg) in LAYOUT.items():
        vals = [int.from_bytes(raw[off + i * w:off + (i + 1) * w], "little", signed=bool(sg)) for i in range(n)]
        s[name] = vals if n > 1 else vals[0]
    s["px"] = s["lean"] / ONE
    return s


def snap(gb):
    """The state as of a whole game frame (conftest.logic_paused: a read at PyBoy's frame end can catch it half done)."""
    with logic_paused(gb):
        return lr(gb)


def game_rows(gb, n):
    """The state after each of the next n-1 whole game frames (a hook on vq_frame_end, called right after the frame's update),
    after the state now. A game that finishes its logic early in the frame can have two frames inside one PyBoy tick or none,
    so a loop of run(1) + snap cannot count game frames; this can."""
    rows = [lr(gb)]
    hook = gb.addr("vq_frame_end") & 0xFFFF
    gb.pb.hook_register(0, hook, lambda _: rows.append(lr(gb)), None)
    try:
        for _ in range(4 * n):
            if len(rows) >= n:
                break
            gb.run(1)
    finally:
        gb.pb.hook_deregister(0, hook)
    return rows[:n]


def poke(gb, **kw):
    base = gb.addr("story_scratch")
    with logic_paused(gb):
        for name, v in kw.items():
            off, n, w, sg = LAYOUT[name]
            for i, b in enumerate(int(v).to_bytes(w, "little", signed=bool(sg))):
                gb.write(base + off + i, b)


def log_roll(model, mode=MG_PRACTICE, seed=SEED):
    from test_scores import booted
    rom = booted(model)
    hold_stage_anim(rom)
    mg_enter(rom, MG_LOGROLL, mode, seed)
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


def to_playing(gb, extra=2):
    to_play(gb)
    frames(gb, extra)


def calm(gb):
    """No push at all (the ramps at 0, the next flip far off), lean and velocity 0: the physics of a tap alone."""
    poke(gb, tsgn=0, dsr=0, tell=0, fdelay=0, flip_in=65000, lean=0, vel=0, fish_in=65000, fish_t=0)
    frames(gb, 1)


def vram_bg(gb, i, n=1):
    """BG tiles LR_BG + i .. + n - 1 (ids below 128 live at 0x9000, the rest at 0x8800: not one run of addresses)."""
    return b"".join(bytes(gb.read((0x9000 + t * 16) if t < 128 else (0x8000 + t * 16), 16))
                    for t in range(LR_BG + i, LR_BG + i + n))


# ---- a Python model of the physics (the same integer arithmetic) -------------------------------------------------------------
def tdiv(a, b):
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b > 0) else -q


def ramped(m, s):
    q, r = tdiv(m, RAMP), m - RAMP * tdiv(m, RAMP)
    return q * s + tdiv(r * s, RAMP)


class Model:
    def __init__(self, seed):
        self.seed = seed or 0xACE1
        self.tsgn = 1 if self.rand() & 1 else -1
        self.tell = self.dsr = self.tsgn * RAMP
        self.fdelay = 0
        self.flip_in = FLIP_MIN + self.rand() % FLIP_RANGE
        self.lean = self.vel = self.roll = self.elapsed = self.on = self.falls = 0
        self.water = False
        self.fall_t = 0
        self.flips = []
        self.drift = ramped(self.mag(), self.dsr)

    def rand(self):
        s = self.seed
        s ^= (s << 7) & 0xFFFF
        s ^= s >> 9
        s ^= (s << 8) & 0xFFFF
        self.seed = s
        return s & 0xFF

    def mag(self):
        return DRIFT0 + (self.elapsed >> 6) * 35 + (((self.elapsed & 63) * 35) >> 6)

    def tick(self, pressed=0):
        """One play frame; pressed: -1 Left, 1 Right, 0 none."""
        if self.water:
            self.fall_t += 1
            if self.fall_t >= FALL_LEN:
                self.water, self.lean, self.vel = False, 0, 0
        self.elapsed += 1
        if self.flip_in:
            self.flip_in -= 1
            if not self.flip_in:
                self.tsgn = -self.tsgn
                self.fdelay = RAMP
                self.flip_in = FLIP_MIN + self.rand() % FLIP_RANGE
                self.flips.append(self.elapsed)
        goal = self.tsgn * RAMP
        self.tell += (self.tell < goal) - (self.tell > goal)
        if self.fdelay:
            self.fdelay -= 1
        else:
            self.dsr += (self.dsr < goal) - (self.dsr > goal)
        m = self.mag()
        self.drift = ramped(m, self.dsr)
        self.roll = (self.roll - ramped(m, self.tell)) & 0xFFFF
        if self.water:
            return
        self.vel += pressed * ONE
        self.vel += self.drift
        self.vel -= self.vel >> 4
        self.lean += self.vel
        self.on += 1
        if abs(self.lean) >> 16 > FALL_PX:
            self.water, self.fall_t, self.lean, self.vel = True, 0, 0, 0
            self.falls += 1


# ---- the screen ------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_screen_and_its_art(model):
    """The intro: the banner, the HUD (score, the falls icon and 0, the hourglass and 40), the scene's tiles and map as tools/gen_lr.py builds
    them, the CGB attributes and palettes, the sprites (marker, the Spigoteer's six entries, the Sasquatch's four), the DMG
    registers as at boot."""
    with log_roll(model) as gb:
        assert gb.mem("mg_id") == MG_LOGROLL and gb.mem("mg_mode") == MG_PRACTICE and gb.mem("mg_phase") == 0
        frames(gb, 30)
        assert text(gb, 2) == "LOG ROLL" and text(gb, 3) == "LEAN AND HOP FISH"
        assert hud_timer(gb) == "40" and score(gb) == 0 and gb.mem16("mg_timer") == TIME_S * 60
        icon = LR_BG + art_define("LRB_HUD")
        row = tilemap_row(gb, 0, 10, 2)
        assert row == [icon, 36], "the falls icon and a 0"   # glyph 0 is 36
        # the tiles of the art: resident tiles, the streamed slots at the first roll / ripple frame
        want = bytes(ART["bg"])
        assert vram_bg(gb, 0, ART["n_bg"]) == want, "BG tiles"
        # the map: rows 1 and 4-17 (rows 2-3 hold the banner)
        for r in [1] + list(range(4, 18)):
            assert tilemap_row(gb, r, 0, 20) == [LR_BG + t for t in ART["map"][(r - 1) * 20:r * 20]], f"row {r}"
        if model == "cgb":
            from test_lift import cgb_bg_palette, cgb_obj_palette
            for r in [1] + list(range(4, 18)):
                gb.write(0xFF4F, 1)
                try:
                    got = [gb.pb.memory[0x9800 + r * 32 + c] & 7 for c in range(20)]
                finally:
                    gb.write(0xFF4F, 0)
                assert got == ART["attr"][(r - 1) * 20:r * 20], f"attributes of row {r}"
            for k, pal in enumerate((2, 3, 5, 6, 7)):
                assert cgb_bg_palette(gb, pal) == ART["pal_bg"][k]
            assert cgb_obj_palette(gb, 1) == ART["pal_obj"][0] and cgb_obj_palette(gb, 2) == ART["pal_obj"][1]
        # the sprites
        mk = oam(gb, OAM_MARK)
        assert (mk["y"], mk["x"], mk["tile"]) == (120 + 16, 76 + 8, otile(art_define("LRO_MARKER")))
        for r in range(2):
            for c in range(3):
                o = oam(gb, OAM_SPIG + 3 * r + c)
                assert (o["y"], o["x"]) == (72 + 16 + 16 * r, 92 + 8 + 8 * c)
                assert o["tile"] == otile(ART["pose_e"][0][3 * r + c]) and not o["prop"] & S_FLIPX
        sq = [oam(gb, OAM_SQ + k) for k in range(4)]
        sw = 3 * snap(gb)["tsgn"]                    # the Sasquatch leans into the push (3 px), mirrored when the log rolls the other way
        xs = [52 + sw, 60 + sw] if sw > 0 else [60 + sw, 52 + sw]
        assert [(o["y"], o["x"]) for o in sq] == [(88, xs[0]), (88, xs[1]), (104, xs[0]), (104, xs[1])]
        assert all(OBJ_DANCER <= o["tile"] < OBJ_DANCER + 32 for o in sq)
        if model == "cgb":
            assert mk["prop"] & 7 == 2 and all(o["prop"] & 7 == SQ_PAL for o in sq)
        assert [oam(gb, OAM_DROPS + k)["y"] for k in range(4)] == [0] * 4, "no droplets yet"
        # the sprites' tile data (the first SLOT entries in 56.., the rest above the BG tiles)
        obj = bytes(ART["obj"])
        assert bytes(gb.read(0x8000 + 56 * 16, 2 * SLOT * 16)) == obj[:2 * SLOT * 16]
        hi = obj[2 * SLOT * 16:]
        assert bytes(gb.read(0x8000 + LR_OBJ_HI * 16, HI_A * 32)) == hi[:HI_A * 32]
        assert bytes(gb.read(0x8000 + 222 * 16, (ART["n_ent"] - SLOT - HI_A) * 32)) == hi[HI_A * 32:]
        if model == "dmg":
            assert gb.mem(0xFF47) == 0xE4 and gb.mem(0xFF48) == 0xD0, "the level's BGP, the boot's OBP0"


# ---- the physics -----------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("key,sign", [("right", 1), ("left", -1)])
def test_one_tap_moves_the_lean_about_15_px_and_a_hold_adds_nothing(model, key, sign):
    """Without the push: a press of Right / Left is vel +- 1.0 px a frame, damped by 1/16 a frame: the lean settles 15 px (the
    spec's "about 16") away; holding the key for 40 frames moves it no further than one press."""
    with log_roll(model) as gb:
        to_playing(gb)
        calm(gb)
        tap(gb, key)
        frames(gb, 200)
        s = snap(gb)
        assert sign * 14.5 <= s["px"] * 1 <= sign * 15.5 or sign * 15.5 <= s["px"] <= sign * 14.5, s["px"]
        calm(gb)
        gb.hold(key)
        frames(gb, 40)
        gb.release(key)
        frames(gb, 200)
        assert abs(abs(snap(gb)["px"]) - 15) < 0.5, "a hold is one press"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_two_quick_taps_over_correct_and_both_keys_cancel(model):
    with log_roll(model) as gb:
        to_playing(gb)
        calm(gb)
        tap(gb, "right")
        tap(gb, "right")
        frames(gb, 200)
        assert snap(gb)["px"] > 25, "two taps go twice as far: the dose is the skill"
        calm(gb)
        gb.hold("left")
        gb.hold("right")
        frames(gb, 2)
        gb.release("left")
        gb.release("right")
        frames(gb, 200)
        assert abs(snap(gb)["px"]) < 1.0, "both pressed in one frame cancel"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_physics_follow_the_model_through_flips_and_falls(model):
    """With no input: the lean, velocity, push, the bark's phase, the next flip, the ramps, the falls and the time on the log
    as the model computes them from the seed, at eleven points over 1500 frames (several flips told, two or three falls)."""
    with log_roll(model) as gb:
        to_play(gb)
        poke(gb, fish_in=65000)                      # (the fish are tested below: here the physics alone)
        seen_falls = set()
        for target in (40, 130, 200, 260, 400, 560, 700, 900, 1100, 1300, 1500):
            while snap(gb)["elapsed"] < target:
                frames(gb, 1)
            s = snap(gb)
            mm = Model(SEED)
            for _ in range(s["elapsed"]):
                mm.tick()
            assert (s["lean"], s["vel"], s["drift"], s["roll"], s["flip_in"], s["tsgn"], s["tell"], s["dsr"], s["on"], s["falls"],
                    s["st"]) == (mm.lean, mm.vel, mm.drift, mm.roll, mm.flip_in, mm.tsgn, mm.tell, mm.dsr, mm.on, mm.falls,
                                 LS_WATER if mm.water else LS_RUN), f"after {s['elapsed']} frames"
            seen_falls.add(s["falls"])
        assert max(seen_falls) >= 2 and len(mm.flips) >= 5


def sfx(gb, i):
    return gb.read("sfx_count", 14)[i]


def run_until_state(gb, stop, limit=400):
    """Game frames one at a time (a read in a paused frame each) until stop(state)."""
    for _ in range(limit):
        s = snap(gb)
        if stop(s):
            return s
        frames(gb, 1)
    raise AssertionError("the stop condition was not reached")


def set_push(gb, sign, elapsed=None, **kw):
    """A steady push of `sign` at the size of play frame `elapsed` (no flip pending), the Spigoteer centred."""
    poke(gb, tsgn=sign, dsr=sign * RAMP, tell=sign * RAMP, fdelay=0, flip_in=65000, lean=0, vel=0, fish_in=65000, fish_t=0,
         **({} if elapsed is None else {"elapsed": elapsed}), **kw)
    frames(gb, 1)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_push_grows_from_0_025_to_0_045(model):
    with log_roll(model) as gb:
        to_playing(gb)
        set_push(gb, 1, 0)
        s = snap(gb)
        assert abs(s["drift"] - 0.025 * 65536) < 120, s["drift"]
        set_push(gb, -1, 1199)
        s = snap(gb)
        assert abs(s["drift"] + 0.035 * 65536) < 150, s["drift"]
        set_push(gb, 1, 2398)
        s = snap(gb)
        assert abs(s["drift"] - 0.045 * 65536) < 150, s["drift"]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_flip_is_told_30_frames_before_the_push_turns(model):
    """flip_in reaches 0: the creak, the bark's ramp turns at once (it slows, stops and rolls back over 30 frames), the push
    stays as it was for 30 frames and then turns over 30 more; the bark's phase moves one way, stands still, moves the other."""
    with log_roll(model) as gb:
        to_playing(gb)
        set_push(gb, 1, 600, on=0)
        poke(gb, flip_in=3)
        shakes = sfx(gb, SFX_SHAKE)
        rows = game_rows(gb, 90)
        t0 = next(i for i, r in enumerate(rows) if r["tsgn"] == -1)
        assert sfx(gb, SFX_SHAKE) == shakes + 1, "a creak"
        tell = [r["tell"] for r in rows[t0:]]
        dsr = [r["dsr"] for r in rows[t0:]]
        assert tell[0] == RAMP - 1 and tell[59] == -RAMP, "the bark turns at once, over 60 frames"
        assert all(a - b == 1 for a, b in zip(tell, tell[1:60]))
        assert dsr[:RAMP] == [RAMP] * RAMP, "the push waits 30 frames"
        assert all(dsr[k + RAMP] == tell[k] for k in range(len(dsr) - RAMP)), "then follows the bark's ramp 30 frames late"
        assert len(dsr) - RAMP > 50 and dsr[-1] < 0
        # the bark: phase deltas change sign through zero
        ph = [rows[i + 1]["roll"] - rows[i]["roll"] for i in range(t0 - 3, t0 + 62)]
        ph = [d - 65536 if d > 32767 else d + 65536 if d < -32768 else d for d in ph]
        assert ph[0] < 0 < ph[-1] and any(abs(d) < 60 for d in ph), "slows, stops, reverses"
        assert [d for d in ph if d][0] < 0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_no_input_falls_in_under_3_seconds_at_the_end_push_but_not_at_once_at_the_start(model):
    with log_roll(model) as gb:
        to_playing(gb)
        set_push(gb, 1, 2300)
        s = run_until_state(gb, lambda s: s["st"] == LS_WATER, 300)
        assert s["elapsed"] - 2300 < 180, "end push: under 3 s"
    with log_roll(model) as gb:
        to_playing(gb)
        set_push(gb, 1, 0)
        s = run_until_state(gb, lambda s: s["st"] == LS_WATER, 400)
        assert 120 < s["elapsed"] < 260, s["elapsed"]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_mashing_both_directions_falls_and_a_few_taps_do_not(model):
    """Left, Right, Left, Right on every frame cancel out: the push wins. A tap every 70 frames against it holds."""
    with log_roll(model) as gb:
        to_playing(gb)
        set_push(gb, 1, 2300)
        keys = ["left", "right"]
        for i in range(260):
            gb.hold(keys[i % 2])
            frames(gb, 1)
            gb.release(keys[i % 2])
            if snap(gb)["st"] == LS_WATER:
                break
        assert snap(gb)["st"] == LS_WATER and snap(gb)["falls"] == 1, "mashing falls"
    with log_roll(model) as gb:
        to_playing(gb)
        set_push(gb, 1, 0)
        for i in range(300):
            if i % 70 == 0 and i:
                tap(gb, "left")
            else:
                frames(gb, 1)
        assert snap(gb)["st"] == LS_RUN and snap(gb)["falls"] == 0 and abs(snap(gb)["px"]) < 60


# ---- falling ---------------------------------------------------------------------------------------------------------------
def pose_tiles(gb):
    return [oam(gb, OAM_SPIG + k)["tile"] for k in range(6)]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_fall_splashes_for_180_frames_with_droplets_then_climbs_back(model):
    """Past 64 px: SPLASH at the water's y with 4 droplets, the HUD's falls digit, lean 0, the partner startled (frame 3); no
    time counts on the log in the water; SPLASH 90 frames, CLIMB 90 (the last 12 rising); back on the log after 180."""
    with log_roll(model) as gb:
        to_playing(gb)
        set_push(gb, 1, 1000)
        poke(gb, lean=63 * 65536 + 60000, vel=2 * 65536)
        breaks = sfx(gb, SFX_BREAK)
        run_until_state(gb, lambda s: s["st"] == LS_WATER, 5)
        frames(gb, 1)
        s = snap(gb)
        assert s["falls"] == 1 and s["lean"] == 0 and s["vel"] == 0 and sfx(gb, SFX_BREAK) == breaks + 1
        assert tilemap_row(gb, 0, 11, 1) == [36 + 1], "the HUD digit"
        assert pose_tiles(gb) == [otile(e) for e in ART["pose_e"][4]], "SPLASH"
        assert oam(gb, OAM_SPIG)["y"] == 100 + 16
        assert all(oam(gb, OAM_DROPS + k)["y"] for k in range(4)), "four droplets"
        sq_tiles = [oam(gb, OAM_SQ + k)["tile"] for k in range(4)]
        shot(gb, "fall")
        check_golden(gb, "lr_fall")
        on0 = s["on"]
        frames(gb, 70)
        s = snap(gb)
        assert s["on"] == on0 and s["st"] == LS_WATER and s["fall_t"] >= 60
        assert [oam(gb, OAM_SQ + k)["tile"] for k in range(4)] != sq_tiles, "the partner calms down"
        run_until_state(gb, lambda s: s["fall_t"] == SPLASH_LEN + 2)
        frames(gb, 1)
        assert pose_tiles(gb) == [otile(e) for e in ART["pose_e"][5]], "CLIMB"
        assert oam(gb, OAM_SPIG)["y"] == 100 + 16
        assert [oam(gb, OAM_DROPS + k)["y"] for k in range(4)] == [0] * 4, "the burst is over"
        shot(gb, "climb")
        check_golden(gb, "lr_climb")
        run_until_state(gb, lambda s: s["fall_t"] == HOP_AT + 6)
        frames(gb, 1)
        assert 72 + 16 < oam(gb, OAM_SPIG)["y"] < 100 + 16, "rising onto the log"
        launches = sfx(gb, SFX_LAUNCH)
        s = run_until_state(gb, lambda s: s["st"] == LS_RUN, 100)
        assert abs(s["lean"]) < 6000 and s["falls"] == 1 and sfx(gb, SFX_LAUNCH) == launches + 1   # (back on the log: lean 0, one push step)
        frames(gb, 3)
        assert oam(gb, OAM_SPIG)["y"] == 72 + 16 and snap(gb)["on"] > on0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_pose_follows_the_lean_and_right_leans_are_the_x_flip(model):
    with log_roll(model) as gb:
        to_playing(gb)
        calm(gb)
        for sign in (-1, 1):
            for px, pose in ((0, "C"), (13, "C"), (14, "L1"), (39, "L1"), (40, "L2"), (63, "L2")):
                poke(gb, lean=sign * (px * 65536 + 5000), vel=0)
                frames(gb, 2)                    # (the OAM lags the logic by a frame)
                tiles = pose_tiles(gb)
                if pose == "C":
                    assert tiles in ([otile(e) for e in ART["pose_e"][0]], [otile(e) for e in ART["pose_e"][1]])
                    assert not any(oam(gb, OAM_SPIG + k)["prop"] & S_FLIPX for k in range(6))
                    continue
                e = [otile(x) for x in ART["pose_e"][2 if pose == "L1" else 3]]
                flipped = [oam(gb, OAM_SPIG + k)["prop"] & S_FLIPX for k in range(6)]
                if sign < 0:
                    assert tiles == e and not any(flipped), (px, "left lean as drawn")
                else:
                    assert tiles == e and all(flipped), (px, "right lean: the same tiles, X-flipped")
                    assert [oam(gb, OAM_SPIG + k)["x"] for k in range(3)] == [92 + 8 + 16, 92 + 8 + 8, 92 + 8], "columns mirrored"
        # the marker: 76 + lean, clamped at the meter's ends
        for px, mx in ((0, 76), (20, 96), (-30, 46), (64, 140)):
            poke(gb, lean=px * 65536, vel=0)
            frames(gb, 2)
            assert oam(gb, OAM_MARK)["x"] == mx + 8
        poke(gb, lean=-(65 * 65536 + 100), vel=0)
        frames(gb, 1)
        assert snap(gb)["st"] == LS_WATER


# ---- scoring, medals, the outro --------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_100_points_for_each_second_on_the_log_and_none_in_the_water(model):
    with log_roll(model) as gb:
        to_playing(gb)
        calm(gb)
        poke(gb, on=0, s60=0)
        s0 = gb.mem16("mg_score")
        frames(gb, 57)                               # (PyBoy's frame cut shifts the count by a frame or two)
        assert gb.mem16("mg_score") == s0
        frames(gb, 5)
        assert gb.mem16("mg_score") == s0 + PTS_SEC and score(gb) == s0 + PTS_SEC
        frames(gb, 60)
        assert gb.mem16("mg_score") == s0 + 2 * PTS_SEC
        poke(gb, lean=70 * 65536, vel=0)             # a fall: the next seconds do not count
        frames(gb, 100)
        assert snap(gb)["st"] == LS_WATER and gb.mem16("mg_score") == s0 + 2 * PTS_SEC


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("secs,medal", [(0, MEDAL_NONE), (BRONZE - 1, MEDAL_NONE), (BRONZE, MEDAL_BRONZE),
                                        (SILVER - 1, MEDAL_BRONZE), (SILVER, MEDAL_SILVER), (GOLD - 1, MEDAL_SILVER),
                                        (GOLD, MEDAL_GOLD)])
def test_the_medal_is_by_seconds_on_the_log(model, secs, medal):
    with log_roll(model) as gb:
        to_playing(gb)
        calm(gb)
        poke(gb, on=secs * 60 + 59)
        to_result(gb)
        assert gb.mem("mg_medal") == medal
        word = ["NO MEDAL", "BRONZE 500", "SILVER 1500", "GOLD 3000"][medal]
        assert text(gb, 3, True, x0=4) == word


def finish(gb):
    """Run the play out to MG_END (mg_timer 3 frames from 0)."""
    gb.write("mg_timer", 3)
    gb.write(gb.addr("mg_timer") + 1, 0)
    until(gb, lambda: gb.mem("mg_phase") == MG_END, 10)


def attr_row(gb, r):
    gb.write(0xFF4F, 1)
    try:
        return [gb.pb.memory[0x9800 + r * 32 + c] & 7 for c in range(20)]
    finally:
        gb.write(0xFF4F, 0)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_banner_rows_are_pines_in_play_and_the_hud_band_for_time_up(model):
    """Rows 2-3 hold the banner until the first play frame, then the pines (tiles and, on CGB, colours); TIME UP and NO FALLS
    show in the HUD band; at MG_END frame 40 the pines are back."""
    with log_roll(model) as gb:
        frames(gb, 5)
        assert text(gb, 2) == "LOG ROLL"
        to_playing(gb, 6)
        for r in (2, 3):
            assert tilemap_row(gb, r, 0, 20) == [LR_BG + t for t in ART["map"][(r - 1) * 20:r * 20]], f"pines on row {r}"
            if model == "cgb":
                assert attr_row(gb, r) == ART["attr"][(r - 1) * 20:r * 20]
        calm(gb)
        finish(gb)
        frames(gb, 2)
        assert text(gb, 2) == "TIME UP" and text(gb, 3) == "NO FALLS 1000"
        if model == "cgb":
            assert attr_row(gb, 2) == [HUD_ATTR_PAL] * 20 and attr_row(gb, 3) == [HUD_ATTR_PAL] * 20
        shot(gb, "timeup")
        until(gb, lambda: gb.mem("mg_t") >= BAND_OFF + 3, 80)
        for r in (2, 3):
            assert tilemap_row(gb, r, 0, 20) == [LR_BG + t for t in ART["map"][(r - 1) * 20:r * 20]]
            if model == "cgb":
                assert attr_row(gb, r) == ART["attr"][(r - 1) * 20:r * 20]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_up_at_time_up_gives_1000_and_the_partner_topples_in(model):
    with log_roll(model) as gb:
        to_playing(gb, 3)
        calm(gb)
        catches = sfx(gb, SFX_CATCH)
        s0 = gb.mem16("mg_score")
        finish(gb)
        frames(gb, 1)
        assert gb.mem16("mg_score") == s0 + PTS_CLEAN and sfx(gb, SFX_CATCH) == catches + 1, "NO FALLS 1000"
        ys = []
        for _ in range(TOPPLE + 4):
            frames(gb, 1)
            ys.append(oam(gb, OAM_SQ)["y"])
        assert ys == sorted(ys) and ys[-1] == 100 + 16 and ys[0] < ys[-1], "into the river"
        top = [oam(gb, OAM_SQ + k) for k in range(4)]
        assert all(o["prop"] & S_FLIPX for o in top), "tumbling the other way"
        assert top[0]["x"] > top[1]["x"], "X-flipped: columns swap"
        assert all(oam(gb, OAM_DROPS + k)["y"] for k in range(4)), "its splash"
        shot(gb, "topple")
        check_golden(gb, "lr_topple")
        until(gb, lambda: gb.mem("mg_phase") == MG_RESULT, 60)
    # a fall earlier: no bonus, no NO FALLS line, and nobody topples when he is in the water
    with log_roll(model) as gb:
        to_playing(gb, 3)
        set_push(gb, 1, 800)
        poke(gb, lean=70 * 65536, vel=65536)
        frames(gb, 3)
        assert snap(gb)["st"] == LS_WATER
        s0 = gb.mem16("mg_score")
        finish(gb)
        frames(gb, 3)
        assert gb.mem16("mg_score") == s0 and text(gb, 3) == ""
        assert snap(gb)["top_t"] == 0 and not oam(gb, OAM_SQ)["prop"] & S_FLIPX


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_game_that_ends_in_the_water_keeps_the_climb_going_in_the_outro(model):
    with log_roll(model) as gb:
        to_playing(gb, 3)
        calm(gb)
        poke(gb, lean=70 * 65536, vel=65536)
        frames(gb, 2)
        finish(gb)
        frames(gb, 40)
        assert snap(gb)["st"] == LS_WATER and snap(gb)["fall_t"] > 30


# ---- streamed tiles --------------------------------------------------------------------------------------------------------
def roll_slots(gb):
    return vram_bg(gb, ART["roll_at"], 4), vram_bg(gb, ART["rip_at"], 2)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_bark_and_ripple_tiles_are_streamed_into_their_slots(model):
    """Every game frame the log's 4 body tiles in VRAM are the roll frame the phase says and the ripples' two the frame of the
    beat (every 20 frames); over 700 frames the bark goes both ways (a flip), and the map is never touched."""
    with log_roll(model) as gb:
        to_playing(gb)
        poke(gb, flip_in=60, fish_in=65000)
        seen, dirs, ripples, last, prev = set(), set(), set(), None, None
        frame = [b"".join(bytes(t) for t in ART["roll"][f]) for f in range(4)]
        ripf = [b"".join(bytes(t) for t in ART["rip"][f]) for f in range(2)]
        for i in range(700):
            frames(gb, 1)
            s = snap(gb)
            roll, rip = roll_slots(gb)
            assert s["roll_vis"] == s["roll_f"] == s["roll"] >> 14, "the queued frame is the one the phase says"
            # (a read at PyBoy's frame end sees the VRAM as of the last VBlank: the frame queued this frame lands in the next)
            ok = {s["roll_vis"]} if prev and prev[0] == s["roll_vis"] else {s["roll_vis"], prev[0] if prev else s["roll_vis"]}
            assert roll in [frame[f] for f in ok], f"bark frame {s['roll_vis']} at {s['elapsed']}"
            okr = {s["rip_vis"]} if prev and prev[1] == s["rip_vis"] else {s["rip_vis"], prev[1] if prev else s["rip_vis"]}
            assert rip in [ripf[f] for f in okr], f"ripple frame {s['rip_vis']}"
            prev = (s["roll_vis"], s["rip_vis"])
            seen.add(s["roll_f"])
            ripples.add(s["rip_vis"])
            if last is not None and last != s["roll_f"]:
                dirs.add((s["roll_f"] - last) % 4)
            last = s["roll_f"]
        assert seen == {0, 1, 2, 3} and ripples == {0, 1} and dirs == {1, 3}, (seen, ripples, dirs)
        assert tilemap_row(gb, 12, 3, 1)[0] == LR_BG + ART["map"][11 * 20 + 3]
        assert tilemap_row(gb, 12, 4, 2) == [LR_BG + ART["roll_at"] + 0, LR_BG + ART["roll_at"] + 2], "X and Y body tiles"
        assert tilemap_row(gb, 13, 4, 2) == [LR_BG + ART["roll_at"] + 1, LR_BG + ART["roll_at"] + 3]


# ---- a whole game ----------------------------------------------------------------------------------------------------------
def bot_key(s, since):
    ahead = s["px"] + 15 * (s["vel"] / ONE)
    if since >= 8:
        if ahead > 28:
            return "left"
        if ahead < -28:
            return "right"
    return None


def hop_key(s, rnd=None):
    """"a" when the bot hops: a fish aimed at the Spigoteer has just leapt (4-11 frames into the leap), he is on the log and not in a hop."""
    ok = s["st"] == LS_RUN and s["fish_tgt"] == 0 and s["hop_t"] == 0 and WARN + 4 <= s["fish_t"] <= WARN + 11 and not s["stun"]
    return "a" if ok and (rnd is None or rnd.random() < 0.5) else None


def balance(gb, hop=True):
    """A bot keeps the Spigoteer on the log (a tap against where he will be, at most one in 8 frames) until the play ends, and hops each
    fish aimed at him a few frames after it leaps."""
    since, taps, worst = 99, 0, [0]
    while gb.mem("mg_phase") == MG_PLAY:
        s = snap(gb)
        keys = []
        key = bot_key(s, since)
        if key and s["st"] == LS_RUN:
            keys.append(key)
            since, taps = 0, taps + 1
        else:
            since += 1
        if hop and hop_key(s):
            keys.append("a")
        for k in keys:
            gb.hold(k)
        frames(gb, 2 if keys else 1, worst)
        for k in keys:
            gb.release(k)
    return taps, worst[0]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("seed", [0x5A17, 0x1234])
def test_a_bot_balances_a_whole_game_for_gold(model, seed):
    """40 seconds, every frame at <= 10 sprites a line: no fall, 4000 for the seconds, 1000 for no fall, GOLD 3000 more."""
    with log_roll(model, seed=seed) as gb:
        to_play(gb)
        taps, worst = balance(gb)
        s = snap(gb)
        assert s["falls"] == 0 and s["on"] == TIME_S * 60 and taps > 15 and worst <= 9      # (9: the Sasquatch's own splash after a fish)
        assert s["hits"] == 0 and s["dodged"] >= 4, (s["hits"], s["dodged"])
        total = TIME_S * PTS_SEC + PTS_CLEAN + s["dodged"] * PTS_DODGE
        until(gb, lambda: gb.mem("mg_phase") == MG_RESULT, 80)
        assert gb.mem16("mg_score") == total
        until(gb, lambda: gb.mem("overlay_on") == 1, 10)
        frames(gb, 3)
        assert gb.mem("mg_medal") == MEDAL_GOLD and score(gb) == total + 3000
        assert text(gb, 2, True, x0=4) == f"SCORE {total}"
        if seed == SEED:
            shot(gb, "result")
            check_golden(gb, "lr_result")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_game_with_falls_keeps_to_10_sprites_a_line(model):
    """No input at all for the whole 40 s: falls at the push's pace, every frame at <= 10 a line (the splash is the worst)."""
    with log_roll(model, seed=0x0F0F) as gb:
        to_play(gb)
        worst = [0]
        while gb.mem("mg_phase") == MG_PLAY:
            frames(gb, 1, worst)
        s = snap(gb)
        assert s["falls"] >= 3 and 7 <= worst[0] <= 9, (s["falls"], worst)
        assert gb.mem16("mg_score") == (s["on"] // 60) * PTS_SEC + s["dodged"] * PTS_DODGE, "100 a second on the log, 150 a dodge, no bonus"
        until(gb, lambda: gb.mem("mg_phase") == MG_RESULT, 80)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_worst_forced_scene_stays_within_10_a_line(model):
    """The partner in the river (the outro's) while the Spigoteer is splashing, every droplet age: 9 on lines 100-103 at most
    (the game never shows both, the layout allows it)."""
    with log_roll(model) as gb:
        to_playing(gb)
        calm(gb)
        poke(gb, st=LS_WATER, fall_t=1, top_t=TOPPLE + 3, drop_t=1, drop_x=100, lean=0)
        worst = 0
        for age in range(DROPS + 2):
            poke(gb, fall_t=1 + age // 2, top_t=TOPPLE + 3)
            frames(gb, 1)
            worst = max(worst, max(lines(gb)))
        assert 8 <= worst <= 10, worst


# ---- practice, the level after, STORY, ARCADE, the list ------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_practice_retry_starts_over_and_menu_goes_to_the_list(model):
    with log_roll(model) as gb:
        to_playing(gb)
        calm(gb)
        poke(gb, on=60 * 26)
        to_result(gb)
        assert text(gb, 4, True, x0=4) == "A RETRY B MENU" and gb.mem("mg_medal") == MEDAL_BRONZE
        gb.press("a", 2)
        run_until(gb, lambda: state(gb) == GS_MINI and gb.pb.memory[0xFF40] & 0x80, 30)
        frames(gb, 3)
        s = snap(gb)
        assert gb.mem("mg_phase") == 0 and gb.mem16("mg_score") == 0 and s["on"] == 0 and s["falls"] == 0 and s["elapsed"] == 0
        assert text(gb, 2) == "LOG ROLL" and score(gb) == 0
        to_result(gb)
        gb.press("b", 2)
        run_until(gb, lambda: state(gb) == GS_MGLIST and gb.pb.memory[0xFF40] & 0x80, 30)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_level_after_log_roll_has_everything_back(model):
    """Log Roll (a fall, a bark step) -> B to the list -> the title -> a level: OBJ tiles (56-91 and the ones above the BG
    tiles too), BG 77-255, OBP0 / OBP1 and every palette are byte for byte those of a level started from a fresh boot."""
    from test_bs import level_vram, palettes
    from test_scores import booted
    with booted(model) as gb:
        hold_stage_anim(gb)
        title_level(gb)
        run_until(gb, lambda: state(gb) == PLAYING, 60)
        gb.run(2)
        fresh, pals = level_vram(gb), palettes(gb)
    with log_roll(model) as gb:
        to_playing(gb)
        set_push(gb, 1, 1500)
        run_until_state(gb, lambda s: s["st"] == LS_WATER, 300)
        frames(gb, 30)
        to_result(gb)
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
        gb.run(2)
        assert level_vram(gb) == fresh
        assert palettes(gb) == pals


def to_mini_slot(model):
    from test_story import to_shift, win
    gb = to_shift(model, LUMBER, 1)
    win(gb, LUMBER, 1)
    run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 20)
    run_until(gb, lambda: state(gb) == GS_MINI, 800)
    run_until(gb, lambda: gb.pb.memory[0xFF40] & 0x80, 10)
    return gb


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_story_plays_it_in_chapter_3_and_the_last_call_has_everything_back(model):
    """The lumber lodge: after the Happy hour, Log Roll in MG_STORY (the score carried, the count not skippable, unlocked for
    Practice at once); A CONTINUE leads to the Last call, whose VRAM and palettes are those of the Last call reached without it."""
    from test_bs import level_vram, palettes
    from test_story import to_goal, to_shift
    with to_shift(model, LUMBER, 2) as gb:
        gb.run(2)
        fresh, pals = level_vram(gb), palettes(gb)
    with to_mini_slot(model) as gb:
        assert gb.mem("mg_id") == MG_LOGROLL and gb.mem("mg_mode") == MG_STORY and gb.mem("venue_id") == LUMBER
        assert text(gb, 2) == "LOG ROLL" and score(gb) > 0
        assert gb.mem16("mg_unlocked") == 1 << MG_LOGROLL
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
        assert gb.mem("story_chapter") == LUMBER and gb.mem("story_shift") == 2 and gb.mem("story_step") == 3
        to_goal(gb)
        gb.run(2)
        assert level_vram(gb) == fresh
        assert palettes(gb) == pals


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_arcade_plays_it_in_chapter_3(model):
    from test_arcade import start_arcade
    from test_story import to_goal, win
    with start_arcade(model) as gb:
        to_goal(gb)
        gb.write("story_chapter", LUMBER)
        gb.write("story_step", 1)
        win(gb, 0, 0)
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 20)
        run_until(gb, lambda: state(gb) == GS_MINI, 800)
        run_until(gb, lambda: gb.pb.memory[0xFF40] & 0x80, 10)
        assert gb.mem("mg_id") == MG_LOGROLL and gb.mem("mg_mode") == MG_STORY and gb.mem("venue_id") == LUMBER
        assert gb.mem("save_lock") == 1 and gb.mem16("mg_unlocked") == 1 << MG_LOGROLL
        assert text(gb, 2) == "LOG ROLL"


# ---- goldens: the intro, the log balanced, a hard lean (fall / climb / topple / result are taken in their own tests) ----------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_goldens(model):
    with log_roll(model) as gb:
        frames(gb, 30)
        shot(gb, "intro")
        check_golden(gb, "lr_intro")
        to_playing(gb, 3)
        calm(gb)
        poke(gb, lean=6 * 65536, on=10 * 60 + 20, s60=20)
        t = 30 * 60 - 3
        gb.write("mg_timer", t & 255)
        gb.write(gb.addr("mg_timer") + 1, t >> 8)
        frames(gb, 20)
        shot(gb, "play")
        check_golden(gb, "lr_play")
        poke(gb, lean=-52 * 65536, vel=0)
        frames(gb, 2)
        shot(gb, "lean")
        check_golden(gb, "lr_lean")


# ---- speed and the VBlank copy: the slowdown, flicker and black bars the owner saw ------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_whole_game_has_no_late_frame_and_no_copy_into_the_picture(model):
    """40 seconds of balancing, with 200 frames of leaning one way (a fall, the splash, the droplets): every frame's logic and music end before
    line 128 (the VBlank is at 144: a late frame was the slowdown), no VBlank copy was refused, and every copy ended inside VBlank
    (vq_end_ly_max < 154: a copy that runs on into line 0 or 1 loses its last bytes on the hardware, and with them the banner rows
    put back: the black bars)."""
    with log_roll(model) as gb:
        to_play(gb)
        late0, worst_end, worst_drain, held, hold, since, i = gb.mem16("vq_late"), 0, 0, None, 0, 99, 0
        while gb.mem("mg_phase") == MG_PLAY and i < 3300:
            if hold:
                hold -= 1
                if not hold:
                    gb.release(held)
            else:
                key = "right" if 400 < i < 600 and since >= 3 else None if 400 < i < 600 else bot_key(lr(gb), since)
                if key:
                    gb.hold(key)
                    held, hold, since = key, 2, 0
            since += 1
            gb.run(1)
            i += 1
            worst_end = max(worst_end, gb.mem16("perf_end_last"))
            worst_drain = max(worst_drain, gb.mem("vq_end_ly_max"))
            gb.write("vq_end_ly_max", 0)
        assert gb.mem("mg_phase") != MG_PLAY and snap(gb)["falls"] >= 1
        assert worst_end < 128, f"a frame ended at line {worst_end}"
        assert gb.mem16("vq_late") == late0, "a VBlank copy was refused"
        assert worst_drain < 154, f"a copy ended at line {worst_drain - 154} of the next frame"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_oam_dma_is_off_while_a_mini_game_draws(model):
    """mg_update turns the VBlank OAM DMA off for the frame's logic and on again at its end (a frame that runs past VBlank shows
    the last complete sprite list, not a half-written one): checked at the game's own update and at the end of every frame."""
    with log_roll(model) as gb:
        from test_mg import BANKS
        inside, outside = [], []
        h1, h2 = gb.addr("lr_update") & 0xFFFF, gb.addr("vq_frame_end") & 0xFFFF
        gb.pb.hook_register(BANKS["b_lr_update"], h1, lambda _: inside.append(gb.mem("_shadow_OAM_base")), None)
        gb.pb.hook_register(0, h2, lambda _: outside.append(gb.mem("_shadow_OAM_base")), None)
        try:
            frames(gb, 400)
        finally:
            gb.pb.hook_deregister(BANKS["b_lr_update"], h1)
            gb.pb.hook_deregister(0, h2)
        assert len(inside) > 100 and set(inside) == {0}, "off while the game draws"
        assert len(outside) > 300 and 0 not in outside, "on again at the end of every frame"
