// Spigoteer for Game Boy / Game Boy Color: game flow, screens, HUD and score, input, and the frame loop.
// The rules live in patrons.c and mugs.c, the BG composition and the VBlank queue in render.c (see game.h).
//
// Everything a test can assert on is a plain global in WRAM, so it shows up
// in build/game.noi and tests/ can read it by name (bar, bartender_x, ...).
//
// Conventions:
//   - positions in pixels, screen coordinates (OAM's +8/+16 offset is added
//     only when writing OAM)
//   - the whole frame runs between vsync() calls; OAM is written through
//     GBDK's shadow OAM and DMA'd in the VBlank handler
//   - sprites are 8x16; the bartender is 4 entries (2 columns x 2 rows)
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>
#include <string.h>

#include "game.h"
#include "tip2.h"
#include "palettes.h"
#include "bonus.h"
#include "music.h"
#include "mg.h"
#include "asm_cfg.h"
#include "showlights.h"

BANKREF_EXTERN(art_tiles)

// ---- SETTINGS > SCREEN BRIGHT (bright.h): the palette writer every set_*_palette call goes through; ROM0 because its callers sit in every bank and pass pointers
// into theirs (a banked function could not read them). NORMAL: GBDK's writer straight through (one extra call). BRIGHT: the palettes (8 at most: 64 bytes of
// stack) are copied out, and src/bright.c lifts and writes them.
void pal_put(uint8_t first, uint8_t n, const uint16_t *p) {
    uint16_t q[32];
    if (SCR_BRIGHT()) { memcpy(q, p, (uint8_t)(n << 3)); pal_put_b(first, n, q); return; }
    if (first & 0x80) (set_sprite_palette)(first & 0x7F, n, p); else (set_bkg_palette)(first, n, p);
}

// Tile data lives in switchable banks (build/art.c, build/venue_*.c); these copy it to VRAM (LCD off or VBlank
// only) or WRAM and switch back to the caller's bank, so banked code (venue.c) can use them too.
void bkg_data_far(uint8_t first, uint8_t n, const uint8_t *d, uint8_t bank) {
    uint8_t saved = CURRENT_BANK;
    SWITCH_ROM(bank);
    set_bkg_data(first, n, d);
    SWITCH_ROM(saved);
}

void spr_data_far(uint8_t first, uint8_t n, const uint8_t *d, uint8_t bank) {
    uint8_t saved = CURRENT_BANK;
    SWITCH_ROM(bank);
    set_sprite_data(first, n, d);
    SWITCH_ROM(saved);
}

void far_copy(void *dst, const void *src, uint16_t n, uint8_t bank) {
    uint8_t saved = CURRENT_BANK;
    SWITCH_ROM(bank);
    memcpy(dst, src, n);
    SWITCH_ROM(saved);
}

// (game.h redirects GBDK's calls to these: the music ticks through an LCD-off rebuild. The names in parentheses are the real ones.)
void lcd_off_p(void) {
    uint8_t w = TRANS;
    TRANS = w & ~TR_WANT;
    if (!(LCDC_REG & LCDCF_ON)) return;
    if ((w & (TR_WANT | TR_OFF)) == TR_WANT && game_state != GS_PAUSED) { trans_cover(); return; }   // (a scene change: the drink fills the screen, then the LCD goes off)
    while (LY_REG >= 0x92) music_pump();        // (display_off's own two waits: the LCD goes off at line 145)
    while (LY_REG < 0x91) music_pump();
    LCDC_REG &= ~LCDCF_ON;
    if (SPLIT_ON) split_off();                  // (the Color level screen's palette split: the stage's palette back; banked, level.c)
}

void lcd_on_p(void) {
    uint8_t t = TRANS;
    if (t & TR_PEND) trans_arm();                // (a scene change: the drink is the first frame, src/trans.c)
    LCDC_REG |= LCDCF_ON;
    if ((t & (TR_PEND | TR_HOLD)) == TR_PEND) trans_reveal();   // (the new scene is up: the drink drains; TR_HOLD: the caller still has work to do, and reveals itself)
}

void set_bkg_tiles_p(uint8_t x, uint8_t y, uint8_t w, uint8_t h, const uint8_t *t) {
    (set_bkg_tiles)(x, y, w, h, t);
    if (!(LCDC_REG & LCDCF_ON)) music_pump();
}

static void data_p(uint8_t obj, uint8_t first, uint8_t n, const uint8_t *d) {
    uint8_t k;
    do {
        k = n > 8 ? 8 : n;
        if (obj) (set_sprite_data)(first, k, d); else (set_bkg_data)(first, k, d);
        if (!(LCDC_REG & LCDCF_ON)) music_pump();
        first += 8; d += 128;
    } while (n -= k);
}
void set_bkg_data_p(uint8_t first, uint8_t n, const uint8_t *d) { data_p(0, first, n, d); }
void set_sprite_data_p(uint8_t first, uint8_t n, const uint8_t *d) { data_p(1, first, n, d); }

#define bkg_data(first, n, d) bkg_data_far(first, n, d, BANK(art_tiles))
#define spr_data(first, n, d) spr_data_far(first, n, d, BANK(art_tiles))

// Per-section frame cost in DIV ticks (256 cycles), only in a measurement build (-DPERF_SECTIONS); SEC / SEC_P* in game.h.
#ifdef PERF_SECTIONS
uint8_t  sec_frame[SEC_N];        // this frame's ticks per section
uint8_t  sec_done[SEC_N];         // ... of the last finished frame, and its frame_counter (read by the measuring script)
uint8_t  sec_done_id;
uint8_t  sec_t;
void sec_mark(uint8_t i) { uint8_t t = DIV_REG; sec_frame[i] += (uint8_t)(t - sec_t); sec_t = t; }
#endif

// game flow
#define CLEAR_FRAMES        150


// ---- state (globals => symbols) ----------------------------------------------
uint8_t  bar;               // 0 top .. 3 bottom
uint8_t  bartender_x;       // pixel x of the bartender's left edge (screen coords)
uint8_t  bartender_frac;    // sub-pixel part of his walk (1/256 px); 0 whenever he stands
uint8_t  facing;            // 0 left, 1 right
uint8_t  bartender_frame;   // BT_*
uint8_t  catch_pose;        // frames left of BT_CATCH (an empty caught, a glass taken; M8d)
uint8_t  at_tap;            // 1 when bartender_x == bar_tap[bar] (TAP_X on a straight bar)
uint8_t  tap_now;           // bar_tap[bar], set at the start of every play frame (mugs.c: the catch at the tap, the spout)
uint8_t  walk_timer;        // frames into the current step of the walk cycle (0..WALK_STEP_FRAMES-1)
uint8_t  bt_bob;           // 1 on the passing poses of the walk: his sprites are drawn 1 px higher
uint8_t  walk_phase;        // step of the walk cycle: 0 walk1, 1 idle, 2 walk2, 3 idle
uint8_t  frame_counter;
uint8_t  joy, joy_prev;
uint32_t score;             // HUD shows 6 digits
uint8_t  is_cgb;            // running on colour hardware
uint8_t  lives = START_LIVES;
uint32_t extra_at;          // the score that gives the next extra life (ARCADE, CLASSIC; 0: none in this mode)
uint8_t  level = 1;
uint8_t  fill_timer;        // frames A has been held at the tap (0 = not filling)
uint8_t  fill_stage;        // 0..3 mug fill animation frame while filling (0 otherwise)
uint8_t  slide_timer;       // frames left showing the "slide" pose
uint8_t  game_over;         // set when lives reach 0; gameplay freezes
uint8_t  game_state;        // GS_*
uint8_t  state_timer;       // frames spent in LIFE_LOST / LEVEL_CLEAR
uint8_t  life_lost;         // a life went this frame; the state machine reacts at the end of update()
uint8_t  overlay_on;        // window banner shown
uint32_t hi_score;          // entry 1 of the top-5 table (save.c, SRAM)
uint8_t  hi_digits[6];
uint8_t  served;            // patrons served (pushed back to the left end) this level
uint8_t  start_mask, start_per_bar, cur_group;
uint8_t  hud_dirty;         // HUD_LIVES / HUD_SCORE bits: needs redrawing
uint8_t  score_digits[6];   // the HUD digits, most significant first
uint8_t  level_clear;       // quota spawned, no patrons, no mugs

