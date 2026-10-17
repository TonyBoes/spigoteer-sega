# docs/minigames_bosses.md 4.1: QUICK DRAW (src/qd.c), the saloon's mini-game, on the framework (src/mg.c): the screen
# (the approved art), the rules (READY, the random wait, DRAW! with its badge, the Kid's draw at R, ties to the player,
# fouls, held buttons, feints from round 3 never in the last 30 frames), the points, best of five stopping at three, the
# medals by rounds, the soda duel (the shake, the spray across the wall, the wet loser, the foul's fizz), seeded repeats
# and everything put back afterwards. Sprites per line <= 10 on every frame.
import itertools
import json
import re

import pytest
from conftest import ROOT, check_golden, hold_stage_anim, logic_paused, title_level
from test_flow import PLAYING, TITLE, run_until, state, tilemap_row
from test_mg import (BLANK, END_LEN, GS_MGLIST, GS_MINI, MEDAL_PTS, MG_END, MG_PLAY, MG_PRACTICE, MG_RESULT, MG_STORY,
                     define, frames, lines, mg_enter, score, text, until)

pytestmark = pytest.mark.timeout(300)

QD_C = (ROOT / "src" / "qd.c").read_text()
QD_H = (ROOT / "build" / "qd_art.h").read_text()
MG_H = (ROOT / "src" / "mg.h").read_text()
ART = json.loads((ROOT / "build" / "mg.json").read_text())
MG_QUICKDRAW = 0
QS_NEXT, QS_READY, QS_WAIT, QS_DRAW, QS_SHOW, QS_OVER = range(6)
QR_NONE, QR_YOU, QR_SLOW, QR_FOUL, QR_WRONG = range(5)
QF_NONE, QF_TUMBLE, QF_CROW = range(3)
KID_STAND, KID_DRAW, KID_CHEER = range(3)
MEDAL_NONE, MEDAL_BRONZE, MEDAL_SILVER, MEDAL_GOLD = range(4)
SFX_LAUNCH, SFX_CATCH, SFX_BREAK, SFX_SERVE, SFX_LIFE, SFX_SHAKE = 2, 3, 4, 5, 7, 8
_TUNE = re.findall(r"\{ \{ ([\d, ]+) \}, (\d+), (\d+), (\d+) \},", QD_C)   # qd_tune rows: NORMAL, HARD, EASY
KID_R = [int(v) for v in _TUNE[0][0].split(", ")]                 # NORMAL's (STORY / ARCADE / Practice NORMAL)
(READY_LEN, WAIT_MIN, WAIT_SPAN, SHOW_LEN, FEINT_LEN, FEINT_GAP, ROUND_PTS, SPEED_PTS, MATCH_PTS, SIGN_COL,
 SIGN_ROW, SIGN_W, LET_COL, PIP_ROW, PIP_KID_COL, PIP_YOU_COL, KID_X, SPIG_X, DUEL_Y, TW_Y, CROW_X, CROW_Y) = (
    define(n, QD_C) for n in ("QD_READY_LEN", "QD_WAIT_MIN", "QD_WAIT_SPAN", "QD_SHOW_LEN",
                              "QD_FEINT_LEN", "QD_FEINT_GAP", "QD_ROUND_PTS", "QD_SPEED_PTS", "QD_MATCH_PTS",
                              "SIGN_COL", "SIGN_ROW", "SIGN_W", "LET_COL", "PIP_ROW", "PIP_KID_COL", "PIP_YOU_COL",
                              "KID_X", "SPIG_X", "DUEL_Y", "TW_Y", "CROW_X", "CROW_Y"))
FEINT_FROM = int(_TUNE[0][1])
QH = {m[0]: int(m[1]) for m in re.findall(r"#define (Q\w+) (\d+)", QD_H)}
MG_GAME_BG = 77 + 48
QD_BG = MG_GAME_BG
QD_OBJ, QD_KID, QD_CROW = 56, 96, QD_BG + QH["QD_BG_TILES"]
QD_SODA = QD_CROW + QH["QDO_CROW_N"]
(OAM_WET, OAM_FOAM, OAM_HAND_YOU, OAM_HAND_KID, OAM_AIM, OAM_SPIG, OAM_KID, OAM_TW, OAM_CROW, OAM_N, STREAM_ROW, STREAM_N,
 STREAM_STEP, STREAM_CUT, WET_AT, DRIP_AT, FOUL_FIZZ, FOUL_FOAM_AT, FOUL_FOAM_END, FOUL_WET_AT) = (
    define(n, QD_C) for n in ("OAM_WET", "OAM_FOAM", "OAM_HAND_YOU", "OAM_HAND_KID", "OAM_AIM", "OAM_SPIG", "OAM_KID",
                              "OAM_TW", "OAM_CROW", "OAM_N", "STREAM_ROW", "STREAM_N", "STREAM_STEP", "STREAM_CUT",
                              "WET_AT", "DRIP_AT", "FOUL_FIZZ", "FOUL_FOAM_AT", "FOUL_FOAM_END", "FOUL_WET_AT"))
B_STILL, B_UP, B_DOWN, B_FIZZ, B_FOAM = range(5)
W_SPLASH, W_DRIP_A, W_DRIP_B = range(3)
ST_MID_A, ST_MID_B, ST_HEAD_R, ST_HEAD_L, ST_RISE_R = range(5)
SEED = 0x5A17
OUT = ROOT / "out" / "qd"


def qd(gb):
    b = gb.read("story_scratch", 16)
    return dict(st=b[0], round=b[1], you=b[2], kid=b[3], wait=b[4] | b[5] << 8, badge=b[6], r=b[7], t=b[8], res=b[9],
                react=b[10], feint=b[11], feint_at=b[12] | b[13] << 8, feint_t=b[14], fx=b[15])


def poke_wait(gb, w):
    a = gb.addr("story_scratch")
    gb.write(a + 4, w & 0xFF)
    gb.write(a + 5, w >> 8)


