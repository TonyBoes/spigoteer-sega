# The story map (src/smap.c; owner 2026-10-18, the approved v14 art, Q59-Q70): the screen between a story's chapters. Snapping movement along the v14
# table with locked stops skipped, the direction arrows, the name tag, A at the next venue (its PRE scene), a cleared venue's PLAY / BACK panel (the
# mini-game alone: the medal upgrades, the story's score and progress do not move), the town's FESTIVAL GAMES / THE POUR-OFF panel, the festival's gradual
# unlock and its "!", the Pour-Off's lives (3 + the festival golds of this story run, NORMAL / HARD only, cap +3, reset by a new run), the greyed
# THE POUR-OFF, the save block "SM" and its round trip, the goldens of the screen and its two panels.
import json

import pytest
import test_story as ts
from conftest import K_CONTINUE, ROOT, check_golden, menu_items, menu_tap, title_pick
from test_flow import GS_STORY, run_until, state
from test_mg import mg_enter
from test_scores import booted, v7_image
from test_sound import save_ram

pytestmark = pytest.mark.timeout(300)

SP_MAP, SP_SCENE = 9, 1
GS_MINI, MG_RESULT, MG_RESULT_MIN = 13, 4, 63
MG_MAP, MG_PRACTICE = 8, 1
TOWN = 10
SMAP = json.loads((ROOT / "build" / "smap.json").read_text())
SM_AT = 0x1E
N = None
# the v14 snap table, written out here on its own (up, down, left, right per stop; None: the button does nothing). Stops 0-9 are the chapters.
SNAP = [(1, N, N, 10), (2, 0, N, N), (N, 1, N, 3), (N, N, 2, 4), (N, 5, 3, N), (4, 6, N, N), (5, 7, N, N), (6, N, 8, N), (N, N, 9, 7), (10, N, N, 8), (N, 9, 0, N)]
DIRS = ("up", "down", "left", "right")
STOP_TILE = [(2, 12), (0, 5), (3, 3), (10, 3), (17, 3), (16, 8), (16, 13), (17, 17), (9, 17), (6, 16), (11, 11)]   # the dots' tile coordinates (the v14 notes)
OAM_ARROWS, OAM_SAL, OAM_BANG, OAM_DOTS = 0, 2, 4, 5
OB = 56                                                  # the map's OBJ tiles start at this id (src/smap.c)
DIM_BASE = 233                                           # the greyed letters (tools/gen_smap.py)
INV = {v: k for k, v in ts.GLYPH.items()}
INV.update({DIM_BASE + i: c for i, c in enumerate("THEPOURF-")})
PAIR = SMAP["obj_pairs"]


def to_map(model, progress=3, step=0, ram=None, stop=None, flags=None, cards=True, tag_gone=True):
    """A rom on the story map: CONTINUE from a save with `progress` chapters cleared (a venue's step reached when step > 0). stop / flags are poked after."""
    if progress in (0, 10) and not step and ram is None:
        step = 1                                          # (a save CONTINUE offers: a step reached in chapter 1; all ten cleared and the finale not done)
    rom = booted(model, ram if ram is not None else v7_image([], story=progress, step=step), cards=cards)
    title_pick(rom, ts.K_PLAY, K_CONTINUE, press=False)
    menu_tap(rom, "a")
    run_until(rom, lambda: rom.mem("story_phase") == SP_MAP and state(rom) == GS_STORY, 400)
    rom.run(100 if tag_gone else 4)                      # (the name tag on the window layer is up for the first 90 frames)
    if stop is not None:
        rom.write("smap_stop", stop)
    if flags is not None:
        rom.write("smap_flags", flags)
    rom.run(2)
    return rom


def tap(gb, b, wait=8):
    gb.press(b, 2)
    gb.run(wait)


def win_text(gb, r):
    """Window row r as text (the greyed letters read as their letters)."""
    return "".join(" " if (t & 0xFF) == ts.GLYPH[" "] else INV.get(t & 0xFF, "#") for t in gb.bg_tilemap(True)[r][:20]).strip()


def oam(gb, i):
    return gb.oam()[i]


def shown(gb, i):
    return oam(gb, i)["y"] != 0


def sal_xy(gb):
    """Sal's top-left (his left column may be off the screen's edge: then its entry is hidden and the right one gives it)."""
    o = oam(gb, OAM_SAL)
    if not o["y"]:
        o = oam(gb, OAM_SAL + 1)
        return o["x"] - 16, o["y"] - 16
    return o["x"] - 8, o["y"] - 16


