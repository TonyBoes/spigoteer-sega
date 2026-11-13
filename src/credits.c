// The credits roll (owner 2026-10-17): a cast of characters, then the game's credits scrolling up the screen in the story's lettering, and
// "THANKS FOR PLAYING!" alone at the end. It IS the story's credits: the CREDITS scene shows its picture and the four closing narrator
// pages, and its end (story.c scene_done) is this roll (credits_enter(1); its end is story_end: the STORY score entry) and from the
// title's BONUS > CREDITS (credits_enter(0); its end or B: back to BONUS, the cursor on CREDITS). The wording is CREDITS.md's, the
// "Special thanks to:" list in it.
//
// The music is the credits tune (TUNE_CREDITS), started by credits_enter while the screen is built (BONUS' own tune stops there). The whole
// roll runs on its own clock (the frames on the screen, CR->t; owner 2026-11-05: the tune is not changed to fit): every boundary below is a share
// (units of 1/392) of CR_PIC_FRAMES, 9692 frames (162 s). The tune (the Easy Winners, music batch 5) is 9986 frames (166 s): it starts with the roll and runs 4.9 s past its picture clock (the last words wait for it: its ending is never cut),
// in silence, with no loop or restart; the cards and the roll go on at the same pace to the end.
//
//   units  0-6     "CAST OF CHARACTERS"
//          7-270   32 cards: Sal Tapley AKA the Spigoteer, Dregs (each his story portrait, his sprite, his name), then for each venue the owner
//                  (portrait, name, venue; 7 units), the patrons (11 units, owner Q80: DMG the three base looks in a row, Color all eight in rows of
//                  3, 3 and 2, a name under each) and the boss (7; animated: his fight walk and gulp)
//          271-361 the credits roll (text rows streamed in as before; its first 40 frames build it behind the fade)
//          362-391 "THANKS FOR PLAYING!" alone, the tune's last bars and its ring; the roll ends when the tune has
//          (a unit is 24.7 frames: a card 2.9 s, a patron card 4.5 s; the tune ends at unit 352, in the roll)
//
// A card changes behind a fade to WHITE (trans.c trans_cast, palette RAM written in the VBlank only, ~9 frames each way, the tune's ticks kept
// frame for frame): the old card fades out, the new one is built unit by unit WITH THE LCD ON (the library's tile writes wait for the picture's
// blanking: a byte a scanline, so a unit is a few tiles and the tune is ticked between them, once a frame), the card fades in. A venue's name is the HEADER of
// its three cards (rows 0-1): it fades in once with the owner and out once after the boss, and stays through the fades between (CGB: its cells are
// BG palette 6, which trans.c skips; DMG: BGP is one palette for the screen, so main.c cast_isr changes it at line 16: the header's BGP above,
// the card's below). The card's colours live in RAM (CR_PAL: all 128 bytes of palette RAM on CGB; BGP / OBP0 / OBP1 on DMG). The build's ticks
// are the frame's (cr_pp: one at the first call after line 18 of each frame, as the main loop's and the fades'), so the tune keeps wall time
// through every change with nothing to make up. The tilemap is the
// 32-row ring the roll scrolls (SCY 0 during the cast; the cards use rows 0-17). BG tile ids: the portrait from STORY_PORTRAIT_BASE (44 at
// most), the boss's tile pairs from CR_T_BOSS; OBJ ids: Dregs 56.., the topper 64.., the patrons' shift-0 poses 100-117 (the roll's robots too).
//
// The text (every cast label, every roll line) is PRE-RENDERED at build time (tools/gen_credits.py), as the title menu's is: each row's tiles cut from a
// pixel row on which its ink is centred to the pixel (an odd-length line sits 4 px right inside one more tile), streamed into VRAM as the row is
// needed (credits_text.c). The roll's text is one row per tilemap ROW (the list is in the generator); "" is a blank row. The lines of one sentence are on consecutive rows, the items of
// a list have two blank rows between them, sections more. Every line is at most 18 tiles (a clear column at each edge). CR_BAND is the row
// where the sprites' band starts (4 rows: the three robots stand under the "robot friends" line, who bob in turn, and the Spigoteer, facing
// them, raises a hand now and then). B / START skip (a fade or a build is cut short and the press seen). With the sound on the roll ends when the music
// has; with the sound off when its length has passed.
// State in story_scratch (no WRAM of its own; nothing else runs while the roll shows): tests read it at story_scratch + offset.
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"
#include "music.h"
#include "palettes.h"
#include "story.h"
#include "credits_text.h"

extern uint8_t overlay_on, joy, story_phase;

#define CR_FIRST      18      // the roll's first row, in world rows (just under the screen)
#define CR_AHEAD      20      // rows are kept written up to T + CR_AHEAD (T: the top row of the screen)
#ifdef CREDITS_SCROLL
#define CR_BAND       CT_ROLL2_BAND   // the roll's row where the sprites' band starts (4 rows); this variant's roll has a blank row after each line of an entry
#else
#define CR_BAND       14      // the roll's row where the sprites' band starts (4 rows)
#endif
#define CR_T_P       100      // the patrons' OBJ tiles: 3 variants x 6 (OBJ ids 100-117, in dgag.c's patron range)
#define CR_T_D        56      // Dregs's 8 OBJ tiles
#define CR_T_HAT      64      // the topper (8x16)
#ifdef CREDITS_SCROLL
#define CR_T_BOSS    146      // BG ids: the boss's tile pairs (top, bottom; 29 at most, 58 tiles); the scroll's own slot (portraits 93-145: 53 tiles at most, boss 146-203, DMG text 204-255)
#else
#define CR_T_BOSS    100      // BG ids: the boss's tile pairs (top, bottom; 30 at most, 60 tiles)
#endif
#define CR_RING_T     93      // BG ids of the roll's text: a ring of CT_RING tiles (the roll shows no portrait or boss)
#define CR_HDR_T     160      // the venue header's tiles (17 at most), kept through its venue's three cards
#define CR_TXT_T     178      // a card's text tiles, up to 255
#define CR_BT_X      120      // the Spigoteer's left edge in the roll; the robots stand at 24, 56, 88
#define OBJPAL_ROBOT   5
#define OBJPAL_CAST    3      // Dregs's, the topper's
#define BGPAL_BOSS     5
#define BGPAL_HDR      6      // the venue header's BG palette (CGB): a copy of the HUD's, the fades leave it alone within a venue
#define COL_GOLD  0x231E      // RGB15(30, 24, 8): the labels of CREDITS=SCROLL (palette 0 colour 1)
#define COL_BAND  0x2043      // RGB15(3, 2, 8): the band (colour 3 of the HUD palette), the bosses' colour 0
#define DMG_HAT_OBP1  0x93    // the topper on the band: its three shades one step lighter (idx 1 white, 2 light, 3 dark; the DMG boss body is remapped the same way)

#define CR_CARDS      33      // the title, the Spigoteer, Dregs, then three cards for each of the ten venues
#define CR_SHARE      392     // the tune's units: 1/392 of it (24.7 frames of the 162 s tune)
#define CR_UNIT_PAT    11     // a patron card's units (owner Q80: held longer, to read all eight names); the other cards 7
#define CR_UNIT_END   362     // the roll ends at this unit, "THANKS FOR PLAYING!" fills the rest
#define CR_PIC_FRAMES 9692    // the cast and the roll run on their own clock: this many frames (162 s). The tune is 9986 frames (166 s): the roll waits for it to end (credits_update; owner 2026-11-05: the tune is never stretched to fit)

// state in story_scratch
#ifdef CREDITS_SCROLL
// CREDITS=SCROLL (a playtest variant, owner 2026-11-05: "instead of flashing between cards we scroll the whole thing"): one continuous vertical roll
// of the same cards (the cast, then the text roll), no fade between them. See the block "the scrolling credits" below. 1 px every 2 frames.
struct cr_state {
    uint8_t row[20];          // the row being built (queued rows are read at VBlank)
    uint16_t scroll;          // world px scrolled, as the picture shows it (SCY moves in the VBlank only)
    uint16_t pos;             // the timeline's position (px): scroll catches up with it in the VBlank
    uint16_t next;            // the next world row to build
    uint16_t t;               // frames on the screen
    uint16_t gs;              // the world row card gc starts at
    uint16_t wroll;           // the world row the roll's own row 0 stands on
    uint16_t lw;              // the world row the text step is building
    uint16_t ss;              // the world row card sc (the sprites' cursor) starts at
    uint16_t ts;              // the world row the stop's card (k) starts at
    uint16_t ph;              // frames in the timeline's state
    uint8_t from_story, gc, gl, sc, live, pb, pp, bn, bp, pose, ft, ls, rt, ld, lr, skipq, txs, txd, phase, pq, pr;
    uint8_t k, st, nc, rr;    // the timeline: the stop's card, its state (0 hold, 1 glide, 2 the text roll, 3 its end), the glide's cruise frames and the px its ramps leave over
    // gc: the card being built (33: the roll), gl: its loads done (units; 255: all), live: the colours go to the hardware as they are made, pb / pp: the portrait's first BG tile / BG palette,
    // rt: the text ring's next tile
};
#else
struct cr_state {
    uint8_t row[20];          // the row being built (queued rows are read at VBlank)
    uint16_t scroll;          // px scrolled
    uint8_t card;             // the card shown (255: none yet; 200: the roll's rows being written, 201: the roll)
    uint8_t next;             // the next world row to write
    uint16_t t;               // frames on the screen
    uint8_t phase;            // 1 clearing, 2 loading, 3 rows, 4 built, 5 shown (a card)
    uint8_t from_story;       // 1: story_end follows
    uint16_t f;               // the position in the tune's frames (cr_pos)
    uint8_t pad;              // (keeps the fields below where the tests read them)
    uint32_t tmask, amask;    // rows (bit y) the last card wrote: their tiles, and their CGB attributes
    uint16_t T;               // the tune's frames
    uint16_t e_title, card_len, roll, f1;   // the timeline's boundaries (frames): the title card ends, a card's length, the roll starts, its scroll ends
    uint8_t k;                // the scroll's speed: px = frames * k / 32
    uint8_t bn, bp, pose;     // the boss card: his columns, his tile pairs, the pose drawn
    uint8_t ft;               // the frame (sys_time) of the build's last tick
    uint8_t ls;               // sys_time at the last update (the frames on the screen, t, are counted from it: a build or a fade is several)
    uint8_t tn;               // the card's next text tile id
    uint8_t rt;               // the roll's ring: the next tile
    uint8_t ld;               // the roll row being built: its cells done
    uint8_t lr;               // ... which row (255: none)
    uint8_t ky;               // the card's key row (its content block is centred vertically from it)
    uint8_t skipq;            // B / START came down during a build
    uint16_t pl;              // a patron card's length (frames)
};
#endif
#define CR ((struct cr_state *)story_scratch)
// (story_scratch + 68 / + 69: the DMG header's BGP and the card's, main.c cast_isr)
#define CR_PAL ((uint8_t *)story_scratch + 72)                          // the card's colours (CGB: 128 bytes; DMG: BGP, OBP0, OBP1, the first OBP1)
#define CR_PT  ((portrait_t *)(story_scratch + 200))                    // the owner's portrait (while a venue card is built)
#define CR_BUF ((uint8_t *)story_scratch + 200 + sizeof(portrait_t))    // 64 bytes: four tiles on their way, the owner's name
#define CR_ATT (CR_BUF + 64)      // CREDITS=SCROLL: the row's CGB attributes (20 bytes), then the Spigoteer's OBJ palette 0 (8 bytes)
#define CR_SAVE (CR_ATT + 20)
typedef char cr_fits[(sizeof(struct cr_state) <= 68 && 200 + sizeof(portrait_t) + 64 + 28 <= STORY_SCRATCH) ? 1 : -1];

