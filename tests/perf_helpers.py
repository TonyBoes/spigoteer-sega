# Frame-time benchmark helpers (M7.1). The game records, in WRAM, the scanline its per-frame work ended on
# (perf_logic_max: logic only, perf_end_max: logic + music tick; > 143 = ran past the next VBlank)
# and missed_frames (a frame that began outside VBlank or was skipped). Scenarios are set up by poking state.
PLAYING = 1
MAX_P, MAX_M = 16, 20
WALKING, PUSHED, DRINKING = 1, 2, 3
FULL, EMPTY, BREAKING, HELD = 1, 2, 3, 4


def put(gb, name, i, v):
    gb.write(gb.addr(name) + i, v)


def put16(gb, name, v):
    gb.write(name, v & 255)
    gb.write(gb.addr(name) + 1, v >> 8)


def start_game(gb):
    gb.press("start", 2)
    for _ in range(30):
        if gb.mem("game_state") == PLAYING:
            break
        gb.run(1)
    assert gb.mem("game_state") == PLAYING


def perf_reset(gb):
    for name in ("perf_logic_max", "perf_end_max", "missed_frames"):
        put16(gb, name, 0)


def perf_read(gb):
    return dict(logic=gb.mem16("perf_logic_max"), end=gb.mem16("perf_end_max"), missed=gb.mem16("missed_frames"))


def goto_level(gb, lvl):
    """Jump to the start of level lvl (an even level 2..8 is reached through the odd level before it)."""
    gb.write("level", lvl - 1)
    gb.write("game_state", 3)           # GS_LEVEL_CLEAR, one frame from the next level
    gb.write("state_timer", 149)
    for _ in range(40):
        gb.run(1)
        if gb.mem("level") == lvl and gb.mem("game_state") == PLAYING and gb.mem("quota") != 8:
            return
    raise AssertionError("level did not start")


SCRIPT = ["a"] * 30 + [None] * 6 + ["down"] + ["left"] * 12 + ["right"] * 12 + ["a"] * 26 + [None] * 4 + ["up"]


def play_script(gb, frames, lvl=8, keep=None):
    """The level-8 play script: the bartender keeps filling and serving; lives and quota are topped up."""
    gb.write("tip_chance", 255)
    held = None
    for i in range(frames):
        want = SCRIPT[i % len(SCRIPT)]
        if want != held:
            if held:
                gb.release(held)
            if want:
                gb.hold(want)
            held = want
        gb.run(1)
        gb.write("lives", 3)
        gb.write("quota", 250)
        if keep:
            keep(gb, i)
    if held:
        gb.release(held)


