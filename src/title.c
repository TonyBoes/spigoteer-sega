// Title screen (M10a): the SPIGOTEER logo fills with beer letter by letter (bottom-up, a frothy head, drips),
// then sparkles once; a menu ARCADE / STORY / MUSIC ON-OFF with a mug cursor and the HI score, every line
// centred to the pixel (tools/gen_art.py pre-renders the text: an odd-length line sits 4 px right inside one more
// tile); below it a looping bar scene on the bottom counter: the bartender slides a mug to a patron, who drinks
// and sends the empty back. Foam bubbles drift up past the logo now and then.
//
// LCD off to enter. Afterwards every tilemap change goes through the VBlank queue (vq_add) from WRAM buffers.
// BG ids (title only; the level load restores them): menu text over the venue's stage slot (0..19: no stage on
// the title) and after the logo fill states; the lettering, its fill states and the scene's patron over the
// patron range (72..227). OBJ: the effects over the show performers' tiles (OBJ_DANCER, reloaded by load_venue);
// the bartender (permanent) and the saloon's drink frames (load_venue(0)).
// OAM: bartender 0-3, scene mug 4, cursor 5, sparkle 6, drip 7, bubbles 8-9. Per scanline at most 4 (scene 3).
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"
#include "palettes.h"
#include "music.h"
#include "title_art.h"      // this bank's own art data (static const)

extern uint8_t overlay_on, hi_digits[6];
extern const uint8_t bar_tiles[];
BANKREF_EXTERN(art_tiles)
BANKREF_EXTERN(patron_tiles_cowboys)
extern const uint8_t patron_tiles_cowboys[];
void bkg_data_far(uint8_t first, uint8_t n, const uint8_t *d, uint8_t bank);

#define WALL_RGB_T (venue.pal[VENUE_PAL_BAR][0])   // the saloon's wall: colour 0 of every title BG palette
#define RGB15(r, g, b) ((uint16_t)((r) | ((g) << 5) | ((b) << 10)))

// ---- layout ----
#define LOGO_ROW        2       // the logo: rows 2-3, columns 1..18
#define ROW_ARCADE      6
#define ROW_STORY       8
#define ROW_MUSIC      10
#define ROW_HI         12
#define SCENE_BAR       3       // the scene stands on bar 3's rows (14-15 wall, 16 counter): draw_bartender() places him
#define SCENE_TOP_Y   (BAR_TOP_Y(SCENE_BAR) + 16)   // OAM y of the scene's wall top
#define PATRON_COL      3       // the patron: BG tiles at columns 3-4 of rows 14-15 (x 24..39)
#define PATRON_PX      24
#define CATCH_X        40       // a full mug's left edge here: the patron catches it
#define BT_X          124       // the bartender's x
#define LAUNCH_X      116       // where his mug starts (and the empty comes back to)
#define BGPAL_LOGO      BGPAL_PATRON       // 2
#define BGPAL_TEXT      3
#define BGPAL_TEXT_SEL  4
#define BGPAL_TPATRON   BGPAL_STAGE        // 5 (no stage on the title)
#define OBJPAL_FX       6
#define OBJ_FX          OBJ_DANCER
#define FX_BUBBLE       (OBJ_FX + 0)       // small, big
#define FX_SPARKLE      (OBJ_FX + 4)       // small, big
#define FX_DRIP         (OBJ_FX + 8)       // forming, falling
#define OAM_TMUG        4
#define OAM_CURSOR      5
#define OAM_SPARKLE     6
#define OAM_DRIP        7
#define OAM_BUBBLE      8

// ---- logo timing (frames since the title appeared) ----
#define LOGO_T0         6       // first letter starts filling
#define LOGO_STAGGER    8       // next letter this much later
#define LOGO_STEP       4       // frames per fill state
#define LOGO_LETTERS    9
#define LOGO_FILLED   (LOGO_T0 + (LOGO_LETTERS - 1) * LOGO_STAGGER + (TT_LOGO_STATES - 1) * LOGO_STEP)
#define SPARKLE_T0    (LOGO_FILLED + 6)
#define SPARKLE_EACH    6       // frames on each letter
#define LOGO_DONE_T   (SPARKLE_T0 + LOGO_LETTERS * SPARKLE_EACH)
#define DRIP_LEN       22
#define MSG_FRAMES     60       // "COMING SOON"
#define TITLE_IDLE_FRAMES 1200  // 20 s

