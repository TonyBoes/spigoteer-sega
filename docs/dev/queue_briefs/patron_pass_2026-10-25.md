BRIEF: patron design pass, 2026-10-25 (gb-pixel-art skill, references/briefs.md template)

Owner, 2026-10-25: "Take a look at all current patrons, not including the saloon patrons. Give each of them another
design pass using the skill we didn't have the first time around."
These are PROPOSALS only. Patron changes stay held: nothing goes into assets/, src/ or main, and nothing is committed.

TASK
A quality pass on Spigoteer's bar patrons (Game Boy / Game Boy Color, 16x16 busts at a bar), front and back view.
Keep each patron who he is: the same character, costume idea, silhouette and colours. Improve the drawing.

SCOPE AND GATE
- The 27 patrons of the 9 non-Saloon venues, in assets/art/patrons/<group>.txt (frames A, B, C) and <group>_back.txt.
  Names are in tools/artifacts/palette_plan/build.py NAMES.
- Your brief names the patrons you do. Finish the FIRST one completely (front + back, all pipeline steps, clean-up log,
  1x comparison, self-audit table) and STOP for review before the others.
- If the rest cannot all be hand-drawn to the same standard, deliver fewer.

A PASS, NOT A REDRAW
- The owner approved these designs in earlier rounds. Keep each design and its readable details.
- Fix what breaks the skill's rules: script-like uniform outlines, L-shaped doubles, staircases, V or "arrowhead" chins,
  flat faces with no light/shade, features that merge on the DMG, a silhouette lost on the venue's dark CGB wall.
- The owner reads tiny details differently from agents (he once read a removed pixel cluster as an ear, and scarf
  buttons as eyes). Do not remove a detail whose meaning you are unsure of: keep it and list it as a question.
- If a fix would visibly change the look, show it as an option beside the minimal version; do not apply it silently.

HARD RULES (from the gb-pixel-art skill)
- Decide every pixel yourself (SKILL.md rule 1). Code may only transcribe your hand-edited grid, render previews and
  run checks. No script may outline, mirror, fill, shade or generate pixels. An asset made that way is not delivered.
- The house format makes outlines easy to compute (`#` is both the outline and the darkest shade). Outlines are still
  hand-placed. Back views are drawn, not mirrored by script.
- Do the clean-up pass by hand and include the clean-up log (pixel, before -> after, the rule).
- Lint PASS is not a quality judgement.
- Repository: read docs/dev/agent_rules/rules_code.txt. Work only in your worktree's docs/dev/concepts/patron_pass/<group>/ (NOT out/: out/ is git-ignored, and a worktree with only ignored changes is deleted when the agent finishes; CEDAR's first run was lost that way). No commits.

REQUIRED READING BEFORE THE FIRST PIXEL
- ~/.claude/skills/gb-pixel-art/SKILL.md in full.
- references/sprites.md, references/linework.md, references/light-and-form.md, references/portraits.md;
  figures 03, 11, 12, 15, 18, 19, 20.
- docs/dev/notes/PATRON_SPEC.md, all 12 sections (the held mug in section 8, back views in 9, walls in 11, quality in 12),
  and the headers of the group's .txt files.
- In your first message, list what you read and quote one rule from each.

QUALITY BAR
- The Saloon's planned art, which the owner approved or drew himself: tools/artifacts/palette_plan/art/cowboys_redd.txt
  (the outlaw; the owner's favourite), cowboys_rosie.txt (redrawn by the owner), cowboys_emma.txt, cowboys_gus.txt.
- Compare at 1x, in DMG shades and in CGB on the venue wall. If yours is rougher, redo it rather than listing a concern.

PROJECT CONSTRAINTS (PATRON_SPEC.md has the details)
- 16x16; front in 3/4 view facing right; back 16x16. The whole picture is flipped on mirrored levels.
- Index 0 is the wall, transparent when lifted; no index-0 holes. Indices 1-3 light to dark; keep each figure's
  colour-slot use (skin stays in the same index), because palettes are shared between patrons.
- Variant A's back view must be symmetric about column 8 with column 0 empty (as tests/test_cowboy_back.py checks the
  Saloon's). B and C: keep the back's symmetry as it is.
- The held mug covers his right half at face height (spec section 8): the face must still read with it there.
- Preview colours: the PLANNED palettes from the Palette Plan (python3 tools/artifacts/palette_plan/build.py writes a
  Markdown table per venue; the planned colours are also in its PLANS), on the venue's CGB wall:
  sports #39415A, lodge #6A4A31, bistro #295A5A, igloo #4A417B, factory #523129, biker #39294A, teahouse #4A6A5A,
  zoo #204A5A, space #20295A. DMG: shades 0-3 on white. All 27 are DMG looks too, so both must read.

DELIVERABLES (in docs/dev/concepts/patron_pass/<group>/ in your worktree)
- <name>.txt (front) and <name>_back.txt in the house format.
- One contact sheet per patron with tools/dev/contact_sheet.py: before | after, front and back, DMG and CGB, x4, plus
  the 1x comparison beside the quality bar.
- The clean-up log, the self-audit table (SKILL.md section 9), and questions about any detail you were unsure of.
- Report: the files, what changed per patron in one or two lines, the self-audit rows 1-3, any deviation from the
  skill quoted exactly.
