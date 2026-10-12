#!/usr/bin/env python3
"""docs/story.md (the owner-approved script) + assets/story/portraits.json + assets/tiles/story.txt -> story mode data.

  build/story.h            scene / speaker / chapter ids, the cut-scene tile budget, the BANKED accessors
  build/story_data.c       the script (pages, scene table, names), chapter goals, the story font tiles, the picture slots
  build/story_portraits.c  the portraits (BG tiles, map, attributes, palettes, optional OBJ overlay)
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
    ("BISTRO", 3, G_SERVE, 20, 0, 120, "SERVE 20 CHEFS", "BEFORE THE RUSH", "serve 20 before the timer"),
    ("IGLOO", 4, G_SERVE, 20, 0, 120, "SERVE 20 COCOAS", "BEFORE THEY COOL", "serve 20 before the timer"),
    ("ROBOT", 5, G_CATCH, 25, 0, 0, "RECYCLE 25", "EMPTY BATTERIES", "catch 25 empties"),
    ("BIKER", 6, G_SERVE, 22, 0, 0, "SERVE 22 PUNKS", "NO CRYING OVER MILK", "serve 22"),
    ("TEAHOUSE", 7, G_CLEAR, 0, F_NO_BREAK, 0, "SERVE EVERY GUEST", "BROKEN CUP COSTS TWO",
     "clear the venue, a broken glass costs 2 lives"),
    ("ZOO", 8, G_SERVE, 25, 0, 0, "SERVE 25 ANIMALS", "", "serve 25"),
    ("SPACE", 9, G_SERVE, 30, 0, 0, "SERVE 30 GLOWING", "BEAKERS", "serve 30"),
]
PICTURE_SCENES = ["INTRO", "FINALE", "CREDITS"]
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
# Big Tex (the saloon), the Sasquatch (the lumber lodge) and the Food Critic (the bistro) so far, and the mini-game
# framework (src/mg.c) Quick Draw (src/qd.c), the saloon's mini-game; the other venues' slots are still skipped.
BUILT_SLOTS = {"BOSS": {"SALOON", "LUMBER", "BISTRO"}, "MINI": {"SALOON"}}
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
     (G_SERVE, 22, 0, 120, 0, "SERVE 22 CHEFS", "TABLES FOR TWO", "serve 22 in 120 s", "pairs", 115, 85)),
    ((G_SERVE, 10, 0, 75, 0, "SERVE 10 COCOAS", "BEFORE THEY COOL", "serve 10 in 75 s"),
     (G_SERVE, 22, 0, 120, 0, "SERVE 22 COCOAS", "BEFORE THEY FREEZE", "serve 22 in 120 s", "zigzag", 115, 85)),
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
            if not 0 <= sh["secs"] <= 255:
                fail(f"{where}: timer 0-255 s")
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
        pages, alts = [], []
        for blk in re.split(r"\n\s*\n", code.group(1).strip("\n")):
            lines = [l.rstrip() for l in blk.split("\n")]
            spk, body_lines = lines[0], lines[1:]
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
            for l in body_lines:
                if len(l) > LINE_W:
                    fail(f"{where}: {l!r} is {len(l)} characters (max {LINE_W})")
                bad = set(l) - CHARSET
                if bad:
                    fail(f"{where}: {l!r} has characters outside the font: {''.join(sorted(bad))!r}")
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
                continue
            pages.append((SPEAKERS.index(spk), body_lines))
            alts.append([])
        if len(title) > 20 or set(title) - CHARSET:
            fail(f"{sid}: title {title!r} (max 20, the story charset)")
        scenes.append({"id": sid, "title": title, "pages": pages, "alts": alts})
    want = ["INTRO"] + [f"{k}_{c[0]}" for c in CHAPTERS for k in ("PRE", "POST")] + ["FINALE", "CREDITS"]
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


# ---- output -----------------------------------------------------------------------------------------------------
def carr(name, vals, typ="uint8_t"):
    vals = list(vals)
    body = []
    for i in range(0, len(vals), 20):
        body.append("    " + ", ".join(str(v) for v in vals[i:i + 20]) + ",")
    return f"static const {typ} {name}[{max(1, len(vals))}] = {{\n" + ("\n".join(body) if vals else "    0") + "\n};"


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
        if s["id"] in PICTURE_SCENES:
            s["pic"] = PICTURE_SCENES.index(s["id"])
        else:
            suffix = s["id"].split("_", 1)[1]
            s["venue"] = next(c[1] for c in CHAPTERS if c[0] == suffix)

    # picture placeholders: the slot for INTRO / FINALE / CREDITS (20 x PIC_ROWS map + attributes; own tiles none yet)
    pics = []
    for sid in PICTURE_SCENES:
        title = next(s["title"] for s in scenes if s["id"] == sid)
        m = [[ids["TILE_HUD_BLANK"]] * 20 for _ in range(PIC_ROWS)]
        m[1][1], m[1][18], m[11][1], m[11][18] = fid["frame_tl"], fid["frame_tr"], fid["frame_bl"], fid["frame_br"]
        for x in range(2, 18):
            m[1][x], m[11][x] = fid["frame_t"], fid["frame_b"]
        for y in range(2, 11):
            m[y][1], m[y][18] = fid["frame_l"], fid["frame_r"]
        m[3][9] = m[3][10] = fid["spigot_icon"]

        def put(y, s):
            x0 = (20 - len(s)) // 2
            for i, ch in enumerate(s):
                m[y][x0 + i] = glyph(ch)
        put(5, title)
        put(7, sid)
        put(9, "PICTURE SLOT")
        pics.append({"id": sid, "tiles": [], "map": [v for r in m for v in r], "attr": [1] * (20 * PIC_ROWS),
                     "pals": []})

    # ---- build/story_data.c ----
    text = []
    scene_ofs = []
    for s in scenes:
        scene_ofs.append(len(text))
        for pid, (_, lines), alts in zip(s["pids"], s["pages"], s["alts"]):
            if pid >= 0x80:
                fail(f"portrait id {pid}: bit 7 of the page byte marks a variant")
            # a page's variants first (portrait id | 0x80, the condition id, the lines), then the page itself
            for cond, vl in alts:
                text += [pid | 0x80, cond]
                for i in range(PAGE_LINES):
                    l = vl[i] if i < len(vl) else ""
                    text.append(len(l))
                    text += [ord(ch) for ch in l]
            text.append(pid)
            for i in range(PAGE_LINES):
                l = lines[i] if i < len(lines) else ""
                text.append(len(l))
                text += [ord(ch) for ch in l]
    names = []
    for n in SPEAKERS:
        names += [ord(ch) for ch in n.ljust(12, "\0")[:12]]
    npid = max(ports) + 1
    pid_spk = [ports[i]["speaker"] if i in ports else NARRATOR for i in range(npid)]
    hdr = []
    for s in scenes:
        spk = s["spk"] + [255] * (MAX_SPK - len(s["spk"]))
        hdr += [s["venue"], s["pic"], len(s["pages"]), len(s["spk"])] + spk + [0]
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
         "#pragma bank 255", "#include <gb/gb.h>", "#include <gb/cgb.h>", "#include <stdint.h>", '#include "story.h"', "",
         "// the script: per page the portrait id (the speaker's own, or a variant of his), then 3 lines of (length,",
         "// characters); before a page its text variants: the portrait id | 0x80, the condition id, 3 lines",
         carr("st_text", text), carr("st_scene_ofs", scene_ofs, "uint16_t"),
         "// portrait id -> its speaker (the speaker's own id: his main portrait; NARRATOR: none)",
         carr("st_pid_spk", pid_spk),
         "// per scene: venue (255: a picture), picture (255: none), pages, portraits, their ids x3, 0, title",
         carr("st_scene_hdr", hdr), carr("st_names", names),
         "// per chapter, per shift (opening, happy hour, last call): goal type, count, flags, timer seconds, twist bits",
         "// (TWIST_*), arrival pattern, walk %, spawn %, quota (0: the row's), the mosh pit's x limit (0: none), the two",
         "// banner lines", carr("st_goals", goals),
         "// arrival patterns: entries (bar | wait code << 4) and per pattern its offset | length << 8",
         carr("st_pats", pats or [0]), carr("st_pat_ofs", pat_ofs, "uint16_t"),
         "// per chapter the sequence of steps: kind << 4 | index, STEP_SKIP: not built yet (the engine passes over it)",
         carr("st_seq", seq), carr("st_font", font)]
    for i, p in enumerate(pics):
        d += [carr(f"st_pic{i}_map", p["map"]), carr(f"st_pic{i}_attr", p["attr"])]
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
          "        q++; for (k = 0; k < 3; k++) q += 1 + *q;",
          "    }",
          "    k = *q++;",
          "    if (k & 0x80) { k &= 0x7F; q++; }",
          "    dst[55] = k; *dst++ = st_pid_spk[k];",
          "    for (k = 0; k < 3; k++) {",
          "        n = *q++;",
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
          "}", "",
          "// the picture slot (LCD off): rows 0..STORY_PIC_ROWS-1; its own tiles (none in the placeholders) at ids 0..",
          "void story_pic_draw(uint8_t pic, uint8_t cgb) BANKED {",
          "    const uint8_t *m, *a;"]
    for i in range(len(pics)):
        d.append(f"    {'if' if i == 0 else 'else if'} (pic == {i}) {{ m = st_pic{i}_map; a = st_pic{i}_attr; }}")
    d += ["    else return;",
          f"    set_bkg_tiles(0, 0, 20, {PIC_ROWS}, m);",
          "    if (cgb) {",
          "        VBK_REG = VBK_BANK_1;",
          f"        set_bkg_tiles(0, 0, 20, {PIC_ROWS}, a);",
          "        VBK_REG = VBK_BANK_0;",
          "    }",
          "}", ""]
    (outdir / "story_data.c").write_text("\n".join(d))

    # ---- build/story_portraits.c ----
    P = ["// generated by tools/gen_story.py from assets/story/portraits.json -- do not edit",
         "#pragma bank 255", "#include <gb/gb.h>", "#include <stdint.h>", '#include "story.h"', ""]
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
          "    for (i = 0; i < 12; i++) dst->pal[i] = p[i];",
          "    for (i = 0; i < 16; i++) dst->opal[i] = o[i];",
          f"    for (i = 0; i < {MAX_OBJ * 4}; i++) dst->obj[i] = e[i];",
          "}", "",
          "// LCD off: its BG tiles at bg_first.., its overlay tiles at OBJ obj_first..",
          "void portrait_tiles_load(uint8_t spk, uint8_t bg_first, uint8_t obj_first) BANKED {",
          "    const uint8_t *t, *ot;",
          "    switch (spk) {"] + selt + [
          "    default: return;",
          "    }",
          "    set_bkg_data(bg_first, pt_n[spk], t);",
          "    if (pt_on[spk]) set_sprite_data(obj_first, pt_on[spk], ot);",
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
          f"#define SPK_NARRATOR {NARRATOR}", f"#define STORY_SPEAKERS {len(SPEAKERS)}",
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
          f"#define STORY_MAX_SPK {MAX_SPK}", f"#define STORY_PIC_ROWS {PIC_ROWS}", "",
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
          "    uint8_t venue, pic, pages, nspk, spk[3], pad;",
          "    char title[21];",
          "} scene_hdr_t;",
          "typedef struct {",
          "    uint8_t type, count, flags, secs, twist, pattern, walk, spawn, quota, pad;   // pad: the mosh pit's limit",
          "    char line1[21], line2[21];",
          "} goal_t;                         // one shift's goal",
          "void story_scene_get(uint8_t s, uint8_t *dst) BANKED;   // dst: scene_hdr_t",
          "void story_page_get(uint8_t s, uint8_t p, uint8_t conds, uint8_t *dst) BANKED;   // dst[56]: speaker, 3 x 18, portrait",
          "void story_name_get(uint8_t spk, uint8_t *dst) BANKED;  // dst[12], 0-terminated",
          "void story_goal_get(uint8_t ch, uint8_t sh, uint8_t *dst) BANKED;   // dst: goal_t",
          "uint8_t story_pattern_get(uint8_t id, uint8_t *dst) BANKED;   // dst[STORY_PAT_MAX] (WRAM); the length",
          "uint8_t story_step_get(uint8_t ch, uint8_t s) BANKED;",
          "void story_font_load(void) BANKED;",
          "void story_pic_draw(uint8_t pic, uint8_t cgb) BANKED;",
          "void portrait_get(uint8_t spk, portrait_t *dst) BANKED;",
          "void portrait_tiles_load(uint8_t spk, uint8_t bg_first, uint8_t obj_first) BANKED;",
          "#endif", ""]
    (outdir / "story.h").write_text("\n".join(H))

    # ---- build/story.json (tests) ----
    js = {"scenes": [{"id": s["id"], "title": s["title"], "venue": s["venue"], "pic": s["pic"], "spk": s["spk"],
                      "pages": [{"speaker": SPEAKERS[p], "portrait": ports[q]["name"] if q in ports else None,
                                 "lines": l, "variants": [{"cond": COND_NAME[c], "lines": vl} for c, vl in a]}
                                for (p, l), q, a in zip(s["pages"], s["pids"], s["alts"])],
                      "bg_tiles": s["bg_tiles"], "obj_tiles": s["obj_tiles"]} for s in scenes],
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
                                     "tiles": len(sp["tiles"]), "pals": len(sp["pals"]), "obj": len(sp["obj"]),
                                     "map": sp["map"], "attr": sp["attr"], "palettes": sp["pals"]}
                        for pid, sp in sorted(ports.items())},
          "pictures": [{"id": p["id"], "map": p["map"]} for p in pics],
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
