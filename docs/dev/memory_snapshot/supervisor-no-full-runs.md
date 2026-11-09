---
name: supervisor-no-full-runs
description: "Owner 2026-11-09 (test batch 1, item 2) - the supervisor never runs a full make test or verify.sh itself; gb-runner does, including the rerun on main"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 64761c6b-46f6-4217-a6f1-457b4de3152f
  modified: 2026-11-09T16:56:00.103Z
---

The supervisor never runs a full test suite itself. Every full `make test` and every `verify.sh` run goes to `gb-runner`, including the one rerun on main when other merges landed in between. The supervisor may run targeted tests (`pytest` one file or `-k`) for a quick check.

**Why:** the audit (.claude/audit/test-audit-report.md) found 98 supervisor full runs in 7 days, each a turn on the largest context in the project. Owner's batch 1 brief (docs/dev/notes/test_batch1_brief_2026-11-09.md), item 2.

**How to apply:** brief gb-runner for any full run; see [[one-full-test-run]] and docs/dev/SUPERVISOR.md steps 6-7.
