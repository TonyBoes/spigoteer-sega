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
            for b in range(4):                      # a bar whose door is clear
                if not any(pst[q] and pbar[q] == b and px[q] < 34 for q in range(MAX_P)):
                    self.put_patron(p, b, 0, WALKING, 1 if p % 3 == 0 else 0)
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
