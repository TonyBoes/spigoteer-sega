"""Proposed boss texts. Each boss: id, name, p1, p2, optional p3 (shared icon page), banner (l1,l2), reasons, disagreements."""

ICONS = ["MUG ICONS BY HIM:", "BRIGHT: THROW MORE", "DARK: HE HOLDS ONE", "FULL UP: IT BREAKS"]

B = []

B.append(dict(
    key="B_TEX", name="BIG TEX", id=0,
    p1=["SEND TEX 8 MUGS.", "HITS PUSH HIM BACK", "IF HE REACHES TAP,", "YOU LOSE A LIFE."],
    p2=["HE SENDS EMPTIES", "BACK UP HIS BAR.", "CATCH EACH AT THE", "TAP OR LOSE A LIFE"],
    p3=ICONS,
    banner=("BIG TEX STOMPS IN", "SLIDE HIM 8 MUGS"),
    why=[
        "P1: 'TEX STOMPS TO TAP' is a fragment (to THE tap?) and the lines read as four slogans. Now: what to do (send 8 mugs), what a hit does, what costs a life.",
        "P2: 'HE HOLDS 3 MUGS, THE 4TH ONE BREAKS' is true (hands 3) but 'MUGS' means his empties and yours alike. Now says what the player must do with his empties (catch them at the tap, else a life); the hands rule moves to the icon page.",
        "Banner: 'RIDES IN' is wrong, he walks in (E8 'the swagger'; 'riding in on a horse' is listed as NOT built). 'QUENCH HIM' is a pun that hides the task; 'SLIDE HIM 8 MUGS' says it.",
    ],
    dis=["Doc 3.3 says 'Each sarsaparilla knocks him back two hops': code push 16 px = two 8 px hops. Agrees.",
         "boss_big_tex.c says 'the tutorial boss, no special'. Agrees. (Doc 3.3's old suggested PRE_SALOON text 'WATCH FOR BIG TEX' is not in the built story script.)"],
))

B.append(dict(
    key="B_MASC", name="THE MASCOT", id=1,
    p1=["10 MUGS BEAT HIM.", "HE CROUCHES, THEN", "JUMPS TO ANOTHER", "BAR: DUST MARKS IT"],
    p2=["HE WAITS FOR MUGS", "ALREADY SLIDING.", "A MUG THROWN AFTER", "HE LEAVES BREAKS."],
    p3=ICONS,
    banner=("THE MASCOT JUMPS", "FOLLOW HIM 10 MUGS"),
    why=[
        "P1: 'HE HOPS TO ANOTHER / BAR. DUST SHOWS...' broke the sentence after 'ANOTHER'. Now the win condition is first (meter is 10) and the jump is one sentence over three lines, with the crouch (the 1 s tell) named.",
        "P2: 'A MUG AT HIS OLD / BAR BREAKS' broke mid-phrase and was vague ('at' = thrown at). Code: he leaps only after mugs already on his bar have reached him (max 60 frames); a mug thrown into the crouch that is still short of him when he goes slides on and breaks. Now says exactly that.",
        "Banner: fine; kept (a test pins it: tests/test_boss_mascot.py:73).",
    ],
    dis=["boss_mascot.c header says gulp 24; boss.c rows[1] and the doc 3.2 say 34 (the 2011c71 slowdown). Code row wins: 34. Header comment is stale, harmless."],
))

