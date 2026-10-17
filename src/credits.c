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
#include "boss_cast_art.h"

extern uint8_t overlay_on, joy, story_phase;

#define CR_FIRST      18      // the roll's first row, in world rows (just under the screen)
#define CR_AHEAD      20      // rows are kept written up to T + CR_AHEAD (T: the top row of the screen)
#define CR_BAND       14      // the roll's row where the sprites' band starts (4 rows)
#define CR_T_P       100      // the patrons' OBJ tiles: 3 variants x 6 (OBJ ids 100-117, in dgag.c's patron range)
#define CR_T_D        56      // Dregs's 8 OBJ tiles
#define CR_T_HAT      64      // the topper (8x16)
#define CR_T_BOSS    160      // BG ids: the boss's columns (top, bottom), 5 at most
#define CR_BT_X      120      // the Spigoteer's left edge in the roll; the robots stand at 24, 56, 88
#define OBJPAL_ROBOT   5
#define OBJPAL_CAST    3      // Dregs's, the topper's
#define BGPAL_BOSS     5
#define COL_BAND  0x2043      // RGB15(3, 2, 8): the band (colour 3 of the HUD palette), the bosses' colour 0
#define DMG_HAT_OBP1  0x93    // the topper on the band: its three shades one step lighter (idx 1 white, 2 light, 3 dark; the DMG boss body is remapped the same way)

#define CR_UNITS       4      // work units a frame at most (cards): another starts only while the frame is young
#define CR_LY_STOP    56      // ... on line 56 or earlier (a unit takes up to ~30 lines)
#define CR_CARDS      22      // title, hero, 10 venue (owner and boss) cards, 10 patron cards
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
    uint16_t e_title, e_hero, card_len, roll, f1;   // the timeline's boundaries (frames): the hero card starts, the first venue card, a card's length, the roll starts, its scroll ends
    uint8_t k;                // the scroll's speed: px = frames * k / 32
};
#define CR ((struct cr_state *)story_scratch)
#define CR_PAL ((uint8_t *)story_scratch + 64)                          // the card's colours (CGB: 128 bytes; DMG: BGP, OBP0, OBP1, the first OBP1)
#define CR_PT  ((portrait_t *)(story_scratch + 192))                    // the owner's portrait (while a venue card is built)
#define CR_BUF ((uint8_t *)story_scratch + 192 + sizeof(portrait_t))    // 96 bytes: a few tiles on their way, the owner's name
typedef char cr_fits[(sizeof(struct cr_state) <= 64 && 192 + sizeof(portrait_t) + 96 <= STORY_SCRATCH) ? 1 : -1];

#define CR_F0   (CR->roll + 40)

// ---- the cast: names from the game's own data (boss names and venues: src/rush.c; the owners: the story's speakers; the player and Dregs) -----
static const char *const cr_venue[10] = {
    "THE SALOON", "THE STADIUM", "THE LUMBER LODGE", "THE BISTRO", "THE IGLOO", "THE ROBOT FACTORY", "THE CHROME COW", "THE TEAHOUSE",
    "THE JUNGLE ZOO", "THE SPACE LOUNGE",
};
static const char *const cr_bn[10][2] = {         // the boss's name, broken at a word boundary where it must be (in venue order)
    { "BIG TEX", "" }, { "THE MASCOT", "" }, { "SASQUATCH", "" }, { "THE CRITIC", "" }, { "THE YETI", "" }, { "PROTOTYPE", "" }, { "DUKE", "" },
    { "SUMO CHAMP", "" }, { "LEO THE", "LION" }, { "MOTHERSHIP", "" },
};
static const uint8_t cr_owner[10] = { 2, 3, 4, 5, 6, 7, 11, 8, 10, 9 };   // the venue owner's speaker id (tools/gen_story.py SPEAKERS): Sadie, Coach, June, Colby, Aurora, Manager-Bot, Granny, Hana, Kiki, Zizz
static const uint8_t cr_hat_dx[10] = { 16, 8, 12, 9, 9, 8, 16, 16, 6, 12 };   // boss.c rows[]: the topper's x from his left edge
// The patrons have no names in the game: short labels for what they look like, three a venue (art order A, B, C). A label of one word, or of
// two that fit, is one line (line 1); a longer one breaks between its words (no word is split). A line is at most 6 tiles.
static const char *const cr_pat[10][3][2] = {
    { { "COWBOY", "" }, { "COW", "GIRL" }, { "RANCH", "HAND" } },
    { { "CAP", "FAN" }, { "BAND", "FAN" }, { "REF", "" } },
    { { "BIG", "JACK" }, { "RED", "HAIR" }, { "GREEN", "CAP" } },
    { { "HEAD", "CHEF" }, { "SOUS", "CHEF" }, { "LINE", "COOK" } },
    { { "PARKA", "MAN" }, { "PARKA", "GIRL" }, { "BIG", "PARKA" } },
    { { "BOX", "BOT" }, { "LADY", "BOT" }, { "DOME", "BOT" } },
    { { "MOHAWK", "" }, { "SCARF", "" }, { "QUIFF", "" } },
    { { "NINJA", "" }, { "NINJA", "GIRL" }, { "RED", "HELM" } },
    { { "MONKEY", "" }, { "PANDA", "" }, { "HIPPO", "" } },
    { { "EYE", "STALK" }, { "GREY", "" }, { "SQUID", "" } },
};

