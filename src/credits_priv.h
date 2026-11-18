// The credits' private state, shared by src/credits.c and src/credits_load.c (the card loads, a bank of their own: credits.c's was full). No code of its own; everything is in story_scratch.
#ifndef CREDITS_PRIV_H
#define CREDITS_PRIV_H
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "game.h"
#include "palettes.h"
#include "story.h"
#include "credits_text.h"
#include "asm_cfg.h"
#ifndef CT_SPLIT
#define CT_SPLIT 0                                         // (credits_text.h: CRSPLIT=1)
#endif
#ifndef CT_ZN
#define CT_ZN 0
#endif
extern uint8_t overlay_on, joy, story_phase;

#define CR_FIRST      18      // the roll's first row, in world rows (just under the screen)
#define CR_AHEAD      20      // rows are kept written up to T + CR_AHEAD (T: the top row of the screen)
#define CR_BAND       CT_ROLL2_BAND   // the roll's row where the sprites' band starts (4 rows); this variant's roll has a blank row after each line of an entry
#define CR_T_P       100      // the patrons' OBJ tiles: 3 variants x 6 (OBJ ids 100-117, in dgag.c's patron range)
#define CR_T_D        56      // Dregs's 8 OBJ tiles
#define CR_T_HAT      64      // the topper (8x16)
#define CR_T_BOSS    146      // BG ids: the boss's tile pairs (top, bottom; 29 at most, 58 tiles); the scroll's own slot (portraits 93-145: 53 tiles at most, boss 146-203, DMG text 204-255)
#define CR_RING_T     93      // BG ids of the roll's text: a ring of CT_RING tiles (the roll shows no portrait or boss)
#define CR_HDR_T     160      // the venue header's tiles (17 at most), kept through its venue's three cards
#define CR_TXT_T     178      // a card's text tiles, up to 255
#define CR_BT_X      120      // the Spigoteer's left edge in the roll; the robots stand at 24, 56, 88
#define OBJPAL_ROBOT   5
#define OBJPAL_CAST    3      // Dregs's, the topper's
#define BGPAL_BOSS     5
#define BGPAL_HDR      6      // the venue header's BG palette (CGB): a copy of the HUD's, the fades leave it alone within a venue
#define COL_GOLD  0x231E      // RGB15(30, 24, 8): the labels (palette 0 colour 1)
#if CT_SPLIT
#define COL_BAND  0x0C21      // RGB15(1, 1, 3): the roll's one black #080818 (tools/gen_credits.py NAVY: the band the HUD palette had, colour 3 of every BG palette), the bosses' colour 0
#else
#define COL_BAND  0x2043      // RGB15(3, 2, 8): the band (colour 3 of the HUD palette), the bosses' colour 0
#endif
#define DMG_HAT_OBP1  0x93    // the topper on the band: its three shades one step lighter (idx 1 white, 2 light, 3 dark; the DMG boss body is remapped the same way)

#define CR_SLOT(p) (CT_SCENEFMT ? (p) : cr_scene_slot[(p)])   // (CRSCENE: a scene page's palette number is its BG slot; CRMAP's go to the free ones)
static const uint8_t cr_scene_slot[7] = { 2, 3, 4, 6, 7, 5, 1 };   // a scene's palettes' BG slots: the free ones, then the previous boss's (5) and the HUD's (1), written once his body and name have scrolled off
#if CT_SCENEFMT
#define CR_SIGM 0x3FFF
#else
#define CR_SIGM 0x1FFF
#endif
#define CR_SOLID_ID  77     // CRMAP: the four flat tiles of the buildings (BG ids 77-80, both machines)
#define CR_BLD_PAL    6     // CRMAP: the building's BG palette (a venue's title page: the portraits' 2-4, the boss's 5 are not on it)
#define CR_CARDS      (CT_MAPFMT ? 43 : 33)      // the title, the Spigoteer, Dregs, then three cards for each of the ten venues (CRMAP proposal: four, the venue's title page first)
#define CR_SHARE      392     // the tune's units: 1/392 of it (24.7 frames of the 162 s tune)
#define CR_UNIT_PAT    11     // a patron card's units (owner Q80: held longer, to read all eight names); the other cards 7
#define CR_UNIT_END   362     // the roll ends at this unit, "THANKS FOR PLAYING!" fills the rest
#define CR_PIC_FRAMES 9692    // the cast and the roll run on their own clock: this many frames (162 s). The tune is 10700 frames (178 s; 15 frames a row, slowed from 14 on the owner's word 2026-11-13, so that it ends after the roll's text is done): the roll waits for it to end (credits_update; owner 2026-11-05: the tune is never stretched to fit)

