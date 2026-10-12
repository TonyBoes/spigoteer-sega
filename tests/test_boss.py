# docs/minigames_bosses.md step 2: the boss engine (src/boss.c) and Big Tex, the saloon's boss, on placeholder art.
# The fight follows the saloon's Last call in story mode (the saloon's boss slot is built: gen_story BUILT_SLOTS): its
# banner, the body on bar 1 (BG) with the topper (OAM 28), the HUD face and meter, stomps, catches, push-back, the hands
# rule, fair empties, the tap, a life lost (he starts over, his meter kept), the win (outro, CHAPTER CLEAR, POST scene)
# and the loss (TRY AGAIN, the venue from its Opening), the regulars on the other bars (slower, variants A / B, no
# tips), the topper's line guard, and everything the fight borrowed put back by the next level load. Every frame of
# every fight here is checked at <= 10 sprites a line (test_bonus.lines).
import json
import re

import pytest
from conftest import GAME, ROOT, check_golden, venue
from test_bonus import lines
from test_flow import (GS_GOAL, GS_STORY, LEVEL_CLEAR, LIFE_LOST, PLAYING, inject_mug, patron_group_tiles, run_until,
                       state, tilemap_row)
from test_story import (BOSS_BUILT, BOSS_STEP, SC, SHIFTS, banner_text, centred, post, pre, settle, skip_scene,
                        to_chapter, to_goal, to_shift, try_again, win)
from test_venues import cgb_palette

pytestmark = pytest.mark.timeout(300)

BOSS_C = (ROOT / "src" / "boss.c").read_text() + (ROOT / "src" / "boss.h").read_text()   # (the engine and its inside)
ART = json.loads((ROOT / "build" / "boss.json").read_text())
TEX = ART["bosses"][0]
ART_H = (ROOT / "build" / "art.h").read_text()
BLANK = int(re.search(r"#define TILE_HUD_BLANK (\d+)", ART_H).group(1))


def define(name):
    return int(re.search(rf"#define {name}\s+\(?(\d+)", BOSS_C).group(1))


ROW = dict(zip(("width", "x", "bar", "step", "push", "gulp", "hands", "sip", "meter", "hat"),
               (int(v) for v in re.search(r"\{\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),"
                                          r"\s*(\d+),\s*(\d+),\s*0, \"BIG TEX", BOSS_C).groups())))
LINE1, LINE2 = re.search(r'"(BIG TEX[^"]*)", "([^"]*)"', BOSS_C).groups()
STOMP_FRAMES, HOP_FRAMES, CATCH_DX, OUTRO_FRAMES = (define(n) for n in ("STOMP_FRAMES", "HOP_FRAMES", "CATCH_DX",
                                                                          "OUTRO_FRAMES"))
SPAWN_PCT, HUD_BG = define("BOSS_SPAWN_PCT"), define("BOSS_HUD_BG")
BS_WALK, BS_GULP, BS_OUTRO = 0, 1, 5
BP_WALK, BP_STOMP, BP_GULP, BP_WINCE, BP_HAPPY = range(5)
SP_FAIL, SP_OUTRO = 4, 5
OAM_TOPPER, OBJ_TOPPER = GAME["OAM_DANCERS"], 96
BAR_ROW = 5 + 3 * ROW["bar"]                      # his bar's first wall row
TOP_Y = BAR_ROW * 8                               # ... its first pixel line
SPOUT_X, TAP_X = GAME["SPOUT_X"], GAME["TAP_X"]
OUT = ROOT / "out" / "boss"
FULL, EMPTY = 1, 2


def pair_id(p):
    return 162 + 2 * p if p < 21 else 216 + 2 * (p - 21)


def pose_cols(pose, hold=0):
    cols = [pair_id(p) for p in TEX["pose"][pose]]
    if hold and pose in (BP_WALK, BP_STOMP, BP_WINCE):
        cols[-1] = pair_id(TEX["hand"][min(hold, 3)])
    return cols


def meter_tiles(hp, meter=ROW["meter"]):
    out = []
    for k in range(7):
        if k >= (meter + 1) // 2:
            out.append(BLANK)
        else:
            out.append(HUD_BG + (3 if hp >= 2 else 2 if hp else 1))
            hp = max(hp - 2, 0)
    return [HUD_BG] + out


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


