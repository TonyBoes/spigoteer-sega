"""Song sources for the buffered tunes (title, show, ten venue tunes).  Imported by gen_music.py.

All tunes are public domain compositions.  Oh! Susanna, Galop infernal and the tunes entered from
docs/music_specs.md follow the owner's note lists (Drunken Sailor: our transcription of the owner's pick); the arrangement (accompaniment, rhythm, instruments) is ours.  Notation: see gen_music.py.  One song row is one
unit note (an eighth note unless the comment says sixteenth); `tempo` is frames per row (60 fps).
The melody is channel 2 (pulse), the bass channel 3 (wave), the percussion channel 4 (noise);
channel 1 belongs to the sound effects.  Upper-case K S H are the quiet drum kit (kick, snare,
hat); lower-case k s h are the louder old kit the bonus tune uses.
"""

# chord -> (root, fifth) played by the bass (a seventh chord uses its triad's notes)
CHORD = {
    "C": ("C3", "G3"), "F": ("F2", "C3"), "G": ("G2", "D3"), "D": ("D3", "A3"),
    "Am": ("A2", "E3"), "Dm": ("D3", "A3"), "Em": ("E3", "B3"), "E": ("E3", "B3"),
    "Bm": ("B2", "F#3"), "A": ("A2", "E3"), "Bb": ("A#2", "F3"), "Eb": ("D#3", "A#3"),
    "F#": ("F#2", "C#3"), "C#7": ("C#3", "G#3"),
    "C7": ("C3", "G3"), "A7": ("A2", "E3"), "D7": ("D3", "A3"), "E7": ("E3", "B3"), "G7": ("G2", "D3"),
}


def oompah(chords, rows):
    """root / fifth bass, staccato.  rows per bar: 4 = 2/4 boom-chick, 6 = 3/4 oom-pah-pah,
    8 = 4/4 or 2/4 with sixteenth rows, 'c6' = 6/8 (two dotted beats)."""
    out = []
    for c in chords:
        if "/" in c:                       # two chords in one bar ("C/D7"): the root of each on its half
            a, b = c.split("/")
            h = {"c6": 3, 4: 2}.get(rows, 4)           # half a bar
            out += [f"{CHORD[a][0]}:{h}!", f"{CHORD[b][0]}:{h}!"]
            continue
        r, f = CHORD[c]
        if rows == 4:
            out += [f"{r}:2!", f"{f}:2!"]
        elif rows == 6:
            out += [f"{r}:2!", f"{f}:2!", f"{f}:2!"]
        elif rows == 8:
            out += [f"{r}:2!", f"{f}:2!", f"{r}:2!", f"{f}:2!"]
        elif rows == "c6":
            out += [f"{r}:3!", f"{f}:3!"]
        else:
            raise ValueError(rows)
    return " ".join(out)


def rep(text, n):
    return " ".join([text] * n)


SONGS = {}


def song(name, tempo, bufname, ch2, ch3, ch4="", inst=5, gap=True, stac_all=None, groove=""):
    """stac_all: (num, den) cuts every melody note after num/den of its length (staccato).
    groove: a short drum loop (tokens as ch4, one or two bars) that src/music.c plays on channel 4 by itself,
    over and over, in step with the song's rows.  It costs no pattern in the WRAM buffer (a 64-row pattern is
    not a whole number of 3/4 or 6/8 bars, so a shared hUGEDriver pattern could not keep the beat across orders).
    The song's length must be a whole number of grooves (gen_music checks)."""
    SONGS[name] = dict(tempo=tempo, buf=bufname, ch2=ch2, ch3=ch3, ch4=ch4, inst=inst, gap=gap, stac_all=stac_all,
                       groove=groove)


# GAME TEMPO.  The owner approved these tempos for the game (the melody notes stay exactly as the spec's; only the
# speed changes), in beats per minute of the beat the spec names; the spec's own tempo is in docs/music_specs.md and
# SPEC_BPM_ROWS in tests/test_sound.py.  tempo = frames per row is the nearest whole number (60 fps), so the tempo
# the game really plays is 3600 / (tempo x rows per beat): entertainer 8 -> 112.5, sakura 15 -> 120,
# funicula 11 -> 109.1 (dotted quarter), skaters / danube / ballgame 9 -> 200 (quarter).  Tunes not listed play
# at the spec tempo.
GAME_BPM = {"entertainer": 112, "sakura": 120, "funicula": 112, "skaters": 192, "danube": 192, "ballgame": 192}