def quickdraw(model, mode=MG_PRACTICE, seed=SEED):
    """A booted rom on the title, then Quick Draw in practice (or `mode`)."""
    from test_scores import booted
    rom = booted(model)
    hold_stage_anim(rom)
    mg_enter(rom, MG_QUICKDRAW, mode, seed)
    return rom


def shot(gb, name):
    OUT.mkdir(parents=True, exist_ok=True)
    gb.screenshot(OUT / f"{name}.{gb.model_name}.png", 4)


def to_state(gb, st, limit=900):
    until(gb, lambda: qd(gb)["st"] == st, limit)


def tap(gb, b):
    gb.hold(b)
    frames(gb, 1)
    gb.release(b)
    frames(gb, 1)


def right_button(gb):
    return "b" if qd(gb)["badge"] else "a"


def to_draw(gb):
    """The next round's wait cut short (qd_wait poked to 1): DRAW! on the next frame."""
    to_state(gb, QS_WAIT)
    poke_wait(gb, 1)
    to_state(gb, QS_DRAW, 5)


def press_on(gb, at, button=None):
    """At DRAW!: the button pressed so that the game sees it on frame `at` after DRAW! (held from the frame before)."""
    while qd(gb)["t"] < at - 1:
        frames(gb, 1)
    assert qd(gb)["st"] == QS_DRAW and qd(gb)["t"] == at - 1
    tap(gb, button or right_button(gb))


def win_round(gb, at=5):
    to_draw(gb)
    press_on(gb, at)
    assert qd(gb)["res"] == QR_YOU and qd(gb)["react"] == at


def lose_round(gb):
    """A foul: A during the wait."""
    to_state(gb, QS_WAIT)
    frames(gb, 2)
    tap(gb, "a")
    assert qd(gb)["res"] == QR_FOUL


def after_show(gb):
    until(gb, lambda: qd(gb)["st"] in (QS_READY, QS_OVER), SHOW_LEN + 5)


def oam(gb, i):
    a = 0xFE00 + 4 * i
    return dict(y=gb.mem(a), x=gb.mem(a + 1), tile=gb.mem(a + 2), prop=gb.mem(a + 3))


def bg_vram(gb, t):
    return bytes(gb.read((0x9000 if t < 128 else 0x8000) + t * 16, 16))


def shown(gb, i):
    o = oam(gb, i)
    return o["tile"] if o["y"] else None


def poses(gb):
    """(the Spigoteer's first tile, the Kid's first tile, the bottle in the Spigoteer's fist, in the Kid's, the aimed
    bottle, the wet overlay, the foul's foam): tiles, None when not shown."""
    return (oam(gb, OAM_SPIG)["tile"], oam(gb, OAM_KID)["tile"]) + tuple(
        shown(gb, i) for i in (OAM_HAND_YOU, OAM_HAND_KID, OAM_AIM, OAM_WET, OAM_FOAM))


def kid_tile(f):
    return QD_KID + f * 8


def spig_tile(f):                               # mg_spigoteer frames: 7 stand, 8 draw (OBJ 56, 64); 6 fail
    return f * 8


def bottle(f):                                  # the bottle in a fist (shake_bottle.txt): B_*
    return QD_SODA + QH["QDS_BOT"] + 2 * f


def aim(f):                                     # the aimed bottle, f the spurt's flicker (left entry)
    return QD_SODA + QH["QDS_AIM"] + 4 * f


def wet(f):                                     # the wet overlay: W_* (left entry)
    return QD_SODA + QH["QDS_WET"] + 4 * f


def stream_tile(k):
    return QD_SODA + QH["QDS_STREAM"] + k


STILL, AIMS, DRIPS = bottle(B_STILL), (aim(0), aim(1)), (wet(W_DRIP_A), wet(W_DRIP_B))
SHAKE_KID_BR, SHAKE_SPIG_BL = QD_SODA + QH["QDS_KID_BR"], QD_SODA + QH["QDS_SPIG_BL"]


def shake_bodies(gb, kid=True, you=True):
    """The STAND bodies with the holstered bottle out (it is in the fist): the Kid's BR entry, the Spigoteer's BL."""
    if kid:
        assert oam(gb, OAM_KID)["tile"] == kid_tile(KID_STAND) and oam(gb, OAM_KID + 3)["tile"] == SHAKE_KID_BR
    if you:
        assert oam(gb, OAM_SPIG)["tile"] == spig_tile(7) and oam(gb, OAM_SPIG + 2)["tile"] == SHAKE_SPIG_BL


def wall_row(gb):
    return tilemap_row(gb, STREAM_ROW, 0, 20)


def sign_rows(gb):
    return [tilemap_row(gb, SIGN_ROW + 1, LET_COL, 12), tilemap_row(gb, SIGN_ROW + 2, LET_COL, 12)]


def face_rows(badge, model="cgb"):
    a, b = [], []
    for k in range(4):
        c = QD_BG + QH["QDB_LETTERS"] + 4 * k
        a += [c, c + 1]
        b += [c + 2, c + 3]
    a += [QD_BG + QH["QDB_BANG"], QD_BG + QH["QDB_FACE"]]
    b += [QD_BG + QH["QDB_BANG"] + 1, QD_BG + QH["QDB_FACE"]]
    c = QD_BG + (QH["QDB_BADGE"] + 4 if badge and model == "cgb" else QH["QDB_BADGE_DMG"] if badge else QH["QDB_BADGE"])
    return [a + [c, c + 1], b + [c + 2, c + 3]]


BACK_ROWS = [[QD_BG + QH["QDB_BACK"]] * 12] * 2


def badge_attrs(gb):                            # CGB: the badge's four cells' BG palette numbers
    return [gb.pb.memory[1, 0x9800 + r * 32 + LET_COL + 10 + c] & 7 for r in (SIGN_ROW + 1, SIGN_ROW + 2) for c in (0, 1)]


