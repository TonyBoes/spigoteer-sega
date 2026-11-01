// The title's BONUS > MINI GAMES (Practice, docs/minigames_bosses.md 2.3; owner 2026-10-11: BONUS's second item): the mini-games that are built, each playable
// once STORY or ARCADE has reached it (save.c's Practice block at SRAM 0x40), and the wood-wall look the full-screen lists share (list_frame below).
//
// Screen, in the one-line style of src/oneline.h (owner Q38-Q45; light HUD glyphs and the story font's punctuation on the wall):
//   row 0 "MINI GAMES" and the mode word at column 13   row 3 the selection line "< ORDER UP >" in the panel's band (rows 2-4)
//   rows 6-13, columns 1-10: the illustration frame (80 x 64 px)   right of it, from column 12: row 7 the counter "4 / 14", row 9 the best medal's icon, row 11 its
//   word (GOLD / SILVER / BRONZE / NO MEDAL), a blank row between   row 15 a panel line   row 16 "(A) PLAY (B) BACK"
// No instructions text: the HOW TO PLAY cards and the pause menu cover the controls.
// LEFT / RIGHT select the previous / next game (wrapping, hold-to-repeat). UP / DOWN jump between the two groups, the venues' games and the bonus rounds (DOWN
// to the first of the next group, UP to the first of this group, then of the one before). SELECT cycles the mode EASY / NORMAL / HARD (it applies to every game
// in the list and to the next one played; kept in ml_mode, so it outlasts a game and the title): the header names it, the medal shown is the selected game's
// best in that mode (save.c keeps a medal per game per mode: mg_best's bits 0-1 NORMAL, 2-3 HARD, 4-5 EASY, and the bonus rounds' "MD" block). A or START plays
// the selected game in MG_PRACTICE | the mode's bit (mg.h; score from 0; its result offers "A RETRY B MENU", and B comes back here: src/mg.c); a locked one
// does nothing. B goes back to the title's BONUS submenu with the cursor on MINI GAMES.
// A game not reached yet lists as "? ? ?" with LOCKED in place of the medal and no A on the hint row.
// The list: every built game, the ten venues' mini-games in chapter order and then the three old bonus rounds (CAN SHAKE-UP, PERFECT POUR, TIP SHOWER: owner
// 2026-10-14; ARCADE and CLASSIC play them, here they play in the framework, src/bonus.c bonus_practice). The DEBUG_MENU build (`make`) lists them all
// unlocked, the stub GREEN LIGHT included, so the owner can test; `make release` lists the thirteen (the stub is not in it) and applies the unlock rule: a
// venue's game once STORY or ARCADE reached it, a bonus round once ARCADE or CLASSIC played it (save.c "MGB1").
//
// THE ILLUSTRATION. The frame is the 10 x 8 tiles of ML_ART_*: the one-tile border (OL_T_BOX) and the 8 x 6 tile interior (a 64 x 48 px picture; art that draws
// its own border takes the full 80 x 64 px). A game's picture is one 80 x 64 px indexed PNG, assets/art/practice/<game>.png (see assets/art/practice/README.md:
// 4 colours, one CGB palette, the DMG shades by index, at most 80 unique tiles, aim 56), which tools/gen_practice_art.py turns into de-duplicated tiles, a map
// and a palette (build/practice_art.h and two banked data files). A game without a PNG shows the empty frame.
// The loader (the pa_ functions below) keeps tile buffers of 80 tiles: a DMG TWO (BG ids ML_ART_T..255, the ids reserved for the art, and ML_ART_T2..+79, free on this
// screen: the one-line tiles, the wall look and the story font take 0..92), a Color FOUR (the same two id ranges in VRAM bank 0 and in bank 1, which nothing here uses).
// One buffer is on screen. The selection's picture is streamed into another, PA_CHUNK tiles (80 B, one queue entry: the VBlank budget is 86) a frame whenever the copy
// queue is idle, and only when it is complete is it switched on: the map and, on a Color, the attributes (tile bank, and the palette slot 0 or 1 that the picture on
// screen does not use, loaded just before) of its rows go out three rows (a Color) or six (a DMG) a VBlank, each frame's batch in one drain, so what shows is always the
// old picture, the new one, or whole rows of each (a 2-3 frame wipe), never a half-loaded picture. While the screen idles the neighbours are prefetched: the one in the
// direction last pressed (a DMG: over the other neighbour if that is all it has; a Color: into a free buffer), then on a Color the other one too, so a Color steps either way
// with only the wipe and a DMG steps on the way it is walking. A press that moves on drops the unfinished stream and restarts on the new target; the picture on screen
// lags the name until its own stream is done (the name, counter and medal rows never wait). A game that is still locked shows the empty frame, like its name "? ? ?".
// The state (struct pa) and the 80-byte stream / map staging sit in story_scratch after ml_d (tests/test_scratch_map.py: "mglist.ART", "mglist.STAGE").
//
// LCD off to enter; afterwards the rows go through the VBlank queue from WRAM buffers (story_scratch: no cut-scene and no mini-game runs while this screen
// shows; mg_enter rewrites it).
#pragma bank 255
#include <gb/gb.h>
#include <stdint.h>

