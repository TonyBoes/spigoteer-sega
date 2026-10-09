# M13b: the overlap rules (docs/overlap_design.md "Rules"). Patrons overlap and pass: a pushed patron slides back
# through anyone, walkers pass slower walkers and drinkers (they wait only where a step would put three patrons in
# one tile column), about 1 in 4 patrons hurries from level 3, and the chooser (src/lift.c) lifts patrons to sprites
# so that the BG ones never share a tile column; when the budgets say no, the pair stays on the BG with the would-be
# lifted one drawn over the other.
#
# The picture is checked structurally, every frame: each BG patron's real columns show his tile ids (or, where two
# share a column, those of the one on top), every other column of the bar's wall rows shows the venue's wall or a
# patron's empty column (no garbage), and each lifted patron has his two sprites. State is snapshotted where the game's
# frame ends (vq_frame_end): the emulator's frame boundary falls inside the game's update.
from pathlib import Path

import pytest

from conftest import GAME, ROOT, bar_top_row, bar_top_y, venue_rows
from test_patrons import (BASE, DRINKING, EMPTY, FULL, HELD, MAX_M, MAX_P, PUSHED, SHIFT0_OFS, WALKING, clear_patrons,
                          freeze, go, hold_mug, inject_mug, lineup, mugs, pose_first, put, set_patron)

pytestmark = pytest.mark.timeout(120)

OBJ_BASE = BASE + SHIFT0_OFS
PX = 32                                   # level 1 push-back (4 columns)
DRAW_BACK = 0x80
OUT = ROOT / "out" / "m13b"
OVL_SHARED, OVL_TOP, OVL_TWO = GAME["OVL_SHARED"], GAME["OVL_TOP"], GAME["OVL_TWO"]
BACK_BASE = BASE + int(__import__("re").search(r"#define PATRON_TILES_PER_GROUP (\d+)",
                                               (ROOT / "build" / "art.h").read_text()).group(1))


# ---- the structural picture check -----------------------------------------------------------------------------------
class Frames:
    """Snapshots of the patron state at the end of every game frame (a PyBoy hook on vq_frame_end)."""
    FIELDS = ("patron_state", "patron_bar", "patron_draw", "patron_variant", "patron_lift", "patron_ovl", "patron_x")

    def __init__(self, gb):
        self.gb = gb
        self.snaps = []
        a = gb.addr("vq_frame_end")
        gb.pb.hook_register(a >> 16, a & 0xFFFF, self._cb, None)

    def _cb(self, _):
        self.snaps.append({f: list(self.gb.read(f, MAX_P)) for f in self.FIELDS})


def blank_ids():
    return {OBJ_BASE + 6 * v + 4 for v in range(3)}, {OBJ_BASE + 6 * v + 5 for v in range(3)}


def expected_cols(s, p):
    """{column: (top id, bottom id)} of BG patron p's real columns in snapshot s."""
    d, v = s["patron_draw"][p], s["patron_variant"][p] % 3
    if d & DRAW_BACK:
        c, t = (d & 0x7F) >> 3, BACK_BASE + 4 * v
        return {c: (t, t + 2), c + 1: (t + 1, t + 3)}
    c, sh = d >> 3, d & 7
    first = pose_first(v, sh)
    return {c + k: (first + 2 * k, first + 2 * k + 1) for k in range(3 if sh else 2)}


