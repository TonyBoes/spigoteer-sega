// The story map: what smap.c (the screen) and smap_eng.c (the streaming engine: slots, palettes, lines, camera, region) share. Written by hand; the layout of
// story_scratch is the map's while the map is up (src/scratch.h, tests/test_scratch_map.py).
#ifndef SMAP_PRIV_H
#define SMAP_PRIV_H

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
#define A_PCNT       176     // Color: 18 x u16: the cells of the region in each palette
#define A_PSLOT      212     // Color: 18 bytes: the hardware slot of each palette (255: none)
#define A_PUSE       230     // Color: 8 bytes: the palette in each hardware slot (255: free)
#define A_ATTR_UI    240     // Color: 20 bytes: the window layer's attribute row (the town palette's slot)
#define A_IDA        260     // Color: 22 bytes: the attribute bytes of the cells being written
#define A_PSTG       282     // Color: 9 bytes: the palette write (BCPS, then 8 colour bytes)
#define S_V          396     // the variables (V_N <= 68)
#define S_T          464     // 56 bytes: tile staging (2 tiles) | the line's tile ids (22) | SCY, SCX; the panel's two rolling rows and the name tag's row lie over the first 40
#define T_TILES      0
#define T_IDS        32
#define T_CAM        54
#define V(n)         (story_scratch[S_V + (n)])
enum { V_PANEL, V_SEL, V_ROWS, V_STEP, V_TAG, V_BOTTOM, V_TOP, V_ATTR, V_WY, V_WH, V_DONE, V_PREV,
       V_CAMX = 12, V_CAMY = 14, V_FX = 16, V_FY = 18,                         // the camera's and Sal's feet's pixel positions in the world (16 bit each)
       V_WALK = 20, V_LEG, V_REV, V_WK, V_DEST, V_TICK,                        // the walk: on, the leg, walked backwards, the waypoint heading for, the stop heading for
       V_C0, V_C1, V_R0, V_R1,                                                 // the region (cells; V_C1 = V_C0 - 1: no columns yet)
       V_JK, V_JI, V_JA, V_JN, V_JP,                                           // the add job: none / column / row, the line's index, its first cell, its length, the next cell
       V_DK, V_DI, V_DA, V_DN, V_DP,                                           // the drop job: the same
       V_STATE, V_DIRECT, V_NSTG, V_RES, V_RESE, V_STALL, V_RR, V_UIPAL, V_PALQ, V_DIRX, V_DIRY, V_WXB,
       V_BF, V_BCAP, V_PWL, V_PWH, V_LIMC, V_LIMQ, V_BM, V_BMODE, V_ID, V_NDISP, V_CS, V_SLOW, V_DOTS, V_LAG, V_FULL, V_N };   // (V_BF..V_ID: the DMG burst's parameters, smap_burst)
typedef char smap_scratch_fits[(S_V + V_N <= S_T && S_T + 56 <= STORY_SCRATCH && A_IDA + 22 <= A_PSTG && A_PSTG + 9 <= S_V
                                && A_ATTR_UI + 20 <= A_IDA && A_CNT + 176 <= S_V && T_CAM + 2 <= 56 && T_IDS + 22 <= T_CAM) ? 1 : -1];
#define PANBUF       (S_T)                                          // the panel's rolling rows (2 x 20 bytes)
#define J_NONE       0
#define J_COL        1
#define J_ROW        2
enum { P_NONE, P_TOWN, P_VENUE, P_FEST, P_NUDGE, P_MENU };

static void fill(uint8_t *d, uint8_t v, uint8_t n) { while (n--) *d++ = v; }
static uint16_t g16(uint8_t n) { return V(n) | ((uint16_t)V(n + 1) << 8); }
static void s16(uint8_t n, uint16_t v) { V(n) = (uint8_t)v; V(n + 1) = (uint8_t)(v >> 8); }

static uint8_t open_stop(uint8_t s) { return s == TOWN || s <= story_progress; }

// ---- the VBlank copy list: entries the list's own vq_add cannot name (a raw address), with its tally ---------------------------------------------------------
typedef struct { uint8_t n, bank; const uint8_t *src; uint8_t *dst; uint8_t pad[2]; } vq_entry_t;   // (render.c's list entry)
extern vq_entry_t vq[];
#define VQ_USE       22                       // entries a frame may add (the list holds 24; the panel and the tag take their own through vq_add)

// The frame's spare time: the first slow job (a cell that needs a lookup or a load) of a frame always runs, the next ones only before line LY_WORK (a frame that starts late, in the
// VBlank, counts as new). What does not get done waits a frame: the camera waits for the lines it needs.
#define LY_WORK 64
#define LY_FIRST 64
#define CAM_LAG  24                                   // Sal waits while the camera is further behind him than this (px, both axes together)
// (the first slow job of a frame waits for the line LY_FIRST only while Sal walks with the camera in step: standing, or with the camera behind, it always runs: no deadlock)
static uint8_t ly_ok(void) { uint8_t l = LY_REG; return l >= 144 || l < (V(V_SLOW) ? LY_WORK : (!V(V_WALK) || V(V_LAG) > CAM_LAG) ? 255 : LY_FIRST); }

static void qraw(uint8_t bank, const uint8_t *src, uint16_t dst, uint8_t n) {
    vq_entry_t *e;
    if (vq_count >= VQ_USE + 2) return;       // (cannot happen: every caller checks its room first)
    e = &vq[vq_count++];
    if (qv_cost <= VQ_DRAIN_BUDGET) qv_cost += n + 3 + (bank << 1);
    e->n = n; e->bank = bank; e->src = src; e->dst = (uint8_t *)dst;
}

static uint8_t room(void) { return qv_cost >= VQ_DRAIN_BUDGET ? 0 : (uint8_t)(VQ_DRAIN_BUDGET - qv_cost); }

static uint16_t tile_addr(uint8_t id) { return id < 128 ? 0x9000 + ((uint16_t)id << 4) : 0x8800 + ((uint16_t)(id - 128) << 4); }
static uint16_t map_addr(uint8_t cx, uint8_t cy) { return 0x9800 + ((uint16_t)(cy & 31) << 5) + (cx & 31); }
static uint8_t pool_id(uint8_t i) { return i < 36 ? i : (uint8_t)(i + 57); }   // the pool: BG ids 0-35 and 93-232 (the generic tiles, the font and the dim letters stay out)

#define CAM_SPD  4
#define CAM_MAXX 352                                  // 512 - 160
#define CAM_MAXY 240                                  // 384 - 144
#define WALK_SPD 1
#define ADD_CAP  4
#define DROP_CAP 4

// the engine (src/smap_eng.c)
uint8_t smap_camera_step(void) BANKED;                 // the camera moves toward Sal where the region covers its view. 1: it moved
void smap_region_work(void) BANKED;                    // the region follows the camera: lines drop, lines load
void smap_cam_target(int16_t *tx, int16_t *ty) BANKED; // where the camera wants to be (Sal at the centre, clamped to the world)
void smap_fill_view(uint8_t c0, uint8_t c1) BANKED;    // LCD off: the columns c0..c1 of the view, straight into VRAM (the region starts as that)
void smap_pin_town(void) BANKED;                       // Color: the town palette takes its hardware slot for good (the window layer's)

#endif
