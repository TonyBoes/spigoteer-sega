# docs/minigames_bosses.md 4.4: ORDER UP! (src/ou.c), the bistro's mini-game, on the framework (src/mg.c): the screen
# (the approved art, 2026-10-12: look B dishes, Chef Colby, the cloche, the bubble, the pips, the strikes, the steam,
# the X, the dancing waiter), the rules (the order called dish by dish at the round's timings, repeated with the D-pad,
# grown by one dish a round from one seeded sequence; a wrong press or a timeout is a strike and the same order is called
# again; three strikes end it), the points, the medals by rounds served, the MINI GAMES list, STORY and ARCADE reaching it
# in the bistro, and everything it borrowed back at the next level load. Sprites per line <= 10 on every frame.
import pytest
from conftest import ROOT, check_golden, hold_stage_anim
from test_flow import GS_GOAL, LEVEL_CLEAR, PLAYING, run_until, state, tilemap_row
from test_mg import (BLANK, GS_MINI, MEDAL_PTS, MG_END, MG_PLAY, MG_PRACTICE, MG_RESULT, MG_STORY, define, frames,
                     mg_enter, score, text, until)

pytestmark = pytest.mark.timeout(600)

OU_C = (ROOT / "src" / "ou.c").read_text()
OU_H = (ROOT / "build" / "ou_art.h").read_text()
MG_ORDERUP = 3
BISTRO = 3
OS_NEXT, OS_PRE, OS_CALL, OS_TURN, OS_ORDERUP, OS_SENT, OS_OVER = range(7)
C_CALL, C_WATCH, C_PLEASED, C_CROSS = range(4)
UP, RIGHT, DOWN, LEFT = range(4)
NONE, CLOCHE, EMPTY = 255, 4, 5
KEYS = ["up", "right", "down", "left"]
MEDAL_NONE, MEDAL_BRONZE, MEDAL_SILVER, MEDAL_GOLD = range(4)
SFX_LAUNCH, SFX_CATCH, SFX_BREAK, SFX_SERVE, SFX_COIN, SFX_SHAKE = 2, 3, 4, 5, 6, 8
TONE = [SFX_COIN, SFX_CATCH, SFX_LAUNCH, SFX_SHAKE]
(ROUNDS, PRE, PRESS_LEN, LIGHT_LEN, UP_LEN, CLOCHE_BEAT, SENT_LEN, STEAM_BEAT, DISH_PTS, ROUND_PTS, PERFECT, OAM_X,
 OAM_STEAM, OAM_COLBY, OAM_SPIG, OAM_WAITER, OAM_N, COLBY_X, COLBY_Y, SPIG_X, SPIG_Y, WAITER_X, WAITER_Y, PIP_ROW,
 PIP_COL, PIP_MID, STRIKE_COL, BUB_COL, BUB_ROW) = (
    define(n, OU_C) for n in ("OU_ROUNDS", "OU_PRE", "OU_PRESS_LEN", "OU_LIGHT_LEN", "OU_UP_LEN", "OU_CLOCHE_BEAT",
                              "OU_SENT_LEN", "OU_STEAM_BEAT", "OU_DISH_PTS", "OU_ROUND_PTS", "OU_PERFECT", "OAM_X",
                              "OAM_STEAM", "OAM_COLBY", "OAM_SPIG", "OAM_WAITER", "OAM_N", "COLBY_X", "COLBY_Y",
                              "SPIG_X", "SPIG_Y", "WAITER_X", "WAITER_Y", "PIP_ROW", "PIP_COL", "PIP_MID",
                              "STRIKE_COL", "BUB_COL", "BUB_ROW"))
OH = {m[0]: int(m[1]) for m in __import__("re").findall(r"#define (OU\w+) (\d+)", OU_H)}
LIT_LEN = [24, 24, 24, 20, 20, 16, 16]                 # the spec's calling timings (rounds 1-7)
GAP_LEN = [8, 8, 8, 6, 6, 6, 6]
OU_BG = 77 + 48                                        # MG_GAME_BG
OU_OBJ = 56
CELL = {UP: (12, 5), RIGHT: (14, 7), DOWN: (12, 9), LEFT: (10, 7), CLOCHE: (12, 7)}
DISH_PAL = [2, 3, 5, 6]
SEED = 0x5A17
OUT = ROOT / "out" / "ou"


def ou(gb):
    b = gb.read("story_scratch", 29)
    return dict(st=b[0], round=b[1], len=b[2], idx=b[3], strikes=b[4], t=b[5], wait=b[6], cleared=b[7],
                seq=list(b[8:8 + b[2]]), x_on=b[17], want=b[18], shown=b[19], pal_dish=b[20], light_t=b[22],
                serve_t=b[23], bubble=b[24], colby=b[25], again=b[26], cloche=b[28])


