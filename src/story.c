// Story mode (M11b): "The Golden Spigot" (docs/story.md). Cut-scenes, the chapter flow, the chapter goals.
//
// Flow: title STORY -> INTRO -> per chapter c (0..8): PRE scene -> the venue's level with the chapter goal (a banner
// first, GS_GOAL) -> on success CHAPTER CLEAR, the progress saved (SRAM, save.c), the POST scene -> the next chapter;
// after chapter 9's POST scene FINALE, CREDITS, then the title. CONTINUE on the title resumes at the PRE scene of the
// first chapter not cleared. A failed goal shows TRY AGAIN and the chapter restarts at its goal banner, with fresh
// lives (lives work as in arcade: losing all three fails the goal; the score carries on and never enters the top 5).
//
// Cut-scene ("hybrid lighter" style): the venue's stage + bar rows as the backdrop (no patrons), the Spigoteer's
// normal sprite at bar 1's tap, the scene title on the HUD row, a framed speaker portrait above a full-width text
// box (rows 13-17: panel, 3 lines of 18 characters at columns 1-18, panel). The NARRATOR has no portrait: the box shows
// the small golden spigot where a name would be. INTRO, FINALE and CREDITS show a picture slot instead of a venue
// (tools/gen_story.py: placeholders for now). The text types on, one character a frame. Buttons: A or B shows the
// rest of the page at once, then the next page; START skips the rest of the scene.
//
// The portrait slot is data-driven (build/story_portraits.c, from assets/story/portraits.json): size up to 7x7 tiles,
// position, up to 3 CGB BG palettes (slots 2-4) and an optional OBJ overlay (OAM 4.., OBJ tiles OBJ_DANCER.., palettes
// 3, 4, 6, 7). All the scene's portraits are loaded when it starts (LCD off); a speaker change rewrites only the tile
// map: the old frame is wiped back to the backdrop (a WRAM copy of rows 0-12), then the palettes change (at the top
// of a frame, in VBlank) and the new frame is drawn, 2 rows a frame through the VBlank queue.
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"
#include "music.h"
#include "bonus.h"
#include "story.h"

BANKREF_EXTERN(art_tiles)
extern const uint8_t bar_tiles[];
extern uint8_t overlay_on, level, game_over, state_timer, score_digits[6];
extern uint32_t score;

#define SCENE_BAR        1         // the Spigoteer stands at this bar's tap during a cut-scene
#define BOX_ROW         13         // the text box: panel row 13, text rows 14-16, panel row 17
#define BOX_TEXT_ROW    14
#define SWAP_ROWS        2         // portrait rows queued per frame (map + attributes: <= 36 bytes)
#define OAM_OVERLAY      4         // the portrait's OBJ overlay: OAM 4..
#define GOAL_FRAMES    180         // the goal banner stays 3 s (or until A / START)
#define FAIL_FRAMES    150         // TRY AGAIN
#define GOAL_WY        BANNER_WY   // the goal banner: window rows 0-4 (map rows 32-36): panel, 3 lines, panel
#define GOAL_LYC       (BANNER_WY + 38)
#define HUD_GOAL_COL    12         // story HUD: goal letter + 2 digits (what is left) at 12-14, timer 'T' + 3 digits at 16-19

enum { SP_OFF, SP_SCENE, SP_GOAL, SP_PLAY, SP_FAIL };
enum { SW_IDLE, SW_OUT, SW_PAL, SW_IN };

