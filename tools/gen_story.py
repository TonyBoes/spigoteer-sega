#!/usr/bin/env python3
"""docs/story.md (the owner-approved script) + assets/story/portraits.json + assets/tiles/story.txt -> story mode data.

  build/story.h            scene / speaker / chapter ids, the cut-scene tile budget, the BANKED accessors
  build/story_data.c       the script (pages, scene table, names), chapter goals, the story font tiles, the picture slots
  build/story_portraits.c  the portraits (BG tiles, map, attributes, palettes, optional OBJ overlay)
  build/story_pictures.c   the full-screen pictures of INTRO / FINALE_A / FINALE_B / CREDITS (assets/story/pictures/*.txt) and the INTRO
                           explosion's ten flying pieces as OBJ sprites (assets/story/pictures/intro_pieces.txt)
  build/story.json         the same for the tests
  out/preview/story_*.png  the font and every portrait (its variants too), x8

Both .c files are `#pragma bank 255` (autobanked). Their data is static and read only through the BANKED accessors in
the same file, which copy into the caller's WRAM buffer or write VRAM themselves (LCD off): src/story.c never passes a
pointer into its own bank to them.

The script is validated and the build fails on: a line longer than 18 characters, more than 3 lines on a page, a
character outside A-Z 0-9 . , ! ? ' - : and space, an unknown speaker, a scene title longer than 20, a chapter goal that
disagrees with the chapters table, a portrait or scene that does not fit the cut-scene budget (see story.h). Portraits:
also on a speaker without approved portrait-v2 art (there are no placeholders), a portrait over 56x56, 44 unique tiles
or 3 CGB BG palettes, and a variant range (portraits.json "variants") that names no scene or page, whose given page is
not the speaker's, that overlaps another variant of his or that no page uses (assign_portraits). Story shifts:
also on a shift (SHIFTS, the shifts table of docs/story.md) whose engine goal or last-call pattern disagrees with the
table, a banner line over 20 or outside the HUD glyphs, speeds outside the sane limits, an opening that is not about half
the goal and slower, a last call that is not faster with its own pattern (ten different ones), a timed goal that too
few patrons arrive for, or an arrival pattern that changes the arrival rate (check_shifts). Page text variants
("SPEAKER IF COND" blocks, CONDITIONS): also on an unknown condition, a variant with no page above it, of another
speaker, with the same text as its page, or a second variant with the same condition on one page.
Usage: gen_story.py outdir previewdir
"""
import json
import math
import os
import re
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_art import GREY, IDX, blocks, fmt, rgb15, tile_bytes  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LINE_W, PAGE_LINES = 18, 3
CHARSET = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,!?'-: ")
HUD_CHARSET = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ")     # the play screen's banner has no story font loaded
SPEAKERS = ["SPIGOTEER", "DREGS", "SADIE", "COACH", "JUNE", "COLBY", "AURORA", "MANAGER-BOT", "HANA", "ZIZZ", "KIKI",
            "GRANNY", "NARRATOR"]
NARRATOR = SPEAKERS.index("NARRATOR")
# The name plate (the frame's bottom row, src/story.c compose_portrait): inside the 56x56 portrait's 9-tile frame the plate has 7
# cells, so a longer name shows in a short form (PLATE_NAMES). Its tiles are the HUD glyphs inverted (dark ink on the frame's light
# gold), appended to each portrait's own tiles (add_plates): one per letter of its plate name, (the cells either side of the name are the frame's own bottom moulding).
PLATE_FULL = os.environ.get("SPIGOT_PLATE", "A") == "B"     # A (default): 7 cells between the frame corners. B: all 9 cells, SPIGOTEER whole; needs 2 more BG tiles than INTRO has, see PLATE_NAMES
PLATE_CELLS = 9 if PLATE_FULL else 7
PLATE_NAMES = {"MANAGER-BOT": "MGR-BOT"} if PLATE_FULL else {"SPIGOTEER": "SPIGOT", "MANAGER-BOT": "MGR-BOT"}   # B keeps SPIGOTEER whole but INTRO is 2 tiles short (the trail dots)
PUNCT = {".": "period", ",": "comma", "!": "excl", "?": "quest", "'": "apos", "-": "hyphen", ":": "colon"}

# ---- the cut-scene budget (src/story.c draws to it; see PLAN.md "M11b story engine as built") ----
# BG ids while a cut-scene shows: 0-35 the venue pool (stage + bar), 36-76 the HUD glyphs and panels; the patron range
# and everything above it are free (no patrons on a cut-scene): the story font, then the scene's portraits.
BG_END = 256
MAX_W = MAX_H = 7                # portrait size in tiles (56x56)
MAX_TILES = 44                   # unique BG tiles per portrait (docs/story.md "Portraits": the approved style's budget)
MAX_BG_PALS = 3                  # CGB BG palettes 2-4 (0 bar, 1 HUD / text box, 5-6 stage, 7 keg stay the venue's)
MAX_OBJ_PALS = 4                 # CGB OBJ palettes 3-6 (0 the Spigoteer, 1-2 the drinks)
OBJ_TILES = 32                   # OBJ ids of the show performers (OBJ_DANCER.. 127): the overlay tiles, all speakers
MAX_OBJ = 16                     # overlay entries per portrait (OAM 4..)
LINE_OBJ = 8                     # overlay sprites on one line (10 minus the Spigoteer's 2)
MAX_SPK = 3                      # portrait speakers per scene (their tiles are all loaded when the scene starts)
PIC_ROWS = 13                    # picture slot: rows 0-12, above the text box
PIC_POOL = 36                    # its own tiles at BG ids 0.. (no venue on a picture scene)

SHIFT_TIMER_MAX = 99             # a shift's timer shows as two digits + the hourglass (owner 2026-10-13): at most 99 s
# goal types / flags (src/story.c)
G_SERVE, G_CATCH, G_CLEAR = 0, 1, 2
F_NO_TAP, F_NO_BREAK = 1, 2      # strict rules (owner): breaking one costs 2 lives instead of 1 (src/story.c)
# chapter: scene suffix, venue (theme index), goal, count, flags, timer seconds (0 none), banner lines (HUD glyphs only),
# and the engine column of the chapters table it must agree with
CHAPTERS = [
    ("SALOON", 0, G_SERVE, 15, 0, 0, "SERVE 15 COWBOYS", "", "serve 15"),
    ("STADIUM", 1, G_SERVE, 20, F_NO_TAP, 0, "SERVE 20 FANS", "FAN AT TAP COSTS TWO",
     "serve 20, a patron at the tap costs 2 lives"),
    ("LUMBER", 2, G_SERVE, 18, 0, 0, "WAKE UP 18", "SLEEPY LUMBERJACKS", "serve 18"),
    ("BISTRO", 3, G_SERVE, 20, 0, SHIFT_TIMER_MAX, "SERVE 20 CHEFS", "BEFORE THE RUSH", "serve 20 before the timer"),
    ("IGLOO", 4, G_SERVE, 20, 0, SHIFT_TIMER_MAX, "SERVE 20 COCOAS", "BEFORE THEY COOL", "serve 20 before the timer"),
    ("ROBOT", 5, G_CATCH, 25, 0, 0, "RECYCLE 25", "EMPTY BATTERIES", "catch 25 empties"),
    ("BIKER", 6, G_SERVE, 22, 0, 0, "SERVE 22 PUNKS", "NO CRYING OVER MILK", "serve 22"),
    ("TEAHOUSE", 7, G_CLEAR, 0, F_NO_BREAK, 0, "SERVE EVERY GUEST", "BROKEN CUP COSTS TWO",
     "clear the venue, a broken glass costs 2 lives"),
    ("ZOO", 8, G_SERVE, 25, 0, 0, "SERVE 25 ANIMALS", "", "serve 25"),
    ("SPACE", 9, G_SERVE, 30, 0, 0, "SERVE 30 GLOWING", "BEAKERS", "serve 30"),
]
PICTURE_SCENES = ["INTRO", "FINALE_A", "FINALE_B", "CREDITS"]
# The full-screen pictures of the picture scenes (rows 0-12 instead of a venue): assets/story/pictures/<name>.txt, each
# portrait-v2 at 160x104 (@size 160 104, @maxpal 4, an exact-HUD palette allowed: see read_pic). Per scene its pictures
# in the order shown, with the 1-based page each one appears on (the first: 1). A later picture replaces the earlier
# one at the start of its page behind a white flash (src/story.c pic_switch); that page must be the narrator's (no
# portrait frame up) and docs/story.md's scene must say "Picture (page N):". A picture's id is its place in this list
# (scene header byte 1 = the scene's first picture; the next one of the scene is +1).
SCENE_PICS = {"INTRO": [(1, "intro_before"), (5, "intro_a")], "FINALE_A": [(1, "finale_a")], "FINALE_B": [(1, "finale_a")], "CREDITS": [(1, "credits_b")]}
# A picture scene that shows another scene's picture (FINALE_B: the Pour-Off was played between the two halves) shares its one
# copy in ROM: the picture's tiles sit above the first scene's portrait slot, so the sharer's biggest portrait must fit it.
PIC_SHARE = {"FINALE_B": "FINALE_A"}
PIC_DIR = ROOT / "assets/story/pictures"
PIC_W, PIC_H = 160, 104
PIC_SLOTS = (0, 5, 6, 7)         # CGB BG palette slots of a picture's palettes, in order (BG 1, the HUD, is also usable)
PIC_MAX_PALS = len(PIC_SLOTS)
# Page text variants (docs/story.md "Script format"): a page may carry variants "SPEAKER IF COND" whose lines replace
# its own when the condition holds (the first that holds, in script order). Condition ids 1-8: bit id - 1 of src/story.c
# story_conds, set and cleared by the engine; the data stores the id (one byte per variant page). The page's portrait
# and speaker stay the page's.
CONDITIONS = {
    "GLASS_BROKEN": 1,           # a glass broken (the life it cost: the strict rule's event in chapter 8) in the venue
                                 # attempt just played: set in story_play, cleared by venue_start (a chapter's first
                                 # entry from its PRE scene, a restart after the last life, CONTINUE)
}

# ---- story shifts (src/story.c): each chapter plays its venue several times in a row ------------------------------
# The chapter's sequence: Opening shift, Happy hour (the CHAPTERS goal above), the mini-game slot, Last call, the boss
# slot. A step byte is kind << 4 | index (the shift 0-2, or the mini-game / boss id); STEP_SKIP marks a kind the engine
# cannot play yet (NOT_BUILT): it passes over that step. Adding the mini-games or bosses = their mode in the engine and
# taking the kind out of NOT_BUILT, or one venue at a time into BUILT_SLOTS (a data change).
SHIFT_NAMES = ["OPENING SHIFT", "HAPPY HOUR", "LAST CALL"]   # the goal banner's first line (no chapter number)
STEP_KINDS = {"SHIFT": 0, "MINI": 1, "BOSS": 2}
STEP_SKIP = 0x80
SEQUENCE = [("SHIFT", 0), ("SHIFT", 1), ("MINI", 0), ("SHIFT", 2), ("BOSS", 0)]
NOT_BUILT = {"MINI", "BOSS"}
# Slots of a NOT_BUILT kind that are built in some venues already (by chapter suffix): the boss engine (src/boss.c) has
# Big Tex (the saloon), the Sasquatch (the lumber lodge), the Food Critic (the bistro) and the Yeti (the igloo) so far,
# and the mini-game framework (src/mg.c) Quick Draw (src/qd.c), the saloon's mini-game, Order Up! (src/ou.c), the
# bistro's, Battery Sort (src/bs.c), the robot factory's, Milk Run (src/mr.c), The Chrome Cow's, Log Roll (src/lr.c), the lumber lodge's, and Asteroid Delivery (src/ad.c), the space lounge's, and Taiko Pour (src/tk.c), the teahouse's, Marshmallow Drop (src/mm.c), the igloo's, Monkey Business (src/mk.c), the jungle zoo's, and T-Shirt Cannon (src/ts.c), the stadium's; the other venues' slots are still skipped.
BUILT_SLOTS = {"BOSS": {"SALOON", "LUMBER", "BISTRO", "IGLOO", "TEAHOUSE", "ZOO", "STADIUM", "ROBOT", "BIKER", "SPACE"},"MINI": {"SALOON", "LUMBER", "BISTRO", "ROBOT", "BIKER", "SPACE", "TEAHOUSE", "IGLOO", "ZOO", "STADIUM"}}
# Arrival patterns (patrons.c try_spawn): a cycle of (bar, wait) entries; the wait after a spawn is n the shift's spawn
# interval I, s PAT_SHORT frames, d 2 I, b 4 I (a breather). Every pattern keeps about one patron per I on average
# (checked below), so a pattern changes WHERE and in what rhythm patrons come, not how many. "normal": today's random
# bar every I (no table). Bars are numbered 0 (top) to 3 (bottom).
PAT_SHORT = 12
PAT_WAITS = {"n": 0, "s": 1, "d": 2, "b": 3}
PAT_MAX = 8
PATTERNS = {
    "normal": [],
    "stairs down": [(0, "n"), (1, "n"), (2, "n"), (3, "n")],
    "all bars at once": [(0, "s"), (1, "s"), (2, "s"), (3, "b")],
    "flood bar 2": [(1, "n"), (0, "n"), (1, "n"), (2, "n"), (1, "n"), (3, "n")],
    "pairs": [(0, "s"), (2, "d"), (1, "s"), (3, "d")],
    "zigzag": [(0, "n"), (2, "n"), (1, "n"), (3, "n"), (2, "n"), (0, "n"), (3, "n"), (1, "n")],
    "stairs up": [(3, "n"), (2, "n"), (1, "n"), (0, "n")],
    "flood bar 4": [(3, "n"), (0, "n"), (3, "n"), (1, "n"), (3, "n"), (2, "n")],
    "inside out": [(1, "s"), (2, "d"), (0, "s"), (3, "d")],
    "stampede": [(0, "s"), (1, "s"), (2, "s"), (3, "b"), (3, "s"), (2, "s"), (1, "s"), (0, "b")],
    "chord": [(0, "s"), (1, "s"), (2, "b"), (3, "s"), (2, "s"), (1, "d")],   # three bars at once, a long breather, three more
}
OPEN_WALK, OPEN_SPAWN = 85, 115      # the Opening shift: the row's walkers 15 % slower, patrons 15 % further apart
WALK_RANGE, SPAWN_RANGE = (70, 130), (70, 150)   # sane limits (the arcade's loop ceiling is +30 % walk, -24 % spawn)
# per chapter: the Opening shift and the Last call (the Happy hour is the chapter's CHAPTERS goal, row speeds, normal
# arrivals). Opening: (goal, count, flags, secs, quota (G_CLEAR: patrons in the shift; 0 the row's), line1, line2,
# engine text of the docs/story.md shifts table). Last call: the same + (pattern, walk %, spawn %).
SHIFTS = [
    ((G_SERVE, 8, 0, 0, 0, "SERVE 8 COWBOYS", "", "serve 8"),
     (G_SERVE, 18, 0, 0, 0, "SERVE 18 COWBOYS", "ONE BAR AT A TIME", "serve 18", "stairs down", 110, 90)),
    ((G_SERVE, 10, F_NO_TAP, 0, 0, "SERVE 10 FANS", "FAN AT TAP COSTS TWO", "serve 10, a fan at the tap costs 2 lives"),
     (G_SERVE, 22, F_NO_TAP, 0, 0, "22 FANS RUSH IN", "FAN AT TAP COSTS TWO", "serve 22, a fan at the tap costs 2 lives",
      "all bars at once", 105, 95)),
    ((G_SERVE, 9, 0, 0, 0, "WAKE UP 9", "SLEEPY LUMBERJACKS", "serve 9"),
     (G_SERVE, 20, 0, 0, 0, "WAKE UP 20", "ONE BAR IS PACKED", "serve 20", "flood bar 2", 115, 85)),
    ((G_SERVE, 10, 0, 75, 0, "SERVE 10 CHEFS", "BEFORE THE RUSH", "serve 10 in 75 s"),
     (G_SERVE, 22, 0, SHIFT_TIMER_MAX, 0, "SERVE 22 CHEFS", "TABLES FOR TWO", "serve 22 in 99 s", "pairs", 115, 85)),
    ((G_SERVE, 10, 0, 75, 0, "SERVE 10 COCOAS", "BEFORE THEY COOL", "serve 10 in 75 s"),
     (G_SERVE, 22, 0, SHIFT_TIMER_MAX, 0, "SERVE 22 COCOAS", "BEFORE THEY FREEZE", "serve 22 in 99 s", "zigzag", 115, 85)),
    ((G_CATCH, 12, 0, 0, 0, "RECYCLE 12", "EMPTY BATTERIES", "catch 12 empties"),
     (G_CATCH, 28, 0, 0, 0, "RECYCLE 28", "BATTERIES PILE UP", "catch 28 empties", "stairs up", 115, 85)),
    ((G_SERVE, 10, 0, 0, 0, "SERVE 10 PUNKS", "ICE COLD MILK", "serve 10"),
     (G_SERVE, 24, 0, 0, 0, "SERVE 24 PUNKS", "THE BAND SPEEDS UP", "serve 24", "chord", 115, 85)),
    ((G_CLEAR, 0, F_NO_BREAK, 0, 7, "SERVE 7 GUESTS", "BROKEN CUP COSTS TWO", "7 guests, a broken glass costs 2 lives"),
     (G_CLEAR, 0, F_NO_BREAK, 0, 15, "SERVE 15 GUESTS", "BROKEN CUP COSTS TWO", "15 guests, a broken glass costs 2 lives",
      "flood bar 4", 115, 85)),
    ((G_SERVE, 12, 0, 0, 0, "SERVE 12 ANIMALS", "", "serve 12"),
     (G_SERVE, 28, 0, 0, 0, "STAMPEDE", "SERVE 28 ANIMALS", "serve 28", "stampede", 120, 80)),
    ((G_SERVE, 15, 0, 0, 0, "SERVE 15 GLOWING", "BEAKERS", "serve 15"),
     (G_SERVE, 32, 0, 0, 0, "SERVE 32 GLOWING", "BEAKERS", "serve 32", "inside out", 125, 75)),
]


