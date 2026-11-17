"""Approach A: the owner's portrait in front of the venue's OWN in-game backdrop (assets/approved/venues, copied tile for tile), recomposed to a 20 x 13 page.

Copied tiles (S<col>_<row> = <venue>_stage, B<col>_<row> = <venue>_bar): the back wall, the ledge, the lane, the counter and the dispenser. Hand-drawn here: the
frame around the portrait's box (corner, lintel, two posts: five tiles, in the venue's wall pattern) and the counter's front row. Page rows 0-12:
 0       the frame's lintel (the stage's top row beside it)
 1-7     the portrait's 7 x 7 cells between the frame's posts; the wall (the game's own parity pattern) and the venue's wall pieces to the sides
 8       the ledge (stage row 3)       9-11  the bar's three rows as the game draws them (lane, counter, dispenser)       12  the counter's front
The portrait's backdrop is the dark opening of the frame: the owner's art is copied unchanged.
"""
from scenes_lib import *

# ---- hand-drawn tiles, digits = the shade in the venue's palette (the tile's stage_a or bar colours) ----------------------------------------------------
SALOON_KIT = {
    # the wooden frame: outer ink, a lit edge, two columns of face, the inner ink (light from the top left, so the lit edge is the left one of a post, the top one of the lintel)
    "TL": ["11111111", "11111111", "11111111", "11133333", "11130000", "11130222", "11130222", "11130223"],
    "T":  ["11111111", "11111111", "11111111", "33333333", "00000000", "22222222", "22222222", "33333333"],
    "TR": ["11111111", "11111111", "11111111", "33333111", "00003111", "22223111", "22223111", "30223111"],
    "L":  ["11130223", "11130223", "10130223", "11130223", "11130223", "11130223", "11130223", "11130223"],
    "L2": ["11130223", "11130223", "11130223", "11130223", "11130223", "01130223", "11130223", "11130223"],
    "R":  ["30223111", "30223111", "30223111", "30223011", "30223111", "30223111", "30223111", "30223111"],
    "R2": ["30223111", "30223111", "30223111", "30223111", "30223111", "30223111", "30223110", "30223111"],
}
SALOON_BAR_KIT = {   # bar palette: 0 teal, 1 gold, 2 brown, 3 dark: the counter's front, two variants (the game's own counter dots, spaced)
    "F1": ["33333333", "33233333", "33333333", "33333323", "33333333", "33233333", "33333333", "33333332"],
    "F2": ["33333333", "33333323", "33333333", "32333333", "33333333", "33333233", "33333333", "33233333"],
}
IGLOO_KIT = {
    "TL": ["30130133", "31031033", "32132133", "11133333", "11130000", "11130011", "11130111", "11130113"],
    "T":  ["33103103", "33013013", "33123123", "33333333", "00000000", "00000000", "11111111", "33333333"],
    "TR": ["30130133", "31031033", "32132133", "33333111", "00003111", "00003111", "11103111", "30113111"],
    "L":  ["11130003", "11130003", "11130003", "11132223", "11130013", "11130013", "11130013", "11132223"],
    "L2": ["11130013", "11132223", "11130003", "11130003", "11130003", "11132223", "11130013", "11130013"],
    "R":  ["30003111", "30003111", "30003111", "32223111", "30003111", "30003111", "30003111", "32223111"],
    "R2": ["30003111", "32223111", "30003111", "30003111", "30003111", "32223111", "30003111", "30003111"],
}
IGLOO_BAR_KIT = {   # bar palette: 0 purple, 1 ice white, 2 light blue, 3 deep blue
    "F1": ["22222222", "11121111", "11121111", "11121111", "22222222", "11111211", "11111211", "11111211"],
    "F2": ["22222222", "11111211", "11111211", "11111211", "22222222", "11121111", "11121111", "11121111"],
}
SPACE_KIT = {
    "TL": ["33333333", "31313131", "33333333", "33322222", "33321111", "33321122", "33321122", "33321123"],
    "T":  ["33333333", "13131313", "33333333", "22222222", "11111111", "22222222", "22222222", "33333333"],
    "TR": ["33333333", "31313131", "33333333", "22222333", "11112333", "22222333", "22222333", "32212333"],
    "L":  ["12222232", "12222232", "12222232", "12220132", "12221132", "12222232", "12222232", "12222232"],
    "L2": ["12222232", "12222232", "12222232", "12222232", "12221132", "12220132", "12222232", "22222232"],
    "R":  ["32122222", "32122222", "32122222", "32122222", "32122222", "32122222", "32122222", "32122222"],
    "R2": ["32122222", "32122222", "32122222", "32102222", "32112222", "32122222", "32122222", "32122222"],
}
SPACE_BAR_KIT = {   # bar palette: 0 navy, 1 white, 2 grey, 3 ink: the counter's front: the gold-grey rail's lower half and a hull plate
    "F1": ["33333333", "22222222", "22222222", "33333333", "22221222", "22221222", "22221222", "33333333"],
    "F2": ["33333333", "22222222", "22222222", "33333333", "22212222", "22212222", "22212222", "33333333"],
}

