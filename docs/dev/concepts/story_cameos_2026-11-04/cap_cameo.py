"""Capture the cameo pages from a built tree (the scratch mockup or the unchanged base), CGB (double speed) and DMG.
Usage: python3 cap_cameo.py TREE OUTDIR. Uses TREE/tests (conftest, test_story, test_debug) and TREE/build/game.gb.
A cue page is captured at the cue's frame counts (win_rows[4][1], src/cameo.c in the scratch tree); the base ROM at the same
moments after the page turn. Prints the OAM sprites per scanline (worst line in the scene area, rows 0-103) for every shot."""
import contextlib
import json
import os
import sys

TREE, OUT = sys.argv[1], sys.argv[2]
os.environ["GB_ROM"] = os.path.join(TREE, "build", "game.gb")
sys.path.insert(0, os.path.join(TREE, "tests"))
from conftest import Rom, ROM, double_speed, hold_stage_anim, K_STORY  # noqa: E402
from test_flow import run_until  # noqa: E402
import test_story as T  # noqa: E402
import test_debug as D  # noqa: E402

SHOTS = [  # scene index, page (0-based), frame counts after the page turn
    (5, 2, [40]), (5, 3, [40]),
    (6, 1, [60, 150]), (6, 2, [40]), (6, 3, [40]),
    (17, 3, [40]),
    (18, 0, [40]), (18, 1, [40]), (18, 2, [40]),
    (19, 0, [36, 60, 130]), (19, 1, [60]),
]


def lines(gb):
    oam = [gb.mem(0xFE00 + i) for i in range(160)]
    cnt = [0] * 144
    for e in range(40):
        y = oam[e * 4] - 16
        for ly in range(max(0, y), min(144, y + 16)):
            cnt[ly] += 1
    used = sum(1 for e in range(40) if 0 < oam[e * 4] < 160)
    return max(cnt[:104]), used


CAM = os.path.exists(os.path.join(TREE, "src", "cameo.c"))


def at_t(gb, t, k, done):
    if not CAM:                    # the base ROM has no cue counter: the same frames after the turn
        gb.run(max(0, t - done))
        return t
    st = gb.addr("win_rows") + 81
    for _ in range(400):
        if gb.mem("story_page") == k and gb.mem(st) >= t:
            return gb.mem(st)
        gb.run(1)
    return -1


def main():
    os.makedirs(OUT, exist_ok=True)
    story = json.load(open(os.path.join(TREE, "build", "story.json")))
    log = []
    for model in ("cgb", "dmg"):
        for scene in sorted({s for s, _, _ in SHOTS}):
            sc = story["scenes"][scene]
            post = sc["id"].startswith("POST_")
            with (double_speed() if model == "cgb" else contextlib.nullcontext()):
                rom = Rom(ROM, model)
            with rom:
                rom.run(120)
                rom.model_name = model
                hold_stage_anim(rom)
                D.open_on(rom, K_STORY)
                for _ in range(sc["venue"]):
                    D.chap(rom, 1)
                if post:
                    D.pos(rom, -1)
                D.tap(rom, "a")
                run_until(rom, lambda: rom.mem("game_state") == T.GS_STORY and rom.mem("story_scene") == scene, 60)
                T.settle(rom)
                want = {p: ts for s, p, ts in SHOTS if s == scene}
                for k in range(max(want) + 1):
                    if k:
                        T.page_ready(rom)
                        T.turn_page(rom, k)
                    if k not in want:
                        continue
                    if rom.mem("story_typed") < 54:
                        rom.press("a", 2)
                    rom.run(2)
                    done = 4
                    for t in want[k]:
                        got = at_t(rom, t, k, done)
                        done = t
                        p = os.path.join(OUT, f"{model}_{sc['id']}_p{k + 1}_t{t}.png")
                        rom.image().convert("RGB").save(p)
                        mx, used = lines(rom)
                        obp = (rom.mem(0xFF48), rom.mem(0xFF49))
                        log.append((model, sc["id"], k + 1, t, got, mx, used, "OBP0 %02X OBP1 %02X" % obp))
                        print(*log[-1], flush=True)
    json.dump(log, open(os.path.join(OUT, "shots.json"), "w"), indent=0)


main()
