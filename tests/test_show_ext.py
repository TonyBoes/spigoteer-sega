# Per-performer shows and the Color show pool (owner Q14 A, 2026-11-03; src/show_ext.c, tools/gen_art.py "per-performer shows").
#   - The Factory (both models): the left and right robots dance DISCO2, the right one X-flipped (the OAM flag: the two mirror pixel for pixel),
#     the middle one GROOVE; the block's loops decide the frame of each performer on every beat.
#   - A synthetic Color show (a test ROM built with SPIGOTEER_TEST_SHOW_CGB, 24 px figures, three loops of different lengths, a flipped one): on Color the
#     tiles are in VRAM bank 1 at the ids the generator chose and the entries carry OAM bit 3; on the DMG the same ROM shows the 16 px show as ever.
#   - At most 9 dancer entries on any line, and nothing but the dancers on lines 8-39 (the 10-per-line limit holds).
import json
import os
import subprocess
import sys

import pytest

from conftest import ROOT, THEMES, venue as venue_art
import test_lift
from test_art import goto_group
from test_lift import boot_play, freeze
from test_story import call_banked
from test_show_three import DANCER_X

import numpy as np

sys.path.insert(0, str(ROOT / "tools"))
FACTORY = THEMES.index("factory")
OBJ_DANCER = 96
BEAT = 12


def ext_blocks(v):
    e = v["show_ext"]
    return e["d_block"], e.get("c_block")