static uint8_t cr_len(const char *s) { uint8_t n = 0; while (s[n]) n++; return n; }

// patron k's centre x (px) on a venue card: the columns 48 px apart, 32 / 80 / 128; a label whose longest line is an odd number of tiles
// centres on a tile boundary + 4 px, so its sprite moves 4 px with it (the sprite is centred on the label)
static uint8_t cr_pat_cx(uint8_t v, uint8_t k) {
    uint8_t n = cr_len(cr_pat[v][k][0]), m = cr_len(cr_pat[v][k][1]);
    if (m > n) n = m;
    return 32 + 48 * k + ((n & 1) ? 4 : 0);
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

static void cr_put(uint8_t y) { set_bkg_tiles(0, y, 20, 1, CR->row); }

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

// ---- sprites --------------------------------------------------------------------------------------------------------------------------
static void cr_oam(uint8_t n, int16_t y, uint8_t x, uint8_t tile, uint8_t prop) {   // y: OAM y; off the screen: hidden
    OAM_item_t *o = shadow_OAM + n;
    if (y < 1 || y > 159) { o->y = 0; return; }
    o->y = (uint8_t)y; o->x = x; o->tile = tile; o->prop = prop;
}

static void cr_fig(uint8_t n, int16_t y, uint8_t x, uint8_t base, uint8_t prop, uint8_t flip) {   // the bartender's four entries (x: left edge)
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
// card c: 0 title, 1 hero, 2-11 the venues' owner and boss (venue c-2), 12-21 the venues' patrons (venue c-12).
// Writing VRAM with the LCD on is slow (the library waits for the picture's blanking for every byte): a card is built in UNITS, CR_UNITS a
// frame (a row, a few tiles), so that no frame runs over its VBlank and the tune never loses a tick. Stage 1 blanks the rows the last card
// used, stage 2 loads, stage 3 writes the rows; then the card fades in.
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

static void cr_remap(uint8_t *b) {                // DMG: a column's 2 tiles with the shades one step on (0 -> 3, the band; 1 -> 0; 2 -> 1; 3 -> 2): v - 1, a plane at a time
    uint8_t i, lo;
    for (i = 0; i < 32; i += 2) {
        lo = ~b[i];                                   // (the low bit always flips; the high bit with it where the low bit was 0)
        b[i + 1] ^= lo;
        b[i] = lo;
    }
}

static uint8_t cr_load_unit(uint8_t c, uint8_t i) {   // unit i of card c's loads; 1: there are no more
    uint8_t v, k, n, nch, *buf = CR_BUF;
    uint16_t p[4];
    portrait_t *pt = CR_PT;
    if (c == 1) {
        if (i) return 1;
        dregs_cast_load(CR_T_D, p);
        if (is_cgb) cr_pal(1, OBJPAL_CAST, p);
    } else if (c >= 2 && c < 12) {
        v = c - 2;
        if (i == 0) {                              // the owner's portrait: its palettes (BG 2-4); the boss's (BG 5) with the band as colour 0
            portrait_get(cr_owner[v], pt);
            if (is_cgb) {
                for (k = 0; k < pt->npal; k++) cr_pal(0, BGPAL_PATRON + k, pt->pal + 4 * k);
                p[0] = COL_BAND; p[1] = boss_cast_pal[v][1]; p[2] = boss_cast_pal[v][2]; p[3] = boss_cast_pal[v][3];
                cr_pal(0, BGPAL_BOSS, p);
                p[0] = 0;
                cr_pal(1, OBJPAL_CAST, p);
            }
            return 0;
        }
        i--;
        nch = (pt->ntiles + 5) / 6;
        if (i < nch) {                             // its tiles, six at a time
            n = pt->ntiles - 6 * i;
            if (n > 6) n = 6;
            portrait_tile_copy(cr_owner[v], 6 * i, n, buf);
            set_bkg_data(STORY_PORTRAIT_BASE + 6 * i, n, buf);
            return 0;
        }
        i -= nch;
        n = boss_cast_cols[v];                     // the boss's body: CGB at once; DMG a column a unit, remapped
        if (is_cgb) {
            if (i == 0) set_bkg_data(CR_T_BOSS, n << 1, boss_cast_tiles[v]);
            else if (i == 1) set_sprite_data(CR_T_HAT, 2, boss_cast_hat[v]);
            else return 1;
        } else if (i < n) {
            for (k = 0; k < 32; k++) buf[k] = boss_cast_tiles[v][32 * i + k];
            cr_remap(buf);
            set_bkg_data(CR_T_BOSS + 2 * i, 2, buf);
        } else if (i == n) set_sprite_data(CR_T_HAT, 2, boss_cast_hat[v]);
        else return 1;
    } else if (c >= 12) {
        v = c - 12;
        if (i >= 4) return 1;
        if (i < 3) load_patron_pose0(v, CR_T_P + 6 * i, i);
        else if (is_cgb) for (k = 0; k < 3; k++) { patron_pal_get(v, k, p); p[0] = 0; cr_pal(1, OBJPAL_ROBOT + k, p); }
    } else return 1;
    return 0;
}

static void cr_names(const uint8_t *buf, char *l1, char *l2) {   // an owner's name (as the story has it) into two lines: broken after a hyphen if it is long
    uint8_t i = 0, n, h = 255;
    while (buf[i] && i < 12) { l1[i] = buf[i]; if (buf[i] == '-') h = i; i++; }
    n = i;
    l1[n] = 0; l2[0] = 0;
    if (n > 9 && h != 255) {
        for (i = h + 1; i < n; i++) l2[i - h - 1] = l1[i];
        l2[n - h - 1] = 0;
        l1[h + 1] = 0;
    }
}

static uint8_t cr_show_unit(uint8_t c, uint8_t i) {   // unit i of card c's rows; 1: there are no more
    uint8_t k, v, L, n, m, h;
    portrait_t *pt = CR_PT;
    char *l1 = (char *)CR_BUF + 16, *l2 = (char *)CR_BUF + 32;
    if (c < 2) {
        if (i >= 2) return 1;
        cr_blank();
        if (c) i++;                                // (the hero card's rows are 11 and 13)
        if (c == 0) { cr_cell(i ? "CHARACTERS" : "CAST OF", 0, 20); cr_put_card(7 + 2 * i); }
        else {                                     // (the two figures 72 px apart, their names centred under them: the pair's ink is centred on the screen)
            cr_place(i == 1 ? "SPIGOTEER" : "BARTENDER", 52);
            cr_place(i == 1 ? "DREGS" : "RIVAL", 124);
            cr_put_card(9 + 2 * i);
        }
    } else if (c < 12) {                           // the venue's owner (left) and boss (right), their names under them
        v = c - 2;
        h = pt->h;
        n = boss_cast_cols[v];
        L = (uint8_t)(44 - 4 * pt->w) >> 3;        // the portrait's first column: 7 tiles at column 2
        if (i == 0) { cr_blank(); cr_cell(cr_venue[v], 0, 20); cr_put_card(1); }
        else if (i < 3) {                          // the names: rows 11 and 13 (a blank row between the lines)
            story_name_get(cr_owner[v], (uint8_t *)CR_BUF);
            cr_names(CR_BUF, l1, l2);
            cr_blank();
            m = cr_len(i == 1 ? l1 : l2);
            cr_place(i == 1 ? l1 : l2, m >= 8 ? 40 : 44);
            cr_place(cr_bn[v][i - 1], 116);
            cr_put_card(9 + 2 * i);
        } else {
            i -= 3;
            if (i < h) {                           // a portrait row (rows 3..), the boss's two (rows 6, 7) beside it
                for (k = 0; k < 20; k++) CR->row[k] = TILE_HUD_BLANK;
                for (k = 0; k < pt->w; k++) CR->row[L + k] = STORY_PORTRAIT_BASE + pt->map[i * pt->w + k];
                if (i == 3 || i == 4) for (k = 0; k < n; k++) CR->row[12 + k] = CR_T_BOSS + 2 * k + i - 3;
                cr_put_card(3 + i);
                return 0;
            }
            i -= h;
            if (!is_cgb || i >= h) return 1;
            for (k = 0; k < 20; k++) CR->row[k] = BGPAL_HUD;   // their attributes (CGB)
            for (k = 0; k < pt->w; k++) CR->row[L + k] = BGPAL_PATRON + pt->attr[i * pt->w + k];
            if (i == 3 || i == 4) for (k = 0; k < n; k++) CR->row[12 + k] = BGPAL_BOSS;
            VBK_REG = VBK_BANK_1; cr_put(3 + i); VBK_REG = VBK_BANK_0;
            cr_amark(3 + i);
        }
    } else {
        if (i >= 3) return 1;
        cr_blank();
        if (!i) { cr_cell(cr_venue[c - 12], 0, 20); cr_put_card(2); }
        else {
            for (k = 0; k < 3; k++) {                  // each line centred under its sprite (to the half tile)
                const char *t = cr_pat[c - 12][k][i - 1];
                n = cr_len(t);
                L = (uint8_t)(cr_pat_cx(c - 12, k) - 4 * n) >> 3;
                for (m = 0; m < n; m++) CR->row[L + m] = cr_glyph(t[m]);
            }
            cr_put_card(8 + 2 * i);                   // (a blank row between the two lines: rows 10 and 12)
        }
    }
    return 0;
}

static void cr_card_sprites(uint8_t c) {          // every frame a card is shown
    uint8_t t = (uint8_t)CR->t, k, n, bob;
    if (c == 1) {                                 // the two bartenders, facing each other
        cr_fig(0, 72, 44, OBJ_BARTENDER, OBJPAL_BARTENDER, 1);
        cr_fig(4, 72, 116, CR_T_D, is_cgb ? OBJPAL_CAST : 0, 0);
    } else if (c >= 2 && c < 12) {                // the topper over the boss's body (his body's left edge: 96 px)
        cr_oam(0, 5 * 8 + 16, 96 + cr_hat_dx[c - 2] + 8, CR_T_HAT, is_cgb ? OBJPAL_CAST : S_PALETTE);
    } else if (c >= 12) {
        for (k = 0; k < 3; k++) {                 // the three patrons, bobbing in turn
            bob = (((t >> 4) + k) & 3) ? 0 : 2;
            n = cr_pat_cx(c - 12, k);                 // (the pair's left edge + 8: the OAM x of its first column)
            cr_oam(2 * k, 72 - bob, n, CR_T_P + 6 * k, is_cgb ? OBJPAL_ROBOT + k : 0);
            cr_oam(2 * k + 1, 72 - bob, n + 8, CR_T_P + 6 * k + 2, is_cgb ? OBJPAL_ROBOT + k : 0);
        }
    }
}

// a card's work, CR_UNITS units a frame: phase 1 clearing, 2 loading, 3 rows, 4 built (CR->step: the unit)
static void cr_card_work(uint8_t c) {
    uint8_t u;
    for (u = 0; u < CR_UNITS; u++) {
        if (u && LY_REG >= CR_LY_STOP) break;          // (a frame's logic must be over by line 124 or the tune's tick is postponed: music.h MUSIC_LATEST_LY)
        if (CR->phase == 1) { if (cr_clear_unit()) { CR->phase = 2; CR->step = 0; } }
        else if (CR->phase == 2) { if (cr_load_unit(c, CR->step)) { CR->phase = 3; CR->step = 0; } else CR->step++; }
        else if (CR->phase == 3) { if (cr_show_unit(c, CR->step)) { CR->phase = 4; CR->step = 0; return; } else CR->step++; }
        else return;
    }
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
        BCPS_REG = 0x80; OCPS_REG = 0x80;             // and the screen in the band's colour until the first card fades in
        for (y = 0; y < 32; y++) { BCPD_REG = COL_BAND & 255; BCPD_REG = COL_BAND >> 8; OCPD_REG = COL_BAND & 255; OCPD_REG = COL_BAND >> 8; }
    } else {
        o[0] = BGP_REG; o[1] = OBP0_REG; o[2] = o[3] = OBP1_REG;
        BGP_REG = OBP0_REG = OBP1_REG = 0xFF;
    }
    music_pump();
    CR->T = music_tune_frames(TUNE_CREDITS);          // the timeline: shares of the tune (1/352: 8 for the title, 10 for the hero, 10 a card, the roll to 322)
    CR->e_title = cr_share(8);
    CR->e_hero = cr_share(18);
    CR->card_len = cr_share(10);
    CR->roll = CR->e_hero + 20 * CR->card_len;
    CR->f1 = cr_share(322);
    CR->k = (uint8_t)((CR_LAST_T * 32 + (CR->f1 - CR_F0) / 2) / (CR->f1 - CR_F0));
    CR->scroll = 0; CR->card = 255; CR->next = CR_AHEAD + 1; CR->t = 0; CR->phase = 0; CR->from_story = from_story; CR->f = 0; CR->step = 0; CR->tmask = 0; CR->amask = 0;
    SCX_REG = 0; SCY_REG = 0;
    story_phase = STORY_PHASE_CREDITS;
    game_state = GS_STORY;
    music_load_now();                                 // the tune's first notes sound with the picture
    DISPLAY_ON;
}

static uint8_t cr_fade(uint8_t in) {              // (a fade takes frames: they count on the clock the sound-off roll keeps). 1: B or START is down after it
    uint8_t f = trans_cast(CR_PAL, in);
    CR->t += f + 1;                                   // (+1: the partial frame the call began in)
    return (joypad() & (J_B | J_START)) != 0;           // (the press that came during the fade is not lost)
}

static void cr_leave(void) {
    uint8_t s = CR->from_story;
    if (!is_cgb) CR_PAL[2] = CR_PAL[3];               // (OBP1 as it was)
    trans_cast_set(CR_PAL);                           // the card's own colours, whatever the fade was doing
    SCY_REG = 0;
    TRANS_WANT();                                     // (src/trans.c: the next screen comes up behind the drink)
    if (s) story_end();
    else { title_back = TM_BONUS; title_back_sel = 3; title_enter(); }   // BONUS, the cursor on CREDITS
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
        c = f < CR->e_title ? 0 : f < CR->e_hero ? 1 : 2 + (uint8_t)((f - CR->e_hero) / CR->card_len);
        if (c >= CR_CARDS - 0) c = CR_CARDS - 1;
        if (CR->card != c) {
            if (CR->card < CR_CARDS && CR->phase == 5 && cr_fade(0)) { cr_leave(); return 1; }   // the old card fades out
            CR->card = c; CR->phase = 1; CR->step = 0; hide_all_sprites();
            if (!is_cgb) CR_PAL[2] = (c >= 2 && c < 12) ? DMG_HAT_OBP1 : CR_PAL[3];
        }
        if (CR->phase < 4) cr_card_work(c);
        if (CR->phase == 4) {                                              // built: its sprites, then it fades in
            cr_card_sprites(c);
            if (cr_fade(1)) { cr_leave(); return 1; }
            CR->phase = 5;
        } else if (CR->phase == 5) cr_card_sprites(c);
        return 0;
    }
    if (CR->card < 200 || CR->card == 255) {                               // the roll's start: behind the fade its rows from the top, the robots
        if (CR->card < CR_CARDS && CR->phase == 5 && cr_fade(0)) { cr_leave(); return 1; }
        CR->card = 200; CR->step = 0; CR->tmask = 0; hide_all_sprites();
        if (!is_cgb) CR_PAL[2] = CR_PAL[3];
    }
    if (CR->card == 200) {
        for (c = 0; c < CR_UNITS && CR->card == 200; c++, CR->step++) {
            if (c && LY_REG >= CR_LY_STOP) break;
            if (CR->step < 32) cr_rows(CR->step, 1);
            else if (CR->step < 35) load_patron_pose0(5, CR_T_P + 6 * (CR->step - 32), CR->step - 32);
            else {
                if (is_cgb) for (top = 0; top < 3; top++) { patron_pal_get(5, top, (uint16_t *)CR->row); ((uint16_t *)CR->row)[0] = 0; cr_pal(1, OBJPAL_ROBOT + top, (uint16_t *)CR->row); }
                CR->card = 201;
                if (cr_fade(1)) { cr_leave(); return 1; }
            }
        }
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
