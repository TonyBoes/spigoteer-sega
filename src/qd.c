// QUICK DRAW, the saloon's mini-game (docs/minigames_bosses.md 4.1; art approved by the owner 2026-10-11, look B of
// the Sarsaparilla Kid; the soda duel approved 2026-10-11). The Kid challenges the Spigoteer; both shake a bottle of
// soda while they wait. A DRAW! sign flips up with a bell: press the button its badge shows before the Kid draws, and
// the winner sprays the loser. First to three rounds.
//
// Rules (the spec's numbers):
// - A round: "ROUND n" / "WAIT FOR THE SIGN" for QD_READY_LEN frames and on through the wait (nothing reads as a countdown), a wait W = 90 + 0..210 frames, then DRAW!.
// - The badge: rounds 1-2 always A, rounds 3-5 A or B at random. Only a fresh press counts (`pressed`: a button held
//   through the sign is not one).
// - The Kid draws R frames after DRAW! (rounds 1-5: 34 30 30 28 26). The player's right button on frame t <= R after
//   DRAW! wins the round (a tie at t == R is his); no press by R: the Kid's ("TOO SLOW"). A or B during the wait, or the
//   wrong button after DRAW!: FOUL, the Kid's round. (A press during the first QD_READY_LEN frames, before the wait, is ignored: it is the
//   pause between rounds.)
// - Feints from round 3: once during the wait, never in its last QD_FEINT_GAP frames, a tumbleweed rolls across the
//   floor (SFX_SHAKE) or a crow lands on the sign and caws (SFX_LAUNCH); QD_FEINT_LEN frames each.
// - The soda duel (poses()): through the banner (READY and the wait) both shake their bottles, out of step (the Kid
//   every 4 frames, the Spigoteer every 5); at DRAW! both freeze. After a round, QD_SHOW_LEN frames: the winner (the
//   Kid on TOO SLOW) takes his DRAW pose with a level, uncorked bottle and sprays a stream of BG tiles along the wall's
//   row STREAM_ROW (3 columns a frame from frame 1, flowing, cut off from his end from frame STREAM_CUT, the wall put
//   back from the copy taken at entry by frame 40); the loser holds his bottle as ever, SPLASH over his head from
//   frame WET_AT, then drips. A FOUL fizzes over the player's own bottle (FIZZ, the FOAM column, SPLASH, drips) while
//   the Kid stands. The pips, and "YOU 0.32" (the reaction in seconds, '.' the story font's) / "FOUL" / "TOO SLOW".
//   The match's end: YOU WIN, the Spigoteer aiming (no stream), the Kid dripping; THE KID WINS, the Kid's cheer, the
//   Spigoteer dripping.
// - Score: 500 a round won + (R - t) x 20; the match won +2000. Medal (qd_medal, not a score threshold): GOLD 3-0,
//   SILVER won 3-1 / 3-2, BRONZE lost with a round won, else none. One setting for story and practice (no HARD).
// - Sounds: the DRAW! bell SFX_CATCH, a round won SFX_SERVE, a foul SFX_BREAK, too slow SFX_LIFE.
//
// Screen (the approved mock-up): the framework's saloon backdrop (counter row 11); the sign's frame at columns 3-16,
// rows 6-9 (CGB BG palette 2; badge B's cells palette 3, a blue disc; DMG: B is the inverted, light-disc tiles), its letter rows 7-8 the planks while waiting, "DRAW!" + the badge on the sign; the pips
// on row 12 (the Kid's columns 2-4, the player's 15-17, BG palette 0: the saloon bar's); the Kid (16x24, OBJ palettes 3
// top, 4 body; DMG OBP1) at x 20 and the Spigoteer (his duel poses, OBJ palette 0) at x 124, both y 112; the bottles,
// the wet overlay and the foam (OBJ palette 1, the saloon's full drink; DMG OBP0), the feints (OBJ palette 6; DMG
// OBP1); the stream in the wall's own BG palette.
// OAM in draw priority (OAM_*): 0-1 the wet overlay, 2 the foam, 3-4 the bottles in hand, 5-6 the aimed bottle, 7-10
// the Spigoteer (mg_spigoteer from slot 7), 11-14 the Kid, 15-16 tumbleweed, 17 crow. Worst line 9 (the spray's row:
// 2 a man, 2 the aimed bottle, 1 the loser's bottle, 2 the wet overlay); 8 during a tumbleweed.
// Tiles: BG QD_BG.. (MG_GAME_BG: 43, ids 125-167), OBJ 56-79 (the Spigoteer's 2 poses as bartender frames 7-8, the
// tumbleweed), 96-119 (the Kid's 3 frames), 168-210 (the crow, the soda duel: 34 OBJ tiles and the stream's 5 BG tiles): 111.
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"
#include "music.h"
#include "mg.h"
#include "qd_art.h"         // this bank's own art (assets/art/quickdraw/*.txt)

