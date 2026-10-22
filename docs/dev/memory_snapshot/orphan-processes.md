---
name: orphan-processes
description: Finished agents can leave CPU-hungry background jobs running for days; check ps when runs are slow and after an agent finishes
metadata:
  node_type: memory
  type: feedback
  originSessionId: 14228534-aec7-4761-a172-2f78e37cb357
  modified: 2026-10-19T04:59:33.014Z
---

On 2026-10-18 I found 14 `python3 prof_run.py pile` processes from an old asm-pass agent's worktree (`out/asm_scripts`). They had been running for about 30 hours, using about 4 CPUs, and slowed every test run while the owner kept asking why builds took so long. I killed them by exact PID.

**Why:** an agent's "background work still running" note does not mean anyone cleans that work up.
**How to apply:**
- When runs seem slow, and after each agent finishes, run `ps -eo pid,etimes,%cpu,args --sort=-etimes` and look for long-lived python, pytest or sameboy processes.
- Find what a process is from `readlink /proc/<pid>/cwd`. Never use `pgrep -f` here, because it matches your own shell's command line (see [[wait-loop-pgrep]]).
- Kill only processes from finished agents' worktrees or scratch folders.
- Never run make or tests in a worktree while a background verification is running there. They share build/, so the two clash; on 2026-10-20 I had to stop a run and restart it. Use a separate worktree, or wait.
- Start verifications with run_in_background, not with a trailing `&`, so the task is tracked.