// level state (loaded from level_table by start_level)
uint8_t  quota, spawned, step_frames, pushback_cols, serve_score, empty_gap;
uint8_t  patron_speed;      // walking speed in 1/256 px per frame
uint8_t  pushback_px;       // pushback_cols * 8
uint16_t spawn_interval, spawn_timer;   // frames; 16-bit: level 1 spawns every 300
uint8_t  intro_timer;
uint8_t  rng_state;
uint8_t  tip_chance = TIP_CHANCE_DEFAULT;   // 0..255 out of 256; 255 = always
uint16_t tip_timer;         // frames the tip has left (0 = no tip on screen)
uint8_t  tip_bar, tip_x;    // where the coin lies (screen x of its left edge)
uint16_t show_timer;        // frames the show has left (0 = no show)
uint8_t  dancer_frame;      // 0 stand, 1 left kick, 2 arms up, 3 right kick
uint8_t  dance_tick;        // frames in the current dance step

// ---- palettes ----------------------------------------------------------------

// ---- scene -------------------------------------------------------------------
// prep_hud, lose_life and end_note: src/main_cold.c (banked: ROM0 relief for the mid-frame palette split's handlers)
// add_score (score as 32-bit total plus decimal digits) lives in src/rom0_relief.c, banked: ROM0 relief.


// The mid-frame palette split (game.h SPLIT_*): a stage palette is rewritten from `src` (8 bytes; HBlank, VBlank or LCD off). The late one (SPLIT_LY, the Saloon's BG 5)
// is BCPS SPLIT_L_BCPS, the early one (SPLIT_EARLY_LY, another venue's stage palette that ends a row sooner) SPLIT_E_BCPS.
#if ASM_SPLIT_PAL
void split_pal_put(const volatile uint8_t *src) __naked {      // the late palette
    (void)src;
__asm
    ld   a, (_story_scratch + SCR_SPLIT_AT + 1)   ; BCPS of the late palette
_split_put_a::                      ; A = BCPS (auto-increment), DE = the 8 bytes
    ldh  (0x68), a
    ld   h, d
    ld   l, e
    ld   c, #0x69                   ; BCPD
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl)
    ldh  (c), a
    ret
_split_put_o2::                     ; the next line's HBlank, then the write below: this HBlank over first (mode 2 or 3: not "mode 3", which WasmBoy, Pocket Player's core, never reports: it hung there, owner 11-03), then mode 0
    ld   h, a
    ldh  a, (0x44)
    cp   a, #38
    ret  nc                         ; (late: the first write was a frame's end away, or in the VBlank: no line to wait for before the next frame's)
9403$:
    ldh  a, (0x41)
    and  a, #3
    jr   z, 9403$
9404$:
    ldh  a, (0x41)
    and  a, #3
    jr   nz, 9404$
    ld   a, h
_split_put_o::                      ; OBJ palettes during a show (game.h EV_OBJ, EV_OBJS): A = OCPS, DE = the 8 bytes (split_isr3 / split_isr3n after the HBlank wait, nothing before the write: it must be out before
    ldh  (0x6A), a                  ; mode 3 of the next line; tests/test_show_obj5.py hooks this, _split_put_o2 and _split_put_oe: every write must be in HBlank). OCPS: auto-increment
    ld   h, d
    ld   l, e
    ld   c, #0x6B                   ; OCPD
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl)
    ldh  (c), a
_split_put_oe::                     ; what comes next is by the source (DE): OBJ 5's give-back (OBJ_PAT) goes on to OBJ 4's and OBJ 3's, the show's OBJ 3 (OBJX_SHOW) to OBJ 4's; the others are the second and third writes: done
    ld   a, e
    cp   a, #<(_story_scratch + 218)
    jr   z, 9407$
    cp   a, #<(_story_scratch + 16)
    ret  nz
    ld   a, #0xE0                   ; the show's OBJ 4 (OBJX_SHOW + 8)
    ld   de, #_story_scratch + 24
    jr   _split_put_o2
9407$:
    ld   a, (_story_scratch + 226)  ; OBJX_F: three show palettes: bit 1 OBJ 4's give-back, bit 2 OBJ 3's, each in the HBlank of the next line (and the one after)
    ld   b, a
    bit  1, b
    jr   z, 9401$
    ld   a, #0xE0                   ; OBJ 4's OCPS
    ld   de, #_story_scratch + 0    ; OBJX_PAT4
    call _split_put_o2
9401$:
    bit  2, b
    ret  z
    ld   a, #0xD8                   ; OBJ 3's
    ld   de, #_story_scratch + 8    ; OBJX_PAT3
    jr   _split_put_o2
__endasm;
}
#else
void split_pal_put(const volatile uint8_t *src) {
    uint8_t i;                                  // (cold, LCD off: a loop; the hot callers write the bytes themselves, split_line / split_vbl)
    BCPS_REG = SPLIT_L_BCPS;
    for (i = 0; i != 8; i++) BCPD_REG = src[i];
}
#endif

void set_wy(uint8_t x) {      // (game.h SET_WY: out of line, ROM0)
    WY_REG = x;
    if (SPLIT_ON == 3 && (LCDC_REG & LCDCF_ON)) split_plan();   // (LCD off: the screen's builder plans once at its end, WIN_SYNC; a plan is ~15000 cycles, the pause card's build has the music to tick)
}
void lcd_isr(void) {          // LYC: switch the banner window off below the banner
    HIDE_WIN;
}

#if ASM_SPLIT_PAL
// (asm: the window's end must be hidden as early as lcd_isr does, a few cycles late and a 48 px menu shows one line more; a split line gives the window back
// before its pixels start, unless it is also the window's own line)
// The events of a frame, in line order: the early reload (31, when SPLIT_E_BCPS), the late one (39), the window's own line (SPLIT_WANT, anywhere). LYC holds the next one;
// a window line only records itself in SPLIT_WANT. The next event after line b: the first of the chain lines after b, or the window's line if that comes sooner.
typedef char split_ly_is_39[(SPLIT_LY == 39) ? 1 : -1];
typedef char split_early_is_31[(SPLIT_EARLY_LY == 31) ? 1 : -1];
typedef char split_stage_is_5[(BGPAL_STAGE == 5) ? 1 : -1];
void split_isr(void) __naked {          // the Saloon's one reload (SPLIT_ON 1): cycle for cycle what it was before the chain existed
__asm
    ldh  a, (0x40)                  ; LCDC
    ld   c, a
    res  5, a
    ldh  (0x40), a                  ; HIDE_WIN
    ldh  a, (0x45)                  ; LYC
    cp   a, #39                     ; SPLIT_LY
    jr   z, 9100$
    ldh  (0xD5), a                  ; SPLIT_WANT = the window's line
    ld   a, #39
    ldh  (0x45), a
    ret
9100$:
    ld   a, c
    ldh  (0x40), a                  ; the window as it was
9101$:
    ldh  a, (0x41)                  ; STAT: HBlank, palette RAM is open; the line's pixels are out
    and  a, #3
    jr   nz, 9101$
    ld   de, #0xFFD6                ; SPLIT_PAL
    ld   a, #0xA8                   ; BCPS: BG 5, auto-increment
    call _split_put_a
    ldh  a, (0xD5)
    ldh  (0x45), a                  ; LYC = SPLIT_WANT
    ret
__endasm;
}
#else
static void split_line(void) {  // (the Saloon's split line, in its own function: the ISR's frame must not cost cycles before the window is hidden)
    // (the 8 bytes are read from their fixed HRAM addresses as they go out, `ldh a, (n)` then `ldh (c), a`: no pre-read into locals, whose spills ended after the line did)
    while (STAT_REG & 3) ;                     // (HBlank: palette RAM is open; the line's pixels are out)
    BCPS_REG = 0x80 | (BGPAL_STAGE << 3);
    BCPD_REG = SPLIT_PAL[0]; BCPD_REG = SPLIT_PAL[1]; BCPD_REG = SPLIT_PAL[2]; BCPD_REG = SPLIT_PAL[3];
    BCPD_REG = SPLIT_PAL[4]; BCPD_REG = SPLIT_PAL[5]; BCPD_REG = SPLIT_PAL[6]; BCPD_REG = SPLIT_PAL[7];
    LYC_REG = SPLIT_WANT;
}

void split_isr(void) {        // (the Saloon's, the C twin: the one reload)
    uint8_t lcdc = LCDC_REG;
    LCDC_REG = lcdc & ~0x20;                   // (HIDE_WIN, from the one read)
    if (LYC_REG == SPLIT_LY) {
        LCDC_REG = lcdc;                       // (the window as it was)
        split_line();
        return;
    }
    SPLIT_WANT = LYC_REG; LYC_REG = SPLIT_LY;
}

#endif