# Venue twists (docs/story.md "Chapters"; each changes one parameter or adds one small behaviour), per shift: bits of
# goal_t.twist -> src/story.c story_twist. Only in story shifts (never the Opening shift unless listed, never arcade or a
# boss fight: boss.c sets 0). TWIST_MOSH: the mosh pit (docs/minigames_bosses.md section 9; src/mosh.c), with
# MOSH_LIMIT its x limit per shift; TWIST_FAST_TUNE: the venue's tune one frame a row faster (src/music.c music_fast).
TWIST_MOSH, TWIST_FAST_TUNE = 0x01, 0x02
TWISTS = {("BIKER", 1): TWIST_MOSH, ("BIKER", 2): TWIST_MOSH | TWIST_FAST_TUNE}   # (chapter suffix, shift): bits
MOSH_LIMIT = {1: 88, 2: 72}       # Happy hour, Last call (owner 2026-10-11: on in Last call too, 48 px from the tap)


def slot_skipped(kind, suffix):
    """A step of this kind in the chapter with this suffix is not built yet (STEP_SKIP)."""
    return kind in NOT_BUILT and suffix not in BUILT_SLOTS.get(kind, ())


def level_rows(path):
    """src/level.c's level table: [(start patrons, quota, spawn interval)] per row (for the checks below)."""
    rows = re.findall(r"^\s*\{\s*\d+,\s*(0x[0-9A-Fa-f]+),\s*(\d+),\s*(\d+),\s*(\d+),", path.read_text(), re.M)
    return [(bin(int(m, 16)).count("1") * int(n), int(q), int(sp)) for m, n, q, sp in rows]


def shift_list():
    """-> per chapter [opening, happy hour, last call] as dicts (the one view of the shift data the generator uses)."""
    out = []
    for c, (op, lc) in zip(CHAPTERS, SHIFTS):
        happy = (c[2], c[3], c[4], c[5], 0, c[6], c[7], c[8], "normal", 100, 100)
        row = []
        for k, sh in enumerate((op + ("normal", OPEN_WALK, OPEN_SPAWN), happy, lc)):
            t, n, f, secs, q, l1, l2, eng, pat, walk, spawn = sh
            tw = TWISTS.get((c[0], k), 0)
            row.append({"name": SHIFT_NAMES[k], "type": t, "count": n, "flags": f, "secs": secs, "quota": q,
                        "line1": l1, "line2": l2, "engine": eng, "pattern": pat, "walk": walk, "spawn": spawn,
                        "twist": tw, "mosh_limit": MOSH_LIMIT[k] if tw & TWIST_MOSH else 0})
        out.append(row)
    return out


def pattern_mean(name):
    """Mean frames between arrivals, in units of the interval I (PAT_SHORT taken at I = 250)."""
    e = PATTERNS[name]
    if not e:
        return 1.0
    w = {"n": 1.0, "s": PAT_SHORT / 250, "d": 2.0, "b": 4.0}
    return sum(w[x] for _, x in e) / len(e)


def check_shifts(rows):
    """The shift data the engine trusts: limits, the shifts' order of difficulty, timed goals that arrivals can meet."""
    for name, e in PATTERNS.items():
        if len(e) > PAT_MAX or any(not 0 <= b <= 3 or x not in PAT_WAITS for b, x in e):
            fail(f"pattern {name!r}: at most {PAT_MAX} entries (bar 0-3, wait n / s / d / b)")
        if not 0.9 <= pattern_mean(name) <= 1.15:
            fail(f"pattern {name!r}: one patron per {pattern_mean(name):.2f} intervals (0.9-1.15)")
    lv = level_rows(ROOT / "src/level.c")
    if len(lv) != len(CHAPTERS):
        fail(f"src/level.c: {len(lv)} level rows, {len(CHAPTERS)} chapters")
    lasts = []
    for c, row in enumerate(rows):
        start, row_quota, row_iv = lv[c]
        for sh in row:
            where = f"chapter {c + 1} {sh['name'].lower()}"
            for l in (sh["line1"], sh["line2"]):
                if len(l) > 20 or set(l) - HUD_CHARSET:
                    fail(f"{where} banner {l!r}: max 20, A-Z 0-9 and space")
            if len(sh["name"]) > 20 or set(sh["name"]) - HUD_CHARSET:
                fail(f"{where}: the banner's first line (the shift's name) is over 20 or outside the HUD glyphs")
            if sh["type"] == G_CLEAR:
                if sh["count"] or (sh["quota"] and not 2 <= sh["quota"] <= 40):
                    fail(f"{where}: a clear goal has no count and a quota of 2-40 (0: the row's)")
            elif not 1 <= sh["count"] <= 99 or sh["quota"]:
                fail(f"{where}: count 1-99 (two HUD digits), no quota")
            if not (WALK_RANGE[0] <= sh["walk"] <= WALK_RANGE[1] and SPAWN_RANGE[0] <= sh["spawn"] <= SPAWN_RANGE[1]):
                fail(f"{where}: walk {sh['walk']} % / spawn {sh['spawn']} % outside {WALK_RANGE} / {SPAWN_RANGE}")
            if sh["pattern"] not in PATTERNS:
                fail(f"{where}: unknown pattern {sh['pattern']!r}")
            if not 0 <= sh["secs"] <= SHIFT_TIMER_MAX:
                fail(f"{where}: timer 0-{SHIFT_TIMER_MAX} s (two HUD digits and the hourglass)")
            if sh["secs"]:                       # enough arrivals in time: start patrons + spawns >= 1.3 x the goal
                iv = row_iv * sh["spawn"] / 100 * pattern_mean(sh["pattern"])
                arrivals = start + (sh["secs"] * 60 - 90) / iv
                if arrivals < 1.3 * sh["count"]:
                    fail(f"{where}: only {arrivals:.0f} patrons arrive in {sh['secs']} s for a goal of {sh['count']}")
        op, happy, last = row
        size = (lambda s: s["count"] or s["quota"] or row_quota)
        if not (op["walk"] < 100 < op["spawn"] and 0.4 <= size(op) / size(happy) <= 0.6):
            fail(f"chapter {c + 1}: the opening is about half the goal (40-60 %) and slower")
        if not (last["walk"] > 100 > last["spawn"] and size(last) >= size(happy) and last["pattern"] != "normal"):
            fail(f"chapter {c + 1}: the last call is faster, no smaller, with its own arrival pattern")
        if not (op["type"] == happy["type"] == last["type"] and op["flags"] == happy["flags"] == last["flags"]):
            fail(f"chapter {c + 1}: all shifts keep the chapter's kind of goal")
        lasts.append(last["pattern"])
    if len(set(lasts)) != len(lasts):
        fail(f"two last calls share a pattern: {lasts}")


class StoryError(Exception):
    pass


COND_NAME = {i: n for n, i in CONDITIONS.items()}
assert all(1 <= i <= 8 for i in CONDITIONS.values()) and len(COND_NAME) == len(CONDITIONS)


def fail(msg):
    raise StoryError(msg)


# ---- the script --------------------------------------------------------------------------------------------------
# ---- beats (docs/story.md "Beats"): pauses in the typing -----------------------------------------------------------
# `|` / `||` right after a word: a short / long pause there. In the data a mark is a control cell (MARK_SHORT / MARK_LONG)
# that takes the place of the space after the word, or sits in the first free cell at the end of the line; the engine
# (src/story.c type_frame) waits BEAT_FRAMES for it. `@beat [N]` on the line after the speaker: a pause of N x
# BEAT_UNIT frames before the page types (N 1-7, default BEAT_DEFAULT); its N rides in the first line's length byte.
MARK_SHORT, MARK_LONG = "\x01", "\x02"
MARK_CELLS = MARK_SHORT + MARK_LONG
BEAT_FRAMES = (15, 36)           # frames of a short and of a long mid-line beat
BEAT_UNIT, BEAT_DEFAULT = 8, 3   # frames per @beat step; N when "@beat" has none
GAP_SPEAKER, GAP_PAGE = 12, 6    # the engine's own gap before a page: another speaker's, the same speaker's next page


def parse_marks(line, where):
    """A script line with `|` marks -> the cells of the text box (control cells for the marks). Fails on a bad mark."""
    out, i = "", 0
    while i < len(line):
        c = line[i]
        if c != "|":
            if c not in CHARSET:
                fail(f"{where}: {line!r} has characters outside the font: {c!r}")
            out += c
            i += 1
            continue
        n = 1
        while line[i + n:i + n + 1] == "|":
            n += 1
        if n > 2:
            fail(f"{where}: {line!r}: use | (short beat) or || (long beat)")
        if not out or out[-1] == " " or out[-1] in MARK_CELLS:
            fail(f"{where}: {line!r}: a beat goes right after a word")
        i += n
        if i < len(line) and line[i] != " ":
            fail(f"{where}: {line!r}: a beat must be followed by a space or the end of the line")
        out += (MARK_SHORT, MARK_LONG)[n - 1]   # takes the space after the word, or the line's first free cell
        if i < len(line):
            i += 1
    return out


def marks_of(raw_lines):
    """[(line, cell, frames)] of a page's beats, in typing order (tests)."""
    return [[r, k, BEAT_FRAMES[MARK_CELLS.index(c)]] for r, l in enumerate(raw_lines) for k, c in enumerate(l) if c in MARK_CELLS]


def clean_line(raw):
    """The text a line shows: marks back to the spaces they replaced (a mark at the end of a line: nothing)."""
    return raw.replace(MARK_SHORT, " ").replace(MARK_LONG, " ").rstrip()


