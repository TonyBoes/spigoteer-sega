// The title's BONUS > BOSS RUSH (owner 2026-10-12: "a boss rush mode in the BONUS section, that can be unlockable, but
// will also help us in play testing the bosses. Options: play all, or choose a boss").
//
// Screens (the MINI GAMES list's style: light HUD glyphs and the story font's punctuation on the dark band, the HUD
// palette; row 0 the title, row 1 a panel line, rows 13-16 the details between panel lines 12 and 17), all run as
// GS_STORY with story_phase STORY_PHASE_RUSH (story_update hands the frame here: no ROM0 case):
//   MENU    ALL / CHOOSE (rows 4 / 6, the mug cursor). ALL needs 2 bosses unlocked ("ALL LOCKED" and A does nothing
//           until then). B: the title's BONUS submenu, the cursor on BOSS RUSH.
//   LIST    (CHOOSE) every built boss in chapter order, one a line from row 2: the name at column 1, his best rush win's
//           time at 15; a boss not unlocked lists as "? ? ?" and A does nothing. B: the menu, on CHOOSE.
//   NEXT    (ALL) before each fight: FIGHT n OF m, NEXT: <BOSS>, his venue, the lives, score and time so far; A / START
//           or NEXT_FRAMES and the fight starts.
//   RESULT  YOU WIN / YOU LOSE (CHOOSE) or ALL CLEAR / GAME OVER (ALL), the time, the score, the best (NEW BEST);
//           A RETRY (the same boss, or ALL from the first), B BACK (the list on that boss, or the menu on ALL).
// A fight (story.c rush_fight) is the venue's boss step exactly as the story plays it (his banner, the regulars, the
// perfect pour, the HUD meter; a lost life restarts him with his damage kept) with MODE_RUSH: no story progress, no
// tune unlocks (save_lock 1), no top 5, no extra lives by score. CHOOSE: 3 lives, the score from 0. ALL: 3 lives at
// the start, carried from fight to fight; a won fight gives one back (+1, never above START_LIVES: with three lives
// for up to ten bosses a run would otherwise end at the third or fourth boss for a strong player, and a refill to 3
// would take the rush's edge away), the score totalled. Lives out: GAME OVER over the frozen fight (story.c), then the
// result. The time is the fights' PLAYING frames (the banners, freezes and outros not counted).
//
// Which bosses: the built ones, read from the same data the story plays (build/story.h's step table: a chapter whose
// boss step is not STEP_SKIP, i.e. tools/gen_story.py BUILT_SLOTS["BOSS"]), so a boss added later appears here with
// no edit to this file. Unlocked: beaten in STORY or ARCADE (save.c boss_beaten; a debug-select run records nothing).
// The DEBUG_MENU build (`make`) lists every built boss unlocked (for play testing); `make release` the real rule.
// Saved (save.c, the Practice block's rush part; written only by a won fight or a finished run): each boss's fastest
// rush win (CHOOSE or a fight of ALL), ALL's best score with that run's time and bosses beaten.
#pragma bank 255
#include <gb/gb.h>
#include <stdint.h>

#include "game.h"
#include "music.h"
#include "story.h"
#include "boss.h"
#include "rush.h"

extern uint8_t overlay_on, score_digits[6], story_phase;
extern uint32_t score;
#if RUSH_TOP != STORY_SCRATCH - BOSS_SCRATCH_N
#error "rush.h RUSH_TOP must be where boss.h's BOSS_SCRATCH starts"
#endif

#define ROW_HEAD        0
#define ROW_LIST        2
#define ROW_BOX        12       // panel; the info lines 13-16; panel 17
#define INFO_LINES      4
// The list (owner 2026-10-15: the capitals touched): RVIS bosses on every other row 2, 4 .. 12 (a blank row between them, as the MINI GAMES list),
// the window scrolls with the cursor (RUSH->top, the shared scroll arrows); a blank row 13, panel 14, the info lines 15-16 (best, keys), panel 17.
#define RVIS            6
#define ROW_BOX_LIST   14
#define INFO_LIST       2
#define MENU_ROW0       4       // the menu's lines: rows 4 and 6, the text at column 7
#define MENU_COL        7
#define COL_NAME        1
#define COL_BEST       15
#define ROWS_PER_FRAME  2       // rows built and queued a frame (~15k cycles each: a quick scroll with 4 ran the frame past its VBlank)
#define NEXT_FRAMES   180       // the NEXT card stays 3 s (or until A / START)
#define ROW(k)        (story_scratch + (uint8_t)(k) * 20)   // row buffer k: a line k < lines(), else info line
#define T_MAX      0xFFFFu

