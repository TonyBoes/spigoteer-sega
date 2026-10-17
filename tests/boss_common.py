# Helpers shared by the per-boss test files (tests/test_boss_<name>.py; tests/test_boss.py has Big Tex's and the
# engine's): a boss's row of src/boss.c rows[] and his art (build/boss.json) by venue, the way into his fight after the
# chapter's Last call, his body on the BG, the HUD meter, mugs on his bar, and every frame checked at <= 10 sprites a
# line. Not a test module (no test_ prefix): pytest collects nothing here.
import json
import re

from conftest import GAME, ROOT, logic_paused, venue
from test_bonus import lines
from test_flow import GS_GOAL, LEVEL_CLEAR, PLAYING, inject_mug, run_until, state, tilemap_row
from test_story import banner_text, centred, to_goal, to_shift, win
from test_venues import cgb_palette

BOSS_C = (ROOT / "src" / "boss.c").read_text() + (ROOT / "src" / "boss.h").read_text()
ART = json.loads((ROOT / "build" / "boss.json").read_text())
ART_H = (ROOT / "build" / "art.h").read_text()
BLANK = int(re.search(r"#define TILE_HUD_BLANK (\d+)", ART_H).group(1))
THEMES = ["saloon", "sports", "lodge", "bistro", "igloo", "factory", "biker", "teahouse", "zoo", "space"]
FIELDS = ("width", "x", "bar", "step", "push", "gulp", "hands", "sip", "meter", "hat", "sway")
BS_WALK, BS_GULP, BS_TELL, BS_SPECIAL, BS_JUMP, BS_OUTRO, BS_WARM, BS_ENTER, BS_WALKIN = range(9)
BP_WALK, BP_STOMP, BP_GULP, BP_WINCE, BP_HAPPY = range(5)
SP_FAIL, SP_OUTRO = 4, 5
FULL, EMPTY, BREAKING, RETURN = 1, 2, 3, 5
OAM_TOPPER, OBJ_TOPPER = GAME["OAM_DANCERS"], 96
SPOUT_X, TAP_X = GAME["SPOUT_X"], GAME["TAP_X"]
HUD_BG = 252
SFX_LAUNCH, SFX_CATCH, SFX_BREAK = 2, 3, 4


def define(name, src=BOSS_C):
    return int(re.search(rf"#define {name}\s+\(?(\d+)", src).group(1))


def row(c):
    """src/boss.c rows[c] as a dict (FIELDS, line1, line2)."""
    m = re.search(rf"\[{c}\] = \{{\s*" + r",\s*".join([r"(\d+)"] * 11) + r',\s*"([^"]*)",\s*"([^"]*)"\s*\}', BOSS_C)
    v = m.groups()
    d = dict(zip(FIELDS, (int(x) for x in v[:11])))
    d["line1"], d["line2"] = v[11], v[12]
    return d


def art(name):
    return next(b for b in ART["bosses"] if b["name"] == name)


def pair_id(p):
    return 162 + 2 * p if p < 21 else 216 + 2 * (p - 21)


def pose_cols(a, pose, hold=0):
    cols = [pair_id(p) for p in (a["sway_map"] if pose == "sway" else a["pose"][pose])]   # ("sway": his shifted GULP, BP_SWAY)
    # (no hand column any more: the held empties are the capacity row of glasses, sprites; `hold` stays for the callers)
    return cols


def meter_tiles(hp, meter):
    out = []
    for k in range(7):
        if k >= (meter + 1) // 2:
            out.append(BLANK)
        else:
            out.append(HUD_BG + (3 if hp >= 2 else 2 if hp else 1))
            hp = max(hp - 2, 0)
    return [HUD_BG] + out


def bar_row(r):
    return 5 + 3 * r["bar"]


def body(gb, r):
    """The tile ids of his bar's two wall rows."""
    y = bar_row(r)
    return tilemap_row(gb, y, 0, 20), tilemap_row(gb, y + 1, 0, 20)