#ifndef CREDITS_SCROLL
#define CR_F0   (CR->roll + 40)
#endif

// ---- the cast: the names are in tools/gen_credits.py (pre-rendered); the owners' portraits are the story's speakers' ----
static const uint8_t cr_owner[10] = { 2, 3, 4, 5, 6, 7, 11, 8, 10, 9 };   // the venue owner's speaker id (tools/gen_story.py SPEAKERS): Sadie, Coach, June, Colby, Aurora, Manager-Bot, Granny, Hana, Kiki, Zizz
static const uint8_t cr_hat_dx[10] = { 16, 8, 12, 9, 9, 8, 16, 16, 6, 12 };   // boss.c rows[]: the topper's x from his left edge
static const uint8_t cr_walk[4] = { BT_WALK1, BT_IDLE, BT_WALK2, BT_IDLE };   // the pair's walk cycle (po.c walk_cycle's)
static const uint8_t cr_seq[8] = { 0, 1, 0, 2, 0, 1, 0, 2 };      // the boss's poses (WALK, STOMP, GULP: boss.h BP_*), 16 frames each
uint8_t boss_big_tex_cast(uint8_t cmd, uint8_t a, uint8_t b, uint8_t *dst) BANKED;      // each boss file's cast accessor (src/boss_load.h BOSS_CAST_FN)
uint8_t boss_mascot_cast(uint8_t cmd, uint8_t a, uint8_t b, uint8_t *dst) BANKED;
uint8_t boss_sasquatch_cast(uint8_t cmd, uint8_t a, uint8_t b, uint8_t *dst) BANKED;
uint8_t boss_critic_cast(uint8_t cmd, uint8_t a, uint8_t b, uint8_t *dst) BANKED;
uint8_t boss_yeti_cast(uint8_t cmd, uint8_t a, uint8_t b, uint8_t *dst) BANKED;
uint8_t boss_prototype_cast(uint8_t cmd, uint8_t a, uint8_t b, uint8_t *dst) BANKED;
uint8_t boss_duke_cast(uint8_t cmd, uint8_t a, uint8_t b, uint8_t *dst) BANKED;
uint8_t boss_sumo_cast(uint8_t cmd, uint8_t a, uint8_t b, uint8_t *dst) BANKED;
uint8_t boss_leo_cast(uint8_t cmd, uint8_t a, uint8_t b, uint8_t *dst) BANKED;
uint8_t boss_mothership_cast(uint8_t cmd, uint8_t a, uint8_t b, uint8_t *dst) BANKED;

// his body for the card from his own art file (the fight's tiles, poses, topper and colours): cmd 0: body chunk a (4 tiles) to dst, the tiles
// copied; 1: the column b of pose a: its tile pair; 2: the topper's four tiles to dst; 3: dst = columns, pairs, then his colours 1-3 (3 x LE)
static uint8_t cr_boss(uint8_t v, uint8_t cmd, uint8_t a, uint8_t b, uint8_t *dst) {
    switch (v) {
    case 0: return boss_big_tex_cast(cmd, a, b, dst);
    case 1: return boss_mascot_cast(cmd, a, b, dst);
    case 2: return boss_sasquatch_cast(cmd, a, b, dst);
    case 3: return boss_critic_cast(cmd, a, b, dst);
    case 4: return boss_yeti_cast(cmd, a, b, dst);
    case 5: return boss_prototype_cast(cmd, a, b, dst);
    case 6: return boss_duke_cast(cmd, a, b, dst);
    case 7: return boss_sumo_cast(cmd, a, b, dst);
    case 8: return boss_leo_cast(cmd, a, b, dst);
    }
    return boss_mothership_cast(cmd, a, b, dst);
}

#ifdef CREDITS_SCROLL
#define CR_N CT_ROLL2_N
#define CR_ROLL ct_roll2
#define CR_LAST_T ((CR_FIRST + (CR_N - 2)) * 8 + 4 - 72)   // the scroll at which the last three rows (a blank between the lines) are in the middle of the screen
#else
#define CR_N CT_ROLL_N
#define CR_ROLL ct_roll
#define CR_LAST_T ((CR_FIRST + (CR_N - 2)) * 8 + 8 - 72)   // the scroll at which the last two rows are in the middle of the screen
#endif

static void cr_blank(void) { uint8_t i; for (i = 0; i < 20; i++) CR->row[i] = TILE_HUD_BLANK; }

static void cr_pp(void);
static void cr_put(uint8_t y) {                   // a row of the map (LCD off: the project's own fast copy; on: the library's, which waits for the picture)
    if (LCDC_REG & LCDCF_ON) set_bkg_tiles(0, y, 20, 1, CR->row);
    else vram_put(0, y, CR->row, 20);
}

// the map row for world row w (blank before the roll and after it) into CR->row, its pre-rendered tiles written to the ring (at most `max` a call: one
// is a twentieth of a frame with the LCD on); 1: the row is complete
static uint8_t cr_roll_step(uint8_t w, uint8_t max) {
    uint8_t r, n, i, id;
    uint16_t *cell = (uint16_t *)(CR_BUF + 2);
    if (CR->lr != w) {
        CR->lr = w; CR->ld = 0;
        cr_blank();
        r = w >= CR_FIRST && (uint8_t)(w - CR_FIRST) < CR_N ? CR_ROLL[w - CR_FIRST] : 255;
        if (r == 255) CR_BUF[1] = 0;
        else credits_row_get(r, CR_BUF);
    }
    n = CR_BUF[1];
    while (CR->ld < n && max) {
        i = CR->ld++;
        if (cell[i] == 0xFFFF) continue;
        id = CR_RING_T + CR->rt;
        if (++CR->rt == CT_RING) CR->rt = 0;
        credits_tile_put(cell[i], id);
        CR->row[CR_BUF[0] + i] = id;
        max--;
    }
    return CR->ld >= n;
}

#ifndef CREDITS_SCROLL
static void cr_rows(uint8_t y, uint8_t n) {       // n rows from row y of the roll's rows, ring slot y & 31 (the build: the tune ticked between tiles)
    uint8_t d;
    for (; n; n--, y++) {
        do { d = cr_roll_step(y, 1); cr_pp(); } while (!d);
        cr_put(y & 31);
    }
}

#endif

#ifndef CREDITS_SCROLL
// ---- the tune's position, in frames ---------------------------------------------------------------------------------------------------
static uint16_t cr_pos(void) {
    if (sound_on && cur_tune == TUNE_CREDITS) return music_frames;   // the frames the engine has ticked since the tune began: its real position, whatever its tempo does
    return CR->t;
}

static uint16_t cr_share(uint16_t units) {        // units / 352 of the tune (16-bit maths: the library's long multiply and divide would not fit ROM0)
    uint16_t q = CR->T / CR_SHARE, r = CR->T - q * CR_SHARE;
    return q * units + ((r >> 3) * units) / (CR_SHARE >> 3);
}

#endif

// ---- the card's colours: in RAM, faded to the hardware by trans.c ----------------------------------------------------------------------
#ifdef CREDITS_SCROLL
// CGB: palette i of the BG (obj 0) or OBJ (1) set, from CR_PAL to the hardware, a byte at a time in the first HBlank or VBlank there is (mode 0 or 1: STAT bit 1 clear;
// the write follows within 8 cycles, inside the next mode 0 / 2 at worst, and palette RAM is shut in mode 3 only)
static void cr_hw(uint8_t obj, uint8_t i) {
    uint8_t *s = CR_PAL + (obj ? 64 : 0) + 8 * i, k;
    CRITICAL { if (obj) OCPS_REG = 0x80 | (uint8_t)(i << 3); else BCPS_REG = 0x80 | (uint8_t)(i << 3); }
    for (k = 0; k < 8; k++) CRITICAL { while (STAT_REG & 2) ; if (obj) OCPD_REG = s[k]; else BCPD_REG = s[k]; }
}
#endif
static void cr_pal(uint8_t obj, uint8_t i, const uint16_t *p) {   // CGB: palette i of the BG (obj 0) or OBJ (1) set
    uint16_t *q = (uint16_t *)(CR_PAL + (obj ? 64 : 0) + i * 8);
    q[0] = BRIGHTEN(p[0]); q[1] = BRIGHTEN(p[1]); q[2] = BRIGHTEN(p[2]); q[3] = BRIGHTEN(p[3]);   // (SCREEN BRIGHT: lifted once, here; trans.c fades them in as they are)
#ifdef CREDITS_SCROLL
    if (CR->live) cr_hw(obj, i);                      // (the scroll: no fade, a card's colours go on as they are made; nothing on the screen uses that palette: see cr_gen)
#endif
}