// The ten planned bosses by venue (docs/minigames_bosses.md section 3; the list shows only the built ones)
static const char *const boss_name[BOSS_COUNT] = {
    "BIG TEX", "THE MASCOT", "SASQUATCH", "THE CRITIC", "THE YETI", "PROTOTYPE", "DUKE", "SUMO CHAMP",
    "LEO THE LION", "MOTHERSHIP",
};
static const char *const venue_name[BOSS_COUNT] = {
    "THE SALOON", "THE STADIUM", "THE LUMBER LODGE", "THE BISTRO", "THE IGLOO", "THE ROBOT FACTORY",
    "THE CHROME COW", "THE TEAHOUSE", "THE JUNGLE ZOO", "THE SPACE LOUNGE",
};
static const char locked_name[] = "? ? ?";
static const char *const locked_info[INFO_LINES] = { locked_name, "LOCKED", "BEAT HIM IN STORY", "OR ARCADE" };

// ---- the bosses -------------------------------------------------------------------------------------------------
static uint8_t built(uint8_t v) { return (RUSH->built >> v) & 1; }   // (the mask: rush_enter)

static uint8_t scan_built(uint8_t v) {           // venue v's boss fight is built (it follows Last call: build/story.h BOSS_BUILT_MASK)
    return (BOSS_BUILT_MASK >> v) & 1;
}

static uint8_t unlocked(uint8_t v) {
    if (!built(v)) return 0;
#ifdef DEBUG_MENU
    return 1;
#else
    return (((uint16_t)RUSH->save[RSV_BITS] | ((uint16_t)RUSH->save[RSV_BITS + 1] << 8)) >> v) & 1;
#endif
}

static uint8_t nth_built(uint8_t k) {            // the venue of the list's line k (BOSS_COUNT: none)
    uint8_t v;
    for (v = 0; v < BOSS_COUNT; v++) if (built(v) && !k--) return v;
    return BOSS_COUNT;
}

static uint8_t lines(void) { return RUSH->nlines; }   // the list's lines (the built bosses, counted once in rush_enter)

static uint8_t count_unlocked(void) {
    uint8_t v, n = 0;
    for (v = 0; v < BOSS_COUNT; v++) n += unlocked(v);
    return n;
}

static uint8_t next_unlocked(uint8_t v) {        // the first unlocked boss from venue v (BOSS_COUNT: none)
    for (; v < BOSS_COUNT; v++) if (unlocked(v)) return v;
    return BOSS_COUNT;
}

static uint16_t get16(uint8_t i) { return RUSH->save[i] | ((uint16_t)RUSH->save[i + 1] << 8); }
static void put16(uint8_t i, uint16_t v) { RUSH->save[i] = (uint8_t)v; RUSH->save[i + 1] = (uint8_t)(v >> 8); }
static uint32_t all_score(void) {
    return RUSH->save[RSV_ALL_SCORE] | ((uint32_t)RUSH->save[RSV_ALL_SCORE + 1] << 8)
         | ((uint32_t)RUSH->save[RSV_ALL_SCORE + 2] << 16);
}

// ---- text ------------------------------------------------------------------------------------------------------
static uint8_t glyph(char c) {
    if ((uint8_t)(c - 'A') < 26) return glyph_az[(uint8_t)(c - 'A')];   // (letters first: the common case, no switch)
    switch (c) {
    case '.': return ST_GLYPH_PERIOD; case '?': return ST_GLYPH_QUEST; case '-': return ST_GLYPH_HYPHEN;
    case ':': return ST_GLYPH_COLON;
    }
    return GLYPH_FAST(c, glyph_for(c));
}

static void blank(uint8_t *r) {
    uint8_t i;
    for (i = 0; i < 20; i++) r[i] = TILE_HUD_BLANK;
}

static uint8_t slen(const char *s) {
    uint8_t n = 0;
    while (s[n]) n++;
    return n;
}

static void put(uint8_t *r, uint8_t x, const char *s) {   // a string (this bank or WRAM) at column x (255: centred)
    if (x == 255) x = (20 - slen(s)) >> 1;
    while (*s && x < 20) r[x++] = glyph(*s++);
}

