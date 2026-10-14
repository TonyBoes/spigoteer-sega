// The HOW TO PLAY cards (owner 2026-10-14), shown by mg.c before a mini-game.
//   The FULL card, the first time a game is played (a bit a game in the save: save.c card_seen / card_mark, block "MGB1"): a screen of its own
//   in the list's look (light glyphs on the dark HUD band): row 1 "HOW TO PLAY", the game's name, up to three short lines (the buttons and the
//   goal), the Spigoteer, "PRESS A" blinking on row 16. A starts the game (mg.c's MG_CARD phase builds the game's screen then).
//   The SHORT card, after that: the banner of old (the name and one line, mg.c's mg_instr, 90 frames), which A now skips at once.
// Every game of mg.h's G_* has an entry in cards[], in that order (tests/test_mg_card.py checks it). Text: the HUD letters and digits, and the story
// font's . , ! ? - : ' (no %, no slash); a line has at most 18 letters (two columns of margin on the 20-wide screen), a placeholder
//   (today's banner line, up to 20) excepted.
//   PENDING cards: a game that is being reworked has its card text pending (PLAN.md "card text pending the Batch D rework"): the banner's
//   words stand in as its one line until its rework settles the controls.
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"
#include "story.h"
#include "mg.h"

#define ROW_TITLE        1
#define ROW_RULE_TOP     2
#define ROW_NAME         4
#define ROW_LINE         6              // rows 6, 8, 10 (a blank row between: readable at 1x)
#define ROW_PICTURE      12             // the Spigoteer (16 x 24 px) stands on rows 12-14 (y 96), in the middle
#define ROW_RULE_BOT    15
#define ROW_BOTTOM      17
#define PICTURE_X       72

typedef struct { const char *name, *line[3]; } card_t;   // (strings of this bank: the card is drawn from here, not from mg.c's)

static const card_t cards[MG_GAMES] = {
    /* G_STUB */ { "GREEN LIGHT", { "PRESS A ON GREEN", "NOT ON RED", "5 ROUNDS" } },
    /* G_QD   */ { "QUICK DRAW", { "WAIT FOR THE SIGN", "A OR B: THE BADGE", "WIN 3 FOR GOLD" } },
    /* G_BS   */ { "BATTERY SORT", { "LEFT FULL RIGHT DEAD", "", "" } },                   // PENDING (the Batch D rework)
    /* G_OU   */ { "ORDER UP!", { "WATCH THE ORDER", "D-PAD: REPEAT IT", "SERVE 7 FOR GOLD" } },
    /* G_MR   */ { "MILK RUN", { "UP DOWN LANE A TOSS", "", "" } },                    // PENDING
    /* G_LR   */ { "LOG ROLL", { "TAP AGAINST THE ROLL", "", "" } },                   // PENDING
    /* G_AD   */ { "ASTEROID DELIVERY", { "D-PAD: FLY, DODGE", "SOFT LAND AT LIGHT", "DELIVER 7 FOR GOLD" } },
    /* G_TK   */ { "TAIKO POUR", { "A: TOP LANE", "B: BOTTOM LANE", "STAY ON THE BEAT" } },
    /* G_MM   */ { "MARSHMALLOW DROP", { "A DROPS MARSHMALLOWS", "", "" } },                   // PENDING
    /* G_MK   */ { "MONKEY BUSINESS", { "LEFT RIGHT: HOP", "A: SHOO MONKEYS", "KEEP THE COCONUTS" } },
    /* G_TS   */ { "SHIRT CANNON", { "UP DOWN AIM A FIRE", "", "" } },                     // PENDING
    /* G_PO   */ { "THE POUR OFF", { "MOVE, THEN A: POUR", "SERVE THE GUESTS", "FIRST TO 20 WINS" } },
    /* G_B0   */ { "CAN SHAKE UP", { "TRACK THE CALM CAN", "LEFT RIGHT: CHOOSE", "A: PICK IT" } },
    /* G_B1   */ { "PERFECT POUR", { "HOLD A: POUR", "LET GO AT THE LINE", "3 GLASSES TO FILL" } },
    /* G_B2   */ { "TIP SHOWER", { "LEFT RIGHT: WALK", "TRAY CATCHES COINS", "AVOID THE TOMATOES" } },
};

static uint8_t glyph(char c) {
    switch (c) {
    case '.': return ST_GLYPH_PERIOD; case ',': return ST_GLYPH_COMMA; case '!': return ST_GLYPH_EXCL;
    case '?': return ST_GLYPH_QUEST;  case '\'': return ST_GLYPH_APOS; case '-': return ST_GLYPH_HYPHEN;
    case ':': return ST_GLYPH_COLON;
    }
    return glyph_for(c);
}

static void line(uint8_t y, const char *s) {     // LCD off: a centred text row (blank when s is "")
    uint8_t n = 0, x, i;
    while (s[n]) n++;
    for (i = 0; i < 20; i++) row_buf[i] = TILE_HUD_BLANK;
    x = (uint8_t)(20 - n) >> 1;
    while (*s) row_buf[x++] = glyph(*s++);
    set_bkg_tiles(0, y, 20, 1, row_buf);
}

static void rule(uint8_t y, uint8_t t) {
    uint8_t i;
    for (i = 0; i < 20; i++) row_buf[i] = t;
    set_bkg_tiles(0, y, 20, 1, row_buf);
}

// The full card for game `game` (mg.h G_*); LCD off, the venue and the generic tiles loaded (mg.c mg_enter)
void mg_card_draw(uint8_t game) BANKED {
    const card_t *c = &cards[game];
    uint8_t y;
    story_font_load();                           // the punctuation (over the BG ids the game's own screen loads again)
    for (y = 0; y < 18; y++) line(y, "");
    line(ROW_TITLE, "HOW TO PLAY");
    rule(ROW_RULE_TOP, TILE_PANEL_TOP);
    line(ROW_NAME, c->name);
    for (y = 0; y < 3; y++) line(ROW_LINE + 2 * y, c->line[y]);
    rule(ROW_RULE_BOT, TILE_PANEL_TOP);
    line(MG_CARD_PROMPT_ROW, "PRESS A");
    rule(ROW_BOTTOM, TILE_PANEL_BOT);
    if (is_cgb) {
        VBK_REG = VBK_BANK_1;
        for (y = 0; y < 20; y++) row_buf[y] = BGPAL_HUD;
        for (y = 0; y < 18; y++) set_bkg_tiles(0, y, 20, 1, row_buf);
        VBK_REG = VBK_BANK_0;
    }
    mg_spigoteer(PICTURE_X, ROW_PICTURE * 8, 0, 0, 0);
}