class WorstCase:
    """The heaviest realistic frame, kept up for as long as the test runs: 4 patrons on every bar (walking,
    pushed back, drinking; a third of the walkers distracted by a running show), 20 mugs in flight (full,
    empty, breaking, held by drinkers), a tip on the counter and the dancers on stage. Served or lost
    patrons and mugs are replaced every frame, so the load is a steady state of redraws, catches, serves and
    score changes rather than a one-off pile. Deterministic."""

    def __init__(self, gb):
        self.gb = gb
        self.rng = 12345

    def rand(self, n):
        self.rng = (self.rng * 1103515245 + 12345) & 0x7FFFFFFF
        return (self.rng >> 16) % n

    def seed(self):
        gb = self.gb
        for p in range(MAX_P):
            b, k = p & 3, p >> 2
            x = 2 + k * 32 + (p * 5) % 12
            state = (WALKING, WALKING, PUSHED, DRINKING)[(p + k) & 3]
            self.put_patron(p, b, x, state)
        for m in range(MAX_M):
            self.put_mug(m, m % 4, (FULL, EMPTY, EMPTY, BREAKING, FULL)[m % 5], 40 + (m * 23) % 90)
        self.top_up_effects(True)

    def put_patron(self, p, b, x, state, dist=0):
        gb = self.gb
        put(gb, "patron_state", p, state)
        put(gb, "patron_bar", p, b)
        put(gb, "patron_x", p, x)
        put(gb, "patron_frac", p, (p * 37) & 255)
        put(gb, "patron_draw", p, x)
        put(gb, "patron_variant", p, p % 3)
        put(gb, "patron_timer", p, (p * 11) % 80)
        put(gb, "patron_aux", p, (8 + p) if state == PUSHED else 0)
        put(gb, "patron_mug", p, 255)
        put(gb, "patron_dist", p, dist)
        put(gb, "patron_catchx", p, x)

    def put_mug(self, m, b, st, x):
        gb = self.gb
        put(gb, "mug_state", m, st)
        put(gb, "mug_bar", m, b)
        put(gb, "mug_x", m, x)
        put(gb, "mug_timer", m, (m * 5) % 40)

    def top_up_effects(self, first=False):
        gb = self.gb
        if gb.mem16("tip_timer") < 100:
            put16(gb, "tip_timer", 400)
            gb.write("tip_bar", 1)
            gb.write("tip_x", 60)
        if gb.mem16("show_timer") < 100:
            put16(gb, "show_timer", 704)

    def tick(self):
        """Call once per frame, before gb.run(1): refill what the game consumed."""
        gb = self.gb
        gb.write("lives", 3)
        gb.write("quota", 250)
        gb.write("spawned", 0)
        gb.write("level_clear", 0)
        gb.write("game_state", PLAYING)
        self.top_up_effects()
        pst = gb.read("patron_state", MAX_P)
        pbar = gb.read("patron_bar", MAX_P)
        px = gb.read("patron_x", MAX_P)
        for p in range(MAX_P):
            if pst[p]:
                continue
            for b in range(4):                      # a bar whose left end is clear (no doors: put in at ENTRY_X 16,
                if not any(pst[q] and pbar[q] == b and px[q] < 50 for q in range(MAX_P)):   # where a BG patron may stand)
                    self.put_patron(p, b, 16, WALKING, 1 if p % 3 == 0 else 0)
                    break
        mst = gb.read("mug_state", MAX_M)
        mbar = gb.read("mug_bar", MAX_M)
        live = 0
        for m in range(MAX_M):
            if mst[m]:
                live += 1
                continue
            b = self.rand(4)
            if sum(1 for q in range(MAX_M) if mst[q] and mbar[q] == b) >= 6:
                continue
            kind = self.rand(4)
            self.put_mug(m, b, FULL if kind < 2 else EMPTY, 136 if kind < 2 else 20 + self.rand(60))
            mst = gb.read("mug_state", MAX_M)
            live += 1
        gb.write("mugs_live", live)


def worst_case_run(gb, frames):
    """Level 9 speeds, the WorstCase pile; returns perf_read over `frames` frames."""
    start_game(gb)
    goto_level(gb, 8)
    gb.write("level", 9)
    gb.write("intro_timer", 0)
    gb.write("tip_chance", 255)
    wc = WorstCase(gb)
    wc.seed()
    gb.run(2)
    perf_reset(gb)
    for _ in range(frames):
        wc.tick()
        gb.run(1)
    return perf_read(gb)


# ---- M13b: the level-9 overlap scenario ---------------------------------------------------------------------------
def goto_level9(gb):
    """The start of level 9 (row 9: the fastest walkers, hurried patrons), through the bonus round after level 8."""
    gb.write("level", 8)
    gb.write("game_state", 3)           # GS_LEVEL_CLEAR, one frame from the next level (level 8 is followed by a bonus)
    gb.write("state_timer", 149)
    for _ in range(400):
        gb.run(1)
        st = gb.mem("game_state")
        if st == 6 and gb.mem("bonus_phase") != 4:   # GS_BONUS: jump to its last frame
            gb.write("bonus_phase", 4)
            gb.write("bonus_timer", 129)
        if gb.mem("level") == 9 and st == PLAYING:
            return
    raise AssertionError("level 9 did not start")


