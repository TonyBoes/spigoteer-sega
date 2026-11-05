// Story mode (M11b): "The Golden Spigot" (docs/story.md). Cut-scenes, the chapter flow, the chapter goals.
//
// Flow: title STORY -> INTRO -> per chapter c (0..9): PRE scene -> the chapter's steps (build/story.h STORY_STEPS:
// Opening shift, Happy hour, the mini-game slot, Last call; a step marked STEP_SKIP is not built yet and passed over) -> the
// POST scene -> the next chapter. The boss is no step (owner 2026-10-17): Last call's serve quota turns that level into the venue's
// boss fight in place (shift_won, boss_in_place), and his defeat is the venue's clear; after chapter 10's POST scene FINALE_A, the Pour-Off (src/po.c, a mini-game on the framework, won to go on), FINALE_B, CREDITS, the title.
// A shift is the venue's level with that shift's goal, speeds and arrival pattern (a banner first, GS_GOAL); on
// success SHIFT CLEAR (CHAPTER CLEAR after the last step), the progress saved (SRAM, save.c: chapters cleared + the
// furthest step reached), the next step. Lives (owner's rule): 3 per venue, set when its Opening shift starts and
// carried through its shifts (a gold medal in the venue's mini-game: +1, at most MAX_LIVES); losing the last one shows
// TRY AGAIN and restarts the venue at its Opening shift's banner (no PRE scene) with 3 lives. A strict rule (chapter
// 2: a patron at the tap, 8: a broken glass) costs 2 lives instead of 1 ("2 LIVES LOST", the two mugs blink during the
// freeze). A timed goal's clock running out costs a life and retries that shift (the venue when it was the last).
// CONTINUE on the title starts the chapter not cleared over: its Opening banner when one of its steps was reached,
// else its PRE scene (lives are not saved: 3; the score is the one the venue was entered with, save.c venue_score_put). The score carries on through a lost life and a timed goal's retry, but
// goes back to the venue's start score when the lives run out (TRY AGAIN, the venue again, as CONTINUE: owner 2026-10-14,
// no incentive to quit before dying; a debug-select run has none saved: 0); when the credits end it goes into the STORY top 5 (initials, the table; not from a
// debug-select run).
//
// ARCADE (the three modes, owner 2026-10-11: PLAY > ARCADE, story_arc = 1, play_mode MODE_ARCADE) runs this same
// engine with arcade rules: no scene, no portrait, no story text, nothing saved or unlocked (save_lock); the venues in
// story order, each its playable steps (shifts, the mini-game; Last call goes on into the boss fight; STEP_SKIP passed over)
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
// the small golden spigot where a name would be. INTRO, FINALE_A, FINALE_B and CREDITS show a full-screen picture instead of a venue
// (assets/story/pictures, build/story_pictures.c: its tiles at BG ids 0-35 and above the scene's one portrait slot; a
// speaker's tiles are streamed into that slot when he comes on; INTRO page 5 switches pictures behind a white flash: the
// picture then shows the spigot gone and the fountain stopped, and the ten pieces, as OBJ sprites where the spigot was,
// fly off the screen while a trail of dots fades in the sky behind each (PB_T, story_burst_step); a gold burst star (BG cells over the spigot) pulses meanwhile and dies down, then sparks spray off the stump in short bursts for the rest of the scene (story_burst_crackle). The text types on, one character a frame. Buttons: A or B shows the
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
#include "scratch.h"
#include "music.h"
#include "bonus.h"
#include "story.h"
#include "mg.h"
#include "rush.h"

BANKREF_EXTERN(art_tiles)
extern const uint8_t bar_tiles[];
extern uint8_t overlay_on, level, game_over, state_timer, score_digits[6], new_rank;
extern uint32_t score;
// Dregs's late-arrival gags (src/dgag.c): their state is win_rows[0] (the goal banner's buffer, unused in a scene); [4] 1 = a gag is running
void dg_load(uint8_t *st, uint8_t v) BANKED;
void dg_page(uint8_t *st, uint8_t scene, uint8_t prev, uint8_t spk) BANKED;
void dg_frame(uint8_t *st) BANKED;
void cam_load(uint8_t s) BANKED;            // story cameos: the bosses and the UFO beam-up (src/cameo.c)
void cam_page(uint8_t s, uint8_t page) BANKED;
void cam_frame(void) BANKED;

#define G_BOSS           3         // story_goal.type of a boss fight (boss.c), and after Last call's quota while the bars empty (shift_won)
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
#define HUD_GOAL_COL    11         // story HUD: the goal's icon + 2 digits (what is left) at 11-13, a timer's hourglass + 2 digits at 17-19

enum { SP_OFF, SP_SCENE, SP_GOAL, SP_PLAY, SP_FAIL, SP_OUTRO, SP_LOOP, SP_RUSH, SP_CREDITS, SP_MAP };   // SP_OUTRO: a boss satisfied
                                                     // (boss.c); SP_LOOP: ARCADE's "LOOP n" before a goal banner;
                                                     // SP_RUSH: a BOSS RUSH screen (src/rush.c rush_update)
typedef char sp_rush_is_game_h[(SP_RUSH == STORY_PHASE_RUSH && SP_CREDITS == STORY_PHASE_CREDITS && SP_MAP == STORY_PHASE_MAP) ? 1 : -1];
enum { SW_IDLE, SW_OUT, SW_PAL, SW_IN, SW_TILES };   // SW_TILES: picture scenes only (the portrait slot's tiles stream in)