def to_fight(model, banner=False):
    """The saloon's Last call won: SHIFT CLEAR, then the boss fight's banner (banner=True: still on it), or the fight."""
    gb = to_shift(model, 0, 2)
    win(gb, 0, 2)
    run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 20)
    gb.run(3)
    assert banner_text(gb, 1) == centred("SHIFT CLEAR"), "the Last call is not the chapter's last step any more"
    run_until(gb, lambda: state(gb) == GS_GOAL, 300)
    gb.run(3)
    return gb if banner else to_goal(gb)


def still_regulars(gb):
    """The regulars stand still (a test of the boss alone: no one reaches the tap)."""
    gb.write("patron_speed", 0)
    gb.write("hurry_speed", 0)


def body(gb):
    """The tile ids of his bar's two wall rows."""
    return tilemap_row(gb, BAR_ROW, 0, 20), tilemap_row(gb, BAR_ROW + 1, 0, 20)


def assert_body(gb, x, pose, hold=0):
    top, bottom = body(gb)
    c = x // 8
    want = pose_cols(pose, hold)
    assert top[c:c + len(want)] == want and bottom[c:c + len(want)] == [t + 1 for t in want], (x, pose, hold)
    bar = venue("saloon")["bar_map"]
    assert top[:c] == bar[0:c] and bottom[:c] == bar[20:20 + c], "the wall left of him"


def hud(gb):
    return tilemap_row(gb, 0, 12, 8)


def full_on_bar(gb, b):
    st, mb = gb.read("mug_state", 20), gb.read("mug_bar", 20)
    return sum(1 for m in range(20) if st[m] == FULL and mb[m] == b)


def throw(gb, x=72):
    """A full mug on his bar at x (as if just launched and slid there): his next catch."""
    inject_mug(gb, ROW["bar"], x)


def pour(gb, fill=20):
    """The bartender (on his bar, at the tap) fills for `fill` frames and lets go: a full mug slides to him (returns
    the frames it took, the launch included)."""
    launched = gb.read("sfx_count", 9)[2]                 # SFX_LAUNCH
    gb.hold("a")
    frames(gb, fill)
    gb.release("a")
    n = fill
    while gb.read("sfx_count", 9)[2] == launched and n < fill + 10:
        frames(gb, 1)
        n += 1
    assert gb.read("sfx_count", 9)[2] != launched, "launched"
    return n


def shot(gb, name):
    OUT.mkdir(parents=True, exist_ok=True)
    gb.screenshot(OUT / f"{name}.{gb.model_name}.png", 4)


def snapshot(gb):
    """What the fight borrows, as the level shows it: patron tiles 78-233, OBJ 96-127, the palettes, OBP1."""
    s = {"bg": bytes(gb.read(0x9000 + 78 * 16, 50 * 16)) + bytes(gb.read(0x8800, 106 * 16)),
         "obj": bytes(gb.read(0x8000 + 96 * 16, 32 * 16))}
    if gb.model_name == "cgb":
        s["pal"] = [cgb_palette(gb, i) for i in range(8)] + [cgb_palette(gb, i, True) for i in range(8)]
    else:
        s["obp1"] = gb.mem(0xFF49)
    return s


# ---- the data ------------------------------------------------------------------------------------------------------
BUILT = {0: "big_tex", 2: "sasquatch", 3: "critic", 4: "yeti"}   # the venues whose boss is built (wave 1: the bosses without movement)


def test_the_table_has_a_row_per_venue_and_the_built_bosses():
    """BOSS_COUNT rows (a 10th venue adds a row, not a constant), Big Tex's as in spec 3.2 / 3.3; the built bosses'
    slots are the ones built in the story data; Big Tex's art and the meter are approved; the right size."""
    assert re.search(r"#define BOSS_COUNT\s+10\b", (ROOT / "src" / "game.h").read_text())
    assert "rows[BOSS_COUNT]" in BOSS_C
    assert ROW == dict(width=40, x=16, bar=1, step=120, push=16, gulp=40, hands=3, sip=60, meter=8, hat=16)
    assert (LINE1, LINE2) == ("BIG TEX RIDES IN", "QUENCH HIM 8 MUGS")
    assert BOSS_BUILT == set(BUILT) and BOSS_STEP == 4
    assert {r: f[len("boss_"):] for r, f in boss_rows()[1].items()} == BUILT
    assert len(TEX["pairs"]) <= ART["pairs_max"] == 30 and TEX["cols"] == 5 and len(TEX["pose"]) == 5
    assert "; Art: approved design" in (ROOT / "assets/art/boss/meter.txt").read_text()
    assert "; Art: approved design" in (ROOT / "assets/art/boss/big_tex.txt").read_text()


