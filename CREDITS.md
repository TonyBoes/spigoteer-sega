# Spigoteer: credits

These are the release credits. The same words roll in the game after the story's last page and under BONUS > CREDITS
(`src/credits.c`); change one place, change the other.

## Game

Game Design, Media, and Story by Tony and his tireless team of robot friends.

## Music

The music is public domain: public-domain melodies, arranged for this game. The arrangements (bass, harmony, rhythm, drums,
instruments), the sound effects and the three jingles (level clear, game over, bonus round) are original to this game.

## Special thanks to

- GBDK-2020, the C library and toolchain the game is written on
- SDCC, the compiler under GBDK
- hUGEDriver (SuperDisk and contributors), the music driver (modified here; see below)
- RGBDS, the assembler that builds the music driver
- SameBoy, the accuracy emulator the game was checked against
- PyBoy, the emulator the tests drive
- Pan Docs, the Game Boy hardware reference
- The Game Boy development community (gbdev)

## Licences

The licence texts that travel with the code libraries are in `licenses/`:

| Library | Used for | Licence |
|---|---|---|
| hUGEDriver (modified) | music playback | dedicated to the public domain by its authors (no licence file upstream; see `licenses/hUGEDriver-NOTICE.txt`) |
| GBDK-2020 4.5.0 | C library and start-up code | GPLv2 with Linking Exception (`licenses/GBDK-runtime-GPLv2-with-linking-exception.txt`); GBDK's manual says no credit or licence text is required with a ROM |
| SDCC | compiler and runtime library | runtime libraries GPLv2+LE; generated code is not licensed (`licenses/SDCC-suite-notice.txt`) |

hUGEDriver changes made here: C-visible aliases for the playback position, tick count and note table, a pending-jump pair, and a
per-channel "row has no effects" flag that saves time without changing the sound.
