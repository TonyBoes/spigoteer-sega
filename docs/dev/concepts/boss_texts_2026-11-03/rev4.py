"""REVISION 4 (owner 2026-11-03): each card covers only what is unique to that boss; Big Tex explains what every boss does.
Icons in a line: \x01 = the ROOM mug (a free hand, bright), \x02 = the TAKEN mug (an empty he holds, dark with a bright rim): the capacity
indicator's tiles (assets/art/boss/tag.txt) as BG tiles. Each icon is one column. HELD = today's text stays (owner will playtest / rethink).
Applied by render_rev4.py. None as page 2 = no second page."""
R, T = "\x01", "\x02"
HELD = "HELD"
R4 = {
 "B_TEX": (["EVERY BOSS WALKS", "TO YOUR TAP. A MUG", "PUSHES HIM BACK", "AND FILLS HIM UP."],
           [R*3 + " HE HAS ROOM", T + R*2 + " HOLDING ONE", T*3 + " HANDS FULL:", "NEXT MUG BREAKS."]),
 "B_MASC": (["HE JUMPS TO A NEW", "BAR NOW AND THEN.", "WHEN HE CROUCHES,", "HOLD YOUR MUGS."], None),
 "B_SASQ": (["HE VANISHES, THEN", "POPS UP ON ANOTHER", "BAR. WATCH OUT!"],
            ["HE DRINKS FAST AND", "HIS EMPTIES SLIDE", "BACK REAL FAST."]),
 "B_CRIT": HELD,
 "B_YETI": "REV3",   # rev2.R2["B_YETI"], unchanged
 "B_PROT": (["GREEN: SERVE HIM.", "YELLOW: GET READY.", "RED: HIS BELT RUNS", "BACKWARDS."],
            ["THEN HE MOVES TO", "ANOTHER BAR."]),
 "B_DUKE": (["HE LURCHES FORWARD", "IN BURSTS. A MUG", "DURING HIS REV", "STOPS THE LURCH."],
            ["THE MORE HE DRINKS", "THE SOONER HE", "REVS AGAIN."]),
 "B_SUMO": (["PUSH HIM OUT OF", "THE TEAHOUSE TO", "WIN. EACH PUSH", "NEEDS FEWER CUPS."], None),
 "B_LEO": HELD,
 "B_MOTH": HELD,
}
