#!/usr/bin/env python3
"""Where the palette work of the credits' split falls in a frame (a CRSPLIT build made with CRCFLAGS=-DCR_DBG).

    CRFLOW=SMOOTH CRSCENE=1 CRSPLIT=1 CRCFLAGS=-DCR_DBG make BUILD=out/b_dbg OUT=out/o_dbg unlocked
    python3 tools/dev/credits_split_trace.py out/b_dbg/game-unlocked.gb 1088,6578

For each frame (the same numbering as tools/dev/credits_roll_check.py: a PyBoy frame of the live roll) prints the frame before it and it, each event as name@LY:
a SCY written (credits_update, after the scroll), e the plan made and LYC set, f/g the whole-set write (cr_pset) begins / ends, b the update's set sync is done,
c/d the split interrupt enters / leaves, fb vq_frame_begin, cu credits_update, vbl the VBlank interrupt, mt music_tick. A Color runs at double speed
as shipped (credits_shots.start). Reads the ROM, writes nothing."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "tools" / "dev"))
from credits_shots import start      # noqa: E402

rom = sys.argv[1]
frames = [int(x) for x in sys.argv[2].split(",")]
NAMES = {"vq_frame_begin": "fb", "cr_dbg_a": "a", "cr_dbg_b": "b", "cr_dbg_c": "c", "cr_dbg_d": "d", "cr_dbg_e": "e", "cr_dbg_f": "f", "cr_dbg_g": "g",
         "credits_update": "cu", "vq_vbl": "vbl", "music_tick": "mt"}
gb = start(rom, "cgb")
noi = Path(rom).with_suffix(".noi").read_text()
cur = [0]
ev = {}


def mk(nm):
    def f(ctx):
        ev.setdefault(cur[0], []).append("%s@%d" % (NAMES[nm], gb.pb.memory[0xFF44]))
    return f


for nm in NAMES:
    ll = [x for x in noi.splitlines() if x.startswith("DEF _%s " % nm)]
    if ll:
        v = int(ll[0].split()[2], 16)
        gb.pb.hook_register(v >> 16, v & 0xFFFF, mk(nm), None)
for n in range(max(frames) + 1):
    cur[0] = n
    gb.pb.tick(1, True)
for fr in frames:
    for k in (fr - 1, fr):
        print("frame", k, " ".join(ev.get(k, [])))
    print()