static char *cat(char *d, const char *s) {       // append s at d (WRAM), return the end
    while (*s) *d++ = *s++;
    *d = 0;
    return d;
}

static char *num(char *d, uint8_t v) {            // v (0..99) without leading zero
    if (v >= 10) { *d++ = '0' + v / 10; v %= 10; }
    *d++ = '0' + v;
    *d = 0;
    return d;
}

static char *mmss(char *d, uint16_t f) {         // frames as M:SS (16 bits of frames: at most 18:12)
    uint16_t s = f / 60;
    d = num(d, (uint8_t)(s / 60));
    s %= 60;
    *d++ = ':';
    *d++ = '0' + (uint8_t)s / 10; *d++ = '0' + (uint8_t)s % 10;
    *d = 0;
    return d;
}

static char *six(char *d, uint32_t v) {          // a score's six digits
    uint8_t g[6], i;
    split6(g, v);
    for (i = 0; i < 6; i++) *d++ = '0' + g[i];
    *d = 0;
    return d;
}

static void line_at(uint8_t y, uint8_t x, const char *s) {  // LCD off: a text row
    blank(row_buf);
    put(row_buf, x, s);
    set_bkg_tiles(0, y, 20, 1, row_buf);
    music_pump();                                // (a screen's build is several frames: the tune ticks on)
}

// ---- the screen's frame -------------------------------------------------------------------------------------------
static uint8_t box_row(void) { return RUSH->scr == RS_LIST ? ROW_BOX_LIST : ROW_BOX; }
static uint8_t info_n(void) { return RUSH->scr == RS_LIST ? INFO_LIST : INFO_LINES; }

static void frame_begin(uint8_t scr) {           // LCD off: a blank band with the title, its panels, HUD attributes
    TRANS_MENU();                                // (src/trans.c: the quick white fade between the menu, the list and the result)
    DISPLAY_OFF;
    if (scr != RS_NEXT) {                        // the menu, the list and the result play the title tune (left alone when it
        music_play(TUNE_TITLE);                  // already plays; after a fight its patterns are copied back now and the
        music_load_now();                        // pumps below tick it through the rebuild)
    }
    music_pump();
    RUSH->scr = scr;
    overlay_on = 0; HIDE_WIN; LYC_REG = BANNER_LYC;
    vq_reset(); hud_dirty = 0; vram_pending = 0; life_lost = 0;
    clear_dirty();
    clear_patrons(); clear_mugs();
    tip_timer = 0; show_timer = 0;
    hide_all_sprites();
    story_on = 0;                                // (the rush's screens are not a story; a fight sets it again)
    story_font_load();                           // the punctuation (over the patron range: a fight's load puts it back)
    music_pump();
    list_frame(box_row());   // (the wood wall, src/mg_list.c: the header band, the board seams on the menu and the list, the panel)
    music_pump();
    line_at(ROW_HEAD, 255, "BOSS RUSH");
    RUSH->t = 0; RUSH->dirty = 0;
    story_phase = STORY_PHASE_RUSH;
    game_state = GS_STORY;
}

// ---- MENU and LIST: lines with a cursor, the details below ---------------------------------------------------------
static uint8_t n_lines(void) { uint8_t n; if (RUSH->scr == RS_MENU) return 2; n = lines(); return n < RVIS ? n : RVIS; }   // (the list: its window)
static uint8_t sel(void) { return RUSH->scr == RS_MENU ? RUSH->sel : RUSH->list_sel - RUSH->top; }   // the cursor's line in the window

static void build_menu(uint8_t k, uint8_t *r) {
    char b[20], *d;
    uint8_t all_ok = count_unlocked() >= 2;
    blank(r);
    if (k < 2) {
        put(r, MENU_COL, k ? "CHOOSE" : "ALL");
        if (!k && !all_ok) put(r, MENU_COL + 4, "LOCKED");
        return;
    }
    k -= 2;
    if (RUSH->sel) {                             // CHOOSE
        static const char *const ci[INFO_LINES] = { "ONE BOSS ALONE", "3 LIVES", "", "A PICK  B BACK" };
        put(r, 255, ci[k]);
        return;
    }
    if (!all_ok) {
        static const char *const li[INFO_LINES] = { "LOCKED", "BEAT 2 BOSSES IN", "STORY OR ARCADE", "B BACK" };
        put(r, 255, li[k]);
        return;
    }
    switch (k) {
    case 0: put(r, 255, "EVERY BOSS IN A ROW"); break;
    case 1:
        if (!all_score()) { put(r, 255, "NO BEST YET"); break; }
        d = cat(b, "BEST ");
        six(d, all_score());
        put(r, 255, b);
        break;
    case 2:
        if (!all_score()) break;
        d = num(b, RUSH->save[RSV_ALL_N]);
        d = cat(d, RUSH->save[RSV_ALL_N] == 1 ? " BOSS " : " BOSSES ");
        mmss(d, get16(RSV_ALL_TIME));
        put(r, 255, b);
        break;
    default: put(r, 255, "A PLAY  B BACK");
    }
}

