// Hand-written assembly switches (the asm pass, owner-authorised 2026-10-17).
//
// ASM_PASS = 1 (default): every candidate that has an asm version builds it. ASM_PASS = 0 (`make cfall`, build/game-c.gb): every
// candidate builds its C version, the reference the owner may port to other platforms. Each candidate has its own ASM_<X> switch,
// defaulting to ASM_PASS, so one can be turned off alone (-DASM_F=0).
//
// Rules for a switch:
//  - `#if ASM_<X>` ... `#else` (the C) ... `#endif` goes around FUNCTION BODIES only, never around a data declaration: _DATA and
//    _INITIALIZED must stay byte-identical between the two builds (tools/data_layout_check.py proves it).
//  - The C version is always kept, built (cfall) and tested (GB_ROM=build/game-c.gb pytest tests).
//  - Add a new ASM_<X> line below with its batch (PLAN.md, asm_plan section 5).
#ifndef ASM_CFG_H
#define ASM_CFG_H

#ifndef ASM_PASS
#define ASM_PASS 1
#endif

// batch 1: perf_ly / perf_snap / the main tail (main.c)
#ifndef ASM_F
#define ASM_F ASM_PASS
#endif
// batch 3: draw_held / draw_glass / oam_put folded into draw_mugs_loop (mugs.c)
#ifndef ASM_DRAW_HELD
#define ASM_DRAW_HELD ASM_PASS
#endif
// batch 4: find_catcher and scan_catcher behind catch_full (patrons.c; col_scan and blocked_behind stay C)
#ifndef ASM_SCANS
#define ASM_SCANS ASM_PASS
#endif
// batch 5: draw_lifted_asm and lifted_scan (lift.c)
#ifndef ASM_LIFT_DRAW
#define ASM_LIFT_DRAW ASM_PASS
#endif
// batch 6: the update_mugs group (mugs.c)
#ifndef ASM_UPDATE_MUGS
#define ASM_UPDATE_MUGS ASM_PASS
#endif
// batches 7, 8: the patron steps (patrons.c); the sway compare chain
#ifndef ASM_PATRON_LOOP
#define ASM_PATRON_LOOP ASM_PASS
#endif
#ifndef ASM_PATRON_STEPS
#define ASM_PATRON_STEPS ASM_PASS
#endif
// batch 10: the boss_draw hat count (boss.c)
#ifndef ASM_BOSS_HATS
#define ASM_BOSS_HATS ASM_PASS
#endif
// batch 11: the lift_frame skeleton (lift.c)
#ifndef ASM_LIFT_FRAME
#define ASM_LIFT_FRAME ASM_PASS
#endif
// batch 12: the crowd chooser, choose_bar (lift.c): the bar's records, the greedy lift pass, the overlap flags, the lifted ones' busy flags
#ifndef ASM_CHOOSER
#define ASM_CHOOSER ASM_PASS
#endif

// patron-rev-2: the mid-frame palette split's 8-byte palette write (main.c split_pal_put)
#ifndef ASM_SPLIT_PAL
#define ASM_SPLIT_PAL ASM_PASS
#endif

#endif
