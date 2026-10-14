# Shared fixtures. GB_ROM overrides the ROM path; GB_UPDATE_GOLDEN=1 rewrites goldens.
import os
from pathlib import Path

import pytest
from gbtools import Rom

ROOT = Path(__file__).resolve().parent.parent
ROM = Path(os.environ.get("GB_ROM", ROOT / "build" / "game.gb"))
GOLDEN = ROOT / "tests" / "golden"
UPDATE = os.environ.get("GB_UPDATE_GOLDEN") == "1"


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


def with_cards(ram=None, seen=0xFFFF):
    """A cartridge image (None: blank) with the bonus block in it, unless the image already carries one."""
    r = bytearray(ram) if ram is not None else bytearray(0x2000)
    if bytes(r[BX_AT:BX_AT + 4]) != b"MGB1":
        r[BX_AT:BX_AT + 10] = bx_block(seen=seen)
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
K_ARCADE, K_STORY, K_MUSIC, K_CONTINUE, K_BONUS, K_PLAY, K_SETTINGS, K_SOUNDTRACK, K_CLASSIC, K_MINIGAMES, K_BOSSRUSH = range(11)
TM_TOP, TM_PLAY, TM_BONUS, TM_SETTINGS = range(4)
MENU_SETTLE = 6          # frames for a submenu's lines to reach the screen (2-5: src/title.c menu_frame)


def menu_items(rom):
    return list(rom.read("title_items", rom.mem("title_n")))


def menu_tap(rom, b):
    rom.press(b, 2)
    rom.run(1)                                # (the release must be seen before the next press)


def menu_to(rom, k):
    """Move the title's cursor down to item k of the menu shown."""
    items = menu_items(rom)
    assert k in items, (k, items)
    while items[rom.mem("title_sel")] != k:
        menu_tap(rom, "down")


def title_pick(rom, top, item=None, press=True):
    """From the title's top level: open top item `top` (K_PLAY / K_BONUS / K_SETTINGS); then with `item`, move to it
    and (press) choose it with A."""
    assert rom.mem("title_menu") == TM_TOP
    menu_to(rom, top)
    menu_tap(rom, "a")
    if item is not None:
        menu_to(rom, item)
        if press:
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


def check_golden(gb, name):
    """Compare the screen with tests/golden/<name>.<model>.png; diffs land in out/diff/."""
    ok = gb.golden(GOLDEN / f"{name}.{gb.model_name}.png", update=UPDATE, diff_dir=ROOT / "out" / "diff")
    assert ok, f"screen differs from golden {name}.{gb.model_name}.png (see out/diff/). Intentional? GB_UPDATE_GOLDEN=1 make test"


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


OBJ_MUG_ID = _art("BARTENDER_TILE_COUNT")
OBJ_MUG_DRINK_ID = OBJ_MUG_ID + _art("MUG_TILE_COUNT") + _art("GLASS_TILE_COUNT") + _art("MUG_FILL_TILE_COUNT")
OBJ_DMG_COPY = GAME["OBJ_DMG_COPY"]
DMG_COPIES = {OBJ_DMG_COPY + k: OBJ_MUG_ID + k for k in range(4)}                     # sliding full, sliding empty
DMG_COPIES.update({OBJ_DMG_COPY + 4 + k: OBJ_MUG_DRINK_ID + 6 + k for k in range(2)})  # the empty in a patron's hand


def logical_tile(t):
    """The tile a sprite shows, with a DMG copy (OBJ 240-245) mapped back to its original id."""
    return DMG_COPIES.get(t, t)
