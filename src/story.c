// Story mode (M11b): "The Golden Spigot" (docs/story.md). Cut-scenes, the chapter flow, the chapter goals.
//
// Flow: title STORY -> INTRO -> per chapter c (0..9): PRE scene -> the chapter's steps (build/story.h STORY_STEPS:
// Opening shift, Happy hour, the mini-game slot, Last call, the boss slot; a step marked STEP_SKIP is not built yet
// and passed over) -> the POST scene -> the next chapter; after chapter 10's POST scene FINALE, CREDITS, the title.
// A shift is the venue's level with that shift's goal, speeds and arrival pattern (a banner first, GS_GOAL); on
// success SHIFT CLEAR (CHAPTER CLEAR after the last step), the progress saved (SRAM, save.c: chapters cleared + the
// furthest step reached), the next step. Lives (owner's rule): 3 per venue, set when its Opening shift starts and
// carried through its shifts (a gold medal in the venue's mini-game: +1, at most MAX_LIVES); losing the last one shows
// TRY AGAIN and restarts the venue at its Opening shift's banner (no PRE scene) with 3 lives. A strict rule (chapter
// 2: a patron at the tap, 8: a broken glass) costs 2 lives instead of 1 ("2 LIVES LOST", the two mugs blink during the
// freeze). A timed goal's clock running out costs a life and retries that shift (the venue when it was the last).
// CONTINUE on the title starts the chapter not cleared over: its Opening banner when one of its steps was reached,
// else its PRE scene (lives are not saved). The score carries on through a lost life and a timed goal's retry, but
// starts from 0 again when the lives run out (TRY AGAIN, the venue again: owner 2026-10-11), so a story score is one
// run with no game over; when the credits end it goes into the STORY top 5 (initials, the table; not from a
// debug-select run).
//
// ARCADE (the three modes, owner 2026-10-11: PLAY > ARCADE, story_arc = 1, play_mode MODE_ARCADE) runs this same
// engine with arcade rules: no scene, no portrait, no story text, nothing saved or unlocked (save_lock); the venues in
// story order, each its playable steps (shifts, the mini-game, the boss fight as they are built; STEP_SKIP passed over)
// with the story's rules (goals, perfect pour, strict rules, the mosh pit, the fast band). Lives: 3 for the whole run
// (venue_start leaves them), extra lives by score (main.c add_score: 20,000, then every 40,000; at most MAX_LIVES), a
// gold medal +1 as in the story. Losing the last one is the normal GAME OVER -> initials -> the ARCADE top 5 (a timed
// goal's clock costs a life and retries the shift while lives are left). After a venue's last step, VENUE CLEAR, then a
// bonus round (rotating as before: bonus.c) and the next venue (arcade_next); after the space lounge the saloon again,
// harder (level.c's loop rule: level = (loop - 1) * 10 + chapter + 1, so start_level's loop maths and the HUD's L nn
// follow; the loops' difficulty stops growing after loop 4), its first banner "LOOP n" for LOOP_FRAMES (SP_LOOP).
//
// Cut-scene ("hybrid lighter" style): the venue's stage + bar rows as the backdrop (no patrons), the Spigoteer's
// normal sprite at bar 1's tap, the scene title on the HUD row, a framed speaker portrait above a full-width text
// box (rows 13-17: panel, 3 lines of 18 characters at columns 1-18, panel). The NARRATOR has no portrait: the box shows
// the small golden spigot where a name would be. INTRO, FINALE and CREDITS show a picture slot instead of a venue
// (tools/gen_story.py: placeholders for now). The text types on, one character a frame. Buttons: A or B shows the
// rest of the page at once, then the next page; START skips the rest of the scene. A page may have text variants
// (docs/story.md "SPEAKER IF CONDITION"): story_page_get shows the first whose condition bit is set in story_conds.
//
// The portrait slot is data-driven (build/story_portraits.c, from assets/story/portraits.json): size up to 7x7 tiles,
// position, up to 3 CGB BG palettes (slots 2-4) and an optional OBJ overlay (OAM 4.., OBJ tiles OBJ_DANCER.., palettes
// 3, 4, 6, 7; flag bit 5: a CGB-only accent, hidden on DMG). A picture whose bottom row is 12 stands on the text box
// (the box's top panel is its frame's bottom edge: the approved 56x56 portraits). Each page names a portrait id: the
// speaker's own, or one of his variants over a range of pages (portraits.json "variants": the Spigoteer's cozy, Dregs's
// apology), resolved by tools/gen_story.py. All the scene's portraits are loaded when it starts (LCD off); a portrait
// change rewrites only the tile map: the old frame is wiped back to the backdrop (a WRAM copy of rows 0-12), then the
// palettes change (at the top of a frame, in VBlank) and the new frame is drawn, 2 rows a frame through the VBlank queue.
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"
#include "music.h"
#include "bonus.h"
#include "story.h"
#include "mg.h"

