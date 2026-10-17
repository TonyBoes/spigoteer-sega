// The credits roll (owner 2026-10-17): a cast of characters, then the game's credits scrolling up the screen in the story's lettering, and
// "THANKS FOR PLAYING!" alone at the end. It IS the story's credits: the CREDITS scene shows its picture and the four closing narrator
// pages, and its end (story.c scene_done) is this roll (credits_enter(1); its end is story_end: the STORY score entry) and from the
// title's BONUS > CREDITS (credits_enter(0); its end or B: back to BONUS, the cursor on CREDITS). The wording is CREDITS.md's, the
// "Special thanks to:" list in it.
//
// The music is the credits tune (TUNE_CREDITS), started by credits_enter while the screen is built (BONUS' own tune stops there). The whole
// roll is tied to the tune's POSITION (the frames its engine has ticked: cr_pos, the same count as the tune's length, so a tempo change inside it does not matter) and its LENGTH (music_tune_frames: orders x 64 rows x tempo), not to
// constants: every boundary below is a share of the tune (units of 1/352, the 352 rows of the 88 s C3 draft), so a longer arrangement slows
// everything in proportion. With the sound off the position is the frames on the screen (the same pace).
//
//   units  0-7     "CAST OF CHARACTERS"
//          8-17    card: the Spigoteer (the player) and Dregs, the Pour-Off's rival
//          18-217  20 cards of 10 units: the ten venues' owner and boss (their story portrait, his fight body and topper: build/boss_cast_art.h),
//                  then the ten venues' three patrons each, side by side with a label under each
//          218-321 the credits roll (text rows streamed in as before; its first 40 frames build it behind the fade)
//          322-351 "THANKS FOR PLAYING!" alone, the tune's last bars and its held C; the roll ends when the tune has
//          (C3, 88 s: a unit is 15 frames, a card 2.5 s; a 180 s tune: 30.7 frames, a card 5.1 s)
//
// A card changes behind a fade (trans.c trans_cast: the picture to the band colour and back, ~8 frames each way, palette RAM written in the
// VBlank only). The card's colours live in RAM (CR_PAL: all 128 bytes of palette RAM on CGB; BGP / OBP0 / OBP1 on DMG), never written to the
// hardware by the card's own code, so it is built behind the faded screen: the old card fades out, its rows are cleared, the new one's tiles,
// palettes and rows are loaded (CR_UNITS a frame), its sprites set, then it fades in. The tilemap is the 32-row ring the roll scrolls (SCY 0
// during the cast; the cards use rows 0-17). BG tile ids: the owner's portrait from STORY_PORTRAIT_BASE (44 at most), the boss's body from
// CR_T_BOSS; OBJ ids: Dregs 56.., the topper 64.., the patrons' shift-0 poses 100-117 (the roll's robots are the same).
//
// The roll's text is one string per tilemap ROW, centred; "" is a blank row. The lines of one sentence are on consecutive rows, the items of
// a list have two blank rows between them, sections more. Every line is at most 18 tiles (a clear column at each edge). CR_BAND is the row
// where the sprites' band starts (4 rows: the three robots stand under the "robot friends" line, who bob in turn, and the Spigoteer, facing
// them, raises a hand now and then). B / START skip (not during a fade: they last 8 frames). With the sound on the roll ends when the music
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

extern uint8_t overlay_on, joy, story_phase;

