# Shared fixtures. GB_ROM overrides the ROM path; GB_UPDATE_GOLDEN=1 rewrites goldens.
import os
from pathlib import Path

import pytest
from gbtools import Rom

ROOT = Path(__file__).resolve().parent.parent
ROM = Path(os.environ.get("GB_ROM", ROOT / "build" / "game.gb"))
GOLDEN = ROOT / "tests" / "golden"
UPDATE = os.environ.get("GB_UPDATE_GOLDEN") == "1"
GOLDEN_REPORT = os.environ.get("GB_GOLDEN_REPORT")   # a file: a golden that differs is listed there (name, model, the differing bounding box) and the test goes on; nothing under tests/golden is written


# ---- Color double speed (src/main_cold.c boot_init): the shipped ROM switches a Color to double speed at boot, unless its byte 0x3FFE is 0.
# Every existing test was written (and every golden taken) at normal speed, so each PyBoy the tests make loads a copy of the ROM with that
# byte patched to 0 (a ROM that is not this game, or without the byte, is untouched; a DMG never reads it). tests/test_double_speed.py
# runs the ROM as built: `with double_speed(): Rom(...)`, or GB_DOUBLE_SPEED=1 for the whole run (then the old tests are not expected to pass).
from io import BytesIO
import contextlib
import hashlib
import pyboy as _pyboy_mod
import gbtools.rom as _gbtools_rom

SPEED_BYTE = 0x3FFE
SEED_BYTE = 0x3FFD       # free ROM0 padding too, 0xFF as built: the DIV counter is mixed into the random generator only while it is non-zero (src/title.c rng_mix, src/mirror.c spawn_variant).
                         # Every test ROM has it 0 (a DMG too, double speed or not): the fixed seeds stay reproducible. tests/test_rng.py runs `with seeding():`.
_SEEDING = [False]


@contextlib.contextmanager
def seeding():
    """Inside the block a PyBoy made keeps the ROM's seed byte (the DIV mixing of the shipped game)."""
    old, _SEEDING[0] = _SEEDING[0], True
    try:
        yield
    finally:
        _SEEDING[0] = old
_DS = [bool(os.environ.get("GB_DOUBLE_SPEED"))]
_patched_cache = {}


@contextlib.contextmanager
def double_speed():
    """Inside the block a PyBoy made loads the ROM as built (double speed on a Color)."""
    old, _DS[0] = _DS[0], True
    try:
        yield
    finally:
        _DS[0] = old


# ---- Owner Q92 (2026-11-01, "A"): the Color ([cgb]) speed checks run at double speed, the way the game ships.
# These are the perf / timing guards (missed and late frames, end lines, VBlank drain budgets): every [cgb] instance of them runs the ROM as built.
# They measure the line the frame's LOGIC ended on at double speed (perf_helpers.end_line: the music tick waits for a fixed line there, so the end
# line only shows that line). Everything else (screens, goldens, mechanics) stays at normal speed (the patch above). The DMG is untouched.
# module -> the tests (None: every test of the module).
PERF_DS = {
    "test_perf": None, "test_perf_arcade": None, "test_perf_saloon": None,
    "test_boss_in_place": {"test_a_boss_fight_s_frames_end_no_later_than_at_579e173", "test_a_boss_fight_with_regulars_is_late_on_hardly_any_frame",
                           "test_a_boss_entrance_has_no_late_frame_but_dukes_hand_over"},
    "test_debug_stress": {"test_the_crowd_stays_at_its_target_with_an_idle_player"},
    "test_extra_looks": {"test_the_factory_looks_mirror_pixel_for_pixel_on_an_r_level"},
    "test_extra_looks_zoo_space": {"test_the_looks_mirror_pixel_for_pixel_on_an_r_level"},
    "test_flow": {"test_submenu_redraws_stay_within_the_vblank_drain_budget"},
    "test_half_rate": {"test_the_heaviest_levels_run_at_60_game_steps_a_second_and_keep_the_budgets"},
    "test_menu_scroll": {"test_mashing_a_list_never_runs_a_frame_late", "test_mashing_the_soundtrack_while_a_tune_plays_never_runs_a_frame_late"},
    "test_mg_logroll": {"test_a_whole_game_has_no_late_frame_and_no_copy_into_the_picture"},
    "test_mg_logroll_fish": {"test_the_fish_cost_no_late_frame_and_few_lines"},
    "test_patrons": {"test_four_patrons_stepping_together_fit_in_vblank"},
    "test_pouroff": {"test_a_frame_of_the_game_ends_before_the_next_vblank"},
    "test_practice_art": {"test_fast_left_right_never_runs_a_frame_late_and_settles"},
    "test_sound": {"test_no_frame_is_skipped_with_music_and_effects_running"},
    "test_stage_anim": {"test_the_stage_animates_only_its_own_tiles"},
    "test_story_pictures": {"test_finale_streams_each_speakers_portrait_into_the_one_slot", "test_the_pieces_fly_off_the_screen_and_the_trail_fades",
                            "test_mashing_a_through_the_burst_keeps_the_line_limit", "test_mashing_a_never_makes_the_drain_leave_vblank"},
    "test_taper": {"test_a_slanted_r_bar_is_the_slanted_l_bar_mirrored"},      # (the Space Lounge's level 10: at normal speed its R run lags the L run by frames, as the Factory's)
    "test_twists": {"test_a_mosh_on_all_four_bars_keeps_the_sprite_budgets", "test_a_mosh_on_two_bars_keeps_the_frame_time"},
    "test_vq_budget": {"test_classic_crowd_drains_inside_vblank"},
}
# In those modules, but kept at normal speed (their assertion is about a phase or a mechanic at normal speed, not a limit): module -> {test: why}.
PERF_NORMAL = {
    "test_sound": {"test_no_frame_is_skipped_with_music_and_effects_running": "reads frame_counter after run(1) from a state poked between frames: at double speed the first emulator frame has no counter step (a phase, frame 0 only); test_double_speed (c) checks a game frame per emulator frame at double speed"},
    "test_perf": {"test_vram_queue_is_drained_only_inside_vblank": "pokes vq_latest_ly and counts frames from the poke: at double speed the poked list forms one frame later (the shipped game still never writes outside VBlank: diagnosed, same refusals, same drain)"},
}


