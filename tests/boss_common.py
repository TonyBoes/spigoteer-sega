# Helpers shared by the per-boss test files (tests/test_boss_<name>.py; tests/test_boss.py has Big Tex's and the
# engine's): a boss's row of src/boss.c rows[] and his art (build/boss.json) by venue, the way into his fight after the
# chapter's Last call, his body on the BG, the HUD meter, mugs on his bar, and every frame checked at <= 10 sprites a
# line. Not a test module (no test_ prefix): pytest collects nothing here.
import json
import re

from conftest import GAME, ROOT, venue
from test_bonus import lines
from test_flow import GS_GOAL, LEVEL_CLEAR, PLAYING, inject_mug, run_until, state, tilemap_row
from test_story import banner_text, centred, to_goal, to_shift, win
from test_venues import cgb_palette

BOSS_C = (ROOT / "src" / "boss.c").read_text() + (ROOT / "src" / "boss.h").read_text()
ART = json.loads((ROOT / "build" / "boss.json").read_text())
ART_H = (ROOT / "build" / "art.h").read_text()
BLANK = int(re.search(r"#define TILE_HUD_BLANK (\d+)", ART_H).group(1))
THEMES = ["saloon", "sports", "lodge", "bistro", "igloo", "factory", "biker", "teahouse", "zoo", "space"]
FIELDS = ("width", "x", "bar", "step", "push", "gulp", "hands", "sip", "meter", "hat")
BS_WALK, BS_GULP, BS_TELL, BS_SPECIAL, BS_JUMP, BS_OUTRO = range(6)
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
    d = dict(zip(FIELDS, (int(x) for x in v[:10])))
    d["line1"], d["line2"] = v[11], v[12]
    return d


def art(name):
    return next(b for b in ART["bosses"] if b["name"] == name)


def pair_id(p):
    return 162 + 2 * p if p < 21 else 216 + 2 * (p - 21)


def pose_cols(a, pose, hold=0):
    cols = [pair_id(p) for p in a["pose"][pose]]
    if hold and pose in (BP_WALK, BP_STOMP, BP_WINCE):
        cols[-1] = pair_id(a["hand"][min(hold, 3)])
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


def until(gb, cond, limit=600):
    for _ in range(limit):
        if cond():
            return
        frames(gb, 1)
    raise AssertionError(f"not reached in {limit} frames (state {state(gb)}, boss_state {gb.mem('boss_state')})")


def fight(model, c, banner=False):
    """Chapter c's Last call won: SHIFT CLEAR, then its boss fight's banner (banner=True: still on it), or the fight."""
    gb = to_shift(model, c, 2)
    win(gb, c, 2)
    run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 20)
    gb.run(3)
    assert banner_text(gb, 1) == centred("SHIFT CLEAR"), "the Last call is not the chapter's last step any more"
    run_until(gb, lambda: state(gb) == GS_GOAL, 300)
    gb.run(3)
    assert gb.mem("boss_on") == 1 and gb.mem("boss_id") == c
    return gb if banner else to_goal(gb)


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
    """A full mug on bar b at x (as if just launched and slid there); perfect: a story perfect pour (mug_timer 1)."""
    inject_mug(gb, b, x)
    if perfect:
        m = max(i for i, s, _, _ in mugs(gb, b, FULL))
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
        assert cgb_palette(gb, 7, True)[1:] == a["pal"][1:], "OBJ 7: the topper in the same colours"
    else:
        assert gb.mem(0xFF49) == 0xE4, "DMG: the topper under OBP1 0xE4, the BG's shades"
    for p, data in enumerate(a["pairs"]):
        t = pair_id(p)
        assert bytes(gb.read((0x9000 if t < 128 else 0x8000) + t * 16, 32)) == bytes(data), f"body column {p} at {t}"
    assert bytes(gb.read(0x8000 + HUD_BG * 16, 16)) == bytes(a["icon"])
    assert bytes(gb.read(0x8000 + (HUD_BG + 1) * 16, 48)) == bytes(ART["meter"])
    assert bytes(gb.read(0x8000 + OBJ_TOPPER * 16, 64)) == bytes(a["hat"])
    assert gb.mem("boss_x") == r["x"] and gb.mem("boss_bar") == r["bar"] and gb.mem("boss_hp") == r["meter"]
    assert_body(gb, c, a, r["x"], BP_WALK)
    assert hud(gb) == meter_tiles(r["meter"], r["meter"])
    o = gb.oam()[OAM_TOPPER]
    top_y = bar_row(r) * 8
    assert (o["y"], o["x"], o["tile"]) == (top_y + 16 - 8, r["x"] + r["hat"] + 8, OBJ_TOPPER)
    pb = gb.read("patron_bar", 16)
    assert all(pb[p] != r["bar"] for p, s in enumerate(gb.read("patron_state", 16)) if s), "no regular on his bar"