def orderup(model, mode=MG_PRACTICE, seed=SEED):
    """A booted rom on the title, then Order Up! in practice (or `mode`)."""
    from test_scores import booted
    rom = booted(model)
    hold_stage_anim(rom)
    mg_enter(rom, MG_ORDERUP, mode, seed)
    return rom


def shot(gb, name):
    OUT.mkdir(parents=True, exist_ok=True)
    gb.screenshot(OUT / f"{name}.{gb.model_name}.png", 4)


def to_state(gb, st, limit=2000, worst=None):
    for _ in range(limit):
        if ou(gb)["st"] == st:
            return
        frames(gb, 1, worst)
    raise AssertionError(f"state {st} not reached: {ou(gb)}")


def tap(gb, d, worst=None):
    """A D-pad press held 2 frames, then 2 frames released (a 1-frame tap can fall between two of the game's joypad reads
    when a long VBlank copy moves the logic against PyBoy's frame cut)."""
    gb.hold(KEYS[d])
    frames(gb, 2, worst)
    gb.release(KEYS[d])
    frames(gb, 2, worst)


def oam(gb, i):
    a = 0xFE00 + 4 * i
    return dict(y=gb.mem(a), x=gb.mem(a + 1), tile=gb.mem(a + 2), prop=gb.mem(a + 3))


def cell_tiles(gb, c):
    x, y = CELL[c]
    return tilemap_row(gb, y, x, 2) + tilemap_row(gb, y + 1, x, 2)


def dish_tiles(d, lit=False):
    t = OU_BG + (OH["OUB_LIT"] if lit else OH["OUB_DISH"]) + 4 * d
    return [t, t + 1, t + 2, t + 3]


def cell_attrs(gb, c):
    x, y = CELL[c]
    return [gb.pb.memory[1, 0x9800 + (y + r) * 32 + x + k] & 7 for r in (0, 1) for k in (0, 1)]


def strikes_hud(gb):
    on, off = OU_BG + OH["OUB_STRIKE_ON"], OU_BG + OH["OUB_STRIKE_OFF"]
    row = tilemap_row(gb, 0, STRIKE_COL, 3)
    assert set(row) <= {on, off}, row
    return row.count(on)


def pips(gb):
    """(pips shown, pips done) on row 12."""
    row = tilemap_row(gb, PIP_ROW, PIP_COL, 9)
    done, todo = OU_BG + OH["OUB_PIP_DONE"], OU_BG + OH["OUB_PIP_TODO"]
    shown = [t for t in row if t in (done, todo)]
    return len(shown), shown.count(done)


def pip_start(n):
    return PIP_MID - (n + 1) // 2


def bubble_inside(gb):
    return tilemap_row(gb, BUB_ROW + 1, BUB_COL + 1, 2) + tilemap_row(gb, BUB_ROW + 2, BUB_COL + 1, 2)


def colby(gb):
    return (oam(gb, OAM_COLBY)["tile"] - OU_OBJ - OH["OUO_COLBY"]) // 4


def spig(gb):
    return oam(gb, OAM_SPIG)["tile"] // 8                 # the bartender's PICTURE index (mg_spigoteer): 0 idle, 3 fill (= slide and catch), 4 fail


def sfx(gb):
    return list(gb.read("sfx_count", 9))


def serve(gb, worst=None):
    """Your turn: every dish of the order pressed right, one after the other."""
    to_state(gb, OS_TURN, worst=worst)
    for d in ou(gb)["seq"]:
        tap(gb, d, worst)


def play_rounds(gb, n, worst=None):
    """n rounds served without a strike; returns each round's order as called."""
    orders = []
    for _ in range(n):
        to_state(gb, OS_TURN, worst=worst)
        orders.append(ou(gb)["seq"])
        serve(gb, worst)
        to_state(gb, OS_ORDERUP, worst=worst)
    return orders


def wrong(d):
    return (d + 1) & 3


def strike_out(gb, worst=None):
    """Strikes until the game ends: a wrong first press each time the order has been called."""
    while ou(gb)["strikes"] < 3:
        to_state(gb, OS_TURN, worst=worst)
        tap(gb, wrong(ou(gb)["seq"][0]), worst)
        to_state(gb, OS_SENT if ou(gb)["strikes"] < 3 else OS_OVER, worst=worst)


def to_play(gb):
    until(gb, lambda: gb.mem("mg_phase") == MG_PLAY, 200)