#define CR_FIRST      18      // the roll's first row, in world rows (just under the screen)
#define CR_AHEAD      20      // rows are kept written up to T + CR_AHEAD (T: the top row of the screen)
#define CR_BAND       14      // the roll's row where the sprites' band starts (4 rows)
#define CR_T_P       100      // the patrons' OBJ tiles: 3 variants x 6 (OBJ ids 100-117, in dgag.c's patron range)
#define CR_T_D        56      // Dregs's 8 OBJ tiles
#define CR_T_HAT      64      // the topper (8x16)
#define CR_T_BOSS    100      // BG ids: the boss's tile pairs (top, bottom; 30 at most, 60 tiles)
#define CR_BT_X      120      // the Spigoteer's left edge in the roll; the robots stand at 24, 56, 88
#define OBJPAL_ROBOT   5
#define OBJPAL_CAST    3      // Dregs's, the topper's
#define BGPAL_BOSS     5
#define COL_BAND  0x2043      // RGB15(3, 2, 8): the band (colour 3 of the HUD palette), the bosses' colour 0
#define DMG_HAT_OBP1  0x93    // the topper on the band: its three shades one step lighter (idx 1 white, 2 light, 3 dark; the DMG boss body is remapped the same way)

#define CR_CARDS      33      // the title, the Spigoteer, Dregs, then three cards for each of the ten venues
#define CR_LAG        19      // hundredths of a frame the tune loses to one card change (the fades' ticks, the LCD-off build's: measured)
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
    uint8_t step;             // the unit of the card's stage
    uint32_t tmask, amask;    // rows (bit y) the last card wrote: their tiles, and their CGB attributes
    uint16_t T;               // the tune's frames
    uint16_t e_title, card_len, roll, f1;   // the timeline's boundaries (frames): the title card ends, a card's length, the roll starts, its scroll ends
    uint8_t k;                // the scroll's speed: px = frames * k / 32
    uint8_t bn, bp, pose;     // the boss card: his columns, his tile pairs, the pose drawn
    uint8_t d0, ph;           // the LCD-off build's tick clock: DIV last read, the tick count (the period 274, 274, 275 DIV counts: 274.3 a frame)
    uint16_t acc, dsum;       // ... DIV counts since the last tick, all of them
    uint8_t lagq;             // the tune's lag behind the wall clock, in hundredths of a frame (see CR_LAG)
};
#define CR ((struct cr_state *)story_scratch)
#define CR_PAL ((uint8_t *)story_scratch + 72)                          // the card's colours (CGB: 128 bytes; DMG: BGP, OBP0, OBP1, the first OBP1)
#define CR_PT  ((portrait_t *)(story_scratch + 200))                    // the owner's portrait (while a venue card is built)
#define CR_BUF ((uint8_t *)story_scratch + 200 + sizeof(portrait_t))    // 64 bytes: four tiles on their way, the owner's name
typedef char cr_fits[(sizeof(struct cr_state) <= 72 && 200 + sizeof(portrait_t) + 64 <= STORY_SCRATCH) ? 1 : -1];

#define CR_F0   (CR->roll + 40)

// ---- the cast: names from the game's own data (boss names and venues: src/rush.c; the people: the story's speakers; the patrons have none) ----
static const char *const cr_venue[10] = {
    "THE SALOON", "THE STADIUM", "THE LUMBER LODGE", "THE BISTRO", "THE IGLOO", "THE ROBOT FACTORY", "THE CHROME COW", "THE TEAHOUSE",
    "THE JUNGLE ZOO", "THE SPACE LOUNGE",
};
static const char *const cr_bname[10] = {         // the boss's name, in venue order (Boss Rush's)
    "BIG TEX", "THE MASCOT", "SASQUATCH", "THE CRITIC", "THE YETI", "PROTOTYPE", "DUKE", "SUMO CHAMP", "LEO THE LION", "MOTHERSHIP",
};
static const uint8_t cr_owner[10] = { 2, 3, 4, 5, 6, 7, 11, 8, 10, 9 };   // the venue owner's speaker id (tools/gen_story.py SPEAKERS): Sadie, Coach, June, Colby, Aurora, Manager-Bot, Granny, Hana, Kiki, Zizz
static const uint8_t cr_hat_dx[10] = { 16, 8, 12, 9, 9, 8, 16, 16, 6, 12 };   // boss.c rows[]: the topper's x from his left edge
static const uint8_t cr_seq[8] = { 0, 1, 0, 2, 0, 1, 0, 2 };      // the boss's poses (WALK, STOMP, GULP: boss.h BP_*), 16 frames each
// The patrons have no names in the game: one short label each (at most 6 letters), three a venue (art order A, B, C). Change a name here.
static const char *const cr_pat[10][3] = {
    { "DUSTY", "ROSIE", "HANK" },        // the saloon: the cowboy, the cowgirl, the ranch hand
    { "PETE", "SERENA", "NORM" },        // the stadium: the cap fan, the band fan, the ref
    { "TIMBER", "RUSTY", "SPRUCE" },     // the lumber lodge
    { "PIERRE", "BRIE", "BASIL" },       // the bistro
    { "IGGY", "POLLY", "MOOSE" },       // the igloo: the parka man, the parka girl, the big parka
    { "BOXY", "VOLTA", "BLIP" },         // the robot factory
    { "SPIKE", "BANDIT", "SLICK" },      // the chrome cow
    { "KAGE", "SAKURA", "RONIN" },       // the teahouse
    { "COCO", "BAMBOO", "MUDDY" },       // the jungle zoo: the monkey, the panda, the hippo
    { "ZORP", "XENO", "GLORP" },         // the space lounge: the green one with eye stalks, the grey one, the squid
};

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

