// The story map's denser clouds (owner 11-11, "for the clouds to matter at all, we need to substantially increase them"; make CLOUDS=C|D, Color only, a test build:
// the default build keeps the five clouds of src/smap.c). Its own bank: smap.c has no room left.
//
// 33-41 clouds over the whole 512 x 560 world, as DATA (assets/story_map/cloud_layout.txt, laid out by tools/dev/cloud_layout.py): a cloud is a row (world y = 16 * row),
// a position and one of four shapes (the approved A B C and one new Q: 2 3 3 2 sprites wide, 8x16 entries; the one-sprite puffs looked like snowballs and are gone). They all drift 1 px every 8 frames, like the approved clouds,
// and stay where they are on the map (world-pinned): x = pos + clock / 8 (mod 512; a cloud past 488 comes in again from the left edge, the twin at pos - 512).
//
// One POOL of 16 entries (OAM 23-38) is handed out to whatever is on the screen, in two stacks: the clouds of the even rows take entries from the pool's first one up, the
// clouds of the odd rows from its last one down, each cloud's entries in a row. A stack is built again from the clock and the camera (exact: the rows the screen shows plus
// 16 px each way, their clouds that reach into it plus 16 px each way) on every 8th frame, the even rows' four frames after the odd rows'; the live entries of both slide with the
// camera and the drift between (cl_shift). The camera moves 2 px a frame: 8 frames are 16 px, the margin, so no cloud comes in or goes out inside the screen. The two stacks
// never hold more than the pool: the layout is searched so that no screen and clock holds more than 15 entries (tools/dev/cloud_layout.py), and no line more than 4. Sal, the
// arrows, the dots, the bang, the UFO and the panel's cursor keep their own entries (0-22) and are never touched: nothing that must show can lose its sprite to a cloud. A window
// layer over a row hides that row's clouds (both stacks are built every frame a window is up).
// The build is the hot spot: a C statement costs about a scanline at double speed, so cl_half is asm of the same loops (ASM_CLOUD); the C twin is the #else, built by
// make cfall and kept equal to it frame for frame by tests/test_smap_clouds_pool.py.
// State: 5 bytes of story_scratch (A_CLN 1-5): the temporaries of a build (par | x's 9th bit, n, x's low byte) while one runs, the two stacks' counts; and OAM 39's spare bytes. No WRAM global.
#pragma bank 255
#if defined(CLOUDS_C) || defined(CLOUDS_D)     // (the default build has no code here: the five clouds of smap.c)
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "asm_cfg.h"
#include "game.h"
#include "music.h"
#include "story.h"
#include "order.h"
#define SMAPW_VIEWS
#include "smap_world.h"
#include "smap_priv.h"
#define SMAP_CLOUD_TABLE
#include "smap_art.h"

#define OAM_CLOUDS 23
#define N_POOL     16          // OAM 23-38 (39: y 0, x: the clouds are on, tile, prop: the camera's low bytes the last frame; like the five clouds' OAM 36, 37)
#define CL_ON      (shadow_OAM[39].x)
#define CL_PX      (shadow_OAM[39].tile)
#define CL_PY      (shadow_OAM[39].prop)
#define PAL_CLOUD  1           // Color OBJ palette 1
#define CLN(i)     (SC(A_CLN)[i])   // 0: spare; 1, 2, 5: a build's temporaries (par | x bit 8 << 1; n; x low byte); 3, 4: the entries in use of the even rows' stack, of the odd rows' stack

void cl_all(void) BANKED;
void cl_off(void) BANKED;

