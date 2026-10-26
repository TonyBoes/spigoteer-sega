import json, sys
from PIL import Image
from collections import defaultdict
R = "/workspace/out/atlas/"
G = {(255,255,255):0, (170,170,170):1, (85,85,85):2, (0,0,0):3}
def rec(name):
    t = open(R + "data/%s.js" % name).read()
    i = t.index("= {", t.index('ATLAS["')) + 2
    return json.loads(t[i:t.rindex("}") + 1])
def tiles(model, d, b):
    p = d[model]["pack"]; x0, y0 = p["sheets"][b]["gray"]
    im = Image.open(R + p["png"]).convert("RGB")
    out = []
    for s in range(384):
        ox, oy = x0 + (s % 16) * 8, y0 + (s // 16) * 8
        out.append(tuple(tuple(G[im.getpixel((ox + x, oy + y))] for x in range(8)) for y in range(8)))
    return out
def hf(t): return tuple(r[::-1] for r in t)
def vf(t): return t[::-1]
for v in "cowboys sports lumberjacks chefs divers robots punks ninjas zoo aliens".split():
    d = rec("level_" + v)
    model = "cgb"
    tb = d[model]["tiles"][0]
    T = tiles(model, d, 0)
    use, loaded, changed = tb["use"], tb["loaded"], set()
    for a in tb["changed"]: pass
    live = [s for s in range(384) if use[s] != "0" or loaded[s] == "1"]
    exact, flip = defaultdict(list), defaultdict(list)
    for s in live:
        exact[T[s]].append(s)
        t = T[s]; flip[min(t, hf(t), vf(t), hf(vf(t)))].append(s)
    blank = tuple(tuple([0]*8) for _ in range(8))
    ex = sum(len(g) - 1 for k, g in exact.items() if len(g) > 1)
    fl = sum(len(g) - 1 for k, g in flip.items() if len(g) > 1)
    nb = len(exact.get(blank, []))
    # region split
    def reg(s): return "spr" if s < 128 else ("shr" if s < 256 else "bg")
    exr = defaultdict(int)
    for k, g in exact.items():
        for s in g[1:]: exr[reg(s)] += 1
    print(f"{v:12} live {len(live)} exact-dup {ex} (blank {max(nb-1,0)}) +flips {fl-ex}  by region {dict(exr)}")

print("\n--- by owner region, excluding blanks and tiles that changed during the capture ---")
sys.path.insert(0, "/workspace/tools/gfx_atlas"); import analyze as A
def rname(s):
    for r in A.REGIONS:
        if r["lo"] <= s <= r["hi"]: return r["label"].split(":")[1].split("(")[0].strip()[:28]
for v in "cowboys sports lumberjacks chefs divers robots punks ninjas zoo aliens".split():
    d = rec("level_" + v); tb = d["cgb"]["tiles"][0]; T = tiles("cgb", d, 0)
    ch = set()
    for a in tb["changed"]:
        if isinstance(a, list) and len(a) == 2: ch.update(range(a[0], a[1] + 1))
        elif isinstance(a, int): ch.add(a)
    live = [s for s in range(384) if (tb["use"][s] != "0" or tb["loaded"][s] == "1") and s not in ch]
    blank = tuple(tuple([0]*8) for _ in range(8))
    g = defaultdict(list)
    for s in live:
        t = T[s]
        if t == blank: continue
        g[min(t, hf(t), vf(t), hf(vf(t)))].append(s)
    within, across = defaultdict(int), defaultdict(int)
    for k, ss in g.items():
        if len(ss) < 2: continue
        regs = [rname(s) for s in ss]
        for s, r in zip(ss[1:], regs[1:]):
            (within if r in regs[:regs.index(r)] or r == regs[0] else across)[r] += 1
    print(v, "within-region:", dict(within), "| across:", dict(across))

print("\n--- BG-reachable (ids 128-383) only: exact / with flips; blank extras separately ---")
for v in "cowboys sports lumberjacks chefs divers robots punks ninjas zoo aliens".split():
    d = rec("level_" + v); tb = d["cgb"]["tiles"][0]; T = tiles("cgb", d, 0)
    live = [s for s in range(128, 384) if (tb["use"][s] != "0" or tb["loaded"][s] == "1") and s not in (277, 278)]
    blank = tuple(tuple([0]*8) for _ in range(8))
    nb = sum(1 for s in live if T[s] == blank)
    ge, gf = defaultdict(list), defaultdict(list)
    for s in live:
        t = T[s]
        if t == blank: continue
        ge[t].append(s); gf[min(t, hf(t), vf(t), hf(vf(t)))].append(s)
    e = defaultdict(int); f = defaultdict(int)
    for k, ss in ge.items():
        for s in ss[1:]: e[rname(s)] += 1
    for k, ss in gf.items():
        for s in ss[1:]: f[rname(s)] += 1
    print(f"{v:12} blanks {nb}  exact {dict(e)}  with-flip {sum(f.values())}")

print("\n--- sprite regions: duplicate 8x16 PAIRS (what OAM can share), exact / with h-flip ---")
for v in ["cowboys", "divers", "ninjas"]:
    d = rec("level_" + v); T = tiles("cgb", d, 0)
    for lo, hi, nm in [(0, 39, "Sal"), (96, 127, "show")]:
        pe, pf = defaultdict(list), defaultdict(list)
        for s in range(lo, hi + 1, 2):
            p = (T[s], T[s + 1]); pe[p].append(s)
            pf[min(p, (hf(T[s]), hf(T[s + 1])))].append(s)
        print(v, nm, "dup pairs exact", sum(len(x) - 1 for x in pe.values()), "with h-flip", sum(len(x) - 1 for x in pf.values()))
