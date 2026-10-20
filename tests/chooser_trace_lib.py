"""The crowd chooser's decisions as data (src/lift.c choose_bar; tests/test_chooser_trace.py, tools/gen_chooser_trace.py).

A case is the state the chooser reads, by name (the patron arrays, the lift budgets, the bar lists, the copy-list state bg_urgent looks at, the
mug state the line estimate counts), the bar, and what the call changed in WRAM, by name + offset (scratch left out). One case runs through the
function-level rig (tests/asm_rig.py: interrupts off, LCD off, so nothing depends on the line the call lands on) on a booted ROM, so a case
means the same on any build of the game. tests/data/chooser_trace.json.gz holds the cases and the changes the chooser made BEFORE the speed-up
(asm_cfg.h ASM_CHOOSER): any later build must make exactly the same changes.

Why not a trace of whole runs: the builds differ in speed, so frames fall in different places (the chooser defers itself on a late frame, a
bar's spans too) and two runs of one scene drift apart after a few hundred frames, whatever the code does (tests/test_mugs_asm.py says the same).
The cases are the states real runs put the chooser in (captured from the ARCADE peaks, CLASSIC's 16-patron level, with their shows), so every
call of a long run is a case; the calls of a run are what a trace of its decisions would be made of.
"""
import gzip
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
from asm_rig import Call, Rig  # noqa: E402

DATA = ROOT / "tests" / "data" / "chooser_trace.json.gz"

# what the chooser reads (and writes): global arrays, then statics ("module:_name")
FIELDS = [("patron_state", 16), ("patron_bar", 16), ("patron_draw", 16), ("patron_lift", 16), ("patron_ovl", 16), ("patron_dist", 16),
          ("patron_hurry", 16), ("lift_bp", 32), ("lift_clear", 16), ("lift_n", 4), ("lift_total", 1), ("lift_lifts", 1), ("ovl_bars", 1),
          ("ovl_dirty", 1), ("mugs_live", 1), ("mug_events", 1), ("lift_mug_oam", 1), ("bar_list", 64), ("bar_n", 4), ("lists_ok", 1),
          ("vq_held", 1), ("vram_pending", 1), ("mug_state", 20), ("mug_bar", 20), ("fill_timer", 1), ("bar", 1), ("tip_timer", 2),
          ("tip_bar", 1),
          ("lift:_est_ok", 1), ("lift:_ld", 4), ("lift:_mg_ld", 4), ("lift:_mg_oam", 1), ("lift:_mg_live", 1), ("lift:_mg_ev", 1),
          ("render:_urg_n", 1), ("render:_urg_b", 2), ("render:_urg_c", 2), ("render:_dirty_x0", 4), ("render:_dirty_x1", 4)]
# what the call writes that is not a decision (dead after it, whichever way the build keeps it)
SCRATCH = ["rec", "rec_end", "g_bar", "g_c", "g_d", "g_o", "ch_l", "ch_r", "ch_x", "ch_b", "ch_bit", "s_r", "s_x", "md_x0", "md_x1"]
FN = "lift:_choose_bar"


class Table:
    """Address -> name + offset for WRAM, from the globals (.noi) and the statics (tools/asm_symtab.py) of one ROM."""

    def __init__(self, rig):
        syms = {}
        for k, v in rig.noi.items():
            a = v & 0xFFFF
            if 0xC000 <= a < 0xE000 and not k.startswith("__") and not k.startswith("l_") and not k.startswith("s_"):
                syms[k[1:] if k.startswith("_") else k] = a
        for k, a in rig.statics.items():
            if 0xC000 <= a < 0xE000:
                syms[k] = a
        self.sorted = sorted((a, n) for n, a in syms.items())
        self.addrs = [a for a, _ in self.sorted]
        self.scratch = set()
        for n in SCRATCH:
            a = syms["lift:_" + n]
            nxt = min([x for x in self.addrs if x > a] or [a + 1])
            self.scratch |= set(range(a, nxt))
        self.syms = syms

    def name(self, addr):
        import bisect
        i = bisect.bisect_right(self.addrs, addr) - 1
        a, n = self.sorted[i]
        return f"{n}+{addr - a}"


def read_fields(m, rig):
    return {n: bytes(m[rig.addr(n):rig.addr(n) + sz]).hex() for n, sz in FIELDS}