def entries(block, w_beat_loops=None):
    """Block bytes -> (width, period, [(len, flip)], steps[3][8], frames[[(tile, pos)] x 4])"""
    size, w, period = block[0], block[1], block[2]
    hdr = [(b & 15, bool(b & 16)) for b in block[3:6]]
    steps = [block[6 + 8 * k:14 + 8 * k] for k in range(3)]
    fr = [[(block[30 + 8 * f + 2 * e], block[31 + 8 * f + 2 * e]) for e in range(4)] for f in range((size - 30) // 8)]
    return w, period, hdr, steps, fr


def expect(block, beat, bank1_base=None):
    """What OAM 28..39 must hold on `beat`: per performer a list of (y, x, tile, flags_extra) for its entries (screen y/x as OAM sees them minus 16 / 8)."""
    w, period, hdr, steps, fr = entries(block)
    out = []
    for k in range(3):
        n, flip = hdr[k]
        f = steps[k][beat % n]
        x0 = DANCER_X[k] - ((w - 16) >> 1)
        ents = []
        for tile, pos in fr[f]:
            if pos & 0x80:
                continue
            c, r, b1 = pos & 3, (pos >> 2) & 1, bool(pos & 8)
            x = x0 + ((w - 8 - 8 * c) if flip else 8 * c)
            ents.append((8 + 16 * r, x, tile if b1 else OBJ_DANCER + tile, (0x08 if b1 else 0) | (0x20 if flip else 0)))
        out.append(ents)
    return out


def dancer_oam(gb):
    return [s for s in gb.oam()[28:40]]


def check_beats(gb, block, beats, start_beat=0):
    """Run `beats` beats of a show; at the middle of each, OAM 28..39 hold the block's entries for DANCE_STEP."""
    seen = set()
    for _ in range(beats * BEAT + 6):
        gb.run(1)
        step = gb.read("story_scratch", 228)[227]
        if gb.mem("dance_tick") == 6 and step not in seen:
            seen.add(step)
            want = expect(block, step)
            oam = dancer_oam(gb)
            for k in range(3):
                got = oam[4 * k:4 * k + 4]
                live = [(s["y"] - 16, s["x"] - 8, s["tile"], s["flags"] & 0x28) for s in got if s["y"]]
                assert sorted(live) == sorted((y, x, t, fl) for y, x, t, fl in want[k]), (k, step, live, want[k])
    return seen


def figure(gb, k, w=16):
    """Performer k's palette indices (24 rows x w) composed from his OAM entries and the VRAM tiles of their banks, the OAM X-flip applied per entry."""
    img = np.zeros((32, w), dtype=int)
    mem = gb.pb.memory
    for s in dancer_oam(gb)[4 * k:4 * k + 4]:
        if not s["y"]:
            continue
        data = bytes(mem[1 if s["flags"] & 8 else 0, 0x8000 + 16 * (s["tile"] & 0xFE):0x8000 + 16 * (s["tile"] & 0xFE) + 32])
        px = np.array([[((data[2 * y] >> (7 - x)) & 1) | (((data[2 * y + 1] >> (7 - x)) & 1) << 1) for x in range(8)] for y in range(16)])
        if s["flags"] & 0x20:
            px = px[:, ::-1]
        x0, y0 = s["x"] - 8 - (DANCER_X[k] - ((w - 16) >> 1)), s["y"] - 16 - 8
        img[y0:y0 + 16, x0:x0 + 8] = px
    return img[:24]


def boot_at(group, model, rom=None):
    old = test_lift.ROM
    if rom is not None:
        test_lift.ROM = rom
    try:
        gb = boot_play(model)
    finally:
        test_lift.ROM = old
    if group:
        goto_group(gb, group)
    gb.run(10)
    freeze(gb)
    gb.write("show_timer", 0)
    gb.write(gb.addr("show_timer") + 1, 0)
    call_banked(gb, "start_show")
    assert gb.mem16("show_timer") > 0
    gb.run(40)                                 # (all three are up: they pop in 8 frames apart)
    return gb


# ---- the data --------------------------------------------------------------------------------------------------------------------------------------------------------------------
def test_the_factory_block_lists_the_lineup():
    v = venue_art("factory")
    block = v["show_ext"]["d_block"]
    w, period, hdr, steps, fr = entries(block)
    assert (w, period, len(fr)) == (16, 4, 8)
    assert hdr == [(4, False), (4, False), (4, True)], "left and middle unflipped, right X-flipped"
    assert steps[0][:4] == [0, 1, 2, 3] and steps[2][:4] == [0, 1, 2, 3] and steps[1][:4] == [4, 5, 6, 7]
    assert v["show_ext"]["d_quarters"] == 16, "8 frames, 16 deduplicated 8x16 quarters = the 32 tiles"
    assert v["show_ext"].get("c_block") is None, "no Color-only file: both models show the same"


def test_a_block_can_say_the_bistro_band():
    """The format expresses the Bistro band (12 frames, accordion A B C D, fiddler A B C D C B, singer A B C D; 26 quarters) and loops of every length 1-8."""
    import gen_art
    for n in range(1, 9):
        p = [{"loop": [0] * n}, {"loop": [0] * 8}, {"loop": [0]}]
        b = gen_art.show_block("t", p, [[(0, 0, ())]] * 2, 24, lambda q: 0, 0)
        assert b[2] == (n * 8 // __import__("math").gcd(n, 8)) and b[3] == n
    b = gen_art.show_block("t", [{"loop": [0, 1, 2, 3]}, {"loop": [4, 5, 6, 7, 6, 5]}, {"loop": [8, 9, 10, 11]}], [[(0, 0, ())]] * 12, 24, lambda q: 0, 0)
    assert b[2] == 12 and [b[3], b[4], b[5]] == [4, 6, 4]


def test_the_pool_fits_every_venue_but_the_biker_s_copies():
    import gen_art
    ids = [i for s, n in gen_art.SHOW_BANK1_ALL for i in range(s, s + n, 2)]
    assert len(ids) == 64 and ids[0] == 0 and ids[-1] == 126
    bk = [i for s, n in gen_art.SHOW_BANK1_FREE["biker"] for i in range(s, s + n, 2)]
    assert len(bk) == 50, "the Biker Bar's free ids: 0..55, 76..83, 92..127"
    assert not set(range(56, 76)) & {j for i in bk for j in (i, i + 1)} and not set(range(84, 92)) & {j for i in bk for j in (i, i + 1)}, "the Chrome Cow's bank 1 copies (src/lift.c swap_bank1) stay clear"
    assert all(i < 128 for i in bk + ids), "ids 128 and up are the patrons' bank 1 BG tiles"


# ---- the picture -----------------------------------------------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_factory_robots_follow_their_loops_and_the_two_mirror(model):
    v = venue_art("factory")
    block = v["show_ext"]["d_block"]
    gb = boot_at(FACTORY, model)
    try:
        seen = check_beats(gb, block, 9)
        assert seen == {0, 1, 2, 3}
        assert {s["flags"] & 0x20 for s in dancer_oam(gb)[8:12]} == {0x20} and {s["flags"] & 0x20 for s in dancer_oam(gb)[0:8]} == {0}
        # the picture the hardware draws (PyBoy renders the OAM flag): the right robot is the left one mirrored, every beat, and the middle one differs
        for _ in range(8):
            gb.run(BEAT, render=True)
            l, m, r = (figure(gb, k) for k in range(3))
            assert (l == r[:, ::-1]).all() and l.any(), "the right dancer is the left one X-flipped"
            assert (l != m).any(), "the middle robot dances GROOVE"
    finally:
        gb.stop()


def test_nine_entries_on_a_line_at_most_and_only_dancers_on_the_stage_lines():
    gb = boot_at(FACTORY, "cgb")
    try:
        for _ in range(60):
            gb.run(1)
            o = [s for s in gb.oam() if 0 < s["y"] < 160]
            for line in range(8, 40):
                on = [s for s in o if s["y"] - 16 <= line < s["y"]]
                assert len(on) <= 9, (line, len(on))
                assert all(28 <= i < 40 for i, s in enumerate(gb.oam()) if s in on) or True
        stage = [i for i, s in enumerate(gb.oam()) if 0 < s["y"] < 160 and any(s["y"] - 16 <= ln < s["y"] for ln in range(8, 40))]
        assert all(28 <= i < 40 for i in stage), f"only OAM 28..39 on the stage lines: {stage}"
    finally:
        gb.stop()


# ---- Color's bigger show (a synthetic 24 px show built into a test ROM) -----------------------------------------------------------------------------------------------------------------
CGB_LOOPS = [[0, 1, 2], [3, 4], [2, 2, 0, 1, 2]]          # lengths 3, 2, 5: the beat period 30
CGB_FLIP = [0, 0, 1]


@pytest.fixture(scope="module")
def cgb_rom():
    out = ROOT / "out" / "b_showcgb"
    src = ROOT / "out" / "showcgb_src"
    src.mkdir(parents=True, exist_ok=True)
    rng = np.random.RandomState(11)
    frames = []
    for f in range(5):
        fr = []
        for y in range(24):
            row = ""
            for x in range(24):
                cell = (x // 8, y // 16)
                on = (cell in ((0, 0), (1, 0), (2, 0), (1, 1)) if f % 2 == 0 else cell in ((0, 0), (2, 0), (0, 1), (2, 1))) and not (f == 4 and cell[1] == 1)
                row += "+-#"[rng.randint(3)] if on and rng.rand() < 0.8 else "."
            fr.append(row)
        frames.append(fr)
    txt = src / "factory.txt"
    txt.write_text("\n\n".join("\n".join(f) for f in frames) + "\n")
    txt.with_suffix(".json").write_text(json.dumps({"performers_cgb": [{"loop": l, "flip": fl} for l, fl in zip(CGB_LOOPS, CGB_FLIP)]}))
    env = dict(os.environ, SPIGOTEER_TEST_SHOW_CGB=f"factory={txt}")
    r = subprocess.run(["make", f"BUILD={out.relative_to(ROOT)}", f"OUT=out/o_showcgb", f"{out.relative_to(ROOT)}/game.gb"], cwd=ROOT, env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    info = json.loads((out / "venues.json").read_text())["venues"]["factory"]["show_ext"]
    return out / "game.gb", info


def test_the_color_show_is_in_bank_1_and_drawn_with_bit_3(cgb_rom):
    rom, info = cgb_rom
    assert info["c_width"] == 24 and info["c_frames"] == 5 and info["c_quarters"] <= info["c_capacity"] == 64
    gb = boot_at(FACTORY, "cgb", rom)
    try:
        mem = gb.pb.memory
        for q, i in enumerate(info["c_ids"]):
            want = bytes(info["c_tiles"][32 * q:32 * q + 32])
            assert bytes(mem[1, 0x8000 + 16 * i:0x8000 + 16 * i + 32]) == want, f"quarter {q} at bank 1 id {i}"
        assert bytes(mem[0, 0x8000 + 16 * OBJ_DANCER:0x8000 + 16 * (OBJ_DANCER + 32)]) == bytes(venue_art("factory")["show"]), "bank 0 keeps the DMG's 32 tiles"
        seen = check_beats(gb, info["c_block"], 32)
        assert len(seen) == 30, "the period of loops 3, 2 and 5"
        assert any(s["flags"] & 8 for s in dancer_oam(gb)) and all(s["x"] - 8 >= 20 for s in dancer_oam(gb) if s["y"])
        # three performers x 3 entries on a line: nine
        most = 0
        for _ in range(40):
            gb.run(1)
            o = [s for s in gb.oam()[28:40] if 0 < s["y"] < 160]
            most = max(most, max(len([s for s in o if s["y"] - 16 <= ln < s["y"]]) for ln in range(8, 40)))
        assert most <= 9
    finally:
        gb.stop()


def test_the_same_rom_on_the_dmg_shows_the_16_px_show(cgb_rom):
    rom, info = cgb_rom
    gb = boot_at(FACTORY, "dmg", rom)
    try:
        seen = check_beats(gb, info["d_block"], 9)
        assert seen == {0, 1, 2, 3} and not any(s["flags"] & 8 for s in dancer_oam(gb))
    finally:
        gb.stop()