def pytest_collection_modifyitems(config, items):
    """PERF_ONLY=1: keep only the perf / timing guards of PERF_DS (a quick run of just the Color speed checks)."""
    if os.environ.get("PERF_ONLY"):
        keep = [i for i in items if i.module.__name__ in PERF_DS and (PERF_DS[i.module.__name__] is None or i.function.__name__ in PERF_DS[i.module.__name__])]
        config.hook.pytest_deselected(items=[i for i in items if i not in keep])
        items[:] = keep


@pytest.fixture(autouse=True)
def _perf_guards_at_double_speed(request):
    mod = request.module.__name__.split(".")[-1]
    names = PERF_DS.get(mod, ())
    fn = getattr(request.function, "__name__", None) if request.scope == "function" else None
    cs = getattr(request.node, "callspec", None)
    cgb = cs is None or "cgb" in cs.id.split("-")   # (a test without a model parameter builds its own Color: they are listed only when they do)
    if fn and cgb and not os.environ.get("GB_PERF_NORMAL") and mod in PERF_DS and (names is None or fn in names) and fn not in PERF_NORMAL.get(mod, {}):
        with double_speed():
            yield
    else:
        yield


def ds_active():
    """True inside `double_speed()` (or with GB_DOUBLE_SPEED=1): a Color built now runs at double speed."""
    return _DS[0]


def _speed_off_copy(path):
    """The ROM at `path` with its speed-switch byte 0 (unless double_speed()) and its seed byte 0 (unless seeding()): a temp copy under out/dsoff/, or `path` itself when it is not this game's ROM."""
    key = str(path)
    st = os.stat(key)
    ck = (key, st.st_mtime_ns, st.st_size, _DS[0], _SEEDING[0])
    if ck in _patched_cache:
        return _patched_cache[ck]
    data = Path(key).read_bytes()
    out = key
    if len(data) > SPEED_BYTE and data[0x134:0x13D] == b"SPIGOTEER":
        b = bytearray(data)
        if not _DS[0] and b[SPEED_BYTE] == 0xFF:
            b[SPEED_BYTE] = 0
        if not _SEEDING[0] and b[SEED_BYTE] == 0xFF:
            b[SEED_BYTE] = 0
        if bytes(b) != data:
            d = ROOT / "out" / "dsoff"
            d.mkdir(parents=True, exist_ok=True)
            p = d / (hashlib.sha1(bytes(b)).hexdigest()[:16] + ".gb")
            if not p.is_file():
                tmp = d / f".{os.getpid()}.{p.name}"
                tmp.write_bytes(bytes(b))
                os.replace(tmp, p)
            out = str(p)
    _patched_cache[ck] = out
    return out


# ---- a Game Boy Advance (SETTINGS > SCREEN, src/bright.h): a GBA runs the cartridge in Color mode and hands it B = 1 (GBDK: _is_GBA, bit 0), a plain Color B = 0.
# PyBoy's boot ROM leaves B = 0, so a hook on the cartridge's entry point (0x0100: nothing has run yet) sets B = 1. `with gba_hardware(): Rom(...)` makes every
# PyBoy built inside the block a GBA; GB_GBA=1 does it for a whole run (then the goldens, which are the Color's, are expected to differ).
# A GBA with nothing saved asks for its SCREEN choice at the title (title.c TM_SCR). `gba_hardware(True, choice=2)` also puts that choice in the cartridge RAM
# ("SC" block at 0x30: 1 NORMAL, 2 BRIGHT; an image that already holds a block keeps its own), so the run starts as a GBA that has chosen: no prompt.
_GBA = [bool(os.environ.get("GB_GBA"))]
_SC = [int(os.environ.get("GB_GBA_SC", "0")) or None]


@contextlib.contextmanager
def gba_hardware(on=True, choice=None):
    old, _GBA[0] = _GBA[0], on
    old_sc, _SC[0] = _SC[0], choice
    try:
        yield
    finally:
        _GBA[0], _SC[0] = old, old_sc


def _with_choice(ram, choice):
    r = bytearray(ram) if ram is not None else bytearray(0x2000)
    if bytes(r[0x30:0x32]) != b"SC":
        r[0x30:0x35] = bytes([ord("S"), ord("C"), choice, (0x5A + 0x53 + 0x43 + choice) & 255, ~(0x5A + 0x53 + 0x43 + choice) & 255])
    return bytes(r)


