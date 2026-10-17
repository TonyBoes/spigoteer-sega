// The credits roll (owner 2026-10-17): a cast of characters, then the game's credits scrolling up the screen in the story's lettering, and
// "THANKS FOR PLAYING!" alone at the end. It IS the story's credits: the CREDITS scene shows its picture and the four closing narrator
// pages, and its end (story.c scene_done) is this roll (credits_enter(1); its end is story_end: the STORY score entry) and from the
// title's BONUS > CREDITS (credits_enter(0); its end or B: back to BONUS, the cursor on CREDITS). The wording is CREDITS.md's, the
// "Special thanks to:" list in it.
//
// The music is the credits tune (TUNE_CREDITS: the Entertainer's intro, the strains the title tune lacks and its opening bar again, 88 s =
// 352 rows of 15 frames, played once), started by credits_enter while the screen is built (BONUS' own tune stops there). The whole roll is
// tied to the tune's POSITION (hUGE order, row and tick: cr_pos), not to a frame count, so it keeps step with it on DMG, CGB and whatever
// the frames do. With the sound off the position is the frames on the screen (the same 15 a row), so it runs at the same pace.
//
//   frames 0-119         "CAST OF CHARACTERS"
//   120-329              card: the Spigoteer (the player) and Dregs, the Pour-Off's rival
//   330-1899             10 cards of 157 frames: the ten bosses, one a card, in venue order (their body, WALK pose, and topper: build/boss_cast_art.h)
//   1900-3469            10 cards of 157 frames: a venue each (its name, its three patrons, side by side with a label under each)
//   3470-4829            the credits roll (about 0.53 px a frame, text rows streamed in as before)
//   4830-5279            "THANKS FOR PLAYING!" alone, the tune's last bars and its held C; the roll ends when the tune has
//
// A card is built behind a blank screen with the LCD ON (nothing on the screen, no flash): frame 0 of a card clears it (sprites hidden, text
// rows blank), frame 2 loads its tiles and palettes (the new art goes over ids nothing visible uses), frame 4 writes its rows and shows the
// sprites. The tilemap is the 32-row ring the roll scrolls (SCY 0 during the cast; the cards use rows 0-17). BG tile ids CR_T_BOSS.. hold
// the bosses' body, OBJ ids 56.. Dregs, 64.. the toppers, 100-117 the patrons' shift-0 poses (the roll's robots are the same).
//
// The roll's text is one string per line, centred, two tilemap rows a line (the glyphs fill their rows); "" is a blank line; every line is
// at most 18 tiles (a clear column at each edge). CR_BAND is the line where the sprites' band starts (2 lines: the Spigoteer's art is 24 px
// tall; the three robots stand under the "robot friends" line, who bob in turn, and he, facing them, raises a hand now and then).
// B / START skip (to the end: story_end, or the BONUS menu). With the sound on the roll ends when the music has; with the sound off at 5280.
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
extern unsigned char hUGE_tick, hUGE_row, hUGE_current_order;
void spr_data_far(uint8_t first, uint8_t n, const uint8_t *d, uint8_t bank);   // src/main.c (ROM0)

#define CR_FIRST      18      // the roll's first row, in world rows (just under the screen)
#define CR_AHEAD      20      // rows are kept written up to T + CR_AHEAD (T: the top row of the screen)
#define CR_BAND       10      // the roll's line where the sprites' band starts (2 lines)
#define CR_SPR        (2 * CR_BAND)   // ... its first row
#define CR_T_P       100      // the patrons' OBJ tiles: 3 variants x 6 (OBJ ids 100-117, in dgag.c's patron range)
#define CR_T_D        56      // Dregs's 8 OBJ tiles
#define CR_T_HAT      64      // the two toppers (8x16 each)
#define CR_T_BOSS    120      // BG ids: boss A's 5 columns (top, bottom), 130 a blank (colour 0) tile, 131.. boss B's
#define CR_T_BLANK   130
#define CR_BT_X      120      // the Spigoteer's left edge in the roll; the robots stand at 24, 56, 88
#define OBJPAL_ROBOT   5
#define OBJPAL_CAST    3      // Dregs's, boss A's topper; boss B's is 4
#define CR_PANEL      RGB15(31, 29, 22)   // the bosses' panel (colour 0): the HUD's light colour, so the dark outlines read