#define S               (MG->qd)
#define QD_BG           MG_GAME_BG
// OBJ tiles in three runs, all where the next level load puts the game's own back (load_venue: the drink frames
// and the show; the patron ids 78..): the coin (OBJ_COIN 92-95) is loaded once at boot, so it is left alone.
#define QD_OBJ          OBJ_MUG             // 56..87: the Spigoteer's duel poses (bartender frames 7-9), tumbleweed
#define QD_KID          OBJ_DANCER          // 96..127: the Kid
#define QD_CROW        (QD_BG + QD_BG_TILES)   // 164..167: the crow (OBJ = BG ids 128+: past the sign's BG tiles)
#define QD_SODA        (QD_CROW + QDO_CROW_N)  // 168..210: the soda duel; its stream tiles are BG ids (QDS_STREAM..)
typedef char qd_obj_fits[(QD_OBJ + QDO_RUN_A <= OBJ_COIN && QD_OBJ == 7 * BARTENDER_TILES_PER_FRAME
                          && QDO_KID_N <= DANCER_TILE_COUNT && QD_CROW + QDO_RUN_C <= OBJ_POUR) ? 1 : -1];
#define QD_ROUNDS       5
#define QD_TO_WIN       3
#define QD_READY_LEN    60
#define QD_WAIT_MIN     90
#define QD_WAIT_SPAN   211                  // W = QD_WAIT_MIN + 0..210
#define QD_SHOW_LEN     60
#define QD_FEINT_FROM   3                   // feints from this round
#define QD_FEINT_LEN    48
#define QD_FEINT_GAP    30                  // never in the last 30 frames before DRAW!
#define QD_ROUND_PTS   500
#define QD_SPEED_PTS    20                  // per frame under R
#define QD_MATCH_PTS  2000
#define SIGN_COL        3                   // the sign: columns 3-16, rows 6-9; letters on rows 7-8, columns 4-15
#define SIGN_ROW        6
#define SIGN_W         14
#define LET_COL         4
#define SIGN_PAL        BGPAL_PATRON        // CGB BG palette 2 (a game's own)
#define BADGE_B_PAL     (BGPAL_PATRON + 1)  // CGB BG palette 3 (also a game's own): badge B's blue disc
#define PIP_ROW        12
#define PIP_KID_COL     2
#define PIP_YOU_COL    15
#define KID_X          20
#define SPIG_X        124
#define DUEL_Y        112
#define TW_Y          120
#define CROW_X        100
#define CROW_Y         32                   // perched on the sign's top edge (screen y)
#define PAL_KID_TOP     3
#define PAL_KID_BODY    4
#define PAL_BOTTLE      OBJPAL_MUG_FULL     // 1
#define PAL_FEINT       6
// OAM in draw priority (CGB: the lower slot wins; DMG: the smaller x, then the lower slot, and the overlays share x
// with the bodies): the wet overlay and the foam over everything, the bottles in hand and the aimed bottle over the
// bodies, then the duelists, then the feints
#define OAM_WET         0                   // 0-1: the wet overlay (16x16)
#define OAM_FOAM        2                   // the foul's foam column
#define OAM_HAND_YOU    3                   // the bottle in the Spigoteer's fist
#define OAM_HAND_KID    4                   // the bottle in the Kid's fist
#define OAM_AIM         5                   // 5-6: the winner's aimed bottle (16x16)
#define OAM_SPIG        7                   // 7-10: the Spigoteer (mg_spigoteer)
#define OAM_KID        11                   // 11-14: the Kid
#define OAM_TW         15                   // 15-16: the tumbleweed
#define OAM_CROW       17
#define OAM_N          18
#define STREAM_ROW     15                   // the wall's tile row (y 120-127) the stream is written into
#define STREAM_N       10                   // its columns: 6..15 from the Kid, 13..4 from the Spigoteer
#define STREAM_STEP     3                   // columns a frame, growing and cut off
#define STREAM_CUT     36                   // the round-end frame its cut-off starts on (restored by frame 40)
#define WET_AT          4                   // the round-end frame the stream reaches the loser: SPLASH
#define DRIP_AT        38                   // DRIP A / B from here, alternating every 8 frames
#define FOUL_FIZZ      24                   // the foul: FIZZ frames 0-23, FOAM 2-17, SPLASH 6-23, then DRIP
#define FOUL_FOAM_AT    2
#define FOUL_FOAM_END  18
#define FOUL_WET_AT     6
enum { QS_NEXT, QS_READY, QS_WAIT, QS_DRAW, QS_SHOW, QS_OVER };
enum { QR_NONE, QR_YOU, QR_SLOW, QR_FOUL, QR_WRONG };
enum { QF_NONE, QF_TUMBLE, QF_CROW };
enum { KID_STAND, KID_DRAW, KID_CHEER };
#define SPIG_STAND      7                   // mg_spigoteer frames: the duel poses at OBJ 56, 64
#define SPIG_DRAW       8
enum { B_STILL, B_UP, B_DOWN, B_FIZZ, B_FOAM };   // the bottle in a fist (shake_bottle.txt)
enum { W_SPLASH, W_DRIP_A, W_DRIP_B };            // the wet overlay (wet.txt)
enum { WHO_KID, WHO_YOU };
enum { ST_MID_A, ST_MID_B, ST_HEAD_R, ST_HEAD_L, ST_RISE_R };   // the stream's BG tiles (stream.txt)