def boss_rows():
    """src/boss.c rows[]: (row index, width) of every row, and the hook table's rows (row index -> dispatcher)."""
    body = re.search(r"rows\[BOSS_COUNT\] = \{(.*?)\n\};", BOSS_C, re.S).group(1)
    rows = [0] * 10
    for r, w in re.findall(r"^\s*\[(\d+)\] = \{\s*(\d+),", body, re.M):
        rows[int(r)] = int(w)
    hooks = {int(r): f for r, f in re.findall(r"case (\d+): return (boss_\w+)\(ev, arg\);", BOSS_C)}
    return rows, hooks


def test_every_built_boss_has_its_row_its_hook_its_file_and_its_art():
    """The structure for parallel boss work (PLAN.md "Boss hooks as built"): every row of rows[] with a width has a row
    in the hook table (boss_call), its dispatcher is declared in src/boss.h and defined BANKED in its own banked file
    src/boss_<name>.c, which #includes its own art header (build/boss_<name>_art.h, gen_boss BOSSES) and the loaders;
    every gen_boss boss has a file; every boss slot built in the story data has a row of its own (no built slot falls
    back to Big Tex's); the extra poses fit the engine."""
    rows, hooks = boss_rows()
    header = (ROOT / "src" / "boss.h").read_text()
    names = {b["name"] for b in ART["bosses"]}
    assert set(hooks) == {r for r, w in enumerate(rows) if w}, "a row of rows[] without its hook row (or the reverse)"
    for r, fn in hooks.items():
        name = fn[len("boss_"):]
        assert name in names, f"{fn}: no art in gen_boss BOSSES"
        src = (ROOT / "src" / f"boss_{name}.c").read_text()
        assert src.startswith("//") and "#pragma bank 255" in src
        assert f'#include "boss_{name}_art.h"' in src and '#include "boss_load.h"' in src
        assert re.search(rf"uint8_t {fn}\(uint8_t ev, uint8_t arg\) BANKED \{{", src)
        assert re.search(rf"uint8_t {fn}\(uint8_t ev, uint8_t arg\) BANKED;", header)
        assert "boss_art_set()" in src and "boss_art_load()" in src
    for b in ART["bosses"]:
        assert (ROOT / "src" / f"boss_{b['name']}.c").exists()
        assert len(b["poses"]) <= ART["poses_max"] and b["poses"][:5] == ART["poses"]
        assert len(b["pairs"]) <= ART["pairs_max"]
    assert all(c < len(rows) and rows[c] for c in BOSS_BUILT), "a built boss slot plays another boss's row"