// ---- the tune's time through a build: one tick a frame, the first call after line 18 (as the loop's and the fades': a unit is a fraction of a frame, so a
// tick is that late at most), B / START noted. The build begins with this frame's tick still to come, and ends at the top of the next frame
// (cr_sync), where the fade's first tick (line 18) follows one frame later: no tick is lost or doubled at either seam. ---------------------------------
#define TICK_LY 18
static void cr_pp(void) {
    uint8_t ly = LY_REG;
    if (ly >= TICK_LY && ly < 144 && (uint8_t)sys_time != CR->ft) { CR->ft = (uint8_t)sys_time; music_tick(); }
    if (joypad() & (J_B | J_START)) CR->skipq = 1;
}

static void cr_begin(void) { CR->ft = (uint8_t)sys_time - 1; CR->skipq = 0; }

static void cr_sync(void) {                       // the build ends: this frame's tick made (a call that missed its window makes it now), then the next frame's top, so that the fade's tick there (its start needs line < 18) is one frame on
    uint8_t ly = LY_REG;
    if ((uint8_t)sys_time != CR->ft && ly >= TICK_LY && ly < 144) { CR->ft = (uint8_t)sys_time; music_tick(); }
    while ((uint8_t)sys_time == CR->ft) ;
    while (LY_REG >= TICK_LY) ;
}

// ---- sprites --------------------------------------------------------------------------------------------------------------------------
static void cr_oam(uint8_t n, int16_t y, uint8_t x, uint8_t tile, uint8_t prop) {   // y: OAM y; off the screen: hidden
    OAM_item_t *o = shadow_OAM + n;
    if (y < 1 || y > 159) { o->y = 0; return; }
    o->y = (uint8_t)y; o->x = x; o->tile = tile; o->prop = prop;
}

static void cr_fig(uint8_t n, int16_t y, uint8_t x, uint8_t base, uint8_t prop, uint8_t flip) {   // the Spigoteer's four entries (x: left edge)
    uint8_t a = flip ? 2 : 0, b = flip ? 0 : 2, p = flip ? prop | S_FLIPX : prop;
    cr_oam(n, y, x + 8, base + a, p);
    cr_oam(n + 1, y, x + 16, base + b, p);
    cr_oam(n + 2, y + 16, x + 8, base + 4 + a, p);
    cr_oam(n + 3, y + 16, x + 16, base + 4 + b, p);
}

#ifndef CREDITS_SCROLL
static void cr_sprites(void) {                    // the roll's band
    int16_t y = (int16_t)(CR_FIRST + CR_BAND) * 8 - CR->scroll + 16;   // the band's top, OAM y
    uint8_t t = (uint8_t)CR->t, k, f, bob;
    for (k = 0; k < 3; k++) {                         // the robots, bobbing in turn (2 px up for 16 frames in every 64)
        bob = (((t >> 4) + k) & 3) ? 0 : 2;
        cr_oam(4 + 2 * k, y + 8 - bob, 24 + 32 * k + 8, CR_T_P + 6 * k, is_cgb ? OBJPAL_ROBOT + k : 0);
        cr_oam(5 + 2 * k, y + 8 - bob, 24 + 32 * k + 16, CR_T_P + 6 * k + 2, is_cgb ? OBJPAL_ROBOT + k : 0);
    }
    f = ((t >> 4) & 3) == 1 ? BT_CATCH : BT_IDLE;     // the Spigoteer: a hand up now and then
    cr_fig(0, y, CR_BT_X, OBJ_BARTENDER + BT_PIC(f) * BARTENDER_TILES_PER_FRAME, OBJPAL_BARTENDER, 0);
}

#endif

// ---- the cards ------------------------------------------------------------------------------------------------------------------------
// card c: 0 the title, 1 the Spigoteer, 2 Dregs (portrait and sprite), then venue by venue three cards: 3 + 3v the owner (portrait, name, venue),
// 4 + 3v the patrons (the venue, three with a label each), 5 + 3v the boss (animated on the band, his name, the venue).
// Writing VRAM with the LCD on is slow (the library waits for the picture's blanking for every byte): a card is built in UNITS, CR_UNITS a
// frame (a row, a few tiles), so that no frame runs over its VBlank and the tune never loses a tick. Stage 1 blanks the rows the last card
// used, stage 2 loads, stage 3 writes the rows; then the card fades in.
enum { CK_TITLE, CK_SPIGOTEER, CK_DREGS, CK_OWNER, CK_PATRONS, CK_BOSS };
#ifdef CREDITS_SCROLL
static const uint8_t cr_kt[CR_CARDS] = { 0, 1, 2, 3, 4, 5, 3, 4, 5, 3, 4, 5, 3, 4, 5, 3, 4, 5, 3, 4, 5, 3, 4, 5, 3, 4, 5, 3, 4, 5, 3, 4, 5 };   // (tables: the scroll asks every frame, and a divide by 3 is 300 cycles)
static const uint8_t cr_vt[CR_CARDS] = { 0, 0, 0, 0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 6, 7, 7, 7, 8, 8, 8, 9, 9, 9 };
static uint8_t cr_kind(uint8_t c, uint8_t *v) { *v = cr_vt[c]; return cr_kt[c]; }
#else
static uint8_t cr_kind(uint8_t c, uint8_t *v) {    // the card's kind, and its venue
    if (c < 3) return c;
    c -= 3;
    *v = c / 3;
    return CK_OWNER + c % 3;
}
#endif

#ifndef CREDITS_SCROLL
static void cr_mark(uint8_t y) { CR->tmask |= 1UL << y; }   // (card rows: 0-17)
static void cr_amark(uint8_t y) { CR->amask |= 1UL << y; }

static void cr_put_card(uint8_t y) { cr_put(y); cr_mark(y); }

static uint8_t cr_clear_unit(void) {              // one row of what the last card wrote; 1: none left
    uint8_t y, i;
    if (CR->tmask) {
        for (y = 0; !((CR->tmask >> y) & 1); y++) ;
        CR->tmask &= ~(1UL << y);
        cr_blank();
        cr_put(y);
        return 0;
    }
    if (CR->amask) {                               // the last card's CGB attributes: the HUD's again
        for (y = 0; !((CR->amask >> y) & 1); y++) ;
        CR->amask &= ~(1UL << y);
        for (i = 0; i < 20; i++) CR->row[i] = BGPAL_HUD;
        VBK_REG = VBK_BANK_1;
        cr_put(y);
        VBK_REG = VBK_BANK_0;
        return 0;
    }
    return 1;
}

#endif

static void cr_remap(uint8_t *b, uint8_t n) {     // DMG: n bytes of tiles with the shades one step on (0 -> 3, the band; 1 -> 0; 2 -> 1; 3 -> 2): v - 1, a plane at a time
    uint8_t i, lo;
    for (i = 0; i < n; i += 2) {
        lo = ~b[i];                                   // (the low bit always flips; the high bit with it where the low bit was 0)
        b[i + 1] ^= lo;
        b[i] = lo;
    }
}

static uint8_t cr_spk(uint8_t c, uint8_t v) { return c == CK_SPIGOTEER ? 0 : c == CK_DREGS ? 1 : cr_owner[v]; }

