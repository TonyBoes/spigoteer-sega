"""REVISION 2 (owner 2026-11-03: no lines about losing a life: that is normal play). Applied over data.py by render.py."""
ICONS = ["MUG ICONS BY HIM:", "BRIGHT: HAS ROOM", "DARK: HE HOLDS ONE", "ALL DARK: WAIT."]
R2 = {
 "B_TEX": (["SEND TEX 8 MUGS.", "HITS PUSH HIM BACK", "HE HOLDS 3 EMPTIES", "THEN SENDS THEM."], ICONS,
           ["P1: goal, what a hit does, and his hands (3 empties). The 'reaches the tap' and 'catch or lose a life' lines are gone.",
            "P2 (the icon page, kept only here): the tutorial boss is where the player first meets the icons; it tells what they cannot see (a dark icon is an empty he holds; all dark means a mug now is wasted).",
            "Banner: 'RIDES IN' was wrong (he walks in); 'SLIDE HIM 8 MUGS' states the task."]),
 "B_MASC": (["10 MUGS BEAT HIM.", "HE CROUCHES, THEN", "JUMPS TO ANOTHER", "BAR: DUST MARKS IT"], ["HE LEAVES ONCE THE", "MUGS ON HIS BAR", "HAVE REACHED HIM.", "MOVE TO THE DUST!"],
           ["P1 unchanged from proposal 1 (goal, crouch = the tell, dust = where).",
            "P2: the real rule (he waits for mugs already on his bar) and the action (move to the dust). The 'a late mug breaks' line is gone.",
            "Banner kept."]),
 "B_SASQ": (["12 COFFEES WIN.", "HE DUCKS, VANISHES", "AND POPS UP WHERE", "FOOTPRINTS BLINK."], ["HE DRINKS AT ONCE", "AND SENDS EMPTIES", "BACK 2X AS FAST.", "STAY NEAR HIS TAP."],
           ["P1 unchanged. P2: the two numbers that matter (instant drinker, empties twice as fast); the 'empty bar breaks' line is gone.", "Banner as proposed."]),
 "B_CRIT": (["8 PERFECT POURS", "BEAT THE CRITIC.", "RELEASE A WHEN THE", "WINE SPARKLES."], ["SLOPPY OR BUSY:", "HE WAVES IT BACK.", "CATCH IT AT THE", "TAP, TRY AGAIN."],
           ["P1 unchanged. P2: what happens to a sloppy pour or one sent while he is busy, and what to do; the 'or lose a life' tail is gone.", "Banner kept."]),
 "B_YETI": (["12 COCOAS BEAT HIM", "HE BLOWS FROST ON", "HIS BAR. YOUR TAP", "THERE FREEZES."], ["THROW ONE BEFORE", "THE ICE, OR SERVE", "REGULARS, THEN BE", "BACK FOR EMPTIES."],
           ["Unchanged from proposal 1 (neither page was about life loss).", "Banner kept."]),
 "B_PROT": (["12 BATTERIES WIN.", "GREEN LAMP: THROW", "YELLOW: STOP SOON", "RED: THEY BOUNCE"], ["RED BOUNCES THEM", "BACK: CATCH THEM.", "THEN HE RIDES TO", "THE MARKED BAR."],
           ["P1 unchanged. P2: 'MISS ONE: A LIFE' removed; the freed line names the second trick (he rides to the marked bar).", "Banner kept."]),
 "B_DUKE": (["12 MILKS BEAT DUKE", "REVS, THEN LURCHES", "A MUG DURING A REV", "STALLS HIM."], ["HE IDLES LESS AS", "HIS SHAKE FILLS:", "KEEP A MUG READY", "FOR EACH REV."],
           ["P1: 'IF HE REACHES TAP' removed; the stall rule (his key trick) moves up to page 1. 'REVS, THEN LURCHES' is honest to the code (rev 50 frames, lurch 16 px in 8).",
            "P2: his idle shrinks 150, 120, 90 frames as the meter falls, so the rev comes sooner (boss_duke.c). Kept because the player cannot see it coming.", "Banner kept."]),
 "B_SUMO": (["PUSH HIM OFF THE", "LEFT END TO WIN.", "EACH FULL METER", "SHOVES HIM BACK."], ["NEXT METER: ONE", "CUP SHORTER.", "HE STAMPS, THEN", "CHARGES. FEED HIM!"],
           ["P1: how to win and the meter. P2: the shrinking meter and the stamp rule (a cup during the stamp calls the charge off). The 'reaches the tap' lines are gone.", "Banner kept."]),
 "B_LEO": (["14 COCONUTS WIN.", "HIS ROAR IS A WIND", "BLOWING MUGS BACK", "ON EVERY BAR."], ["'!!' BY HIS HEAD:", "ROAR IS COMING.", "STOP THROWING,", "WAIT IT OUT."],
           ["P1 unchanged. P2: the tell and the action; the 'catch them or lose a life' tail is gone.", "Banner as proposed."]),
 "B_MOTH": (["IT JUMPS BARS:", "A BEAM SHOWS WHERE", "8 DRINKS SPLIT IT:", "MINIS WANT 2 EACH"], ["2 PASSENGERS LAND", "WITH EACH JUMP.", "STAY ON ONE BAR:", "RAY STUNS: SWITCH!"],
           ["Unchanged (no life-loss line).", "Banner kept."]),
}


def apply(data):
    data.ICONS = ICONS
    for b in data.B:
        p1, p2, why = R2[b["key"]]
        b["p1"], b["p2"], b["p3"], b["why"] = p1, p2, None, why
        if b["key"] != "B_TEX":
            b["dis"] = b["dis"]
