"""Driver for the glitch hunt (tests/glitch_lib.py): a seeded stream of the game's own events on a venue, every frame watched.

Events (the pokes land between two whole game frames, logic_paused): a served mug (a full mug thrown into a patron: push back, serve), a tip and
the show that follows it (and its end), a clump (patrons put on top of each other: lifts and drops), a pause and resume, the game's own spawns
and exits. The game plays itself otherwise (the bartender idle: lives are topped up so patrons reaching the tap do not end the run)."""
import contextlib
import random

from gbtools import Rom
from conftest import ROM, logic_paused, double_speed, title_level
from glitch_lib import Watch
from test_lift import boot_play
from test_patrons import FULL, MAX_P, set_patron, inject_mug, put, clear_patrons
from test_tips import w16
from test_art import goto_group

PAUSED = 5
PLAYING = 1


def boot(model, group=0, seed=0, ds=True, dirs=0):
    """A game in play on venue `group`, at double speed on a Color (the shipped mode), with junk in the bytes the game keeps in WRAM and HRAM.
    dirs: the bars' directions (bit b: bar b is R, mirrored: the CLASSIC levels' patrons from the right)."""
    cm = double_speed() if ds and model == "cgb" else contextlib.nullcontext()
    with cm:
        gb = Rom(ROM, model)
    gb.__enter__()
    gb.model_name = model
    gb.run(120)
    gb.write("sa_hold", 1)
    junk(gb, seed)
    if dirs:
        gb.write("level_dirs", dirs)
    title_level(gb, group + 1)
    for _ in range(80):
        if gb.mem("game_state") == PLAYING:
            break
        gb.run(1)
    assert gb.mem("game_state") == PLAYING and gb.mem("bar_dirs") == dirs, (gb.mem("game_state"), gb.mem("bar_dirs"))
    gb.run(2)
    gb.write("tip_chance", 0)
    gb.write("intro_timer", 0)
    gb.write("quota", 200)
    w16(gb, "spawn_interval", 20)
    return gb


def junk(gb, seed):
    """PyBoy zeroes RAM that real hardware leaves as junk: poke junk over the shadow rows and the dirty-span bytes the game has not yet set."""
    r = random.Random(seed * 7919 + 1)
    for name, n in (("sh_rows", 2 * 8 * 32),):
        a = gb.addr(name)
        for i in range(n):
            gb.pb.memory[a + i] = r.randrange(256)


class Soak:
    def __init__(self, gb, seed=0, events=("serve", "tip", "clump", "pause"), watch=None):
        self.gb, self.rng, self.w = gb, random.Random(seed), watch or Watch(gb)
        self.events = events
        self.log = []

    def topup(self):
        self.gb.write("lives", 9)

    def event(self, kind):
        gb, rng = self.gb, self.rng
        self.log.append((self.w.frame, kind))
        if kind == "serve":
            b = rng.randrange(4)
            with logic_paused(gb):
                inject_mug(gb, b, rng.choice([40, 64, 80, 100, 120]))
        elif kind == "tip":
            with logic_paused(gb):
                gb.write("tip_bar", gb.mem("bar"))
                gb.write("tip_x", gb.mem("bartender_x") + 4)
                w16(gb, "tip_timer", 200)
        elif kind == "endshow":
            with logic_paused(gb):
                if gb.mem16("show_timer"):
                    w16(gb, "show_timer", 1)
        elif kind == "clump":
            b = rng.randrange(4)
            x = rng.choice([16, 24, 40])
            with logic_paused(gb):
                for dx in (0, 32, 64):          # (the game's own spacing: they overlap only when a push drives one through the next)
                    st, bar, px = gb.read("patron_state", MAX_P), gb.read("patron_bar", MAX_P), gb.read("patron_x", MAX_P)
                    free = all(abs(px[q] - (x + dx)) >= 32 for q in range(MAX_P) if st[q] and bar[q] == b)
                    if free and gb.mem("patrons_live") < MAX_P - 1:
                        set_patron(gb, b, x + dx, variant=rng.randrange(3))
        elif kind == "pause":
            gb.press("start", 2)
            self.w.step(rng.randrange(3, 40))
            gb.press("start", 2)

    def run(self, frames):
        done = 0
        while done < frames:
            n = self.rng.randrange(8, 60)
            self.w.step(n)
            done += n
            self.topup()
            self.event(self.rng.choice(self.events))
            if self.rng.random() < 0.3:
                self.event("endshow")
        return self.w