// ---- state (globals => symbols the tests read) ----
uint8_t  story_on;                 // 1: story mode (main.c, main_cold.c)
uint8_t  story_phase;              // SP_*
uint8_t  story_scene;              // SC_* (build/story.h)
uint8_t  story_page;               // page of the scene on screen
uint8_t  story_chapter;            // 0..8
uint8_t  story_typed;              // characters of the page typed so far (54: the whole page)
uint8_t  story_spk;                // speaker of the page
uint8_t  story_cur;                // speaker whose portrait is on screen (255: none)
uint8_t  story_swap;               // SW_*: a portrait change in progress
uint8_t  story_catches, story_breaks, story_taps;   // this attempt: empties caught, glasses broken, patrons at the tap
uint8_t  story_left;               // what is left of the goal's count (HUD)
uint16_t story_timer;              // frames left of a timed goal (0: none / out)
uint8_t  story_fails;              // goal failures so far (tests)
uint8_t  story_twist;              // the chapter's twist id (0 none): the hook for a later milestone
scene_hdr_t story_hdr;
goal_t   story_goal;

static uint8_t page_buf[55];
static uint8_t box_tiles[3][18];
static uint8_t tag_row[20];
static uint8_t hud_buf[8];
static uint8_t win_rows[5][20];
static uint8_t bd_map[STORY_PIC_ROWS * 20], bd_attr[STORY_PIC_ROWS * 20];   // the backdrop of rows 0-12
static portrait_t pt;              // the portrait being drawn / on screen
static uint8_t pt_map[9 * 9], pt_attr[9 * 9];   // its framed rectangle, composed
static uint8_t spk_bg[STORY_MAX_SPK], spk_obj[STORY_MAX_SPK];   // where each scene speaker's tiles were loaded
static uint8_t cx, cy, cw, ch;     // the rectangle on screen (frame included); cw 0: none
static uint8_t sw_row, sw_next;    // swap: next row to queue; the speaker coming in
static uint8_t st_last_catch, st_last_break, st_secs;
static uint8_t story_t;            // frames in this phase

static const uint8_t alpha[26] = {
    TILE_GLYPH_A, TILE_GLYPH_B, TILE_GLYPH_C, TILE_GLYPH_D, TILE_GLYPH_E, TILE_GLYPH_F, TILE_GLYPH_G, TILE_GLYPH_H,
    TILE_GLYPH_I, TILE_GLYPH_J, TILE_GLYPH_K, TILE_GLYPH_L, TILE_GLYPH_M, TILE_GLYPH_N, TILE_GLYPH_O, TILE_GLYPH_P,
    TILE_GLYPH_Q, TILE_GLYPH_R, TILE_GLYPH_S, TILE_GLYPH_T, TILE_GLYPH_U, TILE_GLYPH_V, TILE_GLYPH_W, TILE_GLYPH_X,
    TILE_GLYPH_Y, TILE_GLYPH_Z,
};
static const uint8_t ovl_pal[4] = { 3, 4, 6, 7 };   // CGB OBJ slots of the overlay's palettes (5: the coin / show)

static uint8_t st_glyph(uint8_t c) {
    if (c >= 'A' && c <= 'Z') return alpha[c - 'A'];
    if (c >= '0' && c <= '9') return TILE_GLYPH_0 + (c - '0');
    switch (c) {
    case '.': return ST_GLYPH_PERIOD; case ',': return ST_GLYPH_COMMA; case '!': return ST_GLYPH_EXCL;
    case '?': return ST_GLYPH_QUEST; case '\'': return ST_GLYPH_APOS; case '-': return ST_GLYPH_HYPHEN;
    case ':': return ST_GLYPH_COLON;
    }
    return TILE_HUD_BLANK;
}

static void fill(uint8_t *d, uint8_t v, uint8_t n) { while (n--) *d++ = v; }

// a string (WRAM or this bank) centred into a 20-tile row of HUD glyphs (and story glyphs)
static void centre(uint8_t *row, const char *s) {
    uint8_t n = 0, i;
    fill(row, TILE_HUD_BLANK, 20);
    while (s[n] && n < 20) n++;
    for (i = 0; i < n; i++) row[((20 - n) >> 1) + i] = st_glyph(s[i]);
}

// ---- the portrait slot ------------------------------------------------------------------------------------
static uint8_t spk_index(uint8_t spk) {          // the speaker's place in the scene's list (255: no portrait)
    uint8_t i;
    for (i = 0; i < story_hdr.nspk; i++) if (story_hdr.spk[i] == spk) return i;
    return 255;
}

