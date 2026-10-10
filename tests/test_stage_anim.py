# Stage animation (src/venue.c, render.c queue_stage): each venue with assets/approved/venues/<t>_anim.txt rewrites the
# pixels of a few stage tile ids on a looped script, through the VBlank copy queue. build/venues.json ("anim") has the
# animated ids, the frames and the script as tools/gen_art.py compiled them. conftest's fixtures freeze the animation
# (sa_hold = 1); these tests turn it on.
import pytest
from conftest import GAME, LAYOUT, THEMES, VENUES, check_golden, venue
from test_art import goto_group
from test_flow import BONUS, PAUSED, PLAYING, TITLE, run_until, state, tilemap_row
from test_bonus import enter_bonus, pick
from test_venues import attr_row, bg_vram

pytestmark = pytest.mark.timeout(300)

ANIMATED = [t for t in THEMES if venue(t)["anim"]]
STAGE_SLOT = VENUES["stage_slot"]
SA_MAX_WAIT = GAME["SA_MAX_WAIT"]
LAG = SA_MAX_WAIT + 3          # frames an update may land after its script time (a busy queue; a 4-tile frame's 2nd half)


def anim(t):
    return venue(t)["anim"]


def frame_tiles(t, f):
    """Frame f of theme t as k tiles of 16 bytes."""
    a = anim(t)
    d = bytes(a["frames"][f])
    return [d[i * 16:i * 16 + 16] for i in range(a["k"])]


def period(t):
    return sum(h for _, h in anim(t)["script"])


def timeline(t, n):
    """The frame index the script shows on each of n frames, the first step at frame 0."""
    out = []
    while len(out) < n:
        for f, h in anim(t)["script"]:
            out += [f] * h
    return out[:n]


def stage_vram(gb):
    d = bg_vram(gb, 0, STAGE_SLOT)
    return [d[i * 16:i * 16 + 16] for i in range(STAGE_SLOT)]


def keep_playing(gb):
    gb.write("lives", 3)
    gb.write("quota", 250)


def at_venue(gb, t):
    goto_group(gb, THEMES.index(t))
    gb.write("tip_chance", 0)
    keep_playing(gb)
    assert gb.mem("venue_id") == THEMES.index(t)


def record(gb, n):
    """Run n frames with the animation on; the stage tiles (ids 0..19) after each."""
    gb.write("sa_hold", 0)
    seen = []
    for i in range(n):
        gb.run(1)
        if i % 32 == 0:
            keep_playing(gb)
        seen.append(stage_vram(gb))
    return seen


