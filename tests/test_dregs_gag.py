# G17: Dregs's late-arrival gags (src/dgag.c). In every POST scene the narrator page after Dregs's own page plays an OBJ-sprite gag over the
# venue's backdrop; the page cannot be turned until it ends. The gag's frame counter, and whether it runs (1), was left standing (2) or is
# over (0), are win_rows[0][0] and [0][4] (src/story.c, the goal banner's buffer, unused in a scene).
import pytest

from conftest import check_golden
from test_flow import GS_STORY, run_until, state
from test_scores import v7_image
from test_story import (SCENES, STORY_STEPS, post, page_ready, settle, skip_scene, start_story, tilemap_row, to_goal, win)

OAM0 = 20                  # the gag's first OAM entry (the Spigoteer 0-3, Sadie's accent 4..19)
LANE_ROWS = range(0, 13)   # the backdrop rows (the text box starts at row 13)
VENUES = ["saloon", "stadium", "lumber", "bistro", "igloo", "robot", "punks", "teahouse", "zoo", "space"]
# the gag pages of each POST scene: the narrator page after Dregs's (every venue), the punks' second narrator page (the blast), the
# space lounge's "came down" page
EXPECT = {c: 1 for c in range(10)}
EXPECT[6] = EXPECT[9] = 2
LENGTH = (100, 300)        # real frames a gag runs (2-4 s asked first; the beat before the venue acts and the slower slide of 2026-10-17 lift the cap to 5 s)
OPEN, HOLD = 48, 72        # src/dgag.c: the opening's frames, the beat after it (Dregs stands, arm out) before the venue's own gag
LENGTHS = {}


def st_addr(gb):
    return gb.addr("win_rows")


def gag_state(gb):
    return gb.mem(st_addr(gb) + 4)


def gag_t(gb):
    """The gag's next (closed-form) frame number: it idles at 33-48 through the beat and then runs at 13/16 speed."""
    return gb.mem(st_addr(gb))


def gag_raw(gb):
    """The real frames since the page turn (16 bits at win_rows[0][5])."""
    return gb.mem16(st_addr(gb) + 5)


def gag_pages(c):
    pages = SCENES[post(c)]["pages"]
    out = []
    for i, p in enumerate(pages):
        if p["speaker"] == "NARRATOR" and i:
            prev = pages[i - 1]["speaker"]
            if prev == "DREGS" or (prev == "NARRATOR" and c == 6) or (prev == "SPIGOTEER" and c == 9):
                out.append(i)
    return out


def post_scene(model, c):
    gb = start_story(model, v7_image([], story=c), cont=True) if c else start_story(model)
    if not c:
        skip_scene(gb)                                    # INTRO
    skip_scene(gb)                                        # the PRE scene
    to_goal(gb)
    gb.write("story_step", STORY_STEPS - 1)
    win(gb, c, 0)
    run_until(gb, lambda: state(gb) == GS_STORY and gb.mem("story_scene") == post(c), 400)
    settle(gb)
    return gb


def to_page(gb, k):
    """The scene's page k has just begun (the turn from page k - 1 done)."""
    if gb.mem("story_page") == k:                         # (a test that turned the page itself)
        return
    while gb.mem("story_page") < k - 1:
        page_ready(gb)
        gb.press("a", 2)
    page_ready(gb)
    assert gb.mem("story_page") == k - 1
    gb.press("a", 2)
    assert gb.mem("story_page") == k


def per_line(gb):
    """The most sprites on one scanline (8x16 sprites; every entry with a Y on the screen's lines counts, even off to the side)."""
    cnt = [0] * 144
    for s in gb.oam():
        if 0 < s["y"] < 160:
            for y in range(max(0, s["y"] - 16), min(144, s["y"])):
                cnt[y] += 1
    return max(cnt)


def gag_sprites(gb):
    return [s for s in gb.oam()[OAM0:] if s["y"]]


def rows(gb):
    return [tilemap_row(gb, r, 0, 20) for r in LANE_ROWS]