// pt (fetched) -> its framed rectangle in pt_map / pt_attr; new cx..ch
static void compose_portrait(uint8_t k) {
    uint8_t w = pt.w + 2, h = pt.h + 2, x, y, i = 0, t, a;
    for (y = 0; y < h; y++)
        for (x = 0; x < w; x++, i++) {
            a = BGPAL_HUD;
            if (y == 0)          t = x == 0 ? ST_FRAME_TL : x == w - 1 ? ST_FRAME_TR : ST_FRAME_T;
            else if (y == h - 1) t = x == 0 ? ST_FRAME_BL : x == w - 1 ? ST_FRAME_BR : ST_FRAME_B;
            else if (x == 0)     t = ST_FRAME_L;
            else if (x == w - 1) t = ST_FRAME_R;
            else {
                t = spk_bg[k] + pt.map[(y - 1) * pt.w + x - 1];
                a = BGPAL_PATRON + pt.attr[(y - 1) * pt.w + x - 1];
            }
            pt_map[i] = t; pt_attr[i] = a;
        }
    cx = pt.x - 1; cy = pt.y - 1; cw = w; ch = h;
}

static void overlay_hide(void) {
    uint8_t i;
    for (i = 0; i < STORY_MAX_OBJ; i++) shadow_OAM[OAM_OVERLAY + i].y = 0;
}

static void overlay_show(uint8_t k) {
    uint8_t i, *e = pt.obj, f;
    OAM_item_t *o = shadow_OAM + OAM_OVERLAY;
    for (i = 0; i < pt.nobj; i++, e += 4, o++) {
        o->y = pt.y * 8 + e[0] + 16; o->x = pt.x * 8 + e[1] + 8;
        o->tile = spk_obj[k] + e[2];
        f = e[3];
        o->prop = is_cgb ? ovl_pal[f & 3] : ((f & 0x10) ? S_PALETTE : 0);
    }
}

static void write_palettes(void) {              // CGB, in VBlank (the top of a frame) or with the LCD off
    uint8_t i;
    if (!is_cgb) return;
    for (i = 0; i < pt.npal; i++) set_bkg_palette(BGPAL_PATRON + i, 1, pt.pal + i * 4);
    for (i = 0; i < pt.nobjpal; i++) set_sprite_palette(ovl_pal[i], 1, pt.opal + i * 4);
}

// LCD off: the page's portrait straight to the screen (scene start)
static void portrait_now(uint8_t spk) {
    uint8_t k = spk_index(spk), y;
    story_cur = 255; cw = 0;
    if (k == 255) return;
    portrait_get(spk, &pt);
    compose_portrait(k);
    write_palettes();
    for (y = 0; y < ch; y++) {
        set_bkg_tiles(cx, cy + y, cw, 1, pt_map + y * cw);
        if (is_cgb) { VBK_REG = VBK_BANK_1; set_bkg_tiles(cx, cy + y, cw, 1, pt_attr + y * cw); VBK_REG = VBK_BANK_0; }
    }
    overlay_show(k);
    story_cur = spk;
}

// one frame of a portrait change (LCD on)
static void swap_frame(void) {
    uint8_t n, k;
    switch (story_swap) {
    case SW_OUT:                                 // wipe the old frame back to the backdrop
        for (n = 0; n < SWAP_ROWS && sw_row < ch; n++, sw_row++) {
            k = (cy + sw_row) * 20 + cx;
            vq_add(0, bd_map + k, cx, cy + sw_row, cw);
            if (is_cgb) vq_add(1, bd_attr + k, cx, cy + sw_row, cw);
        }
        if (sw_row >= ch) { cw = 0; story_cur = 255; story_swap = spk_index(sw_next) == 255 ? SW_IDLE : SW_PAL; }
        break;
    case SW_PAL:                                 // (the top of the frame after the wipe went out: VBlank)
        k = spk_index(sw_next);
        portrait_get(sw_next, &pt);
        write_palettes();
        compose_portrait(k);
        sw_row = 0;
        story_swap = SW_IN;
        // fall through: the first rows of the new frame
    case SW_IN:
        for (n = 0; n < SWAP_ROWS && sw_row < ch; n++, sw_row++) {
            vq_add(0, pt_map + sw_row * cw, cx, cy + sw_row, cw);
            if (is_cgb) vq_add(1, pt_attr + sw_row * cw, cx, cy + sw_row, cw);
        }
        if (sw_row >= ch) { story_cur = sw_next; story_swap = SW_IDLE; overlay_show(spk_index(sw_next)); }
        break;
    }
}

