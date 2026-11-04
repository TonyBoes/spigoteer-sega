#!/usr/bin/env python3
"""mksheet.py OUT.png TITLE VER... : tools/dev/contact_sheet.py over the cells: rows = VER x (dmg, cgb), columns = poses"""
import subprocess
import sys
from pathlib import Path
from PIL import Image

ROOT = Path("/workspace/.claude/worktrees/agent-a781dd25b24512d04")
out, title, vers = sys.argv[1], sys.argv[2], sys.argv[3:]
cells = ROOT / "out/cells"
blank = cells / "blank.png"
Image.new("RGB", (64, 30), (60, 60, 60)).save(blank)
bands = [["WALK", "STOMP", "GULP_UP", "GULP", "GULP_SWAY", "GULP_END"], ["WINCE", "HAPPY", "TASTE", "HOLD", "HOLDHOP", None]]
items = []
for band in bands:
    for v in vers:
        for m in ("dmg", "cgb"):
            for p in band:
                items.append(f"{v} {m} {p}={cells / f'{v}_{m}_{p}.png'}" if p else f"_={blank}")
cmd = ["python3", str(ROOT / "tools/dev/contact_sheet.py"), out, "--scale", "4", "--cols", "6", "--title", title] + items
subprocess.run(cmd, check=True)
