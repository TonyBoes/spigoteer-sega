// The credits (owner 2026-11-05: "instead of flashing between cards we scroll the whole thing"; 2026-11-13: the scrolling credits are the only ones): one
// continuous vertical roll of the cast (the Spigoteer, Dregs, then each venue's owner, patrons and boss), the game's credits text and "THANKS FOR PLAYING!"
// alone at the end, no fade between them. It IS the story's credits: the CREDITS scene shows its picture and the four closing narrator pages, and its end
// (story.c scene_done) is this roll (credits_enter(1); its end is story_end: the STORY score entry) and from the title's BONUS > CREDITS (credits_enter(0);
// its end or B: back to BONUS, the cursor on CREDITS). The wording is CREDITS.md's, the "Special thanks to:" list in it.
//
// The music is the credits tune (TUNE_CREDITS: the Easy Winners), started by credits_enter while the screen is built (BONUS' own tune stops there). The roll
// runs on its own clock (the frames on the screen, CR->t): every boundary of the timeline is a share (units of 1/392) of CR_PIC_FRAMES, 9692 frames; the tune
// is not changed to fit, and the roll leaves when its own end has been held and the tune is over. See the block "the scrolling credits" below.
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
#include "asm_cfg.h"
BANKREF_EXTERN(art_tiles)
extern const uint8_t bartender_tiles[];
static void cr_sal(uint8_t n) {                    // Sal's picture n back into OBJ 0-54: the scene pages' sprite tiles (set_sprite_data from 0) and nothing else loads them again, for the roll's end card and for the title
    spr_data_far(OBJ_BARTENDER + n * BARTENDER_TILES_PER_FRAME, BARTENDER_TILES_PER_FRAME, bartender_tiles + (uint16_t)n * BARTENDER_TILES_PER_FRAME * 16, BANK(art_tiles));
}
#ifndef CT_SPLIT
#define CT_SPLIT 0                                         // (credits_text.h: CRSPLIT=1)
#endif
#ifndef CT_ZN
#define CT_ZN 0
#endif
#define music_pump() music_pump_cr()   // (the roll's pump: a tick due in the picture's last lines waits for the VBlank, src/music.c)

extern uint8_t overlay_on, joy, story_phase;

#define CR_FIRST      18      // the roll's first row, in world rows (just under the screen)
#define CR_AHEAD      20      // rows are kept written up to T + CR_AHEAD (T: the top row of the screen)
#define CR_BAND       CT_ROLL2_BAND   // the roll's row where the sprites' band starts (4 rows); this variant's roll has a blank row after each line of an entry
#define CR_T_P       100      // the patrons' OBJ tiles: 3 variants x 6 (OBJ ids 100-117, in dgag.c's patron range)
#define CR_T_D        56      // Dregs's 8 OBJ tiles
#define CR_T_HAT      64      // the topper (8x16)
#define CR_T_BOSS    146      // BG ids: the boss's tile pairs (top, bottom; 29 at most, 58 tiles); the scroll's own slot (portraits 93-145: 53 tiles at most, boss 146-203, DMG text 204-255)
#define CR_RING_T     93      // BG ids of the roll's text: a ring of CT_RING tiles (the roll shows no portrait or boss)
#define CR_HDR_T     160      // the venue header's tiles (17 at most), kept through its venue's three cards
#define CR_TXT_T     178      // a card's text tiles, up to 255
#define CR_BT_X      120      // the Spigoteer's left edge in the roll; the robots stand at 24, 56, 88
#define OBJPAL_ROBOT   5
#define OBJPAL_CAST    3      // Dregs's, the topper's
#define BGPAL_BOSS     5
#define BGPAL_HDR      6      // the venue header's BG palette (CGB): a copy of the HUD's, the fades leave it alone within a venue
#define COL_GOLD  0x231E      // RGB15(30, 24, 8): the labels (palette 0 colour 1)
#if CT_SPLIT
#define COL_BAND  0x0C21      // RGB15(1, 1, 3): the roll's one black #080818 (tools/gen_credits.py NAVY: the band the HUD palette had, colour 3 of every BG palette), the bosses' colour 0
#else
#define COL_BAND  0x2043      // RGB15(3, 2, 8): the band (colour 3 of the HUD palette), the bosses' colour 0
#endif
#define DMG_HAT_OBP1  0x93    // the topper on the band: its three shades one step lighter (idx 1 white, 2 light, 3 dark; the DMG boss body is remapped the same way)

#define CR_SLOT(p) (CT_SCENEFMT ? (p) : cr_scene_slot[(p)])   // (CRSCENE: a scene page's palette number is its BG slot; CRMAP's go to the free ones)
static const uint8_t cr_scene_slot[7] = { 2, 3, 4, 6, 7, 5, 1 };   // a scene's palettes' BG slots: the free ones, then the previous boss's (5) and the HUD's (1), written once his body and name have scrolled off
#if CT_SCENEFMT
#define CR_SIGM 0x3FFF
#else
#define CR_SIGM 0x1FFF
#endif
#define CR_SOLID_ID  77     // CRMAP: the four flat tiles of the buildings (BG ids 77-80, both machines)
#define CR_BLD_PAL    6     // CRMAP: the building's BG palette (a venue's title page: the portraits' 2-4, the boss's 5 are not on it)
#define CR_CARDS      (CT_MAPFMT ? 43 : 33)      // the title, the Spigoteer, Dregs, then three cards for each of the ten venues (CRMAP proposal: four, the venue's title page first)
#define CR_SHARE      392     // the tune's units: 1/392 of it (24.7 frames of the 162 s tune)
#define CR_UNIT_PAT    11     // a patron card's units (owner Q80: held longer, to read all eight names); the other cards 7
#define CR_UNIT_END   362     // the roll ends at this unit, "THANKS FOR PLAYING!" fills the rest
#define CR_PIC_FRAMES 9692    // the cast and the roll run on their own clock: this many frames (162 s). The tune is 10700 frames (178 s; 15 frames a row, slowed from 14 on the owner's word 2026-11-13, so that it ends after the roll's text is done): the roll waits for it to end (credits_update; owner 2026-11-05: the tune is never stretched to fit)

// state in story_scratch
// The scrolling credits: one continuous vertical roll of the cast and then the text roll, no fade between them. See the block "the scrolling credits" below. 1 px every 2 frames.
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
    uint16_t sig;             // the sprites' last drawn state (scroll, animation step), with sig2 (card loads, boss pose): a frame that changes neither leaves OAM as it is
    uint8_t sig2;
    // gc: the card being built (33: the roll), gl: its loads done (units; 255: all), live: the colours go to the hardware as they are made, pb / pp: the portrait's first BG tile / BG palette,
    // rt: the text ring's next tile
};
#define CR ((struct cr_state *)story_scratch)
// (story_scratch + 68 / + 69: the DMG header's BGP and the card's, main.c cast_isr)
#define CR_PAL ((uint8_t *)story_scratch + 72)                          // the card's colours (CGB: 128 bytes; DMG: BGP, OBP0, OBP1, the first OBP1)
#define CR_PT  ((portrait_t *)(story_scratch + 200))                    // the owner's portrait (while a venue card is built)
#define CR_PT_B ((uint8_t *)story_scratch + 200)       // CRSCENE: the scene page's meta (n objects, OBJ palettes, tiles, then 3 bytes an object), where the owner's portrait used to be
#ifndef CR_RING_C
#define CR_RING_C 127                                  // CRSCENE, Color: the text ring is bank 1 ids 0-126 (BG ids 128-255 of bank 1 are the OBJ tiles 128-255 there: the Color looks)
#endif
#ifndef CR_NOGATE
#define CR_NOGATE 0
#endif
#ifndef CR_ISRRES
#define CR_ISRRES 40
#endif
#define CR_SH_DIRTY 212                                // CRSPLIT: the card set's RAM copy (CR_PAL) is ahead of the hardware
#define CR_SH_HW 213                                   //          which set the hardware holds at the end of the frame: 0 the cards', 1 the page's
#define CR_SH_TOP 214                                  //          which set the top of the screen shows this frame
#define CR_SH_LINE 215                                 //          the line the interrupt swaps at (255: none)
#define CR_SH_LO 217                                   //          the page's objects on the screen: from, up to (in the order they enter)
#define CR_SH_HI 218
#define CR_SH_V 219                                    //          the first venue whose page the plan has not left behind
#define CR_SH_DIR 216                                  //          0: cards' -> page's, 1: page's -> cards'
#if CT_SPLIT
extern uint8_t vq_held;
void cr_split_isr(void) NONBANKED;
void cr_split_isr_b(void) BANKED;
static void cr_pump(void);
void cr_pset(uint8_t scene) BANKED;           // (src/credits_split.c: the palette work of the shared screen, a bank of its own)
void cr_split_frame(void) BANKED;
void cr_split_pre(void) BANKED;
#else
#define cr_pump() music_pump()
#endif
#define CR_BUF ((uint8_t *)story_scratch + 200 + sizeof(portrait_t))    // 64 bytes: four tiles on their way, the owner's name
#define CR_ATT (CR_BUF + 64)      // the row's CGB attributes (20 bytes), then the Spigoteer's OBJ palette 0 (8 bytes)
#define CR_SAVE (CR_ATT + 20)
typedef char cr_fits[(sizeof(struct cr_state) <= 68 && 200 + sizeof(portrait_t) + 64 + 28 <= STORY_SCRATCH) ? 1 : -1];


// ---- the cast: the names are in tools/gen_credits.py (pre-rendered); the owners' portraits are the story's speakers' ----
static const uint8_t cr_owner[10] = { 2, 3, 4, 5, 6, 7, 11, 8, 10, 9 };   // the venue owner's speaker id (tools/gen_story.py SPEAKERS): Sadie, Coach, June, Colby, Aurora, Manager-Bot, Granny, Hana, Kiki, Zizz
static const uint8_t cr_hat_dx[10] = { 16, 8, 12, 9, 9, 8, 16, 16, 6, 12 };   // boss.c rows[]: the topper's x from his left edge
static const uint8_t cr_bdx[10] = CT_BDX;          // each boss's body and topper moved right by this many px (tools/gen_credits.py BOSS_DX: his ink box centred on x 80)
#define CR_GW(v) (CR->bn + ((cr_bdx[v] + 7) >> 3))    // the columns of his tiles once moved
static const uint8_t cr_walk[4] = { BT_WALK1, BT_IDLE, BT_WALK2, BT_IDLE };   // the pair's walk cycle (po.c walk_cycle's)
static const uint8_t cr_bpose[10][3] = CT_BPOSE;      // each boss's three poses (boss.h BP_*; slot 0 WALK, slot 1 STOMP: the topper's bob), cycled 0 1 2 1, 16 frames each (tools/gen_credits.py BOSS_POSES)
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

#define CR_N CT_ROLL2_N
#define CR_ROLL ct_roll2
#define CR_LAST_T ((CR_FIRST + (CR_N - 2)) * 8 + 4 - 72)   // the scroll at which the last three rows (a blank between the lines) are in the middle of the screen

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



