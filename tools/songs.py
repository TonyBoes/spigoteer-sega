"""Song sources for the buffered tunes (title, show, nine venue tunes).  Imported by gen_music.py.

All tunes are public domain compositions; the notes are entered from memory and the arrangement
(accompaniment, rhythm, instruments) is ours.  Notation: see gen_music.py.  One song row is one
unit note (an eighth note unless the comment says sixteenth); `tempo` is frames per row (60 fps).
The melody is channel 2 (pulse), the bass channel 3 (wave), the percussion channel 4 (noise);
channel 1 belongs to the sound effects.  Upper-case K S H are the quiet drum kit (kick, snare,
hat); lower-case k s h are the louder old kit the bonus tune uses.
"""

# chord -> (root, fifth) played by the bass
CHORD = {
    "C": ("C3", "G3"), "F": ("F2", "C3"), "G": ("G2", "D3"), "D": ("D3", "A3"),
    "Am": ("A2", "E3"), "Dm": ("D3", "A3"), "Em": ("E3", "B3"), "E": ("E3", "B3"),
    "Bm": ("B2", "F#3"), "A": ("A2", "E3"), "Bb": ("A#2", "F3"), "Eb": ("D#3", "A#3"),
}


def oompah(chords, rows):
    """root / fifth bass, staccato.  rows per bar: 4 = 2/4 boom-chick, 6 = 3/4 oom-pah-pah,
    8 = 4/4 or 2/4 with sixteenth rows, 'c6' = 6/8 (two dotted beats)."""
    out = []
    for c in chords:
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


def song(name, tempo, bufname, ch2, ch3, ch4="", inst=5, gap=True):
    SONGS[name] = dict(tempo=tempo, buf=bufname, ch2=ch2, ch3=ch3, ch4=ch4, inst=inst, gap=gap)


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
# Title: "The Entertainer" (Scott Joplin, 1902), the opening A strain.  2/4, one row = a sixteenth
# note, 9 frames per row (about 100 bpm).  Loop: pickup D D# | 8 bars.
ENT_1 = "E5:1 C6:2 E5:1 C6:2 E5:1 C6:4 r:1 C6:1 D6:1 D#6:1 E6:1"     # bars 1-2 (the long C is tied over the barline)
ENT_2 = "C6:1 D6:1 E6:2 B5:1 D6:2 C6:5 r:2 D5:1 D#5:1"                 # bars 3-4, ending on the pickup
ENT_3 = "C6:1 D6:1 E6:2 B5:1 D6:2 C6:1  C6:2 G5:2 E5:2 C5:2"           # bars 7-8: the resolution
song("entertainer", 9, "A", "D5:1 D#5:1  " + " ".join([ENT_1, ENT_2, ENT_1, ENT_3]),
     "r:2 " + oompah(["C", "C", "G", "C", "C", "C", "G", "C"], 8))

# ---------------------------------------------------------------------------------------------
# Show: "Galop infernal" (Jacques Offenbach, 1858, the can-can), 2/4, 13 frames per eighth row
# (about 140 bpm).  12 bars, about 10 s; the show lasts 6 s so the main theme is what is heard.
GAL = ["E5:1 E5:1 E5:1 E5:1", "E5:1 D5:1 C5:2",
       "D5:1 D5:1 D5:1 D5:1", "D5:1 C5:1 B4:2",
       "C5:1 C5:1 C5:1 C5:1", "C5:1 D5:1 E5:2",
       "G5:1 F5:1 E5:1 D5:1", "C5:3 r:1",
       "G5:1 G5:1 G5:1 G5:1", "G5:1 A5:1 G5:2",
       "E5:1 D5:1 C5:1 B4:1", "C5:3 r:1"]
song("galop", 13, "B", " ".join(GAL),
     oompah(["C", "C", "G", "G", "C", "C", "G", "C", "C", "C", "G", "C"], 4),
     rep("K:1 S:1 K:1 S:1", 12))

# ---------------------------------------------------------------------------------------------
# Sports bar: "Take Me Out to the Ball Game" (Albert Von Tilzer, 1908), chorus.  3/4, 17 frames per
# eighth row.  Key C.
TMO_BARS = [
    "C5:2 A4:2 G4:1 E4:1", "G4:2 D4:2 C4:2",          # Take me out to the ball game
    "C5:2 A4:2 G4:1 E4:1", "G4:2 A4:3 r:1",           # Take me out with the crowd
    "E5:2 E5:1 D5:1 C5:2", "D5:2 E5:2 G4:2",          # Buy me some peanuts and Cracker Jack
    "E5:2 E5:1 D5:1 C5:2", "D5:2 C5:2 A4:2",          # I don't care if I never get back
    "G4:2 G4:1 G4:1 G4:2", "A4:2 G4:2 E4:2",          # Let me root root root for the home team
    "G4:2 G4:1 G4:1 A4:2", "G4:4 r:2",                # If they don't win it's a shame
    "C5:2 C5:2 C5:2", "D5:2 E5:2 D5:2",               # For it's one, two, three strikes
    "C5:2 A4:2 G4:1 E4:1", "G4:2 E4:2 C4:2",          # you're out at the old ball game
]
TMO_CH = ["C", "G", "C", "F", "C", "G", "C", "G", "C", "F", "C", "G", "C", "G", "C", "C"]
song("ballgame", 17, "A", "C4:2 " + " ".join(TMO_BARS), "r:2 " + oompah(TMO_CH, 6),
     "r:2 " + rep("K:1 r:1 H:1 r:1 H:1 r:1", 16))