enum { SC_IDLE, SC_SLIDE, SC_DRINK, SC_WINDUP, SC_RETURN, SC_CATCH };
#define SC_IDLE_FRAMES   40
#define SC_SLIDE_POSE     8
#define SC_DRINK_FRAMES  96
#define SC_WINDUP_FRAMES 24
#define SC_CATCH_FRAMES  14

// ---- state (globals => symbols the tests read) ----
uint16_t title_t;               // frames since the title appeared
uint8_t  title_sel;             // 0 ARCADE, 1 STORY, 2 MUSIC
uint8_t  title_msg;             // frames left of "COMING SOON" (0: the menu)
uint16_t title_idle;            // M10b: frames without a key; at TITLE_IDLE_FRAMES the top-5 table shows (scores.c)
uint8_t  logo_state[LOGO_LETTERS];   // fill state per letter: 0 empty .. TT_LOGO_STATES-1 the final art
uint8_t  logo_done;             // filled and sparkled
uint8_t  tscene_phase, tscene_timer, tscene_mug_x, tscene_loops;
uint8_t  bubble_y[2], bubble_x[2], bubble_timer;   // bubble_y 0: free (else screen y + 16, in 1/2 px: see below)
static uint8_t bubble_half;
static uint8_t t_rng = 0x5D;    // the title's own random numbers (the game's sequence must not depend on the title)

static uint8_t logo_buf[LOGO_LETTERS][4];
static uint8_t row_story[20], row_music[20], attr_txt[20], attr_sel[20];

static uint8_t trand(void) {
    t_rng ^= t_rng << 7;
    t_rng ^= t_rng >> 5;
    t_rng ^= t_rng << 3;
    return t_rng;
}

// a 20-wide row: blank, then the string (column, count, ids) at its column
static void build_row(uint8_t *row, const uint8_t *s) {
    uint8_t i;
    for (i = 0; i < 20; i++) row[i] = TT_BLANK;
    for (i = 0; i < s[1]; i++) row[s[0] + i] = s[2 + i];
}

static void build_music(void) { build_row(row_music, sound_on ? tt_music_on : tt_music_off); }

static const uint8_t sel_row[3] = { ROW_ARCADE, ROW_STORY, ROW_MUSIC };

static uint8_t text_left(uint8_t i) {           // screen x of the first text pixel of menu item i
    return i == 0 ? TT_X_ARCADE : i == 1 ? TT_X_STORY : sound_on ? TT_X_MUSIC_ON : TT_X_MUSIC_OFF;
}

static void set_sel_attr(uint8_t sel, uint8_t on) {
    if (is_cgb) vq_add(1, on ? attr_sel : attr_txt, 0, sel_row[sel], 20);
}

void title_music_toggle(void) BANKED {
    music_set_on(!sound_on);
    build_music();
    vq_add(0, row_music, 0, ROW_MUSIC, 20);
}

static void logo_put(uint8_t i) {               // letter i's current state into its buffer (LCD off: straight to VRAM)
    const uint8_t *q = tt_logo[tt_word[i]][logo_state[i]];
    logo_buf[i][0] = q[0]; logo_buf[i][1] = q[1]; logo_buf[i][2] = q[2]; logo_buf[i][3] = q[3];
}

