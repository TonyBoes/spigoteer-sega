// The HOW TO PLAY cards (owner 2026-10-14), shown by mg.c before a mini-game and from the pause menu (src/pause.c).
//   The FULL card, the first time a game is played (a bit a game in the save: save.c card_seen / card_mark, block "MGB1"): a screen of its own
//   in the list's look (light glyphs on the dark HUD band), in the story box's gold moulding (ST_FRAME_*, tiles the font load brings): row 1
//   "HOW TO PLAY", the game's icon (an 8x8 tile, assets/art/mg_card.txt, loaded over the font's spigot-icon tile), its name, up to four short
//   lines (the buttons and the goal), "PRESS A" blinking on row 16. A starts the game (mg.c's MG_CARD phase builds the game's screen then).
//   No sprites: BG tiles only (the Spigoteer of the first cards is gone).
//   PAGES: a card has 1-3 pages. The table below is page 1 (the name and up to four lines); a game's further pages are the entries of more[]
//   (page 2, then 3: four lines each, under the same name). With more pages to come the prompt row reads NEXT (A turns the page); on the last page
//   A starts the game (PRESS A). From BONUS > MINI GAMES the full card also takes B (back to the list): its prompt row then reads
//   "A START  B BACK" ("A NEXT  B BACK" on a page that is not the last).
//   OVER A PAUSED GAME (kind 2, pause.c's HOW TO PLAY row): the same card drawn into the window map (0x9C00) rows 0-17, so the game's own BG map and
//   tiles stay untouched; sprites are switched off by pause.c, the story font's tiles (16: the punctuation, the frame, the spigot icon the
//   game's icon replaces) are kept in the window map's rows 20-27 (never on screen) while the card shows them and put back afterwards.
//   The SHORT card, after that: the banner of old (the name and one line, mg.c's mg_instr, 90 frames), which A now skips at once.
// Every game of mg.h's G_* has an entry in cards[], in that order (tests/test_mg_card.py checks it). Text: the HUD letters and digits, and the story
// font's . , ! ? - : ' (no %, no slash); a line has at most 18 letters (the frame takes a column each side), a placeholder
//   (today's banner line, up to 20: drawn over the frame's sides) excepted.
//   PENDING cards: a game that is being reworked has its card text pending (PLAN.md "card text pending the Batch D rework"): the banner's
//   words stand in as its one line until its rework settles the controls.
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"
#include "story.h"
#include "mg.h"
#include "mg_card_art.h"   // card_icons[]: one 8x8 tile a game (assets/art/mg_card.txt)

#define ROW_TITLE        1
#define ROW_RULE_TOP     2
#define ROW_ICON         3              // the game's icon, column 9
#define ROW_NAME         5              // (row 4 blank: the icon stands clear of the name)
#define ROW_RULE_MID     6
#define ROW_LINE         7              // rows 7, 9, 11, 13 (a blank row between: readable at 1x)
#define ROW_RULE_BOT    15
#define ICON_COL         9
#define SAVE_ROW        20              // the saved font tiles (all 16 of the font: story_font_load loads them together): tile i at window map row 20 + i / 2,
                                        // columns 0-15 (i even) or 16-31 (18 rows show: never seen)

typedef struct { const char *name, *line[4]; } card_t;   // (strings of this bank: the card is drawn from here, not from mg.c's)
typedef struct { uint8_t game; const char *line[4]; } more_t;   // a further page of game `game`

static const card_t cards[MG_GAMES] = {
    /* G_STUB */ { "GREEN LIGHT", { "PRESS A ON GREEN", "NOT ON RED", "5 ROUNDS", "" } },
    /* G_QD   */ { "QUICK DRAW", { "WAIT FOR THE SIGN", "A OR B: THE BADGE", "WIN 3 FOR GOLD", "" } },
    /* G_BS   */ { "BATTERY SORT", { "LEFT: FULL CELL", "RIGHT: DEAD CELL", "DOWN: BROKEN CELL", "3 STRIKES END IT" } },
    /* G_OU   */ { "ORDER UP!", { "WATCH THE ORDER", "D-PAD: REPEAT IT", "SERVE 7 FOR GOLD", "" } },
    /* G_MR   */ { "MILK RUN", { "UP DOWN LANE A TOSS", "", "", "" } },                    // PENDING
    /* G_LR   */ { "LOG ROLL", { "LEFT RIGHT: LEAN", "AGAINST THE ROLL", "A OR B: HOP", "OVER THE FISH" } },
    /* G_AD   */ { "ASTEROID DELIVERY", { "D-PAD: FLY, DODGE", "SOFT LAND AT LIGHT", "DELIVER 7 FOR GOLD", "" } },
    /* G_TK   */ { "TAIKO POUR", { "A: TOP LANE", "B: BOTTOM LANE", "STAY ON THE BEAT", "" } },
    /* G_MM   */ { "MARSHMALLOW DROP", { "D-PAD: MOVE ARM", "A: DROP A MALLOW", "FILL SIX MUGS WITH", "THREE EACH" } },
    /* G_MK   */ { "MONKEY BUSINESS", { "LEFT RIGHT: HOP", "A: SHOO MONKEYS", "KEEP THE COCONUTS", "" } },
    /* G_TS   */ { "SHIRT CANNON", { "A STARTS THE METER", "A AGAIN TO FIRE", "RED ENDS: OOPS", "OOPS: NO POINTS" } },
    /* G_PO   */ { "THE POUR OFF", { "MOVE, THEN A: POUR", "SERVE THE GUESTS", "FIRST TO 20 WINS", "" } },
    /* G_B0   */ { "CAN SHAKE UP", { "TRACK THE CALM CAN", "LEFT RIGHT: CHOOSE", "A: PICK IT", "" } },
    /* G_B1   */ { "PERFECT POUR", { "HOLD A: POUR", "LET GO AT THE LINE", "3 GLASSES TO FILL", "FOAM KEEPS RISING" } },
    /* G_B2   */ { "TIP SHOWER", { "LEFT RIGHT: WALK", "TRAY CATCHES COINS", "AVOID THE TOMATOES", "100 POINTS A COIN" } },
};

