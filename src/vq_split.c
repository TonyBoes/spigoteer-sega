// The slow halves of the VBlank copy list's per-VBlank budget (render.c vq_frame_end / vq_frame_begin; VQ_DRAIN_BUDGET in game.h).
// They run only when a list is over budget (a mini-game's HUD and wall rows together, a cut-scene's page turn with a burst, ...),
// so the banked calls cost the crowd frames nothing, and ROM0 keeps the room.
#pragma bank 20          // (pinned: bank 20 is the roomy one; autobank would move other modules to make room)
#include <stdint.h>
#include <string.h>
#include "game.h"

typedef struct { uint8_t n, bank; const uint8_t *src; uint8_t *dst; uint8_t pad[2]; } vq_entry_t;   // (render.c's list entry)
extern vq_entry_t vq[];
extern volatile uint8_t vq_ready;
extern uint8_t qv_bar, qv_w;

// The list is over budget: the VBlank interrupt gets the first k entries that fit (bytes + 3 an entry; at least one), vq_count
// is cut to k, and the other n - k stay in place behind them. Their number goes to qv_bar and their start to qv_w: vq_restore
// (the next vq_frame_begin) puts them back in the list, in order, whether the interrupt took the first k by then or not.
void vq_split(void) BANKED {
    uint8_t n = vq_count, k = 0, rem = VQ_DRAIN_BUDGET, u;
    for (; k != n; k++) {
        u = vq[k].n + 3;
        if (u > rem) {
            if (k) break;
            u = rem;                             // (the first entry always goes, whatever its size)
        }
        rem -= u;
    }
    qv_bar = n - k;
    qv_w = k;
    vq_count = k;
    qv_cost = qv_bar ? VQ_SPLIT : 0;               // (a tail waits: vq_frame_begin brings it back)
}

void vq_restore(void) BANKED {
    if (!vq_count) memcpy(vq, vq + qv_w, (uint16_t)qv_bar << 3);   // the first k went out: the rest moves to the head
    vq_count += qv_bar;                                              // (not drained yet: they are right behind the first k)
    vq_held = 1;
}