# ---- the screen -------------------------------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_map_is_up_with_its_stops_dots_and_sal(model):
    gb = to_map(model, 3)
    assert gb.mem("story_phase") == SP_MAP and state(gb) == GS_STORY and gb.mem("smap_stop") == 3, "CONTINUE: Sal at the next venue (chapter 4)"
    for s, (tx, ty) in enumerate(STOP_TILE):
        o = oam(gb, OAM_DOTS + s)
        assert (o["x"] - 8, o["y"] - 16) == (tx * 8, ty * 8), s
        openstop = s <= 3 or s == TOWN
        assert o["tile"] == OB + PAIR["dot_open0" if openstop else "dot_locked0"], f"stop {s}: open = the filled diamond, locked = hollow with a cross"
    assert sal_xy(gb) == (10 * 8 - 8, 3 * 8 - 14), "Sal stands left of and above the stop's dot"
    used = sum(1 for o in gb.oam() if o["y"])
    assert 16 <= used <= 19, used
    per = [0] * 144                                      # 8x16 mode: the worst scanline stays under the hardware's 10
    for o in gb.oam():
        for y in range(max(0, o["y"] - 16), min(144, o["y"])) if o["y"] else ():
            per[y] += 1
    assert max(per) <= 10, max(per)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_picture_is_the_approved_one_tile_for_tile(model):
    gb = to_map(model, 10, step=1)
    assert [t & 0xFF for row in gb.bg_tilemap()[:18] for t in row[:20]] == SMAP["map"]
    tiles = bytes.fromhex(SMAP["tiles_hex"])
    for k, tid in enumerate(SMAP["ids"]):
        a = 0x9000 + tid * 16 if tid < 128 else 0x8800 + (tid - 128) * 16
        assert bytes(gb.pb.memory[a:a + 16]) == tiles[k * 16:k * 16 + 16], f"tile {k} at BG id {tid}"
    objs = bytes.fromhex(SMAP["obj_hex"])
    assert bytes(gb.pb.memory[0x8000 + OB * 16:0x8000 + OB * 16 + len(objs)]) == objs


def test_the_art_budget():
    assert SMAP["ntiles"] == 176 and max(SMAP["ids"]) < DIM_BASE and len(SMAP["bg_pal"]) == 8 and len(SMAP["obj_pal"]) == 6
    assert SMAP["ids"][SMAP["ranges"][1][1]] == 93, "the picture sits around the font's ids 36-92"
    assert SMAP["tile_bytes"] == 176 * 16 and SMAP["obj_bytes"] == 22 * 16