def picture_problems(gb, s, b):
    """What is wrong with bar b's wall rows and the lifted patrons' sprites for the state s (empty: all right)."""
    tm = gb.bg_tilemap()
    rows = [[t & 0xFF for t in tm[bar_top_row(b) + r][:20]] for r in range(2)]
    wall = venue_rows(gb.mem("cur_group"), "bar_map")
    btop, bbot = blank_ids()
    pats = [p for p in range(MAX_P) if s["patron_state"][p] and s["patron_bar"][p] == b and s["patron_draw"][p] != 255]
    bg = [p for p in pats if not (s["patron_lift"][p] & 3) or (s["patron_lift"][p] & 0x80)]
    lifted = [p for p in pats if (s["patron_lift"][p] & 3)]
    cover = {}
    for p in bg:
        for c, ids in expected_cols(s, p).items():
            if c < 20:
                cover.setdefault(c, []).append((p, ids))
    problems = []
    for c in range(20):
        got = (rows[0][c], rows[1][c])
        if c in cover:
            owners = cover[c]
            tops = [o for o in owners if s["patron_ovl"][o[0]] & OVL_TOP]
            if len(owners) == 1 or len(tops) == 1:
                want = [(tops or owners)[0][1]]
            else:
                want = [o[1] for o in owners]
            if got not in want:
                problems.append((c, got, "want one of", want, [o[0] for o in owners]))
        elif got != (wall[0][c], wall[1][c]) and not (got[0] in btop and got[1] in bbot):
            problems.append((c, got, "not wall or an empty patron column"))
    oam = [o for o in gb.oam() if o["y"]]
    for p in lifted:
        d, v = s["patron_draw"][p], s["patron_variant"][p] % 3
        y = bar_top_y(b) + 16
        for dx, t in ((0, OBJ_BASE + 6 * v), (8, OBJ_BASE + 6 * v + 2)):
            if not any(o["y"] == y and o["x"] == d + 8 + dx and o["tile"] == t for o in oam):
                problems.append(("lifted", p, d, dx, "sprite missing"))
    return problems


def assert_picture(gb, frames, b, tag=""):
    """The picture after this emulator frame matches the last finished game frame, or (a copy that waited for the
    VBlank budget) the one before it."""
    probs = picture_problems(gb, frames.snaps[-1], b)
    if probs and len(frames.snaps) > 1:
        probs2 = picture_problems(gb, frames.snaps[-2], b)
        if not probs2:
            return
    assert not probs, (tag, probs)


def oam_lines(gb):
    c = [0] * 144
    for s in gb.oam():
        if not s["y"] or s["y"] >= 160:
            continue
        y = s["y"] - 16
        for line in range(max(0, y), min(144, y + 16)):
            c[line] += 1
    return c


def lift(gb, p):
    return gb.read("patron_lift", MAX_P)[p]


# ---- pushed patrons slide through ---------------------------------------------------------------------------------
def test_a_pushed_patron_slides_through_a_walker_and_both_stay_visible(gb):
    """The pushed patron is lifted while he shares a column with the walker (the higher priority), slides through
    him his full push-back, drinks on top of him (still lifted), and every frame shows both: the walker's tiles on the
    BG, the pushed one's sprites, nothing else. x4 screenshot mid-slide in out/m13b/."""
    freeze(gb)
    slots = lineup(gb, {0: [(40, 1, 0), (80, 2, 0)], 2: [(64, 0, 0)]})   # (the level's own start patrons, moved)
    w, p = slots[(0, 40)][0], slots[(0, 80)][0]
    gb.run(3)
    frames = Frames(gb)
    inject_mug(gb, 0, 84)
    lifted_seen, shot = False, False
    OUT.mkdir(parents=True, exist_ok=True)
    for i in range(3 + PX + 20):
        gb.run(1)
        assert_picture(gb, frames, 0, i)
        if lift(gb, p) & 3:
            lifted_seen = True
            x = gb.read("patron_x", MAX_P)[p]
            if not shot and x <= 52:                    # (he ends at 48, over the walker at 40)
                gb.screenshot(OUT / f"slide_through.{gb.model_name}.png", 4)
                shot = True
        assert not (lift(gb, w) & 3), "the walker stays on the BG (the pushed one has the priority)"
    assert lifted_seen and shot
    assert gb.read("patron_x", MAX_P)[p] == 80 - PX and gb.read("patron_state", MAX_P)[p] == DRINKING
    assert gb.read("patron_x", MAX_P)[w] == 40 and gb.read("patron_state", MAX_P)[w] == WALKING
    assert lift(gb, p) & 3, "he drinks lifted while he shares a column with the walker"
    assert max(oam_lines(gb)) <= 10