# ---- the screen --------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_screen(model):
    """The intro as the approved mock-up: the banner ORDER UP! (its own '!') / REPEAT THE ORDER, three empty strikes in
    the timer's place, the four dishes round the cloche, no bubble or pips yet, Colby watching behind the counter and the
    Spigoteer idle; the art in VRAM; CGB: the dishes in BG palettes 2 3 5 6 (colour 0 the wall's), Colby's palettes
    3 / 4, the bistro backdrop in palette 0 only (so 5-7 are free); DMG: OBP1 0xC4 for the X and the waiter."""
    from test_lift import cgb_bg_palette, cgb_obj_palette
    with orderup(model) as gb:
        frames(gb, 30)
        assert gb.mem("mg_id") == MG_ORDERUP and gb.mem("venue_id") == BISTRO and gb.mem16("mg_timer") == 0
        assert text(gb, 2) == "ORDER UP" and text(gb, 3) == "REPEAT THE ORDER"
        bang = OU_BG + OH["OUB_BANG"]
        assert tilemap_row(gb, 2, 0, 20).count(bang) == 1 and gb.mem("say_bang") == bang, "the '!'"
        assert strikes_hud(gb) == 0 and tilemap_row(gb, 0, 19, 1) == [BLANK], "the strikes, no timer"
        for d in range(4):
            assert cell_tiles(gb, d) == dish_tiles(d)
        c = OU_BG + OH["OUB_CLOCHE"]
        assert cell_tiles(gb, CLOCHE) == [c, c + 1, c + 2, c + 3], "the cloche, down"
        assert pips(gb) == (0, 0)
        s = ou(gb)
        assert s["st"] == OS_NEXT and s["bubble"] == NONE and s["round"] == 0 and s["strikes"] == 0
        o = oam(gb, OAM_COLBY)
        assert (o["x"], o["y"], colby(gb)) == (COLBY_X + 8, COLBY_Y + 16, C_WATCH)
        o = oam(gb, OAM_COLBY + 2)
        assert (o["y"], o["tile"]) == (COLBY_Y + 32, OU_OBJ + OH["OUO_COLBY_LOW"])
        o = oam(gb, OAM_SPIG)
        assert (o["x"], o["y"], spig(gb)) == (SPIG_X + 8, SPIG_Y + 16, 0)
        assert all(oam(gb, i)["y"] == 0 for i in (OAM_X, OAM_X + 1, OAM_STEAM, OAM_STEAM + 1, OAM_WAITER))
        assert all(oam(gb, i)["y"] == 0 for i in range(OAM_N, 40))
        bg = b"".join(bytes(gb.read((0x9000 if t < 128 else 0x8000) + t * 16, 16))
                      for t in range(OU_BG, OU_BG + OH["OU_BG_TILES"]))
        from test_mg import ART
        assert bg == bytes(ART["ou_bg"])
        assert bytes(gb.read(0x8000 + OU_OBJ * 16, OH["OU_OBJ_TILES"] * 16)) == bytes(ART["ou_obj"])
        assert OU_OBJ + OH["OU_OBJ_TILES"] <= 92, "the coin's OBJ 92-95 untouched"
        if model == "cgb":
            for d in range(4):
                assert cell_attrs(gb, d) == [DISH_PAL[d]] * 4
                pal = cgb_bg_palette(gb, DISH_PAL[d])
                assert pal[0] == cgb_bg_palette(gb, 0)[0] and len(set(pal)) == 4, "the wall's colour 0, 3 food tones"
            assert cell_attrs(gb, CLOCHE) == [0] * 4
            mine = {(x + i, y + j) for x, y in CELL.values() for i in (0, 1) for j in (0, 1)}
            for y in range(1, 18):
                if y in (2, 3):
                    continue                                # the banner rows: the HUD's
                pals = {gb.pb.memory[1, 0x9800 + y * 32 + x] & 7 for x in range(20) if (x, y) not in mine}
                assert pals == {0}, f"the bistro's mini-game backdrop row {y}: palette 0 only ({pals})"
            assert oam(gb, OAM_COLBY)["prop"] & 7 == 3 and oam(gb, OAM_COLBY + 2)["prop"] & 7 == 4
            assert cgb_obj_palette(gb, 3)[2] != cgb_obj_palette(gb, 4)[2], "skin above, the neckerchief below"
        else:
            assert gb.mem(0xFF49) == 0xC4 and gb.mem(0xFF48) == 0xD0
            assert oam(gb, OAM_COLBY)["prop"] & 0x10 == 0, "Colby on OBP0"
        shot(gb, "intro")
        check_golden(gb, "ou_intro")


