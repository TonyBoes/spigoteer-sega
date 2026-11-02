# Release prep: the version on the title (from the Makefile's VERSION), the cartridge header facts, and `make dist`.
import hashlib, json, re, subprocess, sys
from pathlib import Path

import pytest
from conftest import ROOT, check_golden
from test_flow import settle_title, tilemap_row

sys.path.insert(0, str(ROOT / "tools"))
from dist_info import header

VERSION = re.search(r"^VERSION\s*:=\s*(\d)\.(\d)", (ROOT / "Makefile").read_text(), re.M).groups()
TITLE = json.loads((ROOT / "build" / "title.json").read_text())


def test_version_on_title(boot):
    settle_title(boot)
    row = tilemap_row(boot, 0, 0, 20)
    d = TITLE["digits"]
    assert [row[17], row[18], row[19]] == [d[int(VERSION[0])], TITLE["dot"], d[int(VERSION[1])]], "major, the dot, minor in the top-right corner (0.9)"
    check_golden(boot, "title")  # (the same picture as test_flow.py: the title with the version line)


@pytest.mark.parametrize("name", ["game.gb", "release.gb"])
def test_header(name):
    p = ROOT / "build" / name
    if not p.exists():
        pytest.skip("not built")
    d = p.read_bytes()
    h = header(d)
    assert h["title"] == "SPIGOTEER" and len(h["title"]) <= 11
    assert h["cgb_flag"] == 0x80, "dual DMG/CGB"
    assert h["cart_type"] == 0x1B and h["ram_size"] == 2, "MBC5+RAM+BATTERY, 8 KB"
    assert 32 * 1024 << h["rom_size"] == len(d)
    assert h["dest"] == 1
    assert h["version"] == int(VERSION[0]) * 10 + int(VERSION[1])
    assert h["header_ok"] and h["global_ok"]


def dist_is_current(v):
    """True when `make dist` would only reproduce what is there: make's own dependency check (`make release`, which rebuilds only a stale
    build/release.gb; `make -q` cannot be used, the generated-source rules always look stale to it) leaves the ROM untouched, and dist/
    holds that exact ROM, newer than it, with its sha file. Anything else (stale, missing, edited) runs the real `make dist`."""
    rel, rom = ROOT / "build" / "release.gb", ROOT / "dist" / f"spigoteer-v{v}.gb"
    before = rel.stat().st_mtime_ns if rel.is_file() else None
    if subprocess.run(["make", "release"], cwd=ROOT, capture_output=True).returncode != 0:
        return False
    if before is None or rel.stat().st_mtime_ns != before:      # it was rebuilt just now: dist/ is not from this ROM
        return False
    need = [rom, ROOT / "dist" / f"spigoteer-v{v}.gb.sha256", ROOT / "dist" / "RELEASE.txt", ROOT / "dist" / "CREDITS.md", ROOT / "dist" / "licenses" / "README.txt"]
    return (rel.is_file() and all(p.is_file() and p.stat().st_mtime >= rel.stat().st_mtime for p in need)
            and rom.read_bytes() == rel.read_bytes())


def test_make_dist():
    v = ".".join(VERSION)
    if not dist_is_current(v):
        r = subprocess.run(["make", "dist"], cwd=ROOT, capture_output=True, text=True)
        assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    rom = ROOT / "dist" / f"spigoteer-v{v}.gb"
    assert rom.read_bytes() == (ROOT / "build" / "release.gb").read_bytes()
    assert (ROOT / "dist" / f"spigoteer-v{v}.gb.sha256").read_text().split()[0] == hashlib.sha256(rom.read_bytes()).hexdigest()
    txt = (ROOT / "dist" / "RELEASE.txt").read_text()
    assert f"Spigoteer v{v}" in txt and "SHA-256" in txt and "licenses/" in txt
    assert (ROOT / "dist" / "CREDITS.md").exists() and (ROOT / "dist" / "licenses" / "README.txt").exists()
    assert b"Tapper" not in rom.read_bytes()
