# Melody specs (owner-supplied)

Supplied by the owner (prepared with an internet-connected agent), 2026-10-09.
These are the reference for tools/songs.py. Every tune is public domain; credit each SOURCE line in CREDITS.md.

Revised 2026-10-11 (music step 1, owner-approved): The Entertainer and The Blue Danube were checked note by note
against Mutopia Project scores and corrected (their "Corrected" notes say what changed; the Blue Danube is now in
the score's C major). The last bar of the Skaters' Waltz, Take Me Out to the Ball Game, In the Hall of the
Mountain King, Sakura Sakura and the Galop infernal was changed so the tune flows back into bar 1 when it loops
(each tune's "Game loop" note gives the old bar). No score was found for the other tunes; their notes are unchanged.

Revised 2026-10-11 (music step 3, rhythm audit; the owner heard "comin'" and "Su-san-na" sung in even notes): every
melody's rhythm was compared with a public-domain score found on GitHub where one exists. Oh! Susanna (not in this
file; tools/songs.py) now has Foster's rhythm. She'll Be Coming 'Round the Mountain (tune 4) moved to sixteenth units
and the owner's described rhythm (no score found). Drunken Sailor (tune 11): the chorus bars 9, 11 and 13 were
flattened, fixed from a lead sheet. Confirmed by a score, unchanged: Funiculi (1, one echo bar differs between
sources), Pop Goes the Weasel (5), Blue Danube (6), In the Hall of the Mountain King (7, bars 1-12), The Entertainer (9).
No score found on GitHub: Skaters' Waltz (2), Take Me Out to the Ball Game (3), Sakura (8; the Mutopia
"Sakura-Miyotote" is another piece), Galop infernal (10). Each tune's "Rhythm" note says what was compared.