# ---- calling ------------------------------------------------------------------------------------------------------------
def bubble_runs(gb, worst=None):
    """From OS_PRE to YOUR TURN: the bubble's contents frame by frame as runs [(value, frames)]."""
    to_state(gb, OS_PRE, worst=worst)
    runs = []
    while ou(gb)["st"] != OS_TURN:
        b = ou(gb)["bubble"]
        if runs and runs[-1][0] == b:
            runs[-1][1] += 1
        else:
            runs.append([b, 1])
        frames(gb, 1, worst)
    return [tuple(r) for r in runs]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_round_1_is_called_dish_by_dish(model):
    """ROUND 1 / LISTEN, three to-do pips centred under the cross; the empty bubble for OU_PRE frames; each dish lit on the
    cross (its LIT tiles; CGB: palette 7 = [dark, mid, light, glow]) and big in the bubble for 24 frames with its sound and
    Colby calling, then 8 dark; then YOUR TURN, the bubble gone (the wall back tile for tile)."""
    from test_lift import cgb_bg_palette
    with orderup(model) as gb:
        wall = [tilemap_row(gb, BUB_ROW + r, BUB_COL, 4) for r in range(5)]
        to_play(gb)
        frames(gb, 2)
        s = ou(gb)
        assert s["st"] == OS_PRE and s["round"] == 1 and s["len"] == 3 and all(d < 4 for d in s["seq"])
        assert text(gb, 2) == "ROUND 1" and text(gb, 3) == "LISTEN"
        assert pips(gb) == (3, 0) and tilemap_row(gb, PIP_ROW, pip_start(3), 1) == [OU_BG + OH["OUB_PIP_TODO"]]
        frames(gb, 2)
        assert bubble_inside(gb) == [OU_BG + OH["OUB_BLANK"]] * 4, "the empty bubble"
        b = OU_BG + OH["OUB_BUBBLE"]
        assert tilemap_row(gb, BUB_ROW, BUB_COL, 4) == [b, b + 1, b + 1, b + 2]
        assert tilemap_row(gb, BUB_ROW + 4, BUB_COL, 2) == [b + 9, b + 10], "the tail"
        seq = s["seq"]
        before = sfx(gb)
        until(gb, lambda: ou(gb)["st"] == OS_CALL, PRE)
        frames(gb, 10)
        d = seq[0]
        assert cell_tiles(gb, d) == dish_tiles(d, lit=True) and bubble_inside(gb) == dish_tiles(d)
        assert colby(gb) == C_CALL and sfx(gb)[TONE[d]] == before[TONE[d]] + 1
        if model == "cgb":
            assert cell_attrs(gb, d) == [7] * 4
            p = cgb_bg_palette(gb, DISH_PAL[d])
            assert cgb_bg_palette(gb, 7)[:3] == [p[3], p[2], p[1]], "the lit dish: its colours round the glow"
            assert [gb.pb.memory[1, 0x9800 + (BUB_ROW + 1 + r) * 32 + BUB_COL + 1 + k] & 7
                    for r in (0, 1) for k in (0, 1)] == [DISH_PAL[d]] * 4, "the bubble's dish in its own palette"
        shot(gb, "call")
        check_golden(gb, "ou_call")
        until(gb, lambda: ou(gb)["st"] == OS_TURN, 200)
        frames(gb, 2)
        assert text(gb, 2) == "ROUND 1" and text(gb, 3) == "YOUR TURN"
        assert [tilemap_row(gb, BUB_ROW + r, BUB_COL, 4) for r in range(5)] == wall, "the wall back"
        assert all(cell_tiles(gb, k) == dish_tiles(k) for k in range(4)) and colby(gb) == C_WATCH
        if model == "cgb":
            assert all(cell_attrs(gb, k) == [DISH_PAL[k]] * 4 for k in range(4))


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_calling_timings_per_round(model):
    """Every round's call, frame by frame: OU_PRE frames of empty bubble (the first two before it is drawn), then each
    dish of the order L frames and an empty G (24 / 8 rounds 1-3, 20 / 6 rounds 4-5, 16 / 6 rounds 6-7); the order is
    r + 2 dishes long and keeps the last round's order as its start (one sequence, grown by one)."""
    with orderup(model) as gb:
        prev = []
        for r in range(1, ROUNDS + 1):
            runs = bubble_runs(gb)
            s = ou(gb)
            assert s["round"] == r and s["len"] == r + 2 and s["seq"][:len(prev)] == prev
            prev = s["seq"]
            want = [(NONE, 2), (EMPTY, PRE - 2)]
            for d in prev:
                want += [(d, LIT_LEN[r - 1]), (EMPTY, GAP_LEN[r - 1])]
            merged = []
            for v, n in want:                          # (the same dish twice: one run)
                if merged and merged[-1][0] == v:
                    merged[-1] = (v, merged[-1][1] + n)
                else:
                    merged.append((v, n))
            # (the hidden bubble's first frames: how many are seen depends on where PyBoy's frame cuts the logic; so does a run's edge, by one frame:
            # the logic of a heavy frame ends past the cut, so each boundary may sit one frame either side of the model's)
            assert runs[0][0] == NONE and [v for v, _ in runs[1:]] == [v for v, _ in merged[1:]], (r, runs)
            seen = [sum(n for _, n in runs[1:k + 1]) for k in range(1, len(runs))]
            want_t = [sum(n for _, n in merged[1:k + 1]) for k in range(1, len(merged))]
            assert all(abs(a - b) <= 1 for a, b in zip(seen, want_t)), (r, runs)
            serve(gb)
            to_state(gb, OS_ORDERUP)