def bg_tile_px(gb, t):                          # the 64 pixels (colour 0-3) of BG tile id t (bank 0)
    raw = bytes(gb.read(0x8000 + t * 16, 16)) if t < 128 else bytes(gb.read(0x8800 + (t - 128) * 16, 16))
    return [((raw[2 * y + 1] >> (7 - x)) & 1) << 1 | (raw[2 * y] >> (7 - x)) & 1 for y in range(8) for x in range(8)]


def pips(gb):
    """(the Kid's rounds, the player's) as the pips on row 12 show them."""
    on = QD_BG + QH["QDB_PIP_ON"]
    k, y = tilemap_row(gb, PIP_ROW, PIP_KID_COL, 3), tilemap_row(gb, PIP_ROW, PIP_YOU_COL, 3)
    assert set(k + y) <= {on, QD_BG + QH["QDB_PIP_OFF"]}
    assert k == sorted(k, key=lambda t: t != on) and y == sorted(y, key=lambda t: t != on), "filled from the left"
    return k.count(on), y.count(on)


def reaction_text(react):
    h = (react * 100 + 30) // 60
    return f"YOU 0 {h:02d}"                     # (the '.' is the story font's tile: checked on its own)


# ---- the screen ----------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_screen(model):
    """The intro: the banner, no timer, the sign's frame and planks, the empty pips, the duelists where the approved
    mock-up has them; the art in VRAM; CGB attributes (the sign in palette 2, the pips in the bar's palette 0) and the
    sign / Kid / feint palettes; DMG OBP1 0xE4 (the title leaves 0xC4)."""
    with quickdraw(model) as gb:
        frames(gb, 30)
        assert gb.mem("mg_id") == MG_QUICKDRAW and gb.mem("venue_id") == 0 and gb.mem16("mg_timer") == 0
        assert text(gb, 2) == "QUICK DRAW" and text(gb, 3) == "PRESS A OR B ON DRAW"
        assert tilemap_row(gb, 0, 16, 4) == [BLANK] * 4, "no timer"
        fr = QD_BG + QH["QDB_FRAME"]
        assert tilemap_row(gb, SIGN_ROW, SIGN_COL, SIGN_W) == [fr] + [fr + 1] * (SIGN_W - 2) + [fr + 2]
        assert tilemap_row(gb, SIGN_ROW + 3, SIGN_COL, SIGN_W) == [fr + 5] + [fr + 6] * (SIGN_W - 2) + [fr + 7]
        for r in (1, 2):
            row = tilemap_row(gb, SIGN_ROW + r, SIGN_COL, SIGN_W)
            assert row[0] == fr + 3 and row[-1] == fr + 4
        assert sign_rows(gb) == BACK_ROWS
        assert pips(gb) == (0, 0)
        sp = oam(gb, OAM_SPIG)
        assert (sp["x"], sp["y"], sp["tile"]) == (SPIG_X + 8, DUEL_Y + 16, spig_tile(7))
        k = oam(gb, OAM_KID)
        assert (k["x"], k["y"], k["tile"]) == (KID_X + 8, DUEL_Y + 16, kid_tile(KID_STAND))
        shake_bodies(gb)
        assert poses(gb) == (spig_tile(7), kid_tile(KID_STAND), STILL, STILL, None, None, None), "the intro: held still"
        assert all(oam(gb, i)["y"] == 0 for i in (OAM_WET + 1, OAM_AIM + 1, OAM_TW, OAM_TW + 1, OAM_CROW))
        assert all(oam(gb, i)["y"] == 0 for i in range(OAM_N, 40))
        bg = b"".join(bg_vram(gb, t) for t in range(QD_BG, QD_BG + QH["QD_BG_TILES"]))
        assert bg == bytes(ART["qd_bg"])
        obj = ART["qd_obj"]
        n_a, n_k = QH["QDO_RUN_A"], QH["QDO_KID_N"]
        assert bytes(gb.read(0x8000 + QD_OBJ * 16, n_a * 16)) == bytes(obj[:n_a * 16])
        assert bytes(gb.read(0x8000 + QD_KID * 16, n_k * 16)) == bytes(obj[n_a * 16:(n_a + n_k) * 16])
        assert bytes(gb.read(0x8000 + QD_CROW * 16, QH["QDO_RUN_C"] * 16)) == bytes(obj[(n_a + n_k) * 16:])
        assert len(obj) == (n_a + n_k + QH["QDO_RUN_C"]) * 16 and n_k == 24 and n_a == 24, "no FUMBLE poses"
        if model == "cgb":
            from test_lift import cgb_bg_palette, cgb_obj_palette
            attr = lambda r, c: gb.pb.memory[1, 0x9800 + r * 32 + c] & 7
            assert all(attr(SIGN_ROW + r, SIGN_COL + c) == 2 for r in range(4) for c in range(SIGN_W))
            assert all(attr(PIP_ROW, c) == 0 for c in list(range(PIP_KID_COL, PIP_KID_COL + 3))
                       + list(range(PIP_YOU_COL, PIP_YOU_COL + 3)))
            assert k["prop"] & 7 == 3 and oam(gb, OAM_KID + 2)["prop"] & 7 == 4, "the Kid: palettes 3 (top) and 4"
            assert oam(gb, OAM_HAND_YOU)["prop"] & 7 == 1 and oam(gb, OAM_HAND_KID)["prop"] & 7 == 1, "the bottles: 1"
            assert cgb_bg_palette(gb, 2)[2] != cgb_bg_palette(gb, 2)[0], "the sign's own palette"
            assert cgb_obj_palette(gb, 3)[2] != cgb_obj_palette(gb, 4)[2], "orange serape top, green below"
        else:
            assert gb.mem(0xFF49) == 0xE4 and k["prop"] & 0x10, "the Kid on OBP1 (0xE4)"
            assert oam(gb, OAM_SPIG)["prop"] & 0x10 == 0, "the Spigoteer on OBP0"
            assert oam(gb, OAM_HAND_KID)["prop"] & 0x10 == 0, "the bottles on OBP0"
        shot(gb, "intro")
        check_golden(gb, "qd_intro")


