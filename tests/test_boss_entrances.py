# E8 (2026-10-15): the entrances of Big Tex (the saloon: "the swagger"), the Mascot (the stadium: "fired from the T-shirt cannon") and the
# Prototype (the robot factory: "lowered by the crane, then powers up"), built like Duke's (tests/test_boss_duke.py): on the fight's
# first start the boss is not on his bar (BS_JUMP, BP_HIDE), the intro's clock is held, the player's input is held (the bartender at
# bar 0's tap, nothing poured), he is drawn as sprites in the mugs' OAM entries (5-24) and each frame has at most 10 sprites a line;
# at the last frame his BG body takes over at x 16 (WALK) and the intro's 90 frames start; no sprite is left; no entrance after a
# lost life; the same on the Story, ARCADE, BOSS RUSH and Practice paths.
import pytest
from boss_common import (BP_HAPPY, BP_WALK, BS_ENTER, BS_JUMP, BS_WALK, start_entrance, ENTRANCES, Own, SPOUT_X, art, check_start, entrance_running, fight, frames,
                         mugs, play, row, still_regulars, until)
from conftest import check_golden
from test_flow import GS_GOAL, LEVEL_CLEAR, LIFE_LOST, PLAYING, run_until, state
from test_story import boss_from_opening, to_boss_banner, to_goal, to_shift, win

pytestmark = pytest.mark.timeout(300)

INTRO = 90
BP_HIDE = 14
SFX_LAUNCH, SFX_SERVE, SFX_COIN, SFX_SHAKE, SFX_EXTRA, SFX_WHOOSH = 2, 5, 6, 8, 9, 13
# venue: (name, entrance frames, {sfx: (at least, at most) times from the entrance})
SPEC = {
    0: ("big_tex", 138, {SFX_COIN: (4, 6), SFX_SERVE: (1, 1), SFX_SHAKE: (1, 1)}),         # the spurs, the cheer, the landing's thud
    1: ("mascot", 124, {SFX_WHOOSH: (1, 1), SFX_SHAKE: (1, 1), SFX_SERVE: (1, 1)}),        # the cannon, the thud, the crowd
    5: ("prototype", 124, {SFX_SHAKE: (1, 1), SFX_COIN: (1, 1), SFX_EXTRA: (1, 1)}),       # the clunk, the lamp's yellow, the lit green
}
VENUES = sorted(SPEC)


def clock(gb, c):
    name, field, run0 = ENTRANCES[c]
    return Own(name).get(gb, field)


def ent_t(gb, c):
    """The entrance frame the game has drawn (0-based), None when it is not running (or not begun)."""
    v = clock(gb, c) - (1000 if c == 5 else 0)
    return v - 2 if v >= 2 else None


def sfxs(gb):
    return gb.read("sfx_count", 14)


def entrance_oam(gb):
    """The entries the entrances may use (OAM 5-24): (y, x, tile, flags) of the ones on."""
    return [(o["y"], o["x"], o["tile"], o["flags"]) for o in gb.oam()[5:25] if o["y"]]


def fight_raw(model, c):
    """The fight's first frame of play: the entrance has just begun."""
    return start_entrance(to_goal(fight(model, c, banner=True), boss_start=False))


POP_TILES = (100, 102, 104, 106)   # OBJ_TOPPER + 4..: HAT_POP0..3, the whole hat (crown and brim) in four 8x16 sprites


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_big_tex_whole_hat_pops_off_with_the_brim_and_comes_back(model):
    """The tip lifts the crown AND the brim (four sprites, x 24-48) while his BG-art pair tiles show a bare head (the BARE pose: the
    body columns 0-3 differ from the hatted ones); before the tip and after it the hat is on again (the crown sprite, the hatted body)."""
    c = 0
    with fight_raw(model, c) as gb:
        to_frame(gb, c, 90)
        on = sorted(entrance_oam(gb), key=lambda o: o[1])
        assert not [o for o in on if o[2] in POP_TILES]
        assert len(on) == 6 and [o for o in on if o[2] == 96], "hat on: five body columns and the crown"
        by = max(o[0] for o in on)
        seen = 0
        for t in range(98, 128):
            to_frame(gb, c, t)
            oam = entrance_oam(gb)
            pop = sorted(o for o in oam if o[2] in POP_TILES)
            if not pop:
                continue
            seen += 1
            body = sorted((o for o in oam if o[2] not in POP_TILES), key=lambda o: o[1])
            assert [o[1] for o in pop] == [24, 32, 40, 48] and len({o[0] for o in pop}) == 1 and pop[0][0] < by - 8, (t, oam)
            assert len(body) == 5 and all(o[0] == body[0][0] for o in body) and not [o for o in body if o[2] in (96, 98)], (t, oam)
            assert [o[2] for o in body[:4]] != [o[2] for o in on[:4] if o[2] != 96] and len(oam) == 9, "a bare head under the hat"
        assert seen >= 20, "the whole hat is up for most of the tip"
        to_frame(gb, c, 130)
        oam = entrance_oam(gb)
        assert not [o for o in oam if o[2] in POP_TILES] and [o for o in oam if o[2] in (96, 98)], "the hat is back on"
        assert sorted(o[2] for o in oam if o[2] not in (96, 98)) == sorted(o[2] for o in on if o[2] != 96), "the hatted body again"
        until(gb, lambda: not entrance_running(gb), 60)


