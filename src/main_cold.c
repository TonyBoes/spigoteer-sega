// Cold game flow, moved out of src/main.c (ROM0) into a switchable bank: boot, the HUD's full redraw, the level
// screen and the state changes (new game, life lost, game over, level clear), the banner window's setup and the
// glyph lookup. None of it runs in the per-frame hot path. What must stay in ROM0 stays in main.c: the far-copy
// helpers (they switch banks), the LCD interrupt handler, show_overlay (its callers pass strings from their own
// banks), the frame loop.
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"
#include "palettes.h"
#include "bonus.h"
#include "music.h"

BANKREF_EXTERN(art_tiles)
#define bkg_data(first, n, d) bkg_data_far(first, n, d, BANK(art_tiles))
#define spr_data(first, n, d) spr_data_far(first, n, d, BANK(art_tiles))

#define LEVEL_BONUS        1000

extern uint32_t score;
extern uint8_t  bar, bartender_x, bartender_frac, facing, bartender_frame, at_tap, walk_timer, bt_bob, walk_phase;
extern uint8_t  fill_timer, fill_stage, slide_timer, game_over, state_timer, overlay_on, level, cur_group;
extern uint8_t  story_shift;
extern uint8_t  frame_counter, joy, joy_prev, rng_state, score_digits[6], arcade_loop, new_rank;

// ---- palettes ----------------------------------------------------------------
#define RGB15(r, g, b) ((uint16_t)((r) | ((g) << 5) | ((b) << 10)))

// BG 1: HUD, light text on a dark band (art: '.' text, '#' band). c2 (0: none) replaces colour 2, the HUD flag's cloth in a STORY EASY / HARD run (draw_hud)
// (tools/gen_story.py reads the four literal colours below)
static void hud_palette(uint16_t c2) {
    palette_t p;
    p[0] = RGB15(31, 29, 22);
    p[1] = RGB15(24, 20, 10);
    p[2] = RGB15(29, 20, 4);
    p[3] = RGB15(3, 2, 8);
    if (c2) p[2] = c2;
    set_bkg_palette(BGPAL_HUD, 1, p);
}

void hud_pal_reset(void) BANKED {                  // a STORY run ends (credits, quit): the HUD palette as it was made (an EASY / HARD run tinted its colour 2)
    if (is_cgb) hud_palette(0);
}

static void load_cgb_palettes(void) {
    palette_t p;

    // BG 0, 5, 6, 7 (bar, stage, keg) and the drink / show OBJ palettes come with the venue (load_venue)
    hud_palette(0);

    pal_get(PAL_BARTENDER, p);
    set_sprite_palette(OBJPAL_BARTENDER, 1, p);
    pal_get(PAL_COIN, coin_pal);               // render.c's slot-5 switch reads it every frame (the table is banked)
    // M13a: the glass shares the venue's empty-drink palette, the coin slot 5 (render.c), patrons 3/6/7 (lift.c)
}

// ---- scene -------------------------------------------------------------------
static void glyph_row(uint8_t y, uint8_t x, const uint8_t *tiles, uint8_t n) {
    vram_put(x, y, tiles, n);
}

static uint8_t digit_tile(uint8_t d) { return TILE_GLYPH_0 + d; }

static void draw_lives(void) {
    glyph_row(HUD_ROW, 7, lives_tiles, 2);
    hud_dirty &= ~HUD_LIVES;
}

static void draw_score(void) {
    glyph_row(HUD_ROW, 0, score_tiles, 6);
    hud_dirty &= ~HUD_SCORE;
}

void draw_hud(void) BANKED {
    uint8_t buf[3], i;
    volatile uint8_t *t;

    prep_hud();
    for (i = 0; i < 20; i++) row_buf[i] = TILE_HUD_BLANK;
    put_row(HUD_ROW);
    draw_score();                                   // six digits, cols 0-5
    draw_lives();                                   // the head and the lives digit, cols 7-8
    buf[0] = TILE_HUD_FLAG;                          // the level: a flag col 17, two digits cols 18-19
    buf[1] = digit_tile(level / 10); buf[2] = digit_tile(level % 10);
    glyph_row(HUD_ROW, 17, buf, 3);
    if (is_cgb && RUN_DIFF) {                       // the difficulty's colour (STORY only; DMG shows none; NORMAL: as always, nothing here): the flag's cloth, the
        i = RUN_DIFF;                               // tile's pixels of colour 0, becomes colour 2 of the HUD palette, which is green (EASY) or red (HARD) for this
        hud_palette(i == DIFF_EASY ? RGB15(6, 24, 8) : RGB15(30, 5, 5));   // run (hud_pal_reset puts it back when the run ends)
        t = (volatile uint8_t *)(0x9000 + TILE_HUD_FLAG * 16);   // (LCD off: the tile's bytes in VRAM, signed id 76 < 128 at 0x9000)
        for (i = 0; i < 16; i += 2) t[i + 1] |= ~(t[i] | t[i + 1]);
    }
}

