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
- Backs: keep each back's symmetry as it is. Only the Saloon's variant A must be symmetric (PATRON_SPEC section 9;
  tests/test_cowboy_back.py); these venues' A backs need not be.
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

OWNER 2026-10-25 (Q55, answer 1): CEDAR IS DONE, AS THE OWNER DREW HIM. HIS CEDAR IS THE QUALITY BAR AND STYLE GUIDE.
- File: docs/dev/concepts/patron_pass/lumberjacks/cedar_owner.txt (front). His changes to the old CEDAR show the level of
  change he wants: a patterned cap (red/black check), dark hair showing under it, brows over the eyes, an open collar
  with a V of skin, a broken buffalo-check plaid instead of even stripes. More character, same person.
- So this is more than a clean-up: give each patron that kind of character detail, keeping who he is (costume idea,
  colours, silhouette). Bolder changes than his are options beside the main version, not the main version.
- Put cedar_owner.txt FIRST in the quality bar, before the Saloon four. Compare every figure with it at 1x.

PLANNED PALETTES (colours 1-3; the Palette Plan, owner merges 2026-10-25). Shared palettes: check every patron that shares.
- sports (#39415A): PETE #FFE6CD #E63931 #311818 (shares the full mug); SERENA #B47B52 #295ADE #000000;
  NORM #FFFFF6 #F6BD8B #202031 (Sal's)
- lumberjacks (#6A4A31): CEDAR and WILLOW #FFC594 #D53129 #291820 (shared); ASH #BD7B52 #399441 #102910
- chefs (#295A5A): PIERRE and BRIE #FFFFF6 #F6BD8B #202031 (Sal's); BASIL #F6F6EE #CD8B5A #411820
- divers (#4A417B): IGGY #E6AC7B #5ABDFF #101829; POLLY #D59C7B #318B7B #102929; MOOSE #B4734A #627B39 #101808
- robots (#523129): BOXY #5AF6FF #7B8BA4 #101829; VOLTA #FFD55A #BD8B4A #181829; BLIP #CDFFCD #5AA46A #102010
- punks (#39294A): SPIKE #FFCDA4 #F64AA4 #180818; BANDIT #F6BD94 #4ACD4A #100810 (shares the band's); SLICK #FFDEC5 #397BFF #100829
- ninjas (#4A6A5A): KAGE #FFCDA4 #29396A #080810; SAKURA #FFEEDE #CD2939 #181010 (shares the drummer's); RONIN #EEBD7B #AC2931 #201018
- zoo (#204A5A): COCO #F6D5A4 #8B5229 #291808 (shares the full mug); BAMBOO #FFFFF6 #A4A4B4 #101010; MUDDY #F6B4C5 #947BAC #201029
- aliens (#20295A): ZORP #F6FF9C #4ACD62 #102020 (full mug); XENO #E6E6EE #9CA4B4 #101018 (empty mug); GLORP #8BFFF6 #EE7B31 #311008

OWNER 2026-10-26 (Q56-Q58 answered, in order of presentation): "Where I kept the old versions try again."
- Lodge: new, new, old. Stadium: new, old, old. Bistro: old, old, new. Factory: new, new, new. Igloo: old, old, old.
  Cow: new, new, new. Tea house: old, new, old. Zoo: new, new, old. UFO: old, old, old.
- ACCEPTED (round 1 pass, front + back; a quality pass before import stays the default): CEDAR (owner's), WILLOW, PETE,
  BASIL, BOXY, VOLTA, BLIP, SPIKE, BANDIT, SLICK, SAKURA, COCO, BAMBOO.
- ROUND 2 (he preferred the old drawing; no reason given): ASH, SERENA, NORM, PIERRE, BRIE, IGGY, POLLY, MOOSE, KAGE,
  RONIN, MUDDY, ZORP, XENO, GLORP. Start from the OLD sprite (assets/art/patrons/), not the round-1 draft. Files:
  <name>_v2.txt and <name>_v2_back.txt; round-1 files stay as the record.

OWNER 2026-10-26 (Q59, round 2): "Ok, things you can keep: v2 backs on ash, serena, norm, brie, ronin, zorp, xeno,
and glorp. v2 fronts on glorp"
- KEPT FROM ROUND 2: backs ash_v2_back, serena_v2_back, norm_v2_back, brie_v2_back, ronin_v2_back, zorp_v2_back,
  xeno_v2_back, glorp_v2_back; front glorp_v2. No options taken.
- NOT KEPT: every other v2 front (ASH, SERENA, NORM, PIERRE, BRIE, IGGY, POLLY, MOOSE, MUDDY, KAGE, RONIN, ZORP, XENO)
  and the backs of PIERRE, IGGY, POLLY, MOOSE, MUDDY, KAGE.
- Match check: serena_v2_back has a sleeve stripe and ronin_v2_back gold chevrons that their OLD fronts lack.

OWNER 2026-10-26 (Q60): "Old version will stand. I'm going to edit them manually."
- Every drawing not kept in round 1 or 2 stays the OLD one (assets/art/patrons/). No round 3; no agent redraws these.
- The owner edits them by hand himself (the SERENA sleeve stripe / RONIN chevron mismatch with kept backs is his call).
- The pass is closed for agents. Final set per patron = round-1 picks + round-2 picks + old for the rest + his edits.
