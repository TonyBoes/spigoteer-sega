#!/usr/bin/env python3
"""Writes tests/data/chooser_trace.json.gz: the crowd chooser's decisions in crowded scenes, as made by the ROM given (the build BEFORE
a change to choose_bar; see tests/chooser_trace_lib.py for what a case is and why it is not a trace of whole runs).

usage: python3 tools/gen_chooser_trace.py ROM [out.json.gz]

Run it from the tree that built ROM (tools/asm_symtab.py reads build/<variant>.flags and src/ of its own tree). Scenes: the ARCADE peaks of
10 and 12 patrons (space lounge, loop 4; shows and tips alternate in them) and CLASSIC's 16-patron level (25), DMG and CGB, two variants
each (another RNG, script phase, alignment), plus random crowded bars. Each captured case is replayed twice: from the booted game with only
the named fields poked (what the test does) and on the full WRAM image of the capture; the two must make the same changes, which proves the
fields are everything the chooser reads.
"""
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
import chooser_trace_lib as L  # noqa: E402
from asm_rig import Call, Rig  # noqa: E402

PER_SCENE = 26        # cases kept per (scene, model, variant)
FRAMES = 1800
RANDOM = 400


def main(argv):
    rom = Path(argv[1]).resolve()
    out = Path(argv[2]) if len(argv) > 2 else L.DATA
    cases = []
    for name in L.SCENES:
        for model in ("dmg", "cgb"):
            for v in (0, 1):
                got = L.capture(rom, name, model, v, FRAMES, 5)
                step = max(1, len(got) // PER_SCENE)
                keep = got[::step][:PER_SCENE]
                print(name, model, v, len(got), "calls,", len(keep), "kept", flush=True)
                cases += keep
    rnd = random.Random(2026)
    base = cases[0]["in"]
    cases += [L.random_case(rnd, base) for _ in range(RANDOM)]
    bad = 0
    for model in ("dmg", "cgb"):
        idx = [i for i, c in enumerate(cases) if c["s"] == "random" or c["s"].split("-")[1] == model]
        sub = [cases[i] for i in idx]
        diffs, res = L.run_cases(rom, model, sub)
        rig = Rig(rom, model)
        tab = L.Table(rig)
        full = [L.call({"b": c["b"], "in": {}}, wram=c["_wram"], hram=c["_hram"]) for c in sub if "_wram" in c]
        fres = rig.run(full, frames_max=3 * len(full) + 100)
        k = 0
        for j, (i, c) in enumerate(zip(idx, sub)):
            cases[i].setdefault("out", {})[model] = diffs[j]
            if "_wram" in c:
                fd = {tab.name(a): v for a, v in fres[k].diff.items() if a not in tab.scratch}
                k += 1
                if fd != diffs[j]:
                    bad += 1
                    if bad <= 5:
                        print("MISMATCH fresh vs full image", c["s"], {x: (fd.get(x), diffs[j].get(x)) for x in set(fd) | set(diffs[j]) if fd.get(x) != diffs[j].get(x)})
    for c in cases:
        c.pop("_wram", None)
        c.pop("_hram", None)
    assert not bad, f"{bad} cases differ between the poked fields and the full image: a field is missing from FIELDS"
    L.save(cases, out)
    n_changed = sum(1 for c in cases for m in c["out"].values() if m)
    print("wrote", out, len(cases), "cases,", n_changed, "with changes; size", out.stat().st_size)


if __name__ == "__main__":
    main(sys.argv)