class _PyBoy(_pyboy_mod.PyBoy):
    def __init__(self, gamerom, *a, **kw):
        if isinstance(gamerom, (str, os.PathLike)) and Path(gamerom).suffix in (".gb", ".gbc"):
            gamerom = _speed_off_copy(gamerom)
        if _GBA[0] and _SC[0]:
            rf = kw.get("ram_file")
            kw["ram_file"] = BytesIO(_with_choice(rf.getvalue() if rf is not None else None, _SC[0]))
        super().__init__(gamerom, *a, **kw)
        if _GBA[0]:
            rf = self.register_file
            self.hook_register(0, 0x0100, lambda ctx: setattr(rf, "B", 1), None)


_pyboy_mod.PyBoy = _PyBoy
_gbtools_rom.PyBoy = _PyBoy


def golden_report(name, model, actual):
    """GB_GOLDEN_REPORT: one line per differing golden: its name, the model and the bounding box of the difference."""
    from PIL import Image, ImageChops
    ref = Image.open(GOLDEN / f"{name}.{model}.png").convert("RGB")
    box = ImageChops.difference(ref, actual.convert("RGB")).getbbox() if ref.size == actual.size else "size"
    with open(GOLDEN_REPORT, "a") as f:
        f.write(f"{name}.{model} {box}\n")
    new = Path(GOLDEN_REPORT).parent / "golden_new"                  # the picture the game drew now, for the old | new sheets (never under tests/golden)
    new.mkdir(exist_ok=True)
    actual.convert("RGB").save(new / f"{name}.{model}.png")


# ---- test hook: the game rebuilds its per-bar patron lists only when a patron arrives or leaves (M8a perf).
# A test that writes patron_state or patron_bar between frames changes that membership behind the game's back,
# so it must set `lists_dirty`; the next frame then rebuilds the lists. Every write through Rom.write (so every
# helper in every test file, perf_helpers included) is checked here and sets the hook when it touches those two
# arrays: no helper can forget it.
LIST_FIELDS = ("patron_state", "patron_bar")
MAX_PATRONS = 16
_rom_write = Rom.write


def mark_lists_dirty(gb):
    """Tell the game the patron lists must be rebuilt (after poking patron_state / patron_bar). PyBoy's frame ends a
    few lines after the game's logic has begun (it starts in VBlank), so a poke can land in the middle of a frame's
    logic, after main.c has looked at lists_dirty: lists_ok is cleared too, so the rest of that frame already
    rebuilds them (every user checks lists_ok first). Otherwise a patron poked in then is composed from the old lists
    (not drawn) on whichever frame the code layout puts it."""
    _rom_write(gb, "lists_dirty", 1)
    _rom_write(gb, "lists_ok", 0)


def clear_regulars(gb):
    """Every regular off the bars (a boss fight ends only when none is left: src/boss.c boss_frame): the tests that
    want the outro now call this after the meter is empty."""
    for i in range(MAX_PATRONS):
        gb.write(gb.addr("patron_state") + i, 0)
    gb.write("patrons_live", 0)


GS_PAUSED = 5

# ---- the HOW TO PLAY cards (src/mg_card.c): the first play of a game shows its full card and waits for A. Almost every mini-game test is about
# the game, not the card, so the cartridge images the tests build (test_sound.new_pyboy, the release list's) already hold the bonus block "MGB1"
# (src/save.c, SRAM 0x70) with every card seen; tests/test_mg_card.py asks for a fresh one (seen=0).
BX_AT = 0x70


def bx_block(reached=0, medals=0, seen=0xFFFF):
    """The save's "MGB1" block: played-bonus bits, medals (2 bits a round), cards seen (16 bits), checksum and complement."""
    b = bytearray(b"MGB1" + bytes([reached, medals]) + seen.to_bytes(2, "little"))
    c = (0x5A + sum(b)) & 255
    return bytes(b + bytes([c, c ^ 255]))


BK_AT = 0x28


def bk_block(seen=0x3FF):
    """The save's "BK" block (src/save.c): the boss cards seen, bit v = venue v's boss (the first time a boss appears the game opens his card)."""
    b = bytearray(b"BK" + seen.to_bytes(2, "little"))
    c = (0x5A + sum(b)) & 255
    return bytes(b + bytes([c, c ^ 255]))


def with_cards(ram=None, seen=0xFFFF):
    """A cartridge image (None: blank) with the bonus block in it, unless the image already carries one; and the boss cards block "BK"
    (every boss card seen: seen=0 leaves them all unseen), unless the image already carries one."""
    r = bytearray(ram) if ram is not None else bytearray(0x2000)
    if bytes(r[BX_AT:BX_AT + 4]) != b"MGB1":
        r[BX_AT:BX_AT + 10] = bx_block(seen=seen)
    if bytes(r[BK_AT:BK_AT + 2]) != b"BK":
        r[BK_AT:BK_AT + 6] = bk_block(0x3FF if seen else 0)
    return bytes(r)


class logic_paused:
    """`with logic_paused(gb): ...` pokes made inside land between two whole game frames: the game runs one frame
    paused first (update_patrons and the rest of the play logic skip it), so the pokes cannot fall halfway through a
    frame's patron loop (PyBoy's frame ends a few lines after the game's logic has begun: see mark_lists_dirty); the
    next frame plays them all. For a test whose patrons must all start on the same game frame."""
    def __init__(self, gb):
        self.gb = gb

    def __enter__(self):
        self.st = self.gb.mem("game_state")
        self.gb.write("game_state", GS_PAUSED)
        self.gb.run(1)
        return self.gb

    def __exit__(self, *exc):
        self.gb.write("game_state", self.st)
        return False