# ---- the maps: 13 rows of 20 cells. Tokens: S<c>_<r> stage tile, B<c>_<r> bar tile, a kit name, w the wall's game parity pattern (D / E by column + row), . the portrait's cell ----
SAL_MAP = [
    "S0_0 S1_0 w w w TL T T T T T T T TR w w w w S18_0 S19_0",
    "S0_1 S1_1 w w w L . . . . . . . R w w w w S18_1 S19_1",
    "S0_2 S1_2 w w w L2 . . . . . . . R2 w w w w S18_2 S19_2",
    "S0_0 S1_0 w w w L . . . . . . . R w w w w S18_0 S19_0",
    "S0_1 S1_1 w w w L2 . . . . . . . R2 w w w w S18_1 S19_1",
    "S0_2 S1_2 w w w L . . . . . . . R w w w w S18_2 S19_2",
    "S0_0 S1_0 w w w L2 . . . . . . . R2 w S14_1 w w S18_0 S19_0",
    "S0_1 S1_1 w w w L . . . . . . . R S13_2 S14_2 w w S18_1 S19_1",
    "g g g g g g g g g g g g g g S13_3 g g g g g",
    "b b b b b b b b b b b b b b b b b b b b",
    "b b b b b b b b b b b b b b b b b b b b",
    "b b b b b b b b b b b b b b b b b b b b",
    "F1 F2 F1 F2 F1 F2 F1 F2 F1 F2 F1 F2 F1 F2 F1 F2 F1 F2 F1 F2",
]
IGL_MAP = [
    "i i i i i TL T T T T T T T TR i i i i i i",
    "S5_1 S6_1 S7_1 S8_1 a1 L . . . . . . . R b1 a1 b1 a1 a1 a1",
    "S5_2 S6_2 S7_2 S8_2 a1 L2 . . . . . . . R2 b1 a1 b1 a1 a1 a1",
    "a1 a1 a1 b1 b1 L . . . . . . . R a1 b1 b1 a1 a1 a1",
    "a1 a1 a1 b1 b1 L2 . . . . . . . R2 b1 a1 a1 b1 a1 a1",
    "a1 a1 a1 b1 b1 L . . . . . . . R b1 b1 a1 a1 a1 a1",
    "a1 a1 a1 b1 b1 L2 . . . . . . . R2 b1 S12_1 S13_1 S14_1 a1 a1",
    "a1 a1 a1 b1 b1 L . . . . . . . R S11_2 S12_2 S13_2 a1 a1 a1",
    "g g g g g g g g g g g g g g g S12_3 S13_3 g g g",
    "b b b b b b b b b b b b b b b b b b b b",
    "b b b b b b b b b b b b b b b b b b b b",
    "b b b b b b b b b b b b b b b b b b b b",
    "F1 F2 F1 F2 F1 F2 F1 F2 F1 F2 F1 F2 F1 F2 F1 F2 F1 F2 F1 F2",
]
SPA_MAP = [
    "i i i i i TL T T T T T T T TR i i i i i i",
    "p p p p p L . . . . . . . R p p p p p p",
    "p p p p p L2 . . . . . . . R2 p p p p p p",
    "p p p p p L . . . . . . . R p p p p p p",
    "p p p p p L2 . . . . . . . R2 p p p p p p",
    "p p S5_1 S6_1 p L . . . . . . . R p p S12_1 S13_1 p p",
    "p p S5_2 S6_2 p L2 . . . . . . . R2 p p S12_2 S13_2 p p",
    "p p p p p L . . . . . . . R p p p p p p",
    "g g g g g g g g g g g g g g g g g g g g",
    "b b b b b b b b b b b b b b b b b b b b",
    "b b b b b b b b b b b b b b b b b b b b",
    "b b b b b b b b b b b b b b b b b b b b",
    "F1 F2 F1 F2 F1 F2 F1 F2 F1 F2 F1 F2 F1 F2 F1 F2 F1 F2 F1 F2",
]