static void build_list(uint8_t k, uint8_t *r) {
    char b[20];
    uint8_t v, n = n_lines();
    uint16_t f;
    blank(r);
    v = nth_built(k < n ? RUSH->top + k : RUSH->list_sel);
    if (v >= BOSS_COUNT) return;
    f = get16(RSV_BEST + 2 * v);
    if (k < n) {                                 // a line: the name and his best time
        if (!unlocked(v)) { put(r, COL_NAME, locked_name); return; }
        put(r, COL_NAME, boss_name[v]);
        if (f) { mmss(b, f); put(r, COL_BEST, b); }
        return;
    }
    k -= n;
    k += 2;                                      // (the list has no name or venue line: the cursor's line is his name)
    if (!unlocked(v)) { put(r, 255, locked_info[k]); return; }
    switch (k) {
    case 2:
        if (!f) { put(r, 255, "NOT BEATEN YET"); break; }
        mmss(cat(b, "BEST "), f);
        put(r, 255, b);
        break;
    default: put(r, 255, "A PLAY  B BACK");
    }
}

static void build(uint8_t k) {
    if (RUSH->scr == RS_MENU) build_menu(k, ROW(k)); else build_list(k, ROW(k));
}

static uint8_t screen_row(uint8_t k) {
    uint8_t n = n_lines();
    if (k >= n) return box_row() + 1 + k - n;
    return RUSH->scr == RS_MENU ? MENU_ROW0 + 2 * k : ROW_LIST + 2 * k;
}

static void cursor(void) {
    OAM_item_t *o = shadow_OAM;
    o->y = screen_row(sel()) * 8 - 7 + 16;       // the mug stands on the line (as the title's cursor)
    o->x = RUSH->scr == RS_MENU ? (MENU_COL - 1) * 8 + 8 : 8;
    o->tile = OBJ_MUG; o->prop = is_cgb ? OBJPAL_MUG_FULL : 0;
}

extern uint8_t frame_counter;
static void arrows(void) { list_arrows_show(RUSH->top != 0, RUSH->top + RVIS < lines(), frame_counter); }

static void lines_open(uint8_t scr) {            // LCD off: the menu or the list
    uint8_t k, n;
    frame_begin(scr);
    mug_cursor_load();                           // (a fight borrowed the mug's tiles and palettes)
    music_pump();
    n = n_lines() + info_n();
    for (k = 0; k < n; k++) {
        build(k);
        set_bkg_tiles(0, screen_row(k), 20, 1, ROW(k));
        if (!(k & 3)) music_pump();
    }
    cursor();
    if (RUSH->scr == RS_LIST) { music_pump(); list_arrows_load(); music_pump(); arrows(); }
    DISPLAY_ON;
}

static void menu_open(uint8_t s) { RUSH->sel = s; lines_open(RS_MENU); }

static void list_open(void) {
    if (RUSH->list_sel >= lines()) RUSH->list_sel = 0;
    RUSH->top = RUSH->list_sel >= RVIS ? RUSH->list_sel - RVIS + 1 : 0;   // (the window that shows the cursor)
    lines_open(RS_LIST);
}

// From the title's BONUS submenu: the menu (LCD off)
void rush_enter(void) BANKED {
    uint8_t v;
    rush_load(RUSH->save);
    RUSH->built = 0;
    RUSH->nlines = 0;
    for (v = 0; v < BOSS_COUNT; v++) if (scan_built(v)) { RUSH->built |= (uint16_t)1 << v; RUSH->nlines++; }
    RUSH->list_sel = 0;
    menu_open(0);
}

// The pause menu's QUIT TO MENU in a fight (src/pause.c): back to the menu, nothing recorded (no time, no best)
void rush_quit(void) BANKED {
    boss_set(BOSS_NONE);
    menu_open(0);
}