static const uint8_t kid_r[QD_ROUNDS] = { 34, 30, 30, 28, 26 };

static uint16_t rand16(void) {
    uint16_t v = mg_rand();
    return (v << 8) | mg_rand();
}

static void qd_put(uint8_t col, uint8_t row, uint8_t *t, uint8_t n) {
    if (LCDC_REG & LCDCF_ON) vq_add(0, t, col, row, n); else vram_put(col, row, t, n);
}

// CGB: the badge's four cells take palette 2 (A, the planks) or 3 (B: a blue disc), in bank 1 beside the tiles. B's go
// in the frame after the sign's (the DRAW! frame's VBlank list is already as long as it can be)
static void badge_pal(uint8_t b) {
    if (!is_cgb || !(LCDC_REG & LCDCF_ON)) return;       // (at entry the LCD is off and fill_attr has set palette 2)
    S.attr[0] = S.attr[1] = b ? BADGE_B_PAL : SIGN_PAL;   // (WRAM: the queue is read in VBlank)
    vq_add(1, S.attr, LET_COL + 10, SIGN_ROW + 1, 2);
    vq_add(1, S.attr, LET_COL + 10, SIGN_ROW + 2, 2);
}

// the sign's letter rows: the planks (waiting), or DRAW! with the badge
static void sign(uint8_t face) {
    uint8_t c, k, *a = S.sign[0], *b = S.sign[1];
    for (c = 0; c < 12; c++) a[c] = b[c] = (uint8_t)(QD_BG + QDB_BACK);
    if (face) {
        for (k = 0; k < 4; k++) {               // D R A W: 2x2 each
            c = QD_BG + QDB_LETTERS + 4 * k;
            a[2 * k] = c; a[2 * k + 1] = c + 1; b[2 * k] = c + 2; b[2 * k + 1] = c + 3;
        }
        a[8] = (uint8_t)(QD_BG + QDB_BANG); b[8] = (uint8_t)(QD_BG + QDB_BANG + 1);
        a[9] = b[9] = (uint8_t)(QD_BG + QDB_FACE);
        c = QD_BG + (S.badge ? (is_cgb ? QDB_BADGE + 4 : QDB_BADGE_DMG) : QDB_BADGE);   // B: blue (CGB) / light (DMG)
        a[10] = c; a[11] = c + 1; b[10] = c + 2; b[11] = c + 3;
    }
    qd_put(LET_COL, SIGN_ROW + 1, a, 12);
    qd_put(LET_COL, SIGN_ROW + 2, b, 12);
}