def test_a_drinker_on_top_of_someone_drops_to_the_bg_when_clear(gb):
    """A push ends on top of a walker: the drinker stays lifted; the walker walks away; LIFT_CLEAR_FRAMES frames after
    their columns part the drinker drops back to the BG, and the picture is right on every frame."""
    clear_patrons(gb)
    freeze(gb)
    w = set_patron(gb, 1, 48)
    p = set_patron(gb, 1, 80, variant=1)
    gb.run(3)
    frames = Frames(gb)
    inject_mug(gb, 1, 84)
    gb.run(3 + PX + 4)
    assert gb.read("patron_x", MAX_P)[p] == 48 and lift(gb, p) & 3
    gb.write("intro_timer", 0)                        # the walker walks on (the drinker drinks, ~90 frames)
    clear_frame = None
    for i in range(80):
        gb.write("patron_speed", 255)
        gb.run(1)
        assert_picture(gb, frames, 1, i)
        s = frames.snaps[-1]
        wc = set(expected_cols(s, w)) if not (s["patron_lift"][w] & 3) else set()
        pd = s["patron_draw"][p]
        pc = set(range(pd >> 3, (pd >> 3) + (3 if pd & 7 else 2)))
        if clear_frame is None and not (wc & pc):
            clear_frame = i
        if not (lift(gb, p) & 3):
            break
    assert clear_frame is not None and not (lift(gb, p) & 3), "dropped"
    assert i - clear_frame >= GAME["LIFT_CLEAR_FRAMES"], (clear_frame, i)
    assert gb.read("patron_state", MAX_P)[p] == DRINKING


# ---- walkers pass ----------------------------------------------------------------------------------------------------
def test_a_hurried_walker_passes_a_slower_one(gb):
    """A hurried walker (1.5x) catches up with a walker ahead and passes him: one of them is lifted while they share a
    column (the hurried one: the faster walker has the priority), both are visible every frame. x4 screenshot of the
    pass in out/m13b/."""
    freeze(gb)
    slots = lineup(gb, {0: [(20, 0, 0), (16, 2, 0)], 2: [(20, 1, 0)]})   # (the level's own start patrons, moved)
    slow, fast = slots[(0, 20)][0], slots[(0, 16)][0]
    put(gb, "patron_hurry", fast, 1)
    put(gb, "patron_hurry", slots[(2, 20)][0], 0)
    gb.run(2)
    go(gb)
    frames = Frames(gb)
    shot, lifted = False, set()
    for i in range(600):
        gb.write("patron_speed", 128)                 # (a quick test: 0.5 and 0.75 px a frame, the 1.5 ratio)
        gb.write("hurry_speed", 192)
        gb.run(1)
        assert_picture(gb, frames, 0, i)
        xs = gb.read("patron_x", MAX_P)
        for q in (slow, fast):
            if lift(gb, q) & 3:
                lifted.add(q)
        if not shot and lift(gb, fast) & 3 and abs(xs[fast] - xs[slow]) <= 3:
            gb.screenshot(OUT / f"pass.{gb.model_name}.png", 4)
            shot = True
        if xs[fast] > xs[slow] + 16:
            break
    assert xs[fast] > xs[slow] + 16, "passed"
    assert lifted == {fast}, "the hurried walker goes up, the slower one stays on the BG"
    assert shot and gb.mem("lives") == 3


def test_hurried_patrons_from_level_3_at_one_and_a_half_times_the_speed(gb):
    """Levels 1-2: nobody hurries. From level 3 about 1 in 4 spawns is hurried, at 1.5x the level's speed."""
    from test_edge import goto_level
    assert gb.mem("hurry_speed") == 0
    goto_level(gb, 3)
    speed = gb.mem("patron_speed")
    assert gb.mem("hurry_speed") == speed + speed // 2
    gb.write("quota", 250)
    hurried = 0
    for n in range(48):
        clear_patrons(gb)
        gb.write("intro_timer", 0)
        gb.write("spawn_timer", 0)
        gb.write(gb.addr("spawn_timer") + 1, 0)
        gb.run(2)
        st = gb.read("patron_state", MAX_P)
        p = [i for i in range(MAX_P) if st[i]]
        assert len(p) == 1, p
        hurried += gb.read("patron_hurry", MAX_P)[p[0]]
    assert 5 <= hurried <= 20, hurried
    clear_patrons(gb)
    fast = set_patron(gb, 0, 40, hurry=1)
    slow = set_patron(gb, 2, 40)
    gb.run(240)
    xs = gb.read("patron_x", MAX_P)
    assert 1.35 <= (xs[fast] - 40) / max(1, xs[slow] - 40) <= 1.65, xs


