"""SCRATCH TREE ONLY (out/town/st), after _patch_st.py: CREDITS has no speaker page, so its 5th palette (BG 2) may be used
anywhere (round 2's "Option A, BG 2 anywhere, no speakers"). Not a proposal for src/."""
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "st/tools/gen_story.py"
s = p.read_text()
old = "    if len(need) > 4:\n        fail(f\"{name}: {len(need)} palettes needed outside the portrait frame (max 4)\")"
assert old in s
s = s.replace(old, "    if len(need) > 4 and name != \"credits_b\":   # SCRATCH: CREDITS has no speaker page\n        fail(f\"{name}: {len(need)} palettes needed outside the portrait frame (max 4)\")")
p.write_text(s)
print("patched", p)
