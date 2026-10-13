"""Record Taiko Pour's sound balance (sfx4): a perfect bot over the tune, then the hits alone.

usage: python3 tools/rec_taiko.py <rom> <outprefix> [model]
Writes <outprefix>.wav (16-bit stereo, 48 kHz, one fixed gain for every file).
Clean recorder: per 1-frame tick take ndarray[:raw_buffer_head // 2] (the real rows only), PyBoy at 480 kHz, box-average to
48 kHz, DC block (the out/rec_sfx3.py approach, tools/dump_audio.py).
"""
import sys
import wave
from io import BytesIO
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "tools"))
rom_path, prefix = sys.argv[1], sys.argv[2]
model = sys.argv[3] if len(sys.argv) > 3 else "dmg"

import os  # noqa: E402
os.environ["GB_ROM"] = str(Path(rom_path).resolve())
from conftest import hold_stage_anim  # noqa: E402
from gbtools import Rom  # noqa: E402
from pyboy import PyBoy  # noqa: E402
from test_mg import MG_PRACTICE, mg_enter  # noqa: E402
from tk_helpers import CHART, LAYOUT, MG_TAIKO, plan_for, tk  # noqa: E402

GAIN = 3.0
RATE_IN = 480000


def new_rom():
    rom = Rom(Path(rom_path), model)
    rom.pb.stop(save=False)
    rom.pb = PyBoy(str(rom_path), window="null", sound_emulated=True, cgb=(model == "cgb"), log_level="ERROR",
                   sound_sample_rate=RATE_IN)
    rom.pb.set_emulation_speed(0)
    rom.model_name = model
    return rom


class Rec:
    def __init__(self, rom):
        self.rom, self.chunks = rom, []
        self.on = False

    def run(self, n):
        for _ in range(n):
            self.rom.run(1)
            if self.on:
                s = self.rom.pb.sound
                self.chunks.append(s.ndarray[:s.raw_buffer_head // 2].astype(np.float32).copy())

    def silence(self, frames):
        self.chunks.append(np.zeros((int(RATE_IN * frames / 59.7275), 2), np.float32))

    def audio(self):
        a = np.concatenate(self.chunks)
        k = RATE_IN // 48000
        n = len(a) // k * k
        a = a[:n].reshape(-1, k, 2).mean(axis=1)
        return a


def start(music):
    rom = new_rom()
    rom.run(120)
    hold_stage_anim(rom)
    if not music:
        rom.write("sound_on", 0)
    mg_enter(rom, MG_TAIKO, MG_PRACTICE, 0x5A17)
    return rom


parts = []
# 1. the bot, perfect, over the tune, clock 1000..2000
rom = start(True)
rec = Rec(rom)
plan = {} if "tune" in sys.argv else plan_for()      # 'tune': no presses, the backing alone (for the level numbers)
for _ in range(8000):
    s = tk(rom)
    rec.on = 1000 <= s["clk"] < 2000
    if s["clk"] >= 2000:
        break
    keys = plan.get(s["clk"] + 2, ())
    for k in keys:
        rom.hold(k)
    if keys:
        rec.run(2)
        for k in keys:
            rom.release(k)
    else:
        rec.run(1)
parts.append(rec.audio())
s = tk(rom)
print("bot: clk", s["clk"], "perfect", s["perfect"], "good", s["good"], "miss", s["miss"], "spills", s["spills"], flush=True)
rom.stop()
sil = np.zeros((96000, 2), np.float32)
parts.append(sil)

# 2. the hits alone (music off): DON KA DON KA 40 apart, 12 apart, DON DON, KA
rom = start(False)
rec = Rec(rom)
rec.on = True
fl = rom.addr("story_scratch") + LAYOUT["flash_t"][0]
sq = rom.addr("sfx_req")
rec.run(60)


def hit(lane):
    rom.write(fl + lane, 8)
    v = rom.mem16("sfx_req") | (1 << (10 + lane - 1))     # SFX_DON 10 / SFX_KA 11 (bit id - 1)
    rom.write(sq, v & 255)
    rom.write(sq + 1, v >> 8)


for gap, seq in ((40, (0, 1, 0, 1)), (12, (0, 1, 0, 1)), (24, (0, 0)), (40, (1,))):
    for lane in seq:
        hit(lane)
        rec.run(gap)
    rec.run(30)
rec.run(40)
parts.append(rec.audio())
rom.stop()

a = np.concatenate(parts)
a = a - a.mean(axis=0)
# DC block (one-pole high-pass, ~20 Hz)
W = 4800                                      # minus a 100 ms moving average (~10 Hz high-pass)
c = np.cumsum(np.pad(a, ((W, 0), (0, 0))), axis=0)
y = a - (c[W:] - c[:-W]) / W
mono = y.mean(axis=1, keepdims=True)
out = np.repeat(mono, 2, axis=1)              # the speaker: L+R mono mix
pcm = np.clip(out * GAIN * 1000 / 8, -32767, 32767).astype("<i2")
p = Path(prefix + ".wav")
with wave.open(str(p), "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(48000)
    w.writeframes(pcm.tobytes())
bot = parts[0]
print(p, f"{len(pcm) / 48000:.1f}s", "bot rms", float(np.sqrt((bot ** 2).mean())), "peak", float(np.abs(bot).max()),
      "hits rms", float(np.sqrt((parts[2] ** 2).mean())), "hits peak", float(np.abs(parts[2]).max()))
