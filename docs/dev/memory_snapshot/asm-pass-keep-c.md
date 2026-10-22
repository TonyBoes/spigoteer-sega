---
name: asm-pass-keep-c
description: "Owner authorised the assembly pass (2026-10-17) at the supervisor's discretion; every asm routine must keep its C version buildable as reference"
metadata:
  node_type: memory
  type: project
  originSessionId: 14228534-aec7-4761-a172-2f78e37cb357
  modified: 2026-10-17T17:49:21.029Z
---

The C-only rule is lifted for the planned optimisation pass (plan: scratchpad batchH/asm_plan/PLAN.md, batches 0-9). Start batches when wise, i.e. when the files they touch are not being changed by feature agents.

**Why:** the owner may port the game to other platforms later; the C code is the portable reference.

**How to apply:** every asm replacement sits behind a define with the C version kept, built and tested (C-vs-asm rig diffing WRAM on random inputs). Never delete the C path. Related: [[perf-no-long-loops]], [[goldens-supervisor-only]].