def call(case, **kw):
    """ch_retry (an output: the bar's lift has to wait) starts at 255, so that the change shows whatever it was left at before."""
    poke = {n: bytes.fromhex(h) for n, h in case["in"].items()}
    poke["lift:_ch_retry"] = b"\xff"
    return Call(FN, a=case["b"], poke=poke, **kw)


def run_cases(rom, model, cases):
    """The changes (name + offset -> value) each case makes on `rom`."""
    rig = Rig(rom, model)
    tab = Table(rig)
    res = rig.run([call(c) for c in cases], frames_max=3 * len(cases) + 100)
    return [{tab.name(a): v for a, v in r.diff.items() if a not in tab.scratch} for r in res], res


def load(path=DATA):
    with gzip.open(path, "rt") as f:
        return json.load(f)


def save(cases, path=DATA):
    path.parent.mkdir(exist_ok=True)
    with gzip.open(path, "wt", compresslevel=9) as f:
        json.dump(cases, f, separators=(",", ":"))


# ---- scenes (the realistic peaks of tests/perf_helpers.py, as the perf profile runs them) -------------------------------------------------
def new_rom(rom, model):
    from gbtools import Rom
    gb = Rom(rom, model)
    gb.run(120)
    gb.model_name = model
    return gb


def arcade_at(rom, model, chapter=9, loop=4):
    """ARCADE run, chapter `chapter`'s Last call (shift 2) at loop `loop` (level = chapter + 1 + (loop - 1) * 10): the space lounge."""
    from test_arcade import start_arcade
    from test_story import SHIFT_STEP, win, to_goal
    from test_flow import state, LEVEL_CLEAR, GS_GOAL, run_until
    gb = start_arcade(model)
    to_goal(gb)
    gb.write("story_step", SHIFT_STEP[2] - 1)
    gb.write("story_chapter", chapter)
    gb.write("arc_loop", loop)
    win(gb, 0, 0)
    run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 40)
    run_until(gb, lambda: state(gb) == GS_GOAL, 800)
    to_goal(gb)
    for _ in range(220):
        if gb.mem("game_state") == 1:
            break
        gb.run(1)
    return gb


SCENES = {"peak10": ("arcade", 10), "peak12": ("arcade", 12), "classic16": ("classic", 16)}


def scene(rom, name, model, v):
    """(gb, scenario, script) for one scene and variant v (a different RNG / script phase / alignment)."""
    import perf_helpers as ph
    kind, n = SCENES[name]
    if kind == "arcade":
        gb = arcade_at(rom, model)
        gb.write("intro_timer", 0)
        gb.write("tip_chance", 0)
        rp = ph.RealisticPeak(gb, n)
    else:
        from test_classic_mode import classic_at
        gb = new_rom(rom, model)
        classic_at(gb, 25)
        gb.write("intro_timer", 0)
        gb.write("tip_chance", 0)
        rp = ph.ClassicPeak(gb, n)
    rp.seed()
    if v:
        gb.write("rng_state", (v * 37 + 11) & 255 or 1)
    gb.run(2 + (v * 3) % 11)
    return gb, rp


def capture(rom, name, model, v, frames, every):
    """Every `every`-th call of choose_bar in `frames` frames of the scene, as cases (without their changes yet)."""
    import perf_helpers as ph
    gb, rp = scene(rom, name, model, v)
    rig = Rig(rom, model, gb=gb)
    bank, fa = rig.fn(FN)
    m, rf = gb.pb.memory, gb.pb.register_file
    got = []
    n = [0]

    def entry(_):
        n[0] += 1
        if n[0] % every == 0:
            got.append({"s": f"{name}-{model}-{v}", "b": rf.A & 3, "in": read_fields(m, rig),
                        "_wram": bytes(m[0xC000:0xE000]), "_hram": bytes(m[0xFF80:0xFFFF])})   # (the images only prove the fields are enough)
    gb.pb.hook_register(bank if fa >= 0x4000 else 0, fa, entry, None)
    held, i = None, (v * 17) % len(ph.SCRIPT)
    for _ in range(frames):
        want = ph.SCRIPT[i % len(ph.SCRIPT)]
        i += 1
        if want != held:
            if held:
                gb.release(held)
            if want:
                gb.hold(want)
            held = want
        rp.tick()
        gb.run(1)
        rp.observe()
        gb.write("lives", 3)
        gb.write("served", 0)
        gb.write("story_catches", 0)
        gb.write("quota", 250)
    gb.stop()
    return got


