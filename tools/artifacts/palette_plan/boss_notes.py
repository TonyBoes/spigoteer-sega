"""What the Palette Plan page's boss section says and draws beyond the body poses (read by build.py boss_section).

Everything here is sourced from src/boss.c (the engine: topper, hand mug, capacity mugs), src/boss.h, src/boss_<name>.c (each
boss's tells and entrance), tools/gen_boss.py (BOSSES: poses, hats, fx) and assets/art/boss/*.txt. A "?" marks a guess.

Coordinates are in px from the body's top-left corner (the 16 body rows); the topper sits at y -8.
Colour keys: body (BG 4), top (OBJ 7, the topper), ring (OBJ 5), red (OBJ 4), mug (OBJ 1, the served drink), cap (OBJ 2, the empty glass),
bar (BG 0, the counter), bg7 (BG 7, the conveyor).
"""

EXTRA = dict(big_tex=["BARE"], sasquatch=["DUCK", "BURST1", "BURST2"], critic=["TASTE", "HOLD", "HOLDHOP"], yeti=["INHALE", "BLOW"],
             sumo=["SHIKO", "HMPH"], leo=["INHALE", "ROAR"], mascot=["CROUCH", "PUFF1", "PUFF2"], prototype=["RED"],
             duke=["TELL1", "TELL2"], mothership=[])
HANDS = dict(big_tex=3, mascot=2, sasquatch=2, critic=1, yeti=2, prototype=2, duke=2, sumo=2, leo=2, mothership=2)   # boss.c rows[]
HAND_BASE = dict(big_tex=15, mascot=15, sasquatch=15, critic=12, yeti=15, prototype=11, duke=12, sumo=None, leo=15, mothership=None)  # boss.c hand_base

# per pose overrides (key: pose name): hat = (block, colour key) or None for no topper; caps = (TAKEN, ROOM) or None for none;
# hand = False for no hand mug (default: on in GULP); add = [(file, block, x, y, colour key, behind the body)]
OVR = dict(
    big_tex=dict(BARE=dict(hat=None, caps=None, add=[("big_tex", "HAT_POP%d" % k, 8 * k, -18, "top", False) for k in range(4)])),
    mascot=dict(CROUCH=dict(hat=("HAT_BOB", "top")), PUFF1=dict(hat=None, caps=None), PUFF2=dict(hat=None, caps=None)),
    sasquatch=dict(DUCK=dict(hat=("HAT_DUCK", "top")), BURST1=dict(hat=None, caps=None), BURST2=dict(caps=None)),
    critic=dict(WALK=dict(caps=(0, 1)), STOMP=dict(caps=(0, 1)), GULP=dict(caps=(1, 0)), WINCE=dict(caps=(1, 0)), TASTE=dict(caps=(1, 0)),
                HOLD=dict(caps=(1, 0)), HOLDHOP=dict(caps=(1, 0))),
    yeti={},
    prototype=dict(RED=dict(hat=("LAMP_X", "red"), caps=None)),
    duke=dict(TELL2=dict(hat=("HAT_BOB", "top"))),
    sumo=dict(WALK=dict(caps=(1, 0)), STOMP=dict(caps=(1, 0)), GULP=dict(caps=(1, 0)), WINCE=dict(caps=(1, 0)), SHIKO=dict(caps=(1, 0)),
              HMPH=dict(caps=(1, 0)), HAPPY=dict(caps=None)),
    leo=dict(ROAR=dict(caps=(2, 0), add=[("leo_fx", "ARC1", 28, -4, "top", False)]),
             INHALE=dict(add=[("leo", "BANG", 32, 0, "body", False)])),
    mothership=dict(HAPPY=dict(hat=("HAT_BOB", "top")),
                    GULP=dict(add=[("mothership", "BEAM1", 11, 15, "top", False), ("mug", "", 11, 4, "mug", True)])),
)
# extra pictures: label, base pose, the same keys as OVR
ADD = dict(
    critic=[("TASTE NO", "TASTE", dict(add=[("critic", "NO_L", 38, -1, "top", False), ("critic", "NO_R", 46, -1, "top", False)])),
            ("TASTE BAD", "TASTE", dict(add=[("critic", "BAD_L", 38, -1, "top", False), ("critic", "BAD_R", 46, -1, "top", False)]))],
    prototype=[("WALK YELLOW", "WALK", dict(hat=("LAMP_RING", "ring")))],
    mothership=[("TELL", "WALK", dict(hat=("HAT_BOB", "top")))],
)
# small separate pictures of what lives on another bar or on the counter: label, [(file, block, x, y)], colour key (colour 0 = the wall,
# or for bar / bg7 that palette's own colour 0), width in px
SIDE = dict(
    mascot=[("MARKER", [("mascot", "MARKER", 0, 0)], "body", 16)],
    sasquatch=[("FOOTPRINTS", [("sasquatch", "MARKER", 0, 0)], "body", 16)],
    leo=[("ARC1", [("leo_fx", "ARC1", 0, 0)], "top", 8), ("ARC2", [("leo_fx", "ARC2", 0, 0)], "top", 8)],
    mothership=[("BEAM", [("mothership", "BEAM", 0, 0), ("mothership", "BEAM", 8, 0)], "body", 16),
                ("BEAM1", [("mothership", "BEAM1", 0, 0)], "top", 8), ("BEAM2", [("mothership", "BEAM2", 0, 0)], "top", 8)],
    yeti=[("ICE", [("yeti", "ICE_A", 0, 0), ("yeti", "ICE_B", 8, 0), ("yeti", "ICE_A", 16, 0), ("yeti", "ICE_B", 24, 0)], "bar", 32),
          ("SPARKS", [("yeti", "SPARK%d" % k, 8 * (k - 1), 0) for k in range(1, 5)], "bar", 32)],
    prototype=[("CONVEYOR", [("prototype", "CONV_A", 0, 0), ("prototype", "CONV_B", 8, 0), ("prototype", "CONV_A", 16, 0), ("prototype", "CONV_B", 24, 0)], "bg7", 32),
               ("MARKER", [("mascot", "MARKER", 0, 0)], "body", 16)],
)

