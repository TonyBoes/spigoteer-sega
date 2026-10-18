"""Arranging helpers for the channel-1 harmony lines (music step 5; songs.harmony).  Imported by songs.py.

The lines are ours, written from each tune's own melody and chords (the *_CHORDS lists in songs.py, from the score
sources named there): every harmony note is a tone of the tune's key or of the bar's chord, chosen against the melody
so that it sits a third, sixth, fourth or fifth below it (or a chord tone between the melody and the bass), with no
second, seventh or tritone against a melody note held on a beat, and moves to the nearest such note (smooth voice
leading).  Three textures:
  follow(): a voice under the melody in its rhythm, one note per beat at most (thirds and sixths below);
  guide():  one sustained chord tone per chord or bar (the third or the seventh first), a slow counter-line;
  stabs():  short chord tones on the off-beats (an accompaniment figure).
Each returns tokens for its bars; songs.py strings sections together.  check() verifies a finished line."""
import re

NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
SEMI = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
QUAL = {"": (0, 4, 7), "m": (0, 3, 7), "7": (0, 4, 7, 10), "dim7": (0, 3, 6, 9), "m7": (0, 3, 7, 10)}
ROLE = {0: "1", 3: "3", 4: "3", 6: "5", 7: "5", 9: "7", 10: "7"}
SCALES = {
    "C": (0, 2, 4, 5, 7, 9, 11), "G": (7, 9, 11, 0, 2, 4, 6), "D": (2, 4, 6, 7, 9, 11, 1), "F": (5, 7, 9, 10, 0, 2, 4),
    "Bm": (11, 1, 2, 4, 6, 7, 9, 10),        # B harmonic minor (A#) with the natural A
    "Ddor": (2, 4, 5, 7, 9, 11, 0),          # D Dorian
    "Asak": (9, 11, 0, 4, 5),                # Sakura's miyako-bushi scale
}
def harsh(m, p, chord):
    """Does harmony note p grate against melody note m over the chord?  A minor second / major seventh always; a major
    second / minor seventh within an octave (a ninth or seventh further apart is mild); a tritone unless both notes
    are tones of the chord (the third and seventh of a dominant seventh)."""
    iv = (m - p) % 12
    if iv in (1, 11):
        return True
    if iv in (2, 10):
        return abs(m - p) < 12
    if iv == 6:
        return not (m % 12 in chord and p % 12 in chord)
    return False


def midi(name):
    m = re.fullmatch(r"([A-G])([#b]?)(-?\d)", name)
    return 12 * (int(m.group(3)) + 1) + SEMI[m.group(1)] + {"#": 1, "b": -1, "": 0}[m.group(2)]


def name_of(m):
    return f"{NAMES[m % 12]}{m // 12 - 1}"


def chord_pcs(c):
    m = re.fullmatch(r"([A-G][#b]?)(.*)", c)
    root = midi(m.group(1) + "4") % 12
    return {(root + i) % 12: ROLE[i] for i in QUAL[m.group(2)]}


def timeline(text):
    """Melody tokens -> [(start row, rows, midi or None)] (ties folded, '!' and '/N' dropped)."""
    out, row = [], 0
    for tok in text.split():
        tok = tok.rstrip("!").split("/")[0]
        nm, n = tok.split(":")
        n = int(n)
        if nm == "~":
            s, ln, p = out[-1]
            out[-1] = (s, ln + n, p)
        else:
            out.append((row, n, None if nm in ("r", "R") else midi(nm)))
        row += n
    return out


def per_row(tl):
    rows = []
    for s, n, p in tl:
        rows += [p] * n
    return rows