B.append(dict(
    key="B_SASQ", name="SASQUATCH", id=2,
    p1=["12 COFFEES WIN.", "HE DUCKS, VANISHES", "AND POPS UP WHERE", "FOOTPRINTS BLINK."],
    p2=["HIS EMPTIES COME", "BACK 2X AS FAST.", "A MUG SENT TO THE", "EMPTY BAR BREAKS."],
    p3=ICONS,
    banner=("THE SASQUATCH HIDES", "12 COFFEES BEAT HIM"),
    why=[
        "P1: 'HE DUCKS, VANISHES / THEN POPS UP WHERE / FOOTPRINTS BLINK / GO THERE FIRST' lacked how to win and 'GO THERE FIRST' is an order with no reason. Now: the goal, then the trick as one sentence. The player infers 'go to the footprints' from 'pops up where footprints blink'.",
        "P2 is new: the original page 2 was only the shared mug rule. The facts that hurt: his empties return at 1 px/frame (twice normal, code and doc agree) and while he is gone his old bar has no catcher, so a mug sent there breaks (a life).",
        "Banner: 'NO SUCH THING' is a joke with no meaning for a first-time player ('no such thing as Sasquatch'). 'THE SASQUATCH HIDES / 12 COFFEES BEAT HIM' says the trick and the goal. (Pinned by tests/test_boss_sasquatch.py:46: update with the change.)",
    ],
    dis=["Doc 3.5 says he vanishes after 'at least 36 frames' of ducking, then waits up to 150 frames for mugs; code constants SASQ_DUCK 36, SASQ_WAITMAX 150. Agrees.",
         "Doc 3.2 table lists his meter 12, code 12. Agrees."],
))

B.append(dict(
    key="B_CRIT", name="THE FOOD CRITIC", id=3,
    p1=["8 PERFECT POURS", "BEAT THE CRITIC.", "RELEASE A WHEN THE", "WINE SPARKLES."],
    p2=["SLOPPY OR BUSY:", "HE WAVES IT BACK.", "CATCH IT AT TAP,", "OR LOSE A LIFE."],
    p3=None,
    banner=("THE CRITIC DINES", "PERFECT POURS ONLY"),
    why=[
        "P1: kept the idea ('PERFECT POURS ONLY', 'LET GO WHEN') but added the goal (8) and named the button. 'GLOWS WHITE' replaced with 'SPARKLES': the code and doc call the window the 'sparkle frame'; I could not confirm from the code that it is white (see doubts).",
        "P2: the original page 2 ('EMPTY MUG: THROW / FULL MUG: BUSY / SHAKING: SENT BACK / CATCH THEM AT TAP') describes the status tag that the owner had REMOVED on 2026-10-17 ('get rid of the drink arrow on the bosses'). There is no shaking mug any more. What really happens: a sloppy pour he tastes, or any drink while he holds his glass or tastes, is waved back as a full mug the bartender must catch at the tap (a miss is a life; a bubble 'NO!' or 'BAD' shows).",
        "No icon page: with hands 1 the indicator is one mug icon that goes dark while he is busy; P2 says it in plain words.",
        "Banner: fine; kept.",
    ],
    dis=["Doc 3.6: 12-frame perfect window. Code CRIT_WIN 12 (the story's own pour window is 5). Agrees.",
         "Doc 3.6 says 'hands 1: a busy critic waves drinks back'. Code agrees, but also caps the waiting returns at CRIT_QUEUE 3 and then a drink breaks; not on the card (rare)."],
))

B.append(dict(
    key="B_YETI", name="THE YETI", id=4,
    p1=["12 COCOAS BEAT HIM", "HE BLOWS FROST ON", "HIS BAR. YOUR TAP", "THERE FREEZES."],
    p2=["THROW ONE BEFORE", "THE ICE, OR SERVE", "REGULARS, THEN BE", "BACK FOR EMPTIES."],
    p3=ICONS,
    banner=("THE YETI IS COLD", "12 COCOAS ON ICE"),
    why=[
        "P1: the original ('HE BLOWS ICE ONTO / HIS BAR. THE TAP / FREEZES: NO THROWS / AT HIM WHILE ICY') was accurate but had no goal; 'WHILE ICY' is jargon. Now goal first, then the trick: the tap on his bar freezes (it is the owner's 'frozen tap' rework).",
        "P2: the original page 2 had 'THROW ONE BEFORE THE FROST COMES' and then the shared mug rule. Kept the advice (it is the design intent in the doc: one last mug before the frost, or serve other bars) and added what hurts: his empties come back at 1 px/frame during the ice, so be at his tap for them. The ice lasts 3 s (180 frames), too long to fit in a line.",
        "Banner: 'THE YETI IS COLD' fine; '12 COCOAS ON ICE' is a pun that still states the goal; kept.",
    ],
    dis=["Doc 1.2 (the original pitch table) says 'icy mugs 2x'; code and doc 3.7 say full mugs 3 px/frame (3x), empties 1 px/frame. Code wins; not on the card."],
))