BANKREF_EXTERN(art_tiles)
extern const uint8_t bar_tiles[];
extern uint8_t overlay_on, level, game_over, state_timer, score_digits[6], new_rank;
extern uint32_t score;

#define SCENE_BAR        1         // the Spigoteer stands at this bar's tap during a cut-scene
#define BOX_ROW         13         // the text box: panel row 13, text rows 14-16, panel row 17
#define BOX_TEXT_ROW    14
#define SWAP_ROWS        2         // portrait rows queued per frame (map + attributes: <= 36 bytes)
#define OAM_OVERLAY      4         // the portrait's OBJ overlay: OAM 4..
#define GOAL_FRAMES    180         // the goal banner stays 3 s (or until A / START)
#define ARC_LOOP_FRAMES 120        // ARCADE: "LOOP n" before a new loop's first goal banner (as the old arcade's LOOP_FRAMES)
#define FAIL_FRAMES    150         // TRY AGAIN
#define GOAL_WY        BANNER_WY   // the goal banner: window rows 0-4 (map rows 32-36): panel, 3 lines, panel
#define GOAL_LYC       (BANNER_WY + 38)
#define HUD_GOAL_COL    12         // story HUD: goal letter + 2 digits (what is left) at 12-14, timer 'T' + 3 digits at 16-19

enum { SP_OFF, SP_SCENE, SP_GOAL, SP_PLAY, SP_FAIL, SP_OUTRO, SP_LOOP };   // SP_OUTRO: a boss satisfied (boss.c);
                                                                          // SP_LOOP: ARCADE's "LOOP n" before a goal banner
enum { SW_IDLE, SW_OUT, SW_PAL, SW_IN };

// ---- state (globals => symbols the tests read) ----
uint8_t  story_on;                 // 1: story mode (main.c, main_cold.c)
uint8_t  play_mode;                // MODE_* (game.h): set by whatever starts a game
uint8_t  story_arc;                // 1: ARCADE on this engine (see the top of the file)
uint8_t  arc_loop;                 // ARCADE: the pass through the ten venues (1, 2, ...)
uint8_t  arc_banner;               // ARCADE: the next shift_start shows "LOOP n" first (a new loop's first shift)
uint8_t  story_phase;              // SP_*
uint8_t  story_scene;              // SC_* (build/story.h)
uint8_t  story_page;               // page of the scene on screen
uint8_t  story_chapter;            // 0..9
uint8_t  story_typed;              // characters of the page typed so far (54: the whole page)
uint8_t  story_spk;                // speaker of the page (the name tag)
uint8_t  story_pid;                // portrait of the page: the speaker's id, or a variant (build/story.h, portraits.json)
uint8_t  story_cur;                // portrait id on screen (255: none)
uint8_t  story_swap;               // SW_*: a portrait change in progress
uint8_t  story_catches, story_breaks, story_taps;   // this attempt: empties caught, glasses broken, patrons at the tap
uint8_t  story_left;               // what is left of the goal's count (HUD)
uint16_t story_timer;              // frames left of a timed goal (0: none / out)
uint8_t  story_fails;              // goal failures so far (tests)
uint8_t  story_twist;              // the shift's twist bits (TWIST_*, build/story.h; 0 none; a boss fight 0)
uint8_t  story_step;               // the step of the chapter's sequence being played (0..STORY_STEPS-1)
uint8_t  story_shift;              // the shift being played: 0 opening, 1 happy hour, 2 last call
uint8_t  story_pen;                // lives the strict rule just cost (2, or 1 from the last one): the freeze's blink
uint8_t  story_restarts;           // venue restarts so far (tests)
uint8_t  story_conds;              // page text conditions (COND_*, build/story.h): which pages' variants show
uint8_t  pat_pos, pat_buf[STORY_PAT_MAX];   // the shift's arrival pattern (patrons.c pat_len / pat_bar): position, entries
uint16_t pat_wait[4];              // frames per wait code: the interval, PAT_SHORT, twice, four times the interval
scene_hdr_t story_hdr;
goal_t   story_goal;

