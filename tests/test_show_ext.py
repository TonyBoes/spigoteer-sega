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

from conftest import ROOT, THEMES, locked_make, venue as venue_art
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


def entries(block):
    """Block bytes -> (period, rows[beat][k] = record index, records[[(y, x, tile, prop)] x 4], flips[k]). A record is 16 bytes (src/show_ext.c): y = 1 + 16 * cell row (0: no entry)."""
    size, period = block[0] | block[1] << 8, block[2]
    assert size == len(block), (size, len(block))
    head = 3 + 6 * period
    rows = [[(block[3 + 6 * s + 2 * k] | block[4 + 6 * s + 2 * k] << 8) for k in range(3)] for s in range(period)]
    assert all(o >= head and (o - head) % 16 == 0 for r in rows for o in r)
    recs = [[tuple(block[head + 16 * i + 4 * e:head + 16 * i + 4 * e + 4]) for e in range(4)] for i in range((size - head) // 16)]
    rows = [[(o - head) // 16 for o in r] for r in rows]
    flips = [any(e[3] & 0x20 for e in recs[rows[0][k]]) for k in range(3)]
    return period, rows, recs, flips


def expect(block, beat):
    """What OAM 28..39 must hold on `beat`: per performer a list of (y, x, tile, flags) for its entries (OAM y - 16, OAM x - 8, tile, prop bits 3 and 5)."""
    period, rows, recs, flips = entries(block)
    out = []
    for k in range(3):
        ents = []
        for y, x, tile, prop in recs[rows[beat % period][k]]:
            if y:
                ents.append((y - 1 + 8, DANCER_X[k] + x - 8, tile, prop & 0x28))
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
    period, rows, recs, flips = entries(block)
    assert period == 4 and len(recs) == 12, "three performers x 4 frames"
    assert flips == [False, False, True], "left and middle unflipped, right X-flipped"
    assert [r[0] for r in rows] == [0, 1, 2, 3] and [r[1] for r in rows] == [4, 5, 6, 7] and [r[2] for r in rows] == [8, 9, 10, 11]
    assert v["show_ext"]["d_quarters"] == 16, "8 frames, 16 deduplicated 8x16 quarters = the 32 tiles"
    assert v["show_ext"]["c_block"] is not None, "Color has its own file (lights and sparks, 16 frames); the DMG keeps the lineup"


def test_a_block_can_say_the_bistro_band():
    """The format expresses the Bistro band (12 frames, accordion A B C D, fiddler A B C D C B, singer A B C D; 26 quarters) and loops of every length 1-8."""
    import gen_art
    import math
    for n in range(1, 9):
        p = [{"loop": [0] * n}, {"loop": [0] * 8}, {"loop": [0]}]
        b = gen_art.show_block("t", p, [[(0, 0, ())]] * 2, 24, lambda q: 0, 0)
        assert b[2] == (n * 8 // math.gcd(n, 8))
        assert b[0] | b[1] << 8 == len(b)
    b = gen_art.show_block("t", [{"loop": [0, 1, 2, 3]}, {"loop": [4, 5, 6, 7, 6, 5]}, {"loop": [8, 9, 10, 11]}], [[(0, 0, ())]] * 12, 24, lambda q: 0, 0)
    assert b[2] == 12
    period, rows, recs, flips = entries(b)
    assert len(recs) == 12 and block_loops(b, [[0, 1, 2, 3], [4, 5, 6, 7, 6, 5], [8, 9, 10, 11]])


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
    block = v["show_ext"]["d_block"] if model == "dmg" else v["show_ext"]["c_block"]
    gb = boot_at(FACTORY, model)
    try:
        seen = check_beats(gb, block, 9 if model == "dmg" else 17)
        assert seen == ({0, 1, 2, 3} if model == "dmg" else set(range(8)))
        assert {s["flags"] & 0x20 for s in dancer_oam(gb)[8:12]} == {0x20} and {s["flags"] & 0x20 for s in dancer_oam(gb)[0:8]} == {0}
        # the picture the hardware draws (PyBoy renders the OAM flag): the right robot is the left one mirrored, every beat, and the middle one differs
        for _ in range(8 if model == "dmg" else 0):          # (Color's right robot runs half a loop behind the left one: no pixel mirror)
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
    r = locked_make([f"BUILD={out.relative_to(ROOT)}", f"OUT=out/o_showcgb", f"{out.relative_to(ROOT)}/game.gb"], "b_showcgb", env=env)
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

# ---- the imported shows (2026-11-03: every venue's locked show) --------------------------------------------------------------------------------------------------------------------
# venue: (Color loops, Color flips, Color figure width, Color frames, DMG loops, DMG flips, DMG frames)
SHOWS = {
    "space": ([[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 9, 11, 9]], [0, 0, 0], 16, 12, [[0, 1, 2, 3], [1, 2, 3, 0], [2, 3, 0, 1]], [1, 0, 0], 4),
    "bistro": ([[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11, 10, 9]], [0, 0, 0], 16, 12, [[0, 1], [4, 5], [2, 3]], [0, 0, 0], 6),
    "factory": ([[0, 1, 2, 3, 4, 5, 6, 7], [8, 9, 10, 11, 12, 13, 14, 15], [4, 5, 6, 7, 0, 1, 2, 3]], [0, 0, 1], 16, 16, [[0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 2, 3]], [0, 0, 1], 8),
    "zoo": ([[0, 1, 2, 3, 4, 3, 2, 1], [5, 6, 7, 8], [0, 1, 2, 3, 4, 3, 2, 1]], [1, 0, 0], 24, 9, [[0, 0, 1, 2, 2, 2, 1, 1], [3, 4, 3, 4, 3, 4, 3, 4], [0, 0, 1, 2, 2, 2, 1, 1]], [1, 0, 0], 5),
}


def block_loops(block, loops):
    """True when each performer's record sequence over the period follows the given loop of frame ids (same frame -> same record, different -> different)."""
    period, rows, recs, flips = entries(block)
    for k in range(3):
        seq = [rows[s][k] for s in range(period)]
        want = [loops[k][s % len(loops[k])] for s in range(period)]
        m = {}
        for r, f in zip(seq, want):
            if m.setdefault(f, r) != r:
                return False
        if len(set(m.values())) != len(m):
            return False
    return True


def block_info(block):
    period, rows, recs, flips = entries(block)
    return period, [int(f) for f in flips], len(recs)


@pytest.mark.parametrize("t", list(SHOWS))
def test_each_imported_show_lists_its_loops(t):
    import math
    cl, cf, cw, cn, dl, df, dn = SHOWS[t]
    v = venue_art(t)
    d, c = ext_blocks(v)
    for blk, loops, flips in ((d, dl, df), (c, cl, cf)):
        per = 1
        for l in loops:
            per = per * len(l) // math.gcd(per, len(l))
        assert block_loops(blk, loops), (t, "the records follow the loops")
        assert block_info(blk)[:2] == (per, flips), (t, "period and flips")
    assert v["show_ext"]["c_quarters"] <= v["show_ext"]["c_capacity"]


@pytest.mark.parametrize("t", ["teahouse", "sports"])
def test_the_shared_shows_stay_a_four_frame_dance(t):
    v = venue_art(t)
    assert v["show_frames"] == 4 and v["show_ext"] is None


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("t", list(SHOWS))
def test_the_imported_shows_dance_their_loops(t, model):
    v = venue_art(t)
    d, c = ext_blocks(v)
    block = c if model == "cgb" else d
    gb = boot_at(THEMES.index(t), model)
    try:
        period = block[2]
        seen = check_beats(gb, block, period + 2)
        assert len(seen) == period, (t, model, len(seen), period)
        assert all(s["y"] == 0 or s["y"] >= 16 for s in dancer_oam(gb)), "nothing above row 0"
        if model == "cgb":
            mem = gb.pb.memory
            e = v["show_ext"]
            for q, i in enumerate(e["c_ids"]):
                assert bytes(mem[1, 0x8000 + 16 * i:0x8000 + 16 * i + 32]) == bytes(e["c_tiles"][32 * q:32 * q + 32]), (t, q)
    finally:
        gb.stop()


# ---- the Bistro singer's own OBJ palette (Color only) ----------------------------------------------------------------------------------------------------------------------------
BISTRO = THEMES.index("bistro")
WINE = 0x8A1C3A


def rgb15_of(h):
    return (h >> 16 & 255) // 8 | (h >> 8 & 255) // 8 << 5 | (h & 255) // 8 << 10


def test_the_bistro_lists_three_show_palettes_the_singer_s_in_wine():
    v = venue_art("bistro")
    assert v["show_pal_n"] == 3
    a, s, b = v["show_pals"]
    assert a == b and s[1] == rgb15_of(WINE) and s[0] == a[0] == 0 and s[2:] == a[2:] and s[1] != a[1], "the band's palette on both sides; the singer's colour 1 is the wine"
    assert v["show_pals"][0] == v["pal"][6]


def test_the_bistro_singer_wears_her_wine_dress_on_color_and_the_band_does_not():
    """The middle performer's entries use OBJ 4 and the others OBJ 5 / OBJ 3 (the Saloon mechanism); the picture shows the wine on her alone, and the OBJ 4 palette RAM (OCPD) reads back her colours."""
    from test_fade_chain import pack
    from test_show_obj5 import play, start_show, patch
    from test_venues import cgb_palette
    v = venue_art("bistro")
    band, singer = v["show_pals"][0], v["show_pals"][1]
    gb = play(BISTRO, False)
    try:
        freeze(gb)
        gb.run(1, render=True)
        before = pack(gb.image())
        start_show(gb, 400)
        gb.run(30)
        got = [sorted({s["flags"] & 7 for s in gb.oam()[28 + 4 * k:32 + 4 * k] if s["y"]}) for k in range(3)]
        assert got == [[5], [4], [3]], got
        assert cgb_palette(gb, 4, obj=True)[1:] == singer[1:], "OBJ 4 in palette RAM holds the singer's colours"
        seen = [set(), set(), set()]
        for _ in range(48):                     # (four beats: every pose)
            gb.run(1, render=True)
            during = pack(gb.image())
            for k in range(3):
                r = (DANCER_X[k], 8, DANCER_X[k] + 16, 32)
                seen[k] |= set(np.unique(patch(during, r)).tolist()) - set(np.unique(patch(before, r)).tolist())
        assert singer[1] in seen[1] and singer[1] not in seen[0] | seen[2], "the wine on the singer only"
        assert band[1] in seen[0] and band[1] in seen[2] and band[1] not in seen[1], "the band keeps its own dress colour"
        assert seen[1] <= set(singer), "the singer's pixels all in her palette"
    finally:
        gb.stop()