def assert_body(gb, c, a, x, pose, hold=0):
    """His pose `pose` (holding `hold`) at x on his bar, the venue's wall left of him."""
    r = row(c)
    top, bottom = body(gb, r)
    k = x // 8
    want = pose_cols(a, pose, hold)
    assert top[k:k + len(want)] == want and bottom[k:k + len(want)] == [t + 1 for t in want], (x, pose, hold, top)
    bar = venue(THEMES[c])["bar_map"]
    assert top[:k] == bar[0:k] and bottom[:k] == bar[20:20 + k], "the wall left of him"


def hud(gb):
    return tilemap_row(gb, 0, 12, 8)


# ---- driving -------------------------------------------------------------------------------------------------------
def frames(gb, n):
    """n frames, one at a time, each checked at <= 10 sprites on every line."""
    for _ in range(n):
        gb.run(1)
        assert max(lines(gb)) <= 10


def _lines_ok(gb):
    assert max(lines(gb)) <= 10


def gframes(gb, n):
    """n GAME frames (conftest.game_frames: counted at the end of each frame's logic, not per emulator frame), each emulator frame
    checked at <= 10 sprites on every line. For a test that takes a golden: the shot is then at a fixed game frame."""
    from conftest import game_frames
    return game_frames(gb, n, each=_lines_ok)


def until_g(gb, cond, limit=600):
    """until(), with cond evaluated at the end of each game frame's logic (conftest.until_game): the first game frame it holds on."""
    from conftest import until_game
    try:
        return until_game(gb, cond, limit, each=_lines_ok)
    except AssertionError as e:
        if "not reached" in str(e):
            raise AssertionError(f"not reached in {limit} game frames (state {state(gb)}, boss_state {gb.mem('boss_state')})")
        raise


def until(gb, cond, limit=600):
    for _ in range(limit):
        if cond():
            return
        frames(gb, 1)
    raise AssertionError(f"not reached in {limit} frames (state {state(gb)}, boss_state {gb.mem('boss_state')})")


_own = {}
ENTRANCES = {0: ("big_tex", "ent", 1), 1: ("mascot", "ent", 1), 5: ("prototype", "t", 1000)}   # venue: (boss file, clock field, running from)


def start_entrance(gb):
    """The warm-up is over (boss_hook 5): his entrance begins (the logic can still be mid-frame: a few frames on)."""
    gb.write("boss_hook", 5)
    until(gb, lambda: gb.mem("boss_state") != BS_WARM, 5)
    frames(gb, 3)
    return gb


def entrance_running(gb):
    """The fight's entrance is on: the clock of the ones with a table row (Big Tex, the Mascot, the Prototype: BEV_INTRO + BEV_DRAW),
    else boss_state BS_ENTER / BS_WALKIN."""
    spec = ENTRANCES.get(gb.mem("boss_id"))
    if not spec:
        return gb.mem("boss_state") in (BS_ENTER, BS_WALKIN)
    own = _own.setdefault(spec[0], Own(spec[0]))
    return own.get(gb, spec[1]) >= spec[2]


def skip_entrance(gb):
    """Wait the warm-up / entrance out (every frame checked at <= 10 sprites a line); the intro's 90 frames are still to run."""
    until(gb, lambda: gb.mem("boss_state") not in (BS_WARM, BS_ENTER, BS_WALKIN), 600)
    return gb


def fight(model, c, banner=False, warm=False, entrance=False):
    """Chapter c's Last call won: SHIFT CLEAR, then its boss fight's banner (banner=True: still on it), or the fight (started
    at once: no warm-up, no entrance; warm=True: the warm-up runs; entrance=True: it is over and his entrance has begun)."""
    gb = to_shift(model, c, 2)
    win(gb, c, 2)
    run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 20)
    gb.run(3)
    assert banner_text(gb, 1) == centred("SHIFT CLEAR"), "the Last call is not the chapter's last step any more"
    run_until(gb, lambda: state(gb) == GS_GOAL, 800)
    gb.run(3)
    assert gb.mem("boss_on") == 1 and gb.mem("boss_id") == c
    if banner:
        return gb
    to_goal(gb, boss_start=not (warm or entrance))
    if entrance:                              # the warm-up is over now: his entrance has begun
        start_entrance(gb)
    return gb


