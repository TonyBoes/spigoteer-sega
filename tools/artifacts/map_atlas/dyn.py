"""Map Atlas, the dynamic half: walk one leg in the built ROM (PyBoy) and log, per game frame, the engine load the map's guards check.

The walk is driven the way tests/test_story_map_world.py does it (a hook on walk_step: one record per GAME frame, whose position is Sal's feet and whose
numbers are the frame before's: perf_logic_last / perf_end_last in lines of 154, V_LAG bit 0 = the frame waited for the camera) plus the VBlank drain's
numbers the picture tests guard (drain_ticks_max <= 13, vq_end_ly_max <= 153, vq_late == 0), read and reset every frame.

    run_walk(model, stop, dir)  -> list of (fx, fy, camx, camy, logic, end, hold, drain, endly, late)     model "dmg" | "cgb" (cgb at double speed, owner Q92)
"""
import contextlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT / "tests"))

SV = 396                                                  # story_scratch + the map's variables (src/smap_priv.h S_V), as tests/test_story_map_world.py
V_WALK, V_CAMX, V_CAMY, V_FX, V_FY, V_LAG = 20, 12, 14, 16, 18, 65
DIRS = ("up", "down", "left", "right")


def _var(sc, n):
    return sc[SV + n] | sc[SV + n + 1] << 8


def run_walk(model, s, d):
    import test_story_map as sm
    from conftest import double_speed
    noi = (ROOT / "build" / "game.noi").read_text()
    v = int(re.search(r"DEF _walk_step (0x[0-9A-F]+)", noi).group(1), 16)
    with double_speed() if model == "cgb" else contextlib.nullcontext():
        gb = sm.to_map(model, 10, stop=s)
    log = []

    def hook(ctx):
        sc = gb.read("story_scratch", 520)
        log.append((_var(sc, V_FX), _var(sc, V_FY), _var(sc, V_CAMX), _var(sc, V_CAMY), gb.mem16("perf_logic_last"), gb.mem16("perf_end_last"),
                    sc[SV + V_LAG] & 1, gb.mem("drain_ticks_max"), gb.mem("vq_end_ly_max"), gb.mem16("vq_late")))
        gb.write("drain_ticks_max", 0)
        gb.write("vq_end_ly_max", 0)

    gb.pb.hook_register(v >> 16, v & 0xFFFF, hook, None)
    gb.press(DIRS[d], 6)
    log.clear()
    started = False
    for fr in range(1500):
        gb.run(1, True)
        walking = bool(gb.read("story_scratch", 520)[SV + V_WALK])
        started = started or walking
        if fr > 4 and started and not walking:
            break
    stop_at = gb.mem("smap_stop")
    return log[1:], stop_at


def _task(a):
    m, s, d = a
    log, at = run_walk(m, s, d)
    return m, s, d, at, log


def collect(exits, jobs=3):
    """every leg both ways on both models -> {"dmg": {"s,d": {"to": stop, "log": [...]}}, "cgb": ...}"""
    import multiprocessing as mp
    tasks = [(m, s, d) for m in ("dmg", "cgb") for s in range(11) for d in range(4) if exits[s][d] != 255]
    out = {"dmg": {}, "cgb": {}}
    with mp.get_context("spawn").Pool(jobs) as pool:
        for m, s, d, at, log in pool.imap_unordered(_task, tasks):
            out[m]["%d,%d" % (s, d)] = {"to": at, "log": log}
    return out


if __name__ == "__main__":
    m, s, d = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    lg, at = run_walk(m, s, d)
    print(len(lg), at, max(r[4] for r in lg), max(r[7] for r in lg), max(r[8] for r in lg), lg[:3], lg[-2:])