def _list_ranges(gb):
    r = gb.__dict__.get("_list_ranges")
    if r is None:
        r = []
        for name in LIST_FIELDS:
            try:
                a = gb.addr(name)
            except KeyError:                    # a ROM without the hook (not this game)
                continue
            r.append((a, a + MAX_PATRONS))
        gb._list_ranges = r
    return r


def _write(gb, ref, value):
    _rom_write(gb, ref, value)
    a = gb.addr(ref)
    if any(lo <= a < hi for lo, hi in _list_ranges(gb)):
        mark_lists_dirty(gb)


Rom.write = _write


# ---- the scene transition (src/trans.c): a fizzy drink fills the screen at a wired scene change and drains again, ~0.8 s of frames the
# older tests' fixed waits do not expect. Every Rom the tests make has it off (HRAM 0xFFF1 bit 7, set after the game's first frame: main()
# clears the flags at start-up); tests/test_trans.py turns it on with trans_enable and tests it.
TRANS_ADDR, TR_OFF = 0xFFF1, 0x80
_rom_run = Rom.run


def _run(self, frames=1, render=False):
    if not getattr(self, "_trans_managed", False):
        self._trans_managed = True
        while frames > 0:                       # (main() clears TRANS once the game's first frame has run: frame_counter is 1 by then)
            _rom_run(self, 1, render and frames == 1)
            frames -= 1
            if self.mem("frame_counter") >= 1:
                break
        self.pb.memory[TRANS_ADDR] = TR_OFF if self.mem("frame_counter") >= 1 else 0
        if frames <= 0:
            self._trans_managed = self.mem("frame_counter") >= 1
            return
    _rom_run(self, frames, render)


Rom.run = _run


def trans_enable(gb, on=True):
    """Transitions on (default) or off for this Rom, whatever the first run did."""
    gb._trans_managed = True
    gb.pb.memory[TRANS_ADDR] = gb.pb.memory[TRANS_ADDR] & ~TR_OFF if on else gb.pb.memory[TRANS_ADDR] | TR_OFF


PLAYING = 1
OLD_INTRO_LEFT = 44    # intro_timer the M1-M3 fixture had after 120 frames; kept so old tests see the same timing


@pytest.fixture(params=["dmg", "cgb"])
def boot(request):
    """A booted ROM sitting on the title screen, once per hardware model."""
    with Rom(ROM, request.param) as rom:
        rom.run(120)
        rom.model_name = request.param
        hold_stage_anim(rom)
        yield rom


def hold_stage_anim(rom, hold=1):
    """Freeze the stage animation (src/venue.c sa_hold): every level then keeps its stage's own tiles (frame 0), so
    goldens and tile checks do not depend on the animation's timing. tests/test_stage_anim.py turns it back on."""
    rom.write("sa_hold", hold)


# ---- the title menu (src/title.c): the top level PLAY / BONUS / SETTINGS, each opening a submenu in the same place:
# PLAY [CONTINUE] / STORY / ARCADE / CLASSIC, BONUS SOUNDTRACK / MINI GAMES / BOSS RUSH, SETTINGS MUSIC. K_* / TM_*: src/game.h.
(K_ARCADE, K_STORY, K_MUSIC, K_CONTINUE, K_BONUS, K_PLAY, K_SETTINGS, K_SOUNDTRACK, K_CLASSIC, K_MINIGAMES, K_BOSSRUSH,
 K_ERASE, K_DEBUG, K_ERASEQ, K_NO, K_YES, K_BARCHANGE, K_BARKEEP, K_CREDITS, K_EASY, K_NORMAL, K_HARD, K_CAP_EASY, K_CAP_NORMAL, K_CAP_HARD,
 K_SCR_NORMAL, K_SCR_BRIGHT, K_SCR, K_SET_STD, K_SET_GBA) = range(30)
TM_TOP, TM_PLAY, TM_BONUS, TM_SETTINGS, TM_ERASE, TM_HARD, TM_SCR = range(7)
MENU_SETTLE = 6          # frames for a submenu's lines to reach the screen (2-5: src/title.c menu_frame)
SETTINGS_SETTLE = 8      # ... and the rest of SETTINGS' (up to ten rows, one a frame on a Color), waited by title_pick when it opens SETTINGS


def menu_items(rom):
    return list(rom.read("title_items", rom.mem("title_n")))


def menu_tap(rom, b):
    rom.press(b, 2)
    rom.run(1)                                # (the release must be seen before the next press)


def menu_to(rom, k):
    """Move the title's cursor down to item k of the menu shown."""
    items = menu_items(rom)
    assert k in items, (k, items)
    key = "right" if rom.mem("title_menu") == TM_SETTINGS else "down"      # (SETTINGS shows one setting at a time: LEFT / RIGHT browse)
    while items[rom.mem("title_sel")] != k:
        menu_tap(rom, key)


def title_pick(rom, top, item=None, press=True):
    """From the title's top level: open top item `top` (K_PLAY / K_BONUS / K_SETTINGS); then with `item`, move to it
    and (press) choose it with A."""
    assert rom.mem("title_menu") == TM_TOP
    menu_to(rom, top)
    menu_tap(rom, "a")
    if top == K_SETTINGS:
        rom.run(SETTINGS_SETTLE)
    if item is not None:
        menu_to(rom, item)
        if press:
            menu_tap(rom, "a")
            if item == K_STORY:                   # a new story asks HOW HARD (2026-10-16): the cursor starts on NORMAL, A takes it
                assert rom.mem("title_menu") == TM_HARD
                menu_tap(rom, "a")
                if rom.mem("title_menu") == TM_HARD and rom.mem("game_state") == 0:   # (a 2-frame tap can fall inside a long pass of the title and not be read: once more)
                    menu_tap(rom, "a")


