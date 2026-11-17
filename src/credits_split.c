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
#ifndef CR_NOQP
#define CR_NOQP 0
#endif
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
#define CR_PS_P (story_scratch[70])                                      // the NEXT frame's plan, made at the end of this frame's update (the frame's start only copies it): v | top << 4 | dir << 5
#define CR_PS_L (story_scratch[71])                                      //          the swap's line
#define CR_PS_1 223                                    //          the band's patch line
#define CR_PS_2 224                                    //          the name's patch line
#define CR_PS_Q 225                                    //          the top version
#define CR_PS_T 226                                    //          the scroll's low byte it is made for
#define CR_SH_E1 220                                   // the line the band's end is patched at (255: none)
#define CR_SH_E2 221                                   // the line the name's row is patched at
#define CR_SH_QV 222                                   // the stage palette's version at the top of the screen: 0 the page's, 1 cream ink, 2 cream ink and navy
#define CR_HUD ((const uint16_t *)(CR_PAL + 8))          // the cards' HUD palette (BG 1), as the hardware takes it (lifted once at the roll's start): colour 0 the letters cream #f8e8b0, colour 3 the cards' navy #181040
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
    ld   b, #4
    jr   _cr_wn
__endasm;
}
static void cr_bg64(const uint8_t *s) __naked {    // the same to BCPD
    (void)s;
__asm
    ld   c, #0x69
    ld   b, #4
    jr   _cr_wn
__endasm;
}
static void cr_ob48(const uint8_t *s) __naked {    // 48 bytes (six OBJ palettes) to OCPD; B x 16 bytes from DE to the port in C: the others come in here
    (void)s;
__asm
    ld   c, #0x6B
    ld   b, #3
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
static void cr_wn(const uint8_t *s, uint8_t n) {         // n x 16 bytes to the port the caller named (the C twin of _cr_wn: a pointer, sixteen stores a pass, no index arithmetic: the set must be in before the first line is drawn)
    do {
        BCPD_REG = *s++; BCPD_REG = *s++; BCPD_REG = *s++; BCPD_REG = *s++; BCPD_REG = *s++; BCPD_REG = *s++; BCPD_REG = *s++; BCPD_REG = *s++;
        BCPD_REG = *s++; BCPD_REG = *s++; BCPD_REG = *s++; BCPD_REG = *s++; BCPD_REG = *s++; BCPD_REG = *s++; BCPD_REG = *s++; BCPD_REG = *s++;
    } while (--n);
}
static void cr_wo(const uint8_t *s, uint8_t n) {
    do {
        OCPD_REG = *s++; OCPD_REG = *s++; OCPD_REG = *s++; OCPD_REG = *s++; OCPD_REG = *s++; OCPD_REG = *s++; OCPD_REG = *s++; OCPD_REG = *s++;
        OCPD_REG = *s++; OCPD_REG = *s++; OCPD_REG = *s++; OCPD_REG = *s++; OCPD_REG = *s++; OCPD_REG = *s++; OCPD_REG = *s++; OCPD_REG = *s++;
    } while (--n);
}
static void cr_bg64(const uint8_t *s) { cr_wn(s, 4); }
static void cr_ob64(const uint8_t *s) { cr_wo(s, 4); }
static void cr_ob48(const uint8_t *s) { cr_wo(s, 3); }
// The interrupt's writers, in C. The poll for the HBlank is INLINE in each (no call between seeing the HBlank and the first store: a function's return
// and a pop cost ~40 cycles of the ~250 the HBlank has, and a palette that does not fit takes a second line: 25 lines for a swap, not 20, and the VBlank handler comes after the
// latest line its drain may start at). Line 144 on ends the wait (the writes are free then), as _cr_sw1's first loop does.
static void cr_sw1(const uint8_t *s) {
    for (;;) { if (LY_REG >= 144) break; if (STAT_REG & 2) { while (STAT_REG & 2) ; break; } }
    BCPD_REG = *s++; BCPD_REG = *s++; BCPD_REG = *s++; BCPD_REG = *s++; BCPD_REG = *s++; BCPD_REG = *s++; BCPD_REG = *s++; BCPD_REG = *s;
}
static void cr_sw_ob8(const uint8_t *s) {
    uint8_t p;
    OCPS_REG = 0x88;
    for (p = 0; p < 6; p++) {
        while (!(STAT_REG & 2)) ;
        while (STAT_REG & 2) ;
        OCPD_REG = *s++; OCPD_REG = *s++; OCPD_REG = *s++; OCPD_REG = *s++; OCPD_REG = *s++; OCPD_REG = *s++; OCPD_REG = *s++; OCPD_REG = *s++;
    }
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

static void cr_qver(uint8_t qv, uint8_t qp, uint16_t *e) {       // the stage palette's entries 0 and 1 (BG 7's for the Chrome Cow) in version qv: 0 the page's, 1 cream ink, 2 cream ink and, where the page's blank is navy, navy behind it
    if (qv) { e[qp & 1] = CR_HUD[0]; if (qv == 2 && (qp & 8)) e[1 - (qp & 1)] = CR_HUD[3]; }
}
static void cr_qpal(uint8_t qv, uint8_t qp) {      // the entries as the RAM copy of the page's set holds them, in version qv, to the hardware in the next HBlank
    uint16_t e[2];
    uint8_t pal = qp & 4 ? 7 : 0;
    const uint16_t *s = (const uint16_t *)(CR_PT_B + CR_SH_BG + 8 * pal);
    e[0] = s[0]; e[1] = s[1];
    cr_qver(qv, qp, e);
    while (STAT_REG & 2) ;
    BCPS_REG = 0x80 | (uint8_t)(pal << 3);
    BCPD_REG = (uint8_t)e[0]; BCPD_REG = (uint8_t)(e[0] >> 8); BCPD_REG = (uint8_t)e[1]; BCPD_REG = (uint8_t)(e[1] >> 8);
}

static void cr_split_plan(uint16_t sc) {          // the plan for the frame that shows scroll sc: its top set, the line (if any) the interrupt swaps at, the patch lines: into the PS bytes
    uint16_t u = 0, w;
    uint8_t v = CR_PT_B[CR_SH_V], top = 0, line = 255, dir = 0, e1 = 255, e2 = 255, qv = 0;      // (the roll only goes forward: the venues behind the screen are not asked again, a scan from the first cost 5 lines)
    if (v && sc < (uint16_t)(ct_ostart[v - 1] + CT_SGT + 19) * 8) v = 0;
    for (; v < 10; v++) {
        u = (ct_ostart[v] + CT_SGT) * 8;             // the swap line before the page: the top of its row 0 (flat navy in a palette that is navy in both sets, 8 lines: the page set goes in by the time its band begins), the cards' set above, the page's below
        w = (ct_ostart[v] + CT_SGT + 19) * 8;        // the strip after it
        if (sc < u) { if (u - sc <= 135) { line = (uint8_t)(u - sc); dir = 0; } break; }          // (the page's band starts 8 lines below the line: its stage palette must be in before; the swap ends by line 144 from 124 up (a palette a line, 14 of them), else the OBJ ones wait for the next frame)
        if (sc < w) { top = 1; if (w - sc <= 124) { line = (uint8_t)(w - sc); dir = 1; } break; }
    }
    if (line < (KEY1_REG & 0x80 ? 2 : 12)) {
        if (is_cgb && line + (dir ? 16 : 8) >= (KEY1_REG & 0x80 ? 2 : 12) + (dir ? 8 : 2)) line = KEY1_REG & 0x80 ? 2 : 12;          // (the lines above the page are not blank in the other set: the swap goes later, into the rows that are navy in both (the strip 16 lines; the page's row 0 8 lines, its stage palette first) if they are long enough for it)
        else { if (!dir) top = 1; else top = 0; line = 255; }          // (the page is at the top and the interrupt could not come in time (a late frame): the other set from the start)
    }
    if (is_cgb && !CR_NOQP && v < 10 && ct_qp[v] && (top || (line != 255 && !dir))) {          // (a page whose letters are patched: the band's end and the name's row are lines of the picture)
        int16_t yp = (int16_t)u - (int16_t)sc, be = yp + 32, nt = yp + 136;
        if (top) qv = nt <= 9 ? 2 : be > 3 ? 1 : 0;        // (an event for one of the first lines would be armed after the line has passed on a late frame and the chain would stall: those lines take the next version at once)
        if (be > 3 && be < 147) e1 = be > 6 ? (uint8_t)(be - 3) : 3;         // (the write is in the HBlank at the end of the line, and the interrupt is a line or two late: 3 lines early; the band's letters end 4 lines above its end, the picture's last lines do not use the ink)
        if (nt > 9 && nt < 147) e2 = (uint8_t)(nt - 3);
    }
    CR_PS_P = v | top << 4 | dir << 5; CR_PS_L = line; CR_PT_B[CR_PS_1] = e1; CR_PT_B[CR_PS_2] = e2; CR_PT_B[CR_PS_Q] = qv; CR_PT_B[CR_PS_T] = (uint8_t)sc;
}

static void cr_split_sync(void) {
    uint8_t top = CR_PT_B[CR_SH_TOP], qp = is_cgb && top && CR_PT_B[CR_SH_V] < 10 ? ct_qp[CR_PT_B[CR_SH_V]] : 0;
    uint16_t *pe = 0, sv0 = 0, sv1 = 0;
    if (qp) {                                         // (the last frame ended with the name's version: this one starts as the page has it, or in the band's: the RAM copy has it for the set's write, then goes back)
        pe = (uint16_t *)(CR_PT_B + CR_SH_BG + (qp & 4 ? 56 : 0));
        sv0 = pe[0]; sv1 = pe[1];
        cr_qver(CR_PT_B[CR_SH_QV], qp, pe);
    }
    if (CR_PT_B[CR_SH_HW] != top || (!top && CR_PT_B[CR_SH_DIRTY])) {
        cr_pset(top);
        CR_PT_B[CR_SH_HW] = top;
        if (!top) CR_PT_B[CR_SH_DIRTY] = 0;
    } else if (qp) CRITICAL { cr_qpal(0, qp); }
    if (qp) { pe[0] = sv0; pe[1] = sv1; }
}

void cr_split_isr_b(void) BANKED {
    uint8_t ly = LYC_REG, sl = CR_PT_B[CR_SH_LINE], dir = CR_PT_B[CR_SH_DIR], p, q, e1, e2, qp, qb[8];
    const uint8_t *sp, *s7, *sp0;
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
    e1 = CR_PT_B[CR_SH_E1]; e2 = CR_PT_B[CR_SH_E2];
    qp = CR_PT_B[CR_SH_V] < 10 ? ct_qp[CR_PT_B[CR_SH_V]] : 0;
    if (ly == e1 || ly == e2) cr_qpal(ly == e2 ? 2 : 0, qp);
    else if (ly == sl) {
        q = dir ? 0 : 1;
        sp = q ? CR_PT_B + CR_SH_BG : CR_PAL;
        s7 = sp + 56;
        if (q && qp) {                               // (a page's letters are patched: the stage palette goes in with the band's cream ink; its end is the next line)
            const uint8_t *src = qp & 4 ? s7 : sp;
            for (p = 0; p < 8; p++) qb[p] = src[p];
            ((uint16_t *)qb)[qp & 1] = CR_HUD[0];
            if (qp & 4) s7 = qb; else sp = qb;
            sp0 = sp;
        } else sp0 = sp;
        BCPS_REG = 0x80; cr_sw1(sp0);                // BG 0 and 7 first (the stage palette: the band and the name; the Chrome Cow's band is BG 7's), then 1-6, then OBJ 1-6: a palette a line, in its HBlank
        BCPS_REG = 0xB8; cr_sw1(s7);
        sp0 = q ? CR_PT_B + CR_SH_BG : CR_PAL;
        BCPS_REG = 0x88;
        for (p = 1; p < 7; p++) cr_sw1(sp0 + 8 * p);
        if (sl <= 124) cr_sw_ob8(dir ? CR_PAL + 72 : CR_PT_B + CR_SH_OB);
        CR_PT_B[CR_SH_HW] = !dir;
    } else { LYC_REG = 255; return; }
    ly = LY_REG;
    sl = 255;
    if (CR_PT_B[CR_SH_LINE] > ly && CR_PT_B[CR_SH_LINE] < sl) sl = CR_PT_B[CR_SH_LINE];
    if (e1 > ly && e1 < sl) sl = e1;
    if (e2 > ly && e2 < sl) sl = e2;
    LYC_REG = sl;
    cr_dbg_d();
}


void cr_split_pre(void) BANKED {                   // the end of credits_update: the scroll the next frame shows is the timeline's position now
    cr_split_plan(*(uint16_t *)(story_scratch + 22));
}

void cr_split_frame(void) BANKED {                 // every frame of the roll, in credits_update after the scroll register: the plan (made at the end of the last update, or now on a late frame), the interrupt's line, the set the top of the screen shows
    uint8_t p, l;
    cr_dbg_a();
    if (CR_PT_B[CR_PS_T] != (uint8_t)CR_SCROLL) cr_split_plan(CR_SCROLL);
    p = CR_PS_P;
    CR_PT_B[CR_PS_T]++;                              // (used)
    CR_PT_B[CR_SH_V] = p & 15; CR_PT_B[CR_SH_TOP] = (p >> 4) & 1; CR_PT_B[CR_SH_DIR] = p >> 5;
    l = CR_PT_B[CR_SH_LINE] = CR_PS_L;
    CR_PT_B[CR_SH_E1] = CR_PT_B[CR_PS_1]; CR_PT_B[CR_SH_E2] = CR_PT_B[CR_PS_2]; CR_PT_B[CR_SH_QV] = CR_PT_B[CR_PS_Q];
    if (!is_cgb) LYC_REG = l != 255 ? l : 0;         // (a DMG's chain goes on from line 0: the header. BEFORE the set goes in: a line near the top would be gone by the time the write is made)
    else {                                           // (Color: the first of the swap's line and the two patches')
        if (CR_PT_B[CR_SH_E1] < l) l = CR_PT_B[CR_SH_E1];
        if (CR_PT_B[CR_SH_E2] < l) l = CR_PT_B[CR_SH_E2];
        LYC_REG = l;
    }
    cr_dbg_e();
    cr_split_sync();
    cr_dbg_b();
}
#endif