# ---------------------------------------------------------------------------------------------
# "Oh! Susanna" (Stephen Foster, 1848), the cowboys' tune: the owner's spec.  Key C, 2/4, 15 frames
# per eighth note (120 bpm quarter).  Melody C4 = middle C.
A1 = "E4:1 G4:1 G4:1 A4:1  G4:1 E4:1 C4:1 D4:1  E4:1 E4:1 D4:1 C4:1  D4:2 C4:1 D4:1"
A2 = "E4:1 G4:1 G4:1 A4:1  G4:1 E4:1 C4:1 D4:1  E4:1 E4:1 D4:1 D4:1  C4:2 C4:1 D4:1"
A2_LAST = "E4:1 G4:1 G4:1 A4:1  G4:1 E4:1 C4:1 D4:1  E4:1 E4:1 D4:1 D4:1  C4:4"
CHORUS = "F4:2 F4:2  A4:2 A4:2  G4:1 G4:1 E4:1 C4:1  D4:2 C4:1 D4:1"
ENDING = A2_LAST
SUS_MEL = "C4:1 D4:1  " + "  ".join([A1, A2, A1, A2_LAST, CHORUS, ENDING])
SUS_CH = (["C", "C", "C", "G"] + ["C", "C", "G", "C"]) * 2 + ["F", "C", "C", "G"] + ["C", "C", "G", "C"]
SUS_BASS_BAR = {"C": "C3:2! G2:2!", "G": "G2:2! D3:2!", "F": "F2:2! C3:2!"}
SUS_BASS = "r:2 " + " ".join(SUS_BASS_BAR[c] for c in SUS_CH[:-1]) + " C3:4"
VERSE_D = "K:1 r:1 S:1 r:1"
CHORUS_D = "K:1 H:1 S:1 H:1"
SUS_DRUMS = "r:2 " + " ".join([VERSE_D] * 16 + [CHORUS_D] * 4 + [VERSE_D] * 3 + ["K:1 r:3"])
song("susanna", 15, "A", SUS_MEL, SUS_BASS, SUS_DRUMS)


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
# Title: "The Entertainer" (Scott Joplin, 1902), A section.  2/4, one row = a sixteenth note; quarter = 90
# is 10 frames per row (game tempo: 8 frames, 112 bpm, see GAME_BPM).  16 bars (bars 4, 8 and 16 end with the D D# pickup).  Bars 12-16 are low confidence.
ENT_BARS = [
    "E5:1 C6:2 E5:1 C6:2 E5:1 C6:1", "~:4 C6:1 D6:1 D#6:1 E6:1", "C6:1 D6:1 E6:2 B5:1 D6:2 C6:1",
    "~:4 R:2 D5:1 D#5:1", "E5:1 C6:2 E5:1 C6:2 E5:1 C6:1", "~:4 A5:1 G5:1 F#5:1 A5:1",
    "C6:1 E6:2 D6:1 C6:1 A5:1 D6:2", "~:4 R:2 D5:1 D#5:1", "E5:1 C6:2 E5:1 C6:2 E5:1 C6:1",
    "~:4 C6:1 D6:1 D#6:1 E6:1", "C6:1 D6:1 E6:2 B5:1 D6:2 C6:1", "~:4 C6:1 D6:1 E6:1 C6:1",
    "D6:1 E6:2 C6:1 D6:1 C6:1 E6:2", "C6:1 D6:1 E6:2 C6:1 D6:1 C6:2",
    "E6:1 C6:1 D6:2 E6:1 B5:1 D6:2", "C6:4 R:2 D5:1 D#5:1",
]
ENT_CHORDS = [
    "C", "C", "G7", "C", "C", "D7", "D7", "G7", "C", "C", "G7", "C", "C", "F", "G7", "C",
]
song("entertainer", 8, "A", " ".join(ENT_BARS), oompah(ENT_CHORDS, 8),
     groove="K:1 r:1 H:1 r:1 S:1 r:1 H:1 r:1")