# ---- the fight -----------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_fight_follows_the_last_call(model):
    """After the Last call: the fight's banner (BOSS and Tex's two lines), the lives carried, no tips, the
    regulars' arrivals never on his bar; then Big Tex on bar 1 at x 16 (his WALK pose from VRAM ids 162.. / 216..,
    his tiles and palettes loaded), the topper over his head, the HUD's face and a full meter of 8."""
    with to_fight(model, banner=True) as gb:
        assert banner_text(gb, 1) == centred("BOSS")
        assert banner_text(gb, 2) == centred(LINE1) and banner_text(gb, 3) == centred(LINE2)
        assert gb.mem("story_step") == BOSS_STEP and gb.mem("story_reached") == BOSS_STEP
        assert (gb.mem("boss_on"), gb.mem("boss_id"), gb.mem("boss_bar"), gb.mem("boss_hp")) == (1, 0, 1, 8)
        assert gb.mem("lives") == 3 and gb.mem("tip_chance") == 0
        assert gb.mem("pat_len") == 8 and all(b != ROW["bar"] for b in gb.read("pat_buf", 8))
        assert gb.mem16("spawn_interval") == 300 * SPAWN_PCT // 100, "the saloon's 300 frames x 1.5"
        if model == "cgb":
            wall = cgb_palette(gb, 2)[0]                   # (the venue's wall: colour 0 of every patron palette)
            assert cgb_palette(gb, 4) == [wall] + TEX["pal"][1:], "BG 4: his colours over the venue's wall"
            assert cgb_palette(gb, 7, True)[1:] == TEX["pal"][1:], "OBJ 7: the topper in the same colours"
        else:
            assert gb.mem(0xFF49) == 0xE4, "DMG: the topper under OBP1 0xE4, the BG's shades"
        for p, data in enumerate(TEX["pairs"]):
            a = pair_id(p)
            vram = bytes(gb.read((0x9000 if a < 128 else 0x8000) + a * 16, 32))
            assert vram == bytes(data), f"body column {p} at {a}"
        assert bytes(gb.read(0x8000 + HUD_BG * 16, 64)) == bytes(TEX["icon"] + ART["meter"])
        assert bytes(gb.read(0x8000 + OBJ_TOPPER * 16, 64)) == bytes(TEX["hat"])
        to_goal(gb)
        gb.run(2)
        assert state(gb) == PLAYING and gb.mem("boss_x") == ROW["x"] and gb.mem("boss_state") == BS_WALK
        assert_body(gb, ROW["x"], BP_WALK)
        assert hud(gb) == meter_tiles(8)
        o = gb.oam()[OAM_TOPPER]
        assert (o["y"], o["x"], o["tile"]) == (TOP_Y + 16 - 8, ROW["x"] + ROW["hat"] + 8, OBJ_TOPPER)
        assert o["flags"] == (7 if model == "cgb" else 0x10)
        pb = gb.read("patron_bar", 16)
        assert all(pb[p] != ROW["bar"] for p, s in enumerate(gb.read("patron_state", 16)) if s), "no regular on his bar"
        frames(gb, 60)
        shot(gb, "start")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_win_the_fight_by_pouring(model):
    """The bartender at bar 1's tap pours for real: each sarsaparilla that reaches him (boss_x + 40 - 4) is a catch:
    meter -1 on the HUD, the serve score, pushed back 16 px in two hops (WINCE), the GULP pose; he holds at most 3
    empties (his hand column shows them) and sends them back by the fair-empties rule (arrivals >= empty_gap apart).
    Eight and he is satisfied: the outro (HAPPY, the mugs gone, everything frozen), CHAPTER CLEAR, the POST scene, the
    chapter saved; then the next venue's Opening has everything back."""
    with to_fight(model) as gb:
        still_regulars(gb)
        gb.press("down", 2)
        assert gb.mem("bar") == ROW["bar"]
        hands = gb.mem("boss_hands")
        assert hands == ROW["hands"]
        arrivals, seen, holds, f = [], set(), set(), 0
        catches = gb.read("sfx_count", 9)[3]
        while gb.mem("boss_hp") and f < 3000:
            if gb.mem("boss_hold") + full_on_bar(gb, 1) < hands:
                f += pour(gb)
            else:
                frames(gb, 1)
                f += 1
            st, mb, mx = gb.read("mug_state", 20), gb.read("mug_bar", 20), gb.read("mug_x", 20)
            for m in range(20):
                if st[m] == EMPTY and mb[m] == 1 and m not in seen:
                    seen.add(m)
                    arrivals.append(f + (TAP_X - mx[m]) * 2)
                if st[m] != EMPTY:
                    seen.discard(m)
            holds.add(gb.mem("boss_hold"))
            if gb.mem("boss_hp") == 5 and not (OUT / f"mid.{model}.png").exists():
                shot(gb, "mid")
        assert gb.mem("boss_hits") == 8 and max(holds) == hands, "the hands rule held him to 3"
        assert len(arrivals) >= 3
        gap = gb.mem("empty_gap")
        assert all(b - a >= gap - 2 for a, b in zip(arrivals, arrivals[1:])), (arrivals, gap)
        assert gb.read("sfx_count", 9)[3] > catches, "his empties came back to the bartender"
        assert gb.mem("lives") == 3
        frames(gb, 1)
        assert state(gb) == GS_STORY and gb.mem("story_phase") == SP_OUTRO and gb.mem("boss_state") == BS_OUTRO
        gb.run(OUTRO_FRAMES // 2)
        assert all(s == 0 for s in gb.read("mug_state", 20)), "the mugs vanish"
        assert_body(gb, gb.mem("boss_x"), BP_HAPPY)
        assert hud(gb) == meter_tiles(0)
        shot(gb, "win")
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, OUTRO_FRAMES)
        gb.run(3)
        assert banner_text(gb, 1) == centred("CHAPTER CLEAR")
        run_until(gb, lambda: state(gb) == GS_STORY and gb.mem("story_scene") == post(0), 300)
        assert (gb.mem("boss_on"), gb.mem("boss_bar")) == (0, 255)
        assert (gb.mem("story_progress"), gb.mem("story_reached")) == (1, 0), "the chapter is saved as cleared"
        settle(gb)
        skip_scene(gb)
        assert gb.mem("story_scene") == pre(1)
        skip_scene(gb)
        run_until(gb, lambda: state(gb) == GS_GOAL, 60)
        assert gb.mem("tip_chance") == GAME["TIP_CHANCE_DEFAULT"], "tips again"
        to_goal(gb)
        gb.run(2)
        restored(gb, "sports")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_meter_counts_each_drink(model):
    """Each catch takes a pip off the meter (2 pips a tile, columns 13-16 for 8; 17-19 blank), the meter and his pose
    change at once; a perfect pour scores its bonus on him too (the story's rule in every boss fight)."""
    with to_fight(model) as gb:
        still_regulars(gb)
        until(gb, lambda: gb.mem("intro_timer") == 0, 200)
        perfect_n = gb.mem("perfect_n")
        for hp in range(7, 0, -1):
            gb.write("boss_hold", 0)
            score = int.from_bytes(gb.read("score", 4), "little")
            perfect = hp == 4
            throw(gb)
            if perfect:
                m = list(gb.read("mug_state", 20)).index(FULL)
                gb.write(gb.addr("mug_timer") + m, 1)
            until(gb, lambda: gb.mem("boss_hp") == hp, 30)
            frames(gb, 2)
            assert hud(gb) == meter_tiles(hp)
            gained = int.from_bytes(gb.read("score", 4), "little") - score
            assert gained == gb.mem("serve_score") * (3 if perfect else 1), (hp, gained)
            if hp == 5:
                assert gb.mem("boss_push") or gb.mem("boss_state") == BS_GULP
                shot(gb, "meter")
                check_golden(gb, "boss_fight")
            until(gb, lambda: gb.mem("boss_state") == BS_WALK, 60)
        assert gb.mem("perfect_n") == perfect_n + 1
        gb.write("boss_hook", 3)                     # the test hook: satisfied now
        frames(gb, 1)
        assert state(gb) == GS_STORY and gb.mem("story_phase") == SP_OUTRO


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_stomps_push_back_and_the_gulp(model):
    """Unhit he stomps 8 px every 120 frames (STOMP pose for 8 frames, the topper bobbing); a catch pushes him back
    16 px in two hops 4 frames apart (WINCE), he gulps for 40 frames (no stomp meanwhile), then walks on; the push-back
    stops at his start x."""
    with to_fight(model) as gb:
        still_regulars(gb)
        until(gb, lambda: gb.mem("intro_timer") == 0, 200)
        xs = []
        for f in range(3 * ROW["step"] + 2):
            x = gb.mem("boss_x")
            frames(gb, 1)
            if gb.mem("boss_x") != x:
                xs.append((f, gb.mem("boss_x")))
                assert_body(gb, gb.mem("boss_x"), BP_STOMP)
                assert gb.oam()[OAM_TOPPER]["tile"] == OBJ_TOPPER + 2, "the hat bobs with the stomp"
        assert [x for _, x in xs] == [ROW["x"] + 8, ROW["x"] + 16, ROW["x"] + 24]
        assert xs[1][0] - xs[0][0] == ROW["step"] and xs[2][0] - xs[1][0] == ROW["step"]
        frames(gb, STOMP_FRAMES)
        assert_body(gb, ROW["x"] + 24, BP_WALK)
        throw(gb, ROW["x"] + 24 + ROW["width"] - CATCH_DX + 8)
        until(gb, lambda: gb.mem("boss_hits") == 1, 10)
        hops = []
        for f in range(ROW["gulp"] + 2):
            frames(gb, 1)
            hops.append(gb.mem("boss_x"))
            if f == 1:
                assert_body(gb, gb.mem("boss_x"), BP_WINCE, 1)
        assert hops[0] == ROW["x"] + 24 and ROW["x"] + 16 in hops and hops[-1] == ROW["x"] + 8
        assert hops.index(ROW["x"] + 8) - hops.index(ROW["x"] + 16) == HOP_FRAMES
        assert gb.mem("boss_state") == BS_WALK
        # the push-back stops at his start
        gb.write("boss_hold", 0)
        throw(gb)
        until(gb, lambda: gb.mem("boss_hits") == 2, 10)
        frames(gb, 3 * HOP_FRAMES)
        assert gb.mem("boss_x") == ROW["x"] and gb.mem("boss_push") == 0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_full_hands_let_the_mug_pass_and_break(model):
    """Holding 3 empties he catches nothing: the full mug slides on past him and breaks at the left end (a life); the
    meter is unchanged, and after the freeze he starts again at x 16 with empty hands."""
    with to_fight(model) as gb:
        still_regulars(gb)
        frames(gb, 2)
        gb.write("boss_hold", 3)
        gb.write("next_arrival", 0xFF)
        gb.write(gb.addr("next_arrival") + 1, 0xFF)   # (his empties may not go: the hands stay full)
        frames(gb, 2)
        assert gb.mem("boss_lim") == 0
        assert_body(gb, ROW["x"], BP_WALK, 3)
        throw(gb)
        seen = []
        for _ in range(60):
            frames(gb, 1)
            st, mx = gb.read("mug_state", 20), gb.read("mug_x", 20)
            seen += [mx[m] for m in range(20) if st[m] == FULL]
            if state(gb) == LIFE_LOST:
                break
        assert state(gb) == LIFE_LOST and min(seen) < ROW["x"] + ROW["width"] - CATCH_DX - 16, "it slid past him"
        assert gb.mem("boss_hp") == 8 and gb.mem("boss_hits") == 0 and gb.mem("lives") == 2
        until(gb, lambda: state(gb) == PLAYING, 200)
        frames(gb, 2)
        assert (gb.mem("boss_x"), gb.mem("boss_hold"), gb.mem("boss_hp")) == (ROW["x"], 0, 8)
        assert_body(gb, ROW["x"], BP_WALK)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_tap_costs_a_life_and_he_starts_over_with_his_meter(model):
    """His right edge reaching the tap end (136) costs a life; after the freeze he is back at x 16 (the bar redrawn: no
    copy of him left at the tap), the damage he took kept on the meter (the owner's rule: only a venue restart refills
    it)."""
    with to_fight(model) as gb:
        still_regulars(gb)
        frames(gb, 2)
        for hp in (7, 6, 5):
            gb.write("boss_hold", 0)
            throw(gb)
            until(gb, lambda: gb.mem("boss_hp") == hp, 30)
        gb.write("boss_hold", 0)                         # (no empty sent: the bartender is on bar 0)
        until(gb, lambda: gb.mem("boss_state") == BS_WALK and not gb.mem("boss_push"), 100)
        until(gb, lambda: gb.mem("intro_timer") == 0, 200)
        gb.write("boss_x", SPOUT_X - ROW["width"] - 8)
        until(gb, lambda: state(gb) == LIFE_LOST, ROW["step"] + 2)
        assert gb.mem("boss_x") + ROW["width"] == SPOUT_X and gb.mem("lives") == 2
        until(gb, lambda: state(gb) == PLAYING, 200)
        frames(gb, 3)
        assert (gb.mem("boss_x"), gb.mem("boss_hp"), gb.mem("boss_hold")) == (ROW["x"], 5, 0)
        assert_body(gb, ROW["x"], BP_WALK)
        top, bottom = body(gb)
        bar = venue("saloon")["bar_map"]
        assert top[7:17] == bar[7:17] and bottom[7:17] == bar[27:37], "nothing of him left near the tap"
        assert hud(gb) == meter_tiles(5)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_losing_the_fight_restarts_the_venue_and_puts_everything_back(model):
    """The last life lost in the fight: TRY AGAIN, then the saloon's Opening (3 lives, no PRE scene); no boss any more,
    tips back, and the level load put back all he borrowed: the patron tiles (variant C, its shift-0 pose, the back
    views), the performers' OBJ tiles, every CGB palette, DMG OBP1, his bar's wall, the HUD."""
    with to_chapter(model, 0) as ref:
        ref.run(2)
        want, want_hud = snapshot(ref), tilemap_row(ref, 0, 0, 20)
    with to_fight(model) as gb:
        frames(gb, 2)
        gb.write("lives", 1)
        gb.write("boss_x", SPOUT_X - ROW["width"] - 8)
        gb.write("intro_timer", 0)
        until(gb, lambda: state(gb) == LIFE_LOST, ROW["step"] + 2)
        until(gb, lambda: state(gb) == GS_STORY, 200)
        assert gb.mem("story_phase") == SP_FAIL and banner_text(gb, 1) == centred("TRY AGAIN")
        shot(gb, "lose")
        try_again(gb)
        assert (gb.mem("story_step"), gb.mem("story_shift"), gb.mem("lives"), gb.mem("story_restarts")) == (0, 0, 3, 1)
        assert (gb.mem("boss_on"), gb.mem("boss_bar")) == (0, 255)
        assert gb.mem("tip_chance") == GAME["TIP_CHANCE_DEFAULT"]
        assert banner_text(gb, 1) == centred("OPENING SHIFT")
        to_goal(gb)
        gb.run(2)
        got = snapshot(gb)
        assert got == want
        hud_now = tilemap_row(gb, 0, 0, 20)
        assert hud_now[7:] == want_hud[7:], "the HUD's goal and level, no face, no meter"
        restored(gb, "saloon")
        top, bottom = body(gb)
        bar = venue("saloon")["bar_map"]
        assert top == bar[0:20] and bottom == bar[20:40], "his bar's wall rows as the venue draws them"
        frames(gb, 30)
        assert gb.oam()[OAM_TOPPER]["y"] == 0