B.append(dict(
    key="B_PROT", name="THE PROTOTYPE", id=5,
    p1=["12 BATTERIES WIN.", "GREEN LAMP: THROW", "YELLOW: STOP SOON", "RED: THEY BOUNCE"],
    p2=["RED BOUNCES THEM", "BACK: CATCH THEM.", "MISS ONE: A LIFE.", "THEN HE MOVES BARS"],
    p3=None,
    banner=("GREEN MEANS GO", "RED MEANS STOP"),
    why=[
        "P1: the original ('WATCH HIS LAMP / GREEN: THROW / YELLOW: STOP / RED: MUGS BOUNCE') was the clearest of the ten; kept its shape, added the goal, and fixed YELLOW: in code yellow still takes a battery, it is the 60-frame warning, so 'STOP SOON' not 'STOP'.",
        "P2: the original was the shared mug rule. In the Prototype's fight the icons are different (no limit, only the held ones show), so 'EMPTY MUG: THROW / FULL MUG: BUSY' was misleading. Now: what red does to every battery on his bar and why it matters (they return like empties: catch them at the tap, a miss is a life), and the second trick (after red he rides to another bar; the landing marker shows for the last second).",
        "Banner: fine; kept (pinned by tests/test_boss_prototype.py:87).",
    ],
    dis=["Doc 3.8 and code agree on the cycle 240 green, 60 yellow, 150 red, 10 ride. The tag/legend for this boss: the engine shows only the 'taken' mugs (room_free 254 when boss_cap > 9) so there is no bright 'room' icon."],
))

B.append(dict(
    key="B_DUKE", name="DUKE", id=6,
    p1=["12 MILKS BEAT DUKE", "REVS, THEN LURCHES", "IF HE REACHES TAP,", "YOU LOSE A LIFE."],
    p2=["A MUG DURING A REV", "STOPS HIS LURCH.", "HE REVS SOONER AS", "HIS SHAKE FILLS."],
    p3=ICONS,
    banner=("THE BIGGEST SHAKE", "12 MILKS FOR DUKE"),
    why=[
        "P1: 'REVS, THEN LURCHES' is honest to the code (rev 50 frames, then a 16 px lurch in 8 frames). The original ('DUKE REVS, THEN / LURCHES AT THE TAP / A MUG WHILE HE / REVS STALLS HIM') split the key rule across two cards and broke 'A MUG WHILE HE / REVS'. The rule 'a mug during the rev stalls him' now sits whole on page 2; page 1 has the goal and the one thing he does.",
        "P2 adds a fact the player cannot see otherwise: his idle time before the next rev is 150, 120, then 90 frames as the meter falls (boss_duke.c), so he gets pushier toward the end. 'Shake' = the milkshake meter.",
        "Banner: fine; kept (pinned by tests/test_boss_duke.py:78).",
    ],
    dis=["Doc 3.12 text above 'as built' says he rolls in on a bike and the bike lurches; the code: he STANDS behind the bar, no bike in the fight (only in the entrance, 62 frames). The card never mentions a bike. Agrees with code.",
         "Doc 3.2 table row 'Duke (PROPOSAL)' is the proposal; the code row: step 0, push 16, gulp 30 (header comment in boss_duke.c says 20; rows[6] says 30). Row wins."],
))

