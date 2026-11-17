// The credits' shared screen (CRSPLIT): the palette work behind it, in a bank of its own (credits.c's was full). See the block comment below and credits.c credits_update, cr_leave, cr_pump.
#pragma bank 255
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"
#include "palettes.h"
#include "credits_text.h"
#include "asm_cfg.h"

#if CT_SPLIT
#define CR_SCROLL (*(uint16_t *)(story_scratch + 20))                 // struct cr_state's scroll (credits.c)
#define CR_PAL ((uint8_t *)story_scratch + 72)                          // the card's colours (CGB: 128 bytes; DMG: BGP, OBP0, OBP1, the first OBP1)
#define CR_PT_B ((uint8_t *)story_scratch + 200)       // CRSCENE: the scene page's meta, where the owner's portrait used to be
#define CR_SH_DIRTY 212                                // CRSPLIT: the card set's RAM copy (CR_PAL) is ahead of the hardware
#define CR_SH_HW 213                                   //          which set the hardware holds at the end of the frame: 0 the cards', 1 the page's
#define CR_SH_TOP 214                                  //          which set the top of the screen shows this frame
#define CR_SH_LINE 215                                 //          the line the interrupt swaps at (255: none)
#define CR_SH_LO 217                                   //          the page's objects on the screen: from, up to (in the order they enter)
#define CR_SH_HI 218
#define CR_SH_V 219                                    //          the first venue whose page the plan has not left behind
#define CR_SH_DIR 216                                  //          0: cards' -> page's, 1: page's -> cards'
#define CR_SH_BG 100                                   // CRSCENE: the page's BG palettes (8 x 8 bytes) and OBJ palettes (6 x 8: colour 0 is 0), as the hardware takes them
#define CR_SH_OB 164
// CRCFLAGS=-DCR_DBG: empty banked calls at the split's steps, for tools/dev/credits_split_trace.py (a hook on each logs LY); nothing in a build without it
#ifdef CR_DBG
void cr_dbg_a(void) BANKED {} void cr_dbg_b(void) BANKED {} void cr_dbg_c(void) BANKED {} void cr_dbg_d(void) BANKED {} void cr_dbg_e(void) BANKED {}
#else
#define cr_dbg_a()
#define cr_dbg_b()
#define cr_dbg_c()
#define cr_dbg_d()
#define cr_dbg_e()
#endif
// ---- the page shares the screen with the cards above and below it (CRSPLIT): two palette sets, the cards' (CR_PAL, BG 0-7 and OBJ 0-7) and the page's (CR_SH_BG: BG 0-7, CR_SH_OB: OBJ 1-6). The hardware
// holds the set the TOP of the screen shows (cr_split_sync, at the frame's start, in the VBlank), and on the line a strip of blank rows begins (16 lines, 2 rows) the LYC interrupt
// (cr_split_isr) writes the other set, one palette a HBlank. On a DMG the sets are OBP0 / OBP1 (BGP is the same). ---------------------------------------------------------------------------
#if ASM_CR_SPLIT
// The writers run one auto-incrementing index (BCPS / OCPS, set by the caller) through a whole set: bytes at 4 cycles each, no per-palette setup (the C version took ~100 cycles a palette:
// 23 lines for a set in the VBlank, and in the interrupt a palette's writes ran past its HBlank into the next line's drawing, where the hardware ignores them).
static void cr_ob64(const uint8_t *s) __naked {    // 64 bytes at DE to OCPD (the VBlank: no STAT to wait for)
    (void)s;
__asm
    ld   c, #0x6B
    ld   b, #16
    jr   _cr_wn
__endasm;
}
static void cr_bg64(const uint8_t *s) __naked {    // the same to BCPD
    (void)s;
__asm
    ld   c, #0x69
    ld   b, #16
    jr   _cr_wn
__endasm;
}
static void cr_ob48(const uint8_t *s) __naked {    // 48 bytes (six OBJ palettes) to OCPD; B x 4 bytes from DE to the port in C: the others come in here
    (void)s;
__asm
    ld   c, #0x6B
    ld   b, #12
_cr_wn:
    ld   h, d
    ld   l, e
1$:
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl+)
    ldh  (c), a
    dec  b
    jr   nz, 1$
    ret
