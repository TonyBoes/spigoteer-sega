"""Song sources for the buffered tunes (title, show, ten venue tunes).  Imported by gen_music.py.

All tunes are public domain compositions.  Galop infernal and the tunes entered from docs/music_specs.md follow the
owner's note lists (Drunken Sailor: our transcription of the owner's pick; rhythms checked against scores where one was
found, music step 3); Oh! Susanna's notes are the owner's list in the rhythm of Foster's score; the arrangement (accompaniment, rhythm, instruments) is ours.  Notation: see gen_music.py.  One song row is one
unit note (an eighth note unless the comment says sixteenth); `tempo` is frames per row (60 fps).
The melody is channel 2 (pulse), the bass channel 3 (wave), the percussion channel 4 (noise);
channel 1 is shared: a quieter harmony line (harmony(), music step 5) that steps aside whenever a sound effect needs it.  Upper-case K S H are the quiet drum kit (kick, snare,
hat); lower-case k s h are the louder old kit the bonus tune uses.
"""

import harmony as H   # noqa: E402  (tools/harmony.py: the channel-1 harmony lines' helpers)

# chord -> (root, fifth) played by the bass (a seventh chord uses its triad's notes)
CHORD = {
    "C": ("C3", "G3"), "F": ("F2", "C3"), "G": ("G2", "D3"), "D": ("D3", "A3"),
    "Am": ("A2", "E3"), "Dm": ("D3", "A3"), "Em": ("E3", "B3"), "E": ("E3", "B3"),
    "Bm": ("B2", "F#3"), "A": ("A2", "E3"), "Bb": ("A#2", "F3"), "Eb": ("D#3", "A#3"),
    "F#": ("F#2", "C#3"), "C#7": ("C#3", "G#3"), "F#dim7": ("F#2", "C3"),
    "C7": ("C3", "G3"), "A7": ("A2", "E3"), "D7": ("D3", "A3"), "E7": ("E3", "B3"), "G7": ("G2", "D3"),
}


def oompah(chords, rows):
    """root / fifth bass, staccato.  rows per bar: 4 = 2/4 boom-chick, 6 = 3/4 oom-pah-pah,
    8 = 4/4 or 2/4 with sixteenth rows, 16 = 4/4 with sixteenth rows, 'c6' = 6/8 (two dotted beats)."""
    out = []
    for c in chords:
        if "/" in c:                       # two chords in one bar ("C/D7"): the root of each on its half
            a, b = c.split("/")
            h = {"c6": 3, 4: 2, 16: 8}.get(rows, 4)           # half a bar
            out += [f"{CHORD[a][0]}:{h}!", f"{CHORD[b][0]}:{h}!"]
            continue
        r, f = CHORD[c]
        if rows == 4:
            out += [f"{r}:2!", f"{f}:2!"]
        elif rows == 6:
            out += [f"{r}:2!", f"{f}:2!", f"{f}:2!"]
        elif rows in (8, 16):
            q = rows // 4
            out += [f"{r}:{q}!", f"{f}:{q}!", f"{r}:{q}!", f"{f}:{q}!"]
        elif rows == "c6":
            out += [f"{r}:3!", f"{f}:3!"]
        else:
            raise ValueError(rows)
    return " ".join(out)


def rep(text, n):
    return " ".join([text] * n)


def with_inst(text, inst):
    """Every note token without an instrument gets /inst (rests, '~' ties and tokens that have one are untouched; a staccato '!' stays last)."""
    out = []
    for tok in text.split():
        if tok.startswith(("r:", "R:", "~:")) or "/" in tok:
            out.append(tok)
        else:
            nm, n = tok.split(":")
            out.append(f"{nm}:{n.rstrip('!')}/{inst}{'!' if n.endswith('!') else ''}")
    return " ".join(out)


SONGS = {}
DUTY_RING, LEAD_PRO, LEGATO_LEAD = 5, 6, 7   # gen_music.DUTY: the credits ring, the brass lead, its held-volume twin for the sung tunes (gen_music asserts)
BASS_HELD = 2         # gen_music.WAVE: the bass without its pluck table (the default bass, 1, is plucked)
SUNG_ARTIC = 3       # frames of silence between two sung notes of the same pitch (legato=)


def song(name, tempo, bufname, ch2, ch3, ch4="", inst=LEAD_PRO, gap=True, stac_all=None, groove="", legato=None, start=0, swing=0, tempo_map=None, fx_map=None,
         short_orders=()):
    """stac_all: (num, den) cuts every melody note after num/den of its length (staccato).
    legato: n frames.  A sung tune: the melody plays on the legato lead (gen_music instrument 6, a held volume
    instead of the song lead's decay, which made every note a plucked syllable), each note runs into the next, and a
    repeated pitch is cut n frames early so the new syllable is still heard.  Rests stay rests.
    groove: a short drum loop (tokens as ch4, one or two bars) that src/music.c plays on channel 4 by itself,
    over and over, in step with the song's rows.  It costs no pattern in the WRAM buffer (a 64-row pattern is
    not a whole number of 3/4 or 6/8 bars, so a shared hUGEDriver pattern could not keep the beat across orders).
    The song's length must be a whole number of grooves (gen_music checks).
    start: the row the FIRST play begins on (a pickup: the song's loop still wraps to row 0, so every later pass
    starts at bar 1).  src/music.c jumps the driver there before its first tick; tunes with a start have no groove
    or harmony (gen_music checks).
    swing: bit n set = the rows with (row mod 8) == n are one frame shorter than `tempo` (a groove tune only: the mask
    takes the place of the tempo byte in the groove's header, which src/music.c reads; 0 = none, a mask is over 15).
    0xAA: rows of 9, 8, 9, 8 frames = 105.9 bpm at tempo 9 for the Entertainer.
    tempo_map: {row: frames a row from that row on} (hUGE Fxx, put on a free effect column of that row; gen_music counts the
    tune's frames with it).  fx_map: {row: [(channel, hUGE effect word)]} (a channel's own effect, e.g. 0xC50 wave volume).
    short_orders: order numbers (in the tune's hUGE order list) that play only their first 32 rows: the melody and bass text has no rows for
    the other 32; gen_music pads them with rests and puts a pattern break on row 31 (the streamed title: its intro and bridge are 4 bars)."""
    if legato:
        inst = LEGATO_LEAD
    SONGS[name] = dict(tempo=tempo, buf=bufname, ch2=ch2, ch3=ch3, ch4=ch4, inst=inst, gap=gap, stac_all=stac_all,
                       groove=groove, legato=legato, start=start, swing=swing, tempo_map=tempo_map, fx_map=fx_map, ch1="", ch1_inst=None,
                       short_orders=tuple(short_orders))


def harmony(name, tune, ch1, inst=("harm", "harm")):
    """Music step 5: the tune's channel-1 harmony line (tokens as the melody: NOTE:ROWS, r:ROWS, ~:ROWS ties, '/2' picks
    the second instrument), as long as the tune.  tune: its harmony.Tune (melody, chords, key: tests/test_harmony.py
    checks the line against it).  inst: two names from gen_music.HARM_INST (instrument A, B).  src/music.c plays the
    line itself (harm_tick), not hUGEDriver, and gives the channel to a sound effect whenever one needs it."""
    SONGS[name].update(ch1=ch1, ch1_inst=tuple(inst), harm_tune=tune)


# GAME TEMPO.  The owner approved these tempos for the game (sakura 150 with the lively arrangement, approved
# 2026-10-11; it was 120) (the melody notes stay exactly as the spec's; only the
# speed changes), in beats per minute of the beat the spec names; the spec's own tempo is in docs/music_specs.md and
# SPEC_BPM_ROWS in tests/test_sound.py.  tempo = frames per row is the nearest whole number (60 fps), so the tempo
# the game really plays is 3600 / (tempo x rows per beat): entertainer 9 and 8 alternating (swing 0xAA) -> 105.9, sakura 12 -> 150,
# funicula 10 and 9 alternating (swing 0xAA) -> 126.3 (dotted quarter), skaters / danube / ballgame 9 -> 200 (quarter).  Tunes not listed play
# at the spec tempo.  mountain 4 -> 225 spec-quarters (music step 6: 3.88 frames per row is the MIDI's 116 MIDI-quarters of 8 rows;
# 4 plays 112.5 of them, 5 would play 90, 6 played 75 and was too slow, the owner said; MTN_TEMPO).
GAME_BPM = {"entertainer": 106, "sakura": 150, "funicula": 126, "skaters": 192, "danube": 192, "ballgame": 192,
            "mountain": 225}


# ---------------------------------------------------------------------------------------------
# "Oh! Susanna" (Stephen Foster, 1848), the cowboys' tune.  Key C, 2/4, one row = a sixteenth note (8 rows a bar),
# 8 frames per row = quarter 112.5 (the score's MM 114; the owner's list played 15 frames per eighth = 120).  Melody
# C4 = middle C.  Rhythm checked bar by bar (music step 3, 2026-10-11) against Craig Sapp's Humdrum encoding of the
# song (github.com/humdrum-tools/foster-songs, kern/fostr20.krn, from the "Stephen Foster Song Book", Dover, pp. 89-91;
# in G there, transposed to C here; the Wikifonia lead sheet in github.com/00sapo/OpenEWLD agrees on the chorus and the
# pickups; the encoding's repository has no licence file, the song itself is public domain and only its rhythm was
# read).  The owner's list had every note an even eighth; the song has sixteenth pickups ("I come", "I'm gwine"),
# a dotted eighth and a sixteenth in bars 2, 6, 10, 14 and 22 (C. D, "with my ban-jo") and 5 and 13 (G. A,
# "Lou'-si-an-a"), and the chorus "Oh! Su-san-na, oh" is two quarters, then eighth, quarter, eighth
# ("san-na, oh" bunched together, the owner's note; the third A, "oh", was missing from the owner's list).  Bar 16 ends the verse as the score does, a quarter and a quarter
# rest before "Oh!" (it was a held half note).  Seamless loop: the tune starts on bar 1 and its last bar (the score's
# C4 and a rest) is the C, C D turnaround of bar 8, whose sixteenth pickup leads every pass into bar 1 (no first-time
# pickup, as in the other tunes).  24 bars = 192 rows = three whole 64-row orders.
A1 = "E4:2 G4:2 G4:2 A4:2  G4:2 E4:2 C4:3 D4:1  E4:2 E4:2 D4:2 C4:2  D4:6 C4:1 D4:1"
A2 = "E4:2 G4:2 G4:3 A4:1  G4:2 E4:2 C4:3 D4:1  E4:2 E4:2 D4:2 D4:2  C4:6 C4:1 D4:1"
A2_LAST = "E4:2 G4:2 G4:3 A4:1  G4:2 E4:2 C4:3 D4:1  E4:2 E4:2 D4:2 D4:2  C4:4 r:4"
CHORUS = "F4:4 F4:4  A4:2 A4:4 A4:2  G4:2 G4:2 E4:2 C4:2  D4:6 C4:1 D4:1"
ENDING = "E4:2 G4:2 G4:2 A4:2  G4:2 E4:2 C4:3 D4:1  E4:2 E4:2 D4:2 D4:2  C4:6 C4:1 D4:1"   # (score: C4:4 r:4)
SUS_MEL = "  ".join([A1, A2, A1, A2_LAST, CHORUS, ENDING])
SUS_CH = (["C", "C", "C", "G"] + ["C", "C", "G", "C"]) * 2 + ["F", "C", "C", "G"] + ["C", "C", "G", "C"]
# Music batch 1 (owner-approved 2026-10-17, docs/proarr/BATCH_1.md on branch promusic): the arrangement is ours, the melody unchanged.
# Bass (plucked, BASS_PRO: a banjo song's thumb; the walking eighths are full plucks, the beat notes die before the next, which
# grooves with the kit): root on 1, fifth or third on 2, a walk at every chord change (C B A into G, D B into C, D E into the
# chorus's F, B into C), the verse ending C G B into the next verse.
SUS_BASS = " ".join(H.expand([
    "C3:4 G2:4", "C3:4 E3:4", "C3:4 B2:2 A2:2", "G2:4 D3:2 B2:2",      # 1-4   C C C G
    1, "C3:4 E3:2 D3:2", "G2:4 B2:2 D3:2", "C3:4 G2:2 B2:2",          # 5-8   C C G C
    1, 2, 3, 4,                                                       # 9-12
    1, 6, 7, "C3:4 D3:2 E3:2",                                        # 13-16 (16: the walk into the chorus's F)
    "F3:4 C3:2 B2:2", 1, 3, 4,                                        # 17-20 F C C G
    1, 6, 7, 8,                                                       # 21-24 C C G C (24 walks into bar 1)
], 24))
# Drums (a pattern: fills cost nothing): verse kick, hat, snare, hat; a snare double at the end of every first four-bar phrase, a
# snare-snare tom-tom roll at the end of every eighth bar (into the second verse, into the chorus, into the next pass).  Every
# 8-bar order has the same drum pattern: one pattern, so the tune keeps 7 in the WRAM buffer.
SUS_DRUMS = " ".join(H.expand([
    "b:2 t:2 n:2 t:2", 1, 1, "b:2 t:2 n:2 n:1 n:1",                    # 1-4
    1, 1, 1, "b:2 t:2 n:1 n:1 m:1 m:1",                               # 5-8
    1, 1, 1, 4,                                                       # 9-12
    1, 1, 1, 8,                                                       # 13-16 (the roll into the chorus)
    1, 1, 1, 4,                                                       # 17-20 chorus
    1, 1, 1, 8,                                                       # 21-24 (the roll into the next pass)
], 24))
song("susanna", 8, "A", SUS_MEL, SUS_BASS, SUS_DRUMS, legato=SUNG_ARTIC)
# Harmony (music step 5): a second voice in thirds and sixths under the verses (one note an eighth at most, held where it
# repeats), a slow counter-line of chord tones under the chorus ("Oh! Su-san-na"), on the held 12.5% pad like a second
# singer.  Batch 1: under the held "comes" D (bars 4, 12, 20) and the verse-ending C (8, 24) the voice moves, and the chorus
# gets a counter-line of its own under "Oh! Su-san-na, oh".
_t = H.Tune(SUS_MEL, SUS_CH, 8, 4, "C")
SUS_HARM_BARS = {
    4: "B3:4 A3:2 G3:2", 12: "B3:4 A3:2 G3:2", 20: "B3:4 A3:2 G3:2",
    8: "G3:2 E3:2 G3:4", 24: "G3:2 E3:2 G3:4",
    17: "A3:4 C4:2 D4:2",          # under F F: A, C, D (F chord, D of the key)
    18: "E4:2 C4:2 D4:2 E4:2",     # under the repeated A: E C D E
    19: "E4:2 D4:2 C4:2 G3:2",     # under G G E C: a line stepping down
}
SUS_HARM = H.patch_bars(" ".join([H.follow(_t, (1, 16), "G3", "A4", grid=2), H.guide(_t, (17, 20), "G3", "E4"),
                                  H.follow(_t, (21, 24), "G3", "A4", grid=2)]), 8, SUS_HARM_BARS)