# ---------------------------------------------------------------------------------------------
# Show: "Galop infernal" (Jacques Offenbach, Orphee aux enfers, 1858, the can-can), the owner's spec (docs/music_specs.md
# tune 10): key D, 2/4, quarter = 160 -> 11 frames per eighth row (163.6 bpm).  16 bars = 64 rows = one 64-row pattern per
# channel (buffer B holds 2 patterns), a pass is 704 frames (11.7 s).  The quarter notes of bars 3, 5, 11 and 13 are
# detached ('!').  Bass: oom-pah, root then fifth (bar 15 = D then A7).  Drums: a groove, kick / hat / snare / hat.
GAL = ["D5:4", "E5:1 G5:1 F#5:1 E5:1", "A5:2! A5:2!", "A5:1 B5:1 F#5:1 G5:1",
       "E5:2! E5:2!", "E5:1 G5:1 F#5:1 E5:1", "D5:1 D6:1 C#6:1 B5:1", "A5:1 G5:1 F#5:1 E5:1",
       "D5:4", "E5:1 G5:1 F#5:1 E5:1", "A5:2! A5:2!", "A5:1 B5:1 F#5:1 G5:1",
       "E5:2! E5:2!", "E5:1 G5:1 F#5:1 E5:1", "D5:1 A5:1 E5:1 F#5:1", "D5:2 R:2"]
GAL_CHORDS = ["D", "A7", "D", "D", "A7", "A7", "D", "A7", "D", "A7", "D", "D", "A7", "A7", "D/A7", "D"]
song("galop", 11, "B", " ".join(GAL), oompah(GAL_CHORDS, 4), groove="K:1 H:1 S:1 H:1")


# ---------------------------------------------------------------------------------------------
# Sports bar: "Take Me Out to the Ball Game" (Albert Von Tilzer, 1908), chorus.  3/4, key G, quarter = 168
# is 10.7 frames per eighth row: 11 (164 bpm; game tempo 9, see GAME_BPM).  32 bars.
TMO_BARS = [
    "G4:4 G5:2", "E5:2 D5:2 B4:2", "D5:6", "A4:6", "G4:4 G5:2", "E5:2 D5:2 B4:2", "D5:6", "~:6",
    "E5:2 D#5:2 E5:2", "B4:2 C5:2 D5:2", "E5:4 C5:2", "A4:6", "E5:4 E5:2", "E5:2 F#5:2 G5:2",
    "A5:2 F#5:2 E5:2", "D5:2 B4:2 A4:2", "G4:4 G5:2", "E5:2 D5:2 B4:2", "D5:6", "A4:4 B4:2",
    "G4:4 A4:2", "B4:2 C5:2 D5:2", "E5:6", "~:2 E5:2 F#5:2", "G5:2 R:4", "G5:2 R:4",
    "G5:2 F#5:2 E5:2", "D5:2 C#5:2 D5:2", "E5:6", "F#5:6", "G5:6", "~:2 R:4",
]
TMO_CHORDS = [
    "G", "Em", "D7", "D7", "G", "Em", "D", "D", "E7", "E7", "Am", "Am", "A7", "A7", "D", "D", "G",
    "Em", "D7", "D7", "G", "G7", "C", "C", "C", "A7", "D", "E7", "Am", "D7", "G", "G",
]
song("ballgame", 9, "A", " ".join(TMO_BARS), oompah(TMO_CHORDS, 6), groove="K:1 r:1 S:1 r:1 S:1 r:1")

# ---------------------------------------------------------------------------------------------
# Lumber lodge: "She'll Be Coming 'Round the Mountain" (American folk song).  4/4, key D, quarter = 160 is
# 11.25 frames per eighth row: 11.  16 bars; bar 16 ends with the pickup of the next pass.
MTN_BARS = [
    "D5:2 D5:2 D5:2 D5:2", "B4:2 A4:2 F#4:2 A4:2", "D5:8", "~:4 D5:2 E5:2",
    "F#5:2 F#5:2 F#5:2 F#5:2", "A5:2 F#5:2 E5:2 D5:2", "E5:8", "~:4 A5:2 G5:2",
    "F#5:2 F#5:2 F#5:2 F#5:2", "E5:2 D5:2 D5:2 D5:2", "B4:2 B4:2 B4:2 B4:2", "E5:2 D5:2 C#5:2 B4:2",
    "A4:2 A4:2 A4:2 A4:2", "F#5:2 E5:2 B4:2 C#5:2", "D5:8", "~:4 A4:2 B4:2",
]
MTN_CHORDS = [
    "D", "A7", "D", "D", "D", "D", "A7", "A7", "D", "D7", "G", "A7", "D", "A7", "D", "D",
]
song("mountain", 11, "A", " ".join(MTN_BARS), oompah(MTN_CHORDS, 8),
     " ".join(["K:1 r:1 S:1 r:1 K:1 r:1 S:1 r:1"] * 16))