def still_regulars(gb):
    """The regulars stand still (a test of the boss alone: no one reaches the tap)."""
    gb.write("patron_speed", 0)
    gb.write("hurry_speed", 0)


def play(gb):
    """Into the play proper: the intro over, PLAYING."""
    until(gb, lambda: gb.mem("intro_timer") == 0 and state(gb) == PLAYING, 200)


def mugs(gb, b=None, st=None):
    """[(slot, state, bar, x)] of the live mugs (on bar b, in state st)."""
    s, mb, mx = gb.read("mug_state", 20), gb.read("mug_bar", 20), gb.read("mug_x", 20)
    return [(i, s[i], mb[i], mx[i]) for i in range(20)
            if s[i] and (b is None or mb[i] == b) and (st is None or s[i] == st)]


def throw(gb, b, x=72, perfect=False):
    """A full mug on bar b at x (as if just launched and slid there); perfect: a story perfect pour (mug_timer 1). The
    pokes land between two game frames (logic_paused: a poke mid-frame could see update_mugs recount mugs_live to 0
    after it, and the mug would never move)."""
    with logic_paused(gb):
        inject_mug(gb, b, x)
        if perfect:
            m = [i for i, s, mb, mx in mugs(gb, b, FULL) if mx == x][-1]
            gb.write(gb.addr("mug_timer") + m, 1)


def block_empties(gb):
    """No empty may be sent (next_arrival far ahead)."""
    gb.write("next_arrival", 0xFF)
    gb.write(gb.addr("next_arrival") + 1, 0x7F)


def pour(gb, fill=20):
    """The bartender (at his bar's tap) fills for `fill` frames and lets go (returns the frames it took)."""
    launched = gb.read("sfx_count", 9)[SFX_LAUNCH]
    gb.hold("a")
    frames(gb, fill)
    gb.release("a")
    n = fill
    while gb.read("sfx_count", 9)[SFX_LAUNCH] == launched and n < fill + 10:
        frames(gb, 1)
        n += 1
    assert gb.read("sfx_count", 9)[SFX_LAUNCH] != launched, "launched"
    return n


def to_bar(gb, b):
    """The bartender to bar b (Up / Down)."""
    for _ in range(4):
        cur = gb.mem("bar")
        if cur == b:
            return
        gb.press("down" if b > cur else "up", 2)
        frames(gb, 2)
    assert gb.mem("bar") == b


class Clock:
    """Game frames (frame_counter, wrapping at 256) since it was made; now() must be called at least every 255."""
    def __init__(self, gb):
        self.gb, self.t, self.last = gb, 0, gb.mem("frame_counter")

    def now(self):
        c = self.gb.mem("frame_counter")
        self.t += (c - self.last) & 255
        self.last = c
        return self.t


def arrivals_ok(arr, gap, own_gap=None):
    """arr: [(arrival frame, his own?)] sorted; every two >= gap apart (two of his own: own_gap), 2 frames' slack."""
    for (a, o1), (b, o2) in zip(arr, arr[1:]):
        g = own_gap if (own_gap is not None and o1 and o2) else gap
        assert b - a >= g - 2, (arr, gap, own_gap)