def title_arcade(rom):
    """From the title's top level: PLAY > ARCADE (the game starts on the next frames)."""
    title_pick(rom, K_PLAY, K_ARCADE)


def title_level(rom, lv=1):
    """From the title's top level: the LEVEL harness (MODE_LEVEL: the old 10-level rotation, its loops and bonus rounds
    after even levels) from level lv. The title's test hook `title_go` starts it; the keys and frames are exactly those
    PLAY > ARCADE took when it started this rotation, so every gameplay test and golden starts on the same frame."""
    title_pick(rom, K_PLAY, K_ARCADE, press=False)
    rom.write("title_go", lv)
    menu_tap(rom, "a")                        # (the hook is taken first: A on the menu line does nothing)


@pytest.fixture
def gb(boot):
    """Gameplay: boot, the LEVEL harness at level 1, then run until the intro delay is where the M1-M3 tests expect it."""
    title_level(boot)
    for _ in range(30):
        if boot.mem("game_state") == PLAYING:
            break
        boot.run(1)
    assert boot.mem("game_state") == PLAYING
    boot.write("tip_chance", 0)      # tips are M5; the M1-M4 tests and goldens must not see a coin (test_tips sets it)
    while boot.mem("intro_timer") > OLD_INTRO_LEFT:
        boot.run(1)
    return boot


def without_water(img):
    """The screen's bytes with the town pictures' jet cells blacked out. The fountain flows (src/story.c story_water, owner Q74 2026-11-04):
    the jet cells' tiles change every 8 frames, so two runs that bring a picture up at different times show the jets in different phases.
    (tests/test_story_pictures.py checks the water itself.)"""
    import json
    from PIL import ImageDraw
    im = img.convert("RGB").copy()
    d = ImageDraw.Draw(im)
    for cx, cy in json.loads((ROOT / "build" / "story.json").read_text())["water_cells"]:
        d.rectangle((cx * 8, cy * 8, cx * 8 + 7, cy * 8 + 7), fill=(0, 0, 0))
    return im.tobytes()


def check_golden(gb, name):
    """Compare the screen with tests/golden/<name>.<model>.png; diffs land in out/diff/."""
    ok = gb.golden(GOLDEN / f"{name}.{gb.model_name}.png", update=UPDATE, diff_dir=ROOT / "out" / "diff")
    if not ok and GOLDEN_REPORT:
        from PIL import Image
        golden_report(name, gb.model_name, Image.open(ROOT / "out" / "diff" / f"{name}.{gb.model_name}.actual.png"))
        return
    assert ok, f"screen differs from golden {name}.{gb.model_name}.png (see out/diff/). Intentional? GB_UPDATE_GOLDEN=1 make test"


