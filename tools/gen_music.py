#!/usr/bin/env python3
"""Tune sources -> build/music_data.c, build/music_pat10.c (hUGEDriver song data, C).

No tracker GUI is involved: each tune is a few lines of text per channel.  A token is NOTE:ROWS
(rows are 16th/8th notes depending on the tune's tempo), 'r:ROWS' is a rest, a trailing '!' makes
the note staccato (note cut), and '/N' picks instrument N for that note.  hUGEDriver's channel 1 is never used
(its patterns are empty): the buffered tunes' channel-1 harmony (songs.harmony, music step 5) is a compact event list
(harm_<tune>, bank HARM_BANK) that src/music.c plays itself and gives up to the sound effects; channel 4 is
percussion (b kick, n snare, t closed hat, o open hat, m tom, x rim: KIT).

Two kinds of tune:
 * jingles (level clear, game over, bonus): small, their patterns sit in bank 2 beside the driver.
 * "buffered" tunes (title, show, ten venue tunes, tools/songs.py): hUGEDriver reads patterns through
   plain pointers into whatever ROM bank is mapped, and bank 2 is the only place the driver runs
   from, so these songs cannot live elsewhere in ROM as they are.  Their patterns are packed into
   blobs in ROM bank 10 (BLOB_BANKS; bank 3 until the longer Entertainer outgrew it); at music_play() src/music.c copies the song's blob into a WRAM buffer
   (A for the title/venue tune, B for the show tune), and the order tables that stay in bank 2 point
   into that buffer.  Bank 2 then only holds the driver, the order tables and the instruments.

Usage: gen_music.py OUTDIR
"""
import math
import re
import sys
from pathlib import Path

SEMI = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
REST = 90          # ___ in hUGEDriver.h

# ---- instruments (indexes are 1-based in the pattern data) -------------------------------------
DUTY = [  # sweep, len_duty (NR11), envelope (NR12), subpattern, highmask
    (0x08, 0x80, 0x83),   # 1 lead: 50% pulse, volume 8, slow decay
    (0x08, 0x40, 0x73),   # 2 soft lead: 25% pulse, volume 7, slow decay
    (0x08, 0x80, 0xA1),   # 3 plink: 50% pulse, volume 10, fast decay (short jingle notes)
    (0x08, 0x00, 0xC1),   # 4 thin: 12.5% pulse, volume 12, fast decay (quick bonus-round notes)
    (0x08, 0x80, 0xC7),   # 5 ring: 50% pulse, volume 12, slowest decay (12 x 7/64 s = 1.3 s): the credits tune's final chord
]
WAVE = []   # length, volume (NR32: 0x20 = 100%, 0x40 = 50%), waveform index, subpattern, highmask
NOISE = []  # envelope (NR42), subpattern, highmask+length: the one kit (KIT below)
# channel-1 harmony instruments (songs.harmony inst names): NR11 (duty), NR12 (envelope).  Quieter than the melody
# (song lead 0x85, legato lead 0x60) and the effects (channel 1 volume 8-12): volume 5, a thinner duty.
HARM_INST = {
    "harm": (0x40, 0x57),     # 25% pulse, volume 5, slow decay (0.55 s to silence): thirds and sixths under a melody
    "pad": (0x00, 0x50),      # 12.5% pulse, volume 5 held: sustained chord tones (waltzes, the sung tunes)
    "stab": (0x40, 0x52),     # 25% pulse, volume 5, quick decay (0.16 s): off-beat stabs
    "harm50": (0x80, 0x57),   # "harm" at 50% duty (the Entertainer's thirds: rounder, less nasal)
    "pluck": (0x00, 0x55),    # 12.5% pulse, volume 5, medium decay (0.39 s): plucked, koto-like
    "voice": (0x80, 0x67),    # 50% pulse, volume 6, slow decay (0.66 s): the show tune's counter-melody
    "vstab": (0x40, 0x62),    # 25% pulse, volume 6, quick decay (0.19 s): a stab chord's lower note (unused: see ARPEGGIO CHORD STABS)
    "ring50": (0x80, 0x97),   # 50% pulse, volume 9, slowest decay (1.0 s): the credits tune's final chord rings
}
HARM_REST = 0x7F
HARM_BANK = 24              # src/music.h HARM_BANK (checked in main): the venue and show tunes' harmony shares bank 24 with the jingles' patterns (bank 10 was full)
NOISE_NOTE = {}     # drum letter -> (note number, noise instrument), filled from KIT
DRUM_ID = {}        # groove byte -> row of the kit (1-based; 0 = no hit)

# THE KIT: one definition (owner-approved 2026-10-17, tools/proarr.py batch 0).  letter: (name, NR42 envelope, 7-bit LFSR, length (NR41
# field, None = free-running), NR43 clock steps without the 7-bit flag: the value written with the hit, then one a frame).  Every value is
# one the driver can reach from a note number (get_note_poly: no -36), so the pattern route (hUGEDriver's noise instruments and their
# tables, kit_instruments) and the groove route (src/music.c's rows, drum_kit) write the same bytes.
KIT = {   # the "-3" research kit with tom R3 and rim R2 (owner 2026-11-12; docs/proarr/batch5/DRUMS_RESEARCH.md on the audition branch)
    "b": ("kick",       0x71, 0, None, [0x37, 0x57, 0x77]),   # a click: 4.7 kHz -> 1.2 kHz -> 292 Hz over three frames; its body is the wave channel (KICK_BODY)
    "n": ("snare",      0x91, 0, None, [0x35, 0x57, 0x16]),   # 15-bit: body 6.6 kHz, a low frame 1.2 kHz, a bright tail 22 kHz
    "t": ("hat_closed", 0x61, 0, 52,   [0x06]),               # 15-bit at 44 kHz, cut by the length counter (NR41 0x34) at 47 ms
    "o": ("hat_open",   0x53, 0, None, [0x15]),               # 15-bit at 26 kHz, a long fade
    "m": ("tom",        0x82, 0, 18,   [0x44, 0x55, 0x56]),   # 15-bit, 4.1 -> 1.6 -> 1.4 kHz, cut at 0.18 s (NR41 0x12)
    "x": ("rim",        0x71, 1, 55,   [0x14]),               # the one 7-bit sound (NR43 0x1C with the flag): 33 kHz, cut at 35 ms (NR41 0x37)
}
KIT_ORDER = "bntomx"
GROOVE_STEPS = 3            # NR43 writes per hit in the groove player's rows (hit, +1 frame, +2 frames)
DRUM_ID.update({letter: i + 1 for i, letter in enumerate(KIT_ORDER)})