class OverlapCase:
    """Level 9, every bar: a pair of walkers overlapping (they pass each other: one is lifted, or both stay on the BG
    when the budgets say no), a third patron to their right who catches a full mug and, thirsty (his 3rd drink, 72 px),
    slides back through the pair; 4 mugs per bar in flight (the push mug and empties sliding to the tap end). The
    pusher is put back on his spot (walking) once he has drunk, the pair is put back when it reaches x 92, the empties
    are topped up: a steady state of pushes through pairs on all four bars. Deterministic."""
    PAIR_X, PAIR_DX, PUSHER_X = 44, 6, 100

    def __init__(self, gb, mugs=4):
        self.mugs = mugs                        # mugs per bar at most (all states)
        self.gb = gb
        self.slots = {}
        self.frame = 0

    def seed(self):
        gb = self.gb
        for p in range(MAX_P):
            put(gb, "patron_state", p, 0)
        for m in range(MAX_M):
            put(gb, "mug_state", m, 0)
        gb.write("mugs_live", 0)
        for b in range(4):
            a, c, d = 3 * b, 3 * b + 1, 3 * b + 2
            self.slots[b] = (a, c, d)
            self.put_patron(a, b, self.PAIR_X + 2 * b, hurry=0)
            self.put_patron(c, b, self.PAIR_X + 2 * b + self.PAIR_DX, hurry=0)
            put(gb, "patron_hurry", a, 1)                  # the one behind is hurried: he passes the other
            self.put_patron(d, b, self.PUSHER_X - 4 * b, hurry=0)
        gb.write("patrons_live", 12)

    def put_patron(self, p, b, x, state=WALKING, hurry=0):
        gb = self.gb
        put(gb, "patron_state", p, state)
        put(gb, "patron_bar", p, b)
        put(gb, "patron_x", p, x)
        put(gb, "patron_frac", p, 0)
        put(gb, "patron_draw", p, 255)
        put(gb, "patron_variant", p, p % 3)
        put(gb, "patron_timer", p, 0)
        put(gb, "patron_aux", p, 0)
        put(gb, "patron_mug", p, 255)
        put(gb, "patron_dist", p, 0)
        put(gb, "patron_drinks", p, 2)
        put(gb, "patron_hurry", p, hurry)
        put(gb, "patron_catchx", p, x)

    def free_mug(self, b, st, x):
        gb = self.gb
        mst = gb.read("mug_state", MAX_M)
        if 0 not in mst:
            return
        m = list(mst).index(0)
        put(gb, "mug_state", m, st)
        put(gb, "mug_bar", m, b)
        put(gb, "mug_x", m, x)
        put(gb, "mug_timer", m, 0)
        gb.write("mugs_live", sum(1 for s in gb.read("mug_state", MAX_M) if s))

    def tick(self):
        gb = self.gb
        self.frame += 1
        gb.write("lives", 3)
        gb.write("quota", 250)
        gb.write("spawned", 0)
        put16(gb, "spawn_timer", 5000)
        gb.write("level_clear", 0)
        gb.write("game_state", PLAYING)
        st, px = gb.read("patron_state", MAX_P), gb.read("patron_x", MAX_P)
        mst, mbar, mx = gb.read("mug_state", MAX_M), gb.read("mug_bar", MAX_M), gb.read("mug_x", MAX_M)
        for m in range(MAX_M):
            if mst[m] == EMPTY and mx[m] >= 110:           # an empty before the bartender slides again from the left end
                put(gb, "mug_x", m, 20)
        for b, (a, c, d) in self.slots.items():
            if not st[d] or (st[d] == WALKING and px[d] < self.PUSHER_X - 20):   # drunk (or served out): back on his spot
                self.put_patron(d, b, self.PUSHER_X - 4 * b)
            if not st[a] or not st[c] or max(px[a], px[c]) >= 92:
                self.put_patron(a, b, self.PAIR_X + 2 * b, hurry=1)
                self.put_patron(c, b, self.PAIR_X + 2 * b + self.PAIR_DX)
            # 4 mugs on the bar at most, all states counted: the pusher's (full, then held, then his empty) and empties
            on_bar = [mst[m] for m in range(MAX_M) if mst[m] and mbar[m] == b]
            if (st[d] == WALKING and FULL not in on_bar and HELD not in on_bar and len(on_bar) < self.mugs
                    and (self.frame + 7 * b) % 20 == 0):
                self.free_mug(b, FULL, min(136, px[d] + 30))
                on_bar.append(FULL)
            if on_bar.count(EMPTY) < self.mugs - 2 and len(on_bar) < self.mugs:
                self.free_mug(b, EMPTY, 20 + 10 * (self.frame % 5))
            mst, mbar = gb.read("mug_state", MAX_M), gb.read("mug_bar", MAX_M)


def overlap_run(gb, frames, check=None, mugs=4):
    """The OverlapCase scenario for `frames` frames; check(gb, i) after each. Returns perf_read."""
    start_game(gb)
    goto_level9(gb)
    gb.write("intro_timer", 0)
    gb.write("tip_chance", 0)
    oc = OverlapCase(gb, mugs)
    oc.seed()
    gb.run(2)
    perf_reset(gb)
    for i in range(frames):
        oc.tick()
        gb.run(1)
        if check:
            check(gb, i)
    return perf_read(gb)