# ---- movement ---------------------------------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_dpad_snaps_along_the_table_with_every_stop_open(model):
    gb = to_map(model, 10, step=1)
    for s in range(11):
        for d, name in enumerate(DIRS):
            gb.write("smap_stop", s)
            gb.run(2)
            tap(gb, name, 4)
            want = SNAP[s][d] if SNAP[s][d] is not None else s
            assert gb.mem("smap_stop") == want, f"stop {s} {name}"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("progress, moves", [
    (3, [(3, "right", 10), (10, "down", 3), (10, "left", 0), (0, "up", 1), (1, "up", 2), (2, "right", 3), (3, "left", 2), (0, "right", 10)]),
    (0, [(0, "up", 10), (0, "right", 10), (10, "left", 0), (10, "down", 0)]),                    # only the saloon and the town are open: the ring passes everything else
    (6, [(6, "down", 10), (5, "down", 6), (6, "up", 5), (10, "down", 6), (4, "down", 5)]),
])
def test_locked_stops_are_skipped(model, progress, moves):
    gb = to_map(model, progress)
    for s, name, want in moves:
        gb.write("smap_stop", s)
        gb.run(2)
        tap(gb, name, 4)
        assert gb.mem("smap_stop") == want, f"progress {progress}: stop {s} {name} -> {gb.mem('smap_stop')}, wanted {want}"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_dots_show_open_and_locked_stops(model):
    gb = to_map(model, 4)
    for s in range(11):
        o = oam(gb, OAM_DOTS + s)
        locked = s > 4 and s != TOWN
        assert (o["tile"] - OB == PAIR["dot_locked0"]) == locked
        if model == "cgb":
            assert (o["flags"] & 7) == (4 if locked else 3), "red palette 4 for a locked stop, green 3 for an open one"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_gold_arrows_show_the_open_directions(model):
    gb = to_map(model, 10, step=1)
    for s in range(11):
        gb.write("smap_stop", s)
        gb.run(3)
        want = sorted(d for d in range(4) if SNAP[s][d] is not None)
        arrows = [o for o in gb.oam()[OAM_ARROWS:OAM_ARROWS + 2] if o["y"]]
        assert len(arrows) == len(want), f"stop {s}"
        sx, sy = sal_xy(gb)
        got = []
        for o in arrows:
            ax, ay, t = o["x"] - 8, o["y"] - 16, o["tile"] - OB
            if t == PAIR["arrow_u0"]:
                assert (ax, ay) == (sx + 4, sy - 9); got.append(0)
            elif t == PAIR["arrow_d0"]:
                assert (ax, ay) == (sx + 4, sy + 17); got.append(1)
            elif o["flags"] & 0x20:
                assert (ax, ay) == (sx - 9, sy + 4); got.append(2)
            else:
                assert (ax, ay) == (sx + 17, sy + 4); got.append(3)
        assert sorted(got) == want, f"stop {s}"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_arrows_follow_the_open_stops_not_the_table(model):
    gb = to_map(model, 3)                                # the bistro: the igloo past it is locked, so right leads round to the town
    assert sum(1 for o in gb.oam()[OAM_ARROWS:OAM_ARROWS + 2] if o["y"]) == 2
    gb.write("smap_stop", 0)
    gb.run(3)
    assert sorted(o["tile"] - OB for o in gb.oam()[OAM_ARROWS:OAM_ARROWS + 2] if o["y"]) == sorted([PAIR["arrow_u0"], PAIR["arrow_r0"]])
    gb.write("smap_stop", 3)
    gb.run(3)
    assert sorted(o["tile"] - OB for o in gb.oam()[OAM_ARROWS:OAM_ARROWS + 2] if o["y"]) == [PAIR["arrow_r0"]] * 2


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_name_tag_shows_90_frames_on_the_window_layer(model):
    gb = to_map(model, 10, step=1, stop=1)
    tap(gb, "up", 3)                     # the lodge: Sal in the top rows: the tag goes along the bottom
    assert gb.mem("smap_stop") == 2
    run_until(gb, lambda: gb.mem("overlay_on") == 3, 6)
    assert gb.regs()["WY"] == 136 and win_text(gb, 0) == "CH3 LUMBER LODGE"
    n = 0
    while gb.mem("overlay_on") == 3 and n < 200:
        gb.run(1)
        n += 1
    assert 85 <= n <= 92, n
    tap(gb, "down", 3)                   # the stadium: the tag at the top
    assert gb.mem("smap_stop") == 1
    run_until(gb, lambda: gb.mem("overlay_on") == 3, 6)
    assert gb.regs()["WY"] == 0 and win_text(gb, 0) == "CH2 THE STADIUM"
    gb.write("smap_stop", 0)
    tap(gb, "right", 3)
    run_until(gb, lambda: gb.mem("overlay_on") == 3, 6)
    assert gb.mem("smap_stop") == TOWN and win_text(gb, 0) == "FESTIVAL SQUARE"
    gb.run(95)
    assert gb.mem("overlay_on") == 0


# ---- A at a venue -----------------------------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("progress", [1, 3, 9])
def test_a_at_the_next_uncleared_venue_starts_its_pre_scene(model, progress):
    gb = to_map(model, progress)
    assert gb.mem("smap_stop") == progress
    tap(gb, "a", 2)
    run_until(gb, lambda: gb.mem("story_phase") == SP_SCENE, 120)
    assert gb.mem("story_scene") == ts.pre(progress) and gb.mem("story_chapter") == progress
    assert gb.mem("overlay_on") == 0, "the map's window is gone"
    assert gb.regs()["WY"] == 64, "the banner window's own place again"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_at_the_next_venue_with_a_step_reached_opens_its_banner_as_continue_did(model):
    gb = to_map(model, 3, step=ts.SHIFT_STEP[1])
    tap(gb, "a", 2)
    run_until(gb, lambda: state(gb) == ts.GS_GOAL, 120)
    assert gb.mem("story_chapter") == 3 and gb.mem("lives") == 3


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_borrowed_hud_palette_flag_is_cleared_once_the_next_screen_is_built(model):
    gb = to_map(model, 3)
    assert (gb.mem("smap_flags") & 0x80 != 0) == (model == "cgb"), "the picture borrowed BG palette 1 (CGB)"
    tap(gb, "a", 2)
    run_until(gb, lambda: gb.mem("story_phase") == SP_SCENE, 120)
    assert gb.mem("smap_flags") & 0x80 == 0, "smap_pal_back put the HUD palette back"


