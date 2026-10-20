// The credits roll (owner 2026-10-17): a cast of characters, then the game's credits scrolling up the screen in the story's lettering, and
// "THANKS FOR PLAYING!" alone at the end. It IS the story's credits: the CREDITS scene shows its picture and the four closing narrator
// pages, and its end (story.c scene_done) is this roll (credits_enter(1); its end is story_end: the STORY score entry) and from the
// title's BONUS > CREDITS (credits_enter(0); its end or B: back to BONUS, the cursor on CREDITS). The wording is CREDITS.md's, the
// "Special thanks to:" list in it.
//
// The music is the credits tune (TUNE_CREDITS), started by credits_enter while the screen is built (BONUS' own tune stops there). The whole
// roll is tied to the tune's POSITION (the frames its engine has ticked: cr_pos, the same count as the tune's length, so a tempo change inside it
// does not matter) and its LENGTH (music_tune_frames), not to constants: every boundary below is a share of the tune (units of 1/352), so a
// longer arrangement slows everything in proportion. With the sound off the position is the frames on the screen (the same pace).
//
//   units  0-6     "CAST OF CHARACTERS"
//          7-230   32 cards of 7 units: Sal Tapley AKA the Spigoteer, Dregs (each his story portrait, his sprite, his name), then for each
//                  venue the owner (portrait, name, venue), the patrons (three, a label each) and the boss (animated: his fight walk and gulp)
//          231-321 the credits roll (text rows streamed in as before; its first 40 frames build it behind the fade)
//          322-351 "THANKS FOR PLAYING!" alone, the tune's last bars and its ring; the roll ends when the tune has
//          (D3c, 146 s: a unit is 24.8 frames, a card 2.9 s; the 88 s C3: 15 frames, 1.75 s; a 180 s tune 5.1 s)
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
#define CR_BAND       14      // the roll's row where the sprites' band starts (4 rows)
#define CR_T_P       100      // the patrons' OBJ tiles: 3 variants x 6 (OBJ ids 100-117, in dgag.c's patron range)
#define CR_T_D        56      // Dregs's 8 OBJ tiles
#define CR_T_HAT      64      // the topper (8x16)
#define CR_T_BOSS    100      // BG ids: the boss's tile pairs (top, bottom; 30 at most, 60 tiles)
#define CR_RING_T     93      // BG ids of the roll's text: a ring of CT_RING tiles (the roll shows no portrait or boss)
#define CR_HDR_T     160      // the venue header's tiles (17 at most), kept through its venue's three cards
#define CR_TXT_T     178      // a card's text tiles, up to 255
#define CR_BT_X      120      // the Spigoteer's left edge in the roll; the robots stand at 24, 56, 88
#define OBJPAL_ROBOT   5
#define OBJPAL_CAST    3      // Dregs's, the topper's
#define BGPAL_BOSS     5
#define BGPAL_HDR      6      // the venue header's BG palette (CGB): a copy of the HUD's, the fades leave it alone within a venue
#define COL_BAND  0x2043      // RGB15(3, 2, 8): the band (colour 3 of the HUD palette), the bosses' colour 0
#define DMG_HAT_OBP1  0x93    // the topper on the band: its three shades one step lighter (idx 1 white, 2 light, 3 dark; the DMG boss body is remapped the same way)

#define CR_CARDS      33      // the title, the Spigoteer, Dregs, then three cards for each of the ten venues
#define CR_SHARE      352     // the tune's units: 1/352 of it (a row of the 88 s draft)

// state in story_scratch
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
};
#define CR ((struct cr_state *)story_scratch)
// (story_scratch + 68 / + 69: the DMG header's BGP and the card's, main.c cast_isr)
#define CR_PAL ((uint8_t *)story_scratch + 72)                          // the card's colours (CGB: 128 bytes; DMG: BGP, OBP0, OBP1, the first OBP1)
#define CR_PT  ((portrait_t *)(story_scratch + 200))                    // the owner's portrait (while a venue card is built)
#define CR_BUF ((uint8_t *)story_scratch + 200 + sizeof(portrait_t))    // 64 bytes: four tiles on their way, the owner's name
typedef char cr_fits[(sizeof(struct cr_state) <= 68 && 200 + sizeof(portrait_t) + 64 <= STORY_SCRATCH) ? 1 : -1];

#define CR_F0   (CR->roll + 40)

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

#define CR_N CT_ROLL_N
#define CR_LAST_T ((CR_FIRST + (CR_N - 2)) * 8 + 8 - 72)   // the scroll at which the last two rows are in the middle of the screen

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
        r = w >= CR_FIRST && (uint8_t)(w - CR_FIRST) < CR_N ? ct_roll[w - CR_FIRST] : 255;
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

static void cr_rows(uint8_t y, uint8_t n) {       // n rows from row y of the roll's rows, ring slot y & 31 (the build: the tune ticked between tiles)
    uint8_t d;
    for (; n; n--, y++) {
        do { d = cr_roll_step(y, 1); cr_pp(); } while (!d);
        cr_put(y & 31);
    }
}