def restored(gb, theme):
    """The level's screen and VRAM as a level load leaves them (test_mg.restored's checks, less the result window's
    rows a mini-game uses): the venue's rows, the performers' OBJ tiles, every patron tile (the fight borrows variant C,
    its shift-0 pose and the back views), the banner window, LYC, DMG OBP1, the saloon's bank-1 tiles and extra
    palettes; no boss face on the HUD."""
    from test_enhanced import bank1_ok, palettes_ok
    from test_mg import PANEL_BOT, PANEL_TOP
    v = venue(theme)
    assert tilemap_row(gb, 7, 0, 20) == v["bar_map"][40:60]
    assert tilemap_row(gb, 17, 0, 20) == [v["floor_tile"]] * 20
    assert bytes(gb.read(0x8000 + 96 * 16, 32 * 16)) == bytes(v["show"]), "the performer tiles are back"
    assert tilemap_row(gb, 0, 0, 20, True) == [PANEL_TOP] * 20 and tilemap_row(gb, 2, 0, 20, True) == [PANEL_BOT] * 20
    assert gb.mem(0xFF45) == gb.mem(0xFF4A) + 22, "LYC is the banner's (BANNER_LYC)"
    if gb.model_name == "dmg":
        assert gb.mem(0xFF49) == 0xE4, "OBP1 is the game's (0xE4 in play)"
    elif theme == "saloon":
        bank1_ok(gb)
        palettes_ok(gb)
    g = gb.mem("cur_group")
    bg = bytes(gb.read(0x9000 + 78 * 16, 50 * 16)) + bytes(gb.read(0x8800, 106 * 16))
    assert bg == patron_group_tiles(g), "every patron tile is back (variant C, the back views)"
    assert HUD_BG not in tilemap_row(gb, 0, 0, 20), "no boss face on the HUD"


