# docs/minigames_bosses.md 4.9: MONKEY BUSINESS (src/mk.c), the jungle zoo's mini-game, on the framework (src/mg.c): the screen (the
# approved reading 1 / G1 art, its palettes, the DMG registers), hopping and shooing (timings, the buffered command, the held
# repeat, the whiff lockout), scoring (shooed 100, quick +100, the parrot -200), the pops (the lid's 20-frame rattle, U, the
# interval, the caps, the parrot from 15 s), the reachability rule (a scripted bot never loses a coconut), thefts and the one
# runner, the end (time up, an empty pile, the leftover coconuts), medals, sprites per line over whole games and a forced worst
# case, STORY / ARCADE reaching it in chapter 9, BONUS > MINI GAMES, what is put back when it is left.
#
# Harness notes (as tests/test_mg_taiko.py): PyBoy's frame ends a few lines after the game's logic has begun, so exact tests read
# in a paused frame (`snap`: the VBlank copy and the OAM DMA have caught up there, so VRAM and OAM read right after are the state's)
# and a held key is read by the update after the one in progress.
import pytest
from conftest import ROOT, check_golden, hold_stage_anim, logic_paused
from mk_helpers import (ART, MA_HOP, MA_NONE, MA_SHOO, MC_AFTER, MC_FLY, MC_IDLE, MC_RATTLE, MC_UP, MG_MONKEY, MK_BG, MK_OBJ,
                        ML_PARROT, ML_QUICK, ML_SHOOED, ML_THEFT, ML_WHIFF, STATE_SIZE, ZOO, bot_keys, glyph, mk, mk_define,
                        poke, poke_crate, run_bot, LAYOUT)
from test_bonus import lines
from test_flow import GS_GOAL, LEVEL_CLEAR, TITLE, run_until, state, tilemap_row
from test_mg import (GS_MGLIST, GS_MINI, MG_COUNT, MG_END, MG_PLAY, MG_PRACTICE, MG_RESULT, MG_STORY, RESULT_MIN, frames, mg_enter,
                     score, text, to_play, to_result, until)
from test_mg_list import release_built  # noqa: F401  (the fixture: `make release`)

pytestmark = pytest.mark.timeout(300)

MEDAL_NONE, MEDAL_BRONZE, MEDAL_SILVER, MEDAL_GOLD = range(4)
SEED = 0x5A17
OUT = ROOT / "out" / "mk"
OFF = ART["off"]
(TIME, COCO, RATTLE, PEEK, U0, U_MIN, U_STEP, GAP0, GAP_MIN, GAP_STEP, FIRST_POP, CAP_LATE, PARROT_AT, HOP, REPEAT, SHOO, HIT, LOCK,
 SPARE, QUICK, AFTER, FLY_END, RUN_SPEED, PUFF_LEN, FAIL_LEN) = (mk_define(n) for n in (
    "MK_TIME", "MK_COCO", "MK_RATTLE", "MK_PEEK", "MK_U0", "MK_U_MIN", "MK_U_STEP", "MK_GAP0", "MK_GAP_MIN", "MK_GAP_STEP",
    "MK_FIRST_POP", "MK_CAP_LATE", "MK_PARROT_AT", "MK_HOP", "MK_REPEAT", "MK_SHOO", "MK_HIT", "MK_LOCK", "MK_SPARE", "MK_QUICK",
    "MK_AFTER", "MK_FLY_END", "MK_RUN_SPEED", "MK_PUFF_LEN", "MK_FAIL_LEN"))
OAM_PUFF, OAM_DUSTER, OAM_SPIG, OAM_RUN, OAM_OCC = (mk_define(n) for n in ("OAM_PUFF", "OAM_DUSTER", "OAM_SPIG", "OAM_RUN", "OAM_OCC"))
MEDAL_AT = (2500, 5000, 8000)                    # src/mg.c's medal_at row of Monkey Business
SFX_LAUNCH, SFX_CATCH, SFX_BREAK, SFX_SERVE, SFX_COIN, SFX_LIFE, SFX_SHAKE = 2, 3, 4, 5, 6, 7, 8
S_PALETTE = 0x10
BT_IDLE, BT_WALK1, BT_WALK2, BT_FILL, BT_SLIDE, BT_CATCH, BT_FAIL = range(7)
BT_TILES = 8                                     # the bartender's OBJ tiles a frame
HOP_DX = (0, 5, 11, 16, 21, 27, 32)
DUSTER_F = (0, 1, 0, 2, 0, 1, 2, 0)
PILE_OF = (5, 4, 3, 3, 2, 2, 1, 1, 0)
SPR = ART["spr"]                                 # MKS_*: peek, run0, run1, up, ppeek, perch, flap0, flap1: (left, right) OBJ tile ids
MKS_PEEK, MKS_RUN0, MKS_RUN1, MKS_UP, MKS_PPEEK, MKS_PERCH, MKS_FLAP0, MKS_FLAP1 = range(8)
SPIG_X = lambda k: 4 + 32 * k                    # noqa: E731  the Spigoteer in front of crate k
CRATE_X = lambda k: 8 + 32 * k                   # noqa: E731


def monkey(model, mode=MG_PRACTICE, seed=SEED, quiet=True):
    """A booted rom on the title, then Monkey Business in practice (or `mode`); sound off. `quiet`: the first pop is far off (the
    scheduler is not under test) so a test can set its crates by hand."""
    from test_scores import booted
    rom = booted(model)
    hold_stage_anim(rom)
    rom.write("sound_on", 0)
    mg_enter(rom, MG_MONKEY, mode, seed)
    return rom


def shot(gb, name):
    OUT.mkdir(parents=True, exist_ok=True)
    gb.screenshot(OUT / f"{name}.{gb.model_name}.png", 4)


