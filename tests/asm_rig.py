"""Function-level differential rig for the asm pass (asm_plan PLAN.md section 6.1).

Calls ONE game function directly inside PyBoy with chosen inputs and returns the WRAM / HRAM bytes it changed, its return
registers and its T-cycles. Run the same case list on the asm ROM (build/game.gb) and the C ROM (build/game-c.gb) and compare:
the diffs are compared as absolute addresses, which is valid because `_DATA` / `_INITIALIZED` are byte-identical in both
builds (tools/data_layout_check.py proves it).

How it works
  1. Boot the ROM and hook `vq_frame_end`, a ROM0 address the game reaches every frame.
  2. In the hook, for each queued case: save the registers, LCDC, IE and all of WRAM + HRAM; set IE = 0 (no interrupt handler
     can run) and turn the LCD off (LY reads 0, so LY-gated code such as the chooser and perf_snap is deterministic); poke the
     inputs; push the sentinel (vq_frame_end) as the return address; set PC to the function.
  3. When execution returns to the sentinel: record cycles, the diff outside the stack, and A / BC / DE / HL; restore everything
     and start the next case. When the queue is empty the game carries on as if nothing happened.

Symbols: globals come from the .noi; statics (mugs.c `_oam_next`) and every function's bank come from
tools/asm_symtab.py (run on demand, cached in out/symtab/<variant>/). Name a static as "mugs:_oam_next".

Calling convention (__sdcccall(1), gbdk manual 4.5.2): the first 8-bit argument in A, the second in E, a 16-bit argument in DE;
the rest on the stack above the return address (`stack=` bytes, lowest address first); the return is in A, or BC for 16 bits (measured on perf_ly; DE for a 16-bit first argument).
`Result` carries A, BC, DE and HL so a test picks what its function returns.
"""
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
import numpy as np  # noqa: E402
from gbtools import Rom  # noqa: E402

WRAM = (0xC000, 0xE000)
HRAM = (0xFF80, 0xFFFF)


@dataclass
class Call:
    """One function call: `fn` a function name ("perf_ly", "mugs:_draw_held" for a static), registers, stack arguments, and either
    `poke` {address or name: byte or bytes} on top of the running game, or `wram` / `hram`: a complete memory image (a captured
    real call) restored first."""
    fn: str
    a: int = 0
    e: int = 0
    de: int | None = None          # sets D and E together (a 16-bit argument)
    bc: int = 0
    hl: int = 0
    stack: bytes = b""
    poke: dict = field(default_factory=dict)
    wram: bytes | None = None
    hram: bytes | None = None


@dataclass
class Result:
    cycles: int
    diff: dict                      # absolute address -> value after the call, for every byte that changed (stack excluded)
    a: int
    bc: int
    de: int
    hl: int

    def ret(self, kind):
        return {"a": self.a, "bc": self.bc, "de": self.de, "hl": self.hl, "none": 0}[kind]


def parse_noi(path):
    d = {}
    for line in open(path):
        m = re.match(r"DEF (\S+) 0x([0-9A-Fa-f]+)", line)
        if m:
            d[m[1]] = int(m[2], 16)
    return d


def stack_floor(map_path):
    """End of _INITIALIZED in the map: everything from there up to 0xE000 is the stack, never compared."""
    end = 0xDD82
    for line in open(map_path, errors="replace"):
        m = re.match(r"^(_DATA|_INITIALIZED)\s+([0-9A-F]{8})\s+([0-9A-F]{8})", line)
        if m:
            end = max(end, int(m[2], 16) + int(m[3], 16)) if m[1] == "_INITIALIZED" else end
    return end