# The owner's list above the pictures: (label, text) per boss. Plain words, one line each.
DESC = dict(
    big_tex=[
        ("WALK", "standing on his bar; the default"),
        ("STOMP", "one 8 px step toward the tap (every 2 s); the hat bobs a row down"),
        ("GULP", "he caught a served mug (3 hands): hand mug up, 58 frames"),
        ("WINCE", "pushed back 16 px after the catch"),
        ("HAPPY", "the outro, he is full"),
        ("BARE", "entrance only: bare head while the whole hat pops up for the bow"),
        ("Tiles", "the body (5 columns) is BG; the old hand-column swaps are no longer used"),
        ("Sprites", "hat crown always; hand mug in GULP; capacity mugs above-right (3 hands: shown 2 TAKEN + 1 ROOM); 4 hat-pop sprites in the entrance"),
        ("Entrance", "swaggers in as sprites made of his body tiles, bows, tips the hat, then the BG body takes over"),
    ],
    mascot=[
        ("WALK / STOMP", "on his bar; STOMP after each 8 px step"),
        ("GULP / WINCE", "caught a mug (hand mug up) / pushed back 8 px"),
        ("HAPPY", "the outro"),
        ("CROUCH", "the leap tell, 60 frames every 5 s of walking: hat one row lower, a dust MARKER (BG) on the bar he will land on"),
        ("PUFF1 PUFF2", "in the air, 20 frames: body gone, two dust puffs (BG) where he stood; no hat, no mugs, nothing caught"),
        ("Tiles", "body, puffs and the landing marker (248-251) are BG"),
        ("Sprites", "forelock hat (OBJ 7); hand mug in GULP; capacity mugs above-right (2 hands: 1 TAKEN + 1 ROOM); the entrance ball"),
        ("Entrance", "fired from a T-shirt cannon: a spinning ball (one 16x16 sprite) lands on the marker, CROUCH, then HAPPY"),
    ],
    sasquatch=[
        ("WALK / STOMP", "on his bar; STOMP after each 8 px step"),
        ("GULP", "coffee downed in 20 frames, no sway; hand mug up"),
        ("WINCE / HAPPY", "pushed back 8 px / the outro"),
        ("DUCK", "the vanish tell, 36+ frames every 6 s of walking: sinks behind the counter, crest lowered; then he is gone and FOOTPRINTS (BG, blinking) show on the target bar"),
        ("BURST2", "he pops up on the target bar: leaves and splinters (hat shown ?)"),
        ("BURST1", "entrance only: the fist through the wall"),
        ("Tiles", "body and footprints are BG; the entrance uses no sprites"),
        ("Sprites", "crest hat (lowered in DUCK; none in BURST1 ?); hand mug in GULP; capacity mugs (2 hands)"),
    ],
    critic=[
        ("WALK / STOMP", "free: smiling, palm out; STOMP after each step"),
        ("GULP", "savouring a perfect drink, 84 frames, hand mug up"),
        ("HOLD / HOLDHOP", "holding his empty glass (HOLDHOP just after a step); it goes back after 90 frames"),
        ("TASTE", "frown and flat hand: tasting a sloppy drink or waving one back; the NO / BAD bubble shows with it"),
        ("WINCE / HAPPY", "pushed back 16 px / the outro"),
        ("Tiles", "body (the beret is BG) is BG; the hand column is not used"),
        ("Sprites", "beret stalk (the hat frames also hold cloche, glint and bubbles); NO / BAD bubble just right of him (44 frames); hand mug in GULP; one capacity mug: ROOM when free, else TAKEN"),
        ("Entrance", "a silver cloche (4 sprites) slides along his counter, a bell, the lid flies off with a glint; then he is there"),
    ],
    yeti=[
        ("WALK / STOMP", "on his bar; STOMP after each 8 px step"),
        ("GULP / WINCE", "caught a cocoa, hand mug up / pushed back 8 px"),
        ("HAPPY", "the outro"),
        ("INHALE", "the breath tell, 50 frames every 6 s of walking: cheeks puffed; frost creeps along his counter (BG ICE tiles)"),
        ("BLOW", "the first 30 frames of the 3 s ice; sparks (BG) twinkle on the counter, 2 at a time"),
        ("Tiles", "body, ice counter tiles (246-247, even and odd columns) and sparks (248-251) are BG"),
        ("Sprites", "hat (takes the body colours); hand mug in GULP; capacity mugs (2 hands)"),
        ("Entrance", "frost spreads over the counter, he steps out of it in the BLOW pose; BG only"),
    ],
    prototype=[
        ("WALK / STOMP", "GREEN: lamp solid, takes batteries as ever; STOMP after each step"),
        ("WALK YELLOW", "the tell, frames 240-299: the lamp is a ring (OBJ 5); he stands but still takes a battery"),
        ("RED", "frames 300-449: arm up, lamp an X (OBJ 4); batteries bounce back; the conveyor (BG 7) runs on his counter; the last 60 frames show the MARKER on the next bar"),
        ("GULP / WINCE", "caught a battery, hand mug up / pushed back 8 px"),
        ("HAPPY", "the outro"),
        ("Tiles", "body, conveyor (246-247) and marker (248-251) are BG"),
        ("Sprites", "lamp (green, ring, X by phase); hand mug in GULP; capacity mugs (none in RED: no limit, only held glasses shown ?)"),
        ("Entrance", "lowered by a crane: body as sprites on OBJ 5, yoke and chain, then sparks; then the BG body"),
    ],
    duke=[
        ("WALK / STOMP", "idle: shakes with the engine, WALK and STOMP every 8 frames; he never steps (step 0)"),
        ("TELL1 TELL2", "the rev, 50 frames: winding a throttle, helmet jumping 1 px (the lower hat frame); then a 16 px lurch in TELL2"),
        ("GULP / WINCE", "caught a milk, hand mug up, 30 frames / pushed back 16 px"),
        ("HAPPY", "the outro"),
        ("Tiles", "body (5 columns) is BG"),
        ("Sprites", "red helmet with a white stripe (own colours); hand mug in GULP; capacity mugs (2 hands)"),
        ("Entrance", "rides in on a chopper, skids, vaults onto his bar: sprites of his own (bike, rider, smoke, dust), the helmet on the rider"),
    ],
    sumo=[
        ("WALK / STOMP", "on his bar; he steps 8 px on the tune's beat (every 3.2 s); STOMP is the step"),
        ("SHIKO", "the charge tell: the stamp pose; then he lunges 16 px"),
        ("HMPH", "a cup cancels the charge: he stands, huffing"),
        ("GULP", "the hit pose when a cup reaches him (he does not stop; no hand mug)"),
        ("WINCE", "knocked back 32 px when the meter fills; at the left end he is out (no HAPPY)"),
        ("Tiles", "body is BG; the HUD meter has two extra one-pip tiles"),
        ("Sprites", "topknot (takes the body colours); TAKEN capacity mugs only (no limit ?); no hand mug"),
        ("Entrance", "walks in, lifts a leg and throws salt (two grains, sprites), stamps with dust at his feet (sprites), twice"),
    ],
    leo=[
        ("WALK / STOMP", "on his bar; STOMP after each 8 px step"),
        ("GULP / WINCE", "caught a coconut, hand mug up / pushed back 8 px"),
        ("HAPPY", "the outro"),
        ("INHALE", "the roar tell, 60 frames every 7 s: mane puffed, a BANG ('!!', BG) in the column right of him"),
        ("ROAR", "30 frames: everybody on screen is pushed back 16 px; a shockwave (two arcs, sprites) sweeps right on every bar and blows back full mugs; no room: 2 TAKEN"),
        ("Tiles", "body and the BANG column (246-247) are BG"),
        ("Sprites", "crown hat; hand mug in GULP; capacity mugs (2 hands); the arcs in ROAR (first frame shown)"),
        ("Entrance", "a flaming hoop (sprites) over his bar, he flies through it as ROAR-pose sprites, lands, roars"),
    ],
    mothership=[
        ("WALK / STOMP", "hovering; STOMP is the bob"),
        ("GULP", "a caught drink: the hatch opens, a beam lifts the served mug into the hull (no hand mug)"),
        ("WINCE", "pushed back 8 px: the lights go out"),
        ("HAPPY", "the split flash (lights magenta, blinking) and the stun-ray charge"),
        ("TELL", "teleport tell, 60 frames: the antenna blinks (the lower hat frame); a BEAM (BG) column marks the target bar"),
        ("Tiles", "saucer and arm (5 columns) and the BEAM marker (248-251) are BG"),
        ("Sprites", "antenna and dome cap; beam light (2 frames) and the lifted mug behind the hull; capacity mugs (2 hands; his limit logic unclear ?)"),
        ("Phase 2", "at meter 6 the saucer splits into three mini aliens (patron tiles reloaded)"),
        ("Entrance", "the beam lights on his bar, the lights flicker, he blinks in"),
    ],
)