harmony("susanna", _t, SUS_HARM, ("pad", "pad"))
SUS_HARM_CHECK = H.check(_t, SUS_HARM)


# ---------------------------------------------------------------------------------------------
# The tunes below are the melody specs (docs/music_specs.md), entered token for token: one
# list entry per bar, "NOTE:ROWS", R = rest, ~ = tie (the previous note held on), the chord of each bar
# in the *_CHORDS list.  The arrangement (bass style, drums, instruments) is ours.  tests/test_sound.py
# parses the spec and compares these lists with it.
#
# Pickups: some specs end the last bar with the pickup of the next pass (Funiculi, Mountain, Entertainer)
# and mark the pickup line "first time only".  The driver always loops from row 0, so the first-time pickup
# is left out: the tune starts on bar 1 and every loop is seamless.
#
# Bass (channel 3, real pitch names; gen_music adds the wave channel's octave correction): waltz 3/4 =
# root, fifth, fifth; 6/8 = root and fifth on the dotted beats; 4/4 and 2/4 = boom-chick.  Tunes whose
# 64-row orders fill the six-pattern WRAM buffer have no room for drum patterns: their drums are a `groove`
# that src/music.c plays by itself (see song()).

# ---------------------------------------------------------------------------------------------
# Title: "The Entertainer" (Scott Joplin, 1902), A and B sections.  2/4, one row = a sixteenth note; quarter = 90
# is 10 frames per row (game tempo: rows of 9 and 8 frames alternating, 106 bpm, see GAME_BPM; the owner chose "1b at
# 106 bpm" on 2026-10-12: thirds harmony, harmony at 50% duty, the melody an octave lower, a slight swing).  32 bars: the A section (bars 1-16, bars 4 and 8
# end with the D D# pickup) with its second ending (bar 16: C, then E F F# up into the B section), the B section
# (bars 17-32, owner request 2026-10-11: "the next section before it loops back") with its second ending (bar 32: the
# held C, then the D D# pickup back into bar 1).
# (ENT_BARS is written one octave below the score and the spec: C5 here is the spec's C6; the owner's choice.)
# Checked note by note against the score: Mutopia Project "The Entertainer" (ftp/JoplinS/entertainer/entertainer.ly,
# Mutopia-2016/11/25-263, typeset by Chris Sawer, overhauled by Simon Albrecht; source "Reproduction of original
# edition (1902)"; licence: Public Domain), the A section's first ending (score bars 5-20).  The melody is the lower
# note of the right hand's octaves.  Fixed 2026-10-11: from bar 2 on the old list ran one sixteenth early (the held C
# is 6 sixteenths, the run C D D# starts on the 6th sixteenth of bar 2 and E lands on bar 3's downbeat), bars 6-7 are
# A G | F# A C E-E D C A (not A G F# A | C E D C A D), and bars 12-16 (the low-confidence end) are the score's
# C | E C D E-E C D C (twice) | E C D E-E B D | C.  Chords from the score's left hand: bars 2, 6 and 10 are F then C/E
# (F/C here; bar 6 was D7).  The B section (score bars 22-36 and the second ending, bar 38) is the top note of the right
# hand as written (its single notes continue the octaves' top line: G A G, E C G | A B C D E D C D); chords from
# the left hand (bar 19 F then F minor: F; bars 20 and 28 have E in the bass: C; bar 23 G over D then D7: D7; bar 29 F
# then F#dim7).
ENT_BARS = [
    "E4:1 C5:2 E4:1 C5:2 E4:1 C5:1", "~:5 C5:1 D5:1 D#5:1", "E5:1 C5:1 D5:1 E5:2 B4:1 D5:2",
    "C5:6 D4:1 D#4:1", "E4:1 C5:2 E4:1 C5:2 E4:1 C5:1", "~:6 A4:1 G4:1",
    "F#4:1 A4:1 C5:1 E5:2 D5:1 C5:1 A4:1", "D5:6 D4:1 D#4:1", "E4:1 C5:2 E4:1 C5:2 E4:1 C5:1",
    "~:5 C5:1 D5:1 D#5:1", "E5:1 C5:1 D5:1 E5:2 B4:1 D5:2", "C5:6 C5:1 D5:1",
    "E5:1 C5:1 D5:1 E5:2 C5:1 D5:1 C5:1", "E5:1 C5:1 D5:1 E5:2 C5:1 D5:1 C5:1",
    "E5:1 C5:1 D5:1 E5:2 B4:1 D5:2", "C5:5 E4:1 F4:1 F#4:1",
    # B section
    "G4:2 A4:1 G4:2 E4:1 F4:1 F#4:1", "G4:2 A4:1 G4:2 E4:1 C4:1 G3:1", "A3:1 B3:1 C4:1 D4:1 E4:1 D4:1 C4:1 D4:1",
    "G3:1 E4:1 F4:1 G4:1 A4:1 G4:1 E4:1 F4:1", "G4:2 A4:1 G4:2 E4:1 F4:1 F#4:1", "G4:2 A4:1 G4:2 G4:1 A4:1 A#4:1",
    "B4:1 B4:2 B4:2 A4:1 F#4:1 D4:1", "G4:5 E4:1 F4:1 F#4:1",
    "G4:2 A4:1 G4:2 E4:1 F4:1 F#4:1", "G4:2 A4:1 G4:2 E4:1 C4:1 G3:1", "A3:1 B3:1 C4:1 D4:1 E4:1 D4:1 C4:1 D4:1",
    "C4:5 G3:1 F#3:1 G3:1", "C4:2 A3:1 C4:2 A3:1 C4:1 A3:1", "G3:1 C4:1 E4:1 G4:2 E4:1 C4:1 G3:1",
    "A3:2 C4:2 E4:1 D4:2 C4:1", "~:6 D4:1 D#4:1",
]
ENT_CHORDS = [
    "C", "F/C", "G7", "C", "C", "F/C", "D7", "G7", "C", "F/C", "G7", "C", "C", "F", "G7", "C",
    "C", "C", "F", "C", "C", "C", "D7", "G7", "C", "C", "F", "C", "F/F#dim7", "C", "D7/G7", "C",
]
# The title tune itself is defined after the credits tune's data (below): the whole Entertainer, looping, from these A and B bars.
# Harmony (the owner's "1b", 2026-10-12): a second voice in thirds and sixths under the whole tune, in the melody's own
# rhythm (grid 1: it moves on any sixteenth, the off-beat ragtime notes included; merge=False re-strikes a repeated note
# as the melody does), on the 50% "harm50" pulse (decaying like a piano's second hand).  C3-B4 keeps it under the melody.

# ---------------------------------------------------------------------------------------------
# Show: "Galop infernal" (Jacques Offenbach, Orphee aux enfers, 1858, the can-can), the owner's spec (docs/music_specs.md
# tune 10): key D, 2/4, quarter = 160 -> 11 frames per eighth row (163.6 bpm).  16 bars = 64 rows = one 64-row pattern per
# channel (buffer B holds 2 patterns), a pass is 704 frames (11.7 s).  The quarter notes of bars 3, 5, 11 and 13 are
# detached ('!').  Bass, harmony, drums: the arrangement below the melody (it replaced the oom-pah, the stabs and the groove).
# Confirmed (music step 4, 2026-10-12) by the owner-supplied transcription of the chorus statement in the vocal score
# "Orpheus in der Unterwelt" (IMSLP #26815, plate 10779; G major there, a fifth up here): every note and rhythm.  Seamless
# loop: the spec's last bar D5:2 R:2 left a hole before bar 1's D5; its rest is an A4 pickup, which is exactly the score's
# first ending (G4 quarter, then the D4 quarter pickup into the repeat).  The score's first-time pickup (a quarter rest
# and that D4) is not added: the driver loops from row 0, so a pickup before bar 1 would also play on every pass after
# bar 16's, two A4 pickups in a row.
GAL = ["D5:4", "E5:1 G5:1 F#5:1 E5:1", "A5:2! A5:2!", "A5:1 B5:1 F#5:1 G5:1",
       "E5:2! E5:2!", "E5:1 G5:1 F#5:1 E5:1", "D5:1 D6:1 C#6:1 B5:1", "A5:1 G5:1 F#5:1 E5:1",
       "D5:4", "E5:1 G5:1 F#5:1 E5:1", "A5:2! A5:2!", "A5:1 B5:1 F#5:1 G5:1",
       "E5:2! E5:2!", "E5:1 G5:1 F#5:1 E5:1", "D5:1 A5:1 E5:1 F#5:1", "D5:2 A4:2"]
GAL_CHORDS = ["D", "A7", "D", "D", "A7", "A7", "D", "A7", "D", "A7", "D", "D", "A7", "A7", "D/A7", "D"]
# The arrangement (owner-approved 2026-10-17, the "v2" audition of tools/promusic.py on branch promusic): the melody is GAL as
# above, on the brass lead (gen_music instrument 8: a 50 % -> 25 % duty attack and a delayed vibrato, from its table); the
# stabbed quarters are plain detached notes on it.  The bass (wave instrument 3: the full-amplitude wave, plucked 100/50/25 % by
# its table) walks under the held and stabbed bars and oom-pahs, with a two-note lead into the next chord, under the running ones.
# The harmony (channel 1, the "voice" 50 % pulse) is a counter-melody a third or a sixth under the running melody in its own
# rhythm, so that the pause mix's bass is joined by a line that still sounds like the can-can in the full mix.  The drums are a
# channel-4 pattern (the 192 B pattern of buffer B): kick, closed hat, snare, closed hat each bar; an open hat closes bar 8 and
# a snare double closes bar 16 into the loop (gen_music: b kick, t closed hat, n snare, o open hat).  v1's arpeggio chord stabs
# are not used; gen_music's "ARPEGGIO CHORD STABS" note says how to bring them back for another song.


def _gal_lead(tok):
    if tok.startswith("r:"):
        return tok
    return tok


GAL_MEL = " ".join(_gal_lead(t) for b in GAL for t in b.split())
GAL_BASS_BARS = [
    "D3:1 F#3:1 A3:1 F#3:1",     # 1  D held: walk up the chord and back
    "A2:2 E3:2",                 # 2  A7 run: oom-pah
    "D3:1 F#3:1 A3:1 A2:1",      # 3  D stabs: walk, the octave A lands on the next bar's D
    "D3:2 C#3:1 B2:1",           # 4  D run: oom, then C# B stepping down into A7
    "A2:1 C#3:1 E3:1 G3:1",      # 5  A7 stabs: the seventh chord, walking up
    "A2:2 E3:2",                 # 6  A7 run
    "D3:2 A2:2",                 # 7  D run (the melody's leap to D6)
    "A2:2 E3:1 C#3:1",           # 8  A7 run: E C# leading into bar 9's D
    "D3:1 F#3:1 A3:1 F#3:1",     # 9
    "A2:2 E3:2",                 # 10
    "D3:1 F#3:1 A3:1 A2:1",      # 11
    "D3:2 C#3:1 B2:1",           # 12
    "A2:1 C#3:1 E3:1 G3:1",      # 13
    "A2:2 E3:2",                 # 14
    "D3:1 F#3:1 A2:1 C#3:1",     # 15 D then A7: a half bar each
    "D3:2 A2:2",                 # 16 D, the A4 pickup over the fifth
]
GAL_BASS = " ".join(t for b in GAL_BASS_BARS for t in b.split())
GAL_HARM_BARS = [
    "F#4:2 A4:2",                # 1  under the held D5: third, then fifth
    "C#5:1 E5:1 D5:1 C#5:1",     # 2  thirds under E G F# E
    "F#4:2 F#4:2",               # 3  the stabs' lower note (D chord)
    "F#5:1 G5:1 D5:1 E5:1",      # 4  thirds under A B F# G
    "C#5:2 C#5:2",               # 5  stabs (A7)
    "C#5:1 E5:1 D5:1 C#5:1",     # 6
    "F#4:1 F#5:1 A5:1 G5:1",     # 7  sixth under D5, sixth under D6, thirds under C#6 B5
    "F#5:1 E5:1 D5:1 C#5:1",     # 8  thirds under A G F# E
    "F#4:2 A4:2",                # 9
    "C#5:1 E5:1 D5:1 C#5:1",     # 10
    "F#4:2 F#4:2",               # 11
    "F#5:1 G5:1 D5:1 E5:1",      # 12
    "C#5:2 C#5:2",               # 13
    "C#5:1 E5:1 D5:1 C#5:1",     # 14
    "F#4:1 F#5:1 C#5:1 D5:1",    # 15 under D5 A5 (D), E5 F#5 (A7)
    "A4:2 F#4:2",                # 16 a fourth under D5, a third under the A4 pickup
]
GAL_HARM = " ".join(GAL_HARM_BARS)
GAL_DRUMS = " ".join(["b:1 t:1 n:1 t:1"] * 7 + ["b:1 t:1 n:1 o:1"] + ["b:1 t:1 n:1 t:1"] * 7 + ["b:1 t:1 n:1 n:1"])
song("galop", 11, "B", GAL_MEL, GAL_BASS, GAL_DRUMS)
_t = H.Tune(" ".join(GAL), GAL_CHORDS, 4, 2, "D")
harmony("galop", _t, GAL_HARM, ("voice", "voice"))


