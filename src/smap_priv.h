// The story map: what smap.c (the screen) and smap_eng.c (the streaming engine: slots, palettes, lines, camera, region) share. Written by hand; the layout of
// story_scratch is the map's while the map is up (src/scratch.h, tests/test_scratch_map.py).
#ifndef SMAP_PRIV_H
#define SMAP_PRIV_H
#include "order.h"

extern uint8_t smap_stop;
extern uint8_t smap_flags;

#define NSTOPS       11
#define TOWN         10
#define NIL          255
#define FEST_N       3
#define OB           56                       // the map's OBJ tiles start at this id (0-55 are the bartender's, the mugs' and the coin: boot-time tiles)
#define TAG_FRAMES   90
#define TAG_SLIDE    12                       // frames the tag takes to slide in from the right (and out)
#define LYC_NONE     255                      // the window runs to the screen's bottom: no raster interrupt wanted

// ---- story_scratch: the whole of it is the map's while the map is up -----------------------------------------------------------------------------------------
#define SC(o)        (story_scratch + (o))
// region A, 0..395: the tile tables (the two models lay theirs over each other)
#define A_TBL        0       // DMG: 220 bytes: 176 low bytes of the tile id in each slot, then 44 bytes of the 2-bit highs (0x3FF: free)
#define A_CNT        220     // DMG: 176 use counts (cells of the region that show the slot's tile)
#define A_NIB        0       // Color: 176 bytes: the variant resident in each of the 352 slots, a nibble each (15: none)
#define A_PCNT       176     // Color: 23 x u16: the cells of the region in each palette (the table: SMAPW_NPAL = 23 palettes: ZOOGATE is the 23rd; the layout has room for 25)
#define A_PSLOT      222     // Color: 23 bytes: the hardware slot of each palette (255: none)
#define A_PUSE       245     // Color: 8 bytes: the palette in each hardware slot (255: free)
#define A_ATTR_UI    253     // Color: 20 bytes: the window layer's attribute row (the town palette's slot)
#define A_IDA        273     // Color: 22 bytes: the attribute bytes of the cells being written
#define A_PEND       295     // Color: 2 bytes (free between the attribute bytes and the staging): the palette hand-over's borrower (NIL: none; bit 5: the lender's cells have left, the hand-over is due), the borrowed line (bit 7: a column)
#define A_XSTG       301     // Color: 5 tiles of staging (80 bytes, on the first 16-byte boundary at or after this; DMA reads them; the DMG's tables lie here). story_scratch is at 0xD373, so 301 is
                             //   already on a boundary and the staging is 301..381 (tests/test_scratch_map.py checks that); the worst case, a staging moved up by 15, still ends at S_V
#define A_PSTG       381     // Color: 9 bytes: the palette write (BCPS, then 8 colour bytes), after the staging (23 palettes left no room for it before the staging: 301 stays aligned)
#define NSTG_MAX     (is_cgb ? 5 : 2)
#define S_V          396     // the variables (V_N <= 68)
#define S_T          464     // 56 bytes: tile staging (2 tiles) | the line's tile ids (22) | SCY, SCX; the panel's two rolling rows and the name tag's row lie over the first 40
#define T_TILES      0
#define T_IDS        32
#define T_CAM        54
#define V(n)         (story_scratch[S_V + (n)])
#define PEND         SC(A_PEND)[0]
#define PLN          SC(A_PEND)[1]
enum { V_PANEL, V_SEL, V_ROWS, V_STEP, V_TAG, V_BOTTOM, V_WT, V_ATTR, V_WY, V_WH, V_DONE, V_PREV,
       V_CAMX = 12, V_CAMY = 14, V_FX = 16, V_FY = 18,                         // the camera's and Sal's feet's pixel positions in the world (16 bit each)
       V_WALK = 20, V_LEG, V_REV, V_WK, V_DEST, V_TICK,                        // the walk: on, the leg, walked backwards, the waypoint heading for, the stop heading for
       V_C0, V_C1, V_R0, V_R1,                                                 // the region (cells; V_C1 = V_C0 - 1: no columns yet)
       V_JK, V_JI, V_JA, V_JN, V_JP,                                           // the add job: none / column / row, the line's index, its first cell, its length, the next cell
       V_DK, V_DI, V_DA, V_DN, V_DP,                                           // the drop job: the same
       V_STATE, V_DIRECT, V_NSTG, V_RES, V_RESE, V_STALL, V_RR, V_UIPAL, V_PALQ, V_DIRX, V_DIRY, V_WXB,
       V_BF, V_BCAP, V_PWL, V_PWH, V_LIMC, V_LIMQ, V_BM, V_BMODE, V_ID, V_NDISP, V_CS, V_SLOW, V_DOTS, V_LAG, V_FULL, V_BEAM, V_N };   // (V_BF..V_ID: the DMG burst's parameters, smap_burst)