// the further pages, in page order (a game's entries together). The debug stub, the shake-up, Marshmallow Drop, T-Shirt Cannon and Log Roll have a second page.
static const more_t more[] = {
    { G_STUB, { "EARLY IS A MISS", "SLOW IS A MISS", "KEEP YOUR EYES UP", "" } },
    { G_MM,   { "MUGS LOOP ROUND", "19 MALLOWS ONLY", "MISS ONE AT MOST", "FOR GOLD" } },
    { G_LR,   { "WATCH THE RIPPLES", "A FISH LEAPS SOON", "HIT: YOU WOBBLE", "STAY UP 40 SECONDS" } },
    { G_B0,   { "3 LEVELS, EACH", "FASTER THAN LAST", "MISS: RUN ENDS", "" } },
    { G_TS,   { "FANS RAISE HANDS", "CATCH: 300 POINTS", "ANY OTHER FAN: 30", "9 CATCHES: GOLD" } },
};
#define MORE_N (sizeof(more) / sizeof(more[0]))

// the pages of game `game`: page 1 (cards[]) plus its entries in more[]
uint8_t mg_card_pages(uint8_t game) BANKED {
    uint8_t i, n = 1;
    for (i = 0; i < MORE_N; i++) if (more[i].game == game) n++;
    return n;
}

static const char *page_line(uint8_t game, uint8_t page, uint8_t k) {
    uint8_t i;
    if (!page) return cards[game].line[k];
    for (i = 0; i < MORE_N; i++) if (more[i].game == game && !--page) return more[i].line[k];
    return "";
}

static uint8_t glyph(char c) {
    switch (c) {
    case '.': return ST_GLYPH_PERIOD; case ',': return ST_GLYPH_COMMA; case '!': return ST_GLYPH_EXCL;
    case '?': return ST_GLYPH_QUEST;  case '\'': return ST_GLYPH_APOS; case '-': return ST_GLYPH_HYPHEN;
    case ':': return ST_GLYPH_COLON;
    }
    return glyph_for(c);
}

// kind: 0 the full card of a story / ARCADE game, 1 of BONUS > MINI GAMES (B goes back), 2 over a paused game (window map)
static void put(uint8_t kind, uint8_t y, const uint8_t *b) {
    if (kind == 2) set_win_tiles(0, y, 20, 1, b); else set_bkg_tiles(0, y, 20, 1, b);
}

static void edges(uint8_t *b) {                 // the frame's sides on a 20-wide row (the middle blank)
    uint8_t i;
    for (i = 1; i < 19; i++) b[i] = TILE_HUD_BLANK;
    b[0] = ST_FRAME_L; b[19] = ST_FRAME_R;
}

static void line(uint8_t kind, uint8_t y, const char *s) {     // a centred text row (blank when s is "")
    uint8_t b[20], n = 0, x;
    while (s[n]) n++;
    edges(b);
    if (n > 18) { b[0] = b[19] = TILE_HUD_BLANK; x = (uint8_t)(20 - n) >> 1; }   // (a pending card's banner line: over the frame's sides)
    else x = 1 + ((uint8_t)(18 - n) >> 1);
    while (*s) b[x++] = glyph(*s++);
    put(kind, y, b);
}

static void rule(uint8_t kind, uint8_t y) {
    uint8_t b[20], i;
    edges(b);
    for (i = 1; i < 19; i++) b[i] = TILE_PANEL_TOP;
    put(kind, y, b);
}

static void frame_row(uint8_t kind, uint8_t y, uint8_t l, uint8_t m, uint8_t r) {   // the top or bottom of the frame
    uint8_t b[20], i;
    for (i = 1; i < 19; i++) b[i] = m;
    b[0] = l; b[19] = r;
    put(kind, y, b);
}