// state in story_scratch
// The scrolling credits: one continuous vertical roll of the cast and then the text roll, no fade between them. See the block "the scrolling credits" below. 1 px every 2 frames.
struct cr_state {
    uint8_t row[20];          // the row being built (queued rows are read at VBlank)
    uint16_t scroll;          // world px scrolled, as the picture shows it (SCY moves in the VBlank only)
    uint16_t pos;             // the timeline's position (px): scroll catches up with it in the VBlank
    uint16_t next;            // the next world row to build
    uint16_t t;               // frames on the screen
    uint16_t gs;              // the world row card gc starts at
    uint16_t wroll;           // the world row the roll's own row 0 stands on
    uint16_t lw;              // the world row the text step is building
    uint16_t ss;              // the world row card sc (the sprites' cursor) starts at
    uint16_t ts;              // the world row the stop's card (k) starts at
    uint16_t ph;              // frames in the timeline's state
    uint8_t from_story, gc, gl, sc, live, pb, pp, bn, bp, pose, ft, ls, rt, ld, lr, skipq, txs, txd, phase, pq, pr;
    uint8_t k, st, nc, rr;    // the timeline: the stop's card, its state (0 hold, 1 glide, 2 the text roll, 3 its end), the glide's cruise frames and the px its ramps leave over
    uint16_t sig;             // the sprites' last drawn state (scroll, animation step), with sig2 (card loads, boss pose): a frame that changes neither leaves OAM as it is
    uint8_t sig2;
    // gc: the card being built (33: the roll), gl: its loads done (units; 255: all), live: the colours go to the hardware as they are made, pb / pp: the portrait's first BG tile / BG palette,
    // rt: the text ring's next tile
};
#define CR ((struct cr_state *)story_scratch)
// (story_scratch + 68 / + 69: the DMG header's BGP and the card's, main.c cast_isr)
#define CR_PAL ((uint8_t *)story_scratch + 72)                          // the card's colours (CGB: 128 bytes; DMG: BGP, OBP0, OBP1, the first OBP1)
#define CR_PT  ((portrait_t *)(story_scratch + 200))                    // the owner's portrait (while a venue card is built)
#define CR_PT_B ((uint8_t *)story_scratch + 200)       // CRSCENE: the scene page's meta (n objects, OBJ palettes, tiles, then 3 bytes an object), where the owner's portrait used to be
#ifndef CR_RING_C
#define CR_RING_C 127                                  // CRSCENE, Color: the text ring is bank 1 ids 0-126 (BG ids 128-255 of bank 1 are the OBJ tiles 128-255 there: the Color looks)
#endif
#ifndef CR_NOGATE
#define CR_NOGATE 0
#endif
#ifndef CR_ISRRES
#define CR_ISRRES 40
#endif
#define CR_SH_DIRTY 212                                // CRSPLIT: the card set's RAM copy (CR_PAL) is ahead of the hardware
#define CR_SH_HW 213                                   //          which set the hardware holds at the end of the frame: 0 the cards', 1 the page's
#define CR_SH_TOP 214                                  //          which set the top of the screen shows this frame
#define CR_SH_LINE 215                                 //          the line the interrupt swaps at (255: none)
#define CR_SH_LO 217                                   //          the page's objects on the screen: from, up to (in the order they enter)
#define CR_SH_HI 218
#define CR_SH_V 219                                    //          the first venue whose page the plan has not left behind
#define CR_SH_DIR 216                                  //          0: cards' -> page's, 1: page's -> cards'
#define CR_BUF ((uint8_t *)story_scratch + 200 + sizeof(portrait_t))    // 64 bytes: four tiles on their way, the owner's name
#define CR_ATT (CR_BUF + 64)      // the row's CGB attributes (20 bytes), then the Spigoteer's OBJ palette 0 (8 bytes)
#define CR_SAVE (CR_ATT + 20)
typedef char cr_fits[(sizeof(struct cr_state) <= 68 && 200 + sizeof(portrait_t) + 64 + 28 <= STORY_SCRATCH) ? 1 : -1];
enum { CK_TITLE, CK_SPIGOTEER, CK_DREGS, CK_OWNER, CK_PATRONS, CK_BOSS, CK_VENUE };
#define CR_TXT_D    204
#define CR_TXT_DN    52
#define CR_DMGID(id) ((id) < CR_TXT_DN ? CR_TXT_D + (id) : (id) - CR_TXT_DN < 54 ? (id) - CR_TXT_DN : (id) - CR_TXT_DN + 1)
#define CR_TXT_CN   CR_RING_C
#if CT_SPLIT
// CRSPLIT: the pages need more text tiles at once than 127 (the round-8 pages: 133, with the cards around them 147). Verified free for the length of the card section by
// tools/dev/credits_vram_owners.py (a canary in every BG id: nothing writes them, nothing shows them): Color bank 0 ids 204-255, DMG ids 80-92, 138-145 and 202-203 (23). The roll keeps its 127.
static uint8_t cr_rn(void) { return CR->next >= CR->wroll ? 127 : is_cgb ? 127 + 52 : 127 + 23; }
static uint8_t cr_pid(uint8_t i) {                 // a ring slot's BG tile id (Color: slots 0-126 bank 1 ids 0-126, the rest bank 0 ids 204-255)
    if (is_cgb) return i < 127 ? i : i - 127 + 204;
    if (i < 127) return CR_DMGID(i);
    i -= 127;
    return i < 13 ? 80 + i : i < 21 ? 138 - 13 + i : 202 - 21 + i;
}
#define CR_BK(i) ((i) < 127 ? 8 : 0)
#else
#define cr_rn() (is_cgb ? CR_TXT_CN : CT_RING_N)
#define cr_pid(i) (is_cgb ? (i) : CR_DMGID(i))
#define CR_BK(i) 8
#endif
#if CT_SCENEFMT
#define CR_OAM_PAT 24                                // CRSCENE: the patrons' OAM entries 24-39 (the page's objects take 0-29: the first to leave the screen share 24-29), the boss's topper 12
#define CR_OAM_HAT 12
#define CR_OAM_SPG 32                                // (the Spigoteer's and Dregs's four: where the patrons' sprites will be, not yet)
#define CR_OAM_DRG 36
#else
#define CR_OAM_PAT 8
#define CR_OAM_HAT 24
#define CR_OAM_SPG 0
#define CR_OAM_DRG 4
#endif
#define CR_SWAPN 1                                  // CRSCENE: palettes a frame while the screen is blank (a load or a swap)
#define CR_SH_BG 100                                   // CRSCENE: the page's BG palettes (8 x 8 bytes) and OBJ palettes (6 x 6: colours 1-3), as the hardware takes them, in the portrait area (meta 3 + 3 per object: 93 at most; to 200 of its 227)
#define CR_SH_OB 164                                   // (six OBJ palettes of eight bytes: colour 0 is 0, as the hardware takes them; to 211)
#ifndef CR_NPRE_S
#define CR_NPRE_S 40
#endif
#define CR_NPRE (CT_SPLIT ? CR_NPRE_S : 96)                                    // CRSCENE: the page's tiles put in the ring before its rows (the ring holds 127: the card on the screen keeps the rest; CRSPLIT: 40, the page shares the screen with the name rows above it, 100 overwrote their tiles and 70 was clean)
#define CR_PT_NP 96                                  // (CR_PT_B[96]: how many of them this page has)
#define PBASE (CR->pb)
#define PPAL  (CR->pp)
#define OBJPAL_TOP 0       // the topper's OBJ palette: 0 (the Spigoteer's, restored before the roll), as patrons use 1-7 and the next card's patrons are on the screen with a boss
static const uint8_t cr_bdx[10] = CT_BDX;          // each boss's body and topper moved right by this many px (tools/gen_credits.py BOSS_DX: his ink box centred on x 80)
#define CR_GW(v) (CR->bn + ((cr_bdx[v] + 7) >> 3))    // the columns of his tiles once moved
#endif