#ifdef CREDITS_SCROLL
#define PBASE (CR->pb)
#define PPAL  (CR->pp)
#define OBJPAL_TOP 0       // the topper's OBJ palette: 0 (the Spigoteer's, restored before the roll), as patrons use 1-7 and the next card's patrons are on the screen with a boss
#else
#define PBASE STORY_PORTRAIT_BASE
#define PPAL  BGPAL_PATRON
#define OBJPAL_TOP OBJPAL_CAST
#endif
static uint8_t cr_load_unit(uint8_t c, uint8_t i) {   // unit i of card c's loads; 1: there are no more
    uint8_t v = 0, k, n, nch, kd = cr_kind(c, &v), *buf = CR_BUF;
    uint16_t p[4], bg;
    portrait_t *pt = CR_PT;
    if (kd == CK_SPIGOTEER || kd == CK_DREGS || kd == CK_OWNER) {
        k = cr_spk(kd, v);
        if (i < 2) { portrait_part(k, i, pt); return 0; }   // the portrait: its header and map, its attributes (portrait_get pumps the timer for over a frame)
        if (i == 2) {                              // its palettes (BG 2-4), the backdrop's colour (the slot of its DMG shade, portrait_backdrop: the top-left tile is all backdrop) the band's
            portrait_part(k, 2, pt);
            if (is_cgb) {
                nch = portrait_backdrop(k);           // (shade 3 backdrop: the outline's colour goes to the band's too, as the story scenes' black backdrop shows it)
                bg = pt->pal[4 * pt->attr[0] + nch];
                for (n = 0; n < pt->npal; n++) {
                    p[0] = pt->pal[4 * n]; p[1] = pt->pal[4 * n + 1]; p[2] = pt->pal[4 * n + 2]; p[3] = pt->pal[4 * n + 3];
                    if (p[nch] == bg) p[nch] = COL_BAND;
                    cr_pal(0, PPAL + n, p);
                }
#ifdef CREDITS_SCROLL
                if (kd == CK_OWNER) {                  // BG palette 0: the labels (colour 1: gold) and the band (colour 2: the venue's); the HUD's colours 0 and 3 (they are brightened already)
                    uint16_t *q = (uint16_t *)CR_PAL, *hq = (uint16_t *)(CR_PAL + 8 * BGPAL_HUD);
                    q[0] = hq[0]; q[1] = BRIGHTEN(COL_GOLD); q[2] = BRIGHTEN(ct_bandcol[v]); q[3] = hq[3];
                    if (CR->live) cr_hw(0, 0);
                }
#endif
            }
            return 0;
        }
        i -= 3;
        nch = pt->ntiles;
        if (i < nch) {                             // its tiles, one a unit (a byte loop in C is ~70 cycles a byte, a tile 0.07 frame)
            if (is_cgb) portrait_tile_set(k, i, PBASE + i);
            else {
                portrait_tile_copy(k, i, 1, buf);
                nch = portrait_backdrop(k);        // DMG: the backdrop becomes the band's shade 3: 3 stays, 2 and 3 change places (lo ^= hi), 1 and 3 (hi ^= lo); the generator refuses shade 0
                if (nch == 2) for (n = 0; n < 16; n += 2) buf[n] ^= buf[n + 1];
                else if (nch == 1) for (n = 0; n < 16; n += 2) buf[n + 1] ^= buf[n];
                set_bkg_data(PBASE + i, 1, buf);
            }
            return 0;
        }
        if (kd == CK_DREGS && i < nch + 24) {      // his three frames (idle, walk, walk: 24 tiles), a tile at a time, and his palette
            i -= nch;
            dregs_cast_load(CR_T_D, i, 1, p);
            if (is_cgb) cr_pal(1, OBJPAL_CAST, p);
            return 0;
        }
        return 1;
    } else if (kd == CK_BOSS) {
        if (i == 0) {                              // his size and colours; the BG palette 5 with the band as colour 0, the topper's OBJ 3
            cr_boss(v, 3, 0, 0, buf);
            CR->bn = buf[0]; CR->bp = buf[1];
            if (is_cgb) {
                p[0] = COL_BAND; p[1] = buf[2] | buf[3] << 8; p[2] = buf[4] | buf[5] << 8; p[3] = buf[6] | buf[7] << 8;
                cr_pal(0, BGPAL_BOSS, p);
                p[0] = 0;
                cr_pal(1, OBJPAL_TOP, p);
            }
            return 0;
        }
        if (i < 5) { cr_boss(v, 5, i - 1, CR_T_HAT + i - 1, 0); return 0; }   // the topper: still and bobbing (4 tiles, one a unit)
        i -= 5;
        if (i >= CR->bp * 2) return 1;
        if (is_cgb) cr_boss(v, 4, i, CR_T_BOSS + i, 0);       // his body's tiles, a unit each, straight to VRAM
        else {                                     // (DMG: the shades one step on)
            cr_boss(v, 0, i, 0, buf);
            cr_remap(buf, 16);
            set_bkg_data(CR_T_BOSS + i, 1, buf);
        }
        return 0;
    } else if (kd == CK_PATRONS) {
        n = is_cgb ? 38 : 18;                      // the three base looks' 18 tiles (bank 0), on Color the five Color-only looks' 20 (bank 1), then the palettes
#ifdef CREDITS_SCROLL
        if (i >= n + (is_cgb ? 7 : 0)) return 1;
#else
        if (i > n) return 1;
#endif
        if (i < 18) load_patron_pose0(v, CR_T_P + 6 * (i / 6), ct_slot[v][i / 6], i % 6);      // (a tile at a time: with the LCD on a byte takes two scanlines; the variant in slot k)
        else if (i < n) load_patron_x0(v, (i - 18) >> 2, (i - 18) & 3);
#ifdef CREDITS_SCROLL
        else if (is_cgb) {                         // OBJ 1-7, one a unit (the hardware's: the HBlanks it takes)
            k = i - n;
            p[0] = 0; p[1] = ct_pcol[v][k][0]; p[2] = ct_pcol[v][k][1]; p[3] = ct_pcol[v][k][2];
            cr_pal(1, 1 + k, p);
        }
#else
        else if (is_cgb) for (k = 0; k < 7; k++) {   // OBJ 1-7: the venue's distinct looks' colours from the plan (OBJ 0 stays the Spigoteer's, for the roll)
            p[0] = 0; p[1] = ct_pcol[v][k][0]; p[2] = ct_pcol[v][k][1]; p[3] = ct_pcol[v][k][2];
            cr_pal(1, 1 + k, p);
        }
#endif
        return 0;
    }
    return 1;
}

#ifndef CREDITS_SCROLL
static void cr_pose_rows(uint8_t v, uint8_t pose, uint8_t q) {   // the boss's two rows in a pose; q: queued for the next VBlank (a card that is up), else written now
    uint8_t r, k, L = (20 - CR->bn) >> 1, *d;
    for (r = 0; r < 2; r++) {
        d = q ? (uint8_t *)CR_BUF + 20 * r : CR->row;
        for (k = 0; k < 20; k++) d[k] = TILE_HUD_BLANK;
        for (k = 0; k < CR->bn; k++) d[L + k] = CR_T_BOSS + 2 * cr_boss(v, 1, pose, k, 0) + r;
        if (q) vq_add(0, d, 0, CR->ky + r, 20);
        else cr_put_card(CR->ky + r);
    }
    CR->pose = pose;
}

// a pre-rendered text row r at map row y: its tiles to ids from *id on (one a call of the writer, the tune ticked between), a blank cell where it is empty
static void cr_trow(uint8_t r, uint8_t y, uint8_t *id) {
    uint8_t n, i, c, *d = CR_BUF;
    uint16_t *cell = (uint16_t *)(d + 2);
    cr_blank();
    n = credits_row_get(r, d);
    c = d[0];
    for (i = 0; i < n; i++) {
        if (cell[i] == 0xFFFF) continue;
        credits_tile_put(cell[i], *id);
        CR->row[c + i] = (*id)++;
        cr_pp();
    }
    cr_put_card(y);
}

static void cr_header(uint8_t v, uint8_t step) {   // the venue's name in the top strip (its text on row 1, the cells of both rows BG palette 6), or none (v 255); a row a step
    uint8_t k, id = CR_HDR_T;
    if (!step) {
        if (v < 10) { cr_trow(CT_HDR + v, 1, &id); CR->tmask &= ~2UL; }   // (the header is not the card's: it stays through the venue)
        else { cr_blank(); cr_put(1); }
    } else if (is_cgb) {
        for (k = 0; k < 20; k++) CR->row[k] = v < 10 ? BGPAL_HDR : BGPAL_HUD;
        VBK_REG = VBK_BANK_1; cr_put(step - 1); VBK_REG = VBK_BANK_0;
    }
}

// The cards' content is centred vertically in the space under the header (rows 2-17, or the whole screen without one): the key row is where the block
// starts. Heights (px), design, from the ink: the pair (portrait h rows, 2 blank rows, the text rows with the sprite beside them) 8 h + 40; an owner
// (portrait, 2 blank rows, the name) 8 h + 24; the patrons (the sprites, a row of air, the label row) 32; the boss (the topper, the body,
// a blank row, his name) 48.
static uint8_t cr_key(uint8_t kd, uint8_t v, uint8_t h) {
    switch (kd) {
    case CK_TITLE: return 8;                       // (rows 8 and 10, the screen scrolled 4 px: the block's ink centred on the screen's middle)
    case CK_SPIGOTEER: case CK_DREGS: return (uint8_t)(112 - 8 * h) >> 4;   // the portrait's first row
    case CK_OWNER: return (uint8_t)(20 + ((104 - 8 * h) >> 1)) >> 3;
    case CK_PATRONS: return 11;                                            // the label row
    }
    return 8;                                      // the boss's body rows
}

static uint8_t cr_show_unit(uint8_t c, uint8_t i) {   // unit i of card c's rows; 1: there are no more
    uint8_t k, v = 0, L, n, h, kd = cr_kind(c, &v), x, id = CR->tn;
    portrait_t *pt = CR_PT;
    CR->ky = cr_key(kd, v, pt->h);
    if (kd == CK_TITLE) {
        if (i >= 2) return 1;
        cr_trow(CT_TITLE + i, 8 + 2 * i, &id);
    } else if (kd <= CK_OWNER) {                   // a person: the portrait (centred), under it the owner's name, or the pair: sprite and two lines
        h = pt->h;
        x = CR->ky;                                // the portrait's first row
        L = (20 - pt->w) >> 1;
        n = kd == CK_OWNER ? 1 : 2;                // the text units
        if (i < n) {
            if (kd == CK_OWNER) cr_trow(CT_OWNER + v, x + h + 2, &id);
            else cr_trow((kd == CK_SPIGOTEER ? CT_SAL : CT_DREGS) + i, x + h + 2 + 2 * i, &id);
            CR->tn = id;
            return 0;
        }
        i -= n;
        if (i < h) {                               // a portrait row
            for (k = 0; k < 20; k++) CR->row[k] = TILE_HUD_BLANK;
            for (k = 0; k < pt->w; k++) CR->row[L + k] = STORY_PORTRAIT_BASE + pt->map[i * pt->w + k];
            cr_put_card(x + i);
            return 0;
        }
        i -= h;
        if (!is_cgb || i >= h) return 1;
        for (k = 0; k < 20; k++) CR->row[k] = BGPAL_HUD;   // their attributes (CGB)
        for (k = 0; k < pt->w; k++) CR->row[L + k] = BGPAL_PATRON + pt->attr[i * pt->w + k];
        VBK_REG = VBK_BANK_1; cr_put(x + i); VBK_REG = VBK_BANK_0;
        cr_amark(x + i);
    } else if (kd == CK_BOSS) {                    // the body (two rows) with the topper above, his name 4 rows under it; the venue is in the header
        n = CR->bn;
        L = (20 - n) >> 1;
        if (i < 1) cr_trow(CT_BOSS + v, CR->ky + 4, &id);
        else if (i < 3) { if (i == 1) cr_pose_rows(v, 0, 0); }
        else {
            if (!is_cgb || i >= 5) return 1;
            for (k = 0; k < 20; k++) CR->row[k] = BGPAL_HUD;
            for (k = 0; k < n; k++) CR->row[L + k] = BGPAL_BOSS;
            VBK_REG = VBK_BANK_1; cr_put(CR->ky + i - 3); VBK_REG = VBK_BANK_0;
            cr_amark(CR->ky + i - 3);
        }
    } else {                                       // the patrons (the venue is in the header): DMG the three labels on one row, Color three rows (3, 3, 2) at tile rows 6, 11, 16
        if (i == 0 || (is_cgb && i < 3)) cr_trow(CT_PATA + 10 * i + v, is_cgb ? 6 + 5 * i : CR->ky, &id);
        else return 1;
    }
    CR->tn = id;
    return 0;
}