#include "game.h"
#include "music.h"
#include "story.h"
#include "mg.h"
#include "oneline.h"
#include "list_skin.h"          // static const uint8_t list_skin_tiles[]: the wood-wall look's seam, header edge and medal icons (assets/art/list_skin.txt)
#include <gb/cgb.h>
#include "palettes.h"
#include "scratch.h"            // SCR_OL_AT
#include "practice_art.h"       // build/practice_art.h (tools/gen_practice_art.py): PA_N, pa_ptr[], pa_bank(i)

#define RGB15(r, g, b) ((uint16_t)((r) | ((g) << 5) | ((b) << 10)))

extern uint8_t overlay_on, joy;

// chapter order (docs/story.md: saloon, stadium, lodge, bistro, igloo, robot factory, Chrome Cow, teahouse, zoo, space lounge), then the bonus rounds
#ifdef DEBUG_MENU
#define ML_N            14
static const uint8_t ml_game[ML_N] = { MG_QUICKDRAW, MG_TSHIRT, MG_LOGROLL, MG_ORDERUP, MG_MARSHMALLOW, MG_BATTERY, MG_MILKRUN, MG_TAIKO, MG_MONKEY, MG_ASTEROID,
                                       MG_SHAKEUP, MG_FILLLINE, MG_TIPS, MG_STUB };
#else
#define ML_N            13
static const uint8_t ml_game[ML_N] = { MG_QUICKDRAW, MG_TSHIRT, MG_LOGROLL, MG_ORDERUP, MG_MARSHMALLOW, MG_BATTERY, MG_MILKRUN, MG_TAIKO, MG_MONKEY, MG_ASTEROID,
                                       MG_SHAKEUP, MG_FILLLINE, MG_TIPS };
#endif
#define ML_GROUP        10      // the first bonus round's place in the list: UP / DOWN jump between 0 and this

