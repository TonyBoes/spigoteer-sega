---
name: no-throwaway-fixes
description: Owner doesn't want interim fixes that a planned redesign will replace; patrons shoving each other is rejected
metadata:
  type: feedback
---
Don't build stopgap fixes for a bug when the agreed next milestone replaces that code. Point at the milestone instead. Patrons must overlap and pass each other, as in arcade Tapper; one patron shoving another along the bar is not acceptable.

**Why:** the owner said (2026-10-09) they "would rather not waste tokens on finishing a feature that won't survive the next round".
**How to apply:** before launching a fix, check whether a pending redesign touches the same code. If it does, fold the bug into that redesign's tests instead.