static uint8_t cr_len(const char *s) { uint8_t n = 0; while (s[n]) n++; return n; }

// patron k's centre x (px) on a venue card: the columns 48 px apart, 32 / 80 / 128; a label of an odd number of tiles centres on a tile boundary
// + 4 px, so its sprite moves 4 px with it (the sprite is centred on the label)
static uint8_t cr_pat_cx(uint8_t v, uint8_t k) {
    return 32 + 48 * k + ((cr_len(cr_pat[v][k]) & 1) ? 4 : 0);
}

// a venue's middle label goes a row lower (row 12; the other two on row 10) when it would stand closer than a tile to either neighbour
static uint8_t cr_lowered(uint8_t v) {
    uint8_t k, n, g[2];
    for (k = 0; k < 2; k++) {
        n = cr_len(cr_pat[v][k]);
        g[k] = (cr_pat_cx(v, k + 1) - 4 * cr_len(cr_pat[v][k + 1])) - (cr_pat_cx(v, k) + 4 * n);
    }
    return g[0] < 8 || g[1] < 8;
}

// ---- the roll. 20 columns a row, one string a ROW. Owner's lines (2026-10-17): "Game Design, Media, and Story by Tony and his tireless team of
// robot friends"; "no credits for public domain tunes. Public Domain."; "Special thanks to:" the platforms, frameworks and projects used.
// A sentence's lines are on consecutive rows; a list's items have two blank rows between them; a section gap is four or five.
static const char *const cr_text[] = {
    "SPIGOTEER",
    "", "", "",
    "GAME DESIGN,", "MEDIA, AND", "STORY BY", "TONY", "AND HIS TIRELESS", "TEAM OF", "ROBOT FRIENDS",   // one sentence
    "", "", "",
    "", "", "", "",                                 // the sprites' band (CR_BAND: 4 rows)
    "", "", "", "",
    "MUSIC",
    "", "", "",
    "PUBLIC DOMAIN", "MELODIES,", "ARRANGED", "FOR THIS GAME",                           // one sentence
    "", "", "", "", "",
    "SPECIAL", "THANKS TO:",
    "", "", "",
    "GBDK-2020", "", "",                            // the list: an item, two blank rows
    "SDCC", "", "",
    "HUGEDRIVER", "", "",
    "RGBDS", "", "",
    "SAMEBOY", "", "",
    "PYBOY", "", "",
    "PAN DOCS", "", "",
    "THE GBDEV", "COMMUNITY",                       // (one item, two lines)
    "", "", "", "", "", "", "", "", "", "", "", "",   // the screen empties before the last words
    "THANKS FOR", "PLAYING!",
};
#define CR_N (sizeof(cr_text) / sizeof(cr_text[0]))
#define CR_LAST_T ((CR_FIRST + (CR_N - 2)) * 8 + 8 - 72)   // the scroll at which the last two rows are in the middle of the screen

