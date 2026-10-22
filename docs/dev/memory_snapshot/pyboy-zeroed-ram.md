---
name: pyboy-zeroed-ram
description: "PyBoy starts HRAM at 0 but real hardware and the owner's emulator don't; any hand-placed HRAM byte must be cleared in main()"
metadata:
  node_type: memory
  type: project
  originSessionId: 14228534-aec7-4761-a172-2f78e37cb357
  modified: 2026-10-15T11:33:43.318Z
---

On 2026-10-15 the owner reported every tune playing as the pause mix. The cause was that `PAUSE_NR51` lives at HRAM 0xFFF0, outside what crt0 clears, and nothing set it at boot. On the owner's emulator it held junk, so `music_tick` thought the menu was open. PyBoy starts HRAM at 0, so all ~3150 tests passed. The fix was 0992b62: main() clears it first, and a test pokes 0x5A before the first instruction.

**Why:** the tests cannot see uninitialised-memory bugs unless they poke junk on purpose.
**How to apply:** when reviewing an agent's change that uses a hand-placed HRAM/WRAM byte (not a C global), check that it is cleared at boot, and ask for a junk-poke test. Related: [[pyboy-audio-stale-row]].