def to_frame(gb, c, t):
    """Frame by frame (each checked at <= 10 sprites a line) to the moment the entrance has just drawn its frame t."""
    while ent_t(gb, c) != t:
        assert ent_t(gb, c) is None or ent_t(gb, c) < t, (ent_t(gb, c), t)
        frames(gb, 1)


def quiet(gb):
    still_regulars(gb)
    play(gb)


def poke_a_life_lost(gb, c):
    gb.write("boss_x", SPOUT_X - row(c)["width"])
    until(gb, lambda: state(gb) == LIFE_LOST, 4)
    until(gb, lambda: state(gb) == PLAYING, 200)


def assert_landed(gb, c, model):
    """The entrance is over: his BG body at x 16 (WALK), his tiles, palettes and topper as the fight's start has them, no sprite
    left, the intro's 90 frames running from the last frame."""
    R, A = row(c), art(SPEC[c][0])
    frames(gb, 2)
    assert gb.mem("boss_state") == BS_WALK and gb.mem("boss_xpose") == 0 and gb.mem("boss_x") == R["x"] and gb.mem("boss_bar") == R["bar"]
    assert INTRO - 5 <= gb.mem("intro_timer") <= INTRO - 1, "the intro's 90 frames start at his landing"
    assert entrance_oam(gb) == [], "no entrance sprite left"
    check_start(gb, c, A, model)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("c", VENUES)
