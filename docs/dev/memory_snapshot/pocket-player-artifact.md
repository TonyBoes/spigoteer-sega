---
name: pocket-player-artifact
description: Browser emulator artifact "Spigoteer Pocket Player" (https://claude.ai/artifact/HepE9Kkxm3sLz8HYeuEQo2); refresh rom.js with the newest unlocked ROM after merges
metadata:
  type: project
---
Owner, 2026-10-21: he wanted a browser Game Boy emulator with on-screen controls for quick tests.

Built: https://claude.ai/artifact/HepE9Kkxm3sLz8HYeuEQo2.
- Source: the scratchpad emulator/ folder (index.html, rom.js, wasmboy-ts-core.patched.js).
- Emulator: WasmBoy 0.7.1's TS core, GPL-3, with 2 patches:
  - CPL masks A to 8 bits, without which all joypad reads were empty;
  - read traps for VBK, BCPD and OCPD, without which there was no is_cgb and palette reads were wrong.
- Refresh the ROM with `python3 tools/emu_page/make_rom_js.py ROM.gb emulator/rom.js --label "main <hash> ..."`. That tool is on branch worktree-agent-a0ff3e770c2d24e15 until merged.

iOS Safari sound is fixed (owner confirmed 2026-10-21, after three tries). The context goes "interrupted" and only unlocks when a sound is played inside a finished tap (touchend, click or pointerup, not pointerdown). wakeAudio therefore retries resume() plus a near-silent oscillator on every such event until the state is "running". It also sets navigator.audioSession.type = "playback". Keep this when editing the page.

Since 2026-10-21 the page has a ROM menu. Bundled ROMs are roms/<id>.js, each setting window.ROMS[id] = {label, b64}, plus the ROM_LIST array in index.html. There is also an "Open .gb file…" picker. Keep the "main" entry as the latest main unlocked build, and add or remove test ROMs as questions open and close. rom.js is no longer used.

**Why:** quick feel tests on his phone. It is not the accuracy reference; SameBoy and hardware are.
**How to apply:** after merges that change gameplay, regenerate rom.js from the unlocked ROM and republish the same file path or URL.

Related: [[gfx-atlas-artifact]], [[review-board-artifact]].