static const char *prompt(uint8_t game, uint8_t page, uint8_t kind) {
    uint8_t next = page + 1 < mg_card_pages(game);
    if (kind == 2) return next ? "NEXT" : "A BACK";
    if (kind == 1) return next ? "A NEXT  B BACK" : "A START  B BACK";
    return next ? "NEXT" : "PRESS A";
}

// the prompt row, shown or blank (mg.c blinks it)
void mg_card_prompt(uint8_t game, uint8_t page, uint8_t kind, uint8_t on) BANKED {
    line(kind, MG_CARD_PROMPT_ROW, on ? prompt(game, page, kind) : "");
}

// the rows that change from page to page: the four lines and the prompt
void mg_card_page(uint8_t game, uint8_t page, uint8_t kind) BANKED {
    uint8_t y;
    for (y = 0; y < 4; y++) line(kind, ROW_LINE + 2 * y, page_line(game, page, y));
    mg_card_prompt(game, page, kind, 1);
}

static void draw_rows(uint8_t game, uint8_t kind) {
    uint8_t y, b[20];
    set_bkg_data(ST_SPIGOT_ICON, 1, card_icons + (uint16_t)game * 16);   // (after story_font_load: the font's spigot tile is this game's icon)
    frame_row(kind, 0, ST_FRAME_TL, ST_FRAME_T, ST_FRAME_TR);
    for (y = 1; y < 17; y++) line(kind, y, "");
    frame_row(kind, 17, ST_FRAME_BL, ST_FRAME_B, ST_FRAME_BR);
    line(kind, ROW_TITLE, "HOW TO PLAY");
    rule(kind, ROW_RULE_TOP);
    edges(b); b[ICON_COL] = ST_SPIGOT_ICON;
    put(kind, ROW_ICON, b);
    line(kind, ROW_NAME, cards[game].name);
    rule(kind, ROW_RULE_MID);
    rule(kind, ROW_RULE_BOT);
}

// The full card (page 1) for game `game` (mg.h G_*); LCD off, the venue and the generic tiles loaded (mg.c mg_enter)
void mg_card_draw(uint8_t game, uint8_t kind) BANKED {
    uint8_t y, b[20];
    story_font_load();                           // the punctuation and the frame (over the BG ids the game's own screen loads again)
    draw_rows(game, kind);
    mg_card_page(game, 0, kind);
    if (is_cgb) {
        VBK_REG = VBK_BANK_1;
        for (y = 0; y < 20; y++) b[y] = BGPAL_HUD;
        for (y = 0; y < 18; y++) set_bkg_tiles(0, y, 20, 1, b);
        VBK_REG = VBK_BANK_0;
    }
}

// ---- over a paused game (kind 2): the window map's rows 0-17, the LCD on ---------------------------------------------------------------
// VRAM read when the LCD is not drawing (the way GBDK's own get_* wait; those library functions would take ~300 bytes of ROM0)
static uint8_t vget(const volatile uint8_t *a) {
    while (STAT_REG & 2) ;
    return *a;
}

void mg_card_win_open(uint8_t game) BANKED {
    uint8_t i, k, b[20];
    for (i = 0; i < STORY_FONT_COUNT; i++) {     // the font tiles, kept
        const volatile uint8_t *t = (const volatile uint8_t *)((STORY_FONT_BASE + i < 128 ? 0x9000 : 0x8000) + (uint16_t)(STORY_FONT_BASE + i) * 16);
        for (k = 0; k < 16; k++) b[k] = vget(t + k);
        set_win_tiles((i & 1) << 4, SAVE_ROW + (i >> 1), 16, 1, b);
    }
    story_font_load();
    if (is_cgb) {
        VBK_REG = VBK_BANK_1;
        for (i = 0; i < 20; i++) b[i] = BGPAL_HUD;
        for (i = 0; i < 18; i++) set_win_tiles(0, i, 20, 1, b);
        VBK_REG = VBK_BANK_0;
    }
    draw_rows(game, 2);
    mg_card_page(game, 0, 2);
}

// the font tiles back; rows 6-17 and the saved tiles' rows empty again (zeros, palette 0: as they were)
void mg_card_win_close(void) BANKED {
    uint8_t i, k, b[20];
    for (i = 0; i < STORY_FONT_COUNT; i++) {
        const volatile uint8_t *r = (const volatile uint8_t *)(0x9C00 + (SAVE_ROW + (i >> 1)) * 32 + ((i & 1) << 4));
        for (k = 0; k < 16; k++) b[k] = vget(r + k);
        set_bkg_data(STORY_FONT_BASE + i, 1, b);
    }
    for (i = 0; i < 20; i++) b[i] = 0;
    for (i = 6; i < 18; i++) set_win_tiles(0, i, 20, 1, b);
    for (i = 0; i < STORY_FONT_COUNT; i++) set_win_tiles((i & 1) << 4, SAVE_ROW + (i >> 1), 16, 1, b);
    if (is_cgb) {
        VBK_REG = VBK_BANK_1;
        for (i = 6; i < 18; i++) set_win_tiles(0, i, 20, 1, b);
        VBK_REG = VBK_BANK_0;
    }
}