// ---- the tune's position, in frames ---------------------------------------------------------------------------------------------------
static uint16_t cr_pos(void) {
    if (sound_on && cur_tune == TUNE_CREDITS) return music_frames;   // the frames the engine has ticked since the tune began: its real position, whatever its tempo does
    return CR->t;
}

static uint16_t cr_share(uint16_t units) {        // units / 352 of the tune (16-bit maths: the library's long multiply and divide would not fit ROM0)
    uint16_t q = CR->T / CR_SHARE, r = CR->T - q * CR_SHARE;
    return q * units + ((r >> 3) * units) / (CR_SHARE >> 3);
}

// ---- the card's colours: in RAM, faded to the hardware by trans.c ----------------------------------------------------------------------
static void cr_pal(uint8_t obj, uint8_t i, const uint16_t *p) {   // CGB: palette i of the BG (obj 0) or OBJ (1) set
    uint16_t *q = (uint16_t *)(CR_PAL + (obj ? 64 : 0) + i * 8);
    q[0] = p[0]; q[1] = p[1]; q[2] = p[2]; q[3] = p[3];
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

static void cr_sprites(void) {                    // the roll's band
    int16_t y = (int16_t)(CR_FIRST + CR_BAND) * 8 - CR->scroll + 16;   // the band's top, OAM y
    uint8_t t = (uint8_t)CR->t, k, f, bob;
    for (k = 0; k < 3; k++) {                         // the robots, bobbing in turn (2 px up for 16 frames in every 64)
        bob = (((t >> 4) + k) & 3) ? 0 : 2;
        cr_oam(4 + 2 * k, y + 8 - bob, 24 + 32 * k + 8, CR_T_P + 6 * k, is_cgb ? OBJPAL_ROBOT + k : 0);
        cr_oam(5 + 2 * k, y + 8 - bob, 24 + 32 * k + 16, CR_T_P + 6 * k + 2, is_cgb ? OBJPAL_ROBOT + k : 0);
    }
    f = ((t >> 4) & 3) == 1 ? BT_CATCH : BT_IDLE;     // the Spigoteer: a hand up now and then
    cr_fig(0, y, CR_BT_X, OBJ_BARTENDER + f * BARTENDER_TILES_PER_FRAME, OBJPAL_BARTENDER, 0);
}

// ---- the cards ------------------------------------------------------------------------------------------------------------------------
// card c: 0 the title, 1 the Spigoteer, 2 Dregs (portrait and sprite), then venue by venue three cards: 3 + 3v the owner (portrait, name, venue),
// 4 + 3v the patrons (the venue, three with a label each), 5 + 3v the boss (animated on the band, his name, the venue).
// Writing VRAM with the LCD on is slow (the library waits for the picture's blanking for every byte): a card is built in UNITS, CR_UNITS a
// frame (a row, a few tiles), so that no frame runs over its VBlank and the tune never loses a tick. Stage 1 blanks the rows the last card
// used, stage 2 loads, stage 3 writes the rows; then the card fades in.
enum { CK_TITLE, CK_SPIGOTEER, CK_DREGS, CK_OWNER, CK_PATRONS, CK_BOSS };
static uint8_t cr_kind(uint8_t c, uint8_t *v) {    // the card's kind, and its venue
    if (c < 3) return c;
    c -= 3;
    *v = c / 3;
    return CK_OWNER + c % 3;
}

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

static void cr_remap(uint8_t *b, uint8_t n) {     // DMG: n bytes of tiles with the shades one step on (0 -> 3, the band; 1 -> 0; 2 -> 1; 3 -> 2): v - 1, a plane at a time
    uint8_t i, lo;
    for (i = 0; i < n; i += 2) {
        lo = ~b[i];                                   // (the low bit always flips; the high bit with it where the low bit was 0)
        b[i + 1] ^= lo;
        b[i] = lo;
    }
}

static uint8_t cr_spk(uint8_t c, uint8_t v) { return c == CK_SPIGOTEER ? 0 : c == CK_DREGS ? 1 : cr_owner[v]; }

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
                    cr_pal(0, BGPAL_PATRON + n, p);
                }
            }
            return 0;
        }
        i -= 3;
        nch = pt->ntiles;
        if (i < nch) {                             // its tiles, one a unit (a byte loop in C is ~70 cycles a byte, a tile 0.07 frame)
            if (is_cgb) portrait_tile_set(k, i, STORY_PORTRAIT_BASE + i);
            else {
                portrait_tile_copy(k, i, 1, buf);
                nch = portrait_backdrop(k);        // DMG: the backdrop becomes the band's shade 3: 3 stays, 2 and 3 change places (lo ^= hi), 1 and 3 (hi ^= lo); the generator refuses shade 0
                if (nch == 2) for (n = 0; n < 16; n += 2) buf[n] ^= buf[n + 1];
                else if (nch == 1) for (n = 0; n < 16; n += 2) buf[n + 1] ^= buf[n];
                set_bkg_data(STORY_PORTRAIT_BASE + i, 1, buf);
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
                cr_pal(1, OBJPAL_CAST, p);
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
        if (i > 18) return 1;
        if (i < 18) load_patron_pose0(v, CR_T_P + 6 * (i / 6), ct_slot[v][i / 6], i % 6);      // (a tile at a time: with the LCD on a byte takes two scanlines; the variant in slot k)
        else if (is_cgb) for (k = 0; k < 3; k++) { patron_pal_get(v, ct_slot[v][k], p); p[0] = 0; cr_pal(1, OBJPAL_ROBOT + k, p); }
        return 0;
    }
    return 1;
}

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
    } else {                                       // the patrons (the venue is in the header): the three labels on one row
        if (i == 0) cr_trow(CT_PATA + v, CR->ky, &id);
        else return 1;
    }
    CR->tn = id;
    return 0;
}