void title_enter(void) BANKED {
    uint8_t i, r;
    palette_t p;
    DISPLAY_OFF;
    overlay_on = 0; HIDE_WIN; vq_reset(); hud_dirty = 0;
    hide_all_sprites();
    bkg_data_far(TILE_GENERIC_BASE, GENERIC_TILE_COUNT, bar_tiles, BANK(art_tiles));
    load_venue(0);                                    // the title stands in the saloon (and its drink frames)
    set_bkg_data(BAR_TILE_COUNT, TITLE_TILE_COUNT, title_tiles);   // lettering over the patron ids; the level load puts them back
    set_bkg_data(TT_EXTRA_BASE, TT_EXTRA_COUNT, tt_extra_tiles);
    set_bkg_data(0, TT_LOW_COUNT, tt_low_tiles);
    for (r = 0; r < 2; r++)                           // the patron: cowboys variant 0, unshifted, 2x2 of its 3x2 tiles
        for (i = 0; i < 2; i++)
            bkg_data_far(TT_PATRON_BASE + r * 2 + i, 1, patron_tiles_cowboys + (r * 3 + i) * 16, BANK(patron_tiles_cowboys));
    set_sprite_data(OBJ_FX, TT_FX_TILES, tt_fx_tiles);
    if (is_cgb) {
        p[0] = WALL_RGB_T; p[1] = RGB15(31, 30, 24); p[2] = RGB15(29, 19, 4); p[3] = RGB15(10, 3, 2);   // logo: foam, beer, outline
        set_bkg_palette(BGPAL_LOGO, 1, p);
        p[1] = RGB15(2, 3, 8); p[2] = RGB15(22, 19, 12); p[3] = RGB15(31, 29, 22);   // text: shadow, muted (HI), cream
        set_bkg_palette(BGPAL_TEXT, 1, p);
        p[3] = RGB15(31, 25, 6);                                                     // the selected item: gold
        set_bkg_palette(BGPAL_TEXT_SEL, 1, p);
        for (i = 1; i < 4; i++) p[i] = palettes[patron_pal_ids[0][0]][i];
        set_bkg_palette(BGPAL_TPATRON, 1, p);
        p[1] = RGB15(31, 31, 27); p[2] = RGB15(30, 20, 4); p[3] = RGB15(12, 5, 2);  // effects: foam, beer, dark
        set_sprite_palette(OBJPAL_FX, 1, p);
    }
    venue_backdrop(0, 16);                            // wall rows 0-15, counter row 16, floor 17 (tiles + attributes)

    // logo: every letter empty
    for (i = 0; i < LOGO_LETTERS; i++) {
        logo_state[i] = 0;
        logo_put(i);
        set_bkg_tiles(1 + 2 * i, LOGO_ROW, 2, 1, logo_buf[i]);
        set_bkg_tiles(1 + 2 * i, LOGO_ROW + 1, 2, 1, logo_buf[i] + 2);
    }
    // the menu block, rows 4-13: plain wall (the text's blank tile is colour 0, the wall colour; no specks), text centred
    for (i = 0; i < 20; i++) row_buf[i] = TT_BLANK;
    for (r = LOGO_ROW + 2; r < BAR_TOP_ROW(SCENE_BAR); r++) set_bkg_tiles(0, r, 20, 1, row_buf);
    for (i = 0; i < 20; i++) { attr_txt[i] = BGPAL_TEXT; attr_sel[i] = BGPAL_TEXT_SEL; }
    title_sel = 0; title_msg = 0;
    build_row(row_story, tt_arcade); set_bkg_tiles(0, ROW_ARCADE, 20, 1, row_story);
    build_row(row_story, tt_story);  set_bkg_tiles(0, ROW_STORY, 20, 1, row_story);
    build_music();                   set_bkg_tiles(0, ROW_MUSIC, 20, 1, row_music);
    for (i = 0; i < 20; i++) row_buf[i] = TT_BLANK;
    row_buf[6] = TT_HI;
    for (i = 0; i < 6; i++) row_buf[8 + i] = tt_digit[hi_digits[i]];
    set_bkg_tiles(0, ROW_HI, 20, 1, row_buf);
    // the scene's patron
    row_buf[0] = TT_PATRON_BASE; row_buf[1] = TT_PATRON_BASE + 1; row_buf[2] = TT_PATRON_BASE + 2; row_buf[3] = TT_PATRON_BASE + 3;
    set_bkg_tiles(PATRON_COL, BAR_TOP_ROW(SCENE_BAR), 2, 1, row_buf);
    set_bkg_tiles(PATRON_COL, BAR_TOP_ROW(SCENE_BAR) + 1, 2, 1, row_buf + 2);
    if (is_cgb) {
        VBK_REG = VBK_BANK_1;
        for (i = 0; i < 20; i++) row_buf[i] = BGPAL_LOGO;
        set_bkg_tiles(1, LOGO_ROW, 18, 1, row_buf); set_bkg_tiles(1, LOGO_ROW + 1, 18, 1, row_buf);
        set_bkg_tiles(0, ROW_ARCADE, 20, 1, attr_sel);
        set_bkg_tiles(0, ROW_STORY, 20, 1, attr_txt);
        set_bkg_tiles(0, ROW_MUSIC, 20, 1, attr_txt);
        set_bkg_tiles(0, ROW_HI, 20, 1, attr_txt);
        for (i = 0; i < 2; i++) row_buf[i] = BGPAL_TPATRON;
        set_bkg_tiles(PATRON_COL, BAR_TOP_ROW(SCENE_BAR), 2, 1, row_buf);
        set_bkg_tiles(PATRON_COL, BAR_TOP_ROW(SCENE_BAR) + 1, 2, 1, row_buf);
        VBK_REG = VBK_BANK_0;
    }
    title_t = 0; logo_done = 0; title_idle = 0;
    tscene_phase = SC_IDLE; tscene_timer = 0; tscene_mug_x = 0; tscene_loops = 0;
    bubble_y[0] = bubble_y[1] = 0; bubble_timer = 90;
    bar = SCENE_BAR; bartender_x = BT_X; bt_bob = 0; facing = 0; bartender_frame = BT_IDLE;
    game_state = GS_TITLE;
    music_play(TUNE_TITLE);
    DISPLAY_ON;
}