# ---- a round ---------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_round_ready_steady_draw_and_won(model):
    """ROUND 1 / WAIT FOR THE SIGN for 60 frames and through the wait, DRAW! with the A badge and the bell, the player's A on
    frame t: 500 + (R - t) x 20 points, "YOU 0.08" with the story font's '.', the poses (he aims his uncorked bottle,
    the Kid holds his), his pip, then the planks again and round 2 (both shaking again)."""
    with quickdraw(model) as gb:
        until(gb, lambda: gb.mem("mg_phase") == MG_PLAY, 200)
        frames(gb, 2)
        s = qd(gb)
        assert s["st"] == QS_READY and s["round"] == 1 and s["r"] == KID_R[0] and s["badge"] == 0
        assert text(gb, 2) == "ROUND 1" and text(gb, 3) == "WAIT FOR THE SIGN"
        assert WAIT_MIN <= s["wait"] < WAIT_MIN + WAIT_SPAN and s["feint"] == QF_NONE
        until(gb, lambda: qd(gb)["st"] == QS_WAIT, READY_LEN + 2)
        frames(gb, 2)
        assert text(gb, 3) == "WAIT FOR THE SIGN" and sign_rows(gb) == BACK_ROWS
        bells = gb.read("sfx_count", 9)[SFX_CATCH]
        to_draw(gb)
        frames(gb, 2)
        assert sign_rows(gb) == face_rows(0, model) and text(gb, 3) == "" and gb.read("sfx_count", 9)[SFX_CATCH] == bells + 1
        if model == "cgb":
            assert badge_attrs(gb) == [2] * 4, "badge A stays in the sign's palette 2"
        shot(gb, "draw")
        check_golden(gb, "qd_draw")
        before = score(gb)
        press_on(gb, 5, "a")
        s = qd(gb)
        assert s["st"] == QS_SHOW and s["res"] == QR_YOU and s["react"] == 5 and (s["you"], s["kid"]) == (1, 0)
        pts = ROUND_PTS + (KID_R[0] - 5) * SPEED_PTS
        assert gb.mem16("mg_score") == pts and score(gb) == before + pts
        frames(gb, 2)
        assert text(gb, 3) == reaction_text(5)
        assert tilemap_row(gb, 3, 11, 1) == [QD_BG + QH["QDB_PERIOD"]], "the '.'"
        assert pips(gb) == (0, 1)
        p = poses(gb)
        assert p[:4] == (spig_tile(8), kid_tile(KID_STAND), None, STILL) and p[4] in AIMS and p[5:] == (None, None)
        shake_bodies(gb, you=False)
        assert oam(gb, OAM_AIM)["prop"] & 0x20, "his aimed bottle: the Kid's art X-flipped"
        assert not oam(gb, OAM_HAND_KID)["prop"] & 0x60, "the Kid's bottle: held as ever, not flipped"
        shot(gb, "you_win")
        check_golden(gb, "qd_you_win")
        after_show(gb)
        frames(gb, 2)
        assert qd(gb)["round"] == 2 and sign_rows(gb) == BACK_ROWS and text(gb, 2) == "ROUND 2"
        shake_bodies(gb)
        p = poses(gb)
        assert p[2] in (bottle(B_UP), bottle(B_DOWN)) and p[3] in (bottle(B_UP), bottle(B_DOWN)) and p[4:] == (None,) * 3


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("at,wins", [(1, True), (KID_R[0], True), (KID_R[0] + 1, False)], ids=["1", "R", "R+1"])
def test_a_press_at_r_wins_and_at_r_plus_1_loses(model, at, wins):
    with quickdraw(model) as gb:
        to_draw(gb)
        press_on(gb, at, "a")                   # (R + 1: the game sees it the frame after the Kid drew)
        s = qd(gb)
        if wins:
            assert s["res"] == QR_YOU and s["react"] == at and gb.mem16("mg_score") == ROUND_PTS + (KID_R[0] - at) * SPEED_PTS
        else:
            assert s["res"] == QR_SLOW and (s["you"], s["kid"]) == (0, 1) and gb.mem16("mg_score") == 0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_no_press_is_too_slow_and_the_kid_draws(model):
    with quickdraw(model) as gb:
        slow = gb.read("sfx_count", 9)[SFX_LIFE]
        to_draw(gb)
        until(gb, lambda: qd(gb)["st"] == QS_SHOW, KID_R[0] + 3)
        s = qd(gb)
        assert s["res"] == QR_SLOW and s["t"] == 0 and (s["you"], s["kid"]) == (0, 1)
        frames(gb, 2)
        assert text(gb, 3) == "TOO SLOW" and pips(gb) == (1, 0) and gb.read("sfx_count", 9)[SFX_LIFE] == slow + 1
        p = poses(gb)
        assert p[:4] == (spig_tile(7), kid_tile(KID_DRAW), STILL, None) and p[4] in AIMS and p[5:] == (None, None)
        shake_bodies(gb, kid=False)
        assert not oam(gb, OAM_AIM)["prop"] & 0x20, "the Kid's aimed bottle: not flipped"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("button", ["a", "b"])