# ---- a cleared venue --------------------------------------------------------------------------------------------------------------------------------------------
def venue_panel(model, progress=5, stop=1):
    gb = to_map(model, progress, stop=stop)
    tap(gb, "a", 20)
    gb.run(10)
    return gb


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_cleared_venue_opens_play_back_and_its_best_medal(model):
    gb = venue_panel(model, 5, 1)
    assert gb.mem("overlay_on") == 3
    assert [win_text(gb, r) for r in range(1, 5)] == ["SHIRT CANNON", "PLAY", "BACK", "BEST: NONE"]
    assert gb.mem("story_progress") == 5 and gb.mem("story_phase") == SP_MAP
    tap(gb, "b", 12)
    assert gb.mem("overlay_on") == 0 and gb.mem("story_phase") == SP_MAP, "B closes the panel"
    tap(gb, "a", 20)
    tap(gb, "down", 4)
    tap(gb, "a", 12)                     # BACK
    assert gb.mem("overlay_on") == 0 and gb.mem("story_phase") == SP_MAP


def play_result(gb, points, bonus=False):
    """The map's game is running: end it at once with `points` (a bonus round reads the score), up to its result screen."""
    run_until(gb, lambda: state(gb) == GS_MINI, 80)
    gb.run(6)
    if bonus:
        a = gb.addr("score")
        for i in range(4):
            gb.write(a + i, (points >> (8 * i)) & 255)
    else:
        gb.write("mg_score", points & 255)
        gb.write(gb.addr("mg_score") + 1, points >> 8)
    gb.write("mg_phase", MG_RESULT)
    run_until(gb, lambda: gb.mem("overlay_on") == 1 and gb.mem("mg_t") >= MG_RESULT_MIN, 200)


def back_to_map(gb):
    gb.press("a", 2)
    run_until(gb, lambda: state(gb) == GS_STORY and gb.mem("story_phase") == SP_MAP, 80)
    gb.run(40)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_play_runs_that_venues_mini_game_only_and_upgrades_the_medal(model):
    gb = venue_panel(model, 5, 1)           # the stadium: Shirt Cannon, bronze 1500, silver 2100, gold 2700
    score = int.from_bytes(gb.read("score", 4), "little")
    tap(gb, "a", 2)                          # PLAY
    run_until(gb, lambda: state(gb) == GS_MINI, 80)
    assert gb.mem("mg_id") == 1 and gb.mem("mg_mode") == MG_PRACTICE | MG_MAP and gb.mem("boss_on") == 0
    assert gb.mem("story_progress") == 5 and gb.mem("story_on") == 1
    play_result(gb, 1600)
    assert gb.mem("mg_medal") == 1 and gb.read("mg_best", 10)[1] & 3 == 1, "bronze saved"
    back_to_map(gb)
    assert gb.mem("smap_stop") == 1 and gb.mem("story_progress") == 5 and gb.mem("story_reached") == 0
    assert int.from_bytes(gb.read("score", 4), "little") == score, "the story's score is as it was"
    tap(gb, "a", 20)
    gb.run(8)                                # the better medal upgrades it ...
    assert win_text(gb, 4) == "BEST: BRONZE"
    tap(gb, "a", 2)
    play_result(gb, 2800)
    assert gb.mem("mg_medal") == 3 and gb.read("mg_best", 10)[1] & 3 == 3
    back_to_map(gb)
    tap(gb, "a", 20)
    gb.run(8)
    assert win_text(gb, 4) == "BEST: GOLD"
    tap(gb, "a", 2)                          # ... a worse one later does not take it away
    play_result(gb, 100)
    assert gb.mem("mg_medal") == 0 and gb.read("mg_best", 10)[1] & 3 == 3
    back_to_map(gb)
    assert gb.mem("story_progress") == 5 and gb.mem("story_reached") == 0 and gb.mem("story_chapter") == 5
    ram = save_ram(gb)
    assert (ram[4] & 0x3F, ram[5]) == (5, 0), "the saved progress did not move"
    assert ram[0x40 + 6 + 1] & 3 == 3, "the saved gold (Practice's block, the stadium's byte)"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_map_play_quit_from_the_pause_menu_returns_to_the_map_without_a_medal(model):
    gb = venue_panel(model, 5, 1)
    tap(gb, "a", 2)
    run_until(gb, lambda: state(gb) == GS_MINI and gb.mem("mg_phase") >= 2, 200)
    gb.run(20)
    tap(gb, "start", 8)                  # the mini-game's pause menu: RESUME / HOW TO PLAY / QUIT TO MENU, then YES
    tap(gb, "down")
    tap(gb, "down")
    tap(gb, "a")
    tap(gb, "up")
    gb.press("a", 2)
    run_until(gb, lambda: state(gb) == GS_STORY and gb.mem("story_phase") == SP_MAP, 120)
    assert gb.read("mg_best", 10)[1] == 0 and gb.mem("story_progress") == 5


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_map_play_on_a_new_games_card_goes_back_with_b(model):
    gb = to_map(model, 5, stop=1, cards=False)
    tap(gb, "a", 20)
    gb.run(10)
    tap(gb, "a", 2)
    run_until(gb, lambda: state(gb) == GS_MINI and gb.mem("mg_phase") == 5, 120)         # MG_CARD
    gb.run(30)
    tap(gb, "b", 2)
    run_until(gb, lambda: state(gb) == GS_STORY and gb.mem("story_phase") == SP_MAP, 120)