static void cr_card_sprites(uint8_t c) {          // every frame a card is shown
    uint8_t t = (uint8_t)CR->t, k, bob, v = 0, kd = cr_kind(c, &v), pose, y, n;
    if (kd == CK_SPIGOTEER || kd == CK_DREGS) {    // his walk cycle (walk, idle, the other foot, idle: 16 frames each), at the text's left, level with it
        pose = cr_walk[(t >> 4) & 3];
        y = 8 * (CR->ky + CR_PT->h + 2) + 12;      // (OAM y: the sprite's top 4 px above the first text row's, so that it stands level with the two lines)
        if (kd == CK_SPIGOTEER) cr_fig(0, y, CT_SAL_X, OBJ_BARTENDER + BT_PIC(pose) * BARTENDER_TILES_PER_FRAME, OBJPAL_BARTENDER, 0);
        else cr_fig(0, y, CT_DREGS_X, CR_T_D + pose * 8, is_cgb ? OBJPAL_CAST : 0, 0);
    } else if (kd == CK_BOSS) {                    // his walk and gulp, the topper bobbing with the stomp
        pose = cr_seq[(t >> 4) & 7];
        if (pose != CR->pose) cr_pose_rows(v, pose, 1);
        cr_oam(0, 8 * CR->ky + 8, ((20 - CR->bn) >> 1) * 8 + cr_hat_dx[v] + 8, CR_T_HAT + (pose == 1 ? 2 : 0), is_cgb ? OBJPAL_CAST : S_PALETTE);
    } else if (kd == CK_PATRONS) {
        for (k = 0; k < (is_cgb ? 8 : 3); k++) {  // the patrons (DMG the three base looks, Color all eight), bobbing in turn, each centred over his own label (ct_cx)
            bob = (((t >> 4) + k) & 3) ? 0 : 2;
            if (is_cgb) {                         // (the label rows are tile rows 6, 11, 16; the sprite's top is 20 px above its row; looks 3-7: bank 1, OBJ tiles PATRON_X_S0 + 4 (k - 3))
                y = 8 * (k < 3 ? 6 : k < 6 ? 11 : 16) - 4 - bob;
                pose = k < 3 ? CR_T_P + 6 * k : PATRON_X_S0 + 4 * (k - 3);
                n = (1 + ct_lp[v][k]) | (k < 3 ? 0 : 8);
            } else { y = 8 * CR->ky - 8 - bob; pose = CR_T_P + 6 * k; n = 0; }
            cr_oam(2 * k, y, ct_cx[v][k], pose, n);
            cr_oam(2 * k + 1, y, ct_cx[v][k] + 8, pose + 2, n);
        }
    }
}

#endif

// The screen goes white (the fade, trans.c trans_cast), the card is built behind it unit by unit (the LCD stays on: the header must not blink), the card
// fades in from white. The tune is pumped (the timer, polled) through the build.
static void cr_white(void) {                      // LCD off: every palette white
    uint8_t i;
    if (is_cgb) {
        BCPS_REG = 0x80; OCPS_REG = 0x80;
        for (i = 0; i < 32; i++) { BCPD_REG = 0xFF; BCPD_REG = 0x7F; OCPD_REG = 0xFF; OCPD_REG = 0x7F; }
    } else BGP_REG = OBP0_REG = OBP1_REG = 0;
}

#ifndef CREDITS_SCROLL
static uint8_t cr_hdr(uint8_t a, uint8_t b) {     // 1: the header (a venue's name) comes or goes between cards a and b (255: none; 200 and over: the roll): it fades with them
    return a < 3 || b < 3 || a >= CR_CARDS || b >= CR_CARDS || (uint8_t)((a - 3) / 3) != (uint8_t)((b - 3) / 3);
}

static void cr_make(uint8_t c, uint8_t hd, uint8_t old) {   // card c's rows and tiles (hd: its header is new; old: the card before)
    uint8_t i, v = 0;
    cr_begin();
    CR->tn = CR_TXT_T;
    SCY_REG = c ? 0 : 4;                            // (the title card: two lines a row apart, 4 px up to the middle; the screen is white now)
    while (!CR->skipq && !cr_clear_unit()) cr_pp();
    if (hd && !CR->skipq) {
        if (cr_kind(c, &v) < CK_OWNER) v = 255;
        if (v < 10 || (old >= 3 && old < CR_CARDS)) for (i = 0; i < 3; i++) { cr_header(v, i); cr_pp(); }
    }
    for (i = 0; !CR->skipq && !cr_load_unit(c, i); i++) cr_pp();
    for (i = 0; !CR->skipq && !cr_show_unit(c, i); i++) cr_pp();
    cr_sync();
}

#endif

#ifdef CREDITS_SCROLL
// ---- the scrolling credits (CREDITS=SCROLL) ---------------------------------------------------------------------------------------------------
// One world of map rows (row w sits in ring slot w & 31 of the 32-row map; SCY = scroll px): the cards of the cast one under the other, then the text roll (its row 0
// at wroll). The layout is tools/gen_credits.py's LAY (credits_text.h CT_*): a venue is its owner card (a larger gap, the divider, the venue's band, OWNER, the portrait
// and the name), the regulars card (REGULARS, then the patrons in rows of 3, 3 and 2 with a name under each; DMG the middle row) and the boss card (BOSS, the boss, his
// name), with the same gap CT_G between the cards. The timeline is FRAMES (CR->t, from sys_time; no music tick is counted): the screen glides from one stop to the next
// (a block centred on the screen), holds, glides on. A glide is a ramp of speeds (1, 2, 3, 4 px a frame, 4 frames each), a cruise at 4, a ramp down (the px that do not
// divide by 4 are one more frame at that speed in the ramp down: the speeds only ever go up, then down), so a block moves a whole number of px a frame and eases in
// and out in 16 frames (0.27 s) each. The holds: the title 120 frames, the Spigoteer and Dregs 180, a venue's band and owner 180, the regulars 270, the boss 180.
// After the last boss the screen glides to the roll (its first row just under the screen) and the text rolls at 1 px every 2 frames to its end, held 240 frames. The tune
// is not asked about the pace: when it ends it ends (silence), and the roll goes on; the screen is left when the roll has ended and the tune is over.
// Rows are built a frame at a time CR_AHEAD_C rows ahead of the screen (cr_gen: a card's tiles first, 3 units a frame, then its rows, text tiles 3 a frame), and queued
// to the next VBlank (a row 20 + 20 bytes: inside the budget).
// The limits:
//   BG tiles   portraits 93-145 (the Spigoteer's, each owner's: 53 tiles at most, name plate included), the bosses' 146-203 (Dregs's portrait too: he follows the Spigoteer's).
//              The cast's text is a ring of CT_RING_N tiles: DMG BG ids 204-255 then 0-75 (but 54, the blank), Color VRAM bank 1 ids 0-126 (the cells' attribute bit 3).
//              The stripe's tile is BG id 76 (bank 0). A card loads when its load row is built (an owner card's is 6 rows above its divider), up to CR_AHEAD_C rows below the
//              screen's top, and the card that used its slot is off the top by then: the cards of a kind are 33 rows or more apart (the Spigoteer's and the first owner's: 34).
//   BG pal     portraits 2-4 (Dregs 5-7), a boss 5, the text the HUD's 1, 0 the labels (ink colour 1: gold) and the band (stripe colour 2: the venue's): written to the
//              hardware in HBlank / VBlank only (cr_hw) while no cell on the screen uses them (palette 0's colour 2 only changes with the band's venue).
//   OBJ tiles  Dregs 56-79, the toppers 64-67, a venue's three base looks 100-117 (the roll's robots reuse them when the last boss is off), the Color looks in bank 1.
//   OBJ pal    Spigoteer 0, Dregs 3, patrons 1-7 (loaded when their card's rows begin: the card with the last patrons is long off), the topper 0 (after the Spigoteer's
//              card; saved in CR_SAVE and put back before the roll), the robots 5-7. DMG: OBP0 for all, OBP1 the topper's (set at the start).
//   sprites    a patron card: 6 a line at most (3 + 3 of 8x16), a boss 1, the Spigoteer or Dregs 2, the roll 6 + 4: never above 10 with the next card's.
#define CR_AHEAD_R   26     // the same inside the text roll (its ring is BG ids 93-252: they are the portraits' and the bosses' slots, free from the last boss on)
#define CR_AHEAD_C   30     // rows are kept built up to the screen's top row + this (the 32-row map: the row above the top is the last one that may be overwritten)
#define CR_LASTGAP    4     // blank rows from the last card to the roll's row 0
#define CR_STRIPE_ID 76     // the stripe's tile
#define CR_TXT_D    204     // the DMG's text ring: ids 204-255, then 0-75 but 54
#define CR_TXT_DN    52
#define CR_TXT_CN   127     // Color: ids 0-126 of bank 1
#define CR_W0         8     // the world row of the first card (the title): blank rows above it
#define CR_VMAX       4     // the glide's cruise speed (px a frame); the ramps take CR_VLEN frames at each speed 1..CR_VMAX
#define CR_VLEN       4
#define CR_RAMP      40     // the px of one ramp: 4 * (1 + 2 + 3 + 4)
#define CR_END_HOLD 240     // the roll's end is held this many frames

