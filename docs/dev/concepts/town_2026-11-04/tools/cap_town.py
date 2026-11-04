"""Capture the INTRO, FINALE_A and CREDITS pages from the scratch ROM (out/town/st/build/game.gb), CGB (double speed) or DMG.
Usage: python3 cap_town.py cgb|dmg.  Writes only under out/town/cap/<model>/. (After /workspace/out/story_scenes/cap.py.)"""
import contextlib, json, os, sys
from pathlib import Path

ST = Path(__file__).resolve().parents[1] / "st"
OUT = Path(__file__).resolve().parents[1] / "cap"
os.environ["GB_ROM"] = str(ST / "build" / "game.gb")
sys.path.insert(0, str(ST / "tests"))
os.chdir(ST)

from conftest import double_speed       # noqa: E402
from test_flow import run_until         # noqa: E402
import test_story as T                  # noqa: E402
from test_story_pictures import to_finale, through_the_pouroff  # noqa: E402

SCENES = json.loads((ST / "build" / "story.json").read_text())["scenes"]


def capture(gb, idx, outdir):
    s = SCENES[idx]
    for k in range(len(s["pages"])):
        if k:
            T.turn_page(gb, k)
        T.page_ready(gb)
        gb.image().convert("RGB").save(outdir / f"{s['id']}_{k:02d}.png")
    print(s["id"], len(s["pages"]), "pages", flush=True)


def main(model):
    outdir = OUT / model
    outdir.mkdir(parents=True, exist_ok=True)
    ds = lambda: double_speed() if model == "cgb" else contextlib.nullcontext()
    if "intro" in sys.argv[2:] or len(sys.argv) == 2:
        with ds():
            rom = T.start_story(model)
        with rom:
            capture(rom, 0, outdir)
    with ds():
        rom = to_finale(model)
    with rom:
        fa = next(i for i, s in enumerate(SCENES) if s["id"] == "FINALE_A")
        capture(rom, fa, outdir)
        through_the_pouroff(rom)
        rom.press("start", 2)
        run_until(rom, lambda: rom.mem("story_scene") == T.SC["CREDITS"], 30)
        T.settle(rom)
        capture(rom, T.SC["CREDITS"], outdir)
    print("DONE", flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
