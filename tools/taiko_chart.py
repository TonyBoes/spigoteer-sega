#!/usr/bin/env python3
"""Taiko Pour's chart (src/tk.c, docs/minigames_bosses.md 4.7): a text grid aligned to the teahouse tune's rows.

"Sakura Sakura" plays at 12 frames a row (an eighth note; tools/songs.py: song("sakura", 12 ...), 8 rows a bar, 96 frames
a bar, 14 bars = 1344 frames, then it loops). The game clock is the music's frame counter (music_frames, 0 at the tune's
first row), so a note's hit time T is a count of music frames: T = FIRST + bar * 96 + row * 12.

One bar is two strings of 8 characters (one per eighth row): lane A (the drum's face, "don": the top lane) and lane B (the
rim, "ka": the bottom lane); 'A' / 'B' = a note, '.' = none. The first bar of the chart (bar 1) is the tune's bar FIRST_BAR + 1,
so the 3 bars before it are the count-in (the framework's banner and READY / GO, then 1 2 3 4 on the beats).

Rounds of density (the spec): bars 1-8 quarter notes, A only; 9-16 both lanes; 17-24 eighth-note pairs. A lane's notes are
never closer than one row (12 frames, 18 px at 1.5 px a frame): only the pairs of the last round are that close; every
other note is at least 2 rows (24 frames, 36 px) from the next in its lane.
"""
ROW = 12                      # frames a row
BAR = 8 * ROW                 # frames a bar
FIRST_BAR = 3                 # bars of the tune before the chart's first bar
FIRST = FIRST_BAR * BAR       # 288: the first note's hit time (the framework's intro + count end at about frame 150)
TUNE_FRAMES = 14 * BAR        # the loop

# (lane A, lane B) per bar
GRID = [
    # round 1: quarter notes, A only (the don)
    *[("A.A.A.A.", "........")] * 8,
    # round 2: both lanes, a note on the beat
    ("A...A...", "..B...B."), ("A.A.....", "....B.B."),
    ("A...A...", "..B...B."), ("A.A.....", "....B.B."),
    ("A...A...", "..B...B."), ("A.A.....", "....B.B."),
    ("A...A...", "..B...B."), ("A.A.A...", "......B."),
    # round 3: eighth-note pairs
    ("AA..AA..", "..B...B."), ("A.AA....", "....B.BB"),
    ("AA.A..A.", "..B..B.."), ("A...AA..", ".BB...B."),
    ("AA..AA..", "..B...B."), ("A.AA....", "....B.BB"),
    ("AA.A..A.", "..B..B.."), ("A.A.A.AA", ".....B.."),
]


# NORMAL (owner 2026-10-15: the chart above is "too many notes too fast" and becomes HARD): the same three rounds with a thinned
# density rule, no eighth notes and no pairs: every note is on a quarter-note row (even rows) and no two notes of either lane
# are closer than 24 frames (a quarter note). Round 1 two notes a bar then three, round 2 three a bar, round 3 four a bar.
GRID_NORMAL = [
    *[("A...A...", "........")] * 4, *[("A.A.A...", "........")] * 4,
    ("A.......", "..B...B."), ("A...A...", "......B."), ("A.......", "..B.B..."), ("A...A...", "..B....."),
    ("A.......", "..B...B."), ("A...A...", "......B."), ("A.......", "..B.B..."), ("A.A.....", "....B..."),
    ("A...A...", "..B...B."), ("A.A.....", "....B.B."), ("A...A.A.", "..B....."), ("A.......", "..B.B.B."),
    ("A...A...", "..B...B."), ("A.A.....", "....B.B."), ("A...A.A.", "..B....."), ("A.A.A...", "......B."),
]

# EASY (the difficulty table, 2026-10-17): a note every half note at most in a lane: round 1 the don on beats 1 and 3, round 2 one note a half bar
# alternating the lanes, round 3 three a bar (a note of the other lane may sit a quarter away, never one of the same lane): 56 notes.
GRID_EASY = [
    *[("A...A...", "........")] * 8,
    ("A.......", "....B..."), ("..A.....", "......B."), ("A.......", "....B..."), ("..A.....", "......B."),
    ("A.......", "....B..."), ("..A.....", "......B."), ("A.......", "....B..."), ("..A.....", "......B."),
    ("A.......", "..B...B."), ("A...A...", "......B."), ("A.......", "..B...B."), ("A...A...", "......B."),
    ("A.......", "..B...B."), ("A...A...", "......B."), ("A.......", "..B...B."), ("A...A...", "..B...B."),
]

GRIDS = {"normal": GRID_NORMAL, "hard": GRID, "easy": GRID_EASY}


def build(level="normal"):
    """-> [(T, lane)] sorted by time (lane 0 = A, 1 = B)."""
    notes = []
    for bar, (a, b) in enumerate(GRIDS[level]):
        for lane, rows in enumerate((a, b)):
            assert len(rows) == 8 and set(rows) <= set(".AB"), (bar, rows)
            for r, ch in enumerate(rows):
                if ch != ".":
                    assert ch == "AB"[lane], (bar, lane, rows)
                    notes.append((FIRST + bar * BAR + r * ROW, lane))
    notes.sort()
    assert len({t for t, _ in notes}) == len(notes), "two notes on one row: one key press each, never both at once"
    if level == "normal":
        assert all(b - a >= 2 * ROW for (a, _), (b, _) in zip(notes, notes[1:])), "NORMAL: no notes closer than a quarter"
    if level == "easy":
        for lane in (0, 1):
            ts = [t for t, ln in notes if ln == lane]
            assert all(b - a >= 4 * ROW for a, b in zip(ts, ts[1:])), "EASY: no two notes of a lane closer than a half note"
    return notes


def stats(notes):
    """The numbers the engine and the tests rely on: per lane the closest pair (frames) and the most notes a lane holds on
    screen at once (notes between x 6 and x 164 live: a window of 105 frames)."""
    out = {"n": len(notes), "last": notes[-1][0]}
    for lane in (0, 1):
        ts = [t for t, ln in notes if ln == lane]
        out[f"gap{lane}"] = min(b - a for a, b in zip(ts, ts[1:]))
        out[f"live{lane}"] = max(sum(1 for u in ts if t <= u < t + 105) for t in ts)
    return out


if __name__ == "__main__":
    for lv in GRIDS:
        n = build(lv)
        print(lv, stats(n))