def test_an_early_press_is_a_foul(model, button):
    """A or B during the wait: FOUL, the Kid's round, no points, the sign never flips. (During READY a press is
    ignored: the pause between rounds.)"""
    with quickdraw(model) as gb:
        to_state(gb, QS_READY)
        tap(gb, button)
        assert qd(gb)["st"] == QS_READY and qd(gb)["res"] == QR_NONE, "READY: ignored"
        to_state(gb, QS_WAIT)
        frames(gb, 3)
        crash = gb.read("sfx_count", 9)[SFX_BREAK]
        tap(gb, button)
        s = qd(gb)
        assert s["st"] == QS_SHOW and s["res"] == QR_FOUL and (s["you"], s["kid"]) == (0, 1)
        assert gb.mem16("mg_score") == 0 and gb.read("sfx_count", 9)[SFX_BREAK] == crash + 1
        frames(gb, 2)
        assert text(gb, 3) == "FOUL" and sign_rows(gb) == BACK_ROWS and pips(gb) == (1, 0)
        assert poses(gb) == (spig_tile(7), kid_tile(KID_STAND), bottle(B_FIZZ), STILL, None, None, bottle(B_FOAM))
        shake_bodies(gb)
        if button == "a":
            shot(gb, "foul")
            check_golden(gb, "qd_foul")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_wrong_badge_is_a_foul_and_the_right_one_wins(model):
    """The B badge (poked in round 1; rounds 3-5 draw it at random, test_the_rounds): A is FOUL, B wins."""
    for press, res in (("a", QR_WRONG), ("b", QR_YOU)):
        with quickdraw(model) as gb:
            to_state(gb, QS_WAIT)
            gb.write(gb.addr("story_scratch") + 6, 1)
            poke_wait(gb, 1)
            to_state(gb, QS_DRAW, 5)
            frames(gb, 2)
            assert sign_rows(gb) == face_rows(1, model)
            press_on(gb, 6, press)
            assert qd(gb)["res"] == res, press
            frames(gb, 2)
            if res == QR_WRONG:
                assert text(gb, 3) == "FOUL" and gb.mem16("mg_score") == 0 and pips(gb) == (1, 0)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_b_badge_looks_different_from_the_a_badge(model):
    """CGB: B's cells use BG palette 3 (a blue disc) while A's stay in palette 2 and the planks put it back; DMG: B is the
    inverted tiles (a light disc, dark outline and letter) against A's dark disc. Same tiles as the art generator made."""
    shots = {}
    for badge in (0, 1):
        with quickdraw(model) as gb:
            to_state(gb, QS_WAIT)
            gb.write(gb.addr("story_scratch") + 6, badge)
            poke_wait(gb, 1)
            to_state(gb, QS_DRAW, 5)
            frames(gb, 2)
            assert sign_rows(gb) == face_rows(badge, model)
            c = sign_rows(gb)[0][10]            # the badge's top-left tile: the disc's rim; the centre cell is TL's corner
            tiles = [bg_tile_px(gb, t) for t in sign_rows(gb)[0][10:] + sign_rows(gb)[1][10:]]
            assert len(tiles[0]) == 64
            if model == "cgb":
                from test_lift import cgb_bg_palette
                assert badge_attrs(gb) == [2 + badge] * 4
                pa, pb = cgb_bg_palette(gb, 2), cgb_bg_palette(gb, 3)
                shots[badge] = pb[3] if badge else pa[3]
                if badge:
                    assert pb[3] != pa[3] and pb[2] != pa[2], "B's disc is another colour"
                    b = pb[3]
                    assert (b >> 10 & 31) > 2 * (b & 31) and (b >> 10 & 31) > (b >> 5 & 31), "blue (BGR555)"
                    check_golden(gb, "qd_draw_b")
                    press_on(gb, 6, "b")
                    frames(gb, 62)
                    until(gb, lambda: sign_rows(gb) == BACK_ROWS, 200)
                    assert badge_attrs(gb) == [2] * 4, "the planks are back in palette 2"
            else:
                shots[badge] = [sum(1 for px in t if px == 3) for t in tiles]
                if badge:
                    check_golden(gb, "qd_draw_b")
    if model == "dmg":
        assert sum(shots[0]) > sum(shots[1]) + 40, "A: a dark disc; B: mostly light with a dark rim and letter"
    else:
        assert shots[0] != shots[1]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_button_held_through_the_sign_does_not_count(model):
    """Only a fresh press counts: A pressed during READY (ignored) and held through the wait and DRAW! is no press at
    all, so the Kid wins (TOO SLOW); and it was no foul either."""
    with quickdraw(model) as gb:
        to_state(gb, QS_READY)
        gb.hold("a")
        frames(gb, 2)
        to_state(gb, QS_WAIT)
        frames(gb, 3)
        poke_wait(gb, 1)
        until(gb, lambda: qd(gb)["st"] == QS_SHOW, KID_R[0] + 10)
        gb.release("a")
        assert qd(gb)["res"] == QR_SLOW


# ---- the match -------------------------------------------------------------------------------------------------------------
def play(gb, seq):
    """Rounds as a string: W the player wins (A/B on frame 5), L a foul. Returns the points of the rounds won."""
    pts = 0
    for i, c in enumerate(seq):
        assert qd(gb)["round"] in (i, i + 1)
        if c == "W":
            win_round(gb)
            pts += ROUND_PTS + (KID_R[i] - 5) * SPEED_PTS
        else:
            lose_round(gb)
        after_show(gb)
    return pts


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("seq,medal", [("WWW", MEDAL_GOLD), ("WLWW", MEDAL_SILVER), ("LWLWW", MEDAL_SILVER),
                                       ("WLLWL", MEDAL_BRONZE), ("LLWL", MEDAL_BRONZE), ("LLL", MEDAL_NONE)])