# ---------------------------------------------------------------------------------------------
# Sports bar: "Take Me Out to the Ball Game" (Albert Von Tilzer, 1908), chorus.  3/4, key G, quarter = 168
# is 10.7 frames per eighth row: 11 (164 bpm; game tempo 9, see GAME_BPM).  32 bars.  Checked bar by bar (music step 4,
# 2026-10-12) against the owner-supplied transcription of the York Music Co. first edition (New York 1908, via the
# Library of Congress; in D there, a fourth up here in G): bars 1, 5 and 17 open with a half note (as here); bar 8 ends
# with a quarter rest (was held); bar 20 is A4 half + A4 quarter, "team, If" on one pitch (was A4 B4); bars 25-26,
# "one, two", are held dotted halves (were a quarter and a half-bar rest each).  Every other bar matched.
# Seamless loop: the score's last bar (G5, then rests) let the final G5 fade into a second of silence;
# it walks down the G chord (D5 B4) into bar 1's G4.
TMO_BARS = [
    "G4:4 G5:2", "E5:2 D5:2 B4:2", "D5:6", "A4:6", "G4:4 G5:2", "E5:2 D5:2 B4:2", "D5:6", "~:4 R:2",
    "E5:2 D#5:2 E5:2", "B4:2 C5:2 D5:2", "E5:4 C5:2", "A4:6", "E5:4 E5:2", "E5:2 F#5:2 G5:2",
    "A5:2 F#5:2 E5:2", "D5:2 B4:2 A4:2", "G4:4 G5:2", "E5:2 D5:2 B4:2", "D5:6", "A4:4 A4:2",
    "G4:4 A4:2", "B4:2 C5:2 D5:2", "E5:6", "~:2 E5:2 F#5:2", "G5:6", "G5:6",
    "G5:2 F#5:2 E5:2", "D5:2 C#5:2 D5:2", "E5:6", "F#5:6", "G5:6", "~:2 D5:2 B4:2",
]
TMO_CHORDS = [
    "G", "Em", "D7", "D7", "G", "Em", "D", "D", "E7", "E7", "Am", "Am", "A7", "A7", "D", "D", "G",
    "Em", "D7", "D7", "G", "G7", "C", "C", "C", "A7", "D", "E7", "Am", "D7", "G", "G",
]
# Music batch 1 (owner-approved 2026-10-17, docs/proarr/BATCH_1.md): a waltz bass with a line: the root on 1, two chord tones on 2
# and 3 that rise or fall toward the next bar's root, the descending D C B into G (bars 4, 16, 20, 30), a chromatic D D# into E7
# (8, 27), B C into D (6, 18), E D C into C and the like.
TMO_BASS = " ".join(H.expand([
    "G2:2 B2:2 D3:2", "E3:2 B2:2 G3:2", "D3:2 F#3:2 A3:2", "D3:2 C3:2 B2:2",     # 1-4   G Em D7 D7
    1, "E3:2 B2:2 C3:2", "D3:2 A2:2 F#3:2", "D3:2 A2:2 D3:1 D#3:1",            # 5-8   G Em D D
    "E3:2 G#3:2 B2:2", 9, "A2:2 E3:2 C3:2", "A2:2 C3:2 E3:2",                  # 9-12  E7 E7 Am Am
    "A2:2 E3:2 G3:2", "A2:2 C#3:2 E3:2", 7, 4,                                 # 13-16 A7 A7 D D
    1, 6, 3, 4,                                                                # 17-20 G Em D7 D7
    1, "G2:2 F3:2 D3:2", "C3:2 E3:2 G3:2", "C3:2 G2:2 E3:2",                   # 21-24 G G7 C C
    "C3:2 E3:2 C3:1 B2:1", 14, 8, 9,                                           # 25-28 C A7 D E7
    11, 4, 1, "G2:2 D3:2 F#2:2",                                               # 29-32 Am D7 G G (32 leads into bar 1)
], 32))
# Drums: a 4-bar groove (24 rows): kick on 1, snare on 2, rim on 3, closed hats between; bar 4 ends with a snare on 3 and an open hat.
TMO_GROOVE = " ".join(["b:1 t:1 n:1 t:1 x:1 t:1"] * 3 + ["b:1 t:1 n:1 t:1 n:1 o:1"])
song("ballgame", 9, "A", " ".join(TMO_BARS), TMO_BASS, groove=TMO_GROOVE)
# Harmony (music step 5): bars 1-16 a moving inner voice on the pad under the long notes (it held one tone a chord before batch 1),
# bars 17-32 a voice in thirds and sixths under "let me root, root, root", one note for each melody eighth (grid 1, no merging).
# Owner's pick (harmony demos, 2026-10-12): held, then thirds.
_t = H.Tune(" ".join(TMO_BARS), TMO_CHORDS, 6, 2, "G")
TMO_HARM_1_16 = [
    "D4:4 B4:2", "G4:2 B4:2 G4:2", "F#4:2 A4:2 B4:2", "F#4:2 E4:2 C4:2",
    "D4:4 B4:2", "G4:2 B4:2 G4:2", "F#4:2 A4:2 B4:2", "A4:2 F#4:2 r:2",
    "G#4:2 B4:2 G#4:2", "G#4:2 E4:2 B4:2", "C5:2 A4:2 E4:2", "E4:2 C4:2 E4:2",
    "C#5:2 A4:2 G4:2", "C#5:2 D5:2 E5:2", "F#5:2 D5:2 B4:2", "B4:2 G4:2 F#4:2",
]
TMO_HARM = " ".join(TMO_HARM_1_16) + " " + H.follow(_t, (17, 32), "D4", "D5", grid=1, merge=False, inst="/2")
harmony("ballgame", _t, TMO_HARM, ("pad", "harm"))
TMO_HARM_CHECK = H.check(_t, TMO_HARM)

# ---------------------------------------------------------------------------------------------
# Lumber lodge: "She'll Be Coming 'Round the Mountain" (American folk song).  4/4, key D, one row = a sixteenth
# note (16 rows a bar), MTN_TEMPO frames per row (music step 6: 4 = 112.5 MIDI-quarters of 8 rows, the source MIDI is
# 116; 5 = 90 is the slower variant, 6 = 75 was too slow; one-line change; GAME_BPM).  16 bars = 256 rows = four whole orders; bar 16 ends with the "she'll be" pickup of the next pass.
# Rhythm and pitches (music step 4, 2026-10-12): the first verse of the Harmonica track of Simon Horn's MIDI
# (2021, CC0, Wikimedia Commons), supplied by the owner 2026-10-12, in G there, transposed up a fifth to D here, one
# MIDI quarter note = 8 rows (the rows keep the grid and tempo of music step 3).  Every "com-ing round the" bar is
# X:2 X:6 X:6 X:2 (the snap), every "moun-tain when she" / "moun-tain, she'll be" bar is four even eighths
# (X:4 Y:4 Z:4 W:4), "comes" is a half note (D5:16 / E5:16) and then a rest (R:8) before the pickup.  This replaced the
# owner's listening-note rhythm (X:3 Y:5 Z:4 W:4 and a tied "comes"); the pitches are the same as before.
MTN_BARS = [
    "D5:2 D5:6 D5:6 D5:2", "B4:4 A4:4 F#4:4 A4:4", "D5:16", "R:8 D5:4 E5:4",
    "F#5:2 F#5:6 F#5:6 F#5:2", "A5:4 F#5:4 E5:4 D5:4", "E5:16", "R:8 A5:4 G5:4",
    "F#5:2 F#5:6 F#5:6 F#5:2", "E5:4 D5:4 D5:4 D5:4", "B4:2 B4:6 B4:6 B4:2", "E5:4 D5:4 C#5:4 B4:4",
    "A4:2 A4:6 A4:6 A4:2", "F#5:4 E5:4 B4:4 C#5:4", "D5:16", "R:8 A4:4 B4:4",
]
MTN_CHORDS = [
    "D", "A7", "D", "D", "D", "D", "A7", "A7", "D", "D7", "G", "A7", "D", "A7", "D", "D",
]
# The "She'll be" pickup is the last 8 rows of bar 16 (row 248): the FIRST play starts there (start=), the loop wraps to
# bar 1 as always.  (Rotating the tune instead cost a 9th WRAM pattern: the bass bars stop repeating.)
MTN_PICKUP_ROW = 248
MTN_TEMPO = 4
# Music batch 2 (owner-approved 2026-10-17, docs/proarr/BATCH_2.md and specs/mountain.md on branch promusic): the arrangement is ours, the melody
# unchanged.  Bass: a country two-beat in quarters with a walk at every change (C# B down into A7, C# up into D, B C# up into the next verse
# under the "she'll be" pickup, C B A down from D7 into G, G G# up into A7).  Bars 13-16 = 1-4, so order 4's bass is order 1's.
MTN_BASS = " ".join(H.expand([
    "D3:4 A2:4 D3:4 C#3:2 B2:2",       # 1  D -> A7
    "A2:4 E3:4 A2:4 C#3:4",            # 2  A7 -> D
    "D3:4 A2:4 F#3:4 A2:4",            # 3  D
    "D3:4 F#3:4 A2:4 B2:2 C#3:2",      # 4  D: the walk-up under the pickup
    3, 1,                              # 5, 6
    "A2:4 E3:4 C#3:4 E3:4",            # 7  A7
    2, 3,                              # 8, 9
    "D3:4 A2:4 C3:4 B2:2 A2:2",        # 10 D7 -> G
    "G2:4 D3:4 B2:4 G2:2 G#2:2",       # 11 G -> A7
    2,                                 # 12
    1, 2, 3, 4,                        # 13-16
], 16))
# Drums (a pattern, the same 4 bars in every order: one pattern): a train beat, kick 1 and 3, snare 2 and 4, hats on the "ands"; bar 4 of every
# order fills the melody's half-bar rest: snare snare tom tom snare, open hat.
MTN_DRUM_BAR = "b:2 t:2 n:2 t:2 b:2 t:2 n:2 t:2"
MTN_DRUM_FILL = "b:2 t:2 n:2 t:2 n:1 n:1 m:1 m:1 n:2 o:2"
MTN_DRUMS = " ".join([MTN_DRUM_BAR, MTN_DRUM_BAR, MTN_DRUM_BAR, MTN_DRUM_FILL] * 4)
song("mountain", MTN_TEMPO, "A", " ".join(MTN_BARS), MTN_BASS, MTN_DRUMS, legato=SUNG_ARTIC, start=MTN_PICKUP_ROW)
# Harmony (music step 6): the Susanna approach, a second voice in thirds and sixths under the whole verse in the melody's
# own rhythm (it moves where the melody does, the 2/6 snap included; grid 2 = an eighth or finer), on the held 12.5% pad.
# The pickup row is a note boundary of the line (gen_music asserts it), so the first play can start the line there.
_t = H.Tune(" ".join(MTN_BARS), MTN_CHORDS, 16, 4, "D")
# Batch 2: where the melody holds, the voice walks under it, and "toot toot" in the rests (bars 3-4, 7-8, 15-16).
MTN_HARM_BARS = {
    3: "F#4:4 A4:4 B4:4 A4:4",
    4: "D5:2 r:2 D5:2 r:2 F#4:4 A4:4",
    7: "C#5:4 A4:4 G4:4 A4:4",
    8: "E5:2 r:2 E5:2 r:2 C#5:4 E5:4",
    15: "F#4:4 A4:4 B4:4 A4:4",
    16: "D5:2 r:2 D5:2 r:2 F#4:8",
}
MTN_HARM = H.patch_bars(H.follow(_t, (1, 16), "A3", "F#5", grid=2), 16, MTN_HARM_BARS)
harmony("mountain", _t, MTN_HARM, ("pad", "pad"))
MTN_HARM_CHECK = H.check(_t, MTN_HARM)
MTN_BASS_CHECK = H.bass_check(MTN_BASS, MTN_CHORDS, 16)

