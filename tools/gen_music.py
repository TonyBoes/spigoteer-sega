#!/usr/bin/env python3
"""Tune sources -> build/music_data.c, build/music_pat10.c (hUGEDriver song data, C).

No tracker GUI is involved: each tune is a few lines of text per channel.  A token is NOTE:ROWS
(rows are 16th/8th notes depending on the tune's tempo), 'r:ROWS' is a rest, a trailing '!' makes
the note staccato (note cut), and '/N' picks instrument N for that note.  hUGEDriver's channel 1 is never used
(its patterns are empty): the buffered tunes' channel-1 harmony (songs.harmony, music step 5) is a compact event list
(harm_<tune>, bank HARM_BANK) that src/music.c plays itself and gives up to the sound effects; channel 4 is
percussion (k s h: the loud old kit, K S H: the quiet kit).

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
import re
import sys
from pathlib import Path

SEMI = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
REST = 90          # ___ in hUGEDriver.h

# ---- instruments (indexes are 1-based in the pattern data) -------------------------------------
LEGATO_ENV = 0x60   # NR12 of the legato lead: volume 6, envelope off (period 0): a sung note holds its level
DUTY = [  # sweep, len_duty (NR11), envelope (NR12), subpattern, highmask
    (0x08, 0x80, 0x83),   # 1 lead: 50% pulse, volume 8, slow decay
    (0x08, 0x40, 0x73),   # 2 soft lead: 25% pulse, volume 7, slow decay
    (0x08, 0x80, 0xA1),   # 3 plink: 50% pulse, volume 10, fast decay (short jingle notes)
    (0x08, 0x00, 0xC1),   # 4 thin: 12.5% pulse, volume 12, fast decay (quick bonus-round notes)
    (0x08, 0x80, 0x85),   # 5 song lead: 50% pulse, volume 8, slow decay (long notes keep sounding)
    (0x08, 0x80, LEGATO_ENV),   # 6 legato lead (sung tunes, songs.song(legato=)): 50% pulse, held volume, no decay
    (0x08, 0x80, 0xC7),   # 7 ring: 50% pulse, volume 12, slowest decay (12 x 7/64 s = 1.3 s): the credits tune's final chord
]
WAVE = [  # length, volume (NR32: 0x20 = 100%, 0x40 = 50%), waveform index, subpattern, highmask
    (0, 0x20, 0),         # 1 bass: triangle, NR32 100% (the waveform itself is scaled, BASS_AMP)
    (0, 0x20, 1),         # 2 hollow bass: pulse-ish wave at 100%
]
NOISE = [  # envelope (NR42), subpattern, highmask+length
    (0x81, 0x00),         # 1 kick  (vol 8, fast decay)
    (0x61, 0x00),         # 2 snare (vol 6, fast decay)
    (0x31, 0x80),         # 3 hat   (vol 3, fast decay, 7-bit LFSR = metallic)
    (0x81, 0x00),         # 4 kick, quiet kit: low noise, 15-bit LFSR, volume 8, fast decay
    (0x73, 0x00),         # 5 snare, quiet kit: mid noise, 15-bit LFSR, volume 7, medium decay
    (0x61, 0xB6),         # 6 hat, quiet kit: high noise, 7-bit LFSR, volume 6, very short (length-limited)
]
# channel-1 harmony instruments (songs.harmony inst names): NR11 (duty), NR12 (envelope).  Quieter than the melody
# (song lead 0x85, legato lead 0x60) and the effects (channel 1 volume 8-12): volume 5, a thinner duty.
HARM_INST = {
    "harm": (0x40, 0x57),     # 25% pulse, volume 5, slow decay (0.55 s to silence): thirds and sixths under a melody
    "pad": (0x00, 0x50),      # 12.5% pulse, volume 5 held: sustained chord tones (waltzes, the sung tunes)
    "stab": (0x40, 0x52),     # 25% pulse, volume 5, quick decay (0.16 s): off-beat stabs
    "harm50": (0x80, 0x57),   # "harm" at 50% duty (the Entertainer's thirds: rounder, less nasal)
    "pluck": (0x00, 0x55),    # 12.5% pulse, volume 5, medium decay (0.39 s): plucked, koto-like
    "ring50": (0x80, 0x97),   # 50% pulse, volume 9, slowest decay (1.0 s): the credits tune's final chord rings
}
HARM_REST = 0x7F
HARM_BANK = 10              # src/music.h HARM_BANK (checked in main)
NOISE_NOTE = {"k": (12, 1), "s": (44, 2), "h": (60, 3), "K": (12, 4), "S": (44, 5), "H": (60, 6)}   # note number sets the pitch
DRUM_ID = {"K": 1, "S": 2, "H": 3}     # groove byte -> row of the generator's kit (0 = no hit)


def noise_poly(n):
    """NR43 base value hUGEDriver's get_note_poly makes of a noise note number n (before the instrument's 7-bit step flag)."""
    a = (~((n - 36 + 192) & 255)) & 255
    if a < 7:
        return a
    return ((((a >> 2) - 1) << 4) | ((a & 3) + 4)) & 255


def drum_kit():
    """The quiet kit as register values (NR41, NR42, NR43, NR44) for src/music.c's groove player, derived from the
    same instruments hUGEDriver plays so that a groove sounds like the pattern drums."""
    out = []
    for key in "KSH":
        n, inst = NOISE_NOTE[key]
        env, hm = NOISE[inst - 1]
        nr43 = noise_poly(n) | (0x08 if hm & 0x80 else 0)
        nr44 = 0x80 | (hm & 0x40)
        out.append((hm & 0x3F, env, nr43, nr44))
    return out


BASS_AMP = 0.5      # the bass wave runs at 100% output (NR32 0x20) but its samples span this fraction of the full 4-bit range


def scaled_wave(w, amp):
    """Pack 32 4-bit samples (16 bytes, high nibble first) scaled around the centre 7.5; the DAC stays centred."""
    nib = [x for b in w for x in (b >> 4, b & 15)]
    nib = [int(round(7.5 + (x - 7.5) * amp)) for x in nib]
    return [(nib[i] << 4) | nib[i + 1] for i in range(0, 32, 2)]


WAVES = [
    # 0 triangle (full range 0..15 scaled by BASS_AMP)
    scaled_wave([0x01, 0x23, 0x45, 0x67, 0x89, 0xAB, 0xCD, 0xEF, 0xFE, 0xDC, 0xBA, 0x98, 0x76, 0x54, 0x32, 0x10], BASS_AMP),
    # 1 hollow: 25% duty square, softened
    [0xFF, 0xFF, 0xFF, 0xFF, 0xCC, 0x88, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
]


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
     ch2="C5:2/3 E5:2/3 G5:2/3 C6:2/3 E6:2/3 G5:2/3 C6:2/3 E6:2/3 G6:10/1 r:2",
     ch3="C3:4! G3:4! C3:4! G3:4! C3:10 r:2",
     ch4="")

# GAME OVER: original descending A-minor figure.  Tempo 6.
tune("over", 6, 0,
     ch2="A5:3/2 G5:3/2 F5:3/2 E5:3/2 D5:3/2 C5:3/2 B4:3/2 A4:14/2 r:4",
     ch3="A3:6 F3:6 D3:6 E3:6 A3:12 r:6",
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
     ch4=" ".join(["k:1 h:1 h:1 k:1 h:1 h:1"] * 8))
# the bonus lead uses the thin pulse
TUNES["bonus"]["ch2"] = " ".join(t + "/4" if ":" in t and not t.startswith("r:") else t
                                 for t in TUNES["bonus"]["ch2"].split())



# ---- tune table: the order is music.h's TUNE_* enum ----------------------------------------------
JINGLES = {"clear": TUNES["clear"], "over": TUNES["over"], "bonus": TUNES["bonus"]}
ORDER = ["title", "clear", "over", "bonus", "show"] + [f"venue{i}" for i in range(len(songs.VENUES))]
SOURCE = {"title": "entertainer", "show": "galop"}
SOURCE.update({f"venue{i}": n for i, n in enumerate(songs.VENUES)})
BLOB_BANKS = (10,)      # a bank of their own (the autobanker only places `#pragma bank 255` files)
# The credits tune (music.h TUNE_CREDITS, after the listed tunes: no jukebox item, no unlock): 146 s, 10 orders of 2 patterns (melody,
# bass; no drums), so its 20 patterns do not fit the 8-pattern WRAM buffer A (4 orders).  Its blob (bank CREDITS_BANK, src/music.h,
# a bank of its own with the tune's harmony) holds one pattern pair per order, a repeated pattern stored again: slots 0-7 = orders 0-3,
# copied to buffer A before it starts (tune_t.bytes); then src/music.c copies order k+2 over the buffer slot of order k-2 (finished
# two orders ago) while order k plays, in slices of one order / CREDITS_COPY_ROWS bytes a row.  It plays once (a jingle: the credits
# roll waits for it), so nothing is ever reloaded for a second pass.
CREDITS = "credits"
CREDITS_BANK = 22
CREDITS_PRELOAD = 8          # patterns in the first copy (the buffer's size)
CREDITS_ORDERS = 10
TUNES = ORDER + [CREDITS]
SOURCE[CREDITS] = CREDITS
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


def harm_bytes(t, ev):
    a, b = (HARM_INST[k] for k in t["ch1_inst"])
    out = [a[0], a[1], b[0], b[1]]
    for n, note, inst in ev:
        out += [HARM_REST if note is None else note | (0x80 if inst else 0), n]
    return out + [0, 0]


def chunks_of(chan_rows, n_orders):
    for o in range(n_orders):
        chunk = chan_rows[o * 64:(o + 1) * 64]
        yield tuple(chunk + [(REST, 0, 0)] * (64 - len(chunk)))


def build(name, t, legacy):
    """Rows -> orders.  Returns the song's channel chunks (4 channels x n_orders patterns)."""
    tempo = t["tempo"]
    inst = t.get("inst", 1)
    gap = t.get("gap", True)
    chans = {
        2: rows_for(2, t["ch2"], inst, tempo, legacy, gap, t.get("stac_all"), t.get("legato"), t.get("swing", 0)),
        3: rows_for(3, t["ch3"], 1, tempo, legacy, gap, swing=t.get("swing", 0)),
        4: rows_for(4, t["ch4"], 1, tempo, legacy) if t["ch4"] else [],
    }
    total = max(len(v) for v in chans.values())
    chans = {c: v + [(REST, 0, 0)] * (total - len(v)) for c, v in chans.items()}
    chans[1] = [(REST, 0, 0)] * total
    n_orders = (total + 63) // 64
    if total % 64:      # a pattern break on the last row ends the final pattern early
        # hUGEDriver keeps the break row plus one (row_break 0 means no break; fx_pattern_break stores the
        # parameter as it is), so D01 starts the next order (wrapping to order 0) on row 0.  D00 did nothing:
        # the last pattern ran on through its empty rows, a dead gap of 64 - (total % 64) rows before the loop.
        for c in ((2, 3, 4, 1) if not legacy else (1,)):
            note, ins, eff = chans[c][total - 1]
            if eff == 0:
                chans[c][total - 1] = (note, ins, BREAK_TO_ROW0)
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