// ---- pages ------------------------------------------------------------------------------------------------
static void tag_build(void) {                    // row 13: the panel with the speaker's name (or the spigot) at the left
    uint8_t name[12], i;
    fill(tag_row, TILE_PANEL_TOP, 20);
    tag_row[1] = TILE_HUD_BLANK;
    if (story_spk == SPK_NARRATOR) {
        tag_row[2] = ST_SPIGOT_ICON; tag_row[3] = TILE_HUD_BLANK;
        return;
    }
    story_name_get(story_spk, name);
    for (i = 0; name[i] && i < 12; i++) tag_row[2 + i] = st_glyph(name[i]);
    tag_row[2 + i] = TILE_HUD_BLANK;
}

// LCD on (lcd 0) or off (1): the page's box cleared, its name tag; a portrait change starts if the speaker's differs
static void page_begin(uint8_t lcd_off) {
    uint8_t r;
    story_page_get(story_scene, story_page, page_buf);
    story_spk = page_buf[0];
    story_typed = 0;
    for (r = 0; r < 3; r++) fill(box_tiles[r], TILE_HUD_BLANK, 18);
    tag_build();
    if (lcd_off) {
        for (r = 0; r < 3; r++) set_bkg_tiles(1, BOX_TEXT_ROW + r, 18, 1, box_tiles[r]);
        set_bkg_tiles(0, BOX_ROW, 20, 1, tag_row);
        portrait_now(story_spk);
        return;
    }
    for (r = 0; r < 3; r++) vq_add(0, box_tiles[r], 1, BOX_TEXT_ROW + r, 18);
    vq_add(0, tag_row, 0, BOX_ROW, 20);
    if (story_spk == story_cur || (spk_index(story_spk) == 255 && story_cur == 255)) return;
    sw_next = story_spk;
    sw_row = 0;
    if (story_cur != 255) { story_swap = SW_OUT; overlay_hide(); }
    else story_swap = SW_PAL;
}

static void type_frame(void) {                   // one character a frame (spaces are free)
    uint8_t c, r, k;
    while (story_typed < 54) {
        c = page_buf[1 + story_typed];
        r = story_typed / 18; k = story_typed - r * 18;
        story_typed++;
        if (c != ' ') {
            box_tiles[r][k] = st_glyph(c);
            vq_add(0, &box_tiles[r][k], 1 + k, BOX_TEXT_ROW + r, 1);
            return;
        }
    }
}

static void type_all(void) {
    uint8_t r, k;
    for (r = 0; r < 3; r++) {
        for (k = 0; k < 18; k++) box_tiles[r][k] = st_glyph(page_buf[1 + r * 18 + k]);
        vq_add(0, box_tiles[r], 1, BOX_TEXT_ROW + r, 18);
    }
    story_typed = 54;
}

// ---- scenes -----------------------------------------------------------------------------------------------
static void read_rows(uint8_t *d) {              // LCD off: map rows 0..STORY_PIC_ROWS-1 of the selected VRAM bank
    uint8_t y, x;
    const uint8_t *m = (const uint8_t *)0x9800;
    for (y = 0; y < STORY_PIC_ROWS; y++, m += 32)
        for (x = 0; x < 20; x++) *d++ = m[x];
}

