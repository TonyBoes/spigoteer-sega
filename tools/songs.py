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


SONGS = {}
LEGATO_LEAD = 6      # gen_music.DUTY: the legato lead
SUNG_ARTIC = 3       # frames of silence between two sung notes of the same pitch (legato=)


def song(name, tempo, bufname, ch2, ch3, ch4="", inst=5, gap=True, stac_all=None, groove="", legato=None, start=0, swing=0):
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
    0xAA: rows of 9, 8, 9, 8 frames = 105.9 bpm at tempo 9 for the Entertainer."""
    if legato:
        inst = LEGATO_LEAD
    SONGS[name] = dict(tempo=tempo, buf=bufname, ch2=ch2, ch3=ch3, ch4=ch4, inst=inst, gap=gap, stac_all=stac_all,
                       groove=groove, legato=legato, start=start, swing=swing, ch1="", ch1_inst=None)


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
SUS_BASS_BAR = {"C": "C3:4! G2:4!", "G": "G2:4! D3:4!", "F": "F2:4! C3:4!"}
SUS_BASS = " ".join(SUS_BASS_BAR[c] for c in SUS_CH)
VERSE_D = "K:2 r:2 S:2 r:2"
CHORUS_D = "K:2 H:2 S:2 H:2"
SUS_DRUMS = " ".join([VERSE_D] * 16 + [CHORUS_D] * 4 + [VERSE_D] * 4)
song("susanna", 8, "A", SUS_MEL, SUS_BASS, SUS_DRUMS, legato=SUNG_ARTIC)
# Harmony (music step 5): a second voice in thirds and sixths under the verses (one note an eighth at most, held where it
# repeats), a slow counter-line of chord tones under the chorus ("Oh! Su-san-na"), on the held 12.5% pad like a second
# singer.
_t = H.Tune(SUS_MEL, SUS_CH, 8, 4, "C")
harmony("susanna", _t, " ".join([H.follow(_t, (1, 16), "G3", "A4", grid=2), H.guide(_t, (17, 20), "G3", "E4"),
                                 H.follow(_t, (21, 24), "G3", "A4", grid=2)]), ("pad", "pad"))


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
song("entertainer", 9, "A", " ".join(ENT_BARS), oompah(ENT_CHORDS, 8), swing=0xAA,
     groove="K:1 r:1 H:1 r:1 S:1 r:1 H:1 r:1")
# Harmony (the owner's "1b", 2026-10-12): a second voice in thirds and sixths under the whole tune, in the melody's own
# rhythm (grid 1: it moves on any sixteenth, the off-beat ragtime notes included; merge=False re-strikes a repeated note
# as the melody does), on the 50% "harm50" pulse (decaying like a piano's second hand).  C3-B4 keeps it under the melody.
_t = H.Tune(" ".join(ENT_BARS), ENT_CHORDS, 8, 4, "C")
harmony("entertainer", _t, H.follow(_t, (1, 32), "C3", "B4", grid=1, merge=False), ("harm50", "harm50"))

# ---------------------------------------------------------------------------------------------
# Show: "Galop infernal" (Jacques Offenbach, Orphee aux enfers, 1858, the can-can), the owner's spec (docs/music_specs.md
# tune 10): key D, 2/4, quarter = 160 -> 11 frames per eighth row (163.6 bpm).  16 bars = 64 rows = one 64-row pattern per
# channel (buffer B holds 2 patterns), a pass is 704 frames (11.7 s).  The quarter notes of bars 3, 5, 11 and 13 are
# detached ('!').  Bass: oom-pah, root then fifth (bar 15 = D then A7).  Drums: a groove, kick / hat / snare / hat.
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
song("galop", 11, "B", " ".join(GAL), oompah(GAL_CHORDS, 4), groove="K:1 H:1 S:1 H:1")
# Harmony (music step 5): light off-beat stabs, the can-can's "pah" between the bass's beats: a chord tone (D or A7)
# under the melody on every second eighth, short and dry (the 25% "stab").
_t = H.Tune(" ".join(GAL), GAL_CHORDS, 4, 2, "D")
harmony("galop", _t, H.stabs(_t, (1, 16), "F#4", "D5", [(1, False), (1, True)] * 2), ("stab", "stab"))


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
song("ballgame", 9, "A", " ".join(TMO_BARS), oompah(TMO_CHORDS, 6), groove="K:1 r:1 S:1 r:1 S:1 r:1")
# Harmony (music step 5): the first sixteen bars hold one chord tone a chord (the organ's sustained chord: the third or
# seventh first, G#4 in the E7 bars), the second sixteen a voice in thirds and sixths under "let me root, root, root",
# one note for each melody eighth (grid 1, no merging).  Owner's pick (harmony demos, 2026-10-12): held, then thirds.
_t = H.Tune(" ".join(TMO_BARS), TMO_CHORDS, 6, 2, "G")
harmony("ballgame", _t, " ".join([H.guide(_t, (1, 16), "D4", "C5"),
                                  H.follow(_t, (17, 32), "D4", "D5", grid=1, merge=False, inst="/2")]), ("pad", "harm"))

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
song("mountain", MTN_TEMPO, "A", " ".join(MTN_BARS), oompah(MTN_CHORDS, 16),
     " ".join(["K:2 r:2 S:2 r:2 K:2 r:2 S:2 r:2"] * 16), legato=SUNG_ARTIC, start=MTN_PICKUP_ROW)
# Harmony (music step 6): the Susanna approach, a second voice in thirds and sixths under the whole verse in the melody's
# own rhythm (it moves where the melody does, the 2/6 snap included; grid 2 = an eighth or finer), on the held 12.5% pad.
# The pickup row is a note boundary of the line (gen_music asserts it), so the first play can start the line there.
_t = H.Tune(" ".join(MTN_BARS), MTN_CHORDS, 16, 4, "D")
harmony("mountain", _t, H.follow(_t, (1, 16), "A3", "F#5", grid=2), ("pad", "pad"))

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
song("funicula", 10, "A", " ".join(FUN_BARS), oompah(FUN_CHORDS, "c6"), groove="K:1 r:1 S:1 K:1 r:1 S:1", swing=0xAA)
# Tempo (owner pick, harmony demos 2026-10-12): rows alternate 10 and 9 frames (swing 0xAA, as the Entertainer) = 9.5 on
# average = 126 bpm for the dotted quarter; a 6-row bar has the same long-short pattern every time.  Harmony unchanged.
# Harmony (music step 5): the verse in thirds and sixths under the melody, one note a dotted beat (the echoes "and so
# do I" answered in thirds, B-flat and C under D and E); the chorus ("Funiculi, funicula") a slow line of held chord
# tones under the repeated A, through the A7 / D minor turn (C#4 / D4).
_t = H.Tune(" ".join(FUN_BARS), FUN_CHORDS, 6, 3, "F")
harmony("funicula", _t, " ".join([H.follow(_t, (1, 16), "C4", "C5", grid=3), H.guide(_t, (17, 25), "C4", "G4", inst="/2")]),
        ("harm", "pad"))

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
song("skaters", 9, "A", " ".join(SKT_BARS), oompah(SKT_CHORDS, 6), groove="K:1 r:1 H:1 r:1 H:1 r:1")
# Harmony (music step 5): the first strain holds one chord tone a bar on the pad (the waltz's sustained middle voice:
# B, then C, the seventh of D7, back to B), the repeat a voice in thirds and sixths under the melody, one note a beat.
_t = H.Tune(" ".join(SKT_BARS), SKT_CHORDS, 6, 2, "G")
harmony("skaters", _t, " ".join([H.guide(_t, (1, 16), "D4", "D5", per_bar=True),
                                 H.follow(_t, (17, 32), "D4", "E5", grid=2, inst="/2")]), ("pad", "harm"))

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
HALL_BASS = " ".join(("F#2:2! " if 9 <= i <= 12 else "B2:2! ") * 4 for i in range(1, 17))
song("hall", 15, "A", " ".join(HALL_BARS), HALL_BASS,
     " ".join(["K:1 r:3 S:1 r:3"] * 16), stac_all=(1, 2))
# Harmony (music step 5): a voice in thirds and sixths UNDER the melody the whole way (G3 to B4, never crossing, one note
# for each melody eighth, grid 1, no merging), a plucked "harm" voice.  The motif creeps down to B3 over the B2 bass, so
# the line sits right above the bass: dark and a little thick there.  Owner's pick (harmony demos, 2026-10-12): thirds.
_t = H.Tune(" ".join(HALL_BARS), HALL_CHORDS, 8, 2, "Bm")
harmony("hall", _t, H.follow(_t, (1, 16), "G3", "B4", grid=1, merge=False), ("harm", "harm"))

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


song("sakura", 12, "A", " ".join(SAK_BARS), sakura_bass(SAK_CHORDS), "", gap=True, stac_all=(3, 4),
     groove="K:1 r:1 H:1 K:1 K:1 r:1 H:1 H:1 K:1 r:1 H:1 K:1 K:1 r:1 S:1 S:1")
# Harmony (music step 5): a koto's second string, a fourth or fifth under the melody (E under A, E under B), one plucked
# note per melody note on the beat, only the scale's notes (A B C E F: the E chord's G# is left out).
_t = H.Tune(" ".join(SAK_BARS), SAK_CHORDS, 8, 2, "Asak", strict=True)
harmony("sakura", _t, H.follow(_t, (1, 14), "E3", "A4", prefer=(5, 7, 3, 4, 8, 9), grid=2, merge=False), ("pluck", "pluck"))

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
song("danube", 9, "A", " ".join(DAN_BARS), oompah(DAN_CHORDS, 6),
     groove="K:1 r:1 H:1 r:1 H:1 r:1")
# Harmony (music step 5): a voice in thirds and sixths under the melody (G3 to A5, one note for each melody eighth, grid 1,
# no merging) through bar 24, the closing phrase (bars 25-32) one held chord tone a bar on the pad, G3 to E5.  Owner's
# pick (harmony demos, 2026-10-12): thirds, the last phrase held.
_t = H.Tune(" ".join(DAN_BARS), DAN_CHORDS, 6, 2, "C")
harmony("danube", _t, " ".join([H.follow(_t, (1, 24), "G3", "A5", grid=1, merge=False),
                                H.guide(_t, (25, 32), "G3", "E5", inst="/2")]), ("harm", "pad"))

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
song("weasel", 12, "A", " ".join(WEA_BARS), oompah(WEA_CHORDS, "c6"),
     " ".join(["K:1 r:2 S:1 r:2"] * 16))
# Harmony (music step 5): the verse (bars 1-8) short dry stabs on the 6/8 off-beats (the bass plays the two dotted beats,
# the stabs the two eighths after each: A3 to D5), the second strain (bars 9-16) a voice in thirds and sixths under the
# melody, one note for each melody eighth (grid 1, no merging).  Owner's pick (harmony demos, 2026-10-12): stabs, then thirds.
_t = H.Tune(" ".join(WEA_BARS), WEA_CHORDS, 6, 3, "G")
harmony("weasel", _t, " ".join([H.stabs(_t, (1, 8), "A3", "D5", [(1, False), (1, True), (1, True)] * 2),
                                H.follow(_t, (9, 16), "A3", "D5", grid=1, merge=False, inst="/2")]), ("stab", "harm"))

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


song("sailor", 9, "A", " ".join(SAI_BARS), punk_bass(SAI_CHORDS), stac_all=(3, 4),
     groove="K:1 H:1 S:1 H:1 K:1 K:1 S:1 H:1")
# Harmony (music step 5): the verse gets punk off-beat upstrokes (a short chord tone on every second eighth: D or F for D
# minor, C or E for C), the chorus ("Hur-ray and up she ri-ses") a voice in thirds under the melody, struck on each
# eighth like a second shouting voice.
_t = H.Tune(" ".join(SAI_BARS), SAI_CHORDS, 8, 2, "Ddor")
harmony("sailor", _t, " ".join([H.stabs(_t, (1, 8), "C4", "A4", [(1, False), (1, True)] * 4),
                                H.follow(_t, (9, 16), "A3", "A4", grid=2, merge=False, inst="/2")]), ("stab", "harm"))

# ---------------------------------------------------------------------------------------------
# The credits tune (src/credits.c; owner picked draft "C3", 2026-10-17): The Entertainer's intro, then the strains the title tune
# does not use (the C strain in F, the bridge, the D strain), then the A strain's first three bars and a held C, in a slow warm
# style (15 frames a row, no drums, held root / fifth bass, the title's thirds on the 50% pulse).  A pass is 352 rows = 88 s: not
# a venue tune (it is no VENUES entry, no jukebox item): gen_music plays it once as a jingle and streams its patterns (12 of
# them: the buffer holds 8, see gen_music.CREDITS and src/music.c).  The notes were read from the Mutopia Project score
# entertainer.ly (Public Domain, 1902 edition) by the draft generator (tools/music_drafts.py on the drafts branch); they are
# data here so that no score file is needed to build.  The bass chords and the harmony (tools/harmony.py follow) are ours.
CR_MEL = (
    "D5:1 E5:1 C5:1 A4:2 B4:1 G4:2 D5:1 E5:1 C5:1 A4:2 B4:1 G4:2 D5:1 E5:1 C5:1 A4:2 B4:1 A4:1 G#4:1 G4:2 r:2 G4:2 D4:1 "
    "D#4:1 A4:1 G#4:1 A4:4 C5:2 D5:8 F4:1 E4:1 F4:4 A4:2 A#4:7 G4:1 D4:2 G4:1 D4:2 G4:1 D4:2 C4:4 F4:4 E4:1 G#4:1 B4:1 E5:2 "
    "D5:1 B4:1 C5:1 A4:4 A#4:4 A4:1 G#4:1 A4:4 C5:2 D5:8 F4:1 E4:1 F4:4 A4:2 A#4:7 G4:1 D4:2 G4:1 D4:2 G4:1 D4:2 C4:4 F4:3 "
    "F4:1 A4:1 C5:2 G4:2 C4:1 D4:1 E4:1 F5:2 r:2 F5:2 r:2 C5:2 A4:1 C5:2 A4:1 C5:1 A4:1 G4:1 C5:1 E5:1 G5:2 E5:1 C5:1 G4:1 "
    "A4:2 C5:2 E5:1 D5:2 C5:1 C5:4 C5:2 r:2 F4:2 E4:1 F4:2 E4:1 F4:2 r:1 A4:1 D5:1 A4:1 C5:1 D5:1 C5:1 A4:1 G4:2 F#4:1 G4:2 "
    "F#4:1 G4:2 r:1 C5:1 E5:1 C5:1 D5:1 E5:1 D5:1 C5:1 D5:2 C#5:1 D5:2 C#5:1 D5:2 r:1 F5:1 A5:1 F5:1 G5:1 A5:1 G5:1 F5:1 "
    "C6:1 C6:1 C6:4 A5:2 G5:2 G4:1 G4:1 G4:2 G4:2 F4:2 E4:1 F4:2 E4:1 F4:2 r:1 A4:1 D5:1 A4:1 C5:1 D5:1 C5:1 A4:1 G4:2 "
    "F#4:1 G4:2 F#4:1 G4:2 r:1 C5:1 E5:1 C5:1 D5:1 E5:1 D5:1 C5:1 A4:1 G#4:1 A4:1 G5:2 F5:2 C5:1 E5:1 D#5:1 E5:1 A5:2 C6:1 "
    "G5:1 E5:1 C5:2 C5:2 E5:1 D5:2 C5:1 C5:4 C5:2 r:2 E4:1 C5:2 E4:1 C5:2 E4:1 C5:1 ~:5 C5:1 D5:1 D#5:1 E5:1 C5:1 D5:1 E5:2 "
    "B4:1 D5:2 C5:8"
)
CR_BASS = (
    "G2:4 D3:4 G2:4 D3:4 G2:4 D3:4 G2:4 D3:4 F2:4 C3:4 A#2:4 F3:4 D3:4 A3:4 G2:4 D3:4 A#2:4 G2:4 F2:4 D3:4 E3:4 B3:4 A2:4 "
    "C3:4 F2:4 C3:4 A#2:4 F3:4 D3:4 A3:4 G2:4 D3:4 A#2:4 G2:4 F2:4 C3:4 C3:4 G3:4 F2:4 C3:4 F2:4 F#2:4 C3:4 G3:4 D3:4 G2:4 "
    "C3:4 G3:4 D3:4 A3:4 D3:4 A3:4 C3:4 G3:4 C3:4 G3:4 G2:4 D3:4 G2:4 D3:4 F#2:4 C3:4 C3:4 G3:4 D3:4 A3:4 D3:4 A3:4 C3:4 "
    "G3:4 C3:4 G3:4 F2:4 C3:4 C3:4 G3:4 D3:4 G2:4 C3:4 G3:4 C3:4 G3:4 F2:4 C3:4 G2:4 D3:4 C3:4 G3:4"
)
CR_HARM = (
    "B4:1 B4:1 G4:1 F4:2 G4:1 B3:2 B4:1 B4:1 G4:1 F4:2 G4:1 B3:2 B4:1 B4:1 G4:1 F4:2 G4:1 F4:1 F4:1 B3:2 r:2 B3:2 B3:1 B3:1 "
    "F4:1 F4:1 F4:4 A4:2 A#4:8 D4:1 A3:1 D4:4 F4:2 G4:7 D4:1 A#3:2 A#3:1 A#3:1 A#3:1 A#3:1 A#3:2 A3:4 D4:4 G#3:1 E4:1 G#4:1 "
    "G#4:2 B4:1 G#4:1 G#4:1 E4:4 G4:4 F4:1 F4:1 F4:4 A4:2 A#4:8 D4:1 A3:1 D4:4 F4:2 G4:7 D4:1 A#3:2 A#3:1 A#3:1 A#3:1 A#3:1 "
    "A#3:2 A3:4 C4:3 C4:1 C4:1 E4:2 E4:2 E3:1 A#3:1 C4:1 A4:2 r:2 A4:2 r:2 A4:2 F4:1 A4:1 A4:1 F#4:1 A4:1 F#4:1 E4:1 E4:1 "
    "G4:1 B4:2 G4:1 E4:1 E4:1 F#4:2 A4:2 G4:1 B4:2 G4:1 E4:4 E4:2 r:2 D4:2 A3:1 D4:2 A3:1 D4:2 r:1 F4:1 F4:1 F4:1 A4:1 A4:1 "
    "A4:1 F4:1 E4:2 D4:1 E4:2 D4:1 E4:2 r:1 E4:1 G4:1 E4:1 G4:1 G4:1 G4:1 E4:1 B4:2 F4:1 B4:2 F4:1 B4:2 r:1 A4:1 G4:1 A4:1 "
    "B4:1 G4:1 B4:1 A4:1 A4:1 A4:1 A4:4 F#4:2 B4:2 E4:1 E4:1 E4:2 E4:2 D4:2 A3:1 D4:2 A3:1 D4:2 r:1 F4:1 F4:1 F4:1 A4:1 "
    "A4:1 A4:1 F4:1 E4:2 D4:1 E4:2 D4:1 E4:2 r:1 E4:1 G4:1 E4:1 G4:1 G4:1 G4:1 E4:1 F4:1 F4:1 F4:1 B4:2 A4:2 A4:1 G4:1 G4:1 "
    "G4:1 G4:2 G4:1 B4:1 G4:1 A4:2 A4:2 G4:1 B4:2 G4:1 E4:4 E4:2 r:2 C4:1 E4:2 C4:1 E4:2 C4:1 E4:1 A4:4 E4:1 E4:1 G4:1 G4:1 "
    "G4:1 G4:1 B4:1 B4:2 G4:1 B4:2 E4:8"
)
song("credits", 15, "A", CR_MEL, CR_BASS, "", inst=5)
SONGS["credits"].update(ch1=CR_HARM, ch1_inst=("harm50", "harm50"))

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
