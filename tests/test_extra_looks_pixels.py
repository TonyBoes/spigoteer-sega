# Every Color-only extra look of every venue, drawn from the BG at each of the 8 shifts and lifted to sprites, against its SOURCE ART
# (assets/art/patrons/<group>_x.txt): each 16x16 figure's pixels, index by index, must be on the screen where the art puts them.
# The colour of an index is not asserted by value (the mid-frame palette chain decides which palette a bar shows); it must be ONE colour per
# index, different for the three indices, and the same colour on the BG and lifted. A garbled tile fails on the first pixel.
import re

import pytest
from gbtools import Rom
from test_extra_looks_venues import GROUPS, ROOT, table, variant, venue_play
from test_lift import HOOK_DROP, HOOK_LIFT, freeze, hook, lift_state, screen
from test_patrons import lineup, patrons
from conftest import ROM, TRANS_ADDR, bar_top_y, title_level, trans_enable
from test_flow import PLAYING

pytestmark = [pytest.mark.only_model("cgb"), pytest.mark.timeout(600)]

ART = ROOT / "assets" / "art" / "patrons"


def look_art(v, look):
    """The 16 rows of the Color-only look `look` (3-7) of venue group v (front view)."""
    txt = (ART / f"{'saloon' if v == 'cowboys' else v}_x.txt").read_text()      # (the Saloon's file predates the group naming)
    blocks = [[r for r in b.splitlines() if r and not r.startswith(";")] for b in txt.split("\n\n")]
    blocks = [b for b in blocks if b]
    assert len(blocks) == 5
    return blocks[look - 3]


def check_figure(img, art, x, y, what, seen):
    """Pixel-for-pixel: index k of the art is one colour on screen (the same in every figure of this look/instance: `seen`)."""
    got = {}
    for r in range(16):
        for c in range(16):
            k = ".-+#".index(art[r][c])
            if not k:
                continue
            px = tuple(int(t) for t in img[y + r, x + c][:3])
            if got.setdefault(k, px) != px:
                return f"{what}: index {k} is {got[k]} and {px} (row {r}, col {c})"
    cols = list(got.values())
    if len(set(cols)) != len(cols):
        return f"{what}: indices share a colour {got}"
    if seen.setdefault("cols", got) != got:
        return f"{what}: colours {got} differ from the other shifts' {seen['cols']}"
    return None


def blob_of(v):
    name = "saloon" if v == "cowboys" else v
    txt = (ROOT / "build" / f"patrons_{name}_x.c").read_text()
    body = txt[txt.index(f"patron_tiles_{name}_x[4032] = {{"):]
    return bytes(int(h, 16) for h in re.findall(r"0x([0-9A-F]{2})", body[:body.index("};")]))


def venue_play_trans(v, variant=1):
    """The venue's first level entered the way a player enters it: the scene change's fade on (the other tests turn it off), the LCD on in the
    reveal that fades the new colours in. (The fade keeps the scene's colours in VRAM bank 1 while the scene is built.)"""
    gb = Rom(ROM, "cgb")
    gb.__enter__()
    gb.model_name = "cgb"
    gb.run(120)
    gb.write("sa_hold", 1)
    trans_enable(gb, True)
    gb.pb.memory[TRANS_ADDR] |= variant << 5       # (the shipped default, TRANS_DEFAULT: the fade to white; 2 through amber; the tests' 0 is the drink)
    title_level(gb, GROUPS.index(v) + 1)
    for _ in range(600):
        gb.run(1)
        if gb.mem("game_state") == PLAYING:
            break
    assert gb.mem("game_state") == PLAYING and gb.mem("cur_group") == GROUPS.index(v)
    for _ in range(400):                            # (the reveal fades the colours in over a few dozen frames)
        if not gb.pb.memory[TRANS_ADDR] & 0x1F:
            break
        gb.run(1)
    gb.run(30)
    gb.write("tip_chance", 0)
    return gb


