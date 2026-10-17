// The credits roll (owner 2026-10-17): the game's credits scrolling up the screen in the story's lettering, the Spigoteer and three of
// the robot patrons standing under the "robot friends" line. It IS the story's credits: the CREDITS scene shows its picture and the
// four closing narrator pages, and its end (story.c scene_done) is this roll (credits_enter(1); its end is story_end: the STORY score entry) and from the title's BONUS > CREDITS (credits_enter(0); its end or B:
// back to BONUS, the cursor on CREDITS). The wording is CREDITS.md's, the "Special thanks to:" list in it.
//
// Screen: the HUD band (the scores table's style). One text row of the 32-row tilemap is queued each time the scroll has moved 8 px
// (a ring: row W of the roll, W = 18 + its index, lives at tilemap row W & 31; SCY is the scroll's low 8 bits; the roll's first row
// starts just under the screen). Up to two rows are never due at once (the scroll moves at most 2 px a frame). The text is in ROM here
// (cr_text), a string every other tilemap row (the glyphs fill their rows), "" a blank line; CR_SPR is the roll's row where the sprites' band starts.
// Sprites (OAM 0-9, the first 4 the Spigoteer as draw_bartender places him, 6 the robots as 8x16 entries: at most 8 on a line):
// the three robot variants of the factory's patron group (shift-0 poses as OBJ tiles, OBJ palettes 5-7), who bob in turn, and the
// bartender, facing them, who raises a hand now and then. They move up with the text and are hidden once off the screen.
// A speeds it up (held), B / START skip (to the end: story_end, or the BONUS menu). The roll ends HOLD_FRAMES after the last line
// has scrolled to the middle of the screen. The music plays on as it was (the title's tune in both places).
// State in story_scratch (no WRAM of its own; nothing else runs while the roll shows): tests read it at story_scratch + offset.
#pragma bank 20          // (pinned: bank 20 is the roomy one)
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"
#include "music.h"
#include "palettes.h"
#include "story.h"

extern uint8_t overlay_on, joy, story_phase;
BANKREF_EXTERN(patron_tiles_robots)
extern const uint8_t patron_tiles_robots[];
void spr_data_far(uint8_t first, uint8_t n, const uint8_t *d, uint8_t bank);   // src/main.c (ROM0)

#define CR_FIRST      18      // the roll's first row, in world rows (just under the screen)
#define CR_AHEAD      20      // rows are kept written up to T + CR_AHEAD (T: the top row of the screen)
#define CR_SPR        16      // the sprites' band's first row of the roll (4 rows: entries 8-9; the Spigoteer's art is 24 px tall)
#define CR_SLOW        2      // quarter pixels a frame: half a pixel
#define CR_FAST        8      // A held: 2 px a frame
#define CR_HOLD      150      // the last line stays this many frames (A shortens it)
#define CR_T_P       100      // the robots' OBJ tiles: 3 variants x 6 (OBJ ids 100-117, in dgag.c's patron range)
#define CR_BT_X      120      // the Spigoteer's left edge; the robots stand at 24, 56, 88
#define OBJPAL_ROBOT   5

// state in story_scratch
struct cr_state {
    uint8_t row[20];          // the row being queued (the copy list reads it at VBlank)
    uint16_t scroll;          // px scrolled
    uint8_t sub;              // quarter pixels carried
    uint8_t next;             // the next world row to write
    uint8_t t;                // frames on the screen
    uint8_t hold;             // frames at the end
    uint8_t from_story;       // 1: story_end follows
};
#define CR ((struct cr_state *)story_scratch)