void split_vbl(void) {        // vq_vbl's place while the split is armed (the VBlank chain keeps its one entry)
#if ASM_SPLIT_PAL
    split_pal_put(SPLIT_STG);
#else
    BCPS_REG = SPLIT_L_BCPS;                   // (the C twin: fixed HRAM addresses, `ldh a, (n)`: through a pointer parameter SDCC spends 4 lines of a frame here)
    BCPD_REG = SPLIT_STG[0]; BCPD_REG = SPLIT_STG[1]; BCPD_REG = SPLIT_STG[2]; BCPD_REG = SPLIT_STG[3];
    BCPD_REG = SPLIT_STG[4]; BCPD_REG = SPLIT_STG[5]; BCPD_REG = SPLIT_STG[6]; BCPD_REG = SPLIT_STG[7];
#endif
    vq_vbl();
}

// ---- mode 3 (SPLIT_ON 3, every venue but the Saloon): game.h KEG_* / SPLIT_E_* / SPLIT_L_*. C only: the writes are split_put_a (asm label, or its C twin below).
#if !ASM_SPLIT_PAL
// (the 8 bytes unrolled: a counted loop cost ~120 T-cycles a byte, 960 for the put against the asm's 156; two puts in the VBlank chain made the C build's main loop resume
// 4 lines after the asm build's, so a fade's vframe (src/trans.c: lines 144-149) never found a frame in time: a livelock at Color normal speed, tests/test_c_state_equiv.py)
static void put8(volatile uint8_t *reg, const uint8_t *s) {   // (the source is plain bytes: no reload per store; one copy, ROM0 is tight: ~190 T-cycles of stores)
    *reg = *s++; *reg = *s++; *reg = *s++; *reg = *s++; *reg = *s++; *reg = *s++; *reg = *s++; *reg = *s;
}
static void put_o8(uint8_t ocps, const volatile uint8_t *src, uint8_t wait) {   // (C twin: 8 bytes at OCPS, in the HBlank after the next mode 3 when `wait`)
    if (wait) { while (!(STAT_REG & 3)) ; while (STAT_REG & 3) ; }   // (this HBlank over, then the next: no wait for mode 3, which WasmBoy never reports)
    OCPS_REG = ocps;
    put8(&OCPD_REG, (const uint8_t *)src);
}
static void put_obj(uint8_t bcps, const volatile uint8_t *src) {   // (EV_OBJ: OBJ 5, then with three show palettes OBJ 4 and OBJ 3, each in the next line's HBlank. EV_OBJS: OBJ 3, then OBJ 4 with the show's colours)
    uint8_t f = OBJX_F;
    put_o8(bcps, src, 0);
    if (bcps == 0xD8) put_o8(0xE0, src + 8, 1);
    else {
        if (f & 2) put_o8(0xE0, OBJX_PAT4, 1);
        if (f & 4) put_o8(0xD8, OBJX_PAT3, 1);
    }
}
void split_put_a(uint8_t bcps, const volatile uint8_t *src) {   // (the C twin of the asm label: 8 bytes at BCPS; the BG put first, nothing before its stores)
    if (bcps & 0x40) { put_obj(bcps, src); return; }
    BCPS_REG = bcps;
    put8(&BCPD_REG, (const uint8_t *)src);
}
#endif

