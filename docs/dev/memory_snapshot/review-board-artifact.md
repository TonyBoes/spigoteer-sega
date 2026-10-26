---
name: review-board-artifact
description: "Review Board (https://claude.ai/artifact/SHg2h5cuTDMN5qrKfiFRho) is only for an open question's animation/large item that won't fit on Open Questions; keep it cleared otherwise"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 64761c6b-46f6-4217-a6f1-457b4de3152f
  modified: 2026-10-26T00:00:26.934Z
---

Owner, 2026-10-21: "I can't see the gifs you post as animated in chat. Maybe make an artifact where you place gifs you need to show me? They are animated in those."

Owner, 2026-10-25: "You can keep the review board cleared whenever things [are answered] ... I really only need it for whenever I'm working on an open project, but the item wouldn't fit in the question space."

The Review Board is at https://claude.ai/artifact/SHg2h5cuTDMN5qrKfiFRho. Its source is `tools/artifacts/review_board/index.html`, with its files in `media/`. Cleared on 2026-10-25 (empty-state line "Nothing here right now.").

**Why:** chat shows GIFs as stills; the board is the overflow for an open question's item, not an archive.
**How to apply:**
- Default home for a question's pictures is its Open Questions card. Use the board only when an item for an OPEN question will not fit there (long animations, large sheets); link it from the Qn card.
- When that question is answered, remove its card from the board. No "Answered" or reference cards; an empty board is normal.
- Republish the same URL and commit the source.

Related: [[open-questions-artifact]], [[batched-numbered-questions]], [[gfx-atlas-artifact]].