// vq_entry_t of src/render.c (the VBlank copy list): tile data goes to a raw VRAM address, which vq_add cannot express
typedef struct { uint8_t n, bank; const uint8_t *src; uint8_t *dst; uint8_t pad[2]; } vq_entry_t;
extern vq_entry_t vq[];

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
uint8_t win_rows[5][20];            // (global for the tests: [0][4] is Dregs's gag state, src/dgag.c)
// the backdrop of rows 0-12 (map, then attributes): used only while a cut-scene shows, and rewritten from scratch by
// every scene_enter, so the mini-games lay their state over it (src/mg.h union mg_ram)
#if STORY_PIC_ROWS * 40 != STORY_SCRATCH
#error "story_scratch: STORY_SCRATCH (game.h) must be the backdrop buffer's size"
#endif
uint8_t story_scratch[STORY_SCRATCH];
#define bd_map  story_scratch
#define bd_attr (story_scratch + STORY_PIC_ROWS * 20)
// A picture scene (INTRO, FINALE_A, FINALE_B, CREDITS: story_hdr.venue == 255) keeps no backdrop copy: the picture is in ROM
// (story_pic_row), so story_scratch is free there and holds, no new WRAM global:
#define PS_FX    (story_scratch[0])                  // the picture switch's step (0: none); read only when swpage != 0
#define PS_ROWS  (story_scratch + 2)                 // a wipe's two rows: per row w tiles then w attributes (<= 18)
#define PS_TILES (story_scratch + 40)                // a swap's streamed tiles: PS_BURST x 16 bytes
#define PS_BURST 3                                   // tiles per frame (48 bytes through the VBlank list: 10 of its 17 DIV ticks)
#define PS_PALS  ((uint16_t *)(story_scratch + 40 + PS_BURST * 16))   // the fade: 4 picture palettes + the HUD's (20 words)
#define PS_OUT   ((uint16_t *)(story_scratch + 40 + PS_BURST * 16 + 40))   // the fade step to write next (20 words)
#define PS_W     (story_scratch[1])                  // its w: 3 white .. 0 as drawn (also what DMG's BGP is set from)
#define PB_T     (story_scratch[168])                // the INTRO's explosion: frames since the flash (255: none running)
#define PW_AT    300                                 // the fountain flowing (story_water), above the burst's bytes:
#define PW_T     (story_scratch[PW_AT])              // frames since the picture came up (mod 256)
#define PW_PH    (story_scratch[PW_AT + 1])          // the jets' phase now (0 .. STORY_WATER_PHASES - 1; 0 = the picture as drawn)
#define PW_DUE   (story_scratch[PW_AT + 2])          // bit j: jet j (0 left, 1 right) still shows an older phase
#define PW_BUF   (story_scratch + PW_AT + 3)         // a jet's three tiles (48 bytes), then their VRAM addresses (6), on their way through the list
#define PW_END   (PW_AT + 3 + 54)
#define SK_C     (story_scratch[PW_END])             // the clouds drifting (Color, story_sky): px right of their place in the picture
#define SK_ON    (story_scratch[PW_END + 1])         // 0 none or hidden, 1 drifting, 2 to come on this frame, 3 waiting for the switch's fade-in
#define SK_BUF   (story_scratch + PW_END + 2)        // the cloud cells for the VBlank list: count, the sky tile id, x y each (story_sky_cells)
#define SK_END   (PW_END + 2 + 2 + 2 * STORY_SKY_CELLS)
// a picture scene's bytes in order, none touching the next (and the INTRO burst's own, generated: gen_story.py, STORY_STB_AT..STORY_STB_END)
typedef char ps_fits[(2 + SWAP_ROWS * 18 <= 40 && 40 + PS_BURST * 16 + 40 + 40 <= 168 && 168 + 1 <= STORY_STB_AT && STORY_STB_END <= PW_AT && SK_END <= STORY_SCRATCH) ? 1 : -1];
                                                     // (+170: the trail's cursor and stage, build/story_pictures.c)
#define PIC_SCENE (story_hdr.venue == 255)
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