// tile k of the HUD icons (assets/art/hud_icons.txt) to BG id `id`, LCD off
void hud_icon_load(uint8_t id, uint8_t k) BANKED {
    bkg_data(id, 1, hud_icon_tiles + ((uint16_t)k << 4));
}

// The level screen (LCD off): shared tiles, the venue's stage / counters / floor, the HUD, then the bars' wall
// rows with their patrons (render.c). load_venue() has run (start_level).
static void init_scene(void) {
    bkg_data(TILE_GENERIC_BASE, GENERIC_TILE_COUNT, bar_tiles);
    draw_venue();
    draw_hud();
    write_all_bars();
    stage_anim_start();
}

// ---- game -----------------------------------------------------------------------
static void win_init(void);
void boot_init(void) BANKED {
    uint8_t i;

    TRANS = TRANS_DEFAULT << TR_VSHIFT;                                  // (HRAM is not cleared at power-on: first, DISPLAY_OFF reads it)
#ifdef AUTO_NOTRANS                                                      // test-only (tests/test_fade_hw.py): the reference ROM, no transition at all
    TRANS |= TR_OFF;
#endif
    DISPLAY_OFF;
    // _cpu alone is not enough under PyBoy: its DMG mode still hands the cart
    // A=0x11. FF4F (VBK) reads 0xFE|bank on colour hardware, but plain 0x00 in
    // PyBoy's DMG mode, so the VBK test rejects PyBoy-DMG. It cannot tell a real
    // DMG apart (unmapped I/O reads 0xFF, which also passes), but a real DMG
    // already fails the _cpu test, so the pair is right on all three.
    VBK_REG = VBK_BANK_0;
    is_cgb = (_cpu == CGB_TYPE) && ((VBK_REG & 0xFE) == 0xFE);
    if (is_cgb) {
        load_cgb_palettes();
    } else {
        BGP_REG  = 0xE4;   // 11 10 01 00: index 3 darkest
        OBP0_REG = 0xD0;   // bartender: idx1 white, idx2 light grey, idx3 black
        OBP1_REG = OBP1_MENU;   // title: mugs, sparkles: idx1 light grey, idx2 white, idx3 black; in play OBP1_PLAY (lift.c)
    }
    music_init();
    hi_load();
    SPRITES_8x16;
    spr_data(OBJ_BARTENDER, BARTENDER_FRAMES * BARTENDER_TILES_PER_FRAME, bartender_tiles);
    spr_data(OBJ_COIN, COIN_TILE_COUNT, coin_tiles);      // the drink and show tiles come with each venue (load_venue)
    for (i = 0; i < 40; i++) move_sprite(i, 0, 0);          // hide everything

    rng_state = 0xA7;
    boss_bar = BOSS_NONE;          // no boss fight (render.c / patrons.c compare against it)
    frame_counter = 0; joy = joy_prev = 0;
    game_over = 0; game_state = GS_TITLE;
    CRITICAL { add_VBL(vq_vbl); }  // the VBlank copy queue drains from the interrupt (render.c)
    win_init();
    SHOW_BKG; SHOW_SPRITES;
    title_enter();                 // turns the LCD on (title.c)
}