static uint8_t cr_hgt(uint8_t c) {                // a card's rows
    uint8_t v = 0, kd;
    if (c >= CR_CARDS) return 0;
    kd = cr_kind(c, &v);
    return kd == CK_TITLE ? CT_H_TITLE : kd <= CK_DREGS ? CT_H_SD : kd == CK_OWNER ? CT_H_OWN : kd == CK_BOSS ? CT_H_BOSS : CT_H_PAT;
}

static uint8_t cr_gap(uint8_t c) { return c == CR_CARDS - 1 ? CR_LASTGAP : c ? CT_G : CT_GAP_TITLE; }

static uint8_t cr_off(uint8_t c) {                // the px from the card's top to the middle of its stop's block
    uint8_t v = 0, kd = cr_kind(c, &v);
    return kd == CK_TITLE ? CT_OFF_TITLE : kd <= CK_DREGS ? CT_OFF_SD : kd == CK_OWNER ? CT_OFF_OWN : kd == CK_BOSS ? CT_OFF_BOSS : CT_OFF_PAT;
}

static uint8_t cr_lrow(uint8_t c) { return cr_kt[c] == CK_OWNER ? CT_R_DIV - 6 : 0; }   // the card's row its loads wait for (an owner's: inside the gap before the divider, early enough for the loads to be done in the hold before; the Spigoteer's portrait slot is 34 rows above it)

static uint16_t cr_hold(uint8_t c) {              // frames
    uint8_t kd = cr_kt[c];
    return kd == CK_TITLE ? 120 : kd == CK_PATRONS ? 270 : 180;
}

static void cr_layout(void) {                     // the roll's row: after every card and its gap
    uint16_t w = CR_W0;
    uint8_t c;
    for (c = 0; c < CR_CARDS; c++) w += cr_hgt(c) + cr_gap(c);
    CR->wroll = w;
}

static void cr_attr_hud(void) { uint8_t i; if (is_cgb) for (i = 0; i < 20; i++) CR_ATT[i] = BGPAL_HUD; }

// a pre-rendered text row r (its tiles to the ring, 3 a call); 1: the row is complete in CR->row (CR_ATT: bank 1 on Color). kd 0: the text, the HUD palette; 1: a label, palette 0;
// 2: a band row, palette 0, the stripe all over but where the name's tiles are
static uint8_t cr_tstep(uint8_t r, uint8_t kd) {
    uint8_t n, i, id, m = 3;
    uint16_t *cell = (uint16_t *)(CR_BUF + 2);
    if (CR->lw != CR->next) {
        CR->lw = CR->next; CR->ld = 0;
        cr_blank(); cr_attr_hud();
        if (kd && is_cgb) for (i = 0; i < 20; i++) CR_ATT[i] = 0;
        if (kd == 2) for (i = 0; i < 20; i++) CR->row[i] = CR_STRIPE_ID;
        credits_row_get(r, CR_BUF);
    }
    n = CR_BUF[1];
    while (CR->ld < n && m) {
        i = CR->ld++;
        if (cell[i] == 0xFFFF) continue;
        if (is_cgb) {
            id = CR->rt;
            if (++CR->rt == CR_TXT_CN) CR->rt = 0;
            VBK_REG = VBK_BANK_1; credits_tile_put(cell[i], id); VBK_REG = VBK_BANK_0;
            CR_ATT[CR_BUF[0] + i] = (kd ? 0 : BGPAL_HUD) | 8;
        } else {
            id = CR->rt;
            if (++CR->rt == CT_RING_N) CR->rt = 0;
            id = id < CR_TXT_DN ? CR_TXT_D + id : id - CR_TXT_DN < 54 ? id - CR_TXT_DN : id - CR_TXT_DN + 1;
            credits_tile_put(cell[i], id);
        }
        CR->row[CR_BUF[0] + i] = id;
        m--;
    }
    return CR->ld >= n;
}

static void cr_pose_fill(uint8_t *d, uint8_t v, uint8_t pose, uint8_t r) {    // the boss's row r (0, 1) in a pose
    uint8_t k, L = (20 - CR->bn) >> 1;
    for (k = 0; k < 20; k++) d[k] = TILE_HUD_BLANK;
    for (k = 0; k < CR->bn; k++) d[L + k] = CR_T_BOSS + 2 * cr_boss(v, 1, pose, k, 0) + r;
}

// card c's local row r into CR->row / CR_ATT; 1: done, 0: call again (a text row's tiles)
static uint8_t cr_card_row(uint8_t c, uint8_t r) {
    uint8_t v = 0, kd = cr_kind(c, &v), tr = 255, tk = 0, k, L, h = CR_PT->h, w = CR_PT->w, i = 255;
    portrait_t *pt = CR_PT;
    if (kd == CK_TITLE) { if (r == 0) tr = CT_TITLE; else if (r == 2) tr = CT_TITLE + 1; }
    else if (kd == CK_SPIGOTEER || kd == CK_DREGS) {
        if (r >= 1 && r < 1 + h) i = r - 1;
        else if (r == 3 + h || r == 5 + h) tr = (kd == CK_SPIGOTEER ? CT_SAL : CT_DREGS) + ((r - 3 - h) >> 1);
    } else if (kd == CK_OWNER) {
        if (r == CT_R_DIV) tr = CT_DIV;
        else if (r >= CT_R_BAND && r < CT_R_BAND + 3) { tr = CT_BAND + 3 * v + r - CT_R_BAND; tk = 2; }
        else if (r == CT_R_OLBL) { tr = CT_LBL; tk = 1; }
        else if (r >= CT_R_PORT && r < CT_R_PORT + h) i = r - CT_R_PORT;
        else if (r == CT_R_PORT + h + 1) tr = CT_OWNER + v;
    } else if (kd == CK_PATRONS) {
        if (r == CT_R_PLBL) { tr = CT_LBL + 1; tk = 1; }
        else if (is_cgb) { if (r == CT_R_PN || r == 2 * CT_R_PN || r == 3 * CT_R_PN) tr = CT_PATA + 10 * (r / CT_R_PN - 1) + v; }
        else if (r == 2 * CT_R_PN) tr = CT_PATA + v;
    } else if (r == CT_R_BLBL) { tr = CT_LBL + 2; tk = 1; }
    else if (r == CT_R_BNAME) tr = CT_BOSS + v;
    if (tr != 255) return cr_tstep(tr, tk);
    cr_blank(); cr_attr_hud();
    if (i != 255) {                                // a portrait row
        L = (20 - w) >> 1;
        for (k = 0; k < w; k++) {
            CR->row[L + k] = CR->pb + pt->map[i * w + k];
            if (is_cgb) CR_ATT[L + k] = CR->pp + pt->attr[i * w + k];
        }
    } else if (kd == CK_BOSS && (r == CT_R_BBODY || r == CT_R_BBODY + 1)) {
        cr_pose_fill(CR->row, v, CR->pose, r - CT_R_BBODY);
        if (is_cgb) { L = (20 - CR->bn) >> 1; for (k = 0; k < CR->bn; k++) CR_ATT[L + k] = BGPAL_BOSS; }
    }
    return 1;
}

// the next world row (CR->next): what loads it needs (a few units a call), then the row; 1: it is queued
static uint8_t cr_gen(void) {
    uint16_t w = CR->next;
    uint8_t c = CR->gc, m, i, v = 0, kd;
    while (c < CR_CARDS && w >= CR->gs + cr_hgt(c) + cr_gap(c)) { CR->gs += cr_hgt(c) + cr_gap(c); c++; CR->gl = 0; }
    CR->gc = c;
    if (c < CR_CARDS && w >= CR->gs && w < CR->gs + cr_hgt(c)) {          // a card's row
        if (CR->gl != 255 && w - CR->gs >= cr_lrow(c)) {
            if (!CR->gl) { CR->pb = c == 2 ? CR_T_BOSS : STORY_PORTRAIT_BASE; CR->pp = c == 2 ? BGPAL_STAGE : BGPAL_PATRON; CR->pose = 0; }
            for (m = 0; m < (is_cgb ? 3 : 2); m++) {
                if (cr_load_unit(c, CR->gl)) { CR->gl = 255; break; }
                CR->gl++;
            }
            if (CR->gl != 255) return 0;
            kd = cr_kind(c, &v);
            if (kd == CK_SPIGOTEER) CR->txs = 3 + CR_PT->h;
            else if (kd == CK_DREGS) CR->txd = 3 + CR_PT->h;
        }
        if (!cr_card_row(c, (uint8_t)(w - CR->gs))) return 0;
    } else if (w >= CR->wroll) {                           // the roll
        if (w == CR->wroll) { CR->rt = 0; CR->lr = 255; }
        if (CR->gl != 255 && w >= CR->wroll + 8) {          // its robots (the last boss and patrons are off), the Spigoteer's colours back
            for (m = 0; m < 4; m++) {
                i = CR->gl;
                if (i < 18) load_patron_pose0(5, CR_T_P + 6 * (i / 6), i / 6, i % 6);
                else if (is_cgb && i < 21) { patron_pal_get(5, i - 18, (uint16_t *)CR->row); ((uint16_t *)CR->row)[0] = 0; cr_pal(1, OBJPAL_ROBOT + i - 18, (uint16_t *)CR->row); }
                else if (is_cgb && i == 21) { for (v = 0; v < 8; v++) CR_PAL[64 + v] = CR_SAVE[v]; cr_hw(1, 0); }
                else { CR->gl = 255; break; }
                CR->gl++;
            }
            if (CR->gl != 255) return 0;
        }
        if (!cr_roll_step((uint8_t)(w - CR->wroll), 3)) return 0;
        cr_attr_hud();
    } else { cr_blank(); cr_attr_hud(); }                  // between the cards
    if (CR->live) {                                        // (the queue is the main loop's: it drains it at the frame's end)
        vq_add(0, CR->row, 0, (uint8_t)w & 31, 20);
        if (is_cgb) vq_add(1, CR_ATT, 0, (uint8_t)w & 31, 20);
    } else {                                               // behind the white: written now
        set_bkg_tiles(0, (uint8_t)w & 31, 20, 1, CR->row);
        if (is_cgb) { VBK_REG = VBK_BANK_1; set_bkg_tiles(0, (uint8_t)w & 31, 20, 1, CR_ATT); VBK_REG = VBK_BANK_0; }
    }
    CR->next++;
    return 1;
}