// The screen's rows: row buffer k and the screen row it is drawn on
#define ML_K_NAME       0
#define ML_K_ART        1       // 1-8: the illustration frame's rows (screen rows 6-13), with the counter, the medal and its word right of it
#define ML_K_HINT       9
#define ML_K_HEAD       10
#define ML_ROWS         11
#define ML_ART_ROW      6
#define ML_ART_H        8       // tile rows of the frame
#define ML_ART_COL      1
#define ML_ART_W        10      // tile columns of the frame
#define ML_ART_T        176     // the illustration's tile ids (80) are 176-255 (nothing else of this screen uses them)
#define ML_COL_RIGHT    12      // the counter, the medal and its word
#define ML_COL_MODE     13      // the header's mode word ("MINI GAMES" is columns 1-10)
#define ML_ROW(k)       (story_scratch + (uint8_t)(k) * 20)
#define ml_d            (*(uint16_t *)(story_scratch + ML_ROWS * 20))   // bit k: row buffer k to redraw and send
// The illustration's loader (below): its state and its staging buffer follow ml_d in story_scratch
#define ML_ART_T2       96      // buffer B's tile ids (80): 96-175, free on this screen (ol_load's 4.., the generic tiles 36.., the story font ..92)
#define PA_CHUNK        5       // tiles a frame: 80 bytes + 3 (+ 2 into VRAM bank 1) of the VBlank queue's 86
#define PA_NONE         255
#define PA_EMPTY        254     // "the empty frame" as a picture to switch to
struct pa {
    uint8_t shown;              // the picture on screen (0..PA_N-1), or PA_EMPTY
    uint8_t sbuf;               // the buffer it is in (not streamed over)
    uint8_t held[4];            // the picture each buffer holds complete, or PA_NONE (a DMG uses two buffers, a Color four)
    uint8_t ld_pic, ld_n, ld_buf;   // the picture being streamed (PA_NONE: none), how many of its tiles are queued, and into which buffer
    uint8_t sw_pic, sw_row;     // the picture being switched on (PA_NONE: none) and how many of its rows are done
    uint8_t dir;                // 1: the last LEFT / RIGHT was LEFT (the prefetch looks that way first)
    uint8_t pslot;              // the CGB palette slot (0 or 1) of the picture on screen; the next one goes in the other
    uint8_t pal[8];             // the CGB palette on its way from the picture's bank
};
#define ML_PA_AT        (ML_ROWS * 20 + 2)
#define ML_STAGE_AT     (ML_PA_AT + 22)
#define PA              ((struct pa *)(story_scratch + ML_PA_AT))
#define PA_STAGE        (story_scratch + ML_STAGE_AT)
typedef char ml_scratch_fits[(ML_ROWS * 20 + 2 <= STORY_SCRATCH && ML_ART_W * ML_ART_H == 80 && ML_ART_T + 80 == 256 && sizeof(struct pa) <= 22
                              && ML_STAGE_AT + PA_CHUNK * 16 <= SCR_OL_AT && ML_ART_T2 + 80 <= ML_ART_T && PA_CHUNK * 16 + 3 + 2 <= VQ_DRAIN_BUDGET) ? 1 : -1];

uint8_t ml_sel;                 // the selected game (its place in the list)
uint8_t ml_n;                   // games listed (tests)
static uint8_t ml_mode;         // the mode (mg.h MG_D_*), kept across a game and the title

static const char locked_name[] = "? ? ?";
static const char *const medal_name[4] = { "NO MEDAL", "BRONZE", "SILVER", "GOLD" };

static const char *game_name(uint8_t g) {
    if (g == MG_QUICKDRAW) return "QUICK DRAW";
    if (g == MG_ORDERUP) return "ORDER UP";      // (no '!': the list has no tile for it)
    if (g == MG_BATTERY) return "BATTERY SORT";
    if (g == MG_MILKRUN) return "MILK RUN";
    if (g == MG_LOGROLL) return "LOG ROLL";
    if (g == MG_ASTEROID) return "ASTEROIDS";
    if (g == MG_TAIKO) return "TAIKO POUR";
    if (g == MG_MARSHMALLOW) return "MARSHMALLOWS";
    if (g == MG_MONKEY) return "MONKEY BUSINESS";
    if (g == MG_TSHIRT) return "SHIRT CANNON";
    if (g == MG_SHAKEUP) return "CAN SHAKE-UP";
    if (g == MG_FILLLINE) return "PERFECT POUR";
    if (g == MG_TIPS) return "TIP SHOWER";
#ifdef DEBUG_MENU
    return "GREEN LIGHT";
#else
    return "";
#endif
}

static uint8_t is_bonus(uint8_t g) { return g >= MG_SHAKEUP && g < MG_SHAKEUP + MG_BONUS_N; }

static uint8_t unlocked(uint8_t g) {
#ifdef DEBUG_MENU
    (void)g;
    return 1;
#else
    if (is_bonus(g)) return bonus_info(g - MG_SHAKEUP) & 1;     // (played in ARCADE or CLASSIC: save.c's own block)
    return g < MG_PLANNED && ((mg_unlocked >> g) & 1);
#endif
}

static const char *const diff_name[MG_DIFFS] = { "NORMAL", "HARD", "EASY" };   // (by MG_D_*)
static const uint8_t diff_ui[MG_DIFFS] = { 1, 2, 0 };      // MG_D_* -> its place in the cycle EASY, NORMAL, HARD
static const uint8_t ui_diff[MG_DIFFS] = { MG_D_EASY, MG_D_NORMAL, MG_D_HARD };