def test_a_walker_waits_rather_than_make_three_in_a_column(gb):
    """Two drinkers share columns 6-7 (x 48 and 52); a walker from the left end may pass through them only one column at
    a time: from x 32 (columns 4-5) his next step would take him into column 6 with both of them: he waits there,
    and goes on when one of them has left. Never three patrons in a tile column."""
    clear_patrons(gb)
    go(gb)
    d1 = set_patron(gb, 3, 48, state=DRINKING, timer=0)
    d2 = set_patron(gb, 3, 52, state=DRINKING, timer=40)   # (52: columns 6-8, the sway keeps him there)
    w = set_patron(gb, 3, 24)
    gb.run(2)
    frames = Frames(gb)
    xs_w = []
    for i in range(300):
        gb.write("patron_speed", 255)
        gb.run(1)
        assert_picture(gb, frames, 3, i)
        s = frames.snaps[-1]
        cnt = [0] * 21
        for p in (d1, d2, w):
            if s["patron_state"][p] and s["patron_draw"][p] != 255:
                for c in expected_cols(s, p):
                    cnt[c] += 1
        assert max(cnt) <= 2, (i, cnt)
        xs_w.append(gb.read("patron_x", MAX_P)[w])
    assert xs_w[40] == 32, "waits at x 32 while both drinkers stand in column 6"
    assert xs_w[-1] > 60, "and walks on once one has left"


# ---- the budget-exhausted fallback ------------------------------------------------------------------------------------
def fill_oam_with_mugs(gb, bars=(1, 2, 3), per_bar=6):
    for b in bars:
        for k in range(per_bar):
            inject_mug(gb, b, 24 + 12 * k, EMPTY)


def test_when_no_lift_is_possible_the_pair_stays_on_the_bg_and_the_pushed_one_covers(gb):
    """18 empties in flight leave no OAM entries for a lifted patron: a pushed patron sliding through a walker stays on
    the BG, drawn over him (he would have been the one lifted), the walker loses his quick redraws, and the picture is
    right (no garbage) on every frame."""
    clear_patrons(gb)
    freeze(gb)
    w = set_patron(gb, 1, 40, variant=1)
    p = set_patron(gb, 1, 80, variant=2)
    gb.run(3)
    fill_oam_with_mugs(gb, bars=(0, 2, 3))
    frames = Frames(gb)
    inject_mug(gb, 1, 84)
    tops = 0
    for i in range(3 + PX + 10):
        gb.run(1)
        for m in range(MAX_M):                          # keep the empties away from the bartender
            if gb.read("mug_state", MAX_M)[m] == EMPTY and gb.read("mug_x", MAX_M)[m] > 100:
                put(gb, "mug_x", m, 24)
        assert gb.mem("lift_total") == 0
        assert_picture(gb, frames, 1, i)
        ovl = gb.read("patron_ovl", MAX_P)
        if ovl[p] & OVL_TOP:
            tops += 1
            assert ovl[w] & OVL_SHARED, "the covered one is composed, not quick-redrawn"
    assert tops > 0, "the pushed one was drawn on top"
    assert gb.read("patron_x", MAX_P)[p] == 80 - PX


def test_three_patrons_in_one_column_by_a_push_use_both_lifts_of_the_bar(gb):
    """A push ends on two walkers who share columns: three in a column. The bar's two lifts go to the pushed one and
    one walker; the third stays on the BG; every frame is right; 10 objects per line at most."""
    clear_patrons(gb)
    freeze(gb)
    a = set_patron(gb, 3, 44)
    c = set_patron(gb, 3, 48, variant=1)
    p = set_patron(gb, 3, 76, variant=2)
    gb.run(4)
    frames = Frames(gb)
    inject_mug(gb, 3, 80)
    for i in range(3 + PX + 12):
        gb.run(1)
        assert_picture(gb, frames, 3, i)
        assert max(oam_lines(gb)) <= 10
        assert gb.read("lift_n", 4)[3] <= 2
    assert gb.read("patron_x", MAX_P)[p] == 76 - PX == 44
    lifted = [q for q in (a, c, p) if lift(gb, q) & 3]
    assert p in lifted and len(lifted) == 2, lifted


