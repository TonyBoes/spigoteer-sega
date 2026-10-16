# The VBlank copy list's per-VBlank budget (src/render.c vq_frame_end, src/vq_split.c; VQ_DRAIN_BUDGET): whoever queued the
# entries, queue_vram or a direct vq_add (mini-game HUDs, Duke's tile reloads, a cut-scene's page turn), a drain ends inside
# VBlank (LY 144-153: vq_end_ly_max stays below 154, which would be line 0 of the next frame) and no entry is lost: what does not fit
# waits at the head of the next list, in order. The review (batchH perf_review) found 13 CGB scenarios ending on line 0-3.
import pytest
from gbtools import Rom

from conftest import ROM
import perf_helpers as ph
from test_flow import GS_GOAL, state


@pytest.fixture(params=["dmg", "cgb"])
def model(request):
    return request.param


def watch(gb, frames, step=None):
    """Run `frames` frames; the latest line a drain ended on (154 + LY when it ran into the next frame) and the longest drain
    in DIV ticks, over all of them. step(i) runs before each frame."""
    gb.write("vq_end_ly_max", 0)
    gb.write("drain_ticks_max", 0)
    end = ticks = 0
    for i in range(frames):
        if step:
            step(i)
        gb.run(1)
        end = max(end, gb.mem("vq_end_ly_max"))
        ticks = max(ticks, gb.mem("drain_ticks_max"))
        gb.write("vq_end_ly_max", 0)
        gb.write("drain_ticks_max", 0)
    return end, ticks


def test_classic_crowd_drains_inside_vblank(model):
    """CLASSIC level 25 at the realistic peak (the review's worst CGB case: it ended on line 1)."""
    with Rom(ROM, model) as gb:
        gb.run(120)
        gb.model_name = model
        worst = [0, 0]

        def check(g, i):
            worst[0] = max(worst[0], g.mem("vq_end_ly_max"))
            worst[1] = max(worst[1], g.mem("drain_ticks_max"))
            g.write("vq_end_ly_max", 0)
            g.write("drain_ticks_max", 0)
        ph.realistic_run(gb, 600, check, target=16, cls=ph.ClassicPeak, classic=25)
        assert worst[0] <= 153, f"a drain ended on line {worst[0] - 154} of the next frame ({worst[1]} ticks)"
        assert gb.mem16("vq_late") == 0


def test_dukes_entrance_drains_inside_vblank(model):
    """Duke's entrance (his tile reloads queue 64 bytes a frame behind the frame's bars): 20 ticks, ending on line 3, before."""
    from boss_common import fight
    with fight(model, 6, entrance=True) as gb:
        end, ticks = watch(gb, 330)
        assert end <= 153, f"a drain ended on line {end - 154} of the next frame ({ticks} ticks)"


@pytest.mark.parametrize("scene", [3, 5])
def test_a_story_pre_scene_drains_inside_vblank(model, scene):
    """A story PRE scene, A held over it (page turns with portrait bursts: the review's PRE_BISTRO ended on line 1)."""
    from test_scores import v7_image
    import test_story
    gb = test_story.start_story(model, v7_image([], story=scene), cont=True)
    try:
        def mash(i):
            if i % 4 == 0:
                gb.hold("a")
            elif i % 4 == 2:
                gb.release("a")
        end, ticks = watch(gb, 700, mash)
        gb.release("a")
        assert end <= 153, f"a drain ended on line {end - 154} of the next frame ({ticks} ticks)"
    finally:
        gb.stop()


@pytest.mark.parametrize("gid", [0, 1, 2, 3, 4, 6, 7, 8, 9])
def test_a_mini_game_hud_drains_inside_vblank(model, gid):
    """The mini-games the review found ending on line 0 (HUD time, wall rows and banners queued directly with vq_add)."""
    import test_mg
    from test_scores import booted
    from conftest import hold_stage_anim
    gb = booted(model)
    try:
        hold_stage_anim(gb)
        test_mg.mg_enter(gb, gid, test_mg.MG_PRACTICE)

        def mash(i):
            if i % 6 == 0:
                gb.hold("a")
            elif i % 6 == 3:
                gb.release("a")
        end, ticks = watch(gb, 900, mash)
        gb.release("a")
        assert end <= 153, f"a drain ended on line {end - 154} of the next frame ({ticks} ticks)"
    finally:
        gb.stop()


def test_a_split_list_loses_nothing_and_keeps_its_order(model):
    """More than one drain's worth of rows queued in one frame: the first go out, the rest follow the next frame, and every row lands
    where it was queued, the later write of a doubled row winning."""
    with Rom(ROM, model) as gb:
        gb.run(120)
        gb.model_name = model
        # (title screen, LCD on: the queue's buffers are the title's own rows)
        vq, cnt = gb.addr("vq"), gb.addr("vq_count")
        assert gb.mem("vq_ready") == 0
        src = gb.addr("row_buf")
        n = 6                                   # 6 entries of 20 bytes: 6 * 23 = 138 units > VQ_DRAIN_BUDGET (86)
        for k in range(20):
            gb.write(src + k, 0x40 + k)
        for k in range(n):
            a = vq + 8 * k
            gb.write(a, 20)
            gb.write(a + 1, 0)
            gb.write(a + 2, src & 255)
            gb.write(a + 3, src >> 8)
            dst = 0x9800 + 32 * (12 + k)
            gb.write(a + 4, dst & 255)
            gb.write(a + 5, dst >> 8)
        gb.write(cnt, n)
        gb.write("qv_cost", 255)                # (what the writers' tally would say: over budget)
        gb.run(1)
        # the frame end splits it; after the next VBlanks every row is on the screen
        gb.run(4)
        tm = gb.bg_tilemap()
        for k in range(n):
            assert [t & 255 for t in tm[12 + k][:20]] == [0x40 + i for i in range(20)], k