static void cr_card_sprites(uint8_t c) {          // every frame a card is shown
    uint8_t t = (uint8_t)CR->t, k, bob, v = 0, kd = cr_kind(c, &v), pose, y;
    if (kd == CK_SPIGOTEER || kd == CK_DREGS) {    // his walk cycle (walk, idle, the other foot, idle: 16 frames each), at the text's left, level with it
        pose = cr_walk[(t >> 4) & 3];
        y = 8 * (CR->ky + CR_PT->h + 2) + 12;      // (OAM y: the sprite's top 4 px above the first text row's, so that it stands level with the two lines)
        if (kd == CK_SPIGOTEER) cr_fig(0, y, CT_SAL_X, OBJ_BARTENDER + pose * BARTENDER_TILES_PER_FRAME, OBJPAL_BARTENDER, 0);
        else cr_fig(0, y, CT_DREGS_X, CR_T_D + pose * 8, is_cgb ? OBJPAL_CAST : 0, 0);
    } else if (kd == CK_BOSS) {                    // his walk and gulp, the topper bobbing with the stomp
        pose = cr_seq[(t >> 4) & 7];
        if (pose != CR->pose) cr_pose_rows(v, pose, 1);
        cr_oam(0, 8 * CR->ky + 8, ((20 - CR->bn) >> 1) * 8 + cr_hat_dx[v] + 8, CR_T_HAT + (pose == 1 ? 2 : 0), is_cgb ? OBJPAL_CAST : S_PALETTE);
    } else if (kd == CK_PATRONS) {
        for (k = 0; k < 3; k++) {                 // the three patrons, bobbing in turn, each centred over his own label (ct_cx)
            bob = (((t >> 4) + k) & 3) ? 0 : 2;
            cr_oam(2 * k, 8 * CR->ky - 8 - bob, ct_cx[v][k], CR_T_P + 6 * k, is_cgb ? OBJPAL_ROBOT + k : 0);
            cr_oam(2 * k + 1, 8 * CR->ky - 8 - bob, ct_cx[v][k] + 8, CR_T_P + 6 * k + 2, is_cgb ? OBJPAL_ROBOT + k : 0);
        }
    }
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
    CR->T = music_tune_frames(TUNE_CREDITS);          // the timeline: shares of the tune (1/352: 7 a card, the title included; the roll to 322)
    CR->e_title = CR->card_len = cr_share(7);
    CR->roll = CR->e_title + (CR_CARDS - 1) * CR->card_len;
    CR->f1 = cr_share(322);
    CR->k = (uint8_t)((CR_LAST_T * 32 + (CR->f1 - CR_F0) / 2) / (CR->f1 - CR_F0));
    CR->scroll = 0; CR->card = 255; CR->next = CR_AHEAD + 1; CR->t = 0; CR->ls = (uint8_t)sys_time; CR->phase = 0; CR->from_story = from_story; CR->f = 0; CR->tmask = 0; CR->amask = 0;
    SCX_REG = 0; SCY_REG = 0;
    story_phase = STORY_PHASE_CREDITS;
    game_state = GS_STORY;
    music_load_now();                                 // the tune's first notes sound with the picture
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
    SCY_REG = 0;
    TRANS_WANT();                                     // (src/trans.c: the next screen comes up behind the drink)
    if (s) story_end();
    else { title_back = TM_BONUS; title_back_sel = 0; title_enter(); }   // BONUS, the cursor on CREDITS (the first item)
}

// story_update, every frame of the roll (GS_STORY). 1: the screen changed.
uint8_t credits_update(uint8_t pressed) BANKED {
    uint8_t c, top, hd, old;
    uint16_t f, p;
    if (pressed & (J_B | J_START)) { cr_leave(); return 1; }
    CR->t += (uint8_t)((uint8_t)sys_time - CR->ls);
    CR->ls = (uint8_t)sys_time;
    f = cr_pos();
    CR->f = f;
    if (sound_on ? (cur_tune != TUNE_CREDITS && CR->t > 30) : f >= CR->T) { cr_leave(); return 1; }   // (the tune ends: cur_tune goes to TUNE_NONE)
    if (f < CR->roll) {                                                    // the cast
        c = f < CR->e_title ? 0 : 1 + (uint8_t)((f - CR->e_title) / CR->card_len);
        if (c >= CR_CARDS) c = CR_CARDS - 1;
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