def keyed(venue, kit_stage, kit_bar):
    sp = json.load(open(VEN / f"{venue}_pal.json"))
    ks = {str(i): (i, sp["stage_a"]["hex"][i]) for i in range(4)}
    kb = {str(i): (i, sp["bar"]["hex"][i]) for i in range(4)}
    lib = {}
    lib.update(kit(ks, kit_stage))
    lib.update(kit(kb, kit_bar))
    return lib


def build(venue, owner, cx, cell_map, kit_stage, kit_bar, over=None):
    st = venue_tiles(venue, "stage", "stage_a")
    bar = venue_tiles(venue, "bar", "bar")
    lib = keyed(venue, kit_stage, kit_bar)
    page = Page(f"{venue}_A", (0, "#000000"))
    pix, bg = read_portrait(owner)
    for cy, line in enumerate(cell_map):
        toks = line.split()
        assert len(toks) == 20, (venue, cy, len(toks))
        for c, t in enumerate(toks):
            if t == ".":
                continue
            if t == "w":
                t = "S2_0" if (c + cy) % 2 == 0 else "S3_0"
            elif t == "g":       # the ledge: the game's plain pair (cols 0 and 1)
                t = f"S{c % 2}_3"
            elif t == "b":
                t = f"B{c}_{cy - 9}"
            elif t == "i":
                t = f"S{c}_0"
            elif t == "a1":
                t = "S0_1"
            elif t == "b1":
                t = "S3_1"
            elif t == "p":     # space: the plain panel, the game's own two (col parity)
                t = "S0_1" if c % 2 == 0 else "S3_1"
            if t[0] in "SB" and "_" in t and t[1:2].isdigit():
                a, b = t[1:].split("_")
                tile = (st if t[0] == "S" else bar)[(int(a), int(b))]
            else:
                tile = lib[t]
            page.tile(c, cy, tile, t)
    page.portrait(pix, cx, 1, over)
    return page


def saloon():
    return build("saloon", "sadie", 6, SAL_MAP, SALOON_KIT, SALOON_BAR_KIT)


def igloo():
    return build("igloo", "aurora", 6, IGL_MAP, IGLOO_KIT, IGLOO_BAR_KIT)


def space():
    return build("space", "zizz", 6, SPA_MAP, SPACE_KIT, SPACE_BAR_KIT)


if __name__ == "__main__":
    import sys
    out = Path(sys.argv[1])
    for fn, v, o in ((saloon, "saloon", "SADIE"), (igloo, "igloo", "AURORA"), (space, "space", "ZIZZ")):
        p = fn()
        for cgb in (False, True):
            page_card(p, v, o, cgb).save(out / f"A_{v}_{'cgb' if cgb else 'dmg'}.png")
        pals, attr, n = p.palettes()
        print(v, "tiles", p.unique_tiles(), "flip-merged", p.unique_tiles_flip(), "palettes", len(pals))