typedef char smap_scratch_fits[(S_V + V_N <= S_T && S_T + 56 <= STORY_SCRATCH && A_IDA + 22 <= A_PEND && A_PEND + 2 <= A_XSTG && A_XSTG + 80 <= A_PSTG && A_PSTG + 9 <= S_V && A_XSTG + 15 + 80 <= S_V
                                && A_ATTR_UI + 20 <= A_IDA && A_PUSE + 8 <= A_ATTR_UI && A_PCNT + 2 * 23 <= A_PSLOT && A_PSLOT + 23 <= A_PUSE && A_CNT + 176 <= S_V && T_CAM + 2 <= 56 && T_IDS + 22 <= T_CAM) ? 1 : -1];
#define PANBUF       (S_T)                                          // the panel's rolling rows (2 x 20 bytes)
#define J_NONE       0
#define J_COL        1
#define J_ROW        2
enum { P_NONE, P_TOWN, P_VENUE, P_FEST, P_NUDGE, P_MENU, P_RESUME };

static void fill(uint8_t *d, uint8_t v, uint8_t n) { while (n--) *d++ = v; }
static uint16_t g16(uint8_t n) { return V(n) | ((uint16_t)V(n + 1) << 8); }
static void s16(uint8_t n, uint16_t v) { V(n) = (uint8_t)v; V(n + 1) = (uint8_t)(v >> 8); }

extern uint8_t story_chapter, save_lock;
// How far the map is open: the story's progress, or in a debug-select run (nothing saved: the real progress stays) the chapter being played, so that the quit lands on its stop
// (a stop is a CHAPTER, a place in the story's order, as progress is; story_chapter is the VENUE being played: src/order.h POS(venue) is its chapter, VEN(chapter) the venue; the debug-select run opens the chapter being played)
static uint8_t map_progress(void) { uint8_t c = story_chapter & 0x7F; return save_lock == SAVE_LOCK_DEBUG && c < NSTOPS - 1 && POS(c) > story_progress ? POS(c) : story_progress; }
static uint8_t open_stop(uint8_t s) { return s == TOWN || s <= map_progress(); }

// ---- the VBlank copy list: entries the list's own vq_add cannot name (a raw address), with its tally ---------------------------------------------------------
typedef struct { uint8_t n, bank; const uint8_t *src; uint8_t *dst; uint8_t pad[2]; } vq_entry_t;   // (render.c's list entry)
extern vq_entry_t vq[];
#define VQ_USE       22                       // entries a frame may add (the list holds 24; the panel and the tag take their own through vq_add)
#define SMAP_VQ_MAX 24                                // (render.c VQ_MAX: the list's entries)

// The frame's spare time: the first slow job (a cell that needs a lookup or a load) of a frame always runs, the next ones only before line LY_WORK (a frame that starts late, in the
// VBlank, counts as new). What does not get done waits a frame: the camera waits for the lines it needs.
#define LY_WORK 50                                    // (Color: double speed, the same work takes half the lines)
#define LY_FIRST 50
#define LY_WORK_C 99
#define LY_FIRST_C 100
#define LY_DOTS  (is_cgb ? 12 : 24)
#define LY_SLOWC 0
#define CAM_LAG  0                                    // Sal waits while the camera is behind him at all (px, both axes together): it never is, when the region keeps up
// (the first slow job of a frame waits for the line LY_FIRST only while Sal walks with the camera in step: standing, or with the camera behind, it always runs: no deadlock)
static uint8_t ly_ok(uint8_t slow) {      // slow: the cell that comes needs a lookup or a load (the C path: up to about 40 lines for one)
    uint8_t l = LY_REG, lim = V(V_SLOW) ? (is_cgb ? LY_WORK_C : LY_WORK) : (!V(V_WALK) || (V(V_LAG) & 1)) ? 255 : (is_cgb ? LY_FIRST_C : LY_FIRST);
    if (lim != 255 && (V(V_DOTS) || (V(V_LAG) & 2))) lim -= LY_DOTS;      // (the still sprites will be drawn in full this frame: that takes about 30 lines)
    if (lim != 255 && slow) lim -= LY_SLOWC;
    return (l >= 144 && l < 150) || l < lim;
}

static void qraw(uint8_t bank, const uint8_t *src, uint16_t dst, uint8_t n) {
    vq_entry_t *e;
    if (vq_count >= VQ_USE + 2) return;       // (cannot happen: every caller checks its room first)
    e = &vq[vq_count++];
    if (qv_cost <= VQ_DRAIN_BUDGET) qv_cost += n + 3 + (bank << 1);
    e->n = n; e->bank = bank; e->src = src; e->dst = (uint8_t *)dst;
}