static uint8_t best(uint8_t g) {                  // g's best medal in the mode shown
    if (is_bonus(g)) return bonus_best(g - MG_SHAKEUP, ml_mode);
    return g < MG_PLANNED ? (mg_best[g] >> (ml_mode * 2)) & 3 : MEDAL_NONE;
}

// The 10 cells of row br (0-7) of the empty frame: the border, the blank inside
static void ml_frame_row(uint8_t *d, uint8_t br) {
    uint8_t m;
    d[0] = br == 0 ? OL_T_BOX : br == ML_ART_H - 1 ? OL_T_BOX + 5 : OL_T_BOX + 3;
    d[ML_ART_W - 1] = br == 0 ? OL_T_BOX + 2 : br == ML_ART_H - 1 ? OL_T_BOX + 7 : OL_T_BOX + 4;
    for (m = 1; m < ML_ART_W - 1; m++) d[m] = br == 0 ? OL_T_BOX + 1 : br == ML_ART_H - 1 ? OL_T_BOX + 6 : TILE_HUD_BLANK;
}

static void build(uint8_t k) {
    uint8_t *r = ML_ROW(k), g = ml_game[ml_sel], ok = unlocked(g), br;
    char buf[8];
    ol_blank(r);
    switch (k) {
    case ML_K_NAME: ol_arrows(r); ol_put(r, 255, ok ? game_name(g) : locked_name); return;
    case ML_K_HINT: ol_hint(r, ok ? OL_A_PLAY : OL_A_NONE); return;
    case ML_K_HEAD: ol_put(r, 1, "MINI GAMES"); ol_put(r, ML_COL_MODE, diff_name[ml_mode]); return;
    }
    br = k - ML_K_ART;                          // a row of the frame (0-7), and what stands right of it
    ml_frame_row(r + ML_ART_COL, br);           // (the empty frame: the picture's cells are not sent with these rows, see mg_list_update)
    if (br == 1) { ol_counter(buf, ml_sel + 1, ML_N); ol_put(r, ML_COL_RIGHT, buf); }
    if (br == 3 && ok && best(g)) r[ML_COL_RIGHT] = SKIN_TILE_MEDAL + best(g);     // (the icon: ids SKIN_TILE_MEDAL + MEDAL_BRONZE .. GOLD)
    if (br == 5) ol_put(r, ML_COL_RIGHT, ok ? medal_name[best(g)] : "LOCKED");
}

static uint8_t screen_row(uint8_t k) {
    switch (k) {
    case ML_K_NAME: return OL_ROW_BAND;
    case ML_K_HINT: return OL_ROW_HINT;
    case ML_K_HEAD: return 0;
    }
    return ML_ART_ROW + (k - ML_K_ART);
}

// ---- the illustration's loader (see THE ILLUSTRATION above). A picture p: blob pa_ptr[p] in bank pa_bank(p): [0] n tiles, [1..8] palette, [9..88] map, [89..] tiles ----
typedef struct { uint8_t n, bank; const uint8_t *src; uint8_t *dst; uint8_t pad[2]; } vq_entry_t;   // (render.c's list entry; boss.c queues tile runs the same way)
extern vq_entry_t vq[];

#define PA_MAP      9
#define PA_TILES    89

// Buffer k: a DMG has two (0: ids ML_ART_T.., 1: ids ML_ART_T2..), a Color four, the same two id ranges in each VRAM bank (k & 1: the bank, k >> 1: the id range;
// the range at 176 first, it needs no split at id 128). Its tiles are used by the map's cells with the attribute (bank << 3) | palette slot.
static uint8_t pa_nbuf(void) { return is_cgb ? 4 : 2; }
static uint8_t pa_id0(uint8_t k) { return (is_cgb ? k >> 1 : k) ? ML_ART_T2 : ML_ART_T; }
static uint8_t pa_vbk(uint8_t k) { return is_cgb ? k & 1 : 0; }

static uint8_t pa_of(uint8_t sel) {             // the picture the list line `sel` shows: PA_EMPTY for a locked game, one with no PNG and the stub
    return sel < PA_N && pa_ptr[sel] && unlocked(ml_game[sel]) ? sel : PA_EMPTY;
}