# ---- the regulars ----------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_regulars_keep_coming_more_slowly_on_the_other_bars(model):
    """The regulars come on in a fight (owner Q10), every 450 frames (the saloon's 300 x 1.5; the Happy hour's is 300),
    to the other three bars only, variants A and B only (variant C's tiles are his), no tips."""
    with to_fight(model) as gb:
        assert gb.mem16("spawn_interval") == 450 > 300
        spawns, last = [], gb.mem("spawned")
        for f in range(2400):
            frames(gb, 1)
            if gb.mem("boss_x") >= 64:
                gb.write("boss_x", ROW["x"])                  # (kept from the tap too)
            st, xs = gb.read("patron_state", 16), gb.read("patron_x", 16)
            for p in range(16):
                if st[p] == 1 and xs[p] >= 72:
                    gb.write(gb.addr("patron_x") + p, 40)      # (kept from the tap: a life would reset the bars)
            n = gb.mem("spawned")
            if n != last:
                spawns.append(f)
                last = n
            pb, pv = gb.read("patron_bar", 16), gb.read("patron_variant", 16)
            live = [p for p in range(16) if st[p]]
            assert all(pb[p] != ROW["bar"] for p in live) and all(pv[p] < 2 for p in live), f
            assert gb.mem16("tip_timer") == 0
        assert len(spawns) >= 4
        assert all(b - a >= 450 for a, b in zip(spawns, spawns[1:])), spawns
        assert gb.mem("boss_hp") == 8 and gb.mem("lives") == 3