# ---------------------------------------------------------------------------------------------
# Bistro: "Funiculi, Funicula" (Luigi Denza, 1880), verse and chorus.  6/8, key F, dotted quarter = 92 is
# 13 frames per eighth row.  25 bars; bars 9 and 25 end with the C5 pickup, so the loop is seamless.  Rhythm checked
# (music step 3, 2026-10-11) against the Wikifonia lead sheet "Funiculi funicula" in OpenEWLD (github.com/00sapo/OpenEWLD,
# public-domain scores): every bar has the same note onsets (the lead sheet writes some chorus notes as an eighth and a
# rest where ours hold, and has a bar's rest after bar 21), except the echo "and so do I" of bar 7, three even eighths
# there.  Settled (music step 4, 2026-10-12) by the owner-supplied transcription of Ricordi's first edition (Milan 1880,
# plate 47127, IMSLP #148203; in E-flat there, a tone up here): the echo is the long-short form every time, the "-do"
# held on by a tied eighth, an eighth rest, then "Tu sa-ie ad-" as eighth, quarter, eighth (bar 7 was a quarter rest
# and the same three notes).  Our 25 bars hold only this one echo (the later ones are in the omitted part of the verse).
FUN_BARS = [
    "F5:6", "~:2 F5:1 E5:2 E5:1", "C5:2 C5:1 D5:2 D5:1", "A4:3 A4:3", "~:2 A4:1 G4:2 F4:1", "F4:6",
    "~:1 R:1 A4:1 G4:2 F4:1", "F4:6", "~:1 R:4 C5:1", "E5:3 D5:1 R:2", "E5:3 D5:1 R:2",
    "F5:2 E5:1 D5:2 F5:1", "E5:3 R:3", "E5:3 D5:1 R:2", "E5:3 D5:1 R:2", "F5:2 E5:1 D5:2 F5:1",
    "C5:2 A4:1 A4:2 A4:1", "A4:2 A4:1 A4:2 A4:1", "A4:2 A4:1 A4:2 A4:1", "A4:2 A4:1 A4:2 A4:1",
    "F5:6", "G5:2 F5:1 D5:2 F5:1", "C5:2 A4:1 A4:2 Bb4:1", "C5:2 Bb4:1 A4:2 G4:1", "F4:3 R:2 C5:1",
]
FUN_CHORDS = [
    "F", "F", "F", "F", "C7", "F", "C7", "F", "F", "C7", "C7", "C7", "C7", "C7", "C7", "C7", "F",
    "A7", "Dm", "A7", "Dm", "Bb", "F", "C7", "F",
]
# Music batch 2 (specs/funicula.md): bass 6/8 oom-pah, root and a chord tone on the two dotted beats, the second ending with an eighth that
# leads into the next chord.
FUN_BASS = " ".join(H.expand([
    "F2:3 C3:3", "F2:3 A2:3", 1, "F2:3 A2:2 B2:1",                 # 1-4   F F F F->C7
    "C3:3 G2:2 E2:1", 4, 5, 1, 4,                                    # 5-9   C7 F C7 F F->C7
    "C3:3 G2:3", "C3:3 E3:3", "C3:3 A#2:3", 10, 11, 12, 5,           # 10-16 C7 (16 -> F)
    "F2:3 C3:2 G#2:1", "A2:3 E3:2 C#3:1", "D3:3 F3:2 E3:1", 18,      # 17-20 F A7 Dm A7
    "D3:3 A2:3", "A#2:3 F2:2 E2:1", 4, 5, 1,                         # 21-25 Dm Bb F C7 F
], 25))
# Drums (a groove): kick on each dotted beat, snare on the last eighth of each, hats between; five bars with the fill (three snares and an
# open hat) on the fifth (30 rows, 150 / 30 = 5 times a pass).  FUN_GROOVE_1BAR is the one-bar fallback (6 rows, no fill: 24 B less of bank 2).
FUN_DRUM_BAR = "b:1 t:1 n:1 b:1 t:1 n:1"
FUN_DRUM_FILL = "b:1 t:1 n:1 n:1 n:1 o:1"
FUN_GROOVE = " ".join([FUN_DRUM_BAR] * 4 + [FUN_DRUM_FILL])
FUN_GROOVE_1BAR = FUN_DRUM_BAR
song("funicula", 10, "A", " ".join(FUN_BARS), FUN_BASS, groove=FUN_GROOVE, swing=0xAA)
# Tempo (owner pick, harmony demos 2026-10-12): rows alternate 10 and 9 frames (swing 0xAA, as the Entertainer) = 9.5 on
# average = 126 bpm for the dotted quarter; a 6-row bar has the same long-short pattern every time.  Harmony unchanged.
# Harmony (music step 5): the verse in thirds and sixths under the melody, one note a dotted beat (the echoes "and so
# do I" answered in thirds, B-flat and C under D and E); the chorus ("Funiculi, funicula") a slow line of held chord
# tones under the repeated A, through the A7 / D minor turn (C#4 / D4).
_t = H.Tune(" ".join(FUN_BARS), FUN_CHORDS, 6, 3, "F")
# Batch 2: the chorus is a moving inner voice on the pad (/2), one note a dotted beat.
FUN_CHORUS_HARM = "F4:3/2 C4:3/2 C#4:3/2 E4:3/2 D4:3/2 F4:3/2 E4:3/2 C#4:3/2 A4:3/2 D4:3/2 D4:3/2 F4:3/2 A4:3/2 F4:3/2 G4:3/2 E4:3/2 C4:3/2 r:2 A4:1/2"
FUN_HARM = " ".join([H.follow(_t, (1, 16), "C4", "C5", grid=3), FUN_CHORUS_HARM])
harmony("funicula", _t, FUN_HARM, ("harm", "pad"))
FUN_HARM_CHECK = H.check(_t, FUN_HARM)
FUN_BASS_CHECK = H.bass_check(FUN_BASS, FUN_CHORDS, 6)

# ---------------------------------------------------------------------------------------------
# Arctic: "The Skaters' Waltz" (Emile Waldteufel, 1882), main theme, an octave above the source.  3/4, key G,
# quarter = 160: 11 frames per eighth row (about 164).  32 bars, no drums.  The spec's short slide up into
# bars 1, 5 and 9 is not done: hUGEDriver's portamento starts from a note already sounding, so it would
# need an extra row before each of those notes.  Checked (music step 4, 2026-10-12) against the owner-supplied
# transcription of Luck's Music Library full score (IMSLP #102459, violin 1 at letter A; A major there, here a tone
# down and an octave up): bars 1-14 (and 17-30) match.  The strain ends A3 dotted half | A3 quarter, then rests (bars
# 15-16 in G: G4:6 | G4:2 R:4); kept as ours: bars 15-16 run quarters into the repeat (the spec's ABC) and bars 31-32
# hold G4 and climb back, because the score's ending leaves two beats of silence after a held, decaying G4 (0.62 s,
# more than the 0.25 s tests/test_music_loops.py allows at the loop).  Seamless
# loop: the spec's last two bars held G4 for six beats, which faded out long before bar 1; the last bar now climbs
# A4 A#4 into bar 1's B4 (the chromatic approach stands in for the skater's slide).
SKT_BARS = [
    "B4:6", "D5:4 E5:2", "E5:6", "~:6", "C5:6", "E5:4 F#5:2", "F#5:6", "~:6", "A5:6", "G5:4 B4:2",
    "D5:6", "C5:4 B4:2", "B4:6", "A4:6", "G4:2 E5:2 D5:2", "C5:2 B4:2 A4:2", "B4:6", "D5:4 E5:2",
    "E5:6", "~:6", "C5:6", "E5:4 F#5:2", "F#5:6", "~:6", "A5:6", "G5:4 B4:2", "D5:6", "C5:4 B4:2",
    "B4:6", "A4:6", "G4:6", "~:2 A4:2 A#4:2",
]
SKT_CHORDS = [
    "G", "G", "D7", "D7", "D7", "D7", "G", "G", "Em", "Em", "Am", "Am", "D", "D7", "G", "D7", "G",
    "G", "D7", "D7", "D7", "D7", "G", "G", "Em", "Em", "Am", "Am", "D", "D7", "G", "G",
]
# Music batch 2 (specs/skaters.md): a Viennese waltz bass: the root on 1, two chord tones on 2 and 3 that lead into the next bar (D C B into
# G, C up into D, F# under into the loop's G).
SKT_BASS = " ".join(H.expand([
    "G2:2 B2:2 D3:2",          # 1  G
    "G2:2 B2:2 C3:2",          # 2  G -> D7
    "D3:2 F#3:2 A3:2",         # 3  D7
    "D3:2 A2:2 C3:2",          # 4  D7
    3,                         # 5
    "D3:2 C3:2 B2:2",          # 6  D7 -> G: D C B
    1, 1,                      # 7, 8 (8: D3 steps up to E3)
    "E3:2 G3:2 B2:2",          # 9  Em
    9,                         # 10 Em -> Am (B2 steps down to A2)
    "A2:2 C3:2 E3:2",          # 11 Am
    "A2:2 E3:2 C3:2",          # 12 Am -> D
    3, 6, 2, 6,                # 13-16 D D7 G D7
    1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14,   # 17-30 = 1-14
    1,                         # 31 G
    "G2:2 D3:2 F#2:2",         # 32 G: F# under into bar 1's G
], 32))
# Drums (a 4-bar groove, 24 rows): kick on 1, rim clicks on 2 and 3, closed hats between; the open hat ends every fourth bar.
SKT_DRUM_BAR = "b:1 t:1 x:1 t:1 x:1 t:1"
SKT_GROOVE = " ".join([SKT_DRUM_BAR] * 3 + ["b:1 t:1 x:1 t:1 x:1 o:1"])
song("skaters", 9, "A", " ".join(SKT_BARS), SKT_BASS, groove=SKT_GROOVE)
# Harmony (music step 5): the first strain holds one chord tone a bar on the pad (the waltz's sustained middle voice:
# B, then C, the seventh of D7, back to B), the repeat a voice in thirds and sixths under the melody, one note a beat.
_t = H.Tune(" ".join(SKT_BARS), SKT_CHORDS, 6, 2, "G")
# Batch 2: bars 1-16 a rocking inner voice on the pad under the held notes; 17-32 the thirds on "harm" (/2).
SKT_HARM_1_16 = [
    "D4:4 G4:2", "B4:4 C5:2", "C5:2 A4:2 C5:2", "A4:2 C5:2 A4:2",
    "A4:2 F#4:2 A4:2", "C5:4 A4:2", "D5:2 B4:2 D5:2", "B4:2 D5:2 B4:2",
    "E5:2 C5:2 E5:2", "E5:4 G4:2", "A4:2 F#4:2 A4:2", "A4:2 E4:2 G4:2",
    "F#4:2 D4:2 F#4:2", "F#4:2 C4:2 F#4:2", "D4:2 C5:2 B4:2", "A4:2 G4:2 F#4:2",
]
SKT_HARM = " ".join(SKT_HARM_1_16) + " " + H.follow(_t, (17, 32), "D4", "E5", grid=2, inst="/2")
harmony("skaters", _t, SKT_HARM, ("pad", "harm"))
SKT_HARM_CHECK = H.check(_t, SKT_HARM)
SKT_BASS_CHECK = H.bass_check(SKT_BASS, SKT_CHORDS, 6)

# ---------------------------------------------------------------------------------------------
# Robot factory: "In the Hall of the Mountain King" (Edvard Grieg, 1875).  4/4, key B minor, quarter = 120 =
# 15 frames per eighth row.  16 bars, every melody note staccato (cut after half its length), bass = a root
# ostinato in quarter notes: B in the A phrases, F# in the answer (bars 9-12).  Checked (music step 3, 2026-10-11)
# against the Mutopia Project's "In the Hall of the Mountain King" (ftp/GriegE/O46/Dans_l_antre_du_roi_de_la_montagne,
# Mutopia-2013/12/07-1888, typeset by Coyau from The University Society 1918 edition; public domain): bars 1-12 are
# the score's bars 2-13 note for note and in rhythm (staccato eighths, the quarter on beat 4, the half notes of bars 4,
# 8 and 12); bars 13-16 repeat the motif for the loop (Grieg's piece goes on with the answer an octave up).  Seamless loop: the last bar's staccato half note A4 left half
# a bar of silence; its second half is F#4 A#3, the leading tone rising into bar 1's B3.
HALL_BARS = [
    "B3:1 C#4:1 D4:1 E4:1 F#4:1 D4:1 F#4:2", "E#4:1 C#4:1 E#4:2 E4:1 C4:1 E4:2",
    "B3:1 C#4:1 D4:1 E4:1 F#4:1 D4:1 F#4:1 B4:1", "A4:1 F#4:1 D4:1 F#4:1 A4:4",
    "B3:1 C#4:1 D4:1 E4:1 F#4:1 D4:1 F#4:2", "E#4:1 C#4:1 E#4:2 E4:1 C4:1 E4:2",
    "B3:1 C#4:1 D4:1 E4:1 F#4:1 D4:1 F#4:1 B4:1", "A4:1 F#4:1 D4:1 F#4:1 A4:4",
    "F#4:1 G#4:1 A#4:1 B4:1 C#5:1 A#4:1 C#5:2", "D5:1 A#4:1 D5:2 C#5:1 A#4:1 C#5:2",
    "F#4:1 G#4:1 A#4:1 B4:1 C#5:1 A#4:1 C#5:2", "D5:1 A#4:1 D5:2 C#5:4",
    "B3:1 C#4:1 D4:1 E4:1 F#4:1 D4:1 F#4:2", "E#4:1 C#4:1 E#4:2 E4:1 C4:1 E4:2",
    "B3:1 C#4:1 D4:1 E4:1 F#4:1 D4:1 F#4:1 B4:1", "A4:1 F#4:1 D4:1 F#4:1 A4:2 F#4:1 A#3:1",
]
HALL_CHORDS = [
    "Bm", "C#7/C", "Bm", "D", "Bm", "C#7/C", "Bm", "D", "F#", "F#", "F#", "F#", "Bm", "C#7/C", "Bm",
    "D",
]
# Music batch 3 (owner-approved 2026-10-17, docs/proarr/BATCH_3.md and specs/hall.md on branch promusic): the arrangement is ours, melody and
# harmony unchanged.  Bass: THE THEME IN THE BASS (Grieg's cellos and basses): the melody an octave below in the A phrases, two octaves below
# in the F# answer (bars 9-12), row for row, plucked and cut (!).
HALL_BASS = " ".join(H.expand([
    "B2:1! C#3:1! D3:1! E3:1! F#3:1! D3:1! F#3:2!",              # 1
    "F3:1! C#3:1! F3:2! E3:1! C3:1! E3:2!",                       # 2 (E# = F)
    "B2:1! C#3:1! D3:1! E3:1! F#3:1! D3:1! F#3:1! B3:1!",        # 3
    "A3:1! F#3:1! D3:1! F#3:1! A3:4!",                            # 4
    1, 2, 3, 4,                                                   # 5-8
    "F#2:1! G#2:1! A#2:1! B2:1! C#3:1! A#2:1! C#3:2!",           # 9
    "D3:1! A#2:1! D3:2! C#3:1! A#2:1! C#3:2!",                   # 10
    9,                                                            # 11
    "D3:1! A#2:1! D3:2! C#3:4!",                                  # 12
    1, 2, 3,                                                      # 13-15
    "A3:1! F#3:1! D3:1! F#3:1! A3:2! F#3:1! A#2:1!",              # 16: A# the leading tone into bar 1's B2
], 16))
# Drums (one pattern: bars 9-16 = 1-8): a ticking machine, kick 1, snare 3, hats on 2 and 4, rims on the off-eighths; four snares close bar 4,
# snare snare tom tom snare and an open hat close bar 8.
HALL_DRUM_BAR = "b:1 x:1 t:1 x:1 n:1 x:1 t:1 x:1"
HALL_DRUMS = " ".join(H.expand([HALL_DRUM_BAR] * 3 + ["b:1 x:1 t:1 x:1 n:1 n:1 n:1 n:1"] + [HALL_DRUM_BAR] * 3 + ["b:1 x:1 n:1 n:1 m:1 m:1 n:1 o:1"]
                                + list(range(1, 9)), 16))