# ---- random crowded states ----------------------------------------------------------------------------------------------------------------
def random_case(rnd, base):
    """A random bar: patrons of every state at every column, lifted ones, flags, budgets. `base`: the fields of any real case (the rest)."""
    f = {n: bytearray(bytes.fromhex(h)) for n, h in base.items()}
    st = [rnd.choice([0, 1, 1, 1, 2, 3, 3, 4]) if rnd.random() < 0.8 else 0 for _ in range(16)]
    bar = [rnd.randrange(4) for _ in range(16)]
    heavy = rnd.randrange(4)
    for s in range(16):
        if rnd.random() < 0.5:
            bar[s] = heavy
    draw, lift = [], []
    for s in range(16):
        col = rnd.choice([rnd.randrange(16), rnd.randrange(3, 9)])
        d = col * 8 + rnd.choice([0, 0, 1, 2, 3, 4, 5, 6, 7])
        if rnd.random() < 0.12:
            d |= 0x80
        draw.append(255 if (st[s] and rnd.random() < 0.06) else d & 0xFF)
        lift.append(rnd.choice([0] * 7 + [1, 1, 2, 0x81, 0x82]))
    roomy = rnd.random() < 0.5                           # room for lifts: few lifted already, few mugs, room on the lines
    lift = [lift[s] if st[s] and (not roomy or rnd.random() < 0.3) else 0 for s in range(16)]
    f["patron_state"][:] = bytes(st)
    f["patron_bar"][:] = bytes(bar)
    f["patron_draw"][:] = bytes(draw)
    f["patron_lift"][:] = bytes(lift)
    f["patron_ovl"][:] = bytes(rnd.choice([0, 0, 0, 1, 2, 3, 4, 5, 6, 7]) for _ in range(16))
    f["patron_dist"][:] = bytes(rnd.choice([0, 0, 0, 0, 1]) for _ in range(16))
    f["patron_hurry"][:] = bytes(rnd.choice([0, 0, 1]) for _ in range(16))
    f["lift_bp"][:] = bytes(rnd.choice([0, 1]) for _ in range(32))
    f["lift_clear"][:] = bytes(rnd.randrange(10) for _ in range(16))
    nl = [sum(1 for s in range(16) if lift[s] and bar[s] == b) for b in range(4)]
    if rnd.random() < 0.85:
        f["lift_n"][:] = bytes(nl)
        f["lift_total"][0] = sum(nl)
    else:
        f["lift_n"][:] = bytes(rnd.randrange(4) for _ in range(4))
        f["lift_total"][0] = rnd.randrange(6)
    f["lift_lifts"][0] = rnd.randrange(256)
    f["ovl_bars"][0] = rnd.randrange(16)
    f["mugs_live"][0] = rnd.randrange(6) if roomy else rnd.choice([rnd.randrange(22), rnd.randrange(8)])
    f["lift_mug_oam"][0] = rnd.randrange(8) if roomy else rnd.randrange(22)
    lists = [[s for s in range(16) if st[s] and bar[s] == b] for b in range(4)]
    for l_ in lists:
        if rnd.random() < 0.5:
            rnd.shuffle(l_)
    f["bar_n"][:] = bytes(len(l_) for l_ in lists)
    f["bar_list"][:] = b"".join(bytes(l_ + [rnd.randrange(16) for _ in range(16 - len(l_))]) for l_ in lists)
    f["lists_ok"][0] = 1
    f["vq_held"][0] = 1 if rnd.random() < (0.05 if roomy else 0.15) else 0
    f["lift:_est_ok"][0] = 1
    f["lift:_ld"][:] = bytes(rnd.randrange(7) if roomy else rnd.choice([rnd.randrange(12), rnd.randrange(6, 11)]) for _ in range(4))
    f["render:_urg_n"][0] = rnd.choice([0, 0, 0, 1, 2])
    f["render:_dirty_x0"][:] = bytes(255 if rnd.random() < 0.6 else rnd.randrange(20) for _ in range(4))
    f["render:_dirty_x1"][:] = bytes(0 if rnd.random() < 0.6 else rnd.randrange(1, 21) for _ in range(4))
    return {"s": "random", "b": heavy if rnd.random() < 0.8 else rnd.randrange(4), "in": {n: bytes(v).hex() for n, v in f.items()}}