// ---- the card's colours: in RAM, faded to the hardware by trans.c ----------------------------------------------------------------------
// CGB: palette i of the BG (obj 0) or OBJ (1) set, from CR_PAL to the hardware, a byte at a time in the first HBlank or VBlank there is (mode 0 or 1: STAT bit 1 clear;
// the write follows within 8 cycles, inside the next mode 0 / 2 at worst, and palette RAM is shut in mode 3 only)
static void cr_hw(uint8_t obj, uint8_t i) {
    uint8_t *s = CR_PAL + (obj ? 64 : 0) + 8 * i, k;
    CRITICAL { if (obj) OCPS_REG = 0x80 | (uint8_t)(i << 3); else BCPS_REG = 0x80 | (uint8_t)(i << 3); }
    for (k = 0; k < 8; k++) CRITICAL { while (STAT_REG & 2) ; if (obj) OCPD_REG = s[k]; else BCPD_REG = s[k]; }
}
#if CT_MAPFMT || CT_SCENEFMT
static void cr_hw_raw(uint8_t i, const uint16_t *p) {   // BG palette i straight to the hardware, its RAM copy (CR_PAL) left as it is: it is put back when the scene is gone
    uint8_t k;
    uint16_t w;
    CRITICAL { BCPS_REG = 0x80 | (uint8_t)(i << 3); }
    for (k = 0; k < 4; k++) {
        w = BRIGHTEN(p[k]);
        CRITICAL { while (STAT_REG & 2) ; BCPD_REG = (uint8_t)w; }
        CRITICAL { while (STAT_REG & 2) ; BCPD_REG = (uint8_t)(w >> 8); }
    }
}
#endif
#if CT_MAPFMT
static const uint8_t cr_back[5] = { 2, 3, 4, 5, 1 };
static void cr_restore(void) {                    // one palette of the scene's slots back from its RAM copy (CR->ft bits 5-7: how many are done; 5 and 1 only if the scene took them)
    uint8_t s = CR->ft >> 5, b;
    while (s < 5) {
        b = cr_back[s++];
        if (b == 5 && !(CR->ft & 2)) continue;
        if (b == 1 && !(CR->ft & 4)) continue;
        cr_hw(0, b);
        break;
    }
    CR->ft = s >= 5 ? 0 : (CR->ft & 31) | (uint8_t)(s << 5);
}
#endif
static void cr_pal(uint8_t obj, uint8_t i, const uint16_t *p) {   // CGB: palette i of the BG (obj 0) or OBJ (1) set
    uint16_t *q = (uint16_t *)(CR_PAL + (obj ? 64 : 0) + i * 8);
    q[0] = BRIGHTEN(p[0]); q[1] = BRIGHTEN(p[1]); q[2] = BRIGHTEN(p[2]); q[3] = BRIGHTEN(p[3]);   // (SCREEN BRIGHT: lifted once, here; trans.c fades them in as they are)
#if CT_SPLIT
    CR_PT_B[CR_SH_DIRTY] = 1;                         // (the hardware follows at the next frame's start: it may hold the page's colours now)
#else
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
    if (y < 1 || y > 159) { if (!CT_SPLIT || (o->x == x && (o->tile == tile || (tile >= CR_T_HAT && tile <= CR_T_HAT + 2 && o->tile >= CR_T_HAT && o->tile <= CR_T_HAT + 2)))) o->y = 0; return; }       // (CRSCENE: the page's objects share the slots: a sprite is hidden only if the slot still holds it)
    o->y = (uint8_t)y; o->x = x; o->tile = tile; o->prop = prop;
}

static void cr_oam_band(uint8_t n, int16_t y, uint8_t x, uint8_t tile, uint8_t prop) {      // the roll's band: OAM 0-3 are its own (the pages have gone): off the screen is hidden whatever tile the entry holds (the pose changes: an entry of the old pose left at the top edge stayed, 10 sprites on line 0)
    if (y < 1 || y > 159) { shadow_OAM[n].y = 0; return; }
    cr_oam(n, y, x, tile, prop);
}

static void cr_fig(uint8_t n, int16_t y, uint8_t x, uint8_t base, uint8_t prop, uint8_t flip) {   // the Spigoteer's four entries (x: left edge)
    uint8_t a = flip ? 2 : 0, b = flip ? 0 : 2, p = flip ? prop | S_FLIPX : prop;
    cr_oam(n, y, x + 8, base + a, p);
    cr_oam(n + 1, y, x + 16, base + b, p);
    cr_oam(n + 2, y + 16, x + 8, base + 4 + a, p);
    cr_oam(n + 3, y + 16, x + 16, base + 4 + b, p);
}


// ---- the cards ------------------------------------------------------------------------------------------------------------------------
// card c: 0 the title, 1 the Spigoteer, 2 Dregs (portrait and sprite), then venue by venue three cards: 3 + 3v the owner (portrait, name, venue),
// 4 + 3v the patrons (the venue, three with a label each), 5 + 3v the boss (animated on the band, his name, the venue).
// Writing VRAM with the LCD on is slow (the library waits for the picture's blanking for every byte): a card is built in UNITS, CR_UNITS a
// frame (a row, a few tiles), so that no frame runs over its VBlank and the tune never loses a tick. Stage 1 blanks the rows the last card
// used, stage 2 loads, stage 3 writes the rows; then the card fades in.
enum { CK_TITLE, CK_SPIGOTEER, CK_DREGS, CK_OWNER, CK_PATRONS, CK_BOSS, CK_VENUE };
#if CT_MAPFMT
static const uint8_t cr_kt[CR_CARDS] = { 0, 1, 2, 6, 3, 4, 5, 6, 3, 4, 5, 6, 3, 4, 5, 6, 3, 4, 5, 6, 3, 4, 5, 6, 3, 4, 5, 6, 3, 4, 5, 6, 3, 4, 5, 6, 3, 4, 5, 6, 3, 4, 5 };
static const uint8_t cr_vt[CR_CARDS] = { 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 6, 6, 6, 6, 7, 7, 7, 7, 8, 8, 8, 8, 9, 9, 9, 9 };
#else
static const uint8_t cr_kt[CR_CARDS] = { 0, 1, 2, 3, 4, 5, 3, 4, 5, 3, 4, 5, 3, 4, 5, 3, 4, 5, 3, 4, 5, 3, 4, 5, 3, 4, 5, 3, 4, 5, 3, 4, 5 };   // (tables: the scroll asks every frame, and a divide by 3 is 300 cycles)
static const uint8_t cr_vt[CR_CARDS] = { 0, 0, 0, 0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 6, 7, 7, 7, 8, 8, 8, 9, 9, 9 };
#endif
static uint8_t cr_kind(uint8_t c, uint8_t *v) { *v = cr_vt[c]; return cr_kt[c]; }


static void cr_remap(uint8_t *b, uint8_t n) {     // DMG: n bytes of tiles with the shades one step on (0 -> 3, the band; 1 -> 0; 2 -> 1; 3 -> 2): v - 1, a plane at a time
    uint8_t i, lo;
    for (i = 0; i < n; i += 2) {
        lo = ~b[i];                                   // (the low bit always flips; the high bit with it where the low bit was 0)
        b[i + 1] ^= lo;
        b[i] = lo;
    }
}

static uint8_t cr_spk(uint8_t c, uint8_t v) { return c == CK_SPIGOTEER ? 0 : c == CK_DREGS ? 1 : cr_owner[v]; }

#define CR_TXT_D    204
#define CR_TXT_DN    52
#define CR_DMGID(id) ((id) < CR_TXT_DN ? CR_TXT_D + (id) : (id) - CR_TXT_DN < 54 ? (id) - CR_TXT_DN : (id) - CR_TXT_DN + 1)
#define CR_TXT_CN   CR_RING_C
#if CT_SPLIT
// CRSPLIT: the pages need more text tiles at once than 127 (the round-8 pages: 133, with the cards around them 147). Verified free for the length of the card section by
// tools/dev/credits_vram_owners.py (a canary in every BG id: nothing writes them, nothing shows them): Color bank 0 ids 204-255, DMG ids 80-92, 138-145 and 202-203 (23). The roll keeps its 127.
static uint8_t cr_rn(void) { return CR->next >= CR->wroll ? 127 : is_cgb ? 127 + 52 : 127 + 23; }
static uint8_t cr_pid(uint8_t i) {                 // a ring slot's BG tile id (Color: slots 0-126 bank 1 ids 0-126, the rest bank 0 ids 204-255)
    if (is_cgb) return i < 127 ? i : i - 127 + 204;
    if (i < 127) return CR_DMGID(i);
    i -= 127;
    return i < 13 ? 80 + i : i < 21 ? 138 - 13 + i : 202 - 21 + i;
}
#define CR_BK(i) ((i) < 127 ? 8 : 0)
#else
#define cr_rn() (is_cgb ? CR_TXT_CN : CT_RING_N)
#define cr_pid(i) (is_cgb ? (i) : CR_DMGID(i))
#define CR_BK(i) 8
#endif
#if CT_SCENEFMT
#define CR_OAM_PAT 24                                // CRSCENE: the patrons' OAM entries 24-39 (the page's objects take 0-29: the first to leave the screen share 24-29), the boss's topper 12
#define CR_OAM_HAT 12
#define CR_OAM_SPG 32                                // (the Spigoteer's and Dregs's four: where the patrons' sprites will be, not yet)
#define CR_OAM_DRG 36
#else
#define CR_OAM_PAT 8
#define CR_OAM_HAT 24
#define CR_OAM_SPG 0
#define CR_OAM_DRG 4
#endif
#define CR_SWAPN 1                                  // CRSCENE: palettes a frame while the screen is blank (a load or a swap)
#define CR_SH_BG 100                                   // CRSCENE: the page's BG palettes (8 x 8 bytes) and OBJ palettes (6 x 6: colours 1-3), as the hardware takes them, in the portrait area (meta 3 + 3 per object: 93 at most; to 200 of its 227)
#define CR_SH_OB 164                                   // (six OBJ palettes of eight bytes: colour 0 is 0, as the hardware takes them; to 211)
#ifndef CR_NPRE_S
#define CR_NPRE_S 40
#endif
#define CR_NPRE (CT_SPLIT ? CR_NPRE_S : 96)                                    // CRSCENE: the page's tiles put in the ring before its rows (the ring holds 127: the card on the screen keeps the rest; CRSPLIT: 40, the page shares the screen with the name rows above it, 100 overwrote their tiles and 70 was clean)
#define CR_PT_NP 96                                  // (CR_PT_B[96]: how many of them this page has)
#define PBASE (CR->pb)
#define PPAL  (CR->pp)
#define OBJPAL_TOP 0       // the topper's OBJ palette: 0 (the Spigoteer's, restored before the roll), as patrons use 1-7 and the next card's patrons are on the screen with a boss
static void cr_bfetch(uint8_t v, uint8_t pose, int8_t c, uint8_t r, uint8_t *d) {      // the body tile in column c, row r of a pose (blank outside his columns)
    uint8_t k;
    if (c < 0 || c >= CR->bn) { for (k = 0; k < 16; k++) d[k] = 0; return; }
    cr_boss(v, 0, 2 * cr_boss(v, 1, pose, c, 0) + r, 0, d);
}
static void cr_btile(uint8_t v, uint8_t u, uint8_t *buf) {       // unit u of his body: pose u / (2 w), column, row: the tile moved right by cr_bdx px (the tile to its left spills in)
    uint8_t w = CR_GW(v), S = cr_bdx[v], s = S & 7, p = u / (2 * w), q = u - p * 2 * w, k;
    int8_t c = (int8_t)(q >> 1) - (int8_t)(S >> 3);
    p = cr_bpose[v][p];
    cr_bfetch(v, p, c, q & 1, buf);
    if (s) {
        cr_bfetch(v, p, c - 1, q & 1, buf + 16);
        for (k = 0; k < 16; k++) buf[k] = buf[k] >> s | buf[16 + k] << (8 - s);
    }
}