@pytest.mark.parametrize("fade", [1, 2], ids=["white", "amber"])
@pytest.mark.parametrize("v", GROUPS)
def test_the_blob_in_bank_1_is_whole_after_the_scene_change_fade(v, fade):
    """VRAM bank 1 holds all 252 tiles of the venue's Color-only looks once its level is on screen. (The fade stashed the scene's 64 colours in
    bank 1 tile ids 248-255 and left the blob's last four tiles, the end of look 7's poses, as colour bytes.)"""
    gb = venue_play_trans(v, fade)
    try:
        blob = blob_of(v)
        assert len(blob) == 252 * 16
        vram = gb.pb.memory
        got = bytes(vram[1, 0x9000:0x9800]) + bytes(vram[1, 0x8800:0x9000])[:124 * 16]
        bad = [i for i in range(252) if got[16 * i:16 * i + 16] != blob[16 * i:16 * i + 16]]
        assert not bad, f"{v}: bank-1 tiles {bad} are not the blob's"
    finally:
        gb.stop()


@pytest.mark.parametrize("trans", [False, True], ids=["cut", "fade"])
@pytest.mark.parametrize("v", GROUPS)
def test_every_color_look_is_its_art_at_every_shift_on_the_bg_and_lifted(v, trans):
    """Four (look, palette) pairs at a time, one a bar, set down at x = 24 + 24 b and left to WALK: every frame in which nobody moved is a picture of
    each figure at the shift its x has (a walker passes all eight in a few dozen frames). Each is checked on the BG, then again with all four lifted."""
    if v == "cowboys":      # (the Saloon predates tools/gen_looks.py: its (look, instance) pairs are test_saloon_looks.COMBOS)
        from test_saloon_looks import COMBOS
        combos = [(lk, pi) for lk, pis in COMBOS.items() if lk > 2 for pi in pis]
    else:
        combos = [(lk, pi) for lk, pi in table(v)["combo"] if lk > 2]
    gb = venue_play_trans(v) if trans else venue_play(v)
    bad = []
    done = 0
    try:
        freeze(gb)
        gb.run(4)
        seen = {}
        for g in range(0, len(combos), 4):
            group = combos[g:g + 4]
            spec = {b: [(24 + 24 * b, variant(*group[b]) if b < len(group) else 0, 0)] for b in range(4)}      # (a short last group: look 0 fills the bars, unchecked)
            lineup(gb, spec)
            gb.run(8, render=True)
            ids = {p["bar"]: p["i"] for p in patrons(gb)}
            for lifted in (0, 1):
                if lifted:
                    for b in range(len(group)):
                        hook(gb, ids[b], HOOK_LIFT)
                        for _ in range(20):
                            gb.run(1, render=True)
                            if gb.mem("lift_hook_res"):
                                break
                    assert all(lift_state(gb)[ids[b]] == HOOK_LIFT for b in range(len(group))), lift_state(gb)
                shifts = {b: set() for b in range(len(group))}
                last, still = None, 0
                for _ in range(900):
                    gb.run(1, render=True)
                    now = {q["bar"]: q["x"] for q in patrons(gb) if q["state"] == 1}
                    still = still + 1 if now == last else 0
                    if still >= 2 and len(now) == 4:          # (the picture follows a step of x by a frame: shoot on the third frame at one x)
                        img = screen(gb)
                        for b, (lk, pi) in enumerate(group):
                            x = now[b]
                            what = f"{v} look {lk} palette {pi} shift {x & 7} {'lifted' if lifted else 'BG'}"
                            bad_ = check_figure(img, look_art(v, lk), x, bar_top_y(b), what, seen.setdefault((lk, pi), {}))
                            if bad_:
                                bad.append(bad_)
                            shifts[b].add(x & 7)
                            done += 1
                    last = now
                    if all(len(s) == 8 for s in shifts.values()):
                        break
                assert all(len(s) == 8 for s in shifts.values()), (group, lifted, shifts, "a walker did not pass all eight shifts")
                if lifted:
                    for b in range(len(group)):
                        hook(gb, ids[b], HOOK_DROP)
                    gb.run(8, render=True)
    finally:
        gb.stop()
    assert not bad, "\n".join(bad[:12]) + f"\n({len(bad)} bad figures of {done})"
