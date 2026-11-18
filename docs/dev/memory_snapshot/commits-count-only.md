---
name: commits-count-only
description: "End-of-reply push list is just the number of commits to push, not the hashes"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 64761c6b-46f6-4217-a6f1-457b4de3152f
  modified: 2026-10-28T11:35:38.038Z
---

Owner 2026-10-28: "You don't need to list the commits to push. Just the number."

**Why:** the hash list got long (50+) and he reads on a phone.
**How to apply:** end replies with "Commits to push: N" (count `git rev-list --count origin/main..main`); no hash lists.
