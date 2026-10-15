// The music through a rebuild: the redirects game.h (and the generated story sources) apply after <gb/gb.h>. See the comment below.
#ifndef MPUMP_H
#define MPUMP_H
#include <stdint.h>

// ---- the music through a rebuild (owner 2026-10-15: stutter entering and leaving menus) -------------------------------------
// With the LCD off a screen's rebuild is one long main-loop pass of several frames, and the tune has to tick through it. These
// ROM0 wrappers (main.c) stand in for GBDK's calls in every source that includes this header: each pumps the music (music_pump:
// a tick when a frame's time has passed) after its call while the LCD is off, tile data goes in slices of 8 tiles, and the LCD-off
// wait (a frame when the pass begins late in VBlank) polls the timer instead of sleeping through the tick that falls due in it.
void lcd_off_p(void);
void set_bkg_tiles_p(uint8_t x, uint8_t y, uint8_t w, uint8_t h, const uint8_t *t);
void set_bkg_data_p(uint8_t first, uint8_t n, const uint8_t *d);
void set_sprite_data_p(uint8_t first, uint8_t n, const uint8_t *d);
#undef DISPLAY_OFF
#define DISPLAY_OFF lcd_off_p();
#define set_bkg_tiles(...) set_bkg_tiles_p(__VA_ARGS__)    // (function-like: main.c's wrappers call the real ones as (set_bkg_tiles)(...))
#define set_bkg_data(...) set_bkg_data_p(__VA_ARGS__)
#define set_sprite_data(...) set_sprite_data_p(__VA_ARGS__)

#endif
