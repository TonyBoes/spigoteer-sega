#!/usr/bin/env python3
"""The boss cards' poses from the generated art headers (build/boss_<name>_art.h): per boss, each pose's picture (his body columns, 16 lines) and how many pixels differ
between poses, for the ones the credits cycle (credits.c cr_seq) and for all of his poses.

    python3 tools/dev/credits_boss_poses.py [BUILD_DIR] [--seq 0,1,0,2,0,1,0,2]

Prints a table: the pose pairs' differing pixels (2 bits a pixel: any change of the colour index counts). Reads build/, writes nothing."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NAMES = [("big_tex", "BIG TEX"), ("mascot", "THE MASCOT"), ("sasquatch", "SASQUATCH"), ("critic", "THE CRITIC"), ("yeti", "THE YETI"), ("prototype", "PROTOTYPE"),
         ("duke", "DUKE"), ("sumo", "SUMO CHAMP"), ("leo", "LEO THE LION"), ("mothership", "MOTHERSHIP")]
POSE_NAMES = ["WALK", "STOMP", "GULP", "WINCE", "HAPPY", "X5", "X6", "X7"]


def arr(text, name):
    m = re.search(name + r"[^=]*=\s*\{(.*?)\};", text, re.S)
    return [int(x, 0) for x in re.findall(r"0x[0-9A-Fa-f]+|\d+", m.group(1))]


def load(build, key):
    t = (build / f"boss_{key}_art.h").read_text()
    cols = int(re.search(r"#define BOSS_ART_COLS (\d+)", t).group(1))
    poses = int(re.search(r"#define BOSS_ART_POSES (\d+)", t).group(1))
    body = arr(t, "boss_art_body")
    pose = arr(t, "boss_art_pose")
    pose = [pose[i * cols:(i + 1) * cols] for i in range(poses)]
    return cols, body, pose


def picture(cols, body, pose):
    """16 lines x 8 cols pixels: tile pair p = tiles 2p (top), 2p+1 (bottom), 16 bytes each (plane 0, plane 1 per line)"""
    img = [[0] * (8 * cols) for _ in range(16)]
    for c, p in enumerate(pose):
        for half in range(2):
            t = body[(2 * p + half) * 16:(2 * p + half) * 16 + 16]
            for y in range(8):
                lo, hi = t[2 * y], t[2 * y + 1]
                for x in range(8):
                    img[half * 8 + y][8 * c + x] = ((lo >> (7 - x)) & 1) | (((hi >> (7 - x)) & 1) << 1)
    return img


def diff(a, b):
    return sum(1 for ra, rb in zip(a, b) for x, y in zip(ra, rb) if x != y)


def main():
    build = Path(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else ROOT / "build"
    seq = [0, 1, 0, 2, 0, 1, 0, 2]
    if "--seq" in sys.argv:
        seq = [int(x) for x in sys.argv[sys.argv.index("--seq") + 1].split(",")]
    for key, nm in NAMES:
        cols, body, pose = load(build, key)
        pics = [picture(cols, body, p) for p in pose]
        used = sorted(set(seq))
        print(f"{nm:13s} {cols} cols, {len(pose)} poses; cycle {seq}")
        for a in range(len(pics)):
            row = " ".join(f"{diff(pics[a], pics[b]):3d}" for b in range(len(pics)))
            print(f"   {POSE_NAMES[a] if a < len(POSE_NAMES) else a:6s} vs all: {row}")
        ch = sum(diff(pics[seq[i]], pics[seq[(i + 1) % len(seq)]]) for i in range(len(seq)))
        print(f"   pixels changed over one cycle of {len(seq)} steps: {ch}")


if __name__ == "__main__":
    main()
