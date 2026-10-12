// The framework's stub mini-game, GREEN LIGHT: it proves the flow (src/mg.c) and is not part of the story (no story slot
// plays it until a test marks the mini slot built). A lamp shows red for a random while, then green: press A on green.
// STUB_ROUNDS rounds; points 1000 - 20 per frame of reaction (HARD: 30), at least 100; A on red is TOO SOON (0), no A
// within GREEN_MAX frames TOO SLOW (0). A 30 s timer caps the game (the framework's HUD timer).
//   BG: the lamp, 2x2 tiles at columns 9-10, rows 6-7 (MG_GAME_BG.., CGB BG palette 2). OAM 0-3 the Spigoteer.
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"
#include "music.h"
#include "mg.h"
#include "mg_stub_art.h"    // this bank's own art: the lamp (assets/art/mg_lamp.txt)

#define S               (MG->stub)
#define LAMP_COL        9
#define LAMP_ROW        6
#define LAMP_PAL        BGPAL_PATRON        // CGB BG palette 2 (a game's own)
#define STUB_ROUNDS     5
#define STUB_TIME       (30 * 60)
#define RED_MIN         45                  // frames of red: RED_MIN + 0..63 (HARD: RED_MIN_HARD + 0..63)
#define RED_MIN_HARD    30
#define GREEN_MAX       60
#define SHOW_LEN        40
#define STEP_PTS        20                  // points lost per frame of reaction (HARD: STEP_PTS_HARD)
#define STEP_PTS_HARD   30
#define BT_X            72
#define BT_Y            112
enum { GL_NEXT, GL_RED, GL_GREEN, GL_SHOW };

static void lamp(uint8_t green, uint8_t lcd_off) {
    uint8_t t = MG_GAME_BG + (green ? 4 : 0);
    S.lamp[0][0] = t;     S.lamp[0][1] = t + 1;
    S.lamp[1][0] = t + 2; S.lamp[1][1] = t + 3;
    if (lcd_off) {
        vram_put(LAMP_COL, LAMP_ROW, S.lamp[0], 2);
        vram_put(LAMP_COL, LAMP_ROW + 1, S.lamp[1], 2);
    } else {
        vq_add(0, S.lamp[0], LAMP_COL, LAMP_ROW, 2);
        vq_add(0, S.lamp[1], LAMP_COL, LAMP_ROW + 1, 2);
    }
}

// LCD off, after the framework's screen
void stub_enter(void) BANKED {
    uint16_t p[4];
    set_bkg_data(MG_GAME_BG, LAMP_TILES, lamp_tiles);
    if (is_cgb) {
        p[0] = RGB8(216, 216, 208);              // the pale housing
        p[1] = RGB8(64, 224, 72);                // green
        p[2] = RGB8(224, 40, 32);                // red
        p[3] = RGB8(24, 24, 32);                 // the rim
        set_bkg_palette(LAMP_PAL, 1, p);
        S.lamp[0][0] = S.lamp[0][1] = LAMP_PAL;
        VBK_REG = VBK_BANK_1;
        vram_put(LAMP_COL, LAMP_ROW, S.lamp[0], 2);
        vram_put(LAMP_COL, LAMP_ROW + 1, S.lamp[0], 2);
        VBK_REG = VBK_BANK_0;
    }
    lamp(0, 1);
    S.st = GL_NEXT; S.round = 0; S.t = 0; S.wait = 0; S.react = 0;
    mg_timer = STUB_TIME;
    mg_spigoteer(BT_X, BT_Y, BT_IDLE, 0, 0);
}

static void show(uint8_t react) {
    S.react = react; S.st = GL_SHOW; S.t = 0;
}

void stub_update(uint8_t pressed) BANKED {
    uint8_t f = BT_IDLE;
    uint16_t d;
    if (mg_phase == MG_PLAY) {
        S.t++;
        switch (S.st) {
        case GL_NEXT:
            S.round++;
            S.wait = ((mg_mode & MG_HARD) ? RED_MIN_HARD : RED_MIN) + (mg_rand() & 63);
            S.st = GL_RED; S.t = 0;
            S.txt[0] = 'R'; S.txt[1] = 'O'; S.txt[2] = 'U'; S.txt[3] = 'N'; S.txt[4] = 'D'; S.txt[5] = ' ';
            mg_number(S.txt + 6, S.round);
            mg_say(MG_TEXT_A, S.txt);
            mg_say(MG_TEXT_B, "WAIT FOR GREEN");
            break;
        case GL_RED:
            if (pressed & J_A) { show(0); mg_say(MG_TEXT_B, "TOO SOON"); SFX(SFX_BREAK); }
            else if (!--S.wait) { lamp(1, 0); S.st = GL_GREEN; S.t = 0; }
            break;
        case GL_GREEN:
            if (pressed & J_A) {
                d = (uint16_t)S.t * ((mg_mode & MG_HARD) ? STEP_PTS_HARD : STEP_PTS);
                d = d >= 900 ? 100 : 1000 - d;
                mg_points(d);
                mg_number(S.txt, d);                     // "920 POINTS" (the HUD glyphs have no '+')
                for (f = 0; S.txt[f]; f++) ;
                S.txt[f++] = ' '; S.txt[f++] = 'P'; S.txt[f++] = 'O'; S.txt[f++] = 'I'; S.txt[f++] = 'N';
                S.txt[f++] = 'T'; S.txt[f++] = 'S'; S.txt[f] = 0;
                f = BT_IDLE;
                mg_say(MG_TEXT_B, S.txt);
                SFX(SFX_COIN);
                show(S.t);
            } else if (S.t >= GREEN_MAX) { show(0); mg_say(MG_TEXT_B, "TOO SLOW"); }
            break;
        default:                                 // GL_SHOW
            if (S.t >= SHOW_LEN) {
                lamp(0, 0);
                if (S.round >= STUB_ROUNDS) { mg_say(MG_TEXT_A, "WELL DONE"); mg_finish(); }
                else S.st = GL_NEXT;
            }
        }
    }
    if (S.st == GL_SHOW) f = S.react ? BT_CATCH : BT_FAIL;
    mg_spigoteer(BT_X, BT_Y, f, 0, 0);
}
