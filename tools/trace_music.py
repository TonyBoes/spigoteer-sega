#!/usr/bin/env python3
"""Record every write to the sound registers (FF10-FF3F) the music engine makes, frame by frame, in PyBoy.

    tools/trace_music.py build/game.gb out/trace_before.json            # every tune (jukebox), both models, with effects
    tools/trace_music.py build/game.gb out/trace_after.json --quick
    tools/trace_music.py --diff out/trace_before.json out/trace_after.json

Any change to src/music.c's tick (a speed-up, say) must leave the trace identical: the same writes, same values, same
order, on the same video frame, for every tune, with and without effects. PyBoy cannot hook memory writes, so this
hooks every instruction of bank 2's music code (music.c and hUGEDriver, found by a linear sweep) that can store, and
decodes the store from the registers when it is reached: ldh (n),a / ld (c),a / ld (nn),a / ld (hl+-),a / ld (hl),r|n /
ld (bc|de),a. Each run starts from a fresh boot, opens BONUS > SOUNDTRACK, picks a tune and mashes A; effects
(sfx_req bits) are requested at fixed frames, alone and together.
"""
import argparse
import json
import os
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))

LEN3 = {0x01, 0x11, 0x21, 0x31, 0x08, 0xC2, 0xC3, 0xC4, 0xCA, 0xCC, 0xCD, 0xD2, 0xD4, 0xDA, 0xDC, 0xEA, 0xFA}
LEN2 = {0x06, 0x0E, 0x16, 0x1E, 0x26, 0x2E, 0x36, 0x3E, 0x10, 0x18, 0x20, 0x28, 0x30, 0x38, 0xC6, 0xCE, 0xD6, 0xDE,
        0xE0, 0xE6, 0xE8, 0xEE, 0xF0, 0xF6, 0xF8, 0xFE, 0xCB}
HL_STORES = {0x77: "A", 0x70: "B", 0x71: "C", 0x72: "D", 0x73: "E", 0x74: "H", 0x75: "L", 0x22: "A", 0x32: "A", 0x36: None}


def sweep(rom_bytes, bank, lo, hi):
    """[(addr, opcode, operands)] of the instructions of a linear sweep over bank `bank`, addresses lo..hi."""
    base = bank * 0x4000 - 0x4000
    out, a = [], lo
    while a < hi:
        op = rom_bytes[base + a]
        n = 3 if op in LEN3 else 2 if op in LEN2 else 1
        out.append((a, op, rom_bytes[base + a + 1:base + a + n]))
        a += n
    return out


def install_hooks(gb, log):
    from gbtools import load_symbols
    syms = load_symbols(gb.path)
    rom = Path(gb.path).read_bytes()
    lo = syms["music_init"][1]
    hi = syms["hUGE_note_table"][1]
    rf = gb.pb.register_file

    def reg(name):
        return getattr(rf, name) & 0xFF

    def hl():
        return rf.HL

    def rec(addr, val):
        if 0xFF10 <= addr <= 0xFF3F:
            log.append((gb.pb.frame_count, addr, val & 0xFF))

    def make(op, operands):
        if op == 0xE0:
            a = 0xFF00 + operands[0]
            return lambda c: rec(a, rf.A)
        if op == 0xE2:
            return lambda c: rec(0xFF00 + rf.C, rf.A)
        if op == 0xEA:
            a = operands[0] | operands[1] << 8
            return lambda c: rec(a, rf.A)
        if op in HL_STORES:
            r = HL_STORES[op]
            if op == 0x36:
                v = operands[0]
                return lambda c: rec(hl(), v)
            if r in ("H", "L"):
                return lambda c: rec(hl(), (rf.HL >> 8) if r == "H" else rf.HL)
            return lambda c: rec(hl(), getattr(rf, r))
        if op == 0x02:
            return lambda c: rec(rf.B << 8 | rf.C, rf.A)
        if op == 0x12:
            return lambda c: rec(rf.D << 8 | rf.E, rf.A)
        return None

    n = 0
    for a, op, operands in sweep(rom, 2, lo, hi):
        cb = make(op, operands)
        if cb:
            gb.pb.hook_register(2, a, cb, None)
            n += 1
    return n