static uint8_t pa_find(uint8_t p) {             // the buffer that holds picture p whole, or 255
    uint8_t k;
    for (k = 0; k < pa_nbuf(); k++)
        if (PA->held[k] == p) return k;
    return 255;
}

// The buffer a stream may overwrite, or 255: never the one on screen; by what it holds, 0 nothing, 1 a picture the selection's neighbours do not need, 2 the
// neighbour behind the way last pressed, 3 the one ahead; only those up to `max`, the lowest first.
static uint8_t pa_victim(uint8_t max) {
    struct pa *a = PA;
    uint8_t k, h, sc, best = 255, bs = 255, f = pa_of(ol_wrap(ml_sel, ML_N, a->dir ? -1 : 1)), bk = pa_of(ol_wrap(ml_sel, ML_N, a->dir ? 1 : -1));
    for (k = 0; k < pa_nbuf(); k++) {
        if (a->shown != PA_EMPTY && k == a->sbuf) continue;
        h = a->held[k];
        sc = h == PA_NONE ? 0 : h == f ? 3 : h == bk ? 2 : 1;
        if (sc <= max && sc < bs) { bs = sc; best = k; }
    }
    return best;
}

// One run of picture p's tiles into buffer b: up to PA_CHUNK, never over the id 128 (the VRAM block changes there). Direct with the LCD off, else one queue entry
// (the staging buffer is read by the next VBlank; the caller waits for an idle queue). 1: the picture is complete.
static uint8_t pa_stream(uint8_t p, uint8_t b) {
    struct pa *a = PA;
    const uint8_t *src = pa_ptr[p];
    uint8_t bank = pa_bank(p), nt, c, id;
    uint16_t d;
    vq_entry_t *e;
    far_copy(&nt, src, 1, bank);
    id = pa_id0(b) + a->ld_n;
    c = nt - a->ld_n;
    if (c > PA_CHUNK) c = PA_CHUNK;
    if (id < 128 && (uint8_t)(id + c) > 128) c = 128 - id;
    far_copy(PA_STAGE, src + PA_TILES + (uint16_t)a->ld_n * 16, (uint16_t)c << 4, bank);
    if (LCDC_REG & LCDCF_ON) {
        d = (id < 128 ? 0x9000 : 0x8000) + ((uint16_t)id << 4);
        e = &vq[vq_count++];
        e->n = c << 4; e->bank = pa_vbk(b); e->src = PA_STAGE; e->dst = (uint8_t *)d;
        if (qv_cost <= VQ_DRAIN_BUDGET) qv_cost += (c << 4) + 3 + (e->bank << 1);
    } else {
        VBK_REG = pa_vbk(b);
        set_bkg_data(id, c, PA_STAGE);
        VBK_REG = VBK_BANK_0;
    }
    a->ld_n += c;
    return a->ld_n == nt;
}