static void cr_pose(uint8_t v, uint8_t pose, uint16_t bw) {    // the boss's two rows in a pose, written now, a row a call (pq: the pose + 1 on its way, pr: rows done)
    uint8_t d[20];
    if (!CR->pq) { CR->pq = pose + 1; CR->pr = 0; }
    cr_pose_fill(d, v, CR->pq - 1, CR->pr);
    set_bkg_tiles(0, (uint8_t)(bw + CR->pr) & 31, 20, 1, d);
    if (++CR->pr == 2) { CR->pose = CR->pq - 1; CR->pq = 0; }
}

static void cr_sprites_v(uint8_t busy) {                   // the cards' sprites (the cards that are loaded) and the roll's band
    uint16_t cs, sc = CR->pos, bw;           // (the position of the NEXT frame: the sprites reach the picture a frame after SCY, which is written first thing in the update)
    int16_t y, y0;
    uint8_t c, k, t = (uint8_t)CR->t, kd, v, pose, bob, n;
    const uint8_t *cx, *lp;
    hide_all_sprites();
    while (CR->sc < CR_CARDS && (uint16_t)(CR->ss + cr_hgt(CR->sc) + 1) * 8 <= sc) { CR->ss += cr_hgt(CR->sc) + cr_gap(CR->sc); CR->sc++; }
    cs = CR->ss;
    for (c = CR->sc; c < CR_CARDS && c < CR->sc + 3 && cs * 8 < sc + 160; c++) {
        if (c > CR->gc || (c == CR->gc && CR->gl != 255)) break;
        kd = cr_kind(c, &v);
        y0 = (int16_t)(8 * cs) - (int16_t)sc;                          // the card's top, screen y (the arithmetic is 16-bit and slow: once a card, not a sprite)
        if (kd == CK_SPIGOTEER || kd == CK_DREGS) {
            pose = cr_walk[(t >> 4) & 3];
            y = y0 + 8 * (kd == CK_SPIGOTEER ? CR->txs : CR->txd) + 12;
            if (kd == CK_SPIGOTEER) cr_fig(0, y, CT_SAL_X, OBJ_BARTENDER + BT_PIC(pose) * BARTENDER_TILES_PER_FRAME, OBJPAL_BARTENDER, 0);
            else cr_fig(4, y, CT_DREGS_X, CR_T_D + pose * 8, is_cgb ? OBJPAL_CAST : 0, 0);
        } else if (kd == CK_BOSS) {
            bw = cs + CT_R_BBODY;
            pose = cr_seq[(t >> 4) & 7];
            if ((pose != CR->pose || CR->pq) && !busy && CR->next >= bw + 3 && CR->next - bw <= 32) cr_pose(v, pose, bw);
            cr_oam(24, y0 + 8 * CT_R_BBODY + 8, ((20 - CR->bn) >> 1) * 8 + cr_hat_dx[v] + 8, CR_T_HAT + (CR->pose == 1 ? 2 : 0), is_cgb ? OBJPAL_TOP : S_PALETTE);
        } else if (kd == CK_PATRONS) {
            cx = ct_cx[v]; lp = ct_lp[v];
            for (k = 0; k < (is_cgb ? 8 : 3); k++) {
                bob = (((t >> 4) + k) & 3) ? 0 : 2;
                if (is_cgb) {                                           // (the names are on card rows 5, 10, 15; a sprite's OAM y is 4 above its name row's top)
                    y = y0 + (k < 3 ? 8 * CT_R_PN - 4 : k < 6 ? 16 * CT_R_PN - 4 : 24 * CT_R_PN - 4);
                    pose = k < 3 ? CR_T_P + 6 * k : PATRON_X_S0 + 4 * (k - 3);
                    n = (1 + lp[k]) | (k < 3 ? 0 : 8);
                } else { y = y0 + 16 * CT_R_PN - 4; pose = CR_T_P + 6 * k; n = 0; }
                cr_oam(8 + 2 * k, y - bob, cx[k], pose, n);
                cr_oam(9 + 2 * k, y - bob, cx[k] + 8, pose + 2, n);
            }
        }
        cs += cr_hgt(c) + cr_gap(c);
    }
    if (CR->gc >= CR_CARDS && CR->gl == 255) {             // the roll's band: the robots bob in turn, the Spigoteer raises a hand now and then
        y = (int16_t)((CR->wroll + CR_FIRST + CR_BAND) * 8) - (int16_t)sc + 16;
        for (k = 0; k < 3; k++) {
            bob = (((t >> 4) + k) & 3) ? 0 : 2;
            cr_oam(4 + 2 * k, y + 8 - bob, 24 + 32 * k + 8, CR_T_P + 6 * k, is_cgb ? OBJPAL_ROBOT + k : 0);
            cr_oam(5 + 2 * k, y + 8 - bob, 24 + 32 * k + 16, CR_T_P + 6 * k + 2, is_cgb ? OBJPAL_ROBOT + k : 0);
        }
        pose = ((t >> 4) & 3) == 1 ? BT_CATCH : BT_IDLE;
        cr_fig(0, y, CR_BT_X, OBJ_BARTENDER + BT_PIC(pose) * BARTENDER_TILES_PER_FRAME, OBJPAL_BARTENDER, 0);
    }
}

// ---- the timeline: a frame at a time (CR->st: 0 a stop's hold, 1 a glide to the next stop, 2 the text roll, 3 its end held) -------------------------------------------------
static uint8_t cr_speed(uint8_t g) {              // the glide's speed (px) in its frame g
    uint8_t L, sz;
    if (g < CR_VMAX * CR_VLEN) return 1 + (g >> 2);
    g -= CR_VMAX * CR_VLEN;
    if (g < CR->nc) return CR_VMAX;
    g -= CR->nc;                                   // the ramp down: each speed 4 frames, the one the remainder (rr) names one more
    for (L = CR_VMAX; L > 1; L--) {
        sz = CR_VLEN + (L == CR->rr);
        if (g < sz) return L;
        g -= sz;
    }
    return 1;
}

static void cr_glide(void) {                      // the glide from stop k to the next (the roll, after the last): its cruise and remainder from the distance
    uint16_t d, a;
    uint8_t c = CR->k;
    a = CR->ts + cr_hgt(c) + cr_gap(c);            // the next card's top row
    if (c + 1 < CR_CARDS) d = a * 8 + cr_off(c + 1) - 72;
    else d = CR->wroll * 8;
    d -= CR->pos;                                  // the px to go (>= 2 ramps: the layout)
    d -= 2 * CR_RAMP;
    CR->nc = (uint8_t)(d >> 2); CR->rr = (uint8_t)(d & 3);
    CR->ph = 0; CR->st = 1;
}

static void cr_step(void) {                       // one frame
    uint8_t c = CR->k;
    switch (CR->st) {
    case 0:
        if (++CR->ph >= cr_hold(c)) cr_glide();
        break;
    case 1:
        CR->pos += cr_speed((uint8_t)CR->ph);
        if (++CR->ph >= 2 * CR_VMAX * CR_VLEN + CR->nc + (CR->rr != 0)) {
            CR->ts += cr_hgt(c) + cr_gap(c);
            CR->k = c + 1; CR->ph = 0;
            CR->st = c + 1 < CR_CARDS ? 0 : 2;
        }
        break;
    case 2:
        if (CR->t & 1) CR->pos++;
        if (CR->pos >= CR->wroll * 8 + CR_LAST_T) { CR->pos = CR->wroll * 8 + CR_LAST_T; CR->st = 3; CR->ph = 0; }
        break;
    default:
        if (CR->ph < 0xFFFF) CR->ph++;
    }
}
#endif

void credits_enter(uint8_t from_story) BANKED {
    uint8_t y, *o = CR_PAL;
    DISPLAY_OFF;
    CR->lr = 255;
    music_play(TUNE_CREDITS);                         // (BONUS' or the story's tune stops here; copied while the screen is built: music_load_now below finishes it)
    music_pump();
    overlay_on = 0; HIDE_WIN; LYC_REG = BANNER_LYC;
    vq_reset(); hud_dirty = 0; vram_pending = 0;
    hide_all_sprites();
    story_font_load();                                // the punctuation (over the patron range: the next screen's load puts it back)
    music_pump();
    cr_blank();
    for (y = 0; y < 32; y++) cr_put(y);               // (a blank screen: the cards come up behind it)
    if (is_cgb) {
        for (y = 0; y < 20; y++) CR->row[y] = BGPAL_HUD;
        VBK_REG = VBK_BANK_1;
        for (y = 0; y < 32; y++) cr_put(y);
        VBK_REG = VBK_BANK_0;
        for (y = 0; y < 64; y++) { BCPS_REG = y; o[y] = BCPD_REG; OCPS_REG = y; o[64 + y] = OCPD_REG; }   // the palettes as they are (LCD off: readable)
        for (y = 0; y < 8; y++) o[8 * BGPAL_HDR + y] = o[8 * BGPAL_HUD + y];   // the header's: the HUD's
    } else {
        o[0] = BGP_REG; o[1] = OBP0_REG; o[2] = o[3] = OBP1_REG;
        story_scratch[68] = story_scratch[69] = 0;      // (white: the first card fades in)
        CRITICAL { remove_LCD(lcd_isr); add_LCD(cast_isr); }   // the header split, to cr_leave
        LYC_REG = 16;
    }
    cr_white();                                       // (the screen white until the first card fades in)
    music_pump();
#ifdef CREDITS_SCROLL
    cr_layout();
    credits_tile_put(CT_STRIPE, CR_STRIPE_ID);        // (LCD off)
    if (is_cgb) for (y = 0; y < 8; y++) CR_SAVE[y] = o[64 + y];    // (OBJ 0, the Spigoteer's: the bosses' topper wears it in the cast)
    else o[2] = DMG_HAT_OBP1;                          // (OBP1: the topper's, for the whole cast; cr_leave puts it back)
    CR->scroll = CR->pos = CR_W0 * 8 + CT_OFF_TITLE - 72; CR->next = 0; CR->t = 0; CR->ls = (uint8_t)sys_time; CR->phase = 0; CR->from_story = from_story;
    CR->gc = 0; CR->gs = CR_W0; CR->gl = 0; CR->sc = 0; CR->ss = CR_W0; CR->ts = CR_W0; CR->live = 0; CR->lw = 0xFFFF; CR->rt = 0; CR->pb = STORY_PORTRAIT_BASE; CR->pp = BGPAL_PATRON; CR->pose = 0; CR->pq = 0;
    CR->k = 0; CR->st = 0; CR->ph = 0; CR->nc = 0; CR->rr = 0;
#else
    CR->T = CR_PIC_FRAMES;                            // the timeline: shares of 9692 frames (1/392: 7 a card, 11 a patron card, the title included; the roll to 362)
    CR->e_title = CR->card_len = cr_share(7);
    CR->pl = cr_share(CR_UNIT_PAT);
    CR->roll = CR->e_title + 22 * CR->card_len + 10 * CR->pl;   // (the 32 cards after the title: 22 of 7 units, the ten patron cards longer)
    CR->f1 = cr_share(CR_UNIT_END);
    CR->k = (uint8_t)((CR_LAST_T * 32 + (CR->f1 - CR_F0) / 2) / (CR->f1 - CR_F0));
    CR->scroll = 0; CR->card = 255; CR->next = CR_AHEAD + 1; CR->t = 0; CR->ls = (uint8_t)sys_time; CR->phase = 0; CR->from_story = from_story; CR->f = 0; CR->tmask = 0; CR->amask = 0;
#endif
    SCX_REG = 0; SCY_REG = 0;
#ifdef CREDITS_SCROLL
    SCY_REG = (uint8_t)CR->scroll;
#endif
    story_phase = STORY_PHASE_CREDITS;
    game_state = GS_STORY;
    music_load_now_p();                               // the tune's first notes sound with the picture
    DISPLAY_ON;
}