static void pips(void) {                        // the Kid's rounds (left), the player's (right)
    uint8_t k, *p = S.pips;
    for (k = 0; k < 3; k++) {
        p[k] = QD_BG + (k < S.wins[1] ? QDB_PIP_ON : QDB_PIP_OFF);
        p[3 + k] = QD_BG + (k < S.wins[0] ? QDB_PIP_ON : QDB_PIP_OFF);
    }
    qd_put(PIP_KID_COL, PIP_ROW, p, 3);
    qd_put(PIP_YOU_COL, PIP_ROW, p + 3, 3);
}

static void fill_attr(uint8_t col, uint8_t row, uint8_t w, uint8_t h, uint8_t pal) {   // LCD off, CGB
    uint8_t k;
    for (k = 0; k < 20; k++) row_buf[k] = pal;
    VBK_REG = VBK_BANK_1;
    while (h--) vram_put(col, row++, row_buf, w);
    VBK_REG = VBK_BANK_0;
}

// LCD off, after the framework's screen
void qd_enter(void) BANKED {
    uint16_t p[4];
    uint8_t k;
    set_bkg_data(QD_BG, QD_BG_TILES, qd_bg_tiles);
    set_sprite_data(QD_OBJ, QDO_RUN_A, qd_obj_tiles);
    set_sprite_data(QD_KID, QDO_KID_N, qd_obj_tiles + QDO_KID * 16);
    set_sprite_data((uint8_t)QD_CROW, QDO_RUN_C, qd_obj_tiles + QDO_CROW * 16);   // the crow, the soda duel (and its stream)
    if (is_cgb) {
        p[0] = RGB8(248, 240, 208); p[1] = RGB8(216, 168, 96); p[2] = RGB8(216, 40, 24); p[3] = RGB8(48, 16, 8);
        set_bkg_palette(SIGN_PAL, 1, p);         // the sign: cream face, tan wood, red letters, dark
        p[1] = p[0]; p[2] = RGB8(72, 128, 248); p[3] = RGB8(24, 56, 176);
        set_bkg_palette(BADGE_B_PAL, 1, p);      // badge B: a blue disc (tile colour 3, dark blue) with a cream letter (colour 1)
        p[0] = 0;
        p[1] = RGB8(248, 200, 152); p[2] = RGB8(248, 160, 32); p[3] = RGB8(24, 16, 32);
        set_sprite_palette(PAL_KID_TOP, 1, p);   // the Kid's hat and face: skin, orange, dark
        p[2] = RGB8(56, 168, 80);
        set_sprite_palette(PAL_KID_BODY, 1, p);  // his serape and legs: skin, green, dark
        p[1] = RGB8(240, 216, 144); p[2] = RGB8(176, 120, 56); p[3] = RGB8(40, 24, 8);
        set_sprite_palette(PAL_FEINT, 1, p);     // tumbleweed, crow: tan, brown, dark
        fill_attr(SIGN_COL, SIGN_ROW, SIGN_W, 4, SIGN_PAL);
        fill_attr(PIP_KID_COL, PIP_ROW, 3, 1, BGPAL_BAR);
        fill_attr(PIP_YOU_COL, PIP_ROW, 3, 1, BGPAL_BAR);
    } else OBP1_REG = OBP1_PLAY;                 // the Kid and the feints (OBP1 0xE4; the title leaves 0xC4)
    // the frame: TL T.. TR / L .. R / BL B.. BR
    for (k = 0; k < SIGN_W; k++) { S.sign[0][k] = (uint8_t)(QD_BG + QDB_FRAME + 1); S.sign[1][k] = (uint8_t)(QD_BG + QDB_FRAME + 6); }
    S.sign[0][0] = QD_BG + QDB_FRAME; S.sign[0][SIGN_W - 1] = QD_BG + QDB_FRAME + 2;
    S.sign[1][0] = (uint8_t)(QD_BG + QDB_FRAME + 5); S.sign[1][SIGN_W - 1] = (uint8_t)(QD_BG + QDB_FRAME + 7);
    vram_put(SIGN_COL, SIGN_ROW, S.sign[0], SIGN_W);
    vram_put(SIGN_COL, SIGN_ROW + 3, S.sign[1], SIGN_W);
    S.sign[0][0] = (uint8_t)(QD_BG + QDB_FRAME + 3); S.sign[0][1] = (uint8_t)(QD_BG + QDB_FRAME + 4);
    vram_put(SIGN_COL, SIGN_ROW + 1, S.sign[0], 1); vram_put(SIGN_COL + SIGN_W - 1, SIGN_ROW + 1, S.sign[0] + 1, 1);
    vram_put(SIGN_COL, SIGN_ROW + 2, S.sign[0], 1); vram_put(SIGN_COL + SIGN_W - 1, SIGN_ROW + 2, S.sign[0] + 1, 1);
    S.st = QS_NEXT; S.round = 0; S.wins[0] = S.wins[1] = 0; S.wait = 0; S.badge = 0; S.r = 0; S.t = 0;
    S.res = QR_NONE; S.react = 0; S.feint = QF_NONE; S.feint_at = 0; S.feint_t = 0; S.fx = 0;
    S.anim = 0;
    for (k = 0; k < 20; k++)                     // the wall under the stream, put back after each spray (LCD off)
        S.wall[k] = S.row[k] = ((uint8_t *)0x9800)[STREAM_ROW * 32 + k];
    sign(0);
    pips();
    qd_update(0);                                // the duelists (the update draws them; no play before MG_PLAY)
}