# ---- game frames, not emulator frames (asm pass, PLAN.md 6.2) -----------------------------------------------------------------------
# A golden shot after `gb.run(n)` or after `until(cond)` polling once per EMULATOR frame lands on a different GAME frame when the game
# gets faster or slower: a game frame that straddled the VBlank (the logic ran into the next one) no longer does, and the shot is one
# game frame later. These helpers count GAME frames instead: a hook on vq_frame_end (called once at the end of every game frame's
# logic) and one on the VBlank vector. The picture of a game frame is the one on screen once its copy list has been drained and shown:
# the emulator frame that ends after the second VBlank following the frame-end hook (the first VBlank drains the list, the picture
# drawn after it is complete at the second). The shot is taken then, so the game is 1-3 game frames further on when it is taken
# (it is never wound back: PyBoy's save_state / load_state does not restore everything, a shot after a rewind differs).
#
#   until_game(gb, cond)          cond() is evaluated at the end of each game frame's logic (the hook), so it is the first game frame
#                                 for which it holds, whatever the speed. Returns that frame's index (the clock's `frames`).
#   game_frames(gb, n)            n more game frames after the last until_game / game_frames (not after the current emulator frame).
#   check_golden_game(gb, name)   check_golden on the picture of the current game frame (runs on until it is shown).
#                  wait=False     only arms the shot: it is taken inside the next until_game / game_frames loop that gets there, so a
#                                 test can go on counting frames; finish_goldens(gb) at the end asserts none is left.
#
# Phase probing (tools/golden_phase.py): the classifier runs the tests three times with GB_PHASE_PROBE=<dir> and GB_PHASE_SHIFT=0, -1, +1.
# check_golden_game then shoots the game frame that many frames earlier / later (+1: one more game frame before the shot; -1: the
# game_frames advance just before the shot is one shorter, the next advance one longer; not possible after an until_game) and writes
# <dir>/<name>.<model>.0|m1|p1.png instead of asserting. A picture is never taken from a ticking sequence the test did not have: only
# the emulator frame that shows the game frame is rendered (rendering every frame changes what some scenes draw).
class GameClock:
    def __init__(self, gb):
        self.gb, self.frames, self.vb, self.anchor, self.cond, self.hit = gb, 0, 0, None, None, None
        self.vb_at = {0: 0}                                 # game frame -> the VBlank count (self.vb, only ever grows) at its end hook
        self.deficit = 0                                    # PHASE_SHIFT -1: game frames the last game_frames left out (made up by the next)
        self.na = False                                     # the last advance was an until_game: a -1 shot is not possible
        self.armed = []                                     # (name, game frame) shots waiting for their picture
        a = gb.addr("vq_frame_end")
        gb.pb.hook_register(a >> 16, a & 0xFFFF, self._frame, None)
        gb.pb.hook_register(0, 0x0040, self._vbl, None)

    def _frame(self, _):
        self.frames += 1
        self.vb_at[self.frames] = self.vb
        self.vb_at.pop(self.frames - 12, None)
        if self.cond is not None and self.hit is None and self.cond():
            self.hit = self.frames

    def _vbl(self, _):
        self.vb += 1

    def tick(self, each=None):
        """One emulator frame, rendered only if it is the one that shows an armed shot's game frame (the frame whose second VBlank
        after its end hook arrives in it); the armed shots that became due are checked."""
        want = any(f in self.vb_at and self.vb - self.vb_at[f] == 1 for _, f in self.armed)
        self.gb.run(1, render=want)
        if each:
            each(self.gb)
        due = [x for x in self.armed if x[1] in self.vb_at and self.vb - self.vb_at[x[1]] >= 2]
        if due:
            img = self.gb.pb.screen.image.convert("RGB").copy()
            for x in due:
                self.armed.remove(x)
                self._finish(x[0], img)

    def _finish(self, name, im):
        gb = self.gb
        if PHASE_PROBE:
            d = Path(PHASE_PROBE)
            d.mkdir(parents=True, exist_ok=True)
            tag = {0: "0", -1: "m1", 1: "p1"}[PHASE_SHIFT]
            im.save(d / f"{name}.{gb.model_name}.{tag}.png")
            return
        from PIL import Image, ImageChops
        path = GOLDEN / f"{name}.{gb.model_name}.png"
        if UPDATE or not path.is_file():
            im.save(path)
            return
        ref = Image.open(path).convert("RGB")
        ok = ref.size == im.size and ImageChops.difference(ref, im).getbbox() is None
        if not ok:
            d = ROOT / "out" / "diff"
            d.mkdir(parents=True, exist_ok=True)
            im.save(d / f"{path.stem}.actual.png")
            if ref.size == im.size:
                ImageChops.difference(ref, im).point(lambda v: 255 if v else 0).save(d / f"{path.stem}.diff.png")
            if GOLDEN_REPORT:
                golden_report(name, gb.model_name, im)
                return
        assert ok, f"screen differs from golden {name}.{gb.model_name}.png (see out/diff/). Intentional? GB_UPDATE_GOLDEN=1 make test"


PHASE_PROBE = os.environ.get("GB_PHASE_PROBE")
PHASE_SHIFT = int(os.environ.get("GB_PHASE_SHIFT", "0")) if PHASE_PROBE else 0


def game_clock(gb):
    if not hasattr(gb, "_game_clock"):
        gb._game_clock = GameClock(gb)
        gb._game_clock.anchor = gb._game_clock.frames
    return gb._game_clock


def until_game(gb, cond, limit=400, each=None):
    """Run until cond() holds at the end of a game frame's logic (checked first, now). `each(gb)` after every emulator frame."""
    c = game_clock(gb)
    c.na, c.deficit = True, 0
    if cond():
        return c.anchor
    c.cond, c.hit, start = cond, None, c.frames
    try:
        while c.hit is None:
            assert c.frames - start <= limit, "condition not reached in %d game frames" % limit
            c.tick(each)
    finally:
        c.cond = None
    c.anchor = c.hit
    return c.hit


def game_frames(gb, n, each=None):
    """Advance to n game frames after the last until_game / game_frames."""
    c = game_clock(gb)
    if c.anchor is None or c.anchor > c.frames:
        c.anchor = c.frames
    eff = n + c.deficit
    c.deficit, c.na = 0, False
    if PHASE_SHIFT < 0:                                      # (probing one game frame earlier: the next advance makes it up)
        eff, c.deficit = eff - 1, 1
    c.anchor += max(eff, 0)
    while c.frames < c.anchor:
        c.tick(each)
    return c.anchor


def check_golden_game(gb, name, wait=True):
    """check_golden on the picture of the current game frame (where game_frames / until_game stopped)."""
    c = game_clock(gb)
    if PHASE_SHIFT < 0 and c.na:
        d = Path(PHASE_PROBE)
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{name}.{gb.model_name}.m1.na").write_text("the golden follows an until_game: one game frame earlier is not possible")
        return
    if PHASE_SHIFT > 0:
        c.anchor += PHASE_SHIFT
        while c.frames < c.anchor:
            c.tick()
    c.armed.append((name, c.anchor))
    for _ in range(40):
        if not wait or (name, c.anchor) not in c.armed:
            break
        c.tick()
    if wait:
        assert (name, c.anchor) not in c.armed, "the picture of game frame %d never came" % c.anchor


def finish_goldens(gb, each=None):
    """Run until every shot armed with wait=False has been taken and checked."""
    c = game_clock(gb)
    for _ in range(40):
        if not c.armed:
            return
        c.tick(each)
    assert not c.armed, c.armed


# ---- screen layout: parsed from src/layout.h so a layout tweak needs no test edits ----
import re as _re

