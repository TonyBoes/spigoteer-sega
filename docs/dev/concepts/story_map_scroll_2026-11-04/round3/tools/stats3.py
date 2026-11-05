"""Scenarios for the DMG tile budget (round 2): what the window needs if ground variants, then scenery, are collapsed."""
import render2 as R
import world2 as W
import stats2 as S

w = R.LATE
sg = S.sig_grid(w)
PLAIN = tuple(tuple([0] * 8) for _ in range(8))
for label, kinds in (("as drawn", set()), ("ground variants -> plain", {"ground"}), ("ground + scenery -> plain", {"ground", "decor"})):
    g = [[PLAIN if w.kind[y][x] in kinds else sg[y][x] for x in range(W.CW)] for y in range(W.CH)]
    t, p, at = S.window_stats(g, w.pal)
    wc, wr, mc = S.stream(g)
    print(f"{label:28s} world {len({c for r in g for c in r}):4d}  window max {t:3d} at {at}  stream worst col {wc} row {wr} mean col {mc:.1f}")
