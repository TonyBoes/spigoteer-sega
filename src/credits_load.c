// The credits' card loads (credits.c cr_gen): one unit of a card's tiles, palettes and sprites a call, in a bank of its own (credits.c's was full). The state is credits_priv.h's.
#pragma bank 255
#include "credits_priv.h"
#include "music.h"
void cr_hw_b(uint8_t obj, uint8_t i) BANKED;           // (credits.c: palette i to the hardware)
static void cr_pal(uint8_t obj, uint8_t i, const uint16_t *p) {   // CGB: palette i of the BG (obj 0) or OBJ (1) set (credits.c's, the same)
    uint16_t *q = (uint16_t *)(CR_PAL + (obj ? 64 : 0) + i * 8);
    q[0] = BRIGHTEN(p[0]); q[1] = BRIGHTEN(p[1]); q[2] = BRIGHTEN(p[2]); q[3] = BRIGHTEN(p[3]);
#if CT_SPLIT
    CR_PT_B[CR_SH_DIRTY] = 1;
#else
    if (CR->live) cr_hw_b(obj, i);
#endif
}

static const uint8_t cr_owner[10] = { 2, 3, 4, 5, 6, 7, 11, 8, 10, 9 };   // the venue owner's speaker id (tools/gen_story.py SPEAKERS): Sadie, Coach, June, Colby, Aurora, Manager-Bot, Granny, Hana, Kiki, Zizz
static const uint8_t cr_bpose[10][3] = CT_BPOSE;      // each boss's three poses (boss.h BP_*; slot 0 WALK, slot 1 STOMP: the topper's bob), cycled 0 1 2 1, 16 frames each (tools/gen_credits.py BOSS_POSES)
uint8_t boss_big_tex_cast(uint8_t cmd, uint8_t a, uint8_t b, uint8_t *dst) BANKED;      // each boss file's cast accessor (src/boss_load.h BOSS_CAST_FN)
uint8_t boss_mascot_cast(uint8_t cmd, uint8_t a, uint8_t b, uint8_t *dst) BANKED;
uint8_t boss_sasquatch_cast(uint8_t cmd, uint8_t a, uint8_t b, uint8_t *dst) BANKED;
uint8_t boss_critic_cast(uint8_t cmd, uint8_t a, uint8_t b, uint8_t *dst) BANKED;
uint8_t boss_yeti_cast(uint8_t cmd, uint8_t a, uint8_t b, uint8_t *dst) BANKED;
uint8_t boss_prototype_cast(uint8_t cmd, uint8_t a, uint8_t b, uint8_t *dst) BANKED;
uint8_t boss_duke_cast(uint8_t cmd, uint8_t a, uint8_t b, uint8_t *dst) BANKED;
uint8_t boss_sumo_cast(uint8_t cmd, uint8_t a, uint8_t b, uint8_t *dst) BANKED;
uint8_t boss_leo_cast(uint8_t cmd, uint8_t a, uint8_t b, uint8_t *dst) BANKED;
uint8_t boss_mothership_cast(uint8_t cmd, uint8_t a, uint8_t b, uint8_t *dst) BANKED;
// his body for the card from his own art file (the fight's tiles, poses, topper and colours): cmd 0: body chunk a (4 tiles) to dst, the tiles
// copied; 1: the column b of pose a: its tile pair; 2: the topper's four tiles to dst; 3: dst = columns, pairs, then his colours 1-3 (3 x LE)
static uint8_t cr_boss(uint8_t v, uint8_t cmd, uint8_t a, uint8_t b, uint8_t *dst) {
    switch (v) {
    case 0: return boss_big_tex_cast(cmd, a, b, dst);
    case 1: return boss_mascot_cast(cmd, a, b, dst);
    case 2: return boss_sasquatch_cast(cmd, a, b, dst);
    case 3: return boss_critic_cast(cmd, a, b, dst);
    case 4: return boss_yeti_cast(cmd, a, b, dst);
    case 5: return boss_prototype_cast(cmd, a, b, dst);
    case 6: return boss_duke_cast(cmd, a, b, dst);
    case 7: return boss_sumo_cast(cmd, a, b, dst);
    case 8: return boss_leo_cast(cmd, a, b, dst);
    }
    return boss_mothership_cast(cmd, a, b, dst);
}