```
GAME BOY MELODY SPECS - 11 public-domain tunes
==============================================
Octave convention: C4 = middle C (261.6 Hz). "#" = sharp, "b" = flat.
Format: NOTE+octave:length, separated by spaces, one bar per line.
   R:n  = rest for n units
   ~:n  = keep holding the previous note for n more units (a tie)
Each tune states its own unit (eighth note for all except The Entertainer,
which uses sixteenths). Every bar's total has been checked by script
against the time signature.
Melody -> pulse channel 2. Chords (one per bar unless marked X/Y = two
half-bars) -> bass on the wave channel.
Confidence and source are listed per tune; credit the SOURCE line.


------------------------------------------------------------
1. FUNICULI, FUNICULA (Denza, 1880) - verse (first strain) + chorus
------------------------------------------------------------
Key: F major
Time: 6/8
Tempo: dotted quarter = 92 (quarter ~ 138)
Game tempo: dotted quarter = 112 (11 frames per eighth row, plays at 109). Owner-approved; melody notes unchanged. See GAME_BPM in tools/songs.py.
Unit: 1 = eighth note (bar = 6)
Length: 25 bars + pickup

PICKUP: C5:1
  [VERSE]
 1 | F5:6                                         | F
 2 | ~:2 F5:1 E5:2 E5:1                           | F
 3 | C5:2 C5:1 D5:2 D5:1                          | F
 4 | A4:3 A4:3                                    | F
 5 | ~:2 A4:1 G4:2 F4:1                           | C7
 6 | F4:6                                         | F
 7 | ~:1 R:1 A4:1 G4:2 F4:1                       | C7
 8 | F4:6                                         | F
 9 | ~:1 R:4 C5:1                                 | F
  [CHORUS ("Jammo, jammo...")]
10 | E5:3 D5:1 R:2                                | C7
11 | E5:3 D5:1 R:2                                | C7
12 | F5:2 E5:1 D5:2 F5:1                          | C7
13 | E5:3 R:3                                     | C7
14 | E5:3 D5:1 R:2                                | C7
15 | E5:3 D5:1 R:2                                | C7
16 | F5:2 E5:1 D5:2 F5:1                          | C7
  [("Funiculi, funicula")]
17 | C5:2 A4:1 A4:2 A4:1                          | F
18 | A4:2 A4:1 A4:2 A4:1                          | A7
19 | A4:2 A4:1 A4:2 A4:1                          | Dm
20 | A4:2 A4:1 A4:2 A4:1                          | A7
21 | F5:6                                         | Dm
22 | G5:2 F5:1 D5:2 F5:1                          | Bb
23 | C5:2 A4:1 A4:2 Bb4:1                         | F
24 | C5:2 Bb4:1 A4:2 G4:1                         | C7
25 | F4:3 R:2 C5:1                                | F

Note: Bar 9 holds F4; its final C5 is the source's repeat pickup, used here as a lead-in to the chorus. Bar 25 ends with the same C5 pickup, so on looping go straight to bar 1 (play the PICKUP line only the first time).
Note: Chorus melody is the top voice of the source's two-note chords.
Confidence: High (from transcription; bars 1-9 checked against the 1880 Ricordi edition).
Rhythm checked 2026-10-11 (music step 3) against the Wikifonia lead sheet "Funiculi funicula" in OpenEWLD (github.com/00sapo/OpenEWLD, public-domain scores): the same note onsets in every bar (the lead sheet writes some chorus notes as an eighth and a rest, and has a bar's rest after bar 21), except the echo "and so do I" in bar 7, three even eighths there (A4:1 G4:1 F4:1 after a held F4 and a rest); the spec's rhythm was kept.
Corrected 2026-10-12 (music step 4) from the owner-supplied transcription of Ricordi's first edition (see Source; E-flat major there, transposed up a tone to F): the echo "Tu sa-ie ad-do" is the long-short form every time, never three even eighths: the held "-do" goes on for a tied eighth, an eighth rest, then A4 eighth, G4 quarter, F4 eighth (bar 7 was 'R:2 A4:1 G4:2 F4:1', a quarter rest). The later echoes ("Farme non po", "Te lassa sta", ...) repeat the pattern but lie in the omitted second half of the verse, so bar 7 is the only echo here. Bars 1-6 and 8 match the transcription; one difference left as it was: the transcription restrikes "-ra" (E-flat5 quarter, bar 2) where bar 2 ties F5 on from bar 1 (~:2).
Source: Melody from John Chambers' ABC transcription (trillian.mit.edu/~jc/music/abc/Italy/FuniculiFunicula.abc, via folktunefinder.com); the echo bar transcribed from Ricordi, Milan 1880, first edition, plate 47127 (IMSLP #148203, public domain) (owner-supplied transcription, 2026-10-11). Underlying work: Luigi Denza, Ricordi 1880 (public domain). The full verse modulates through A minor and C major after bar 9; that part is omitted here.

------------------------------------------------------------
2. THE SKATERS' WALTZ (Waldteufel, 1882, Op. 183) - main waltz theme
------------------------------------------------------------
Key: G major
Time: 3/4
Tempo: quarter = 160
Game tempo: quarter = 192 (9 frames per eighth row, plays at 200). Owner-approved; melody notes unchanged. See GAME_BPM in tools/songs.py.
Unit: 1 = eighth note (bar = 6)
Length: 32 bars

 1 | B4:6                                         | G
 2 | D5:4 E5:2                                    | G
 3 | E5:6                                         | D7
 4 | ~:6                                          | D7
 5 | C5:6                                         | D7
 6 | E5:4 F#5:2                                   | D7
 7 | F#5:6                                        | G
 8 | ~:6                                          | G
 9 | A5:6                                         | Em
10 | G5:4 B4:2                                    | Em
11 | D5:6                                         | Am
12 | C5:4 B4:2                                    | Am
13 | B4:6                                         | D
14 | A4:6                                         | D7
15 | G4:2 E5:2 D5:2                               | G
16 | C5:2 B4:2 A4:2                               | D7
17 | B4:6                                         | G
18 | D5:4 E5:2                                    | G
19 | E5:6                                         | D7
20 | ~:6                                          | D7
21 | C5:6                                         | D7
22 | E5:4 F#5:2                                   | D7
23 | F#5:6                                        | G
24 | ~:6                                          | G
25 | A5:6                                         | Em
26 | G5:4 B4:2                                    | Em
27 | D5:6                                         | Am
28 | C5:4 B4:2                                    | Am
29 | B4:6                                         | D
30 | A4:6                                         | D7
31 | G4:6                                         | G
32 | ~:2 A4:2 A#4:2                               | G

Note: Transposed up one octave from the source for a brighter pulse sound.
Note: The long notes are the famous sliding 'skater' notes; a short pitch slide up into bars 1, 5 and 9 sounds idiomatic.
Game loop: bar 32 was '~:6' (G4 held six beats, faded out long before bar 1); A4 A#4 climb into bar 1's B4.
Checked 2026-10-12 (music step 4) against the owner-supplied transcription of the full score (see Source; violin 1 "sul G" at letter A, A major, A3-B4; here transposed down a tone to G and up an octave): bars 1-14 (and 17-30) match exactly. Bars 15-16 differ: the score ends the strain A3 dotted half | A3 quarter, then rests ("Fine", repeat from bar 1), which would be 'G4:6 | G4:2 R:4' here; the ABC's running quarters (bars 15-16 'G4:2 E5:2 D5:2 | C5:2 B4:2 A4:2') are kept into the repeat, and bars 31-32 keep the game loop's held G4 and A4 A#4 climb. Reason: the score's ending does not loop cleanly; two beats of rest after a held G4 on the decaying song lead leave 0.62 s of melody silence before bar 1 (measured; tests/test_music_loops.py allows 0.25 s). Option for the owner: bar 32 could restrike G4 (the score's A3 quarter) before the climb, 'G4:2 A4:2 A#4:2'.
Confidence: High for melody (bars 1-14 confirmed by the score). Chords as given in the source.
Source: Traditional Tune Archive (tunearch.org, 'Skater's Waltz'), transcription by Carl Allison from Joe Buchanan's Scottish Tome; bars 1-14 confirmed against a transcription from Luck's Music Library full score, Detroit, n.d., plate K. & E. 5154 (IMSLP #102459, public domain) (owner-supplied transcription, 2026-10-11). Underlying work: Emile Waldteufel, 1882 (public domain).

------------------------------------------------------------
3. TAKE ME OUT TO THE BALL GAME (Von Tilzer, 1908) - chorus
------------------------------------------------------------
Key: G major
Time: 3/4
Tempo: quarter = 168
Game tempo: quarter = 192 (9 frames per eighth row, plays at 200). Owner-approved; melody notes unchanged. See GAME_BPM in tools/songs.py.
Unit: 1 = eighth note (bar = 6)
Length: 32 bars

  ["Take me out to the ball game"]
 1 | G4:4 G5:2                                    | G
 2 | E5:2 D5:2 B4:2                               | Em
 3 | D5:6                                         | D7
 4 | A4:6                                         | D7
 5 | G4:4 G5:2                                    | G
 6 | E5:2 D5:2 B4:2                               | Em
 7 | D5:6                                         | D
 8 | ~:4 R:2                                      | D
  ["Buy me some peanuts..."]
 9 | E5:2 D#5:2 E5:2                              | E7
10 | B4:2 C5:2 D5:2                               | E7
11 | E5:4 C5:2                                    | Am
12 | A4:6                                         | Am
13 | E5:4 E5:2                                    | A7
14 | E5:2 F#5:2 G5:2                              | A7
15 | A5:2 F#5:2 E5:2                              | D
16 | D5:2 B4:2 A4:2                               | D
  ["Let me root, root, root..."]
17 | G4:4 G5:2                                    | G
18 | E5:2 D5:2 B4:2                               | Em
19 | D5:6                                         | D7
20 | A4:4 A4:2                                    | D7
21 | G4:4 A4:2                                    | G
22 | B4:2 C5:2 D5:2                               | G7
23 | E5:6                                         | C
24 | ~:2 E5:2 F#5:2                               | C
  ["For it's one, two, three strikes..."]
25 | G5:6                                         | C
26 | G5:6                                         | A7
27 | G5:2 F#5:2 E5:2                              | D
28 | D5:2 C#5:2 D5:2                              | E7
29 | E5:6                                         | Am
30 | F#5:6                                        | D7
31 | G5:6                                         | G
32 | ~:2 D5:2 B4:2                                | G

Note: Bars 1, 5 and 17: the ABC source wrote the first note short followed by a rest (G4 z G5); the 1908 edition has a half note, as here.
Corrected 2026-10-12 (music step 4) bar by bar against the owner-supplied transcription of the 1908 York Music Co. edition (see Source; D major there, transposed up a fourth to G): bar 8 ends with a quarter rest (was '~:6'); bar 20 is the same pitch twice, "team, If" (was 'A4:4 B4:2'); bars 25-26, "one, two", are held dotted halves (were 'G5:2 R:4' each). Every other bar matches the edition. Bar 32 keeps the loop's walk-down (the edition: D5 quarter, then rests).
Game loop: bar 32 was '~:2 R:4' (the final G5 faded into a second of silence); D5 B4 walk down into bar 1's G4.
Confidence: High: checked bar by bar against the 1908 edition.
Source: transcribed from York Music Co., New York, 1908, pp. 4-5, via the Library of Congress (public domain) (owner-supplied transcription, 2026-10-11). Earlier list: John Chambers' ABC (trillian.mit.edu/~jc/music/session/waltz/Take_Me_Out_to_the_Ball_Game.abc). Underlying work: Albert Von Tilzer / Jack Norworth, 1908 (public domain).

------------------------------------------------------------
4. SHE'LL BE COMING 'ROUND THE MOUNTAIN (traditional) - one verse
------------------------------------------------------------
Key: D major
Time: 4/4
Tempo: quarter = 160
Game tempo: quarter = 225 in this spec's 4-row beat (4 frames per sixteenth row = 112.5 of the source MIDI's 8-row quarters, which is marked 116; was 6 = 150). Music step 6 (owner: too slow), MTN_TEMPO and GAME_BPM in tools/songs.py.
Unit: 1 = SIXTEENTH note (bar = 16) since music step 3 (2026-10-11); it was an eighth (bar = 8)
Length: 16 bars + pickup

PICKUP: A4:4 B4:4
 1 | D5:2 D5:6 D5:6 D5:2                          | D
 2 | B4:4 A4:4 F#4:4 A4:4                         | A7
 3 | D5:16                                        | D
 4 | R:8 D5:4 E5:4                                | D
 5 | F#5:2 F#5:6 F#5:6 F#5:2                      | D
 6 | A5:4 F#5:4 E5:4 D5:4                         | D
 7 | E5:16                                        | A7
 8 | R:8 A5:4 G5:4                                | A7
 9 | F#5:2 F#5:6 F#5:6 F#5:2                      | D
10 | E5:4 D5:4 D5:4 D5:4                          | D7
11 | B4:2 B4:6 B4:6 B4:2                          | G
12 | E5:4 D5:4 C#5:4 B4:4                         | A7
13 | A4:2 A4:6 A4:6 A4:2                          | D
14 | F#5:4 E5:4 B4:4 C#5:4                        | A7
15 | D5:16                                        | D
16 | R:8 A4:4 B4:4                                | D

Note: Bar 16 ends with the pickup for the next loop.
Note: Bar 12: the source chord is Ddim; A7 is a simpler substitute that fits the C#.
Rhythm and pitches changed 2026-10-12 (music step 4): melody rhythm and pitches from Simon Horn's MIDI (2021, CC0, Wikimedia Commons), supplied by the owner 2026-10-12 (Harmonica track, first verse, in G there, transposed to D here; one MIDI quarter = 8 rows). Every "com-ing round the" bar is X:2 X:6 X:6 X:2; every "moun-tain when she" / "moun-tain, she'll be" bar is four even eighths (X:4 Y:4 Z:4 W:4); "comes" is a half note (16 rows) then a rest (R:8) before the next pickup (bars 4, 8, 16). Music step 3 (2026-10-11) had the owner's listening description (X:3 Y:5 Z:4 W:4 and the held "comes" tied on for 8 more rows); the pitches did not change.
Confidence: High for melody (cross-checked against an independent letter-note chart).
Source (rhythm and pitches, 2026-10-12): Simon Horn's MIDI, 2021, CC0 (Wikimedia Commons), supplied by the owner 2026-10-12. Earlier source (pitches, still agree): John Chambers' ABC collection (mirror of David Kidd's dulcimer transcription, originally everythingdulcimer.com). Tune is traditional; in print by Carl Sandburg's 'The American Songbag' (1927), public domain.

------------------------------------------------------------
5. POP GOES THE WEASEL (traditional) - verse + second strain
------------------------------------------------------------
Key: G major
Time: 6/8
Tempo: dotted quarter = 100
Unit: 1 = eighth note (bar = 6)
Length: 16 bars

  [VERSE ("All around the mulberry bush..." / "Pop! goes the weasel" = bar 7)]
 1 | G4:2 G4:1 A4:2 A4:1                          | G
 2 | B4:1 D5:1 B4:1 G4:2 R:1                      | G
 3 | G4:2 G4:1 A4:2 C5:1                          | D7
 4 | B4:3 G4:2 R:1                                | G
 5 | G4:2 G4:1 A4:2 A4:1                          | G
 6 | B4:1 D5:1 B4:1 G4:2 R:1                      | G
 7 | E5:3 A4:2 C5:1                               | Am
 8 | B4:3 G4:2 R:1                                | G
  [SECOND STRAIN (instrumental; optional)]
 9 | G5:3 E5:2 G5:1                               | G
10 | F#5:1 A5:1 F#5:1 D5:3                        | D
11 | G5:2 G5:1 E5:2 G5:1                          | G
12 | F#5:3 D5:2 B4:1                              | D
13 | C5:2 B4:1 C5:2 D5:1                          | C
14 | E5:2 F#5:1 G5:2 R:1                          | G
15 | E5:1 R:2 A4:2 C5:1                           | C/D7
16 | B4:3 G4:2 R:1                                | G

Note: Bars 1-8 are the sung verse. Bars 9-16 are the original dance tune's second strain; use them to reach ~20 seconds, or loop bars 1-8 twice.
Note: Bar 15 'C/D7' = C for the first half-bar, D7 for the second.
Note: Many versions add a D4 pickup before bar 1 ("Half a..."): D4:1 replacing the R:1 at the end of bar 16 works for looping.
Confidence: High for melody; chords are standard but not from the source.
Rhythm checked 2026-10-11 (music step 3) against the same Ryan's Mammoth tune as encoded in the music21 corpus (github.com/cuthbertLab/music21, corpus/ryansMammoth/PopGoesTheWeasel.abc): all 16 bars match.
Source: Ryan's Mammoth Collection (1882), p. 264, via John Chambers' ABC mirror on abcnotation.com. Public domain. Chords are my harmonization (the source gives none).

------------------------------------------------------------
6. THE BLUE DANUBE (Johann Strauss II, 1867, Op. 314) - Waltz 1A, main theme
------------------------------------------------------------
Key: C major (the Mutopia score's key; Strauss wrote it in D)
Time: 3/4
Tempo: quarter = 160
Game tempo: quarter = 192 (9 frames per eighth row, plays at 200). Owner-approved; melody notes unchanged. See GAME_BPM in tools/songs.py.
Unit: 1 = eighth note (bar = 6)
Length: 32 bars

 1 | C4:2 E4:2 G4:2                               | C
 2 | G4:4 G5:2                                    | C
 3 | G5:4 E5:2                                    | C
 4 | E5:4 C4:2                                    | C
 5 | C4:2 E4:2 G4:2                               | C
 6 | G4:4 G5:2                                    | C
 7 | G5:4 F5:2                                    | G7
 8 | F5:4 B3:2                                    | G7
 9 | B3:2 D4:2 A4:2                               | G7
10 | A4:4 A5:2                                    | G7
11 | A5:4 F5:2                                    | G7
12 | F5:4 B3:2                                    | G7
13 | B3:2 D4:2 A4:2                               | G7
14 | A4:4 A5:2                                    | G7
15 | A5:4 E5:2                                    | C
16 | E5:4 C4:2                                    | C
17 | C4:2 E4:2 G4:2                               | C
18 | C5:4 C6:2                                    | C
19 | C6:4 G5:2                                    | C
20 | G5:4 C4:2                                    | C
21 | C4:2 E4:2 G4:2                               | C
22 | C5:4 C6:2                                    | Dm
23 | C6:4 A5:2                                    | Dm
24 | A5:4 D4:2                                    | Dm
25 | D4:2 F4:2 A4:2                               | Dm
26 | A4:6                                         | G7
27 | ~:2 F#4:2 G4:2                               | G7
28 | E5:6                                         | C
29 | ~:2 C5:2 E4:2                                | C
30 | E4:4 D4:2                                    | F
31 | A4:4 G4:2                                    | G
32 | C4:3 C5:1 C5:2                               | C

Note: The melody is the top note of the score's right hand.
Note: Range C4-C6 except the B3 that opens bars 9 and 13; the bass (C3/G3, G2/D3) stays below.
Note: Earlier list (G major): James Kerr, 'Merry Melodies' vol. 4, via John Chambers' ABC; replaced by the score.
Corrected 2026-10-11 against the Mutopia score (see Source), in its key, C major: the old G-major list had bars 9-14 as F#4 A4 C5 | C5 . E5 (the score: B3 D4 A4 | A4 . A5, i.e. F# A E in G) and bars 25-32 an octave too high; the score's half notes are written as X:4 (the old 'X R Y' bars held through the rest); bar 32 is the score's closing bar (C4 dotted quarter, C5 C5), which flows into bar 1. Our bar 1 is the score's bar 2; its pickup C4 is the last note of bars 4, 16 and 20. Chords from the score's left hand (bars 22-25 Dm, 26-27 G7, 30 F, 31 G).
Confidence: High: checked note by note against the Mutopia score.
Source: Mutopia Project, 'The Blue Danube Waltz (main theme)' (ftp/StraussJJ/O314/blue_danube/blue_danube.ly, Mutopia-2014/03/24-519), typeset by Nikos Kouremenos from Christian Mondrup's four-hand piano reduction (Werner Icking Music Archive); typesetting licensed Creative Commons Attribution-ShareAlike 4.0 (attribution: Nikos Kouremenos / The Mutopia Project). Underlying work: Johann Strauss II, 1867 (public domain).

------------------------------------------------------------
7. IN THE HALL OF THE MOUNTAIN KING (Grieg, 1875) - main motif + answer, 16 bars
------------------------------------------------------------
Key: B minor (Grieg's key)
Time: 4/4
Tempo: quarter = 120, accelerating each loop if you like
Unit: 1 = eighth note (bar = 8)
Length: 16 bars

  [A (motif)]
 1 | B3:1 C#4:1 D4:1 E4:1 F#4:1 D4:1 F#4:2        | Bm
 2 | E#4:1 C#4:1 E#4:2 E4:1 C4:1 E4:2             | C#7/C
 3 | B3:1 C#4:1 D4:1 E4:1 F#4:1 D4:1 F#4:1 B4:1   | Bm
 4 | A4:1 F#4:1 D4:1 F#4:1 A4:4                   | D
 5 | B3:1 C#4:1 D4:1 E4:1 F#4:1 D4:1 F#4:2        | Bm
 6 | E#4:1 C#4:1 E#4:2 E4:1 C4:1 E4:2             | C#7/C
 7 | B3:1 C#4:1 D4:1 E4:1 F#4:1 D4:1 F#4:1 B4:1   | Bm
 8 | A4:1 F#4:1 D4:1 F#4:1 A4:4                   | D
  [B (answer, on F#)]
 9 | F#4:1 G#4:1 A#4:1 B4:1 C#5:1 A#4:1 C#5:2     | F#
10 | D5:1 A#4:1 D5:2 C#5:1 A#4:1 C#5:2            | F#
11 | F#4:1 G#4:1 A#4:1 B4:1 C#5:1 A#4:1 C#5:2     | F#
12 | D5:1 A#4:1 D5:2 C#5:4                        | F#
  [A (return)]
13 | B3:1 C#4:1 D4:1 E4:1 F#4:1 D4:1 F#4:2        | Bm
14 | E#4:1 C#4:1 E#4:2 E4:1 C4:1 E4:2             | C#7/C
15 | B3:1 C#4:1 D4:1 E4:1 F#4:1 D4:1 F#4:1 B4:1   | Bm
16 | A4:1 F#4:1 D4:1 F#4:1 A4:2 F#4:1 A#3:1       | D

Note: E#4 = F4 (same pitch). Played staccato: about half the written length, then silence.
Note: For a Grieg-like bass, skip the chords and repeat the root as an ostinato: B in A phrases, F# in the B phrase.
Note: 'C#7/C' = C#7 for the first half-bar, C major for the second (the chromatic slide F#, E#, E).
Game loop: bar 16 was 'A4:1 F#4:1 D4:1 F#4:1 A4:4' (half a bar of silence after the staccato A4); F#4 A#3 lead into bar 1's B3.
Confidence: High for bars 1-8. Moderate for bars 9-12 (the answer phrase). Bars 13-16 are a return I chose for looping; Grieg's own continuation differs.
Checked 2026-10-11 (music step 3): bars 1-12 are note for note and in rhythm the score's bars 2-13 (after the opening fermata) in the Mutopia Project's "In the Hall of the Mountain King" (ftp/GriegE/O46/Dans_l_antre_du_roi_de_la_montagne/Dans_l_antre_du_roi_de_la_montagne.ly in github.com/MutopiaProject/MutopiaProject, Mutopia-2013/12/07-1888, typeset by Coyau from The University Society's 1918 piano edition; placed in the public domain by the typesetter). Bars 13-16 stay the return chosen for looping.
Source: written from memory (owner's spec), confirmed for bars 1-12 by the Mutopia score above. Underlying work: Edvard Grieg, 1875 (public domain).

------------------------------------------------------------
8. SAKURA SAKURA (traditional Japanese, Edo period) - full melody
------------------------------------------------------------
Key: A minor (miyako-bushi scale: A B C E F)
Time: 4/4
Tempo: quarter = 72
Game tempo: quarter = 150 (12 frames per eighth row, plays at 150), with the lively arrangement, owner-approved 2026-10-11 (was 120 = 15 frames). Melody notes unchanged. See GAME_BPM in tools/songs.py.
Unit: 1 = eighth note (bar = 8)
Length: 14 bars

 1 | A4:2 A4:2 B4:4                               | Am
 2 | A4:2 A4:2 B4:4                               | Am
 3 | A4:2 B4:2 C5:2 B4:2                          | Am
 4 | A4:2 B4:1 A4:1 F4:4                          | Dm
 5 | E4:2 C4:2 E4:2 F4:2                          | Am
 6 | E4:2 E4:1 C4:1 B3:4                          | E
 7 | A4:2 B4:2 C5:2 B4:2                          | Am
 8 | A4:2 B4:1 A4:1 F4:4                          | Dm
 9 | E4:2 C4:2 E4:2 F4:2                          | Am
10 | E4:2 E4:1 C4:1 B3:4                          | E
11 | A4:2 A4:2 B4:4                               | Am
12 | A4:2 A4:2 B4:4                               | Am
13 | E4:2 F4:2 B4:1 A4:1 F4:2                     | Dm
14 | E4:4 C4:2 E4:2                               | Am

Note: 14 bars total; about 47 s at 72 bpm, so it's already a full loop. At ~100 bpm it lands near 34 s.
Note: Traditionally unharmonized. A soft A/E drone on the wave channel sounds more authentic than chords. If you use the E chord, try it without the G# (E+B only), since G# isn't in the scale.
Game loop: bar 14 was 'E4:4 R:4'; E4 C4 E4 (bar 5's figure) lift into bar 1's A4.
Checked 2026-10-12 (music step 4) against the owner-supplied transcription of the 1888 koto collection (see Source; voice part, no key signature, same key and register as here): bars 1-12 are identical. Bars 13-14 differ and are NOT changed (the owner approved the current arrangement): the 1888 version starts bar 13 with a rest and holds "ni", then "yu-ka-n": 'R:2 E4:2 F4:4 | B4:1 A4:1 F4:2 E4:4' in this file's units (rest, E4 q, F4 h | B4 e A4 e F4 q E4 h), where ours is 'E4:2 F4:2 B4:1 A4:1 F4:2 | E4:4 C4:2 E4:2'. An option for the owner; with it, bar 14's last half note would again need a lift into bar 1 for the loop (as the current E4 C4 E4 does).
Confidence: High (two independent transcriptions agree, except for minor variants in the last two bars; bars 1-12 confirmed by the 1888 source).
Source: Melody: John Chambers' ABC 'Sakura (Cherry Blossom)' (trillian.mit.edu/~jc/music/abc/Japan/Sakura_Am.utf8.abc). Chords adapted from Frank Nordberg's Musica Viva transcription (same collection). Traditional; public domain. Bars 1-12 confirmed against a transcription from Sokyokushu (Collection of Japanese Koto Music), Ministry of Education Music Investigation Committee, October 1888, No. 2 "Sakura", NDL pid 857651, public domain (owner-supplied transcription, 2026-10-11).

------------------------------------------------------------
9. THE ENTERTAINER (Joplin, 1902) - A and B sections, 32 bars
------------------------------------------------------------
Key: C major
Time: 2/4
Tempo: quarter = 90 (Joplin: 'Not fast')
Game tempo: quarter = 106 (rows of 9 and 8 frames alternating, a slight swing, plays at 105.9; the owner chose "1b at 106 bpm" 2026-10-12, it was 8 frames = 112.5). Owner-approved; the melody's pitches are the spec's, played an octave lower in the game (ENT_BARS), with a second voice in thirds under it. See GAME_BPM in tools/songs.py.
Unit: 1 = SIXTEENTH note (bar = 8)
Length: 32 bars + pickup (A section 1-16, B section 17-32)

PICKUP: D5:1 D#5:1
 1 | E5:1 C6:2 E5:1 C6:2 E5:1 C6:1                | C
 2 | ~:5 C6:1 D6:1 D#6:1                          | F/C
 3 | E6:1 C6:1 D6:1 E6:2 B5:1 D6:2                | G7
 4 | C6:6 D5:1 D#5:1                              | C
 5 | E5:1 C6:2 E5:1 C6:2 E5:1 C6:1                | C
 6 | ~:6 A5:1 G5:1                                | F/C
 7 | F#5:1 A5:1 C6:1 E6:2 D6:1 C6:1 A5:1          | D7
 8 | D6:6 D5:1 D#5:1                              | G7
 9 | E5:1 C6:2 E5:1 C6:2 E5:1 C6:1                | C
10 | ~:5 C6:1 D6:1 D#6:1                          | F/C
11 | E6:1 C6:1 D6:1 E6:2 B5:1 D6:2                | G7
12 | C6:6 C6:1 D6:1                               | C
13 | E6:1 C6:1 D6:1 E6:2 C6:1 D6:1 C6:1           | C
14 | E6:1 C6:1 D6:1 E6:2 C6:1 D6:1 C6:1           | F
15 | E6:1 C6:1 D6:1 E6:2 B5:1 D6:2                | G7
16 | C6:5 E5:1 F5:1 F#5:1                         | C
17 | G5:2 A5:1 G5:2 E5:1 F5:1 F#5:1               | C
18 | G5:2 A5:1 G5:2 E5:1 C5:1 G4:1                | C
19 | A4:1 B4:1 C5:1 D5:1 E5:1 D5:1 C5:1 D5:1      | F
20 | G4:1 E5:1 F5:1 G5:1 A5:1 G5:1 E5:1 F5:1      | C
21 | G5:2 A5:1 G5:2 E5:1 F5:1 F#5:1               | C
22 | G5:2 A5:1 G5:2 G5:1 A5:1 A#5:1               | C
23 | B5:1 B5:2 B5:2 A5:1 F#5:1 D5:1               | D7
24 | G5:5 E5:1 F5:1 F#5:1                         | G7
25 | G5:2 A5:1 G5:2 E5:1 F5:1 F#5:1               | C
26 | G5:2 A5:1 G5:2 E5:1 C5:1 G4:1                | C
27 | A4:1 B4:1 C5:1 D5:1 E5:1 D5:1 C5:1 D5:1      | F
28 | C5:5 G4:1 F#4:1 G4:1                         | C
29 | C5:2 A4:1 C5:2 A4:1 C5:1 A4:1                | F/F#dim7
30 | G4:1 C5:1 E5:1 G5:2 E5:1 C5:1 G4:1           | C
31 | A4:2 C5:2 E5:1 D5:2 C5:1                     | D7/G7
32 | ~:6 D5:1 D#5:1                               | C

Note: Bars 1-11: pitches cross-checked against a published letter-note chart; rhythms are the standard syncopated pattern (16th-8th-16th).
Note: Bars 12-16 (closing phrase): were low confidence; corrected against the score (below).
Note: Bar 32 ends with the D-D# pickup, so it loops cleanly.
Added 2026-10-11 (owner: "I kind of wish the next section of The Entertainer was there before it looped back"): the A section now takes its second ending (bar 16 = score bar 21: C, then E F F# into the B section) and the B section follows (bars 17-31 = score bars 22-36, bar 32 = the B section's second ending, score bar 38, whose D D# pickup leads back to bar 1). The B section's melody is the top note of the right hand as written (its single notes continue the octaves' top line), so it sits below the A section, as in the score. Chords from the left hand: bar 19 F then F minor (F); bars 20 and 28 have E in the bass under C (C); bar 23 G over D then D7 (D7); bar 29 F then F#dim7.
Corrected 2026-10-11 against the Mutopia score (see Source): from bar 2 on, the old list ran one sixteenth early (the held C is 6 sixteenths and the run C D D# starts on bar 2's sixth sixteenth, E on bar 3's downbeat); bars 6-7 were '~:4 A5:1 G5:1 F#5:1 A5:1 | C6:1 E6:2 D6:1 C6:1 A5:1 D6:2'; bars 12-16 (the low-confidence end) are now the score's. The melody is the lower note of the right hand's octaves. Chords from the score's left hand: bars 2, 6 and 10 are F then C/E (F/C; bar 6 was D7).
Confidence: High: checked note by note against the Mutopia score.
Source: Mutopia Project, 'The Entertainer' (ftp/JoplinS/entertainer/entertainer.ly, Mutopia-2016/11/25-263; typeset by Chris Sawer, overhauled by Simon Albrecht 2015; source: reproduction of the original 1902 edition; licence: Public Domain), the A section (score bars 5-19, second ending bar 21) and the B section (score bars 22-36, second ending bar 38). Earlier list: written from memory of the 1902 John Stark & Son edition. Underlying work: Scott Joplin, 1902 (public domain).

------------------------------------------------------------
10. GALOP INFERNAL ("CAN-CAN") (Offenbach, 1858) - main theme
------------------------------------------------------------
Orphee aux enfers, Act II, No. 15b
Key: D major
Time: 2/4
Tempo: quarter = 160
Game tempo: quarter = 160 (11 frames per eighth row, plays at 163.6).
Unit: 1 = eighth note (bar = 4)
Length: 16 bars, no pickup. Play twice for ~24 s.
Octave: raised from the low register for a brighter pulse sound.

 1 | D5:4                    | D
 2 | E5:1 G5:1 F#5:1 E5:1    | A7
 3 | A5:2 A5:2               | D
 4 | A5:1 B5:1 F#5:1 G5:1    | D
 5 | E5:2 E5:2               | A7
 6 | E5:1 G5:1 F#5:1 E5:1    | A7
 7 | D5:1 D6:1 C#6:1 B5:1    | D
 8 | A5:1 G5:1 F#5:1 E5:1    | A7
 9 | D5:4                    | D
10 | E5:1 G5:1 F#5:1 E5:1    | A7
11 | A5:2 A5:2               | D
12 | A5:1 B5:1 F#5:1 G5:1    | D
13 | E5:2 E5:2               | A7
14 | E5:1 G5:1 F#5:1 E5:1    | A7
15 | D5:1 A5:1 E5:1 F#5:1    | D/A7
16 | D5:2 A4:2               | D

Note: "D/A7" = D for the first half-bar, A7 for the second.
Note: Bars 1-8 end on the dominant and 9-16 resolve, so the 16 bars loop cleanly. Play the quarter notes in bars 3, 5, 11 and 13 slightly detached for the galop bounce.
Note: Bass works best as "oom-pah": root on beat 1, chord fifth on beat 2.
Game loop: bar 16 was 'D5:2 R:2'; the A4 pickup leads back to bar 1's D5.
Confirmed 2026-10-12 (music step 4) by the owner-supplied transcription of the chorus ("Alle") statement in the vocal score (see Source; G major there, transposed up a fifth to D): all 16 bars, notes and rhythm. The score has a quarter-note pickup (D4 after a quarter rest = A4 here); bar 16's game-loop A4 is exactly the score's first ending (G4 quarter, D4 quarter pickup into the repeat), so every pass after the first already has it. The first-time pickup is not added: the driver loops from row 0, so a pickup bar before bar 1 would replay on every pass right after bar 16's A4.
Source: Owner-supplied; Offenbach, Orphée aux enfers (1858), Act II No. 15b, public domain. Transcribed from the German vocal score "Orpheus in der Unterwelt", IMSLP #26815, pp. 123-124, plate 10779 (probably Bote & Bock), public domain (owner-supplied transcription, 2026-10-11).

------------------------------------------------------------
11. DRUNKEN SAILOR (traditional sea shanty) - verse + chorus
------------------------------------------------------------
Added 2026-10-11 for The Chrome Cow (venue 7): the owner picked the tune ("Drunken Sailor", played fast and punky);
the melody below is the engine agent's transcription of the traditional tune, not owner-supplied.
Key: D Dorian (D minor with B natural)
Time: 4/4
Tempo: quarter = 200 (fast and punky)
Game tempo: quarter = 200 (9 frames per eighth row). Last call in The Chrome Cow: 8 frames per row (225, "the band
plays faster").
Unit: 1 = eighth note (bar = 8)
Length: 16 bars, no pickup.

  [VERSE ("What shall we do with a drunken sailor", x3, "early in the morning")]
 1 | A4:2 A4:1 A4:1 A4:2 A4:1 A4:1   | Dm
 2 | A4:2 D4:2 F4:2 A4:2             | Dm
 3 | G4:2 G4:1 G4:1 G4:2 G4:1 G4:1   | C
 4 | G4:2 C4:2 E4:2 G4:2             | C
 5 | A4:2 A4:1 A4:1 A4:2 A4:1 A4:1   | Dm
 6 | A4:2 B4:2 C5:2 D5:2             | Dm
 7 | C5:2 A4:2 G4:2 E4:2             | C
 8 | D4:4 D4:4                       | Dm
  [CHORUS ("Way hay and up she rises", x3, "early in the morning")]
 9 | A4:4 A4:3 A4:1                  | Dm
10 | A4:2 D4:2 F4:2 A4:2             | Dm
11 | G4:4 G4:3 G4:1                  | C
12 | G4:2 C4:2 E4:2 G4:2             | C
13 | A4:4 A4:3 A4:1                  | Dm
14 | A4:2 B4:2 C5:2 D5:2             | Dm
15 | C5:2 A4:2 G4:2 E4:2             | C
16 | D4:4 D4:4                       | Dm

Note: Bars 1-8 and 9-16 end on D, so the 16 bars loop cleanly.
Note: Bass works best as driving root eighth notes (punk), the fifth on the last two eighths of a bar.
Confidence: High (the shanty's well-known melody: its first and third lines on A, the second a tone lower on G).
Rhythm checked 2026-10-11 (music step 3) against the Wikifonia lead sheet "What Shall We Do with a Drunken Sailor?" in OpenEWLD (github.com/00sapo/OpenEWLD, a dataset of public-domain scores): the verse matches; the chorus was flattened: "Way hay (and) up she rises" is a quarter, a dotted eighth and a sixteenth (A4:4 A4:3 A4:1), not two quarters (old bars 9, 11 and 13: 'A4:4 A4:4', 'G4:4 G4:4', 'A4:4 A4:4', which left out "and").
Source: Traditional English sea shanty (19th century or earlier), public domain.
```