# ---- your turn --------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_right_presses_serve_and_order_up(model):
    """Each right press: 50 points, its pip filled, the dish lit and the Spigoteer serving for 14 frames, its sound; the
    last one: ORDER UP! / 200 POINTS (x the round), the bell, the cloche lifted and set down every 12 frames, Colby
    pleased, the Spigoteer cheering, the bistro show's waiter dancing (OAM 12-15); then round 2, one dish longer."""
    with orderup(model) as gb:
        to_state(gb, OS_TURN)
        s = ou(gb)
        seq = s["seq"]
        assert s["wait"] == PRESS_LEN and s["idx"] == 0
        start = score(gb)
        for i, d in enumerate(seq):
            before = sfx(gb)
            tap(gb, d)
            s = ou(gb)
            assert s["idx"] == i + 1 and gb.mem16("mg_score") == DISH_PTS * (i + 1)
            assert score(gb) == start + DISH_PTS * (i + 1), "the HUD score live"
            assert sfx(gb)[TONE[d]] == before[TONE[d]] + 1
            frames(gb, 1)
            assert pips(gb) == (3, i + 1) and cell_tiles(gb, d) == dish_tiles(d, lit=True) and spig(gb) == 3
            if i == 1:
                shot(gb, "turn")
                check_golden(gb, "ou_turn")
            if i < 2:
                frames(gb, LIGHT_LEN)
                assert cell_tiles(gb, d) == dish_tiles(d) and spig(gb) == 0, "the light and the serve pose: 14 frames"
        bells = sfx(gb)[SFX_SERVE]
        to_state(gb, OS_ORDERUP)
        frames(gb, 3)
        assert text(gb, 2) == "ORDER UP" and text(gb, 3) == "200 POINTS" and sfx(gb)[SFX_SERVE] == bells + 1
        assert gb.mem16("mg_score") == 3 * DISH_PTS + ROUND_PTS and ou(gb)["cleared"] == 1
        c = OU_BG + OH["OUB_CLOCHE"] + 4
        assert cell_tiles(gb, CLOCHE) == [c, c + 1, c + 2, c + 3], "the cloche lifted"
        assert colby(gb) == C_PLEASED and spig(gb) == 3 and pips(gb) == (3, 3)
        w = [oam(gb, OAM_WAITER + k) for k in range(4)]
        assert all(o["y"] for o in w) and (w[0]["x"], w[0]["y"]) == (WAITER_X + 8, WAITER_Y + 16)
        assert all(96 <= o["tile"] < 128 for o in w), "the bistro show's waiter (its tiles from the level load)"
        assert all(o["prop"] & 7 == 5 for o in w) if model == "cgb" else all(o["prop"] & 0x10 for o in w)
        shot(gb, "orderup")
        check_golden(gb, "ou_orderup")
        lifted = []
        while ou(gb)["st"] == OS_ORDERUP:
            lifted.append(ou(gb)["cloche"])
            frames(gb, 1)
        assert UP_LEN - 6 <= len(lifted) <= UP_LEN and lifted[:CLOCHE_BEAT - 4] == [1] * (CLOCHE_BEAT - 4)
        assert 0 in lifted, "set down and lifted again on the beat"
        frames(gb, 2)
        s = ou(gb)
        assert s["round"] == 2 and s["len"] == 4 and s["seq"][:3] == seq and text(gb, 2) == "ROUND 2"
        assert all(oam(gb, OAM_WAITER + k)["y"] == 0 for k in range(4)) and ou(gb)["cloche"] == 0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_wrong_press_is_sent_back_and_the_same_order_called_again(model):
    """A wrong press: a strike (HUD), SENT BACK, the X over that dish (lit), Colby cross with his steam puffing every 8
    frames, the Spigoteer's shrug, the break sound; 64 frames, then ROUND 1 / LISTEN and the very same order called
    again from its first dish (not grown, not a new one), the pips empty again."""
    with orderup(model) as gb:
        to_state(gb, OS_TURN)
        seq = ou(gb)["seq"]
        tap(gb, seq[0])
        breaks = sfx(gb)[SFX_BREAK]
        bad = wrong(seq[1])
        tap(gb, bad)
        s = ou(gb)
        assert s["st"] == OS_SENT and s["strikes"] == 1 and s["x_on"] == bad and sfx(gb)[SFX_BREAK] == breaks + 1
        assert gb.mem16("mg_score") == DISH_PTS
        frames(gb, 8)
        assert text(gb, 3) == "SENT BACK" and strikes_hud(gb) == 1
        x, y = CELL[bad]
        o = oam(gb, OAM_X)
        assert (o["x"], o["y"], o["tile"]) == (x * 8 + 8, y * 8 + 16, OU_OBJ + OH["OUO_X"])
        assert o["prop"] & 7 == 6 if model == "cgb" else o["prop"] & 0x10, "the X: OBJ palette 6 / OBP1"
        assert cell_tiles(gb, bad) == dish_tiles(bad, lit=True)
        assert colby(gb) == C_CROSS and spig(gb) == 4 and pips(gb) == (3, 1)
        st = oam(gb, OAM_STEAM)
        assert (st["x"], st["y"]) == (COLBY_X - 1 + 8, COLBY_Y - 16 + 16)
        puffs = {oam(gb, OAM_STEAM)["tile"]}
        frames(gb, STEAM_BEAT)
        puffs.add(oam(gb, OAM_STEAM)["tile"])
        assert puffs == {OU_OBJ + OH["OUO_STEAM"], OU_OBJ + OH["OUO_STEAM"] + 4}, "two puffs, alternating"
        frames(gb, 2 - STEAM_BEAT)
        shot(gb, "sent_back")
        check_golden(gb, "ou_sent_back")
        to_state(gb, OS_PRE)
        frames(gb, 2)
        s = ou(gb)
        assert s["round"] == 1 and s["len"] == 3 and s["seq"] == seq and s["idx"] == 0 and s["x_on"] == NONE
        assert text(gb, 2) == "ROUND 1" and text(gb, 3) == "LISTEN" and pips(gb) == (3, 0)
        assert oam(gb, OAM_X)["y"] == 0 and oam(gb, OAM_STEAM)["y"] == 0 and colby(gb) == C_WATCH
        assert cell_tiles(gb, bad) == dish_tiles(bad)
        runs = [ou(gb)["bubble"]]
        while ou(gb)["st"] != OS_TURN:
            if ou(gb)["bubble"] != runs[-1]:
                runs.append(ou(gb)["bubble"])
            frames(gb, 1)
        assert [b for b in runs if b < 4] == seq, "called again, dish for dish"
        serve(gb)
        to_state(gb, OS_ORDERUP)
        assert ou(gb)["cleared"] == 1 and ou(gb)["strikes"] == 1


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_time_for_each_press(model):
    """150 frames for each press: from YOUR TURN and again after each right press; frame 150 with no press is a strike
    (TIME OUT: the X over the cloche, no dish lit)."""
    with orderup(model) as gb:
        to_state(gb, OS_TURN)
        seq = ou(gb)["seq"]
        frames(gb, PRESS_LEN - 10)
        assert ou(gb)["st"] == OS_TURN and ou(gb)["wait"] in (9, 10)       # (a frame's logic may end past PyBoy's frame cut: one frame either way)
        tap(gb, seq[0])
        n = PRESS_LEN - ou(gb)["wait"]
        assert ou(gb)["idx"] == 1 and 0 < n <= 5, "the time starts again after a right press"
        while ou(gb)["st"] == OS_TURN:
            frames(gb, 1)
            n += 1
        s = ou(gb)
        assert s["st"] == OS_SENT and s["wait"] == 0 and abs(n - PRESS_LEN) <= 2, n
        assert s["strikes"] == 1 and s["x_on"] == CLOCHE and s["want"] == NONE
        frames(gb, 2)
        x, y = CELL[CLOCHE]
        assert (oam(gb, OAM_X)["x"], oam(gb, OAM_X)["y"]) == (x * 8 + 8, y * 8 + 16)
        assert all(cell_tiles(gb, k) == dish_tiles(k) for k in range(4))
        assert text(gb, 3) == "SENT BACK"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_presses_outside_your_turn_do_nothing(model):
    """While Colby calls (and during SENT BACK / ORDER UP!) the D-pad does nothing."""
    with orderup(model) as gb:
        to_state(gb, OS_CALL)
        for d in range(4):
            tap(gb, d)
        s = ou(gb)
        assert s["st"] == OS_CALL and s["strikes"] == 0 and gb.mem16("mg_score") == 0