uint8_t qd_medal(void) BANKED {
    if (S.wins[0] >= QD_TO_WIN) return S.wins[1] ? MEDAL_SILVER : MEDAL_GOLD;
    return S.wins[0] ? MEDAL_BRONZE : MEDAL_NONE;
}

// "3 TO 1" (a, b) into S.txt
static void score_line(uint8_t a, uint8_t b) {
    char *d = S.txt;
    *d++ = '0' + a; *d++ = ' '; *d++ = 'T'; *d++ = 'O'; *d++ = ' '; *d++ = '0' + b; *d = 0;
}

static void end_round(uint8_t res) {
    uint8_t h, *b;
    S.res = res; S.st = QS_SHOW; S.t = 0;
    S.feint_t = QD_FEINT_LEN;                    // (a feint still on goes)
    if (res == QR_YOU) {
        S.wins[0]++;
        mg_points(QD_ROUND_PTS + (uint16_t)(S.r - S.react) * QD_SPEED_PTS);
        h = (uint8_t)(((uint16_t)S.react * 100 + 30) / 60);   // hundredths of a second
        S.txt[0] = 'Y'; S.txt[1] = 'O'; S.txt[2] = 'U'; S.txt[3] = ' '; S.txt[4] = '0'; S.txt[5] = ' ';
        S.txt[6] = '0' + h / 10; S.txt[7] = '0' + h % 10; S.txt[8] = 0;
        b = mg_say(MG_TEXT_B, S.txt);
        b[(20 - 8) / 2 + 5] = (uint8_t)(QD_BG + QDB_PERIOD);   // the '.' (queued: patched before the VBlank copies it)
        SFX(SFX_SERVE);
    } else {
        S.wins[1]++;
        if (res == QR_SLOW) { mg_say(MG_TEXT_B, "TOO SLOW"); SFX(SFX_LIFE); }
        else { mg_say(MG_TEXT_B, "FOUL"); SFX(SFX_BREAK); }
    }
    pips();
}

static void kid_obj(uint8_t f) {             // (KID_STAND: the shake body, his bottle in his fist)
    OAM_item_t *o = shadow_OAM + OAM_KID;
    uint8_t t = QD_KID + f * 8, y = (uint8_t)(DUEL_Y + 16), x = (uint8_t)(KID_X + 8), pt, pb;
    pt = is_cgb ? PAL_KID_TOP : S_PALETTE; pb = is_cgb ? PAL_KID_BODY : S_PALETTE;
    o->y = y;      o->x = x;     o->tile = t;     o->prop = pt; o++;
    o->y = y;      o->x = x + 8; o->tile = t + 2; o->prop = pt; o++;
    o->y = y + 16; o->x = x;     o->tile = t + 4; o->prop = pb; o++;
    o->y = y + 16; o->x = x + 8; o->tile = f == KID_STAND ? QD_SODA + QDS_KID_BR : t + 6; o->prop = pb;
}