// ---- a run ------------------------------------------------------------------------------------------------------
static void run_reset(void) {
    uint8_t i;
    score = 0;
    for (i = 0; i < 6; i++) score_digits[i] = 0;
    lives = START_LIVES;
    RUSH->won = 0; RUSH->total_t = 0; RUSH->result = 0; RUSH->best = 0;
}

static void fight(void) {                        // the fight with RUSH->boss (LCD off from here: story.c)
    RUSH->scr = RS_FIGHT; RUSH->fight_t = 0;
    rush_fight(RUSH->boss);
}

static void next_card(void) {                    // ALL: before fight RUSH->won + 1 (LCD off)
    char b[22], *d;
    uint8_t v = RUSH->boss;
    frame_begin(RS_NEXT);
    d = cat(b, "FIGHT ");
    d = num(d, RUSH->won + 1);
    d = cat(d, " OF ");
    num(d, RUSH->n);
    line_at(3, 255, b);
    d = cat(b, "NEXT: ");
    cat(d, boss_name[v]);
    line_at(6, 255, b);
    line_at(8, 255, venue_name[v]);
    d = cat(b, "LIVES ");
    num(d, lives);
    line_at(ROW_BOX + 1, 255, b);
    six(cat(b, "SCORE "), score);
    line_at(ROW_BOX + 2, 255, b);
    mmss(cat(b, "TIME "), RUSH->total_t);
    line_at(ROW_BOX + 3, 255, b);
    line_at(ROW_BOX + 4, 255, "A GO");
    DISPLAY_ON;
}

static void run_start(uint8_t mode) {            // A on ALL (or RETRY): 3 lives, the score from 0, the first fight
    RUSH->mode = mode;
    run_reset();
    if (mode == RM_ALL) {
        RUSH->n = count_unlocked();
        RUSH->boss = next_unlocked(0);
        next_card();
    } else {
        RUSH->n = 1;
        RUSH->boss = nth_built(RUSH->list_sel);
        fight();
    }
}

static void result_show(void) {                  // LCD off: the run's result
    char b[22], *d;
    uint8_t all = RUSH->mode == RM_ALL;
    uint16_t f = all ? RUSH->total_t : RUSH->fight_t;
    frame_begin(RS_RESULT);
    line_at(3, 255, all ? (RUSH->result ? "ALL CLEAR" : "GAME OVER") : (RUSH->result ? "YOU WIN" : "YOU LOSE"));
    if (all) {
        d = num(b, RUSH->won);
        d = cat(d, " OF ");
        d = num(d, RUSH->n);
        cat(d, " BOSSES");
        line_at(5, 255, b);
    } else line_at(5, 255, boss_name[RUSH->boss]);
    mmss(cat(b, "TIME "), f);
    line_at(7, 255, b);
    six(cat(b, "SCORE "), score);
    line_at(9, 255, b);
    if (RUSH->best) line_at(ROW_BOX + 1, 255, "NEW BEST");
    else if (all && all_score()) { six(cat(b, "BEST "), all_score()); line_at(ROW_BOX + 1, 255, b); }
    else if (!all && get16(RSV_BEST + 2 * RUSH->boss)) {
        mmss(cat(b, "BEST "), get16(RSV_BEST + 2 * RUSH->boss));
        line_at(ROW_BOX + 1, 255, b);
    }
    line_at(ROW_BOX + 3, 255, "A RETRY  B BACK");
    DISPLAY_ON;
}

static void all_record(void) {                   // ALL is over: its best (the highest score), saved when it is one
    if (score <= all_score()) return;
    RUSH->save[RSV_ALL_SCORE] = (uint8_t)score; RUSH->save[RSV_ALL_SCORE + 1] = (uint8_t)(score >> 8);
    RUSH->save[RSV_ALL_SCORE + 2] = (uint8_t)(score >> 16);
    put16(RSV_ALL_TIME, RUSH->total_t);
    RUSH->save[RSV_ALL_N] = RUSH->won;
    RUSH->best = 1;
    rush_store(RUSH->save);
}