static void cr_remap(uint8_t *b, uint8_t n) {     // DMG: n bytes of tiles with the shades one step on (0 -> 3, the band; 1 -> 0; 2 -> 1; 3 -> 2): v - 1, a plane at a time
    uint8_t i, lo;
    for (i = 0; i < n; i += 2) {
        lo = ~b[i];                                   // (the low bit always flips; the high bit with it where the low bit was 0)
        b[i + 1] ^= lo;
        b[i] = lo;
    }
}

static uint8_t cr_spk(uint8_t c, uint8_t v) { return c == CK_SPIGOTEER ? 0 : c == CK_DREGS ? 1 : cr_owner[v]; }
static void cr_bfetch(uint8_t v, uint8_t pose, int8_t c, uint8_t r, uint8_t *d) {      // the body tile in column c, row r of a pose (blank outside his columns)
    uint8_t k;
    if (c < 0 || c >= CR->bn) { for (k = 0; k < 16; k++) d[k] = 0; return; }
    cr_boss(v, 0, 2 * cr_boss(v, 1, pose, c, 0) + r, 0, d);
}
static void cr_btile(uint8_t v, uint8_t u, uint8_t *buf) {       // unit u of his body: pose u / (2 w), column, row: the tile moved right by cr_bdx px (the tile to its left spills in)
    uint8_t w = CR_GW(v), S = cr_bdx[v], s = S & 7, p = u / (2 * w), q = u - p * 2 * w, k;
    int8_t c = (int8_t)(q >> 1) - (int8_t)(S >> 3);
    p = cr_bpose[v][p];
    cr_bfetch(v, p, c, q & 1, buf);
    if (s) {
        cr_bfetch(v, p, c - 1, q & 1, buf + 16);
        for (k = 0; k < 16; k++) buf[k] = buf[k] >> s | buf[16 + k] << (8 - s);
    }
}