static void feint_obj(void) {
    OAM_item_t *o = shadow_OAM + OAM_TW;
    uint8_t ft = S.feint_t, pal = is_cgb ? PAL_FEINT : S_PALETTE, t, y;
    o[0].y = o[1].y = o[2].y = 0;
    if (S.st != QS_WAIT || ft >= QD_FEINT_LEN || S.wait > S.feint_at) return;
    if (S.feint == QF_TUMBLE) {                  // rolls left to right, 4 px a frame
        S.fx = ft << 2;
        t = QD_OBJ + QDO_TW + (((ft / 3) & 1) << 2);
        o[0].y = o[1].y = (uint8_t)(TW_Y + 16);
        o[0].x = S.fx; o[1].x = S.fx + 8;
        o[0].tile = t; o[1].tile = t + 2;
        o[0].prop = o[1].prop = pal;
    } else if (S.feint == QF_CROW) {             // drops in, perches, caws, perches, flies off (12 frames each)
        y = CROW_Y + 16;
        if (ft < 12) y = ft << 2;
        else if (ft >= 36) y = CROW_Y + 16 - ((ft - 35) << 2);
        S.fx = CROW_X + 8;
        o[2].y = y; o[2].x = S.fx;
        o[2].tile = QD_CROW + (ft >= 24 && ft < 36 ? 2 : 0);
        o[2].prop = pal;
    }
}

// ---- the soda duel (approved 2026-10-11): both shake their bottles through the banner, freeze at DRAW!, the round's
// winner sprays the loser across the wall, the loser drips; a foul fizzes over the player's own bottle ----
// A piece drawn for the Kid (facing right; the Spigoteer's is X-flipped): 8x16, or 16x16 (wide: this slot and the next).
static void piece(uint8_t oam, uint8_t t, uint8_t x, uint8_t y, uint8_t who, uint8_t wide) {
    OAM_item_t *o = shadow_OAM + oam;
    uint8_t prop = (is_cgb ? PAL_BOTTLE : 0) | (who == WHO_YOU ? S_FLIPX : 0);
    x += 8; y += 16;
    o->y = y; o->tile = t; o->prop = prop; o->x = x;
    if (!wide) return;
    o[1].y = y; o[1].tile = t + 2; o[1].prop = prop; o[1].x = x + 8;
    if (who == WHO_YOU) { o->x = x + 8; o[1].x = x; }
}

static void hand(uint8_t who, uint8_t f, int8_t dy) {   // the bottle in his fist, frame f, dy px of shake
    if (who == WHO_YOU) piece(OAM_HAND_YOU, QD_SODA + QDS_BOT + 2 * f, SPIG_X - 4, DUEL_Y + 6 + dy, who, 0);
    else piece(OAM_HAND_KID, QD_SODA + QDS_BOT + 2 * f, KID_X + 12, DUEL_Y + 6 + dy, who, 0);
}

static void shake_body(uint8_t who) {            // STAND with the holstered bottle out (it is in his fist)
    if (who == WHO_KID) { kid_obj(KID_STAND); return; }
    mg_spigoteer(SPIG_X, DUEL_Y, SPIG_STAND, 0, OAM_SPIG);
    shadow_OAM[OAM_SPIG + 2].tile = (uint8_t)(QD_SODA + QDS_SPIG_BL);
}

static void wet(uint8_t who, uint8_t f) {        // the wet overlay on his head: W_SPLASH, W_DRIP_A, W_DRIP_B
    if (who == WHO_YOU) piece(OAM_WET, QD_SODA + QDS_WET + 4 * f, SPIG_X, DUEL_Y - 4, who, 1);
    else piece(OAM_WET, QD_SODA + QDS_WET + 4 * f, KID_X, DUEL_Y - 2, who, 1);
}

static uint8_t drip(void) { return W_DRIP_A + ((S.anim >> 3) & 1); }