// story_level_done in MODE_RUSH (GS_LEVEL_CLEAR is over, LCD on): the fight was won
void rush_won(void) BANKED {
    uint8_t i = RSV_BEST + 2 * RUSH->boss;
    uint16_t f = RUSH->fight_t, b = get16(i);
    RUSH->won++;
    RUSH->total_t = (uint16_t)(T_MAX - RUSH->total_t) < f ? T_MAX : RUSH->total_t + f;
    if (!b || f < b) {                           // his fastest rush win (CHOOSE or a fight of ALL)
        put16(i, f);
        if (RUSH->mode == RM_CHOOSE) RUSH->best = 1;
        rush_store(RUSH->save);
    }
    if (RUSH->mode == RM_ALL) {
        RUSH->boss = next_unlocked(RUSH->boss + 1);
        if (RUSH->boss < BOSS_COUNT) {
            if (lives < START_LIVES) lives++;    // a won fight gives a life back (never above 3)
            next_card();
            return;
        }
        RUSH->result = 1;
        all_record();
        result_show();
        return;
    }
    RUSH->result = 1;
    result_show();
}

// story SP_FAIL in MODE_RUSH (GAME OVER over the frozen fight is over): out of lives
void rush_lost(void) BANKED {
    boss_set(BOSS_NONE);
    RUSH->total_t = (uint16_t)(T_MAX - RUSH->total_t) < RUSH->fight_t ? T_MAX : RUSH->total_t + RUSH->fight_t;
    RUSH->result = 0;
    if (RUSH->mode == RM_ALL) all_record();
    result_show();
}

// ---- frames -----------------------------------------------------------------------------------------------------
static uint8_t lines_frame(uint8_t pressed) {
    uint8_t n = n_lines(), s = RUSH->scr == RS_MENU ? RUSH->sel : RUSH->list_sel, old = s, k, q, top = RUSH->top, m = RUSH->scr == RS_MENU ? n : lines();
    if (pressed & J_UP) s = s ? s - 1 : m - 1;
    else if (pressed & J_DOWN) s = s == m - 1 ? 0 : s + 1;
    if (s != old) {
        if (RUSH->scr == RS_MENU) RUSH->sel = s;
        else {                                   // the list: the window slides when the cursor leaves it (a wrap: to the other end)
            RUSH->list_sel = s;
            if (s < top) top = s;
            else if (s >= top + RVIS) top = s - RVIS + 1;
            if (top != RUSH->top) { RUSH->top = top; RUSH->dirty |= (1 << n) - 1; }
        }
        RUSH->dirty |= (RUSH->scr == RS_LIST ? 1 : (1 << info_n()) - 1) << n;   // (the list: the best line; the keys line only when the lock changes)
        if (RUSH->scr == RS_LIST && unlocked(nth_built(s)) != unlocked(nth_built(old))) RUSH->dirty |= 2 << n;
    } else if (pressed & (J_A | J_START)) {
        if (RUSH->scr == RS_LIST) {
            if (unlocked(nth_built(s))) { run_start(RM_CHOOSE); return 1; }
        } else if (s) { list_open(); return 1; }
        else if (count_unlocked() >= 2) { run_start(RM_ALL); return 1; }
    } else if (pressed & J_B) {
        if (RUSH->scr == RS_LIST) { menu_open(1); return 1; }
        title_back = TM_BONUS; title_back_sel = 3;   // the BONUS submenu, the cursor on BOSS RUSH
        title_enter();
        return 1;
    }
    for (k = 0, q = 0; k < n + info_n() && q < ROWS_PER_FRAME; k++) {
        if (!(RUSH->dirty & (1 << k))) continue;
        RUSH->dirty &= ~(1 << k);
        build(k);
        vq_add(0, ROW(k), 0, screen_row(k), 20);
        q++;
    }
    cursor();
    if (RUSH->scr == RS_LIST) arrows();
    return 0;
}

// story_update, every frame of a rush screen (GS_STORY). 1: the screen changed.
uint8_t rush_update(uint8_t pressed) BANKED {
    if (RUSH->t != 255) RUSH->t++;
    switch (RUSH->scr) {
    case RS_MENU:
    case RS_LIST:
        return lines_frame(pressed);
    case RS_NEXT:
        if ((pressed & (J_A | J_START)) || RUSH->t >= NEXT_FRAMES) { fight(); return 1; }
        return 0;
    case RS_RESULT:
        if (pressed & (J_A | J_START)) { run_start(RUSH->mode); return 1; }
        if (pressed & J_B) {
            if (RUSH->mode == RM_ALL) menu_open(0); else list_open();
            return 1;
        }
        return 0;
    }
    return 0;
}