// The map and attributes of the rows of picture p (PA_EMPTY: the empty frame) from sw_row on that fit one VBlank's drain: three on a Color (a tiles entry 13 and an
// attributes entry 15 each: 84 of 86), six on a DMG (13 each: 78). They all go in one list that nothing else shares (the caller saw an idle queue), so a drain
// shows the whole batch. LCD off (`now`): all eight rows straight in. A Color shows the picture in the palette slot the old one does not use (0 or 1), loaded
// before the first row goes; p is in buffer b.
static void pa_rows(uint8_t p, uint8_t b, uint8_t now) {
    struct pa *a = PA;
    uint8_t *s = PA_STAGE, r, n = now ? ML_ART_H : is_cgb ? 3 : 6, i, bank = p == PA_EMPTY ? 0 : pa_bank(p), stride = is_cgb && !now ? 20 : 10, av;
    av = p == PA_EMPTY ? SKIN_PAL_WALL : (pa_vbk(b) << 3) | (a->pslot ^ 1);
    if (!a->sw_row && is_cgb && p != PA_EMPTY) {
        far_copy(a->pal, pa_ptr[p] + 1, 8, bank);
        set_bkg_palette(a->pslot ^ 1, 1, (uint16_t *)a->pal);
    }
    for (; n && a->sw_row < ML_ART_H; n--, a->sw_row++, s += stride) {
        r = a->sw_row;
        if (p == PA_EMPTY) ml_frame_row(s, r);
        else {
            far_copy(s, pa_ptr[p] + PA_MAP + r * ML_ART_W, ML_ART_W, bank);
            for (i = 0; i < ML_ART_W; i++) s[i] += pa_id0(b);
        }
        if (now) {
            set_bkg_tiles(ML_ART_COL, ML_ART_ROW + r, ML_ART_W, 1, s);
            if (is_cgb) {
                for (i = 0; i < ML_ART_W; i++) s[i] = av;
                VBK_REG = VBK_BANK_1;
                set_bkg_tiles(ML_ART_COL, ML_ART_ROW + r, ML_ART_W, 1, s);
                VBK_REG = VBK_BANK_0;
            }
            continue;
        }
        vq_add(0, s, ML_ART_COL, ML_ART_ROW + r, ML_ART_W);
        if (is_cgb) {
            for (i = 10; i < 20; i++) s[i] = av;
            vq_add(1, s + 10, ML_ART_COL, ML_ART_ROW + r, ML_ART_W);
        }
    }
    if (a->sw_row == ML_ART_H) {                // done: p is what shows
        a->shown = p;
        if (p != PA_EMPTY) { a->sbuf = b; a->pslot ^= 1; }
        a->sw_pic = PA_NONE; a->sw_row = 0;
    }
}

// Entering (LCD off): the selection's picture goes straight into buffer 0 and onto the map.
static void pa_enter(void) {
    struct pa *a = PA;
    uint8_t p = pa_of(ml_sel), k;
    a->shown = PA_EMPTY; a->sbuf = 0; a->pslot = 1; a->ld_pic = a->sw_pic = PA_NONE; a->ld_n = a->sw_row = 0; a->dir = 0;
    for (k = 0; k < 4; k++) a->held[k] = PA_NONE;
    if (p == PA_EMPTY) return;                  // (the empty frame is on the map already)
    while (!pa_stream(p, 0)) music_pump();
    a->held[0] = p; a->ld_n = 0;
    music_pump();                               // (the last chunk returned without one)
    pa_rows(p, 0, 1);
    music_pump();
}

// Each frame, after the keys: the picture the selection wants goes on screen once it is in a buffer; else it is streamed into a buffer (any but the one on screen);
// else (idle) the neighbours are prefetched, the one in the direction last pressed first (a DMG only that one, over the other if need be; a Color the other too, into
// a buffer nothing needs). Only with an idle copy queue (the row rebuilds of a press go first, and the batch below has the list to itself).
static void pa_update(void) {
    struct pa *a = PA;
    uint8_t want, hb, load, max, b, f, bk;
    if (vq_count || vq_held) return;
    if (a->sw_pic != PA_NONE) { pa_rows(a->sw_pic, pa_find(a->sw_pic), 0); return; }
    want = pa_of(ml_sel);
    if (want != a->shown) {
        hb = pa_find(want);
        if (want == PA_EMPTY || hb != 255) {    // in a buffer already (the empty frame needs none): switch
            a->sw_pic = want; a->sw_row = 0;
            pa_rows(want, hb, 0);
            return;
        }
        load = want; max = 3;
    } else {
        f = pa_of(ol_wrap(ml_sel, ML_N, a->dir ? -1 : 1));
        bk = pa_of(ol_wrap(ml_sel, ML_N, a->dir ? 1 : -1));
        max = 2;
        if (f != PA_EMPTY && pa_find(f) == 255) load = f;
        else if (is_cgb && bk != PA_EMPTY && pa_find(bk) == 255) { load = bk; max = 1; }
        else return;
    }
    if (a->ld_pic != load) {                    // (a stream the selection has left is dropped where it is)
        b = pa_victim(max);
        if (b == 255) return;
        a->ld_pic = load; a->ld_n = 0; a->ld_buf = b; a->held[b] = PA_NONE;
    }
    if (pa_stream(load, a->ld_buf)) { a->held[a->ld_buf] = load; a->ld_pic = PA_NONE; a->ld_n = 0; }
}