static void aim(uint8_t who, uint8_t f) {        // the winner's DRAW pose, his bottle aimed level (f: the spurt's flicker)
    if (who == WHO_YOU) {
        mg_spigoteer(SPIG_X, DUEL_Y, SPIG_DRAW, 0, OAM_SPIG);
        piece(OAM_AIM, QD_SODA + QDS_AIM + 4 * f, SPIG_X - 14, DUEL_Y + 6, who, 1);
    } else {
        kid_obj(KID_DRAW);
        piece(OAM_AIM, QD_SODA + QDS_AIM + 4 * f, KID_X + 14, DUEL_Y + 9, who, 1);
    }
}

// The stream on the wall's row: `who` sprays, columns cut..len-1 out from his bottle (the Kid's from column 6 to the
// right, the Spigoteer's from column 13 to the left) over the wall saved at entry; queued only when the row changes.
static void stream(uint8_t who, uint8_t len, uint8_t cut) {
    uint8_t c, k, v, dirty = 0, flow = QD_SODA + QDS_STREAM + ((S.anim >> 2) & 1);
    if (len > STREAM_N) len = STREAM_N;
    for (c = 0; c < 20; c++) {
        k = who == WHO_YOU ? (uint8_t)(13 - c) : (uint8_t)(c - 6);   // (off the stream: wraps past STREAM_N)
        v = S.wall[c];
        if (k >= cut && k < len) {
            if (k == len - 1 && len < STREAM_N) v = QD_SODA + QDS_STREAM + (who == WHO_YOU ? ST_HEAD_L : ST_HEAD_R);
            else if (k == 0 && who == WHO_KID) v = (uint8_t)(QD_SODA + QDS_STREAM + ST_RISE_R);   // up from his lower hand
            else v = flow;
        }
        if (S.row[c] != v) { S.row[c] = v; dirty = 1; }
    }
    if (dirty) qd_put(0, STREAM_ROW, S.row, 20);
}

static void poses(void) {
    uint8_t s = S.st, t = S.t, f, win = WHO_KID, len = 0, cut = 0;
    S.anim++;
    for (f = 0; f < OAM_SPIG; f++) shadow_OAM[f].y = 0;   // the overlays and bottles: off unless placed below
    if (s == QS_SHOW && (S.res == QR_FOUL || S.res == QR_WRONG)) {   // his own bottle fizzes over onto him
        shake_body(WHO_KID); hand(WHO_KID, B_STILL, 0);
        shake_body(WHO_YOU);
        if (t < FOUL_FIZZ) {
            hand(WHO_YOU, B_FIZZ, 0);
            if (t >= FOUL_FOAM_AT && t < FOUL_FOAM_END)
                piece(OAM_FOAM, (uint8_t)(QD_SODA + QDS_BOT + 2 * B_FOAM), SPIG_X - 4, DUEL_Y - 7 + ((t >> 1) & 1), WHO_YOU, 0);
        } else hand(WHO_YOU, B_STILL, 0);
        if (t >= FOUL_WET_AT) wet(WHO_YOU, t < FOUL_FIZZ ? W_SPLASH : drip());
    } else if (s == QS_SHOW) {                   // the winner sprays (the Kid on TOO SLOW), the loser gets wet
        win = S.res == QR_YOU ? WHO_YOU : WHO_KID;
        aim(win, (t >> 1) & 1);
        shake_body(1 - win); hand(1 - win, B_STILL, 0);
        if (t) {                                 // (frame 0 queues the result's text and pips: the stream starts on 1)
            len = t < STREAM_N ? STREAM_STEP * t : STREAM_N;
            if (t >= STREAM_CUT) cut = STREAM_STEP * (t - STREAM_CUT + 1);
        }
        if (t >= WET_AT) wet(1 - win, t < DRIP_AT ? W_SPLASH : drip());
    } else if (s == QS_OVER) {                   // the winner's last pose, the loser still dripping
        if (S.wins[0] >= QD_TO_WIN) { aim(WHO_YOU, 0); shake_body(WHO_KID); hand(WHO_KID, B_STILL, 0); wet(WHO_KID, drip()); }
        else { kid_obj(KID_CHEER); shake_body(WHO_YOU); hand(WHO_YOU, B_STILL, 0); wet(WHO_YOU, drip()); }
    } else {                                     // the banner: both shake, out of step; DRAW! (and the intro): still
        shake_body(WHO_KID); shake_body(WHO_YOU);
        if (s != QS_DRAW && mg_phase == MG_PLAY) {
            f = (S.anim >> 2) & 1; hand(WHO_KID, f ? B_UP : B_DOWN, f ? -2 : 1);
            f = S.anim % 10 < 5;   hand(WHO_YOU, f ? B_UP : B_DOWN, f ? -2 : 1);
        } else { hand(WHO_KID, B_STILL, 0); hand(WHO_YOU, B_STILL, 0); }
    }
    stream(win, len, cut);
}

