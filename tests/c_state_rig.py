# The timing-independent asm/C check's rig (tests/test_c_state_equiv.py): the same scripted run on build/game.gb (asm) and build/game-c.gb
# (`make cfall`, every asm routine as its C twin), compared on GAME STATE only, at the start of EVERY game step: the RAM that holds the game's
# logic (score, lives, patrons, mugs, bartender, boss, story progress, RNG), never a picture and never a frame count.
#
# How it stays independent of speed. The C ROM is slower: its frames run late, and PyBoy's frame boundary falls at another point of a step
# than the asm ROM's. So neither the input nor the sampling is tied to emulator frames. A hook on the RET of GBDK's joypad() (a PyBoy hook:
# the callback sets register A) answers the game's own update() call of joypad(), the first thing a game step does, with the button mask the
# SCRIPT gives for the current game step (steps counted by main-loop passes), and the same call records the state. Both ROMs see the
# same input at the same game step and are sampled at the same logical point, whatever the speed.
# (Not covered: logic that reads the clock, e.g. DIV or LY. The test ROMs have the DIV seed switch off, tests/conftest.py SEED_BYTE.)
from conftest import ROOT

import os
ASM_ROM = ROOT / "build" / "game.gb"
C_ROM = ROOT / "build" / ("game-c.gb" if not os.environ.get("C_STATE_C_ROM") else os.environ["C_STATE_C_ROM"])   # (a single-twin ROM, build/tw_<X>.gb, to attribute a divergence)

# Names (C globals, by their .noi symbol) and byte counts of the logic state. A name missing from a ROM's symbol table is skipped.
WATCH = {
    # the run
    "game_state": 1, "state_timer": 1, "game_over": 1, "level_clear": 1, "life_lost": 1, "level": 1, "lives": 1, "score": 4, "extra_at": 4,
    "served": 1, "quota": 1, "spawned": 1, "cur_group": 1, "start_mask": 1, "intro_timer": 1, "rng_state": 1,
    "patron_speed": 1, "spawn_interval": 2, "spawn_timer": 2, "tip_timer": 2, "tip_bar": 1, "tip_x": 1,
    # the bartender
    "bar": 1, "bartender_x": 1, "bartender_frac": 1, "facing": 1, "bartender_frame": 1, "catch_pose": 1, "fill_timer": 1, "fill_stage": 1,
    "slide_timer": 1, "walk_timer": 1, "walk_phase": 1, "joy": 1, "joy_prev": 1, "bt_bob": 1, "at_tap": 1, "tap_now": 1,
    # patrons and mugs (MAX_P 16, MAX_M 20)
    "patron_state": 16, "patron_bar": 16, "patron_x": 16, "patron_frac": 16, "patron_variant": 16, "patron_timer": 16, "patron_aux": 16,
    "patron_mug": 16, "patron_hurry": 16, "patron_shove": 16, "patron_stag": 16, "patron_catchx": 16, "patron_drinks": 16, "patron_dist": 16,
    "patron_facing": 16, "patrons_live": 1,
    "mug_state": 20, "mug_bar": 20, "mug_x": 20, "mug_timer": 20, "mug_patron": 20, "mugs_live": 1, "mug_events": 1,
    # bosses
    "boss_on": 1, "boss_id": 1, "boss_bar": 1, "boss_x": 1, "boss_hp": 1, "boss_state": 1, "boss_t": 1, "boss_special_t": 1, "boss_hits": 1,
    "boss_step": 1, "boss_hold": 1, "boss_pose": 1, "boss_push": 1, "boss_returns": 1, "boss_cols": 5,
    # story map and mini-games (names that a ROM lacks are skipped)
    "story_progress": 1, "story_chapter": 1, "story_on": 1, "story_arc": 1, "story_phase": 1, "story_scene": 1, "story_page": 1, "story_swap": 1, "story_typed": 1, "story_timer": 1, "story_step": 1, "story_shift": 1, "story_reached": 1, "story_pts": 2, "smap_stop": 1, "smap_flags": 1, "mg_id": 1, "mg_state": 1, "mg_score": 2,
}
BUTTONS = {"right": 0x01, "left": 0x02, "up": 0x04, "down": 0x08, "a": 0x10, "b": 0x20, "select": 0x40, "start": 0x80}


def mask(held):
    m = 0
    for b in held:
        m |= BUTTONS[b]
    return m


