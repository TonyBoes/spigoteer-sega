"""One-off: put my hand-written tavern facade rows (tavern_facade_r3.txt) into master.py lines 165-204. Transcription only."""
from pathlib import Path
T = Path(__file__).resolve().parent
lines = (T / "master.py").read_text().split("\n")
assert lines[164] == "BBBBBBBBBBBBBBBB########BBBBBBBBBBBBBBB#", lines[164]
assert lines[203].endswith('#ddddd##"""'), lines[203]
new = (T / "tavern_facade_r3.txt").read_text().strip("\n").split("\n")
assert len(new) == 40
new[-1] += '"""'
lines[164:204] = new
(T / "master.py").write_text("\n".join(lines))
print("ok")