# ---------------------------------------------------------------------------------------------
# Bistro: "Funiculi, Funicula" (Luigi Denza, 1880), verse and chorus.  6/8, key F, dotted quarter = 92 is
# 13 frames per eighth row.  25 bars; bars 9 and 25 end with the C5 pickup, so the loop is seamless.
FUN_BARS = [
    "F5:6", "~:2 F5:1 E5:2 E5:1", "C5:2 C5:1 D5:2 D5:1", "A4:3 A4:3", "~:2 A4:1 G4:2 F4:1", "F4:6",
    "R:2 A4:1 G4:2 F4:1", "F4:6", "~:1 R:4 C5:1", "E5:3 D5:1 R:2", "E5:3 D5:1 R:2",
    "F5:2 E5:1 D5:2 F5:1", "E5:3 R:3", "E5:3 D5:1 R:2", "E5:3 D5:1 R:2", "F5:2 E5:1 D5:2 F5:1",
    "C5:2 A4:1 A4:2 A4:1", "A4:2 A4:1 A4:2 A4:1", "A4:2 A4:1 A4:2 A4:1", "A4:2 A4:1 A4:2 A4:1",
    "F5:6", "G5:2 F5:1 D5:2 F5:1", "C5:2 A4:1 A4:2 Bb4:1", "C5:2 Bb4:1 A4:2 G4:1", "F4:3 R:2 C5:1",
]
FUN_CHORDS = [
    "F", "F", "F", "F", "C7", "F", "C7", "F", "F", "C7", "C7", "C7", "C7", "C7", "C7", "C7", "F",
    "A7", "Dm", "A7", "Dm", "Bb", "F", "C7", "F",
]
song("funicula", 11, "A", " ".join(FUN_BARS), oompah(FUN_CHORDS, "c6"), groove="K:1 r:1 S:1 K:1 r:1 S:1")

# ---------------------------------------------------------------------------------------------
# Arctic: "The Skaters' Waltz" (Emile Waldteufel, 1882), main theme, an octave above the source.  3/4, key G,
# quarter = 160: 11 frames per eighth row (about 164).  32 bars, no drums.  The spec's short slide up into
# bars 1, 5 and 9 is not done: hUGEDriver's portamento starts from a note already sounding, so it would
# need an extra row before each of those notes.
SKT_BARS = [
    "B4:6", "D5:4 E5:2", "E5:6", "~:6", "C5:6", "E5:4 F#5:2", "F#5:6", "~:6", "A5:6", "G5:4 B4:2",
    "D5:6", "C5:4 B4:2", "B4:6", "A4:6", "G4:2 E5:2 D5:2", "C5:2 B4:2 A4:2", "B4:6", "D5:4 E5:2",
    "E5:6", "~:6", "C5:6", "E5:4 F#5:2", "F#5:6", "~:6", "A5:6", "G5:4 B4:2", "D5:6", "C5:4 B4:2",
    "B4:6", "A4:6", "G4:6", "~:6",
]
SKT_CHORDS = [
    "G", "G", "D7", "D7", "D7", "D7", "G", "G", "Em", "Em", "Am", "Am", "D", "D7", "G", "D7", "G",
    "G", "D7", "D7", "D7", "D7", "G", "G", "Em", "Em", "Am", "Am", "D", "D7", "G", "G",
]
song("skaters", 9, "A", " ".join(SKT_BARS), oompah(SKT_CHORDS, 6), groove="K:1 r:1 H:1 r:1 H:1 r:1")