class Twin:
    """The joypad() hook and the per-step sampler of one running Rom. Every Rom made after install() (by a scenario or by another test's
    helper, boss_common.fight and the like) gets one automatically: rom._twin."""

    def __init__(self, rom):
        self.model = getattr(rom, "model_name", "?")
        self.rom = rom
        self.pb = rom.pb
        self.names = [k for k in WATCH if self._has(k)]
        self.addrs = {k: self.rom.addr(k) for k in self.names}
        self.fc_addr = self.rom.addr("frame_counter")
        self.joy_addr = self.rom.addr("joypad")
        self.ret_addr = self.joy_addr + 0x27                 # the RET of GBDK's joypad(): LD A,E ; RET
        assert self.pb.memory[self.ret_addr] == 0xC9 and self.ret_addr < 0x4000, "joypad() is not the GBDK routine this rig knows"
        self.script = None          # fn(step, twin) -> button mask; None: the hook passes the real input through
        self.arm_cond = None        # fn(twin) -> bool, tested at update()'s joypad() call; the script's step 0 is the first call where it is true
        self.arm_pokes = {}
        self.total = 0
        self.last_fc = 0
        self.snaps = {}
        self.pb.hook_register(0, self.ret_addr, self._hook, None)

    def rebind(self):
        """The Rom got another emulator (tests/test_sound.py make_rom swaps it for one with a save image): hook the new one."""
        self.pb = self.rom.pb
        self.pb.hook_register(0, self.ret_addr, self._hook, None)

    def _has(self, name):
        try:
            self.rom.addr(name)
            return True
        except Exception:
            return False

    def stop(self):
        self.rom.stop()

    def mem(self, name):
        return self.pb.memory[self.rom.addr(name)]

    def snapshot(self):
        m = self.pb.memory
        return {k: bytes(m[self.addrs[k]:self.addrs[k] + WATCH[k]]) for k in self.names}

    def _hook(self, _ctx):
        pb = self.pb
        if self.script is None and self.arm_cond is None:
            return
        sp = pb.register_file.SP
        ret = pb.memory[sp] | (pb.memory[sp + 1] << 8)
        if ret >= self.joy_addr:                              # not update(): waitpad() and the like
            return
        if self.arm_cond is not None:
            if not self.arm_cond(self):
                return
            for k, v in self.arm_pokes.items():
                self.rom.write(k, v)
            self.arm_cond = None
            self.total = -1
        self.total += 1                  # one update() call = one pass of the main loop (frame_counter does not move in a pause or a card)
        if self.total not in self.snaps:
            self.snaps[self.total] = self.snapshot()
        m = self.script(self.total, self)
        pb.register_file.A = m & 0xFF
        pb.register_file.E = m & 0xFF

    def arm(self, script, arm_cond, arm_pokes=None):
        """The script starts at update()'s first joypad() call where arm_cond(twin) is true (until then the real input passes through)."""
        self.script, self.arm_cond, self.arm_pokes = script, arm_cond, arm_pokes or {}
        self.snaps = {}
        self.total = 0

    def run_script(self, steps, limit=40000):
        """Run until `steps` game steps of the armed script have been sampled."""
        for _ in range(limit):
            self.rom.run(1)
            if self.arm_cond is None and self.total >= steps:
                break
        else:
            raise AssertionError("%s: %d of %d steps in %d frames (armed: %s)" % (self.model, self.total, steps, limit, self.arm_cond is None))
        self.script = None
        return self.snaps


STORY, STORY_MAP = 11, 9      # game_state GS_STORY, story_phase SP_MAP (src/game.h STORY_PHASE_MAP)


def map_entry(run):
    """The first step at which the story map is active (None: never)."""
    for s in sorted(run["snaps"]):
        sn = run["snaps"][s]
        if sn.get("game_state") == bytes([STORY]) and sn.get("story_phase") == bytes([STORY_MAP]):
            return s
    return None


def first_divergence(a, c):
    """The first game step at which two runs' states differ: (step, [(name, asm bytes, C bytes)]), or None. a, c: {"names", "snaps"} (a worker's output).
    The comparison ends at the story map's first step: the map's walk adapts its pace to how many cells the loader manages a frame (src/smap.c, V_RATE),
    so the map's state depends on speed by design (the story map's own tests measure that pace)."""
    names = [n for n in a["names"] if n in c["names"]]
    ends = [e for e in (map_entry(a), map_entry(c)) if e is not None]
    last = min(ends) if ends and not os.environ.get("C_STATE_MAP") else None
    for s in sorted(set(a["snaps"]) & set(c["snaps"])):
        if last is not None and s > last:
            break
        diff = [(n, a["snaps"][s][n], c["snaps"][s][n]) for n in names if a["snaps"][s][n] != c["snaps"][s][n]]
        if diff:
            return s, diff
    return None


def describe(div):
    if div is None:
        return "no divergence"
    s, diff = div
    return "game step %d: %s" % (s, "; ".join("%s asm %s C %s" % (n, x.hex(), y.hex()) for n, x, y in diff[:8]))


# ---- every Rom made while installed (by this rig or by another test's helper) gets a Twin, and the spec in ARM_NEXT armed at once ----
ARM_NEXT = []        # [(script, arm_cond, arm_pokes)]: armed on the next Rom made (before its first frame)
TWINS = []           # the Twins made, in order


def _set_pb(rom, v):
    rom.__dict__["_pb"] = v
    tw = rom.__dict__.get("_twin")
    if tw is not None and v is not None and tw.pb is not v:
        tw.rebind()


def install():
    import gbtools.rom as gr
    if getattr(gr.Rom, "_c_state_installed", False):
        return
    orig = gr.Rom.__init__

    def init(self, *a, **k):
        orig(self, *a, **k)
        self._twin = Twin(self)
        TWINS.append(self._twin)
        if ARM_NEXT:
            self._twin.arm(*ARM_NEXT.pop(0))
    gr.Rom.__init__ = init
    gr.Rom.pb = property(lambda self: self.__dict__.get("_pb"), lambda self, v: _set_pb(self, v))
    gr.Rom._c_state_installed = True
