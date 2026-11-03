import sys
sys.path.insert(0, "tests")
import numpy as np
from test_lift import boot_play
from test_art import goto_group
from test_show_obj5 import start_show, end_show

out = "out/spotlight"
N = 48
for name, grp in (("saloon", 0), ("bistro", 3), ("space", 9)):
    gb = boot_play("cgb")
    if grp:
        goto_group(gb, grp)
    gb.run(10)
    gb.run(4, render=True)
    plate = np.asarray(gb.image())[..., :3].astype(np.uint8).copy()
    start_show(gb, 700)
    gb.run(50)
    fr = []
    for i in range(N):
        gb.run(1, render=True)
        fr.append(np.asarray(gb.image())[..., :3].astype(np.uint8).copy())
    np.savez_compressed(f"{out}/cap_{name}.npz", plate=plate, frames=np.stack(fr))
    print(name, "pal5_cur", gb.mem("pal5_cur"), "timer", gb.mem("show_timer"), "step", gb.mem("dancer_frame"))
    gb.__exit__(None, None, None)