_LAYOUT_H = (ROOT / "src" / "layout.h").read_text()
LAYOUT = {m.group(1): int(m.group(2)) for m in _re.finditer(r"#define (\w+)\s+(\d+)\b", _LAYOUT_H)}


def bar_top_row(b):
    return LAYOUT["BAR_FIRST_ROW"] + LAYOUT["BAR_ROW_STRIDE"] * b


def bar_counter_row(b):
    return bar_top_row(b) + LAYOUT["BAR_COUNTER_DROW"]


def bar_top_y(b):
    return bar_top_row(b) * 8


def mug_top_y(b):
    """Screen y of the top of a mug / fill / glass sprite on bar b."""
    return bar_top_y(b) + LAYOUT["MUG_DY"]


# per-venue drop of the glass held under the spout (tools/gen_art.py FILL_DY, packed into venue.show_band bits 1-2 and read by
# src/mugs.c draw_fill; build/venues.json "fill_dy"), px below a sliding mug. Index = theme (saloon sports lodge bistro igloo
# factory biker teahouse zoo space).
def _fill_dy_table():
    import json
    v = json.loads((ROOT / "build" / "venues.json").read_text())
    return [v["venues"][t]["fill_dy"] for t in v["themes"]]


FILL_DY = _fill_dy_table()


def fill_top_y(b, venue_id=0):
    """Screen y of the top of the fill glass held under the spout on bar b (FILL_DY[venue] below a sliding mug)."""
    return mug_top_y(b) + FILL_DY[venue_id]


# ---- game tunables: parsed from src/game.h (plain numeric defines only) ----
GAME = {m.group(1): int(m.group(2)) for m in _re.finditer(r"#define (\w+)\s+(\d+)\b", (ROOT / "src" / "game.h").read_text())}


# ---- M9 themed venues: build/venues.json (tools/gen_art.py) has each theme's tile ids, maps, attributes, palettes ----
import json as _json

VENUES = _json.loads((ROOT / "build" / "venues.json").read_text())
THEMES = VENUES["themes"]                     # theme index = patron group index (saloon = 0)


def venue(theme):
    """Theme (name or index) -> dict: stage_map / stage_attr (20x4), bar_map / bar_attr (20x3), floor_tile, pal, ..."""
    return VENUES["venues"][THEMES[theme] if isinstance(theme, int) else theme]


def keg_bg(theme):
    """The keg's BG palette slot on the level screen (the Atlas plan, build/art.h VENUE_KEG_BG0: bit t set = BG 0, else BG 1); the venue art itself names BG 7 (mini-games, title)."""
    mask = int(_re.search(r"#define VENUE_KEG_BG0 (\d+)", (ROOT / "build" / "art.h").read_text()).group(1))
    return 0 if (mask >> theme) & 1 else 1


def level_attr(theme, attrs):
    """The venue's attribute bytes as the level screen draws them: the keg tiles' BG 7 is the plan's keg slot (src/level.c keg_remap)."""
    k = keg_bg(theme)
    return [k if a == 7 else a for a in attrs]


def venue_rows(theme, key):
    """A 20-wide map of the venue as a list of rows."""
    m = venue(theme)[key]
    return [m[i:i + 20] for i in range(0, len(m), 20)]


# ---- M13a: on DMG the mug / empty sprites use bit-plane-swapped copies of their tiles at OBJ 240-245 (OBP0;
# OBP1 belongs to lifted patrons). logical_tile() maps a copy back to the tile it was made from, so tests can ask
# "which frame is this" on both models.
_ART = (ROOT / "build" / "art.h").read_text()


def _art(name):
    return int(_re.search(rf"#define {name} (\d+)", _ART).group(1))


OBJ_BT_END = GAME["OBJ_BT_END"]                       # Sal: 5 frames x 8 = OBJ 0..39, 40..55 free; the venue drink starts at 56
OBJ_MUG_ID = OBJ_BT_END


def bt_picture(state):
    """Sal's logical state (BT_* in src/game.h, 0..6) -> his PICTURE index in assets/art/bartender.txt (idle, walk1, walk2,
    fill, fail): SLIDE (4) and CATCH (5) show the fill picture (owner decision 2026-10-20), FAIL (6) is picture 4."""
    return state if state <= 3 else 4 if state == 6 else 3
OBJ_MUG_DRINK_ID = OBJ_MUG_ID + _art("MUG_TILE_COUNT") + _art("GLASS_TILE_COUNT") + _art("MUG_FILL_TILE_COUNT")
OBJ_DMG_COPY = GAME["OBJ_DMG_COPY"]
DMG_COPIES = {OBJ_DMG_COPY + k: OBJ_MUG_ID + k for k in range(4)}                     # sliding full, sliding empty
DMG_COPIES.update({OBJ_DMG_COPY + 4 + k: OBJ_MUG_DRINK_ID + 6 + k for k in range(2)})  # the empty in a patron's hand


def logical_tile(t):
    """The tile a sprite shows, with a DMG copy (OBJ 240-245) mapped back to its original id."""
    return DMG_COPIES.get(t, t)


# ---- the debug menu (src/debug.c): in every build, locked until its flag is saved (SRAM 0x18 "DU": src/save.c) ----
DU_AT = 0x18


def du_block(flag=1):
    """The save's "DU" block: magic, the flag (1 unlocked), checksum, complement."""
    b = bytearray(b"DU" + bytes([flag]))
    c = (0x5A + sum(b)) & 255
    return bytes(b + bytes([c, c ^ 255]))