def row_text(key):
    out = []
    for i in range(0, 64, 4):
        out.append("    " + " ".join(
            "DN({},{},0x{:03X}),".format("___" if n == REST else n, ins, eff) for n, ins, eff in key[i:i + 4]) + "\n")
    return "".join(out)


EMPTY = tuple([(REST, 0, 0)] * 64)


def emit_instruments(f):
    f.write("static const hUGEDutyInstr_t duty_inst[] = {\n")
    for sw, ld, env in DUTY:
        f.write(f"    {{{sw},{ld},{env},0,128}},\n")
    f.write("};\nstatic const hUGEWaveInstr_t wave_inst[] = {\n")
    for ln, vol, wv in WAVE:
        f.write(f"    {{{ln},{vol},{wv},0,128}},\n")
    f.write("};\nstatic const hUGENoiseInstr_t noise_inst[] = {\n")
    for env, hm in NOISE:
        f.write(f"    {{{env},0,{hm},0,0}},\n")
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
    slots = {}        # tune -> {key: slot}
    for name in TUNES:
        if name in JINGLES:
            continue
        sl = {}
        if name == CREDITS:        # order by order: melody, bass (pairs of slots), see CREDITS above; a repeated pattern is stored again
            b = built[name]
            assert b["n_orders"] == CREDITS_ORDERS and not songs.SONGS[SOURCE[name]]["ch4"], f"the credits tune: {CREDITS_ORDERS} orders, no drums"
            assert all(k == EMPTY for c in (1, 4) for k in b["per"][c])
            for o in range(CREDITS_ORDERS):
                for c in (2, 3):
                    assert b["per"][c][o] != EMPTY, f"credits order {o} channel {c}: an empty pattern (the stream expects every slot)"
                    sl[(o, c)] = len(sl)
            assert len(sl) == 2 * CREDITS_ORDERS
        else:
            for c in (1, 2, 3, 4):
                for key in built[name]["per"][c]:
                    if key != EMPTY and key not in sl:
                        sl[key] = len(sl)
        slots[name] = sl
    max_a = max(len(sl) for n, sl in slots.items() if songs.SONGS[SOURCE[n]]["buf"] == "A" and n != CREDITS)
    assert max_a >= CREDITS_PRELOAD, "buffer A is the credits tune's preload size: no tune needs fewer patterns than that"
    max_b = max(len(sl) for n, sl in slots.items() if songs.SONGS[SOURCE[n]]["buf"] == "B")

    # blobs -> banks (first fit, in tune order)
    bank_of, used = {}, {b: 0 for b in BLOB_BANKS}
    for name in slots:
        size = len(slots[name]) * SLOT_BYTES
        if name == CREDITS:
            bank_of[name] = CREDITS_BANK
            assert size <= 16384, "the credits blob and harmony share a bank of their own"
            continue
        for b in BLOB_BANKS:
            if used[b] + size <= 15500:
                bank_of[name] = b
                used[b] += size
                break
        else:
            raise SystemExit("blobs do not fit banks %s" % (BLOB_BANKS,))
    def blob_keys(name):        # the patterns of a tune's blob in slot order
        if name == CREDITS:
            return [built[name]["per"][c][o] for (o, c) in slots[name]]
        return list(slots[name])

    harms = {}
    for name in slots:
        t = songs.SONGS[SOURCE[name]]
        ev = harm_events(name, t, built[name]["total"])
        if ev:
            harms[name] = harm_bytes(t, ev)
            if name == CREDITS:     # the credits tune's harmony sits in its blob's bank (src/music.c: cur_tune == TUNE_CREDITS ? CREDITS_BANK : HARM_BANK)
                assert len(harms[name]) + len(slots[name]) * SLOT_BYTES <= 16384, "the credits bank"
            else:
                used[HARM_BANK] += len(harms[name])
    assert used[HARM_BANK] <= 16384, used
    hdr = (Path(__file__).resolve().parent.parent / "src" / "music.h").read_text()
    m = re.search(r"#define HARM_BANK (\d+)", hdr)
    assert m and int(m.group(1)) == HARM_BANK, "src/music.h HARM_BANK differs from gen_music.HARM_BANK"
    m = re.search(r"#define CREDITS_BANK\s+(\d+)", hdr)
    assert m and int(m.group(1)) == CREDITS_BANK, "src/music.h CREDITS_BANK differs from gen_music.CREDITS_BANK"
    m = re.search(r"#define CREDITS_ORDERS\s+(\d+)", hdr)
    assert m and int(m.group(1)) == CREDITS_ORDERS, "src/music.h CREDITS_ORDERS differs from gen_music.CREDITS_ORDERS"
    m = re.search(r"#define CREDITS_ORDER_BYTES\s+\(?(\d+) \* (\d+)\)?", hdr)
    assert m and int(m.group(1)) * int(m.group(2)) == 2 * SLOT_BYTES, "src/music.h CREDITS_ORDER_BYTES (a melody and a bass pattern)"
    assert CREDITS_PRELOAD == 8, "src/music.c: the buffer holds four orders (a slot is order & 3)"
    for b in BLOB_BANKS + (CREDITS_BANK,):
        with open(out / f"music_pat{b}.c", "w") as f:
            f.write("// Generated by tools/gen_music.py from tools/songs.py. Do not edit.\n// Pattern blobs: copied into WRAM by src/music.c.\n")
            f.write(f"#pragma bank {b}\n#include \"hUGEDriver.h\"\n\n")
            for name in slots:
                if bank_of[name] != b:
                    continue
                f.write(f"const unsigned char blob_{name}[] = {{   // {SOURCE[name]}: {len(slots[name])} patterns\n")
                for key in blob_keys(name):
                    f.write(row_text(key))
                f.write("};\n\n")
            for name, hb in harms.items():
                if (name == CREDITS and b != CREDITS_BANK) or (name != CREDITS and b != HARM_BANK):    # (the credits tune's harmony: its own bank)
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
        f.write("// drum kit of the groove player (src/music.c): NR41, NR42, NR43, NR44 of kick, snare, hat\n")
        f.write("const unsigned char drum_kit[3][4] = {" + ", ".join("{" + ",".join(f"0x{v:02X}" for v in d) + "}" for d in drum_kit()) + "};\n")
        grooves = {}
        for name in TUNES:
            if name in JINGLES:
                continue
            t = songs.SONGS[SOURCE[name]]
            g = groove_rows(name, t)
            if g:
                assert built[name]["total"] % len(g) == 0, f"{name}: {built[name]['total']} rows is not a whole number of {len(g)}-row grooves"
                assert len(g) < 256 and t["tempo"] < 256
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
            if name in JINGLES:
                pats = {}
                orders = {1: [], 2: [], 3: [], 4: []}
                for c in (1, 2, 3, 4):
                    for key in b["per"][c]:
                        if key == EMPTY:
                            orders[c].append("empty_pat")
                            continue
                        if key not in pats:
                            pats[key] = f"{name}_p{len(pats)}"
                            f.write(f"static const unsigned char {pats[key]}[] = {{\n{row_text(key)}}};\n")
                        orders[c].append(pats[key])
            else:
                buf = "mus_buf_" + songs.SONGS[SOURCE[name]]["buf"].lower()
                wrap = CREDITS_PRELOAD if name == CREDITS else 1 << 30      # the credits' later orders sit over the first ones
                slot = (lambda o, c, key: slots[name][(o, c)]) if name == CREDITS else (lambda o, c, key: slots[name][key])
                orders = {c: [("empty_pat" if key == EMPTY else f"&{buf}[{slot(o, c, key) % wrap * SLOT_BYTES}]")
                              for o, key in enumerate(b["per"][c])] for c in (1, 2, 3, 4)}
            f.write(f"static const unsigned char {name}_order_cnt = {b['n_orders'] * 2};\n")
            for c in (1, 2, 3, 4):
                f.write(f"static const unsigned char * const {name}_order{c}[] = {{{', '.join(orders[c])}}};\n")
            f.write(f"static const hUGESong_t song_{name} = {{{b['tempo']}, &{name}_order_cnt, "
                    f"(const unsigned char **){name}_order1, (const unsigned char **){name}_order2, "
                    f"(const unsigned char **){name}_order3, (const unsigned char **){name}_order4, "
                    f"duty_inst, wave_inst, noise_inst, NULL, waves}};\n\n")
        f.write("// song, loop, frames per pass, buffer (0 none, 1 A, 2 B), bank / source / bytes of the pattern blob, groove (or NULL), first row\n")
        f.write("const tune_t tunes[TUNE_ALL] = {\n")
        for name in TUNES:
            b = built[name]
            sw = songs.SONGS[SOURCE[name]].get("swing", 0) if name in SOURCE else 0
            frames = pass_frames(b["total"], b["tempo"], sw, (JINGLES[name] if name in JINGLES else songs.SONGS[SOURCE[name]]).get("tempo_map"))
            b["frames"] = frames
            loop = JINGLES[name]["loop"] if name in JINGLES else int(name != CREDITS)
            if name in JINGLES:
                tail = "0, 0, NULL, 0"
            else:
                tail = "{}, {}, blob_{}, {}".format(BUF_ID[songs.SONGS[SOURCE[name]]["buf"]], bank_of[name], name,
                                                    min(len(slots[name]), CREDITS_PRELOAD if name == CREDITS else 99) * SLOT_BYTES)
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