def driver_poly(n):
    """NR43 the driver makes of noise note n (hUGEDriver.asm get_note_poly: no -36)."""
    a = (~((n + 192) & 255)) & 255
    return a if a < 7 else ((((a >> 2) - 1) << 4) | ((a & 3) + 4)) & 255


def note_for(nr43):
    for n in range(64):
        if driver_poly(n) == nr43:
            return n
    raise ValueError(f"NR43 0x{nr43:02X} is not a note's poly")


def kit_instruments():
    """KIT -> the driver's noise instruments (appended to NOISE, 1-based in KIT_ORDER) and tables; fills NOISE_NOTE.  The note is the
    LAST step's; the table walks the earlier steps as offsets (row 0 runs on the hit's own tick); a one-step drum has no table."""
    for letter in KIT_ORDER:
        name, env, bit7, length, steps = KIT[letter]
        base = note_for(steps[-1])
        hm = (0x80 if bit7 else 0) | ((0x40 | length) if length is not None else 0)
        ins = (env, hm)
        if len(steps) > 1:
            table(f"sp_{name}", [(note_for(v) - base, 0) for v in steps])
            ins = (env, hm, f"sp_{name}")
        NOISE.append(ins)
        NOISE_NOTE[letter] = (base, len(NOISE))


def drum_kit():
    """The groove player's rows (src/music.c): NR41, NR42, NR43 (hit), NR44, NR43 a frame later, NR43 two frames later."""
    out = []
    for letter in KIT_ORDER:
        name, env, bit7, length, steps = KIT[letter]
        flag = 0x08 if bit7 else 0
        s = [v | flag for v in steps] + [steps[-1] | flag] * GROOVE_STEPS
        out.append((length or 0, env, s[0], 0x80 | (0x40 if length is not None else 0), s[1], s[2]))
    return out


BASS_AMP = 0.5      # the bass wave runs at 100% output (NR32 0x20) but its samples span this fraction of the full 4-bit range


def scaled_wave(w, amp):
    """Pack 32 4-bit samples (16 bytes, high nibble first) scaled around the centre 7.5; the DAC stays centred."""
    nib = [x for b in w for x in (b >> 4, b & 15)]
    nib = [int(round(7.5 + (x - 7.5) * amp)) for x in nib]
    return [(nib[i] << 4) | nib[i + 1] for i in range(0, 32, 2)]


WAVES = []


# ---- the show tune's instruments (galop, "v2" arrangement) and the tables (hUGEDriver subpatterns) they use ----------
# A subpattern is a per-tick script attached to an instrument, 3 bytes a tick: (note offset or None, jump, effect).  Effects in a
# table run on every row they stand in.  A table is as long as its hold row (the last, which jumps to itself).  Only the show tune
# uses these; every other tune's instruments are the plain ones above.
NO_NOTE = 90
SUBPAT = {}


def table(name, rows):
    """rows: [(note offset from the channel's note or None, effect)]; the last row holds (jumps to itself)."""
    out = []
    for i, (off, eff) in enumerate(rows):
        n = NO_NOTE if off is None else 36 + off
        assert 0 <= n <= 71 or n == NO_NOTE
        out.append((n, len(rows) if i == len(rows) - 1 else 0, eff))
    SUBPAT[name] = out
    return name


def pro_bass_wave():
    """32 samples over the full 4-bit range: a sine with a touch of 2nd and 3rd harmonic (warm, with enough edge for a small
    speaker); the triangle above runs at half amplitude."""
    v = []
    for i in range(32):
        x = 2 * math.pi * (i + 0.5) / 32
        y = 0.72 * math.sin(x) + 0.2 * math.sin(2 * x) + 0.1 * math.sin(3 * x)
        v.append(max(0, min(15, int(round(7.5 + 7.5 * y)))))
    return [(v[i] << 4) | v[i + 1] for i in range(0, 32, 2)]

# lead: 50 % duty (effect 0x980 = duty 50 %) for two ticks, 25 % after; from tick 8 a 7.5 Hz triangle vibrato of +-2 period units
# (about 15 cents at D5) made of 1-unit pitch slides, rows 8-15 looping (a delayed vibrato: eighths stay clean).
table("sp_lead", [(None, 0x980), (None, 0x980), (None, 0x940)] + [(None, 0)] * 5
      + [(None, 0x101), (None, 0x101), (None, 0x201), (None, 0x201), (None, 0x201), (None, 0x201), (None, 0x101), (None, 0x101)])
SUBPAT["sp_lead"][-1] = (NO_NOTE, 9, 0x101)      # the last row jumps back to row 8
# bass: the wave channel has no envelope; the table steps NR32 (0xC0x): 100 % for 7 ticks, 50 % for 5, 25 % for 3, then off.
table("sp_bass", [(None, 0)] * 7 + [(None, 0xC05)] + [(None, 0)] * 4 + [(None, 0xC02)] + [(None, 0)] * 2 + [(None, 0xC00)])
DUTY.append((0x08, 0x80, 0xA5, "sp_lead"))       # 6 brass lead: volume 10, decay 5 (0.78 s), the duty attack + delayed vibrato table
LEAD_PRO = len(DUTY)
DUTY.append((0x08, 0x80, 0x80, "sp_lead"))       # 7 the sung tunes' lead: the same table, held volume 8 (no decay)
LEAD_LEGATO = len(DUTY)
WAVES.append(pro_bass_wave())
WAVE.append((0, 0x20, 0, "sp_bass"))             # 1 pro bass: the full-amplitude wave at 100 %, the plucked decay table
BASS_PRO = len(WAVE)
WAVE.append((0, 0x20, 0))                        # 2 held bass: the same wave, no table (the credits tune's last chord fades by hand)
BASS_HELD = len(WAVE)
kit_instruments()
# THE KICK BODY: a bass note that starts together with a kick plays two octaves up on this instrument and its table steps down to the
# note's own pitch over three frames (-12, -19, -24 semitones: a pitched thump under the noise click), then fades like the plucked bass.
# The wave channel starts at 50 % (NR32 0x40) and the second row puts it back to 100 % (Cxx 0xC0A), so the first drop frame is half level.
# The note in the pattern is the TOP of the drop, so the table's first row (the hit's own call, the dearest) computes no pitch.
table("sp_kickbass", [(None, 0), (-12, 0xC0A), (-19, 0), (-24, 0)] + [(None, 0)] * 3 + [(None, 0xC05)] + [(None, 0)] * 4
      + [(None, 0xC02)] + [(None, 0)] * 2 + [(None, 0xC00)])