def oam(gb, i):
    a = 0xFE00 + 4 * i
    return dict(y=gb.mem(a), x=gb.mem(a + 1), tile=gb.mem(a + 2), prop=gb.mem(a + 3))


def snap(gb):
    """The state as of a whole update, read in a paused frame."""
    with logic_paused(gb):
        return mk(gb)


def step(gb, n=1):
    """n frames, then the state of the update just done."""
    frames(gb, n)
    return snap(gb)


def tap(gb, key, n=2):
    gb.hold(key)
    frames(gb, n)
    gb.release(key)


def quiet(gb, n=255):
    """No pop for a while (the scheduler's countdown poked up)."""
    poke(gb, next=n)


def play(model, seed=SEED):
    """Monkey Business at its first play frame, no pop coming."""
    gb = monkey(model, seed=seed)
    to_play(gb)
    frames(gb, 2)
    quiet(gb)
    return gb


def put_crate(gb, k, st=MC_UP, kind=0, t=0, u=None):
    """Crate k set by hand (u: its up time; the default is the game's U now + the peek)."""
    u = (6 + mk(gb)["unow"]) if u is None else u
    poke_crate(gb, k, st=st, kind=kind, t=t, u=u)


def bank1(gb, col, row):
    gb.pb.memory[0xFF4F] = 1
    try:
        return gb.pb.memory[0x9800 + row * 32 + col]
    finally:
        gb.pb.memory[0xFF4F] = 0


def map_row(gb, row):
    return tilemap_row(gb, row, 0, 20)


def tile_bytes(gb, t):
    a = 0x9000 + t * 16 if t < 128 else 0x8800 + (t - 128) * 16
    return list(gb.read(a, 16))


def all_lines(gb):
    return max(lines(gb))


