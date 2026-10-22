BRIEF (queued 2026-10-21; uses the gb-pixel-art skill's references/briefs.md template)

TASK
A hand clean-up of ONE saloon bar patron for the Game Boy / Game Boy Color game "Spigoteer": THE OUTLAW (slot C), front and back view, 16x16 each.
The owner likes this figure as he is. This is a CLEAN-UP, NOT A REDRAW: keep his design, silhouette, proportions, colours and look. Change only pixels that break the skill's rules.

SCOPE AND GATE
- One asset only: the outlaw, front + back. Finish it completely, including the clean-up log, the 1x comparison and the self-audit table. Then stop for review.
- Every changed pixel must be justified in the clean-up log by a rule. If a fix would visibly change his look, list it as a proposal with a before/after image; do not apply it.

HARD RULES (from the gb-pixel-art skill)
- Decide every pixel yourself (SKILL.md rule 1). Code may only transcribe your hand-edited grid, render previews and run checks. No script may outline, mirror, fill, shade or generate pixels.
- His current outline was made by a script (a uniform 1 px shade-3 outline on every edge; see scratchpad/saloon_patrons/SKILL_DEVIATIONS.md). Fix its typical faults by hand: L-shaped doubles, staircase steps, a V-point chin, uneven runs, and outline weight where selective outlining applies. Keep everything that already reads well.
- The house format makes outlines easy to compute (`#` is both the outline and the darkest shade). Outlines are still hand-placed.
- Do the clean-up pass by hand and include the clean-up log (pixel coordinates, before -> after, the rule).
- Lint PASS is not a quality judgement.
- Repository rules: read and obey scratchpad/decisions/rules_code.txt. Nothing goes into main. Never replace goldens.

REQUIRED READING BEFORE THE FIRST PIXEL
- ~/.claude/skills/gb-pixel-art/SKILL.md in full.
- From the skill's table for characters: references/sprites.md, references/linework.md, references/light-and-form.md; figures 03, 11, 12, 15, 18, 20. Also references/portraits.md and figure 19, for small faces.
- Project notes: scratchpad/PATRON_SPEC.md (all 12 sections: the patron constraints, the walls behind patrons, the quality examples); the headers of assets/art/patrons/cowboys.txt and cowboys_back.txt.
- In your first message, list what you read and quote one rule from each.

THE FIGURE
- scratchpad/saloon_patrons/potentials/outlaw_round1/: outlaw.txt, outlaw_back.txt, palette.json (variant "c" colours; the wall is #2c5060).
- He is round 1's d2_dusty variant C: flat dark hat with a band, bandana, poncho.
- See him in context: scratchpad/saloon_patrons/all_compare_x8.png (the d2_dusty rows) and d2_context_x4.png.

QUALITY BAR
- Prospector 1, scratchpad/saloon_patrons/potentials/prospector_1/, which the owner called "much improved"; and the current approved trio in assets/art/patrons/cowboys.txt.
- Compare at 1x in DMG shades and CGB. If yours is rougher, redo the clean-up rather than listing it as a concern. But do NOT drift from his design.

PROJECT CONSTRAINTS (PATRON_SPEC.md has the details)
- 16x16, front in 3/4 view facing right; back 16x16.
- Index 0 is the wall, and transparent when lifted. No index-0 holes. Indices 1-3 are light to dark.
- One palette, not enhanced.
- The held mug covers his right half at face height (spec section 8). Check that his face still reads with it there.
- The whole picture is flipped on mirrored levels.
- The back view must be symmetric about column 8 with column 0 empty if he goes into slot A. As slot C, symmetry is optional: keep his back as it is unless a rule needs a fix.
- The wall behind him is white on DMG and dark teal on CGB (spec section 11). Check both.

DELIVERABLES, in scratchpad/saloon_patrons/potentials/outlaw_round1_cleanup/:
- outlaw.txt, outlaw_back.txt, palette.json, indexed PNGs.
- Before/after previews at 1x and 4x, DMG and CGB-corrected, beside the quality bar: front, back, and with the mug.
- One in-game screenshot at x4, DMG and CGB, from a throwaway build with him as variant C.
- The clean-up log, the filled-in self-audit table (SKILL.md section 9) with figure-specific evidence in every row (no template text), and the engine questions.
Then STOP and report. Kill every process you start.