static void screen_off(void) {
    DISPLAY_OFF;
    overlay_on = 0; HIDE_WIN; vq_reset(); hud_dirty = 0; vram_pending = 0; life_lost = 0;
    clear_dirty();
    hide_all_sprites();
}

static void scene_enter(uint8_t s) {
    uint8_t i, bgn, objn, y;
    screen_off();
    clear_patrons(); clear_mugs();
    tip_timer = 0; show_timer = 0;
    story_scene = s; story_page = 0; story_swap = SW_IDLE; story_phase = SP_SCENE; story_t = 0;
    story_scene_get(s, (uint8_t *)&story_hdr);
    bkg_data_far(TILE_GENERIC_BASE, GENERIC_TILE_COUNT, bar_tiles, BANK(art_tiles));
    story_font_load();
    if (story_hdr.venue != 255) {
        load_venue(story_hdr.venue);
        draw_venue();
        write_all_bars();                         // the bars' wall rows, nobody on them
        centre(row_buf, story_hdr.title);         // the HUD row: the scene's title
        set_bkg_tiles(0, HUD_ROW, 20, 1, row_buf);
        bar = SCENE_BAR; bartender_x = TAP_X; facing = 0; bartender_frame = BT_IDLE; bt_bob = 0;
        draw_bartender();
        stage_anim_start();
    } else {
        story_pic_draw(story_hdr.pic, is_cgb);
    }
    // the text box
    fill(row_buf, TILE_PANEL_TOP, 20); set_bkg_tiles(0, BOX_ROW, 20, 1, row_buf);
    fill(row_buf, TILE_HUD_BLANK, 20);
    for (y = 0; y < 3; y++) set_bkg_tiles(0, BOX_TEXT_ROW + y, 20, 1, row_buf);
    fill(row_buf, TILE_PANEL_BOT, 20); set_bkg_tiles(0, BOX_ROW + 4, 20, 1, row_buf);
    if (is_cgb) {
        VBK_REG = VBK_BANK_1;
        fill(row_buf, BGPAL_HUD, 20);
        for (y = BOX_ROW; y < 18; y++) set_bkg_tiles(0, y, 20, 1, row_buf);
        VBK_REG = VBK_BANK_0;
    }
    // the backdrop under the portrait slot (rows 0-12), to wipe a portrait away
    read_rows(bd_map);
    if (is_cgb) { VBK_REG = VBK_BANK_1; read_rows(bd_attr); VBK_REG = VBK_BANK_0; }
    // every portrait of the scene, one after the other
    bgn = STORY_PORTRAIT_BASE; objn = OBJ_DANCER;
    for (i = 0; i < story_hdr.nspk; i++) {
        portrait_get(story_hdr.spk[i], &pt);
        portrait_tiles_load(story_hdr.spk[i], bgn, objn);
        spk_bg[i] = bgn; spk_obj[i] = objn;
        bgn += pt.ntiles; objn += pt.nobjtiles;
    }
    page_begin(1);
    music_play(story_hdr.venue != 255 ? TUNE_VENUE0 + story_hdr.venue : TUNE_TITLE);
    game_state = GS_STORY;
    DISPLAY_ON;
}

// ---- the chapter's HUD and banner --------------------------------------------------------------------------
static void two_digits(uint8_t *d, uint8_t v) {
    uint8_t t = 0;
    while (v >= 10) { v -= 10; t++; }
    d[0] = TILE_GLYPH_0 + t; d[1] = TILE_GLYPH_0 + v;
}

static void hud_goal(void) {                     // queue the goal counter (and the timer) on the HUD row
    uint8_t s, h = 0;
    if (story_goal.type == G_CLEAR) return;
    hud_buf[0] = story_goal.type == G_CATCH ? TILE_GLYPH_C : TILE_GLYPH_S;
    two_digits(hud_buf + 1, story_left);
    vq_add(0, hud_buf, HUD_GOAL_COL, HUD_ROW, 3);
    if (!story_goal.secs) return;
    s = st_secs;
    hud_buf[4] = TILE_GLYPH_T;
    while (s >= 100) { s -= 100; h++; }
    hud_buf[5] = TILE_GLYPH_0 + h;
    two_digits(hud_buf + 6, s);
    vq_add(0, hud_buf + 4, 16, HUD_ROW, 4);
}

