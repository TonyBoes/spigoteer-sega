"""python3 mm_table.py MMDIR TAG... : one line per measure run (the JSON line measure.py prints): DMG tiles, Color tile ids against the 1024 limit, worst 21x19, windows over 8, table entries, flat uses."""
import json
import sys
from pathlib import Path

d = Path(sys.argv[1])
print("%-14s %5s %11s %6s %5s %5s %5s" % ("run", "DMG", "Color/1024", "worst", "over8", "table", "flat"))
for tag in sys.argv[2:]:
    j = None
    for line in (d / (tag + ".log")).read_text().splitlines():
        if line.startswith("{"):
            j = json.loads(line)
    if j is None:
        print("%-14s no result" % tag)
        continue
    print("%-14s %5d %11d %6d %5d %5d %5d%s" % (tag, j["dmg_tiles"], j["color_tiles"], j["dmg_worst_21x19"], j["windows_over_8"], j["table_entries_used"], j["dmg_max_uses_22x20"],
                                                "" if j.get("generator_ok") else ("  FAIL: " + (j.get("generator_error") or "palettes at %s" % (j["palettes_worst_at"],)))[:70]))
