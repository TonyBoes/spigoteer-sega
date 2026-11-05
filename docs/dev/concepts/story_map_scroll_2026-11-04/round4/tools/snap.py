"""Scratch snapshots of the world while drawing: python3 snap.py -> world_{early,late}{,_dmg}.png in the scratchpad."""
import render2 as R

S = "/tmp/claude-1000/-workspace/64761c6b-46f6-4217-a6f1-457b4de3152f/scratchpad/w/"

if __name__ == "__main__":
    for st in ("early", "late"):
        R.img(st, "cgb").save(S + f"world_{st}.png")
        R.img(st, "dmg").save(S + f"world_{st}_dmg.png")
    print("bad decor:", len(R.W2.WORLD.bad))