def check_start(gb, c, a, model):
    """The fight's screen after the banner: his WALK pose at his start x, his tiles and palettes, the HUD's face and a
    full meter, the topper over his head, no regular on his bar."""
    r = row(c)
    if model == "cgb":
        wall = cgb_palette(gb, 2)[0]
        assert cgb_palette(gb, 4) == [wall] + a["pal"][1:], "BG 4: his colours over the venue's wall"
        lamp = a["name"] == "prototype"       # (the Prototype's lamp: colour 2 is green in OBJ 7 at the start)
        want = a["pal"][1:]
        if a["name"] == "duke":               # (his helmet has its own colours: red shell, white stripe, outline)
            want = [29 | 7 << 5 | 7 << 10, 31 | 31 << 5 | 31 << 10, 3 | 2 << 5 | 4 << 10]
        assert [c for k, c in enumerate(cgb_palette(gb, 7, True)[1:]) if not (lamp and k == 1)] == [
            c for k, c in enumerate(want) if not (lamp and k == 1)], "OBJ 7: the topper in the same colours"
    else:
        assert gb.mem(0xFF49) == 0xE4, "DMG: the topper under OBP1 0xE4, the BG's shades"
    for p, data in enumerate(a["pairs"]):
        t = pair_id(p)
        assert bytes(gb.read((0x9000 if t < 128 else 0x8000) + t * 16, 32)) == bytes(data), f"body column {p} at {t}"
    assert bytes(gb.read(0x8000 + HUD_BG * 16, 16)) == bytes(a["icon"])
    assert bytes(gb.read(0x8000 + (HUD_BG + 1) * 16, 48)) == bytes(ART["meter"])
    assert bytes(gb.read(0x8000 + OBJ_TOPPER * 16, len(a["hat"]))) == bytes(a["hat"])   # (STILL, BOB and his `hats`)
    assert gb.mem("boss_x") == r["x"] and gb.mem("boss_bar") == r["bar"] and gb.mem("boss_hp") == r["meter"]
    assert_body(gb, c, a, r["x"], BP_WALK)
    assert hud(gb) == meter_tiles(r["meter"], r["meter"])
    o = gb.oam()[OAM_TOPPER]
    top_y = bar_row(r) * 8
    assert (o["y"], o["x"], o["tile"]) == (top_y + 16 - 8, r["x"] + r["hat"] + 8, OBJ_TOPPER)
    pb = gb.read("patron_bar", 16)
    assert all(pb[p] != r["bar"] for p, s in enumerate(gb.read("patron_state", 16)) if s), "no regular on his bar"


# ---- a boss file's own state (src/boss_<name>.c: a struct in BOSS_OWN over story_scratch, no WRAM of its own) ------
class Own:
    """Fields of the struct `<name>_t` in src/boss_<name>.c, which lives at BOSS_OWN (src/boss.h: the end of
    story_scratch, after the pose table and the hand column): own.get(gb, field), own.put(gb, field, v)."""
    def __init__(self, name):
        src = (ROOT / "src" / f"boss_{name}.c").read_text()
        body = re.search(r"typedef struct \{(.*?)\} " + name + r"_t;", src, re.S).group(1)
        self.fields, off = {}, 0
        for t, n in re.findall(r"(uint8_t|uint16_t)\s+(\w+);", body):
            self.fields[n] = (off, 2 if t == "uint16_t" else 1)
            off += 2 if t == "uint16_t" else 1
        poses = define("BOSS_POSES_MAX", (ROOT / "build" / "boss_art.h").read_text()) + 1   # (+ the sway pose: BP_SWAY)
        self.base = GAME["STORY_SCRATCH"] - define("BOSS_SCRATCH_N") + poses * GAME["BOSS_W_MAX"] + 4
        assert off <= define("BOSS_SCRATCH_N") - poses * GAME["BOSS_W_MAX"] - 4

    def addr(self, gb, field):
        return gb.addr("story_scratch") + self.base + self.fields[field][0]

    def get(self, gb, field):
        a, n = self.addr(gb, field), self.fields[field][1]
        return gb.mem(a) if n == 1 else gb.mem(a) | gb.mem(a + 1) << 8

    def put(self, gb, field, v):
        a, n = self.addr(gb, field), self.fields[field][1]
        gb.write(a, v & 255)
        if n == 2:
            gb.write(a + 1, v >> 8)
