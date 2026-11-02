# The Color levels' palette chain (src/main.c split_isr / split_isr3: BG palettes reloaded partway down the screen, the stage's put back in the VBlank) under the
# palette fades (src/trans.c, variants 1 and 2). Owner 2026-11-01: "when the fade to white transitions happen they flicker and some tiles appear".
# A fade writes the BG palette RAM in one burst a step; the chain kept reloading the full-colour palettes below the split (and the VBlank kept putting the full-colour
# stage palettes back), so those rows flashed in full colour in a faded screen. trans.c chain_apply / chain_flat / chain_back now fade the chain's buffers with the screen.
#
# The check, on every frame of a scene change (the level before it faded out, the next venue's level faded in): the frame's top lines (above every reload) tell the fade
# level (the colours of the scene faded by the game's own arithmetic, `lerp` below, to white or to amber, one of the nine eighths); then EVERY scanline of the frame, the
# reloaded ones below the split included, may hold only colours of that level (or one the sprites are late by: their palettes follow the BG's in the next frame, so the
# levels up to three eighths away are allowed, never the unfaded one). Not a whole screen at one level once: all 110 frames of both fades, each venue out and the next one in, normal speed and double speed.
import contextlib

import numpy as np
import pytest

from conftest import TRANS_ADDR, double_speed, trans_enable
from test_art import GS_BONUS, GS_LEVEL_CLEAR, goto_group
from test_lift import boot_play
from test_venues import cgb_palette

pytestmark = pytest.mark.timeout(900)

WHITE, AMBER = 0x7FFF, 0x0E7F
FRAMES = 110


def part(x, k):
    r = 0
    if k & 4:
        r += (x >> 1) & 0x3DEF
    if k & 2:
        r += (x >> 2) & 0x1CE7
    if k & 1:
        r += (x >> 3) & 0x0C63
    return r


def lerp(w, k, t):                                  # src/trans.c lerpn
    if k == 8:
        return w
    return ((t - part(t, k)) + part(w, k)) & 0xFFFF


def pack(img):
    a = np.asarray(img.convert("RGB"), dtype=np.uint16) >> 3
    return a[:, :, 0] | (a[:, :, 1] << 5) | (a[:, :, 2] << 10)


def scene_change(old, variant, ds, model="cgb", bright=False):
    """Venue `old` playing (no transitions), then the next level's start with the fade on: every frame of it."""
    new = (old + 1) % 10
    cm = double_speed() if ds else contextlib.nullcontext()
    with cm:
        gb = boot_play(model)
    try:
        if bright:                                   # SETTINGS > COLOR: GBA (src/bright.h): every colour computed in RAM is lifted, the chain's too
            gb.write("_is_GBA", gb.mem("_is_GBA") | 2)
        if old or bright:
            goto_group(gb, old)
        gb.run(10)
        trans_enable(gb, True)
        gb.pb.memory[TRANS_ADDR] = (gb.pb.memory[TRANS_ADDR] & ~0x60) | (variant << 5)
        gb.write("level", new)
        if new % 2:
            gb.write("game_state", GS_LEVEL_CLEAR)
            gb.write("state_timer", 149)
        else:
            gb.write("bonus_kind", 0)
            gb.write("bonus_phase", 4)
            gb.write("bonus_timer", 129)
            gb.write("game_state", GS_BONUS)
        known = set()
        frames = [pack(gb.image())]
        for _ in range(FRAMES):
            gb.write(0xFF40, gb.read(0xFF40, 1)[0] & ~2)         # (sprites off: their palettes follow the BG ones a frame later, and this is about the BG chain)
            gb.run(1)
            frames.append(pack(gb.image()))
        for _ in range(3):                           # (the new scene settled: its palettes' colours, the sprites' too)
            gb.run(20)
            frames.append(pack(gb.image()))
        for f in frames[:1] + frames[-3:]:
            known |= set(np.unique(f).tolist())
        for obj in (False, True):
            for n in range(8):
                known |= set(cgb_palette(gb, n, obj))
        assert gb.mem("cur_group") == new
        return frames, known
    finally:
        gb.stop()


def level_sets(known):
    known = sorted(known | {AMBER, WHITE})
    return {(t, k): np.array(sorted({lerp(s, k, t) for s in known}), dtype=np.uint16) for t in (WHITE, AMBER) for k in range(9)}


def violations(frame, sets):
    """The scanlines whose colours are not those of the level the top lines are at; (the level, the lines)."""
    best = None
    for t in (WHITE, AMBER):
        for k in range(9):
            miss = (~np.isin(frame[:28], sets[t, k])).sum()
            if best is None or miss < best[0]:
                best = (miss, t, k)
    _, t, k = best
    allowed = sets[t, k]
    bad = np.nonzero((~np.isin(frame, allowed)).any(axis=1))[0]
    return (t, k), bad


def check(old, variant, ds, bright=False):
    frames, known = scene_change(old, variant, ds, bright=bright)
    sets = level_sets(known)
    faded = 0
    for i, f in enumerate(frames):
        (t, k), bad = violations(f, sets)
        faded += k < 8
        assert not len(bad), f"venue {old}->{(old + 1) % 10}, variant {variant}, frame {i} (fade level {k}/8 toward {t:#06x}): scanlines {bad.tolist()[:8]} hold colours of another level"
    assert faded >= 8, "the fade ran"


@pytest.mark.parametrize("old", range(10))
def test_every_scanline_follows_the_fade_to_white(old):
    check(old, 1, False)


@pytest.mark.parametrize("old", [0, 2, 5, 9])
def test_every_scanline_follows_the_fade_through_amber(old):
    check(old, 2, False)


@pytest.mark.parametrize("old", [0, 5, 9])
def test_every_scanline_follows_the_fade_with_screen_bright(old):
    check(old, 1, False, bright=True)


@pytest.mark.parametrize("old", [0, 2, 5, 9])
def test_every_scanline_follows_the_fade_at_double_speed(old):
    check(old, 1, True)


# ---- the pause menu's HOW TO PLAY card (src/pause.c CARD_FADE, trans.c trans_card_out): the same fade over a boss fight's level, which has the chain too.
@pytest.mark.parametrize("c", [0, 2, 5, 9])
def test_every_scanline_follows_the_pause_cards_fade(c):
    from boss_common import fight, play
    from test_pause import CARD_FRAMES, tap

    with fight("cgb", c) as gb:
        play(gb)
        gb.run(40)
        frames, steady = [], [pack(gb.image())]

        def cap(n, hide=True):
            for _ in range(n):
                if hide:
                    gb.write(0xFF40, gb.read(0xFF40, 1)[0] & ~2)
                gb.run(1)
                frames.append(pack(gb.image()))

        gb.press("start", 2)
        cap(10, False)
        steady.append(pack(gb.image()))
        gb.press("down", 2)
        cap(3, False)
        gb.press("a", 2)
        cap(CARD_FRAMES)
        steady.append(pack(gb.image()))
        gb.press("b", 2)
        cap(CARD_FRAMES)
        steady.append(pack(gb.image()))
        gb.press("start", 2)
        cap(40, False)
        steady.append(pack(gb.image()))
        known = set()
        for f in steady:
            known |= set(np.unique(f).tolist())
        sets = level_sets(known)
        faded = 0
        for i, f in enumerate(frames):
            (t, k), bad = violations(f, sets)
            faded += k < 8
            assert not len(bad), f"venue {c}, card frame {i} (fade level {k}/8): scanlines {bad.tolist()[:8]} hold colours of another level"
        assert faded >= 6, "the card's fades ran"