def test_best_of_five_stops_at_three_and_the_medal_is_the_rounds(model, seq, medal):
    """First to three ends the match on its round (never a 6th); YOU WIN / THE KID WINS and the score line; the
    match won +2000; the outro poses (YOU WIN: the Spigoteer aims, no stream, the Kid drips holding his bottle; THE KID
    WINS: the Kid cheers, the Spigoteer drips holding his); the medal: GOLD 3-0, SILVER 3-1 / 3-2, BRONZE lost with a
    round, else none."""
    with quickdraw(model) as gb:
        start, wall0 = score(gb), wall_row(gb)
        pts = play(gb, seq)
        you, kid = seq.count("W"), seq.count("L")
        s = qd(gb)
        assert s["st"] == QS_OVER and s["round"] == len(seq) and (s["you"], s["kid"]) == (you, kid)
        assert gb.mem("mg_phase") == MG_END
        frames(gb, 2)
        won = you == 3
        assert text(gb, 2) == ("YOU WIN" if won else "THE KID WINS")
        assert text(gb, 3) == (f"3 TO {kid}" if won else f"3 TO {you}")
        assert gb.mem16("mg_score") == pts + (MATCH_PTS if won else 0)
        p = poses(gb)
        if won:
            assert p[:4] == (spig_tile(8), kid_tile(KID_STAND), None, STILL) and p[4] == aim(0) and p[5] in DRIPS
            assert p[6] is None
            shake_bodies(gb, you=False)
        else:
            assert p[:5] == (spig_tile(7), kid_tile(KID_CHEER), STILL, None, None) and p[5] in DRIPS and p[6] is None
            shake_bodies(gb, kid=False)
        assert wall_row(gb) == wall0, "no stream on the end screen"
        if seq == "LLL":
            shot(gb, "kid_cheer")
            check_golden(gb, "qd_kid_cheer")
        if seq == "WWW":
            shot(gb, "match_won")
            check_golden(gb, "qd_match_won")
        until(gb, lambda: gb.mem("mg_phase") == MG_RESULT, END_LEN + 2)
        until(gb, lambda: gb.mem("overlay_on") == 1, 10)
        frames(gb, 2)
        assert gb.mem("mg_medal") == medal
        assert score(gb) == start + pts + (MATCH_PTS if won else 0) + MEDAL_PTS[medal]
        assert text(gb, 1, True, x0=4) == "QUICK DRAW" and text(gb, 4, True, x0=4) == "A RETRY B MENU"
        word = ["NO MEDAL", "BRONZE 500", "SILVER 1500", "GOLD 3000"][medal]
        assert text(gb, 3, True, x0=4) == word
        if seq == "WWW":
            shot(gb, "result")
            check_golden(gb, "qd_result")


# ---- the draw of the rounds: waits, badges, feints, seeds -----------------------------------------------------------------
def round_draws(model, seed):
    """Rounds 1-5 with seed (fouls in rounds 1-2, wins in 3-5: 3-2): per round (wait, badge, R, feint, feint_at)."""
    out = []
    with quickdraw(model, seed=seed) as gb:
        for i, c in enumerate("LLWWW"):
            to_state(gb, QS_WAIT)
            s = qd(gb)
            out.append((s["wait"], s["badge"], s["r"], s["feint"], s["feint_at"]))
            win_round(gb) if c == "W" else lose_round(gb)
            after_show(gb)
    return out


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_rounds_follow_the_seed_and_the_rules(model):
    """W = 90 + 0..210 frames (READY's 60 come first); R 34 30 30 28 26; badges A in rounds 1-2, A or B after; a
    feint from round 3 only, starting no later than its wait allows: it ends >= 30 frames before DRAW!; mg_seed_force
    repeats a match exactly."""
    seen = []
    for seed in (0x1234, 0x0F0F, 0xBEEF, 0x5A17):
        a = round_draws(model, seed)
        seen += a
        for i, (w, badge, r, feint, at) in enumerate(a):
            rnd = i + 1
            assert r == KID_R[i]
            assert WAIT_MIN - 2 <= w <= WAIT_MIN + WAIT_SPAN - 1, "(read on the wait's first frames)"
            if rnd < FEINT_FROM:
                assert badge == 0 and feint == QF_NONE
            else:
                assert feint in (QF_TUMBLE, QF_CROW) and FEINT_GAP + FEINT_LEN <= at <= w + 2
    assert round_draws(model, 0x1234) == seen[:5], "the same seed, the same match"
    assert {b for (_, b, _, _, _) in seen[2::5] + seen[3::5] + seen[4::5]} == {0, 1}, "rounds 3-5: both badges"
    assert {f for (_, _, _, f, _) in seen if f} == {QF_TUMBLE, QF_CROW}, "both feints"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("seed", [0x1234, 0x0F0F, 0xBEEF])
def test_feints_never_inside_the_last_30_frames(model, seed):
    """Rounds 3-5 played to DRAW! frame by frame: a feint shows once, for QD_FEINT_LEN frames, only while 30 or more
    frames of the wait are left; the tumbleweed rolls along the floor (SFX_SHAKE), the crow drops onto the sign, caws
    (SFX_LAUNCH) and leaves; none in rounds 1-2; <= 10 sprites a line throughout."""
    with quickdraw(model, seed=seed) as gb:
        for i, c in enumerate("LLWWW"):
            to_state(gb, QS_WAIT)
            kind = qd(gb)["feint"]
            sfx0 = list(gb.read("sfx_count", 9))
            shown, worst = 0, [0]
            while qd(gb)["st"] == QS_WAIT:
                frames(gb, 1, worst)
                s = qd(gb)
                tw = oam(gb, OAM_TW)["y"] or oam(gb, OAM_TW + 1)["y"]
                crow = oam(gb, OAM_CROW)
                if s["st"] != QS_WAIT:
                    assert not tw and not crow["y"], "gone at DRAW!"
                    break
                if tw or crow["y"]:
                    shown += 1
                    assert s["wait"] >= FEINT_GAP, (i, s)
                    if tw:
                        assert kind == QF_TUMBLE and oam(gb, OAM_TW)["y"] == TW_Y + 16
                    else:
                        assert kind == QF_CROW and crow["x"] == CROW_X + 8 and crow["y"] <= CROW_Y + 16
            sfx = list(gb.read("sfx_count", 9))
            if i + 1 < FEINT_FROM:
                assert kind == QF_NONE and shown == 0
            else:
                assert shown >= FEINT_LEN - 8, (i, shown)          # (frames off screen at either end)
                assert sfx[SFX_SHAKE if kind == QF_TUMBLE else SFX_LAUNCH] == sfx0[SFX_SHAKE if kind == QF_TUMBLE else SFX_LAUNCH] + 1
            assert worst[0] <= 8
            if c == "W":
                press_on(gb, 4)
            else:
                assert qd(gb)["st"] == QS_DRAW
                until(gb, lambda: qd(gb)["st"] == QS_SHOW, KID_R[i] + 3)
            after_show(gb)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_feint_on_screen(model):
    """Round 3 of seed 0x1234 (fouls in rounds 1-2), half way through its feint."""
    with quickdraw(model, seed=0x1234) as gb:
        lose_round(gb)
        after_show(gb)
        lose_round(gb)
        after_show(gb)
        to_state(gb, QS_WAIT)
        s = qd(gb)
        assert s["feint"] != QF_NONE
        until(gb, lambda: qd(gb)["wait"] <= qd(gb)["feint_at"] and qd(gb)["feint_t"] == 30, 400)
        frames(gb, 1)
        assert text(gb, 2) == "ROUND 3" and text(gb, 3) == "WAIT FOR THE SIGN"
        shot(gb, "feint")
        check_golden(gb, "qd_feint")