// ---- screens and state changes --------------------------------------------------------
uint8_t say_bang;           // '!' has no HUD glyph: a screen with its own '!' tile points this at it (0: blank)
uint8_t glyph_for(char c) BANKED {
    if (c >= '0' && c <= '9') return TILE_GLYPH_0 + (c - '0');
    switch (c) {
    case 'A': return TILE_GLYPH_A; case 'C': return TILE_GLYPH_C; case 'E': return TILE_GLYPH_E;
    case 'G': return TILE_GLYPH_G; case 'H': return TILE_GLYPH_H; case 'I': return TILE_GLYPH_I;
    case 'L': return TILE_GLYPH_L; case 'M': return TILE_GLYPH_M; case 'O': return TILE_GLYPH_O;
    case 'P': return TILE_GLYPH_P; case 'R': return TILE_GLYPH_R; case 'S': return TILE_GLYPH_S;
    case 'B': return TILE_GLYPH_B; case 'D': return TILE_GLYPH_D; case 'K': return TILE_GLYPH_K;
    case 'N': return TILE_GLYPH_N; case 'W': return TILE_GLYPH_W; case 'Y': return TILE_GLYPH_Y;
    case 'F': return TILE_GLYPH_F; case 'T': return TILE_GLYPH_T; case 'U': return TILE_GLYPH_U; case 'V': return TILE_GLYPH_V;
    case 'J': return TILE_GLYPH_J; case 'Q': return TILE_GLYPH_Q; case 'X': return TILE_GLYPH_X; case 'Z': return TILE_GLYPH_Z;
    case '!': if (say_bang) return say_bang;
    }
    return TILE_HUD_BLANK;
}

// Banner window (tile rows 0..2 of the 0x9C00 map): frame, a text row that
// show_overlay() rewrites through the VBlank queue, frame. Attributes are HUD palette.
static void win_init(void) {
    uint8_t i;
    for (i = 0; i < 20; i++) row_buf[i] = TILE_PANEL_TOP;
    vram_put(0, 32, row_buf, 20);
    for (i = 0; i < 20; i++) row_buf[i] = TILE_HUD_BLANK;
    vram_put(0, 33, row_buf, 20);
    for (i = 0; i < 20; i++) row_buf[i] = TILE_PANEL_BOT;
    vram_put(0, 34, row_buf, 20);
    if (is_cgb) {
        VBK_REG = VBK_BANK_1;
        for (i = 0; i < 20; i++) row_buf[i] = BGPAL_HUD;
        vram_put(0, 32, row_buf, 20); vram_put(0, 33, row_buf, 20); vram_put(0, 34, row_buf, 20);
        VBK_REG = VBK_BANK_0;
    }
    LCDC_REG |= LCDCF_WIN9C00;
    WX_REG = 7; WY_REG = BANNER_WY;
    STAT_REG = STATF_LYC; LYC_REG = BANNER_LYC;
    add_LCD(lcd_isr);              // (the handler itself is in ROM0: main.c)
    set_interrupts(VBL_IFLAG | LCD_IFLAG);
}

static void reset_actors(void) {
    uint8_t i;
    bar = 0; bartender_x = bar_tap[0]; bartender_frac = 0; facing = 0; bartender_frame = BT_IDLE; at_tap = 1;
    bt_bob = 0; walk_timer = 0; walk_phase = 0; fill_timer = 0; fill_stage = 0; slide_timer = 0; catch_pose = 0;
    cue_t = 0;                                   // (story's PERFECT cue; hide_all_sprites takes its entry)
    clear_mugs();
    next_arrival = 0;
    tip_timer = 0; show_timer = 0; dancers_vis = 0; oam_touched();      // a bar reset ends the show and takes the tip away
    for (i = 0; i < MAX_PATRONS; i++) patron_dist[i] = 0;
    if (boss_on) boss_reset();                   // a boss fight: he starts over at his start x (his meter kept)
}

// Draw the playfield for the current level/lives/score. Screen transition: LCD off.
void enter_level_screen(void) BANKED {
    TRANS_WANT();                                 // (src/trans.c: title -> a level, a level -> the next; a story shift's LCD is already off: nothing wanted then)
    DISPLAY_OFF;                                 // (start_level reloads the show tiles the bonus round borrowed)
    overlay_on = 0; HIDE_WIN; vq_reset(); hud_dirty = 0; life_lost = 0;
    state_timer = 0;                              // (the antics' 255 of the clear before)
    start_level();
    dust_load();                                 // the bar-change puff's tiles (OBJ ids above the DMG copies)
    if (boss_on) boss_load();                    // a boss fight (story): his tiles over variant C's, his palettes
    init_scene();
    reset_actors();
    hide_all_sprites();
    draw_bartender();
    if (bar_dirs) mirror_oam();                  // P3: on an R bar from the first frame shown
    game_over = 0;
    music_play(TUNE_VENUE0 + cur_group);          // the venue's own tune (before the state: a test sampling mid-load sees it)
    if (play_mode == MODE_LEVEL && cur_group == 0 && level > 1) {   // M10b: a new loop: "LOOP n" first, then the intro
                                                  // (the LEVEL harness only; ARCADE shows its own: story.c; CLASSIC none)
        char s[8] = "LOOP ";
        if (arcade_loop >= 10) { s[5] = '0' + arcade_loop / 10; s[6] = '0' + arcade_loop % 10; }
        else s[5] = '0' + arcade_loop;
        show_overlay(s);
        state_timer = 0;
        game_state = GS_LOOP;
    } else game_state = GS_PLAYING;               // (one write: a test sampling mid-load never sees PLAYING before LOOP)
    DISPLAY_ON;
}

