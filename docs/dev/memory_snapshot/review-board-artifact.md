---
name: review-board-artifact
description: Owner can't see GIFs animate in chat. Put every animation for a question on the Review Board artifact (https://claude.ai/artifact/SHg2h5cuTDMN5qrKfiFRho)
metadata:
  type: feedback
---
Owner, 2026-10-21: "I can't see the gifs you post as animated in chat. Maybe make an artifact where you place gifs you need to show me? They are animated in those."

The Review Board is at https://claude.ai/artifact/SHg2h5cuTDMN5qrKfiFRho. Its source is the scratchpad review_board/index.html, with its files in media/.

**Why:** chat shows GIFs as stills, so animated review items were invisible to him.
**How to apply:**
- Any question that needs motion (animations, cycles, meters, gameplay clips): add a card to the Review Board, with the Q number in the card's tag only for real questions. Republish the same URL, and say in chat "see the Review Board, Q<n>".
- Remove cards once their question is answered.
- Stills can still go in chat under the question.

Related: [[batched-numbered-questions]], [[gfx-atlas-artifact]].