def parse_script(path):
    """-> [{"id", "title", "pages": [(speaker, [lines])], "alts": per page [(condition id, [lines])]}] in the order of
    docs/story.md. A block whose speaker line reads "SPEAKER IF COND" is a text variant of the page right above it
    (same speaker, a CONDITIONS name, other text): the engine shows its lines instead when the condition holds."""
    text = path.read_text()
    scenes = []
    for m in re.finditer(r'^### (\w+): "([^"]*)"\n(.*?)(?=^### |^## |\Z)', text, re.S | re.M):
        sid, title, body = m.group(1), m.group(2).upper(), m.group(3)
        code = re.search(r"^```\n(.*?)^```", body, re.S | re.M)
        if not code:
            fail(f"{sid}: no script block")
        pages, alts, raws, alts_raw = [], [], [], []
        for blk in re.split(r"\n\s*\n", code.group(1).strip("\n")):
            lines = [l.rstrip() for l in blk.split("\n")]
            spk, body_lines = lines[0], lines[1:]
            pre = 0                             # "@beat [N]": a pause before the page types (BEAT_UNIT frames x N)
            if body_lines and body_lines[0].startswith("@beat"):
                mb = re.fullmatch(r"@beat(?: ([1-7]))?", body_lines[0])
                if not mb:
                    fail(f"{sid} page {len(pages) + 1}: {body_lines[0]!r} is not '@beat' or '@beat N' (N 1-7)")
                pre = int(mb.group(1) or BEAT_DEFAULT)
                body_lines = body_lines[1:]
            cond = None
            m2 = re.fullmatch(r"(\S+) IF (\S+)", spk)
            if m2:                              # a text variant of the page above (CONDITIONS)
                spk, cond = m2.groups()
                where = f"{sid} page {len(pages)} variant IF {cond}"
            else:
                where = f"{sid} page {len(pages) + 1}"
            if spk not in SPEAKERS:
                fail(f"{where}: unknown speaker {spk!r}")
            if not 1 <= len(body_lines) <= PAGE_LINES:
                fail(f"{where}: {len(body_lines)} lines (1-{PAGE_LINES})")
            raw_lines = []
            for l in body_lines:
                l = parse_marks(l, where)
                if len(l) > LINE_W:
                    fail(f"{where}: {l!r} is {len(l)} characters (max {LINE_W})" +
                         ("; a beat at the end of a full line has no room" if l[-1] in MARK_CELLS else ""))
                raw_lines.append(l)
            body_lines = [clean_line(l) for l in raw_lines]
            if raw_lines[-1][-1:] in MARK_CELLS:
                fail(f"{where}: a beat at the end of the page's last line pauses nothing")
            if cond is not None:
                if cond not in CONDITIONS:
                    fail(f"{where}: unknown condition {cond!r} (known: {', '.join(CONDITIONS)})")
                if not pages:
                    fail(f"{where}: a variant needs the page it replaces right above it")
                if SPEAKERS.index(spk) != pages[-1][0]:
                    fail(f"{where}: the variant's speaker must be the page's ({SPEAKERS[pages[-1][0]]})")
                if any(c == CONDITIONS[cond] for c, _ in alts[-1]):
                    fail(f"{where}: a second variant IF {cond} of one page")
                if body_lines == pages[-1][1]:
                    fail(f"{where}: the same text as the page it replaces")
                alts[-1].append((CONDITIONS[cond], body_lines))
                alts_raw[-1].append((CONDITIONS[cond], pre or raws[-1][0], raw_lines))   # (it keeps the page's @beat unless it has its own)
                continue
            pages.append((SPEAKERS.index(spk), body_lines))
            raws.append((pre, raw_lines))
            alts.append([])
            alts_raw.append([])
        if len(title) > 20 or set(title) - CHARSET:
            fail(f"{sid}: title {title!r} (max 20, the story charset)")
        scenes.append({"id": sid, "title": title, "pages": pages, "alts": alts, "raws": raws, "alts_raw": alts_raw})
    want = ["INTRO"] + [f"{k}_{c[0]}" for c in CHAPTERS for k in ("PRE", "POST")] + ["FINALE_A", "FINALE_B", "CREDITS"]
    if [s["id"] for s in scenes] != want:
        fail(f"scene order {[s['id'] for s in scenes]} != {want}")
    # the chapters table: each chapter's engine goal must match CHAPTERS
    rows = re.findall(r"^\| (\d+) \| [^|]+\| [^|]+\| [^|]+\| \"[^\"]*\" / ([^|]+)\|", text, re.M)
    if len(rows) != len(CHAPTERS):
        fail(f"chapters table: {len(rows)} rows")
    for (n, eng), c in zip(rows, CHAPTERS):
        if c[8] not in eng:
            fail(f"chapter {n}: the table says {eng.strip()!r}, gen_story has {c[8]!r}")
        for l in c[6:8]:
            if len(l) > 20 or set(l) - HUD_CHARSET:
                fail(f"chapter {n} banner {l!r}: max 20, A-Z 0-9 and space")
    # the shifts table: each shift's engine goal and the last call's arrival pattern must match shift_list()
    sec = text.split("\n## Shifts", 1)
    rows = re.findall(r'^\| (\d+) \| "[^"]*" / ([^|]+)\| "[^"]*" / ([^|]+)\| "[^"]*" / ([^|]+)\| ([^|]+)\|',
                      sec[1] if len(sec) > 1 else "", re.M)
    if len(rows) != len(CHAPTERS):
        fail(f"shifts table: {len(rows)} rows")
    for (n, *cells), shifts in zip(rows, shift_list()):
        for cell, sh in zip(cells, shifts):
            if sh["engine"] not in cell:
                fail(f"chapter {n} {sh['name'].lower()}: the shifts table says {cell.strip()!r}, gen_story has "
                     f"{sh['engine']!r}")
        if not cells[3].strip().lower().startswith(shifts[2]["pattern"]):
            fail(f"chapter {n}: the shifts table's last call arrives {cells[3].strip()!r}, gen_story has "
                 f"{shifts[2]['pattern']!r}")
    check_shifts(shift_list())
    return scenes


# ---- art --------------------------------------------------------------------------------------------------------
def art_ids(path):
    h = path.read_text()
    return {m.group(1): int(m.group(2)) for m in re.finditer(r"#define (\w+) (\d+)", h)}


def tiles_of(px):
    """px rows (lists of 0..3) whose size is whole tiles -> (list of 16-byte tiles row-major, w, h)."""
    rows = ["".join(".-+#"[v] for v in r) for r in px]
    w, h = len(rows[0]) // 8, len(rows) // 8
    return [tuple(tile_bytes(rows, tx * 8, ty * 8)) for ty in range(h) for tx in range(w)], w, h


# ---- portrait-v2: the approved colour-key sources (assets/story/portraits/*.txt) ----------------------------------
# Format (from the portrait study, docs/story.md "Portraits"):
#     ; comments
#     @size W H                      whole 8x8 tiles, up to 56x56
#     @maxpal N                      CGB BG palettes the picture may use (at most 3)
#     @key
#     <ch> <DMG shade 0-3> <#rrggbb> <name> [obj=<base ch>]
#     @pixels
#     H rows of W key characters
# The DMG shade of a key is its BG colour index, so one set of tile data serves both models: on CGB each 8x8 tile picks
# one of the picture's palettes, whose slot k is the colour of shade k in that tile. A key with obj=<base> is a CGB-only
# accent drawn by the OBJ overlay (free-positioned 8x16 cells); the BG underneath holds <base>, which is what DMG shows.
# The converter is exact or fails: two colours on one shade in a tile, more palettes than allowed, more than 3 overlay
# colours.
def is_v2(path):
    return any(l.strip() == "@key" for l in path.read_text().splitlines())


def parse_v2(path):
    key, pix, meta, sec = {}, [], {"maxpal": MAX_BG_PALS}, None
    for ln in path.read_text().splitlines():
        if ln.startswith(";") or (not ln.strip() and sec != "pixels"):
            continue
        if ln.startswith("@size"):
            meta["w"], meta["h"] = (int(v) for v in ln.split()[1:3])
        elif ln.startswith("@maxpal"):
            meta["maxpal"] = int(ln.split()[1])
        elif ln.startswith("@key"):
            sec = "key"
        elif ln.startswith("@pixels"):
            sec = "pixels"
        elif sec == "key":
            p = ln.split()
            if len(p) < 3 or p[1] not in "0123" or not re.fullmatch(r"#[0-9a-fA-F]{6}", p[2]):
                fail(f"{path}: bad key line {ln!r}")
            obj = next((q[4:] for q in p[4:] if q.startswith("obj=")), None)
            key[p[0]] = {"dmg": int(p[1]), "hex": p[2].lower(), "obj": obj}
        elif sec == "pixels":
            if not ln.strip():
                break
            pix.append(ln)
    if "w" not in meta or len(pix) != meta["h"] or any(len(r) != meta["w"] for r in pix):
        fail(f"{path}: the pixels are not @size")
    if meta["w"] % 8 or meta["h"] % 8:
        fail(f"{path}: not whole 8x8 tiles")
    for c, k in key.items():
        if k["obj"] and (k["obj"] not in key or key[k["obj"]]["obj"]):
            fail(f"{path}: key {c!r}: obj= names no BG key")
    for y, r in enumerate(pix):
        for c in r:
            if c not in key:
                fail(f"{path}: row {y}: unknown key {c!r}")
    return key, pix, meta


def pack_palettes(tiles):
    """tiles: per tile {shade: hex}. The fewest palettes ({shade: hex}) so every tile fits one (exact search);
    returns (palettes, palette index per tile)."""
    order = sorted(range(len(tiles)), key=lambda i: -len(tiles[i]))
    best = [None]

    def fits(p, t):
        return all(p.get(s, c) == c for s, c in t.items())

    def rec(i, pals, assign):
        if best[0] is not None and len(pals) >= len(best[0][0]):
            return
        if i == len(order):
            best[0] = ([dict(p) for p in pals], dict(assign))
            return
        t = tiles[order[i]]
        for pi, p in enumerate(pals):
            if fits(p, t):
                old = dict(p)
                p.update(t)
                assign[order[i]] = pi
                rec(i + 1, pals, assign)
                p.clear()
                p.update(old)
                del assign[order[i]]
        if len(pals) < 8:
            pals.append(dict(t))
            assign[order[i]] = len(pals) - 1
            rec(i + 1, pals, assign)
            pals.pop()
            del assign[order[i]]

    rec(0, [], {})
    pals, assign = best[0]
    return pals, [assign[i] for i in range(len(tiles))]