B.append(dict(
    key="B_SUMO", name="SUMO CHAMPION", id=7,
    p1=["PUSH HIM OFF THE", "LEFT END TO WIN.", "IF HE REACHES TAP,", "YOU LOSE A LIFE."],
    p2=["EACH FULL METER", "SHOVES HIM BACK.", "NEXT: ONE SHORTER.", "A STAMP? FEED HIM!"],
    p3=None,
    banner=("THE CHAMPION", "PUSH HIM OUT"),
    why=[
        "P1: the original ('NO DRINK LIMIT / FILL THE METER TO / SHOVE HIM BACK / PUSH HIM OUT!') never said that the way to WIN is to push him off the bar's left end, nor that reaching the tap costs a life. Now both.",
        "P2: the meter (a full one shoves him back 32 px, the next is one cup shorter: 6, 5, 4 ... 1) and the one special: a stamp is a charge, and any cup during the stamp calls it off (the stamp rule went here, on page 2, in place of the 'every cup fills it' line, which the HUD shows). The original had 'HE STEPS ON THE DRUM BEAT'; that is visible and audible, so dropped for space.",
        "No icon page: the Sumo has no drink limit, so the icons mean nothing (the original card, correctly, has none either).",
        "Banner: 'THE CHAMPION / PUSH HIM OUT' is accurate; kept (pinned by tests/test_boss_sumo.py:113).",
    ],
    dis=["Doc 3.2 table row for the Sumo is the OLD design: step 90, start x 16, meter 12 'single / chained hits', push 0/8. Doc 10.2 and the code: step 192 on the drum beat, start x 24, meter 6 shrinking to 1, ring-out at x 0. Code wins; card follows the code.",
         "Doc 1.2 table 'chained hits' is the old pitch."],
))

B.append(dict(
    key="B_LEO", name="LEO THE LION", id=8,
    p1=["14 COCONUTS WIN.", "HIS ROAR IS A WIND", "BLOWING MUGS BACK", "ON EVERY BAR."],
    p2=["'!!' BY HIS HEAD:", "STOP THROWING!", "CATCH THEM AT TAP", "OR LOSE A LIFE."],
    p3=ICONS,
    banner=("LEO THE LION", "14 COCONUTS WIN"),
    why=[
        "P1: the original ('HIS ROAR IS A WIND / BLOWING FULL MUGS / BACK ON EVERY BAR / CATCH THEM!') is good and accurate; kept, with the goal added and 'FULL' dropped (a player says mug, not full mug).",
        "P2: the original page 2 was the shared mug rule. The real second page is the tell: two '!' appear beside his head for a second before each roar; mugs in flight on any bar come back, to be caught at that bar's tap (a miss is a life).",
        "Banner: '14 COCONUTS NO FEAR' hints at the courage joke but 'NO FEAR' tells nothing; now '14 COCONUTS WIN'. (No test pins Leo's banner.)",
    ],
    dis=["Doc 3.11 says roar OAM 29-36; code: 30-37. Not relevant to text.",
         "Doc 1.2 'walkers jump back 16 px, drinkers send empties early' is the old pitch; built: the roar is a wind (mugs blow back); walkers are still pushed back 16 px (LEO_PUSH) but the card does not need it."],
))

B.append(dict(
    key="B_MOTH", name="THE MOTHERSHIP", id=9,
    p1=["IT JUMPS BARS:", "A BEAM SHOWS WHERE", "8 DRINKS SPLIT IT:", "MINIS WANT 2 EACH"],
    p2=["2 PASSENGERS LAND", "WITH EACH JUMP.", "STAY ON ONE BAR:", "RAY STUNS: SWITCH!"],
    p3=ICONS,
    banner=("THE MOTHERSHIP", "IT SPLITS WHEN FULL"),
    why=[
        "P1: the original facts were right; 'AFTER 8 IT SPLITS' is now 'FULL' of what: 8 drinks. The two 'beams' confuse (the landing beam and the stun ray); P1 says 'A BEAM SHOWS WHERE', P2 calls the other thing the ray.",
        "P2: 'STAYING PUT: STUN / RAY! CHANGE BARS' is cryptic. Code: if the bartender stays on one bar 270 frames (4.5 s) the ship charges for 60 frames (a blinking beam under it on HIS bar), then stuns the bartender 90 frames; any bar change in the charge dodges it. Now a sentence a player can follow.",
        "Banner: fine; kept (pinned by tests/test_boss_mothership.py:96).",
    ],
    dis=["Doc 3.10 says meter 6 and minis at x 16; code: meter 14 = 8 + 6, minis at x 24 (doc says 'as built' notes, 3.2 table lists 6 then 3 minis x 2). Code wins; card says 8 drinks then minis, which is right.",
         "The ray (phase 1 only), and the passengers, came with E7 (2026-10-15) and are not in doc 3.10's text, only in 10.2."],
))


# the shared mug rule is gone from the pages that had it