song("hall", 15, "A", " ".join(HALL_BARS), HALL_BASS, HALL_DRUMS, stac_all=(1, 2))
# Harmony (music step 5): a voice in thirds and sixths UNDER the melody the whole way (G3 to B4, never crossing, one note
# for each melody eighth, grid 1, no merging), a plucked "harm" voice.  The motif creeps down to B3 over the B2 bass, so
# the line sits right above the bass: dark and a little thick there.  Owner's pick (harmony demos, 2026-10-12): thirds.
_t = H.Tune(" ".join(HALL_BARS), HALL_CHORDS, 8, 2, "Bm")
harmony("hall", _t, H.follow(_t, (1, 16), "G3", "B4", grid=1, merge=False), ("harm", "harm"))
HALL_HARM_CHECK = H.check(_t, SONGS["hall"]["ch1"])
HALL_BASS_ONSETS = ([s for s, n, p in H.timeline(HALL_BASS) if p is not None]
                    == [s for s, n, p in H.timeline(SONGS["hall"]["ch2"]) if p is not None])      # the bass moves with the melody

# ---------------------------------------------------------------------------------------------
# Teahouse: "Sakura Sakura" (Japanese traditional).  4/4, key A minor (A B C E F), the spec's quarter = 72-100.
# Lively arrangement (owner: keep Sakura, make it livelier; the melody's notes are unchanged): game tempo 12 frames per
# eighth row = 150 bpm (was 15 = 120; GAME_BPM, owner-approved 2026-10-11), 14 bars = 22.4 s.  Every melody note
# is played detached (cut after 3/4 of its length) so the tune bounces; the bass is a syncopated pentatonic figure on
# each bar's chord (root, fifth and octave: A minor, D minor, and E without its G#, which is not in the scale) instead
# of the A / E drone; the drums are a two-bar taiko-like groove: "don . ka don don . ka ka" (kick and rim = the hat),
# the second bar ending with two snare hits.  Seamless loop (the only change to the notes): the last bar's rest
# (E4:4 R:4) is E4 C4 E4 (bar 5's figure), lifting into bar 1's A4.
# Bars 1-12 match the 1888 Ministry of Education koto collection (NDL pid 857651; owner-supplied transcription,
# music step 4); its bars 13-14 differ (rest, E4 F4 held | B4 A4 F4 E4 held), recorded in docs/music_specs.md as an
# option; the owner-approved arrangement is kept.
SAK_BARS = [
    "A4:2 A4:2 B4:4", "A4:2 A4:2 B4:4", "A4:2 B4:2 C5:2 B4:2", "A4:2 B4:1 A4:1 F4:4",
    "E4:2 C4:2 E4:2 F4:2", "E4:2 E4:1 C4:1 B3:4", "A4:2 B4:2 C5:2 B4:2", "A4:2 B4:1 A4:1 F4:4",
    "E4:2 C4:2 E4:2 F4:2", "E4:2 E4:1 C4:1 B3:4", "A4:2 A4:2 B4:4", "A4:2 A4:2 B4:4",
    "E4:2 F4:2 B4:1 A4:1 F4:2", "E4:4 C4:2 E4:2",
]
SAK_CHORDS = [
    "Am", "Am", "Am", "Dm", "Am", "E", "Am", "Dm", "Am", "E", "Am", "Am", "Dm", "Am",
]
SAK_BASS_NOTES = {"Am": ("A2", "E3", "A3"), "Dm": ("D2", "A2", "D3"), "E": ("E2", "B2", "E3")}


def sakura_bass(chords):
    """One bar of eighth rows per chord: root (quarter), fifth, octave, a rest, the root on the off-beat, the fifth."""
    out = []
    for c in chords:
        r, f, o = SAK_BASS_NOTES[c]
        out.append(f"{r}:2! {f}:1! {o}:1! r:1 {r}:1! {f}:2!")
    return " ".join(out)


# Music batch 3 (specs/sakura.md): the riff above with the scale's own falls at the changes (F E down into D, F down into E); length, tempo and
# loop unchanged (the Sumo counts music_frames, Taiko Pour silences the groove).  The groove is the taiko figure on the kit, kick = don, rim =
# ka; the second bar closes tom tom snare snare.
SAK_RIFF = {
    ("Am", "Am"): "A2:2! E3:1! A3:1! r:1 A2:1! E3:2!",
    ("Am", "Dm"): "A2:2! E3:1! A3:1! r:1 A2:1! F2:1! E2:1!",
    ("Am", "E"): "A2:2! E3:1! A3:1! r:1 A2:1! F2:2!",
    ("Dm", "Am"): "D2:2! A2:1! D3:1! r:1 D2:1! A2:2!",
    ("E", "Am"): "E2:2! B2:1! E3:1! r:1 E2:1! B2:2!",
}
SAK_BASS = " ".join(SAK_RIFF[(c, SAK_CHORDS[(i + 1) % 14])] for i, c in enumerate(SAK_CHORDS))
SAK_GROOVE = "b:1 r:1 x:1 b:1 b:1 r:1 x:1 x:1 b:1 r:1 x:1 b:1 m:1 m:1 n:1 n:1"
song("sakura", 12, "A", " ".join(SAK_BARS), SAK_BASS, "", gap=True, stac_all=(3, 4), groove=SAK_GROOVE)
# Harmony (music step 5): a koto's second string, a fourth or fifth under the melody (E under A, E under B), one plucked
# note per melody note on the beat, only the scale's notes (A B C E F: the E chord's G# is left out).
_t = H.Tune(" ".join(SAK_BARS), SAK_CHORDS, 8, 2, "Asak", strict=True)
# Batch 3: the second string is struck again under the held melody notes.
SAK_HARM_BARS = {
    1: "E4:2 E4:2 E4:2 E4:2", 2: "E4:2 E4:2 E4:2 E4:2", 11: "E4:2 E4:2 E4:2 E4:2", 12: "E4:2 E4:2 E4:2 E4:2",
    4: "F4:2 E4:2 A3:2 A3:2", 8: "F4:2 E4:2 A3:2 A3:2",
    6: "B3:2 B3:2 E3:2 E3:2", 10: "B3:2 B3:2 E3:2 E3:2",
    14: "A3:2 A3:2 A3:2 A3:2",
}
SAK_HARM = H.patch_bars(H.follow(_t, (1, 14), "E3", "A4", prefer=(5, 7, 3, 4, 8, 9), grid=2, merge=False), 8, SAK_HARM_BARS)
harmony("sakura", _t, SAK_HARM, ("pluck", "pluck"))
SAK_HARM_CHECK = H.check(_t, SAK_HARM)
SAK_BASS_CHECK = H.bass_check(SAK_BASS, SAK_CHORDS, 8)

# ---------------------------------------------------------------------------------------------
# Space lounge: "The Blue Danube" (Johann Strauss II, 1867, Op. 314), first waltz theme.  3/4, quarter = 160: 11
# frames per eighth row (game tempo 9, see GAME_BPM).  32 bars, no drums.  Checked note by note against the score:
# Mutopia Project "The Blue Danube Waltz (main theme)" (ftp/StraussJJ/O314/blue_danube/blue_danube.ly,
# Mutopia-2014/03/24-519, typeset by Nikos Kouremenos from Christian Mondrup's four-hand piano reduction (Werner Icking
# Music Archive); licence: Creative Commons Attribution-ShareAlike 4.0 for the typesetting, the music is public
# domain).  The melody is the top note of the right hand, in the score's key, C major (the spec's G-major list put
# bars 9-14 and 25-32 in the wrong octave and had C instead of E in bars 9-14: B D A | A . a, not F# A C | C . E in
# G); our bar 1 is the score's bar 2 (its pickup C4 comes back as the end of bars 4, 16 and 20), bar 32 is its closing
# bar 33 (C4 . C5 C5), which flows straight into bar 1.  Chords from the score's left hand: bars 22-25 Dm,
# 26-27 G7, 30 F, 31 G.
DAN_BARS = [
    "C4:2 E4:2 G4:2", "G4:4 G5:2", "G5:4 E5:2", "E5:4 C4:2", "C4:2 E4:2 G4:2",
    "G4:4 G5:2", "G5:4 F5:2", "F5:4 B3:2", "B3:2 D4:2 A4:2", "A4:4 A5:2",
    "A5:4 F5:2", "F5:4 B3:2", "B3:2 D4:2 A4:2", "A4:4 A5:2", "A5:4 E5:2",
    "E5:4 C4:2", "C4:2 E4:2 G4:2", "C5:4 C6:2", "C6:4 G5:2", "G5:4 C4:2",
    "C4:2 E4:2 G4:2", "C5:4 C6:2", "C6:4 A5:2", "A5:4 D4:2", "D4:2 F4:2 A4:2", "A4:6",
    "~:2 F#4:2 G4:2", "E5:6", "~:2 C5:2 E4:2", "E4:4 D4:2", "A4:4 G4:2", "C4:3 C5:1 C5:2",
]
DAN_CHORDS = [
    "C", "C", "C", "C", "C", "C", "G7", "G7", "G7", "G7", "G7", "G7", "G7", "G7", "C", "C", "C",
    "C", "C", "C", "C", "Dm", "Dm", "Dm", "Dm", "G7", "G7", "C", "C", "F", "G", "C",
]
# Music batch 4 (owner-approved 2026-10-17, docs/proarr/BATCH_4.md and specs/danube.md on branch promusic): a Viennese waltz bass, root on 1, two
# chord tones that lead into every change (D into G, B into C, C into D, F into G, E into F); a soft kit (kick, rim clicks, an open hat every
# fourth bar: a 4-bar groove, 24 rows; DAN_GROOVE_1BAR is the one-bar fallback, 18 B less of bank 2).
DAN_BASS = " ".join(H.expand([
    "C3:2 E3:2 G3:2", "C3:2 G2:2 E3:2", 1, 2, 1, "C3:2 E3:2 D3:2",                     # 1-6   C
    "G2:2 D3:2 F3:2", "G2:2 B2:2 D3:2", 7, 8, 7, 8, 7, "G2:2 D3:2 B2:2",                # 7-14  G7
    1, 2, 1, 2, 1, 2, "C3:2 G2:2 C3:2",                                                 # 15-21 C
    "D3:2 A2:2 F3:2", "D3:2 F3:2 A3:2", 22, "D3:2 A2:2 F2:2",                           # 22-25 Dm
    7, 14, 1, "C3:2 G2:2 E2:2", "F2:2 A2:2 F2:2", 14, "C3:2 G2:2 B2:2",                 # 26-32 G7 G7 C C F G C
], 32))
DAN_DRUM_BAR = "b:1 t:1 x:1 t:1 x:1 t:1"
DAN_GROOVE = " ".join([DAN_DRUM_BAR] * 3 + ["b:1 t:1 x:1 t:1 x:1 o:1"])
DAN_GROOVE_1BAR = DAN_DRUM_BAR
song("danube", 9, "A", " ".join(DAN_BARS), DAN_BASS, groove=DAN_GROOVE)
# Harmony (music step 5): a voice in thirds and sixths under the melody (G3 to A5, one note for each melody eighth, grid 1,
# no merging) through bar 24, the closing phrase (bars 25-32) one held chord tone a bar on the pad, G3 to E5.  Owner's
# pick (harmony demos, 2026-10-12): thirds, the last phrase held.
_t = H.Tune(" ".join(DAN_BARS), DAN_CHORDS, 6, 2, "C")
# Batch 4: two held notes of the closing phrase rock gently (F D F, G C G) instead of holding.
DAN_HARM_BARS = {26: "F4:2/2 D4:2/2 F4:2/2", 28: "G4:2/2 C5:2/2 G4:2/2"}
DAN_HARM = H.patch_bars(" ".join([H.follow(_t, (1, 24), "G3", "A5", grid=1, merge=False),
                                  H.guide(_t, (25, 32), "G3", "E5", inst="/2")]), 6, DAN_HARM_BARS)
harmony("danube", _t, DAN_HARM, ("harm", "pad"))
DAN_HARM_CHECK = H.check(_t, DAN_HARM)
DAN_BASS_CHECK = H.bass_check(DAN_BASS, DAN_CHORDS, 6)

