#!/usr/bin/env python3
"""Transcription only: writes factory_show_cgb_p1.txt from the approved robot frames (factory_show.txt, copied unchanged)
plus MY hand-listed light and spark pixels below (every coordinate here is a decision; the script only stamps them and
checks that none lands on a body pixel). Prints cells per frame and the 8x16 quarter count (gen_art.show_cells rules).

  factory_sparks_build.py            write the file and report
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "tools"))
BASE = ROOT / "assets/approved/venues/factory_show.txt"


def blocks(p):
    res, cur = [], []
    for l in Path(p).read_text().splitlines() + [""]:
        if l.startswith(";"):
            continue
        if l.strip() == "":
            if cur:
                res.append(cur)
                cur = []
        else:
            cur.append(l.rstrip())
    return res


base = blocks(BASE)
# poses: P0..P3 = disco 0..3 (3 = 1), G0..G3 = groove 4..7
W, O, D = "-", "+", "#"
# lights: per pose (bulb left x, bulb top y, ear row, ear xL, ear xR, chest row); chest pairs A = x6-7, B = x8-9
POSE = {
    "P0": (0, 6, 0, 6, 3, 10, 12), "P1": (1, 7, 0, 6, 4, 11, 12), "P2": (2, 8, 0, 6, 5, 12, 12), "P3": (1, 7, 0, 6, 4, 11, 12),
    "G0": (4, 7, 0, 6, 4, 11, 12), "G1": (5, 7, 1, 7, 4, 11, 12), "G2": (6, 7, 0, 6, 4, 11, 12), "G3": (7, 7, 1, 7, 4, 11, 12),
}
# right-hand and left-hand sparks, (x, y, colour); stage A = shot out of the antenna, B = star (plus), C = X star, D = last dots
R = {"A": [(11, 0, W), (13, 1, O), (15, 0, O)],
     "B": [(14, 2, O), (13, 2, W), (15, 2, W), (14, 1, W), (14, 3, W)],
     "C": [(14, 1, O), (13, 0, W), (15, 0, W), (13, 2, W), (15, 2, W)],
     "D": [(13, 0, O), (15, 2, O)]}
L = {"A": [(4, 0, W), (2, 1, O), (0, 0, O)],
     "B": [(1, 2, O), (0, 2, W), (2, 2, W), (1, 1, W), (1, 3, W)],
     "C": [(1, 1, O), (0, 0, W), (2, 0, W), (0, 2, W), (2, 2, W)],
     "D": [(2, 0, O), (0, 2, O)]}

# per beat (8 beats a loop): bulb, chest (A,B), right spark stage, left spark stage
BULB_D = "WDODODWD"
BULB_G = "WODOWODO"
CHEST_D = [(O, D), (D, O), (O, O), (D, D), (D, O), (O, D), (D, D), (O, O)]
CHEST_G = [(O, D), (O, O), (D, O), (D, D), (O, D), (O, O), (D, O), (D, D)]
SP_D = {"R": {7: "A", 0: "B", 1: "C", 2: "D"}, "L": {1: "A", 2: "B", 3: "C", 4: "D"}}
SP_G = {"R": {0: "A", 1: "B", 2: "C", 3: "D"}, "L": {4: "A", 5: "B", 6: "C", 7: "D"}}
STATE = {"W": W, "O": O, "D": D}


def make(poses, bulbs, chests, sp, src_ids):
    out = []
    for beat in range(8):
        pose = poses[beat % 4]
        g = [list(r) for r in base[src_ids[beat % 4]]]
        _, bx, by, er, exl, exr, cr = POSE[pose]
        ch = STATE[bulbs[beat]]
        for (x, y) in ((bx, by), (bx + 1, by), (bx, by + 1), (bx + 1, by + 1)):
            assert g[y][x] == O, (pose, x, y, g[y][x])
            g[y][x] = ch
        if bulbs[beat] == "W":      # a lit bulb flares: an orange glint each side, on the row above its housing
            for x in (bx - 1, bx + 2):
                assert g[by][x] == ".", (pose, "glint", x)
                g[by][x] = O
        for x in (exl, exr):
            assert g[er][x] == O, (pose, "ear", x)
        ca, cb = chests[beat]
        g[er][exl], g[er][exr] = (O, D) if beat % 2 == 0 else (D, O)
        for x, c in ((6, ca), (7, ca), (8, cb), (9, cb)):
            assert g[cr][x] == O, (pose, "chest", x, g[cr][x])
            g[cr][x] = c
        bad = []
        for side, tab in (("R", R), ("L", L)):
            st = sp[side].get(beat)
            if st:
                for (x, y, c) in tab[st]:
                    if g[y][x] != ".":
                        bad.append((side, st, x, y))
                    near = [(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx or dy) and 0 <= x + dx < 16 and 0 <= y + dy < 24]
                    for (nx, ny) in near:
                        if base[src_ids[beat % 4]][ny][nx] != "." and (nx, ny) not in [(a, b) for a, b, _ in tab[st]]:
                            print(f"  touch: beat {beat} {pose} spark {side}{st} ({x},{y}) next to body ({nx},{ny})")
                    g[y][x] = c
        if bad:
            sys.exit(f"spark on body pixels: beat {beat} {pose}: {bad}")
        out.append(["".join(r) for r in g])
    return out


disco = make(["P0", "P1", "P2", "P3"], BULB_D, CHEST_D, SP_D, [0, 1, 2, 3])
groove = make(["G0", "G1", "G2", "G3"], BULB_G, CHEST_G, SP_G, [4, 5, 6, 7])
frames = disco + groove

HEAD = """; factory show p1 (Color only; DMG keeps factory_show.txt): 16 frames 16x24 (+ the 8-row transparent pad). Bodies pixel-exact from factory_show.txt; added: blinking lights and spark bursts.
; frames 0-7 DISCO (poses 0 1 2 1 0 1 2 1 of today's disco; 0 = right arm up, 2 = left arm up), frames 8-15 GROOVE (poses 4 5 6 7 4 5 6 7 of today's groove).
; "performers_cgb": [{"loop": [0,1,2,3,4,5,6,7], "flip": 0}, {"loop": [8,9,10,11,12,13,14,15], "flip": 0}, {"loop": [4,5,6,7,0,1,2,3], "flip": 1}]
; loop player 0 (disco, left):          0 1 2 3 4 5 6 7
; loop player 1 (groove, middle):       8 9 10 11 12 13 14 15
; loop player 2 (disco, right, flipped): 4 5 6 7 0 1 2 3   (half a loop behind the left one; its sparks mirror too)
; lights (index 1 = on, 3 = off where the body is light; the antenna bulb 2x2 goes white / orange / dark): bulb, the two ear lights alternate, the chest's two top lights (x6-7, x8-9) blink.
; sparks: a burst on each side (A shot out, B plus star, C X star, D last dots) only in the head's free corners (x0-3 / x12-15 at the top), never on a body pixel.
"""
Path(HERE / "factory_show_cgb_p1.txt").write_text(HEAD + "\n" + "\n\n".join("\n".join(f) for f in frames) + "\n")

from gen_art import show_cells  # noqa: E402

cells = show_cells(frames, 16)
qs = []
for cl in cells:
    for _, _, q in cl:
        if q not in qs:
            qs.append(q)
print("cells per frame:", [len(c) for c in cells])
print("quarters:", len(qs))
