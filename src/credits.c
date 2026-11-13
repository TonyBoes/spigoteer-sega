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
#define COL_BAND  0x2043      // RGB15(3, 2, 8): the band (colour 3 of the HUD palette), the bosses' colour 0
#define DMG_HAT_OBP1  0x93    // the topper on the band: its three shades one step lighter (idx 1 white, 2 light, 3 dark; the DMG boss body is remapped the same way)

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
#define CR_BUF ((uint8_t *)story_scratch + 200 + sizeof(portrait_t))    // 64 bytes: four tiles on their way, the owner's name
#define CR_ATT (CR_BUF + 64)      // the row's CGB attributes (20 bytes), then the Spigoteer's OBJ palette 0 (8 bytes)
#define CR_SAVE (CR_ATT + 20)
typedef char cr_fits[(sizeof(struct cr_state) <= 68 && 200 + sizeof(portrait_t) + 64 + 28 <= STORY_SCRATCH) ? 1 : -1];


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
static void cr_pal(uint8_t obj, uint8_t i, const uint16_t *p) {   // CGB: palette i of the BG (obj 0) or OBJ (1) set
    uint16_t *q = (uint16_t *)(CR_PAL + (obj ? 64 : 0) + i * 8);
    q[0] = BRIGHTEN(p[0]); q[1] = BRIGHTEN(p[1]); q[2] = BRIGHTEN(p[2]); q[3] = BRIGHTEN(p[3]);   // (SCREEN BRIGHT: lifted once, here; trans.c fades them in as they are)
    if (CR->live) cr_hw(obj, i);                      // (the scroll: no fade, a card's colours go on as they are made; nothing on the screen uses that palette: see cr_gen)
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

#define PBASE (CR->pb)
#define PPAL  (CR->pp)
#define OBJPAL_TOP 0       // the topper's OBJ palette: 0 (the Spigoteer's, restored before the roll), as patrons use 1-7 and the next card's patrons are on the screen with a boss
static uint8_t cr_load_unit(uint8_t c, uint8_t i) {   // unit i of card c's loads; 1: there are no more
    uint8_t v = 0, k, n, nch, kd = cr_kind(c, &v), *buf = CR_BUF;
    uint16_t p[4], bg;
    portrait_t *pt = CR_PT;
#if CT_MAPFMT
    if (kd == CK_VENUE) {                          // its palettes: BG 6 the building's, BG 0 the band's colour (the label's gold) as the owner's card will have it
        if (i == 0 && is_cgb) {
            for (n = 0; n < 4; n++) p[n] = ct_bldcol[v][n];
            cr_pal(0, CR_BLD_PAL, p);
            return 0;
        }
        if (i == 1 && is_cgb) {
            uint16_t *q = (uint16_t *)CR_PAL, *hq = (uint16_t *)(CR_PAL + 8 * BGPAL_HUD);
            q[0] = hq[0]; q[1] = BRIGHTEN(COL_GOLD); q[2] = BRIGHTEN(ct_bandcol[v]); q[3] = hq[3];
            if (CR->live) cr_hw(0, 0);
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
#if CT_MAPFMT
    if (kd == CK_VENUE) return CT_H_VEN;
#endif
    return kd == CK_TITLE ? CT_H_TITLE : kd <= CK_DREGS ? CT_H_SD : kd == CK_OWNER ? CT_H_OWN : kd == CK_BOSS ? CT_H_BOSS : CT_H_PAT;
}

static uint8_t cr_gap(uint8_t c) { return c == CR_CARDS - 1 ? CR_LASTGAP : c ? CT_G : CT_GAP_TITLE; }

static uint8_t cr_off(uint8_t c) {                // the px from the card's top to the middle of its stop's block
    uint8_t v = 0, kd = cr_kind(c, &v);
#if CT_MAPFMT
    if (kd == CK_VENUE) return CT_OFF_VEN;
#endif
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
// A frame's budget: the music's tick (up to 18 lines) must start before line 126, and a frame whose work runs past its VBlank makes the main loop wait out a whole frame, the tune
// a tick. A step that costs `lines` raster lines (single speed; a Color double-speed frame is twice as long) starts only if it ends by line 118, and not into the lines the sprites'
// redraw (45) still needs; a refused step is the next frame's.  (In the VBlank, LY 144 and on, there is room.)
#define CR_RES ((CR->pos ^ CR->sig) & 0x1FFF ? 45 : 0)
static uint8_t cr_room(uint8_t lines) {
    uint8_t ly = LY_REG;
    if (CR->next < (CR->scroll >> 3) + 21) return 1;     // (the rows are wanted: the screen shows up to scroll/8 + 19)
    return ly >= 144 || (uint16_t)ly + lines + CR_RES <= 96;
}

static uint8_t cr_tstep(uint8_t r, uint8_t kd) {
    uint8_t n, i, id, m = 2;   // (2 tiles a frame: three left the frame with 4 % to spare, and a pattern copy at an order boundary pushed it past its VBlank: a tick 1.6 frames late)
    uint16_t *cell = (uint16_t *)(CR_BUF + 2);
    if (CR->lw != CR->next) {
        if (!cr_room(26)) return 0;
        CR->lw = CR->next; CR->ld = 0;
        cr_blank(); cr_attr_hud();
        if (kd && is_cgb) for (i = 0; i < 20; i++) CR_ATT[i] = 0;
#if CT_MAPFMT
        if (kd == 2 || kd == 4) for (i = 0; i < 20; i++) CR->row[i] = CR_STRIPE_ID;
#else
        if (kd == 2) for (i = 0; i < 20; i++) CR->row[i] = CR_STRIPE_ID;
#endif
        credits_row_get(r, CR_BUF);
    }
    n = CR_BUF[1];
    while (CR->ld < n && m && cr_room(10)) {
        i = CR->ld++;
        if (cell[i] == 0xFFFF) continue;
        if (is_cgb) {
            id = CR->rt;
            if (++CR->rt == CR_TXT_CN) CR->rt = 0;
            VBK_REG = VBK_BANK_1; credits_tile_put(cell[i], id); VBK_REG = VBK_BANK_0;
#if CT_MAPFMT
            CR_ATT[CR_BUF[0] + i] = (kd == 3 || (kd == 4 && CR_BUF[0] + i < 7) ? CR_BLD_PAL : kd ? 0 : BGPAL_HUD) | 8;
#else
            CR_ATT[CR_BUF[0] + i] = (kd ? 0 : BGPAL_HUD) | 8;
#endif
        } else {
            id = CR->rt;
            if (++CR->rt == CT_RING_N) CR->rt = 0;
            id = id < CR_TXT_DN ? CR_TXT_D + id : id - CR_TXT_DN < 54 ? id - CR_TXT_DN : id - CR_TXT_DN + 1;
            credits_tile_put(cell[i], id);
        }
        CR->row[CR_BUF[0] + i] = id;
        m--;
        music_pump();                                  // (a tile is 0.06 frame: a tick due in the middle of a row is struck then, not at the frame's end, where the pump's clock would lose its lateness)
    }
    return CR->ld >= n;
}

static void cr_pose_fill(uint8_t *d, uint8_t v, uint8_t pose, uint8_t r) {    // the boss's row r (0, 1) in a pose
    uint8_t k, L = (20 - CR->bn) >> 1;
    for (k = 0; k < 20; k++) d[k] = TILE_HUD_BLANK;
    for (k = 0; k < CR->bn; k++) {
        d[L + k] = CR_T_BOSS + 2 * cr_boss(v, 1, pose, k, 0) + r;
        if ((k & 3) == 3) music_pump();                  // (a pose's row is 0.2 frame: a tick due in it is struck within 0.1, not at its end)
    }
}

// card c's local row r into CR->row / CR_ATT; 1: done, 0: call again (a text row's tiles)
static uint8_t cr_card_row(uint8_t c, uint8_t r) {
    uint8_t v = 0, kd = cr_kind(c, &v), tr = 255, tk = 0, k, L, h = CR_PT->h, w = CR_PT->w, i = 255;
    portrait_t *pt = CR_PT;
    if (kd == CK_TITLE) { if (r == 0) tr = CT_TITLE; else if (r == 2) tr = CT_TITLE + 1; }
    else if (kd == CK_SPIGOTEER || kd == CK_DREGS) {
        if (r >= 1 && r < 1 + h) i = r - 1;
        else if (r == 3 + h || r == 5 + h) tr = (kd == CK_SPIGOTEER ? CT_SAL : CT_DREGS) + ((r - 3 - h) >> 1);
#if CT_MAPFMT
    } else if (kd == CK_VENUE) {
        if (r >= CT_R_VB && r < CT_R_VB + 4) { tr = CT_BLD + 4 * v + r - CT_R_VB; tk = CT_MAPFMT == 2 && (r == CT_R_VB + 1 || r == CT_R_VB + 2) ? 4 : 3; }
        else if (CT_MAPFMT == 1 && r >= CT_R_VBAND && r < CT_R_VBAND + 3 && !(CT_FONTFMT == 2 && r != CT_R_VBAND + 1)) { tr = CT_BAND + 3 * v + r - CT_R_VBAND; tk = 2; }
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
            if (!cr_room(CR->gl < 3 && cr_kt[c] != CK_BOSS && cr_kt[c] != CK_PATRONS ? 52 : 28)) return 0;   // (a portrait's header, map and palettes: 0.3 frame in one call)
            for (m = 0; m < 1; m++) {
                if (cr_load_unit(c, CR->gl)) { CR->gl = 255; break; }
                CR->gl++;
                music_pump();                                  // (a unit is a fraction of a frame, a call of three more: the tune's tick falls due in between, not a frame late)
            }
            if (CR->gl != 255) return 0;
            kd = cr_kind(c, &v);
            if (kd == CK_SPIGOTEER) CR->txs = 3 + CR_PT->h;
            else if (kd == CK_DREGS) CR->txd = 3 + CR_PT->h;
        }
        music_pump();
        if (!cr_card_row(c, (uint8_t)(w - CR->gs))) return 0;
        music_pump();
    } else if (w >= CR->wroll) {                           // the roll
        if (w == CR->wroll) { CR->rt = 0; CR->lr = 255; }
        if (CR->gl != 255 && w >= CR->wroll + 8) {          // its robots (the last boss and patrons are off), the Spigoteer's colours back
            for (m = 0; m < 2; m++) {                         // (a pose tile is 0.14 frame on DMG: four a frame left no room for a tick's pattern copy)
                i = CR->gl;
                if (i < 18) load_patron_pose0(5, CR_T_P + 6 * (i / 6), i / 6, i % 6);
                else if (is_cgb && i < 21) { patron_pal_get(5, i - 18, (uint16_t *)CR->row); ((uint16_t *)CR->row)[0] = 0; cr_pal(1, OBJPAL_ROBOT + i - 18, (uint16_t *)CR->row); }
                else if (is_cgb && i == 21) { for (v = 0; v < 8; v++) CR_PAL[64 + v] = CR_SAVE[v]; cr_hw(1, 0); }
                else { CR->gl = 255; break; }
                CR->gl++;
                music_pump();
            }
            if (CR->gl != 255) return 0;
        }
        music_pump();
        if (!cr_roll_step((uint8_t)(w - CR->wroll), 3)) return 0;
        music_pump();
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
    music_pump();
    if (++CR->pr == 2) { CR->pose = CR->pq - 1; CR->pq = 0; CR->sig2 = 255; }
}

extern uint8_t hUGE_tick, hUGE_ticks_per_row;
static uint8_t cr_calm(void) {                                // a boss's pose row (0.2 frame) goes in a frame the tune's tick is light: not a row's first ticks (the driver's row, the pattern copy on tick 3) nor its last (before them)
    return hUGE_tick >= 5 && (uint8_t)(hUGE_tick + 3) < hUGE_ticks_per_row;
}

static void cr_sprites_v(uint8_t busy) {                   // the cards' sprites (the cards that are loaded) and the roll's band
    uint16_t cs, sc = CR->pos, bw;           // (the position of the NEXT frame: the sprites reach the picture a frame after SCY, which is written first thing in the update)
    int16_t y, y0, ya, yb, yc;
    OAM_item_t *oo;
    uint8_t c, k, t = (uint8_t)CR->t, kd, v, pose, bob, n;
    const uint8_t *cx, *lp;
    uint8_t g2 = CR->gc | (CR->gl == 255 ? 64 : 0) | (CR->pose == 1 ? 128 : 0);
    uint16_t g = sc | (uint16_t)((t >> 4) & 7) << 13, dg = g ^ CR->sig;           // (sig: the scroll in bits 0-12, the animation step above)
    uint8_t rd = (dg & 0x1FFF) || g2 != CR->sig2, rs = rd || dg;   // rd: the scroll or a card's loads moved: every sprite is written; rs: only an animation step: the sprites that change in it
    CR->sig = g; CR->sig2 = g2;
    if (rd) hide_all_sprites();                   // (OAM keeps what it has when nothing it shows has moved: the stage is 0.3 frame, and a frame that runs past its VBlank costs the tune a tick)
    while (CR->sc < CR_CARDS && (uint16_t)(CR->ss + cr_hgt(CR->sc) + 1) * 8 <= sc) { CR->ss += cr_hgt(CR->sc) + cr_gap(CR->sc); CR->sc++; }
    cs = CR->ss;
    for (c = CR->sc; c < CR_CARDS && c < CR->sc + 3 && cs * 8 < sc + 160; c++) {
        if (c > CR->gc || (c == CR->gc && CR->gl != 255)) break;
        kd = cr_kind(c, &v);
        y0 = (int16_t)(8 * cs) - (int16_t)sc;                          // the card's top, screen y (the arithmetic is 16-bit and slow: once a card, not a sprite)
        if (kd == CK_SPIGOTEER || kd == CK_DREGS) {
            pose = cr_walk[(t >> 4) & 3];
            y = y0 + 8 * (kd == CK_SPIGOTEER ? CR->txs : CR->txd) + 12;
            if (!rs) {}
            else if (kd == CK_SPIGOTEER) cr_fig(0, y, CT_SAL_X, OBJ_BARTENDER + BT_PIC(pose) * BARTENDER_TILES_PER_FRAME, OBJPAL_BARTENDER, 0);
            else cr_fig(4, y, CT_DREGS_X, CR_T_D + pose * 8, is_cgb ? OBJPAL_CAST : 0, 0);
        } else if (kd == CK_BOSS) {
            bw = cs + CT_R_BBODY;
            pose = cr_seq[(t >> 4) & 7];
            if ((pose != CR->pose || CR->pq) && !busy && CR->next >= bw + 3 && CR->next - bw <= 32 && (!sound_on || cr_calm()) && cr_room(30)) cr_pose(v, pose, bw);
            if (rs) cr_oam(24, y0 + 8 * CT_R_BBODY + 8, ((20 - CR->bn) >> 1) * 8 + cr_hat_dx[v] + 8, CR_T_HAT + (CR->pose == 1 ? 2 : 0), is_cgb ? OBJPAL_TOP : S_PALETTE);
        } else if (kd == CK_PATRONS) {
            cx = ct_cx[v]; lp = ct_lp[v];
            ya = y0 + 8 * CT_R_PA - 4; yb = ya + 8 * CT_R_PN; yc = yb + 8 * CT_R_PN;       // (the three name rows' sprite y: a sprite's OAM y is 4 above its name row's top; the pairs are written in place, a call each was 0.1 frame a card)
            for (k = 0; rs && k < (is_cgb ? 8 : 3); k++) {
                if (!rd && ((((t >> 4) + k) & 3) > 1)) continue;   // (an animation step moves the two whose bob starts or ends in it)
                bob = (((t >> 4) + k) & 3) ? 0 : 2;
                if (is_cgb) {
                    y = k < 3 ? ya : k < 6 ? yb : yc;
                    pose = k < 3 ? CR_T_P + 6 * k : PATRON_X_S0 + 4 * (k - 3);
                    n = (1 + lp[k]) | (k < 3 ? 0 : 8);
                } else { y = yb; pose = CR_T_P + 6 * k; n = 0; }
                y -= bob;
                oo = shadow_OAM + 8 + 2 * k;
                if ((uint16_t)(y - 1) >= 159) { oo->y = 0; oo[1].y = 0; }
                else {
                    oo->y = oo[1].y = (uint8_t)y; oo->x = cx[k]; oo[1].x = cx[k] + 8; oo->tile = pose; oo[1].tile = pose + 2; oo->prop = oo[1].prop = n;
                }
                if ((k & 1) && k != 7) music_pump();                               // (a card of eight patrons is a long frame on Color: the tick falls due in the middle)
            }
        }
        cs += cr_hgt(c) + cr_gap(c);
    }
    if (rs && CR->gc >= CR_CARDS && CR->gl == 255) {             // the roll's band: the robots bob in turn, the Spigoteer raises a hand now and then
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
    cr_layout();
    credits_tile_put(CT_STRIPE, CR_STRIPE_ID);        // (LCD off)
    if (is_cgb) for (y = 0; y < 8; y++) CR_SAVE[y] = o[64 + y];    // (OBJ 0, the Spigoteer's: the bosses' topper wears it in the cast)
    else o[2] = DMG_HAT_OBP1;                          // (OBP1: the topper's, for the whole cast; cr_leave puts it back)
    CR->scroll = CR->pos = CR_W0 * 8 + CT_OFF_TITLE - 72; CR->next = 0; CR->t = 0; CR->ls = (uint8_t)sys_time; CR->phase = 0; CR->from_story = from_story;
    CR->gc = 0; CR->gs = CR_W0; CR->gl = 0; CR->sc = 0; CR->ss = CR_W0; CR->ts = CR_W0; CR->live = 0; CR->lw = 0xFFFF; CR->rt = 0; CR->pb = STORY_PORTRAIT_BASE; CR->pp = BGPAL_PATRON; CR->pose = 0; CR->pq = 0; CR->sig = 0xFFFF; CR->sig2 = 255;
    CR->k = 0; CR->st = 0; CR->ph = 0; CR->nc = 0; CR->rr = 0;
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
    if (!is_cgb) {
        CR_PAL[2] = CR_PAL[3];                        // (OBP1 as it was)
        CRITICAL { remove_LCD(cast_isr); add_LCD(lcd_isr); }
        LYC_REG = BANNER_LYC;
    }
    trans_cast_set(CR_PAL);                           // the card's own colours, whatever the fade was doing
    TRANS_WANT();                                     // (src/trans.c: the next screen comes up behind the drink)
    SCY_REG = 0;                                      // (the roll's last scroll: the next screen is built from the top; the story's score entry did not reset it)
    if (s) story_end();
    else { title_back = TM_BONUS; title_back_sel = 0; title_enter(); }   // BONUS, the cursor on CREDITS (the first item)
}


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
    if (is_cgb) music_pump();                              // (Color: the frame's tick first, so the main loop's own never has to be the late one)
    if (LY_REG >= 144) CR->scroll = CR->pos;               // (SCY moves in the VBlank only, and FIRST: the update can start in the VBlank's last lines, the main loop's ISR work is before it; an update that starts late would tear the top lines, the next frame catches up)
    SCY_REG = (uint8_t)CR->scroll;
    music_pump();                                          // (after the scroll register: the tick falls due here when the frame began late)
    for (d = (uint8_t)((uint8_t)sys_time - CR->ls), CR->ls = (uint8_t)sys_time; d; d--) { CR->t++; cr_step(); }   // (frames, not the tune's ticks: a lost tick does not stretch it)
    if (CR->st == 3 && CR->ph >= CR_END_HOLD && (!sound_on || cur_tune != TUNE_CREDITS)) { cr_leave(); return 1; }   // (the roll's end, and the tune over: it ends on its own, cur_tune goes to TUNE_NONE)
    if (CR->next <= (CR->scroll >> 3) + (CR->next >= CR->wroll ? CR_AHEAD_R : CR_AHEAD_C)) { cr_gen(); busy = 1; }
    music_pump();
    cr_sprites_v(busy);
    music_pump();
    return 0;
}