static uint8_t cr_glyph(char c) {
    if ((uint8_t)(c - 'A') < 26) return glyph_az[(uint8_t)(c - 'A')];
    switch (c) {
    case '.': return ST_GLYPH_PERIOD; case ',': return ST_GLYPH_COMMA; case '!': return ST_GLYPH_EXCL;
    case '?': return ST_GLYPH_QUEST; case '\'': return ST_GLYPH_APOS; case '-': return ST_GLYPH_HYPHEN;
    case ':': return ST_GLYPH_COLON;
    }
    return GLYPH_FAST(c, glyph_for(c));
}

static void cr_blank(void) { uint8_t i; for (i = 0; i < 20; i++) CR->row[i] = TILE_HUD_BLANK; }

static void cr_cell(const char *s, uint8_t c0, uint8_t w) {   // s centred in the columns c0 .. c0 + w - 1 of CR->row
    uint8_t i, n = cr_len(s), x = c0 + ((uint8_t)(w - n) >> 1);
    for (i = 0; i < n; i++) CR->row[x + i] = cr_glyph(s[i]);
}

static void cr_place(const char *s, uint8_t cx) {   // s centred on x = cx px (to the tile), kept a tile clear of each edge
    uint8_t i, n = cr_len(s);
    int16_t x = (int16_t)cx - 4 * n;
    if (x < 8) x = 8;
    if (x > 152 - 8 * n) x = 152 - 8 * n;
    for (i = 0; i < n; i++) CR->row[(x >> 3) + i] = cr_glyph(s[i]);
}

static void cr_put(uint8_t y) {                   // a row of the map (LCD off: the project's own fast copy; on: the library's, which waits for the picture)
    if (LCDC_REG & LCDCF_ON) set_bkg_tiles(0, y, 20, 1, CR->row);
    else vram_put(0, y, CR->row, 20);
}

// the row for world row w (blank before the roll and after it), centred, into CR->row
static void cr_build(uint8_t w) {
    cr_blank();
    if (w >= CR_FIRST && (uint8_t)(w - CR_FIRST) < CR_N) cr_cell(cr_text[w - CR_FIRST], 0, 20);
}

