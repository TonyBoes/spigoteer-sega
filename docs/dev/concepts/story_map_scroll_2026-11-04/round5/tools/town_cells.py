"""Which town cells use the accent palettes, and which indices they use (round 4)."""
from collections import Counter

import v_town

c = v_town.build()
rows = c.out()
cp = c.cellpals()
tot = Counter()
for j, r in enumerate(cp):
    for i, p in enumerate(r):
        cnt = Counter(ch for k in range(8) for ch in rows[j * 8 + k][i * 8:i * 8 + 8])
        tot[(p, "has1" if cnt.get("1") else "no1")] += 1
        if p == "town1" and cnt.get("1"):
            tot[("town1 idx1 px", min(cnt["1"], 20))] += 1
print(sorted(tot.items(), key=str))