# ---- what gen_art compiled ----------------------------------------------------------------------------------------
def test_animated_ids_are_the_last_stage_ids_and_frame_0_is_the_stage():
    assert "saloon" not in ANIMATED, "the saloon has no stage animation (owner: the neon S was rejected)"
    assert set(ANIMATED) == {"sports", "lodge", "bistro", "igloo", "factory", "teahouse", "space", "zoo"}
    for t in ANIMATED:
        v, a = venue(t), anim(t)
        first, k = a["first"], a["k"]
        assert first + k == v["stage_n"] <= STAGE_SLOT, t
        assert bytes(a["frames"][0]) == bytes(v["stage_tiles"][first * 16:(first + k) * 16]), f"{t}: frame 0 is the stage"
        slots = {(c, r) for c, r in a["slots"]}
        for i, tid in enumerate(v["stage_map"]):
            assert (tid >= first) == ((i % 20, i // 20) in slots), f"{t}: position {(i % 20, i // 20)}"
        assert all(h >= 6 for _, h in a["script"]), t
        for (fk, lo, hi, h), (f, h2) in zip(a["steps"], a["script"]):
            assert fk == f * k and 0 <= lo <= hi <= k and hi - lo <= 4 and h == h2, t
        assert len(a["frames"]) * k * 16 <= 400 and len(a["names"]) == len(a["frames"]), t


def test_the_stadium_has_one_scoreboard_and_a_cheering_section():
    m = [venue("sports")["stage_map"][r * 20:r * 20 + 20] for r in range(4)]
    board = {m[r][c] for r in (1, 2) for c in range(5, 9)}
    other = {m[r][c] for r in (1, 2) for c in range(11, 15)}
    assert not board & other, "columns 11-14 no longer repeat the scoreboard"
    assert m[1][11] == m[1][13] != m[1][12] == m[1][14], "four fans, A/B/A/B"
    a = anim("sports")
    assert {(c, r) for c, r in a["slots"]} == {(5, 2), (6, 2), (7, 2), (8, 2), (11, 1), (12, 1), (13, 1), (14, 1)}
    names = a["names"]
    assert "cheer" in names and "all" in names
    # alternating cycles: no step moves the bulbs and the fans together (they share the update slot)
    for fk, lo, hi, h in a["steps"]:
        assert hi <= 3 or lo >= 3, (lo, hi)


# ---- in play ------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("t", ANIMATED)
def test_the_stage_animates_only_its_own_tiles(gb, t):
    at_venue(gb, t)
    v, a = venue(t), anim(t)
    first, k = a["first"], a["k"]
    base = stage_vram(gb)
    assert b"".join(base[:v["stage_n"]]) == bytes(v["stage_tiles"]), "level start: the stage's own tiles"
    n = min(2 * period(t), 1100)
    seen = record(gb, n)
    exp = timeline(t, n)
    frames = [frame_tiles(t, f) for f in range(len(a["frames"]))]
    shown = set()
    for i, vr in enumerate(seen):
        assert vr[:first] == base[:first], f"frame {i}: a static stage tile changed"
        assert vr[first + k:] == base[first + k:], f"frame {i}: an id past the stage changed"
        for j in range(k):
            ok = {frames[exp[i - d]][j] for d in range(LAG + 1) if i - d >= 0} | ({frames[0][j]} if i <= LAG else set())
            assert vr[first + j] in ok, f"frame {i}: tile {first + j} is not where the script is (+- {LAG} frames)"
        for f in range(len(frames)):
            if vr[first:first + k] == frames[f]:
                shown.add(f)
    assert shown == set(range(len(frames))), f"every frame was on screen: {sorted(shown)}"
    top = LAYOUT["STAGE_FIRST_ROW"]
    for r in range(4):
        assert tilemap_row(gb, top + r, 0, 20) == v["stage_map"][r * 20:r * 20 + 20], "the tilemap never changes"
        if gb.model_name == "cgb":
            assert attr_row(gb, top + r) == v["stage_attr"][r * 20:r * 20 + 20], "the attributes never change"
    assert gb.mem16("vq_late") == 0 and gb.mem("vq_end_ly_max") <= 153


def test_sa_hold_freezes_the_animation(gb):
    at_venue(gb, "lodge")
    record(gb, 40)
    gb.write("sa_hold", 1)
    gb.run(2)
    snap = stage_vram(gb)
    for _ in range(4):
        gb.run(50)
        keep_playing(gb)
        assert stage_vram(gb) == snap
    seen = record(gb, 60)
    assert any(s != snap for s in seen), "it runs again when released"


def test_the_saloon_does_not_animate(gb):
    assert gb.mem("venue_id") == 0
    gb.write("sa_hold", 0)
    snap = stage_vram(gb)
    for _ in range(14):
        gb.run(50)
        keep_playing(gb)
        assert stage_vram(gb) == snap
    assert gb.mem("sa_on") == 0


def test_pause_freezes_the_stage(gb):
    at_venue(gb, "bistro")
    record(gb, 30)
    gb.press("start", 2)
    assert state(gb) == PAUSED
    gb.run(2)
    snap = stage_vram(gb)
    for _ in range(6):
        gb.run(50)
        assert stage_vram(gb) == snap
    gb.press("start", 2)
    assert state(gb) == PLAYING
    seen = record(gb, 40)
    assert any(s != snap for s in seen)


def test_title_and_bonus_round_leave_stage_ids_alone(gb):
    # the title (boot fixture state is past; open it again from a fresh game over is long, so: the bonus round, which
    # follows level 2 (sports, animated), then the next level starts on its frame 0)
    at_venue(gb, "sports")
    record(gb, 100)
    gb.write("sa_hold", 0)
    enter_bonus(gb)
    gb.run(3)
    assert state(gb) == BONUS and gb.mem("sa_on") == 0 and gb.mem("sa_left") == 0
    snap = stage_vram(gb)
    for _ in range(6):
        gb.run(50)
        assert state(gb) != BONUS or stage_vram(gb) == snap
    pick(gb, 1)
    run_until(gb, lambda: state(gb) == PLAYING, 600)
    assert gb.mem("venue_id") == THEMES.index("lodge")
    lodge = venue("lodge")
    assert b"".join(stage_vram(gb)[:lodge["stage_n"]]) == bytes(lodge["stage_tiles"]), "a level starts on frame 0"
    assert gb.mem("sa_on") == 1


def test_the_title_screen_text_is_never_touched(boot):
    assert state(boot) == TITLE and boot.mem("sa_on") == 0
    boot.write("sa_hold", 0)
    snap = stage_vram(boot)
    for _ in range(12):
        boot.run(50)
        assert stage_vram(boot) == snap


@pytest.mark.parametrize("t", ANIMATED)
def test_stage_anim_golden(gb, t):
    """Each animated stage a few frames into its first step that is not the stage's own picture (sports: the crowd's
    cheer, zoo: the squawk, space: the shooting star)."""
    at_venue(gb, t)
    a = anim(t)
    want = {"sports": "cheer", "zoo": "squawk", "space": "s2"}.get(t)
    at = 0
    for f, h in a["script"]:
        if (a["names"][f] == want) if want else (f != 0 and h >= 6):
            break
        at += h
    record(gb, at + 5)
    check_golden(gb, f"stage_anim_{t}")