// ---- the logo -------------------------------------------------------------------------------
static void logo_frame(void) {
    uint8_t i, s;
    int16_t d;
    OAM_item_t *o;
    if (logo_done) return;
    for (i = 0; i < LOGO_LETTERS; i++) {
        d = (int16_t)title_t - LOGO_T0 - i * LOGO_STAGGER;
        if (d < 0) break;
        s = d >= (TT_LOGO_STATES - 1) * LOGO_STEP ? TT_LOGO_STATES - 1 : (uint8_t)d / LOGO_STEP;
        if (s != logo_state[i]) {
            logo_state[i] = s;
            logo_put(i);
            vq_add(0, logo_buf[i], 1 + 2 * i, LOGO_ROW, 2);
            vq_add(0, logo_buf[i] + 2, 1 + 2 * i, LOGO_ROW + 1, 2);
        }
    }
    // drips under P, O and the second E as they fill up
    o = shadow_OAM + OAM_DRIP;
    o->y = 0;
    for (i = 1; i < LOGO_LETTERS; i += 3) {
        d = (int16_t)title_t - (LOGO_T0 + i * LOGO_STAGGER + (TT_LOGO_STATES - 2) * LOGO_STEP);
        if (d >= 0 && d < DRIP_LEN) {
            o->x = 8 + 16 * i + 3 + 8;                // under the letter's left stem (every letter has one)
            if (d < 8) { o->y = (LOGO_ROW + 2) * 8 - 3 + 16; o->tile = FX_DRIP; }
            else       { o->y = (LOGO_ROW + 2) * 8 - 4 + (uint8_t)d + 16; o->tile = FX_DRIP + 2; }
            o->prop = is_cgb ? OBJPAL_FX : 0;
        }
    }
    // one sparkle across the letters once they are all full
    o = shadow_OAM + OAM_SPARKLE;
    o->y = 0;
    if (title_t >= SPARKLE_T0) {
        d = (int16_t)title_t - SPARKLE_T0;
        i = (uint8_t)d / SPARKLE_EACH;
        if (i < LOGO_LETTERS) {
            s = (uint8_t)d % SPARKLE_EACH;
            o->y = LOGO_ROW * 8 - 2 + 16; o->x = 8 + 16 * i + 11 + 8;      // centred on the letter's top-right corner
            o->tile = (s && s < SPARKLE_EACH - 1) ? FX_SPARKLE + 2 : FX_SPARKLE;
            o->prop = is_cgb ? OBJPAL_FX : S_PALETTE;
        }
    }
    if (title_t >= LOGO_DONE_T) logo_done = 1;
}

// ---- bubbles: now and then one rises from below the logo to the top of the screen ----------------
static void bubbles_frame(void) {
    uint8_t i, y;
    OAM_item_t *o = shadow_OAM + OAM_BUBBLE;
    bubble_half ^= 1;
    if (title_t > LOGO_FILLED && !--bubble_timer) {
        bubble_timer = 50 + (trand() & 63);
        i = bubble_y[0] ? 1 : 0;
        if (!bubble_y[i]) {
            bubble_y[i] = (LOGO_ROW + 2) * 8 + 16;                  // OAM y: just under the logo
            bubble_x[i] = 12 + (trand() & 127) + 8;
        }
    }
    for (i = 0; i < 2; i++, o++) {
        y = bubble_y[i];
        if (y && bubble_half && !--y) y = 0;                        // 0.5 px per frame; gone above the screen
        if (y < 4) y = 0;
        bubble_y[i] = y;
        if (!y) { o->y = 0; continue; }
        o->y = y;
        o->x = bubble_x[i] + ((y >> 3) & 1);                        // a little wobble
        o->tile = y < LOGO_ROW * 8 + 16 ? FX_BUBBLE + 2 : FX_BUBBLE;
        o->prop = is_cgb ? OBJPAL_FX : S_PALETTE;
    }
}