# ---- the town and the festival ----------------------------------------------------------------------------------------------------------------------------------
def town_panel(model, progress, flags=0, golds=0):
    gb = to_map(model, progress, stop=TOWN, flags=flags | (golds << 4))
    tap(gb, "a", 20)
    gb.run(10)
    return gb


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_town_panel_offers_the_festival_and_a_greyed_pour_off(model):
    gb = town_panel(model, 9)
    assert gb.mem("overlay_on") == 3
    assert win_text(gb, 1) == "FESTIVAL GAMES" and win_text(gb, 2) == "THE POUR-OFF" and win_text(gb, 3) == "CLEAR ALL VENUES"
    assert any((t & 0xFF) >= DIM_BASE for t in gb.bg_tilemap(True)[2][:20]), "the Pour-Off line is drawn in the dim letters until every venue is cleared"
    tap(gb, "down", 4)
    tap(gb, "a", 20)
    gb.run(8)
    assert gb.mem("story_phase") == SP_MAP and gb.mem("overlay_on") == 3 and win_text(gb, 1) == "FESTIVAL GAMES", "A on the greyed line does nothing"
    gb = town_panel(model, 10)
    assert not any((t & 0xFF) >= DIM_BASE for t in gb.bg_tilemap(True)[2][:20]) and win_text(gb, 3) == "GOLDS: 0"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("progress, want", [(0, 0), (1, 0), (2, 1), (3, 1), (4, 2), (6, 2), (7, 3), (10, 3)])
def test_the_festival_unlocks_gradually_after_chapters_2_4_and_7(model, progress, want):
    gb = to_map(model, progress, stop=TOWN)
    tap(gb, "a", 20)
    gb.run(6)
    tap(gb, "a", 20)
    gb.run(10)
    assert win_text(gb, 4) == "GOLD: 1 LIFE"
    rows = [win_text(gb, r) for r in (1, 2, 3)]
    assert [r != "? ? ?" for r in rows] == [i < want for i in range(3)], rows
    for r, name in zip(rows, ("SHAKE UP", "PERFECT POUR", "TIP SHOWER")):
        if r != "? ? ?":
            assert r.startswith(name) and r.endswith("----"), "no medal yet"