SFX_PLAN = [(1, 40, [1]), (1, 90, [2]), (1, 140, [3]), (1, 190, [4]), (1, 240, [5]), (1, 290, [6]), (1, 340, [7]),
            (1, 400, [8]), (1, 450, [9]), (1, 520, [10]), (1, 560, [11]), (1, 600, [12]), (1, 700, [3, 4]),
            (1, 760, [2, 11]), (1, 800, [1, 12]), (1, 830, [9, 4]), (1, 900, [10, 3, 2]), (1, 905, [11]),
            (1, 1000, [5, 8]), (1, 1100, [7, 3]), (1, 1130, [3]), (1, 1137, [3]), (1, 1500, [12, 8])]


def request(gb, ids):
    a = gb.addr("sfx_req")
    bit = 0
    for i in ids:
        bit |= 1 << (i - 1)
    gb.write(a, gb.mem(a) | (bit & 0xFF))
    gb.write(a + 1, gb.mem(a + 1) | (bit >> 8))


def run_one(rom_path, model, tune, fast, frames, effects):
    from conftest import K_BONUS, K_SOUNDTRACK, title_pick
    from gbtools import Rom
    log = []
    gb = Rom(rom_path, model)
    try:
        gb.run(120)
        title_pick(gb, K_BONUS, K_SOUNDTRACK)
        for _ in range(30):
            if gb.mem("game_state") == 14:
                break
            gb.run(1)
        gb.run(2)
        gb.write("tune_unlocked", 0xFF)
        gb.write(gb.addr("tune_unlocked") + 1, 0xFF)
        gb.write("jb_sel", tune)
        gb.write("music_fast", fast)
        install_hooks(gb, log)
        gb.press("a", 2)
        plan = {f: ids for _, f, ids in SFX_PLAN} if effects else {}
        for f in range(frames):
            if f in plan:
                request(gb, plan[f])
            gb.run(1)
        return {"log": log, "cur": gb.mem("cur_tune"), "frames": gb.mem16("music_frames")}
    finally:
        gb.stop()


def diff(a, b):
    A, B = json.load(open(a)), json.load(open(b))
    bad = 0
    for k in sorted(set(A) | set(B)):
        if k not in A or k not in B:
            print("only in one:", k); bad += 1; continue
        la, lb = A[k]["log"], B[k]["log"]
        if la != lb:
            bad += 1
            i = next((i for i, (x, y) in enumerate(zip(la, lb)) if x != y), min(len(la), len(lb)))
            print(f"DIFF {k}: {len(la)} vs {len(lb)} writes, first difference at #{i}: {la[i:i+2]} vs {lb[i:i+2]}")
    n = sum(len(v["log"]) for v in A.values())
    print(f"{len(A)} runs, {n} register writes in the first file; {'IDENTICAL' if not bad else str(bad) + ' DIFFER'}")
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom", nargs="?")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--frames", type=int, default=2600)
    ap.add_argument("--diff", action="store_true", help="compare two trace files (the arguments are the files)")
    a = ap.parse_args()
    if a.diff:
        sys.exit(diff(a.rom, a.out))
    import concurrent.futures as cf
    jobs = []
    for model in ("dmg", "cgb"):
        for tune in range(15):
            for fast in ((0, 1) if tune >= 5 else (0,)):
                for fx in (0, 1):
                    if a.quick and (fast or tune % 4):
                        continue
                    jobs.append((model, tune, fast, fx))
    res = {}
    with cf.ProcessPoolExecutor(max_workers=min(os.cpu_count() or 4, 14)) as ex:
        futs = {ex.submit(run_one, a.rom, m, t, f, a.frames, fx): (m, t, f, fx) for m, t, f, fx in jobs}
        for fu in cf.as_completed(futs):
            m, t, f, fx = futs[fu]
            res[f"{m}/tune{t}/fast{f}/fx{fx}"] = fu.result()
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    json.dump(res, open(a.out, "w"))
    n = sum(len(v["log"]) for v in res.values())
    print(f"{len(res)} runs, {n} writes -> {a.out}")
    for k, v in sorted(res.items()):
        if not v["log"]:
            print("WARNING no writes:", k)


if __name__ == "__main__":
    main()
