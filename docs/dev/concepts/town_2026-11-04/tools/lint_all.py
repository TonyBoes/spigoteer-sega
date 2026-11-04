"""Render each composed picture (and the master per time of day) at 1x and run the skill's gb_art_lint on it.   lint_all.py PICDIR OUTDIR"""
import subprocess, sys
from pathlib import Path

T = Path(__file__).resolve().parent
sys.path.insert(0, str(T))
from render_v2 import parse, render   # noqa: E402
import master as M                    # noqa: E402
import keys as K                      # noqa: E402

LINT = Path.home() / ".claude/skills/gb-pixel-art/scripts/gb_art_lint.py"
LIMIT = {"intro_before": 151, "intro_a": 117, "finale_a": 146, "credits_b": 199}
src, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
jobs = []
for n, lim in LIMIT.items():
    key, pix = parse(src / f"{n}.txt")
    render(key, pix, 1).save(out / f"{n}_cgb.png")
    render(key, pix, 1, dmg=True, grey=False).save(out / f"{n}_dmg.png")
    jobs += [(out / f"{n}_cgb.png", "cgb", lim), (out / f"{n}_dmg.png", "dmg", lim)]
g = ["".join(r) for r in M.master()]
for name, kt in (("night", K.NIGHT), ("day", K.DAY), ("dawn", K.DAWN)):
    key = {c: (v[0], v[1]) for c, v in kt.items()}
    render(key, g, 1).save(out / f"master_{name}_cgb.png")
    jobs.append((out / f"master_{name}_cgb.png", "cgb", 256))
for f, mode, lim in jobs:
    r = subprocess.run([sys.executable, str(LINT), "--mode", mode, "--kind", "bg", "--max-tiles", str(lim), str(f)],
                       capture_output=True, text=True)
    print(f"== {f.name} ({mode}, max {lim}) rc={r.returncode}")
    print((r.stdout + r.stderr).strip()[:900])