# ---- the end, the points, the medals ------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_perfect_game(model):
    """Seven rounds served without a strike, frame by frame (never more than 10 sprites a line; the worst is 4):
    42 presses x 50 + 200 x (1 + ... + 7) + 1000 for no strike = 8700, ALL ORDERS SERVED / NO STRIKES 1000, the outro
    (Colby pleased, the cheer, the waiter), then GOLD and its 3000 in the result."""
    with orderup(model) as gb:
        worst = [0]
        orders = play_rounds(gb, ROUNDS, worst)
        assert [len(o) for o in orders] == [3, 4, 5, 6, 7, 8, 9]
        assert all(orders[k + 1][:len(orders[k])] == orders[k] for k in range(ROUNDS - 1))
        to_state(gb, OS_OVER, worst=worst)
        frames(gb, 3, worst)
        assert gb.mem("mg_phase") == MG_END
        assert text(gb, 2) == "ALL ORDERS SERVED" and text(gb, 3) == "NO STRIKES 1000"
        total = 42 * DISH_PTS + ROUND_PTS * 28 + PERFECT
        assert gb.mem16("mg_score") == total == 8700 and score(gb) == total
        assert colby(gb) == C_PLEASED and spig(gb) == 3 and oam(gb, OAM_WAITER)["y"]
        until(gb, lambda: gb.mem("mg_phase") == MG_RESULT and gb.mem("overlay_on") == 1, 100)
        frames(gb, 3, worst)
        assert gb.mem("mg_medal") == MEDAL_GOLD and score(gb) == total + MEDAL_PTS[MEDAL_GOLD]
        assert text(gb, 1, True, x0=4) == "ORDER UP" and text(gb, 2, True, x0=4) == f"SCORE {total}"
        assert text(gb, 3, True, x0=4) == "GOLD 3000"
        assert worst[0] <= 4, worst
        shot(gb, "result")
        check_golden(gb, "ou_result")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("cleared,medal", [(0, MEDAL_NONE), (2, MEDAL_NONE), (3, MEDAL_BRONZE), (4, MEDAL_BRONZE),
                                           (5, MEDAL_SILVER), (6, MEDAL_SILVER)])