// The wood-wall look of the full-screen lists (owner 2026-10-17: v1 of the tavern mock-ups without the shelves and the bottles). LCD off: loads the tiles over the
// stage ids and the CGB palettes 2-7, then all 18 rows: row 0 the header's text row (the caller writes its text over it), row 1 the band's edge (SKIN_TILE_EDGE),
// the wall with a board seam in the blank rows (`seams`: the odd rows 3.. above the panel, the seam shifting two tiles every other row), the panel's top line on
// `sep`, its info rows, its bottom line on 17. CGB: the header on a gold band with dark text (the text row's tiles have the letters on tile rows 1-7: with the
// edge row's first gold pixel row the text has 1 px of band above and below), the wall dark wood, the panel a darker reddish band. DMG: the wall stays the
// darkest shade (the letters' tiles have colour 3 for the ground), the edge row is two light lines under the header.
static const uint16_t skin_pal[6][4] = {
    { RGB15(31, 29, 22), RGB15(14, 9, 4), RGB15(3, 1, 1), RGB15(7, 3, 2) },       // SKIN_PAL_WALL: cream text, -, the seams' gap, the wall
    { RGB15(31, 25, 6), RGB15(26, 28, 30), RGB15(22, 12, 5), RGB15(7, 3, 2) },    // SKIN_PAL_MEDAL: gold, silver, bronze, the wall
    { RGB15(31, 23, 6), RGB15(24, 17, 4), RGB15(18, 12, 3), RGB15(11, 4, 3) },    // SKIN_PAL_BTN: the buttons' golds on the panel
    { RGB15(5, 2, 1), RGB15(5, 2, 1), RGB15(5, 2, 1), RGB15(30, 24, 10) },        // SKIN_PAL_HEAD: dark text on the gold band
    { RGB15(31, 29, 22), RGB15(24, 18, 8), RGB15(15, 9, 4), RGB15(11, 4, 3) },    // SKIN_PAL_FOOT: cream text, the panel's lines, the panel
    { RGB15(30, 24, 10), RGB15(15, 9, 2), RGB15(0, 0, 0), RGB15(7, 3, 2) },       // SKIN_PAL_EDGE: the band's last gold row, its shadow, the wall
};

void list_skin_load(void) BANKED {            // the tiles and palettes alone (LCD off; the debug menu's window map uses them too, src/debug.c)
    set_bkg_data(0, 4, list_skin_tiles);
    if (is_cgb) set_bkg_palette(SKIN_PAL_WALL, 6, (uint16_t *)skin_pal);
}

void list_frame(uint8_t sep) BANKED {
    uint8_t y, x;
    list_skin_load();
    music_pump();
    for (y = 0; y < 18; y++) {
        for (x = 0; x < 20; x++)
            row_buf[x] = y == 1 ? SKIN_TILE_EDGE : y == sep ? TILE_PANEL_TOP : y == 17 ? TILE_PANEL_BOT
                       : TILE_HUD_BLANK;
        set_bkg_tiles(0, y, 20, 1, row_buf);
        if (is_cgb) {
            for (x = 0; x < 20; x++) row_buf[x] = y == 0 ? SKIN_PAL_HEAD : y == 1 ? SKIN_PAL_EDGE : y >= sep ? SKIN_PAL_FOOT : SKIN_PAL_WALL;
            VBK_REG = VBK_BANK_1;
            set_bkg_tiles(0, y, 20, 1, row_buf);
            VBK_REG = VBK_BANK_0;
        }
        if (!(y & 1)) music_pump();
    }
}