static uint8_t cr_load_unit(uint8_t c, uint8_t i) {   // unit i of card c's loads; 1: there are no more
    uint8_t v = 0, k, n, nch, kd = cr_kind(c, &v), *buf = CR_BUF;
    uint16_t p[4], bg;
    portrait_t *pt = CR_PT;
#if CT_MAPFMT
    if (kd == CK_VENUE) {                          // its palettes: BG 6 the building's, BG 0 the band's colour (the label's gold) as the owner's card will have it
        if (i < 5 && is_cgb) {                     // the scene's palettes (the map's own, one for each its cells name: BG 2, 3, 4, 6, 7; the owner's portrait colours wait in RAM until the scene is off the screen)
            if (i < ct_snp[v]) {
                for (n = 0; n < 4; n++) p[n] = ct_scol[v][i][n];
                if (!v && i > 2) { uint8_t lv = CR->live; CR->live = 0; cr_pal(0, cr_scene_slot[i], p); CR->live = lv; CR->ft |= 8; }   // (the first scene follows Dregs, whose portrait is BG 5-7: 6 and 7 go to the hardware when he is off)
                else cr_pal(0, cr_scene_slot[i], p);
            }
            return 0;
        }
        if (i == 5 && is_cgb) {
            uint16_t *q = (uint16_t *)CR_PAL, *hq = (uint16_t *)(CR_PAL + 8 * BGPAL_HUD);
            q[0] = hq[0]; q[1] = BRIGHTEN(COL_GOLD); q[2] = BRIGHTEN(ct_bandcol[v]); q[3] = hq[3];
            if (CR->live) cr_hw(0, 0);
            return 0;
        }
        return 1;
    }
#endif
#if CT_SCENEFMT
    if (kd == CK_OWNER) {                          // the scene page's loads: unit 0 its meta (RAM: the sprites' x, y, tile, flags), then its sprite tiles, then (Color) its OBJ palettes
        uint8_t tn = CR_PT_B[2], nm;
        if (i == 0) { credits_scene_get(v, 3, 0, CR_PT_B); CR->ft &= 7; CR_PT_B[CR_SH_LO] = CR_PT_B[CR_SH_HI] = 0; return 0; }
        nm = (3 + 3 * CR_PT_B[0] + 31) >> 5;           // (the meta comes in 32-byte units)
        if (i < nm) { credits_scene_get(v, 3, i, CR_PT_B + 32 * i); return 0; }
        i -= nm;
        tn = CR_PT_B[2];
        if (i < tn) { credits_scene_get(v, 0, i, buf); set_sprite_data(i, 1, buf); return 0; }
        i -= tn;
        {                                          // the page's first CR_NPRE tiles into the ring now, in the order its rows first use them: the rows then need no tile put (CR->rt stays where the page's rows will start)
            uint8_t np = credits_scene_get(2 * v + (is_cgb ? 1 : 0), 4, 0, buf), id;
            if (np > CR_NPRE) np = CR_NPRE;
            CR_PT_B[CR_PT_NP] = np;
            if (i < np) {
                credits_scene_get(2 * v + (is_cgb ? 1 : 0), 4, i, buf);
                id = CR->rt + i;
                if (id >= cr_rn()) id -= cr_rn();
                if (is_cgb && CR_BK(id)) VBK_REG = VBK_BANK_1;
                credits_tile_put(buf[0] | buf[1] << 8, cr_pid(id)); VBK_REG = VBK_BANK_0;
                return 0;
            }
            i -= np;
        }
        if (i < 8) {                               // the page's eight BG palettes into RAM (CR_SH_BG: the colours as the hardware takes them), where the swap and the split read them: no ROM read, no bank, at the swap
            if (is_cgb) {
                uint16_t *q = (uint16_t *)(CR_PT_B + CR_SH_BG + 8 * i);
                credits_scene_get(v, 1, i, buf);
                for (k = 0; k < 4; k++) q[k] = BRIGHTEN(((uint16_t *)buf)[k]);
            }
            return 0;
        }
        i -= 8;
        if (is_cgb && i < CR_PT_B[1]) {
            uint16_t *q = (uint16_t *)(CR_PT_B + CR_SH_OB + 8 * i);
            credits_scene_get(v, 2, i, buf);
            p[0] = 0; p[1] = buf[0] | buf[1] << 8; p[2] = buf[2] | buf[3] << 8; p[3] = buf[4] | buf[5] << 8;
            q[0] = 0; q[1] = BRIGHTEN(p[1]); q[2] = BRIGHTEN(p[2]); q[3] = BRIGHTEN(p[3]);       // (and its OBJ palettes' colours 1-3)
#if !CT_SPLIT
            cr_pal(1, 1 + i, p);
#endif
            return 0;
        }
        return 1;
    }
#endif
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
#if CT_MAPFMT
                    if (kd == CK_OWNER) { uint8_t lv = CR->live; CR->live = 0; cr_pal(0, PPAL + n, p); CR->live = lv; CR->ft |= 1; }   // (BG 2-4 are the venue scene's while it is on the screen: written when it is gone, credits_update)
                    else
#endif
                    cr_pal(0, PPAL + n, p);
                }
                if (kd == CK_OWNER) {                  // BG palette 0: the labels (colour 1: gold) and the band (colour 2: the venue's); the HUD's colours 0 and 3 (they are brightened already)
                    uint16_t *q = (uint16_t *)CR_PAL, *hq = (uint16_t *)(CR_PAL + 8 * BGPAL_HUD);
                    q[0] = hq[0]; q[1] = BRIGHTEN(COL_GOLD); q[2] = BRIGHTEN(ct_bandcol[v]); q[3] = hq[3];
                    if (CR->live) cr_hw(0, 0);
                }
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
        if (i >= 6 * CR_GW(v)) return 1;
        cr_btile(v, i, buf);                       // his body's tiles in his three poses, each moved right by cr_bdx px, a unit each
        if (!is_cgb) cr_remap(buf, 16);            // (DMG: the shades one step on)
        set_bkg_data(CR_T_BOSS + i, 1, buf);
        return 0;
    } else if (kd == CK_PATRONS) {
        n = is_cgb ? 38 : 18;                      // the three base looks' 18 tiles (bank 0), on Color the five Color-only looks' 20 (bank 1), then the palettes
        if (i >= n + (is_cgb ? 7 : 0)) return 1;
        if (i < 18) load_patron_pose0(v, CR_T_P + 6 * (i / 6), ct_slot[v][i / 6], i % 6);      // (a tile at a time: with the LCD on a byte takes two scanlines; the variant in slot k)
        else if (i < n) load_patron_x0(v, (i - 18) >> 2, (i - 18) & 3);
        else if (is_cgb) {                         // OBJ 1-7, one a unit (the hardware's: the HBlanks it takes)
            k = i - n;
            p[0] = 0; p[1] = ct_pcol[v][k][0]; p[2] = ct_pcol[v][k][1]; p[3] = ct_pcol[v][k][2];
            cr_pal(1, 1 + k, p);
        }
        return 0;
    }
    return 1;
}


// The screen goes white (the fade, trans.c trans_cast), the card is built behind it unit by unit (the LCD stays on: the header must not blink), the card
// fades in from white. The tune is pumped (the timer, polled) through the build.
static void cr_white(void) {                      // LCD off: every palette white
    uint8_t i;
    if (is_cgb) {
        BCPS_REG = 0x80; OCPS_REG = 0x80;
        for (i = 0; i < 32; i++) { BCPD_REG = 0xFF; BCPD_REG = 0x7F; OCPD_REG = 0xFF; OCPD_REG = 0x7F; }
    } else BGP_REG = OBP0_REG = OBP1_REG = 0;
}


// ---- the scrolling credits ---------------------------------------------------------------------------------------------------
// One world of map rows (row w sits in ring slot w & 31 of the 32-row map; SCY = scroll px): the cards of the cast one under the other, then the text roll (its row 0
// at wroll). The layout is tools/gen_credits.py's LAY (credits_text.h CT_*): a venue is its owner card (a larger gap, the venue's band, OWNER, the portrait
// and the name), the regulars card (the patrons in rows of 3, 3 and 2 with a name under each; DMG the middle row) and the boss card (the boss, his
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
#define CR_DMGID(id) ((id) < CR_TXT_DN ? CR_TXT_D + (id) : (id) - CR_TXT_DN < 54 ? (id) - CR_TXT_DN : (id) - CR_TXT_DN + 1)
#define CR_TXT_CN   127     // Color: ids 0-126 of bank 1
#define CR_W0         8     // the world row of the first card (the title): blank rows above it
#define CR_VMAX       4     // the glide's cruise speed (px a frame); the ramps take CR_VLEN frames at each speed 1..CR_VMAX
#define CR_VLEN       4
#define CR_RAMP      40     // the px of one ramp: 4 * (1 + 2 + 3 + 4)
#if CT_FLOWFMT
#define CR_END_HOLD  45     // (smooth: the last page is on as the tune ends, and goes with it)
#else
#define CR_END_HOLD 240     // the roll's end is held this many frames
#endif

static uint8_t cr_hgt(uint8_t c) {                // a card's rows
    uint8_t v = 0, kd;
    if (c >= CR_CARDS) return 0;
    kd = cr_kind(c, &v);
#if CT_SCENEFMT
    if (kd == CK_OWNER) return CT_SGT + 18 + CT_SGB;                  // a scene page: the screen to itself, blank rows above and below
#endif
#if CT_MAPFMT
    if (kd == CK_VENUE) return ct_vg[v] + ct_bh[v] + CT_VPAD;
#endif
    return kd == CK_TITLE ? CT_H_TITLE : kd <= CK_DREGS ? CT_H_SD : kd == CK_OWNER ? CT_H_OWN : kd == CK_BOSS ? CT_H_BOSS : CT_H_PAT;
}

static uint8_t cr_gap(uint8_t c) { return c == CR_CARDS - 1 ? CR_LASTGAP : c ? CT_G : CT_GAP_TITLE; }

