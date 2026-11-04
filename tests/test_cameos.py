# Story cameos (src/cameo.c, owner-approved 2026-11-04): the Sasquatch on the lumber pages, Leo and his crown on the zoo pages, and the UFO beam-up
# on PRE_SPACE. Sprites only (OAM 20-39); the cue's page and frame counter are win_rows[4][0..1], the entries drawn last frame win_rows[4][2].
import pytest

from test_flow import GS_STORY, run_until, state
from test_scores import v7_image
from test_story import SC, SCENES, page_ready, settle, skip_scene, start_story, turn_page

OAM0 = 20
CU = {"NONE": 0, "PRE_WAVE": 1, "HANDOVER": 2, "SNEAK": 3, "WAVE": 4, "LEO_CROWN": 5, "LEO_PURR": 6, "LEO_PLACED": 7, "CROWNED": 8, "UP": 9, "DOWN": 10}
# (scene, 0-based page, cue, frame to look at, cameo OAM entries then)
CUES = [
    ("PRE_LUMBER", 2, "PRE_WAVE", 40, 5),
    ("PRE_LUMBER", 3, "PRE_WAVE", 40, 5),
    ("POST_LUMBER", 1, "HANDOVER", 60, 7),
    ("POST_LUMBER", 1, "HANDOVER", 150, 4),
    ("POST_LUMBER", 2, "SNEAK", 40, 4),
    ("POST_LUMBER", 3, "WAVE", 40, 7),
    ("PRE_ZOO", 3, "LEO_CROWN", 40, 5),
    ("POST_ZOO", 0, "LEO_PURR", 40, 5),
    ("POST_ZOO", 1, "LEO_PLACED", 40, 5),
    ("POST_ZOO", 2, "CROWNED", 40, 1),
    ("PRE_SPACE", 0, "UP", 36, 9),
    ("PRE_SPACE", 0, "UP", 60, 12),
    ("PRE_SPACE", 1, "DOWN", 60, 12),
]
SCENE_NAMES = ["PRE_LUMBER", "POST_LUMBER", "PRE_ZOO", "POST_ZOO", "PRE_SPACE"]


def st(gb, i):
    return gb.mem(gb.addr("win_rows") + 80 + i)


def per_line(gb):
    cnt = [0] * 144
    for s in gb.oam():
        if 0 < s["y"] < 160:
            for y in range(max(0, s["y"] - 16), min(144, s["y"])):
                cnt[y] += 1
    return max(cnt)


def cameo_sprites(gb):
    return [s for s in gb.oam()[OAM0:] if s["y"]]


def scene_of(model, sid):
    """The scene `sid` on its page 0 (a POST scene is reached by winning the chapter's boss: the debug route of test_dregs_gag)."""
    from test_dregs_gag import post_scene
    c = {"LUMBER": 2, "ZOO": 8, "SPACE": 9}[sid.split("_")[1]]
    if sid.startswith("POST"):
        return post_scene(model, c)
    return start_story(model, v7_image([], story=c), cont=True)


def to_page(gb, k):
    while gb.mem("story_page") < k:
        page_ready(gb)
        turn_page(gb, gb.mem("story_page") + 1)


def at_frame(gb, k, t):
    run_until(gb, lambda: gb.mem("story_page") == k and st(gb, 1) >= t, 400)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("sid", SCENE_NAMES)
def test_each_cameo_appears_on_its_pages_and_nowhere_else(model, sid):
    """On each cue page the cue is set and its sprites are drawn (count pinned) within 10 per line; on every other page of the scene no
    cameo sprite is left (state 0, no entry in OAM 20-39 unless Dregs's gag runs); the Spigoteer's four entries are back on a non-UFO page."""
    gb = scene_of(model, sid)
    with gb:
        pages = SCENES[SC[sid]]["pages"]
        sal = [e["y"] for e in gb.oam()[:4]]
        cues = [c for c in CUES if c[0] == sid]
        for k in range(len(pages)):
            if k:
                page_ready(gb)
                turn_page(gb, k)
            mine = [c for c in cues if c[1] == k]
            if not mine:
                gb.run(8)
                assert st(gb, 0) == 0 and st(gb, 2) == 0, (sid, k)
                if gb.mem(gb.addr("win_rows") + 4) == 0:        # (Dregs's gag also uses OAM 20-39)
                    assert not cameo_sprites(gb), (sid, k)
                assert [e["y"] for e in gb.oam()[:4]] == sal, (sid, k)
                continue
            for _, _, cue, t, n in mine:
                at_frame(gb, k, t)
                assert st(gb, 0) == CU[cue], (sid, k)
                assert len(cameo_sprites(gb)) == n, (sid, k, t, len(cameo_sprites(gb)))
                assert per_line(gb) <= 10, (sid, k, t, per_line(gb))
                for e in cameo_sprites(gb):
                    assert e["x"] > 0 and e["x"] < 168, (sid, k, t, e)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_ufo_lifts_the_spigoteer_and_sets_him_down(model):
    gb = scene_of(model, "PRE_SPACE")
    with gb:
        sal = [e["y"] for e in gb.oam()[:4]]
        at_frame(gb, 0, 20)
        assert [e["y"] for e in gb.oam()[:4]] == sal
        at_frame(gb, 0, 60)
        assert all(e["y"] < y for e, y in zip(gb.oam()[:4], sal)), "rising"
        at_frame(gb, 0, 90)
        assert [e["y"] for e in gb.oam()[:4]] == [0, 0, 0, 0], "inside the UFO"
        page_ready(gb)
        turn_page(gb, 1)
        at_frame(gb, 1, 20)
        assert [e["y"] for e in gb.oam()[:4]] == [0, 0, 0, 0], "not yet down"
        at_frame(gb, 1, 60)
        assert all(0 < e["y"] < y for e, y in zip(gb.oam()[:4], sal)), "descending"
        at_frame(gb, 1, 100)
        assert [e["y"] for e in gb.oam()[:4]] == sal, "back at his tap"
        page_ready(gb)
        turn_page(gb, 2)
        gb.run(4)
        assert [e["y"] for e in gb.oam()[:4]] == sal and not cameo_sprites(gb)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("sid,k", [("PRE_LUMBER", 2), ("POST_ZOO", 1), ("PRE_SPACE", 0)])
def test_skipping_the_scene_mid_cue_leaves_no_cameo_sprite(model, sid, k):
    gb = scene_of(model, sid)
    with gb:
        to_page(gb, k)
        at_frame(gb, k, 30)
        assert cameo_sprites(gb)
        skip_scene(gb)
        gb.run(10)
        assert state(gb) != GS_STORY or gb.mem("story_scene") != SC[sid]
        assert not [s for s in gb.oam()[OAM0:] if s["y"] and s["tile"] >= 40 and s["tile"] < 128 and state(gb) != GS_STORY], "stray cameo sprites"