#define CR_UNITS       2      // work units a frame (cards, the roll's start)
#define CR_ROWF       15      // frames a row of the tune
#define CR_TOTAL    5280      // the tune's frames
#define CR_CARD      157      // a card's frames (10.5 rows)
#define CR_TITLE     120
#define CR_HERO_END  330      // the first boss card
#define CR_CARDS      22      // title, hero, 10 boss cards, 10 patron cards
#define CR_ROLL     3470      // (330 + 20 cards of 157) the roll starts (init: 8 frames of rows, then the scroll)
#define CR_F0       (CR_ROLL + 10)
#define CR_F1       4830      // the scroll ends: the last line is up
#define CR_SPAN     (CR_F1 - CR_F0)
#define RGB15(r, g, b) ((uint16_t)((r) | ((g) << 5) | ((b) << 10)))

// state in story_scratch
struct cr_state {
    uint8_t row[20];          // the row being built (queued rows are read at VBlank)
    uint16_t scroll;          // px scrolled
    uint8_t card;             // the card shown (255: none yet; 200: the roll's rows being written, 201: the roll)
    uint8_t next;             // the next world row to write
    uint16_t t;               // frames on the screen
    uint8_t phase;            // 0 blank / 1 cleared / 2 loaded / 3 shown (a card); the roll's init rows done
    uint8_t from_story;       // 1: story_end follows
    uint16_t f;               // the position in the tune's frames (cr_pos)
    uint8_t step;             // the unit of the card's stage
    uint32_t tmask, amask;    // rows (bit y) the last card wrote: their tiles, and their CGB attributes (a boss panel)
    uint8_t blank;            // 1: the screen is cut to the band colour while a card is built
};
#define CR ((struct cr_state *)story_scratch)

// ---- the cast: names from the game's own data (boss names and venues: src/rush.c; the player and Dregs: the story) -------------------------
static const char *const cr_boss[10][2] = {      // name, venue (venue order)
    { "BIG TEX", "THE SALOON" }, { "THE MASCOT", "THE STADIUM" }, { "SASQUATCH", "THE LUMBER LODGE" }, { "THE CRITIC", "THE BISTRO" },
    { "THE YETI", "THE IGLOO" }, { "PROTOTYPE", "THE ROBOT FACTORY" }, { "DUKE", "THE CHROME COW" }, { "SUMO CHAMP", "THE TEAHOUSE" },
    { "LEO THE LION", "THE JUNGLE ZOO" }, { "MOTHERSHIP", "THE SPACE LOUNGE" },
};
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

// ---- the roll. 20 columns a row. Owner's lines (2026-10-17): "Game Design, Media, and Story by Tony and his tireless team of robot
// friends"; "no credits for public domain tunes. Public Domain."; "Special thanks to:" the platforms, frameworks and projects used.
static const char *const cr_text[] = {      // a line every other tilemap row
    "SPIGOTEER",            // 0
    "", "",
    "GAME DESIGN,",
    "MEDIA, AND",
    "STORY BY",
    "TONY",
    "AND HIS TIRELESS",
    "TEAM OF",
    "ROBOT FRIENDS",
    "", "",                 // 10-11: the sprites' band (CR_BAND: 4 rows, the first 3 used)
    "", "",                 // two blank lines between sections
    "MUSIC",                
    "PUBLIC DOMAIN",
    "MELODIES,",
    "ARRANGED",
    "FOR THIS GAME",
    "", "",
    "SPECIAL",              
    "THANKS TO:",
    "",
    "GBDK-2020",
    "SDCC",
    "HUGEDRIVER",           
    "RGBDS",
    "SAMEBOY",
    "PYBOY",
    "PAN DOCS",
    "THE GBDEV",            
    "COMMUNITY",
    "", "", "", "", "", "", "",   // the screen empties before the last words
    "THANKS FOR",           
    "PLAYING!",
};
#define CR_N (sizeof(cr_text) / sizeof(cr_text[0]))
#define CR_LAST_T ((CR_FIRST + 2 * (CR_N - 2)) * 8 + 8 - 72)   // the scroll at which the last two lines are in the middle of the screen
#define CR_K ((uint16_t)((CR_LAST_T * 32UL + CR_SPAN / 2) / CR_SPAN))   // scroll = (frames since CR_F0) * CR_K / 32

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
    uint8_t i, n = 0, x;
    while (s[n]) n++;
    x = c0 + ((uint8_t)(w - n) >> 1);
    for (i = 0; i < n; i++) CR->row[x + i] = cr_glyph(s[i]);
}