static void chapter_start(void) {
    uint8_t i;
    story_goal_get(story_chapter, (uint8_t *)&story_goal);
    story_twist = story_goal.twist;
    DISPLAY_OFF;
    // the goal banner in the window (map rows 32-36): panel, CHAPTER n, the two goal lines, panel
    fill(win_rows[0], TILE_PANEL_TOP, 20);
    fill(win_rows[1], TILE_HUD_BLANK, 20);
    win_rows[1][5] = TILE_GLYPH_C; win_rows[1][6] = TILE_GLYPH_H; win_rows[1][7] = TILE_GLYPH_A; win_rows[1][8] = TILE_GLYPH_P;
    win_rows[1][9] = TILE_GLYPH_T; win_rows[1][10] = TILE_GLYPH_E; win_rows[1][11] = TILE_GLYPH_R;
    win_rows[1][13] = TILE_GLYPH_0 + story_chapter + 1;
    centre(win_rows[2], story_goal.line1);
    centre(win_rows[3], story_goal.line2);
    fill(win_rows[4], TILE_PANEL_BOT, 20);
    for (i = 0; i < 5; i++) vram_put(0, 32 + i, win_rows[i], 20);   // (map rows 32.. = the window's 0x9C00 map)
    if (is_cgb) {
        VBK_REG = VBK_BANK_1;
        fill(row_buf, BGPAL_HUD, 20);
        for (i = 0; i < 5; i++) vram_put(0, 32 + i, row_buf, 20);
        VBK_REG = VBK_BANK_0;
    }
    level = story_chapter + 1;
    lives = START_LIVES;
    enter_level_screen();                        // the venue's level (row level - 1), LCD on again, PLAYING
    if (story_goal.type != G_CLEAR) quota = 255; // serve / catch goals: patrons keep coming until the goal is met
    story_catches = story_breaks = story_taps = 0;
    st_last_catch = sfx_count[SFX_CATCH]; st_last_break = sfx_count[SFX_BREAK];
    story_left = story_goal.count;
    st_secs = story_goal.secs;
    story_timer = (uint16_t)story_goal.secs * 60;
    hud_goal();
    // the twists (a later milestone) hook in here: story_twist names the chapter's twist, 0 none
    overlay_on = 1;
    LYC_REG = GOAL_LYC;
    story_phase = SP_GOAL; story_t = 0;
    game_state = GS_GOAL;
}

static void goal_banner_off(void) {
    fill(win_rows[2], TILE_PANEL_BOT, 20);       // map row 34 is the normal banner's bottom panel again
    vq_add(0, win_rows[2], 0, 34, 20);
    LYC_REG = BANNER_LYC;
    overlay_on = 0;
}

// ---- entry points --------------------------------------------------------------------------------------------
// From the title: a new story (cont 0) or CONTINUE (cont 1: the PRE scene of the first chapter not cleared)
void story_begin(uint8_t cont) BANKED {
    uint8_t i;
    story_on = 1; story_fails = 0;
    score = 0;
    for (i = 0; i < 6; i++) score_digits[i] = 0;
    lives = START_LIVES; bonus_round = 0; game_over = 0;
    if (cont && story_progress && story_progress < STORY_CHAPTERS) {
        story_chapter = story_progress;
        scene_enter(SC_PRE_SALOON + 2 * story_chapter);
    } else {
        story_chapter = 0;
        scene_enter(SC_INTRO);
    }
}