// The roll. 20 columns a row. Owner's lines (2026-10-17): "Game Design, Media, and Story by Tony and his tireless team of robot
// friends"; "no credits for public domain tunes. Public Domain."; "Special thanks to:" the platforms, frameworks and projects used.
static const char *const cr_text[] = {      // a line every other tilemap row (the glyphs fill their rows)
    "SPIGOTEER",            // 0
    "",
    "GAME DESIGN, MEDIA,",
    "AND STORY BY",
    "TONY",                 // 4
    "AND HIS TIRELESS",
    "TEAM OF",
    "ROBOT FRIENDS",        // 7
    "", "",                 // 8-9: the sprites' band (CR_SPR: 4 rows, the first 3 used)
    "MUSIC",                // 10
    "PUBLIC DOMAIN",
    "MELODIES, ARRANGED",
    "FOR THIS GAME",
    "",
    "SPECIAL THANKS TO:",   // 15
    "",
    "GBDK-2020",
    "SDCC",
    "HUGEDRIVER",
    "RGBDS",                // 20
    "SAMEBOY",
    "PYBOY",
    "PAN DOCS",
    "THE GBDEV",
    "COMMUNITY",            // 25
    "",
    "THANKS FOR PLAYING!",  // 27
};
#define CR_N (sizeof(cr_text) / sizeof(cr_text[0]))
#define CR_LAST_T ((CR_FIRST + 2 * (CR_N - 1)) * 8 - 72)   // the scroll at which the last line is in the middle of the screen

static uint8_t cr_glyph(char c) {
    if ((uint8_t)(c - 'A') < 26) return glyph_az[(uint8_t)(c - 'A')];
    switch (c) {
    case '.': return ST_GLYPH_PERIOD; case ',': return ST_GLYPH_COMMA; case '!': return ST_GLYPH_EXCL;
    case '?': return ST_GLYPH_QUEST; case '\'': return ST_GLYPH_APOS; case '-': return ST_GLYPH_HYPHEN;
    case ':': return ST_GLYPH_COLON;
    }
    return GLYPH_FAST(c, glyph_for(c));
}

// the row for world row w (blank before the roll and after it), centred, into CR->row
static void cr_build(uint8_t w) {
    const char *s = "";
    uint8_t i, n = 0, x;
    if (w >= CR_FIRST && !((w - CR_FIRST) & 1) && (w - CR_FIRST) >> 1 < CR_N) s = cr_text[(w - CR_FIRST) >> 1];
    for (i = 0; i < 20; i++) CR->row[i] = TILE_HUD_BLANK;
    while (s[n]) n++;
    x = (20 - n) >> 1;
    for (i = 0; i < n; i++) CR->row[x + i] = cr_glyph(s[i]);
}

static void cr_rows(uint8_t y, uint8_t n) {       // LCD off: n rows from row y of the roll's rows (blank where it is not)
    for (; n; n--, y++) {
        cr_build(y);
        set_bkg_tiles(0, y & 31, 20, 1, CR->row);
    }
}

void credits_enter(uint8_t from_story) BANKED {
    uint8_t v, y;
    uint16_t p[4];
    DISPLAY_OFF;
    music_pump();
    overlay_on = 0; HIDE_WIN; LYC_REG = BANNER_LYC;
    vq_reset(); hud_dirty = 0; vram_pending = 0;
    hide_all_sprites();
    story_font_load();                                // the punctuation (over the patron range: the next screen's load puts it back)
    music_pump();
    for (y = 0; y < 32; y += 4) { cr_rows(y, 4); music_pump(); }   // (rows 0-17 blank, then the roll's first 14 rows: the ring)
    if (is_cgb) {
        VBK_REG = VBK_BANK_1;
        for (y = 0; y < 20; y++) CR->row[y] = BGPAL_HUD;
        for (y = 0; y < 32; y++) set_bkg_tiles(0, y, 20, 1, CR->row);
        VBK_REG = VBK_BANK_0;
    }
    spr_data_far(CR_T_P, 18, patron_tiles_robots + PATRON_SHIFT0_OFS * 16, BANK(patron_tiles_robots));   // the three robots' poses
    if (is_cgb) for (v = 0; v < 3; v++) { patron_pal_get(5, v, p); p[0] = 0; set_sprite_palette(OBJPAL_ROBOT + v, 1, p); }
    music_pump();
    CR->scroll = 0; CR->sub = 0; CR->next = CR_AHEAD + 1; CR->t = 0; CR->hold = 0; CR->from_story = from_story;
    SCX_REG = 0; SCY_REG = 0;
    story_phase = STORY_PHASE_CREDITS;
    game_state = GS_STORY;
    DISPLAY_ON;
}