#if CT_SCENEFMT
typedef uint16_t cr_off_t;                        // (a scene page: 8 * 26 + 72 px from the card top to its middle)
#else
typedef uint8_t cr_off_t;
#endif
static cr_off_t cr_off(uint8_t c) {                // the px from the card's top to the middle of its stop's block
    uint8_t v = 0, kd = cr_kind(c, &v);
#if CT_SCENEFMT
    if (kd == CK_OWNER) return 8 * CT_SGT + 72;
#endif
#if CT_MAPFMT
    if (kd == CK_VENUE) return 8 * ct_vg[v] + 4 * ct_bh[v];
#endif
    return kd == CK_TITLE ? CT_OFF_TITLE : kd <= CK_DREGS ? CT_OFF_SD : kd == CK_OWNER ? CT_OFF_OWN : kd == CK_BOSS ? CT_OFF_BOSS : CT_OFF_PAT;
}

static uint8_t cr_lrow(uint8_t c) { return cr_kt[c] == CK_OWNER ? CT_R_DIV - 6 : 0; }   // the card's row its loads wait for (an owner's: inside the gap before the divider, early enough for the loads to be done in the hold before; the Spigoteer's portrait slot is 34 rows above it)

static uint16_t cr_hold(uint8_t c) {              // frames
    uint8_t kd = cr_kt[c];
#if CT_SCENEFMT
    return kd == CK_TITLE ? 120 : kd == CK_PATRONS ? 245 : kd == CK_OWNER ? 150 : 145;       // (the scene pages' roll is longer: 50 blank rows a page; the holds are shorter so the tune ends a little after the roll)
#else
    return kd == CK_TITLE ? 120 : kd == CK_PATRONS ? 270 : 180;
#endif
}

static void cr_layout(void) {                     // the roll's row: after every card and its gap
    uint16_t w = CR_W0;
    uint8_t c;
    for (c = 0; c < CR_CARDS; c++) w += cr_hgt(c) + cr_gap(c);
    CR->wroll = w;
}

#if CT_SCENEFMT
// A scene page's rows are slow to build (113 tiles a page): when the glide to it has the screen blank and its rows are not all built, the scroll waits (the screen shows nothing but the
// page's colour: no one sees it stop) while the rows come up six tiles a frame.
#ifndef CR_STALL
#define CR_STALL 1
#endif
static uint8_t cr_stalled(void) {
    uint8_t n = CR->k + 1;
    uint16_t pt, b;
    if (!CR_STALL || CR->st != 1 || n >= CR_CARDS || cr_kt[n] != CK_OWNER) return 0;
    pt = CR->ts + cr_hgt(CR->k) + cr_gap(CR->k) + CT_SGT;      // the page's top row
    b = (CR->pos >> 3) + 19;                                   // the row about to scroll in
    return b >= pt && b <= pt + 18 && CR->next <= b;
}
#else
#define cr_stalled() 0
#endif

#if CT_MAPFMT || CT_SCENEFMT
static void cr_attr_hud(void) { uint8_t i; if (is_cgb) for (i = 0; i < 20; i++) CR_ATT[i] = 0; }   // (CRMAP: a blank cell is BG 0's colour 3, which is the page's, as the HUD's is: the HUD palette, BG 1, is the scene's seventh while a scene is on the screen)
#else
static void cr_attr_hud(void) { uint8_t i; if (is_cgb) for (i = 0; i < 20; i++) CR_ATT[i] = BGPAL_HUD; }
#endif

// a pre-rendered text row r (its tiles to the ring, 3 a call); 1: the row is complete in CR->row (CR_ATT: bank 1 on Color). kd 0: the text, the HUD palette; 1: a label, palette 0;
// 2: a band row, palette 0, the stripe all over but where the name's tiles are
// A frame's budget: the music's tick (up to 18 lines) must start before line 126, and a frame whose work runs past its VBlank makes the main loop wait out a whole frame, the tune
// a tick. A step that costs `lines` raster lines (single speed; a Color double-speed frame is twice as long) starts only if it ends by line 118, and not into the lines the sprites'
// redraw (45) still needs; a refused step is the next frame's.  (In the VBlank, LY 144 and on, there is room.)
#if CT_FLOWFMT
#define CR_RES ((CR->pos ^ CR->sig) & CR_SIGM ? 40 : 0)
#else
#if CT_SCENEFMT
static uint8_t cr_res(void) {                       // (a scene page on the screen: its 25 sprites' y is 75 lines, not 45)
#if CT_SPLIT
    if (CR_PT_B[CR_SH_LINE] < 112 && is_cgb) return CR_ISRRES + ((CR->pos ^ CR->sig) & CR_SIGM ? 45 : 0);     // (the interrupt takes the lines of the strip: 16)
#endif
    if (!((CR->pos ^ CR->sig) & CR_SIGM) || (CR->phase > 1 && CR->st == 1)) return 0;     // (the step waited: no sprite stage runs)
    if (cr_kt[CR->sc] == CK_OWNER && CR->pos + 144 > (uint16_t)(CR->ss + CT_SGT) * 8 && CR->pos < (uint16_t)(CR->ss + CT_SGT + 18) * 8) return CT_SPLIT ? 45 + 2 * CR_PT_B[0] : 45 + 3 * CR_PT_B[0];
    return 45;
}
#define CR_RES cr_res()
#else
#define CR_RES ((CR->pos ^ CR->sig) & CR_SIGM ? 45 : 0)
#endif
#endif
static uint8_t cr_room(uint8_t lines) {
    uint8_t ly = LY_REG;
    if (CR->next < (CR->scroll >> 3) + 19) return 1;     // (the rows are wanted: the screen shows up to scroll/8 + 19)
#if CT_FLOWFMT
    return ly >= 144 || (uint16_t)ly + lines + CR_RES <= 100;     // (a scene's rows are 46 lines of setup and the redraw 45: line 96 would never let both into a frame)
#else
    return ly >= 144 || (uint16_t)ly + lines + CR_RES <= 96;
#endif
}

static uint8_t cr_calm(void);
static uint8_t cr_tstep(uint16_t r, uint8_t kd) {
    uint8_t n, i, id, m = 2;   // (2 tiles a frame: three left the frame with 4 % to spare, and a pattern copy at an order boundary pushed it past its VBlank: a tick 1.6 frames late)
    uint16_t *cell = (uint16_t *)(CR_BUF + 2);
#if CT_MAPFMT || CT_SCENEFMT
    kd &= 15;                                      // (a building row: the venue rides in the high bits, no longer needed)
#endif
    if (CR->lw != CR->next) {
#if CT_MAPFMT || CT_SCENEFMT
        if (!cr_room(kd >= 3 ? 46 : 26)) return 0;       // (a scene's row: 16 cells from another bank and their attributes, 0.35 frame)
#if CT_SCENEFMT
        if (sound_on && !cr_calm() && CR->next >= (CR->scroll >> 3) + 19) return 0;    // (and not in the frames of the tune's driver row and pattern copy: 44 lines on top of it)
#endif
#else
        if (!cr_room(26)) return 0;
#endif
        CR->lw = CR->next; CR->ld = 0;
        cr_blank(); cr_attr_hud();
        if (kd && is_cgb) for (i = 0; i < 20; i++) CR_ATT[i] = 0;
#if CT_MAPFMT || CT_SCENEFMT
        if (kd == 2 || kd == 4) for (i = 0; i < 20; i++) CR->row[i] = CR_STRIPE_ID;
#else
        if (kd == 2) for (i = 0; i < 20; i++) CR->row[i] = CR_STRIPE_ID;
#endif
        credits_row_get(r, CR_BUF);
#if CT_MAPFMT || CT_SCENEFMT
        if (kd >= 3) return 0;                          // (a scene's row: its cells are the next frame's)
#endif
    }
    n = CR_BUF[1];
#if CT_SCENEFMT
    if (kd == 3) m = cr_stalled() ? 2 : 1;          // (a scene page's rows: six tiles a frame while the scroll waits for them, three otherwise)
#endif
    while (CR->ld < n && m) {
        i = CR->ld++;
        if (cell[i] == 0xFFFF) continue;
#if CT_MAPFMT || CT_SCENEFMT
        // a building row's cells (CT_MAPFMT): bits 12-15 tell the kind: 0-4 a tile (first use: put in the ring, the scene palette in bits 12-14), 14 a tile the scene has put in the
        // ring already (its slot: the scene's first ring slot, CR->lr, plus its number), 15 a flat tile (a fixed BG tile, no ring slot, no cost); bits 8-10 the scene palette
        if (cell[i] >= 0xF000) {
            CR->row[CR_BUF[0] + i] = CR_SOLID_ID + (uint8_t)(cell[i] & 3);
            if (is_cgb) CR_ATT[CR_BUF[0] + i] = CR_SLOT((cell[i] >> 8) & 7);
            continue;
        }
        if (cell[i] >= 0xE000) {
            id = CR->lr + (uint8_t)(cell[i] & 255);
            if (id < CR->lr) id += (uint8_t)(256 - cr_rn());          // (8 bits: the Color ring is 179 slots, a page that starts at 175 passes 255 and the sum wraps)
            else if (id >= cr_rn()) id -= cr_rn();
            if (is_cgb) CR_ATT[CR_BUF[0] + i] = (kd == 3 ? CR_SLOT((cell[i] >> 8) & 7) : 0) | CR_BK(id);
            CR->row[CR_BUF[0] + i] = cr_pid(id);
            continue;
        }
#endif
#if CT_SCENEFMT
        if (kd == 3 && (uint8_t)(CR->rt >= CR->lr ? CR->rt - CR->lr : CR->rt + cr_rn() - CR->lr) < CR_PT_B[CR_PT_NP]) {     // (one of the page's preloaded tiles: its ring slot is next, no put)
            id = CR->rt;
            if (++CR->rt == cr_rn()) CR->rt = 0;
            if (is_cgb) CR_ATT[CR_BUF[0] + i] = CR_SLOT(cell[i] >> 12) | CR_BK(id);
            CR->row[CR_BUF[0] + i] = cr_pid(id);
            continue;
        }
#endif
        if (!cr_room(kd == 3 && !cr_stalled() && !CT_SPLIT ? 24 : 10)) { CR->ld--; break; }              // (the flat and repeated cells above cost no frame time to speak of: only a tile put is asked about)
        if (is_cgb) {
            id = CR->rt;
            if (++CR->rt == cr_rn()) CR->rt = 0;
            if (CR_BK(id)) VBK_REG = VBK_BANK_1;
            credits_tile_put(cell[i] & 0xFFF, cr_pid(id)); VBK_REG = VBK_BANK_0;
#if CT_MAPFMT || CT_SCENEFMT
            CR_ATT[CR_BUF[0] + i] = (kd == 3 ? CR_SLOT(cell[i] >> 12) : kd ? 0 : BGPAL_HUD) | CR_BK(id);
#else
            CR_ATT[CR_BUF[0] + i] = (kd ? 0 : BGPAL_HUD) | 8;
#endif
            id = cr_pid(id);
        } else {
            id = CR->rt;
            if (++CR->rt == cr_rn()) CR->rt = 0;
            id = cr_pid(id);
#if CT_MAPFMT || CT_SCENEFMT
            credits_tile_put(cell[i] & 0xFFF, id);
#else
            credits_tile_put(cell[i], id);
#endif
        }
        CR->row[CR_BUF[0] + i] = id;
        m--;
        cr_pump();                                  // (a tile is 0.06 frame: a tick due in the middle of a row is struck then, not at the frame's end, where the pump's clock would lose its lateness)
    }
    return CR->ld >= n;
}