def test_the_entrance_runs_holds_the_input_and_ends_with_him_on_his_bar(model, c):
    """First start: BS_JUMP with no body (BP_HIDE), no topper from the engine, nothing caught, the intro held while it runs;
    A and RIGHT held all through: the bartender stays at bar 0's tap, no glass is filled or launched; its length is 2-4 s; its
    sound cues are the existing ones; then he is on his bar and every frame had at most 10 sprites a line (frames())."""
    name, length, cues = SPEC[c]
    R = row(c)
    with fight_raw(model, c) as gb:
        assert entrance_running(gb) and gb.mem("boss_state") == BS_ENTER and gb.mem("boss_xpose") == BP_HIDE
        assert gb.oam()[27 + 1]["y"] == 0, "no topper from the engine before he lands"
        sf0, tap, launched = list(sfxs(gb)), gb.mem("bartender_x"), sfxs(gb)[SFX_LAUNCH]
        gb.hold("a")
        gb.hold("right")
        n, seen = 0, False
        while entrance_running(gb):
            frames(gb, 1)
            n += 1
            assert n < 260
            if entrance_running(gb):
                t = ent_t(gb, c)
                assert gb.mem("boss_state") in (BS_ENTER, BS_WALK), "away until he lands (the last frame: mid-logic)"
                assert gb.mem("intro_timer") >= INTRO - 1, "the intro is held"
                assert gb.mem("boss_state") != BS_JUMP or gb.mem("boss_lim") == 0, "nothing for him to catch while he is away"
            assert gb.mem("bar") == 0 and gb.mem("bartender_x") == tap and gb.mem("fill_timer") <= 1 and gb.mem("fill_stage") == 0, "input held"   # (a press's own frame shows fill_timer 1: the next frame's reset is before the pour)
            assert mugs(gb) == [] and sfxs(gb)[SFX_LAUNCH] == launched
            assert gb.mem("boss_hp") == R["meter"] and gb.mem("boss_hits") == 0, "he catches nothing"
            seen = seen or bool(entrance_oam(gb))
        gb.release("a")
        gb.release("right")
        assert seen, "the entrance drew sprites"
        assert 120 <= n <= 240 and abs(n - length) <= 4, n          # (2-4 s: the frames of the first start)
        for k, (lo, hi) in cues.items():
            assert lo <= sfxs(gb)[k] - sf0[k] <= hi, (k, sfxs(gb)[k] - sf0[k])
        assert_landed(gb, c, model)
        assert gb.mem("lives") == 3 and sfxs(gb)[SFX_LAUNCH] == launched


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("c", VENUES)
def test_no_entrance_after_a_lost_life_and_the_fight_is_the_usual_one(model, c):
    """A life lost after it: he is there at once, walking from x 16 (the entrance does not play again), the intro runs from its start."""
    with fight_raw(model, c) as gb:
        until(gb, lambda: not entrance_running(gb), 260)
        quiet(gb)
        poke_a_life_lost(gb, c)
        assert not entrance_running(gb) and gb.mem("boss_state") == BS_WALK and gb.mem("boss_x") == row(c)["x"]
        assert gb.mem("boss_xpose") == 0 and gb.mem("lives") == 2
        until(gb, lambda: gb.mem("intro_timer") == INTRO - 1, 3)
        frames(gb, 30)
        assert not entrance_running(gb) and entrance_oam(gb) == [] and gb.mem("boss_state") == BS_WALK


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_big_tex_swaggers_in_from_the_left_and_tips_his_hat(model):
    """Sprites only: his body walks in from the left edge (frame 12: off the screen; he is at x -40 + 0.75 px a frame), stops at x 16
    at frame 87, tips the hat from 98 (the whole hat 10 px up, the body bows: the STOMP pose); the hat is back and the BG body
    takes over at 138. Golden boss_big_tex_entrance: the hat tipped (frame 110)."""
    c = 0
    with fight_raw(model, c) as gb:
        to_frame(gb, c, 5)
        assert entrance_oam(gb) == []
        to_frame(gb, c, 40)
        xs = sorted(o[1] for o in entrance_oam(gb))
        assert len(xs) >= 4 and xs[0] < 8 + 16 and max(xs) < 8 + 16 + 40 + 8, xs                 # (still arriving at the left edge)
        to_frame(gb, c, 90)
        oam = sorted(entrance_oam(gb), key=lambda o: o[1])
        body = [o for o in oam if o[0] == oam[-1][0] or o[0] == max(p[0] for p in oam)]
        assert [o[1] for o in body] == [24, 32, 40, 48, 56], oam    # at x 16: his five columns
        to_frame(gb, c, 98 + 7)
        hats = [o for o in entrance_oam(gb) if o[2] in POP_TILES]
        assert len(hats) == 4 and {o[0] for o in hats} == {body[0][0] - 8 - 10}, "the whole hat is lifted 10 px"
        to_frame(gb, c, 110)
        check_golden(gb, "boss_big_tex_entrance")
        until(gb, lambda: not entrance_running(gb), 60)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_mascot_falls_on_the_marker_and_lands_crouching_then_cheers(model):
    """The marker shows on his spot from frame 6, the ball (2 sprites) falls from the top-left corner onto it, bounces once, and
    he lands at frame 74 in the CROUCH pose, HAPPY from 84; the marker is gone at the landing. Golden boss_mascot_entrance:
    the ball falling (frame 40)."""
    c = 1
    with fight_raw(model, c) as gb:
        to_frame(gb, c, 4)
        assert gb.mem("boss_x") == 16 and entrance_oam(gb) == []
        to_frame(gb, c, 40)
        assert len(entrance_oam(gb)) == 2, "the ball: two sprites"
        check_golden(gb, "boss_mascot_entrance")
        ys = []
        for t in range(41, 74):
            to_frame(gb, c, t)
            ys.append(entrance_oam(gb)[0][0])
        assert max(ys) <= 80 and ys[-1] >= 64 + 16 - 16, ys              # (it never goes below his wall's top: OAM y 80)
        to_frame(gb, c, 74 + 3)
        assert gb.mem("boss_state") == BS_ENTER and gb.mem("boss_pose") & 15 == 5 and entrance_oam(gb) == [], "he has landed: CROUCH"
        to_frame(gb, c, 84 + 3)
        assert gb.mem("boss_pose") & 15 == BP_HAPPY
        until(gb, lambda: not entrance_running(gb), 60)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_prototype_is_lowered_by_the_crane_and_powers_up(model):
    """The crane lowers him (body 4 sprites, lamp, yoke, chain) to his bar by frame 56, lets go and rises away (gone by 84), the lamp
    is the red X, then the yellow ring (frame 84) and solid (96); the sparks fly between 84 and 110; at 124 the BG body takes
    over. At most 14 entries. Golden boss_prototype_entrance: the sparks (frame 100)."""
    c = 5
    with fight_raw(model, c) as gb:
        to_frame(gb, c, 30)
        o30 = entrance_oam(gb)
        to_frame(gb, c, 54)
        o54 = entrance_oam(gb)
        assert max(o[0] for o in o54) > max(o[0] for o in o30), "he comes down"
        assert len(o54) <= 14
        to_frame(gb, c, 70)
        assert any(o[1] == 24 + 4 and o[3] == 0 for o in entrance_oam(gb)) or len(entrance_oam(gb)) >= 6
        to_frame(gb, c, 90)
        assert len(entrance_oam(gb)) <= 14
        to_frame(gb, c, 100)
        check_golden(gb, "boss_prototype_entrance")
        until(gb, lambda: not entrance_running(gb), 60)
        assert Own("prototype").get(gb, "t") < 1000