# ---- the soda duel (owner-approved 2026-10-11) -----------------------------------------------------------------------
def hand_y(dy=0):
    return DUEL_Y + 6 + dy + 16


# (Tests look at the screen: the tilemap and OAM after the VBlank that follows the game's frame t - 1. The frame a
# round ends on runs long, so the frames of the round-end hold are keyed by the game's t, not counted.)
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_shake_runs_through_the_banner_and_stops_at_draw(model):
    """The intro holds still; from ROUND 1 / WAIT FOR THE SIGN to DRAW! both shake their bottles, UP (2 px up) and
    DOWN (1 px down), out of step (the Kid every 4 frames, the Spigoteer every 5), in the STAND bodies without the
    holstered bottle; at DRAW! both freeze holding the bottle STILL until the round ends."""
    up, down = bottle(B_UP), bottle(B_DOWN)
    with quickdraw(model) as gb:
        frames(gb, 30)
        assert poses(gb)[2:] == (STILL, STILL, None, None, None)
        to_state(gb, QS_READY, 300)
        frames(gb, 2)
        kid, you = [], []
        while len(kid) < 120:
            frames(gb, 1)
            assert qd(gb)["st"] in (QS_READY, QS_WAIT)
            shake_bodies(gb)
            p = poses(gb)
            assert p[4:] == (None, None, None)
            ky, yy = oam(gb, OAM_HAND_KID)["y"], oam(gb, OAM_HAND_YOU)["y"]
            assert (p[3], ky) in ((up, hand_y(-2)), (down, hand_y(1))) and (p[2], yy) in ((up, hand_y(-2)), (down, hand_y(1)))
            assert oam(gb, OAM_HAND_KID)["x"] == KID_X + 12 + 8 and oam(gb, OAM_HAND_YOU)["x"] == SPIG_X - 4 + 8
            kid.append(p[3])
            you.append(p[2])
        runs = lambda seq: [len(list(g)) for _, g in itertools.groupby(seq)][1:-1]
        assert set(runs(kid)) == {4} and set(runs(you)) == {5}, (runs(kid), runs(you))
        poke_wait(gb, 1)
        to_state(gb, QS_DRAW, 5)
        frames(gb, 2)
        for _ in range(KID_R[0] - 4):
            frames(gb, 1)
            assert qd(gb)["st"] == QS_DRAW
            shake_bodies(gb)
            assert poses(gb)[2:] == (STILL, STILL, None, None, None)
            assert oam(gb, OAM_HAND_KID)["y"] == oam(gb, OAM_HAND_YOU)["y"] == hand_y()


def spray_row(wall, who, t):
    """The stream row the game's round-end frame t asks for (the two flow tiles as one: 'mid')."""
    row = list(wall)
    if t < 1:
        return row
    n = min(STREAM_STEP * t, STREAM_N)
    cut = STREAM_STEP * (t - STREAM_CUT + 1) if t >= STREAM_CUT else 0
    for k in range(cut, n):
        c = 13 - k if who == "you" else 6 + k
        if k == n - 1 and n < STREAM_N:
            row[c] = stream_tile(ST_HEAD_L if who == "you" else ST_HEAD_R)
        elif k == 0 and who == "kid":
            row[c] = stream_tile(ST_RISE_R)
        else:
            row[c] = "mid"
    return row


