// SETTINGS > SCREEN BRIGHT: declarations and the palette macros. #included by game.h and by the generated files that write palettes (tools/gen_story.py).
#ifndef BRIGHT_H
#define BRIGHT_H
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>
// ---- SETTINGS > SCREEN (Color only): NORMAL / BRIGHT, a gamma lift on every palette colour for a Game Boy Advance (its unlit screen shows GBC colours much darker) ----
// No new WRAM: GBDK's _is_GBA (the boot register B, bit 0: a GBA in Color mode) keeps the hardware in bit 0 and the choice in bit 1 (only bit 0 is GBDK's; only this game reads it).
// BRIGHT is set at boot (main_cold.c screen_load): the saved choice, else OFF; on a detected GBA with nothing saved, SCR_ASK (bit 2) also makes the title open a
// one-time prompt (title.c TM_SCR: NORMAL highlighted, the picture switching live as the cursor moves) whose A saves the choice. Never set on a DMG.
// Every palette write that goes through set_bkg_palette / set_sprite_palette is lifted by pal_put (main.c, ROM0: callers sit in any bank); a palette that
// is computed or kept in RAM for a VBlank / fade writer is lifted ONCE when it is made (BRIGHTEN) and written raw, (set_bkg_palette)(...) with the macro off.
// The 32-entry table (src/bright.c) is 31 * (i / 31) ^ 0.7 (tests/test_bright.py checks it); 0 and 31 map to themselves, so black and white (the fades' ends) stay put.
#define SCR_GBA()     (_is_GBA & 1)
#define SCR_BRIGHT()  (_is_GBA & 2)
#define SCR_ASK()     (_is_GBA & 4)                              // bit 2: a GBA with no saved choice: the title opens its SCREEN prompt (TM_SCR) until a line is picked
uint16_t bright_col(uint16_t c) BANKED;                           // one RGB15 colour through the table (src/bright.c)
void pal_lift(uint16_t *q) BANKED;                                // four colours in place
void pal_put_b(uint8_t first, uint8_t n, uint16_t *q) BANKED;     // pal_put's BRIGHT half: n palettes in RAM lifted in place, then written
extern uint16_t pal5_lifted[4];                                   // (render.c)
void pal5_lift(void) BANKED;                                      // pal5_lifted = the show's colours (OBJ palette 5) lifted
void pal5_inst4(uint8_t g) BANKED;                                   // pal5_lifted = palette instance 4's colours (a generated venue: the slot the show gives back) lifted
#define BRIGHTEN(c)   (SCR_BRIGHT() ? bright_col(c) : (c))        // a colour computed in RAM, lifted when SCREEN is BRIGHT
void pal_put(uint8_t first, uint8_t n, const uint16_t *p);        // first | 0x80: OBJ palettes; lifts the colours when BRIGHT, then GBDK's writer
#define set_bkg_palette(first, n, p)     pal_put((first), (n), (p))
#define set_sprite_palette(first, n, p)  pal_put((uint8_t)(first) | 0x80, (n), (p))
void screen_load(void) BANKED;                                    // main_cold.c: the boot's / ERASE DATA's choice (save.c screen_saved) into the flag
void screen_pal_reload(void) BANKED;                              // main_cold.c: the boot palettes (HUD, bartender, coin) again after SETTINGS changed the choice
uint8_t screen_saved(void) BANKED;                                // save.c: 1 NORMAL, 2 BRIGHT as saved, 0 nothing saved
void screen_save(void) BANKED;                                    // save.c: the flag into the save
#endif