// A special entry for the copy list (bank bit 0 = the VRAM bank): smap_isr, a second VBlank handler that only the map registers (after vq_vbl), does the work after the drain.
// dst >= 0x9800: n bytes down the map, 32 apart (stride mode); else one 16-byte tile at dst by general-purpose DMA (Color). The drain itself (render.c, shared with every screen and
// left alone) sees a 1-byte copy to an unused I/O address; the real destination and length ride in pad[] (16 bits): bit 15 set: 0x9800 offset in bits 0-9, n - 1 in
// bits 10-14; clear: (dst - 0x8000) / 16. bank bit 1 marks it (smap_isr clears it once done).
static void qsp(uint8_t bank, const uint8_t *src, uint16_t dst, uint8_t n) {
    vq_entry_t *e;
    uint8_t hi = (uint8_t)(dst >> 8);
    if (vq_count >= VQ_USE + 2) return;
    e = &vq[vq_count++];
    if (qv_cost <= VQ_DRAIN_BUDGET) qv_cost += n + 3 + ((bank | 2) << 1);
    e->n = 1; e->bank = bank | 2; e->src = src; e->dst = (uint8_t *)0xFF7F;
    if (hi >= 0x98) { e->pad[0] = (uint8_t)dst; e->pad[1] = 0x80 | ((n - 1) << 2) | (hi & 3); }
    else { e->pad[0] = (uint8_t)(dst >> 4); e->pad[1] = (hi >> 4) & 1; }
    if (vq_count < SMAP_VQ_MAX) vq[vq_count].n = 0;     // (the list's end, for smap_isr's scan)
}

#define GLIDE_LESS 8                                   // (Color, the camera gliding between a stop's resting view and Sal: the drain budget is 8 less, the drain ends before line 153 as a walk's does)
static uint8_t room(void) { uint8_t b = VQ_DRAIN_BUDGET - 5 - (is_cgb && !V(V_WALK) ? GLIDE_LESS : 0); return qv_cost >= b ? 0 : (uint8_t)(b - qv_cost); }      // (5: the camera's scroll entry, queued after the region's work)

static uint16_t tile_addr(uint8_t id) { return id < 128 ? 0x9000 + ((uint16_t)id << 4) : 0x8800 + ((uint16_t)(id - 128) << 4); }
static uint16_t map_addr(uint8_t cx, uint8_t cy) { return 0x9800 + ((uint16_t)(cy & 31) << 5) + (cx & 31); }
static uint8_t pool_id(uint8_t i) { return i < 36 ? i : (uint8_t)(i + 57); }   // the pool: BG ids 0-35 and 93-232 (the generic tiles, the font and the dim letters stay out)

#define CAM_SPD  2                                    // = WALK_SPD: the camera moves with Sal, step for step
#define CAM_MAXX 352                                  // 512 - 160
#define CAM_MAXY (SMAPW_CH * 8 - 144)                 // the world's height less the screen's
#define WALK_SPD 2                                    // px a frame at full pace; the first WALK_EASE frames of a leg and its last WALK_EASE px go at 1
#define WALK_EASE 8
// The pace follows the room the region leaves the camera (smap_room, px) against the cells the line being loaded still needs at the rate it has been loading (V_RATE),
// with WALK_S frames to spare
#define WALK_LINE 20                                  // cells in a line (the room is 8 px or more when the line the stretch wants next is loaded)
#define WALK_S   4
#define WALK_SC  1
#define V_LEN    V_STEP                               // (while Sal walks no panel is up: V_STEP, V_SEL, V_ROWS and V_WT are free, panel_open sets them again) the walk's stretch length
#define V_WPH    V_ROWS                               // the walk's pose clock: timer << 2 | phase (a panel's byte, free while Sal walks)
#define V_RATE   V_SEL                                // cells a frame the add job has been doing
#define WALK_AHEAD 24                                 // px before a corner at which the region starts loading for the next stretch
#define LEAD     1                                    // lines the region loads ahead of the view, in the direction of travel
#define ADD_CAP  8
#define DROP_CAP 6

// the engine (src/smap_eng.c)
uint8_t smap_room(uint8_t horiz, uint8_t up, uint16_t f) BANKED;   // px Sal may walk on along an axis before the camera shows what the region does not hold
uint8_t smap_camera_step(void) BANKED;                 // the camera moves toward Sal where the region covers its view. 1: it moved
void smap_region_work(void) BANKED;                    // the region follows the camera: lines drop, lines load
void smap_cam_target(int16_t *tx, int16_t *ty) BANKED; // where the camera wants to be (Sal at the centre, clamped to the world)
uint8_t smap_stop_side(uint8_t s) BANKED;              // bit 0: the side of the name tag and the venue panel at a stop (1 the bottom, 0 the top); bit 1: the stop has a resting view
void smap_fill_view(uint8_t c0, uint8_t c1) BANKED;    // LCD off: the columns c0..c1 of the view, straight into VRAM (the region starts as that)
void smap_isr(void) BANKED;                            // the map's second VBlank handler (render.c smap_vbl calls it): the special runs of the copy list
void smap_isr_arm(void) BANKED;                        // (smap_enter: before the handlers go in)
void smap_pin_town(void) BANKED;                       // Color: the town palette takes its hardware slot for good (the window layer's)

#endif