__endasm;
}
// The interrupt's: the same, a palette (eight writes) in each line's HBlank. The wait is for the end of a line's drawing (STAT mode 2/3: bit 1 set), then for the next HBlank (bit 1 clear): a palette is written
// only inside one, however late the interrupt came (the writes are 32 cycles, 8 more to see the mode; an HBlank without sprites is 51). BCPS / OCPS go on counting by themselves from the index the caller set.
static void cr_sw1(const uint8_t *s) __naked {     // BG: ONE palette, the eight bytes at DE to BCPD (the index is set by the caller), in the next HBlank
    (void)s;
__asm
    ld   h, d
    ld   l, e
    ld   c, #0x69
1$:
    ldh  a, (0x44)
    cp   a, #144
    jr   nc, 3$
    ld   a, (#0xFF41)
    bit  1, a
    jr   z, 1$
2$:
    ld   a, (#0xFF41)
    bit  1, a
    jr   nz, 2$
3$:
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl+)
    ldh  (c), a
    ret
__endasm;
}
static void cr_sw_ob8(const uint8_t *s) __naked {  // OBJ 1-6 from 48 bytes at DE: 8 a line (OCPS = 0x88)
    (void)s;
__asm
    ld   h, d
    ld   l, e
    ld   c, #0x6A
    ld   a, #0x88
    ldh  (c), a
    inc  c
    ld   b, #6
1$:
    ld   a, (#0xFF41)
    bit  1, a
    jr   z, 1$
2$:
    ld   a, (#0xFF41)
    bit  1, a
    jr   nz, 2$
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl+)
    ldh  (c), a
    ld   a, (hl+)
    ldh  (c), a
    dec  b
    jr   nz, 1$
    ret
__endasm;
}
#else
static void cr_bg64(const uint8_t *s) { uint8_t k; for (k = 0; k < 64; k++) BCPD_REG = s[k]; }
static void cr_ob64(const uint8_t *s) { uint8_t k; for (k = 0; k < 64; k++) OCPD_REG = s[k]; }
static void cr_ob48(const uint8_t *s) { uint8_t k; for (k = 0; k < 48; k++) OCPD_REG = s[k]; }
static void cr_hb(void) { while (!(STAT_REG & 2)) ; while (STAT_REG & 2) ; }          // (the next HBlank)
static void cr_sw1(const uint8_t *s) { uint8_t k; cr_hb(); for (k = 0; k < 8; k++) BCPD_REG = s[k]; }
static void cr_sw_ob8(const uint8_t *s) {
    uint8_t p, k;
    OCPS_REG = 0x88;
    for (p = 0; p < 6; p++) { cr_hb(); for (k = 0; k < 8; k++) OCPD_REG = *s++; }
}
#endif

void cr_pset(uint8_t scene) BANKED {              // one whole set to the hardware (the VBlank: no STAT to wait for)
    if (!is_cgb) {
        OBP0_REG = scene ? 0x90 : CR_PAL[1]; OBP1_REG = scene ? 0xE4 : CR_PAL[2];
        return;
    }
    CRITICAL {                                       // (the palette interrupt does not come in the middle: it shares the index registers)
        BCPS_REG = 0x80;
        cr_bg64(scene ? CR_PT_B + CR_SH_BG : CR_PAL);
        if (scene) { OCPS_REG = 0x88; cr_ob48(CR_PT_B + CR_SH_OB); }
        else { OCPS_REG = 0x80; cr_ob64(CR_PAL + 64); }
    }
}

static void cr_split_plan(void) {                 // this frame's top set, and the line (if any) the interrupt swaps at, from the scroll the frame shows
    uint16_t sc = CR_SCROLL, u, w;
    uint8_t v = CR_PT_B[CR_SH_V], top = 0, line = 255, dir = 0;      // (the roll only goes forward: the venues behind the screen are not asked again, a scan from the first cost 5 lines)
    if (v && sc < (uint16_t)(ct_ostart[v - 1] + CT_SGT + 19) * 8) v = 0;
    for (; v < 10; v++) {
        u = (ct_ostart[v] + CT_SGT) * 8;             // the swap line before the page: the top of its row 0 (flat navy in a palette that is navy in both sets, 8 lines: the page set goes in by the time its band begins), the cards set above, the page set below
        w = (ct_ostart[v] + CT_SGT + 19) * 8;        // the strip after it
        if (sc < u) { if (u - sc <= 135) { line = (uint8_t)(u - sc); dir = 0; } break; }          // (the page's band starts 8 lines below the line: its stage palette must be in before; the swap ends by line 144 from 124 up (a palette a line, 14 of them), else the OBJ ones wait for the next frame)
        if (sc < w) { top = 1; if (w - sc <= 124) { line = (uint8_t)(w - sc); dir = 1; } break; }
    }
    CR_PT_B[CR_SH_V] = v;
    if (line < (KEY1_REG & 0x80 ? 2 : 12)) { if (!dir) top = 1; else top = 0; line = 255; }          // (the strip is at the top: the interrupt could not come in time (a late frame) and the lines before it are blank: the other set from the start)
    CR_PT_B[CR_SH_TOP] = top; CR_PT_B[CR_SH_LINE] = line; CR_PT_B[CR_SH_DIR] = dir;
}

static void cr_split_sync(void) {
    uint8_t top = CR_PT_B[CR_SH_TOP];
    if (CR_PT_B[CR_SH_HW] != top || (!top && CR_PT_B[CR_SH_DIRTY])) {
        cr_pset(top);
        CR_PT_B[CR_SH_HW] = top;
        if (!top) CR_PT_B[CR_SH_DIRTY] = 0;
    }
}

void cr_split_isr_b(void) BANKED {
    uint8_t ly = LYC_REG, sl = CR_PT_B[CR_SH_LINE], dir = CR_PT_B[CR_SH_DIR], p, q;
    const uint8_t *sp;
    cr_dbg_c();
    if (!is_cgb) {                                   // (the DMG: the header's BGP at 0 and 16 as main.c cast_isr, and the page's shade registers at the split line)
        uint8_t nx = 0;
        if (ly == 0) BGP_REG = story_scratch[68];
        if (ly == 16) BGP_REG = story_scratch[69];
        if (sl != 255 && ly == sl) { OBP0_REG = dir ? CR_PAL[1] : 0x90; OBP1_REG = dir ? CR_PAL[2] : 0xE4; CR_PT_B[CR_SH_HW] = !dir; }
        if (ly < 16) nx = 16;
        if (sl != 255 && sl > ly && (!nx || sl < nx)) nx = sl;
        LYC_REG = nx;
        return;
    }
    if (LY_REG < ly) return;                         // (an interrupt before the line the LYC names: a stray one, seen at line 0 right after a set write: the real one is still to come)
    if (ly != sl) { LYC_REG = 255; return; }
    q = dir ? 0 : 1;
    sp = q ? CR_PT_B + CR_SH_BG : CR_PAL;
    BCPS_REG = 0x80; cr_sw1(sp);                     // BG 0 and 7 first (the stage palette: the band and the name; the Chrome Cow's band is BG 7's), then 1-6, then OBJ 1-6: a palette a line, in its HBlank
    BCPS_REG = 0xB8; cr_sw1(sp + 56);
    BCPS_REG = 0x88;
    for (p = 1; p < 7; p++) cr_sw1(sp + 8 * p);
    if (sl <= 124) cr_sw_ob8(dir ? CR_PAL + 72 : CR_PT_B + CR_SH_OB);
    CR_PT_B[CR_SH_HW] = !dir;
    LYC_REG = 255;
    cr_dbg_d();
}


void cr_split_frame(void) BANKED {                 // every frame of the roll, in credits_update after the scroll register: the plan, the interrupt's line, the set the top of the screen shows
    cr_dbg_a();
    cr_split_plan();
    LYC_REG = CR_PT_B[CR_SH_LINE] != 255 ? CR_PT_B[CR_SH_LINE] : (is_cgb ? 255 : 0);       // (a DMG's chain goes on from line 0: the header. BEFORE the set goes in: a line near the top would be gone by the time the write is made)
    cr_dbg_e();
    cr_split_sync();
    cr_dbg_b();
}
#endif