# ---------------------------------------------------------------------------------------------
# Robot factory: "In the Hall of the Mountain King" (Edvard Grieg, 1875).  4/4, key B minor, quarter = 120 =
# 15 frames per eighth row.  16 bars, every melody note staccato (cut after half its length), bass = a root
# ostinato in quarter notes: B in the A phrases, F# in the answer (bars 9-12).
HALL_BARS = [
    "B3:1 C#4:1 D4:1 E4:1 F#4:1 D4:1 F#4:2", "E#4:1 C#4:1 E#4:2 E4:1 C4:1 E4:2",
    "B3:1 C#4:1 D4:1 E4:1 F#4:1 D4:1 F#4:1 B4:1", "A4:1 F#4:1 D4:1 F#4:1 A4:4",
    "B3:1 C#4:1 D4:1 E4:1 F#4:1 D4:1 F#4:2", "E#4:1 C#4:1 E#4:2 E4:1 C4:1 E4:2",
    "B3:1 C#4:1 D4:1 E4:1 F#4:1 D4:1 F#4:1 B4:1", "A4:1 F#4:1 D4:1 F#4:1 A4:4",
    "F#4:1 G#4:1 A#4:1 B4:1 C#5:1 A#4:1 C#5:2", "D5:1 A#4:1 D5:2 C#5:1 A#4:1 C#5:2",
    "F#4:1 G#4:1 A#4:1 B4:1 C#5:1 A#4:1 C#5:2", "D5:1 A#4:1 D5:2 C#5:4",
    "B3:1 C#4:1 D4:1 E4:1 F#4:1 D4:1 F#4:2", "E#4:1 C#4:1 E#4:2 E4:1 C4:1 E4:2",
    "B3:1 C#4:1 D4:1 E4:1 F#4:1 D4:1 F#4:1 B4:1", "A4:1 F#4:1 D4:1 F#4:1 A4:4",
]
HALL_CHORDS = [
    "Bm", "C#7/C", "Bm", "D", "Bm", "C#7/C", "Bm", "D", "F#", "F#", "F#", "F#", "Bm", "C#7/C", "Bm",
    "D",
]
HALL_BASS = " ".join(("F#2:2! " if 9 <= i <= 12 else "B2:2! ") * 4 for i in range(1, 17))
song("hall", 15, "A", " ".join(HALL_BARS), HALL_BASS,
     " ".join(["K:1 r:3 S:1 r:3"] * 16), stac_all=(1, 2))

# ---------------------------------------------------------------------------------------------
# Teahouse: "Sakura Sakura" (Japanese traditional).  4/4, key A minor (A B C E F), quarter = 100: 18 frames
# per eighth row (the spec's ~100 bpm).  14 bars, about 34 s.  Bass: a soft A / E drone, not chords.
SAK_BARS = [
    "A4:2 A4:2 B4:4", "A4:2 A4:2 B4:4", "A4:2 B4:2 C5:2 B4:2", "A4:2 B4:1 A4:1 F4:4",
    "E4:2 C4:2 E4:2 F4:2", "E4:2 E4:1 C4:1 B3:4", "A4:2 B4:2 C5:2 B4:2", "A4:2 B4:1 A4:1 F4:4",
    "E4:2 C4:2 E4:2 F4:2", "E4:2 E4:1 C4:1 B3:4", "A4:2 A4:2 B4:4", "A4:2 A4:2 B4:4",
    "E4:2 F4:2 B4:1 A4:1 F4:2", "E4:4 R:4",
]
SAK_CHORDS = [
    "Am", "Am", "Am", "Dm", "Am", "E", "Am", "Dm", "Am", "E", "Am", "Am", "Dm", "Am",
]
song("sakura", 15, "A", " ".join(SAK_BARS), " ".join(["A2:4 E3:4"] * 14), "", gap=True,
     groove="K:1 r:1 H:1 r:1 K:1 r:1 H:1 r:1")