def read_v2(path):
    """-> px (DMG indices), attr (palette per tile), pals (#rrggbb x4), overlay cells [(dx, dy, 8x16 px)], overlay
    palette (#rrggbb x4, colour 0 unused), overlay layer px (preview: 0 = transparent)."""
    key, pix, meta = parse_v2(path)
    w, h = meta["w"], meta["h"]
    bg = [[key[c]["obj"] or c for c in r] for r in pix]
    px = [[key[c]["dmg"] for c in r] for r in bg]
    tiles = []
    for ty in range(h // 8):
        for tx in range(w // 8):
            m = {}
            for y in range(ty * 8, ty * 8 + 8):
                for x in range(tx * 8, tx * 8 + 8):
                    k = key[bg[y][x]]
                    if m.get(k["dmg"], k["hex"]) != k["hex"]:
                        fail(f"{path}: tile ({tx},{ty}): two colours on DMG shade {k['dmg']}")
                    m[k["dmg"]] = k["hex"]
            tiles.append(m)
    pals, attr = pack_palettes(tiles)
    if len(pals) > min(meta["maxpal"], MAX_BG_PALS):
        fail(f"{path}: needs {len(pals)} CGB BG palettes (max {min(meta['maxpal'], MAX_BG_PALS)})")
    pals = [[p.get(s, "#000000") for s in range(4)] for p in pals]     # a slot no tile uses: any colour
    # the overlay: its colours in key order are OBJ colours 1-3; greedy 8x16 cover (top row first, then leftmost)
    ocols = [k["hex"] for k in key.values() if k["obj"]]
    ocols = list(dict.fromkeys(ocols))
    if len(ocols) > 3:
        fail(f"{path}: {len(ocols)} overlay colours (max 3)")
    opal = ["#000000"] + ocols + ["#000000"] * (3 - len(ocols))
    lay = [[ocols.index(key[c]["hex"]) + 1 if key[c]["obj"] else 0 for c in r] for r in pix]
    left = {(y, x) for y in range(h) for x in range(w) if lay[y][x]}
    cells = []
    while left:
        y0 = min(y for y, _ in left)
        x0 = min(x for y, x in left if y < y0 + 16)
        cell = [[lay[y][x] if (y, x) in left and y0 <= y < y0 + 16 and x0 <= x < x0 + 8 else 0
                 for x in range(x0, x0 + 8)] for y in range(y0, y0 + 16)]
        left -= {(y, x) for y, x in left if y0 <= y < y0 + 16 and x0 <= x < x0 + 8}
        cells.append((x0, y0, cell))
    return px, attr, pals, cells, [opal] if cells else [], lay if cells else None


def hud_palette():
    """CGB BG palette 1 (the HUD and text box colours, always loaded) as RGB15 triples, read from src/main_cold.c: a
    picture tile whose colours are exactly these can use palette 1 instead of one of the picture's own."""
    t = (ROOT / "src/main_cold.c").read_text()
    m = re.search(r"BG 1: HUD.*?" + r"\s*".join(rf"p\[{i}\] = RGB15\((\d+), (\d+), (\d+)\);" for i in range(4)), t, re.S)
    if not m:
        fail("src/main_cold.c: the HUD palette (BG 1) is not where gen_story looks for it")
    v = [int(x) for x in m.groups()]
    return [tuple(v[i * 3:i * 3 + 3]) for i in range(4)]


def q5(hexc):
    return tuple(int(hexc[i:i + 2], 16) >> 3 for i in (1, 3, 5))


def read_pic(name):
    """One full-screen picture source (assets/story/pictures/<name>.txt, portrait-v2 at 160x104) -> dict: px (DMG
    shade rows), tiles (unique 8x8 tiles by pixels, in order of first use), tmap (index per map cell, row-major,
    20 x 13), attr (per cell: 'H' the HUD palette, else the index of its palette in pals), pals (<= 4 x four #rrggbb),
    key, pix. Exact or fails: two colours on one DMG shade in a tile, more than four palettes. A cell whose colours
    are exactly the HUD palette's (and that no picture palette covers) uses BG palette 1."""
    path = PIC_DIR / f"{name}.txt"
    if not path.is_file() or not is_v2(path):
        fail(f"{name}: {path} is not a portrait-v2 source")
    key, pix, meta = parse_v2(path)
    if (meta["w"], meta["h"]) != (PIC_W, PIC_H):
        fail(f"{name}: {meta['w']}x{meta['h']} (a picture is {PIC_W}x{PIC_H}: rows 0-{PIC_ROWS - 1})")
    if meta["maxpal"] > PIC_MAX_PALS:
        fail(f"{name}: @maxpal {meta['maxpal']} (CGB BG palettes 0, 5, 6, 7 are free: max {PIC_MAX_PALS})")
    if any(k["obj"] for k in key.values()):
        fail(f"{name}: a picture has no OBJ accents")
    px = [[key[c]["dmg"] for c in r] for r in pix]
    hud = hud_palette()
    maps = []
    for ty in range(PIC_ROWS):
        for tx in range(20):
            m = {}
            for y in range(ty * 8, ty * 8 + 8):
                for x in range(tx * 8, tx * 8 + 8):
                    k = key[pix[y][x]]
                    if m.setdefault(k["dmg"], k["hex"]) != k["hex"]:
                        fail(f"{name}: tile ({tx},{ty}): two colours on DMG shade {k['dmg']}")
            maps.append(m)
    fits_hud = lambda m: all(hud[s] == q5(c) for s, c in m.items())
    umaps = []
    for m in maps:
        if not fits_hud(m) and tuple(sorted(m.items())) not in umaps:
            umaps.append(tuple(sorted(m.items())))
    big = list(dict.fromkeys(m for m in umaps if not any(set(m) < set(o) for o in umaps)))
    pals = pack_palettes([dict(m) for m in big])[0] if big else []
    if len(pals) > min(meta["maxpal"], PIC_MAX_PALS):
        fail(f"{name}: needs {len(pals)} CGB BG palettes (max {min(meta['maxpal'], PIC_MAX_PALS)})")
    attr = []
    for m in maps:
        own = next((i for i, p in enumerate(pals) if all(p.get(s, c) == c for s, c in m.items())), None)
        attr.append(own if own is not None else "H")
    pals = [[p.get(s, "#000000") for s in range(4)] for p in pals]
    tiles, tmap = [], []
    srows = ["".join(".-+#"[v] for v in r) for r in px]
    for ty in range(PIC_ROWS):
        for tx in range(20):
            t = tuple(tile_bytes(srows, tx * 8, ty * 8))
            if t not in tiles:
                tiles.append(t)
            tmap.append(tiles.index(t))
    return {"name": name, "px": px, "tiles": tiles, "tmap": tmap, "attr": attr, "pals": pals, "key": key, "pix": pix}


# ---- the INTRO's explosion: assets/story/pictures/intro_pieces.txt ---------------------------------------------------
# The ten pieces of the Golden Spigot start where they sit in the intact spigot of intro_before (an OBJ sprite each cell,
# in place the moment the white flash lets go: the picture itself, intro_a, shows the spigot gone) and fly OUTWARD in a
# straight line, faster and faster, off the screen. Behind each one a trail of dots appears in the sky: the dots are BG
# tiles (the picture's own sky cells with a 2-pixel dash, extra tiles appended to the picture), switched on in the map
# as the piece passes (bright, then faint, then back to plain sky), so the final picture is intro_a exactly.
# Format: ";" comments; "@key" then "<char> <OBJ colour 1-3> <#rrggbb> [name]" for Y y # (they must be intro_a's gold_light,
# gold and ink); then per piece "@piece <name> <x> <y> start=<frame> dir=<degrees> speed=<px per frame>" (x y = its top-left
# corner in the intact spigot, start = the frame it leaves (0 = the first frame after the flash), dir = the direction it
# flies in, 0 right, 90 up, 180 left; speed = its first speed, the flight accelerates) and its rows of ". Y y #"
# (. transparent), up to 16 rows, ended by a blank line. A piece is cut into 8x16 cells from its own left edge; cells that
# repeat (or mirror) share their tiles. The build fails on more than 20 cells, tiles that do not fit OBJ ids 56-91 (the
# drink frames' tiles, which the next level load puts back), any frame with more than 10 sprites on a scanline, a piece
# that does not leave the screen, or trail tiles that do not fit the picture's tile budget.
BURST_FILE = "intro_pieces.txt"
BURST_PIC = "intro_a"
BURST_OBJ = 56                  # OBJ_MUG: tiles 56..91 (36, the ids before OBJ_COIN) hold the pieces
BURST_OBJ_N = 36
BURST_OAM = 20                  # OAM 20..: the portrait overlay of a speaker page has 4..19
BURST_PAL = 4                   # CGB OBJ palette 4 (OBJPAL_ENH: unused on a cut-scene)
BURST_ACC = 0.09                # px / frame^2 added to a piece's first speed
BURST_LINE_MAX = 10
BURST_FRAME = (8, 32, 80, 104)  # a speaker page's portrait frame (x0, y0, x1, y1): no trail dot in a cell it touches
TRAIL_BRIGHT, TRAIL_FAINT = "g", "e"   # intro_a's key characters of the dots: shade 0 cream, shade 1 mauve (both in palette 1)
TRAIL_S0 = 8                    # the first dot is this far (px along the path) from the piece's start centre
TRAIL_SPARSE = 24               # every second dot only over the first TRAIL_SPARSE px after that ("further back is sparser")
TRAIL_BRIGHT_FRAMES = 6         # a dot stays bright this many frames after the piece passed, then faint ...
TRAIL_FAINT_FRAMES = 8          # ... this many, then the sky again
# The burst (owner 2026-10-15: "the actual explosion graphic that used to be in the middle should be there and should pulse while
# the pieces fly away and then die down once they're gone, replaced by an electric crackle"): a gold star of BG tiles over the
# spigot's spot (4 x 4 cells from BURST_CELL0, in the picture's palette 0: light, gold, sky), drawn in three sizes, switched in the
# map by the same timed writes as the trail (an event table; BURST_TIMELINE: frame, size), so the final picture is intro_a.
# Then the crackle: two 8x16 OBJ sprites (OBJ ids CRACKLE_OBJ.., OBJ palette BURST_PAL) flicker above the stub.
BURST_CELL0 = (11, 2)           # the star's top-left cell (column, row): its centre (104, 28) is the middle of the spigot
BURST_W, BURST_H = 4, 3         # cells
BURST_SIZES = {"M": 10, "B": 14.5}      # radii in px of the two sizes (the picture has room for 22 tiles more)
BURST_TIMELINE = ((0, "B"), (9, "M"), (18, "B"), (27, "M"), (32, "."))
CRACKLE_OBJ = 96                # OBJ_DANCER: the INTRO has no overlay, the next venue's load puts its own tiles back
CRACKLE_XY = (98, 27)           # the first crackle sprite's top-left (the second 6 px to the right): above the stump
CRACKLE_PATTERNS = 4            # zig-zag bolts (crackle_art), each one 8x16 sprite pair; story_crackle flickers between them


def crackle_art(k):
    """bolt k -> 16 rows of 8 characters ('. Y y'): a one-pixel zig-zag top to bottom (steps of up to 3 px sideways, a short
    gold side spark here and there), light on the sky, a gold halo beside it"""
    seed, x, rows = 0x35 + 41 * k, 3 + k % 3, []
    for y in range(16):
        seed = (seed * 109 + 89) & 255
        nx = min(6, max(1, x + (seed >> 5) % 5 - 2 + (1 if x < 3 else -1 if x > 4 else 0)))
        r = ["."] * 8
        for c in range(min(x, nx), max(x, nx) + 1):
            r[c] = "Y"
        for c in range(8):
            if r[c] == "." and any(0 <= c + d < 8 and r[c + d] == "Y" for d in (-1, 1)) and (y + k) % 3 == 0:
                r[c] = "y"
        rows.append("".join(r))
        x = nx
    return rows


SCRATCH_CURSOR = 170            # story_scratch offset of the trail's cursor (src/story.c PB_T is [168]); then its stage
TRAIL_SCHED = 3                 # writes a frame the generator schedules at most
BURST_FIRST_WRITE = 6           # the first frame the map can be written (the flash's fade-in has no room before)
TRAIL_PER_FRAME = 5             # map bytes queued per frame at most (each costs ~6 lines of logic and ~0.7 DIV tick of VBlank),
                                # and only while the list has room: an entry already in it counts 2 ticks, one trail byte 1 (of 10)


def read_pieces(burst_key=None):
    path = PIC_DIR / BURST_FILE
    if not path.is_file():
        fail(f"{path} is missing")
    key, pieces, cur = {}, [], None
    for ln in path.read_text().splitlines():
        if ln.startswith(";"):
            continue
        if ln.startswith("@key"):
            continue
        if ln.startswith("@piece"):
            p = ln.split()
            kv = dict(q.split("=") for q in p[4:])
            if len(p) < 7 or set(kv) != {"start", "dir", "speed"}:
                fail(f"{BURST_FILE}: bad piece line {ln!r}")
            cur = {"name": p[1], "x": int(p[2]), "y": int(p[3]), "start": int(kv["start"]), "dir": float(kv["dir"]),
                   "speed": float(kv["speed"]), "rows": []}
            pieces.append(cur)
        elif not ln.strip():
            cur = None
        elif cur is None:
            p = ln.split()
            if len(p) < 3 or p[0] not in "Yy#" or p[1] != "123"["Yy#".index(p[0])] or not re.fullmatch(r"#[0-9a-fA-F]{6}", p[2]):
                fail(f"{BURST_FILE}: bad key line {ln!r}")
            key[p[0]] = p[2].lower()
        else:
            cur["rows"].append(ln)
    if set(key) != set("Yy#"):
        fail(f"{BURST_FILE}: the key must define Y, y and #")
    if burst_key:
        for c in "Yy#":
            if burst_key[c]["hex"] != key[c]:
                fail(f"{BURST_FILE}: {c} is {key[c]}, intro_a's is {burst_key[c]['hex']}")
    return key, pieces


def burst_path(p, t):
    """the piece's top-left corner at frame t (ints): held in the intact spigot before its start"""
    te = max(0, t - p["start"])
    s = p["speed"] * te + BURST_ACC * te * te
    a = p["dir"] * 3.141592653589793 / 180
    return round(p["x"] + s * math.cos(a)), round(p["y"] - s * math.sin(a))


def burst_build(key, pieces, pic):
    """-> dict: the OBJ tiles, entries, the per-frame OAM table, the trail dots (events and the extra BG tiles); mutates pic
    (extra: the dot tiles appended to the picture, attr: the dot cells use the palette that has the dot colours). The build
    fails above BURST_LINE_MAX sprites on a line, on a piece that never leaves the screen, on a tile budget overrun."""
    if not pieces:
        fail(f"{BURST_FILE}: no pieces")
    pairs, entries = [], []
    for i, p in enumerate(pieces):
        rows = p["rows"]
        if not rows or len({len(r) for r in rows}) != 1 or set("".join(rows)) - set(".Yy#") or len(rows) > 16:
            fail(f"{BURST_FILE}: piece {p['name']}: rows of '. Y y #', all as wide, at most 16 high")
        w, h = len(rows[0]), len(rows)
        p["w"], p["h"] = w, h
        if not (0 <= p["x"] and p["x"] + 8 * ((w + 7) // 8) <= 160 and 0 <= p["y"] and p["y"] + 16 <= 144):
            fail(f"{BURST_FILE}: piece {p['name']} is not on the screen")
        grid = [r.translate(str.maketrans("Yy#", "-+#")) + "." * (8 * ((w + 7) // 8) - w) for r in rows]
        grid += ["." * len(grid[0])] * (16 - h)
        for c in range((w + 7) // 8):
            cell = [r[c * 8:c * 8 + 8] for r in grid]
            mirror = [r[::-1] for r in cell]
            canon, flip = (cell, 0) if cell <= mirror else (mirror, 1)
            if canon not in pairs:
                pairs.append(canon)
            entries.append((i, c * 8, pairs.index(canon), flip))
    if len(entries) > 40 - BURST_OAM:
        fail(f"{BURST_FILE}: {len(entries)} cells (OAM {BURST_OAM}..39 holds {40 - BURST_OAM})")
    if len(pairs) * 2 > BURST_OBJ_N:
        fail(f"{BURST_FILE}: {len(pairs)} tile pairs, OBJ ids {BURST_OBJ}..{BURST_OBJ + BURST_OBJ_N - 1} hold {BURST_OBJ_N // 2}")
    tiles = [[b for half in (pair[:8], pair[8:]) for b in tile_bytes(half, 0, 0)] for pair in pairs]

    def shown(q, dx):
        return not (q[1] + 16 < 1 or q[1] + 16 > 160 or q[0] + dx + 8 < 1 or q[0] + dx + 8 > 167)

    # the frame a piece has left the screen for good (every cell hidden): the flight's end
    leave = []
    for p in pieces:
        t = p["start"]
        while any(shown(burst_path(p, t), dx) for (i, dx, _, _) in entries if pieces[i] is p):
            t += 1
            if t > 200:
                fail(f"{BURST_FILE}: piece {p['name']} does not leave the screen")
        leave.append(t)

    # ---- the trail dots: where, when, and the picture's tiles with them ----
    px, pix, tmap = pic["px"], pic["pix"], pic["tmap"]
    frame_x0, frame_y0, frame_x1, frame_y1 = BURST_FRAME
    cellpix = lambda cx, cy: [pix[cy * 8 + y][cx * 8:cx * 8 + 8] for y in range(8)]
    # a cell takes a dash if it holds nothing but sky and ink (palette 1 has the dot colours and both of those) and the
    # dash's pixels are sky, and the speaker pages' portrait frame does not cover it
    pure = lambda cx, cy, px2: set("".join(cellpix(cx, cy))) <= set(".#BO") and all(pix[y][x] == "." for x, y in px2) and not (
        cx * 8 < frame_x1 and cx * 8 + 8 > frame_x0 and cy * 8 < frame_y1 and cy * 8 + 8 > frame_y0)
    bcells = [(BURST_CELL0[0] + i, BURST_CELL0[1] + j) for j in range(BURST_H) for i in range(BURST_W)]
    used, dots = set(bcells), []                 # dots: (t_bright, cx, cy, [(x, y)])   (no dash in the burst's cells)
    for i, p in enumerate(pieces):
        a = p["dir"] * math.pi / 180
        ux, uy = math.cos(a), -math.sin(a)
        c0x, c0y = p["x"] + p["w"] / 2, p["y"] + p["h"] / 2
        cand = []
        if abs(ux) >= abs(uy):                   # two dashes (2 px across) per column of cells
            for k in range(20):
                s = (8 * k + 4 - c0x) / ux
                y = round(c0y + uy * s) & ~1          # (even rows only: few different tiles)
                if s >= TRAIL_S0 and 0 <= y < 104:
                    cand.append((s, k, y // 8, [(8 * k + dx, y) for dx in (1, 2, 5, 6)]))
        else:                                    # two dashes (2 px along) per row of cells
            for j in range(13):
                s = (8 * j + 4 - c0y) / uy
                x = round(c0x + ux * s) & ~1
                if s >= TRAIL_S0 and 0 <= x < 160:
                    cand.append((s, x // 8, j, [(x, 8 * j + dy) for dy in (1, 2, 5, 6)]))
        cand.sort()
        for n, (s, cx, cy, px2) in enumerate(cand):
            if s < TRAIL_S0 + TRAIL_SPARSE and n % 2:
                continue
            if (cx, cy) in used or not pure(cx, cy, px2):
                continue
            used.add((cx, cy))
            te = (-p["speed"] + math.sqrt(p["speed"] ** 2 + 4 * BURST_ACC * s)) / (2 * BURST_ACC)
            dots.append((p["start"] + math.ceil(te), cx, cy, px2))
    # the dot tiles: the cell's plain sky with a bright / faint dash
    extra, ev = [], []
    base = len(pic["tiles"])
    sky = {(cx, cy) for (_, cx, cy, _) in dots}
    for (tb, cx, cy, px2) in sorted(dots):
        ids = []
        for shade in (0, 1):
            srows = [list("".join(".-+#"[v] for v in px[cy * 8 + y][cx * 8:cx * 8 + 8])) for y in range(8)]
            for (x, y) in px2:
                srows[y - cy * 8][x - cx * 8] = ".-+#"[shade]
            t = tuple(tile_bytes(["".join(r) for r in srows], 0, 0))
            if t not in extra:
                extra.append(t)
            ids.append(base + extra.index(t))
        clean = tmap[cy * 20 + cx]
        ev += [(tb, cx, cy, ids[0]), (tb + TRAIL_BRIGHT_FRAMES, cx, cy, ids[1]),
               (tb + TRAIL_BRIGHT_FRAMES + TRAIL_FAINT_FRAMES, cx, cy, clean)]
    ev.sort(key=lambda e: (e[0], e[2], e[1]))
    # ---- the burst star: its tiles per size and the map writes of the timeline (inner cells first; a cell whose tile did not
    # change is not written; the sky is the picture's own tile, so the last step leaves intro_a exactly) ----
    kk0 = pic["key"]
    if pic["pals"][0][:3] != [kk0["Y"]["hex"], kk0["y"]["hex"], kk0["."]["hex"]]:
        fail(f"{BURST_PIC}: palette 0 must be gold_light, gold, sky (the burst star's)")
    for (cx, cy) in bcells:
        if tmap[cy * 20 + cx] != tmap[BURST_CELL0[1] * 20 + BURST_CELL0[0]] or any(v != 2 for r in px[cy * 8:cy * 8 + 8] for v in r[cx * 8:cx * 8 + 8]):
            fail(f"{BURST_PIC}: the burst's cell ({cx},{cy}) is not plain sky")
    sw, sh = BURST_W * 8, BURST_H * 8
    mx, my = (sw - 1) / 2, (sh - 1) / 2

    def star(sz):
        """the size's 32x32 pixels as shade characters (eight points, a light core, gold points, sky around)"""
        if sz == ".":
            return [["+"] * sw for _ in range(sh)]
        rad = BURST_SIZES[sz]
        g = []
        for y in range(sh):
            row = []
            for x in range(sw):
                dx, dy = x - mx, y - my
                r = math.hypot(dx, dy)
                f = 0.5 + 0.5 * abs(math.cos(4 * math.atan2(dy, dx))) ** 2
                row.append("." if r < rad * f * 0.62 else "-" if r < rad * f else "+")
            g.append(row)
        return g

    cur = [[tmap[(BURST_CELL0[1] + j) * 20 + BURST_CELL0[0] + i] for i in range(BURST_W)] for j in range(BURST_H)]
    rows_ev, star0 = [], []                      # star0: the first size: the map's cells as the picture is drawn (LCD off)
    base = len(pic["tiles"])
    order = sorted(range(BURST_H), key=lambda j: abs(j - (BURST_H - 1) / 2))      # a step writes its middle row first
    for n_step, (tb, sz) in enumerate(BURST_TIMELINE):
        g = star(sz)
        grid = []
        for j in range(BURST_H):
            ids = []
            for i in range(BURST_W):
                rows = ["".join(g[j * 8 + y][i * 8:i * 8 + 8]) for y in range(8)]
                t = tuple(tile_bytes(rows, 0, 0))
                if t in pic["tiles"]:
                    ids.append(pic["tiles"].index(t))
                else:
                    if t not in extra:
                        extra.append(t)
                    ids.append(base + extra.index(t))
            grid.append(ids)
        if n_step == 0:
            star0 = [v for r in grid for v in r]
            cur = grid
            continue
        for j in order:
            if grid[j] != cur[j]:                # (a whole row of 4 cells is one VBlank list entry: 2 + 4 ticks, half the cost of four)
                rows_ev.append((tb, BURST_CELL0[1] + j, list(grid[j])))
                cur[j] = grid[j]
    for (cx, cy) in bcells:
        pic["attr"][cy * 20 + cx] = 0            # the star's cells use the picture's palette 0 (light, gold, sky, ink)
    # the schedule, frame by frame, as story_burst_step will find room for it: a row first (its 6 ticks of the list's 10), then the
    # trail's single cells (3 ticks each); one entry is in the list already (the text); nothing is written before the fade-in is over
    sched, srows, ti, ri, f, lag, rlag = [], [], 0, 0, BURST_FIRST_WRITE, 0, 0
    while ti < len(ev) or ri < len(rows_ev):
        vq, by, n = 1, 0, 0
        if ri < len(rows_ev) and rows_ev[ri][0] <= f and vq * 2 + by + 2 + BURST_W <= 11:
            srows.append((f, rows_ev[ri][1], rows_ev[ri][2]))
            rlag = max(rlag, f - rows_ev[ri][0])
            ri, vq, by = ri + 1, vq + 1, by + BURST_W
        while ti < len(ev) and ev[ti][0] <= f and n < TRAIL_PER_FRAME and vq * 2 + by < 10:
            sched.append((f,) + ev[ti][1:])
            lag = max(lag, f - ev[ti][0])
            ti, vq, by, n = ti + 1, vq + 1, by + 1, n + 1
        f += 1
    ev = sched
    print(f"burst schedule: {len(ev)} trail writes (the latest {lag} frames behind its piece), {len(srows)} star rows ({rlag} behind)")
    # the dot cells take the palette that has the dot colours (any palette has the plain sky in slot 2)
    kk = pic["key"]
    want = {0: kk[TRAIL_BRIGHT]["hex"], 1: kk[TRAIL_FAINT]["hex"], 2: kk["."]["hex"]}
    pal = next((n for n, q in enumerate(pic["pals"]) if all(q[s] == c for s, c in want.items())), None)
    if pal is None:
        fail(f"{BURST_PIC}: no palette has the trail dots' colours {want}")
    for (cx, cy) in sky:
        pic["attr"][cy * 20 + cx] = pal
    pic["extra"] = [list(t) for t in extra]
    crackle_t = srows[-1][0] + 1                # the star is gone: the crackle from this frame on
    crk_tiles = []
    for k in range(CRACKLE_PATTERNS):
        rows = [r.translate(str.maketrans("Yy", "-+")) for r in crackle_art(k)]
        crk_tiles.append([b for half in (rows[:8], rows[8:]) for b in tile_bytes(half, 0, 0)])
    seed, crk_seq = 0x5B, []                    # per frame and sprite (32 frames): the bolt shown (0-3, +4: mirrored) or 255
    for _ in range(32):
        seed = (seed * 75 + 74) % 257
        crk_seq.append(255 if seed % 4 == 0 else (seed >> 2) % 4 + (4 if seed % 2 else 0))
    end = max([max(leave), crackle_t] + [e[0] for e in ev])
    pos = []                                    # per frame, per cell: OAM y, x (0, 0: not on the screen)
    for t in range(end + 1):
        for (i, dx, _, _) in entries:
            q = burst_path(pieces[i], t)
            pos += [q[1] + 16, q[0] + dx + 8] if shown(q, dx) else [0, 0]
    worst, worst_t = 0, 0
    for t in range(end + 4):
        lines = [0] * 144
        for (i, dx, _, _) in entries:
            q = burst_path(pieces[i], t)
            if not shown(q, dx):
                continue
            for y in range(max(0, q[1]), min(144, q[1] + 16)):
                lines[y] += 1
        if max(lines) > worst:
            worst, worst_t = max(lines), t
    if worst > BURST_LINE_MAX:
        fail(f"{BURST_FILE}: {worst} sprites on one scanline at frame {worst_t} (at most {BURST_LINE_MAX})")
    if end > 120:
        fail(f"{BURST_FILE}: the explosion lasts {end} frames (at most 120)")
    return {"tiles": tiles, "entries": entries, "end": end, "worst": worst, "worst_t": worst_t, "pos": pos, "leave": leave,
            "events": ev, "dots": len(dots), "extra": len(extra), "pal": pal, "crackle_t": crackle_t,
            "crk_tiles": crk_tiles, "crk_seq": crk_seq, "rows": srows, "star0": star0}


def burst_c(key, pieces, b, pic):
    """the C of the explosion for build/story_pictures.c. The flight is a table worked out here, frame by frame (OAM y, x per
    cell): the step is a copy, not arithmetic (SDCC's 16-bit multiplies made the frame's logic run past VBlank). The trail
    is a time-ordered list of map bytes (frame, x, y, tile id) the step queues from a cursor kept in story_scratch."""
    e, nev = len(b["entries"]), len(b["events"])
    pal = rgb15(["#000000", key["Y"], key["y"], key["#"]])
    ids = pic["ids"]
    pc = [f"// the INTRO's explosion (assets/story/pictures/{BURST_FILE}): {e} cells of 8x16, {len(b['tiles'])} tile pairs "
          f"at OBJ ids {BURST_OBJ}.., the last frame {b['end']}; {nev} trail map writes ({b['dots']} dots, "
          f"{b['extra']} extra BG tiles)",
          f"#define STB_E {e}", f"#define STB_END {b['end']}", f"#define STB_NEV {nev}",
          carr("stb_tiles", [v for t in b["tiles"] for v in t]),
          carr("stb_ent", [v for (i, dx, k, fl) in b["entries"] for v in (BURST_OBJ + 2 * k, (fl << 5) | BURST_PAL)]),
          carr("stb_pos", b["pos"]), carr("stb_pal", pal, "uint16_t"),
          carr("stb_ev", [v for (t, x, y, tile) in b["events"] for v in (t, x, y, ids[tile])]),
          f"#define STB_CRK_T {b['crackle_t']}",
          carr("stb_star", [pic["ids"][t] for t in b["star0"]]),
          f"#define STB_NROW {len(b['rows'])}",
          carr("stb_row", [v for (t, y, tl) in b["rows"] for v in [t, y] + [ids[x] for x in tl]]),
          carr("stb_crk_tiles", [v for t in b["crk_tiles"] for v in t]), carr("stb_crk_seq", b["crk_seq"]), "",
          "extern uint8_t story_scratch[];", "extern uint8_t vq_count, vq_held;",
          "extern void vq_add(uint8_t bank, const uint8_t *src, uint8_t x, uint8_t y, uint8_t n);",
          f"#define STB_CURSOR (*(uint16_t *)(story_scratch + {SCRATCH_CURSOR}))      // the next trail write",
          f"#define STB_RCUR   (story_scratch[{SCRATCH_CURSOR + 10}])                 // the next star row",
          f"#define STB_RSTAGE (story_scratch + {SCRATCH_CURSOR + 11})                // its {BURST_W} tile ids until the list copies them",
          f"#define STB_STAGE  (story_scratch + {SCRATCH_CURSOR + 2})                  // its tile ids until the VBlank list copies them", "",
          "// LCD off: the pieces' tiles into the OBJ ids and (CGB) their palette; the trail cursor to the start",
          "void story_burst_load(uint8_t cgb) BANKED {",
          f"    set_sprite_data({BURST_OBJ}, {len(b['tiles']) * 2}, stb_tiles);",
          f"    set_sprite_data({CRACKLE_OBJ}, {len(b['crk_tiles']) * 2}, stb_crk_tiles);",
          f"    set_bkg_tiles({BURST_CELL0[0]}, {BURST_CELL0[1]}, {BURST_W}, {BURST_H}, stb_star);   // the star, full size",
          f"    if (cgb) set_sprite_palette({BURST_PAL}, 1, stb_pal);",
          "    STB_CURSOR = 0;",
          "    STB_RCUR = 0;",
          "}", "",
          "// the crackle: two bolts flickering above the stump, frame t (any t: 32 repeat)",
          "static void stb_crackle(OAM_item_t *o, uint8_t t) {",
          "    uint8_t i, v;",
          "    for (i = 0; i < 2; i++, o++) {",
          "        v = stb_crk_seq[(uint8_t)(t + (i << 4) + (i << 2)) & 31];",
          "        if (v == 255) { o->y = 0; continue; }",
          f"        o->y = {CRACKLE_XY[1] + 16}; o->x = (uint8_t)({CRACKLE_XY[0] + 8} + i * 6);",
          f"        o->tile = {CRACKLE_OBJ} + ((v & 3) << 1); o->prop = ((v & 4) << 3) | {BURST_PAL};",
          "    }",
          "}", "",
          "void story_burst_crackle(uint8_t t) BANKED { stb_crackle(shadow_OAM + " + str(BURST_OAM) + ", t); }", "",
          "// frame t of the explosion (0 = the first after the flash): the pieces' OAM entries, and, when the VBlank list is free",
          "// (ev: how many it may queue: 0 in the picture switch), the trail's map writes that are due; 1 once everything is done",
          "uint8_t story_burst_step(uint8_t t, uint8_t ev) BANKED {",
          "    uint8_t i, n;",
          "    uint16_t c;",
          "    const uint8_t *p, *q = stb_ent;",
          f"    OAM_item_t *o = shadow_OAM + {BURST_OAM};",
          "    if (t > STB_END) t = STB_END;",
          "    p = stb_pos + (uint16_t)t * (STB_E * 2);",
          "    for (i = 0; i < STB_E; i++, o++, q += 2) {",
          "        o->y = *p++; o->x = *p++; o->tile = q[0]; o->prop = q[1];",
          "    }",
          "    c = STB_CURSOR;",
          "    if (ev && !vq_held) {",
          "        i = 0;                                   // (ticks of the list the star row took)",
          "        n = STB_RCUR;",
          "        p = stb_row + (uint16_t)n * (2 + " + str(BURST_W) + ");",
          "        if (n < STB_NROW && p[0] <= t && (uint8_t)(vq_count * 2) + 2 + " + str(BURST_W) + " <= 11) {",
          "            for (i = 0; i < " + str(BURST_W) + "; i++) STB_RSTAGE[i] = p[2 + i];",
          "            vq_add(0, STB_RSTAGE, " + str(BURST_CELL0[0]) + ", p[1], " + str(BURST_W) + ");",
          "            STB_RCUR = n + 1;",
          "            i = " + str(BURST_W) + ";",
          "        }",
          "        p = stb_ev + c * 4;",
          "        for (n = 0; n < ev && c < STB_NEV && (uint8_t)(vq_count * 2 + n + i) < 10 && p[0] <= t; n++, c++, p += 4) {",
          "            STB_STAGE[n] = p[3];",
          "            vq_add(0, STB_STAGE + n, p[1], p[2], 1);",
          "        }",
          "        STB_CURSOR = c;",
          "    }",
          "    if (t >= STB_CRK_T) stb_crackle(shadow_OAM + " + str(BURST_OAM) + ", t);",
          "    return t >= STB_END && c >= STB_NEV && STB_RCUR >= STB_NROW;",
          "}", ""]
    return pc


def obj_pairs(cells):
    """overlay cells [(dx, dy, 8x16 px)] -> [(dx, dy, tile pair)]."""
    return [(dx, dy, tuple(tile_bytes(r, 0, 0)) + tuple(tile_bytes(r, 0, 8)))
            for dx, dy, cell in cells for r in [["".join(".-+#"[v] for v in row) for row in cell]]]


def portrait(name, art, x, y):
    """One portrait-v2 source -> dict (w, h, x, y, tiles, map, attr, pals, obj, obj_tiles, obj_pals, px, ovl px)."""
    path = ROOT / art
    if not path.is_file() or not is_v2(path):
        fail(f"{name}: {art} is not a portrait-v2 source (every speaker has approved art)")
    px, attr, pals, cells, opals, lay = read_v2(path)
    tl, w, h = tiles_of(px)
    if w > MAX_W or h > MAX_H:
        fail(f"{name}: portrait {w * 8}x{h * 8} (max {MAX_W * 8}x{MAX_H * 8})")
    x = 2 if x is None else x
    y = 12 - h if y is None else y
    # the frame takes a tile around the picture; a picture whose bottom is row 12 stands on the text box, whose
    # top panel (row 13) is then the frame's bottom edge
    if x < 1 or x + w > 19 or y < 1 or y + h > 13:
        fail(f"{name}: the frame ({x - 1},{y - 1})..({x + w},{min(y + h, 13)}) leaves rows 0-13 / columns 0-19")
    uniq, tmap = [], []
    for t in tl:
        if t not in uniq:
            uniq.append(t)
        tmap.append(uniq.index(t))
    if len(uniq) > MAX_TILES:
        fail(f"{name}: {len(uniq)} unique tiles (max {MAX_TILES})")
    obj, otiles = [], []
    for dx, dy, pair in obj_pairs(cells):
        if pair not in otiles:
            otiles.append(pair)
        obj.append((dx, dy, otiles.index(pair) * 2))
    if len(obj) > MAX_OBJ:
        fail(f"{name}: {len(obj)} overlay sprites (max {MAX_OBJ})")
    for line in range(-16, 80):
        n = sum(1 for o in obj if o[1] <= line < o[1] + 16)
        if n > LINE_OBJ:
            fail(f"{name}: {n} overlay sprites on one line (max {LINE_OBJ}: the Spigoteer takes 2 of 10)")
    if len(opals) > MAX_OBJ_PALS:
        fail(f"{name}: {len(opals)} overlay palettes (max {MAX_OBJ_PALS})")
    return {"name": name, "art": art, "w": w, "h": h, "x": x, "y": y, "tiles": uniq, "map": tmap, "attr": attr,
            "pals": pals, "obj": obj, "obj_tiles": otiles, "obj_pals": opals, "px": px, "opx": lay}


def portraits(cfg):
    """-> {portrait id: portrait}. Id = the speaker's index for his main portrait; his variants (cfg 'variants') get
    the ids after the speakers (NARRATOR's id has no portrait), in the json's order. Each also gets 'speaker' and,
    for a variant, 'variant' (its name) and 'frm' / 'to' (the range as written)."""
    out = {}
    nxt = len(SPEAKERS)
    for si, name in enumerate(SPEAKERS):
        if si == NARRATOR:
            continue
        c = cfg.get(name)
        if c is None or "art" not in c:
            fail(f"assets/story/portraits.json: no art for {name}")
        extra = set(c) - {"art", "x", "y", "variants"}
        if extra:
            fail(f"{name}: unknown portraits.json keys {sorted(extra)} (palettes, map and overlay come from the art)")
        out[si] = dict(portrait(name, c["art"], c.get("x"), c.get("y")), speaker=si, variant=None)
        for vn, v in c.get("variants", {}).items():
            if not re.fullmatch(r"[A-Z]+", vn) or set(v) - {"art", "from", "to"} or "art" not in v or "from" not in v:
                fail(f"{name} variant {vn!r}: a name A-Z with 'art', 'from' and optionally 'to'")
            p = portrait(f"{name} {vn}", v["art"], c.get("x"), c.get("y"))
            out[nxt] = dict(p, speaker=si, variant=vn, frm=v["from"], to=v.get("to"))
            nxt += 1
    if nxt > 255:
        fail("too many portraits")
    return out


def page_ref(scenes, ref, last, who):
    """'SCENE' or 'SCENE:page' (pages from 1) -> (scene index, page index, page given); a scene alone: its first page
    (last: its last). Fails on a scene or page that does not exist."""
    m = re.fullmatch(r"(\w+?)(?::(\d+))?", ref or "")
    ids = [s["id"] for s in scenes]
    if not m or m.group(1) not in ids:
        fail(f"{who}: {ref!r} names no scene")
    s = ids.index(m.group(1))
    n = len(scenes[s]["pages"])
    if m.group(2) is None:
        return s, (n - 1 if last else 0), False
    k = int(m.group(2)) - 1
    if not 0 <= k < n:
        fail(f"{who}: {ref!r}: {scenes[s]['id']} has pages 1-{n}")
    return s, k, True


def assign_portraits(scenes, ports):
    """Each page's portrait id (s["pids"]): the speaker's main portrait, or the variant whose range holds the page.
    Fails on a range end given by page number that is not the speaker's page, two variants on one page, a variant
    no page uses."""
    for s in scenes:
        s["pids"] = [p for p, _ in s["pages"]]
    for pid, pt in ports.items():
        if pt["variant"] is None:
            continue
        who = f"{SPEAKERS[pt['speaker']]} variant {pt['variant']}"
        a = page_ref(scenes, pt["frm"], False, who)
        if pt["to"]:
            b = page_ref(scenes, pt["to"], True, who)
        else:
            b = (len(scenes) - 1, len(scenes[-1]["pages"]) - 1, False)
        for si, k, given in (a, b):
            if given and scenes[si]["pages"][k][0] != pt["speaker"]:
                fail(f"{who}: page {k + 1} of {scenes[si]['id']} is not {SPEAKERS[pt['speaker']]}'s")
        if b[:2] < a[:2]:
            fail(f"{who}: 'to' comes before 'from'")
        used = 0
        for si, s in enumerate(scenes):
            for k, (spk, _) in enumerate(s["pages"]):
                if spk == pt["speaker"] and a[:2] <= (si, k) <= b[:2]:
                    if s["pids"][k] != spk:
                        fail(f"{who}: {s['id']} page {k + 1} is already {ports[s['pids'][k]]['name']}")
                    s["pids"][k] = pid
                    used += 1
        if not used:
            fail(f"{who}: no page of {SPEAKERS[pt['speaker']]} in {pt['frm']}..{pt['to'] or 'the end'}")


def check_pictures(scenes):
    """SCENE_PICS against the script: every picture scene has pictures, the first from page 1, at most two (the engine
    switches once), a later one on a page of the scene that is the narrator's, and docs/story.md says so."""
    text = (ROOT / "docs/story.md").read_text()
    if set(SCENE_PICS) != set(PICTURE_SCENES):
        fail(f"SCENE_PICS names {sorted(SCENE_PICS)}, the picture scenes are {PICTURE_SCENES}")
    for s in scenes:
        if s["id"] not in SCENE_PICS:
            continue
        pl = SCENE_PICS[s["id"]]
        if not 1 <= len(pl) <= 2 or pl[0][0] != 1 or any(b[0] <= a[0] for a, b in zip(pl, pl[1:])):
            fail(f"{s['id']}: one picture from page 1, or two with the second on a later page")
        for page, name in pl[1:]:
            if page > len(s["pages"]):
                fail(f"{s['id']}: {name} appears on page {page}, the scene has {len(s['pages'])}")
            if s["pages"][page - 1][0] != NARRATOR:
                fail(f"{s['id']}: {name} appears on page {page}, which is not the narrator's (no portrait frame may "
                     f"be up when the picture changes)")
            if f"Picture (page {page}):" not in text:
                fail(f"docs/story.md: {s['id']} has no 'Picture (page {page}):' line for {name}")


# ---- output -----------------------------------------------------------------------------------------------------
def carr(name, vals, typ="uint8_t"):
    vals = list(vals)
    body = []
    for i in range(0, len(vals), 20):
        body.append("    " + ", ".join(str(v) for v in vals[i:i + 20]) + ",")
    return f"static const {typ} {name}[{max(1, len(vals))}] = {{\n" + ("\n".join(body) if vals else "    0") + "\n};"


def add_plates(ports):
    """Every portrait gets its name plate's tiles after its own (sp["tiles"], sp["art_tiles"] its art's count): one
    inverted HUD glyph per letter of the plate name (the cells either side are the frame's own bottom moulding); sp["plate"]: their tile indices in name order."""
    bar_blocks = dict(blocks(ROOT / "assets/tiles/bar.txt", named=True))
    story_blocks = dict(blocks(ROOT / "assets/tiles/story.txt", named=True))
    inv = lambda rows: ["".join({"#": "-", ".": "#"}.get(c, c) for c in r) for r in rows]
    for sp in ports.values():
        name = PLATE_NAMES.get(SPEAKERS[sp["speaker"]], SPEAKERS[sp["speaker"]])
        if len(name) > PLATE_CELLS:
            fail(f"{sp['name']}: plate name {name!r} is over {PLATE_CELLS} cells (PLATE_NAMES)")
        sp["art_tiles"] = len(sp["tiles"])
        sp["plate_name"] = name
        idx = {}
        for ch in name:
            if ch not in idx:
                src = story_blocks["glyph_hyphen"] if ch == "-" else bar_blocks["glyph_" + ch]
                idx[ch] = len(sp["tiles"])
                sp["tiles"].append(tile_bytes(inv(src), 0, 0))
        sp["plate"] = [idx[ch] for ch in name]
        if len(sp["tiles"]) > 255:
            fail(f"{sp['name']}: too many tiles")


def scene_budget(scenes, ports, budget):
    """Per scene its portraits (s["spk"]: portrait ids in order of appearance; a speaker's variant is one more), all
    loaded when the scene starts: their BG tiles must fit the budget together (a scene with several speakers swaps
    them, it does not reload), their overlay tiles the OBJ ids. The build fails on any overflow."""
    for sp in ports.values():
        if len(sp["tiles"]) > budget:
            fail(f"{sp['name']}: {len(sp['tiles'])} tiles (budget {budget})")
    for s in scenes:
        spk = []
        for p in s["pids"]:
            if p != NARRATOR and p not in spk:
                spk.append(p)
        if len(spk) > MAX_SPK:
            fail(f"{s['id']}: {len(spk)} portraits (max {MAX_SPK})")
        n = sum(len(ports[p]["tiles"]) for p in spk)
        if s["id"] in PICTURE_SCENES:            # a picture scene keeps one portrait slot (the biggest) and streams
            n = max([len(ports[p]["tiles"]) for p in spk] or [0])       # each speaker's tiles into it (src/story.c)
        if n > budget:
            fail(f"{s['id']}: its portraits need {n} BG tiles, {budget} are free")
        no = sum(len(ports[p]["obj_tiles"]) * 2 for p in spk)
        if no > OBJ_TILES:
            fail(f"{s['id']}: its overlays need {no} OBJ tiles, {OBJ_TILES} are free")
        s["spk"] = spk
        s["bg_tiles"] = n
        s["obj_tiles"] = no


def main():
    outdir, prev = Path(sys.argv[1]), Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True)
    prev.mkdir(parents=True, exist_ok=True)
    ids = art_ids(outdir / "art.h")
    scenes = parse_script(ROOT / "docs/story.md")
    cfg = json.loads((ROOT / "assets/story/portraits.json").read_text())
    ports = portraits(cfg)
    assign_portraits(scenes, ports)
    add_plates(ports)

    # the story font: punctuation, frame, icon (ids FONT_BASE..), A-Z 0-9 space are the HUD's own tiles
    font_blocks = blocks(ROOT / "assets/tiles/story.txt", named=True)
    font_names = [n for n, _ in font_blocks]
    font = []
    for n, rows in font_blocks:
        if len(rows) != 8 or any(len(r) != 8 for r in rows):
            fail(f"story.txt @{n}: not 8x8")
        font += tile_bytes(rows, 0, 0)
    font_base = ids["BAR_TILE_COUNT"]
    fid = {n: font_base + i for i, n in enumerate(font_names)}
    port_base = font_base + len(font_names)
    budget = BG_END - port_base

    def glyph(ch):
        if ch == " ":
            return ids["TILE_HUD_BLANK"]
        if ch in PUNCT:
            return fid["glyph_" + PUNCT[ch]]
        return ids["TILE_GLYPH_" + ch]

    scene_budget(scenes, ports, budget)
    for s in scenes:
        s["venue"] = 255
        s["pic"] = 255
        s["swpage"] = 0
        if s["id"] not in PICTURE_SCENES:
            suffix = s["id"].split("_", 1)[1]
            s["venue"] = next(c[1] for c in CHAPTERS if c[0] == suffix)

    # the pictures of the picture scenes (rows 0-12): their tiles at BG ids 0-35 (the venue pool, free here) and then
    # above the scene's one portrait slot (STORY_PORTRAIT_BASE + its biggest portrait) up to 255; map, attributes
    # (CGB palette slots 0 5 6 7, or 1 = the HUD's) and palettes. A scene's second picture loads over its first.
    check_pictures(scenes)
    pics = []
    for sid in PICTURE_SCENES:
        sc = next(s for s in scenes if s["id"] == sid)
        if sid in PIC_SHARE:
            first = next(s for s in scenes if s["id"] == PIC_SHARE[sid])
            if sc["bg_tiles"] > first["bg_tiles"]:
                fail(f"{sid}: its portraits need {sc['bg_tiles']} tiles, the shared picture of {first['id']} sits above {first['bg_tiles']}")
            if SCENE_PICS[sid] != SCENE_PICS[first["id"]]:
                fail(f"{sid}: SCENE_PICS must list {first['id']}'s pictures")
            sc["pic"] = first["pic"]
            continue
        pbase = port_base + sc["bg_tiles"]
        sc["pic"] = len(pics)
        for page, name in SCENE_PICS[sid]:
            p = read_pic(name)
            if name == BURST_PIC:                # its explosion: the pieces' OBJ tiles and the trail dots' BG tiles (appended)
                bkey, bpieces = read_pieces(p["key"])
                burst = burst_build(bkey, bpieces, p)
            n = len(p["tiles"]) + len(p.get("extra", []))
            room = PIC_POOL + BG_END - pbase
            if n > room:
                fail(f"{name}: {n} unique tiles, {sid} has room for {room} (ids 0-{PIC_POOL - 1} and {pbase}-{BG_END - 1})")
            pid = [i if i < PIC_POOL else pbase + i - PIC_POOL for i in range(n)]
            p.update(scene=sid, page=page, base=pbase, ids=pid, map=[pid[t] for t in p["tmap"]], n_extra=len(p.get("extra", [])),
                     cattr=[1 if a == "H" else PIC_SLOTS[a] for a in p["attr"]])
            pics.append(p)
            if page > 1:
                sc["swpage"] = page

    # ---- build/story_data.c ----
    text = []
    scene_ofs = []
    for s in scenes:
        scene_ofs.append(len(text))
        for pid, (pre, lines), alts in zip(s["pids"], s["raws"], s["alts_raw"]):
            if pid >= 0x80:
                fail(f"portrait id {pid}: bit 7 of the page byte marks a variant")
            # a page's variants first (portrait id | 0x80, the condition id, the lines), then the page itself; a line
            # is its length (the first line's top 3 bits: the @beat steps) and its cells
            for cond, vpre, vl in alts:
                text += [pid | 0x80, cond]
                for i in range(PAGE_LINES):
                    l = vl[i] if i < len(vl) else ""
                    text.append(len(l) | (vpre << 5 if i == 0 else 0))
                    text += [ord(ch) for ch in l]
            text.append(pid)
            for i in range(PAGE_LINES):
                l = lines[i] if i < len(lines) else ""
                text.append(len(l) | (pre << 5 if i == 0 else 0))
                text += [ord(ch) for ch in l]
    npid = max(ports) + 1
    names = []                                   # per portrait id: its plate name's tiles (relative to its first), 0-terminated
    for i in range(npid):
        t = ports[i]["plate"] if i in ports else []
        names += (t + [0] * 12)[:12]
    pid_spk = [ports[i]["speaker"] if i in ports else NARRATOR for i in range(npid)]
    hdr = []
    for s in scenes:
        spk = s["spk"] + [255] * (MAX_SPK - len(s["spk"]))
        hdr += [s["venue"], s["pic"], len(s["pages"]), len(s["spk"])] + spk + [s["swpage"]]
        hdr += [ord(ch) for ch in s["title"].ljust(21, "\0")]
    SCENE_HDR = 4 + MAX_SPK + 1 + 21
    shifts = shift_list()
    pat_ids = {n: i for i, n in enumerate(PATTERNS)}
    goals = []
    for row in shifts:
        for sh in row:                     # type, count, flags, seconds, twist bits, pattern, walk %, spawn %, quota,
            goals += [sh["type"], sh["count"], sh["flags"], sh["secs"], sh["twist"], pat_ids[sh["pattern"]], sh["walk"],
                      sh["spawn"], sh["quota"], sh["mosh_limit"]]   # the mosh pit's x limit (0: no mosh pit)
            goals += [ord(ch) for ch in sh["line1"].ljust(21, "\0")] + [ord(ch) for ch in sh["line2"].ljust(21, "\0")]
    GOAL_LEN = 10 + 42
    pats, pat_ofs = [], []
    for e in PATTERNS.values():
        pat_ofs.append(len(pats) | (len(e) << 8))
        pats += [b | (PAT_WAITS[w] << 4) for b, w in e]
    seq = []
    for ch in CHAPTERS:
        seq += [STEP_KINDS[k] << 4 | i | (STEP_SKIP if slot_skipped(k, ch[0]) else 0) for k, i in SEQUENCE]

    d = ["// generated by tools/gen_story.py from docs/story.md -- do not edit",
         "#pragma bank 255", "#include <gb/gb.h>", "#include <gb/cgb.h>", "#include <stdint.h>", '#include "mpump.h"', '#include "story.h"', "",
         "// the script: per page the portrait id (the speaker's own, or a variant of his), then 3 lines of (length,",
         "// characters); before a page its text variants: the portrait id | 0x80, the condition id, 3 lines",
         carr("st_text", text), carr("st_scene_ofs", scene_ofs, "uint16_t"),
         "// portrait id -> its speaker (the speaker's own id: his main portrait; NARRATOR: none)",
         carr("st_pid_spk", pid_spk),
         "// per scene: venue (255: a picture), picture (255: none), pages, portraits, their ids x3, the page the next picture",
         "// appears on (1-based; 0: never), title",
         carr("st_scene_hdr", hdr), carr("st_names", names),
         "// per chapter, per shift (opening, happy hour, last call): goal type, count, flags, timer seconds, twist bits",
         "// (TWIST_*), arrival pattern, walk %, spawn %, quota (0: the row's), the mosh pit's x limit (0: none), the two",
         "// banner lines", carr("st_goals", goals),
         "// arrival patterns: entries (bar | wait code << 4) and per pattern its offset | length << 8",
         carr("st_pats", pats or [0]), carr("st_pat_ofs", pat_ofs, "uint16_t"),
         "// per chapter the sequence of steps: kind << 4 | index, STEP_SKIP: not built yet (the engine passes over it)",
         carr("st_seq", seq), carr("st_font", font)]
    d += ["",
          "void story_scene_get(uint8_t s, uint8_t *dst) BANKED {",
          f"    const uint8_t *p = st_scene_hdr + (uint16_t)s * {SCENE_HDR};",
          "    uint8_t i;",
          f"    for (i = 0; i < {SCENE_HDR}; i++) dst[i] = p[i];",
          "}", "",
          "// page p of scene s: dst[0] the speaker, dst[1..54] the three lines padded with spaces, dst[55] the portrait;",
          "// the text is its first variant whose condition is set in conds (bit id - 1), else the page's own",
          "void story_page_get(uint8_t s, uint8_t p, uint8_t conds, uint8_t *dst) BANKED {",
          "    const uint8_t *q = st_text + st_scene_ofs[s];",
          "    uint8_t i, k, n;",
          "    for (;;) {",
          "        k = *q;",
          "        if (k & 0x80) {                       // a variant (they come before their page)",
          "            if (!p && ((conds >> (q[1] - 1)) & 1)) break;",
          "            q++;",
          "        } else if (!p) break;",
          "        else p--;",
          "        q++; for (k = 0; k < 3; k++) q += 1 + (*q & 31);",
          "    }",
          "    k = *q++;",
          "    if (k & 0x80) { k &= 0x7F; q++; }",
          "    dst[55] = k; *dst++ = st_pid_spk[k] | ((*q >> 5) << 4);   // the speaker, the @beat steps in the top nibble",
          "    for (k = 0; k < 3; k++) {",
          "        n = *q++ & 31;",
          "        for (i = 0; i < 18; i++) *dst++ = i < n ? q[i] : ' ';",
          "        q += n;",
          "    }",
          "}", "",
          "void story_name_get(uint8_t spk, uint8_t *dst) BANKED {",
          "    const uint8_t *p = st_names + (uint16_t)spk * 12;",
          "    uint8_t i;",
          "    for (i = 0; i < 12; i++) dst[i] = p[i];",
          "}", "",
          "// the goal of chapter ch's shift sh",
          "void story_goal_get(uint8_t ch, uint8_t sh, uint8_t *dst) BANKED {",
          f"    const uint8_t *p = st_goals + (uint16_t)(ch * {len(SHIFT_NAMES)} + sh) * {GOAL_LEN};",
          "    uint8_t i;",
          f"    for (i = 0; i < {GOAL_LEN}; i++) dst[i] = p[i];",
          "}", "",
          "// arrival pattern id -> its entries in dst[STORY_PAT_MAX]; returns the length (0: normal, random bars)",
          "uint8_t story_pattern_get(uint8_t id, uint8_t *dst) BANKED {",
          "    uint16_t o = st_pat_ofs[id];",
          "    uint8_t n = o >> 8, i;",
          "    for (i = 0; i < n; i++) dst[i] = st_pats[(uint8_t)o + i];",
          "    return n;",
          "}", "",
          "uint8_t story_step_get(uint8_t ch, uint8_t s) BANKED {   // chapter ch's step s (STEP_* | index)",
          f"    return st_seq[ch * {len(SEQUENCE)} + s];",
          "}", "",
          "void story_font_load(void) BANKED {           // LCD off",
          f"    set_bkg_data(STORY_FONT_BASE, {len(font_names)}, st_font);",
          "}", ""]
    (outdir / "story_data.c").write_text("\n".join(d))

    # ---- build/story_pictures.c (its own bank: the pictures' tiles are ~7 KB) ----
    PC = ["// generated by tools/gen_story.py from assets/story/pictures/*.txt -- do not edit",
          "#pragma bank 255", "#include <gb/gb.h>", "#include <gb/cgb.h>", "#include <stdint.h>", '#include "mpump.h"', '#include "story.h"', ""]
    hud = hud_palette()
    for i, p in enumerate(pics):
        pals = [v for pal in p["pals"] for v in rgb15(pal)]
        alltiles = p["tiles"] + [tuple(t) for t in p.get("extra", [])]
        PC += [f"// picture {i} {p['name']} ({p['scene']} from page {p['page']}): {len(p['tiles'])} tiles (+ {len(alltiles) - len(p['tiles'])} trail), "
               f"{len(p['pals'])} palette(s), {p['attr'].count('H')} HUD-palette cell(s); tiles 0-{PIC_POOL - 1} then "
               f"{p['base']}..",
               carr(f"stp{i}_tiles", [b for t in alltiles for b in t]), carr(f"stp{i}_map", p["map"]),
               carr(f"stp{i}_attr", p["cattr"]), carr(f"stp{i}_pal", pals + [0] * (16 - len(pals)), "uint16_t")]
    n = len(pics)
    PC += ["", f"static const uint8_t *const stp_tiles[{n}] = {{ " + ", ".join(f"stp{i}_tiles" for i in range(n)) + " };",
           f"static const uint8_t *const stp_map[{n}] = {{ " + ", ".join(f"stp{i}_map" for i in range(n)) + " };",
           f"static const uint8_t *const stp_attr[{n}] = {{ " + ", ".join(f"stp{i}_attr" for i in range(n)) + " };",
           f"static const uint16_t *const stp_pal[{n}] = {{ " + ", ".join(f"stp{i}_pal" for i in range(n)) + " };",
           carr("stp_n", [len(p["tiles"]) + len(p.get("extra", [])) for p in pics]), carr("stp_base", [p["base"] for p in pics]),
           carr("stp_npal", [len(p["pals"]) for p in pics]),
           carr("stp_slot", PIC_SLOTS),
           carr("stp_hud", [v for c in hud for v in [c[0] | (c[1] << 5) | (c[2] << 10)]], "uint16_t"), "",
           "// LCD off: picture pic's tiles (ids 0-35, then the scene's free ids), its map and attributes over rows",
           "// 0..STORY_PIC_ROWS-1, and on CGB its palettes in BG slots 0, 5, 6, 7",
           "void story_pic_draw(uint8_t pic, uint8_t cgb) BANKED {",
           "    uint8_t n = stp_n[pic], k;",
           "    const uint8_t *t = stp_tiles[pic];",
           f"    set_bkg_data(0, n < {PIC_POOL} ? n : {PIC_POOL}, t);",
           f"    if (n > {PIC_POOL}) set_bkg_data(stp_base[pic], n - {PIC_POOL}, t + {PIC_POOL * 16});",
           f"    set_bkg_tiles(0, 0, 20, {PIC_ROWS}, stp_map[pic]);",
           "    if (!cgb) return;",
           "    VBK_REG = VBK_BANK_1;",
           f"    set_bkg_tiles(0, 0, 20, {PIC_ROWS}, stp_attr[pic]);",
           "    VBK_REG = VBK_BANK_0;",
           "    for (k = 0; k < stp_npal[pic]; k++) set_bkg_palette(stp_slot[k], 1, stp_pal[pic] + k * 4);",
           "}", "",
           "// the w tiles of map row y from column x, then their w attributes, into dst[2 * w] (a portrait wipe)",
           "void story_pic_row(uint8_t pic, uint8_t y, uint8_t x, uint8_t w, uint8_t *dst) BANKED {",
           f"    const uint8_t *m = stp_map[pic] + (uint16_t)y * 20 + x, *a = stp_attr[pic] + (uint16_t)y * 20 + x;",
           "    uint8_t i;",
           "    for (i = 0; i < w; i++) { dst[i] = m[i]; dst[w + i] = a[i]; }",
           "}", "",
           "// the picture's palettes (slots 0, 5, 6, 7 order) then the HUD's (BG 1): dst[5 * 4] RGB15 words, for the fade",
           "void story_pic_pals(uint8_t pic, uint16_t *dst) BANKED {",
           "    uint8_t i;",
           "    for (i = 0; i < 16; i++) dst[i] = stp_pal[pic][i];",
           "    for (i = 0; i < 4; i++) dst[16 + i] = stp_hud[i];",
           "}", ""]
    PC += burst_c(bkey, bpieces, burst, next(p for p in pics if p["name"] == BURST_PIC))
    (outdir / "story_pictures.c").write_text("\n".join(PC))

    # ---- build/story_portraits.c ----
    P = ["// generated by tools/gen_story.py from assets/story/portraits.json -- do not edit",
         "#pragma bank 255", "#include <gb/gb.h>", "#include <stdint.h>", '#include "mpump.h"', '#include "music.h"', '#include "story.h"', ""]
    for si, sp in sorted(ports.items()):
        t = [b for tt in sp["tiles"] for b in tt]
        ot = [b for pair in sp["obj_tiles"] for b in pair]
        pal = [v for p in sp["pals"] for v in rgb15(p)]
        opal = [v for p in sp["obj_pals"] for v in rgb15(p)]
        obj = []
        for ox, oy, tile in sp["obj"]:
            obj += [oy & 255, ox & 255, tile, 1 << 5]           # bit 5: a CGB-only accent (DMG shows the BG)
        P += [f"// {sp['name']}: {sp['w'] * 8}x{sp['h'] * 8} at tile ({sp['x']},{sp['y']}), {len(sp['tiles'])} tiles, "
              f"{len(sp['pals'])} BG palette(s), {len(sp['obj'])} overlay sprite(s)",
              carr(f"pt{si}_tiles", t), carr(f"pt{si}_otiles", ot)]
        phdr = [sp["w"], sp["h"], sp["x"], sp["y"], len(sp["pals"]), len(sp["tiles"]), len(sp["obj"]), len(sp["obj_pals"]),
               len(sp["obj_tiles"]) * 2]
        body = phdr + sp["map"] + [0] * (49 - len(sp["map"])) + sp["attr"] + [0] * (49 - len(sp["attr"]))
        P += [carr(f"pt{si}_hdr", body), carr(f"pt{si}_pal", pal + [0] * (12 - len(pal)), "uint16_t"),
              carr(f"pt{si}_opal", opal + [0] * (16 - len(opal)), "uint16_t"),
              carr(f"pt{si}_obj", obj + [0] * (MAX_OBJ * 4 - len(obj))), ""]
    sel = [f"    case {si}: h = pt{si}_hdr; p = pt{si}_pal; o = pt{si}_opal; e = pt{si}_obj; break;" for si in sorted(ports)]
    selt = [f"    case {si}: t = pt{si}_tiles; ot = pt{si}_otiles; break;" for si in sorted(ports)]
    P += ["// portrait id spk (a speaker's id: his main portrait; STORY_SPEAKERS..: the variants) into the WRAM struct",
          "// (w 0: none)",
          "void portrait_get(uint8_t spk, portrait_t *dst) BANKED {",
          "    const uint8_t *h, *e; const uint16_t *p, *o;",
          "    uint8_t i, *d = (uint8_t *)dst;",
          "    switch (spk) {"] + sel + [
          "    default: dst->w = 0; return;",
          "    }",
          "    for (i = 0; i < 9 + 98; i++) d[i] = h[i];",
          "    music_pump();                                // (LCD off in a scene's load: the copies take most of a frame each)",
          "    for (i = 0; i < 12; i++) dst->pal[i] = p[i];",
          "    for (i = 0; i < 16; i++) dst->opal[i] = o[i];",
          "    music_pump();",
          f"    for (i = 0; i < {MAX_OBJ * 4}; i++) dst->obj[i] = e[i];",
          "    music_pump();",
          "}", "",
          "// LCD off: its BG tiles at bg_first.., its overlay tiles at OBJ obj_first..",
          "void portrait_tiles_load(uint8_t spk, uint8_t bg_first, uint8_t obj_first) BANKED {",
          "    const uint8_t *t, *ot;",
          "    switch (spk) {"] + selt + [
          "    default: return;",
          "    }",
          "    set_bkg_data(bg_first, pt_n[spk], t);",
          "    if (pt_on[spk]) set_sprite_data(obj_first, pt_on[spk], ot);",
          "}", "",
          "// BG tiles first..first+n-1 of portrait spk into dst[16 * n] (WRAM): a picture scene streams them to VRAM",
          "void portrait_tile_copy(uint8_t spk, uint8_t first, uint8_t n, uint8_t *dst) BANKED {",
          "    const uint8_t *t, *ot;",
          "    uint16_t i;",
          "    switch (spk) {"] + selt + [
          "    default: return;",
          "    }",
          "    t += (uint16_t)first * 16;",
          "    for (i = 0; i < (uint16_t)n * 16; i++) dst[i] = t[i];",
          "}", ""]
    nt = [len(ports[i]["tiles"]) if i in ports else 0 for i in range(npid)]
    no = [len(ports[i]["obj_tiles"]) * 2 if i in ports else 0 for i in range(npid)]
    P.insert(6, "// tiles per portrait id: BG, OBJ (the overlay)")
    P.insert(7, carr("pt_n", nt))
    P.insert(8, carr("pt_on", no))
    (outdir / "story_portraits.c").write_text("\n".join(P))

    # ---- build/story.h ----
    H = ["// generated by tools/gen_story.py -- do not edit", "#ifndef STORY_DATA_H", "#define STORY_DATA_H",
         "#include <gb/gb.h>", "#include <stdint.h>", '#include "art.h"', "",
         f"#define STORY_SCENES {len(scenes)}"]
    for i, s in enumerate(scenes):
        H.append(f"#define SC_{s['id']} {i}")
    H += [f"#define STORY_CHAPTERS {len(CHAPTERS)}   // chapter c: SC_PRE = 1 + 2c, SC_POST = 2 + 2c",
          f"#define SPK_NARRATOR {NARRATOR}",
          f"#define STORY_BEAT_SHORT {BEAT_FRAMES[0]}   // frames of a `|` / `||` mid-line beat (cell 1 / 2 of the text)",
          f"#define STORY_BEAT_LONG {BEAT_FRAMES[1]}", f"#define STORY_BEAT_UNIT {BEAT_UNIT}   // frames per @beat step",
          f"#define STORY_GAP_SPEAKER {GAP_SPEAKER}   // the engine's own gap before a page (an @beat longer than it wins)",
          f"#define STORY_GAP_PAGE {GAP_PAGE}", f"#define STORY_SPEAKERS {len(SPEAKERS)}",
          f"#define G_SERVE {G_SERVE}", f"#define G_CATCH {G_CATCH}", f"#define G_CLEAR {G_CLEAR}",
          f"#define F_NO_TAP {F_NO_TAP}", f"#define F_NO_BREAK {F_NO_BREAK}",
          f"#define TWIST_MOSH 0x{TWIST_MOSH:02X}       // goal_t.twist bits: the mosh pit (src/mosh.c), x limit in goal_t.pad",
          f"#define TWIST_FAST_TUNE 0x{TWIST_FAST_TUNE:02X}  // the venue's tune one frame a row faster (src/music.c)",
          "// page text conditions: bits of story_conds (docs/story.md \"Script format\")"]
    H += [f"#define COND_{n} 0x{1 << (i - 1):02X}" for n, i in CONDITIONS.items()]
    H += ["",
          "// story shifts: each chapter is a sequence of steps (shifts; mini-game and boss slots, skipped until built)",
          f"#define STORY_SHIFTS {len(SHIFT_NAMES)}",
          "#define STORY_SHIFT_NAMES { " + ", ".join(f'"{n}"' for n in SHIFT_NAMES) + " }   // the goal banner",
          f"#define STORY_STEPS {len(SEQUENCE)}    // " + ", ".join(f"{k} {i}" for k, i in SEQUENCE),
          f"#define STEP_SHIFT 0x{STEP_KINDS['SHIFT'] << 4:02X}", f"#define STEP_MINI 0x{STEP_KINDS['MINI'] << 4:02X}",
          f"#define STEP_BOSS 0x{STEP_KINDS['BOSS'] << 4:02X}", f"#define STEP_SKIP 0x{STEP_SKIP:02X}",
          "#define STEP_KIND 0x70", "#define STEP_INDEX 0x0F",
          f"#define STORY_PAT_MAX {PAT_MAX}   // arrival pattern entries: bar (bits 0-1) | wait code << 4",
          f"#define PAT_SHORT {PAT_SHORT}       // wait code 1 in frames (0: the interval, 2: twice it, 3: four times)", "",
          "// cut-scene BG tile budget: the story font at BAR_TILE_COUNT.. (the patron range is free: no patrons)",
          f"#define STORY_FONT_BASE BAR_TILE_COUNT", f"#define STORY_FONT_COUNT {len(font_names)}"]
    for n in font_names:
        H.append(f"#define ST_{n.upper()} (STORY_FONT_BASE + {font_names.index(n)})")
    H += [f"#define STORY_PORTRAIT_BASE (STORY_FONT_BASE + STORY_FONT_COUNT)   // the scene's portraits, one after the other",
          f"#define STORY_BG_END {BG_END}", f"#if STORY_PORTRAIT_BASE != {port_base}", "#error story.h out of date", "#endif",
          f"#define STORY_OBJ_TILES {OBJ_TILES}   // overlay tiles: OBJ_DANCER .. +31", f"#define STORY_MAX_OBJ {MAX_OBJ}",
          f"#define STORY_MAX_SPK {MAX_SPK}", f"#define STORY_PIC_ROWS {PIC_ROWS}",
          f"#define STORY_PICS {len(pics)}         // the full-screen pictures (assets/story/pictures), see SCENE_PICS",
          f"#define STORY_PIC_POOL {PIC_POOL}      // a picture's first 36 tiles at BG ids 0.., the rest above the scene's portrait slot",
          f"#define STORY_BURST_OAM {BURST_OAM}      // the INTRO's flying pieces: OAM entries from here ...",
          f"#define STORY_BURST_CELLS {len(burst['entries'])}      // ... this many",
          f"#define STORY_CRACKLE_T {burst['crackle_t']}      // from this frame on the crackle flickers above the stump",
          f"#define STORY_BURST_PIC {next(i for i, q in enumerate(pics) if q['name'] == BURST_PIC)}      // the picture (index) the crackle goes on showing",
          f"#define STORY_BURST_END {burst['end']}      // the last frame (after the flash) of the explosion",
          f"#define STORY_PLATE_FULL {int(PLATE_FULL)}   // 1: the name plate uses all the frame row's cells, 0: those between its corners",
          f"#define STORY_BURST_PER {TRAIL_PER_FRAME}      // trail map writes a frame at most", "",
          "typedef struct {",
          "    uint8_t w, h, x, y;          // tiles (w 0: no portrait); x, y the picture's top-left screen tile",
          "    uint8_t npal, ntiles, nobj, nobjpal, nobjtiles;",
          "    uint8_t map[49];             // tile index relative to the portrait's first tile, row-major",
          "    uint8_t attr[49];            // BG palette relative to its first slot",
          "    uint16_t pal[12];            // up to 3 BG palettes",
          "    uint16_t opal[16];           // up to 4 overlay OBJ palettes",
          f"    uint8_t obj[{MAX_OBJ * 4}];            // overlay: dy, dx (px from the picture's top-left), tile (relative), flags (bit 4 DMG OBP1, bit 5 CGB only)",
          "} portrait_t;",
          "typedef struct {",
          "    uint8_t venue, pic, pages, nspk, spk[3], swpage;   // swpage: the page (1-based) the next picture (pic + 1) appears on, 0 never",
          "    char title[21];",
          "} scene_hdr_t;",
          "typedef struct {",
          "    uint8_t type, count, flags, secs, twist, pattern, walk, spawn, quota, pad;   // pad: the mosh pit's limit",
          "    char line1[21], line2[21];",
          "} goal_t;                         // one shift's goal",
          "void story_scene_get(uint8_t s, uint8_t *dst) BANKED;   // dst: scene_hdr_t",
          "void story_page_get(uint8_t s, uint8_t p, uint8_t conds, uint8_t *dst) BANKED;   // dst[56]: speaker | @beat steps << 4, 3 x 18 cells (1, 2: beats), portrait",
          "void story_name_get(uint8_t spk, uint8_t *dst) BANKED;  // dst[12]: the plate tile ids, 0-terminated",
          "void story_goal_get(uint8_t ch, uint8_t sh, uint8_t *dst) BANKED;   // dst: goal_t",
          "uint8_t story_pattern_get(uint8_t id, uint8_t *dst) BANKED;   // dst[STORY_PAT_MAX] (WRAM); the length",
          "uint8_t story_step_get(uint8_t ch, uint8_t s) BANKED;",
          "void story_font_load(void) BANKED;",
          "void story_pic_draw(uint8_t pic, uint8_t cgb) BANKED;   // LCD off: tiles, map, attributes, CGB palettes",
          "void story_pic_row(uint8_t pic, uint8_t y, uint8_t x, uint8_t w, uint8_t *dst) BANKED;   // dst[2 w]: tiles, attributes",
          "void story_pic_pals(uint8_t pic, uint16_t *dst) BANKED;    // dst[20]: its 4 palettes (slots 0 5 6 7), then the HUD's",
          "void story_burst_load(uint8_t cgb) BANKED;   // LCD off: the INTRO's pieces' OBJ tiles and (CGB) palette 4",
          "void story_burst_crackle(uint8_t t) BANKED;   // after the explosion: the crackle's two sprites for frame t (each frame, while INTRO A shows)",
          "uint8_t story_burst_step(uint8_t t, uint8_t ev) BANKED;  // frame t of their flight into shadow_OAM (+ up to ev trail map writes); 1 when done",
          "void portrait_tile_copy(uint8_t spk, uint8_t first, uint8_t n, uint8_t *dst) BANKED;   // BG tiles into WRAM",
          "void portrait_get(uint8_t spk, portrait_t *dst) BANKED;",
          "void portrait_tiles_load(uint8_t spk, uint8_t bg_first, uint8_t obj_first) BANKED;",
          "#endif", ""]
    (outdir / "story.h").write_text("\n".join(H))

    # ---- build/story.json (tests) ----
    js = {"scenes": [{"id": s["id"], "title": s["title"], "venue": s["venue"], "pic": s["pic"], "swpage": s["swpage"], "spk": s["spk"],
                      "pages": [{"speaker": SPEAKERS[p], "portrait": ports[q]["name"] if q in ports else None,
                                 "lines": l, "variants": [{"cond": COND_NAME[c], "lines": vl} for c, vl in a],
                                 "pre": pre * BEAT_UNIT, "marks": marks_of(rl)}
                                for (p, l), q, a, (pre, rl) in zip(s["pages"], s["pids"], s["alts"], s["raws"])],
                      "bg_tiles": s["bg_tiles"], "obj_tiles": s["obj_tiles"]} for s in scenes],
          "beat": {"frames": list(BEAT_FRAMES), "unit": BEAT_UNIT, "gap_speaker": GAP_SPEAKER, "gap_page": GAP_PAGE},
          "speakers": SPEAKERS, "font_base": font_base, "font": {n: fid[n] for n in font_names},
          "portrait_base": port_base, "bg_budget": budget, "obj_budget": OBJ_TILES,
          "glyphs": {ch: glyph(ch) for ch in sorted(CHARSET)},
          "chapters": [{"suffix": c[0], "venue": c[1], "type": c[2], "count": c[3], "flags": c[4], "secs": c[5],
                        "line1": c[6], "line2": c[7]} for c in CHAPTERS],
          "shift_names": SHIFT_NAMES, "shifts": shifts,
          "sequence": [{"kind": k, "index": i, "built": k not in NOT_BUILT} for k, i in SEQUENCE],
          "built_slots": {k: sorted(v) for k, v in BUILT_SLOTS.items()},
          "steps": [[{"kind": k, "index": i, "built": not slot_skipped(k, ch[0])} for k, i in SEQUENCE] for ch in CHAPTERS],
          "patterns": [{"name": n, "bars": [b for b, _ in e], "waits": [w for _, w in e]} for n, e in PATTERNS.items()],
          "pat_short": PAT_SHORT, "conditions": CONDITIONS,
          "portraits": {sp["name"]: {"pid": pid, "speaker": SPEAKERS[sp["speaker"]], "variant": sp["variant"],
                                     "art": sp["art"], "w": sp["w"], "h": sp["h"], "x": sp["x"], "y": sp["y"],
                                     "plate_full": int(PLATE_FULL), "tiles": len(sp["tiles"]), "art_tiles": sp["art_tiles"], "plate_name": sp["plate_name"], "plate": sp["plate"], "pals": len(sp["pals"]), "obj": len(sp["obj"]),
                                     "map": sp["map"], "attr": sp["attr"], "palettes": sp["pals"]}
                        for pid, sp in sorted(ports.items())},
          "pictures": [{"id": p["name"], "name": p["name"], "scene": p["scene"], "page": p["page"], "map": p["map"],
                        "attr": p["cattr"], "tiles": len(p["tiles"]), "extra": p.get("n_extra", 0), "base": p["base"], "ids": p["ids"],
                        "pals": p["pals"], "hud_cells": p["attr"].count("H"),
                        "art": f"assets/story/pictures/{p['name']}.txt"} for p in pics],
          "pic_slots": list(PIC_SLOTS), "pic_pool": PIC_POOL,
          "burst": {"file": f"assets/story/pictures/{BURST_FILE}", "oam": BURST_OAM, "obj": BURST_OBJ, "pal": BURST_PAL,
                    "end": burst["end"], "crackle_t": burst["crackle_t"], "crackle_obj": CRACKLE_OBJ, "crackle_xy": list(CRACKLE_XY), "star_cells": [BURST_CELL0[0], BURST_CELL0[1], BURST_W, BURST_H], "star0": burst["star0"], "rows": burst["rows"], "timeline": [list(q) for q in BURST_TIMELINE], "worst_line": burst["worst"], "worst_frame": burst["worst_t"], "leave": burst["leave"],
                    "key": bkey, "frame": list(BURST_FRAME), "acc": BURST_ACC, "scratch_cursor": SCRATCH_CURSOR,
                    "per_frame": TRAIL_PER_FRAME, "bright": TRAIL_BRIGHT_FRAMES, "faint": TRAIL_FAINT_FRAMES,
                    "tiles": len(burst["tiles"]) * 2, "pos": burst["pos"], "dots": burst["dots"], "extra_tiles": burst["extra"],
                    "pal_bg": burst["pal"], "events": [list(e) for e in burst["events"]],
                    "entries": [{"piece": i, "dx": dx, "tile": BURST_OBJ + 2 * k, "flip": fl} for (i, dx, k, fl) in burst["entries"]],
                    "pieces": [{"name": q["name"], "x": q["x"], "y": q["y"], "start": q["start"], "dir": q["dir"],
                                "speed": q["speed"], "rows": q["rows"]} for q in bpieces]},
          "text_bytes": len(text), "chars": sum(len(l) for s in scenes for _, ls in s["pages"] for l in ls),
          "pages": sum(len(s["pages"]) for s in scenes)}
    (outdir / "story.json").write_text(json.dumps(js, indent=1))

    # ---- previews ----
    im = Image.new("RGB", (len(font_names) * 9, 8), (255, 0, 255))
    for i, (_, rows) in enumerate(font_blocks):
        for y in range(8):
            for x in range(8):
                im.putpixel((i * 9 + x, y), GREY[IDX[rows[y][x]]])
    im.resize((im.width * 8, im.height * 8), Image.NEAREST).save(prev / "story_font_x8.png")
    for p in pics:                               # every picture as the CGB and the DMG show it, x3
        rgb = lambda hx: tuple(int(hx[i:i + 2], 16) & 0xF8 for i in (1, 3, 5))
        for model in ("cgb", "dmg"):
            pim = Image.new("RGB", (PIC_W, PIC_H))
            for y in range(PIC_H):
                for x in range(PIC_W):
                    pim.putpixel((x, y), rgb(p["key"][p["pix"][y][x]]["hex"]) if model == "cgb" else GREY[p["px"][y][x]])
            pim.resize((PIC_W * 3, PIC_H * 3), Image.NEAREST).save(prev / f"story_picture_{p['name']}_{model}_x3.png")
    for si, sp in ports.items():
        w, h = sp["w"] * 8, sp["h"] * 8
        pim = Image.new("RGB", (w + 16, h + 16), (40, 30, 20))
        for y in range(h):
            for x in range(w):
                t = (y // 8) * sp["w"] + x // 8
                pc = [tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in sp["pals"][sp["attr"][t]]]
                pim.putpixel((x + 8, y + 8), pc[sp["px"][y][x]])
        if sp["opx"] is not None:
            oc = [tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in sp["obj_pals"][0]]
            for y, r in enumerate(sp["opx"]):
                for x, v in enumerate(r):
                    X, Y = x + 8, y + 8
                    if v and 0 <= X < pim.width and 0 <= Y < pim.height:
                        pim.putpixel((X, Y), oc[v])
        pim.resize((pim.width * 8, pim.height * 8), Image.NEAREST).save(prev / f"story_portrait_{sp['name'].lower().replace(' ', '_')}_x8.png")
    print(f"gen_story: {len(scenes)} scenes, {js['pages']} pages, {js['chars']} characters, script {len(text)} B "
          f"(+ scene table {len(hdr) + 2 * len(scene_ofs)} B, goals {len(goals)} B); portraits "
          f"{len(ports)} portraits, {sum(len(p['tiles']) for p in ports.values())} tiles; BG budget {budget} tiles from id "
          f"{port_base}, the busiest scene {max(s['bg_tiles'] for s in scenes)} "
          f"({', '.join(s['id'] for s in scenes if s['bg_tiles'] == max(t['bg_tiles'] for t in scenes))})")


if __name__ == "__main__":
    try:
        main()
    except StoryError as e:
        sys.exit(f"gen_story: {e}")