def play_gag(gb):
    """From the gag's start to its end: frames, the most sprites seen on a line, the most gag sprites at once."""
    n = most = line = 0
    while gag_state(gb) == 1 and n < 400:
        gb.run(1)
        n += 1
        most = max(most, len(gag_sprites(gb)))
        line = max(line, per_line(gb))
    return n, most, line


@pytest.mark.parametrize("c", range(10))
def test_the_script_has_the_gag_pages(c):
    assert len(gag_pages(c)) == EXPECT[c], (c, gag_pages(c))
    pages = SCENES[post(c)]["pages"]
    assert pages[gag_pages(c)[0] - 1]["speaker"] == "DREGS", "the gag follows Dregs's own page"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("c", range(10))
def test_the_gag_plays_ends_cleanly_and_holds_the_page(model, c):
    """Per venue and gag page: sprites move on the backdrop, never more than 10 on a line, A does not turn the page meanwhile, the
    backdrop's tiles are not touched, and when it ends no gag sprite is left (a held page, the punks' chord, keeps Dregs) and A turns."""
    gb = post_scene(model, c)
    with gb:
        for n, k in enumerate(gag_pages(c)):
            to_page(gb, k)
            assert gag_state(gb) == 1, f"{VENUES[c]}: the gag starts with the page"
            run_until(gb, lambda: gb.mem("story_swap") == 0, 30)
            tiles = rows(gb)
            run_until(gb, lambda: gb.mem("story_typed") == 54, 80)
            gb.press("a", 2)
            gb.run(1)
            assert gb.mem("story_page") == k and gag_state(gb) == 1, "A does not turn the page while the gag plays"
            frames, most, line = play_gag(gb)
            total = gag_raw(gb) + 1               # the real frame count (the gag was already running while the text typed)
            LENGTHS[(c, n)] = total
            assert gag_state(gb) in (0, 2), "the gag ends"
            assert most >= 2, f"{VENUES[c]}: something moved"
            assert line <= 10, f"{VENUES[c]}: {line} sprites on a line"
            assert rows(gb) == tiles, "no tile of the scene was touched"
            if gag_state(gb) == 0:
                assert gag_sprites(gb) == [], f"{VENUES[c]}: nothing of the gag is left"
                assert len(gb.visible_sprites()) == 4, "the Spigoteer alone is on the screen"
            else:
                assert gag_sprites(gb), "a held gag leaves Dregs standing"
            assert LENGTH[0] <= total or (c == 6 and n == 1), (VENUES[c], total)
            assert total <= LENGTH[1]
            gb.press("a", 2)
            assert gb.mem("story_page") == k + 1, "A turns the page once it is over"
            if k + 1 in gag_pages(c):
                continue                              # (the punks' blast page: its gag has started with the turn)
            page_ready(gb)
            assert gag_sprites(gb) == [] and gag_state(gb) == 0, "the next page starts with none of it"
        assert len(gb.visible_sprites()) == 4


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("c", [0, 6, 9])
def test_no_gag_on_the_other_pages_and_start_skips_one_cleanly(model, c):
    gb = post_scene(model, c)
    with gb:
        gag = set(gag_pages(c))
        for k in range(len(SCENES[post(c)]["pages"])):
            if k:
                gb.press("a", 2)
            if k in gag:
                run_until(gb, lambda: gag_state(gb) != 1, 400)
                break
            page_ready(gb)
            assert gag_state(gb) == 0 and gag_sprites(gb) == [], f"page {k}: no gag"
        # START in the middle of the next gag (or the first): the scene is skipped; the next scene starts clean
        gb2 = post_scene(model, c)
        with gb2:
            to_page(gb2, gag_pages(c)[0])
            gb2.run(40)
            assert gag_state(gb2) == 1
            s = gb2.mem("story_scene")
            gb2.press("start", 2)
            run_until(gb2, lambda: gb2.mem("story_scene") != s or state(gb2) != GS_STORY, 30)
            settle(gb2)
            assert gag_state(gb2) == 0 and gag_sprites(gb2) == []


