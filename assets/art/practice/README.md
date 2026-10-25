# Practice illustrations (BONUS > MINI GAMES, src/mg_list.c)

One picture per mini-game, shown in the empty frame left of the medal on the Practice screen.

- Place: `assets/art/practice/<game>.png`, `<game>` one of quickdraw, shirtcannon, logroll, orderup, marshmallows, batterysort, milkrun, taikopour,
  monkeybusiness, asteroids, shakeup, perfectpour, tipshower (the order of `ml_game` in src/mg_list.c; the GREEN LIGHT stub has none).
- Size: exactly 80 x 64 px (10 x 8 tiles on screen columns 1-10, rows 6-13). The one-tile border the empty frame draws is part of that area: art that
  draws its own border uses all 80 x 64 px; art that relies on the game's border is the inner 64 x 48 px, framed.
- Format: indexed PNG, 4 colours (index 0 lightest ... 3 darkest; one CGB palette per picture, the DMG shades by index), pixel-exact at 8x8 multiples
  (`gbsprite check` and `rgbgfx` take it as it is). At most 80 unique 8x8 tiles after de-duplication, 56 or fewer is the aim.
- Reserved on the screen: BG tile ids 176-255 and 96-175 (the second buffer; on a Color also in VRAM bank 1) and CGB BG palettes 0 and 1 (the picture on screen and the one
  coming in) are for this art only (see ML_ART_T, ML_ART_T2 in src/mg_list.c).
- Pipeline (written, tested against placeholders in `tests/data/practice_art/`, which never ship): `tools/gen_practice_art.py` (the Makefile runs it) checks each PNG
  (80 x 64, indexed, indices 0-3, at most 80 unique tiles: the build fails naming the file; more than 56 only warns), de-duplicates the cells and writes two banked data files and
  `build/practice_art.h`; a game with no PNG shows the empty frame. `src/mg_list.c` (the `pa_` functions) streams the selected game's tiles five a frame through the
  VBlank queue and switches the picture on only when it is complete (a 2-3 frame wipe of whole rows), prefetching the neighbours. A picture is looked for in
  `assets/art/practice/` only; drop the PNGs in and rebuild. `make preview` / any build writes `out/preview/practice_<game>_x4.png`: LOOK at them.
- The 80-tile cap cannot be exceeded by a correctly sized PNG (a 10 x 8 picture has 80 cells); the real budget is the stream: n tiles take n / 5 frames (a locked game shows the
  empty frame, like its name "? ? ?").