# ---- the chooser's priorities -------------------------------------------------------------------------------------------
def test_the_walker_goes_up_over_a_drinker_and_never_a_watcher(gb):
    clear_patrons(gb)
    go(gb)
    d = set_patron(gb, 1, 50, state=DRINKING, timer=0)
    w = set_patron(gb, 1, 30)
    gb.run(2)
    for _ in range(40):
        gb.write("patron_speed", 255)
        gb.run(1)
        if lift(gb, w) & 3:
            break
    assert lift(gb, w) & 3 and not (lift(gb, d) & 3), "walker over drinker"
    # a watcher (distracted by the show) is never lifted: the walker passing him goes up
    clear_patrons(gb)
    gb.write("show_timer", 200)
    gb.write(gb.addr("show_timer") + 1, 0)
    v = set_patron(gb, 1, 48)
    put(gb, "patron_dist", v, 1)
    w = set_patron(gb, 1, 24)
    gb.run(3)
    seen = set()
    for _ in range(60):
        gb.write("patron_speed", 255)
        gb.run(1)
        for q in (v, w):
            if lift(gb, q) & 3:
                seen.add(q)
    assert v not in seen and w in seen


# ---- catching and empties with overlaps -----------------------------------------------------------------------------
def test_catch_order_with_overlapping_patrons(gb):
    """Unchanged rule: the rightmost catcher whose 16 px contain the mug catches it, overlapping or not."""
    clear_patrons(gb)
    freeze(gb)
    a = set_patron(gb, 0, 60)
    b = set_patron(gb, 0, 66, variant=1)
    gb.run(3)
    inject_mug(gb, 0, 100)
    gb.run(20)
    st = gb.read("patron_state", MAX_P)
    assert st[b] in (PUSHED, DRINKING) and st[a] == WALKING, "the one further right caught it"
    m = [mm for mm in mugs(gb) if mm["state"] == HELD]
    assert len(m) == 1 and gb.read("mug_patron", MAX_M)[m[0]["i"]] == b


def test_an_overlapped_drinker_sends_his_empty_and_the_bartender_catches_it(gb):
    """A drinker standing over a walker (one of them lifted) finishes, winds up and sends his empty from his right
    edge; it slides to the bartender, who catches it (100 points). Fair empties as before."""
    clear_patrons(gb)
    freeze(gb)
    w = set_patron(gb, 0, 70)
    d = set_patron(gb, 0, 74, state=DRINKING, timer=85, variant=1)
    hold_mug(gb, d, 0)
    gb.run(4)
    assert (lift(gb, w) | lift(gb, d)) & 3
    score0 = int.from_bytes(gb.read("score", 4), "little")
    sent = None
    for i in range(400):
        gb.run(1)
        ms = [mm for mm in mugs(gb) if mm["state"] == EMPTY]
        if ms and sent is None:
            sent = ms[0]["x"]
        if int.from_bytes(gb.read("score", 4), "little") - score0 == 100:
            break
    assert sent is not None and sent >= 74 + 16, sent
    assert int.from_bytes(gb.read("score", 4), "little") - score0 == 100 and gb.mem("lives") == 3


# ---- DMG: a lifted holder keeps his mug in sight -------------------------------------------------------------------------
def test_dmg_lifted_holder_mug_dx(gb):
    """DMG: between sprites the lower X wins, so a lifted patron's own entries would hide his mug where it starts left
    of his right entry: the held mug is drawn at dx 8 (level with that entry) while he carries it back, drinks and
    winds up, and at dx 16 in the last throw pose. CGB keeps the art's offsets (there the lower OAM index wins)."""
    clear_patrons(gb)
    freeze(gb)
    set_patron(gb, 1, 40)
    p = set_patron(gb, 1, 80, variant=1)
    gb.run(3)
    inject_mug(gb, 1, 84)
    gb.run(3)
    m = gb.read("patron_mug", MAX_P)[p]
    assert gb.read("mug_state", MAX_M)[m] == HELD
    dxs, poses = set(), 0
    for i in range(PX + 90 + 40):
        gb.run(1)
        if gb.read("mug_state", MAX_M)[m] != HELD or gb.read("patron_mug", MAX_P)[p] != m:
            break
        if not (lift(gb, p) & 3):
            continue
        dxs.add(gb.read("mug_x", MAX_M)[m] - gb.read("patron_draw", MAX_P)[p])
        poses += 1
    assert poses > 100, poses
    if gb.model_name == "dmg":
        assert dxs == {8, 16}, dxs
    else:
        assert {9, 4, 14} <= dxs, dxs