static void cr_pose_fill(uint8_t *d, uint8_t v, uint8_t pose, uint8_t r) {    // the boss's row r (0, 1) in a pose
    uint8_t k, w = CR_GW(v), L = (20 - CR->bn) >> 1;
    for (k = 0; k < 20; k++) d[k] = TILE_HUD_BLANK;
    for (k = 0; k < w; k++) d[L + k] = CR_T_BOSS + (pose * w + k) * 2 + r;
}

// card c's local row r into CR->row / CR_ATT; 1: done, 0: call again (a text row's tiles)
static uint8_t cr_card_row(uint8_t c, uint8_t r) {
    uint8_t v = 0, kd = cr_kind(c, &v), tk = 0, k, L, h = CR_PT->h, w = CR_PT->w, i = 255;
    uint16_t tr = 0xFFFF;                          // (a row id: the scene pages make over 255)
    portrait_t *pt = CR_PT;
    if (kd == CK_TITLE) { if (r == 0) tr = CT_TITLE; else if (r == 2) tr = CT_TITLE + 1; }
    else if (kd == CK_SPIGOTEER || kd == CK_DREGS) {
        if (r >= 1 && r < 1 + h) i = r - 1;
        else if (r == 3 + h || r == 5 + h) tr = (kd == CK_SPIGOTEER ? CT_SAL : CT_DREGS) + ((r - 3 - h) >> 1);
#if CT_SCENEFMT
    } else if (kd == CK_OWNER) {                    // the scene page: band, picture and the owner's name are rows 1-17 of its 18 (the artist's round 6, tools/gen_scene_pages.py)
        if (r > CT_SGT && r <= CT_SGT + 17) {
            if (r == CT_SGT + 1 && CR->lw != CR->next) CR->lr = CR->rt;          // (the page's rows are built one after the other: its ring slots start here)
            tr = CT_SCN + 17 * (2 * v + (is_cgb ? 1 : 0)) + r - CT_SGT - 1; tk = 3;
        }
#elif CT_MAPFMT
    } else if (kd == CK_VENUE) {
        if (r == ct_vg[v] && CR->lw != CR->next) CR->lr = CR->rt;     // (the scene's rows are built one after the other: its ring slots start here)
        if (r >= ct_vg[v] && r < ct_vg[v] + ct_bh[v]) { tr = CT_BLD + ct_boff[v] + r - ct_vg[v]; tk = ((uint8_t)(r - ct_vg[v] - ct_bs0[v]) < ct_bnl[v] ? 4 : 3) | (v << 4); }
    } else if (kd == CK_OWNER) {
        if (r == CT_R_OLBL) { tr = CT_LBL; tk = 1; }
        else if (r >= CT_R_PORT && r < CT_R_PORT + h) i = r - CT_R_PORT;
        else if (r == CT_R_PORT + h + 1) tr = CT_OWNER + v;
#else
    } else if (kd == CK_OWNER) {
        if (r >= CT_R_BAND && r < CT_R_BAND + 3) { if (!(CT_FONTFMT == 2 && r != CT_R_BAND + 1)) { tr = CT_BAND + 3 * v + r - CT_R_BAND; tk = 2; } }   // (CRFONT=B: the ribbon, one row of stripe)
        else if (r == CT_R_OLBL) { tr = CT_LBL; tk = 1; }
        else if (r >= CT_R_PORT && r < CT_R_PORT + h) i = r - CT_R_PORT;
        else if (r == CT_R_PORT + h + 1) tr = CT_OWNER + v;
#endif
    } else if (kd == CK_PATRONS) {
        if (is_cgb) { k = r - CT_R_PA; if (r >= CT_R_PA && k % CT_R_PN == 0 && k < 3 * CT_R_PN) tr = CT_PATA + 10 * (k / CT_R_PN) + v; }
        else if (r == CT_R_PA + CT_R_PN) tr = CT_PATA + v;
    } else if (r == CT_R_BNAME) tr = CT_BOSS + v;
    if (tr != 0xFFFF) return cr_tstep(tr, tk);
    cr_blank(); cr_attr_hud();
#if CT_SPLIT && CT_SCENEFMT
    if (is_cgb && kd == CK_OWNER && i == 255 && ct_sbp[v] != 255) for (k = 0; k < 20; k++) { CR->row[k] = CR_SOLID_ID + 3; CR_ATT[k] = CR_SLOT(ct_sbp[v]); }      // (the page card's rows around the page: flat navy in the BG palette whose colour 3 is navy in the page's set and in the cards': the strip's palette swap changes nothing on them)
#endif
    if (i != 255) {                                // a portrait row
        L = (20 - w) >> 1;
        for (k = 0; k < w; k++) {
            CR->row[L + k] = CR->pb + pt->map[i * w + k];
            if (is_cgb) CR_ATT[L + k] = CR->pp + pt->attr[i * w + k];
        }
    } else if (kd == CK_BOSS && (r == CT_R_BBODY || r == CT_R_BBODY + 1)) {
        cr_pose_fill(CR->row, v, CR->pose, r - CT_R_BBODY);
        if (is_cgb) { L = (20 - CR->bn) >> 1; for (k = 0; k < CR_GW(v); k++) CR_ATT[L + k] = BGPAL_BOSS; }
    }
    return 1;
}

// the next world row (CR->next): what loads it needs (a few units a call), then the row; 1: it is queued
#if CT_SCENEFMT
static uint8_t cr_page_rows_ok(uint8_t c, uint16_t w) {   // a scene card's rows while its loads are not all done: its blank rows, and the page's rows once its tiles are in the ring
    if (cr_kt[c] != CK_OWNER) return 0;
    return w - CR->gs <= CT_SGT || CR->gl > ((3 + 3 * CR_PT_B[0] + 31) >> 5) + CR_PT_B[2] + CR_PT_B[CR_PT_NP];
}
#endif