# ---------------------------------------------------------------------------------------------
# Zoo: "Pop Goes the Weasel" (English folk tune, c. 1850), verse and second strain.  6/8, key G, dotted
# quarter = 100: 12 frames per eighth row.  16 bars.  The last rest of bar 16 becomes the D4 pickup (the
# spec's note for looping).  Bar 15 is C for the first dotted beat and D7 for the second.  Rhythm checked (music step
# 3, 2026-10-11) against the spec's source itself, Ryan's Mammoth Collection's "Pop Goes the Weasel" as encoded in the
# music21 corpus (github.com/cuthbertLab/music21, corpus/ryansMammoth/PopGoesTheWeasel.abc): all 16 bars match.
WEA_BARS = [
    "G4:2 G4:1 A4:2 A4:1", "B4:1 D5:1 B4:1 G4:2 R:1", "G4:2 G4:1 A4:2 C5:1", "B4:3 G4:2 R:1",
    "G4:2 G4:1 A4:2 A4:1", "B4:1 D5:1 B4:1 G4:2 R:1", "E5:3 A4:2 C5:1", "B4:3 G4:2 R:1",
    "G5:3 E5:2 G5:1", "F#5:1 A5:1 F#5:1 D5:3", "G5:2 G5:1 E5:2 G5:1", "F#5:3 D5:2 B4:1",
    "C5:2 B4:1 C5:2 D5:1", "E5:2 F#5:1 G5:2 R:1", "E5:1 R:2 A4:2 C5:1", "B4:3 G4:2 R:1",
]
WEA_BARS[-1] = WEA_BARS[-1].replace("R:1", "D4:1")
WEA_CHORDS = [
    "G", "G", "D7", "G", "G", "G", "Am", "G", "G", "D", "G", "D", "C", "G", "C/D7", "G",
]
# Music batch 4 (specs/weasel.md): the bass keeps its 6/8 bounce but walks into every change (B C up into D, F# under into G, B down into A);
# the drums are a kit: kick 1, snare 4, hats; three snares close bars 4 and 8, a tom tom leads into the C (12), the "Pop!" is a snare and an
# open hat on bar 15's E5 (the beat stops for a crack, then picks up), and a fill leads into the loop (16).
WEA_BASS = " ".join(H.expand([
    "G2:3 D3:3", "G2:3 B2:2 C3:1", "D3:3 A2:2 F#2:1", 1,                  # 1-4   G G D7 G
    "G2:3 B2:3", "G2:3 D3:2 B2:1", "A2:3 C3:2 A2:1", 1,                   # 5-8   G G Am G
    "G2:3 B2:2 C3:1", "D3:3 A2:2 F#2:1", 9, "D3:3 A2:2 B2:1",            # 9-12  G D G D
    "C3:3 E3:2 A2:1", "G2:3 B2:2 B2:1", "C3:3 D3:2 F#2:1", 1,             # 13-16 C G C,D7 G
], 16))
WEA_DRUM_BAR = "b:1 t:1 t:1 n:1 t:1 t:1"
WEA_DRUMS = " ".join(H.expand([
    WEA_DRUM_BAR, 1, 1, "b:1 t:1 t:1 n:1 n:1 n:1",
    1, 1, 1, 4,
    1, 1, 1, "b:1 t:1 t:1 n:1 m:1 m:1",
    1, 1, "n:1 o:1 r:1 b:1 t:1 t:1", "b:1 t:1 t:1 n:1 n:1 o:1",
], 16))
song("weasel", 12, "A", " ".join(WEA_BARS), WEA_BASS, WEA_DRUMS)
# Harmony (music step 5): the verse (bars 1-8) short dry stabs on the 6/8 off-beats (the bass plays the two dotted beats,
# the stabs the two eighths after each: A3 to D5), the second strain (bars 9-16) a voice in thirds and sixths under the
# melody, one note for each melody eighth (grid 1, no merging).  Owner's pick (harmony demos, 2026-10-12): stabs, then thirds.
_t = H.Tune(" ".join(WEA_BARS), WEA_CHORDS, 6, 3, "G")
harmony("weasel", _t, " ".join([H.stabs(_t, (1, 8), "A3", "D5", [(1, False), (1, True), (1, True)] * 2),
                                H.follow(_t, (9, 16), "A3", "D5", grid=1, merge=False, inst="/2")]), ("stab", "harm"))
WEA_HARM_CHECK = H.check(_t, SONGS["weasel"]["ch1"])
WEA_BASS_CHECK = H.bass_check(WEA_BASS, WEA_CHORDS, 6)

# ---------------------------------------------------------------------------------------------
# The Chrome Cow: "Drunken Sailor" (traditional sea shanty), the owner's pick, played fast and punky (docs/music_specs.md
# tune 11).  4/4, D Dorian, quarter = 200: 9 frames per eighth row.  16 bars: the verse, then the chorus.  Punk
# arrangement: every melody note cut short (3/4 of its length), the bass driving root eighth notes with the fifth on the
# last two, a kick / hat / snare groove with a double kick.  In the Last call the band plays faster (src/music.c
# music_fast: one frame less per row, 225 bpm).  Rhythm checked (music step 3, 2026-10-11) against the Wikifonia lead
# sheet "What Shall We Do with a Drunken Sailor?" in OpenEWLD (github.com/00sapo/OpenEWLD, public-domain scores): the
# verse was right; the chorus's "Hur-ray and up she ri-ses" is a quarter, a dotted eighth and a sixteenth ("-ray and"),
# not two even quarters (bars 9, 11 and 13; the "and" was missing).
SAI_BARS = [
    "A4:2 A4:1 A4:1 A4:2 A4:1 A4:1", "A4:2 D4:2 F4:2 A4:2", "G4:2 G4:1 G4:1 G4:2 G4:1 G4:1", "G4:2 C4:2 E4:2 G4:2",
    "A4:2 A4:1 A4:1 A4:2 A4:1 A4:1", "A4:2 B4:2 C5:2 D5:2", "C5:2 A4:2 G4:2 E4:2", "D4:4 D4:4",
    "A4:4 A4:3 A4:1", "A4:2 D4:2 F4:2 A4:2", "G4:4 G4:3 G4:1", "G4:2 C4:2 E4:2 G4:2",
    "A4:4 A4:3 A4:1", "A4:2 B4:2 C5:2 D5:2", "C5:2 A4:2 G4:2 E4:2", "D4:4 D4:4",
]
SAI_CHORDS = ["Dm", "Dm", "C", "C", "Dm", "Dm", "C", "Dm"] * 2


def punk_bass(chords):
    """Driving eighth notes: the root six times, the fifth twice, every one cut short."""
    return " ".join(" ".join([f"{CHORD[c][0]}:1!"] * 6 + [f"{CHORD[c][1]}:1!"] * 2) for c in chords)


# Music batch 3 (specs/sailor.md): a punk riff, root eighths with a two-note pickup into the next chord (F A when Dm stays, E D into C, E G when
# C stays, G G B C walking back up into Dm).  The same 8 bar types in both orders: one bass pattern.  Drums (a groove): kick 1, snare 2, the
# double kick on 3, snare 4, hats between; three snares and an open hat every fourth bar (32 rows; SAI_GROOVE_2BAR, an open hat every second
# bar, is the 16-row fallback, 16 B less of bank 2).
SAI_RIFF = {
    ("Dm", "Dm"): "D3:1! D3:1! D3:1! D3:1! D3:1! D3:1! F3:1! A3:1!",
    ("Dm", "C"): "D3:1! D3:1! D3:1! D3:1! D3:1! D3:1! E3:1! D3:1!",
    ("C", "C"): "C3:1! C3:1! C3:1! C3:1! C3:1! C3:1! E3:1! G3:1!",
    ("C", "Dm"): "C3:1! C3:1! C3:1! C3:1! G2:1! G2:1! B2:1! C3:1!",
}
SAI_BASS = " ".join(SAI_RIFF[(c, SAI_CHORDS[(i + 1) % 16])] for i, c in enumerate(SAI_CHORDS))
SAI_DRUM_BAR = "b:1 t:1 n:1 t:1 b:1 b:1 n:1 t:1"
SAI_GROOVE = " ".join([SAI_DRUM_BAR] * 3 + ["b:1 t:1 n:1 t:1 n:1 n:1 n:1 o:1"])
SAI_GROOVE_2BAR = SAI_DRUM_BAR + " " + "b:1 t:1 n:1 t:1 b:1 b:1 n:1 o:1"

# THE SAILOR'S ARPEGGIO VARIANT (owner-approved 2026-10-17): hardware chord arpeggios (hUGE 0xy, 20 Hz) on the shouted held notes, on the
# table-less lead (instrument 1), the same at the Last call's tempo, 0 extra bytes (proarr's sailor_b3d: the spec's variant B on the bars
# with 3-4 row notes only, each note's first row plain and the flutter from its second row, so no row tick carries both a new note and
# the arpeggio's set-up: its CPU fix).  ONE LINE chooses: SAILOR_VARIANT = "b3d" (shipped: the owner picked it 2026-10-17) the arpeggios, None the plain riff (proarr's sailor_b3).
SAILOR_VARIANT = "b3d"
# CPU: at the Last call's tempo (music_fast: a row is 8 frames) the row tick of row 5 of bars 8 and 16 (the second long D4's second row: the
# 0x37 arpeggio's set-up beside a groove hit and a harmony note) ran 18.5 lines, two calls over the 18-line budget (src/music.h MUSIC_LATEST_LY);
# without that one effect it is 18.0 (the normal tempo 17.4 either way).  SAILOR_LASTCALL_SAFE = False restores proarr's b3d exactly.
SAILOR_LASTCALL_SAFE = True
SAI_ARP_BARS = {   # bar (1-based): (arpeggio, the token indexes of the bar that get the table-less lead /1, the bar rows that carry the effect)
    8: (0x37, (0, 1), (1, 2, 5, 6)), 16: (0x37, (0, 1), (1, 2, 5, 6)),
    9: (0x58, (0, 1), (1, 2, 5)), 13: (0x58, (0, 1), (1, 2, 5)), 11: (0x59, (0, 1), (1, 2, 5)),
}


def sailor_arp():
    """(the Sailor melody with /1 on the arpeggiated tokens, fx_map {row: [(2, 0xy)]})."""
    out, fx = [], {}
    for i, bar in enumerate(SAI_BARS):
        toks = bar.split()
        if i + 1 in SAI_ARP_BARS:
            arp, idx, rows = SAI_ARP_BARS[i + 1]
            if SAILOR_LASTCALL_SAFE and arp == 0x37:
                rows = tuple(r for r in rows if r != 5)
            toks = [f"{tk}/1" if k in idx else tk for k, tk in enumerate(toks)]
            for r in rows:
                fx[i * 8 + r] = [(2, arp)]
        out.append(" ".join(toks))
    return " ".join(out), fx


_sai_mel, _sai_fx = sailor_arp() if SAILOR_VARIANT == "b3d" else (" ".join(SAI_BARS), None)
song("sailor", 9, "A", _sai_mel, SAI_BASS, stac_all=(3, 4), groove=SAI_GROOVE, fx_map=_sai_fx)
# Harmony (music step 5): the verse gets punk off-beat upstrokes (a short chord tone on every second eighth: D or F for D
# minor, C or E for C), the chorus ("Hur-ray and up she ri-ses") a voice in thirds under the melody, struck on each
# eighth like a second shouting voice.
_t = H.Tune(" ".join(SAI_BARS), SAI_CHORDS, 8, 2, "Ddor")
harmony("sailor", _t, " ".join([H.stabs(_t, (1, 8), "C4", "A4", [(1, False), (1, True)] * 4),
                                H.follow(_t, (9, 16), "A3", "A4", grid=2, merge=False, inst="/2")]), ("stab", "harm"))
SAI_HARM_CHECK = H.check(_t, SONGS["sailor"]["ch1"])
SAI_BASS_CHECK = H.bass_check(SAI_BASS, SAI_CHORDS, 8)