static void cr_put(uint8_t y) { set_bkg_tiles(0, y, 20, 1, CR->row); }

// the row for world row w (blank before the roll and after it), centred, into CR->row
static void cr_build(uint8_t w) {
    cr_blank();
    if (w >= CR_FIRST && !((w - CR_FIRST) & 1) && (w - CR_FIRST) >> 1 < CR_N) cr_cell(cr_text[(w - CR_FIRST) >> 1], 0, 20);
}

static void cr_rows(uint8_t y, uint8_t n) {       // n rows from row y of the roll's rows (blank where it is not), ring slot y & 31
    for (; n; n--, y++) {
        cr_build(y);
        cr_put(y & 31);
    }
}

// ---- the tune's position, in frames ---------------------------------------------------------------------------------------------------
static uint16_t cr_pos(void) {
    if (sound_on && cur_tune == TUNE_CREDITS)         // the driver counts orders by 2; 64 rows an order
        return (uint16_t)(((uint16_t)(hUGE_current_order >> 1) << 6) + hUGE_row) * CR_ROWF + hUGE_tick;
    return CR->t;
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
    int16_t y = (int16_t)(CR_FIRST + CR_SPR) * 8 - CR->scroll + 16;   // the band's top, OAM y
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
// card c: 0 title, 1 hero, 2-6 bosses 2(c-2), 2(c-2)+1, 7-16 venue c-7.
// Writing VRAM with the LCD on is slow (the library waits for the picture's blanking for every byte): a card is built in UNITS, CR_UNITS a
// frame (a row, a few tiles, a palette), so that no frame runs over its VBlank and the tune never loses a tick. Stage 1 blanks the rows the
// last card used, stage 2 loads, stage 3 writes the rows; then the sprites show.
static uint16_t cr_card_start(uint8_t c) {
    return c == 0 ? 0 : c == 1 ? CR_TITLE : CR_HERO_END + (uint16_t)(c - 2) * CR_CARD;
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
    if (CR->amask) {                               // the last boss card's panel palettes: the HUD's again
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

static const uint8_t cr_zero[16];                 // a tile of colour 0: the panel's margin and the topper's row

static uint8_t cr_load_unit(uint8_t c, uint8_t i) {   // unit i of card c's loads; 1: there are no more
    uint8_t b, j;
    uint16_t p[4];
    if (c == 1) {
        if (i) return 1;
        dregs_cast_load(CR_T_D, OBJPAL_CAST);
    } else if (c >= 2 && c < 12) {
        if (i >= 3) return 1;
        b = c - 2;
        switch (i) {
        case 0: set_bkg_data(CR_T_BOSS, boss_cast_cols[b] << 1, boss_cast_tiles[b]); break;
        case 1:
            set_sprite_data(CR_T_HAT, 2, boss_cast_hat[b]);
            set_bkg_data(CR_T_BLANK, 1, cr_zero);
            break;
        default:
            if (is_cgb) {
                p[0] = CR_PANEL; p[1] = boss_cast_pal[b][1]; p[2] = boss_cast_pal[b][2]; p[3] = boss_cast_pal[b][3];
                set_bkg_palette(BGPAL_STAGE, 1, p);
                p[0] = 0;
                set_sprite_palette(OBJPAL_CAST, 1, p);
            }
        }
    } else if (c >= 12) {
        if (i >= 4) return 1;
        if (i < 3) load_patron_pose0(c - 12, CR_T_P + 6 * i, i);
        else if (is_cgb) for (j = 0; j < 3; j++) { patron_pal_get(c - 12, j, p); p[0] = 0; set_sprite_palette(OBJPAL_ROBOT + j, 1, p); }
    } else return 1;
    return 0;
}

static uint8_t cr_show_unit(uint8_t c, uint8_t i) {   // unit i of card c's rows; 1: there are no more
    uint8_t k, b, y, L, n, m;
    if (c < 2) {
        if (i >= 2) return 1;
        cr_blank();
        if (c == 0) { cr_cell(i ? "CHARACTERS" : "CAST OF", 0, 20); cr_put_card(7 + 2 * i); }
        else if (i == 0) { cr_cell("SPIGOTEER", 1, 9); cr_cell("DREGS", 10, 9); cr_put_card(11); }
        else { cr_cell("BARTENDER", 1, 9); cr_cell("RIVAL", 10, 9); cr_put_card(13); }
    } else if (c < 12) {
        if (i >= 12) return 1;                     // one boss a card: 12 units
        k = i;
        b = c - 2;
        n = boss_cast_cols[b];
        L = 10 - (n >> 1);                         // the body's first column
        y = 4;                                     // the panel's top row: a margin row, then the topper's row, the body's two, a margin row
        if (k < 2) { cr_blank(); cr_cell(cr_boss[b][k], 0, 20); cr_put_card(10 + 2 * k); }   // name, a blank row, the venue
        else if (k < 7) {                          // the panel's five rows
            cr_blank();
            if (k == 4 || k == 5) for (m = 0; m < n; m++) CR->row[L + m] = CR_T_BOSS + 2 * m + (k - 4);
            for (m = L - 1; m <= L + n; m++) if (CR->row[m] == TILE_HUD_BLANK) CR->row[m] = CR_T_BLANK;
            cr_put_card(y + k - 2);
        } else if (is_cgb) {                       // their attributes: the panel's palette
            for (m = 0; m < 20; m++) CR->row[m] = BGPAL_HUD;
            for (m = L - 1; m <= L + n; m++) CR->row[m] = BGPAL_STAGE;
            VBK_REG = VBK_BANK_1;
            cr_put(y + k - 7);
            VBK_REG = VBK_BANK_0;
            cr_amark(y + k - 7);
        }
    } else {
        if (i >= 3) return 1;
        cr_blank();
        if (!i) { cr_cell(cr_boss[c - 12][1], 0, 20); cr_put_card(2); }
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
    uint8_t t = (uint8_t)CR->t, k, b, n, bob;
    if (c == 1) {                                 // the two bartenders, facing each other
        cr_fig(0, 72, 36, OBJ_BARTENDER, OBJPAL_BARTENDER, 1);
        cr_fig(4, 72, 108, CR_T_D, is_cgb ? OBJPAL_CAST : 0, 0);
    } else if (c >= 2 && c < 12) {
        b = c - 2;
        n = boss_cast_cols[b];
        cr_oam(0, 5 * 8 + 16, (10 - (n >> 1)) * 8 + cr_hat_dx[b] + 8, CR_T_HAT, is_cgb ? OBJPAL_CAST : 0);
    } else if (c >= 12) {
        for (k = 0; k < 3; k++) {                 // the three patrons, bobbing in turn
            bob = (((t >> 4) + k) & 3) ? 0 : 2;
            n = cr_pat_cx(c - 12, k);                  // (the pair's left edge + 8: the OAM x of its first column)
            cr_oam(2 * k, 72 - bob, n, CR_T_P + 6 * k, is_cgb ? OBJPAL_ROBOT + k : 0);
            cr_oam(2 * k + 1, 72 - bob, n + 8, CR_T_P + 6 * k + 2, is_cgb ? OBJPAL_ROBOT + k : 0);
        }
    }
}

// a card's work, CR_UNITS units a frame: phase 1 clearing, 2 loading, 3 rows, 4 shown (CR->step: the unit)
// The cut: while a card is built (6 to 16 frames) nothing of it may show, so the screen goes to the band colour at once: sprites off and the
// window (the second tilemap, 0x9C00, which credits_enter filled with blank tiles) over the whole screen. All LCDC bits and WX / WY / LYC: no
// palette write at all (palette RAM drops writes in mode 3 on a real LCD), no VRAM access, nothing to wait for. (The library's tile writes
// follow the background map bit of LCDC, so the cut does not use it.) The LYC interrupt, which ends the window at the banner, is parked past the
// frame. The switch is at the top of the frame, whose first lines are blank in every card. cr_unblank is the same in reverse, the frame after
// the card's last step.
static void cr_cut(void) {
    CR->blank = 1;
    LYC_REG = 255;
    overlay_on = 1;                                   // (main.c update shows the window every frame while it is set)
    WX_REG = 7; WY_REG = 0;
    CRITICAL { LCDC_REG = (LCDC_REG & ~LCDCF_OBJON) | LCDCF_WINON | LCDCF_WIN9C00; }
}

static void cr_unblank(void) {
    CR->blank = 0;
    CRITICAL { LCDC_REG = (LCDC_REG | LCDCF_OBJON) & ~LCDCF_WINON; }
    LYC_REG = BANNER_LYC;
    overlay_on = 0;
}

static void cr_card_work(uint8_t c) {
    uint8_t u;
    for (u = 0; u < CR_UNITS; u++) {
        if (CR->phase == 1) { if (cr_clear_unit()) { CR->phase = 2; CR->step = 0; } }
        else if (CR->phase == 2) { if (cr_load_unit(c, CR->step)) { CR->phase = 3; CR->step = 0; } else CR->step++; }
        else if (CR->phase == 3) { if (cr_show_unit(c, CR->step)) { CR->phase = 4; CR->step = 0; return; } else CR->step++; }
        else return;
    }
}

void credits_enter(uint8_t from_story) BANKED {
    uint8_t y;
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
    }
    music_pump();
    cr_blank();                                       // the second map (0x9C00), blank: what the cut shows
    for (y = 0; y < 32; y++) set_win_tiles(0, y, 20, 1, CR->row);
    if (is_cgb) {
        for (y = 0; y < 20; y++) CR->row[y] = BGPAL_HUD;
        VBK_REG = VBK_BANK_1;
        for (y = 0; y < 32; y++) set_win_tiles(0, y, 20, 1, CR->row);
        VBK_REG = VBK_BANK_0;
    }
    music_pump();
    CR->scroll = 0; CR->card = 255; CR->next = CR_AHEAD + 1; CR->t = 0; CR->phase = 0; CR->from_story = from_story; CR->f = 0; CR->step = 0; CR->tmask = 0; CR->amask = 0; CR->blank = 0;
    SCX_REG = 0; SCY_REG = 0;
    story_phase = STORY_PHASE_CREDITS;
    game_state = GS_STORY;
    music_load_now();                                 // the tune's first notes sound with the picture
    DISPLAY_ON;
}

static void cr_leave(void) {
    uint8_t s = CR->from_story;
    cr_unblank();                                     // (a skip in the middle of a card's build)
    SCY_REG = 0;
    TRANS_WANT();                                     // (src/trans.c: the next screen comes up behind the drink)
    if (s) story_end();
    else { title_back = TM_BONUS; title_back_sel = 3; title_enter(); }   // BONUS, the cursor on CREDITS
}

// story_update, every frame of the roll (GS_STORY). 1: the screen changed.
uint8_t credits_update(uint8_t pressed) BANKED {
    uint8_t c, top;
    uint16_t f, p;
    if (CR->blank && CR->phase == 4 && CR->step && CR->card < 200) cr_unblank();   // (first thing: the top lines of every card are blank, so the switch is not seen mid-picture)
    if (pressed & (J_B | J_START)) { cr_leave(); return 1; }
    CR->t++;
    f = cr_pos();
    CR->f = f;
    if (sound_on ? (cur_tune != TUNE_CREDITS && CR->t > 30) : f >= CR_TOTAL) { cr_leave(); return 1; }   // (the tune ends: cur_tune goes to TUNE_NONE)
    if (f < CR_ROLL) {                                                     // the cast
        c = f < CR_TITLE ? 0 : f < CR_HERO_END ? 1 : 2 + (uint8_t)((f - CR_HERO_END) / CR_CARD);
        if (CR->card != c) { CR->card = c; CR->phase = 1; CR->step = 0; if (!CR->blank) cr_cut(); hide_all_sprites(); }
        if (CR->phase < 4) cr_card_work(c);
        if (CR->phase == 4) {
            cr_card_sprites(c);                    // (its OAM goes out with the next VBlank, and then the colours come back, so the card shows whole)
            if (CR->step < 2) CR->step++;
        }
        return 0;
    }
    if (CR->card < 200 || CR->card == 255) { if (CR->blank) cr_unblank(); CR->card = 200; CR->step = 0; CR->tmask = 0; hide_all_sprites(); }   // the roll's start: its rows from the top (a wipe), the robots
    if (CR->card == 200) {
        for (c = 0; c < CR_UNITS && CR->card == 200; c++, CR->step++) {
            if (CR->step < 32) cr_rows(CR->step, 1);
            else if (CR->step < 35) load_patron_pose0(5, CR_T_P + 6 * (CR->step - 32), CR->step - 32);
            else {
                if (is_cgb) for (c = 0; c < 3; c++) { patron_pal_get(5, c, CR->row); CR->row[0] = 0; set_sprite_palette(OBJPAL_ROBOT + c, 1, (uint16_t *)CR->row); }
                CR->card = 201;
            }
        }
        return 0;
    }
    if (f > CR_F0) {
        p = f - CR_F0;
        if (p > CR_SPAN) p = CR_SPAN;
        p = (uint16_t)(p * CR_K) >> 5;
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