// The stack `par` (0: even rows, from the pool's first entry; 1: odd rows, from its last): the clouds of the rows 16 * r (r of that parity) that meet [cy - 16, cy + 160) and
// reach into [cx - 16, cx + 176). A cloud's x is pos + drift (mod 512); its record is (pos / 4, flip << 7 | shape << 4 | width in 4 px units). The coarse test is in 4 px units
// (s = (pos / 4 + b4) & 127: in when s < 51 or s + width >= 128), the exact one (t, 9 bits) only for the clouds that pass it. An entry's x is the low byte of its place.
#if ASM_CLOUD
typedef char smap_cloud_offsets[(S_V == 396 && A_CLN == 390 && V_BOTTOM == 5 && V_WY == 8 && V_WH == 9 && V_CAMX == 12 && V_CAMY == 14 && V_TICK == 25 && SCL_ROWS == 35 && OAM_CLOUDS == 23 && N_POOL == 16) ? 1 : -1];
static void cl_half(uint8_t par) __naked {
    (void)par;
__asm
    ld   c, a                               ; c = par
    xor  a, a
    ld   (_story_scratch + 392), a          ; CLN2: n = 0
    ld   a, (_story_scratch + 396 + 5)      ; kx = (drift + 16 - cx) & 511, drift = (V_BOTTOM >> 1 & 15) << 5 | V_TICK >> 3
    srl  a
    and  a, #15
    ld   h, a
    ld   l, #0
    srl  h
    rr   l
    srl  h
    rr   l
    srl  h
    rr   l
    ld   a, (_story_scratch + 396 + 25)
    srl  a
    srl  a
    srl  a
    add  a, l
    ld   l, a
    ld   de, #16
    add  hl, de
    ld   a, (_story_scratch + 396 + 12)
    ld   e, a
    ld   a, (_story_scratch + 396 + 13)
    ld   d, a
    ld   a, l
    sub  a, e
    ld   l, a
    ld   a, h
    sbc  a, d
    and  a, #1
    ld   h, a                               ; hl = kx
    add  a, a
    or   a, c
    ld   (_story_scratch + 391), a          ; CLN1: par | kx bit 8 << 1
    ld   a, l
    ld   (_story_scratch + 395), a          ; CLN5: kx low byte
    srl  a
    srl  a
    ld   e, a
    ld   a, h
    rrca
    rrca
    or   a, e
    add  a, #2
    ld   d, a                               ; d = b4 = kx / 4 + 2
    ld   a, (_story_scratch + 396 + 14)     ; the rows (cy is 9 bits: the world is 560 tall): r0 = (cy - 16) / 16 (0 when cy < 16), r1 = min(34, (cy + 159) / 16)
    sub  a, #16
    ld   b, a
    ld   a, (_story_scratch + 396 + 15)
    sbc  a, #0
    jr   c, 11$
    ld   e, a
    ld   a, b
    swap a
    and  a, #15
    ld   b, a
    ld   a, e
    swap a
    or   a, b
    jr   12$
11$:
    xor  a, a
12$:
    ld   b, a
    xor  a, c
    and  a, #1
    jr   z, 13$
    inc  b                                  ; (the first row of this stack's parity)
13$:
    ld   a, (_story_scratch + 396 + 14)
    add  a, #159
    ld   e, a
    ld   a, (_story_scratch + 396 + 15)
    adc  a, #0
    swap a
    ld   c, a
    ld   a, e
    swap a
    and  a, #15
    or   a, c
    cp   a, #35
    jr   c, 14$
    ld   a, #34
14$:
    ld   c, a                               ; b = r, c = r1, d = b4
20$:                                        ; the row loop
    ld   a, c
    cp   a, b
    jp   c, 90$
    ld   a, b
    add  a, a
    add  a, a
    add  a, a
    add  a, a
    add  a, #16
    ld   hl, #_story_scratch + 396 + 14
    sub  a, (hl)
    ld   e, a                               ; e = y = (r << 4) + 16 - cy (a byte: the entry's y)
    ld   a, (_story_scratch + 396 + 9)      ; V_WH: a window layer
    or   a, a
    jr   z, 22$
    ld   a, e
    cp   a, #240
    jr   nc, 22$
    ld   hl, #_story_scratch + 396 + 8      ; V_WY
    cp   a, (hl)
    jr   c, 22$
    jr   z, 22$
    ld   a, (hl)
    ld   hl, #_story_scratch + 396 + 9
    add  a, (hl)
    add  a, #16
    cp   a, e
    jr   c, 22$
    jr   z, 22$
    jp   70$                                ; (the row is under the window layer)
22$:
    ld   a, e
    or   a, a
    jr   nz, 23$
    inc  e                                  ; (a live entry's y is never 0)
23$:
    ld   hl, #_scl_rowstart
    ld   a, l
    add  a, b
    ld   l, a
    jr   nc, 24$
    inc  h
24$:
    push bc
    ld   a, (hl+)
    ld   c, a                               ; c = the row's first record (a byte offset)
    ld   a, (hl)
    sub  a, c
    jp   z, 69$                             ; (no clouds in the row)
    ld   b, a                               ; b = its bytes
    ld   hl, #_scl_rec
    ld   a, l
    add  a, c
    ld   l, a
    jr   nc, 25$
    inc  h
25$:
30$:                                        ; a cloud: hl its record
    ld   a, (hl)
    add  a, d
    and  a, #127
    cp   a, #51
    jr   c, 40$
    ld   c, a
    inc  hl
    ld   a, (hl)
    dec  hl
    and  a, #15
    add  a, c
    bit  7, a
    jp   z, 60$
40$:                                        ; near the window: the exact test and the entries
    push hl
    push bc
    push de
    ld   a, (hl+)
    ld   d, a                               ; d = pos / 4
    ld   a, (hl)
    ld   c, a                               ; c = the shape byte
    and  a, #15
    ld   b, a                               ; b = width in 4 px units
    add  a, d
    ld   l, a
    ld   h, #0
    add  hl, hl
    add  hl, hl                             ; hl = (pos / 4 + width) * 4
    ld   a, (_story_scratch + 395)
    add  a, l
    ld   l, a
    jr   nc, 41$
    inc  h
41$:
    ld   a, (_story_scratch + 391)
    bit  1, a
    jr   z, 42$
    inc  h
42$:
    ld   a, h
    and  a, #1
    ld   h, a                               ; hl = t = (pos + kx + 4 * width) & 511
    or   a, l
    jp   z, 49$
    ld   a, b
    add  a, a
    add  a, a
    add  a, #192
    ld   d, a                               ; d = 192 + 4 * width
    ld   a, h
    or   a, a
    jp   nz, 49$
    ld   a, l
    cp   a, d
    jp   nc, 49$                            ; (t >= 176 + 4 * width: out of the window)
    sub  a, d
    add  a, #192
    ld   d, a                               ; d = x of the first entry = t - 4 * width (low byte)
    ld   a, b
    srl  a
    ld   b, a                               ; b = the entries
    ld   a, (_story_scratch + 391)
    rra
    ld   a, (_story_scratch + 394)          ; the other stack's count
    jr   nc, 43$
    ld   a, (_story_scratch + 393)
43$:
    ld   hl, #_story_scratch + 392
    add  a, (hl)
    add  a, b
    cp   a, #17
    jp   nc, 49$                            ; (the pool is full: never in a layout that passed tools/dev/cloud_layout.py)
    ld   a, (_story_scratch + 391)
    rra
    ld   a, (hl)                            ; n
    jr   nc, 44$
    cpl
    add  a, #17
    sub  a, b                               ; (the odd stack: 16 - n - entries)
44$:
    ld   l, a                               ; l = the first entry's index
    ld   a, (_story_scratch + 392)
    add  a, b
    ld   (_story_scratch + 392), a          ; n += entries
    ld   a, l
    add  a, a
    add  a, a
    add  a, #92
    ld   l, a
    ld   h, #0xC0                           ; hl = its place in the shadow OAM
    ld   a, c
    swap a
    and  a, #7
    push hl
    ld   hl, #_scl_tile
    add  a, l
    ld   l, a
    jr   nc, 45$
    inc  h
45$:
    ld   a, (hl)                            ; a = the shape's first tile
    pop  hl
    bit  7, c
    ld   c, #1                              ; prop: the cloud palette
    jr   z, 46$
    add  a, b
    add  a, b
    sub  a, #2                              ; (flipped: the last column's tile first)
    ld   c, #0x21
46$:
47$:
    ld   (hl), e
    inc  hl
    ld   (hl), d
    inc  hl
    ld   (hl+), a
    ld   (hl), c
    inc  hl
    push af
    ld   a, d
    add  a, #8
    ld   d, a
    pop  af
    bit  5, c
    jr   nz, 48$
    add  a, #2
    jr   50$
48$:
    sub  a, #2
50$:
    dec  b
    jr   nz, 47$
49$:
    pop  de
    pop  bc
    pop  hl
60$:
    inc  hl
    inc  hl
    dec  b
    dec  b
    jp   nz, 30$
69$:
    pop  bc
70$:
    inc  b
    inc  b
    jp   20$
90$:                                        ; done: the stack's count, and the entries of its last build that are not needed
    ld   a, (_story_scratch + 391)
    and  a, #1
    ld   c, a
    ld   a, (_story_scratch + 392)
    ld   b, a                               ; b = n
    ld   hl, #_story_scratch + 393
    ld   e, c
    ld   d, #0
    add  hl, de
    ld   a, (hl)
    ld   d, a                               ; d = the count of the last build
    ld   (hl), b
    ld   a, d
    sub  a, b
    ret  z
    ret  c
    ld   e, a                               ; e = entries to clear
    bit  0, c
    jr   z, 91$
    ld   a, #16
    sub  a, d
    jr   92$
91$:
    ld   a, b
92$:
    add  a, a
    add  a, a
    add  a, #92
    ld   l, a
    ld   h, #0xC0
93$:
    ld   (hl), #0
    inc  hl
    inc  hl
    inc  hl
    inc  hl
    dec  e
    jr   nz, 93$
    ret
__endasm;
}
#else
static void cl_half(uint8_t par) {
    uint16_t kx, t;
    uint8_t r, r1, i, e, s, w4, k, y, tl, n = 0, b4, sh, fl, ent, old, other, pos4;
    OAM_item_t *o;
    kx = ((((uint16_t)(V(V_BOTTOM) >> 1) & 15) << 5) | (V(V_TICK) >> 3)) + 16 - g16(V_CAMX);
    kx &= 511;
    b4 = (uint8_t)(kx >> 2) + 2;
    r = g16(V_CAMY) >= 16 ? (g16(V_CAMY) - 16) >> 4 : 0;
    r1 = (uint8_t)((g16(V_CAMY) + 159) >> 4);
    if (r1 > SCL_ROWS - 1) r1 = SCL_ROWS - 1;
    if ((r ^ par) & 1) r++;
    old = CLN(3 + par); other = CLN(4 - par);
    for (; r <= r1; r += 2) {
        y = (uint8_t)((r << 4) + 16 - V(V_CAMY));
        if (V(V_WH) && y < 240 && y > V(V_WY) && y < (uint8_t)(V(V_WY) + V(V_WH) + 16)) continue;     // (under the window layer)
        if (!y) y = 1;
        for (i = scl_rowstart[r], e = scl_rowstart[r + 1]; i < e; i += 2) {
            pos4 = scl_rec[i]; sh = scl_rec[i + 1]; w4 = sh & 15;
            s = (pos4 + b4) & 127;
            if (s >= 51 && (uint8_t)(s + w4) < 128) continue;       // (not near the window)
            t = (((uint16_t)(pos4 + w4)) << 2) + kx;
            t &= 511;
            if (!t || t >= 192 + (w4 << 2)) continue;
            ent = w4 >> 1;
            if (other + n + ent > N_POOL) continue;
            o = shadow_OAM + OAM_CLOUDS + (par ? N_POOL - n - ent : n);
            n += ent;
            tl = scl_tile[(sh >> 4) & 7]; fl = 1;
            if (sh & 0x80) { tl += w4 - 2; fl = 0x21; }
            s = (uint8_t)t - (w4 << 2);
            for (k = ent; k; k--, o++, s += 8) {
                o->y = y; o->x = s; o->tile = tl; o->prop = fl;
                if (fl & 0x20) tl -= 2; else tl += 2;
            }
        }
    }
    CLN(3 + par) = n;
    if (old > n) {
        o = shadow_OAM + OAM_CLOUDS + (par ? N_POOL - old : n);
        for (k = old - n; k; k--, o++) o->y = 0;                   // (the entries of the stack's last build that are not needed now)
    }
}
#endif

// The live pool entries move with the camera (dx, dy: how far the map slid on the screen) and the drift. A live entry's y is never 0. (The C twin is the loop below the #else.)
#if ASM_CLOUD
static void cl_shift(int8_t dx, int8_t dy) __naked {
    (void)dx; (void)dy;
__asm
    ld   c, a
    ld   b, e
    ld   hl, #_shadow_OAM + 92              ; OAM_CLOUDS * 4
    ld   e, #16                             ; N_POOL
1$:
    ld   a, (hl)
    or   a, a
    jr   z, 2$
    add  a, b
    jr   nz, 3$
    inc  a
3$:
    ld   (hl+), a
    ld   a, (hl)
    add  a, c
    ld   (hl+), a
    inc  hl
    inc  hl
    jr   4$
2$:
    inc  hl
    inc  hl
    inc  hl
    inc  hl
4$:
    dec  e
    jr   nz, 1$
    ret
__endasm;
}
#else
static void cl_shift(int8_t dx, int8_t dy) {
    uint8_t k, y;
    OAM_item_t *o = shadow_OAM + OAM_CLOUDS;
    for (k = 0; k < N_POOL; k++, o++) {
        y = o->y;
        if (!y) continue;
        y += dy;
        o->y = y ? y : 1;
        o->x += dx;
    }
}
#endif

// both stacks again (the map was entered, a window layer came or went or is up)
void cl_all(void) BANKED {
    cl_half(0);
    cl_half(1);
}

// smap_enter: the pool is empty and built from the clock and the camera
void cl_init(void) BANKED {
    uint8_t k;
    for (k = 0; k < N_POOL; k++) shadow_OAM[OAM_CLOUDS + k].y = 0;
    shadow_OAM[39].y = 0; CL_ON = 1; CL_PX = V(V_CAMX); CL_PY = V(V_CAMY);
    CLN(3) = 0; CLN(4) = 0;
    cl_all();
}

// Every frame (dx, dy: how far the camera slid the map on the screen since the last). The clock (V_TICK, and V_BOTTOM's bits 1-7 count its wraps) is the drift's.
void cl_tick(void) BANKED {
    uint8_t tk = V(V_TICK), e = !(tk & 7), dx = CL_PX - V(V_CAMX), dy = CL_PY - V(V_CAMY);
    CL_PX = V(V_CAMX); CL_PY = V(V_CAMY);
    if (!tk) V(V_BOTTOM) += 2;
    if (dx | dy | e) cl_shift(dx + e, dy);
    if (V(V_WH)) cl_all();
    else if (!(tk & 3)) cl_half((tk >> 2) & 1);                 // (one stack on every 4th frame: each row is seen again every 8 frames)
}

// the clouds go (the beam-up has OAM 23-31; the map is left): none stays in the shadow OAM for the next screen
void cl_off(void) BANKED {
    uint8_t k;
    for (k = 0; k < N_POOL; k++) shadow_OAM[OAM_CLOUDS + k].y = 0;
    CL_ON = 0; CL_PX = 0; CL_PY = 0; CLN(3) = 0; CLN(4) = 0;
}
#endif