static void cr_oam(uint8_t n, int16_t y, uint8_t x, uint8_t tile, uint8_t prop) {   // y: OAM y; off the screen: hidden
    OAM_item_t *o = shadow_OAM + n;
    if (y < 1 || y > 159) { o->y = 0; return; }
    o->y = (uint8_t)y; o->x = x; o->tile = tile; o->prop = prop;
}

static void cr_sprites(void) {
    int16_t y = (int16_t)(CR_FIRST + CR_SPR) * 8 - CR->scroll + 16;   // the band's top, OAM y
    uint8_t t = CR->t, k, f, base, bob;
    for (k = 0; k < 3; k++) {                         // the robots, bobbing in turn (2 px up for 16 frames in every 64)
        bob = (((t >> 4) + k) & 3) ? 0 : 2;
        cr_oam(4 + 2 * k, y + 8 - bob, 24 + 32 * k + 8, CR_T_P + 6 * k, is_cgb ? OBJPAL_ROBOT + k : 0);
        cr_oam(5 + 2 * k, y + 8 - bob, 24 + 32 * k + 16, CR_T_P + 6 * k + 2, is_cgb ? OBJPAL_ROBOT + k : 0);
    }
    f = ((t >> 4) & 3) == 1 ? BT_CATCH : BT_IDLE;     // the Spigoteer: a hand up now and then (draw_bartender's four entries)
    base = OBJ_BARTENDER + f * BARTENDER_TILES_PER_FRAME;
    cr_oam(0, y, CR_BT_X + 8, base, OBJPAL_BARTENDER);
    cr_oam(1, y, CR_BT_X + 16, base + 2, OBJPAL_BARTENDER);
    cr_oam(2, y + 16, CR_BT_X + 8, base + 4, OBJPAL_BARTENDER);
    cr_oam(3, y + 16, CR_BT_X + 16, base + 6, OBJPAL_BARTENDER);
}

static void cr_leave(void) {
    uint8_t s = CR->from_story;
    SCY_REG = 0;
    TRANS_WANT();                                     // (src/trans.c: the next screen comes up behind the drink)
    if (s) story_end();
    else { title_back = TM_BONUS; title_back_sel = 3; title_enter(); }   // BONUS, the cursor on CREDITS
}

// story_update, every frame of the roll (GS_STORY). 1: the screen changed.
uint8_t credits_update(uint8_t pressed) BANKED {
    uint8_t top;
    if (pressed & (J_B | J_START)) { cr_leave(); return 1; }
    CR->t++;
    if (CR->scroll < CR_LAST_T) {
        CR->sub += (joy & J_A) ? CR_FAST : CR_SLOW;
        CR->scroll += CR->sub >> 2;
        CR->sub &= 3;
        if (CR->scroll > CR_LAST_T) CR->scroll = CR_LAST_T;
        top = (uint8_t)(CR->scroll >> 3);
        if (CR->next <= (uint8_t)(top + CR_AHEAD)) {   // a row has come within reach: its ring slot is off the screen
            cr_build(CR->next);
            vq_add(0, CR->row, 0, CR->next & 31, 20);
            CR->next++;
        }
        SCY_REG = (uint8_t)CR->scroll;
    } else {
        CR->hold += (joy & J_A) ? 4 : 1;
        if (CR->hold >= CR_HOLD) { cr_leave(); return 1; }
    }
    cr_sprites();
    return 0;
}
