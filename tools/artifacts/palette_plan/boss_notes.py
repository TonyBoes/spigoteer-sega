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

# The owner's summary above the pictures (owner 2026-10-26: "two sentences about his actions, then which poses use sprites"):
# ACTS = two sentences; SPR = (pose, its sprites) per pose; "none" = BG only. Every pose not named in a list's last row is as GULP's
# neighbours say. The capacity mugs and the topper are sprites in every on-bar pose unless a row says otherwise.
ACTS = dict(
    big_tex="He swaggers in, bows and tips his hat, then steps toward the tap every 2 s. He drinks three at a time and is pushed back 16 px.",
    mascot="He walks the bar and every 5 s crouches to leap onto another bar, marked by a dust marker. While airborne he catches nothing.",
    sasquatch="He walks the bar and every 6 s ducks behind the counter, then bursts up where the footprints blink. He downs a coffee in 20 frames.",
    critic="He takes only a perfect drink while his hands are free and savours it, then holds the empty before sending it back. Sloppy or early drinks he tastes or waves back with a NO or BAD bubble.",
    yeti="He walks the bar and every 6 s inhales, then blows frost that ices his counter for 3 s. Sparks twinkle on the ice.",
    prototype="His lamp cycles green, yellow and red: green and yellow he takes batteries, red he bounces them back and his counter runs as a conveyor. A marker shows the next bar before he moves.",
    duke="He idles in place, shaking with the engine, and every so often revs and lurches 16 px forward. He rides in on a chopper.",
    sumo="He steps on the beat and every so often stamps, then charges 16 px; a cup cancels the charge. Cups hit him rather than being drunk, and a full meter knocks him back until he is out.",
    leo="He walks the bar and every 7 s inhales, then roars: everyone is pushed back 16 px and full mugs are blown back. He flies in through a flaming hoop.",
    mothership="He hovers, teleporting to a bar marked by a beam, and beams drinks up into the hull. At meter 6 he splits into three mini aliens.",
)
SPR = dict(
    big_tex=[("WALK STOMP WINCE", "hat, capacity mugs"), ("GULP", "hat, hand mug, capacity mugs"), ("HAPPY", "hat"),
             ("BARE", "hat pop (4)"), ("Entrance", "whole body")],
    mascot=[("WALK STOMP WINCE", "hat, capacity mugs"), ("GULP", "hat, hand mug, capacity mugs"), ("CROUCH", "hat, capacity mugs"),
            ("PUFF1 PUFF2", "none"), ("HAPPY", "hat"), ("Entrance", "ball")],
    sasquatch=[("WALK STOMP WINCE", "crest, capacity mugs"), ("GULP", "crest, hand mug, capacity mugs"), ("DUCK", "crest, capacity mugs"),
               ("BURST1", "none"), ("BURST2", "crest ?"), ("HAPPY", "crest"), ("Entrance", "none")],
    critic=[("WALK STOMP WINCE", "stalk, capacity mug"), ("GULP", "stalk, hand mug, capacity mug"), ("HOLD HOLDHOP", "stalk, capacity mug"),
            ("TASTE", "stalk, capacity mug, NO / BAD bubble"), ("HAPPY", "stalk"), ("Entrance", "cloche (4), glint")],
    yeti=[("WALK STOMP WINCE", "hat, capacity mugs"), ("GULP", "hat, hand mug, capacity mugs"), ("INHALE BLOW", "hat, capacity mugs"),
          ("HAPPY", "hat"), ("Entrance", "none")],
    prototype=[("WALK STOMP WINCE", "lamp, capacity mugs"), ("WALK YELLOW", "lamp ring, capacity mugs"), ("RED", "lamp X"),
               ("GULP", "lamp, hand mug, capacity mugs"), ("HAPPY", "lamp"), ("Entrance", "whole body, yoke, chain, sparks")],
    duke=[("WALK STOMP WINCE", "helmet, capacity mugs"), ("TELL1 TELL2", "helmet, capacity mugs"), ("GULP", "helmet, hand mug, capacity mugs"),
          ("HAPPY", "helmet"), ("Entrance", "bike, rider, smoke, dust")],
    sumo=[("WALK STOMP WINCE", "topknot, capacity mugs"), ("SHIKO HMPH GULP", "topknot, capacity mugs"), ("HAPPY", "topknot"),
          ("Entrance", "salt, dust")],
    leo=[("WALK STOMP WINCE", "crown, capacity mugs"), ("GULP", "crown, hand mug, capacity mugs"), ("INHALE", "crown, capacity mugs"),
         ("ROAR", "crown, capacity mugs, shockwave arcs"), ("HAPPY", "crown"), ("Entrance", "hoop, whole body")],
    mothership=[("WALK STOMP WINCE", "antenna, capacity mugs"), ("GULP", "antenna, beam light, lifted mug, capacity mugs"),
                ("TELL", "antenna blink, capacity mugs"), ("HAPPY", "antenna"), ("Entrance", "none")],
)