static void scene_done(void) {
    uint8_t s = story_scene;
    if (s == SC_CREDITS) { story_on = 0; story_phase = SP_OFF; title_enter(); return; }
    if (s == SC_FINALE) { scene_enter(SC_CREDITS); return; }
    if (s == SC_INTRO) { scene_enter(SC_PRE_SALOON); return; }
    if (!((s - SC_PRE_SALOON) & 1)) { chapter_start(); return; }   // a PRE scene: the chapter
    if (story_chapter + 1 < STORY_CHAPTERS) {                       // a POST scene: the next chapter's PRE
        story_chapter++;
        scene_enter(SC_PRE_SALOON + 2 * story_chapter);
    } else scene_enter(SC_FINALE);
}

// GS_LEVEL_CLEAR is over (main.c): the progress saved, the chapter's POST scene
void story_level_done(void) BANKED {
    story_save(story_chapter + 1);
    scene_enter(SC_POST_SALOON + 2 * story_chapter);
}

// the goal failed: TRY AGAIN over the frozen level, then the chapter again (from enter_game_over, or story_play)
void story_fail(void) BANKED {
    show_overlay("TRY AGAIN");
    music_play(TUNE_OVER);
    story_fails++;
    story_phase = SP_FAIL; story_t = 0;
    game_state = GS_STORY;
}

static void story_win(void) {
    enter_level_clear();                         // (its LEVEL CLEAR banner, the bonus, the jingle, GS_LEVEL_CLEAR)
    show_overlay("CHAPTER CLEAR");
}

// Every GS_PLAYING frame in story mode, after the rules (main.c): the goal's counters, success and failure.
void story_play(void) BANKED {
    uint8_t c, b, left;
    c = sfx_count[SFX_CATCH] - st_last_catch; st_last_catch += c; story_catches += c;
    b = sfx_count[SFX_BREAK] - st_last_break; st_last_break += b; story_breaks += b;
    if (life_lost && !b) story_taps++;           // a life lost with no glass broken: a patron reached the tap
    if (((story_goal.flags & F_NO_TAP) && story_taps) || ((story_goal.flags & F_NO_BREAK) && story_breaks)) {
        if (life_lost) { lives = 0; game_over = 1; hud_dirty |= HUD_LIVES; prep_hud(); }   // the freeze plays out, then
        // enter_game_over: story_fail
        return;
    }
    if (life_lost) return;
    if (story_timer && !intro_timer) {
        if (!--story_timer) { story_fail(); return; }
        c = (uint8_t)((story_timer + 59) / 60);
        if (c != st_secs) { st_secs = c; hud_goal(); }
    }
    switch (story_goal.type) {
    case G_SERVE: c = served; break;
    case G_CATCH: c = story_catches; break;
    default:
        if (level_clear) story_win();
        return;
    }
    left = c >= story_goal.count ? 0 : story_goal.count - c;
    if (left != story_left) { story_left = left; hud_goal(); }
    if (!left) story_win();
}

// One frame of GS_STORY (a cut-scene, or TRY AGAIN) or GS_GOAL. 1: the screen was redrawn (LCD off): skip the rest.
uint8_t story_update(uint8_t pressed) BANKED {
    story_t++;
    switch (story_phase) {
    case SP_GOAL:
        if ((pressed & (J_A | J_START)) || story_t >= GOAL_FRAMES) {
            goal_banner_off();
            story_phase = SP_PLAY;
            game_state = GS_PLAYING;
        }
        return 0;
    case SP_FAIL:
        if ((pressed & (J_A | J_START)) || story_t >= FAIL_FRAMES) { chapter_start(); return 1; }
        return 0;
    case SP_SCENE:
        break;
    default:
        return 0;
    }
    if (pressed & J_START) { scene_done(); return 1; }
    if (story_swap) swap_frame();
    if (story_typed < 54) {
        if (pressed & (J_A | J_B)) type_all();
        else type_frame();
        return 0;
    }
    if ((pressed & (J_A | J_B)) && !story_swap) {
        if (++story_page >= story_hdr.pages) { scene_done(); return 1; }
        page_begin(0);
    }
    return 0;
}