# the key moment of each gag, a frame after the page begins: new goldens (dmg + cgb)
MOMENTS = {0: (0, 84), 1: (0, 100), 2: (0, 84), 3: (0, 90), 4: (0, 80), 5: (0, 80), 6: (0, 62), 7: (0, 68), 8: (0, 78), 9: (0, 78)}
MOMENTS_B = {6: (1, 44), 9: (1, 80)}


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("c", range(10))
def test_gag_goldens(model, c):
    gb = post_scene(model, c)
    with gb:
        for which, (n, t) in [(0, MOMENTS[c])] + ([(1, MOMENTS_B[c])] if c in MOMENTS_B else []):
            to_page(gb, gag_pages(c)[which])
            run_until(gb, lambda: gag_t(gb) == t and gag_state(gb) == 1, 300)
            check_golden(gb, f"dregs_gag_{VENUES[c]}" + ("_b" if which else ""))
            run_until(gb, lambda: gag_state(gb) != 1, 300)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("c", range(10))
def test_dregs_stands_a_beat_before_the_venue_acts_and_the_shove_is_slower(model, c):
    """After the dash and the reach Dregs stands HOLD frames (the gag idles on frames 32-47, shown as 33-48), then the venue's gag starts; played at
    13/16 speed its frame number advances 13 for every 16 real frames."""
    gb = post_scene(model, c)
    with gb:
        to_page(gb, gag_pages(c)[0])
        assert gag_raw(gb) < OPEN
        run_until(gb, lambda: gag_raw(gb) == OPEN + 4, 80)
        beat = []
        while gag_raw(gb) < OPEN + HOLD - 1:
            beat.append(gag_t(gb))
            gb.run(1)
        assert 33 <= min(beat) and max(beat) <= 48, f"{VENUES[c]}: Dregs idles through the beat: {sorted(set(beat))}"
        gb.run(6)
        assert gag_raw(gb) >= OPEN + HOLD + 4 and gag_t(gb) > OPEN, f"{VENUES[c]}: the venue acts once the beat is over"
        t0, r0 = gag_t(gb), gag_raw(gb)
        gb.run(32)
        assert 22 <= gag_t(gb) - t0 <= 28, f"{VENUES[c]}: slowed to 13/16 (26 gag frames in 32): {gag_t(gb) - t0}"
        assert gag_raw(gb) - r0 == 32


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_stadium_soda_bath_plays_on_screen_and_gives_the_spigoteer_back(model):
    """POST_STADIUM page 2 ("SPLOOSH! ... SODA BATH", after Coach's page): Coach's cooler and a soda stream/sheet/splash are drawn over the
    Spigoteer (his four entries parked in OAM 36-39 meanwhile, so the soda is in front), A cannot turn the page, at most 10 sprites a line,
    and afterwards the Spigoteer is back in OAM 0-3 with nothing of the bath left."""
    gb = post_scene(model, 1)
    with gb:
        page_ready(gb)                                     # page 0: Coach
        gb.press("a", 2)
        assert gb.mem("story_page") == 1
        run_until(gb, lambda: gag_state(gb) == 1, 10)
        most = line = 0
        n = 0
        parked = None
        while gag_state(gb) == 1 and n < 400:
            gb.run(1)
            n += 1
            most = max(most, len(gag_sprites(gb)))
            line = max(line, per_line(gb))
            if n == 70:
                assert [s["y"] > 0 for s in gb.oam()[36:40]] == [True] * 4, "the Spigoteer is parked behind the soda"
                parked = gb.oam()[36:40]
                check_golden(gb, "dregs_gag_soda")
                gb.press("a", 2)
                assert gb.mem("story_page") == 1, "A does not turn the page while the bath plays"
        assert 120 <= n <= 200, n
        assert most >= 6 and line <= 10
        assert gag_sprites(gb) == [], "nothing of the bath is left"
        assert gb.oam()[0:4] == [dict(s) for s in parked], "the Spigoteer is back where he was"
        assert len(gb.visible_sprites()) == 4
        gb.press("a", 2)
        assert gb.mem("story_page") == 2