WAVE.append((0, 0x40, 0, "sp_kickbass"))         # 3 kick body
KICK_BODY = len(WAVE)
# ARPEGGIO CHORD STABS (the first galop audition's technique, kept for other songs; no tune uses it now).  A stab row carries a
# hardware arpeggio, effect 0xy = the note, +x and +y semitones cycling every frame (0x059 = note, +5, +9).  Give the song
# songs.song(..., fx_map={row: [(2, 0x059)]}): build() writes it into that row's (free) effect column, so the note's staccato cut
# moves to a later row.  Play it on a short 25 % pulse WITHOUT a table (a table would own the pitch): DUTY.append((0x08, 0x40, 0xA3))
# gives the "stab" melody instrument, and HARM_INST["vstab"] is the matching channel-1 voice for the lower note.


def note_no(name):
    m = re.fullmatch(r"([A-G])([#b]?)(\d)", name)
    if not m:
        raise ValueError(name)
    semi = SEMI[m.group(1)] + {"#": 1, "b": -1, "": 0}[m.group(2)]
    n = (int(m.group(3)) - 2) * 12 + semi     # hUGE's index 0 ("C_3") is 65.4 Hz, i.e. a real C2: names here are real pitches
    assert 0 <= n < 72, name
    return n


SLOT_BYTES = 192          # one pattern: 64 rows x 3 bytes
BREAK_TO_ROW0 = 0xD01     # Dxx pattern break to the next order's row 0 (see build())


def merge_ties(text):
    """'~:n' holds the previous note n more rows: fold it into that note's length."""
    toks = []
    for tok in text.split():
        if tok.startswith("R:"):
            tok = "r" + tok[1:]            # the specs write rests as R
        if tok.startswith("~:"):
            m = re.fullmatch(r"([^:]+):(\d+)(.*)", toks[-1])
            assert m and m.group(1) != "r", f"tie after {toks[-1]}"
            toks[-1] = f"{m.group(1)}:{int(m.group(2)) + int(tok[2:])}{m.group(3)}"
        else:
            toks.append(tok)
    return " ".join(toks)


def row_starts(tempo, swing, n):
    """[frame at which row r starts for r in 0..n]: the rows of a swung tune are (swing >> (r % 8)) & 1 frames shorter than
    `tempo` (src/music.c tick; swing 0 = none)."""
    start = [0]
    for r in range(n):
        start.append(start[-1] + tempo - ((swing >> (r % 8)) & 1))
    return start


