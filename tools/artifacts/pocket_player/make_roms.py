#!/usr/bin/env python3
"""Pack ROMs for the Pocket Player page (tools/artifacts/pocket_player/index.html).

    python3 tools/artifacts/pocket_player/make_roms.py OUTDIR id=ROM.gb[:label] [id=ROM.gb[:label] ...]

Each ROM becomes OUTDIR/roms/<id>.js, which sets window.ROMS[id] = {label, b64}; the page loads the one picked in its ROM menu
on demand. The page's ROM_LIST (in index.html) names the ids and labels shown in the menu: keep the two in step. The first entry
there is the default ("main": the newest main, unlocked: `make unlocked`, build/game-unlocked.gb).

Publish OUTDIR's index.html with wasmboy-ts-core.patched.js and roms/*.js as the artifact's files (see tools/artifacts/README.md).
"""
import base64
import hashlib
import json
import os
import sys


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    out = sys.argv[1]
    os.makedirs(os.path.join(out, "roms"), exist_ok=True)
    for spec in sys.argv[2:]:
        rid, rest = spec.split("=", 1)
        path, _, label = rest.partition(":")
        data = open(path, "rb").read()
        label = (label or os.path.basename(path)) + " (sha1 %s)" % hashlib.sha1(data).hexdigest()[:10]
        with open(os.path.join(out, "roms", rid + ".js"), "w") as f:
            f.write("window.ROMS=window.ROMS||{};window.ROMS[%s]={label:%s,b64:\"%s\"};\n"
                    % (json.dumps(rid), json.dumps(label), base64.b64encode(data).decode()))
        print("wrote roms/%s.js  %s" % (rid, label))


main()