# ---------------------------------------------------------------------------------------------
# Lumber lodge: "She'll Be Coming 'Round the Mountain" (American folk song, 19th century).  4/4,
# 14 frames per eighth row.  Key C.
MTN = [
    "C5:2 C5:1 C5:1 C5:1 E5:1 E5:2", "D5:2 C5:2 D5:2 r:1 G4:1",
    "C5:2 C5:1 C5:1 C5:1 E5:1 E5:2", "D5:2 C5:2 C5:2 r:2",
    "A5:2 A5:1 A5:1 A5:2 F5:2", "G5:2 E5:2 E5:2 r:2",
    "A5:2 A5:1 A5:1 A5:2 F5:2", "G5:2 D5:2 D5:2 r:1 G4:1",
    "C5:2 C5:1 C5:1 C5:1 E5:1 E5:2", "D5:2 C5:2 D5:2 r:1 G4:1",
    "C5:2 C5:1 C5:1 C5:1 E5:1 E5:2", "D5:2 B4:2 C5:4",
]
MTN_CH = ["C", "G", "C", "G", "F", "C", "F", "G", "C", "G", "C", "G"]
song("mountain", 14, "A", "G4:1 " + " ".join(MTN), "r:1 " + oompah(MTN_CH, 8),
     "r:1 " + rep("K:1 r:1 S:1 r:1 K:1 r:1 S:1 r:1", 12))

# ---------------------------------------------------------------------------------------------
# Bistro: "Funiculi, Funicula" (Luigi Denza, 1880), chorus.  6/8, one row per eighth, 10 frames per
# row (dotted quarter about 120).  Key C.
FUN = [
    "G4:1 C5:1 E5:1 G5:3", "G5:1 F5:1 E5:1 D5:3",
    "E5:1 D5:1 C5:1 E5:2 G5:1", "F5:1 E5:1 D5:1 C5:3",
    "G4:1 C5:1 E5:1 G5:3", "A5:1 G5:1 F5:1 E5:3",
    "D5:1 E5:1 F5:1 D5:2 B4:1", "C5:6",
    "E5:1 E5:1 E5:1 E5:2 D5:1", "D5:1 D5:1 D5:1 D5:2 C5:1",
    "C5:1 D5:1 E5:1 F5:2 E5:1", "D5:6",
    "G4:1 C5:1 E5:1 G5:3", "A5:1 G5:1 F5:1 E5:3",
    "D5:1 E5:1 F5:1 D5:1 B4:1 D5:1", "C5:6",
]
FUN_CH = ["C", "G", "C", "G", "C", "F", "G", "C", "C", "G", "C", "G", "C", "F", "G", "C"]
song("funicula", 10, "A", " ".join(FUN), oompah(FUN_CH, "c6"),
     rep("K:1 r:2 S:1 r:2", 16))

# ---------------------------------------------------------------------------------------------
# Arctic: "The Skaters' Waltz" (Emile Waldteufel, 1882), main theme.  3/4, 14 frames per eighth row.
# Key G.
SKT = [
    "D5:3 B4:1 G4:2", "A4:3 F#4:1 D4:2", "D5:3 B4:1 G4:2", "A4:6",
    "B4:3 G4:1 D5:2", "C5:3 A4:1 E5:2", "D5:2 C5:2 B4:2", "G4:6",
    "E5:3 C5:1 A4:2", "D5:3 B4:1 G4:2", "C5:3 A4:1 F#4:2", "B4:6",
    "D5:3 B4:1 G4:2", "C5:3 A4:1 F#4:2", "B4:2 A4:2 F#4:2", "G4:6",
]
SKT_CH = ["G", "D", "G", "D", "G", "C", "D", "G", "Am", "G", "D", "G", "G", "D", "D", "G"]
song("skaters", 14, "A", " ".join(SKT), oompah(SKT_CH, 6),
     rep("K:1 r:5", 16), gap=True)