static uint8_t page_buf[56];      // speaker, 3 x 18 characters, portrait id
static uint8_t box_tiles[3][18];
static uint8_t tag_row[20];
static uint8_t hud_buf[8];
static uint8_t win_rows[5][20];
// the backdrop of rows 0-12 (map, then attributes): used only while a cut-scene shows, and rewritten from scratch by
// every scene_enter, so the mini-games lay their state over it (src/mg.h union mg_ram)
#if STORY_PIC_ROWS * 40 != STORY_SCRATCH
#error "story_scratch: STORY_SCRATCH (game.h) must be the backdrop buffer's size"
#endif
uint8_t story_scratch[STORY_SCRATCH];
#define bd_map  story_scratch
#define bd_attr (story_scratch + STORY_PIC_ROWS * 20)
uint8_t story_unskip;              // test hook: bit s set = step s of every chapter is played even if marked STEP_SKIP
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

// pt (fetched) -> its framed rectangle in pt_map / pt_attr; new cx..ch. A picture whose bottom is the row above the
// text box stands on it: the box's top panel is the frame's bottom edge, so the frame has no bottom row.
static void compose_portrait(uint8_t k) {
    uint8_t w = pt.w + 2, h = pt.h + 2, x, y, i = 0, t, a;
    if (pt.y + pt.h == BOX_ROW) h--;
    for (y = 0; y < h; y++)
        for (x = 0; x < w; x++, i++) {
            a = BGPAL_HUD;
            if (y == 0)          t = x == 0 ? ST_FRAME_TL : x == w - 1 ? ST_FRAME_TR : ST_FRAME_T;
            else if (y == pt.h + 1) t = x == 0 ? ST_FRAME_BL : x == w - 1 ? ST_FRAME_BR : ST_FRAME_B;
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
        o->y = (e[3] & 0x20) && !is_cgb ? 0 : pt.y * 8 + e[0] + 16;   // bit 5: a CGB-only accent (DMG shows the BG)
        o->x = pt.x * 8 + e[1] + 8;
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

// LCD on (lcd 0) or off (1): the page's box cleared, its name tag; a portrait change starts if the page's portrait
// differs (another speaker, or the same speaker's variant: the Spigoteer's cozy, Dregs's apology)
static void page_begin(uint8_t lcd_off) {
    uint8_t r;
    story_page_get(story_scene, story_page, story_conds, page_buf);   // its text: a variant when its condition holds
    story_spk = page_buf[0];
    story_pid = page_buf[55];
    story_typed = 0;
    for (r = 0; r < 3; r++) fill(box_tiles[r], TILE_HUD_BLANK, 18);
    tag_build();
    if (lcd_off) {
        for (r = 0; r < 3; r++) set_bkg_tiles(1, BOX_TEXT_ROW + r, 18, 1, box_tiles[r]);
        set_bkg_tiles(0, BOX_ROW, 20, 1, tag_row);
        portrait_now(story_pid);
        return;
    }
    for (r = 0; r < 3; r++) vq_add(0, box_tiles[r], 1, BOX_TEXT_ROW + r, 18);
    vq_add(0, tag_row, 0, BOX_ROW, 20);
    if (story_pid == story_cur || (spk_index(story_pid) == 255 && story_cur == 255)) return;
    sw_next = story_pid;
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
    music_fast = 0;                              // (a scene plays the venue's tune at its own pace)
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
    if (story_goal.type >= G_CLEAR) return;     // (a clear goal has no counter; a boss fight shows his meter: boss.c)
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

// The shift's speeds and arrivals on top of the level row (after the level load): walkers (hurried ones too) and the
// spawn interval scaled by the shift's percentages, the arrival pattern (patrons.c) with its waits, a clear goal's quota.
static void shift_pace(void) {
    uint16_t v;
    if (story_goal.type != G_CLEAR) quota = 255; // serve / catch goals: patrons keep coming until the goal is met
    else if (story_goal.quota) quota = story_goal.quota;
    patron_speed = (uint8_t)(((uint16_t)patron_speed * story_goal.walk) / 100);
    if (hurry_speed) hurry_speed = patron_speed + (patron_speed >> 1);   // (level.c: 1.5x from level 3)
    v = (uint16_t)(((uint16_t)spawn_interval * story_goal.spawn) / 100);
    spawn_interval = v; spawn_timer = v;
    pat_len = story_pattern_get(story_goal.pattern, pat_buf);
    pat_pos = 0; pat_bar = pat_buf[0] & 3;
    pat_wait[0] = v; pat_wait[1] = PAT_SHORT; pat_wait[2] = v << 1; pat_wait[3] = v << 2;
}

// After a patron spawned under an arrival pattern (patrons.c, only then): the frames to the next one (the entry's
// wait code), the pattern's next bar.
uint16_t pat_done(void) BANKED {
    uint8_t e = pat_buf[pat_pos];
    if (++pat_pos == pat_len) pat_pos = 0;
    pat_bar = pat_buf[pat_pos] & 3;
    return pat_wait[e >> 4];
}

static const char *const shift_name[STORY_SHIFTS] = STORY_SHIFT_NAMES;
static const char boss_word[] = "BOSS";

// One shift of the chapter: its goal banner over the venue's level (LCD off, then on), GS_GOAL.
static void shift_start(void) {
    uint8_t i;
    if (boss_on) boss_goal((uint8_t *)&story_goal);   // a boss fight: his banner lines, the regulars' pace (boss.c)
    else story_goal_get(story_chapter, story_shift, (uint8_t *)&story_goal);
    story_twist = story_goal.twist;
    DISPLAY_OFF;
    // the goal banner in the window (map rows 32-36): panel, the shift's name alone (OPENING SHIFT, HAPPY HOUR, LAST
    // CALL, or BOSS; owner 2026-10-11: no chapter number), the two goal lines, panel
    fill(win_rows[0], TILE_PANEL_TOP, 20);
    centre(win_rows[1], boss_on ? boss_word : shift_name[story_shift]);
    centre(win_rows[2], story_goal.line1);
    centre(win_rows[3], story_goal.line2);
    fill(win_rows[4], TILE_PANEL_BOT, 20);
    for (i = 0; i < 5; i++) vram_put(0, 32 + i, win_rows[i], 20);   // (map rows 32.. = the window's 0x9C00 map)
    if (arc_banner) {                            // ARCADE, a new loop: "LOOP n" alone first; SP_LOOP puts the goal back
        char t[8] = "LOOP ";
        i = arc_loop > 99 ? 99 : arc_loop;
        if (i >= 10) { t[5] = '0' + i / 10; t[6] = '0' + i % 10; } else t[5] = '0' + i;
        fill(row_buf, TILE_HUD_BLANK, 20);
        vram_put(0, 33, row_buf, 20); vram_put(0, 35, row_buf, 20);
        centre(row_buf, t);
        vram_put(0, 34, row_buf, 20);
    }
    if (is_cgb) {
        VBK_REG = VBK_BANK_1;
        fill(row_buf, BGPAL_HUD, 20);
        for (i = 0; i < 5; i++) vram_put(0, 32 + i, row_buf, 20);
        VBK_REG = VBK_BANK_0;
    }
    level = story_chapter + 1;                   // (lives: set by venue_start, carried from shift to shift)
    if (story_arc) level += (arc_loop > 9 ? 8 : arc_loop - 1) * 10;   // ARCADE: the loop's row (start_level's loop maths)
    pour_load(story_chapter);                    // the perfect pour's frames and cue (LCD off; the venue = the chapter)
    music_fast = (story_twist & TWIST_FAST_TUNE) != 0;   // the twist: the band plays faster (before the tune starts)
    enter_level_screen();                        // the venue's level (row level - 1), LCD on again, PLAYING
    mosh_set(story_twist, story_goal.pad);       // the twist: the mosh pit (src/mosh.c), with this shift's limit; else off
    shift_pace();
    if (boss_on) boss_begin();                   // the regulars' bars (never his), no tips, his face and meter on the HUD
    story_catches = story_breaks = story_taps = 0;
    st_last_catch = sfx_count[SFX_CATCH]; st_last_break = sfx_count[SFX_BREAK];
    story_left = story_goal.count;
    st_secs = story_goal.secs;
    story_timer = (uint16_t)story_goal.secs * 60;
    hud_goal();
    overlay_on = 1;
    LYC_REG = GOAL_LYC;
    story_phase = arc_banner ? SP_LOOP : SP_GOAL; story_t = 0;
    arc_banner = 0;
    game_state = GS_GOAL;
}

static void goal_banner_off(void) {
    fill(win_rows[2], TILE_PANEL_BOT, 20);       // map row 34 is the normal banner's bottom panel again
    vq_add(0, win_rows[2], 0, 34, 20);
    LYC_REG = BANNER_LYC;
    overlay_on = 0;
}

// ---- the chapter's steps ----------------------------------------------------------------------------------------
// the first step from s the engine can play (STORY_STEPS: none left in the chapter)
static uint8_t next_step(uint8_t s) {
    while (s < STORY_STEPS && (story_step_get(story_chapter, s) & STEP_SKIP) && !((story_unskip >> s) & 1)) s++;
    return s;
}

// story_step (playable) begins, by kind: the chapter's mini-game (src/mg.c; its result goes on with story_level_done,
// whatever the medal: mini-games never block the story), the venue's boss fight (src/boss.c: boss_set here, then the
// level as a shift with his banner and pace; a lost fight restarts the venue as a shift does), or a shift. A slot not
// built yet is STEP_SKIP in the data (gen_story NOT_BUILT / BOSSES_BUILT) and never reaches here.
static void step_start(void) {
    uint8_t s = story_step_get(story_chapter, story_step);
    boss_set((s & STEP_KIND) == STEP_BOSS ? story_chapter : BOSS_NONE);   // the venue's boss fight (src/boss.c), or none
    if ((s & STEP_KIND) == STEP_MINI) { mg_enter(story_chapter, MG_STORY); return; }
    story_shift = s & STEP_INDEX;
    shift_start();
}

// the venue (chapter) from its first playable step, with 3 lives (a new chapter, a lost last life, CONTINUE): a new
// venue attempt, so its page text conditions start over
static void venue_start(void) {
    if (!story_arc) lives = START_LIVES;         // (ARCADE: the run's lives carry on)
    story_conds &= ~COND_GLASS_BROKEN;           // a new attempt at the venue: no glass broken in it yet
    story_step = next_step(0);
    step_start();
}

static void chapter_done(void) {                 // every step done: saved as cleared, the POST scene
    if (story_arc) { bonus_enter(); game_state = GS_BONUS; return; }   // ARCADE: the bonus round (then arcade_next)
    story_save(story_chapter + 1, 0);
    scene_enter(SC_POST_SALOON + 2 * story_chapter);
}

// ---- entry points --------------------------------------------------------------------------------------------
// From the title: a new story (cont 0) or CONTINUE (cont 1: the first chapter not cleared starts over, at its Opening
// banner when a step of it was reached (story_reached > 0), else at its PRE scene)
// a new run on this engine: arc 0 the story, 1 ARCADE
static void run_begin(uint8_t arc) {
    uint8_t i;
    story_on = 1; story_fails = 0; story_arc = arc; play_mode = arc ? MODE_ARCADE : MODE_STORY;
    extra_at = arc ? EXTRA_FIRST : 0;            // extra lives by score: ARCADE only
    score = 0;
    for (i = 0; i < 6; i++) score_digits[i] = 0;
    lives = START_LIVES; bonus_round = 0; game_over = 0;
    arc_loop = 1; arc_banner = 0;
}

void story_begin(uint8_t cont) BANKED {
    run_begin(0);
    if (cont && (story_progress || story_reached) && story_progress < STORY_CHAPTERS) {
        story_chapter = story_progress;
        story_scene = SC_PRE_SALOON + 2 * story_chapter;
        if (!story_reached) scene_enter(story_scene);
        else venue_start();
    } else {
        story_chapter = 0;
        scene_enter(SC_INTRO);
    }
}

// PLAY > ARCADE: the saloon's first playable step, 3 lives, nothing saved (save_lock; title_enter clears it)
void arcade_begin(void) BANKED {
    run_begin(1);
    save_lock = 1;
    story_conds = 0;
    story_chapter = 0;
    venue_start();
}

// ARCADE: GS_BONUS is over (main.c): the next venue, or after the last one the saloon again, a loop harder
void arcade_next(void) BANKED {
    if (++story_chapter >= STORY_CHAPTERS) {
        story_chapter = 0;
        if (arc_loop < 255) arc_loop++;
        arc_banner = 1;
    }
    venue_start();
}

// main.c add_score: the score reached extra_at (ARCADE, CLASSIC): a life (owner: 20,000, then every 40,000; at most
// MAX_LIVES, what the HUD shows; past it only the next threshold moves on). add_score's prep_hud draws it.
void extra_life(void) BANKED {
    extra_at += EXTRA_EVERY;
    if (lives < MAX_LIVES) { lives++; hud_dirty |= HUD_LIVES; SFX(SFX_EXTRA); }   // its cue: music.c s_extra
}

static void scene_done(void) {
    uint8_t s = story_scene;
    uint8_t aaa[3];
    if (s == SC_CREDITS) {                       // the end: the story's score into the STORY top 5 (initials, the table)
        story_on = 0; story_phase = SP_OFF;
        if (save_lock) { title_enter(); return; }   // (a debug-select run: nothing saved)
        score_tbl = MODE_STORY;
        aaa[0] = aaa[1] = aaa[2] = 'A';
        new_rank = top_insert(score, aaa);
        if (new_rank < TOP_N) hi_save();
        scores_after_game();
        return;
    }
    if (s == SC_FINALE) { scene_enter(SC_CREDITS); return; }
    if (s == SC_INTRO) { scene_enter(SC_PRE_SALOON); return; }
    if (!((s - SC_PRE_SALOON) & 1)) { venue_start(); return; }     // a PRE scene: the chapter
    if (story_chapter + 1 < STORY_CHAPTERS) {                       // a POST scene: the next chapter's PRE
        story_chapter++;
        scene_enter(SC_PRE_SALOON + 2 * story_chapter);
    } else scene_enter(SC_FINALE);
}

// GS_LEVEL_CLEAR is over (main.c): the progress saved (the furthest step reached in the chapter, even one not built
// yet, for Practice: a venue restart never lowers it), the next playable step, or the chapter's POST scene
void story_level_done(void) BANKED {
    uint8_t n = story_step + 1, s = next_step(n);
    boss_set(BOSS_NONE);                         // (a won boss fight is over: the POST scene has no boss)
    if (s >= STORY_STEPS) { chapter_done(); return; }
    story_save(story_chapter, story_progress == story_chapter && story_reached > n ? story_reached : n);
    story_step = s;
    step_start();
}

// the goal failed: TRY AGAIN over the frozen level, then the venue again (no lives left: from enter_game_over, or
// the clock's last life) or that shift (the clock ran out, lives left)
void story_fail(void) BANKED {
    show_overlay("TRY AGAIN");
    music_play(TUNE_OVER);
    story_fails++;
    story_phase = SP_FAIL; story_t = 0;
    game_state = GS_STORY;
}

static void story_win(void) {
    enter_level_clear();                         // (its LEVEL CLEAR banner, the bonus, the jingle, GS_LEVEL_CLEAR)
    show_overlay(next_step(story_step + 1) >= STORY_STEPS ? (story_arc ? "VENUE CLEAR" : "CHAPTER CLEAR") : "SHIFT CLEAR");
}

// Every GS_PLAYING frame in story mode, after the rules (main.c): the goal's counters, success and failure.
void story_play(void) BANKED {
    uint8_t c, b, left;
    c = sfx_count[SFX_CATCH] - st_last_catch; st_last_catch += c; story_catches += c;
    b = sfx_count[SFX_BREAK] - st_last_break; st_last_break += b; story_breaks += b;
    if (life_lost) {
        if (!b) story_taps++;                    // a life lost with no glass broken: a patron reached the tap
        else story_conds |= COND_GLASS_BROKEN;   // a broken glass (chapter 8's strict rule): POST_TEAHOUSE's text
        // the strict rule (2: a patron at the tap, 7: a broken glass) costs a second life: "2 LIVES LOST", the two
        // mugs blink during the freeze (story_life_frame); none left: the freeze plays out, then enter_game_over ->
        // story_fail restarts the venue
        if (((story_goal.flags & F_NO_TAP) && !b) || ((story_goal.flags & F_NO_BREAK) && b)) {
            story_pen = 1;
            if (lives) { lives--; story_pen = 2; }
            if (!lives) game_over = 1;
            hud_dirty |= HUD_LIVES; prep_hud();
            show_overlay("2 LIVES LOST");
        }
        return;
    }
    if (boss_on) {                               // a boss fight: no counter, no clock; his meter empty -> the outro
        if (boss_frame()) { story_phase = SP_OUTRO; story_t = 0; game_state = GS_STORY; }
        return;
    }
    if (story_timer && !intro_timer) {
        if (!--story_timer) {                    // time up: a life, and the shift again (the venue: it was the last)
            if (lives) lives--;
            hud_dirty |= HUD_LIVES; prep_hud();
            if (story_arc && !lives) { game_over = 1; enter_game_over(); return; }   // ARCADE: that was the last
            story_fail();
            return;
        }
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
        if ((pressed & (J_A | J_START)) || story_t >= FAIL_FRAMES) {
            if (lives) shift_start();
            else {                               // out of lives: the venue again, the score from 0 (owner 2026-10-11)
                story_restarts++;
                score = 0;
                for (story_t = 0; story_t < 6; story_t++) score_digits[story_t] = 0;
                venue_start();
            }
            return 1;
        }
        return 0;
    case SP_LOOP:                                // ARCADE: "LOOP n", then the goal's lines back, one row a frame
        if ((pressed & (J_A | J_START)) && story_t < ARC_LOOP_FRAMES) story_t = ARC_LOOP_FRAMES;
        if (story_t >= ARC_LOOP_FRAMES) {
            pressed = story_t - ARC_LOOP_FRAMES;     // (0..2: the row)
            vq_add(0, win_rows[1 + pressed], 0, 33 + pressed, 20);
            if (pressed == 2) { story_phase = SP_GOAL; story_t = 0; }
        }
        return 0;
    case SP_OUTRO:                               // a boss satisfied: his outro, then CHAPTER CLEAR as a shift's
        if (boss_outro(story_t)) story_win();
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

// Every GS_LIFE_LOST frame in story mode (main.c, before the freeze's frame count): after a strict rule's penalty the
// lost mugs blink together (8 frames on, 8 off) until the freeze's last frame puts the HUD back.
void story_life_frame(void) BANKED {
    uint8_t t, n;
    if (!story_pen) return;
    if (state_timer + 1 >= LIFE_FREEZE_FRAMES) { story_pen = 0; prep_hud(); hud_dirty |= HUD_LIVES; return; }
    if (state_timer & 7) return;
    t = (state_timer & 8) ? TILE_HUD_MUG : TILE_HUD_BLANK;
    for (n = lives + 1; n <= lives + story_pen; n++) lives_tiles[n > 3 ? 0 : n] = t;
    hud_dirty |= HUD_LIVES;
}

// The mini-game framework calls this on a gold medal (owner: +1 life, at most MAX_LIVES; the HUD's 4th mug sits at
// column 8, left of the three, and is the first to go).
void story_bonus_life(void) BANKED {
    if (lives < MAX_LIVES) lives++;
    prep_hud();
    hud_dirty |= HUD_LIVES;
}

#ifdef DEBUG_MENU
// The debug select in story mode (src/debug.c): chapter ch at position pos (0 its PRE scene, 1..STORY_STEPS the step
// pos - 1, STORY_STEPS + 1 its POST scene) with the story's rules: a fresh score, the venue's lives as venue_start sets
// them (from any step), its goals. arc 1 (the ARCADE box: a step only): the same as an ARCADE run from there (loop 1).
// debug.c has set save.c's save_lock: nothing of the run is saved.
void story_debug_start(uint8_t ch, uint8_t pos, uint8_t arc) BANKED {
    run_begin(arc);                              // (arc: the ARCADE box, its run as ARCADE plays it from that step)
    story_conds = 0;
    story_chapter = ch;
    if (pos == 0) scene_enter(SC_PRE_SALOON + 2 * ch);
    else if (pos > STORY_STEPS) scene_enter(SC_POST_SALOON + 2 * ch);
    else { story_step = pos - 1; step_start(); }
}
#endif