# ---- M13c: the realistic peak of play ---------------------------------------------------------------------------------
class RealisticPeak:
    """Level 9 at the most the game's own limits produce (see test_perf.test_realistic_peak for the arithmetic): about 8
    patrons over the 4 bars at level-9 speeds (hurried ones among them), new ones sliding in from the left edge, at
    most 3 full mugs and 3 empties sliding plus the mugs drinkers hold, a tip on the counter OR the show (never both).
    The bartender plays the level-8 script (fills, launches, catches); everything else is the game's own rules: spawns
    are real (try_spawn + the entry from the left edge, made due at once while fewer than `target` patrons are in, at most every
    SPAWN_GAP frames), catches push patrons back through the others (lifts), drinkers send real empties.
    The test only (1) adds a full mug from the tap end, at most one every FULL_GAP frames and 3 in flight in all,
    for the bar whose front walker is furthest in, as a second bartender would; (2) takes an empty off the counter
    near the tap end on a bar the bartender is not on, as if he caught it; (3) puts a walker who got within reach of
    the tap back a little (a lost life would reset the bars); (4) tops up lives / quota and alternates the tip and the
    show every PHASE frames. Deterministic."""
    FULL_GAP, SPAWN_GAP, PHASE, FULL_MIN_X = 18, 24, 400, 72

    def __init__(self, gb, target=9):
        self.gb = gb
        self.target = target
        self.frame = 0
        self.last_full = -100
        self.last_spawn = -100
        self.stats = {"patrons": [], "mugs": [], "full": [], "empty": [], "held": [], "edge": 0, "hurried": set(),
                      "tip": 0, "show": 0, "both": 0, "spawned": 0, "leaving": 0}

    def seed(self):
        """Two patrons per bar: a walker and a drinker holding his mug."""
        gb = self.gb
        for p in range(MAX_P):
            put(gb, "patron_state", p, 0)
        for m in range(MAX_M):
            put(gb, "mug_state", m, 0)
        slot, mslot = 0, 0
        for b in range(4):
            pair = ((40 + 6 * b, DRINKING), (76 - 4 * b, WALKING)) if b & 1 else ((36 + 4 * b, WALKING), (70 + 3 * b, DRINKING))
            for x, st in pair:
                p = slot
                slot += 1
                for n, v in (("patron_state", st), ("patron_bar", b), ("patron_x", x), ("patron_frac", 0),
                             ("patron_draw", 255), ("patron_variant", p % 3), ("patron_timer", (p * 13) % 60),
                             ("patron_aux", 0), ("patron_mug", 255), ("patron_dist", 0), ("patron_drinks", 1),
                             ("patron_hurry", 1 if p in (1, 6) else 0), ("patron_catchx", x)):
                    put(gb, n, p, v)
                if st == DRINKING:
                    for n, v in (("mug_state", HELD), ("mug_bar", b), ("mug_x", x + 9), ("mug_timer", 0),
                                 ("mug_patron", p)):
                        put(gb, n, mslot, v)
                    put(gb, "patron_mug", p, mslot)
                    mslot += 1
        gb.write("mugs_live", mslot)
        gb.write("patrons_live", slot)

    def tick(self):
        """Call once per frame, before gb.run(1)."""
        gb, f = self.gb, self.frame
        self.frame += 1
        gb.write("lives", 3)
        gb.write("quota", 250)
        if gb.mem("spawned") > 200:
            gb.write("spawned", 100)
        gb.write("level_clear", 0)
        if gb.mem("game_state") != PLAYING:
            gb.write("game_state", PLAYING)
        st, bar, xs = gb.read("patron_state", MAX_P), gb.read("patron_bar", MAX_P), gb.read("patron_x", MAX_P)
        dist = gb.read("patron_dist", MAX_P)
        mst, mbar, mx = gb.read("mug_state", MAX_M), gb.read("mug_bar", MAX_M), gb.read("mug_x", MAX_M)
        live = [p for p in range(MAX_P) if st[p]]
        # tip OR show, alternating
        if (f // self.PHASE) & 1:                          # the show: a tip put under the bartender, picked up
            if f % self.PHASE == 0:
                put16(gb, "tip_timer", 0)
            elif f % self.PHASE == 2:
                put16(gb, "tip_timer", 400)
                gb.write("tip_bar", gb.mem("bar"))
                gb.write("tip_x", gb.mem("bartender_x"))
        else:
            if gb.mem16("show_timer") > 1:
                put16(gb, "show_timer", 1)                    # (ends this frame: the walkers turn back)
            elif f % self.PHASE > 4 and not gb.mem16("show_timer") and gb.mem16("tip_timer") < 100:
                put16(gb, "tip_timer", 400)
                gb.write("tip_bar", 2)
                gb.write("tip_x", 52)
        # spawns: real ones, made due while the bars are short of patrons
        if len(live) < self.target and f - self.last_spawn >= self.SPAWN_GAP and gb.mem16("spawn_timer") > 1:
            put16(gb, "spawn_timer", 0)
            self.last_spawn = f
        # a walker about to reach the tap gets his mug in time (a lost life would reset the bars)
        for p in live:
            if st[p] == WALKING and xs[p] >= 108:
                put(gb, "patron_x", p, 96)
        # one full mug at a time from the tap end, 3 in flight at most, for the bar whose front walker is furthest in
        full = sum(1 for m in range(MAX_M) if mst[m] == FULL)
        if full < 3 and f - self.last_full >= self.FULL_GAP:
            best = None
            for p in live:
                if st[p] != WALKING or xs[p] < self.FULL_MIN_X or dist[p]:
                    continue
                b = bar[p]
                if any(mst[m] == FULL and mbar[m] == b for m in range(MAX_M)):
                    continue
                if best is None or xs[p] > best[0]:
                    best = (xs[p], b)
            if best and 0 in mst:
                m = list(mst).index(0)
                for n, v in (("mug_state", FULL), ("mug_bar", best[1]), ("mug_x", 136), ("mug_timer", 0)):
                    put(gb, n, m, v)
                gb.write("mugs_live", gb.mem("mugs_live") + 1)
                gb.write("mug_events", gb.mem("mug_events") + 1)
                self.last_full = f
        # empties near the tap end on another bar than the bartender's, or a 4th one sliding (fair empties keep 3 at most;
        # a caught drinker's empty goes at once): caught
        btb = gb.mem("bar")
        empties = sorted((mx[m], m) for m in range(MAX_M) if mst[m] == EMPTY)
        for k, (x, m) in enumerate(reversed(empties)):
            if (x >= 112 and mbar[m] != btb) or k < len(empties) - 3:
                put(gb, "mug_state", m, 0)
                gb.write("mugs_live", max(0, gb.mem("mugs_live") - 1))

    def observe(self):
        """Call after each frame: what the frame held (the test checks the scenario is what it says)."""
        gb, s = self.gb, self.stats
        st, lift, hurry = gb.read("patron_state", MAX_P), gb.read("patron_lift", MAX_P), gb.read("patron_hurry", MAX_P)
        mst = gb.read("mug_state", MAX_M)
        s["patrons"].append(sum(1 for v in st if v))
        s["mugs"].append(sum(1 for v in mst if v))
        s["full"].append(sum(1 for v in mst if v == FULL))
        s["empty"].append(sum(1 for v in mst if v == EMPTY))
        s["held"].append(sum(1 for v in mst if v == HELD))
        s["edge"] += sum(1 for p in range(MAX_P) if st[p] and lift[p] == 2)      # LIFT_EDGE: entering or leaving
        s["leaving"] += sum(1 for p in range(MAX_P) if st[p] == 4)
        s["hurried"] |= {p for p in range(MAX_P) if st[p] and hurry[p]}
        oam = gb.oam()                                    # (what the screen shows: the coin, the dancers)
        tip, show = bool(oam[27]["y"]), any(oam[28 + k]["y"] for k in range(12))
        s["tip"] += tip
        s["show"] += show
        s["both"] += tip and show


def realistic_run(gb, frames, check=None, target=9):
    """The RealisticPeak scenario at level 9 for `frames` frames (the bartender on the level-8 script); check(gb, i)
    after each. Returns (perf_read, the scenario's stats, lifts by the chooser in the run)."""
    start_game(gb)
    goto_level9(gb)
    gb.write("intro_timer", 0)
    gb.write("tip_chance", 0)
    rp = RealisticPeak(gb, target)
    rp.seed()
    gb.run(2)
    perf_reset(gb)
    lifts0 = gb.mem("lift_lifts")
    held = None
    for i in range(frames):
        want = SCRIPT[i % len(SCRIPT)]
        if want != held:
            if held:
                gb.release(held)
            if want:
                gb.hold(want)
            held = want
        sp = gb.mem("spawned")
        rp.tick()
        gb.run(1)
        if gb.mem("spawned") > sp:
            rp.stats["spawned"] += gb.mem("spawned") - sp
        rp.observe()
        if check:
            check(gb, i)
    if held:
        gb.release(held)
    return perf_read(gb), rp.stats, (gb.mem("lift_lifts") - lifts0) & 255