void mg_list_enter(void) BANKED {
    uint8_t y;
    TRANS_MENU();                               // (src/trans.c: the quick white fade, from the title's BONUS and back from a game)
    DISPLAY_OFF;
    music_pump();                               // (the tick this pass is due: the rebuild runs several frames)
    overlay_on = 0; HIDE_WIN; vq_reset(); hud_dirty = 0; vram_pending = 0;
    hide_all_sprites();
    story_on = 0;                               // (Practice is never a story)
    music_play(TUNE_TITLE);                     // (left alone when it already plays: from the title; after a game its patterns are
    music_load_now_p();                         // copied back now, and the pumps below tick it through the rebuild)
    music_pump();
    story_font_load();                          // the punctuation (over the title's lettering: title_enter reloads it)
    ol_load();
    music_pump();
    if (ml_sel >= ML_N) ml_sel = 0;
    ml_n = ML_N; ml_d = 0;
    list_frame(OL_SEP);                         // (the wood wall: tiles, palettes, the header band, the panel)
    ol_band(SKIN_PAL_BTN);
    for (y = 0; y < ML_ROWS; y++) {
        build(y);
        set_bkg_tiles(0, screen_row(y), 20, 1, ML_ROW(y));
        if (!(y & 3)) music_pump();
    }
    pa_enter();                                 // (the selection's picture, if it has one)
    if (is_cgb) {                               // the medal icon's palette
        row_buf[0] = SKIN_PAL_MEDAL;
        VBK_REG = VBK_BANK_1;
        set_bkg_tiles(ML_COL_RIGHT, screen_row(ML_K_ART + 3), 1, 1, row_buf);
        VBK_REG = VBK_BANK_0;
    }
    game_state = GS_MGLIST;
    if (!(TMA_REG & 2)) while (TIMA_REG > DS_SCALE(23)) music_pump();   // (as trans.c tick_sync: the LCD comes on just after a tick; the picture's load moved the phase. Not NR51: a silent tune ticks too, and the list is never under the pause menu)
    DISPLAY_ON;
}

// One frame. 1: the screen changed (a game started, or B went back to the title).
uint8_t mg_list_update(uint8_t pressed) BANKED {
    uint8_t old = ml_sel, k, n, key = ol_key(pressed, joy), g;
    if (key == J_LEFT) { ml_sel = ol_wrap(ml_sel, ML_N, -1); PA->dir = 1; }
    else if (key == J_RIGHT) { ml_sel = ol_wrap(ml_sel, ML_N, 1); PA->dir = 0; }
    else if (key == J_DOWN) ml_sel = ml_sel >= ML_GROUP ? 0 : ML_GROUP;                       // the next group's first game
    else if (key == J_UP) ml_sel = ml_sel > ML_GROUP ? ML_GROUP : ml_sel > 0 ? 0 : ML_GROUP;  // this group's first game, then the one before
    if (ol_tick()) ml_d |= 1 << ML_K_NAME;
    if (ml_sel != old) {
        ml_d |= (1 << ML_K_NAME) | (1 << (ML_K_ART + 1)) | (1 << (ML_K_ART + 3)) | (1 << (ML_K_ART + 5));   // name, counter, medal icon and word
        g = ml_game[old]; n = ml_game[ml_sel];
        if (unlocked(g) != unlocked(n)) ml_d |= 1 << ML_K_HINT;
    }
    if (pressed & J_SELECT) {                   // the mode: EASY, NORMAL, HARD, round
        k = diff_ui[ml_mode];
        k = k == MG_DIFFS - 1 ? 0 : k + 1;
        ml_mode = ui_diff[k];
        ml_d |= (1 << ML_K_HEAD) | (1 << (ML_K_ART + 3)) | (1 << (ML_K_ART + 5));
    }
    if (pressed & (J_A | J_START)) {
        g = ml_game[ml_sel];
        if (unlocked(g)) { mg_enter(g, MG_PRACTICE | (ml_mode << 1)); return 1; }
    } else if (pressed & J_B) {
        title_back = TM_BONUS; title_back_sel = 2;   // the BONUS submenu, the cursor on MINI GAMES
        title_enter();
        return 1;
    }
    for (k = 0, n = 0; ml_d && k < ML_ROWS && n < 2; k++) {   // two rows a frame (a row's build is ~15k cycles)
        if (!(ml_d & ((uint16_t)1 << k))) continue;
        ml_d &= ~((uint16_t)1 << k);
        build(k);
        if (k >= ML_K_ART && k < ML_K_ART + ML_ART_H)    // (a row of the frame: only what is right of the picture, whose cells are the loader's)
            vq_add(0, ML_ROW(k) + ML_COL_RIGHT - 1, ML_COL_RIGHT - 1, screen_row(k), 20 - (ML_COL_RIGHT - 1));
        else vq_add(0, ML_ROW(k), 0, screen_row(k), 20);
        n++;
    }
    pa_update();
    return 0;
}
