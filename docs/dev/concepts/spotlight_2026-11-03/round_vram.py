import sys
sys.path.insert(0, "tests")
from test_lift import boot_play
from test_art import goto_group
from test_show_obj5 import start_show

for name, grp in (("saloon", 0), ("space", 9)):
    gb = boot_play("cgb")
    if grp:
        goto_group(gb, grp)
    gb.run(10)
    start_show(gb, 700)
    gb.run(60)
    m = gb.pb.memory
    lcdc = m[0xFF40]
    print(name, "LCDC %02x" % lcdc, "bg data from", "0x8000" if lcdc & 0x10 else "0x8800 signed")
    for bank in (0, 1):
        used = []
        for t in range(128, 384):
            if any(m[bank, 0x8000 + t * 16 + i] for i in range(16)):
                used.append(t)
        free = [t for t in range(128, 384) if t not in used]
        print(" bank", bank, "used (0..255):", len(used), "free:", len(free))
        # runs of free ids
        runs, s = [], None
        for t in range(128, 385):
            f = t < 384 and t in free
            if f and s is None:
                s = t
            if not f and s is not None:
                runs.append(((s - 256) if s >= 256 else s, ((t - 1) - 256) if t - 1 >= 256 else t - 1)); s = None
        print("  free runs", runs)
    # BG ids used by the map (rows 0..31, both banks' attr)
    ids = {}
    for y in range(32):
        for x in range(32):
            t = m[0, 0x9800 + y * 32 + x]
            a = m[1, 0x9800 + y * 32 + x]
            ids.setdefault((a >> 3) & 1, set()).add(t)
    print(" BG map ids by bank:", {b: len(s) for b, s in ids.items()}, "bank1 ids", sorted(ids.get(1, [])))
    gb.__exit__(None, None, None)