uint8_t credits_load_unit(uint8_t kd, uint8_t v, uint8_t i) BANKED {   // unit i of a card of kind kd (cr_kind: CK_*), venue v; 1: there are no more
    uint8_t k, n, nch, *buf = CR_BUF;
    uint16_t p[4], bg;
    portrait_t *pt = CR_PT;
#if CT_MAPFMT
    if (kd == CK_VENUE) {                          // its palettes: BG 6 the building's, BG 0 the band's colour (the label's gold) as the owner's card will have it
        if (i < 5 && is_cgb) {                     // the scene's palettes (the map's own, one for each its cells name: BG 2, 3, 4, 6, 7; the owner's portrait colours wait in RAM until the scene is off the screen)
            if (i < ct_snp[v]) {
                for (n = 0; n < 4; n++) p[n] = ct_scol[v][i][n];
                if (!v && i > 2) { uint8_t lv = CR->live; CR->live = 0; cr_pal(0, cr_scene_slot[i], p); CR->live = lv; CR->ft |= 8; }   // (the first scene follows Dregs, whose portrait is BG 5-7: 6 and 7 go to the hardware when he is off)
                else cr_pal(0, cr_scene_slot[i], p);
            }
            return 0;
        }
        if (i == 5 && is_cgb) {
            uint16_t *q = (uint16_t *)CR_PAL, *hq = (uint16_t *)(CR_PAL + 8 * BGPAL_HUD);
            q[0] = hq[0]; q[1] = BRIGHTEN(COL_GOLD); q[2] = BRIGHTEN(ct_bandcol[v]); q[3] = hq[3];
            if (CR->live) cr_hw_b(0, 0);
            return 0;
        }
        return 1;
    }
#endif
#if CT_SCENEFMT
    if (kd == CK_OWNER) {                          // the scene page's loads: unit 0 its meta (RAM: the sprites' x, y, tile, flags), then its sprite tiles, then (Color) its OBJ palettes
        uint8_t tn = CR_PT_B[2], nm;
        if (i == 0) { credits_scene_get(v, 3, 0, CR_PT_B); CR->ft &= 7; CR_PT_B[CR_SH_LO] = CR_PT_B[CR_SH_HI] = 0; return 0; }
        nm = (3 + 3 * CR_PT_B[0] + 31) >> 5;           // (the meta comes in 32-byte units)
        if (i < nm) { credits_scene_get(v, 3, i, CR_PT_B + 32 * i); return 0; }
        i -= nm;
        tn = CR_PT_B[2];
        if (i < tn) { credits_scene_get(v, 0, i, buf); set_sprite_data(i, 1, buf); return 0; }
        i -= tn;
        {                                          // the page's first CR_NPRE tiles into the ring now, in the order its rows first use them: the rows then need no tile put (CR->rt stays where the page's rows will start)
            uint8_t np = credits_scene_get(2 * v + (is_cgb ? 1 : 0), 4, 0, buf), id;
            if (np > CR_NPRE) np = CR_NPRE;
            CR_PT_B[CR_PT_NP] = np;
            if (i < np) {
                credits_scene_get(2 * v + (is_cgb ? 1 : 0), 4, i, buf);
                id = CR->rt + i;
                if (id >= cr_rn()) id -= cr_rn();
                if (is_cgb && CR_BK(id)) VBK_REG = VBK_BANK_1;
                credits_tile_put(buf[0] | buf[1] << 8, cr_pid(id)); VBK_REG = VBK_BANK_0;
                return 0;
            }
            i -= np;
        }
        if (i < 8) {                               // the page's eight BG palettes into RAM (CR_SH_BG: the colours as the hardware takes them), where the swap and the split read them: no ROM read, no bank, at the swap
            if (is_cgb) {
                uint16_t *q = (uint16_t *)(CR_PT_B + CR_SH_BG + 8 * i);
                credits_scene_get(v, 1, i, buf);
                for (k = 0; k < 4; k++) q[k] = BRIGHTEN(((uint16_t *)buf)[k]);
            }
            return 0;
        }
        i -= 8;
        if (is_cgb && i < CR_PT_B[1]) {
            uint16_t *q = (uint16_t *)(CR_PT_B + CR_SH_OB + 8 * i);
            credits_scene_get(v, 2, i, buf);
            p[0] = 0; p[1] = buf[0] | buf[1] << 8; p[2] = buf[2] | buf[3] << 8; p[3] = buf[4] | buf[5] << 8;
            q[0] = 0; q[1] = BRIGHTEN(p[1]); q[2] = BRIGHTEN(p[2]); q[3] = BRIGHTEN(p[3]);       // (and its OBJ palettes' colours 1-3)
#if !CT_SPLIT
            cr_pal(1, 1 + i, p);
#endif
            return 0;
        }
        return 1;
    }
#endif
    if (kd == CK_SPIGOTEER || kd == CK_DREGS || kd == CK_OWNER) {
        k = cr_spk(kd, v);
        if (i < 2) { portrait_part(k, i, pt); return 0; }   // the portrait: its header and map, its attributes (portrait_get pumps the timer for over a frame)
        if (i == 2) {                              // its palettes (BG 2-4), the backdrop's colour (the slot of its DMG shade, portrait_backdrop: the top-left tile is all backdrop) the band's
            portrait_part(k, 2, pt);
            if (is_cgb) {
                nch = portrait_backdrop(k);           // (shade 3 backdrop: the outline's colour goes to the band's too, as the story scenes' black backdrop shows it)
                bg = pt->pal[4 * pt->attr[0] + nch];
                for (n = 0; n < pt->npal; n++) {
                    p[0] = pt->pal[4 * n]; p[1] = pt->pal[4 * n + 1]; p[2] = pt->pal[4 * n + 2]; p[3] = pt->pal[4 * n + 3];
                    if (p[nch] == bg) p[nch] = COL_BAND;
#if CT_MAPFMT
                    if (kd == CK_OWNER) { uint8_t lv = CR->live; CR->live = 0; cr_pal(0, PPAL + n, p); CR->live = lv; CR->ft |= 1; }   // (BG 2-4 are the venue scene's while it is on the screen: written when it is gone, credits_update)
                    else
#endif
                    cr_pal(0, PPAL + n, p);
                }
                if (kd == CK_OWNER) {                  // BG palette 0: the labels (colour 1: gold) and the band (colour 2: the venue's); the HUD's colours 0 and 3 (they are brightened already)
                    uint16_t *q = (uint16_t *)CR_PAL, *hq = (uint16_t *)(CR_PAL + 8 * BGPAL_HUD);
                    q[0] = hq[0]; q[1] = BRIGHTEN(COL_GOLD); q[2] = BRIGHTEN(ct_bandcol[v]); q[3] = hq[3];
                    if (CR->live) cr_hw_b(0, 0);
                }
            }
            return 0;
        }
        i -= 3;
        nch = pt->ntiles;
        if (i < nch) {                             // its tiles, one a unit (a byte loop in C is ~70 cycles a byte, a tile 0.07 frame)
            if (is_cgb) portrait_tile_set(k, i, PBASE + i);
            else {
                portrait_tile_copy(k, i, 1, buf);
                nch = portrait_backdrop(k);        // DMG: the backdrop becomes the band's shade 3: 3 stays, 2 and 3 change places (lo ^= hi), 1 and 3 (hi ^= lo); the generator refuses shade 0
                if (nch == 2) for (n = 0; n < 16; n += 2) buf[n] ^= buf[n + 1];
                else if (nch == 1) for (n = 0; n < 16; n += 2) buf[n + 1] ^= buf[n];
                set_bkg_data(PBASE + i, 1, buf);
            }
            return 0;
        }
        if (kd == CK_DREGS && i < nch + 24) {      // his three frames (idle, walk, walk: 24 tiles), a tile at a time, and his palette
            i -= nch;
            dregs_cast_load(CR_T_D, i, 1, p);
            if (is_cgb) cr_pal(1, OBJPAL_CAST, p);
            return 0;
        }
        return 1;
    } else if (kd == CK_BOSS) {
        if (i == 0) {                              // his size and colours; the BG palette 5 with the band as colour 0, the topper's OBJ 3
            cr_boss(v, 3, 0, 0, buf);
            CR->bn = buf[0]; CR->bp = buf[1];
            if (is_cgb) {
                p[0] = COL_BAND; p[1] = buf[2] | buf[3] << 8; p[2] = buf[4] | buf[5] << 8; p[3] = buf[6] | buf[7] << 8;
                cr_pal(0, BGPAL_BOSS, p);
                p[0] = 0;
                cr_pal(1, OBJPAL_TOP, p);
            }
            return 0;
        }
        if (i < 5) { cr_boss(v, 5, i - 1, CR_T_HAT + i - 1, 0); return 0; }   // the topper: still and bobbing (4 tiles, one a unit)
        i -= 5;
        if (i >= 6 * CR_GW(v)) return 1;
        cr_btile(v, i, buf);                       // his body's tiles in his three poses, each moved right by cr_bdx px, a unit each
        if (!is_cgb) cr_remap(buf, 16);            // (DMG: the shades one step on)
        set_bkg_data(CR_T_BOSS + i, 1, buf);
        return 0;
    } else if (kd == CK_PATRONS) {
        n = is_cgb ? 38 : 18;                      // the three base looks' 18 tiles (bank 0), on Color the five Color-only looks' 20 (bank 1), then the palettes
        if (i >= n + (is_cgb ? 7 : 0)) return 1;
        if (i < 18) load_patron_pose0(v, CR_T_P + 6 * (i / 6), ct_slot[v][i / 6], i % 6);      // (a tile at a time: with the LCD on a byte takes two scanlines; the variant in slot k)
        else if (i < n) load_patron_x0(v, (i - 18) >> 2, (i - 18) & 3);
        else if (is_cgb) {                         // OBJ 1-7, one a unit (the hardware's: the HBlanks it takes)
            k = i - n;
            p[0] = 0; p[1] = ct_pcol[v][k][0]; p[2] = ct_pcol[v][k][1]; p[3] = ct_pcol[v][k][2];
            cr_pal(1, 1 + k, p);
        }
        return 0;
    }
    return 1;
}