# ---- the screen ------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_screen_and_its_art(model):
    """The intro: the banner, the HUD (the pips and the timer), every row of the approved art as the generator laid it out, the
    tiles and palettes, the sprites, the DMG registers."""
    with monkey(model) as gb:
        assert gb.mem("mg_id") == MG_MONKEY and gb.mem("mg_mode") == MG_PRACTICE and gb.mem("mg_phase") == 0
        frames(gb, 30)
        assert text(gb, 2) == "MONKEY BUSINESS" and text(gb, 3) == "A SHOO NOT PARROTS"
        pips = MK_BG + OFF["pips"]
        assert tilemap_row(gb, 0, 8, 8) == [pips] * 8
        assert tilemap_row(gb, 0, 16, 4) == [glyph("T"), glyph("0"), glyph("4"), glyph("5")]
        s = mk(gb)
        assert (s["coco"], s["time"], s["pos"], s["pile_shown"]) == (COCO, TIME, 2, 0)
        # the art's tiles
        got = [b for t in range(MK_BG, MK_BG + ART["n_bg"]) for b in tile_bytes(gb, t)]
        assert got == ART["bg"], "BG tiles"
        got = [b for t in range(MK_OBJ, MK_OBJ + len(ART["obj_a"]) // 16) for b in gb.read(0x8000 + t * 16, 16)]
        assert got == ART["obj_a"], "OBJ tiles 56-91"
        got = [b for t in range(96, 96 + len(ART["obj_b"]) // 16) for b in gb.read(0x8000 + t * 16, 16)]
        assert got == ART["obj_b"], "OBJ tiles 96-"
        # the awning band's rows 1 and 4 (the banner covers 2-3 until the first play frame), row 11 is wall again, the crates, the
        # pile and the helmet, the counter
        band = [MK_BG + OFF["band"] + i for i in ART["band_map"]]
        assert map_row(gb, 1) == band[0:20] and map_row(gb, 4) == band[60:80]
        assert map_row(gb, 11) == map_row(gb, 9), "no counter at row 11: the zoo wall"
        cm = ART["crate_map"]
        for k in range(5):
            assert tilemap_row(gb, 12, 1 + 4 * k, 2) == [MK_BG + OFF["crate"] + cm[0], MK_BG + OFF["crate"] + cm[1]]
            assert tilemap_row(gb, 13, 1 + 4 * k, 2) == [MK_BG + OFF["crate"] + cm[2], MK_BG + OFF["crate"] + cm[3]]
        pm = ART["pile_map"]
        for r in range(3):
            assert tilemap_row(gb, 5 + r, 16, 4) == [MK_BG + OFF["pile"] + pm[r * 4 + c] for c in range(4)]
        assert tilemap_row(gb, 7, 14, 2) == [MK_BG + OFF["helmet"], MK_BG + OFF["helmet"] + 1]
        c0 = MK_BG + OFF["counter"]
        assert map_row(gb, 14) == [c0] * 20
        assert map_row(gb, 15) == map_row(gb, 16) == [c0 + 1 + (c & 1) for c in range(20)]
        # the sprites: the Spigoteer in front of crate 2 (idle), nothing else
        spig = oam(gb, OAM_SPIG)
        assert (spig["x"], spig["y"]) == (SPIG_X(2) + 8, 112 + 16) and spig["tile"] == BT_IDLE * BT_TILES
        for i in list(range(OAM_PUFF, OAM_PUFF + 3)) + list(range(OAM_RUN, OAM_RUN + 12)):
            assert oam(gb, i)["y"] == 0, i
        if model == "cgb":
            assert [bank1(gb, 3, r) for r in (1, 4)] == [5, 5] and bank1(gb, 3, 2) == 1, "the awning's palette; the banner's is the HUD's"
            assert bank1(gb, 2, 12) == 2 and bank1(gb, 18, 6) == 3 and bank1(gb, 14, 7) == 3 and bank1(gb, 5, 15) == 6
            assert bank1(gb, 8, 0) == 1, "the HUD's palette"
        else:
            assert gb.mem(0xFF49) == 0xE4 and gb.mem(0xFF48) == 0xD0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_colours_are_the_approved_ones(model):
    """CGB: the G1 leafy greens of the awning and the crates, the counter's wood; DMG: the four greys only."""
    from PIL import Image
    with play(model) as gb:
        frames(gb, 3)
        OUT.mkdir(parents=True, exist_ok=True)
        gb.screenshot(OUT / f"colours.{model}.png", 1)
    px = Image.open(OUT / f"colours.{model}.png").convert("RGB")
    if model == "dmg":
        assert len({px.getpixel((x, y)) for x in range(160) for y in range(144)}) <= 4
        return
    near = lambda a, b: all(abs(x - y) <= 8 for x, y in zip(a, b))                 # noqa: E731
    assert near(px.getpixel((10, 12)), (0x48, 0xA8, 0x38)), "the awning's green stripe"
    assert near(px.getpixel((2, 12)), (0xE0, 0xF4, 0xA8)), "its cream stripe"
    assert near(px.getpixel((16, 98)), (0x58, 0xB8, 0x38)), "the crate's face"
    assert near(px.getpixel((100, 70)), (0x23, 0x4E, 0x5C)), "the zoo wall"


# ---- hopping and shooing ---------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_hop_takes_six_frames_and_moves_32_px(model):
    """Right: the Spigoteer is at crate 3 after 6 frames, his x follows the 6-step table, the walk frames show; then idle."""
    with play(model) as gb:
        xs, acts = [], []
        tap(gb, "right")
        for _ in range(10):
            s = snap(gb)
            acts.append((s["act"], s["act_t"]))
            xs.append(oam(gb, OAM_SPIG)["x"] - 8)
            frames(gb, 1)
        hop = [(a, t) for a, t in acts if a == MA_HOP]
        assert [t for _, t in hop] == list(range(hop[0][1], hop[0][1] + len(hop))) and hop[0][1] <= 1 and hop[-1][1] == 5, acts
        assert acts[-1] == (MA_NONE, 0) and xs[-1] == SPIG_X(3)
        for (a, t), x in zip(acts, xs):
            if a == MA_HOP:
                assert x == SPIG_X(2) + HOP_DX[t], (t, x)
        s = snap(gb)
        assert (s["pos"], s["from"]) == (3, 2)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_hop_frames_and_the_walk_pose(model):
    """The first 3 frames of a hop are the first walk frame, the rest the second."""
    with play(model) as gb:
        tap(gb, "left")
        seen = {}
        for _ in range(8):
            s = snap(gb)
            if s["act"] == MA_HOP:
                seen[s["act_t"]] = oam(gb, OAM_SPIG)["tile"] // BT_TILES
            frames(gb, 1)
        assert all(f == (BT_WALK1 if t < 3 else BT_WALK2) for t, f in seen.items()) and len(seen) >= 5, seen


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_held_direction_repeats_every_10_frames_and_stops_at_the_edge(model):
    """Held Left from crate 2: hops at 0, 10, then nothing at crate 0 (the edge); one press is one hop."""
    with play(model) as gb:
        starts, last = [], None
        gb.hold("left")
        for n in range(50):
            frames(gb, 1)
            s = snap(gb)
            if s["act"] == MA_HOP and s["act_t"] == 0 and last != s["from"]:
                starts.append((n, s["from"], s["pos"]))
                last = s["from"]
        gb.release("left")
        assert [(f, p) for _, f, p in starts] == [(2, 1), (1, 0)], starts
        assert 8 <= starts[1][0] - starts[0][0] <= 12
        s = snap(gb)
        assert s["pos"] == 0 and s["act"] == MA_NONE
        tap(gb, "left")
        frames(gb, 8)
        assert snap(gb)["pos"] == 0
    with play(model) as gb:
        poke(gb, pos=4, **{"from": 4})
        frames(gb, 1)
        tap(gb, "right")
        frames(gb, 8)
        assert snap(gb)["pos"] == 4


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_command_pressed_during_a_hop_is_kept_and_runs_when_it_ends(model):
    """Right, then A while hopping: the shoo starts as the hop ends, at the new crate (a monkey there is shooed)."""
    with play(model) as gb:
        put_crate(gb, 3, MC_UP, 0, t=10)
        tap(gb, "right")
        frames(gb, 2)
        tap(gb, "a")
        seen = []
        for _ in range(24):
            frames(gb, 1)
            seen.append(snap(gb))
        assert any(s["act"] == MA_SHOO for s in seen)
        first = next(i for i, s in enumerate(seen) if s["act"] == MA_SHOO)
        assert seen[first - 1]["act"] in (MA_HOP, MA_NONE) and seen[first]["pos"] == 3
        assert seen[-1]["shooed"] == 1


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_shoo_takes_8_frames_the_hit_is_on_the_4th_and_the_duster_swings(model):
    """The shoo pose is the mirrored fill frame; the duster's frames are the mock-up's; a monkey up is shooed on frame 4 (a puff)."""
    with play(model) as gb:
        put_crate(gb, 2, MC_UP, 0, t=30)
        tap(gb, "a")
        rows = []
        for _ in range(12):
            s = snap(gb)
            rows.append((s["act"], s["act_t"], s["shooed"], oam(gb, OAM_DUSTER)["y"], oam(gb, OAM_DUSTER)["tile"],
                         oam(gb, OAM_SPIG)["tile"] // BT_TILES, oam(gb, OAM_SPIG)["prop"] & 0x20, s["c"][2]["st"]))
            frames(gb, 1)
        shoo = [r for r in rows if r[0] == MA_SHOO]
        assert [r[1] for r in shoo] == list(range(shoo[0][1], shoo[0][1] + len(shoo))) and shoo[0][1] <= 1 and shoo[-1][1] == 7, rows
        for r in shoo:
            assert r[5] == BT_FILL and r[6] == 0x20 and r[3] != 0
            f = DUSTER_F[r[1]]
            assert r[4] == ART["duster"][f][0], r
            assert r[2] == (1 if r[1] >= HIT else 0) and r[7] == (MC_IDLE if r[1] >= HIT else MC_UP), r
        assert rows[-1][0] == MA_NONE and rows[-1][3] == 0


# ---- scoring ----------------------------------------------------------------------------------------------------------------
def shoo_at(gb, k):
    """Walk to crate k (taps) and shoo; returns the state when it is over."""
    while mk(gb)["pos"] != k:
        tap(gb, "right" if k > mk(gb)["pos"] else "left")
        frames(gb, HOP)
    tap(gb, "a")
    frames(gb, SHOO + 1)
    return snap(gb)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("t,pts,last", [(0, 200, ML_QUICK), (QUICK - 8, 200, ML_QUICK), (QUICK - 1, 100, ML_SHOOED),
                                          (60, 100, ML_SHOOED)])
def test_a_monkey_shooed_scores_100_and_100_more_within_20_frames_of_the_lid(model, t, pts, last):
    """The shoo's hit is on its 4th frame (a few frames after the press): up to 12 frames up when the shoo starts is within 20 when it lands, 19 is not. A peek counts."""
    with play(model) as gb:
        put_crate(gb, 2, MC_UP, 0, t=t)
        s = shoo_at(gb, 2)
        assert gb.mem16("mg_score") == pts and score(gb) >= pts and s["last"] == last and s["shooed"] == 1
        assert s["puff_t"] > 0 or s["act"] == MA_NONE


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_rattling_crate_or_an_empty_one_is_a_whiff_with_a_lockout(model):
    """Shooing a crate with nothing up scores nothing and locks the Spigoteer out for 12 frames after the swing (the fail pose);
    nothing pressed then is kept; afterwards he can hop and shoo again."""
    with play(model) as gb:
        put_crate(gb, 2, MC_RATTLE, 0, t=2)
        tap(gb, "a")
        locked = []
        for _ in range(30):
            frames(gb, 1)
            s = snap(gb)
            if s["lock"] and s["act"] == MA_NONE:
                locked.append(s["lock"])
                if len(locked) == 3:
                    tap(gb, "right")                  # ignored: not kept either
        assert s["whiffs"] == 1 and s["last"] == ML_WHIFF and gb.mem16("mg_score") == 0
        assert s["pos"] == 2 and s["pend"] == 0
        assert len(locked) >= 10 and locked[0] == LOCK
        tap(gb, "right")
        frames(gb, HOP + 1)
        assert snap(gb)["pos"] == 3


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_mashing_a_is_punished(model):
    """A pressed every other frame for 240 frames at a crate with nothing: each whiff is the 8-frame shoo and the 12-frame lockout,
    so about 12 of them (a game that let the shoos run on every press would make 30)."""
    with play(model) as gb:
        n = 0
        prev = 0
        for _ in range(120):
            gb.hold("a")
            frames(gb, 1)
            gb.release("a")
            frames(gb, 1)
        s = snap(gb)
        assert 10 <= s["whiffs"] <= 12, s["whiffs"]
        assert gb.mem16("mg_score") == 0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_parrot_costs_200_never_below_zero_and_flies_off(model):
    """Shooing the parrot: -200 from what the game earned (not below 0), no lockout; it flies off up and right and the crate
    is free again after its flight; left alone it flies off by itself after the same time."""
    with play(model) as gb:
        gb.write("mg_score", 0)
        put_crate(gb, 2, MC_UP, 1, t=3)
        s = shoo_at(gb, 2)
        assert gb.mem16("mg_score") == 0 and s["last"] == ML_PARROT and s["parrots"] == 1 and s["lock"] == 0
        assert s["c"][2]["st"] in (MC_FLY, MC_IDLE)
    with play(model) as gb:
        mg_points = 700
        gb.write("mg_score", mg_points & 255)
        gb.write(gb.addr("mg_score") + 1, mg_points >> 8)
        put_crate(gb, 1, MC_UP, 1, t=3)
        s = shoo_at(gb, 1)
        assert gb.mem16("mg_score") == 500
        # the flight: the parrot's y rises 3 px a frame from the crate's rim, x 1 px a frame; the crate is closed after FLY_END
        put_crate(gb, 4, MC_FLY, 1, t=0)
        pos = {}
        for _ in range(FLY_END + 30):
            frames(gb, 1)
            s = snap(gb)
            o = oam(gb, OAM_OCC + 8)
            if s["c"][4]["st"] == MC_IDLE:
                break
            if s["c"][4]["st"] == MC_FLY and o["y"]:
                pos[s["c"][4]["t"]] = (o["x"] - 8, o["y"] - 16)
        for t, (x, y) in pos.items():
            assert (x, y) == (CRATE_X(4) + t, 81 - 3 * t), (t, x, y)
        assert s["c"][4]["st"] == MC_IDLE and max(pos) >= 20
    with play(model) as gb:
        put_crate(gb, 3, MC_UP, 1, t=0, u=30)
        for _ in range(40):
            frames(gb, 1)
        s = snap(gb)
        assert s["c"][3]["st"] in (MC_FLY, MC_IDLE) and s["stolen"] == 0 and s["coco"] == COCO and gb.mem16("mg_score") == 0


# ---- thefts ---------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_monkey_up_too_long_grabs_a_coconut_and_runs_off(model):
    """At its time the monkey takes a coconut (the pips, the pile's state), the crate stays open 24 frames, the runner moves
    4 px a frame away from the middle and is gone off screen."""
    with play(model) as gb:
        put_crate(gb, 1, MC_UP, 0, t=0, u=20)
        xs = []
        for _ in range(40):
            frames(gb, 1)
            s = snap(gb)
            if s["run_on"]:
                o = oam(gb, OAM_RUN)
                xs.append((s["run_t"], o["x"] - 8 if o["y"] else None))
        s = snap(gb)
        assert s["coco"] == COCO - 1 and s["stolen"] == 1 and s["last"] == ML_THEFT and s["run_on"] == 0
        assert s["pile_shown"] == PILE_OF[COCO - 1]
        pips = MK_BG + OFF["pips"]
        assert tilemap_row(gb, 0, 8, 8) == [pips] * 7 + [pips + 1]
        pm = ART["pile_map"]
        st = PILE_OF[COCO - 1]
        assert tilemap_row(gb, 5, 16, 4) == [MK_BG + OFF["pile"] + pm[st * 12 + c] for c in range(4)]
        assert [x for t, x in xs if x is not None and t > 0] == [CRATE_X(1) - RUN_SPEED * t for t, x in xs if x is not None and t > 0]
        assert s["c"][1]["st"] in (MC_AFTER, MC_IDLE)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_at_most_one_runner_a_second_thief_waits_up(model):
    """Two monkeys due on the same frame: the first runs, the second stays up (and can still be shooed) until the runner has gone."""
    with play(model) as gb:
        put_crate(gb, 2, MC_UP, 0, t=0, u=20)
        put_crate(gb, 4, MC_UP, 0, t=0, u=20)
        runs = 0
        second_wait = None
        prev = 0
        for _ in range(60):
            frames(gb, 1)
            s = snap(gb)
            assert s["stolen"] <= 2
            if s["stolen"] == 1 and s["run_on"]:
                assert s["c"][4]["st"] == MC_UP or s["c"][2]["st"] == MC_UP, "the other one waits"
                second_wait = True
            if s["stolen"] == 2 and prev == 1:
                assert not s["run_on"] or s["run_t"] <= 1
            prev = s["stolen"]
        assert snap(gb)["stolen"] == 2 and second_wait
    with play(model) as gb:                     # the waiting one can be shot
        put_crate(gb, 2, MC_UP, 0, t=0, u=20)
        put_crate(gb, 4, MC_UP, 0, t=0, u=20)
        poke(gb, pos=4, **{"from": 4})
        for _ in range(40):
            frames(gb, 1)
            s = snap(gb)
            if s["stolen"] == 1 and s["run_on"]:
                break
        if s["c"][4]["st"] == MC_UP:
            tap(gb, "a")
            frames(gb, SHOO)
            assert snap(gb)["shooed"] == 1 and snap(gb)["stolen"] == 1


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_last_coconut_ends_the_game(model):
    """With one coconut left a theft empties the pile: ALL GONE, the game ends (no leftover bonus), the result follows."""
    with play(model) as gb:
        poke(gb, coco=1)
        put_crate(gb, 2, MC_UP, 0, t=0, u=10)
        until(gb, lambda: gb.mem("mg_phase") == MG_END, 60)
        frames(gb, 3)
        assert text(gb, 9) == "ALL GONE"
        assert snap(gb)["coco"] == 0 and gb.mem16("mg_score") == 0
        until(gb, lambda: gb.mem("mg_phase") == MG_RESULT, 90)


# ---- the pops ---------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_pop_rattles_20_frames_peeks_6_and_stays_up_u(model):
    """The first pop at the scheduler's FIRST_POP: the lid rattles RATTLE frames (the crate's tile swap), the monkey peeks PEEK
    frames, stays up until its u (PEEK + U) and then grabs."""
    with monkey(model) as gb:
        to_play(gb)
        log = []
        for _ in range(240):
            frames(gb, 1)
            s = snap(gb)
            cs = [c for c in s["c"] if c["st"] != MC_IDLE]
            log.append((s["time"], [dict(c) for c in cs], oam(gb, OAM_OCC), s["unow"], s["pops"]))
        pops = [i for i in range(1, len(log)) if log[i][4] > log[i - 1][4]]
        assert pops and pops[0] <= FIRST_POP + 4
        # the first crate: count the frames of each state
        first = next(i for i, l in enumerate(log) if l[1])
        crate_of = lambda l: next(c for c in l[1])                                  # noqa: E731
        seq = [crate_of(l)["st"] for l in log[first:first + RATTLE + 8]]
        assert seq[:RATTLE - 1].count(MC_RATTLE) == RATTLE - 1 and MC_UP not in seq[:RATTLE - 1]
        assert seq[RATTLE - 1:RATTLE + 1] and MC_UP in seq[RATTLE - 1:RATTLE + 2]
        c = next(c for c in log[first + RATTLE + 3][1] if c["st"] == MC_UP)
        assert c["u"] == PEEK + U0 and c["kind"] == 0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_peek_then_the_bust_and_the_lid_frames(model):
    """A crate's picture: closed, the lid rattling between two frames every 2 frames, open once the monkey is up; the monkey's
    sprite is the peek for 6 frames, then the bust, at the crate's x on y 81."""
    with play(model) as gb:
        put_crate(gb, 3, MC_RATTLE, 0, t=0, u=96)
        seen_lid = []
        for _ in range(RATTLE + 2):
            frames(gb, 1)
            s = snap(gb)
            seen_lid.append(s["cshown"][3])
        assert set(seen_lid[:RATTLE - 1]) <= {1, 2} and 1 in seen_lid and 2 in seen_lid and seen_lid[-1] == 3
        cm = ART["crate_map"]
        assert tilemap_row(gb, 12, 13, 2) == [MK_BG + OFF["crate"] + cm[12], MK_BG + OFF["crate"] + cm[13]], "open"
        sprites = []
        for _ in range(12):
            frames(gb, 1)
            s = snap(gb)
            if s["c"][3]["st"] == MC_UP:
                o = oam(gb, OAM_OCC + 6)
                sprites.append((s["c"][3]["t"], o["tile"], o["x"] - 8, o["y"] - 16))
        for t, tile, x, y in sprites:
            assert (x, y) == (CRATE_X(3), 81) and tile == SPR[MKS_PEEK if t < PEEK else MKS_UP][0], (t, tile)
        assert any(t < PEEK for t, *_ in sprites) and any(t >= PEEK for t, *_ in sprites)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_u_and_the_interval_fall_with_the_time(model):
    """U 90 -> 45 at 30 s (a step every 40 frames), the pop interval 60 -> 24 at 45 s (a step every 75); the caps and the parrot's
    start follow the time left."""
    with play(model) as gb:
        quiet(gb, 255)
        seen = {}
        for _ in range(2700 // 20):
            poke(gb, next=255)
            frames(gb, 20)
            s = snap(gb)
            seen[TIME - s["time"]] = (s["unow"], s["gap"])
        el = sorted(seen)
        assert seen[el[0]] == (U0, GAP0) or seen[el[0]][0] >= U0 - 1
        e30 = min(e for e in el if e >= 1800)
        assert seen[e30][0] == U_MIN and all(seen[e][0] > U_MIN for e in el if e < 1800 - 40)
        assert seen[el[-1]][1] <= GAP_MIN + 1 and seen[el[-1]][0] == U_MIN
        assert all(a[0] >= b[0] and a[1] >= b[1] for a, b in zip((seen[e] for e in el), (seen[e] for e in el[1:])))


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_at_most_two_up_before_20_s_three_after_and_parrots_from_15_s(model):
    """Nobody shoos: crates (rattling, up, a parrot flying) occupied never exceed 2 until 20 s then 3; a parrot only from 15 s."""
    with monkey(model) as gb:
        to_play(gb)
        peak_early = peak_late = 0
        parrot_at = None
        gb.write("mg_score", 0)
        for _ in range(900):
            frames(gb, 3)
            poke(gb, coco=8)                                  # (the thieves cannot end it)
            s = snap(gb)
            occ = sum(1 for c in s["c"] if c["st"] in (MC_RATTLE, MC_UP, MC_FLY))
            if s["time"] > CAP_LATE:
                peak_early = max(peak_early, occ)
            else:
                peak_late = max(peak_late, occ)
            if parrot_at is None and any(c["kind"] and c["st"] != MC_IDLE for c in s["c"]):
                parrot_at = s["time"]
        assert peak_early == 2 and peak_late == 3, (peak_early, peak_late)
        assert parrot_at is not None and parrot_at <= mk_define("MK_PARROT_AT")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_pop_that_cannot_be_reached_waits(model):
    """The reachability rule: with the Spigoteer at crate 0 and a monkey about to grab at crate 4 (20 frames left: 24 frames of
    hops), nothing new pops however long the scheduler tries; the same monkey with 100 frames left lets pops through."""
    with play(model) as gb:
        poke(gb, pos=0, **{"from": 0})
        put_crate(gb, 4, MC_UP, 0, t=76, u=96)
        poke(gb, next=0)
        pops = snap(gb)["pops"]
        for _ in range(12):
            poke(gb, next=0)
            frames(gb, 1)
        assert snap(gb)["pops"] == pops, "the pop waits"
    with play(model) as gb:
        poke(gb, pos=0, **{"from": 0})
        put_crate(gb, 4, MC_UP, 0, t=0, u=96)
        poke(gb, next=0)
        pops = snap(gb)["pops"]
        for _ in range(6):
            frames(gb, 1)
        assert snap(gb)["pops"] == pops + 1


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("seed", [0x5A17, 0x1234, 0x0077, 0xBEEF, 0xACE1, 0x0F0F])
def test_a_bot_never_loses_a_coconut_and_the_sprites_fit(model, seed):
    """The scripted perfect bot (nearest deadline first, reacting at once) clears the 45 s with no theft at every seed: the
    reachability rule never asks for the impossible; every frame <= 10 sprites a line (9 is the worst the engine makes)."""
    with monkey(model, seed=seed) as gb:
        to_play(gb)
        worst = [0]
        s = run_bot(gb, lambda g, n: frames(g, n, worst), lambda s: s["st"] == 1)
        assert s["stolen"] == 0 and s["coco"] == COCO and s["whiffs"] == 0 and s["time"] == 0 and s["shooed"] >= 40
        assert s["pops"] >= 60, "about 45 s / the interval"
        assert worst[0] <= 9
        until(gb, lambda: gb.mem("mg_phase") == MG_RESULT, 90)
        assert gb.mem("mg_medal") == MEDAL_GOLD and gb.mem16("mg_score") >= MEDAL_AT[2]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_slow_bot_loses_coconuts_and_may_lose_them_all(model):
    """A bot that only reacts 45 frames after the lid opens loses all 8 coconuts well before 45 s: ALL GONE, a low medal."""
    with monkey(model) as gb:
        to_play(gb)
        s = run_bot(gb, frames, lambda s: s["st"] == 1, keys=lambda st: bot_keys(st, 45))
        assert s["coco"] == 0 and s["stolen"] == COCO and s["time"] > 300
        until(gb, lambda: gb.mem("mg_phase") == MG_RESULT, 90)
        assert gb.mem("mg_medal") <= MEDAL_BRONZE


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_forced_worst_case_stays_within_the_sprite_limit(model):
    """The most the engine allows at once: three crates occupied (a monkey, a monkey, a parrot taking off at the rim), a runner and
    the puff on the same lines: 9 a line, never more than 10."""
    with play(model) as gb:
        put_crate(gb, 0, MC_UP, 0, t=10)
        put_crate(gb, 2, MC_UP, 0, t=10)
        put_crate(gb, 4, MC_FLY, 1, t=1)
        poke(gb, run_on=1, run_k=3, run_t=1, puff_t=PUFF_LEN, puff_x=CRATE_X(2) + 4, pos=3, **{"from": 3})
        worst = 0
        for _ in range(8):
            frames(gb, 1)
            worst = max(worst, all_lines(gb))
        assert 8 <= worst <= 10


# ---- the end, medals --------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_time_up_pays_200_a_coconut_left(model):
    """At 45 s: TIME UP (the HUD timer reads T000), +200 for each coconut left, then the result."""
    with play(model) as gb:
        poke(gb, coco=5)
        poke(gb, time=3)
        until(gb, lambda: gb.mem("mg_phase") == MG_END, 20)
        frames(gb, 3)
        assert text(gb, 9) == "TIME UP" and gb.mem16("mg_score") == 1000
        assert tilemap_row(gb, 0, 16, 4)[1:] == [glyph("0")] * 3
        until(gb, lambda: gb.mem("mg_phase") == MG_RESULT, 90)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("points,medal", [(0, MEDAL_NONE), (2499, MEDAL_NONE), (2500, MEDAL_BRONZE), (4999, MEDAL_BRONZE),
                                            (5000, MEDAL_SILVER), (7999, MEDAL_SILVER), (8000, MEDAL_GOLD)])
def test_medals_by_score(model, points, medal):
    with play(model) as gb:
        to_result(gb, points)
        assert gb.mem("mg_medal") == medal
        assert text(gb, 1, True, x0=4) == "MONKEY BUSINESS"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_hud_timer_counts_down_from_45(model):
    """T045 at the start; the seconds follow the frames left (rounded up)."""
    with play(model) as gb:
        assert tilemap_row(gb, 0, 16, 4) == [glyph("T"), glyph("0"), glyph("4"), glyph("5")]
        poke(gb, time=62)
        frames(gb, 2)
        assert tilemap_row(gb, 0, 16, 4) == [glyph("T"), glyph("0"), glyph("0"), glyph("2")]
        frames(gb, 4)
        assert tilemap_row(gb, 0, 16, 4) == [glyph("T"), glyph("0"), glyph("0"), glyph("1")]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_awning_comes_back_on_the_banner_rows(model):
    """The banner rows hold the framework's text through the intro and the count; on the first play frame they are the awning's."""
    with monkey(model) as gb:
        frames(gb, 20)
        assert text(gb, 2) == "MONKEY BUSINESS"
        to_play(gb)
        frames(gb, 3)
        band = [MK_BG + OFF["band"] + i for i in ART["band_map"]]
        assert map_row(gb, 2) == band[20:40] and map_row(gb, 3) == band[40:60]
        if model == "cgb":
            assert bank1(gb, 3, 2) == 5 and bank1(gb, 10, 3) == 5


# ---- flow: practice, story, arcade, the list, what is put back ---------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_practice_retry_and_menu(model):
    """Practice: A on the result retries (the score from 0, the coconuts back), B comes back to the list."""
    with play(model) as gb:
        poke(gb, coco=3, stolen=5)
        to_result(gb, 1000)
        assert text(gb, 4, True, x0=4) == "A RETRY B MENU"
        gb.press("a", 2)
        run_until(gb, lambda: gb.mem("mg_phase") == 0 and gb.pb.memory[0xFF40] & 0x80, 30)
        s = mk(gb)
        assert state(gb) == GS_MINI and score(gb) == 0 and (s["coco"], s["stolen"], s["time"]) == (COCO, 0, TIME)
        assert text(gb, 2) == "MONKEY BUSINESS"
        to_play(gb)
        to_result(gb)
        gb.press("b", 2)
        run_until(gb, lambda: state(gb) == GS_MGLIST and gb.pb.memory[0xFF40] & 0x80, 30)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_story_plays_it_in_chapter_9_and_the_last_call_has_everything_back(model):
    """Chapter 9 (the jungle zoo): after the Happy hour, Monkey Business in MG_STORY (the score carried, the count not skippable,
    unlocked for Practice at once); the result's A CONTINUE leads to the Last call, whose VRAM and palettes are those of the Last
    call reached without it."""
    from test_bs import level_vram, palettes
    from test_story import to_goal, to_shift, win
    with to_shift(model, ZOO, 2) as gb:
        gb.run(2)
        fresh, pals = level_vram(gb), palettes(gb)
    with to_shift(model, ZOO, 1) as gb:
        assert gb.mem16("mg_unlocked") == 0
        win(gb, ZOO, 1)
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 20)
        run_until(gb, lambda: state(gb) == GS_MINI, 300)
        run_until(gb, lambda: gb.pb.memory[0xFF40] & 0x80, 10)
        assert gb.mem("mg_id") == MG_MONKEY and gb.mem("mg_mode") == MG_STORY and gb.mem("venue_id") == ZOO
        assert text(gb, 2) == "MONKEY BUSINESS" and score(gb) > 0
        assert gb.mem16("mg_unlocked") == 1 << MG_MONKEY
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
        assert gb.mem("story_chapter") == ZOO and gb.mem("story_shift") == 2 and gb.mem("story_step") == 3
        to_goal(gb)
        gb.run(2)
        assert level_vram(gb) == fresh
        assert palettes(gb) == pals


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_level_after_monkey_business_has_everything_back(model):
    """Monkey Business (a shoo, a theft) -> B to the list -> the title -> a level: the level's OBJ tiles, BG 77-255, OBP0 / OBP1 and
    every palette are byte for byte those of a level started from a fresh boot."""
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
    with play(model) as gb:
        put_crate(gb, 2, MC_UP, 0, t=5)
        shoo_at(gb, 2)
        put_crate(gb, 0, MC_UP, 0, t=0, u=4)
        frames(gb, 30)
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
def test_arcade_plays_it_in_chapter_9(model):
    """ARCADE plays the story's steps: the zoo's mini slot is Monkey Business, in MG_STORY; reaching it unlocks it."""
    from test_arcade import start_arcade
    from test_story import to_goal, win
    with start_arcade(model) as gb:
        to_goal(gb)
        gb.write("story_chapter", ZOO)
        gb.write("story_step", 1)
        win(gb, 0, 0)
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 20)
        run_until(gb, lambda: state(gb) == GS_MINI, 400)
        run_until(gb, lambda: gb.pb.memory[0xFF40] & 0x80, 10)
        assert gb.mem("mg_id") == MG_MONKEY and gb.mem("mg_mode") == MG_STORY and gb.mem("venue_id") == ZOO
        assert gb.mem("save_lock") == 1 and gb.mem16("mg_unlocked") == 1 << MG_MONKEY
        assert text(gb, 2) == "MONKEY BUSINESS"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_bonus_mini_games_lists_and_plays_it(model):
    """BONUS > MINI GAMES (the debug build: all unlocked): MONKEY BUSINESS on the eighth line (after TAIKO POUR), its details THE
    JUNGLE ZOO; A plays it in practice (score from 0); its result's B comes back to the list on it."""
    from test_mg_list import line, tap as list_tap, to_list
    from test_scores import booted
    with to_list(booted(model)) as gb:
        assert line(gb, 9).strip() == "MONKEY BIZ"
        for _ in range(7):
            list_tap(gb, "down")
        assert gb.mem("ml_sel") == 7
        assert [line(gb, r).strip() for r in range(13, 17)] == ["MONKEY BUSINESS", "THE JUNGLE ZOO", "NO MEDAL YET", "A PLAY  B BACK"]
        list_tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_MINI and gb.pb.memory[0xFF40] & 0x80, 30)
        assert gb.mem("mg_id") == MG_MONKEY and gb.mem("mg_mode") == MG_PRACTICE and score(gb) == 0
        assert text(gb, 2) == "MONKEY BUSINESS"
        gb.write("mg_phase", MG_RESULT)
        run_until(gb, lambda: gb.mem("overlay_on") == 1, 10)
        frames(gb, 3)
        gb.press("b", 2)
        run_until(gb, lambda: state(gb) == GS_MGLIST and gb.pb.memory[0xFF40] & 0x80, 30)
        gb.run(3)
        assert gb.mem("ml_sel") == 7 and line(gb, 9).strip() == "MONKEY BIZ"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_release_list_unlocks_it_when_reached(model, release_built):
    from test_mg_list import MG_PLANNED, line, pr_block, release_rom, tap as list_tap, to_list, with_block
    from test_scores import v7_image
    best = [0] * MG_PLANNED
    best[MG_MONKEY] = MEDAL_SILVER
    ram = with_block(v7_image(), pr_block(1 << MG_MONKEY, best))
    with release_rom(model, ram) as gb:
        to_list(gb)
        assert [line(gb, r).strip() for r in (2, 3, 4, 5, 6, 7, 8)] == ["? ? ?"] * 7
        assert line(gb, 9) == " MONKEY BIZ   SILVER"
        for _ in range(7):
            list_tap(gb, "down")
        assert [line(gb, r).strip() for r in range(13, 16)] == ["MONKEY BUSINESS", "THE JUNGLE ZOO", "BEST SILVER"]
        list_tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_MINI, 30)
        assert gb.mem("mg_id") == MG_MONKEY and gb.mem("mg_mode") == MG_PRACTICE


def test_the_state_fits_the_union():
    assert STATE_SIZE <= 520 and LAYOUT["c"][1] == mk_define("MK_CRATES") == 5


# ---- goldens ---------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_goldens(model):
    """The intro banner; a quick shoo (the puff, the duster); a theft (the runner, the crate open, the pile one down); the parrot
    shooed (the fail pose); all from a seeded game with the crates set by hand (exact frames)."""
    with monkey(model) as gb:
        frames(gb, 40)
        shot(gb, "intro")
        check_golden(gb, "mk_intro")
        to_play(gb)
        frames(gb, 2)
        quiet(gb)
        put_crate(gb, 1, MC_UP, 0, t=14)
        put_crate(gb, 2, MC_UP, 0, t=3)
        put_crate(gb, 4, MC_UP, 1, t=12)
        poke(gb, pos=2, **{"from": 2})
        frames(gb, 2)
        tap(gb, "a")
        frames(gb, 6)
        assert snap(gb)["shooed"] == 1
        shot(gb, "play")
        check_golden(gb, "mk_play")
        # a theft: the monkey at crate 1 is due
        poke_crate(gb, 1, t=mk(gb)["c"][1]["u"] - 2)
        until(gb, lambda: snap(gb)["run_on"] == 1 and snap(gb)["run_t"] >= 2, 20)
        shot(gb, "theft")
        check_golden(gb, "mk_theft")
        # the parrot shooed: walk to crate 4 and shoo it
        gb.release("a")
        until(gb, lambda: snap(gb)["run_on"] == 0, 40)
        while mk(gb)["pos"] != 4:
            tap(gb, "right")
            frames(gb, HOP)
        put_crate(gb, 4, MC_UP, 1, t=20)
        tap(gb, "a")
        frames(gb, 6)
        assert snap(gb)["parrots"] == 1
        shot(gb, "parrot")
        check_golden(gb, "mk_parrot")
        to_result(gb, 5200)
        shot(gb, "result")
        check_golden(gb, "mk_result")