# ---- the topper and the line budget ---------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_topper_gives_way_to_the_tenth_sprite(model):
    """Bar 0 (the bar above his): the bartender filling there (his lower pair on the topper's lines), the fill glass and
    7 empties on its counter are 10 objects on the topper's upper lines: the topper is left out (never an 11th); with 6
    it shows (10 on those lines)."""
    with to_fight(model) as gb:
        still_regulars(gb)
        gb.write("intro_timer", 0)
        assert gb.mem("bar") == 0
        gb.hold("a")
        frames(gb, 4)
        for x in (24, 32, 40, 48, 56, 64, 72):
            inject_mug(gb, 0, x, st=EMPTY)
        frames(gb, 3)
        assert gb.oam()[OAM_TOPPER]["y"] == 0, "10 others on its lines: the topper is left out"
        assert max(lines(gb)) == 10
        st = list(gb.read("mug_state", 20))
        m = max(i for i in range(20) if st[i] == EMPTY)
        gb.write(gb.addr("mug_state") + m, 0)
        gb.write("mugs_live", gb.mem("mugs_live") - 1)
        frames(gb, 3)
        assert gb.oam()[OAM_TOPPER]["y"] == TOP_Y + 8, "9 others: it shows"
        assert max(lines(gb)) == 10
        gb.release("a")
        frames(gb, 30)