# ---------------------------------------------------------------------------------------------
# Space lounge: "The Blue Danube" (Johann Strauss II, 1867), first waltz theme in the spec's G major.  3/4,
# quarter = 160: 11 frames per eighth row.  32 bars, no drums.  As the spec suggests, the first note of
# each 'X R Y' bar is held through the rest (X:2 R:2 Y:2 -> X:4 Y:2).  No transposition: the lowest note, G3,
# stays above the bass (G2 root, D3 fifth).
DAN_BARS = [
    "G3:2 B3:2 D4:2", "D4:2 R:2 D5:2", "D5:2 R:2 B4:2", "B4:2 R:2 G3:2", "G3:2 B3:2 D4:2",
    "D4:2 R:2 D5:2", "D5:2 R:2 C5:2", "C5:2 R:2 F#4:2", "F#4:2 A4:2 C5:2", "C5:2 R:2 E5:2",
    "E5:2 R:2 C5:2", "C5:2 R:2 F#4:2", "F#4:2 A4:2 C5:2", "C5:2 R:2 E5:2", "E5:2 R:2 B4:2",
    "B4:2 R:2 G3:2", "G3:2 B3:2 D4:2", "G4:2 R:2 G5:2", "G5:2 R:2 D5:2", "D5:2 R:2 G3:2",
    "G3:2 B3:2 D4:2", "G4:2 R:2 G5:2", "G5:2 R:2 E5:2", "E5:2 R:2 A4:2", "A4:2 C5:2 E5:2", "E5:6",
    "~:2 C#5:2 D5:2", "B5:6", "~:2 G5:2 B4:2", "B4:4 A4:2", "E5:4 D5:2", "G4:2 R:1 G4:1 G4:2",
]
DAN_CHORDS = [
    "G", "G", "G", "G", "G", "G", "D7", "D7", "D7", "D7", "D7", "D7", "D7", "D7", "G", "G", "G",
    "G", "G", "G", "G", "G", "C", "Am", "Am", "A7", "A7", "G", "G", "D7", "D7", "G",
]


def hold_through_rest(bar):
    t = bar.split()
    if len(t) == 3 and t[1] == "R:2" and t[0].endswith(":2"):
        return f"{t[0][:-2]}:4 {t[2]}"
    return bar


song("danube", 9, "A", " ".join(hold_through_rest(b) for b in DAN_BARS), oompah(DAN_CHORDS, 6),
     groove="K:1 r:1 H:1 r:1 H:1 r:1")

# ---------------------------------------------------------------------------------------------
# Zoo: "Pop Goes the Weasel" (English folk tune, c. 1850), verse and second strain.  6/8, key G, dotted
# quarter = 100: 12 frames per eighth row.  16 bars.  The last rest of bar 16 becomes the D4 pickup (the
# spec's note for looping).  Bar 15 is C for the first dotted beat and D7 for the second.
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

# ---------------------------------------------------------------------------------------------
# The Chrome Cow: "Drunken Sailor" (traditional sea shanty), the owner's pick, played fast and punky (docs/music_specs.md
# tune 11).  4/4, D Dorian, quarter = 200: 9 frames per eighth row.  16 bars: the verse, then the chorus.  Punk
# arrangement: every melody note cut short (3/4 of its length), the bass driving root eighth notes with the fifth on the
# last two, a kick / hat / snare groove with a double kick.  In the Last call the band plays faster (src/music.c
# music_fast: one frame less per row, 225 bpm).
SAI_BARS = [
    "A4:2 A4:1 A4:1 A4:2 A4:1 A4:1", "A4:2 D4:2 F4:2 A4:2", "G4:2 G4:1 G4:1 G4:2 G4:1 G4:1", "G4:2 C4:2 E4:2 G4:2",
    "A4:2 A4:1 A4:1 A4:2 A4:1 A4:1", "A4:2 B4:2 C5:2 D5:2", "C5:2 A4:2 G4:2 E4:2", "D4:4 D4:4",
    "A4:4 A4:4", "A4:2 D4:2 F4:2 A4:2", "G4:4 G4:4", "G4:2 C4:2 E4:2 G4:2",
    "A4:4 A4:4", "A4:2 B4:2 C5:2 D5:2", "C5:2 A4:2 G4:2 E4:2", "D4:4 D4:4",
]
SAI_CHORDS = ["Dm", "Dm", "C", "C", "Dm", "Dm", "C", "Dm"] * 2


def punk_bass(chords):
    """Driving eighth notes: the root six times, the fifth twice, every one cut short."""
    return " ".join(" ".join([f"{CHORD[c][0]}:1!"] * 6 + [f"{CHORD[c][1]}:1!"] * 2) for c in chords)


song("sailor", 9, "A", " ".join(SAI_BARS), punk_bass(SAI_CHORDS), stac_all=(3, 4),
     groove="K:1 H:1 S:1 H:1 K:1 K:1 S:1 H:1")

# which songs, in tune order after title/show
VENUES = ["susanna", "ballgame", "mountain", "funicula", "skaters", "hall", "sailor", "sakura", "weasel", "danube"]

# rows per bar (for the pitch-check table in tools/check_music.py)
BAR_ROWS = {"susanna": 4, "entertainer": 8, "galop": 4, "ballgame": 6, "mountain": 8, "funicula": 6,
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