// The ISR walks the frame's event list (level.c split_plan keeps it: sorted lines, one palette at most on each, EV_*): the LYC hit at an event's line writes its palette in that line's
// HBlank (the next line shows it). The window is hidden FIRST (a window's end on its own line must be as early as lcd_isr's) and given back unless this line is its end (SPLIT_WANT).
// Every hit comes from the list, so a line the list does not name never fires. The hit decodes its own event (EV_I): LYC is the next event's line first thing after the window, so a
// handler that runs on past the next line still has that hit waiting, and the VBlank has no event to decode.
#if ASM_SPLIT_PAL
// (asm, behind ASM_SPLIT_PAL; the C twin is under #else: the same walk. Cycles are the CPU's T-cycles at double speed: a line is 912, the handler starts ~160 into it, the HBlank is
// open from ~500, a palette write is ~190, the dispatcher's own exit waits for an HBlank (STAT) when the handler is still running as the next line begins: ~540 more. So the whole hit,
// decode included, has to be out by 912.) The kinds' table: 5 bytes each, EV_* are their offsets: the window state it wants (0xFF any), where its BCPS is kept (0: none), its palette.
void split_isr3(void) __naked {
__asm
    ldh  a, (0x40)                  ; LCDC
    ld   c, a
    res  5, a
    ldh  (0x40), a                  ; HIDE_WIN
    ldh  a, (0x45)                  ; LYC: this line
    ld   b, a
    bit  5, c
    jr   z, 9100$                   ; (no window was up)
    ldh  a, (0xD5)                  ; SPLIT_WANT
    cp   a, b
    jr   z, 9100$                   ; (this line is its end: it stays off)
    ld   a, c
    ldh  (0x40), a                  ; the window as it was
9100$:
    ld   hl, #_story_scratch + 287  ; EV_I
    ld   a, (hl)
    ld   b, a                       ; i
    inc  a
    ld   e, a                       ; i + 1
    ld   a, (_story_scratch + 286)  ; EV_N
    cp   a, e
    ld   a, e
    jr   nz, 9140$
    xor  a, a                       ; the last: the first is next
9140$:
    ld   (hl), a                    ; EV_I
    ld   a, e                       ; LYC = the line of event i + 1 (the sentinel after the last: the first's)
    add  a, a
    ld   e, a
    ld   d, #0
    ld   hl, #_story_scratch + 369
    add  hl, de
    ld   a, (hl)
    ldh  (0x45), a
    ld   a, b                       ; this event's kind
    add  a, a
    ld   e, a
    ld   hl, #_story_scratch + 370
    add  hl, de
    ld   e, (hl)
    ld   hl, #9310$
    add  hl, de
    ld   a, (hl+)                   ; the window state it wants
    cp   a, #0xFF
    jr   z, 9110$
    ld   b, a
    ld   a, c
    and  a, #0x20
    cp   a, b
    ret  nz                         ; (not this window state: nothing to write)
9110$:
    ld   a, (hl+)
    ld   e, a
    ld   a, (hl+)
    ld   d, a                       ; DE: where its BCPS is kept
    or   a, e
    ret  z                          ; (the window's end line: no palette)
    ld   a, (hl+)
    ld   c, a
    ld   b, (hl)                    ; BC: its 8 colour bytes
    ld   a, (de)
    ld   h, a                       ; its BCPS
    ld   d, b
    ld   e, c
    ld   a, l                       ; (L is still the row's end: the keg-and-late row)
    cp   a, #<(9310$ + 49)
    jr   z, 9300$
    bit  6, h
    jr   nz, 9320$                  ; EV_OBJ (its OCPS has bit 6 set; same cost as the compare it replaces)
9121$:
    ldh  a, (0x41)                  ; STAT: HBlank, palette RAM is open; the line's pixels are out
    and  a, #3
    jr   nz, 9121$
    ld   a, h
    jp   _split_put_a
9320$:                              ; EV_OBJ: its own wait and tail, so the BG palettes' paths cost what they did
    ldh  a, (0x41)
    and  a, #3
    jr   nz, 9320$
    ld   a, h
    jp   _split_put_o
9300$:                              ; EV_KEG_L: the keg's palette and the late one's in one HBlank, nothing but the 16 writes after it opens (BCPS, pointers and the second BCPS
    ld   a, h                       ; are set while it waits: they are not palette RAM accesses). 32 (poll) + 128 + 28 + 128 = ~316 cycles from the HBlank's start; the
    ldh  (0x68), a                  ; last write is then at most ~310 into HBlank + the next line's mode 2 (~1072 - 8 at the latest mode 3 end, Pan Docs' 289 dots = 738): no write in mode 3
    ld   a, (_story_scratch + 237)  ; the late palette's BCPS
    ld   b, a
    ld   h, d
    ld   l, e
    ld   c, #0x69
9301$:
    ldh  a, (0x41)
    and  a, #3
    jr   nz, 9301$
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl)
    ldh  (c), a
    ld   a, b
    ldh  (0x68), a
    ld   hl, #0xFFD6                ; SPLIT_PAL
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl)
    ldh  (c), a
    ret
9310$:                              ; by EV_*: the window it wants, BCPS at, palette
    .db 0xFF
    .dw 0, 0
    .db 0xFF                                         ; EV_E
    .dw _story_scratch + 236, _story_scratch + 238
    .db 0xFF                                         ; EV_L (SPLIT_PAL)
    .dw _story_scratch + 237, 0xFFD6
    .db 0xFF                                         ; EV_KEG (KEG_PAL)
    .dw _story_scratch + 235, _story_scratch + 270
    .db 0x00                                         ; EV_KEG_HID
    .dw _story_scratch + 235, _story_scratch + 270
    .db 0x20                                         ; EV_HUD_SHOWN (KEG_STG)
    .dw _story_scratch + 235, _story_scratch + 278
    .db 0x20                                         ; EV_KEG_SHOWN
    .dw _story_scratch + 235, _story_scratch + 270
    .db 0xFF                                         ; EV_HUD_END
    .dw _story_scratch + 235, _story_scratch + 278
    .db 0x40                                         ; EV_PAD: never this window state
    .dw 0, 0
    .db 0xFF                                         ; EV_KEG_L (the keg's put, then the late palette's)
    .dw _story_scratch + 235, _story_scratch + 270
    .db 0xFF                                         ; EV_OBJ (OBJ_PAT; its OCPS: bit 6 makes _split_put write OCPD)
    .dw 9340$, _story_scratch + 218
    .db 0xFF                                         ; EV_OBJS (OBJX_SHOW)
    .dw 9340$ + 1, _story_scratch + 16
9340$:
    .db 0xE8, 0xD8
__endasm;
}
void split_isr3n(void) __naked {
__asm
    ldh  a, (0x40)                  ; LCDC: the window as it stands
    ld   c, a
    ldh  a, (0x45)                  ; LYC: this event's line less SPLIT_OFF
    ld   b, a
    ldh  a, (0xE6)                  ; SPLIT_OFF
    add  a, b
    ldh  (0xE7), a                  ; SPLIT_TGT: its line
    ld   hl, #_story_scratch + 287  ; EV_I
    ld   a, (hl)
    ld   b, a                       ; i
    inc  a
    ld   e, a                       ; i + 1
    ld   a, (_story_scratch + 286)  ; EV_N
    cp   a, e
    ld   a, e
    jr   nz, 9140$
    xor  a, a                       ; the last: the first is next
9140$:
    ld   (hl), a                    ; EV_I
    ld   a, e                       ; LYC = the line of event i + 1 (the sentinel after the last: the first's)
    add  a, a
    ld   e, a
    ld   d, #0
    ld   hl, #_story_scratch + 369
    add  hl, de
    ld   a, (hl)
    ldh  (0x45), a
    ld   a, b                       ; this event's kind
    add  a, a
    ld   e, a
    ld   hl, #_story_scratch + 370
    add  hl, de
    ld   a, (hl)
    ld   e, a
    and  a, #0xC0                   ; EV_HIDE_FIRST (6): the window off on the event's line, before its palette; EV_HIDE_AFTER (7): off after it
    ldh  (0xE8), a
    ld   a, e
    and  a, #0x3F
    ld   e, a
    cp   a, #45                     ; EV_KEG_L: the keg's put on its line, the late palette's in the next line's HBlank (flag bit 5)
    jr   nz, 9185$
    ldh  a, (0xE8)
    or   a, #0x20
    ldh  (0xE8), a
9185$:
    ld   hl, #9310$
    add  hl, de
    ld   a, (hl+)                   ; the window state it wants
    cp   a, #0xFF
    jr   z, 9110$
    ld   b, a
    ld   a, c
    and  a, #0x20
    cp   a, b
    ret  nz                         ; (not this window state: nothing to write)
9110$:
    ld   a, (hl+)
    ld   e, a
    ld   a, (hl+)
    ld   d, a                       ; DE: where its BCPS is kept
    or   a, e
    jr   z, 9160$                   ; (the window's end line: no palette)
    ld   a, (hl+)
    ld   c, a
    ld   b, (hl)                    ; BC: its 8 colour bytes
    ld   a, (de)
    ld   h, a                       ; its BCPS
    ld   d, b
    ld   e, c
    ldh  a, (0xE7)
    ld   b, a                       ; its line
    ldh  a, (0xE8)
    ld   l, a                       ; the window flags
    bit  6, h
    jp   nz, 9330$                  ; EV_OBJ (its OCPS has bit 6 set; split_plan keeps its line off the window's: no flags)
    bit  6, l
    jr   z, 9121$
9170$:
    ldh  a, (0x44)                  ; (the window ends on this line: it goes off as the line starts, then the palette in its HBlank)
    cp   a, b
    jr   c, 9170$
    ldh  a, (0x40)
    res  5, a
    ldh  (0x40), a
9121$:
    ldh  a, (0x44)                  ; LY: the hit comes SPLIT_OFF lines early at normal speed (the handler is too slow to be in this line's HBlank otherwise): wait for the line
    cp   a, b
    jr   c, 9121$
    ldh  a, (0x41)                  ; STAT: HBlank (or VBlank), palette RAM is open; the line's pixels are out
    and  a, #2
    jr   nz, 9121$
    ld   a, h
    bit  5, l
    jr   nz, 9180$
    bit  7, l
    jp   z, _split_put_a
    call _split_put_a
    jr   9162$                      ; (the window ends on the next line: off now)
9180$:
    call _split_put_a               ; the keg's
    ldh  a, (0xE7)
    inc  a
    ld   b, a                       ; the late palette's line
9181$:
    ldh  a, (0x44)
    cp   a, b
    jr   c, 9181$
9183$:
    ldh  a, (0x41)
    and  a, #2
    jr   nz, 9183$
    ld   de, #0xFFD6                ; SPLIT_PAL
    ld   a, (_story_scratch + 237)  ; its BCPS
    jp   _split_put_a
9330$:                              ; EV_OBJ: its line (the hit comes SPLIT_OFF early), then its HBlank, then OCPD
    ldh  a, (0x44)
    cp   a, b
    jr   c, 9330$
    ldh  a, (0x41)
    and  a, #2
    jr   nz, 9330$
    ld   a, h
    jp   _split_put_o
9160$:
    ldh  a, (0xE7)                  ; the window's end line: wait for it, then hide
    ld   b, a
9161$:
    ldh  a, (0x44)
    cp   a, b
    jr   c, 9161$
9162$:
    ldh  a, (0x40)
    res  5, a
    ldh  (0x40), a                  ; HIDE_WIN
    ret
9310$:                              ; by EV_*: the window state it wants, BCPS at, palette
    .db 0xFF
    .dw 0, 0
    .db 0xFF                                         ; EV_E
    .dw _story_scratch + 236, _story_scratch + 238
    .db 0xFF                                         ; EV_L (SPLIT_PAL)
    .dw _story_scratch + 237, 0xFFD6
    .db 0xFF                                         ; EV_KEG (KEG_PAL)
    .dw _story_scratch + 235, _story_scratch + 270
    .db 0x00                                         ; EV_KEG_HID
    .dw _story_scratch + 235, _story_scratch + 270
    .db 0x20                                         ; EV_HUD_SHOWN (KEG_STG)
    .dw _story_scratch + 235, _story_scratch + 278
    .db 0x20                                         ; EV_KEG_SHOWN
    .dw _story_scratch + 235, _story_scratch + 270
    .db 0xFF                                         ; EV_HUD_END
    .dw _story_scratch + 235, _story_scratch + 278
    .db 0x40                                         ; EV_PAD: never this window state
    .dw 0, 0
    .db 0xFF                                         ; EV_KEG_L
    .dw _story_scratch + 235, _story_scratch + 270
    .db 0xFF                                         ; EV_OBJ
    .dw 9340$, _story_scratch + 218
    .db 0xFF                                         ; EV_OBJS
    .dw 9340$ + 1, _story_scratch + 16
9340$:
    .db 0xE8, 0xD8
__endasm;
}
#else
void split_isr3(void) {       // (the C twin: the same decode)
    uint8_t lcdc = LCDC_REG, tgt = LYC_REG + SPLIT_OFF, i = EV_I, kk = EV_KIND(i), k = kk & 0x3F, r = 0xFF, b = KEG_BCPS;
    const volatile uint8_t *s = KEG_PAL;
    EV_I = i + 1 == EV_N ? 0 : i + 1;
    LYC_REG = EV_LINE(i + 1);
    if (k == EV_E) { b = SPLIT_E_BCPS; s = SPLIT_E_PAL; }
    else if (k == EV_L) { b = SPLIT_L_BCPS; s = SPLIT_PAL; }
    else if (k == EV_OBJ) { b = 0xE8; s = OBJ_PAT; }
    else if (k == EV_OBJS) { b = 0xD8; s = OBJX_SHOW; }
    else if (k >= EV_KEG_HID) {
        r = k == EV_KEG_HID ? 0 : (k == EV_HUD_END || k == EV_KEG_L) ? 0xFF : k == EV_PAD ? 0x40 : 0x20;
        if (k == EV_HUD_SHOWN || k == EV_HUD_END) s = KEG_STG;
    }
    if (r != 0xFF && r != (lcdc & 0x20)) return;             // (not this window state)
    if (!k) { while (LY_REG < tgt) ; HIDE_WIN; return; }     // (the window's end line: wait for it, then the window off)
    if (kk & EV_HIDE_FIRST) { while (LY_REG < tgt) ; HIDE_WIN; }   // (the window ends on this line)
    while (LY_REG < tgt || (STAT_REG & 2)) ;                 // (its line's HBlank, or the VBlank: palette RAM is open; the line's pixels are out)
    split_put_a(b, s);
    if (k == EV_KEG_L) {                                     // (double speed: the keg's put and the late palette's in one HBlank; normal speed: the late one in the next line's)
        BCPS_REG = SPLIT_L_BCPS;                             // (the index may be set at any time: only the data writes wait for an HBlank, so the put below starts the moment it opens)
        if (SPLIT_OFF) { tgt++; while (LY_REG < tgt || (STAT_REG & 2)) ; }
        put8(&BCPD_REG, (const uint8_t *)SPLIT_PAL);
    }
    if (kk & EV_HIDE_AFTER) HIDE_WIN;                        // (the window ends on the next line)
}
#endif

// The VBlank side: the frame's first event is next (EV_I 0, LYC its line; the HUD's BG 1 is back already: the frame's last event, EV_HUD_END), then vq_vbl (its drain must start by
// line VQ_LATEST_LY = 147 or the frame's copy list waits; the VBlank chain starts this handler on line 145 at normal speed, so no cycle may go before it that need not), then the stage
// palettes: they are wanted from line 8, the drain may end on line 153, so each waits for an HBlank or VBlank (split_put_w) rather than assume the VBlank is still there.
#if ASM_SPLIT_PAL
void split_vbl3(void) __naked {   // vq_vbl's place while mode 3 is armed
__asm
    xor  a, a
    ld   (_story_scratch + 270 + 17), a   ; EV_I = 0
    ld   a, (_story_scratch + 369)  ; EV_LINE(0)
    ldh  (0x45), a
    call _vq_vbl
    ld   a, (_story_scratch + 237)  ; the late palette's BCPS (0: none)
    or   a, a
    jr   z, 9200$
    ld   de, #0xFFDE                ; SPLIT_STG
    call _split_put_w
9200$:
    ld   a, (_story_scratch + 236)  ; the early one's
    or   a, a
    ret  z
    ld   de, #_story_scratch + 246  ; SPLIT_E_STG
_split_put_w:
    ld   h, a
9210$:
    ldh  a, (0x41)                  ; STAT: mode 0 or 1 (bit 1 clear): palette RAM is open for the whole write
    and  a, #2
    jr   nz, 9210$
    ld   a, h
    jp   _split_put_a
__endasm;
}
#else
void split_vbl3(void) {       // (the C twin; each put waits for an HBlank or the VBlank, written out here: a wrapper function cost ~100 T-cycles a put, the chain's budget is tight, see put8)
    EV_I = 0;
    LYC_REG = EV_LINE(0);
    vq_vbl();
    if (SPLIT_L_BCPS) { while (STAT_REG & 2) ; BCPS_REG = SPLIT_L_BCPS; put8(&BCPD_REG, (const uint8_t *)SPLIT_STG); }   // (both are BG puts: the HBlank wait, then the index and the 8 bytes; put8 directly, split_put_a is the generic entry the isr uses)
    if (SPLIT_E_BCPS) { while (STAT_REG & 2) ; BCPS_REG = SPLIT_E_BCPS; put8(&BCPD_REG, (const uint8_t *)SPLIT_E_STG); }
}
#endif

void set_lyc(uint8_t x) {
    if (SPLIT_ON) {
        SPLIT_WANT = x;
        if (SPLIT_ON == 3) { if (LCDC_REG & LCDCF_ON) split_plan(); return; }
        if (LYC_REG == SPLIT_LY) return;           // (the Saloon's chain line: the ISR takes SPLIT_WANT up)
    }
    LYC_REG = x;
}


// The credits' cast cards on a DMG (src/credits.c): BGP is one palette for the whole background, but a venue's name stays at the top through the
// fades of its three cards, so the frame is split: lines 0-15 (the header) with the header's BGP, then the card's (story_scratch + 68 / + 69: both
// written by trans.c trans_cast and credits.c). Installed in place of lcd_isr by credits_enter, put back by its end.
void cast_isr(void) {
    if (LYC_REG) { BGP_REG = story_scratch[69]; LYC_REG = 0; }
    else { BGP_REG = story_scratch[68]; LYC_REG = 16; }
}

// Milk Run (src/mr.c) splits the frame: its street scrolls under a HUD row that does not. mr_enter swaps this handler in
// for lcd_isr (mg.c's lcd_normal puts lcd_isr back, so no other screen pays a cycle for it). LYC walks MR_SPLIT_LY (SCX =
// the street's, below the HUD) -> the window's end when one shows -> line 144 (SCX = 0 for the next frame's HUD) ->
// MR_SPLIT_LY; mg.c does not set LYC for Milk Run.
void mr_lcd_isr(void) {
    uint8_t ly;
    HIDE_WIN;                                // (as lcd_isr: the banner window's end)
    if (is_cgb && (KEY1_REG & 0x80)) while ((STAT_REG & 3) > 1) ;   // (Color double speed: the handler reaches its SCX write in half the dots, still inside the split line, so that line scrolled with the street; normal speed writes after the line's pixels (the stub's dispatch is 60+ cycles). Wait for HBlank (or VBlank: line 144) as that lands)
    if ((game_state == GS_MINI || game_state == GS_PAUSED) && mg_id == MG_MILKRUN) {
        ly = LYC_REG;
        if (ly == 144) { SCX_REG = 0; ly = MR_SPLIT_LY; }
        else if (ly == MR_SPLIT_LY) {
            SCX_REG = MG->mr.scx;
            if (overlay_on) {
                SHOW_WIN;                    // (the banner window is wanted from its top line)
                if (game_state == GS_PAUSED && (state_timer & 8)) ly = 144;   // (pause.c's HOW TO PLAY card: the window is the whole screen)
                else if (game_state == GS_PAUSED) ly = BANNER_WY + ((state_timer & 0x80) ? 38 : 46);   // (pause.c WIN_LYC: a mini-game's menu is 5 rows)
                else ly = mg_phase == MG_RESULT ? BANNER_WY + 46 : BANNER_LYC;
            } else ly = 144;
        } else ly = 144;                         // the window's end: hidden above
        LYC_REG = ly;
    }
}

// Milk Run's VBlank handler (added by mr_enter): the next street column, 17 tiles down the map from `dst` and then, on
// CGB, its 17 attributes (they follow the tiles: one loop, twice), from the start of the mini-game state (struct
// mr_state: dst +0, tiles +2, attributes +19). Only early in VBlank (the copy is ~620 cycles).
static void mr_col_copy(void) {
__asm
    push bc
    ldh  a, (0x4F)
    and  a, #1
    ld   c, a               ; the VRAM bank of the interrupted code
    xor  a, a
    ldh  (0x4F), a
    ld   de, #_story_scratch + 2
0$:
    ld   a, (_story_scratch)
    ld   l, a
    ld   a, (_story_scratch + 1)
    ld   h, a
    ld   b, #17
1$:
    ld   a, (de)
    inc  de
    ld   (hl), a
    ld   a, l
    add  a, #32
    ld   l, a
    jr   nc, 2$
    inc  h
2$:
    dec  b
    jr   nz, 1$
    ldh  a, (0x4F)          ; bank bit 0 on CGB: the attributes next (a DMG reads 0xFF and ends; so does bank 1)
    and  a, #1
    jr   nz, 9$
    ld   a, (_is_cgb)
    or   a, a
    jr   z, 9$
    ld   a, #1
    ldh  (0x4F), a
    jr   0$
9$:
    ld   a, c
    ldh  (0x4F), a
    pop  bc
__endasm;
}

void mr_vbl(void) {
    uint8_t ly;
    if (game_state != GS_MINI || mg_id != MG_MILKRUN || !MG->mr.colq) return;
    ly = LY_REG;
    if (ly < 144 || ly > 147) return;            // too late in VBlank: the column waits for the next
    mr_col_copy();
    MG->mr.colq = 0;
}


// ---- game -----------------------------------------------------------------------
// boot_init (src/main_cold.c, banked): hardware, palettes, sprites, the banner window, then the title

uint8_t next_rand(void) {                    // 8-bit xorshift, fixed seed => reproducible runs
    rng_state ^= rng_state << 7;
    rng_state ^= rng_state >> 5;
    rng_state ^= rng_state << 3;
    return rng_state;
}

#define LOOP_FRAMES    120              // the "LOOP n" banner, before the level's intro
#define GAMEOVER_FRAMES 240             // the GAME OVER banner goes on to the initials / table by itself after 4 s
uint8_t arcade_loop = 1;                // pass through the ten venues: 1, 2, ...
// (start_level: src/level.c, declared in game.h)

// ---- screens and state changes --------------------------------------------------------
// glyph_for and the banner window's setup (win_init): src/main_cold.c
// The letters' tiles, in ROM0 so that any bank reads them without a banked call (GLYPH_FAST, game.h: the full-screen menus; glyph_for keeps its own switch).
const uint8_t glyph_az[26] = {
    TILE_GLYPH_A, TILE_GLYPH_B, TILE_GLYPH_C, TILE_GLYPH_D, TILE_GLYPH_E, TILE_GLYPH_F, TILE_GLYPH_G, TILE_GLYPH_H, TILE_GLYPH_I,
    TILE_GLYPH_J, TILE_GLYPH_K, TILE_GLYPH_L, TILE_GLYPH_M, TILE_GLYPH_N, TILE_GLYPH_O, TILE_GLYPH_P, TILE_GLYPH_Q, TILE_GLYPH_R,
    TILE_GLYPH_S, TILE_GLYPH_T, TILE_GLYPH_U, TILE_GLYPH_V, TILE_GLYPH_W, TILE_GLYPH_X, TILE_GLYPH_Y, TILE_GLYPH_Z };

static void hide_banner_sprites(void) {      // 8x16 sprites that would overlap the banner lines
    uint8_t i;
    for (i = 0; i < 40; i++)
        if (shadow_OAM[i].y > BANNER_WY && shadow_OAM[i].y < BANNER_WY + 40) { shadow_OAM[i].y = 0; oam_touched(); }
}

// A line of text centred in HUD glyphs on map row `row` (32.. = the window's): through the VBlank queue, or straight to
// VRAM while the LCD is off. In ROM0 because the strings live in the callers' own banks (bonus.c, bonus2.c, the
// mini-games): a ROM0 callee keeps the caller's bank mapped. Each call takes the next of SAY_BUFS row buffers, so at most
// SAY_BUFS lines a frame; it returns the row's tiles (the caller may patch them before the VBlank: an icon).
#define SAY_BUFS 4
static uint8_t say_buf[SAY_BUFS * 20], say_k;
uint8_t *mg_say(uint8_t row, const char *s) {
    uint8_t *b = say_buf + say_k, *p = b, n = 20;
    const char *e = s;
    say_k += 20; if (say_k == SAY_BUFS * 20) say_k = 0;
    do *p++ = TILE_HUD_BLANK; while (--n);
    while (*e) e++;
    p = b + ((uint8_t)(20 - (uint8_t)(e - s)) >> 1);
    while (*s) *p++ = glyph_for(*s++);
    if (LCDC_REG & LCDCF_ON) vq_add(0, b, 0, row, 20); else vram_put(0, row, b, 20);
    return b;
}

// A note (overlay_on 2) is a one-row window on the stage wall (y 24..30): its text in window map row 32 (the banner's top
// frame, put back by end_note), WY and LYC moved to it. Nothing plays there, so a message can show while the game runs.
void show_note(const char *s) {
    mg_say(32, s);
    SET_WY(NOTE_WY); SET_LYC(NOTE_LYC);
    overlay_on = 2;
}


void show_overlay(const char *s) {
    end_note();
    mg_say(33, s);
    overlay_on = 1;
    hide_banner_sprites();
}

// reset_actors, enter_level_screen, start_new_game: src/main_cold.c

// The debug menu: src/debug.c (opened by the gesture debug_gesture, called from update below).

uint8_t new_rank = TOP_N;   // M10b: the game's place in the top 5 (TOP_N: none)
// resume_after_life, enter_game_over, enter_level_clear: src/main_cold.c

// One walking step: 1.5 px per frame as 1 px plus a 1/256 px fraction.
static uint8_t walk_px(void) {
    uint8_t f = bartender_frac;
    bartender_frac = f + WALK_FRAC;
    return bartender_frac < f ? WALK_PX + 1 : WALK_PX;
}

static const uint8_t walk_cycle[4] = { BT_WALK1, BT_IDLE, BT_WALK2, BT_IDLE };

static void play_frame(uint8_t pressed) {
    uint8_t walked = 0, switched, carry, x, d, t;

    // A full mug still held (A down) is carried along to another bar instead of being cancelled.
    carry = fill_timer >= FILL_FRAMES && (joy & J_A);
    // Up/Down: change bar (wrapping) and snap to that bar's fill position, facing the bar
    switched = pressed & (J_UP | J_DOWN);
    if (pressed & J_UP)        bar = bar == 0 ? NUM_BARS - 1 : bar - 1;
    else if (pressed & J_DOWN) bar = bar == NUM_BARS - 1 ? 0 : bar + 1;
    tap_now = t = bar_tap[bar];                  // the bar's fill position (P6: a slanted bar's is further in)
    if (switched) bar_change(pressed);               // where he lands: src/pour.c (mode A keeps his x; mode B snaps to the tap, dust and swish)

    // Left/Right: walk (1.5 px per frame). On an R bar (CLASSIC, render.c bar_dirs) they swap: the tap is on the left.
    x = bartender_x;
    d = joy;
    if ((bar_dirs & bar_bit[bar]) && ((uint8_t)((d & (J_LEFT | J_RIGHT)) + 1) & 2)) d ^= J_LEFT | J_RIGHT;
    if (d & J_LEFT) {
        facing = 0;
        if (x > LEFT_LIMIT) { d = walk_px(); x = x - d < LEFT_LIMIT ? LEFT_LIMIT : x - d; }
    } else if (d & J_RIGHT) {
        facing = 1;
        if (x < t) { d = walk_px(); x = x + d > t ? t : x + d; }
    }
    if (x != bartender_x) { bartender_x = x; walked = 1; }
    else bartender_frac = 0;                     // standing (or against a wall): the next walk starts afresh
    // A pressed close enough to the fill position: snap to it (a fresh press only)
    if ((pressed & J_A) && !fill_timer && bartender_x >= (uint8_t)(t - TAP_GRACE) && bartender_x < t) {
        bartender_x = t; bartender_frac = 0;
    }
    at_tap = bartender_x == t;

    // Filling: A pressed at the fill position starts it; walking, a bar change (unless carrying a full mug)
    // or letting go ends it, and letting go after FILL_FRAMES launches a mug on the bar he is at.
    if (fill_timer) {
        if (switched && carry && !walked && at_tap) {
            // carried to the new bar's fill position: still holding the full mug under the spout
        } else if (walked || switched || !at_tap || !(joy & J_A)) {
            if (!walked && !switched && at_tap && fill_timer >= FILL_FRAMES) {
                launch_mug();
                slide_timer = SLIDE_FRAMES;
            }
            fill_timer = 0;
            if (!walked) facing = 0;             // turns back to the bar (and slides the mug that way)
        } else if (fill_timer < FILL_FRAMES) {
            fill_timer++;
        }
        fill_stage = fill_timer >= FILL_FRAMES ? 3 : fill_timer >= 2 * FILL_FRAMES / 3 ? 2
                   : fill_timer >= FILL_FRAMES / 3 ? 1 : 0;
    } else if (at_tap && (pressed & J_A)) {
        fill_timer = 1; fill_stage = 0;
        SFX(SFX_FILL);
    }
    if (!fill_timer) fill_stage = 0;
    else facing = 1;                             // filling: faces the tap, the mug under the spout

    if (slide_timer) slide_timer--;
    if (catch_pose) catch_pose--;

    bt_bob = 0;
    if (fill_timer) {
        bartender_frame = BT_FILL;
        walk_timer = 0; walk_phase = 0;
    } else if (catch_pose) {
        bartender_frame = BT_CATCH;
    } else if (walked) {                         // walk1, idle, walk2, idle, WALK_STEP_FRAMES each
        bartender_frame = walk_cycle[walk_phase];
        bt_bob = !switched & walk_phase;         // up on the passing (idle) pose, down on the contact poses
        if (++walk_timer >= WALK_STEP_FRAMES) { walk_timer = 0; walk_phase = (walk_phase + 1) & 3; }
    } else {
        bartender_frame = slide_timer ? BT_SLIDE : BT_IDLE;
        walk_timer = 0; walk_phase = 0;
    }

    // tip: counts down, and is picked up by standing on it (16 px span overlapping its 8 px)
    if (tip_timer) {
        if (tip_pocket && TIP2->t) tip_step();   // two coins (ARCADE, STORY): src/tip.c counts both down, one pick-up a frame
        else {
            tip_timer--;
            if (tip_timer && bar == tip_bar && bartender_x < (uint8_t)(tip_x + 8) && (uint8_t)(bartender_x + 16) > tip_x) {
                tip_timer = 0;
                add_score(TIP_SCORE);
                SFX(SFX_COIN);
                start_show();
            }
        }
    }
    if (show_timer) {
        if (++dance_tick >= DANCER_BEAT) { dance_tick = 0; dance_next(); }
        if (--show_timer == 0) end_show();
    }

    SEC(SEC_INPUT);
    update_mugs();
    SEC(SEC_MUGS);
    update_patrons();
    SEC(SEC_PATRONS);
}


static void update(void) {
    uint8_t pressed, t;

    vq_frame_begin();                // the VBlank interrupt has drained last frame's copy list (or it waits)
#ifdef GLOW_A
    glow_tick();                     // (src/glow.c, make GLOW=A: the bistro's palette pulse; VBlank, first thing)
#endif
    if (lists_dirty) { lists_dirty = 0; lists_ok = 0; }   // a test poked patron_state / patron_bar: rebuild the bar lists
    SEC(SEC_FLUSH);
    if (overlay_on) SHOW_WIN;
    else {
        HIDE_WIN;
        if (WY_REG == NOTE_WY) { SET_WY(BANNER_WY); SET_LYC(BANNER_LYC); }   // (a note cut off by a life lost or a scene change: overlay_on 0 without end_note; the next window would start on the note's line)
    }

    joy_prev = joy;
    joy = joypad();
#ifdef AUTO_TRANS                       // test-only ROM (tests/test_fade_hw.py, never in a release): A tapped every 16 frames walks title -> STORY -> NORMAL -> the scenes
    joy = 0;                                     // (AUTO_TRANS 1: STORY / NORMAL, 2: ARCADE; the frames count from boot, the menu is up from about 90)
    if (game_state == GS_TITLE && frame_counter >= 96 && (frame_counter & 15) < 2) joy = (AUTO_TRANS == 2 && (frame_counter & 0x10)) ? J_DOWN : J_A;
#endif
#ifdef AUTO_NOTE                        // test-only (the hook is in src/debug.c)
    joy |= auto_note();
#endif
#ifdef AUTO_BOSS                       // test-only (tests/test_fade_hw.py): the hook is in src/debug.c
    joy = auto_boss();
#endif
#ifdef AUTO_MR                         // test-only (tests/test_double_speed.py): the hook is in src/debug.c
    joy = auto_mr();
#endif
#ifdef AUTO_MG                         // test-only (tools/mg_capture.py): the hook is in src/debug.c
    joy = auto_mg();
#endif
#ifdef AUTO_CARD                       // test-only (tests/test_fade_hw.py, never in a release): the hook is in src/debug.c (a banked file: ROM0 has no room)
    joy = auto_card();
#endif
    pressed = joy & ~joy_prev;
    if (joy & J_SELECT) pressed = debug_gesture(pressed);   // SELECT + three START taps: the debug menu (src/debug.c; before the state switch: it may change the state)

    switch (game_state) {
    case GS_TITLE:
        if (title_update(pressed) == 2) scores_table();   // the menu (title.c; it starts the games); 2: idle, the top 5
        frame_counter++;
        return;
    case GS_PLAYING:
        if (pressed & (J_START | J_B) && pause_or_pocket(pressed)) break;   // START: the pause menu (src/pause.c); B: a show from the pocketed tip (src/pocket.c)
        play_frame(pressed);
        if (story_on) story_play();              // M11b: the chapter goal
        // 30 fps (DMG, src/half.c): every second VBlank is a logic-only step, the next one is the same plus the picture (the dirty marks,
        // the HUD flags and the chooser's dirty bits just accumulate until then). A step that ends the level or a life, or opens a fight,
        // is drawn at once.
        if (!(frame_counter & 1) && (HALF & HALF_ON) && game_state == GS_PLAYING && !(life_lost | level_clear | boss_on)) {
            if (sa_on > sa_hold && !--sa_timer) stage_anim_step();   // (the frame's other work that is not drawing, as below)
            half_step();
            frame_counter++;
            return;
        }
        break;
    case GS_PAUSED:
        if (pause_update(pressed)) return;       // RESUME / QUIT TO MENU (src/pause.c); 1: the run is over
        break;
    case GS_MINI:                                // a mini-game (src/mg.c); 1: it left, the next screen is up
        if (mg_update(pressed)) return;
        break;
    case GS_BONUS:                               // (these four stay: their frames are long or tick-sensitive, a banked call more shows in the music-tick and bonus-judge tests)
        if (bonus_update(pressed)) {
            if (story_on) { arcade_next(); return; }  // ARCADE: the bonus round after a venue, then the next venue
            if (level < 99) level++;
            enter_level_screen();
            return;
        }
        break;
    case GS_STORY:                               // M11b: a cut-scene / TRY AGAIN, the goal banner
    case GS_GOAL:
        if (story_update(pressed)) return;
        break;
    case GS_JUKEBOX:                             // the title's BONUS: the soundtrack player (src/jukebox.c)
        if (jukebox_update(pressed)) return;
        break;
    case GS_MGLIST:                              // BONUS > MINI GAMES: the list (src/mg_list.c)
        if (mg_list_update(pressed)) return;
        break;
    default:                                    // the other screens (life lost, level clear, bonus, debug, game over, scores, story, jukebox, list, loop): src/main_cold.c, banked (ROM0 relief)
        t = update_cold(pressed);
        if (t) { if (t == 2) frame_counter++; return; }
        break;
    }

    SEC(SEC_REST);
    if ((lift_total | lift_hook_op | ovl_dirty) && (game_state == GS_PLAYING || game_state == GS_LIFE_LOST)) lift_frame();   // M13a/b
    SEC(SEC_LIFT);
    // stage animation: on the level screen (sa_on), not frozen by a test (sa_hold), not while paused
    if (sa_on > sa_hold && game_state != GS_PAUSED && !--sa_timer) stage_anim_step();
    SEC(SEC_ANIM);
    if (vram_pending | hud_dirty | sa_left) queue_vram();
    SEC(SEC_QUEUE);
    if (game_state == GS_PLAYING || game_state == GS_LIFE_LOST) {
        // M13c: no OAM DMA while the sprites are being redrawn. A frame whose logic runs past the start of VBlank would
        // otherwise show a half-drawn OAM for a frame (the realistic-peak perf test caught 11 objects on a line: new mugs
        // already written, a dropped patron's entries not yet taken away); it shows the last complete one instead.
        DISABLE_OAM_DMA;
        draw_bartender();
        draw_fill();
        SEC(SEC_DRAW_BT);
        draw_mugs();
        SEC(SEC_DRAW_MUGS);
        if (lift_total | lift_oam_n) draw_lifted();
        SEC(SEC_DLIFT);
        draw_stage_fx();
        if (bar_dirs) mirror_oam();              // P3: bars from the right: their entries to the mirrored place (mirror.c)
        if (story_on | cue_t) pour_frame();     // story: the perfect pour (src/pour.c; last: it counts OAM lines); else the dust puff (OAM 26)
        ENABLE_OAM_DMA;
        SEC(SEC_FX);
    }
    if (game_state == GS_PLAYING) {              // reactions to what this frame did
        if (life_lost) {
            life_lost = 0;
            state_timer = 0;
            game_state = GS_LIFE_LOST;
            SFX(SFX_LIFE);
        } else if (level_clear) {
            enter_level_clear();
        }
    }
    if (overlay_on == 1) hide_banner_sprites();   // (a note is not over the bars)
    frame_counter++;
    SEC(SEC_REST);
}

// Frame-time instrumentation (tests/test_perf.py reads it; it costs ~1.2 lines a frame, so only the test / playtest builds have it:
// DEBUG_MENU, the Makefile's default, and PERF_SECTIONS; `make release` leaves it out). "End LY" is the LY register
// when the frame's work ended: 0..143 normally (a frame that finishes inside the VBlank it started in reads 0).
// A frame that ran past the next VBlank reads 144 + the lines since that VBlank began (+154 per extra one).
// During the frame only (sys_time, LY) snapshots are taken; the arithmetic happens after the music tick.
uint8_t  frame_t0;          // (uint8_t)sys_time when this frame began (lift.c: has the frame run into the next one?)
#if defined(DEBUG_MENU) || defined(PERF_SECTIONS)
#define FRAME_STATS 1
uint16_t perf_logic_max;    // highest end LY of update() so far
uint16_t perf_end_max;      // ... of update() + music tick
uint16_t perf_logic_last, perf_end_last;     // this frame's
uint16_t missed_frames;     // frames that began outside VBlank (the previous one overran) or were skipped
uint8_t  frame_ly_max;      // latest LY a frame's logic started on (after the VBlank interrupt and its drain)
static uint8_t perf_last_t, perf_prev_playing;
static uint8_t snap_t, snap_ly;

#if ASM_F
// Hand-written (asm pass batch 1, src/asm_cfg.h ASM_F; the C versions are below under #else and are the reference).
static void perf_snap(void) __naked {
__asm
1$:
    ld   a, (_sys_time)
    ld   (_snap_t), a
    ldh  a, (0x44)          ; LY
    ld   (_snap_ly), a
    ld   a, (_sys_time)     ; a VBlank between the reads would skew it: again
    ld   hl, #_snap_t
    cp   a, (hl)
    jr   nz, 1$
    ret
__endasm;
}

// perf_ly(t0 = A, t = E, ly = on the stack, popped here) -> BC: dt = t - t0; dt 0: ly >= 144 ? 0 : ly;
// else 144 + (dt - 1) * 154 + (ly >= 144 ? ly - 144 : ly + 10). The multiply is an add loop: dt is nearly always 1 or 2.
static uint16_t perf_ly(uint8_t t0, uint8_t t, uint8_t ly) __naked {
    (void)t0; (void)t; (void)ly;
__asm
    ld   c, a               ; t0
    ld   a, e
    sub  a, c               ; dt
    ld   c, a
    ldhl sp, #2
    ld   e, (hl)            ; ly
    or   a, a
    jr   nz, 2$
    ld   a, e               ; dt 0
    cp   a, #144
    jr   c, 1$
    xor  a, a
1$:
    ld   c, a
    ld   b, #0
    jr   9$
2$:
    ld   a, e
    cp   a, #144
    jr   c, 3$
    sub  a, #144
    jr   4$
3$:
    add  a, #10
4$:
    ld   e, a
    ld   d, #0
    ld   hl, #144
    add  hl, de             ; 144 + the last-line part
    dec  c                  ; dt - 1 lots of 154
    jr   z, 6$
    ld   de, #154
5$:
    add  hl, de
    dec  c
    jr   nz, 5$
6$:
    ld   b, h
    ld   c, l
9$:
    pop  hl                 ; the return address; the caller's one stack byte goes with it
    inc  sp
    jp   (hl)
__endasm;
}
#else
static void perf_snap(void) {
    do { snap_t = (uint8_t)sys_time; snap_ly = LY_REG; } while (snap_t != (uint8_t)sys_time);   // (a VBlank between the reads would skew it)
}

static uint16_t perf_ly(uint8_t t0, uint8_t t, uint8_t ly) {
    uint8_t dt = t - t0;
    if (dt == 0) return ly >= 144 ? 0 : ly;
    return 144 + (uint16_t)(dt - 1) * 154 + (ly >= 144 ? ly - 144 : ly + 10);
}
#endif

#endif   // FRAME_STATS

#ifndef DS_TICK_LY
#define DS_TICK_LY 60                  // Color double speed: the line the loop's music tick waits for (a tick is up to 18 lines: MUSIC_LATEST_LY 120)
#endif

// Wait for the next VBlank (GBDK's vsync() without its race). vsync() clears the "VBlank done" flag and then halts: a
// VBlank interrupt that lands between the two sets the flag before the halt, and the CPU then sleeps until the next
// interrupt, the banner's LYC at line 86 or a whole frame later (M13b: the worst-case pile's 218/223 end LY was a frame
// that ended at line 143 and slept until line 87). Here the flag is checked with interrupts off, and the halt (IME 0)
// wakes on any pending interrupt, which is then taken after the ei.
void frame_wait(void) __naked {   // (not static: src/half.c half_wait calls it)
__asm
    ldh  a, (0x40)          ; LCD off: nothing to wait for (as vsync)
    and  a, #0x80
    ret  z
    xor  a, a
    ld   (__vbl_done), a
1$:
    di
    ld   a, (__vbl_done)
    or   a, a
    jr   nz, 2$
    ldh  a, (0x0F)          ; the music timer wrapped (IF bit 2; double speed only, nothing takes it): the tick just made zeroed TIMA, the flag is stale (music.c music_pump)
    bit  2, a
    jr   z, 3$
    and  a, #0xFB
    ldh  (0x0F), a          ; (interrupts are off: none is taken between the read and this write; a flag the hardware sets in those 3 cycles would be lost, on the rare frame that has a stale timer flag)
3$:
    halt
    nop                     ; (if an interrupt was already pending, the halt bug only repeats this nop)
    ei
    jr   1$                 ; the pending interrupt is taken after this instruction
2$:
    ei
    ret
__endasm;
}

void main(void) {
#ifdef FRAME_STATS
    uint8_t t0, ly0, st0, lt, lly, d, ok;
#endif
    PAUSE_NR51 = 0;      // (HRAM is not cleared at power-on: left non-zero, music_tick played every tune as the pause mix)
    boot_init();
#ifdef FRAME_STATS
    perf_last_t = (uint8_t)sys_time;
#endif
    while (1) {
        if (HALF & (HALF_ON | HALF_OWED)) half_wait(); else frame_wait();   // (30 fps: src/half.c)
#ifdef FRAME_STATS
        frame_t0 = t0 = (uint8_t)sys_time; ly0 = LY_REG; st0 = game_state;
#else
        frame_t0 = (uint8_t)sys_time;
#endif
        SEC_BEGIN();
        update();
        vq_frame_end();      // the copy list is complete: the next VBlank interrupt executes it
#ifdef FRAME_STATS
        perf_snap(); lt = snap_t; lly = snap_ly;
#endif
        // Music and effects, every frame, after the logic (so they cannot delay the game's input-to-state latency).
        if (is_cgb && (KEY1_REG & 0x80) && (LCDC_REG & LCDCF_ON)) while (LY_REG < DS_TICK_LY) ;   // (double speed: a frame's logic ends by line 20-60, a heavy pass's much later: the ticks would bunch up to 0.7 frame apart. The tick waits for a fixed line, as the credits' and the fades' do: the spare time is idle anyway)
        if (game_state != GS_PAUSED || !PAUSE_NR51 || NR51_REG) music_tick();   // (the pause menu: the bass and drums play on; NR51 0: a tune the game is clocked by stands still, pause.c)
        SEC(SEC_MUSIC);
        if (show_timer && is_cgb && game_state == GS_PLAYING && (!((uint8_t)show_timer & 7) || !SHOWLT_STAMP || SHOWLT_STAMP > 4) && LY_REG < LT_LY_MAX) lights_frame();   // (the show's stage wash, src/lights.c: after the tick, in the time a double-speed frame leaves idle; most frames need nothing)
#ifdef FRAME_STATS
        perf_snap();
#endif
#ifdef PERF_SECTIONS
        for (d = 0; d < SEC_N; d++) sec_done[d] = sec_frame[d];
        sec_done_id = frame_counter;
#endif
#ifdef FRAME_STATS
        d = t0 - perf_last_t;
        perf_last_t = t0;
        ok = perf_prev_playing && st0 == GS_PLAYING;            // transitions turn the LCD off: not a normal frame
        perf_prev_playing = st0 == GS_PLAYING;
        perf_logic_last = perf_ly(t0, lt, lly);
        perf_end_last = perf_ly(t0, snap_t, snap_ly);
        if (perf_logic_last >= 144) music_late++;               // the tick began only after the next VBlank had begun
        if (!ok) continue;
        if ((ly0 < 144 && !(HALF & HALF_ON)) || d != 1) missed_frames++;   // (30 fps: a step that starts at once after one that ran past a VBlank is on time, src/half.c half_wait; only a VBlank nobody started a step in is missed)
        if (ly0 > frame_ly_max) frame_ly_max = ly0;
        if (perf_logic_last > perf_logic_max) perf_logic_max = perf_logic_last;
        if (perf_end_last > perf_end_max) perf_end_max = perf_end_last;
#endif
    }
}
