# Option C (owner 2026-10-16): a catch whose push reaches the left-edge stop serves the patron at once (he slides off
# without drinking). A test bot measures the mugs it takes to clear a patron (the research's 3.5-3.7 on the arcade's
# first rows became about 1.7-1.9).
import pytest
from gbtools import Rom
from conftest import ROM, hold_stage_anim, title_level
import perf_helpers as ph
from perf_helpers import MAX_P, MAX_M

pytestmark = pytest.mark.timeout(300)
TARGETS = (20, 36, 52, 68, 84, 100)     # a fresh patron is first hit once he walks to x >= the target (cycled)


@pytest.fixture(params=["dmg", "cgb"])
def rom(request):
    with Rom(ROM, request.param) as gb:
        gb.run(120)
        hold_stage_anim(gb)
        gb.model_name = request.param
        yield gb


def mugs_to_clear(gb, level, frames):
    """Perfect-aim bot, one real mug (from the spout, real travel) in flight per bar. Returns the mugs each patron
    that was served took, first catch to his exit."""
    title_level(gb, level)
    for _ in range(60):
        if gb.mem("game_state") == 1:
            break
        gb.run(1)
    gb.write("intro_timer", 0)
    gb.write("tip_chance", 0)
    rec, out, k = {}, [], 0
    for _ in range(frames):
        gb.write("lives", 3); gb.write("quota", 250); gb.write("level_clear", 0)
        mx = gb.read("mug_x", MAX_M); ms = gb.read("mug_state", MAX_M)
        for m in range(MAX_M):
            if ms[m] == 2 and mx[m] >= 118:            # an empty on the counter: the bot takes it off
                ph.put(gb, "mug_state", m, 0)
        ms = list(gb.read("mug_state", MAX_M)); mb = list(gb.read("mug_bar", MAX_M))
        st = gb.read("patron_state", MAX_P); px = gb.read("patron_x", MAX_P); bar = gb.read("patron_bar", MAX_P)
        dr = gb.read("patron_drinks", MAX_P); aux = gb.read("patron_aux", MAX_P); dist = gb.read("patron_dist", MAX_P)
        free = [m for m in range(MAX_M) if ms[m] == 0]
        for p in range(MAX_P):
            if not st[p]:
                continue
            if p not in rec and dr[p] == 0 and st[p] == 1:
                rec[p] = dict(tgt=TARGETS[k % len(TARGETS)], n=0)
                k += 1
            r = rec.get(p)
            if r is None or not free:
                continue
            if not ((st[p] == 1 and not (dist[p] | aux[p]) and px[p] >= 16) or (st[p] == 3 and aux[p] != 0)):
                continue
            if dr[p] == 0 and px[p] < r["tgt"]:
                continue
            if any(ms[m] == 1 and mb[m] == bar[p] for m in range(MAX_M)):
                continue
            m = free.pop(0)
            for nm, v in (("mug_state", 1), ("mug_bar", bar[p]), ("mug_x", 136), ("mug_timer", 0)):
                ph.put(gb, nm, m, v)
            ms[m] = 1; mb[m] = bar[p]
        gb.write("mugs_live", sum(1 for v in gb.read("mug_state", MAX_M) if v))
        gb.write("mug_events", (gb.mem("mug_events") + 1) & 255)
        gb.run(1)
        st2 = gb.read("patron_state", MAX_P); dr2 = gb.read("patron_drinks", MAX_P)
        for p in range(MAX_P):
            r = rec.get(p)
            if r is None:
                continue
            if dr2[p] != dr[p] and dr2[p] != 255 and dr2[p] > dr[p] and st2[p]:
                r["n"] += 1
            if dr2[p] == 255 and dr[p] != 255:
                r["n"] += 1 if st[p] in (1, 3) else 0
                r["served"] = True
            if st2[p] == 0 and st[p] != 0:
                if r.get("served") and r["n"]:
                    out.append(r["n"])
                rec.pop(p)
    return out


@pytest.mark.parametrize("level,limit", [(1, 2.1), (9, 2.8)])
def test_a_patron_takes_about_two_mugs_to_clear(rom, level, limit):
    ns = mugs_to_clear(rom, level, 10000)
    mean = sum(ns) / len(ns)
    print(rom.model_name, "level", level, "patrons", len(ns), "mean mugs", round(mean, 2), "max", max(ns))
    assert len(ns) >= 8
    assert mean <= limit, (mean, ns)