def chord_rows(chords, bar_rows):
    out = []
    for c in chords:
        if "/" in c:
            a, b = c.split("/")
            out += [a] * (bar_rows // 2) + [b] * (bar_rows - bar_rows // 2)
        else:
            out += [c] * bar_rows
    return out


class Tune:
    """A melody (songs' ch2 text), its chords (one per bar, 'X/Y' = two halves), rows per bar and per beat, the key."""

    def __init__(self, mel, chords, bar_rows, beat, key, strict=False):
        self.tl = timeline(mel)
        self.mel = per_row(self.tl)
        self.onsets = {s for s, n, p in self.tl if p is not None}
        self.chords = chord_rows(chords, bar_rows)
        assert len(self.chords) == len(self.mel), (len(self.chords), len(self.mel))
        self.bar, self.beat, self.scale = bar_rows, beat, set(SCALES[key])
        self.strict = strict           # only the scale's notes (Sakura: its E chord has no G#)

    def pcs(self, row):
        pcs = chord_pcs(self.chords[row])
        return {k: v for k, v in pcs.items() if k in self.scale} if self.strict else pcs

    def allowed(self, row):
        return self.scale | set(self.pcs(row))

    def clash(self, cand, a, b):
        """Penalty for a harmony note `cand` held over rows a..b-1 against the melody: a second, seventh or tritone
        against a melody note that sounds on a beat (or starts with the harmony) costs much, a passing one little;
        the melody's own pitch (a unison or octave) costs too."""
        pen = 0
        for r in range(a, b):
            p = self.mel[r]
            if p is None:
                continue
            iv = (p - cand) % 12
            strong = r == a or r % self.beat == 0
            if harsh(p, cand, self.pcs(r)):
                pen += 100 if strong else 3
            elif iv == 0:
                pen += 8 if strong else 1
        return pen


def _pick(t, cands, a, b, prev, rank):
    best = None
    for c in cands:
        score = rank(c) + t.clash(c, a, b) + (abs(c - prev) * 0.6 if prev is not None else 0)
        if best is None or score < best[0]:
            best = (score, c)
    return best


def follow(t, bars, lo, hi, prefer=(3, 4, 8, 9, 5, 7), grid=None, min_rows=None, merge=True, inst=""):
    """A voice under the melody over bars (first, last), 1-based: a new note where a melody note starts on the grid
    (default: a beat) or where the chord changes, held at least min_rows (default: the grid); the melody's rests are
    rests.  merge: a note that repeats the last one is held instead of struck again."""
    grid = grid or t.beat
    min_rows = min_rows or grid
    a0, a1 = (bars[0] - 1) * t.bar, bars[1] * t.bar
    lo, hi = midi(lo), midi(hi)
    cuts = [a0]
    for r in range(a0 + 1, a1):
        on_beat = r % grid == 0
        new_note = r in t.onsets and on_beat
        rest_starts = t.mel[r] is None and t.mel[r - 1] is not None and on_beat
        rest_ends = t.mel[r] is not None and t.mel[r - 1] is None
        chord = t.chords[r] != t.chords[r - 1]
        if (new_note or rest_starts or rest_ends or chord) and r - cuts[-1] >= min_rows:
            cuts.append(r)
    cuts.append(a1)
    out, prev = [], None
    for a, b in zip(cuts, cuts[1:]):
        m = t.mel[a] if t.mel[a] is not None else next((p for p in t.mel[a:b] if p is not None), None)
        if m is None:
            out.append((b - a, None))
            continue
        pcs = t.pcs(a)
        ok = t.allowed(a)
        cands = [c for c in range(lo, hi + 1) if c % 12 in ok and (m - c) in prefer]
        if not cands:                    # the melody dips below the line's range: a chord tone in the range
            cands = [c for c in range(lo, hi + 1) if c % 12 in pcs]
        rank = lambda c: prefer.index(m - c) * 2 + (0 if c % 12 in pcs else 10) if (m - c) in prefer else 30
        _, c = _pick(t, cands, a, b, prev, rank)
        if merge and out and out[-1][1] == c:
            out[-1] = (out[-1][0] + b - a, c)
        else:
            out.append((b - a, c))
        prev = c
    return tokens(out, inst)


def guide(t, bars, lo, hi, per_bar=False, pattern=None, roles="37513", below=True, inst=""):
    """A slow line of chord tones over bars (first, last): one note per chord (per bar if per_bar), the third or
    seventh first, each the nearest such tone to the last, below the melody (unless below=False: a low melody gets a
    line above it).  pattern: rows of each bar as [(rows, sound?)] (e.g. a
    waltz's [(2, False), (4, True)]: silent on the downbeat, held over beats 2 and 3)."""
    a0, a1 = (bars[0] - 1) * t.bar, bars[1] * t.bar
    lo, hi = midi(lo), midi(hi)
    cuts = [a0]
    for r in range(a0 + 1, a1):
        if (t.chords[r] != t.chords[r - 1] and not per_bar) or r % t.bar == 0:
            cuts.append(r)
    cuts.append(a1)
    out, prev = [], None
    for a, b in zip(cuts, cuts[1:]):
        pcs = t.pcs(a)
        cands = [c for c in range(lo, hi + 1) if c % 12 in pcs]
        rank = lambda c: roles.index(pcs[c % 12]) * 3 if pcs[c % 12] in roles else 12
        # the note must sit below the melody it accompanies (or the melody rests)
        top = [p for p in t.mel[a:b] if p is not None]
        if top and below:
            cands = [c for c in cands if c < min(top)] or cands
        _, c = _pick(t, cands, a, b, prev, rank)
        prev = c
        if pattern and b - a == t.bar:
            for n, snd in pattern:
                out.append((n, c if snd else None))
        else:
            out.append((b - a, c))
    return tokens(out, inst)


def stabs(t, bars, lo, hi, pattern, inst=""):
    """Short chord tones over bars (first, last) on the pattern's sounding slots (per bar: [(rows, sound?)]), each
    the chord tone nearest the last one that does not clash with the melody."""
    out, prev = [], None
    lo, hi = midi(lo), midi(hi)
    for bar in range(bars[0] - 1, bars[1]):
        r = bar * t.bar
        for n, snd in pattern:
            if not snd:
                out.append((n, None))
            else:
                pcs = t.pcs(r)
                cands = [c for c in range(lo, hi + 1) if c % 12 in pcs]
                top = [p for p in t.mel[r:r + n] if p is not None]
                if top:
                    cands = [c for c in cands if c < min(top)] or cands
                _, c = _pick(t, cands, r, r + n, prev, lambda c: 0)
                out.append((n, c))
                prev = c
            r += n
    return tokens(out, inst)


def tokens(evs, inst=""):
    return " ".join(f"r:{n}" if p is None else f"{name_of(p)}:{n}{inst}" for n, p in evs)


def check(t, ch1):
    """Problems of a finished harmony line against the tune: a note out of key and chord, a second / seventh /
    tritone against a melody note held on a beat, a long unison with the melody, a note above the melody's."""
    probs = []
    for s, n, p in timeline(ch1):
        if p is None:
            continue
        if p % 12 not in t.allowed(s):
            probs.append(f"row {s}: {name_of(p)} is neither in the key nor in the chord {t.chords[s]}")
        for r in range(s, s + n):
            m = t.mel[r]
            if m is not None and (r == s or r % t.beat == 0) and harsh(m, p, t.pcs(r)) and (r in t.onsets or r == s):
                probs.append(f"row {r}: {name_of(p)} against the melody's {name_of(m)}")
        uni = sum(1 for r in range(s, s + n) if t.mel[r] == p)
        if uni > 2 * t.beat:
            probs.append(f"row {s}: {name_of(p)} doubles the melody for {uni} rows")
    return probs


# ---- arranging helpers for the pro arrangements (music batch 1 on: songs.py builds the bass, drum and harmony lines from bars) ----
def merge_ties(text):
    """'~:n' holds the previous note n more rows (the same fold as gen_music.merge_ties; the specs write rests as R)."""
    toks = []
    for tok in text.split():
        if tok.startswith("R:"):
            tok = "r" + tok[1:]
        if tok.startswith("~:"):
            m = re.fullmatch(r"([^:]+):(\d+)(.*)", toks[-1])
            assert m and m.group(1) != "r", f"tie after {toks[-1]}"
            toks[-1] = f"{m.group(1)}:{int(m.group(2)) + int(tok[2:])}{m.group(3)}"
        else:
            toks.append(tok)
    return " ".join(toks)


def nrows(text):
    return sum(int(t.split(":")[1].rstrip("!").split("/")[0]) for t in merge_ties(text).split())


def expand(bars, refs):
    """bars: a list of token strings where an int refers to an earlier bar (1-based); `refs` bars in all."""
    out = []
    for b in bars:
        out.append(out[b - 1] if isinstance(b, int) else b)
    assert len(out) == refs, (len(out), refs)
    return out


def patch_bars(text, rows, edits):
    """A token string with the bars in `edits` ({bar 1-based: tokens of `rows` rows}) replaced; a note of the original
    that crosses into or out of an edited bar is cut at the bar line, every other token boundary is kept."""
    ev = []                                   # per row: (pitch name or None, starts here?)
    for tok in merge_ties(text).split():
        nm, n = tok.split(":")
        n = int(n.rstrip("!").split("/")[0])
        suf = tok[len(nm) + 1 + len(str(n)):]
        ev += [(nm + suf, k == 0) for k in range(n)]
    for bar, toks in edits.items():
        assert nrows(toks) == rows, (bar, toks)
        r0 = (bar - 1) * rows
        new = []
        for tok in toks.split():
            nm, n = tok.split(":")
            n = int(n.rstrip("!").split("/")[0])
            suf = tok[len(nm) + 1 + len(str(n)):]
            new += [(nm + suf, k == 0) for k in range(n)]
        ev[r0:r0 + rows] = new
        if r0 + rows < len(ev):
            ev[r0 + rows] = (ev[r0 + rows][0], True)
    out = []
    for nm, start in ev:
        if start or not out or out[-1][0] != nm:
            out.append([nm, 1])
        else:
            out[-1][1] += 1
    return " ".join(f"{nm}:{n}" if "/" not in nm else f"{nm.split('/')[0]}:{n}/{nm.split('/')[1]}" for nm, n in out)


def transpose(text, octaves):
    out = []
    for tok in text.split():
        nm, rest = tok.split(":", 1)
        if nm not in ("r", "R", "~"):
            nm = nm[:-1] + str(int(nm[-1]) + octaves)
        out.append(f"{nm}:{rest}")
    return " ".join(out)


def bars_of(text, first, last, bar_rows=8):
    """Bars first..last (1-based) of a token string; no note may cross the cut (asserted)."""
    a, b = (first - 1) * bar_rows, last * bar_rows
    out, row = [], 0
    for tok in merge_ties(text).split():
        n = int(tok.split(":")[1].rstrip("!").split("/")[0])
        if a <= row and row + n <= b:
            out.append(tok)
        else:
            assert row + n <= a or row >= b, (first, last, tok, row)
        row += n
    assert nrows(" ".join(out)) == b - a
    return " ".join(out)


def bass_check(bass, chords, bar_rows):
    """The bass line against the chords: every note is a chord tone of its bar's chord, or a short note (1-2 rows) that steps
    (1-2 semitones) into the next bass note, or a short note on the last rows before a chord change that is a chord tone of the
    next chord (an anticipation: the "E into A", "D C B into G" leads).  The line wraps (the last note leads into the first).
    Returns (problems, anticipations)."""
    tl = [(s, n, p) for s, n, p in timeline(bass) if p is not None]
    crow = chord_rows(chords, bar_rows)
    probs, antic = [], []
    for i, (s, n, p) in enumerate(tl):
        if p % 12 in chord_pcs(crow[s]):
            continue
        ns, nn, np_ = tl[(i + 1) % len(tl)]
        if n <= 2 and 1 <= abs(np_ - p) <= 2:
            continue
        if n <= 2 and p % 12 in chord_pcs(crow[ns]) and crow[ns] != crow[s]:
            antic.append(f"bar {s // bar_rows + 1}: {name_of(p)} ({crow[s]}) anticipates {crow[ns]}, then {name_of(np_)}")
            continue
        probs.append(f"bar {s // bar_rows + 1} row {s}: {name_of(p)} is not in {crow[s]} and does not step into {name_of(np_)}")
    return probs, antic
