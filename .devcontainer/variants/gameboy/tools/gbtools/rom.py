"""Headless ROM driver for tests, on top of PyBoy (window='null').

PyBoy is fast and scriptable but not cycle-accurate. Use it to drive and
assert; use `gbcheck` (SameBoy) as the accuracy gate.
"""
from __future__ import annotations

import os
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", message="Using SDL2 binaries")

from PIL import Image, ImageChops  # noqa: E402
from pyboy import PyBoy  # noqa: E402

from .symbols import load_symbols  # noqa: E402

BUTTONS = ("a", "b", "start", "select", "up", "down", "left", "right")
SCREEN_W, SCREEN_H = 160, 144


class Rom:
    """Drive a ROM frame by frame.

    model: "dmg", "cgb" or "auto" (PyBoy decides from the cartridge header).
    Memory reads accept an int address or a symbol name from game.sym / game.noi.
    """

    def __init__(self, path, model: str = "auto", symbols: str | None = None, bootrom: str | None = None):
        self.path = str(path)
        if not Path(self.path).is_file():
            raise FileNotFoundError(self.path)
        cgb = {"dmg": False, "cgb": True, "auto": None}[model]
        self.model = model
        self.pb = PyBoy(self.path, window="null", sound_emulated=False, cgb=cgb, bootrom=bootrom, log_level="ERROR")
        self.pb.set_emulation_speed(0)
        self.symbols = load_symbols(self.path, symbols)
        self._rendered = False

    # -- lifecycle -----------------------------------------------------------
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.stop()

    def stop(self):
        if self.pb is not None:
            self.pb.stop(save=False)
            self.pb = None

    # -- time ------------------------------------------------------------------
    @property
    def frame(self) -> int:
        return self.pb.frame_count

    def run(self, frames: int = 1, render: bool = False):
        """Advance N frames. Rendering only matters for the final frame; screenshot() renders anyway."""
        self.pb.tick(frames, render)
        self._rendered = render

    # -- input -----------------------------------------------------------------
    def _check(self, button: str):
        if button not in BUTTONS:
            raise ValueError(f"unknown button {button!r}; one of {BUTTONS}")

    def press(self, button: str, frames: int = 1):
        """Hold a button for N frames, then release it (and advance one frame so the release is seen)."""
        self._check(button)
        self.pb.button_press(button)
        self.pb.tick(frames, False)
        self.pb.button_release(button)
        self.pb.tick(1, False)

    def hold(self, button: str):
        self._check(button)
        self.pb.button_press(button)

    def release(self, button: str):
        self._check(button)
        self.pb.button_release(button)

    def tap(self, button: str):
        """One-frame press."""
        self.press(button, 1)

    # -- memory ----------------------------------------------------------------
    def addr(self, ref) -> int:
        if isinstance(ref, int):
            return ref
        try:
            return self.symbols[ref][1]
        except KeyError:
            near = [s for s in self.symbols if ref.lower() in s.lower()][:8]
            raise KeyError(f"no symbol {ref!r}; similar: {near}") from None

    def mem(self, ref) -> int:
        return self.pb.memory[self.addr(ref)]

    def mem16(self, ref) -> int:
        a = self.addr(ref)
        return self.pb.memory[a] | (self.pb.memory[a + 1] << 8)

    def mem_s8(self, ref) -> int:
        v = self.mem(ref)
        return v - 256 if v > 127 else v

    def read(self, ref, length: int) -> bytes:
        a = self.addr(ref)
        return bytes(self.pb.memory[a:a + length])

    def write(self, ref, value: int):
        self.pb.memory[self.addr(ref)] = value & 0xFF

    # -- video -----------------------------------------------------------------
    def image(self) -> Image.Image:
        if not self._rendered:
            self.pb.tick(1, True)
            self._rendered = True
        return self.pb.screen.image.convert("RGB").copy()

    def screenshot(self, path, scale: int = 1) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        im = self.image()
        if scale != 1:
            im = im.resize((SCREEN_W * scale, SCREEN_H * scale), Image.NEAREST)
        im.save(path)
        return path

    def is_blank(self) -> bool:
        """True if every pixel is the same colour — the usual sign nothing is being drawn."""
        return len(self.image().getcolors(2) or [0, 0]) == 1

    def golden(self, path, update: bool = False, diff_dir: str | os.PathLike | None = "out/diff") -> bool:
        """Compare the screen to a committed PNG. Missing or update=True writes it and returns True.

        On mismatch writes <diff_dir>/<name>.actual.png and <name>.diff.png and returns False.
        """
        path = Path(path)
        im = self.image()
        if update or not path.is_file():
            path.parent.mkdir(parents=True, exist_ok=True)
            im.save(path)
            return True
        ref = Image.open(path).convert("RGB")
        if ref.size != im.size:
            ok = False
        else:
            ok = ImageChops.difference(ref, im).getbbox() is None
        if not ok and diff_dir is not None:
            d = Path(diff_dir)
            d.mkdir(parents=True, exist_ok=True)
            im.save(d / f"{path.stem}.actual.png")
            if ref.size == im.size:
                ImageChops.difference(ref, im).point(lambda v: 255 if v else 0).save(d / f"{path.stem}.diff.png")
        return ok

    # -- state inspection ---------------------------------------------------------
    def oam(self) -> list[dict]:
        """All 40 OAM entries as dicts (y, x, tile, flags). Raw hardware values, not screen coords."""
        raw = bytes(self.pb.memory[0xFE00:0xFEA0])
        return [dict(y=raw[i], x=raw[i + 1], tile=raw[i + 2], flags=raw[i + 3]) for i in range(0, 160, 4)]

    def visible_sprites(self) -> list[dict]:
        return [s for s in self.oam() if 0 < s["y"] < 160 and 0 < s["x"] < 168]

    def regs(self) -> dict:
        m = self.pb.memory
        return dict(LCDC=m[0xFF40], STAT=m[0xFF41], SCY=m[0xFF42], SCX=m[0xFF43], LY=m[0xFF44],
                    BGP=m[0xFF47], OBP0=m[0xFF48], OBP1=m[0xFF49], WY=m[0xFF4A], WX=m[0xFF4B], IE=m[0xFFFF])

    def bg_tilemap(self, window: bool = False) -> list[list[int]]:
        """The 32x32 background (or window) tilemap as tile ids, from the map the LCDC selects."""
        tm = self.pb.tilemap_window if window else self.pb.tilemap_background
        return [[tm.tile_identifier(x, y) for x in range(32)] for y in range(32)]
