"""Typed art of the falls v2 options (see falls_v2.py for the alphabet).  A row is a list of (x, string) runs: the string starts at absolute map x (y is the key).
The approved column is x 372..379, its bank rim x 371 and 380 (cell edges at x 368, 376, 384); the foot line of the mountain is y 39 (ink); cell rows: y 32..39 is row 4."""
OPTIONS = {}


def merge(*parts):
    out = {}
    for p in parts:
        for y, runs in p.items():
            out.setdefault(y, []).extend(runs)
    return out


# the approved column's top, shared: rim x 371 and 380 (white foam) from y 36, dark channel edge before it
COLUMN_TOP = {
    34: [(371, "2wwwwwwww")],
    35: [(371, "2wwwwwwww2")],
    36: [(371, "0wwwwwwww0")],
    37: [(371, "0wwwwwwww0")],
    38: [(371, "0wwwwwwww0")],
    39: [(371, "0wwwwwwww0")],
}

# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# A: a small cleft partway up the right flank, a narrow cascade (thread with a shadow on its left) that flares into the column; rock shelves step down to the water from both sides
A_FACE = {
    21: [(377, "333")],
    22: [(376, "32223")],
    23: [(376, "32DB3")],
    24: [(377, "2ge")],
    25: [(377, "2ge")],
    26: [(376, "2bge")],
    27: [(376, "2bge")],
    28: [(376, "2bge")],
    29: [(375, "2dbge")],
    30: [(375, "2dbge")],
    31: [(375, "2dbge")],
    32: [(373, "2wwdbge")],
    33: [(372, "2wwwdbge")],
}
A_SHELVES = {                            # bands of shade over a shorter ink underline, stepping down toward the water (the mountain's own strata and crease grammar)
    33: [(361, "2222222")],
    34: [(362, "33333"), (385, "22222222")],
    35: [(364, "2222222"), (386, "333333")],
    36: [(365, "33333"), (382, "2222222")],
    37: [(367, "2222"), (383, "33333")],
    38: [(368, "33"), (381, "2222")],
}
OPTIONS["A"] = dict(rows=merge(A_FACE, COLUMN_TOP, A_SHELVES), title="A: cleft partway up the right flank, narrow cascade, approved column")

# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# B: a notch just under the snow line, a gully cut into the face (dark walls both sides), a lip, a short drop that fans out into the column; a rib and a shelf at the foot
B_FACE = {
    15: [(376, "33")],
    16: [(375, "3223")],
    17: [(374, "22DBG2")],
    18: [(374, "22DBG2")],
    19: [(374, "22DBG2")],
    20: [(373, "22DBG2")],
    21: [(373, "22DBG2")],
    22: [(373, "22DBG2")],
    23: [(374, "22DBG2")],
    24: [(374, "22dbg2")],
    25: [(374, "22dbg2")],
    26: [(374, "22dbg2")],
    27: [(374, "22dbg2")],
    28: [(375, "22bge2")],
    29: [(375, "22bge2")],
    30: [(375, "22bge2")],
    31: [(372, "33332"), (377, "bge"), (380, "33")],
    32: [(373, "2wwwwww")],
    33: [(372, "2wwwwwww")],
}
B_FOOT = {
    30: [(361, "3")],
    31: [(362, "32")],
    32: [(363, "322")],
    33: [(364, "3222")],
    34: [(366, "3222")],
    35: [(366, "3222"), (383, "222")],
    36: [(369, "32"), (382, "2100122")],
    37: [(382, "2111222")],
    38: [(382, "3222223")],
}
OPTIONS["B"] = dict(rows=merge(B_FACE, COLUMN_TOP, B_FOOT), title="B: notch under the snow line, gully, lip, short drop")