# ---------------------------------------------------------------------------------------------
# The credits tune (src/credits.c; owner picked draft "D3c", 2026-10-17): The Entertainer's intro, the A and B strains, the strains the
# title tune does not use (the C strain in F, the bridge, the D strain) and Joplin's own last two bars, then a ringing final chord, in a
# slow warm style (15 frames a row, no drums, held root / fifth bass, the title's thirds on the 50% pulse).  A pass is 579 rows =
# 8732 frames (146 s: gen_music sums the real frames, the ritard's tempo changes included): not a venue tune (it is no VENUES entry,
# no jukebox item): gen_music plays it once as a jingle and streams its patterns (20 of them in 10 orders: the buffer holds 8, see
# gen_music.CREDITS and src/music.c).  The notes were read from the Mutopia Project score entertainer.ly (Public Domain, 1902
# edition) by the draft generator (tools/music_drafts.py on the drafts branch); they are data here so that no score file is needed to
# build.  The bass chords and the harmony (tools/harmony.py follow) are ours.  The ending: a modest ritard on the last bar (tempo_map:
# row -> frames a row, hUGE Fxx on a free effect column), the final chord on the "ring" lead (duty instrument 7) over a harmony on
# "ring50", the bass C2 stepped down (fx_map: row -> [(channel, effect)], hUGE Cxx wave volume 50 %, then 25 %).
CR_MEL = (
    "D5:1 E5:1 C5:1 A4:2 B4:1 G4:2 D5:1 E5:1 C5:1 A4:2 B4:1 G4:2 D5:1 E5:1 C5:1 A4:2 B4:1 A4:1 G#4:1 G4:2 r:2 G4:2 D4:1 "
    "D#4:1 E4:1 C5:2 E4:1 C5:2 E4:1 C5:1 ~:5 C5:1 D5:1 D#5:1 E5:1 C5:1 D5:1 E5:2 B4:1 D5:2 C5:6 D4:1 D#4:1 E4:1 C5:2 E4:1 "
    "C5:2 E4:1 C5:1 ~:6 A4:1 G4:1 F#4:1 A4:1 C5:1 E5:2 D5:1 C5:1 A4:1 D5:6 D4:1 D#4:1 E4:1 C5:2 E4:1 C5:2 E4:1 C5:1 ~:5 "
    "C5:1 D5:1 D#5:1 E5:1 C5:1 D5:1 E5:2 B4:1 D5:2 C5:6 C5:1 D5:1 E5:1 C5:1 D5:1 E5:2 C5:1 D5:1 C5:1 E5:1 C5:1 D5:1 E5:2 "
    "C5:1 D5:1 C5:1 E5:1 C5:1 D5:1 E5:2 B4:1 D5:2 C5:5 E4:1 F4:1 F#4:1 G4:2 A4:1 G4:2 E4:1 F4:1 F#4:1 G4:2 A4:1 G4:2 E4:1 "
    "C4:1 G3:1 A3:1 B3:1 C4:1 D4:1 E4:1 D4:1 C4:1 D4:1 G3:1 E4:1 F4:1 G4:1 A4:1 G4:1 E4:1 F4:1 G4:2 A4:1 G4:2 E4:1 F4:1 "
    "F#4:1 G4:2 A4:1 G4:2 G4:1 A4:1 A#4:1 B4:1 B4:2 B4:2 A4:1 F#4:1 D4:1 G4:5 E4:1 F4:1 F#4:1 G4:2 A4:1 G4:2 E4:1 F4:1 "
    "F#4:1 G4:2 A4:1 G4:2 E4:1 C4:1 G3:1 A3:1 B3:1 C4:1 D4:1 E4:1 D4:1 C4:1 D4:1 C4:5 G3:1 F#3:1 G3:1 C4:2 A3:1 C4:2 A3:1 "
    "C4:1 A3:1 G3:1 C4:1 E4:1 G4:2 E4:1 C4:1 G3:1 A3:2 C4:2 E4:1 D4:2 C4:1 ~:4 C4:2 r:2 A4:1 G#4:1 A4:4 C5:2 D5:8 F4:1 E4:1 "
    "F4:4 A4:2 A#4:7 G4:1 D4:2 G4:1 D4:2 G4:1 D4:2 C4:4 F4:4 E4:1 G#4:1 B4:1 E5:2 D5:1 B4:1 C5:1 A4:4 A#4:4 A4:1 G#4:1 A4:4 "
    "C5:2 D5:8 F4:1 E4:1 F4:4 A4:2 A#4:7 G4:1 D4:2 G4:1 D4:2 G4:1 D4:2 C4:4 F4:3 F4:1 A4:1 C5:2 G4:2 C4:1 D4:1 E4:1 F5:2 "
    "r:2 F5:2 r:2 C5:2 A4:1 C5:2 A4:1 C5:1 A4:1 G4:1 C5:1 E5:1 G5:2 E5:1 C5:1 G4:1 A4:2 C5:2 E5:1 D5:2 C5:1 C5:4 C5:2 r:2 "
    "F4:2 E4:1 F4:2 E4:1 F4:2 r:1 A4:1 D5:1 A4:1 C5:1 D5:1 C5:1 A4:1 G4:2 F#4:1 G4:2 F#4:1 G4:2 r:1 C5:1 E5:1 C5:1 D5:1 "
    "E5:1 D5:1 C5:1 D5:2 C#5:1 D5:2 C#5:1 D5:2 r:1 F5:1 A5:1 F5:1 G5:1 A5:1 G5:1 F5:1 C6:1 C6:1 C6:4 A5:2 G5:2 G4:1 G4:1 "
    "G4:2 G4:2 F4:2 E4:1 F4:2 E4:1 F4:2 r:1 A4:1 D5:1 A4:1 C5:1 D5:1 C5:1 A4:1 G4:2 F#4:1 G4:2 F#4:1 G4:2 r:1 C5:1 E5:1 "
    "C5:1 D5:1 E5:1 D5:1 C5:1 A4:1 G#4:1 A4:1 G5:2 F5:2 C5:1 E5:1 D#5:1 E5:1 A5:2 C6:1 G5:1 E5:1 C5:2 C5:2 E5:1 D5:2 C5:5 "
    "C6:6/5 r:1"
)
CR_BASS = (
    "G2:4 D3:4 G2:4 D3:4 G2:4 D3:4 G2:4 D3:4 C3:4 G3:4 F2:4 C3:4 G2:4 D3:4 C3:4 G3:4 C3:4 G3:4 F2:4 C3:4 D3:4 A3:4 G2:4 "
    "D3:4 C3:4 G3:4 F2:4 C3:4 G2:4 D3:4 C3:4 G3:4 C3:4 G3:4 F2:4 C3:4 G2:4 D3:4 C3:4 G3:4 C3:4 G3:4 C3:4 G3:4 F2:4 C3:4 "
    "C3:4 G3:4 C3:4 G3:4 C3:4 G3:4 D3:4 A3:4 G2:4 D3:4 C3:4 G3:4 C3:4 G3:4 F2:4 C3:4 C3:4 G3:4 F2:4 F#2:4 C3:4 G3:4 D3:4 "
    "G2:4 C3:4 G3:4 F2:4 C3:4 A#2:4 F3:4 D3:4 A3:4 G2:4 D3:4 A#2:4 G2:4 F2:4 D3:4 E3:4 B3:4 A2:4 C3:4 F2:4 C3:4 A#2:4 F3:4 "
    "D3:4 A3:4 G2:4 D3:4 A#2:4 G2:4 F2:4 C3:4 C3:4 G3:4 F2:4 C3:4 F2:4 F#2:4 C3:4 G3:4 D3:4 G2:4 C3:4 G3:4 D3:4 A3:4 D3:4 "
    "A3:4 C3:4 G3:4 C3:4 G3:4 G2:4 D3:4 G2:4 D3:4 F#2:4 C3:4 C3:4 G3:4 D3:4 A3:4 D3:4 A3:4 C3:4 G3:4 C3:4 G3:4 F2:4 C3:4 "
    "C3:4 G3:4 A2:2 D3:2 G2:2 B2:2 C3:2 G2:2 C2:6/2 r:1"
)
CR_HARM = (
    "B4:1 B4:1 G4:1 F4:2 G4:1 B3:2 B4:1 B4:1 G4:1 F4:2 G4:1 B3:2 B4:1 B4:1 G4:1 F4:2 G4:1 F4:1 F4:1 B3:2 r:2 B3:2 B3:1 B3:1 "
    "C4:1 E4:2 C4:1 E4:2 C4:1 E4:1 A4:4 E4:1 E4:1 G4:1 G4:1 G4:1 G4:1 B4:1 B4:2 G4:1 B4:2 E4:6 B3:1 C4:1 C4:1 E4:2 C4:1 "
    "E4:2 C4:1 E4:1 A4:4 E4:2 E4:1 E4:1 D4:1 F#4:1 A4:1 A4:2 F#4:1 A4:1 F#4:1 B4:6 B3:1 B3:1 C4:1 E4:2 C4:1 E4:2 C4:1 E4:1 "
    "A4:4 E4:1 E4:1 G4:1 G4:1 G4:1 G4:1 B4:1 B4:2 G4:1 B4:2 E4:6 E4:1 G4:1 G4:1 E4:1 G4:1 G4:2 E4:1 G4:1 E4:1 A4:1 A4:1 "
    "A4:1 A4:2 A4:1 A4:1 A4:1 G4:1 G4:1 B4:1 B4:2 G4:1 B4:2 E4:5 C4:1 C4:1 D4:1 E4:2 E4:1 E4:2 C4:1 C4:1 D4:1 E4:2 E4:1 "
    "E4:2 C4:1 E3:1 E3:1 F3:1 G3:1 A3:1 A3:1 C4:1 A3:1 A3:1 A3:1 E3:1 C4:1 C4:1 E4:1 E4:1 E4:1 C4:1 C4:1 E4:2 E4:1 E4:2 "
    "C4:1 C4:1 D4:1 E4:2 E4:1 E4:2 E4:1 E4:1 G4:1 F#4:1 F#4:2 F#4:2 F#4:1 D4:1 F#3:1 B3:5 B3:1 D4:1 D4:1 E4:2 E4:1 E4:2 "
    "C4:1 C4:1 D4:1 E4:2 E4:1 E4:2 C4:1 E3:1 E3:1 F3:1 G3:1 A3:1 A3:1 C4:1 A3:1 A3:1 A3:1 E3:5 E3:1 D3:1 E3:1 A3:2 F3:1 "
    "A3:1 A3:1 F#3:1 A3:1 F#3:1 E3:1 E3:1 C4:1 E4:2 C4:1 E3:1 E3:1 F#3:2 A3:2 G3:1 B3:2 G3:1 E3:4 E3:2 r:2 F4:1 F4:1 F4:4 "
    "A4:2 A#4:8 D4:1 A3:1 D4:4 F4:2 G4:7 D4:1 A#3:2 A#3:1 A#3:1 A#3:1 A#3:1 A#3:2 A3:4 D4:4 G#3:1 E4:1 G#4:1 G#4:2 B4:1 "
    "G#4:1 G#4:1 E4:4 G4:4 F4:1 F4:1 F4:4 A4:2 A#4:8 D4:1 A3:1 D4:4 F4:2 G4:7 D4:1 A#3:2 A#3:1 A#3:1 A#3:1 A#3:1 A#3:2 A3:4 "
    "C4:3 C4:1 C4:1 E4:2 E4:2 E3:1 A#3:1 C4:1 A4:2 r:2 A4:2 r:2 A4:2 F4:1 A4:1 A4:1 F#4:1 A4:1 F#4:1 E4:1 E4:1 G4:1 B4:2 "
    "G4:1 E4:1 E4:1 F#4:2 A4:2 G4:1 B4:2 G4:1 E4:4 E4:2 r:2 D4:2 A3:1 D4:2 A3:1 D4:2 r:1 F4:1 F4:1 F4:1 A4:1 A4:1 A4:1 F4:1 "
    "E4:2 D4:1 E4:2 D4:1 E4:2 r:1 E4:1 G4:1 E4:1 G4:1 G4:1 G4:1 E4:1 B4:2 F4:1 B4:2 F4:1 B4:2 r:1 A4:1 G4:1 A4:1 B4:1 G4:1 "
    "B4:1 A4:1 A4:1 A4:1 A4:4 F#4:2 B4:2 E4:1 E4:1 E4:2 E4:2 D4:2 A3:1 D4:2 A3:1 D4:2 r:1 F4:1 F4:1 F4:1 A4:1 A4:1 A4:1 "
    "F4:1 E4:2 D4:1 E4:2 D4:1 E4:2 r:1 E4:1 G4:1 E4:1 G4:1 G4:1 G4:1 E4:1 F4:1 F4:1 F4:1 B4:2 A4:2 A4:1 G4:1 G4:1 G4:1 G4:2 "
    "G4:1 B4:1 G4:1 F#4:2 F#4:2 B4:1 B4:2 G4:5 E5:6/2 r:1"
)
CR_TEMPO_MAP = {568: 17, 570: 19, 572: 20}
CR_FX_MAP = {574: [(3, 0xC05)], 576: [(3, 0xC02)]}   # the last bass chord: 50 %, then 25 % (the driver reads the LOW nibble of Cxy for the wave channel)
# Music batch 4 (specs/credits.md): the bass is the full held one (BASS_HELD: no pluck table, it sustains to the end of each note) all the way, not
# only in the last chord; the lead is the brass one (the notes, the ending and the fade are untouched).  CREDITS_LEAD = LEAD_PRO is the owner's
# brass lead; DUTY_SONG_LEAD (1) is the old song lead: if the brass version's streaming call ever goes over 18 lines, one line changes it.
CREDITS_LEAD = LEAD_PRO
CR_BASS_HELD = with_inst(CR_BASS, BASS_HELD)
song("credits", 15, "A", CR_MEL, CR_BASS_HELD, "", inst=CREDITS_LEAD, tempo_map=CR_TEMPO_MAP, fx_map=CR_FX_MAP)
SONGS["credits"].update(ch1=CR_HARM, ch1_inst=("harm50", "ring50"))

# ---------------------------------------------------------------------------------------------
# The title tune (owner-approved 2026-10-17: music batch 1's title, then "the whole Entertainer, looping", the second B strain an
# octave up; docs/proarr/BATCH_1.md, BATCH_TITLE_FULL.md and specs/title_full.md on branch promusic).  152 bars, 1216 rows, 10336 frames
# (173 s a pass), swing 0xAA like the old title:
#   intro (4) | A1 (16) | A2 (16) | B1 (16) | B2 (16, an octave up: Joplin's "8va") | A3 (16) | C1 (16) | C2 (16, the trio in F) |
#   bridge (4) | D1 (16) | D2 (16) | -> back to the intro
# The A and B strains are the old title's (ENT_BARS), the intro, trio, bridge and D strain the credits tune's notes (CR_MEL, bar by bar).
# It streams like the credits tune: 20 hUGE orders, the intro's and the bridge's short (32 rows, `short_orders`); src/music.c copies
# order k+2 (mod 20) over the buffer slot of order k-2 while order k plays.  The bass is a ragtime left hand with a walk into every
# chord change, the drums a 4-bar groove with a fill on every fourth bar, the second voice on channel 1 in thirds with the walking
# held bars.  Real pitches throughout (the bass gets the wave octave from gen_music).
ENT_BASS = H.expand([
    "C3:2 G2:2 C3:2 D3:1 E3:1",      # 1  C -> F
    "F3:2 A2:2 E3:2 F3:1 F#3:1",     # 2  F, C/E -> G7 (the F F# walk lands on the G above)
    "G3:2 D3:2 G2:2 B2:2",           # 3  G7 -> C: the left hand runs down G D G, B into C
    "C3:2 G2:2 A2:2 B2:2",           # 4  C: the walk-up into bar 5
    1,                               # 5
    "F3:2 A2:2 E3:2 C3:1 C#3:1",     # 6  F, C/E -> D7
    "D3:2 A2:2 D3:2 F#2:2",          # 7  D7 -> G7
    "G2:2 D3:2 G2:2 B2:2",           # 8  G7 -> C (from the low F#: the low G)
    1, 2, 3, 4,                      # 9-12
    1,                               # 13
    "F2:2 C3:2 F2:2 F#2:2",          # 14 F -> G7 (the low F this time)
    8,                               # 15
    "C3:2 G2:2 E3:2 G2:2",           # 16 C, into the B section
    16,                              # 17
    1,                               # 18 C -> F
    "F3:2 C3:2 A2:2 B2:2",           # 19 F -> C
    4,                               # 20
    16,                              # 21
    "C3:2 G2:2 C3:2 C#3:2",          # 22 C -> D7
    7,                               # 23
    8,                               # 24
    16,                              # 25
    1,                               # 26
    19,                              # 27
    "C3:2 G2:2 C3:2 E3:2",           # 28 C -> F
    "F3:2 C3:2 F#3:2 A2:2",          # 29 F, F#dim7 -> C/G
    "G2:2 E3:2 C3:2 C#3:2",          # 30 C -> D7
    "D3:2 A2:2 G2:2 B2:2",           # 31 D7, G7 -> C
    4,                               # 32 C: the walk-up into bar 1
], 32)
# Drums: a 4-bar groove (32 rows; the title's 8 patterns fill the WRAM buffer, so its drums stay with the groove player): kick on 1,
# snare on 2, closed hats on the "ands"; bar 2 ends with a hat double, bar 4 with a snare on the and-of-2 and an open hat.
ENT_GROOVE = " ".join(["b:1 r:1 t:1 r:1 n:1 r:1 t:1 r:1", "b:1 r:1 t:1 r:1 n:1 r:1 t:1 t:1",
                       "b:1 r:1 t:1 r:1 n:1 r:1 t:1 r:1", "b:1 r:1 t:1 r:1 n:1 r:1 n:1 o:1"])
