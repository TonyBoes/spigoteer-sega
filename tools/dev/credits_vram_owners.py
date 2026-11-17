#!/usr/bin/env python3
"""Who owns which BG tile ids during the credits roll: a canary in every BG tile id, then which ids the roll overwrites and when.

    python3 tools/dev/credits_vram_owners.py ROM [--models dmg,cgb] [--every 4]

At the roll's start every BG tile (bank 0 on a DMG; banks 0 and 1 on a Color) gets a canary pattern. Every N frames the tiles that no longer hold it are noted, with the first and last
frame of a change; the tiles that were on the screen's map (BG cell ids, bank by attribute bit 3) are noted too. Prints, per bank, the ranges of ids that were never changed and never
shown (free for a new user, as far as the roll goes), those changed, and those shown without a change (loaded before the canary: fonts, flat tiles). Reads the ROM, writes nothing."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "tools" / "dev"))
from credits_shots import start      # noqa: E402

CAN = bytes([0xA5, 0x5A] * 8)


def addr(i):                                   # BG tile id -> VRAM address (the signed mode: 0-127 at 0x9000, 128-255 at 0x8800)
    return 0x9000 + 16 * i if i < 128 else 0x8800 + 16 * (i - 128)


def ranges(ids):
    out, ids = [], sorted(ids)
    for i in ids:
        if out and out[-1][1] == i - 1:
            out[-1][1] = i
        else:
            out.append([i, i])
    return " ".join(f"{a}-{b}" if a != b else str(a) for a, b in out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom")
    ap.add_argument("--models", default="dmg,cgb")
    ap.add_argument("--every", type=int, default=4)
    ap.add_argument("--until", type=int, default=12000, help="stop at this frame of the roll")
    a = ap.parse_args()
    for model in a.models.split(","):
        gb = start(a.rom, model)
        pb = gb.pb
        banks = (0, 1) if model == "cgb" else (0,)
        for b in banks:
            for i in range(256):
                for k in range(16):
                    pb.memory[b, addr(i) + k] = CAN[k]
        changed = {b: {} for b in banks}
        shown = {b: set() for b in banks}
        for n in range(a.until):
            pb.tick(1, True)
            if gb.mem("story_phase") != 8:
                break
            if n % a.every:
                continue
            for b in banks:
                for i in range(256):
                    if i not in changed[b] and bytes(pb.memory[b, addr(i):addr(i) + 16]) != CAN:
                        changed[b][i] = [n, n]
                    elif i in changed[b]:
                        changed[b][i][1] = n
            lcdc = pb.memory[0xFF40]
            base = 0x9C00 if lcdc & 8 else 0x9800
            for k in range(1024):
                t = pb.memory[0, base + k]
                bank = (pb.memory[1, base + k] >> 3) & 1 if model == "cgb" else 0
                shown[bank].add(t)
        for b in banks:
            allids = set(range(256))
            free = allids - set(changed[b]) - shown[b]
            print(f"{model} bank {b}: never changed, never on the map: {ranges(free)}")
            grp = {}
            for i, (f0, f1) in changed[b].items():
                grp.setdefault((f0 // 250 * 250, f1 // 250 * 250), []).append(i)
            for (f0, f1), ids in sorted(grp.items()):
                print(f"{model} bank {b}: changed between frames ~{f0} and ~{f1}: {ranges(ids)}")
            print(f"{model} bank {b}: on the map but never changed (loaded before the roll): {ranges(shown[b] - set(changed[b]))}")


if __name__ == "__main__":
    main()
