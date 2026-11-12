"""Hand review of the ranked merges (review.py sheets): block ids that must not be changed.  The ids are the build's DMG block ids (gen_smap_world Model.sigs).
Reason per id; a protected block is never replaced by another block (it may still be the representative that others are replaced by)."""
PROTECT_WHY = {
    207: "Igloo sign: the C of COCOA turns into F.",
    341: "Saloon sign: TAPS letters change.",
    342: "Saloon sign: the P and S of TAPS change.",
    343: "Saloon sign: the S of TAPS changes.",
    386: "Lodge sign: the D and G of LODGE change.",
    642: "Factory sign: a letter of ROBOCO changes.",
    734: "Zoo sign: the Z of ZOO changes.",
    791: "Rodeo sign: the M of MILK changes.",
    832: "Zoo gate: a bar of the gate loses a pixel.",
    833: "Zoo gate: a bar of the gate loses a pixel.",
    19: "Stadium (owner 11-11, uneven line): the roofline of the stands above the flag grows by 1 px (19 > 313, also shown in one Zoo cell).",
    189: "Stadium lawn, lower right edge (owner 11-11, uneven line): 5 px of the lawn outline step change (189 > 161).",
    235: "Igloo: the penguin's chest.",
    208: "Igloo sign: the A of COCOA changes.",
    387: "Lodge sign: a letter of LODGE changes.",
    643: "Factory sign: a letter of ROBOCO changes.",
    735: "Zoo sign: a Z or O of ZOO changes.",
    736: "Zoo sign: a Z or O of ZOO changes.",
    737: "Zoo sign: a Z or O of ZOO changes.",
}
PROTECT = set(PROTECT_WHY)
VETO = set()
CAP = 40           # shade steps changed on the map by one merge: costlier merges are not offered (road hatch 825 px, desert edge 378 px, pine foot 84 px ...)