static uint8_t cr_fade(uint8_t in, uint8_t hd) {   // (a fade takes frames: update counts them from sys_time, the clock the sound-off roll keeps). 1: B or START is down after it
    trans_cast(CR_PAL, in, hd);
    return (joypad() & (J_B | J_START)) != 0;           // (the press that came during the fade is not lost)
}

static void cr_leave(void) {
    uint8_t s = CR->from_story;
    if (!is_cgb) {
        CR_PAL[2] = CR_PAL[3];                        // (OBP1 as it was)
        CRITICAL { remove_LCD(cast_isr); add_LCD(lcd_isr); }
        LYC_REG = BANNER_LYC;
    }
    trans_cast_set(CR_PAL);                           // the card's own colours, whatever the fade was doing
#ifndef CREDITS_SCROLL
    SCY_REG = 0;                                      // (the scroll: SCY stays where it is, the scene change's white fade covers the screen as it stands; its LCD-off resets the scroll)
#endif
    TRANS_WANT();                                     // (src/trans.c: the next screen comes up behind the drink)
    if (s) story_end();
    else { title_back = TM_BONUS; title_back_sel = 0; title_enter(); }   // BONUS, the cursor on CREDITS (the first item)
}

#ifndef CREDITS_SCROLL
// story_update, every frame of the roll (GS_STORY). 1: the screen changed.
uint8_t credits_update(uint8_t pressed) BANKED {
    uint8_t c, top, hd, old;
    uint16_t f, p;
    if (pressed & (J_B | J_START)) { cr_leave(); return 1; }
    CR->t += (uint8_t)((uint8_t)sys_time - CR->ls);
    CR->ls = (uint8_t)sys_time;
    f = CR->t;                                                             // (the frames on the screen: the tune may have run out; its silence changes nothing)
    CR->f = f;
    if (f >= CR->T && (!sound_on || cur_tune != TUNE_CREDITS)) { cr_leave(); return 1; }   // (the roll's own end, and the tune over: the Easy Winners, 9986 frames, outlasts the roll's 9692 by 4.9 s, and its ending (the ritard, the ringing chord, the bass fading) must not be cut)
    if (f < CR->roll) {                                                    // the cast
        if (f < CR->e_title) c = 0;
        else {
            p = f - CR->e_title;                                               // the Spigoteer's and Dregs's cards, then per venue the owner, the patrons (longer), the boss
            if (p < 2 * CR->card_len) c = 1 + (uint8_t)(p / CR->card_len);
            else {
                p -= 2 * CR->card_len;
                f = 2 * CR->card_len + CR->pl;                                 // (a venue's three cards)
                c = (uint8_t)(p / f);
                p -= c * f;
                c = 3 + 3 * c + (p < CR->card_len ? 0 : p < CR->card_len + CR->pl ? 1 : 2);
            }
        }
        if (c >= CR_CARDS) c = CR_CARDS - 1;
        f = CR->f;
        if (CR->card != c) {
            hd = cr_hdr(CR->card, c);
            if (CR->card < CR_CARDS && cr_fade(0, hd)) { cr_leave(); return 1; }   // the old card fades out (to white; the header too when the venue changes)
            hide_all_sprites();
            if (!is_cgb) CR_PAL[2] = cr_kind(c, &top) == CK_BOSS ? DMG_HAT_OBP1 : CR_PAL[3];
            old = CR->card;
            CR->card = c; CR->phase = 1;                                       // (1: being built, 4: built, 5: shown)
            cr_make(c, hd, old);
            CR->phase = 4;
            cr_card_sprites(c);
            if (CR->skipq) { cr_leave(); return 1; }
            if (cr_fade(1, hd)) { cr_leave(); return 1; }                      // the new card fades in
            CR->phase = 5;
        } else cr_card_sprites(c);
        return 0;
    }
    if (CR->card < 200 || CR->card == 255) {                               // the roll's start: behind the fade its rows from the top, the robots
        if (CR->card < CR_CARDS && cr_fade(0, 1)) { cr_leave(); return 1; }
        hide_all_sprites();
        if (!is_cgb) CR_PAL[2] = CR_PAL[3];
        CR->phase = 1;
        cr_begin();
        while (!cr_clear_unit()) cr_pp();                  // (the last card's rows and CGB attributes: a boss's palette cells would tint the text)
        if (CR->card >= 3 && CR->card < CR_CARDS) for (c = 0; c < 3; c++) { cr_header(255, c); cr_pp(); }
        CR->rt = 0; CR->lr = 255;
        cr_rows(0, CR_AHEAD + 1);                          // (the rest as the scroll comes: ring slots 21-31 are blank)
        for (c = 0; c < 18; c++) { load_patron_pose0(5, CR_T_P + 6 * (c / 6), c / 6, c % 6); cr_pp(); }
        cr_sync();
        CR->card = 201;
        CR->phase = 4;
        if (is_cgb) for (c = 0; c < 3; c++) { patron_pal_get(5, c, (uint16_t *)CR->row); ((uint16_t *)CR->row)[0] = 0; cr_pal(1, OBJPAL_ROBOT + c, (uint16_t *)CR->row); }
        if (cr_fade(1, 1)) { cr_leave(); return 1; }
        return 0;
    }
    if (f > CR_F0) {
        p = f - CR_F0;
        if (p > CR->f1 - CR_F0) p = CR->f1 - CR_F0;
        p = (uint16_t)(p * CR->k) >> 5;
        if (p > CR_LAST_T) p = CR_LAST_T;
        CR->scroll = p;
        top = (uint8_t)(CR->scroll >> 3);
        if (CR->next <= (uint8_t)(top + CR_AHEAD)) {   // a row has come within reach: its ring slot is off the screen
            if (cr_roll_step(CR->next, 3)) {           // (its tiles three a frame, then the row at the next VBlank)
                vq_add(0, CR->row, 0, CR->next & 31, 20);
                CR->next++;
            }
        }
        SCY_REG = (uint8_t)CR->scroll;
    }
    cr_sprites();
    return 0;
}
#endif

#ifdef CREDITS_SCROLL
// story_update, every frame of the roll (GS_STORY). 1: the screen changed.
uint8_t credits_update(uint8_t pressed) BANKED {
    uint8_t d, busy = 0;
    if (pressed & (J_B | J_START)) { cr_leave(); return 1; }
    if (!CR->phase) {                                      // the first screen's rows (and tiles) behind the white, then the fade in
        CR->phase = 1;
        cr_begin();
        while (!CR->skipq && CR->next <= CR_AHEAD_C) {
            cr_gen();
            cr_pp();
        }
        cr_sync();
        if (CR->skipq) { cr_leave(); return 1; }
        if (cr_fade(1, 1)) { cr_leave(); return 1; }
        CR->live = 1;
        CR->ls = (uint8_t)sys_time;                        // (the timeline counts frames from here)
        return 0;
    }
    if (LY_REG >= 144) CR->scroll = CR->pos;               // (SCY moves in the VBlank only, and FIRST: the update can start in the VBlank's last lines, the main loop's ISR work is before it; an update that starts late would tear the top lines, the next frame catches up)
    SCY_REG = (uint8_t)CR->scroll;
    for (d = (uint8_t)((uint8_t)sys_time - CR->ls), CR->ls = (uint8_t)sys_time; d; d--) { CR->t++; cr_step(); }   // (frames, not the tune's ticks: a lost tick does not stretch it)
    if (CR->st == 3 && CR->ph >= CR_END_HOLD && (!sound_on || cur_tune != TUNE_CREDITS)) { cr_leave(); return 1; }   // (the roll's end, and the tune over: it ends on its own, cur_tune goes to TUNE_NONE)
    if (CR->next <= (CR->scroll >> 3) + (CR->next >= CR->wroll ? CR_AHEAD_R : CR_AHEAD_C)) { cr_gen(); busy = 1; }
    cr_sprites_v(busy);
    return 0;
}
#endif