def test_three_strikes_end_it_and_the_medal_is_the_rounds_served(model, cleared, medal):
    """n rounds served, then three strikes: THREE STRIKES / ORDERS SERVED n, Colby cross, the shrug; the medal is the
    rounds served (BRONZE 3, SILVER 5; GOLD only with round 7: test_a_perfect_game), the points 50 a dish served and
    200 x r a round."""
    with orderup(model, seed=0x1234 + cleared) as gb:
        worst = [0]
        play_rounds(gb, cleared, worst)
        strike_out(gb, worst)
        frames(gb, 3, worst)
        s = ou(gb)
        assert s["st"] == OS_OVER and s["strikes"] == 3 and s["cleared"] == cleared and gb.mem("mg_phase") == MG_END
        assert text(gb, 2) == "THREE STRIKES" and text(gb, 3) == f"ORDERS SERVED {cleared}" and strikes_hud(gb) == 3
        assert colby(gb) == C_CROSS and spig(gb) == 4
        dishes = sum(r + 2 for r in range(1, cleared + 1))
        assert gb.mem16("mg_score") == dishes * DISH_PTS + ROUND_PTS * cleared * (cleared + 1) // 2
        until(gb, lambda: gb.mem("mg_phase") == MG_RESULT and gb.mem("overlay_on") == 1, 100)
        frames(gb, 2, worst)
        assert gb.mem("mg_medal") == medal
        assert worst[0] <= 4, worst


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_all_served_with_a_strike_has_no_perfect_bonus(model):
    with orderup(model) as gb:
        to_state(gb, OS_TURN)
        tap(gb, wrong(ou(gb)["seq"][0]))
        play_rounds(gb, ROUNDS)
        to_state(gb, OS_OVER)
        frames(gb, 3)
        assert text(gb, 2) == "ALL ORDERS SERVED" and text(gb, 3) == ""
        assert gb.mem16("mg_score") == 42 * DISH_PTS + ROUND_PTS * 28
        until(gb, lambda: gb.mem("mg_phase") == MG_RESULT and gb.mem("overlay_on") == 1, 100)
        assert gb.mem("mg_medal") == MEDAL_GOLD


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_order_follows_the_seed(model):
    """mg_seed_force repeats a game's order; another seed gives another; all four dishes come up."""
    def order(seed):
        with orderup(model, seed=seed) as gb:
            play_rounds(gb, 6)
            to_state(gb, OS_TURN)
            return ou(gb)["seq"]
    a, b, c = order(SEED), order(SEED), order(0xBEEF)
    assert a == b and a != c and len(a) == 9 and set(a + c) == {UP, RIGHT, DOWN, LEFT}


# ---- the list, the story, arcade ------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_from_the_mini_games_list(model):
    """BONUS > MINI GAMES lists ORDER UP (fourth, in chapter order; THE BISTRO); A plays it in practice from 0."""
    from test_mg_list import medal_word, selection, tap as list_tap, to_game, to_list
    from test_scores import booted
    with to_list(booted(model)) as gb:
        to_game(gb, 3)
        assert selection(gb) == "ORDER UP" and medal_word(gb) == "NO MEDAL"
        list_tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_MINI and gb.pb.memory[0xFF40] & 0x80, 30)
        assert gb.mem("mg_id") == MG_ORDERUP and gb.mem("mg_mode") == MG_PRACTICE and score(gb) == 0
        assert gb.mem("venue_id") == BISTRO and text(gb, 2) == "ORDER UP"


