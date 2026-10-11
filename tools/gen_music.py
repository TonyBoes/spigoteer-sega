#!/usr/bin/env python3
"""Tune sources -> build/music_data.c, build/music_pat3.c, build/music_pat4.c (hUGEDriver song data, C).

No tracker GUI is involved: each tune is a few lines of text per channel.  A token is NOTE:ROWS
(rows are 16th/8th notes depending on the tune's tempo), 'r:ROWS' is a rest, a trailing '!' makes
the note staccato (note cut), and '/N' picks instrument N for that note.  Channel 1 is never used
by the music (sound effects own it); channel 4 is percussion (k s h: the loud old kit, K S H: the
quiet kit).

Two kinds of tune:
 * jingles (level clear, game over, bonus): small, their patterns sit in bank 2 beside the driver.
 * "buffered" tunes (title, show, nine venue tunes, tools/songs.py): hUGEDriver reads patterns through
   plain pointers into whatever ROM bank is mapped, and bank 2 is the only place the driver runs
   from, so these songs cannot live elsewhere in ROM as they are.  Their patterns are packed into
   blobs in ROM banks 3 and 4; at music_play() src/music.c copies the song's blob into a WRAM buffer
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
DUTY = [  # sweep, len_duty (NR11), envelope (NR12), subpattern, highmask
    (0x08, 0x80, 0x83),   # 1 lead: 50% pulse, volume 8, slow decay
    (0x08, 0x40, 0x73),   # 2 soft lead: 25% pulse, volume 7, slow decay
    (0x08, 0x80, 0xA1),   # 3 plink: 50% pulse, volume 10, fast decay (short jingle notes)
    (0x08, 0x00, 0xC1),   # 4 thin: 12.5% pulse, volume 12, fast decay (quick bonus-round notes)
    (0x08, 0x80, 0x85),   # 5 song lead: 50% pulse, volume 8, slow decay (long notes keep sounding)
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


def rows_for(channel, text, default_inst, tempo, legacy=True, gap=True, stac_all=None):
    """Expand a token string into a list of (note, inst, effect) rows.

    legacy: the jingles' original staccato rule (kept so they sound as before).  Otherwise a note is
    cut with the Exx effect on the row where the cut falls (hUGEDriver counts ticks from the start
    of a row, so a cut can only act inside its own row): a staccato note ('!') is cut after 3/4 of
    its length, and a note that is followed by a rest or by the same pitch again is cut one frame
    before its end (the 1-frame gap that makes repeated notes articulate and rests silent).
    stac_all=(num, den): on channel 2 every note is cut after num/den of its length instead.  A '~:n' token
    ties (see merge_ties)."""
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
        for k, (row, n, name, stac) in enumerate(notes):
            if name is None:
                continue
            nxt = notes[k + 1][2] if k + 1 < len(notes) else "wrap"
            ticks = n * tempo
            if stac:
                cut = (ticks * stac_all[0]) // stac_all[1] if stac_all and channel == 2 else (ticks * 3) // 4
            elif gap and (nxt is None or nxt == name):
                cut = ticks - 1
            else:
                continue
            cut = max(cut, 1)
            r, t = row + cut // tempo, cut % tempo
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

# BONUS: original tarantella-flavoured 6/8 loop in A minor, one row per eighth note.  Tempo 5.
tune("bonus", 5, 1,
     ch2=" ".join([
         "E5:1 A5:1 C6:1 B5:1 A5:1 E5:1", "F5:1 A5:1 D6:1 C6:1 A5:1 F5:1",
         "E5:1 G5:1 C6:1 B5:1 G5:1 E5:1", "A5:3 E5:3",
         "C6:1 E6:1 A6:1 G6:1 E6:1 C6:1", "D6:1 F6:1 A6:1 G6:1 F6:1 D6:1",
         "E6:1 D6:1 C6:1 B5:1 A5:1 G5:1", "A5:3 r:3"]),
     ch3=bass([("A3", "E4"), ("D3", "A3"), ("C3", "G3"), ("A3", "E4"),
               ("A3", "E4"), ("D3", "A3"), ("E3", "B3"), ("A3", "E4")], 6),
     ch4=" ".join(["k:1 h:1 h:1 k:1 h:1 h:1"] * 8))
# the bonus lead uses the thin pulse
TUNES["bonus"]["ch2"] = " ".join(t + "/4" if ":" in t and not t.startswith("r:") else t
                                 for t in TUNES["bonus"]["ch2"].split())



# ---- tune table: the order is music.h's TUNE_* enum ----------------------------------------------
JINGLES = {"clear": TUNES["clear"], "over": TUNES["over"], "bonus": TUNES["bonus"]}
ORDER = ["title", "clear", "over", "bonus", "show"] + [f"venue{i}" for i in range(9)]
SOURCE = {"title": "entertainer", "show": "galop"}
SOURCE.update({f"venue{i}": n for i, n in enumerate(songs.VENUES)})
BLOB_BANKS = (3,)
BUF_ID = {"A": 1, "B": 2}


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
        2: rows_for(2, t["ch2"], inst, tempo, legacy, gap, t.get("stac_all")),
        3: rows_for(3, t["ch3"], 1, tempo, legacy, gap),
        4: rows_for(4, t["ch4"], 1, tempo, legacy) if t["ch4"] else [],
    }
    total = max(len(v) for v in chans.values())
    chans = {c: v + [(REST, 0, 0)] * (total - len(v)) for c, v in chans.items()}
    chans[1] = [(REST, 0, 0)] * total
    n_orders = (total + 63) // 64
    if total % 64:      # a pattern break on the last row ends the final pattern early
        for c in ((2, 3, 4, 1) if not legacy else (1,)):
            note, ins, eff = chans[c][total - 1]
            if eff == 0:
                chans[c][total - 1] = (note, ins, 0xD00)
                break
        else:
            raise SystemExit(f"{name}: no channel has a free effect column on its last row")
    per = {c: list(chunks_of(chans[c], n_orders)) for c in (1, 2, 3, 4)}
    return dict(total=total, tempo=tempo, n_orders=n_orders, per=per)


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
    for name in ORDER:
        if name in JINGLES:
            built[name] = build(name, JINGLES[name], True)
        else:
            built[name] = build(name, songs.SONGS[SOURCE[name]], False)

    # buffered tunes: assign pattern slots (in first-use order, per song) and pack the blobs
    slots = {}        # tune -> {key: slot}
    for name in ORDER:
        if name in JINGLES:
            continue
        sl = {}
        for c in (1, 2, 3, 4):
            for key in built[name]["per"][c]:
                if key != EMPTY and key not in sl:
                    sl[key] = len(sl)
        slots[name] = sl
    max_a = max(len(sl) for n, sl in slots.items() if songs.SONGS[SOURCE[n]]["buf"] == "A")
    max_b = max(len(sl) for n, sl in slots.items() if songs.SONGS[SOURCE[n]]["buf"] == "B")

    # blobs -> banks (first fit, in tune order)
    bank_of, used = {}, {b: 0 for b in BLOB_BANKS}
    for name in slots:
        size = len(slots[name]) * SLOT_BYTES
        for b in BLOB_BANKS:
            if used[b] + size <= 15500:
                bank_of[name] = b
                used[b] += size
                break
        else:
            raise SystemExit("blobs do not fit banks %s" % (BLOB_BANKS,))
    for b in BLOB_BANKS:
        with open(out / f"music_pat{b}.c", "w") as f:
            f.write("// Generated by tools/gen_music.py from tools/songs.py. Do not edit.\n// Pattern blobs: copied into WRAM by src/music.c.\n")
            f.write(f"#pragma bank {b}\n#include \"hUGEDriver.h\"\n\n")
            for name in slots:
                if bank_of[name] != b:
                    continue
                f.write(f"const unsigned char blob_{name}[] = {{   // {SOURCE[name]}: {len(slots[name])} patterns\n")
                for key in slots[name]:
                    f.write(row_text(key))
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
        for name in ORDER:
            if name in JINGLES:
                continue
            t = songs.SONGS[SOURCE[name]]
            g = groove_rows(name, t)
            if g:
                assert built[name]["total"] % len(g) == 0, f"{name}: {built[name]['total']} rows is not a whole number of {len(g)}-row grooves"
                assert len(g) < 256 and t["tempo"] < 256
                grooves[name] = g
                f.write(f"static const unsigned char groove_{name}[] = {{{len(g)}, {t['tempo']}, "
                        + ", ".join(str(x) for x in g) + "};\n")
        f.write("\n")
        for name in slots:
            f.write(f"extern const unsigned char blob_{name}[];\n")
        f.write("\n")
        for name in ORDER:
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
                orders = {c: [("empty_pat" if key == EMPTY else f"&{buf}[{slots[name][key] * SLOT_BYTES}]")
                              for key in b["per"][c]] for c in (1, 2, 3, 4)}
            f.write(f"static const unsigned char {name}_order_cnt = {b['n_orders'] * 2};\n")
            for c in (1, 2, 3, 4):
                f.write(f"static const unsigned char * const {name}_order{c}[] = {{{', '.join(orders[c])}}};\n")
            f.write(f"static const hUGESong_t song_{name} = {{{b['tempo']}, &{name}_order_cnt, "
                    f"(const unsigned char **){name}_order1, (const unsigned char **){name}_order2, "
                    f"(const unsigned char **){name}_order3, (const unsigned char **){name}_order4, "
                    f"duty_inst, wave_inst, noise_inst, NULL, waves}};\n\n")
        f.write("// song, loop, frames per pass, buffer (0 none, 1 A, 2 B), bank / source / bytes of the pattern blob, groove (or NULL)\n")
        f.write("const tune_t tunes[TUNE_COUNT] = {\n")
        for name in ORDER:
            b = built[name]
            frames = b["total"] * b["tempo"]
            loop = JINGLES[name]["loop"] if name in JINGLES else 1
            if name in JINGLES:
                tail = "0, 0, NULL, 0"
            else:
                tail = "{}, {}, blob_{}, {}".format(BUF_ID[songs.SONGS[SOURCE[name]]["buf"]], bank_of[name], name,
                                                    len(slots[name]) * SLOT_BYTES)
            tail += ", " + (f"groove_{name}" if name in grooves else "NULL")
            f.write(f"    {{&song_{name}, {loop}, {frames}, {tail}}},   // {name}"
                    f"{' = ' + SOURCE[name] if name in SOURCE else ''}: {b['total']} rows\n")
        f.write("};\n")
    for name in ORDER:
        b = built[name]
        extra = f", blob {len(slots[name])} patterns in bank {bank_of[name]}" if name in slots else ""
        print(f"gen_music: {name}{'=' + SOURCE[name] if name in SOURCE else ''}: {b['total']} rows x {b['tempo']} frames "
              f"= {b['total'] * b['tempo'] / 60:.1f}s, {b['n_orders']} orders{extra}")
    print(f"gen_music: WRAM buffers: A {max_a} patterns ({max_a * SLOT_BYTES} B), B {max_b} ({max_b * SLOT_BYTES} B); "
          f"blob bytes per bank {used}")
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
