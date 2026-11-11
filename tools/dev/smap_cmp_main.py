#!/usr/bin/env python3
"""Every frame of every leg, both ways, against main's ROM: the same picture wherever the two ROMs show the same place.

    python3 tools/dev/smap_cmp_main.py MAIN_ROM [dmg] [cgb]        # MAIN_ROM: main's build (build/game.gb of main), e.g. out/base_game.gb

Both ROMs walk every leg from every stop (the road's exits, tests/test_story_map_world.py LEG_WALKS), a frame at a time (Color at double speed as shipped).  Each frame is keyed
by what the picture is a function of: Sal's feet, the camera and the two scroll registers.  The pictures are masked where they may differ for reasons that are not the tiles: the sprites of
this frame and the last, the name tag's window, the tile animations' cells (their phase follows the frame logic's timing).  The ROMs pace the walk differently (the new one goes faster), so
a place both visit is compared: every frame of the new ROM whose key the main ROM also shows is compared in full (none may differ), and the frames of keys only one shows are counted (the
other walk skipped that pixel).  Exit 1 on any difference, or when fewer than 2/3 of the frames are matched.  It does not need the test fixtures' goldens; it is not a test of speed."""
import contextlib
import os
import pickle
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def dump(model, out):
    sys.path.insert(0, str(ROOT / "tests"))
    import numpy as np
    import test_story_map as sm
    import test_story_map_world as tw
    from conftest import double_speed
    res = {}
    for s, d in tw.LEG_WALKS:
        with double_speed() if model == "cgb" else contextlib.nullcontext():
            gb = sm.to_map(model, 10, stop=s)
        w = tw.Watch(gb, model, 10)
        gb.press(tw.DIRS[d], 4)
        started = False
        pw, poam, pr = (0, 0), [], gb.regs()
        for f in range(1500):
            gb.run(1, True)
            scr = np.array(gb.image())
            r = gb.regs()
            sc = gb.read("story_scratch", 520)
            co = gb.oam()
            m = np.zeros((144, 160), dtype=bool)
            tw.sprite_mask(co, m)
            tw.sprite_mask(poam, m)
            poam = co
            win = (sc[tw.SV + tw.V_WY], sc[tw.SV + tw.V_WH])
            for wd in (pw, win):
                if wd[1]:
                    m[wd[0]:wd[0] + wd[1], :] = True
            pw = win
            prev_r, pr = pr, r
            walking = bool(sc[tw.SV + tw.V_WALK])
            started = started or walking
            if started:
                fx, fy = tw.var(sc, tw.V_FX), tw.var(sc, tw.V_FY)
                cx, cy = tw.var(sc, tw.V_CAMX), tw.var(sc, tw.V_CAMY)
                if cx + 160 <= 512:
                    reg = np.pad(tw.ANIM_MASK, 3)[cy:cy + 150, cx:cx + 166]           # (the camera moves a px or two between the picture and the read: a margin of 3)
                    for dy in range(7):
                        for dx in range(7):
                            m |= reg[dy:dy + 144, dx:dx + 160]
                res.setdefault((s, d), {})[(prev_r["SCX"], prev_r["SCY"])] = (scr, m)
            if f > 4 and started and not walking:
                break
    pickle.dump(res, open(out, "wb"))


def main(argv):
    if argv and argv[0] == "--dump":
        dump(argv[1], argv[2])
        return 0
    main_rom = str(Path(argv[0]).resolve())
    models = argv[1:] or ["dmg", "cgb"]
    bad = 0
    for model in models:
        outs = {}
        for tag, rom in (("main", main_rom), ("new", str(ROOT / "build" / "game.gb"))):
            out = ROOT / "out" / f"cmp_{tag}_{model}.pkl"
            env = dict(os.environ, GB_ROM=rom)
            subprocess.run([sys.executable, __file__, "--dump", model, str(out)], check=True, env=env)
            outs[tag] = pickle.load(open(out, "rb"))
        import numpy as np
        frames = matched = diff = 0
        for leg, new in outs["new"].items():
            old = outs["main"].get(leg, {})
            for key, (img, m) in new.items():
                frames += 1
                if key not in old:
                    continue
                matched += 1
                img0, m0 = old[key]
                mm = m | m0
                if np.any(np.any(img != img0, axis=2) & ~mm):
                    diff += 1
                    if diff <= 5:
                        print(f"  DIFFERENT {model} leg {leg} at (Sal, scroll) {key}")
        print(f"{model}: new ROM {frames} frames over {len(outs['new'])} legs, {matched} at a place main also shows, {diff} differ")
        bad += diff + (matched * 3 < frames * 2)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
