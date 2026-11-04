// Frames of a ROM on the Pocket Player's own core (WasmBoy 0.7.1 patched: tools/artifacts/pocket_player/wasmboy-ts-core.patched.js), headless.
// The owner plays on it, so a glitch he sees that SameBoy does not show is a difference of this core (scanline renderer, its own timing).
//
//   node tools/dev/wasmboy_frames.js ROM.gb OUTDIR cgb|dmg FRAME[,FRAME...] [--press a:120:4,right:200:2] [--raw]
//
// executeFrame returns after a fixed number of CPU cycles, on whatever line the LCD is then (LY 51 at double speed here), not at VBlank: the buffer
// then holds the new frame down to that line and the previous one below it. --raw writes that buffer as the page used to draw it (a tear at that line,
// which shears anything moving sideways: Taiko Pour's notes); without it the frame is composed as the Pocket Player's drawFrame does now.
// Writes OUTDIR/f<frame>.ppm (160x144, P6) for each frame number counted from boot (60 a second). A --press entry is KEY:FIRST_FRAME:LENGTH.
const fs = require("fs");
const vm = require("vm");
const path = require("path");

const [rom, out, model, frameList, ...rest] = process.argv.slice(2);
const want = new Set(frameList.split(",").map(Number));
const last = Math.max(...want);
const raw = process.argv.includes("--raw");
const presses = [];
const pi = rest.indexOf("--press");
if (pi >= 0) rest[pi + 1].split(",").forEach(s => { const [k, a, n] = s.split(":"); presses.push([k, +a, +n]); });
// the joypad bits WasmBoy's setJoypadState takes: up, right, down, left, a, b, select, start
const KEYS = ["up", "right", "down", "left", "a", "b", "select", "start"];

vm.runInThisContext(fs.readFileSync(path.join(__dirname, "../artifacts/pocket_player/wasmboy-ts-core.patched.js"), "utf8"));
fs.mkdirSync(out, { recursive: true });
WasmBoyTsCore().then(core => {
  const ex = core.instance.exports, mem = core.byteMemory;
  const bytes = fs.readFileSync(rom);
  mem.fill(0, 0, ex.CARTRIDGE_ROM_LOCATION);
  mem.set(bytes, ex.CARTRIDGE_ROM_LOCATION);
  ex.config(0, model === "cgb" ? 1 : 0, 0, 0, 0, 0, 0, 0, 0, 0);
  let prev = null;
  for (let f = 1; f <= last; f++) {
    const held = presses.filter(p => f >= p[1] && f < p[1] + p[2]).map(p => KEYS.indexOf(p[0]));
    ex.setJoypadState(held.includes(0) ? 1 : 0, held.includes(1) ? 1 : 0, held.includes(2) ? 1 : 0, held.includes(3) ? 1 : 0,
                      held.includes(4) ? 1 : 0, held.includes(5) ? 1 : 0, held.includes(6) ? 1 : 0, held.includes(7) ? 1 : 0);
    if (ex.executeFrame() < 0) { console.error("core stopped at frame", f); process.exit(1); }
    ex.clearAudioBuffer();
    const ly = ex.getLY();
    if (want.has(f) || !raw) {
      const o = ex.FRAME_LOCATION, cur = Buffer.alloc(160 * 144 * 3);
      for (let i = 0; i < 160 * 144 * 3; i++) cur[i] = mem[o + i];
      var nextPrev = cur;
    }
    if (want.has(f)) {
      const o = ex.FRAME_LOCATION, buf = Buffer.alloc(160 * 144 * 3);
      for (let i = 0; i < 160 * 144 * 3; i++) buf[i] = mem[o + i];
      if (!raw && prev && ly < 144) prev.copy(buf, 0, 0, ly * 160 * 3);
      fs.writeFileSync(path.join(out, "f" + f + ".ppm"), Buffer.concat([Buffer.from("P6\n160 144\n255\n"), buf]));
    }
    prev = nextPrev;
  }
  console.log("done", out);
});