def round_end(gb, check=None, shots=()):
    """The round-end hold frame by frame: {the game's t: (the stream row as shown, poses)}, the screen of t keyed by
    t (it shows frame t - 1's update). check(gb) on every frame; shots: {t: golden name}."""
    seen = {}
    while qd(gb)["st"] == QS_SHOW:
        frames(gb, 1)
        t = qd(gb)["t"]
        if qd(gb)["st"] != QS_SHOW:
            break
        if check:
            check(gb)
        seen[t] = (wall_row(gb), poses(gb))
        if t in shots and shots[t]:
            shot(gb, shots[t])
            check_golden(gb, shots[t])
            shots = {**shots, t: None}
    return seen


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("who", ["you", "kid"])
def test_the_winner_sprays_and_the_loser_gets_wet(model, who):
    """The round's winner (the player on a right press; the Kid on TOO SLOW) takes his DRAW pose with the aimed bottle
    (the spurt flickering) and sprays: the stream crosses the wall's row 3 columns a frame (10 in 4 frames, a splash
    leading; the Kid's starts with the RISE tile), flows (MID A / MID B), is cut off from the shooter's end from frame
    36 and the wall is back, tile for tile, by frame 40. The loser holds his bottle STILL throughout; SPLASH on his head
    from frame 4 to 37, then DRIP A / B. The wall is the same before and after the round."""
    mid = (stream_tile(ST_MID_A), stream_tile(ST_MID_B))

    def loser_holds(gb):
        h = OAM_HAND_KID if who == "you" else OAM_HAND_YOU
        assert oam(gb, h)["tile"] == STILL and oam(gb, h)["y"] == hand_y()
        assert not oam(gb, h)["prop"] & 0x60 if who == "you" else oam(gb, h)["prop"] & 0x60 == 0x20

    with quickdraw(model) as gb:
        to_state(gb, QS_WAIT)
        frames(gb, 2)
        wall = wall_row(gb)
        to_draw(gb)
        if who == "you":
            press_on(gb, 5)
        else:
            until(gb, lambda: qd(gb)["st"] == QS_SHOW, KID_R[0] + 3)
        seen = round_end(gb, loser_holds, {20: "qd_spray" if who == "you" else "qd_kid_spray"})
        assert len(seen) >= SHOW_LEN - 3
        flows = set()
        for t, (row, p) in seen.items():
            if t < 2:
                continue
            flows |= {v for v in row if v in mid}
            assert len({v for v in row if v in mid}) <= 1, ("one flow tile at a time", t, row)
            assert ["mid" if v in mid else v for v in row] == spray_row(wall, who, t - 1), t
            if who == "you":
                assert p[0] == spig_tile(8) and p[2] is None and p[3] == STILL
            else:
                assert p[1] == kid_tile(KID_DRAW) and p[3] is None and p[2] == STILL
            assert p[4] in AIMS and p[6] is None
            w = t - 1
            assert p[5] == (None if w < WET_AT else wet(W_SPLASH) if w < DRIP_AT else p[5]), t
            if w >= DRIP_AT:
                assert p[5] in DRIPS
        assert flows == set(mid), "the stream flows"
        assert {p[4] for _, p in seen.values()} == set(AIMS), "the spurt flickers"
        assert {p[5] for _, p in seen.values()} >= set(DRIPS)
        assert seen[STREAM_CUT + 4][0] == wall, "the wall restored by frame 40"
        after_show(gb)
        frames(gb, 2)
        assert wall_row(gb) == wall, "the wall tiles before and after the round"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_foul_fizzes_over_the_player(model):
    """A foul: the Spigoteer's own bottle fizzes (FIZZ frames 0-23) with the foam column above it (2-17), the SPLASH on
    his head (6-23), then the drips and the bottle STILL again; the Kid stands holding his bottle; no stream."""
    with quickdraw(model) as gb:
        to_state(gb, QS_WAIT)
        frames(gb, 3)
        wall = wall_row(gb)
        tap(gb, "a")
        assert qd(gb)["res"] == QR_FOUL
        seen = round_end(gb, shots={10: "qd_foul_fizz"})
        assert len(seen) >= SHOW_LEN - 4
        for t, (row, p) in seen.items():
            if t < 3:
                continue
            w = t - 1
            assert row == wall
            assert p[:2] == (spig_tile(7), kid_tile(KID_STAND)) and p[3] == STILL and p[4] is None, t
            assert p[2] == (bottle(B_FIZZ) if w < FOUL_FIZZ else STILL), t
            assert p[6] == (bottle(B_FOAM) if FOUL_FOAM_AT <= w < FOUL_FOAM_END else None), t
            if w < FOUL_WET_AT:
                assert p[5] is None, t
            elif w < FOUL_FIZZ:
                assert p[5] == wet(W_SPLASH), t
            else:
                assert p[5] in DRIPS, t
        assert {p[5] for _, p in seen.values()} >= set(DRIPS)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_whole_match_keeps_to_10_sprites_a_line(model):
    """A full match (seed 0x1234: the player wins, too slow, a foul, then wins with the feints of rounds 3-5) played
    frame by frame from the intro to the result: never more than 10 sprites on a line (the soda duel's worst is 9:
    the spray's row, 2 a man, 2 the aimed bottle, 1 the loser's bottle, 2 the wet overlay)."""
    plan = "WSLWW"
    with quickdraw(model, seed=0x1234) as gb:
        worst, fouled = [0], set()
        while gb.mem("mg_phase") != MG_RESULT:
            s = qd(gb)
            c = plan[max(s["round"] - 1, 0)]
            if gb.mem("mg_phase") == MG_PLAY and s["st"] == QS_WAIT and c == "L" and s["round"] not in fouled:
                fouled.add(s["round"])
                tap(gb, "a")
            elif gb.mem("mg_phase") == MG_PLAY and s["st"] == QS_DRAW and c == "W" and s["t"] == 3:
                tap(gb, right_button(gb))
            else:
                frames(gb, 1, worst)
        s = qd(gb)
        assert (s["you"], s["kid"], s["round"]) == (3, 2, 5)
        assert worst[0] <= 9, worst

# ---- after Quick Draw: everything it borrowed is back --------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_level_after_quick_draw_has_everything_back(model):
    """Quick Draw (a round played) -> B to the list -> the title -> a level: the level's OBJ tiles 0-127 (bartender,
    drink, crash, coin, show) and BG / OBJ 77-255, OBP1 and the palettes are byte for byte those of a level started from
    a fresh boot (the coin, loaded once at boot, was never touched)."""
    from test_mg import restored
    from test_scores import booted

    def level_vram(gb):
        return bytes(gb.read(0x8000, 0x1000)) + bytes(gb.read(0x9000 + 77 * 16, (128 - 77) * 16))

    with booted(model) as gb:
        hold_stage_anim(gb)
        title_level(gb)
        run_until(gb, lambda: state(gb) == PLAYING, 60)
        gb.run(2)
        fresh = level_vram(gb)
    with quickdraw(model) as gb:
        win_round(gb)
        with logic_paused(gb):                  # (a poke must land between two game frames: conftest.logic_paused)
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
        assert gb.mem("bar_dirs") == 0, "the mirror engine's bars all L again (mirror.c mirror_load at the level load)"