def with_unlock(ram=None):
    """A cartridge image (None: blank) with the debug menu unlocked."""
    r = bytearray(ram) if ram is not None else bytearray(0x2000)
    r[DU_AT:DU_AT + 5] = du_block()
    return bytes(r)


def sram_poke(gb, off, data):
    """Write cartridge RAM of a running Rom behind the game's back (the MBC's RAM enable, then off again)."""
    m = gb.pb.memory
    m[0x0000] = 0x0A
    for i, v in enumerate(data):
        m[0xA000 + off + i] = v
    m[0x0000] = 0x00


def sram_peek(gb, off, n):
    m = gb.pb.memory
    m[0x0000] = 0x0A
    out = bytes(m[0xA000 + off + i] for i in range(n))
    m[0x0000] = 0x00
    return out


def unlock_debug(gb):
    """Unlock the debug menu of a running Rom (what the Konami code on the title saves)."""
    sram_poke(gb, DU_AT, du_block())


def debug_unlocked(gb):
    return sram_peek(gb, DU_AT, 5) == du_block()


def gesture(gb, taps=3, gap=3, hold_first=2):
    """SELECT held, START tapped `taps` times (each tap 2 frames down, `gap` frames up). SELECT stays held: release_gesture."""
    gb.hold("select")
    gb.run(hold_first)
    for _ in range(taps):
        gb.press("start", 2)
        gb.run(gap)
    for _ in range(8):                               # (the third tap opens the menu with the LCD off for a few frames: wait for it to come on)
        if gb.pb.memory[0xFF40] & 0x80:
            break
        gb.run(1)


def release_gesture(gb):
    gb.release("select")
    gb.run(2)


KONAMI = ["up", "up", "down", "down", "left", "right", "left", "right", "b", "a"]


def konami(gb, keys=KONAMI):
    for k in keys:
        gb.press(k, 2)
        gb.run(2)


@pytest.fixture(scope="session")
def release_built():
    """`make release`, once per pytest process, under a file lock so that several processes (the shards, or a plain
    `pytest` run in two terminals) never run make on build/ together; ptest has built it already, so this is a no-op there."""
    import fcntl
    import subprocess
    lock = ROOT / "out" / "release.lock"
    lock.parent.mkdir(exist_ok=True)
    with open(lock, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            subprocess.run(["make", "release"], cwd=ROOT, check=True, capture_output=True)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
    return ROOT / "build" / "release.gb"


def newest_source():
    """(mtime, path) of the newest file under src/ and assets/ (plus the Makefile): what a ROM build reads."""
    best = (0.0, None)
    for top in ("src", "assets"):
        for p in (ROOT / top).rglob("*"):
            if p.is_file() and p.suffix in (".c", ".h", ".s", ".asm", ".inc", ".json", ".txt", ".png", ".gbsprite", ".tmx", ".md"):
                best = max(best, (p.stat().st_mtime, str(p)))
    mk = ROOT / "Makefile"
    return max(best, (mk.stat().st_mtime, str(mk)))


@pytest.fixture(scope="session")
def c_rom_fresh():
    """The asm-twin tests compare build/game.gb with build/game-c.gb. An old game-c.gb has another memory layout and fails
    in confusing ways (or, worse, compares the wrong code), so a game-c.gb older than the sources FAILS here and says what to run.
    No game-c.gb at all stays a skip in the tests that need it (a tree where `make cfall` was never run)."""
    c = ROOT / "build" / "game-c.gb"
    if not c.exists():
        return None
    t, src = newest_source()
    if c.stat().st_mtime < t:
        pytest.fail(f"build/game-c.gb is older than the sources ({Path(src).relative_to(ROOT)} is newer): run `make cfall`, "
                    "then these asm-twin tests compare the current code", pytrace=False)
    return c


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: builds the ROM variants from scratch (tests/test_build.py)")
    config.addinivalue_line("markers", "release_only: runs only with FULL=1 (a release or full verify); otherwise deselected at collection, "
                            "so it never shows as a skip (test batch 2, B2)")
    config.addinivalue_line("markers", "only_model(name): the test applies to one hardware model ('dmg' or 'cgb'); the other "
                            "model's case is deselected at collection (so it never shows as a skip)")


def pytest_collection_modifyitems(config, items):
    keep, drop = [], []
    full = bool(os.environ.get("FULL"))
    for it in items:
        if not full and it.get_closest_marker("release_only"):
            drop.append(it)
            continue
        mk = it.get_closest_marker("only_model")
        cs = getattr(it, "callspec", None)
        models = [v for v in cs.params.values() if v in ("dmg", "cgb")] if cs else []
        (drop if mk and models and models[0] != mk.args[0] else keep).append(it)
    if drop:
        config.hook.pytest_deselected(items=drop)
        items[:] = keep


# The story's order of the venues (src/order.h, owner 2026-11-07): chapter c plays venue VEN_AT[c]; venue v is chapter POS_OF[v]. A chapter is a place in that order (story_progress,
# the map's progress, the saved progress); a venue is the content (story_chapter, cur_group, the scenes, bosses, mini-games and tunes).
VEN_AT = (0, 1, 3, 4, 2, 5, 6, 7, 8, 9)
POS_OF = (0, 1, 4, 2, 3, 5, 6, 7, 8, 9)
STEP_STAMP = 0x80    # save.c: byte 5 bit 7, set by every save made with this order