# ---------------------------------------------------------------------------------------------
# Robot factory: "In the Hall of the Mountain King" (Edvard Grieg, 1875).  4/4, one row per eighth
# note, speeds up in two steps (tempo 12 -> the song is written as three passes at one tempo, each
# pass with more notes).  Key A minor.
MK_A = "A3:1 B3:1 C4:1 D4:1 E4:1 C4:1 E4:2"
MK_B = "D#4:1 B3:1 D#4:2 r:4"
MK_C = "A3:1 B3:1 C4:1 D4:1 E4:1 C4:1 E4:2"
MK_D = "E4:1 C4:1 E4:2 r:4"
MK_HI = "A4:1 B4:1 C5:1 D5:1 E5:1 C5:1 E5:2"
MK_HI2 = "D#5:1 B4:1 D#5:2 r:4"
MK_END = "A4:1 B4:1 C5:1 D5:1 E5:1 C5:1 E5:2  A5:2 E5:2 C5:2 A4:2"
MK_MEL = " ".join([MK_A, MK_B, MK_C, MK_D, MK_HI, MK_HI2, MK_HI, MK_HI2, MK_HI, MK_HI2, MK_END])
MK_CH = ["Am", "Am", "Am", "Am", "Am", "E", "Am", "E", "Am", "E", "Am", "Am"]
song("hall", 12, "A", MK_MEL,
     " ".join(f"{CHORD[c][0]}:2! {CHORD[c][1]}:2! {CHORD[c][0]}:2! {CHORD[c][1]}:2!" for c in MK_CH),
     rep("K:1 r:3 S:1 r:3", 12))

# ---------------------------------------------------------------------------------------------
# Teahouse: "Sakura Sakura" (Japanese traditional).  4/4, slow: one row per eighth, 24 frames.  The
# "In" scale on A: A B C E F.
SAK = [
    "A4:2 A4:2 B4:4", "A4:2 A4:2 B4:4", "A4:2 B4:2 C5:2 B4:2", "A4:2 B4:2 A4:2 F4:2",
    "E4:6 r:2", "E4:2 F4:2 E4:2 E4:2", "C5:2 B4:2 A4:2 B4:2", "A4:2 F4:2 E4:4",
]
SAK_BASS = " ".join(["A2:4 E3:4"] * 4 + ["E3:4 A2:4", "E3:4 E3:4", "A2:4 E3:4", "A2:4 E3:4"])
song("sakura", 24, "A", " ".join(SAK), SAK_BASS, "", gap=True)

# ---------------------------------------------------------------------------------------------
# Space lounge: "The Blue Danube" (Johann Strauss II, 1866), first waltz theme.  3/4, 15 frames per
# eighth row.  Key C.
DAN = [
    "E4:2 G4:4", "G4:2 G4:4", "G4:2 E4:2 C4:2", "C4:6",
    "E4:2 G4:4", "G4:2 A4:4", "A4:2 F4:2 D4:2", "D4:6",
    "F4:2 A4:4", "A4:2 A4:4", "A4:2 F4:2 D4:2", "G4:6",
    "E4:2 G4:4", "G4:2 B4:4", "B4:2 G4:2 D4:2", "C4:6",
]
DAN_CH = ["C", "C", "C", "C", "C", "C", "G", "G", "F", "F", "F", "G", "C", "C", "G", "C"]
song("danube", 15, "A", "C4:2 " + " ".join(DAN), "r:2 " + oompah(DAN_CH, 6),
     "r:2 " + rep("K:1 r:5", 16))

# ---------------------------------------------------------------------------------------------
# Zoo: "Pop Goes the Weasel" (English folk tune, c. 1850).  6/8, 11 frames per eighth row.  Key C.
WEA = [
    "C5:2 C5:1 D5:2 D5:1", "E5:2 E5:1 C5:2 C5:1",
    "D5:2 D5:1 E5:2 D5:1", "C5:2 B4:1 C5:3",
    "C5:2 C5:1 D5:2 D5:1", "E5:2 E5:1 C5:2 C5:1",
    "D5:2 D5:1 E5:2 F5:1", "E5:6",
    "E5:2 E5:1 F5:2 F5:1", "G5:2 G5:1 E5:2 E5:1",
    "F5:2 F5:1 G5:2 F5:1", "E5:2 D5:1 E5:3",
    "C5:2 C5:1 D5:2 D5:1", "E5:2 G5:1 G5:3",     # ... Pop! goes the weasel
    "G5:1 G5:1 G5:1 E5:1 D5:1 C5:1", "C5:6",
]
WEA_CH = ["C", "C", "G", "C", "C", "C", "G", "C", "C", "C", "G", "C", "C", "C", "G", "C"]
song("weasel", 11, "A", " ".join(WEA), oompah(WEA_CH, "c6"),
     rep("K:1 r:2 S:1 r:2", 16))

# which songs, in tune order after title/show
VENUES = ["susanna", "ballgame", "mountain", "funicula", "skaters", "hall", "sakura", "danube", "weasel"]

# rows per bar (for the pitch-check table in tools/check_music.py)
BAR_ROWS = {"susanna": 4, "entertainer": 8, "galop": 4, "ballgame": 6, "mountain": 8, "funicula": 6,
            "skaters": 6, "hall": 8, "sakura": 8, "danube": 6, "weasel": 6}