// pt (fetched) -> its framed rectangle in pt_map / pt_attr; new cx..ch. The frame's bottom row is the speaker's name plate:
// the frame's corners, between them the name (story_name_get's plate tiles: dark letters on the frame's gold) centred in the
// plate's cells, the frame's bottom moulding either side. A picture whose bottom is the row above the text box stands on it: the box's top
// panel is then the frame's bottom edge, no plate (no portrait is placed so now).
static void compose_portrait(uint8_t k, uint8_t pid) {
    uint8_t w = pt.w + 2, h = pt.h + 2, x, y, i = 0, t, a, n = 0, o, name[12];
    if (pt.y + pt.h == BOX_ROW) h--;
    story_name_get(pid, name);                   // the name's plate tiles (relative to the portrait's first), 0-terminated
    while (n < 11 && name[n]) n++;
    o = (w - 2 * !STORY_PLATE_FULL - n) >> 1;    // the cells before the name (A: between the corners, B: all of the row)
    for (y = 0; y < h; y++)
        for (x = 0; x < w; x++, i++) {
            a = BGPAL_HUD;
            if (y == 0)          t = x == 0 ? ST_FRAME_TL : x == w - 1 ? ST_FRAME_TR : ST_FRAME_T;
            else if (y == pt.h + 1) {
                t = x == 0 ? ST_FRAME_BL : x == w - 1 ? ST_FRAME_BR : ST_FRAME_B;
                if (x >= !STORY_PLATE_FULL + o && x < !STORY_PLATE_FULL + o + n) t = spk_bg[k] + name[x - !STORY_PLATE_FULL - o];
            }
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
    if (PIC_SCENE) portrait_tiles_load(spk, STORY_PORTRAIT_BASE, spk_obj[k]);   // the one slot holds this speaker's
    portrait_get(spk, &pt);
    compose_portrait(k, spk);
    write_palettes();
    for (y = 0; y < ch; y++) {
        set_bkg_tiles(cx, cy + y, cw, 1, pt_map + y * cw);
        if (is_cgb) { VBK_REG = VBK_BANK_1; set_bkg_tiles(cx, cy + y, cw, 1, pt_attr + y * cw); VBK_REG = VBK_BANK_0; }
    }
    overlay_show(k);
    story_cur = spk;
}

// The VBlank list's room in a cut-scene, in cost units (a list entry's bytes + 4 for the entry itself: ~0.15 DIV ticks a byte,
// ~0.55 an entry). A page turn (the three box rows and the name tag: 74 bytes, 4 entries = 90 units) drains in 13 ticks and ends on
// line 153, the last line of VBlank; nothing a frame queues may cost more, whatever the player presses (A over a tile burst used to
// reach 17 ticks and end on line 2 of the next frame). The swap takes what the press of this frame leaves: see scene_frame.
#define VQ_STORY_ROOM  90
#define COST(n)        ((n) + 4)

static uint8_t room_left(uint8_t room) {         // what is left of `room` after what the list already holds
    uint8_t i;
    for (i = 0; i < vq_count; i++) {
        if (room < COST(vq[i].n)) return 0;
        room -= COST(vq[i].n);
    }
    return room;
}

// one frame of a portrait change (LCD on), within `room` cost units
static void swap_frame(uint8_t room) {
    uint8_t n, k, id, c;
    uint16_t a;
    uint8_t *src;
    room = room_left(room);
    switch (story_swap) {
    case SW_OUT:                                 // wipe the old frame back to the backdrop
        if (PIC_SCENE && vq_held) break;         // (the staging rows are still waiting in last frame's list)
        c = COST(cw) << is_cgb;                  // a row: its tiles, and on CGB its attributes
        for (n = 0; n < SWAP_ROWS && sw_row < ch && room >= c; n++, sw_row++, room -= c) {
            if (PIC_SCENE) {                     // the picture's own rows, from ROM through the staging buffer
                src = PS_ROWS + n * 18;
                story_pic_row(story_hdr.pic, cy + sw_row, cx, cw, src);
                vq_add(0, src, cx, cy + sw_row, cw);
                if (is_cgb) vq_add(1, src + cw, cx, cy + sw_row, cw);
                continue;
            }
            k = (cy + sw_row) * 20 + cx;
            vq_add(0, bd_map + k, cx, cy + sw_row, cw);
            if (is_cgb) vq_add(1, bd_attr + k, cx, cy + sw_row, cw);
        }
        if (sw_row >= ch) {
            cw = 0; story_cur = 255;
            story_swap = spk_index(sw_next) == 255 ? SW_IDLE : PIC_SCENE ? SW_TILES : SW_PAL;
            sw_row = 0;
        }
        break;
    case SW_TILES:                               // the incoming speaker's tiles into the one slot, PS_BURST a frame
        if (vq_held || vq_count > 12) break;     // (the wipe has hidden the slot: nothing of it is on screen)
        if (!sw_row) portrait_get(sw_next, &pt); // (its tile count)
        n = pt.ntiles - sw_row;
        if (n > PS_BURST) n = PS_BURST;
        while (n && COST(16) * n > room) n--;
        if (!n) break;
        portrait_tile_copy(sw_next, sw_row, n, PS_TILES);
        for (k = 0; k < n; k++) {                // BG ids 0-127 are at 0x9000, 128-255 at 0x8800 (LCDC bit 4 clear)
            id = STORY_PORTRAIT_BASE + sw_row + k;
            a = id < 128 ? 0x9000 + (uint16_t)id * 16 : 0x8800 + (uint16_t)(id - 128) * 16;
            vq_add(0, PS_TILES + k * 16, 0, 0, 16);
            vq[vq_count - 1].dst = (uint8_t *)a;
        }
        sw_row += n;
        if (sw_row >= pt.ntiles) story_swap = SW_PAL;
        break;
    case SW_PAL:                                 // (the top of the frame after the wipe went out: VBlank)
        k = spk_index(sw_next);
        portrait_get(sw_next, &pt);
        write_palettes();
        compose_portrait(k, sw_next);
        sw_row = 0;
        story_swap = SW_IN;
        // fall through: the first rows of the new frame
    case SW_IN:
        c = COST(cw) << is_cgb;
        for (n = 0; n < SWAP_ROWS && sw_row < ch && room >= c; n++, sw_row++, room -= c) {
            vq_add(0, pt_map + sw_row * cw, cx, cy + sw_row, cw);
            if (is_cgb) vq_add(1, pt_attr + sw_row * cw, cx, cy + sw_row, cw);
        }
        if (sw_row >= ch) { story_cur = sw_next; story_swap = SW_IDLE; overlay_show(spk_index(sw_next)); }
        break;
    }
}

// ---- pages ------------------------------------------------------------------------------------------------
static void tag_build(void) {                    // row 13: the box's top panel; the narrator's little spigot at the left (a speaker's name is on his portrait's plate)
    fill(tag_row, TILE_PANEL_TOP, 20);
    if (story_spk == SPK_NARRATOR) {
        tag_row[1] = TILE_HUD_BLANK; tag_row[2] = ST_SPIGOT_ICON; tag_row[3] = TILE_HUD_BLANK;
    }
}

// LCD on (lcd 0) or off (1): the page's box cleared, its name tag; a portrait change starts if the page's portrait
// differs (another speaker, or the same speaker's variant: the Spigoteer's cozy, Dregs's apology)
static void page_begin(uint8_t lcd_off) {
    uint8_t r, prev = story_spk;
    uint8_t gap;
    story_page_get(story_scene, story_page, story_conds, page_buf);   // its text: a variant when its condition holds
    gap = (page_buf[0] >> 4) * STORY_BEAT_UNIT;   // the page's @beat: a pause before it types (docs/story.md "Beats")
    page_buf[0] &= 15;
    if (!lcd_off && gap < (page_buf[0] != story_spk ? STORY_GAP_SPEAKER : STORY_GAP_PAGE))
        gap = page_buf[0] != story_spk ? STORY_GAP_SPEAKER : STORY_GAP_PAGE;   // a page turn / speaker change never types at once
    story_t = gap;                                // (the beat counter: story_update does not count frames in a scene)
    story_spk = page_buf[0];
    if (!PIC_SCENE) cam_page(story_scene, story_page);
    if (story_page && !PIC_SCENE) dg_page(win_rows[0], story_scene, prev, story_spk);   // Dregs's exit gag, on the narrator page after his
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
    else story_swap = PIC_SCENE ? SW_TILES : SW_PAL;
}

static void type_frame(void) {                   // one character a frame (spaces are free; a beat cell waits)
    uint8_t c, r, k;
    while (story_typed < 54) {
        c = page_buf[1 + story_typed];
        r = story_typed / 18; k = story_typed - r * 18;
        story_typed++;
        if (c == 1 || c == 2) {                  // a beat: this frame is the first of its pause
            story_t = (c == 1 ? STORY_BEAT_SHORT : STORY_BEAT_LONG) - 1;
            return;
        }
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
    smap_pal_back();                             // (from the story map: the HUD palette its picture borrowed)
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
    win_rows[0][4] = 0;                          // (no Dregs gag running; a POST scene loads its tiles below)
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
        if (!(s & 1)) dg_load(win_rows[0], story_hdr.venue);   // a POST scene: Dregs's gag tiles and palettes (OBJ 56.., LCD off)
        cam_load(s);
    } else {
        story_pic_draw(story_hdr.pic, is_cgb);
        PS_FX = 0;
        PB_T = 255;
        PW_T = 0; PW_PH = 0; PW_DUE = 0;         // (the jets as drawn)
        SK_C = 0;                                // Color: the clouds as OBJ sprites where the picture has them (LCD off: their cells made
        SK_ON = is_cgb && story_sky_load(story_hdr.pic, 1);   // sky at once; the scene's transition fades the OBJ palettes in with the rest)
        if (SK_ON) story_sky_oam(story_hdr.pic, 0);
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
    if (!PIC_SCENE) {                            // (a picture scene's backdrop is its picture, in ROM)
        read_rows(bd_map);
        if (is_cgb) { VBK_REG = VBK_BANK_1; read_rows(bd_attr); VBK_REG = VBK_BANK_0; }
    }
    // every portrait of the scene, one after the other; a picture scene has one slot for them (the picture's tiles
    // sit above it): each speaker's tiles stream into it when he comes on (SW_TILES), the first one is loaded by
    // portrait_now. Overlay tiles are all loaded now either way.
    bgn = STORY_PORTRAIT_BASE; objn = OBJ_DANCER;
    for (i = 0; i < story_hdr.nspk; i++) {
        portrait_get(story_hdr.spk[i], &pt);
        portrait_tiles_load(story_hdr.spk[i], bgn, objn);
        spk_bg[i] = bgn; spk_obj[i] = objn;
        if (!PIC_SCENE) bgn += pt.ntiles;
        objn += pt.nobjtiles;
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

// A timed shift's HUD timer is the mini-games' (hourglass + two digits, src/mg.c hud_timer), so at most 99 s (owner,
// 2026-10-13). The hourglass cannot sit at MG_HOURGLASS (BG 220) in a level: that is variant C's shift-0 pose's 3rd
// column, which a patron standing on a tile boundary draws. BG 252 is free in a shift (a boss fight's HUD face, the
// only other user, has no timer).
#define SHIFT_HOURGLASS HUD_HOURGLASS_BG   // 252 (253 the goal's icon)

static void hud_goal(void) {                     // queue the goal counter (and the timer) on the HUD row
    uint8_t s, h = 0;
    if (story_goal.type >= G_CLEAR) return;     // (a clear goal has no counter; a boss fight shows his meter: boss.c)
    hud_buf[0] = HUD_GOAL_BG;
    two_digits(hud_buf + 1, story_left);
    vq_add(0, hud_buf, HUD_GOAL_COL, HUD_ROW, 3);
    if (!story_goal.secs) return;
    s = st_secs;                                 // (never above SHIFT_TIMER_MAX: gen_story.py fails the build otherwise)
    hud_buf[4] = TILE_HUD_BLANK;                 // column 16 blank, the hourglass, two digits (over the flag): the mini-games' timer
    hud_buf[5] = SHIFT_HOURGLASS;
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
#ifdef DEBUG_MENU
    if (debug_from_title & 6) {                  // the debug menu's STRESS run (src/debug.c): the crowd held at its target by the bars' caps, a short wait, no end by the quota
        quota = 255;
        if (spawned > 200) spawned = 100;
        pat_bar = (pat_bar + 1) & 3;
        if ((debug_from_title & 6) != 4) { bar_cap[0] = bar_cap[1] = 3; bar_cap[2] = bar_cap[3] = 2; }   // (SPACE, ARCADE: 10 patrons; CLASSIC's own caps are 4 a bar: 16)
        return (debug_from_title & 6) == 4 ? 6 : 24;
    }
#endif
    if (++pat_pos == pat_len) pat_pos = 0;
    pat_bar = pat_buf[pat_pos] & 3;
    return pat_wait[e >> 4];
}

// An empty screen with the next patron further off than REFILL_FRAMES (patrons.c): pull the spawn forward to REFILL_FRAMES, or
// after a pattern's breather (the wait the last spawn started was code 3) to the longer BREATHER_REFILL: a breather is a pause
// for the player who is busy, not a stretch with nothing to do (owner 2026-10-17: the Stadium's Last call left him idle for 16 s).
void pat_refill(void) BANKED {
    uint8_t c = pat_len && (pat_buf[pat_pos ? pat_pos - 1 : pat_len - 1] >> 4) == 3 ? BREATHER_REFILL : REFILL_FRAMES;
    if (spawn_timer > c) spawn_timer = c;
}

static const char *const shift_name[STORY_SHIFTS] = STORY_SHIFT_NAMES;
static const char boss_word[] = "BOSS";

// The goal banner in the window (map rows 32-36, LCD off): panel, the shift's name alone (OPENING SHIFT, HAPPY HOUR, LAST CALL, or
// BOSS; owner 2026-10-11: no chapter number), the two goal lines, panel. story_goal is the goal's.
static void banner_build(void) {
    uint8_t i;
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
}

// One shift of the chapter: its goal banner over the venue's level (LCD off, then on), GS_GOAL.
static void shift_start(void) {
    TRANS_HOLD();                                // (src/trans.c: the drink drains at the end of this function, when the scene is whole)
    if (boss_on) boss_goal((uint8_t *)&story_goal);   // a boss fight: his banner lines, the regulars' pace (boss.c)
    else story_goal_get(story_chapter, story_shift, (uint8_t *)&story_goal);
    story_twist = story_goal.twist;
    DISPLAY_OFF;
    smap_pal_back();                             // (from the story map: the HUD palette its picture borrowed)
    banner_build();
    level = story_chapter + 1;                  // (lives: set by venue_start, carried from shift to shift)
    if (story_arc & 1) level += (arc_loop > 9 ? 8 : arc_loop - 1) * 10;   // ARCADE: the loop's row (start_level's loop maths)
    if (story_goal.secs) mg_hourglass_load(SHIFT_HOURGLASS);   // a timed shift: its HUD's hourglass (LCD off)
    if (story_goal.type < G_CLEAR) hud_icon_load(HUD_GOAL_BG, story_goal.type == G_CATCH ? HUD_ICON_CATCH : HUD_ICON_MUGCHECK);   // the goal's icon
    pour_load(story_chapter);                    // the perfect pour's frames and cue (LCD off; the venue = the chapter)
    music_fast = (story_twist & TWIST_FAST_TUNE) != 0;   // the twist: the band plays faster (before the tune starts)
    TUNE_FLUSH();                                // (an unlock heard in the last shift or scene: saved here, the LCD is off)
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
    SET_LYC(GOAL_LYC);
    story_phase = arc_banner ? SP_LOOP : SP_GOAL; story_t = 0;
    arc_banner = 0;
    game_state = GS_GOAL;
    trans_reveal();                              // (the drink drains now: the banner, the boss's HUD and the pace are all in)
}

static void goal_banner_off(void) {
    fill(win_rows[2], TILE_PANEL_BOT, 20);       // map row 34 is the normal banner's bottom panel again
    vq_add(0, win_rows[2], 0, 34, 20);
    SET_LYC(BANNER_LYC);
    overlay_on = 0;
}

// ---- the chapter's steps ----------------------------------------------------------------------------------------
// the first step from s the engine can play (STORY_STEPS: none left in the chapter)
static uint8_t next_step(uint8_t s) {
    while (s < STORY_STEPS && (story_step_get(story_chapter, s) & STEP_SKIP) && !((story_unskip >> s) & 1)) s++;
    return s;
}

// story_step (playable) begins, by kind: the chapter's mini-game (src/mg.c; its result goes on with story_level_done,
// whatever the medal: mini-games never block the story), or a shift. There is no boss step: Last call's serve quota turns
// that level into the venue's boss fight in place (boss_in_place; src/boss.c). A slot not built yet is STEP_SKIP in the data
// (gen_story NOT_BUILT) and never reaches here.
// The state a shift begins with, kept in HRAM (no WRAM): the lives, the step and the score, for RESUME after a QUIT TO MAP (the map overwrites every other byte of the level)
#define RS_LIVES (*(volatile uint8_t *)0xFFF5)
#define RS_STEP  (*(volatile uint8_t *)0xFFF6)
#define RS_SCORE (*(volatile uint32_t *)0xFFF7)    // 0xFFF7-0xFFFA

static void step_start(void) {
    uint8_t s = story_step_get(story_chapter, story_step);
    RS_LIVES = lives; RS_STEP = story_step; RS_SCORE = score;
    boss_set(BOSS_NONE);                         // (no fight until Last call's quota is met)
    if ((s & STEP_KIND) == STEP_MINI) { mg_enter(mg_of_venue(story_chapter), MG_STORY); return; }   // (the game id, not the venue)
    story_shift = s & STEP_INDEX;
    shift_start();
}

// RESUME on the story map: the shift (or mini-game) that was quit, again from its start, with the lives and the score it began with
void story_resume(void) BANKED {
    TRANS_WANT();                                // (src/trans.c: the map -> the level behind the fade)
    lives = RS_LIVES; story_step = RS_STEP; score = RS_SCORE;
    split6(score_digits, score);
    step_start();
}

// the venue (chapter) from its first playable step, with 3 lives (a new chapter, a lost last life, CONTINUE): a new
// venue attempt, so its page text conditions start over
static void venue_start(void) {
    if (!(story_arc & 1)) lives = START_LIVES;         // (ARCADE: the run's lives carry on)
    story_conds &= ~COND_GLASS_BROKEN;           // a new attempt at the venue: no glass broken in it yet
    story_step = next_step(0);
    step_start();
}

static void chapter_done(void) {                 // every step done: saved as cleared, the POST scene
    if (story_arc & 1) { bonus_enter(); game_state = GS_BONUS; return; }   // ARCADE: the bonus round (then arcade_next)
    story_save(story_chapter + 1, story_chapter + 1 == STORY_CHAPTERS);   // (the last venue: step 1 = the finale is reached, not done: CONTINUE returns to the map, src/save.c)
    venue_score_put(story_chapter + 1, score);   // (the next venue's start score: what CONTINUE gives back)
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

void story_begin(uint8_t how) BANKED {
    uint8_t cont = how & 1;
    TRANS_WANT();                                // (src/trans.c: title -> the story)
    run_begin(0);
    if (cont && (story_chapter & DEBUG_RESUME)) {            // a debug-select run was quit: back to its chapter and step, nothing saved
        story_chapter &= ~DEBUG_RESUME;
        save_lock = SAVE_LOCK_DEBUG;
        story_debug_start(story_chapter, story_step + 1, 0);
        return;
    }
    story_arc = cont ? story_diff_saved() << 1 : how & 6;   // the difficulty: the saved one, or the prompt's (bits 1-2, DIFF_*; the run's, game.h RUN_DIFF)
    if (cont && can_continue()) {                // a saved story, not one whose finale is done: the story map, Sal where he stood (src/smap.c)
        story_chapter = story_progress < STORY_CHAPTERS ? story_progress : STORY_CHAPTERS - 1;
        score = venue_score_get(story_progress); // the score the venue was entered with (owner 2026-10-14), lives 3 (run_begin); all ten cleared: the finale's
        split6(score_digits, score);
        smap_continue();                         // (A at the next venue: its Opening banner when a step of it was reached, else its PRE scene: story_map_venue)
    } else {
        story_chapter = 0;
        story_progress = 0; story_reached = 0;   // (a new story: the map opens its venues by the run's progress; the old save is replaced by this run's first save)
        smap_new_run();
        scene_enter(SC_INTRO);
    }
}

// PLAY > ARCADE: the saloon's first playable step, 3 lives, nothing saved (save_lock; title_enter clears it)
void arcade_begin(void) BANKED {
    TRANS_WANT();                                // (src/trans.c: title -> ARCADE)
    run_begin(1);
    save_lock = 1;
    story_conds = 0;
    story_chapter = 0;
    venue_start();
}

// ARCADE: GS_BONUS is over (main.c): the next venue, or after the last one the saloon again, a loop harder
void arcade_next(void) BANKED {
    TRANS_WANT();                                // (src/trans.c: the bonus round -> the next venue)
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

// The story's end (after the credits roll, src/credits.c): the story's score into the STORY top 5 (initials, the table)
void story_end(void) BANKED {
    uint8_t aaa[3];
    story_on = 0; story_phase = SP_OFF;
    if (save_lock) { title_enter(); return; }   // (a debug-select run: nothing saved)
    story_save(STORY_CHAPTERS, 0);              // (the finale is done: CONTINUE is not offered again, src/save.c)
    score_tbl = MODE_STORY;
    aaa[0] = aaa[1] = aaa[2] = 'A';
    if (RUN_DIFF == DIFF_HARD) aaa[0] |= 0x80;             // the table's E / H mark (save.c)
    else if (RUN_DIFF == DIFF_EASY) aaa[1] |= 0x80;
    story_arc = 0; hud_pal_reset();                         // (the run's difficulty and the HUD colour it tinted end here)
    new_rank = top_insert(score, aaa);
    if (new_rank < TOP_N) hi_save();
    scores_after_game();
}

static void scene_done(void) {
    uint8_t s = story_scene;
    TRANS_WANT();                                // (src/trans.c: the next screen comes up behind the drink)
    if (s == SC_CREDITS) { credits_enter(1); return; }   // the end: the credits roll, then story_end
    if (s == SC_FINALE_A) { mg_enter(MG_POUROFF, MG_STORY); return; }   // Dregs challenges: the Pour-Off (src/po.c), then FINALE_B
    if (s == SC_FINALE_B) { scene_enter(SC_CREDITS); return; }
    if (s == SC_INTRO) {                         // the map; a debug-select run (nothing saved, no map) goes on to the first PRE
        if (save_lock) { scene_enter(SC_PRE_SALOON); return; }
        smap_stop = 10; smap_enter(0);          // (a new story starts the map at the town: the saloon is the next stop, Sal walks there)
        return;
    }
    if (!((s - SC_PRE_SALOON) & 1)) { venue_score_put(story_chapter, score); venue_start(); return; }     // a PRE scene: the chapter
    if (!save_lock) { smap_stop = story_chapter; smap_enter(0); return; }   // a POST scene: the map, Sal on the venue just played (A there: the next venue's PRE, or the Pour-Off at the town)
    if (story_chapter + 1 < STORY_CHAPTERS) {                       // (a debug-select run: the next chapter's PRE as before)
        story_chapter++;
        scene_enter(SC_PRE_SALOON + 2 * story_chapter);
    } else scene_enter(SC_FINALE_A);
}

// The map's A on venue c, the next one not cleared (src/smap.c, whose screen is left): its PRE scene and the chapter as ever, or, with a step of it
// reached before (CONTINUE), straight to its Opening banner (as CONTINUE always did)
void story_map_venue(uint8_t c) BANKED {
    TRANS_WANT();                                // (src/trans.c: the map -> the scene behind the fade)
    story_chapter = c;
    story_scene = SC_PRE_SALOON + 2 * c;
    if (story_progress == c && story_reached) venue_start();
    else scene_enter(SC_PRE_SALOON + 2 * c);
}

// The map's THE POUR-OFF (all ten venues cleared): FINALE_A, the Pour-Off, FINALE_B, the credits
void story_map_pouroff(void) BANKED {
    TRANS_WANT();
    story_chapter = STORY_CHAPTERS - 1;
    scene_enter(SC_FINALE_A);
}

// The Pour-Off is won (src/mg.c, its screen already left): the finale's second half
void story_pouroff_done(void) BANKED {
    scene_enter(SC_FINALE_B);
}

// GS_LEVEL_CLEAR is over (main.c): the progress saved (the furthest step reached in the chapter, even one not built
// yet, for Practice: a venue restart never lowers it), the next playable step, or the chapter's POST scene
void story_level_done(void) BANKED {
    uint8_t n = story_step + 1, s = next_step(n);
    state_timer = 0;                             // (the antics' 255 of the clear: a mini-game's pause reads the bits)
    boss_set(BOSS_NONE);                         // (a won boss fight is over: the POST scene has no boss)
    if (play_mode == MODE_RUSH) { rush_won(); return; }   // BOSS RUSH: no progress, the rush's next screen
    TRANS_WANT();                                // (src/trans.c: the next shift / mini-game / boss / scene comes up behind the drink)
    if (s >= STORY_STEPS) { chapter_done(); return; }
    story_save(story_chapter, story_progress == story_chapter && story_reached > n ? story_reached : n);
    story_step = s;
    step_start();
}

// the goal failed: TRY AGAIN over the frozen level, then the venue again (no lives left: from enter_game_over, or
// the clock's last life) or that shift (the clock ran out, lives left)
void story_fail(void) BANKED {
    show_overlay(play_mode == MODE_RUSH ? "GAME OVER" : "TRY AGAIN");   // (BOSS RUSH: the run is over)
    music_play(TUNE_OVER);
    story_fails++;
    story_phase = SP_FAIL; story_t = 0;
    game_state = GS_STORY;
}

static void story_win(void) {
    enter_level_clear();                         // (its LEVEL CLEAR banner, the bonus, the jingle, GS_LEVEL_CLEAR)
    show_overlay(play_mode == MODE_RUSH ? "BOSS BEATEN"
                 : next_step(story_step + 1) >= STORY_STEPS ? ((story_arc & 1) ? "VENUE CLEAR" : "CHAPTER CLEAR") : "SHIFT CLEAR");
}

// The shift's goal is met. A shift's clear is story_win's. Last call (in a venue whose boss is built: all ten) is not the end: the venue's
// level goes on into his fight. G_SERVE / G_CATCH: arrivals stop (quota = what has come), the goal type G_BOSS says "boss next", the HUD
// counter stays at 0 and stops counting, the clock stops; the patrons still on the bars are served (or cost lives) as ever, and story_play
// brings the boss when the bar is empty. clear: a clear goal has met its quota with an empty bar already.
static void shift_won(uint8_t clear) {
    if (story_shift != STORY_SHIFTS - 1 || !((BOSS_BUILT_MASK >> story_chapter) & 1)) { story_win(); return; }
    story_goal.type = G_BOSS;
    story_timer = 0; st_secs = 0;
    level_clear = 0;                             // (main.c would clear the level on it this frame; the next frame's update_patrons raises it again once the bars are empty)
    if (!clear) quota = spawned;
}

// Last call turned into the boss fight (story_play: the bar is empty, quota met), IN PLACE (owner 2026-10-17: "I want the boss to come in at the end of the stage
// without any kind of screen transition"): no cover, no LCD-off swap, no banner. The same venue and bars, bartender and score, the game never leaves GS_PLAYING;
// what changes, all while the scene keeps running:
//   - the fight's state: boss_set (BS_WARM), his goal (a G_BOSS goal, no counter), the HUD's counter columns blanked and the flag and the level put back
//     through the VBlank queue, the mosh pit and the fast tune of Last call's twist off, the venue's tune from its start (the Sumo's beat counts music_frames from it);
//   - the pace: Last call's walk and spawn percentages come off, the fight's go on (a fight's walkers are the row's, the regulars' arrivals BOSS_SPAWN_PCT %: boss.c
//     boss_goal / boss_begin);
//   - his tiles and palettes: boss_load records them and boss.c ld_step streams them over the next frames (BS_WARM), 4 tiles a frame through the copy queue and a
//     palette a frame through the VBlank interrupt, onto tile ids and palettes nothing on screen shows (the bars are empty);
//   - then boss_frame starts his entrance (BS_ENTER / BS_WALKIN; no warm-up: Last call was it), his meter and face come when he has entered (fight_start), and the
//     first time he ever appears, his HOW TO PLAY card opens the frame after (HOOK_CARD), over a whole picture, and the game resumes by itself when it is left.
static void boss_in_place(void) {
    uint8_t *hb = story_scratch + SCR_HB_AT;           // (9 bytes of the backdrop buffer's free middle, kept until the queue has copied them; boss.c LD ends below it)
    add_score(1000);                             // (LEVEL_BONUS, main_cold.c: the clear bonus Last call's end gave before: the venue's score keeps its two bonuses, here and at his defeat)
    boss_set(story_chapter);
    boss_goal((uint8_t *)&story_goal);
    story_twist = 0;
    pocket_clear();                              // (a pocketed tip: his tiles take 252-255, the icon's 255)
    boss_load();                                 // (LCD on: recorded, streamed by boss_frame)
    music_fast = 0;
    music_play(TUNE_VENUE0 + story_chapter);     // (a no-op unless Last call's twist made the tune fast: then it restarts at the normal speed)
    fill(hb, TILE_HUD_BLANK, 6);                 // the goal counter and the clock (columns 11-16, and the hourglass and digits over the level flag at 17-19): blank, and
    hb[6] = TILE_HUD_FLAG;                       // the flag and the level back (draw_hud's), as in a fight that starts on a fresh level, until his face and meter come at 12-19
    two_digits(hb + 7, level);
    vq_add(0, hb, HUD_GOAL_COL, HUD_ROW, 9);
    mosh_set(0, 0);
    level_pace_again();                          // (Last call's percentages off: the level row's own speeds and spawn interval, exactly)
    shift_pace();                                // (the fight's go on: his goal's walk and spawn percentages, a quota of 255, the arrival pattern; boss_begin redraws it)
    level_clear = 0;
    served = spawned = 0;                        // (a fresh count for the fight, as a level load gives: a lost life's start patrons are placed from it, show.c)
    boss_begin();
    story_left = 0; st_secs = 0; story_timer = 0;
}

// Every GS_PLAYING frame in story mode, after the rules (main.c): the goal's counters, success and failure.
void story_play(void) BANKED {
    uint8_t c, b, left;
    if (play_mode == MODE_RUSH && RUSH->fight_t != 0xFFFF) RUSH->fight_t++;   // BOSS RUSH: the fight's time
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
    if (story_goal.type == G_BOSS) {             // Last call's quota is met: no more arrivals (quota = spawned), the counter and the clock stand still;
        if (level_clear) {                       // when the bar is empty (and no tip or show is on: boss_load takes their tiles) the boss comes
            if (tip_timer | show_timer) level_clear = 0;   // (main.c would clear the level on it)
            else boss_in_place();
        }
        return;
    }
    if (story_timer && !intro_timer) {
        if (!--story_timer) {                    // time up: a life, and the shift again (the venue: it was the last)
            if (lives) lives--;
            hud_dirty |= HUD_LIVES; prep_hud();
            if ((story_arc & 1) && !lives) { game_over = 1; enter_game_over(); return; }   // ARCADE: that was the last
            story_fail();
            return;
        }
        c = st_secs;                             // ceil(story_timer / 60), re-derived only when the timer leaves the shown second's 60-frame band
        { uint16_t hi = ((uint16_t)c << 6) - ((uint16_t)c << 2); if (story_timer > hi || story_timer + 60 <= hi) c = (uint8_t)((story_timer + 59) / 60); }
        if (c != st_secs) { st_secs = c; hud_goal(); }
    }
    switch (story_goal.type) {
    case G_SERVE: c = served; break;
    case G_CATCH: c = story_catches; break;
    default:
        if (level_clear) shift_won(1);
        return;
    }
    left = c >= story_goal.count ? 0 : story_goal.count - c;
    if (left != story_left) { story_left = left; hud_goal(); }
    if (!left) shift_won(0);
}

// ---- the picture switch (INTRO page 5: the explosion replaces the "before" picture behind a white flash) ----------
// The screen goes white (DMG BGP 0, CGB all BG palettes white), the LCD goes off for the reload (the new picture's
// tiles, map, attributes and palettes: ~2.5 KB, about 2 frames), then the picture fades in from white in three steps
// of two frames (DMG BGP 0x40, 0x90, 0xE4; CGB the palettes 2/3, 1/3 of the way to white, then true). The page's text
// starts after the fade. The portrait frame is gone with the reload (the switch page is the narrator's).
#define FX_HOLD      2                               // frames of white before the reload (step 1 is the first)
#define FX_RELOAD    (FX_HOLD + 1)
#define FX_END       (FX_RELOAD + 5)                 // the last fade step: the real palettes

static const uint8_t pic_slot[5] = { 0, 5, 6, 7, BGPAL_HUD };   // PS_PALS order: the picture's four, then the HUD's

// The fade is two phases so the palette writes stay inside VBlank (the blend itself is far too slow for it): pic_calc
// works out the palettes w/3 of the way to white (w 3: white, 0: as they are) into PS_OUT a frame early, pic_put (the
// top of a frame) only copies them to palette RAM, or sets DMG's BGP to match.
static const uint8_t fade3[2][32] = {            // floor(d / 3), floor(2 d / 3) for d = 31 - component: no multiply, no divide
    { 0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 6, 7, 7, 7, 8, 8, 8, 9, 9, 9, 10, 10 },
    { 0, 0, 1, 2, 2, 3, 4, 4, 5, 6, 6, 7, 8, 8, 9, 10, 10, 11, 12, 12, 13, 14, 14, 15, 16, 16, 17, 18, 18, 19, 20, 20 },
};

static void pic_calc(uint8_t w) {
    uint8_t k, r, g, b;
    uint16_t v;
    PS_W = w;
    if (!is_cgb) return;
    for (k = 0; k < 20; k++) {
        if (w == 3) { PS_OUT[k] = 0x7FFF; continue; }
        v = PS_PALS[k];
        r = v & 31; g = (v >> 5) & 31; b = (v >> 10) & 31;
        if (w) { r += fade3[w - 1][31 - r]; g += fade3[w - 1][31 - g]; b += fade3[w - 1][31 - b]; }
        PS_OUT[k] = r | ((uint16_t)g << 5) | ((uint16_t)b << 10);
        if (w != 3) PS_OUT[k] = BRIGHTEN(PS_OUT[k]);       // SCREEN BRIGHT: lifted here (white stays white); pic_put / pic_fx write PS_OUT raw
    }
}

static void pic_put(void) {
    uint8_t k;
    if (!is_cgb) { BGP_REG = PS_W == 3 ? 0x00 : PS_W == 2 ? 0x40 : PS_W == 1 ? 0x90 : 0xE4; return; }
    for (k = 0; k < 5; k++) (set_bkg_palette)(pic_slot[k], 1, PS_OUT + k * 4);   // (raw: pic_calc lifted them)
}

// The fountain flowing (owner Q74, 2026-11-04; assets/story/pictures/water.txt): every 8 frames the jets' phase steps on, and each
// jet's three tiles go out through the VBlank list, the left jet one frame and the right the next, when the list has room for them
// and nothing else is changing the screen (a portrait swap, the picture switch's flash, last frame's list still waiting). A jet that
// had to wait shows the newer phase when it goes. DMG and Color alike; a picture without water (INTRO A) answers 0.
static void story_water(void) {
    uint8_t j, k;
    if (!(++PW_T & 7)) { PW_PH = (PW_PH + 1) & (STORY_WATER_PHASES - 1); PW_DUE = 3; }
    if (!PW_DUE || vq_held || story_swap != SW_IDLE || (story_hdr.swpage && PS_FX) || room_left(VQ_STORY_ROOM) < 3 * COST(16)) return;
    j = (PW_DUE & 1) ? 0 : 1;
    PW_DUE &= j ? 1 : 2;
    if (!story_water_tiles(story_hdr.pic, j, PW_PH, PW_BUF)) { PW_DUE = 0; return; }
    for (k = 0; k < 3; k++) {
        vq_add(0, PW_BUF + k * 16, 0, 0, 16);
        vq[vq_count - 1].dst = (uint8_t *)(PW_BUF[48 + 2 * k] | ((uint16_t)PW_BUF[49 + 2 * k] << 8));
    }
}

// The clouds drifting, Color only (owner Q74, 2026-11-04; assets/story/pictures/sky.txt): the picture's clouds are OBJ sprites that move
// one pixel right every 8 frames (with the water's count), masks of the picture's own pixels over them where they pass behind the town.
// After the picture switch's fade-in (SK_ON 2) their BG cells go to sky in the same VBlank as the sprites come on, where the BG clouds were.
static void story_sky(void) {
    uint8_t k;
    if (SK_ON == 2) {
        if (vq_held || room_left(VQ_STORY_ROOM) < (uint8_t)(SK_BUF[0] * COST(1))) return;
        for (k = 0; k < SK_BUF[0]; k++) vq_add(0, SK_BUF + 1, SK_BUF[2 + 2 * k], SK_BUF[3 + 2 * k], 1);
        SK_ON = 1;
        story_sky_oam(story_hdr.pic, SK_C);
    } else if (SK_ON == 1 && !(PW_T & 7) && story_swap == SW_IDLE) story_sky_oam(story_hdr.pic, ++SK_C);   // (not on a page's swap frames: they are full)
}

// The clouds are sprites: not over the white; they come back after the fade-in.
static void pic_hide_sky(void) {
    uint8_t k;
    if (SK_ON) {
        for (k = 0; k < STORY_SKY_SPR; k++) shadow_OAM[STORY_SKY_OAM + k].y = 0;
        SK_ON = 0;
    }
}

#define FX_OUT       9                               // the contest switch: frames 1-8 fade the old picture out, 3 a step (put at 2, 5, 8)

// One step of the switch (PS_FX = the step, 1 on the page turn). 1: the LCD was off for it.
// INTRO page 5 (the explosion, picture 0 -> 1): white at once, on purpose. Any other switch (FINALE's contest, owner Q77 2026-11-04,
// "quick fade") first fades the picture out to white in w 1, 2, 3 (BGP / palette blend), then goes on as step 1 of the same switch.
static uint8_t pic_fx(void) {
    uint8_t f = PS_FX++, k;
    if (story_hdr.pic > STORY_BURST_PIC) {              // (the INTRO's pictures are 0 and 1, the FINALE's 2 and 3)
        if (f < FX_OUT) {
            if (f == 1) { pic_hide_sky(); story_pic_pals(story_hdr.pic, PS_PALS); }
            if (f == 1 || f == 3 || f == 6) pic_calc(f == 1 ? 1 : f == 3 ? 2 : 3);
            else if (f == 2 || f == 5 || f == 8) pic_put();
            return 0;
        }
        f -= FX_OUT - 1;
    }
    if (f == 1) {                                // white (all eight BG palettes: the frame's are white too)
        pic_hide_sky();
        story_pic_pals(story_hdr.pic, PS_PALS);  // (the HUD's palette is kept to fade back to: a skip needs it too)
        pic_calc(3);
        if (!is_cgb) pic_put();
        else {                                   // (eight palette writes do not fit VBlank: LCD off, white at once)
            DISPLAY_OFF;
            for (k = 0; k < 8; k++) (set_bkg_palette)(k, 1, PS_OUT);
            DISPLAY_ON;
            return 1;
        }
    } else if (f == FX_RELOAD) {                 // LCD off: the new picture, the page's box, its palettes still white
        DISPLAY_OFF;
        vq_reset();
        overlay_hide();
        story_swap = SW_IDLE;
        story_hdr.pic++;                         // (the wipes of pages 6-8 restore this one: story_pic_row)
        story_pic_draw(story_hdr.pic, is_cgb);
        PW_PH = 0; PW_DUE = 0;                   // (its jets as drawn)
        SK_C = 0;                                // (its clouds: tiles and palettes now, the cells and sprites once it has faded in)
        if (is_cgb && story_sky_load(story_hdr.pic, 0)) SK_ON = 3;
        story_pic_pals(story_hdr.pic, PS_PALS);
        if (story_hdr.pic == STORY_BURST_PIC) story_burst_load(is_cgb);   // (the INTRO's explosion: ten pieces' OBJ tiles and palette, flown by story_update; FINALE_A's second picture has none)
        page_begin(1);                           // the narrator's page: its box and tag, no portrait (story_cur 255)
        pic_calc(3);
        pic_put();
        pic_calc(2);
        if (story_hdr.pic == STORY_BURST_PIC) {
            PB_T = 1;                            // the pieces sit where the spigot was (frame 0), flying from the next frame on
            story_burst_step(0, 0);
        }
        DISPLAY_ON;
        return 1;
    } else if (f > FX_RELOAD) {                  // the fade: w 2, 1, 0 two frames apart, each worked out a frame ahead
        k = (FX_END - f) >> 1;
        if (!((FX_END - f) & 1)) {
            pic_put();
            if (!k) {
                PS_FX = 0;                         // (faded in: the trail's map writes may go out from now on)
                if (SK_ON == 3) { story_sky_cells(story_hdr.pic, SK_BUF); SK_ON = 2; }
            }
        } else pic_calc(k);
    }
    return 0;
}

// One frame of a cut-scene (SP_SCENE) after START was looked at. 1: the screen was redrawn (LCD off) or the scene is over.
static uint8_t scene_frame(uint8_t pressed) {
    if (story_hdr.swpage && PS_FX) return pic_fx();   // the picture switch: nothing else moves
    if (win_rows[0][4] == 1) dg_frame(win_rows[0]);   // Dregs's gag (src/dgag.c) draws its sprites
    if (!PIC_SCENE) cam_frame();
    if (story_swap) swap_frame(VQ_STORY_ROOM - ((pressed & (J_A | J_B)) ? story_typed < 54 ? 3 * COST(18) : VQ_STORY_ROOM : 0));
                                                 // (the press queues the page's text, or turns the page: the swap waits a frame)
    if (story_typed < 54) {
        if (pressed & (J_A | J_B)) { story_t = 0; type_all(); }   // A or B skips a beat, and shows the rest of the page
        else if (story_t) story_t--;                              // (a beat: before the page, or mid-line)
        else type_frame();
        return 0;
    }
    if ((pressed & (J_A | J_B)) && !story_swap && win_rows[0][4] != 1) {   // (not while Dregs's gag plays)
        if (++story_page >= story_hdr.pages) { scene_done(); return 1; }
        if (story_page + 1 == story_hdr.swpage) { PS_FX = 1; return pic_fx(); }   // the next picture, behind a flash
        page_begin(0);
    }
    return 0;
}

// One frame of GS_STORY (a cut-scene, or TRY AGAIN) or GS_GOAL. 1: the screen was redrawn (LCD off): skip the rest.
uint8_t story_update(uint8_t pressed) BANKED {
    uint8_t btn;
    WIN_FIX();                                   // (the goal banner's window: the plan, main.c's update shows it before this)
    if (story_phase != SP_SCENE) story_t++;      // (a scene's story_t is the typing's beat counter: page_begin, type_frame)
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
            if (play_mode == MODE_RUSH) { rush_lost(); return 1; }   // BOSS RUSH: out of lives, the result
            TRANS_WANT();                        // (the drink: TRY AGAIN -> the shift / the venue again)
            if (lives) shift_start();
            else {                               // out of lives: the venue again, with the score it was entered with (owner 2026-10-14)
                story_restarts++;
                score = save_lock ? 0 : venue_score_get(story_chapter);   // (a debug-select run saves none: it was entered with 0)
                split6(score_digits, score);
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
        if (boss_outro(story_t)) {
            if (play_mode != MODE_RUSH) boss_beaten(story_chapter);   // STORY / ARCADE: BOSS RUSH lists him (save.c)
            story_win();
        }
        return 0;
    case SP_RUSH:                                // a BOSS RUSH screen (src/rush.c)
        return rush_update(pressed);
    case SP_CREDITS:                             // the credits roll (src/credits.c)
        return credits_update(pressed);
    case SP_MAP:                                 // the story map between the chapters (src/smap.c)
        return smap_update(pressed);
    case SP_SCENE:
        break;
    default:
        return 0;
    }
    if (pressed & J_START) {
        if (story_hdr.swpage && PS_FX) { pic_calc(0); pic_put(); }   // (skipped mid-flash: the HUD's palette and BGP back)
        scene_done();
        return 1;
    }
    btn = scene_frame(pressed);
    if (!btn && PIC_SCENE) {
        if (PB_T != 255)                         // the INTRO's explosion, last: its trail and star go into whatever room the frame's list has
            PB_T = story_burst_step(PB_T, (story_hdr.swpage && PS_FX) || (pressed & (J_A | J_B)) ? 0 : story_swap ? 1 : STORY_BURST_PER) ? 255 : PB_T + 1;
        else if (story_hdr.pic == STORY_BURST_PIC && !PS_FX) story_burst_crackle(story_t);   // over: the sparks keep on off the stump
        story_water();                           // (after the burst: it takes what room the frame's list has left)
        story_sky();                             // (Color: the clouds; nothing on a DMG, SK_ON stays 0)
    }
    return btn;
}

// Every GS_LIFE_LOST frame in story mode (main.c, before the freeze's frame count): after a strict rule's penalty the
// lives digit blinks (the count before the penalty 8 frames, the new count 8) until the freeze's last frame puts the
// HUD back.
void story_life_frame(void) BANKED {
    if (!story_pen) return;
    if (state_timer + 1 >= LIFE_FREEZE_FRAMES) { story_pen = 0; prep_hud(); hud_dirty |= HUD_LIVES; return; }
    if (state_timer & 7) return;
    lives_tiles[1] = TILE_GLYPH_0 + ((state_timer & 8) ? lives + story_pen : lives);
    hud_dirty |= HUD_LIVES;
}

// The mini-game framework calls this on a gold medal (owner: +1 life, at most MAX_LIVES; the HUD's digit counts it).
void story_bonus_life(void) BANKED {
    if (lives < MAX_LIVES) lives++;
    prep_hud();
    hud_dirty |= HUD_LIVES;
}

// BOSS RUSH (src/rush.c, which has set the lives and the score): venue v's boss step alone, as the story plays it (his
// banner, the regulars, the perfect pour, the HUD meter), in MODE_RUSH: nothing saved but the rush's own bests
// (save_lock 1: no progress, no tune unlocks; title_enter clears it), no top 5, no extra lives by score. A win ends at
// story_level_done -> rush_won, the last life at SP_FAIL -> rush_lost.
void rush_fight(uint8_t v) BANKED {
    story_on = 1; story_arc = 0; play_mode = MODE_RUSH; save_lock = 1;
    extra_at = 0; bonus_round = 0; game_over = 0; story_conds = 0; story_pen = 0;
    story_chapter = v;
    story_step = STORY_STEPS - 1; story_shift = STORY_SHIFTS - 1;   // (Last call's slot: the fight is the venue's level as Last call turns it, from the start)
    boss_set(v);                                 // (his banner, the regulars, then his entrance)
    shift_start();
}

// The debug select in story mode (src/debug.c): chapter ch at position pos (0 its PRE scene, 1..STORY_STEPS the step
// pos - 1, STORY_STEPS + 1 its POST scene) with the story's rules: a fresh score, the venue's lives as venue_start sets
// them (from any step), its goals. arc 1 (the ARCADE box: a step only): the same as an ARCADE run from there (loop 1).
// debug.c has set save.c's save_lock: nothing of the run is saved.
#ifdef DEBUG_MENU
// the debug menu's STRESS > ARCADE (src/debug.c): ARCADE from the space lounge's (chapter 10) Last call in loop 4, level 40, tests/test_perf_arcade.py's scene
void story_stress_start(void) BANKED {
    run_begin(1);
    story_conds = 0;
    story_chapter = STORY_CHAPTERS - 1;
    arc_loop = 4;
    story_step = 3;
    step_start();
}
#endif

void story_debug_start(uint8_t ch, uint8_t pos, uint8_t arc) BANKED {
    run_begin(arc);                              // (arc: the ARCADE box, its run as ARCADE plays it from that step)
    story_conds = 0;
    story_chapter = ch;
    if (pos == 0) scene_enter(SC_PRE_SALOON + 2 * ch);
    else if (pos > STORY_STEPS) scene_enter(SC_POST_SALOON + 2 * ch);
    else { story_step = pos - 1; step_start(); }
}