static uint8_t cr_gen(void) {
    uint16_t w = CR->next;
    uint8_t c = CR->gc, m, i, v = 0, kd, gate = 0;
    while (c < CR_CARDS && w >= CR->gs + cr_hgt(c) + cr_gap(c)) { CR->gs += cr_hgt(c) + cr_gap(c); c++; CR->gl = 0; }
#if CT_SCENEFMT
    if (c != CR->gc) { CR->gc = c; CR->pose = 0; return 0; }          // (a card begins: the sprite stage sees it (CR->gc is in its signature) and has that frame to itself)
#endif
    CR->gc = c;
    if (c < CR_CARDS && w >= CR->gs && w < CR->gs + cr_hgt(c)) {          // a card's row
#if CT_SCENEFMT
        gate = CR->gl != 255 && cr_kt[c] == CK_OWNER && (CR->lw == CR->next || (CT_SPLIT && !CR_NOGATE && c == 3 && CR->sc < 2) ||  /* (the first page's sprite tiles are OBJ 0-49: the Spigoteer's pictures, on the screen until his card has gone) */ (CR->gl > ((3 + 3 * CR_PT_B[0] + 31) >> 5) + CR_PT_B[2] + CR_PT_B[CR_PT_NP] + 8 && CR->sc < c && !CT_SPLIT));          // (no load while a row is in progress: the units use CR_BUF too; the scene's OBJ palettes wait until the card before it is off the screen: its rows do not)
#endif
        if (CR->gl != 255 && w - CR->gs >= cr_lrow(c) && !gate) {
            if (!CR->gl) { CR->pb = c == 2 ? CR_T_BOSS : STORY_PORTRAIT_BASE; CR->pp = c == 2 ? BGPAL_STAGE : BGPAL_PATRON; CR->pose = 0; }
            if (!cr_room(CR->gl < 3 && cr_kt[c] != CK_BOSS && cr_kt[c] != CK_PATRONS ? 52 : cr_kt[c] == CK_BOSS && CR->gl >= 5 ? 56 : 28)) return 0;   // (a portrait's header, map and palettes: 0.3 frame in one call)
#if CT_SCENEFMT
            if (!CT_SPLIT && is_cgb && cr_kt[c] == CK_PATRONS && CR->gl >= 38 && (CR->sc < c - 1 || (CR->sc == c - 1 && CR->pos < (uint16_t)(CR->ss + CT_SGT + 18) * 8) || (CR->txs == 99 + c && CR->txd < 11))) return 0;   // (the patrons' OBJ palettes: after the scene page is off)
#endif
            for (m = 0; m < (CT_SPLIT && c == 3 ? (is_cgb ? 6 : 3) : CT_SPLIT && cr_kt[c] == CK_OWNER && (CR->gl < ((3 + 3 * CR_PT_B[0] + 31) >> 5) + CR_PT_B[2] || CR->gl > ((3 + 3 * CR_PT_B[0] + 31) >> 5) + CR_PT_B[2] + CR_PT_B[CR_PT_NP]) ? 2 : CT_SCENEFMT && is_cgb && ((cr_kt[c] == CK_PATRONS && CR->gl >= 38) || (cr_kt[c] == CK_OWNER && CR->gl > ((3 + 3 * CR_PT_B[0] + 31) >> 5) + CR_PT_B[2] + CR_PT_B[CR_PT_NP] + 8)) ? CR_SWAPN : 1); m++) {        // (the scene's and the patrons' OBJ palettes: the screen is blank, four a frame)
                if (cr_load_unit(c, CR->gl)) { CR->gl = 255; break; }
                CR->gl++;
                cr_pump();                                  // (a unit is a fraction of a frame, a call of three more: the tune's tick falls due in between, not a frame late)
            }
#if CT_SCENEFMT
            if (CR->gl != 255 && !cr_page_rows_ok(c, w)) return 0;       // (a scene card's loads take their frames beside its blank rows, which the screen reaches first)
#else
            if (CR->gl != 255) return 0;
#endif
            if (CR->gl == 255) {
            kd = cr_kind(c, &v);
            if (kd == CK_SPIGOTEER) CR->txs = 3 + CR_PT->h;
            else if (kd == CK_DREGS) CR->txd = 3 + CR_PT->h;
#if CT_SCENEFMT
            return 0;                                      // (the loads done is a frame of its own: the sprites are all written again, the rows wait for the next)
#endif
            }
        }
#if CT_SCENEFMT
        if (CR->gl != 255 && !cr_page_rows_ok(c, w)) return 0;      // (the loads wait for a free frame: the page's own rows do not go before its tiles)
        if (w > (CR->scroll >> 3) + CR_AHEAD_C) return 0;           // (a scene card's loads are called a frame at a time, its rows only as far ahead of the screen as the map holds)
#endif
        cr_pump();
        if (!cr_card_row(c, (uint8_t)(w - CR->gs))) return 0;
        cr_pump();
    } else if (w >= CR->wroll) {                           // the roll
        if (w == CR->wroll) { CR->rt = 0; CR->lr = 255; }
        if (CR->gl != 255 && w >= CR->wroll + 8) {          // its robots (the last boss and patrons are off), the Spigoteer's colours back
            for (m = 0; m < (CT_SCENEFMT ? 1 : 2); m++) {                         // (a pose tile is 0.14 frame on DMG: four a frame left no room for a tick's pattern copy)
                i = CR->gl;
                if (i < 18) load_patron_pose0(5, CR_T_P + 6 * (i / 6), i / 6, i % 6);
                else if (is_cgb && i < 21) { patron_pal_get(5, i - 18, (uint16_t *)CR->row); ((uint16_t *)CR->row)[0] = 0; cr_pal(1, OBJPAL_ROBOT + i - 18, (uint16_t *)CR->row); }
                else if (is_cgb && i == 21) { for (v = 0; v < 8; v++) CR_PAL[64 + v] = CR_SAVE[v]; cr_hw(1, 0); }
                else if (i - (is_cgb ? 22 : 18) < BARTENDER_FRAMES) cr_sal(i - (is_cgb ? 22 : 18));      // (Sal's pictures, one a frame: the end card's Spigoteer)
                else { CR->gl = 255; break; }
                CR->gl++;
                cr_pump();
            }
            if (CR->gl != 255) return 0;
        }
        cr_pump();
        if (!cr_roll_step((uint8_t)(w - CR->wroll), 3)) return 0;
        cr_pump();
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
    cr_pump();
    if (++CR->pr == 2) { CR->pose = CR->pq - 1; CR->pq = 0; CR->sig2 = 255; }
}

extern uint8_t hUGE_tick, hUGE_ticks_per_row;
static uint8_t cr_calm(void) {                                // a boss's pose row (0.2 frame) goes in a frame the tune's tick is light: not a row's first ticks (the driver's row, the pattern copy on tick 3) nor its last (before them)
    return hUGE_tick >= 5 && (uint8_t)(hUGE_tick + 3) < hUGE_ticks_per_row;
}

#if CT_SCENEFMT
// The page's objects (numbered in the order they enter the screen) and the OAM: the first n - 24 leave the screen before the patrons' sixteen (slots 24-39) come on, so they take slots 24 on; the next fifteen are the ones that
// show with the card above (the Spigoteer's 0-3, Dregs's 4-7, the topper's 12 are not theirs), then four, then the last five, which show with nobody but the patrons.
static const uint8_t cr_pslots[24] = { 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 12 };
static uint8_t cr_pslot(uint8_t k, uint8_t n) { return n > 24 && k < n - 24 ? 24 + k : cr_pslots[n > 24 ? k - (n - 24) : k]; }
#endif
#if CT_SCENEFMT
static void cr_page_pre(uint8_t n) {              // the page's sprites' x, tile and flags into OAM, hidden, n objects a call (CR->ft bits 4-7: how many calls are done): the frame the page comes on the screen is then only their y
    const uint8_t *so = CR_PT_B + 3;
    uint8_t nobj = CR_PT_B[0], k = (CR->ft >> 4) * n;
    OAM_item_t *oo;
    if (CR->ft & 8) return;
    so += 3 * k;
    for (; k < nobj && n; k++, n--, so += 3) { oo = shadow_OAM + cr_pslot(k, nobj); if (oo->tile != (uint8_t)(k << 1) || oo->x != so[0] || oo->prop != (so[2] & 0x7F)) { oo->y = 0; oo->x = so[0]; oo->tile = (uint8_t)(k << 1); oo->prop = so[2] & 0x7F; } }       // (an object that is on the screen already is left as it is)
    CR->ft += 16;
    if (k >= nobj) CR->ft |= 8;
}
#endif

static void cr_sprites_v(uint8_t busy) {                   // the cards' sprites (the cards that are loaded) and the roll's band
    uint16_t cs, sc = CR->pos, bw;           // (the position of the NEXT frame: the sprites reach the picture a frame after SCY, which is written first thing in the update)
    int16_t y, y0, ya, yb, yc;
    OAM_item_t *oo;
    uint8_t c, k, t = (uint8_t)CR->t, kd, v, pose, bob, n;
    const uint8_t *cx, *lp;
    uint8_t g2 = CR->gc | (CR->gl == 255 ? 64 : 0) | (CR->pose == 1 ? 128 : 0), adv = CR->sc;
#if CT_SCENEFMT
    uint16_t g = sc | (uint16_t)((t >> 4) & 3) << 14, dg = g ^ CR->sig;           // (sig: the scroll in bits 0-13 (the scene pages make the roll over 8191 px), the animation step's low two bits above, its third in CR->ft)
#else
    uint16_t g = sc | (uint16_t)((t >> 4) & 7) << 13, dg = g ^ CR->sig;           // (sig: the scroll in bits 0-12, the animation step above)
#endif
    uint8_t rm, rd, rs;
#if CT_SCENEFMT
    while (CR->sc < CR_CARDS && (uint16_t)(CR->ss + cr_hgt(CR->sc) + 1 - (CR->sc + 1 < CR_CARDS && cr_kt[CR->sc + 1] == CK_OWNER ? 3 : 0)) * 8 <= sc) { CR->ss += cr_hgt(CR->sc) + cr_gap(CR->sc); CR->sc++; }     // (before a scene page: when the card's ink is off, three rows before its end)
#else
    while (CR->sc < CR_CARDS && (uint16_t)(CR->ss + cr_hgt(CR->sc) + 1) * 8 <= sc) { CR->ss += cr_hgt(CR->sc) + cr_gap(CR->sc); CR->sc++; }
#endif
#if CT_SCENEFMT
    if (CR->phase > 1 && CR->st == 1) { cr_page_pre(6); return; }       // (this frame's step waited for a page's rows: the screen shows no sprite, the frame is the rows')
#endif
    rm = (dg & CR_SIGM) != 0;                      // rm: the scroll moved: every sprite's y; rd: a card's loads or a card left (its sprites go): every sprite is written whole; rs: an animation step: the sprites that change in it
    rd = g2 != CR->sig2 || adv != CR->sc;
#if CT_SCENEFMT
    rs = (dg >> 14) != 0 || ((CR->ft ^ (t >> 4)) & 4) != 0;
    CR->ft = ((t >> 4) & 4) | (CR->ft & 0xF8);            // (bit 3: the page's sprites' x, tile and flags are in OAM)
#else
    rs = (dg >> 13) != 0;
#endif
#if CT_SCENEFMT
    if (cr_stalled()) rs = 0;                       // (the scroll waits for a page's rows with the screen all but blank: the animation waits too, the frame is the rows')
#endif
    CR->sig = g; CR->sig2 = g2;
    if (rd) hide_all_sprites();                   // (OAM keeps what it has when nothing it shows has moved: the stage is 0.3 frame, and a frame that runs past its VBlank costs the tune a tick)
    cs = CR->ss;
    for (c = CR->sc; c < CR_CARDS && c < CR->sc + 3 && cs * 8 < sc + 160; c++) {
        if (c > CR->gc || (c == CR->gc && CR->gl != 255)) break;
        kd = cr_kind(c, &v);
        y0 = (int16_t)(8 * cs) - (int16_t)sc;                          // the card's top, screen y (the arithmetic is 16-bit and slow: once a card, not a sprite)
        if (kd == CK_SPIGOTEER || kd == CK_DREGS) {
            pose = cr_walk[(t >> 4) & 3];
            y = y0 + 8 * (kd == CK_SPIGOTEER ? CR->txs : CR->txd) + 12;
            if (!(rs || rm || rd)) {}
            else if (kd == CK_SPIGOTEER) cr_fig(CR_OAM_SPG, y, CT_SAL_X, OBJ_BARTENDER + BT_PIC(pose) * BARTENDER_TILES_PER_FRAME, OBJPAL_BARTENDER, 0);
            else cr_fig(CR_OAM_DRG, y + 14, CT_DREGS_X, CR_T_D + pose * 8, is_cgb ? OBJPAL_CAST : 0, 0);
        } else if (kd == CK_BOSS) {
            bw = cs + CT_R_BBODY;
            pose = (t >> 4) & 3;
            if (pose == 3) pose = 1;
            if ((pose != CR->pose || CR->pq) && CR->next >= bw + 3 && CR->next - bw <= 32 && (!sound_on || cr_calm()) && cr_room(30)) cr_pose(v, pose, bw);
            if (rs || rm || rd) cr_oam(CR_OAM_HAT, y0 + 8 * CT_R_BBODY + 8, ((20 - CR->bn) >> 1) * 8 + cr_hat_dx[v] + cr_bdx[v] + 8, CR_T_HAT + (CR->pose == 1 ? 2 : 0), is_cgb ? OBJPAL_TOP : S_PALETTE);
#if CT_SCENEFMT
        } else if (kd == CK_OWNER) {                   // the scene page's sprites (the owner's edge cells): x, tile and flags when all are written (rd), the y when the scroll moved
            if (c == CR->sc) cr_page_pre(6);          // (the page is not on the screen yet: its objects go in, hidden, in the blank before it)
            if ((rs || rm || rd) && y0 + 8 * (CT_SGT + 1) < 160 && y0 + 8 * (CT_SGT + 18) > 0) {      // (the page is on the screen)
                const uint8_t *so = CR_PT_B + 3;
                uint8_t nobj = CR_PT_B[0];
                y = y0 + 8 * (CT_SGT + 4) + 16;
                oo = shadow_OAM;
                // The objects enter the screen (and leave it) in their order: those from CR_SH_LO to CR_SH_HI are on it, and only their y is written (the whole object when it enters; one that has left is hidden if its slot
                // still holds it): the slots are shared with the cards above and below, and a pass over all of them was a frame.
                {
                    uint8_t m24 = nobj > 24 ? nobj - 24 : 0, lo = CR_PT_B[CR_SH_LO], hi = CR_PT_B[CR_SH_HI], y8 = (uint8_t)y;
                    so = CR_PT_B + 3;
                    while (lo < nobj && y + so[3 * lo + 1] <= 0) {
                        oo = shadow_OAM + (lo < m24 ? 24 + lo : cr_pslots[lo - m24]);
                        if (oo->tile == (uint8_t)(lo << 1) && oo->x == so[3 * lo]) oo->y = 0;
                        lo++;
                    }
                    if (hi < lo) hi = lo;
                    while (hi < nobj && y + so[3 * hi + 1] < 160) {
                        oo = shadow_OAM + (hi < m24 ? 24 + hi : cr_pslots[hi - m24]);
                        oo->x = so[3 * hi]; oo->tile = (uint8_t)(hi << 1); oo->prop = so[3 * hi + 2] & 0x7F;      // (flag bit 7: a Color-only accent sprite, not drawn on a DMG)
                        hi++;
                    }
                    for (k = lo; k < hi; k++) {
                        oo = shadow_OAM + (k < m24 ? 24 + k : cr_pslots[k - m24]);
                        oo->y = !is_cgb && (so[3 * k + 2] & 0x80) ? 0 : (uint8_t)(y8 + so[3 * k + 1]);
                    }
                    CR_PT_B[CR_SH_LO] = lo; CR_PT_B[CR_SH_HI] = hi;
                }
            }
#endif
        } else if (kd == CK_PATRONS
#if CT_SPLIT
                   && (CR->gc > c || (CR->gc == c && CR->gl == 255))        // (the card's poses and palettes are in: on a late frame (the C twin) its sprites came up with the previous venue's looks for a frame)
#endif
#if CT_SCENEFMT
                   && (CT_SPLIT || !(c == CR->sc + 1 && CR->pos < (uint16_t)(CR->ss + CT_SGT + 19) * 8))       // (the scene page's sprites hold OAM until the page has gone: the patrons' share its slots; then at once, the card's own rows are not yet in view)
#endif
                   ) {
            cx = ct_cx[v]; lp = ct_lp[v];
            ya = y0 + 8 * CT_R_PA - 4; yb = ya + 8 * CT_R_PN; yc = yb + 8 * CT_R_PN;       // (the three name rows' sprite y: a sprite's OAM y is 4 above its name row's top; the pairs are written in place, a call each was 0.1 frame a card)
            for (k = 0; (rs || rm || rd) && k < (is_cgb ? 8 : 3); k++) {
#if CT_SPLIT
                if (is_cgb && c == CR->sc + 1 && cr_kt[c - 1] == CK_OWNER && CR_PT_B[0] > 24) {          // (the page above (the card the screen's top is in) still has its first objects to leave in OAM 24-29, the pairs' slots: they keep them until they have gone)
                    uint8_t m24 = CR_PT_B[0] - 24, lo = CR_PT_B[CR_SH_LO];
                    if ((2 * k < m24 && 2 * k >= lo) || (2 * k + 1 < m24 && 2 * k + 1 >= lo)) continue;
                }
#endif
                if (!rd && !rm && ((((t >> 4) + k) & 3) > 1)) continue;   // (an animation step moves the two whose bob starts or ends in it)
                bob = (((t >> 4) + k) & 3) ? 0 : 2;
                if (!rd) {                                  // (only the scroll or a bob moved: the sprite is in OAM, its y is all that changes: no tile, no palette)
                    y = (is_cgb ? (k < 3 ? ya : k < 6 ? yb : yc) : yb) - bob;
                    oo = shadow_OAM + CR_OAM_PAT + 2 * k;
                    if ((uint16_t)(y - 1) < 159 && oo->y) { oo->y = oo[1].y = (uint8_t)y; continue; }
                }
                if (is_cgb) {
                    y = k < 3 ? ya : k < 6 ? yb : yc;
                    pose = k < 3 ? CR_T_P + 6 * k : PATRON_X_S0 + 4 * (k - 3);
                    n = (1 + lp[k]) | (k < 3 ? 0 : 8);
                } else { y = yb; pose = CR_T_P + 6 * k; n = 0; }
                y -= bob;
                oo = shadow_OAM + CR_OAM_PAT + 2 * k;
                if ((uint16_t)(y - 1) >= 159) { if (!CT_SPLIT || (oo->tile == pose && oo->x == cx[k])) { oo->y = 0; oo[1].y = 0; } }
                else if (!rd && oo->y) oo->y = oo[1].y = (uint8_t)y;     // (only the scroll moved: the sprite is there, its y is all that changes)
                else {
                    oo->y = oo[1].y = (uint8_t)y; oo->x = cx[k]; oo[1].x = cx[k] + 8; oo->tile = pose; oo[1].tile = pose + 2; oo->prop = oo[1].prop = n;
                }
                if ((k & 1) && k != 7) cr_pump();                               // (a card of eight patrons is a long frame on Color: the tick falls due in the middle)
            }
        }
        cs += cr_hgt(c) + cr_gap(c);
    }
    if ((rs || rm || rd) && CR->gc >= CR_CARDS && CR->gl == 255) {             // the roll's band: the robots bob in turn, the Spigoteer raises a hand now and then
        y = (int16_t)((CR->wroll + CR_FIRST + CR_BAND) * 8) - (int16_t)sc + 16;
        for (k = 0; k < 3; k++) {
            bob = (((t >> 4) + k) & 3) ? 0 : 2;
            cr_oam(4 + 2 * k, y + 8 - bob, 24 + 32 * k + 8, CR_T_P + 6 * k, is_cgb ? OBJPAL_ROBOT + k : 0);
            cr_oam(5 + 2 * k, y + 8 - bob, 24 + 32 * k + 16, CR_T_P + 6 * k + 2, is_cgb ? OBJPAL_ROBOT + k : 0);
        }
        pose = ((t >> 4) & 3) == 1 ? BT_CATCH : BT_IDLE;
        {
            uint8_t base = OBJ_BARTENDER + BT_PIC(pose) * BARTENDER_TILES_PER_FRAME;
            cr_oam_band(0, y, CR_BT_X + 8, base, OBJPAL_BARTENDER);
            cr_oam_band(1, y, CR_BT_X + 16, base + 2, OBJPAL_BARTENDER);
            cr_oam_band(2, y + 16, CR_BT_X + 8, base + 4, OBJPAL_BARTENDER);
            cr_oam_band(3, y + 16, CR_BT_X + 16, base + 6, OBJPAL_BARTENDER);
        }
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

#if CT_FLOWFMT
// CRFLOW=SMOOTH: no stops. The picture moves up CR->ts / 65536 px a frame (CR->nc, rr: the fraction's carry, a whole px on the frames it overflows: the most even a pixel scroll can be)
// from the first frame to the roll's last scroll, which it reaches CR_FLOW_TAIL frames before the tune ends (cr_flow_init); then the last page is held and the roll leaves with the tune.
#define CR_FLOW_TAIL 100          // (the roll starts counting 55 frames after the tune: the fade in; the last scroll lands as the tune's last row rings out)
static void cr_flow_init(void) {
#if CT_SCENEFMT
    uint32_t n = ((uint32_t)(CR->wroll * 8 + CR_LAST_T - CT_ZSKIP) - CR->pos) << 16, r = 0;          // (the blank stretches round the pages are jumped: not in the speed)
    uint16_t d = music_tune_frames(TUNE_CREDITS) - CR_FLOW_TAIL - CT_ZN * CT_ZD, q = 0;                // (and each waits CT_ZD frames)
#else
    uint32_t n = ((uint32_t)(CR->wroll * 8 + CR_LAST_T) - CR->pos) << 16, r = 0;
    uint16_t d = music_tune_frames(TUNE_CREDITS) - CR_FLOW_TAIL, q = 0;
#endif
    uint8_t i;
    for (i = 0; i < 32; i++) {                       // (a long division bit by bit: the library's would sit in ROM0)
        r = (r << 1) | (n >> 31);
        n <<= 1;
        q <<= 1;
        if (r >= d) { r -= d; q |= 1; }
    }
    CR->ts = q; *(uint16_t *)&CR->nc = 0;                // (8.16: CR->nc and rr are the fraction's carry)
}

static void cr_step(void) {
    uint16_t fin = CR->wroll * 8 + CR_LAST_T;
    uint32_t f;
    if (CR->st >= 3) { if (CR->ph < 0xFFFF) CR->ph++; return; }
    f = (uint32_t)*(uint16_t *)&CR->nc + CR->ts;
    *(uint16_t *)&CR->nc = (uint16_t)f;
    CR->pos += (uint16_t)(f >> 16);
#if CT_SCENEFMT
    if (CR->k < CT_ZN && CR->pos >= ct_zone[2 * CR->k]) {              // a blank stretch round a scene page (CR->k: its number, CR->ph: the frames waited): the screen shows nothing, the palettes, sprites and loads of the page go in, then the roll goes on past the blank
        if (CR->ph < CT_ZD) { CR->pos = ct_zone[2 * CR->k]; CR->ph++; }
        else { CR->pos = ct_zone[2 * CR->k + 1]; CR->ph = 0; CR->k++; }
    }
#endif
    if (CR->pos >= fin) { CR->pos = fin; CR->st = 3; CR->ph = 0; }
}
#else
static void cr_step(void) {                       // one frame
    uint8_t c = CR->k;
    switch (CR->st) {
    case 0:
        if (++CR->ph >= cr_hold(c)) cr_glide();
        break;
    case 1:
#if CT_SCENEFMT
        if (CR->phase && cr_stalled() && CR->phase < 251) { CR->phase++; break; }       // (CR->phase: 1 after the first screen, 1 + the frames the step has waited)
        if (CR->phase) CR->phase = 1;
#endif
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
    cr_pump();
    overlay_on = 0; HIDE_WIN; LYC_REG = BANNER_LYC;
    vq_reset(); hud_dirty = 0; vram_pending = 0;
    hide_all_sprites();
    story_font_load();                                // the punctuation (over the patron range: the next screen's load puts it back)
    cr_pump();
    cr_blank();
    for (y = 0; y < 32; y++) cr_put(y);               // (a blank screen: the cards come up behind it)
    if (is_cgb) {
#if CT_MAPFMT || CT_SCENEFMT
        for (y = 0; y < 20; y++) CR->row[y] = 0;
#else
        for (y = 0; y < 20; y++) CR->row[y] = BGPAL_HUD;
#endif
        VBK_REG = VBK_BANK_1;
        for (y = 0; y < 32; y++) cr_put(y);
        VBK_REG = VBK_BANK_0;
        for (y = 0; y < 64; y++) { BCPS_REG = y; o[y] = BCPD_REG; OCPS_REG = y; o[64 + y] = OCPD_REG; }   // the palettes as they are (LCD off: readable)
#if CT_SPLIT
        for (y = 0; y < 8; y++) ((uint16_t *)o)[4 * y + 3] = BRIGHTEN(COL_BAND);   // colour 3 of every BG palette is the roll's one black #080818 (tools/gen_credits.py NAVY): the cards' blank and the pages' margins
#endif
        for (y = 0; y < 8; y++) o[8 * BGPAL_HDR + y] = o[8 * BGPAL_HUD + y];   // the header's: the HUD's
#if CT_MAPFMT || CT_SCENEFMT
        for (y = 0; y < 8; y++) o[y] = o[8 * BGPAL_HUD + y];                   // BG 0 starts as the HUD's: the blank cells use it
#endif
    } else {
        o[0] = BGP_REG; o[1] = OBP0_REG; o[2] = o[3] = OBP1_REG;
        story_scratch[68] = story_scratch[69] = 0;      // (white: the first card fades in)
#if !CT_SPLIT
        CRITICAL { remove_LCD(lcd_isr); add_LCD(cast_isr); }   // the header split, to cr_leave
        LYC_REG = 16;
#endif
    }
#if CT_SPLIT
    CR_PT_B[CR_SH_DIRTY] = 0; CR_PT_B[CR_SH_HW] = 0; CR_PT_B[CR_SH_TOP] = 0; CR_PT_B[CR_SH_LINE] = 255; CR_PT_B[CR_SH_DIR] = 0; CR_PT_B[CR_SH_V] = 0;
    story_scratch[70] = 0; story_scratch[71] = 255; CR_PT_B[223] = 255; CR_PT_B[224] = 255; CR_PT_B[225] = 0; CR_PT_B[226] = 0;      // (credits_split.c's plan for the first frame: scroll 0, no line)
    CRITICAL { remove_LCD(lcd_isr); add_LCD(cr_split_isr); }   // the palette split (and, on a DMG, the header's), to cr_leave
    LYC_REG = is_cgb ? 255 : 0;
#endif
    cr_white();                                       // (the screen white until the first card fades in)
    cr_pump();
    cr_layout();
    credits_tile_put(CT_STRIPE, CR_STRIPE_ID);        // (LCD off)
#if CT_MAPFMT || CT_SCENEFMT
    for (y = 0; y < 4; y++) credits_tile_put(ct_solid[y], CR_SOLID_ID + y);
#endif
    if (is_cgb) for (y = 0; y < 8; y++) CR_SAVE[y] = o[64 + y];    // (OBJ 0, the Spigoteer's: the bosses' topper wears it in the cast)
    else o[2] = DMG_HAT_OBP1;                          // (OBP1: the topper's, for the whole cast; cr_leave puts it back)
    CR->scroll = CR->pos = CR_W0 * 8 + CT_OFF_TITLE - 72; CR->next = 0; CR->t = 0; CR->ls = (uint8_t)sys_time; CR->phase = 0; CR->from_story = from_story;
    CR->gc = 0; CR->gs = CR_W0; CR->gl = 0; CR->sc = 0; CR->ss = CR_W0; CR->ts = CR_W0; CR->live = 0; CR->lw = 0xFFFF; CR->rt = 0; CR->pb = STORY_PORTRAIT_BASE; CR->pp = BGPAL_PATRON; CR->pose = 0; CR->pq = 0; CR->sig = 0xFFFF; CR->sig2 = 255;
    CR->k = 0; CR->st = 0; CR->ph = 0; CR->nc = 0; CR->rr = 0;
#if CT_FLOWFMT
    cr_flow_init();
#endif
    SCX_REG = 0; SCY_REG = 0;
    SCY_REG = (uint8_t)CR->scroll;
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
#if CT_SPLIT
    CRITICAL { remove_LCD(cr_split_isr); add_LCD(lcd_isr); }
    LYC_REG = BANNER_LYC;
    if (!is_cgb) CR_PAL[2] = CR_PAL[3];
    else cr_pset(0);
#else
    if (!is_cgb) {
        CR_PAL[2] = CR_PAL[3];                        // (OBP1 as it was)
        CRITICAL { remove_LCD(cast_isr); add_LCD(lcd_isr); }
        LYC_REG = BANNER_LYC;
    }
#endif
    { uint8_t n; for (n = 0; n < BARTENDER_FRAMES; n++) cr_sal(n); }
    trans_cast_set(CR_PAL);                           // the card's own colours, whatever the fade was doing
    TRANS_WANT();                                     // (src/trans.c: the next screen comes up behind the drink)
    DISPLAY_OFF;                                      // (the cover of the wanted scene change runs here, over the frozen end card: with the scroll reset first it rose over the first rows of the map, the roll's old text ("COMMUNITY") behind the drink)
    SCY_REG = 0;                                      // (the roll's last scroll: the next screen is built from the top; the story's score entry did not reset it)
    if (s) story_end();
    else { title_back = TM_BONUS; title_back_sel = 0; title_enter(); }   // BONUS, the cursor on CREDITS (the first item)
}


// story_update, every frame of the roll (GS_STORY). 1: the screen changed.
#if CT_SPLIT
void cr_split_isr(void) NONBANKED { cr_split_isr_b(); }       // (ROM0: the interrupt's own stub; the body is in this file's bank, the banked call puts the interrupted code's bank back)
static void cr_pump(void) {                       // the music's pump, and a guard: its interrupts-off read-modify-write of IF can swallow the LYC flag when it falls inside it (a hardware race): a swap line that has passed with the interrupt still armed is done now
    music_pump();
    if (is_cgb && LYC_REG != 255 && LY_REG > LYC_REG && LY_REG < 144) cr_split_isr_b();
}
#endif

#if CT_SCENEFMT
static void cr_hw_sh(uint8_t i) {                 // BG palette i of the page (its RAM copy) to the hardware: eight bytes, each when the screen is not drawing
    const uint8_t *s = CR_PT_B + CR_SH_BG + 8 * i;
    uint8_t k;
    CRITICAL { BCPS_REG = 0x80 | (uint8_t)(i << 3); }
    for (k = 0; k < 8; k++) CRITICAL { while (STAT_REG & 2) ; BCPD_REG = s[k]; }
}
#endif
#if CT_SCENEFMT && !CT_SPLIT
// A scene page has the screen to itself: its BG palettes (all 8 slots, one a frame) go in while the cards before and after are off the screen (the blank rows above it are longer than
// the screen) and the three the cards use (0, 1, 5) come back from their RAM copies once the page has gone; the DMG's OBJ shade registers likewise. CR->bp = 100 + card marks whose
// state CR->bn is (0-7 palettes in, 8-10 coming back, 11 done), whatever a boss left in them.
static void cr_scene_swap(void) {
    uint8_t d = CR->sc, st, n, tmp[8];
    if (d >= CR_CARDS || cr_kt[d] != CK_OWNER) return;
    if (CR->txs != 100 + d) { CR->txs = 100 + d; CR->txd = 0; }
    st = CR->txd;
    if (st < 8) {
        if ((CR->gc > d || (CR->gc == d && CR->gl == 255)) && CR->pos + 144 <= (uint16_t)(CR->ss + CT_SGT) * 8 && (CT_ZN || CR->pos >= (uint16_t)(CR->ss - 2) * 8)) {         // (the card before has left the screen: its last blank row would change colour)
            if (is_cgb) { for (n = 0; n < CR_SWAPN && CR->txd < 8; n++) { cr_hw_sh(CR->txd); CR->txd++; } }      // (a blank screen: three palettes a frame, 8 lines each)
            else { OBP0_REG = 0x90; OBP1_REG = 0xE4; CR->txd = 8; }      // (idx 1-3 = shades 0-2, and 1-3: the artist's two OBJ palettes)
        }
    } else if (st < 11 && CR->pos >= (uint16_t)(CR->ss + CT_SGT + 19) * 8) {         // (a row after the page: the frame that shows its last row has been drawn)
        if (is_cgb) { for (n = 0; n < CR_SWAPN && CR->txd < 11; n++) { st = CR->txd; cr_hw(0, st == 8 ? 0 : st == 9 ? 1 : 5); CR->txd = st + 1; } }
        else { OBP0_REG = CR_PAL[1]; OBP1_REG = CR_PAL[2]; CR->txd = 11; }
    }
}
#endif

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
#if CT_MAPFMT
        CR->ft = 0;
#endif
        CR->ls = (uint8_t)sys_time;                        // (the timeline counts frames from here)
        return 0;
    }
    if (is_cgb) cr_pump();                              // (Color: the frame's tick first, so the main loop's own never has to be the late one)
    if (LY_REG >= 144 || (uint16_t)(CR->pos - CR->scroll) > 48) CR->scroll = CR->pos;               // (a lag of more than 48 px (about 85 frames: the C twin's swap interrupt late for a stretch holds the picture 30 frames and catches up in the VBlank by itself) moves the picture in mid-frame, the top lines tear for a frame: an update that always starts late (the swap interrupt at line 135 ran into the next frame: normal speed) must not freeze the picture at the line that makes it late) (SCY moves in the VBlank only, and FIRST: the update can start in the VBlank's last lines, the main loop's ISR work is before it; an update that starts late would tear the top lines, the next frame catches up)
    SCY_REG = (uint8_t)CR->scroll;
#if CT_SPLIT
    cr_split_frame();
#endif
    cr_pump();                                          // (after the scroll register: the tick falls due here when the frame began late)
    for (d = (uint8_t)((uint8_t)sys_time - CR->ls), CR->ls = (uint8_t)sys_time; d; d--) { CR->t++; cr_step(); }   // (frames, not the tune's ticks: a lost tick does not stretch it)
#if CT_SCENEFMT && !CT_SPLIT
    cr_scene_swap();
#endif
#if CT_MAPFMT
    d = CR->sc;
    if (is_cgb && d < CR_CARDS - 1 && (CR->ft || cr_kt[d] == CK_BOSS)) {       // BG palettes the venue scene shares with its neighbours (CR->ft: 1 the owner's portrait colours wait for BG 2-4, 2 and 4 the scene
                                                           // has taken 5 and 1, 8 the first scene's 6 and 7 wait for Dregs, 16 the scene has been on the screen)
        if ((CR->ft & 8) && cr_kt[d] > CK_DREGS) { cr_hw(0, 6); cr_hw(0, 7); CR->ft &= ~8; }
        if (cr_kt[d] == CK_BOSS && cr_kt[d + 1] == CK_VENUE) {      // the previous boss: once his body rows (BG 5) and his name (BG 1) have scrolled off, the scene's extra palettes take their slots
            if (ct_snp[cr_vt[d + 1]] > 5 && !(CR->ft & 2) && CR->pos >= (uint16_t)(CR->ss + 5) * 8) { cr_hw_raw(5, ct_scol[cr_vt[d + 1]][5]); CR->ft |= 2; }
            if (ct_snp[cr_vt[d + 1]] > 6 && !(CR->ft & 4) && CR->pos >= (uint16_t)(CR->ss + 8) * 8) { cr_hw_raw(1, ct_scol[cr_vt[d + 1]][6]); CR->ft |= 4; }
        }
        if (cr_kt[d] == CK_VENUE) {
            CR->ft |= 16;
            if (CR->pos >= (uint16_t)(CR->ss + ct_vg[cr_vt[d]] + ct_bh[cr_vt[d]]) * 8) cr_restore();   // (the scene is gone: the owner's colours, the boss's and the HUD's go back, one palette a frame: a palette is 8 HBlanks)
        } else if (CR->ft & 17) cr_restore();
    }
#endif
    if (CR->st == 3 && CR->ph >= CR_END_HOLD && (!sound_on || cur_tune != TUNE_CREDITS)) { cr_leave(); return 1; }   // (the roll's end, and the tune over: it ends on its own, cur_tune goes to TUNE_NONE)
    if (CR->next <= (CR->scroll >> 3) + (CR->next >= CR->wroll ? CR_AHEAD_R : CR_AHEAD_C)
#if CT_SCENEFMT
        || (CR->gl != 255 && CR->gc < CR_CARDS && cr_kt[CR->gc] == CK_OWNER && CR->next >= CR->gs)         // (a scene card's loads: one unit a frame whether or not a row is wanted)
#endif
        ) {
#if CT_SCENEFMT
        if (CR->sc < CR_CARDS && (uint16_t)(CR->ss + cr_hgt(CR->sc) + 1 - (CR->sc + 1 < CR_CARDS && cr_kt[CR->sc + 1] == CK_OWNER ? 3 : 0)) * 8 <= CR->pos) busy = 1;         // (a card leaves the screen this frame: the sprite stage rewrites every sprite, 80 lines, and has the frame to itself)
        else
#endif
#if CT_SPLIT
        { if (!vq_held) cr_gen(); busy = 1; }               // (the last row's queue entry points at CR->row: while its drain waits (a late VBlank handler: the swap interrupt ran to line 148) no row may begin)
#else
        { cr_gen(); busy = 1; }
#endif
        }
    cr_pump();
    cr_sprites_v(busy);
    cr_pump();
#if CT_SPLIT
    cr_split_pre();                                     // (the next frame's plan, so that its start has only the set to write)
#endif
    return 0;
}