static void cr_rows(uint8_t y, uint8_t n) {       // n rows from row y of the roll's rows (blank where it is not), ring slot y & 31
    for (; n; n--, y++) {
        cr_build(y);
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

// ---- the tune's ticks while the LCD is off (no VBlank to count): the DIV register (16384 Hz, 274.3 counts a frame), read often enough not to wrap
// (16 ms): a tick every 274, 274, 275 counts, so the tune keeps exact time (music_pump's 69 timer counts a frame are 0.6% slow) ----------------------
static void cr_tk(void) {
    uint8_t n = DIV_REG, d = n - CR->d0;               // (read once: a second read would lose the counts between the two)
    CR->d0 = n;
    CR->acc += d;
    CR->dsum += d;
    while (CR->acc >= (CR->ph % 3 == 2 ? 275 : 274)) {
        CR->acc -= (CR->ph % 3 == 2 ? 275 : 274);
        CR->ph++;
        music_tick();
    }
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

static void cr_data(uint8_t first, uint8_t n, const uint8_t *d) {   // set_bkg_data two tiles at a time, the music pumped between (one call of six is a good half frame)
    uint8_t j;
    for (j = 0; j < n; j += 2) {
        cr_tk();
        set_bkg_data(first + j, n - j > 2 ? 2 : n - j, d + 16 * j);
    }
}

static uint8_t cr_spk(uint8_t c, uint8_t v) { return c == CK_SPIGOTEER ? 0 : c == CK_DREGS ? 1 : cr_owner[v]; }

static uint8_t cr_load_unit(uint8_t c, uint8_t i) {   // unit i of card c's loads; 1: there are no more
    uint8_t v = 0, k, n, nch, kd = cr_kind(c, &v), *buf = CR_BUF;
    uint16_t p[4];
    portrait_t *pt = CR_PT;
    if (kd == CK_SPIGOTEER || kd == CK_DREGS || kd == CK_OWNER) {
        k = cr_spk(kd, v);
        if (i == 0) {                              // the portrait: its palettes (BG 2-4)
            portrait_get(k, pt);
            if (is_cgb) for (n = 0; n < pt->npal; n++) cr_pal(0, BGPAL_PATRON + n, pt->pal + 4 * n);
            return 0;
        }
        i--;
        nch = (pt->ntiles + 3) / 4;
        if (i < nch) {                             // its tiles, four at a time
            n = pt->ntiles - 4 * i;
            if (n > 4) n = 4;
            portrait_tile_copy(k, 4 * i, n, buf);
            cr_data(STORY_PORTRAIT_BASE + 4 * i, n, buf);
            return 0;
        }
        if (kd == CK_DREGS && i == nch) { dregs_cast_load(CR_T_D, p); if (is_cgb) cr_pal(1, OBJPAL_CAST, p); return 0; }
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
        if (i == 1) { cr_boss(v, 2, 0, 0, buf); set_sprite_data(CR_T_HAT, 4, buf); return 0; }   // the topper: still and bobbing
        i -= 2;
        nch = (CR->bp * 2 + 3) / 4;
        if (i >= nch) return 1;
        n = cr_boss(v, 0, i, 0, buf);              // his body's tiles, four at a time (DMG: the shades one step on)
        if (!is_cgb) cr_remap(buf, n << 4);
        cr_data(CR_T_BOSS + 4 * i, n, buf);
        return 0;
    } else if (kd == CK_PATRONS) {
        if (i > 6) return 1;
        if (i < 6) load_patron_pose0(v, CR_T_P + 6 * (i >> 1) + 3 * (i & 1), i >> 1, i & 1);
        else if (is_cgb) for (k = 0; k < 3; k++) { patron_pal_get(v, k, p); p[0] = 0; cr_pal(1, OBJPAL_ROBOT + k, p); }
        return 0;
    }
    return 1;
}

static void cr_pose_rows(uint8_t v, uint8_t pose) {   // the boss's two rows in a pose (rows 6, 7)
    uint8_t r, k, L = (20 - CR->bn) >> 1;
    for (r = 0; r < 2; r++) {
        cr_blank();
        for (k = 0; k < CR->bn; k++) CR->row[L + k] = CR_T_BOSS + 2 * cr_boss(v, 1, pose, k, 0) + r;
        cr_put_card(6 + r);
    }
    CR->pose = pose;
}

static uint8_t cr_show_unit(uint8_t c, uint8_t i) {   // unit i of card c's rows; 1: there are no more
    uint8_t k, v = 0, L, n, h, kd = cr_kind(c, &v), x;
    portrait_t *pt = CR_PT;
    const char *s;
    if (kd == CK_TITLE) {
        if (i >= 2) return 1;
        cr_blank();
        cr_cell(i ? "CHARACTERS" : "CAST OF", 0, 20);
        cr_put_card(7 + 2 * i);
    } else if (kd <= CK_OWNER) {                   // a person: the portrait (rows 4..), the name under it (row 12), an owner's venue (row 14)
        h = pt->h;
        x = kd == CK_OWNER ? 6 : 4;                // the portrait's first column (7 tiles: the owner's at 6, centred within a tile; the pair's at 4, the sprite beside it)
        L = x + ((7 - pt->w) >> 1);
        n = kd == CK_DREGS ? 1 : 2;                // the text units: the name; an owner's venue, the Spigoteer's title
        if (i < n) {
            cr_blank();
            if (kd == CK_SPIGOTEER) cr_place(i ? "THE SPIGOTEER" : "SAL TAPLEY", 78);     // (owner 2026-10-17: "Sal Tapley AKA The Spigoteer")
            else if (!i) {
                story_name_get(cr_spk(kd, v), CR_BUF);
                cr_place((const char *)CR_BUF, kd == CK_OWNER ? 80 : 78);
            } else cr_place(cr_venue[v], 80);
            cr_put_card(12 + 2 * i);
            return 0;
        }
        i -= n;
        if (i < h) {                               // a portrait row
            for (k = 0; k < 20; k++) CR->row[k] = TILE_HUD_BLANK;
            for (k = 0; k < pt->w; k++) CR->row[L + k] = STORY_PORTRAIT_BASE + pt->map[i * pt->w + k];
            cr_put_card(4 + i);
            return 0;
        }
        i -= h;
        if (!is_cgb || i >= h) return 1;
        for (k = 0; k < 20; k++) CR->row[k] = BGPAL_HUD;   // their attributes (CGB)
        for (k = 0; k < pt->w; k++) CR->row[L + k] = BGPAL_PATRON + pt->attr[i * pt->w + k];
        VBK_REG = VBK_BANK_1; cr_put(4 + i); VBK_REG = VBK_BANK_0;
        cr_amark(4 + i);
    } else if (kd == CK_BOSS) {                    // the body (rows 6, 7) with the topper above, his name (row 10), the venue (row 12)
        n = CR->bn;
        L = (20 - n) >> 1;
        if (i < 2) { cr_blank(); cr_place(i ? cr_venue[v] : cr_bname[v], 80); cr_put_card(10 + 2 * i); }
        else if (i < 4) { if (i == 2) cr_pose_rows(v, 0); }
        else {
            if (!is_cgb || i >= 6) return 1;
            for (k = 0; k < 20; k++) CR->row[k] = BGPAL_HUD;
            for (k = 0; k < n; k++) CR->row[L + k] = BGPAL_BOSS;
            VBK_REG = VBK_BANK_1; cr_put(6 + i - 4); VBK_REG = VBK_BANK_0;
            cr_amark(6 + i - 4);
        }
    } else {                                       // the patrons
        if (i >= 2 + cr_lowered(v)) return 1;
        cr_blank();
        if (!i) cr_cell(cr_venue[v], 0, 20);
        else {
            for (k = 0; k < 3; k++) {              // each label centred under its sprite (to the half tile); the middle one lower if it is crowded
                if ((k == 1 && cr_lowered(v)) != (i == 2)) continue;
                s = cr_pat[v][k];
                n = cr_len(s);
                L = (uint8_t)(cr_pat_cx(v, k) - 4 * n) >> 3;
                for (h = 0; h < n; h++) CR->row[L + h] = cr_glyph(s[h]);
            }
        }
        cr_put_card(i ? 8 + 2 * i : 2);
    }
    return 0;
}

static void cr_card_sprites(uint8_t c) {          // every frame a card is shown
    uint8_t t = (uint8_t)CR->t, k, n, bob, v = 0, kd = cr_kind(c, &v), pose;
    if (kd == CK_SPIGOTEER) cr_fig(0, 60, 108, OBJ_BARTENDER, OBJPAL_BARTENDER, 0);
    else if (kd == CK_DREGS) cr_fig(0, 60, 108, CR_T_D, is_cgb ? OBJPAL_CAST : 0, 0);
    else if (kd == CK_BOSS) {                      // his walk and gulp, the topper bobbing with the stomp
        pose = cr_seq[(t >> 4) & 7];
        if (pose != CR->pose) cr_pose_rows(v, pose);
        cr_oam(0, 5 * 8 + 16, ((20 - CR->bn) >> 1) * 8 + cr_hat_dx[v] + 8, CR_T_HAT + (pose == 1 ? 2 : 0), is_cgb ? OBJPAL_CAST : S_PALETTE);
    } else if (kd == CK_PATRONS) {
        for (k = 0; k < 3; k++) {                 // the three patrons, bobbing in turn
            bob = (((t >> 4) + k) & 3) ? 0 : 2;
            n = cr_pat_cx(v, k);                  // (the pair's left edge + 8: the OAM x of its first column)
            cr_oam(2 * k, 72 - bob, n, CR_T_P + 6 * k, is_cgb ? OBJPAL_ROBOT + k : 0);
            cr_oam(2 * k + 1, 72 - bob, n + 8, CR_T_P + 6 * k + 2, is_cgb ? OBJPAL_ROBOT + k : 0);
        }
    }
}

// The screen goes white (the fade, trans.c trans_cast), the LCD off, the card is built in one go (no waiting for the picture's blanking: the library's tile
// writes are 1 byte a scanline with the LCD on), the LCD on and the card fades in from white. The tune is pumped (the timer, polled) through the build.
static void cr_white(void) {                      // LCD off: every palette white
    uint8_t i;
    if (is_cgb) {
        BCPS_REG = 0x80; OCPS_REG = 0x80;
        for (i = 0; i < 32; i++) { BCPD_REG = 0xFF; BCPD_REG = 0x7F; OCPD_REG = 0xFF; OCPD_REG = 0x7F; }
    } else BGP_REG = OBP0_REG = OBP1_REG = 0;
}

static void cr_off(void) {                        // the LCD off (at a VBlank), the tune's clock started where the fade's last tick (line 18 of this frame) left it
    uint8_t ly;
    if (LY_REG < 18) { while (LY_REG < 18) ; music_tick(); }   // (the fade returned in the top lines of the frame: this frame's tick first)
    while (LY_REG < 144) ;
    ly = LY_REG;
    CR->d0 = DIV_REG; CR->ph = 0; CR->dsum = 0;
    CR->acc = (uint16_t)(ly - 18) * 7 / 4;            // (a line is 1.78 DIV counts)
    LCDC_REG &= ~LCDCF_ON;                            // (DISPLAY_OFF would wait for line 144 itself, a frame away from line 150)
}

static void cr_on(void) {                         // the LCD on so that line 18 of its first frame is the next tick (the fade's first), the build's frames on the clock
    while (CR->acc + 32 < (CR->ph % 3 == 2 ? 275 : 274)) cr_tk();
    CR->t += CR->dsum / 274;
    DISPLAY_ON;
}

static void cr_make(uint8_t c) {                  // LCD off: card c's rows and tiles
    uint8_t i;
    while (!cr_clear_unit()) cr_tk();
    for (i = 0; !cr_load_unit(c, i); i++) cr_tk();
    for (i = 0; !cr_show_unit(c, i); i++) cr_tk();
}

void credits_enter(uint8_t from_story) BANKED {
    uint8_t y, *o = CR_PAL;
    DISPLAY_OFF;
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
    } else {
        o[0] = BGP_REG; o[1] = OBP0_REG; o[2] = o[3] = OBP1_REG;
    }
    cr_white();                                       // (the screen white until the first card fades in)
    music_pump();
    CR->T = music_tune_frames(TUNE_CREDITS);          // the timeline: shares of the tune (1/352: 7 a card, the title included; the roll to 322)
    CR->e_title = CR->card_len = cr_share(7);
    CR->roll = CR->e_title + (CR_CARDS - 1) * CR->card_len;
    CR->f1 = cr_share(322);
    CR->k = (uint8_t)((CR_LAST_T * 32 + (CR->f1 - CR_F0) / 2) / (CR->f1 - CR_F0));
    CR->lagq = 0;
    CR->scroll = 0; CR->card = 255; CR->next = CR_AHEAD + 1; CR->t = 0; CR->phase = 0; CR->from_story = from_story; CR->f = 0; CR->step = 0; CR->tmask = 0; CR->amask = 0;
    SCX_REG = 0; SCY_REG = 0;
    story_phase = STORY_PHASE_CREDITS;
    game_state = GS_STORY;
    music_load_now();                                 // the tune's first notes sound with the picture
    DISPLAY_ON;
}

static uint8_t cr_fade(uint8_t in) {              // (a fade takes frames: they count on the clock the sound-off roll keeps). 1: B or START is down after it
    uint8_t f = trans_cast(CR_PAL, in);
    CR->t += f;
    return (joypad() & (J_B | J_START)) != 0;           // (the press that came during the fade is not lost)
}

static void cr_leave(void) {
    uint8_t s = CR->from_story;
    if (!is_cgb) CR_PAL[2] = CR_PAL[3];               // (OBP1 as it was)
    trans_cast_set(CR_PAL);                           // the card's own colours, whatever the fade was doing
    SCY_REG = 0;
    TRANS_WANT();                                     // (src/trans.c: the next screen comes up behind the drink)
    if (s) story_end();
    else { title_back = TM_BONUS; title_back_sel = 0; title_enter(); }   // BONUS, the cursor on CREDITS (the first item)
}

// story_update, every frame of the roll (GS_STORY). 1: the screen changed.
uint8_t credits_update(uint8_t pressed) BANKED {
    uint8_t c, top;
    uint16_t f, p;
    if (pressed & (J_B | J_START)) { cr_leave(); return 1; }
    CR->t++;
    f = cr_pos();
    CR->f = f;
    if (sound_on ? (cur_tune != TUNE_CREDITS && CR->t > 30) : f >= CR->T) { cr_leave(); return 1; }   // (the tune ends: cur_tune goes to TUNE_NONE)
    if (f < CR->roll) {                                                    // the cast
        c = f < CR->e_title ? 0 : 1 + (uint8_t)((f - CR->e_title) / CR->card_len);
        if (c >= CR_CARDS) c = CR_CARDS - 1;
        if (CR->card != c) {
            if (CR->card < CR_CARDS && cr_fade(0)) { cr_leave(); return 1; }   // the old card fades out (to white)
            CR->card = c;
            cr_off();
            cr_white();
            hide_all_sprites();
            if (!is_cgb) CR_PAL[2] = cr_kind(c, &top) == CK_BOSS ? DMG_HAT_OBP1 : CR_PAL[3];
            cr_make(c);
            cr_card_sprites(c);
            cr_on();
            if (cr_fade(1)) { cr_leave(); return 1; }                          // the new card fades in
            CR->phase = 5;
            if (sound_on) { CR->lagq += CR_LAG; if (CR->lagq >= 100) { CR->lagq -= 100; music_tick(); } }   // (the card change costs the tune this much: a fraction of a frame each; a tick makes up a whole one now and then)
        } else cr_card_sprites(c);
        return 0;
    }
    if (CR->card < 200 || CR->card == 255) {                               // the roll's start: behind the fade its rows from the top, the robots
        if (CR->card < CR_CARDS && cr_fade(0)) { cr_leave(); return 1; }
        CR->card = 201;
        cr_off();
        cr_white();
        hide_all_sprites();
        if (!is_cgb) CR_PAL[2] = CR_PAL[3];
        for (c = 0; c < 32; c++) { cr_rows(c, 1); cr_tk(); }
        for (c = 0; c < 6; c++) { load_patron_pose0(5, CR_T_P + 6 * (c >> 1) + 3 * (c & 1), c >> 1, c & 1); cr_tk(); }
        if (is_cgb) for (c = 0; c < 3; c++) { patron_pal_get(5, c, (uint16_t *)CR->row); ((uint16_t *)CR->row)[0] = 0; cr_pal(1, OBJPAL_ROBOT + c, (uint16_t *)CR->row); }
        cr_on();
        if (cr_fade(1)) { cr_leave(); return 1; }
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
            cr_build(CR->next);
            vq_add(0, CR->row, 0, CR->next & 31, 20);
            CR->next++;
        }
        SCY_REG = (uint8_t)CR->scroll;
    }
    cr_sprites();
    return 0;
}