void qd_update(uint8_t pressed) BANKED {
    uint8_t right;
    uint16_t w;
    if (mg_phase == MG_PLAY) {
        switch (S.st) {
        case QS_NEXT:
            S.round++;
            S.r = kid_r[S.round - 1];
            S.badge = S.round < QD_FEINT_FROM ? 0 : mg_rand() & 1;
            S.wait = w = QD_WAIT_MIN + rand16() % QD_WAIT_SPAN;
            S.feint = QF_NONE; S.feint_t = QD_FEINT_LEN; S.feint_at = 0;
            if (S.round >= QD_FEINT_FROM) {
                S.feint = (mg_rand() & 1) ? QF_CROW : QF_TUMBLE;
                S.feint_at = QD_FEINT_GAP + QD_FEINT_LEN + rand16() % (w - QD_FEINT_GAP - QD_FEINT_LEN + 1);
                S.feint_t = 0;
            }
            S.res = QR_NONE; S.react = 0; S.t = 0;
            S.st = QS_READY;
            S.txt[0] = 'R'; S.txt[1] = 'O'; S.txt[2] = 'U'; S.txt[3] = 'N'; S.txt[4] = 'D'; S.txt[5] = ' ';
            S.txt[6] = '0' + S.round; S.txt[7] = 0;
            mg_say(MG_TEXT_A, S.txt);
            mg_say(MG_TEXT_B, "WAIT FOR THE SIGN");
            break;
        case QS_READY:
            if (++S.t >= QD_READY_LEN) { S.st = QS_WAIT; S.t = 0; }   // the banner stays
            break;
        case QS_WAIT:
            if (pressed & (J_A | J_B)) { end_round(QR_FOUL); break; }
            if (--S.wait == 0) {                 // DRAW!
                S.st = QS_DRAW; S.t = 0; S.feint_t = QD_FEINT_LEN;
                sign(1);
                mg_say(MG_TEXT_B, "");
                SFX(SFX_CATCH);
            } else if (S.feint && S.wait <= S.feint_at) {   // the feint: frames feint_at .. feint_at - LEN + 1 of the wait
                w = S.feint_at - S.wait;
                S.feint_t = w < QD_FEINT_LEN ? (uint8_t)w : QD_FEINT_LEN;
                if (w == 0 && S.feint == QF_TUMBLE) SFX(SFX_SHAKE);
                if (w == 24 && S.feint == QF_CROW) SFX(SFX_LAUNCH);   // the caw
            }
            break;
        case QS_DRAW:
            if (S.t++ == 0 && S.badge) badge_pal(1);   // (the frame after the sign's: B's blue disc)
            right = S.badge ? J_B : J_A;
            if (pressed & (J_A | J_B) & ~right) end_round(QR_WRONG);
            else if (S.t > S.r) end_round(QR_SLOW);              // the Kid drew on frame R: R + 1 is too late
            else if (pressed & right) { S.react = S.t; end_round(QR_YOU); }   // (a tie at R is the player's)
            break;
        case QS_SHOW:
            if (++S.t < QD_SHOW_LEN) break;
            sign(0);
            if (S.badge) badge_pal(0);               // the planks back in palette 2
            if (S.wins[0] < QD_TO_WIN && S.wins[1] < QD_TO_WIN) { S.st = QS_NEXT; break; }
            S.st = QS_OVER;
            if (S.wins[0] >= QD_TO_WIN) {
                mg_points(QD_MATCH_PTS);
                mg_say(MG_TEXT_A, "YOU WIN");
                score_line(S.wins[0], S.wins[1]);
            } else {
                mg_say(MG_TEXT_A, "THE KID WINS");
                score_line(S.wins[1], S.wins[0]);
            }
            mg_say(MG_TEXT_B, S.txt);
            mg_finish();
            break;
        }
    }
    poses();
    feint_obj();
}