// ---- the bar scene on the bottom counter -----------------------------------------------------------
// held-mug poses while the patron drinks: (frame of the drink art, dx from the patron, dy from the wall top)
static void scene_frame(void) {
    OAM_item_t *o = shadow_OAM + OAM_TMUG;
    uint8_t t = ++tscene_timer, full = is_cgb ? OBJPAL_MUG_FULL : 0, f;
    bartender_frame = BT_IDLE;
    o->y = 0;
    switch (tscene_phase) {
    case SC_IDLE:
        if (t >= SC_IDLE_FRAMES) { tscene_phase = SC_SLIDE; tscene_timer = 0; tscene_mug_x = LAUNCH_X; }
        break;
    case SC_SLIDE:                                  // the full mug slides left, 2 px per frame
        if (t <= SC_SLIDE_POSE) bartender_frame = BT_SLIDE;
        tscene_mug_x -= 2;
        o->y = SCENE_TOP_Y + MUG_DY; o->x = tscene_mug_x + 8; o->tile = OBJ_MUG; o->prop = S_PALETTE | OBJPAL_MUG_FULL;
        if (tscene_mug_x <= CATCH_X) { tscene_phase = SC_DRINK; tscene_timer = 0; }
        break;
    case SC_DRINK:                                  // at the hand, up to the mouth, tilted
        f = t < 12 ? 0 : t < 40 ? 1 : 2;
        o->y = SCENE_TOP_Y + (f ? 1 : 5); o->x = PATRON_PX + (f ? 8 : 9) + 8;
        o->tile = OBJ_MUG_DRINK + f * 2; o->prop = full;
        tscene_mug_x = PATRON_PX + 8;
        if (t >= SC_DRINK_FRAMES) { tscene_phase = SC_WINDUP; tscene_timer = 0; }
        break;
    case SC_WINDUP:                                 // the empty lowered, drawn back, swung forward
        f = t < 8 ? 8 - (t >> 1) : t < 18 ? 4 : 14;
        o->y = SCENE_TOP_Y + 6; o->x = PATRON_PX + f + 8;
        o->tile = OBJ_MUG_DRINK + 3 * 2; o->prop = S_PALETTE | OBJPAL_MUG_EMPTY;
        if (t >= SC_WINDUP_FRAMES) { tscene_phase = SC_RETURN; tscene_timer = 0; tscene_mug_x = CATCH_X; }
        break;
    case SC_RETURN:                                 // the empty slides back, 1 px per frame
        tscene_mug_x++;
        o->y = SCENE_TOP_Y + MUG_DY; o->x = tscene_mug_x + 8; o->tile = OBJ_MUG + 2; o->prop = S_PALETTE | OBJPAL_MUG_EMPTY;
        if (tscene_mug_x >= LAUNCH_X) { tscene_phase = SC_CATCH; tscene_timer = 0; }
        break;
    case SC_CATCH:
        bartender_frame = BT_CATCH;
        if (t >= SC_CATCH_FRAMES) { tscene_phase = SC_IDLE; tscene_timer = 0; tscene_loops++; }
        break;
    }
    draw_bartender();
}

// ---- the menu ---------------------------------------------------------------------------------
static void cursor_frame(void) {
    OAM_item_t *o = shadow_OAM + OAM_CURSOR;
    if (title_msg) { o->y = 0; return; }
    o->y = sel_row[title_sel] * 8 - 7 + 16;
    o->x = text_left(title_sel) - 13 - ((title_t >> 4) & 1) + 8;
    o->tile = OBJ_MUG; o->prop = is_cgb ? OBJPAL_MUG_FULL : 0;     // DMG: OBP0 like the held mug (shows on the white wall)
}

// One title frame. 1: ARCADE was chosen (main.c starts the game); 2: no key for TITLE_IDLE_FRAMES (the table).
uint8_t title_update(uint8_t pressed) BANKED {
    uint8_t old = title_sel;
    title_t++;
    if (pressed) title_idle = 0;
    else if (++title_idle >= TITLE_IDLE_FRAMES) return 2;
    if (pressed & J_SELECT) title_music_toggle();
    if (title_msg) {
        if (!--title_msg) {                         // "COMING SOON" is over: STORY again
            build_row(row_story, tt_story);
            vq_add(0, row_story, 0, ROW_STORY, 20);
        }
    } else {
        if (pressed & J_UP) title_sel = title_sel ? title_sel - 1 : 2;
        else if (pressed & J_DOWN) title_sel = title_sel == 2 ? 0 : title_sel + 1;
        if (title_sel != old) { set_sel_attr(old, 0); set_sel_attr(title_sel, 1); }
        else if (pressed & (J_A | J_START)) {
            if (title_sel == 0) return 1;
            if (title_sel == 1) {
                title_msg = MSG_FRAMES;
                build_row(row_story, tt_soon);
                vq_add(0, row_story, 0, ROW_STORY, 20);
            } else title_music_toggle();
        }
    }
    logo_frame();
    bubbles_frame();
    scene_frame();
    cursor_frame();
    return 0;
}