def level_state(gb):
    """What a level load sets up: VRAM tiles (both banks on CGB), the palettes, the DMG palette registers."""
    from test_lift import cgb_bg_palette, cgb_obj_palette
    v = bytes(gb.read(0x8000, 0x1800))
    if gb.model_name == "cgb":
        v += bytes(gb.pb.memory[1, 0x8000:0x9800])
        return v, [cgb_bg_palette(gb, k) for k in range(8)], [cgb_obj_palette(gb, k) for k in range(8)]
    return v, [gb.mem(0xFF47), gb.mem(0xFF48), gb.mem(0xFF49)], []


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_story_plays_it_in_the_bistro_and_the_last_call_has_everything_back(model):
    """The bistro's Happy hour won: Order Up! in MG_STORY (unlocked for the list at once), a round served, then its
    result (A CONTINUE) and the Last call; that level's VRAM (tiles, both banks), every BG and OBJ palette (5-7 too) and
    the DMG palettes are those of the same Last call reached without the mini-game."""
    from test_story import to_goal, to_shift, win
    with to_shift(model, BISTRO, 2) as gb:
        gb.run(2)
        assert state(gb) == PLAYING and gb.mem("story_chapter") == BISTRO
        fresh = level_state(gb)
    with to_shift(model, BISTRO, 1) as gb:
        assert gb.mem16("mg_unlocked") & (1 << MG_ORDERUP) == 0
        win(gb, BISTRO, 1)
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 20)
        run_until(gb, lambda: state(gb) == GS_MINI, 800)
        run_until(gb, lambda: gb.pb.memory[0xFF40] & 0x80, 10)
        assert gb.mem("mg_id") == MG_ORDERUP and gb.mem("mg_mode") == MG_STORY and gb.mem("venue_id") == BISTRO
        assert gb.mem16("mg_unlocked") & (1 << MG_ORDERUP) and text(gb, 2) == "ORDER UP"
        before = score(gb)
        play_rounds(gb, 1)
        assert score(gb) == before + 3 * DISH_PTS + ROUND_PTS
        gb.write("mg_phase", MG_RESULT)
        until(gb, lambda: gb.mem("overlay_on") == 1 and gb.mem("mg_t") >= 63, 120)
        assert text(gb, 4, True, x0=4) == "A CONTINUE"
        gb.press("a", 2)
        run_until(gb, lambda: state(gb) == GS_GOAL, 60)
        gb.run(3)
        assert gb.mem("story_shift") == 2 and gb.mem("story_chapter") == BISTRO and gb.mem("say_bang") == 0
        to_goal(gb)
        gb.run(2)
        assert state(gb) == PLAYING
        after = level_state(gb)
        # (BG tile 77, MG_BG: neither the level's nor a patron's; the story font's first glyph where a story screen
        # loaded it, the medal icon's first tile after a mini-game)
        t77 = slice(0x1000 + 77 * 16, 0x1000 + 78 * 16)
        a, f = bytearray(after[0]), bytearray(fresh[0])
        a[t77] = f[t77] = bytes(16)
        diff = [k for k in range(len(a)) if a[k] != f[k]]
        assert not diff, f"VRAM tiles as a fresh Last call's: {len(diff)} bytes differ from {hex(0x8000 + diff[0])}"
        assert after[1] == fresh[1], "BG palettes (DMG: BGP, OBP0, OBP1) as a fresh Last call's"
        if model == "cgb":                               # (OBJ 4: Colby's jacket stays; the chefs have no extra OBJ
            for k in (0, 1, 2, 3, 5, 6, 7):              # palette, so no bistro sprite uses 4)
                assert after[2][k] == fresh[2][k], k


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_arcade_reaches_it_in_the_bistro(model):
    """ARCADE plays the same slot: the bistro's Happy hour won (the step poked to it) starts Order Up! in MG_STORY and
    unlocks it for the list."""
    from test_arcade import start_arcade
    from test_story import to_goal, win
    with start_arcade(model) as gb:
        to_goal(gb)
        gb.write("story_chapter", BISTRO)
        gb.write("story_step", 1)
        win(gb, 0, 0)
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 20)
        run_until(gb, lambda: state(gb) == GS_MINI, 800)
        run_until(gb, lambda: gb.pb.memory[0xFF40] & 0x80, 10)
        assert gb.mem("mg_id") == MG_ORDERUP and gb.mem("mg_mode") == MG_STORY and gb.mem("venue_id") == BISTRO
        assert gb.mem16("mg_unlocked") & (1 << MG_ORDERUP)
