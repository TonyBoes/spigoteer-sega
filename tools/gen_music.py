#!/usr/bin/env python3
"""Tune sources -> build/music_data.c (hUGEDriver song data, C format).

All tunes here are written for this project.  No tracker GUI is involved: each tune is a few
lines of text per channel.  A token is NOTE:ROWS (rows are 16th/8th notes depending on the
tune's tempo), 'r:ROWS' is a rest, a trailing '!' makes the note staccato (note cut), and
'/N' picks instrument N for that note.  Channel 1 is never used by the music (sound
effects own it); channel 4 is percussion (k = kick, s = snare, h = hat).

Usage: gen_music.py OUTDIR
"""
import re
import sys
from pathlib import Path

SEMI = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
REST = 90          # ___ in hUGEDriver.h

# ---- instruments (indexes are 1-based in the pattern data) -------------------------------------
DUTY = [  # sweep, len_duty (NR11), envelope (NR12), subpattern, highmask
    (0x08, 0x80, 0xA3),   # 1 lead: 50% pulse, volume 10, slow decay
    (0x08, 0x40, 0x93),   # 2 soft lead: 25% pulse, volume 9, slow decay
    (0x08, 0x80, 0xC1),   # 3 plink: 50% pulse, volume 12, fast decay (short jingle notes)
    (0x08, 0x00, 0x91),   # 4 thin: 12.5% pulse, fast decay (quick bonus-round notes)
]
WAVE = [  # length, volume (NR32: 0x20 = 100%, 0x40 = 50%), waveform index, subpattern, highmask
    (0, 0x40, 0),         # 1 bass: triangle at 50%
    (0, 0x20, 1),         # 2 hollow bass: pulse-ish wave at 100%
]
NOISE = [  # envelope (NR42), subpattern, highmask+length
    (0x81, 0x00),         # 1 kick  (vol 8, fast decay)
    (0x61, 0x00),         # 2 snare (vol 6, fast decay)
    (0x31, 0x80),         # 3 hat   (vol 3, fast decay, 7-bit LFSR = metallic)
]
NOISE_NOTE = {"k": (12, 1), "s": (44, 2), "h": (60, 3)}      # noise note number sets the pitch
WAVES = [
    # 0 triangle
    [0x01, 0x23, 0x45, 0x67, 0x89, 0xAB, 0xCD, 0xEF, 0xFE, 0xDC, 0xBA, 0x98, 0x76, 0x54, 0x32, 0x10],
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


def rows_for(channel, text, default_inst, tempo):
    """Expand a token string into a list of (note, inst, effect) rows."""
    out = []
    for tok in text.split():
        stac = tok.endswith("!")
        tok = tok.rstrip("!")
        inst = default_inst
        if "/" in tok:
            tok, i = tok.split("/")
            inst = int(i)
        name, n = tok.split(":")
        n = int(n)
        assert n >= 1, tok
        if name == "r":
            out += [(REST, 0, 0)] * n
            continue
        if channel == 4:
            note, inst = NOISE_NOTE[name]
            eff = 0
        else:
            note = note_no(name)
            eff = 0xE00 | max(1, (n * tempo * 3) // 5) if stac else 0
        out.append((note, inst, eff))
        out += [(REST, 0, 0)] * (n - 1)
    return out


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


# TITLE: the verse of "Oh! Susanna" (Stephen Foster, 1848, public domain), entered from memory;
# the arrangement (bass line, rhythm, instruments) is ours.  Tempo 7 frames per 16th row.
tune("title", 7, 1,
     ch2=" ".join([
         "C5:2 D5:2 E5:2 G5:2", "G5:3 A5:1 G5:2 E5:2", "C5:2 D5:2 E5:2 E5:2", "D5:6 r:2",
         "C5:2 D5:2 E5:2 G5:2", "G5:3 A5:1 G5:2 E5:2", "C5:2 D5:2 E5:2 D5:2", "C5:6 r:2"]),
     ch3=bass([("C3", "G3"), ("C3", "G3"), ("G3", "D4"), ("G3", "D4"),
               ("C3", "G3"), ("C3", "G3"), ("G3", "D4"), ("C3", "G3")]),
     ch4="")

# IN-GAME: original saloon-style 2/4 tune in C, A part (bars 1-8) and B part (bars 9-16).
tune("game", 7, 1,
     ch2=" ".join([
         "E5:2 G5:2 C6:2 G5:2", "A5:2 G5:2 E5:4", "D5:2 F5:2 A5:2 F5:2", "G5:6 r:2",
         "E5:2 G5:2 C6:2 E6:2", "D6:2 C6:2 A5:4", "G5:2 A5:2 G5:2 F5:2", "E5:4 C5:4",
         "A5:2 A5:2 C6:2 A5:2", "G5:2 G5:2 B5:2 G5:2", "F5:2 F5:2 A5:2 F5:2", "E5:2 G5:2 E5:4",
         "A5:2 C6:2 E6:2 C6:2", "B5:2 G5:2 D6:4", "C6:2 B5:2 A5:2 G5:2", "G5:4 r:4"]),
     ch3=bass([("C3", "G3"), ("C3", "G3"), ("D3", "A3"), ("G3", "D4"),
               ("C3", "G3"), ("F3", "C4"), ("G3", "D4"), ("C3", "G3"),
               ("A3", "E4"), ("G3", "D4"), ("F3", "C4"), ("C3", "G3"),
               ("A3", "E4"), ("G3", "D4"), ("F3", "C4"), ("G3", "D4")]),
     ch4=" ".join(["k:1 r:1 h:2 s:1 r:1 h:2"] * 16))

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
ORDER = ["title", "game", "clear", "over", "bonus"]


def build(name, t):
    tempo = t["tempo"]
    chans = {
        2: rows_for(2, t["ch2"], 1, tempo),
        3: rows_for(3, t["ch3"], 1, tempo),
        4: rows_for(4, t["ch4"], 1, tempo) if t["ch4"] else [],
    }
    total = max(len(v) for v in chans.values())
    chans = {c: v + [(REST, 0, 0)] * (total - len(v)) for c, v in chans.items()}
    chans[1] = [(REST, 0, 0)] * total
    n_orders = (total + 63) // 64
    last = total - 64 * (n_orders - 1)
    if last < 64:        # pattern break on the unused channel 1 ends the final pattern early
        row = chans[1]
        row[total - 1] = (REST, 0, 0xD00)
    pats = {}
    orders = {c: [] for c in (1, 2, 3, 4)}
    cname = []
    for c in (1, 2, 3, 4):
        for o in range(n_orders):
            chunk = chans[c][o * 64:(o + 1) * 64]
            chunk = chunk + [(REST, 0, 0)] * (64 - len(chunk))
            key = tuple(chunk)
            if key not in pats:
                pats[key] = f"{name}_p{len(pats)}"
            orders[c].append(pats[key])
    return dict(total=total, tempo=tempo, pats=pats, orders=orders, n_orders=n_orders)


def emit_song(f, name, t):
    b = build(name, t)
    for key, pname in b["pats"].items():
        f.write(f"static const unsigned char {pname}[] = {{\n")
        for i in range(0, 64, 4):
            f.write("    " + " ".join(
                "DN({},{},0x{:03X}),".format("___" if n == REST else n, ins, eff) for n, ins, eff in key[i:i + 4]) + "\n")
        f.write("};\n")
    f.write(f"static const unsigned char {name}_order_cnt = {b['n_orders'] * 2};\n")
    for c in (1, 2, 3, 4):
        f.write(f"static const unsigned char * const {name}_order{c}[] = {{{', '.join(b['orders'][c])}}};\n")
    f.write(f"static const hUGEDutyInstr_t {name}_duty[] = {{\n")
    for sw, ld, env in DUTY:
        f.write(f"    {{{sw},{ld},{env},0,128}},\n")
    f.write("};\n")
    f.write(f"static const hUGEWaveInstr_t {name}_wave[] = {{\n")
    for ln, vol, wv in WAVE:
        f.write(f"    {{{ln},{vol},{wv},0,128}},\n")
    f.write("};\n")
    f.write(f"static const hUGENoiseInstr_t {name}_noise[] = {{\n")
    for env, hm in NOISE:
        f.write(f"    {{{env},0,{hm},0,0}},\n")
    f.write("};\n")
    f.write(f"const hUGESong_t song_{name} = {{{b['tempo']}, &{name}_order_cnt, "
            f"(const unsigned char **){name}_order1, (const unsigned char **){name}_order2, "
            f"(const unsigned char **){name}_order3, (const unsigned char **){name}_order4, "
            f"{name}_duty, {name}_wave, {name}_noise, NULL, waves}};\n\n")
    return b


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "music_data.c", "w") as f:
        f.write("// Generated by tools/gen_music.py from the tune sources there. Do not edit.\n")
        f.write("#pragma bank 2\n#include <stddef.h>\n#include \"hUGEDriver.h\"\n#include \"music.h\"\n\n")
        f.write("static const unsigned char waves[] = {\n")
        for w in WAVES:
            f.write("    " + ",".join(str(x) for x in w) + ",\n")
        f.write("};\n\n")
        info = []
        for name in ORDER:
            info.append(emit_song(f, name, TUNES[name]))
        f.write("const tune_t tunes[TUNE_COUNT] = {\n")
        for name, b in zip(ORDER, info):
            frames = b["total"] * b["tempo"]
            f.write(f"    {{&song_{name}, {TUNES[name]['loop']}, {frames}}},   // {name}: {b['total']} rows\n")
        f.write("};\n")
    for name, b in zip(ORDER, [build(n, TUNES[n]) for n in ORDER]):
        print(f"gen_music: {name}: {b['total']} rows x {b['tempo']} frames = {b['total'] * b['tempo'] / 60:.1f}s, "
              f"{b['n_orders']} orders, {len(b['pats'])} patterns")


if __name__ == "__main__":
    main()
