# Melody specs (owner-supplied)

Supplied by the owner (prepared with an internet-connected agent), 2026-10-09.
These are the reference for tools/songs.py. Every tune is public domain; credit each SOURCE line in CREDITS.md.

```
GAME BOY MELODY SPECS - 9 public-domain tunes
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
 7 | R:2 A4:1 G4:2 F4:1                           | C7
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
Confidence: High (from transcription).
Source: Melody from John Chambers' ABC transcription (trillian.mit.edu/~jc/music/abc/Italy/FuniculiFunicula.abc, via folktunefinder.com). Underlying work: Luigi Denza, Ricordi 1880 (public domain). The full verse modulates through A minor and C major after bar 9; that part is omitted here.

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
32 | ~:6                                          | G

Note: Transposed up one octave from the source for a brighter pulse sound.
Note: The long notes are the famous sliding 'skater' notes; a short pitch slide up into bars 1, 5 and 9 sounds idiomatic.
Confidence: High for melody. Chords as given in the source.
Source: Traditional Tune Archive (tunearch.org, 'Skater's Waltz'), transcription by Carl Allison from Joe Buchanan's Scottish Tome. Underlying work: Emile Waldteufel, 1882 (public domain).

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
 8 | ~:6                                          | D
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
20 | A4:4 B4:2                                    | D7
21 | G4:4 A4:2                                    | G
22 | B4:2 C5:2 D5:2                               | G7
23 | E5:6                                         | C
24 | ~:2 E5:2 F#5:2                               | C
  ["For it's one, two, three strikes..."]
25 | G5:2 R:4                                     | C
26 | G5:2 R:4                                     | A7
27 | G5:2 F#5:2 E5:2                              | D
28 | D5:2 C#5:2 D5:2                              | E7
29 | E5:6                                         | Am
30 | F#5:6                                        | D7
31 | G5:6                                         | G
32 | ~:2 R:4                                      | G

Note: Bars 1, 5 and 17: the source writes the first note short followed by a rest (G4 z G5). I've held it instead, the way it's usually sung. Use G4:2 R:2 for a choppier ballpark-organ feel.
Confidence: High.
Source: John Chambers' ABC (trillian.mit.edu/~jc/music/session/waltz/Take_Me_Out_to_the_Ball_Game.abc). Underlying work: Albert Von Tilzer / Jack Norworth, 1908 (public domain).

------------------------------------------------------------
4. SHE'LL BE COMING 'ROUND THE MOUNTAIN (traditional) - one verse
------------------------------------------------------------
Key: D major
Time: 4/4
Tempo: quarter = 160
Unit: 1 = eighth note (bar = 8)
Length: 16 bars + pickup

PICKUP: A4:2 B4:2
 1 | D5:2 D5:2 D5:2 D5:2                          | D
 2 | B4:2 A4:2 F#4:2 A4:2                         | A7
 3 | D5:8                                         | D
 4 | ~:4 D5:2 E5:2                                | D
 5 | F#5:2 F#5:2 F#5:2 F#5:2                      | D
 6 | A5:2 F#5:2 E5:2 D5:2                         | D
 7 | E5:8                                         | A7
 8 | ~:4 A5:2 G5:2                                | A7
 9 | F#5:2 F#5:2 F#5:2 F#5:2                      | D
10 | E5:2 D5:2 D5:2 D5:2                          | D7
11 | B4:2 B4:2 B4:2 B4:2                          | G
12 | E5:2 D5:2 C#5:2 B4:2                         | A7
13 | A4:2 A4:2 A4:2 A4:2                          | D
14 | F#5:2 E5:2 B4:2 C#5:2                        | A7
15 | D5:8                                         | D
16 | ~:4 A4:2 B4:2                                | D

Note: Bar 16 ends with the pickup for the next loop.
Note: Bar 12: the source chord is Ddim; A7 is a simpler substitute that fits the C#.
Confidence: High for melody (cross-checked against an independent letter-note chart).
Source: John Chambers' ABC collection (mirror of David Kidd's dulcimer transcription, originally everythingdulcimer.com). Tune is traditional; in print by Carl Sandburg's 'The American Songbag' (1927), public domain.

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
Source: Ryan's Mammoth Collection (1882), p. 264, via John Chambers' ABC mirror on abcnotation.com. Public domain. Chords are my harmonization (the source gives none).

------------------------------------------------------------
6. THE BLUE DANUBE (Johann Strauss II, 1867, Op. 314) - Waltz 1A, main theme
------------------------------------------------------------
Key: G major (Strauss wrote it in D; this source is transposed)
Time: 3/4
Tempo: quarter = 160
Game tempo: quarter = 192 (9 frames per eighth row, plays at 200). Owner-approved; melody notes unchanged. See GAME_BPM in tools/songs.py.
Unit: 1 = eighth note (bar = 6)
Length: 32 bars

 1 | G3:2 B3:2 D4:2                               | G
 2 | D4:2 R:2 D5:2                                | G
 3 | D5:2 R:2 B4:2                                | G
 4 | B4:2 R:2 G3:2                                | G
 5 | G3:2 B3:2 D4:2                               | G
 6 | D4:2 R:2 D5:2                                | G
 7 | D5:2 R:2 C5:2                                | D7
 8 | C5:2 R:2 F#4:2                               | D7
 9 | F#4:2 A4:2 C5:2                              | D7
10 | C5:2 R:2 E5:2                                | D7
11 | E5:2 R:2 C5:2                                | D7
12 | C5:2 R:2 F#4:2                               | D7
13 | F#4:2 A4:2 C5:2                              | D7
14 | C5:2 R:2 E5:2                                | D7
15 | E5:2 R:2 B4:2                                | G
16 | B4:2 R:2 G3:2                                | G
17 | G3:2 B3:2 D4:2                               | G
18 | G4:2 R:2 G5:2                                | G
19 | G5:2 R:2 D5:2                                | G
20 | D5:2 R:2 G3:2                                | G
21 | G3:2 B3:2 D4:2                               | G
22 | G4:2 R:2 G5:2                                | G
23 | G5:2 R:2 E5:2                                | C
24 | E5:2 R:2 A4:2                                | Am
25 | A4:2 C5:2 E5:2                               | Am
26 | E5:6                                         | A7
27 | ~:2 C#5:2 D5:2                               | A7
28 | B5:6                                         | G
29 | ~:2 G5:2 B4:2                                | G
30 | B4:4 A4:2                                    | D7
31 | E5:4 D5:2                                    | D7
32 | G4:2 R:1 G4:1 G4:2                           | G

Note: Rests follow the source literally. In performance the first note of each 'X R Y' bar is often held through the rest (e.g. D4:4 D5:2), which sounds smoother on a pulse channel.
Note: The source's editor notes the downbeat could be read one bar later; the pitches are not affected.
Note: Range is G3-B5; transpose up a 4th or 5th if the low notes sound muddy.
Confidence: High for pitches; moderate for exact note lengths (see notes).
Source: James Kerr, 'Merry Melodies' vol. 4 (Glasgow, c. 1870s-80s), p. 42 #387, transcribed to ABC by John Chambers (abcnotation.com). Public domain. Chords are my harmonization (the source gives none).

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
16 | A4:1 F#4:1 D4:1 F#4:1 A4:4                   | D

Note: E#4 = F4 (same pitch). Played staccato: about half the written length, then silence.
Note: For a Grieg-like bass, skip the chords and repeat the root as an ostinato: B in A phrases, F# in the B phrase.
Note: 'C#7/C' = C#7 for the first half-bar, C major for the second (the chromatic slide F#, E#, E).
Confidence: High for bars 1-8. Moderate for bars 9-12 (the answer phrase). Bars 13-16 are a return I chose for looping; Grieg's own continuation differs.
Source: NO TRANSCRIPTION SOURCE FOUND. Written from memory. Verify against Grieg's Peer Gynt Suite No. 1 score on IMSLP (imslp.org; the 1888 C.F. Peters edition is public domain) before crediting. Underlying work: Edvard Grieg, 1875 (public domain).

------------------------------------------------------------
8. SAKURA SAKURA (traditional Japanese, Edo period) - full melody
------------------------------------------------------------
Key: A minor (miyako-bushi scale: A B C E F)
Time: 4/4
Tempo: quarter = 72
Game tempo: quarter = 120 (15 frames per eighth row, plays at 120). Owner-approved; melody notes unchanged. See GAME_BPM in tools/songs.py.
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
14 | E4:4 R:4                                     | Am

Note: 14 bars total; about 47 s at 72 bpm, so it's already a full loop. At ~100 bpm it lands near 34 s.
Note: Traditionally unharmonized. A soft A/E drone on the wave channel sounds more authentic than chords. If you use the E chord, try it without the G# (E+B only), since G# isn't in the scale.
Confidence: High (two independent transcriptions agree, except for minor variants in the last two bars).
Source: Melody: John Chambers' ABC 'Sakura (Cherry Blossom)' (trillian.mit.edu/~jc/music/abc/Japan/Sakura_Am.utf8.abc). Chords adapted from Frank Nordberg's Musica Viva transcription (same collection). Traditional; public domain.

------------------------------------------------------------
9. THE ENTERTAINER (Joplin, 1902) - A section, 16 bars
------------------------------------------------------------
Key: C major
Time: 2/4
Tempo: quarter = 90 (Joplin: 'Not fast')
Game tempo: quarter = 112 (8 frames per sixteenth row, plays at 112.5). Owner-approved; melody notes unchanged. See GAME_BPM in tools/songs.py.
Unit: 1 = SIXTEENTH note (bar = 8)
Length: 16 bars + pickup

PICKUP: D5:1 D#5:1
 1 | E5:1 C6:2 E5:1 C6:2 E5:1 C6:1                | C
 2 | ~:4 C6:1 D6:1 D#6:1 E6:1                     | C
 3 | C6:1 D6:1 E6:2 B5:1 D6:2 C6:1                | G7
 4 | ~:4 R:2 D5:1 D#5:1                           | C
 5 | E5:1 C6:2 E5:1 C6:2 E5:1 C6:1                | C
 6 | ~:4 A5:1 G5:1 F#5:1 A5:1                     | D7
 7 | C6:1 E6:2 D6:1 C6:1 A5:1 D6:2                | D7
 8 | ~:4 R:2 D5:1 D#5:1                           | G7
 9 | E5:1 C6:2 E5:1 C6:2 E5:1 C6:1                | C
10 | ~:4 C6:1 D6:1 D#6:1 E6:1                     | C
11 | C6:1 D6:1 E6:2 B5:1 D6:2 C6:1                | G7
12 | ~:4 C6:1 D6:1 E6:1 C6:1                      | C
13 | D6:1 E6:2 C6:1 D6:1 C6:1 E6:2                | C
14 | C6:1 D6:1 E6:2 C6:1 D6:1 C6:2                | F
15 | E6:1 C6:1 D6:2 E6:1 B5:1 D6:2                | G7
16 | C6:4 R:2 D5:1 D#5:1                          | C

Note: Bars 1-11: pitches cross-checked against a published letter-note chart; rhythms are the standard syncopated pattern (16th-8th-16th).
Note: Bars 12-16 (closing phrase): LOW CONFIDENCE. The pitch order may be off. Check these against the 1902 score before shipping.
Note: Bar 16 ends with the D-D# pickup, so it loops cleanly.
Confidence: High for bars 1-11, low for bars 12-16.
Source: Written from memory of the 1902 John Stark & Son edition (public domain; scans on IMSLP, imslp.org, 'The Entertainer (Joplin, Scott)'). Pitches for bars 1-11 checked against pianoletternotes.blogspot.com, which is an arrangement and should NOT be credited as the source. Underlying work: Scott Joplin, 1902 (public domain).
```