# ---- HARD and other bosses' slots ------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["cgb"])
def test_hard_stomps_faster_with_a_hand_fewer(model):
    """Practice's HARD toggle (owner Q7; the practice menu is step 10): boss_hard set before the fight -> his step a
    quarter shorter (90 frames), his hands one fewer (2)."""
    gb = to_shift(model, 0, 2)
    with gb:
        gb.write("boss_hard", 1)
        win(gb, 0, 2)
        run_until(gb, lambda: state(gb) == GS_GOAL, 400)
        assert (gb.mem("boss_step"), gb.mem("boss_hands")) == (90, 2)


@pytest.mark.parametrize("model", ["cgb"])
def test_a_boss_slot_not_built_yet_plays_the_first_row(model):
    """The stadium's boss slot is still skipped in the story; marked built by the story_unskip test hook it starts a
    fight with boss_id 1, which has no row yet: Big Tex's row plays (nothing is indexed past the table)."""
    with to_shift(model, 1, 2) as gb:
        gb.write("story_unskip", 1 << BOSS_STEP)
        win(gb, 1, 2)
        run_until(gb, lambda: state(gb) == GS_GOAL, 400)
        gb.run(3)
        assert (gb.mem("boss_on"), gb.mem("boss_id"), gb.mem("boss_hp")) == (1, 1, 8)
        assert banner_text(gb, 1) == centred("BOSS")