def fight_hard(model, c):
    """The fight's play with Practice's HARD toggle set (boss_hard) before it starts."""
    gb = to_shift(model, c, 2)
    gb.write("boss_hard", 1)
    to_boss_banner(gb, c)
    return start_entrance(to_goal(gb, boss_start=False))


@pytest.mark.parametrize("c", VENUES)
def test_practice_hard_starts_with_the_entrance_too(c):
    """Practice's HARD toggle: the entrance plays, then he is there with one hand fewer."""
    with fight_hard("cgb", c) as gb:
        assert gb.mem("boss_hard") == 1 and entrance_running(gb) and gb.mem("boss_state") == BS_ENTER
        until(gb, lambda: not entrance_running(gb), 260)
        frames(gb, 2)
        assert gb.mem("boss_state") == BS_WALK and gb.mem("boss_x") == row(c)["x"] and gb.mem("boss_hands") == row(c)["hands"] - 1


@pytest.mark.parametrize("model", ["cgb"])
@pytest.mark.parametrize("c", VENUES)
def test_arcade_starts_the_boss_with_the_entrance_too(model, c):
    """ARCADE (the story's steps without its scenes): the same entrance, then the usual fight."""
    from test_arcade import start_arcade
    with start_arcade(model) as gb:
        to_goal(gb)
        boss_from_opening(gb, c)
        assert gb.mem("boss_on") == 1 and gb.mem("boss_id") == c and gb.mem("story_arc") == 1
        start_entrance(to_goal(gb, boss_start=False))
        assert entrance_running(gb) and gb.mem("boss_state") == BS_ENTER
        until(gb, lambda: not entrance_running(gb), 260)
        frames(gb, 2)
        assert gb.mem("boss_state") == BS_WALK and gb.mem("boss_x") == row(c)["x"] and entrance_oam(gb) == []
        assert gb.mem("boss_hp") == row(c)["meter"] and gb.mem("lives") == 3


@pytest.mark.parametrize("model", ["cgb"])
@pytest.mark.parametrize("c", VENUES)
def test_boss_rush_starts_with_the_entrance_too(model, c):
    """BOSS RUSH, CHOOSE on the boss: the same entrance, he is on his bar at x 16 after it and the fight is the usual one."""
    from test_rush import BUILT, booted, into_fight, tap, to_list, v7_image
    ram0 = v7_image([("ABC", 500)], story=2, step=1, story_tbl=[("STO", 900)])
    with booted(model, ram0) as gb:
        to_list(gb)
        for _ in range(BUILT.index(c)):
            tap(gb, "right")
        tap(gb, "a")
        into_fight(gb, entered=False)
        until(gb, lambda: gb.mem("boss_state") != 6, 5)     # (BOSS RUSH: no warm-up)
        frames(gb, 3)
        assert gb.mem("boss_id") == c and entrance_running(gb) and gb.mem("boss_state") == BS_ENTER
        until(gb, lambda: not entrance_running(gb), 260)
        frames(gb, 2)
        assert gb.mem("boss_state") == BS_WALK and gb.mem("boss_x") == row(c)["x"] and entrance_oam(gb) == []
        assert gb.mem("boss_hp") == row(c)["meter"] and gb.mem("lives") == 3