// A level-engine game from level lv (play_mode set by the caller: MODE_LEVEL, the old 10-level rotation, the test harness
// and the debug select's LEVEL box; MODE_CLASSIC, CLASSIC's table: classic.c)
void start_new_game(uint8_t lv) BANKED {
    uint8_t i;
    lives = START_LIVES; level = lv; score = 0; bonus_round = 0; story_on = 0; story_arc = 0;
    extra_at = play_mode == MODE_CLASSIC ? EXTRA_FIRST : 0;   // extra lives: CLASSIC, not the harness
    pour_q = 0;                                  // arcade: never a perfect pour (src/pour.c runs in story only)
    pat_len = 0;                                 // arcade: the normal random arrivals (a story shift sets a pattern)
    music_fast = 0; mosh_set(0, 0);              // arcade: no venue twists (a story shift sets them)
    boss_set(BOSS_NONE);                         // (the debug menu may leave a story boss fight)
    for (i = 0; i < 6; i++) score_digits[i] = 0;
    enter_level_screen();
}

// after a lost life: same level, same served count, fresh bars
void resume_after_life(void) BANKED {
    uint8_t p;
    for (p = 0; p < MAX_PATRONS; p++) if (patron_state[p]) remove_patron(p);
    reset_actors();
    hide_all_sprites();
    life_lost = 0; overlay_on = 0;               // (story: the "2 LIVES LOST" banner of the freeze goes)
    if (ramp_t | ramp_k) classic_ramp_reset();   // CLASSIC: the level's own pace again (classic.c)
    spawn_timer = spawn_interval; intro_timer = INTRO_FRAMES;
    place_start_patrons();
    draw_bartender();
    game_state = GS_PLAYING;
    music_play(TUNE_VENUE0 + cur_group);         // a show that was running ended with the life: back to the venue's tune
}

void enter_game_over(void) BANKED {
    // the initials from WRAM (the stack): top_insert runs in its own bank and cannot read a literal in this one
    uint8_t aaa[3];
    if (play_mode == MODE_STORY || play_mode == MODE_RUSH) { story_fail(); return; }   // M11b: in story mode the goal
                                                 // failed: TRY AGAIN (BOSS RUSH: GAME OVER, then the rush's result)
    story_on = 0; story_arc = 0;                 // (ARCADE runs on the story's engine: the run ends here)
    score_tbl = play_mode == MODE_LEVEL ? MODE_ARCADE : play_mode;   // the mode's top 5 (the harness counts as ARCADE)
    aaa[0] = aaa[1] = aaa[2] = 'A';
    new_rank = top_insert(score, aaa);           // in at once (initials follow), so a power-off keeps it
    if (new_rank < TOP_N) hi_save();
    show_overlay("GAME OVER");
    state_timer = 0;
    music_play(TUNE_OVER);
    game_state = GS_GAME_OVER;
}

void enter_level_clear(void) BANKED {
    uint8_t i;
    tip_timer = 0; show_timer = 0;               // a tip is simply forgotten when the level ends
    for (i = OAM_COIN; i < 40; i++) shadow_OAM[i].y = 0;
    dancers_vis = 0; oam_touched();
    add_score(LEVEL_BONUS);
    state_timer = 0;
    show_overlay("LEVEL CLEAR");
    music_play(TUNE_CLEAR);
    // P6: the end-of-level antics (src/antics.c): CLASSIC's, and (F12) STORY / ARCADE's after the Happy hour: the clears of
    // the Happy hour and the Last call (story_shift 1 and 2), not the Opening shift, a boss fight or a mini-game. state_timer
    // 255 tells main.c's GS_LEVEL_CLEAR that the antics run (a plain clear counts it up to CLEAR_FRAMES, never so far).
    if (play_mode == MODE_CLASSIC || (story_on && !boss_on && story_shift)) { antics_start(); state_timer = 255; }
    game_state = GS_LEVEL_CLEAR;                 // last: whoever sees the state sees the banner and the jingle
}