# Harmony: the owner's thirds (follow, grid 1) stay; under the held notes the voice now walks instead of holding one tone.
ENT_HARM_BARS = {
    2: "A4:2 F4:2 E4:2 G4:2",            # under the held C5 (F, then C/E): A F E, G under the D D# pickup
    4: "E4:2 G4:2 E4:1 C4:1 B3:1 C4:1",  # the rag's E-C figure under the held C, B C under the D D# pickup
    6: "A4:2 F4:2 G4:2 E4:2",            # under the held C5, then E under A G
    8: "B4:2 G4:2 F4:2 B3:2",            # under the held D5 (G7): B G F, then B under the pickup
    10: "A4:2 F4:2 E4:2 G4:2",
    12: "E4:2 G4:2 E4:3 G4:1",
    16: "E4:2 G4:2 E4:1 C4:1 C4:1 D4:1",
    24: "D4:2 B3:4 D4:2",                # under the held G4 (G7)
    28: "E3:2 G3:2 E3:2 D3:1 E3:1",      # under the held C4, low
    32: "E3:2 G3:2 E3:2 G3:1 C4:1",      # under the held C4, G C under the D D# pickup into bar 1
}
ENT_TRIO_BASS = H.expand([                # the trio's 15 bars (F major; roots F2, A#2, D3, G2, E3, A2, C3), a lead into every bar
    "F2:2 C3:2 F2:2 A2:2", "A#2:2 F3:2 A#2:2 C3:2", "D3:2 A2:2 F3:2 A2:2", "G2:2 D3:2 G2:2 A2:2",
    "A#2:2 F3:2 G2:2 E2:2", "F2:2 C3:2 D3:2 B2:2", "E3:2 B2:2 E3:2 G#2:2", "A2:2 E3:2 C3:2 G2:2",
    1, 2, 3, 4, 5, "F2:2 C3:2 C3:2 G2:2", "C3:2 G2:2 C3:2 E3:2"], 15)
ENT_D_BASS = H.expand([                   # the D strain's 15 bars (the last, Joplin's own walking bass under the cadence: A D G B)
    "D3:2 A2:2 D3:2 A2:2", "D3:2 A2:2 F3:2 D3:2", "C3:2 G2:2 E3:2 G2:2", "C3:2 G2:2 C3:2 D3:2",
    "G2:2 D3:2 F3:2 D3:2", "G2:2 D3:2 G2:2 G2:2", "F#2:2 A2:2 C3:2 B2:2", "C3:2 G2:2 C3:2 C#3:2",
    1, 2, 3, "C3:2 G2:2 C3:2 E3:2", "F2:2 C3:2 A2:2 B2:2", "C3:2 G2:2 E3:2 C3:2", "A2:2 D3:2 G2:2 B2:2"], 15)
ENT_CH = dict(intro=["G7"] * 4, A=ENT_CHORDS[0:16], B=ENT_CHORDS[16:32],
              C1=["F", "Bb", "Dm", "Gm", "Bb/Gm", "F/Dm", "E7", "Am/C7", "F", "Bb", "Dm", "Gm", "Bb/Gm", "F/C7", "C7", "C7"],
              C2=["F", "Bb", "Dm", "Gm", "Bb/Gm", "F/Dm", "E7", "Am/C7", "F", "Bb", "Dm", "Gm", "Bb/Gm", "F/C7", "C7", "F"],
              bridge=["F/F#dim7", "C", "D7/G7", "C"],
              D=["Dm", "Dm", "C", "C", "G7", "G7", "F#dim7", "C", "Dm", "Dm", "C", "C", "F", "C", "D7/G7", "C"])
ENT_SECTIONS = ("intro", "A1", "A2", "B1", "B2", "A3", "C1", "C2", "bridge", "D1", "D2")


def entertainer_sections():
    """[dict(name, mel, bass, chords, key, harm, tune)] for the 11 sections of the title tune (every one a whole number of bars of 8 rows)."""
    E, B = ENT_BARS, ENT_BASS
    j = " ".join
    trio, bridge = H.bars_of(CR_MEL, 37, 51), H.bars_of(CR_MEL, 53, 56)
    d_strain = H.bars_of(CR_MEL, 57, 70)
    d89 = "C5:2 C5:2 E5:1 D5:2 C5:1"                 # Joplin's bar 89 (the score's), one octave below
    mel = dict(
        intro=H.bars_of(CR_MEL, 1, 4),
        A1=j(E[0:15]) + " C5:6 D4:1 D#4:1",          # the first ending: the C held, D D# back up into A
        A2=j(E[0:16]),                              # the second ending C5:5 E4 F4 F#4 into B
        B1=j(E[16:31]) + " ~:5 E5:1 F5:1 F#5:1",    # the first ending: the C held, the pickup an octave up into the 8va repeat
        B2=H.transpose(j(E[16:31]), 1) + " ~:6 D4:1 D#4:1",   # Joplin marks the B repeat "8va"; its second ending drops back for the D D# pickup into A
        A3=j(E[0:15]) + " C5:4 C5:2 r:2",            # the score's bar 54: the cadence, a chord, a rest, into the trio
        C1=trio + " F5:2 B3:1 C4:1 D4:1 E4:1 F4:1 G4:1",     # the first ending: the F, then the run up into the trio's A4
        C2=trio + " F5:2 r:2 F5:2 r:2",             # the second ending, as the credits have it
        bridge=bridge,
        D1=d_strain + " " + d89 + " ~:2 G4:1 G4:1 G4:2 G4:2",   # bar 89 and the first ending 90a
        D2=d_strain + " " + d89 + " ~:4 C5:3 r:1",  # bar 89 and the second ending: Joplin's "C held, chord, rest", the rest shortened (the loop seam)
    )
    bass = dict(
        intro="D3:1 E3:1 C3:1 A2:2 B2:1 G2:2 D3:1 E3:1 C3:1 A2:2 B2:1 G2:2 D3:1 E3:1 C3:1 A2:2 B2:1 A2:1 G#2:1 G2:2 r:2 G2:2 B2:2",
        A1=j(B[0:15]) + " C3:2 G2:2 A2:2 B2:2", A2=j(B[0:15]) + " C3:2 G2:2 A2:2 B2:2",
        B1=j(B[16:32]), B2=j(B[16:32]),
        A3=j(B[0:15]) + " C3:2 G2:2 C3:2 D3:1 E3:1",
        C1=j(ENT_TRIO_BASS) + " C3:2 G2:2 D3:2 E3:2", C2=j(ENT_TRIO_BASS) + " F2:2 C3:2 F2:2 C3:2",
        bridge="F2:2 C3:2 F#2:2 A2:2 C3:2 G2:2 E3:2 G2:2 D3:2 A2:2 G2:2 B2:2 C3:2 G2:2 C3:2 C#3:2",
        D1=j(ENT_D_BASS) + " C3:2 G2:2 C3:2 C#3:2", D2=j(ENT_D_BASS) + " C3:2 G2:2 B2:2 C3:2",
    )
    chords = dict(intro=ENT_CH["intro"], A1=ENT_CH["A"], A2=ENT_CH["A"], A3=ENT_CH["A"], B1=ENT_CH["B"], B2=ENT_CH["B"],
                  C1=ENT_CH["C1"], C2=ENT_CH["C2"], bridge=ENT_CH["bridge"], D1=ENT_CH["D"], D2=ENT_CH["D"])
    hb = ENT_HARM_BARS
    a_patch = {k: v for k, v in hb.items() if k <= 16}
    b_patch = {k - 16: v for k, v in hb.items() if k > 16}
    patches = dict(
        A1=a_patch | {16: hb[4]}, A2=a_patch, A3=a_patch | {16: "E4:2 G4:2 E4:2 r:2"},
        # B1's last bar: thirds under the pickup (the spec's "E3:2 G3:2 E3:2 C5:1 D5:1 D5:1" is 9 rows: the third E3 is 1 row here)
        B1=b_patch | {16: "E3:2 G3:2 E3:1 C5:1 D5:1 D5:1"},
        B2={k: H.transpose(v, 1) for k, v in b_patch.items() if k != 16} | {16: "E4:2 G4:2 E4:2 G4:1 C5:1"},
    )
    out = []
    for name in ENT_SECTIONS:
        key = "F" if name in ("C1", "C2") else "C"
        ch = chords[name]
        t = H.Tune(mel[name], ch, 8, 4, key)
        lo, hi = ("C4", "B5") if name == "B2" else ("C3", "B4")
        harm = H.follow(t, (1, len(ch)), lo, hi, grid=1, merge=False)
        if name in patches:
            harm = H.patch_bars(harm, 8, patches[name])
        rows = 8 * len(ch)
        assert H.nrows(mel[name]) == H.nrows(bass[name]) == H.nrows(harm) == rows, (name, H.nrows(mel[name]), H.nrows(bass[name]), H.nrows(harm))
        out.append(dict(name=name, mel=mel[name], bass=bass[name], chords=ch, key=key, harm=harm, tune=t, rows=rows))
    return out


ENT_SECS = entertainer_sections()
ENT_FULL_MEL, ENT_FULL_BASS = " ".join(x["mel"] for x in ENT_SECS), " ".join(x["bass"] for x in ENT_SECS)
ENT_FULL_HARM = " ".join(x["harm"] for x in ENT_SECS)
ENT_FULL_CHORDS = sum((x["chords"] for x in ENT_SECS), [])
ENT_ROWS = 1216
assert H.nrows(ENT_FULL_MEL) == H.nrows(ENT_FULL_BASS) == H.nrows(ENT_FULL_HARM) == ENT_ROWS == 8 * len(ENT_FULL_CHORDS)
ENT_HARM_CHECK = {x["name"]: H.check(x["tune"], x["harm"]) for x in ENT_SECS}      # every section: no clash (tests/test_music_batch1.py)
ENT_BASS_CHECK = H.bass_check(ENT_FULL_BASS, ENT_FULL_CHORDS, 8)
# 20 hUGE orders: 0 = the intro and 15 = the bridge play 32 rows (src/music.c streams order k+2 while order k plays; gen_music pads them)
song("entertainer", 9, "A", ENT_FULL_MEL, ENT_FULL_BASS, swing=0xAA, groove=ENT_GROOVE, short_orders=(0, 15))
SONGS["entertainer"].update(ch1=ENT_FULL_HARM, ch1_inst=("harm50", "harm50"))

# which songs, in tune order after title/show
VENUES = ["susanna", "ballgame", "mountain", "funicula", "skaters", "hall", "sailor", "sakura", "weasel", "danube"]

# rows per bar (for the pitch-check table in tools/check_music.py)
BAR_ROWS = {"susanna": 8, "entertainer": 8, "galop": 4, "ballgame": 6, "mountain": 16, "funicula": 6,
            "skaters": 6, "hall": 8, "sakura": 8, "danube": 6, "weasel": 6, "sailor": 8}


# ---------------------------------------------------------------------------------------------
# The soundtrack player (title menu BONUS, src/jukebox.c): what each tune is called on screen.  gen_music.py writes
# build/jukebox_names.h from this in music.h's tune order (title, the jingles, the show, then VENUES), so adding a
# venue tune here and to VENUES is all the player needs.  Keyed by the song (or jingle) name, not the tune slot, so a
# venue inserted in the middle cannot shift the names.  Per tune: the list line (<= 18 characters), the full title
# (word-wrapped by gen_music to at most two lines of 18), the credit line and where the game plays it (<= 18 each).
# Characters: A-Z 0-9 space and . , ! ? ' - : (the HUD glyphs and the story font).  The pieces are the public-domain
# compositions named above; the three jingles are our own.
SOUNDTRACK = {
    "entertainer": ("THE ENTERTAINER", "THE ENTERTAINER", "SCOTT JOPLIN, 1902", "THE TITLE SCREEN"),
    "clear": ("LEVEL CLEAR", "LEVEL CLEAR", "ORIGINAL JINGLE", "A SHIFT WELL DONE"),
    "over": ("GAME OVER", "GAME OVER", "ORIGINAL JINGLE", "THE LAST LIFE LOST"),
    "bonus": ("BONUS ROUND", "BONUS ROUND", "ORIGINAL JINGLE", "THE BONUS ROUNDS"),
    "galop": ("GALOP INFERNAL", "GALOP INFERNAL", "J. OFFENBACH, 1858", "THE CAN-CAN SHOW"),
    "susanna": ("OH! SUSANNA", "OH! SUSANNA", "S. FOSTER, 1848", "THE SALOON"),
    "ballgame": ("TAKE ME OUT...", "TAKE ME OUT TO THE BALL GAME", "VON TILZER, 1908", "THE SPORTS BAR"),
    "mountain": ("ROUND THE MOUNTAIN", "SHE'LL BE COMING ROUND THE MOUNTAIN", "AMERICAN FOLK SONG", "THE LUMBER LODGE"),
    "funicula": ("FUNICULI, FUNICULA", "FUNICULI, FUNICULA", "LUIGI DENZA, 1880", "THE BISTRO"),
    "skaters": ("THE SKATERS' WALTZ", "THE SKATERS' WALTZ", "WALDTEUFEL, 1882", "THE IGLOO"),
    "hall": ("IN THE HALL OF...", "IN THE HALL OF THE MOUNTAIN KING", "EDVARD GRIEG, 1875", "THE ROBOT FACTORY"),
    "sakura": ("SAKURA SAKURA", "SAKURA SAKURA", "JAPANESE FOLK SONG", "THE TEAHOUSE"),
    "danube": ("THE BLUE DANUBE", "THE BLUE DANUBE", "JOHANN STRAUSS II", "THE SPACE LOUNGE"),
    "weasel": ("POP GOES THE...", "POP GOES THE WEASEL", "ENGLISH FOLK TUNE", "THE ZOO"),
    "sailor": ("DRUNKEN SAILOR", "DRUNKEN SAILOR", "TRADITIONAL SHANTY", "THE CHROME COW"),
}
