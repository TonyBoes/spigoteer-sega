"""SCRATCH TREE ONLY (out/town/st): the Option A experiment. A picture may have a 5th palette (CGB BG 2) used only by the cells
under a speaker page's portrait frame (cols 1-9, rows 4-12); palettes are ordered so the four the rest of the picture needs come
first. Not a proposal for src/: see NOTES.md for the real change (fade + restore after a portrait)."""
from pathlib import Path

ST = Path(__file__).resolve().parents[1] / "st"
p = ST / "tools/gen_story.py"
s = p.read_text()
old = "PIC_SLOTS = (0, 5, 6, 7)         # CGB BG palette slots of a picture's palettes, in order (BG 1, the HUD, is also usable)"
assert old in s
s = s.replace(old, "PIC_SLOTS = (0, 5, 6, 7, 2)      # SCRATCH (town 2026-11-04): BG 2 for the frame's cells only")
old = """    attr = []
    for m in maps:
        own = next((i for i, p in enumerate(pals) if all(p.get(s, c) == c for s, c in m.items())), None)"""
assert old in s
new = """    # SCRATCH: the palettes some cell outside the portrait frame can only use come first (BG 2 is the frame's alone)
    inrect = lambda i: 1 <= i % 20 <= 9 and 4 <= i // 20 <= 12
    need = set()
    for i, m in enumerate(maps):
        fit = [n for n, p in enumerate(pals) if all(p.get(s, c) == c for s, c in m.items())]
        if not inrect(i) and len(fit) == 1 and not fits_hud(m):
            need.add(fit[0])
    pals = [p for n, p in enumerate(pals) if n in need] + [p for n, p in enumerate(pals) if n not in need]
    if len(need) > 4:
        fail(f"{name}: {len(need)} palettes needed outside the portrait frame (max 4)")
    attr = []
    for m in maps:
        own = next((i for i, p in enumerate(pals) if all(p.get(s, c) == c for s, c in m.items())), None)"""
s = s.replace(old, new)
p.write_text(s)
print("patched", p)