def bang_shown(gb):
    return shown(gb, OAM_BANG)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_gold_bang_shows_over_the_tent_while_a_new_festival_game_has_not_been_played(model):
    gb = to_map(model, 1, stop=TOWN)
    assert not bang_shown(gb), "nothing is unlocked after one chapter"
    for progress, k in ((2, 0), (4, 1), (7, 2)):
        gb.write("story_progress", progress)
        gb.run(3)
        assert bang_shown(gb), f"game {k} just unlocked"
        o = oam(gb, OAM_BANG)
        assert (o["x"] - 8, o["y"] - 16) == (72, 56), "over the tent"
        gb.write("smap_flags", gb.mem("smap_flags") | (1 << k))
        gb.run(3)
        assert not bang_shown(gb), f"game {k} was played"
    gb.write("smap_flags", 0)
    gb.run(3)
    assert bang_shown(gb), "all three are unlocked and unplayed again"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_playing_a_festival_game_clears_its_bang_and_records_it(model):
    gb = to_map(model, 2, stop=TOWN)
    assert bang_shown(gb)
    tap(gb, "a", 20)
    gb.run(6)
    tap(gb, "a", 20)
    gb.run(8)                             # FESTIVAL GAMES
    tap(gb, "a", 2)                       # SHAKE UP
    run_until(gb, lambda: state(gb) == GS_MINI, 80)
    assert gb.mem("mg_id") == 12 and gb.mem("mg_mode") == MG_PRACTICE | MG_MAP
    assert gb.mem("smap_flags") & 1
    play_result(gb, 3500, bonus=True)
    assert gb.mem("mg_medal") == 3
    back_to_map(gb)
    assert not bang_shown(gb) and gb.mem("smap_stop") == TOWN
    tap(gb, "a", 20)
    gb.run(6)
    tap(gb, "a", 20)
    gb.run(8)
    assert win_text(gb, 1).startswith("SHAKE UP") and win_text(gb, 1).endswith("GOLD")


# ---- Pour-Off lives ---------------------------------------------------------------------------------------------------------------------------------------------
def golds_won(gb, ks, diff=0):
    """The festival games ks won GOLD through the map (each a full play from the festival list)."""
    if diff:
        gb.write("story_arc", diff << 1)
    for k in ks:
        gb.write("smap_stop", TOWN)
        gb.run(2)
        tap(gb, "a", 20)
        gb.run(6)
        tap(gb, "a", 20)
        gb.run(8)
        for _ in range(k):
            tap(gb, "down", 4)
        tap(gb, "a", 2)
        play_result(gb, 9000, bonus=True)
        back_to_map(gb)


def pour_off_lives(gb):
    """From the map with all ten cleared: THE POUR-OFF to the Pour-Off's first frame; its lives."""
    gb.write("smap_stop", TOWN)
    gb.run(2)
    tap(gb, "a", 20)
    gb.run(6)
    tap(gb, "down", 4)
    tap(gb, "a", 20)
    gb.run(8)
    if (gb.mem("smap_flags") >> 4) & 7 != 7:
        assert win_text(gb, 1) == "DREGS", "fewer than 3 festival golds: Dregs's nudge"
        tap(gb, "a", 2)
    run_until(gb, lambda: gb.mem("story_phase") == SP_SCENE and gb.mem("story_scene") == ts.SC["FINALE_A"], 120)
    gb.run(60)
    gb.press("start", 2)
    run_until(gb, lambda: state(gb) == GS_MINI, 150)
    gb.run(3)
    assert gb.mem("mg_id") == 11
    return gb.mem("lives")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("ks", [(), (0,), (0, 2), (0, 1, 2)])
def test_pour_off_lives_are_3_plus_the_festival_golds_of_the_run(model, ks):
    gb = to_map(model, 10, step=1)
    golds_won(gb, ks)
    assert (gb.mem("smap_flags") >> 4) & 7 == sum(1 << k for k in ks)
    assert pour_off_lives(gb) == 3 + len(ks)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_gold_twice_counts_once_and_the_cap_is_three(model):
    gb = to_map(model, 10, step=1)
    golds_won(gb, (1, 1))
    assert (gb.mem("smap_flags") >> 4) & 7 == 2
    gb.write("smap_flags", 0xF7)
    assert pour_off_lives(gb) == 6, "3 + at most 3"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("diff, counts", [(0, 1), (1, 1), (2, 0)])