def load_symtab(rom: Path):
    out = ROOT / "out" / "symtab" / rom.stem
    sj = out / "symtab.json"
    # parallel shards (tools/dev/ptest.py): one regenerates under the lock, the others wait and then find it fresh (the two json files are written one after the other)
    import fcntl
    out.mkdir(parents=True, exist_ok=True)
    with open(out / ".lock", "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        if not sj.exists() or sj.stat().st_mtime < rom.stat().st_mtime:
            subprocess.run([sys.executable, str(ROOT / "tools" / "asm_symtab.py"), str(rom)], check=True, capture_output=True)
        return json.loads(sj.read_text()), json.loads((out / "data.json").read_text())


class Rig:
    def __init__(self, rom, model="dmg", boot_frames=120, gb=None):
        """`gb`: an already running Rom (a scenario set up by a test) to attach to instead of booting a new one."""
        self.rom = Path(rom)
        self.gb = gb if gb is not None else Rom(self.rom, model)
        if gb is None:
            self.gb.run(boot_frames)
        self.pb = self.gb.pb
        self.noi = parse_noi(self.rom.with_suffix(".noi"))
        self.funcs, self.statics = load_symtab(self.rom)
        self.floor = stack_floor(self.rom.with_suffix(".map"))
        self.sentinel = self.noi["_vq_frame_end"] & 0xFFFF
        self.queue, self.results, self.pending = [], [], None
        self.pb.hook_register(0, self.sentinel, self._hook, None)

    # ---- symbols
    def addr(self, name):
        """Absolute address of a global ("patron_state", "_patron_state") or a static ("mugs:_oam_next")."""
        if isinstance(name, int):
            return name
        if ":" in name:
            return self.statics[name]
        return self.noi[name if name.startswith("_") else "_" + name] & 0xFFFF

    def fn(self, name):
        """(bank, address) of a function: a global ("perf_ly" is static in main.c: "main:_perf_ly")."""
        for k in (name, "_" + name):
            if k in self.funcs:
                b, a, _ = self.funcs[k]
                return b, a
        v = self.noi.get("_" + name)                          # a generated function (build/*.c) is not in the symtab: the .noi has it
        if v is not None:
            return (v >> 16) or self.noi.get("b_" + name, 0), v & 0xFFFF
        raise KeyError(name)

    def has_fn(self, name):
        return name in self.funcs or "_" + name in self.funcs

    # ---- running
    def run(self, calls, frames_max=None):
        """Run every call in order; results in the same order. (PyBoy returns from a frame as soon as a hook has redirected PC,
        so a call costs one gb.run(1) and a negligible amount of emulated game time.)"""
        self.results = []
        self.queue = list(calls)
        frames_max = frames_max or 3 * len(self.queue) + 100
        n = 0
        while (self.queue or self.pending) and n < frames_max:
            self.gb.run(1)
            n += 1
        if self.queue or self.pending:
            raise RuntimeError("rig: calls did not come back (the function never returned to the sentinel)")
        if len(self.results) != len(calls):                   # (a hook that raised, e.g. an unknown function name, was swallowed by PyBoy)
            raise RuntimeError(f"rig: {len(calls)} calls, {len(self.results)} results (a call's setup failed)")
        return self.results

    def _snapshot(self):
        m = self.pb.memory
        return m[WRAM[0]:WRAM[1]] + m[HRAM[0]:HRAM[1]]

    def _hook(self, _):
        pb, m, rf = self.pb, self.pb.memory, self.pb.register_file
        if self.pending is not None:                          # a call came back
            t0, before, saved, sp = self.pending
            after = self._snapshot()
            b, a = np.array(before, dtype=np.uint8), np.array(after, dtype=np.uint8)
            diff = {}
            for i in np.nonzero(b != a)[0].tolist():
                if i < 0x2000:
                    if i >= self.floor - 0xC000:                  # the stack
                        continue
                    diff[0xC000 + i] = int(a[i])
                else:
                    diff[HRAM[0] + i - 0x2000] = int(a[i])
            self.results.append(Result(pb._cycles() - t0, diff, rf.A, (rf.B << 8) | rf.C, (rf.D << 8) | rf.E, rf.HL))
            m[WRAM[0]:WRAM[1]] = saved["wram"]                # the game's own state back
            m[HRAM[0]:HRAM[1]] = saved["hram"]
            for r in ("A", "B", "C", "D", "E", "HL", "SP"):
                setattr(rf, r, saved[r])
            m[0xFF40] = saved["LCDC"]
            m[0xFFFF] = saved["IE"]
            m[0x2000] = saved["bank"]                         # (a banked function's bank goes back too)
            self.pending = None
        if not self.queue:
            return
        c = self.queue.pop(0)
        saved = {r: getattr(rf, r) for r in ("A", "B", "C", "D", "E", "HL", "SP")}
        saved["LCDC"], saved["IE"] = m[0xFF40], m[0xFFFF]
        saved["bank"] = m[self.noi["__current_bank"] & 0xFFFF]   # GBDK's shadow of the ROM bank in HRAM
        saved["wram"], saved["hram"] = m[WRAM[0]:WRAM[1]], m[HRAM[0]:HRAM[1]]
        m[0xFFFF] = 0
        m[0xFF40] = saved["LCDC"] & 0x7F                      # no interrupts, LCD off (LY 0)
        if c.wram is not None:
            m[WRAM[0]:WRAM[0] + len(c.wram)] = list(c.wram)
        if c.hram is not None:
            m[HRAM[0]:HRAM[0] + len(c.hram)] = list(c.hram)
        for k, v in c.poke.items():
            a = self.addr(k)
            if isinstance(v, int):
                m[a] = v & 0xFF
            else:
                m[a:a + len(v)] = list(v)
        bank, fa = self.fn(c.fn)
        if fa >= 0x4000:                                      # a function in a switchable bank (lift.c is bank 5): map it in
            m[0x2000] = bank
            m[self.noi["__current_bank"] & 0xFFFF] = bank
        sp = saved["SP"] - 2 - len(c.stack)
        m[sp:sp + 2 + len(c.stack)] = [self.sentinel & 0xFF, self.sentinel >> 8] + list(c.stack)
        rf.SP = sp
        rf.A = c.a & 0xFF
        d, e = ((c.de >> 8) & 0xFF, c.de & 0xFF) if c.de is not None else (0, c.e & 0xFF)
        rf.D, rf.E = d, e
        rf.B, rf.C = (c.bc >> 8) & 0xFF, c.bc & 0xFF
        rf.HL = c.hl & 0xFFFF
        rf.PC = fa
        before = self._snapshot()
        self.pending = (pb._cycles(), before, saved, sp)

    # ---- capture of real calls
    def capture(self, fn, frames, drive=None, limit=100000):
        """Run the game `frames` frames (drive(gb, i) before each, to play) and record every real call of `fn`: its registers,
        the first stack bytes and the full WRAM / HRAM image at entry. Returns Calls that replay it. (Call it before run().)"""
        bank, fa = self.fn(fn)
        caps = []
        m, rf = self.pb.memory, self.pb.register_file

        def entry(_):
            if len(caps) < limit:
                sp = rf.SP
                caps.append(Call(fn, a=rf.A, de=(rf.D << 8) | rf.E, bc=(rf.B << 8) | rf.C, hl=rf.HL,
                                 stack=bytes(m[sp + 2:sp + 10]), wram=bytes(m[WRAM[0]:WRAM[1]]), hram=bytes(m[HRAM[0]:HRAM[1]])))

        self.pb.hook_register(bank if fa >= 0x4000 else 0, fa, entry, None)
        for i in range(frames):
            if drive:
                drive(self.gb, i)
            self.gb.run(1)
        return caps


def compare(asm: "Rig", c: "Rig", calls, ret="none"):
    """Run the same calls on both rigs. Returns (mismatches, asm_results, c_results); a mismatch is
    (index, what differs). `ret` is the return register to compare: a, bc, de, hl or none."""
    ra, rc = asm.run(calls), c.run(calls)
    bad = []
    for i, (x, y) in enumerate(zip(ra, rc)):
        if x.diff != y.diff:
            keys = sorted(set(x.diff) | set(y.diff))
            bad.append((i, "diff", [(hex(k), x.diff.get(k), y.diff.get(k)) for k in keys if x.diff.get(k) != y.diff.get(k)][:8]))
        elif x.ret(ret) != y.ret(ret):
            bad.append((i, "ret", x.ret(ret), y.ret(ret)))
    return bad, ra, rc


def cycles_summary(results):
    c = sorted(r.cycles for r in results)
    return c[0], c[len(c) // 2], c[-1]
