# Spigoteer: credits and licences

> **DRAFT — owner to review.** First pass, proposed text only. The owner decides what is credited and how; every line below
> can be cut or reworded. Items marked (courtesy) are not required by their licences. The evidence for each line, and the
> list of sources that were looked at but not used, is in the audit (kept with the supervisor's notes, not in the repo);
> the previous, more detailed provenance notes are in this file's history.

## Game

- Game design and direction: [OWNER: name / handle]
- Story and writing: [OWNER]
- Programming: [OWNER: credit line for the AI-assisted work, if any]
- Pixel art: [OWNER: who drew the first sprite sheet, `upload/gbc_bar_sprites_native.png`?]; later art drawn in-house and approved by the owner
- Sound effects and the three jingles (level clear, game over, bonus round): original, written for this game
- Special thanks: [OWNER]

## Music

Every composition is in the public domain. The note lists were entered by hand and the arrangement (bass, harmony, rhythm, drums,
instruments) is original; no recording or audio file was used.

| Tune | Where it plays | Composer | Notes checked against | Licence of that reference |
|---|---|---|---|---|
| The Entertainer | title | Scott Joplin, 1902 | Mutopia Project score, typeset by Chris Sawer and Simon Albrecht | public domain (courtesy) |
| Galop infernal | the shows | Jacques Offenbach, 1858 | IMSLP #26815, vocal score, plate 10779 | public domain |
| Oh! Susanna | saloon | Stephen Foster, 1848 | rhythm from the Stephen Foster Song Book encoding in humdrum-tools/foster-songs | public domain (rhythm facts only) |
| Take Me Out to the Ball Game | sports bar | Albert Von Tilzer and Jack Norworth, 1908 | York Music Co. 1908, Library of Congress | public domain |
| She'll Be Coming 'Round the Mountain | lumber lodge | traditional | Simon Horn's MIDI, 2021 | CC0 (courtesy) |
| Funiculi, Funicula | bistro | Luigi Denza, 1880 | Ricordi 1880, IMSLP #148203 | public domain |
| The Skaters' Waltz | igloo | Emile Waldteufel, 1882 | IMSLP #102459 | public domain |
| In the Hall of the Mountain King | robot factory | Edvard Grieg, 1875 | Mutopia Project score, typeset by Coyau | public domain (courtesy) |
| Drunken Sailor | The Chrome Cow | traditional sea shanty | our transcription; OpenEWLD lead sheet for three chorus bars | public domain |
| Sakura Sakura | teahouse | traditional Japanese | Sokyokushu, 1888, National Diet Library | public domain |
| Pop Goes the Weasel | zoo | traditional English | Ryan's Mammoth Collection, 1882 | public domain |
| The Blue Danube | space lounge | Johann Strauss II, 1867 | Mutopia Project score, typeset by Nikos Kouremenos from Christian Mondrup's piano reduction | **CC BY-SA 4.0**, https://creativecommons.org/licenses/by-sa/4.0/ (credit asked) |

Suggested one-line credit for the CC BY-SA item: "The Blue Danube: notes checked against the Mutopia Project edition by Nikos
Kouremenos (CC BY-SA 4.0); arrangement by the Spigoteer team." [OWNER: keep, reword, or drop if you judge the notes to be facts of
a public-domain work.]

Melody lists consulted early on and since superseded or corrected (courtesy thanks, optional): John Chambers' ABC collection;
the Traditional Tune Archive (Carl Allison); the Mutopia Project; IMSLP and its contributors.

## Code libraries

| Library | Used for | Licence | Copyright line |
|---|---|---|---|
| hUGEDriver (modified; see below) | music playback | dedicated to the public domain by its authors (no licence file upstream; see `licenses/hUGEDriver-NOTICE.txt`) | hUGEDriver by SuperDisk and contributors (courtesy) |
| GBDK-2020 4.5.0 | C library and start-up code | GPLv2 with Linking Exception (`licenses/GBDK-runtime-GPLv2-with-linking-exception.txt`); GBDK's manual says no credit or licence text is required with a ROM | GBDK-2020 authors (courtesy) |
| SDCC | compiler and runtime library | runtime libraries GPLv2+LE; generated code is not licensed (`licenses/SDCC-suite-notice.txt`) | SDCC project (courtesy) |

hUGEDriver changes made here: C-visible aliases for the playback position, tick count and note table, a pending-jump pair, and a per-channel
"row has no effects" flag that saves time without changing the sound.

Built with RGBDS, GBDK-2020's lcc, PyBoy and SameBoy (build and test tools, not in the ROM).

## Thanks (optional)

[OWNER] Players, testers, and the open-source Game Boy community (gbdev, Pan Docs).