def rows_for(channel, text, default_inst, tempo, legacy=True, gap=True, stac_all=None, legato=None, swing=0):
    """Expand a token string into a list of (note, inst, effect) rows.

    legacy: the jingles' original staccato rule (kept so they sound as before).  Otherwise a note is
    cut with the Exx effect on the row where the cut falls (hUGEDriver counts ticks from the start
    of a row, so a cut can only act inside its own row): a staccato note ('!') is cut after 3/4 of
    its length, and a note that is followed by a rest or by the same pitch again is cut one frame
    before its end (the 1-frame gap that makes repeated notes articulate and rests silent).
    stac_all=(num, den): on channel 2 every note is cut after num/den of its length instead.  A '~:n' token
    ties (see merge_ties).
    legato=n (sung tunes, channel 2): a note followed by the same pitch is cut n frames before its end instead of 1,
    so a repeated syllable is still heard as a new one against the legato lead's held volume; a note before a
    rest is cut one frame early as before, and a note followed by another pitch runs straight into it."""
    text = merge_ties(text)
    out, notes = [], []          # notes: (first row, rows, pitch name or None for a rest, staccato)
    for tok in text.split():
        stac = tok.endswith("!")
        tok = tok.rstrip("!")
        stac = stac or bool(stac_all and channel == 2 and not tok.startswith("r:"))
        inst = default_inst
        if "/" in tok:
            tok, i = tok.split("/")
            inst = int(i)
        name, n = tok.split(":")
        n = int(n)
        assert n >= 1, tok
        notes.append((len(out), n, None if name == "r" else name, stac))
        if name == "r":
            out += [(REST, 0, 0)] * n
            continue
        if channel == 4:
            note, inst = NOISE_NOTE[name]
            eff = 0
        elif legacy:
            note = note_no(name)
            eff = 0xE00 | max(1, (n * tempo * 3) // 5) if stac else 0
        else:
            note = note_no(name)
            if channel == 3:
                note += 12      # the wave channel sounds an octave below a pulse channel for the same note index
                assert note < 72, name
            eff = 0
        if channel == 3 and inst == KICK_BODY:
            note += 24          # the kick body's table drops from two octaves up to the note (the pitch name stays: the cuts compare names)
            assert note < 72, name
        out.append((note, inst, eff))
        out += [(REST, 0, 0)] * (n - 1)
    if channel != 4 and not legacy:
        # frame at which each row starts: the rows of a swung tune are (swing >> (row % 8)) & 1 frames shorter than `tempo`
        start = row_starts(tempo, swing, len(out) + 64)
        for k, (row, n, name, stac) in enumerate(notes):
            if name is None:
                continue
            nxt = notes[k + 1][2] if k + 1 < len(notes) else "wrap"
            ticks = start[row + n] - start[row]
            if stac:
                cut = (ticks * stac_all[0]) // stac_all[1] if stac_all and channel == 2 else (ticks * 3) // 4
            elif legato and channel == 2 and nxt == name:
                cut = ticks - legato
            elif gap and (nxt is None or nxt == name):
                cut = ticks - 1
            else:
                continue
            cut = max(cut, 1)
            r = row
            while start[r + 1] <= start[row] + cut:
                r += 1
            t = start[row] + cut - start[r]
            if t == 0:
                t = 1              # tick 0 is the trigger itself
                if r == row:
                    continue
            note, inst, eff = out[r]
            assert eff == 0, (name, r)
            out[r] = (note, inst, 0xE00 | t)
    return out


sys.path.insert(0, str(Path(__file__).resolve().parent))
import songs  # noqa: E402
assert (songs.DUTY_RING, songs.LEAD_PRO, songs.LEGATO_LEAD, songs.BASS_HELD) == (5, LEAD_PRO, LEAD_LEGATO, BASS_HELD) and BASS_PRO == 1, "tools/songs.py instrument numbers"

TUNES = {}

def tune(name, tempo, loop, ch2, ch3, ch4=""):
    TUNES[name] = dict(tempo=tempo, loop=loop, ch2=ch2, ch3=ch3, ch4=ch4)


def bass(bars, rows_per_bar=8):
    """oom-pah accompaniment: root and fifth on alternate 8th notes (bars given as 'root,fifth')."""
    t = []
    for root, fifth in bars:
        if rows_per_bar == 8:
            t += [f"{root}:2!", f"{fifth}:2!", f"{root}:2!", f"{fifth}:2!"]
        else:   # 6 rows: two dotted beats
            t += [f"{root}:3!", f"{fifth}:3!"]
    return " ".join(t)


# LEVEL CLEAR: original rising C-major fanfare, about two seconds.  Tempo 4.
tune("clear", 4, 0,
     ch2="C5:2/3 E5:2/3 G5:2/3 C6:2/3 E6:2/3 G5:2/3 C6:2/3 E6:2/3 G6:10/6 r:2",   # (music batch 4: the fanfare ends on the brass lead, LEAD_PRO)
     ch3="C3:4! G3:4! C3:4! G3:4! C3:10 r:2",
     ch4="")

# GAME OVER: original descending A-minor figure.  Tempo 6.
tune("over", 6, 0,
     ch2="A5:3/2 G5:3/2 F5:3/2 E5:3/2 D5:3/2 C5:3/2 B4:3/2 A4:14/2 r:4",
     ch3=songs.with_inst("A3:6 F3:6 D3:6 E3:6 A3:12 r:6", songs.BASS_HELD),   # (music batch 4: the held pro bass sustains to the end of its notes)
     ch4="")

# BONUS: original tarantella-flavoured 6/8 loop in A minor, one row per eighth note.  Tempo 5.  It loops seamlessly:
# the last bar ends with a B4 C5 D5 run into bar 1 (it was a rest, tests/test_music_loops.py).
tune("bonus", 5, 1,
     ch2=" ".join([
         "E5:1 A5:1 C6:1 B5:1 A5:1 E5:1", "F5:1 A5:1 D6:1 C6:1 A5:1 F5:1",
         "E5:1 G5:1 C6:1 B5:1 G5:1 E5:1", "A5:3 E5:3",
         "C6:1 E6:1 A6:1 G6:1 E6:1 C6:1", "D6:1 F6:1 A6:1 G6:1 F6:1 D6:1",
         "E6:1 D6:1 C6:1 B5:1 A5:1 G5:1", "A5:3 B4:1 C5:1 D5:1"]),   # the last bar climbs back into bar 1's E5
     ch3=bass([("A3", "E4"), ("D3", "A3"), ("C3", "G3"), ("A3", "E4"),
               ("A3", "E4"), ("D3", "A3"), ("E3", "B3"), ("A3", "E4")], 6),
     ch4=" ".join(["b:1 t:1 t:1 b:1 t:1 t:1"] * 8))
# the bonus lead uses the thin pulse
TUNES["bonus"]["ch2"] = " ".join(t + "/4" if ":" in t and not t.startswith("r:") else t
                                 for t in TUNES["bonus"]["ch2"].split())



# ---- tune table: the order is music.h's TUNE_* enum ----------------------------------------------
JINGLES = {"clear": TUNES["clear"], "over": TUNES["over"], "bonus": TUNES["bonus"]}
ORDER = ["title", "clear", "over", "bonus", "show"] + [f"venue{i}" for i in range(len(songs.VENUES))]
SOURCE = {"title": "entertainer", "show": "galop"}
SOURCE.update({f"venue{i}": n for i, n in enumerate(songs.VENUES)})
BLOB_BANKS = (10,)      # a bank of their own (the autobanker only places `#pragma bank 255` files)
# STREAMED tunes: the title (the whole Entertainer, 20 orders, 173 s, looping) and the credits tune (146 s, 10 orders, plays once, TUNE_CREDITS,
# after the listed tunes: no jukebox item, no unlock) have more orders than the 8-pattern WRAM buffer A holds (4 orders of a melody and a bass
# pattern; their drums are the groove, their harmony channel 1).  Each has a bank of its own (STREAMED: tune -> bank) that holds its blob, one
# pattern pair per order in order (a repeated pattern is stored again), and its harmony.  Orders 0-3 are copied to buffer A before the
# tune starts (tune_t.bytes, STREAM_PRELOAD patterns); then src/music.c copies order k+2 (mod the order count, for a looping tune; a
# tune that plays once stops copying at its end) over the buffer slot of order k-2 (finished two orders ago) while order k plays, in
# slices of one order / STREAM_COPY_ROWS bytes on each of rows 2 .. 2 + STREAM_COPY_ROWS - 1, on a plain tick (hUGE_tick 3: tick 1 is the
# row tick's own call, the dearest one).  tune_t.buf is 3 for these.  A looping one needs a whole number of 4-order rings.
# The orders may be short (songs.song(short_orders=): the title's intro and bridge play 32 rows; build pads them with rests and puts a
# pattern break on row 31).
CREDITS = "credits"
CREDITS_BANK = 22
TITLE_BANK = 23
MAP = "map"                  # the story map's tune (Swipesy Cake Walk, tools/songs.py "swipesy"): looping, streamed like the title; TUNE_MAP follows TUNE_CREDITS
MAP_BANK = 25
STREAMED = {"title": TITLE_BANK, CREDITS: CREDITS_BANK, MAP: MAP_BANK}
STREAM_BUF = 3                # tune_t.buf of a streamed tune (buffer A, always copied afresh, order tables wrap at 8 patterns)
STREAM_PRELOAD = 8            # patterns in the first copy (the buffer's size)
CREDITS_ORDERS = 12
JINGLE_BANK = 24              # the jingles' patterns (batch 1 moved them out of bank 2): copied to buffer A like any tune's (a jingle starts 1-4 frames later)
PAT_BANKS = BLOB_BANKS + tuple(STREAMED.values()) + (JINGLE_BANK,)     # one build/music_pat<bank>.c each (the Makefile's GEN lists the same; tools/music_rig.py copies these only)
TUNES = ORDER + [CREDITS, MAP]
SOURCE[CREDITS] = CREDITS
SOURCE[MAP] = "swipesy"
BUF_ID = {"A": 1, "B": 2}


def harm_events(name, t, total):
    """A tune's channel-1 harmony (songs.harmony) -> [(rows, note index or None, instrument 0/1)], checked to last
    exactly `total` rows (the tune's length: it loops with the driver)."""
    if not t.get("ch1"):
        return None
    ev = []
    for tok in merge_ties(t["ch1"]).split():
        inst = 0
        if "/" in tok:
            tok, i = tok.split("/")
            inst = int(i) - 1
            assert inst in (0, 1), (name, tok)
        nm, n = tok.split(":")
        n = int(n)
        assert 1 <= n <= 255, (name, tok)
        ev.append((n, None if nm == "r" else note_no(nm), inst))
    rows = sum(n for n, _, _ in ev)
    assert rows == total, f"{name}: the harmony is {rows} rows, the tune {total}"
    return ev


def harm_starts(ev):
    """The rows at which a harmony event begins (a start row must be one: start_song skips whole events)."""
    out, r = set(), 0
    for n, _, _ in ev:
        out.add(r)
        r += n
    return out


def rotated(ev, start):
    """The events of a harmony track starting at song row `start` (an event boundary): a tune whose first play begins mid-song (songs.py start=, a
    pickup) has its harmony track stored from that row on.  The track is a cycle (it restarts at its end, in step with the driver's loop), so it
    plays the same rows; src/music.c then has nothing to walk through at the start (the walk over Mountain's 48 events cost 4 800 M-cycles)."""
    if not start:
        return ev
    r = 0
    for i, (n, _, _) in enumerate(ev):
        if r == start:
            return ev[i:] + ev[:i]
        r += n
    raise AssertionError(f"no harmony event starts on row {start}")


def harm_bytes(t, ev, start=0):
    ev = rotated(ev, start)
    a, b = (HARM_INST[k] for k in t["ch1_inst"])
    out = [a[0], a[1], b[0], b[1]]
    for n, note, inst in ev:
        out += [HARM_REST if note is None else note | (0x80 if inst else 0), n]
    return out + [0, 0]


def chunks_of(chan_rows, n_orders):
    for o in range(n_orders):
        chunk = chan_rows[o * 64:(o + 1) * 64]
        yield tuple(chunk + [(REST, 0, 0)] * (64 - len(chunk)))


def kick_body(t):
    """T's ch3 text with the kick body on every bass note that starts on a kick row (the groove's b rows, or the kick rows of the
    channel-4 pattern line): instrument KICK_BODY (rows_for puts its note two octaves up).  Tied (~), rest and already-instrumented tokens stay."""
    if t.get("groove"):
        g = t["groove"].split()
        period, kicks = len(g), {i for i, tok in enumerate(g) if tok.startswith("b:")}
    else:
        period, kicks, r = 1 << 30, set(), 0
        for tok in t["ch4"].split():
            nm, rest = tok.split(":", 1)
            if nm == "b":
                kicks.add(r)
            r += int(rest.split("/")[0].rstrip("!"))
    if not kicks or t.get("no_kick_body"):      # (songs.SONGS[name]["no_kick_body"] = True: a tune that keeps its bass plain)
        return t["ch3"]
    out, r = [], 0
    for tok in t["ch3"].split():
        nm, rest = tok.split(":", 1)
        if nm not in ("r", "R", "~") and "/" not in tok and r % period in kicks:
            tok = f"{nm}:{rest.rstrip('!')}/{KICK_BODY}" + ("!" if rest.endswith("!") else "")
        out.append(tok)
        r += int(rest.split("/")[0].rstrip("!"))
    return " ".join(out)


def build(name, t, legacy):
    """Rows -> orders.  Returns the song's channel chunks (4 channels x n_orders patterns)."""
    tempo = t["tempo"]
    inst = t.get("inst", LEAD_PRO)
    gap = t.get("gap", True)
    chans = {
        2: rows_for(2, t["ch2"], inst, tempo, legacy, gap, t.get("stac_all"), t.get("legato"), t.get("swing", 0)),
        3: rows_for(3, kick_body(t), BASS_PRO, tempo, legacy, gap, swing=t.get("swing", 0)),
        4: rows_for(4, t["ch4"], 1, tempo, legacy) if t["ch4"] else [],
    }
    total = max(len(v) for v in chans.values())      # the rows played in a pass (the harmony, the groove and the frames count these)
    chans = {c: v + [(REST, 0, 0)] * (total - len(v)) for c, v in chans.items()}
    chans[1] = [(REST, 0, 0)] * total
    for o in sorted(t.get("short_orders") or ()):    # an order that plays 32 rows: 32 rests behind them, never played, and a pattern break
        for c in chans:                              # on row 31 (the notes' cuts above were counted against the real next notes)
            chans[c][o * 64 + 32:o * 64 + 32] = [(REST, 0, 0)] * 32
        for c in (2, 3):
            note, ins, eff = chans[c][o * 64 + 31]
            if eff == 0:
                chans[c][o * 64 + 31] = (note, ins, BREAK_TO_ROW0)
                break
        else:
            raise SystemExit(f"{name}: no free effect column on order {o} row 31")
    padded = len(chans[2])
    n_orders = (padded + 63) // 64
    if padded % 64:      # a pattern break on the last row ends the final pattern early
        # hUGEDriver keeps the break row plus one (row_break 0 means no break; fx_pattern_break stores the
        # parameter as it is), so D01 starts the next order (wrapping to order 0) on row 0.  D00 did nothing:
        # the last pattern ran on through its empty rows, a dead gap of 64 - (total % 64) rows before the loop.
        for c in ((2, 3, 4, 1) if not legacy else (1,)):
            note, ins, eff = chans[c][padded - 1]
            if eff == 0:
                chans[c][padded - 1] = (note, ins, BREAK_TO_ROW0)
                break
        else:
            raise SystemExit(f"{name}: no channel has a free effect column on its last row")
    per = {c: [list(ch) for ch in chunks_of(chans[c], n_orders)] for c in (1, 2, 3, 4)}
    for row, T in sorted((t.get("tempo_map") or {}).items()):      # Fxx is global: any channel's free effect column
        o, r = divmod(row, 64)
        for c in (4, 3, 2):
            if c == 4 and not t["ch4"]:
                continue
            note, ins, eff = per[c][o][r]
            if eff == 0:
                per[c][o][r] = (note, ins, 0xF00 | T)
                break
        else:
            raise SystemExit(f"{name}: no free effect column at row {row}")
    for row, lst in sorted((t.get("fx_map") or {}).items()):       # a channel's own effect (Cxx wave volume, 0xy arpeggio)
        o, r = divmod(row, 64)
        for c, eff in lst:
            note, ins, e0 = per[c][o][r]
            assert e0 == 0, f"{name}: row {row} channel {c} already has effect {e0:03X}"
            per[c][o][r] = (note, ins, eff)
    per = {c: [tuple(ch) for ch in per[c]] for c in per}
    return dict(total=total, tempo=tempo, n_orders=n_orders, per=per)


def pass_frames(total, tempo, swing=0, tempo_map=None):
    """Frames one pass of a tune lasts: every row is the tempo set last (hUGE Fxx, tempo_map: row -> frames a row), a swung
    row a frame shorter (src/music.c tick).  This is what music_tick's jingle stop counts (tune_t.frames)."""
    cur, frames = tempo, 0
    for r in range(total):
        cur = (tempo_map or {}).get(r, cur)
        frames += cur - ((swing >> (r % 8)) & 1)
    return frames


def groove_rows(name, t):
    """The song's groove as one byte per row (0 none, 1 kick, 2 snare, 3 hat), or None."""
    if not t.get("groove"):
        return None
    rows = []
    for tok in t["groove"].split():
        k, n = tok.split(":")
        rows += [DRUM_ID.get(k, 0)] + [0] * (int(n) - 1)
    return rows


TRACK_MARK = 255     # a groove header whose first byte is this is a DRUM TRACK (src/music.h tune_t.groove): the header's table is the identity 0..6


def track_rows(name, t, total, n_orders):
    """A tune's drum track (songs.song(...).update(track=tokens): the groove's tokens, one per row of the whole tune) as one byte a row (0 none, 1-6 the
    kit), padded with 0 to a whole number of 64-row orders: it is stored after the tune's pattern blob in the tune's own bank."""
    rows = []
    for tok in t["track"].split():
        k, n = tok.split(":")
        rows += [DRUM_ID.get(k, 0)] + [0] * (int(n) - 1)
    assert len(rows) == total, f"{name}: the drum track is {len(rows)} rows, the tune {total}"
    assert rows[0] == 0, f"{name}: a drum track starts on a silent row (src/music.c reads row 1 first; g_pos = 0 is row 0's byte)"
    return rows + [0] * (n_orders * 64 - len(rows))


def row_text(key):
    out = []
    for i in range(0, 64, 4):
        out.append("    " + " ".join(
            "DN({},{},0x{:03X}),".format("___" if n == REST else n, ins, eff) for n, ins, eff in key[i:i + 4]) + "\n")
    return "".join(out)


EMPTY = tuple([(REST, 0, 0)] * 64)


def emit_instruments(f):
    for name, rows in SUBPAT.items():
        f.write(f"static const unsigned char {name}[] = {{   // subpattern, {len(rows)} rows\n")
        for n, j, e in rows:
            f.write(f"    DN({n},{j},0x{e:03X}),\n")
        f.write("};\n")
    f.write("static const hUGEDutyInstr_t duty_inst[] = {\n")
    for ins in DUTY:
        sw, ld, env = ins[:3]
        f.write(f"    {{{sw},{ld},{env},{ins[3] if len(ins) > 3 else 0},128}},\n")
    f.write("};\nstatic const hUGEWaveInstr_t wave_inst[] = {\n")
    for ins in WAVE:
        ln, vol, wv = ins[:3]
        f.write(f"    {{{ln},{vol},{wv},{ins[3] if len(ins) > 3 else 0},128}},\n")
    f.write("};\nstatic const hUGENoiseInstr_t noise_inst[] = {\n")
    for ins in NOISE:
        env, hm = ins[:2]
        f.write(f"    {{{env},{ins[2] if len(ins) > 2 else 0},{hm},0,0}},\n")
    f.write("};\n\n")


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    built = {}
    for name in TUNES:
        if name in JINGLES:
            built[name] = build(name, JINGLES[name], True)
        else:
            built[name] = build(name, songs.SONGS[SOURCE[name]], False)

    # buffered tunes: assign pattern slots (in first-use order, per song) and pack the blobs
    def buf_of(name):
        return "A" if name in JINGLES else songs.SONGS[SOURCE[name]]["buf"]

    slots = {}        # tune -> {key: slot}
    for name in TUNES:
        sl = {}
        if name in STREAMED:       # order by order: melody, bass (pairs of slots), see STREAMED above; a repeated pattern is stored again
            b = built[name]
            t = songs.SONGS[SOURCE[name]]
            assert not t["ch4"] and buf_of(name) == "A", f"{name}: a streamed tune has no drum patterns (a groove) and uses buffer A"
            assert all(k == EMPTY for c in (1, 4) for k in b["per"][c])
            assert name != CREDITS or b["n_orders"] == CREDITS_ORDERS, f"the credits tune: {CREDITS_ORDERS} orders"
            assert b["n_orders"] > STREAM_PRELOAD // 2
            assert name == CREDITS or b["n_orders"] % (STREAM_PRELOAD // 2) == 0, f"{name}: a looping streamed tune is whole 4-order rings"
            for o in range(b["n_orders"]):
                for c in (2, 3):
                    assert b["per"][c][o] != EMPTY, f"{name} order {o} channel {c}: an empty pattern (the stream expects every slot)"
                    sl[(o, c)] = len(sl)
        else:
            for c in (1, 2, 3, 4):
                for key in built[name]["per"][c]:
                    if key != EMPTY and key not in sl:
                        sl[key] = len(sl)
        slots[name] = sl
    max_a = max(STREAM_PRELOAD, max(len(sl) for n, sl in slots.items() if buf_of(n) == "A" and n not in STREAMED))
    max_b = max(len(sl) for n, sl in slots.items() if buf_of(n) == "B")

    # blobs -> banks: a streamed tune's bank is its own; the jingles share JINGLE_BANK; the rest first fit, in tune order
    bank_of, used = {}, {b: 0 for b in BLOB_BANKS}
    for name in slots:
        size = len(slots[name]) * SLOT_BYTES
        if name in STREAMED:
            bank_of[name] = STREAMED[name]
            assert size <= 16384, f"{name}: the blob and the harmony share a bank of their own"
            continue
        if name in JINGLES:
            bank_of[name] = JINGLE_BANK
            used[JINGLE_BANK] = used.get(JINGLE_BANK, 0) + size
            assert used[JINGLE_BANK] <= 16384
            continue
        for b in BLOB_BANKS:
            if used[b] + size <= 15500:
                bank_of[name] = b
                used[b] += size
                break
        else:
            raise SystemExit("blobs do not fit banks %s" % (BLOB_BANKS,))
    def blob_keys(name):        # the patterns of a tune's blob in slot order
        if name in STREAMED:
            return [built[name]["per"][c][o] for (o, c) in slots[name]]
        return list(slots[name])

    harms = {}
    for name in slots:
        if name in JINGLES:
            continue
        t = songs.SONGS[SOURCE[name]]
        ev = harm_events(name, t, built[name]["total"])
        if ev:
            harms[name] = harm_bytes(t, ev, t.get("start", 0))
            if name in STREAMED:     # (src/music.c start_song: tunes[tune].buf == 3 ? tunes[tune].bank : HARM_BANK)
                assert len(harms[name]) + len(slots[name]) * SLOT_BYTES + built[name]["n_orders"] * 64 * bool(songs.SONGS[SOURCE[name]].get("track")) <= 16384, f"the {name} bank"
            else:
                used[HARM_BANK] += len(harms[name])
    assert used[HARM_BANK] <= 16384, used
    hdr = (Path(__file__).resolve().parent.parent / "src" / "music.h").read_text()
    m = re.search(r"#define HARM_BANK (\d+)", hdr)
    assert m and int(m.group(1)) == HARM_BANK, "src/music.h HARM_BANK differs from gen_music.HARM_BANK"
    for k, v in (("STREAM_ORDER_BYTES", None), ("STREAM_COPY_ROWS", None), ("STREAM_SLICE", None), ("STREAM_TICK", 3)):
        m = re.search(r"#define %s\s+(.*?)(?:\s*//.*)?$" % k, hdr, re.M)
        assert m, f"src/music.h {k}"
        if v is not None:
            assert int(m.group(1)) == v, f"src/music.h {k}"
    m = re.search(r"#define STREAM_ORDER_BYTES\s+\(?(\d+) \* (\d+)\)?", hdr)
    assert m and int(m.group(1)) * int(m.group(2)) == 2 * SLOT_BYTES, "src/music.h STREAM_ORDER_BYTES (a melody and a bass pattern)"
    assert STREAM_PRELOAD == 8, "src/music.c: the buffer holds four orders (a slot is order & 3)"
    for b in PAT_BANKS:
        with open(out / f"music_pat{b}.c", "w") as f:
            f.write("// Generated by tools/gen_music.py from tools/songs.py. Do not edit.\n// Pattern blobs: copied into WRAM by src/music.c.\n")
            f.write(f"#pragma bank {b}\n#include \"hUGEDriver.h\"\n\n")
            for name in slots:
                if bank_of[name] != b:
                    continue
                f.write(f"const unsigned char blob_{name}[] = {{   // {SOURCE.get(name, name)}: {len(slots[name])} patterns\n")
                for key in blob_keys(name):
                    f.write(row_text(key))
                if songs.SONGS.get(SOURCE.get(name), {}).get("track"):          # (the drum track follows the patterns: src/music.c reads it at blob + orders * STREAM_ORDER_BYTES)
                    tr = track_rows(name, songs.SONGS[SOURCE[name]], built[name]["total"], built[name]["n_orders"])
                    f.write(f"    // the drum track: {len(tr)} bytes, one a row\n")
                    for i in range(0, len(tr), 32):
                        f.write("    " + ",".join(str(x) for x in tr[i:i + 32]) + ",\n")
                f.write("};\n\n")
            for name, hb in harms.items():
                if b != (bank_of[name] if name in STREAMED else HARM_BANK):    # (a streamed tune's harmony: its blob's bank)
                    continue
                f.write(f"const unsigned char harm_{name}[] = {{   // {SOURCE[name]}: channel-1 harmony, "
                        f"{len(hb) // 2 - 3} events\n")
                for i in range(0, len(hb), 16):
                    f.write("    " + ",".join(str(x) for x in hb[i:i + 16]) + ",\n")
                f.write("};\n\n")

    with open(out / "music_data.c", "w") as f:
        f.write("// Generated by tools/gen_music.py from the tune sources there and in tools/songs.py. Do not edit.\n")
        f.write("#pragma bank 2\n#include <stddef.h>\n#include \"hUGEDriver.h\"\n#include \"music.h\"\n\n")
        f.write(f"unsigned char mus_buf_a[{max_a * SLOT_BYTES}];    // WRAM: title / venue tune patterns ({max_a} patterns)\n")
        f.write(f"unsigned char mus_buf_b[{max_b * SLOT_BYTES}];    // WRAM: show tune patterns ({max_b} patterns)\n\n")
        f.write("static const unsigned char waves[] = {\n")
        for w in WAVES:
            f.write("    " + ",".join(str(x) for x in w) + ",\n")
        f.write("};\n\n")
        emit_instruments(f)
        f.write("static const unsigned char empty_pat[] = {\n" + row_text(EMPTY) + "};\n\n")
        f.write("// drum kit of the groove player (src/music.c): NR41, NR42, NR43, NR44, NR43 +1 frame, NR43 +2 frames of b n t o m x\n")
        f.write("const unsigned char drum_kit[6][6] = {" + ", ".join("{" + ",".join(f"0x{v:02X}" for v in d) + "}" for d in drum_kit()) + "};\n")
        grooves = {}
        for name in TUNES:
            if name in JINGLES:
                continue
            t = songs.SONGS[SOURCE[name]]
            g = groove_rows(name, t)
            if t.get("track"):
                assert name in STREAMED and not g and not t.get("swing") and t["tempo"] < 256
                grooves[name] = [0]
                f.write(f"static const unsigned char groove_{name}[] = {{{TRACK_MARK}, 0, 0, 1, 2, 3, 4, 5, 6}};   // a drum track: its row byte (0-6) read as the groove's own\n")
            elif g:
                assert built[name]["total"] % len(g) == 0, f"{name}: {built[name]['total']} rows is not a whole number of {len(g)}-row grooves"
                assert len(g) < TRACK_MARK and t["tempo"] < 256
                grooves[name] = g
                f.write(f"static const unsigned char groove_{name}[] = {{{len(g)}, {t.get('swing', 0) or t['tempo']}, "
                        + ", ".join(str(x) for x in g) + "};\n")
        f.write("\n")
        for name in slots:
            f.write(f"extern const unsigned char blob_{name}[];\n")
        for name in harms:
            f.write(f"extern const unsigned char harm_{name}[];\n")
        f.write("const unsigned char * const harm_tab[TUNE_ALL] = {"
                + ", ".join(f"harm_{n}" if n in harms else "NULL" for n in TUNES) + "};\n\n")
        for name in TUNES:
            b = built[name]
            buf = "mus_buf_" + buf_of(name).lower()
            wrap = STREAM_PRELOAD if name in STREAMED else 1 << 30      # a streamed tune's later orders sit over the first ones
            slot = (lambda o, c, key: slots[name][(o, c)]) if name in STREAMED else (lambda o, c, key: slots[name][key])
            orders = {c: [("empty_pat" if key == EMPTY else f"&{buf}[{slot(o, c, key) % wrap * SLOT_BYTES}]")
                          for o, key in enumerate(b["per"][c])] for c in (1, 2, 3, 4)}
            f.write(f"static const unsigned char {name}_order_cnt = {b['n_orders'] * 2};\n")
            for c in (1, 2, 3, 4):
                f.write(f"static const unsigned char * const {name}_order{c}[] = {{{', '.join(orders[c])}}};\n")
            f.write(f"static const hUGESong_t song_{name} = {{{b['tempo']}, &{name}_order_cnt, "
                    f"(const unsigned char **){name}_order1, (const unsigned char **){name}_order2, "
                    f"(const unsigned char **){name}_order3, (const unsigned char **){name}_order4, "
                    f"duty_inst, wave_inst, noise_inst, NULL, waves}};\n\n")
        f.write("// song, loop, frames per pass, buffer (1 A, 2 B, 3 A streamed), bank / source / bytes of the pattern blob (a streamed tune's first four orders), groove (or NULL), first row\n")
        f.write("const tune_t tunes[TUNE_ALL] = {\n")
        for name in TUNES:
            b = built[name]
            sw = songs.SONGS[SOURCE[name]].get("swing", 0) if name in SOURCE else 0
            frames = pass_frames(b["total"], b["tempo"], sw, (JINGLES[name] if name in JINGLES else songs.SONGS[SOURCE[name]]).get("tempo_map"))
            b["frames"] = frames
            loop = JINGLES[name]["loop"] if name in JINGLES else int(name != CREDITS)
            tail = "{}, {}, blob_{}, {}".format(STREAM_BUF if name in STREAMED else BUF_ID[buf_of(name)], bank_of[name], name,
                                                min(len(slots[name]), STREAM_PRELOAD if name in STREAMED else 99) * SLOT_BYTES)
            tail += ", " + (f"groove_{name}" if name in grooves else "NULL")
            start = 0 if name in JINGLES else songs.SONGS[SOURCE[name]].get("start", 0)
            assert not start or (start < b["total"] and name not in grooves), f"{name}: bad start row {start}"
            assert not start or name not in harms or start in harm_starts(harm_events(name, songs.SONGS[SOURCE[name]], b["total"])), \
                f"{name}: the harmony has no note boundary on the start row {start} (src/music.c start_song walks the events to it)"
            tail += f", {start}"
            f.write(f"    {{&song_{name}, {loop}, {frames}, {tail}}},   // {name}"
                    f"{' = ' + SOURCE[name] if name in SOURCE else ''}: {b['total']} rows\n")
        f.write("};\n")
    for name in TUNES:
        b = built[name]
        extra = f", blob {len(slots[name])} patterns in bank {bank_of[name]}" if name in slots else ""
        print(f"gen_music: {name}{'=' + SOURCE[name] if name in SOURCE else ''}: {b['total']} rows x {b['tempo']} frames "
              f"= {b['frames'] / 60:.1f}s ({b['frames']} frames), {b['n_orders']} orders{extra}")
    print(f"gen_music: WRAM buffers: A {max_a} patterns ({max_a * SLOT_BYTES} B), B {max_b} ({max_b * SLOT_BYTES} B); "
          f"blob and harmony bytes per bank {used} (harmony {sum(len(h) for h in harms.values())} B: "
          + ", ".join(f"{n} {len(h)}" for n, h in harms.items()) + ")")
    write_jukebox_names(out)


# ---- the soundtrack player's names (songs.SOUNDTRACK) -> build/jukebox_names.h, #included by src/jukebox.c ----------
JB_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,!?'-:")
JB_W = 18


def wrap(s, w=JB_W):
    lines, cur = [], ""
    for word in s.split():
        if cur and len(cur) + 1 + len(word) > w:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}" if cur else word
    return lines + [cur]


def jukebox_entries():
    """Per tune in ORDER: (key, list name, [4 info lines: title 1, title 2 (or ''), credit, where])."""
    out = []
    for name in ORDER:
        key = SOURCE.get(name, name)
        if key not in songs.SOUNDTRACK:
            raise SystemExit(f"gen_music: songs.SOUNDTRACK has no entry for {key} (tune {name})")
        short, full, credit, where = songs.SOUNDTRACK[key]
        title = wrap(full)
        if len(title) > 2:
            raise SystemExit(f"gen_music: {key}: the full title needs more than two lines of {JB_W}")
        lines = title + [""] * (2 - len(title)) + [credit, where]
        for s in [short] + lines:
            if len(s) > JB_W or not set(s) <= JB_CHARS:
                raise SystemExit(f"gen_music: {key}: '{s}' is longer than {JB_W} or has a character with no glyph")
        out.append((key, short, lines))
    return out


def write_jukebox_names(out):
    e = jukebox_entries()
    q = lambda s: '"' + s + '"'
    lines = ["// Generated by tools/gen_music.py from tools/songs.py SOUNDTRACK. Do not edit. #included by src/jukebox.c.",
             f"#define JB_TUNES {len(e)}",
             "typedef char jb_count_check[JB_TUNES == TUNE_COUNT ? 1 : -1];   // songs.SOUNDTRACK / ORDER = music.h's tunes",
             f"static const char jb_name[JB_TUNES][{JB_W + 1}] = {{"]
    lines += [f"    {q(s)},   // {k}" for k, s, _ in e] + ["};",
              f"static const char jb_info[JB_TUNES][4][{JB_W + 1}] = {{   // the full title (2 lines), credit, where"]
    lines += ["    { " + ", ".join(q(s) for s in l) + " }," for _, _, l in e] + ["};", ""]
    (out / "jukebox_names.h").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