def test_only_normal_and_hard_story_runs_count_easy_does_not(model, diff, counts):
    gb = to_map(model, 10, step=1)
    golds_won(gb, (0,), diff)
    assert (gb.mem("smap_flags") >> 4) & 7 == counts
    assert pour_off_lives(gb) == 3 + counts


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_festival_gold_says_one_more_life_and_a_repeat_does_not(model):
    gb = to_map(model, 10, step=1, stop=TOWN)
    for again in (False, True):
        gb.write("smap_stop", TOWN)
        gb.run(2)
        tap(gb, "a", 20)
        gb.run(6)
        tap(gb, "a", 20)
        gb.run(8)
        tap(gb, "down", 4)
        tap(gb, "a", 2)
        play_result(gb, 9000, bonus=True)
        gb.run(10)
        assert (win_text(gb, 1).endswith("1 MORE LIFE")) == (not again), (again, win_text(gb, 1))
        back_to_map(gb)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_pour_off_outside_a_story_run_has_three_lives_whatever_the_flags_hold(model):
    gb = booted(model)
    gb.write("smap_flags", 0x70)
    mg_enter(gb, 11, 0)
    run_until(gb, lambda: state(gb) == GS_MINI, 60)
    gb.run(3)
    assert gb.mem("story_on") == 0 and gb.mem("lives") == 3
    # and a gold in Practice does not count
    gb.write("smap_flags", 0)
    mg_enter(gb, 12, 1)
    run_until(gb, lambda: state(gb) == GS_MINI, 60)
    gb.run(6)
    a = gb.addr("score")
    for i in range(4):
        gb.write(a + i, (9000 >> (8 * i)) & 255)
    gb.write("mg_phase", MG_RESULT)
    run_until(gb, lambda: gb.mem("overlay_on") == 1 and gb.mem("mg_t") >= MG_RESULT_MIN, 200)
    assert gb.mem("mg_medal") == 3 and gb.mem("smap_flags") & 0x70 == 0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_new_story_run_resets_the_festival_golds(model):
    gb = booted(model, v7_image([], story=10, step=1))
    gb.write("smap_flags", 0x77)
    gb.write("smap_stop", 7)
    title_pick(gb, ts.K_PLAY, ts.K_STORY)
    run_until(gb, lambda: state(gb) == GS_STORY and gb.mem("story_phase") == SP_SCENE, 60)
    assert gb.mem("smap_flags") & 0x7F == 0 and gb.mem("smap_stop") == 0, "a new run: no festival game played or won, Sal at the saloon"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("progress, open_", [(0, 0), (5, 0), (9, 0), (10, 1)])
def test_the_pour_off_is_greyed_until_all_ten_venues_are_cleared(model, progress, open_):
    gb = town_panel(model, progress, golds=7)
    tap(gb, "down", 4)
    tap(gb, "a", 2)
    gb.run(30)
    went = gb.mem("story_phase") == SP_SCENE and gb.mem("story_scene") == ts.SC["FINALE_A"]
    assert went == bool(open_)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_dregs_nudges_with_fewer_than_three_golds_one_page_text_only(model):
    gb = town_panel(model, 10, golds=7)
    tap(gb, "down", 4)
    tap(gb, "a", 2)
    run_until(gb, lambda: gb.mem("story_phase") == SP_SCENE, 60)
    assert gb.mem("story_scene") == ts.SC["FINALE_A"], "three golds: straight to the finale"
    for golds in (0, 1, 3):                  # (bit masks of 0, 1 and 2 golds)
        gb = town_panel(model, 10, golds=golds)
        tap(gb, "down", 4)
        tap(gb, "a", 20)
        gb.run(8)
        assert gb.mem("story_phase") == SP_MAP and win_text(gb, 1) == "DREGS", f"golds {golds:03b}"
        assert "FESTIVAL" in " ".join(win_text(gb, r) for r in (2, 3, 4))
        tap(gb, "b", 12)
        assert win_text(gb, 1) == "FESTIVAL GAMES", "B goes back to the town panel"


