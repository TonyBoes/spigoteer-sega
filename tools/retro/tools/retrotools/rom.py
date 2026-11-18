"""Headless ROM driver on stable-retro's libretro cores.

Cores: Gambatte (GB/GBC), Genesis Plus GX (SMS, GG), FCEUmm (NES). Fast and
deterministic, not cycle-accurate: drive and assert here, gate with `retrocheck`.
Screens are the core's output: GG 160x144, SMS 256x192, NES 240x224 (FCEUmm
crops overscan), GB 160x144. Goldens are therefore per system and per backend.
FCEUmm runs NROM, CNROM, UNROM, UNROM-512, MMC1 and MMC3; GTROM and Action53
do not run here (use retrocheck, which does).
"""
from __future__ import annotations

import warnings
from pathlib import Path

warnings.filterwarnings("ignore", message=".*SDL2.*")

import numpy as np  # noqa: E402
import stable_retro as retro  # noqa: E402
from PIL import Image, ImageChops  # noqa: E402

from .symbols import load_symbols  # noqa: E402

# extension -> (stable-retro system, short name used in paths and by retrocheck)
SYSTEMS = {".gb": ("GameBoy", "gb"), ".gbc": ("GbColor", "gb"), ".sms": ("Sms", "sms"),
           ".gg": ("GameGear", "gg"), ".nes": ("Nes", "nes")}
# common names -> each system's own button name (SMS has PAUSE on the console, no START)
ALIASES = {"start": ("START", "PAUSE"), "select": ("SELECT",), "a": ("A",), "b": ("B",),
           "up": ("UP",), "down": ("DOWN",), "left": ("LEFT",), "right": ("RIGHT",), "pause": ("PAUSE", "START")}


def system_for(path) -> str:
    ext = Path(path).suffix.lower()
    if ext not in SYSTEMS:
        raise ValueError(f"unsupported ROM type {ext!r}; one of {sorted(SYSTEMS)}")
    return SYSTEMS[ext][1]


class Rom:
    def __init__(self, path, symbols=None):
        self.path = str(path)
        if not Path(self.path).is_file():
            raise FileNotFoundError(self.path)
        self.retro_system, self.system = SYSTEMS[Path(self.path).suffix.lower()]
        self.emu = retro.RetroEmulator(self.path)
        self.data = retro.data.GameData()
        self.emu.configure_data(self.data)
        names = retro.get_system_info(self.retro_system)["buttons"]
        self.button_names = [n for n in names if n]
        self._index = {n: i for i, n in enumerate(names) if n}
        self._mask = np.zeros(len(names), dtype=np.uint8)
        self.symbols = load_symbols(self.path, symbols)
        self.frame = 0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.stop()

    def stop(self):
        if getattr(self, "emu", None) is not None:
            del self.emu
            self.emu = None

    # -- time ---------------------------------------------------------------------
    def run(self, frames: int = 1):
        for _ in range(frames):
            self.emu.set_button_mask(self._mask, 0)
            self.emu.step()
            self.frame += 1
        self.data.update_ram()

    # -- input --------------------------------------------------------------------
    def _button(self, name):
        for cand in ALIASES.get(name.lower(), (name.upper(),)):
            if cand in self._index:
                return self._index[cand]
        raise ValueError(f"{self.system} has no button {name!r}; buttons: {self.button_names}")

    def hold(self, name):
        self._mask[self._button(name)] = 1

    def release(self, name):
        self._mask[self._button(name)] = 0

    def press(self, name, frames: int = 1):
        """Hold for N frames, release, and run one more frame so the release is seen."""
        self.hold(name)
        self.run(frames)
        self.release(name)
        self.run(1)

    def tap(self, name):
        self.press(name, 1)

    # -- memory -------------------------------------------------------------------
    def addr(self, ref) -> int:
        if isinstance(ref, int):
            return ref
        if ref in self.symbols:
            return self.symbols[ref][1]
        near = [s for s in self.symbols if ref.lower() in s.lower()][:8]
        raise KeyError(f"no symbol {ref!r}; similar: {near}")

    def _locate(self, a):
        for base, block in self.data.memory.blocks.items():
            if base <= a < base + len(block):
                return block, a - base
        raise ValueError(f"address {a:#06x} is outside the {self.system} RAM the core exposes: "
                         + ", ".join(f"{b:#06x}+{len(v):#x}" for b, v in self.data.memory.blocks.items()))

    def mem(self, ref) -> int:
        block, off = self._locate(self.addr(ref))
        return block[off]

    def mem16(self, ref) -> int:
        a = self.addr(ref)
        return self.mem(a) | (self.mem(a + 1) << 8)

    def mem_s8(self, ref) -> int:
        v = self.mem(ref)
        return v - 256 if v > 127 else v

    def read(self, ref, length: int) -> bytes:
        a = self.addr(ref)
        return bytes(self.mem(a + i) for i in range(length))

    # -- video --------------------------------------------------------------------
    def image(self) -> Image.Image:
        return Image.fromarray(np.asarray(self.emu.get_screen())).convert("RGB")

    def screenshot(self, path, scale: int = 1) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        im = self.image()
        if scale != 1:
            im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
        im.save(path)
        return path

    def is_blank(self) -> bool:
        return len(self.image().getcolors(2) or [0, 0]) == 1

    def golden(self, path, update: bool = False, diff_dir="out/diff") -> bool:
        """Compare with a committed PNG; missing or update=True writes it. Diffs go to diff_dir."""
        path = Path(path)
        im = self.image()
        if update or not path.is_file():
            path.parent.mkdir(parents=True, exist_ok=True)
            im.save(path)
            return True
        ref = Image.open(path).convert("RGB")
        ok = ref.size == im.size and ImageChops.difference(ref, im).getbbox() is None
        if not ok and diff_dir is not None:
            d = Path(diff_dir)
            d.mkdir(parents=True, exist_ok=True)
            im.save(d / f"{path.stem}.actual.png")
            if ref.size == im.size:
                ImageChops.difference(ref, im).point(lambda v: 255 if v else 0).save(d / f"{path.stem}.diff.png")
        return ok
