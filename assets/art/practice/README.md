# Practice illustrations (BONUS > MINI GAMES, src/mg_list.c)

One picture per mini-game, shown in the empty frame left of the medal on the Practice screen.

- Place: `assets/art/practice/<game>.png`, `<game>` one of quickdraw, shirtcannon, logroll, orderup, marshmallows, batterysort, milkrun, taikopour,
  monkeybusiness, asteroids, shakeup, perfectpour, tipshower (the order of `ml_game` in src/mg_list.c; the GREEN LIGHT stub has none).
- Size: exactly 80 x 64 px (10 x 8 tiles on screen columns 1-10, rows 6-13). The one-tile border the empty frame draws is part of that area: art that
  draws its own border uses all 80 x 64 px; art that relies on the game's border is the inner 64 x 48 px, framed.
- Format: indexed PNG, 4 colours (index 0 lightest ... 3 darkest; one CGB palette per picture, the DMG shades by index), pixel-exact at 8x8 multiples
  (`gbsprite check` and `rgbgfx` take it as it is). At most 80 unique 8x8 tiles after de-duplication, 56 or fewer is the aim.
- Reserved on the screen: BG tile ids 176-255 and a CGB palette of its own are for this art only (see ML_ART_T in src/mg_list.c).
- Not written yet (needs the first picture to test against): the generator for build/practice_art.h and the few-tiles-a-frame stream that puts the
  selected game's tiles into VRAM (src/boss.c `ld_step` is the model).