# ---- the flow and the save ------------------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_intro_leads_to_the_map_and_a_there_starts_chapter_1(model):
    gb = ts.start_story(model)
    ts.skip_scene(gb, stay=True)                # INTRO
    run_until(gb, lambda: gb.mem("story_phase") == SP_MAP, 60)
    assert gb.mem("smap_stop") == 0 and gb.mem("story_chapter") == 0
    tap(gb, "a", 2)
    run_until(gb, lambda: gb.mem("story_phase") == SP_SCENE, 60)
    assert gb.mem("story_scene") == ts.pre(0)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_post_scene_returns_to_the_map_with_sal_on_the_venue_just_played(model):
    gb = ts.to_chapter(model, 2)
    gb.write("story_step", ts.STORY_STEPS - 1)           # (the chapter's last step: the Opening won)
    ts.win(gb, 2, 0)
    run_until(gb, lambda: state(gb) == GS_STORY and gb.mem("story_scene") == ts.post(2), 400)
    assert gb.mem("story_progress") == 3
    ts.skip_scene(gb, stay=True)
    assert gb.mem("smap_stop") == 2 and gb.mem("story_chapter") == 2
    gb.run(130)
    tap(gb, "right", 3)
    assert gb.mem("smap_stop") == 3, "the next venue is open"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_map_block_is_saved_and_continue_returns_to_it(model):
    gb = to_map(model, 6, stop=6, flags=0x13)
    tap(gb, "a", 2)                                 # the next venue: the map is left, its block saved
    run_until(gb, lambda: gb.mem("story_phase") == SP_SCENE, 60)
    ram = save_ram(gb)
    blk = ram[SM_AT:SM_AT + 6]
    assert blk[:2] == b"SM" and blk[2] == 6 and blk[3] == 0x13 and len(blk) == 6
    c = (0x5A + sum(blk[:4])) & 255
    assert blk[4] == c and blk[5] == c ^ 255
    gb = to_map(model, ram=ram, progress=6)
    assert gb.mem("smap_stop") == 6 and gb.mem("smap_flags") & 0x7F == 0x13


def block(stop, flags):
    b = bytearray(b"SM" + bytes([stop, flags]))
    c = (0x5A + sum(b)) & 255
    return bytes(b + bytes([c, c ^ 255]))


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("bad", ["magic", "sum", "stop", "flags", "none"])
def test_a_bad_map_block_reads_as_nothing_and_continue_puts_sal_at_the_next_venue(model, bad):
    ram = bytearray(v7_image([], story=4))
    blk = bytearray(block(2, 0x12))
    if bad == "magic":
        blk[0] = ord("X")
    elif bad == "sum":
        blk[4] ^= 1
    elif bad == "stop":
        blk = bytearray(block(11, 0x12))
    elif bad == "flags":
        blk = bytearray(block(2, 0x88))
    if bad != "none":
        ram[SM_AT:SM_AT + 6] = blk
    gb = to_map(model, ram=bytes(ram), progress=4)
    assert gb.mem("smap_stop") == 4 and gb.mem("smap_flags") & 0x7F == 0, "the venue after the last cleared"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_good_map_block_is_taken_and_a_locked_stop_in_it_is_not(model):
    ram = bytearray(v7_image([], story=4))
    ram[SM_AT:SM_AT + 6] = block(2, 0x12)
    gb = to_map(model, ram=bytes(ram), progress=4)
    assert gb.mem("smap_stop") == 2 and gb.mem("smap_flags") & 0x7F == 0x12
    ram[SM_AT:SM_AT + 6] = block(8, 0x12)              # the zoo is locked with 4 cleared
    gb = to_map(model, ram=bytes(ram), progress=4)
    assert gb.mem("smap_stop") == 4


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_all_ten_cleared_continue_returns_to_the_map_until_the_credits_end(model):
    gb = to_map(model, 10, step=1)
    assert gb.mem("smap_stop") == TOWN and gb.mem("story_progress") == 10 and gb.mem("story_reached") == 1
    gb = booted(model, v7_image([], story=10, step=0))
    title_pick(gb, ts.K_PLAY, press=False)
    assert K_CONTINUE not in menu_items(gb), "a finished story has no CONTINUE"


# ---- the goldens: the map at the start of chapter 1, mid-game, the cleared-venue panel and the festival panel ---------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_golden_map_at_the_start_of_chapter_1(model):
    gb = ts.start_story(model)
    ts.skip_scene(gb, stay=True)
    run_until(gb, lambda: gb.mem("story_phase") == SP_MAP, 60)
    gb.run(60)
    check_golden(gb, "story_map_start")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_golden_map_mid_game(model):
    gb = to_map(model, 6, stop=5)
    gb.run(120)
    check_golden(gb, "story_map_mid")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_golden_cleared_venue_panel(model):
    gb = to_map(model, 6, stop=3)
    tap(gb, "a", 20)
    gb.run(10)
    check_golden(gb, "story_map_venue_panel")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_golden_festival_panel(model):
    gb = to_map(model, 5, stop=TOWN, flags=0x01)
    tap(gb, "a", 20)
    gb.run(8)
    tap(gb, "a", 20)
    gb.run(10)
    check_golden(gb, "story_map_festival_panel")
