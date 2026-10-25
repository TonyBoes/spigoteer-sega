# How the supervisor session works (Spigoteer)

This is the working method the main Claude session follows. The owner's standing rules are in `memory/`; this file is the procedure that ties them together.

## Roles
- **Owner:** makes the look, sound and feel decisions, and answers numbered questions. He pushes to GitHub himself.
- **Supervisor (main session, Opus):**
  - turns the owner's asks into exact briefs;
  - delegates, verifies and merges;
  - is the only one who replaces goldens;
  - keeps the review pages and notes current.
- **Workers (subagents):**
  - Sonnet by default, Opus only by exception, about 3 at once;
  - each in its own git worktree (`isolation: worktree`);
  - each follows `agent_rules/rules_code.txt`.

## The loop for a change
1. **Read the ask.** Turn layout or design asks into an exact table (rows, columns, colours) before briefing. Two misreads happened when this step was skipped.
2. **Brief the agent.** A brief has five parts:
   - the goal, quoting the owner's words;
   - the files involved;
   - the decisions already made;
   - the engineering limits (no new WRAM, ROM0 budget, keep the C twin of asm);
   - the verification list and the deliverables (stills, GIFs, ROM path, report).

   Art briefs must use the owner's `gb-pixel-art` skill. They produce proposals first; nothing is imported before the owner picks. `briefs/ALL_AGENT_BRIEFS.md` has every brief sent.
3. **Review the report.** Look at the images yourself, and separate what the agent checked from what it assumed.
4. **Goldens.**
   - Rerun the failing tests and collect `out/diff/*.actual.png`.
   - Compute each diff's bounding box and check the change is the intended one, for example by comparing against the old golden shifted.
   - Then copy each file by hand. Never use bulk `GB_UPDATE_GOLDEN=1`.
   - Name every replaced golden and the reason in the commit.
5. **Merge main into the branch, then verify.**
   - The script is `scripts/*_verify.sh`, all copies of `tests_verify.sh` with a different worktree path and log. It runs:
     - `make -B`
     - `make cfall`
     - the full pytest
     - `make check`
     - `RUN_SLOW=1` fade tests
     - the full pytest with `GB_ROM=build/game-c.gb`
     - `RUN_SLOW` double-speed and half-rate
   - Run it in the background, about 20 minutes.
6. **Fast-forward main.** Then:
   - refresh Pocket Player's ROMs and republish;
   - `make atlas` and republish after art changes;
   - update the Open Questions page;
   - sync `docs/dev/`;
   - add any lesson to `LESSONS.md`.
7. **Tell the owner** what changed, in plain words, and that he can `git push`.

## Talking to the owner
- Only real questions get a number (Qn, continuing from the last). Batch them. Each goes on the Open Questions page with its pictures, and comes off when answered.
- Use bare labels on owner pages: no explanatory parentheses.
- For every feature, say whether it fits the DMG or is Color only.
- His test lists hold only look, sound and feel calls; the supervisor verifies the mechanics.

## Housekeeping
- After agents finish, check `ps` for orphaned pytest or profiler processes.
- Wait on a PID or a log marker; never on a `pgrep -f` loop, which matches itself.
- Delete branches only by exact name, listing them first.
