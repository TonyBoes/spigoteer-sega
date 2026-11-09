# How the supervisor session works (Spigoteer)

This is the working method the main Claude session follows. The owner's standing rules are in `memory/` and in
CLAUDE.md's Project rules; this file is the procedure that ties them together.

## Roles
- **Owner:** makes the look, sound and feel decisions, and answers numbered questions. He pushes to GitHub himself.
  He is also the one who types `/compact` and `/clear`: the supervisor tells him when.
- **Supervisor (main session, Opus):**
  - turns the owner's asks into exact briefs;
  - delegates, judges the results and merges;
  - is the only one who replaces goldens;
  - keeps the review pages and notes current, through helpers.
- **Workers and helpers (subagents, defined in `.claude/agents/`; about 3 at once):**

  | Agent | Model | Use for |
  |---|---|---|
  | `gb-worker` | Sonnet, own worktree | every code and feature brief |
  | `gb-artist` | Sonnet, own worktree, gb-pixel-art skill loaded | every art brief |
  | `gb-golden-check` | Sonnet, read-only | checking changed goldens before you replace them |
  | `gb-runner` | Haiku, no edits | verify runs, atlas and Pocket Player builds, orphan checks, cleanup lists, docs sync |

  Opus or Fable only when the owner names them (the music split: Fable writes specs, Opus builds). Then pass the
  model on that Agent call.

## Keep the supervisor's context small (the owner's tokens)
Every supervisor call re-reads the whole conversation. In the week to 2026-10-24 that averaged 515k tokens per call
over 1,950 calls, 45% of all usage. Cost per call scales with context size.
- **Mechanical steps go to helpers.** If a step is running a script, reading a log, building a page, listing
  branches or syncing files, brief `gb-runner`. Keep for yourself: briefs, judgement, merges, golden copies, owner
  talk, publishing (if helpers lack the tool).
- **Milestone handoffs.** After each merge-and-report (step 7), update `docs/dev/notes/HANDOFF_<date>.md` (state,
  running agents, open Qn, next steps). Then tell the owner one of:
  - no agents running: "Safe to `/clear` now; start the next session with: read the handoff";
  - agents running: "Good point to `/compact`".
- **Before the owner steps away** (overnight, a meeting), say so too: the first message after a cache expiry
  re-processes the whole context, so a `/clear` (no agents running) or `/compact` first saves a large re-write.
- **Compaction:** automatic (no autoCompactWindow override). CLAUDE.md's "Compact instructions" say what survives.
- **Images:** ask for ONE labelled contact sheet per review instead of opening many stills.
- **Reading:** grep, then read ranges. Never read `PLAN.full.md` or `ALL_AGENT_BRIEFS.md` whole.

## The loop for a change
1. **Read the ask.** Turn layout or design asks into an exact table (rows, columns, colours) before briefing. Three
   misreads happened when this step was skipped.
2. **Brief the agent** (`gb-worker` or `gb-artist`). The project rules are in CLAUDE.md and the agent definitions,
   and the recurring procedures are skills (`spigoteer-music`, `-patrons`, `-minigames`, `-review-pages`). Name the
   skill in the brief instead of restating it; write only what is new for this task. A brief has five parts:
   - the goal, quoting the owner's words;
   - the files involved;
   - the decisions already made;
   - the task's own limits (anything beyond CLAUDE.md's budgets);
   - the verification list and the deliverables (contact sheet, GIFs, ROM path, report).

   Art briefs produce proposals first; nothing is imported before the owner picks. `briefs/ALL_AGENT_BRIEFS.md` has
   every brief sent.
3. **Arm the watchdog.** `tools/dev/watch_agents.sh 15 <agent-id>...` with the Bash tool in the background. It is
   silent until an agent's transcript has been idle 15 minutes. Restart it with the current list whenever you launch
   an agent or one finishes; it stops the previous copy itself.
4. **Review the report.** Look at the contact sheet yourself, and separate what the agent checked from what it
   assumed.
5. **Goldens.**
   - Brief `gb-golden-check` with the worktree, the failing goldens and the intended change.
   - Read its table. Open its contact sheet for every UNEXPECTED or UNSURE row; decide those yourself.
   - Then copy each file by hand. Never use bulk `GB_UPDATE_GOLDEN=1`.
   - Name every replaced golden and the reason in the commit.
6. **Merge main into the branch, then verify.** Brief `gb-runner`: `tools/dev/verify.sh <worktree> <name>` (about
   8 min). The default stages are `make -B`, `make cfall`, the full pytest, `make check`, and the `RUN_SLOW`
   double-speed and half-rate tests, ending with a RESULT line. `FULL=1` adds the `RUN_SLOW=1` fade tests (engine, fade,
   timing or music changes, and before any release). `CBUILD=1` adds the full pytest on `build/game-c.gb` (only before
   a porting release, while C tests are on hold). `QUICK=1` is accepted and does nothing.
   **One full run per change (owner Q12, 2026-11-08):** the verify run is the only full test run. Briefs tell agents
   to run only the tests for the area they touch while working (`pytest -k`, the relevant files), plus `make` and
   `make check`, and to leave the full `make test` to verify.
7. **Fast-forward main.** No full test run on main after a fast-forward of the verified tip. If another branch was
   merged in between (the merge is not a fast-forward of what verify tested), brief `gb-runner` to run `make cfall`,
   `make`, `make test`, `make check` once on main. **The supervisor never runs a full `make test` or `verify.sh`
   itself (owner, test batch 1, 2026-11-09): every full run goes to `gb-runner`, including this rerun.** Targeted
   tests (one file, `-k`) are fine. Then, through `gb-runner` where possible:
   - refresh Pocket Player's ROMs and republish;
   - `make atlas`, rebuild the Graphics Atlas (palette_plan/build.py) and republish after art changes;
   - update the Open Questions page;
   - sync `docs/dev/`;
   - add any lesson to `LESSONS.md`.
8. **Tell the owner** what changed, in plain words, that he can `git push`, and whether it is a good point to
   `/clear` or `/compact` (see above).

## Talking to the owner
- Only real questions get a number (Qn, continuing from the last). Batch them. Each goes on the Open Questions page
  with its pictures, and comes off when answered.
- Use bare labels on owner pages: no explanatory parentheses.
- For every feature, say whether it fits the DMG or is Color only.
- His test lists hold only look, sound and feel calls; the supervisor verifies the mechanics.

## Housekeeping
- After agents finish, have `gb-runner` check `ps` for orphaned pytest or profiler processes.
- Wait on a PID or a log marker; never on a `pgrep -f` loop, which matches itself.
- Delete branches only by exact name, listing them first (a `gb-runner` cleanup list).
- Check `/usage` once a day: its breakdown and recommendations show which agents and habits cost most.

## Owner decisions and plans: write first, then follow (owner 2026-11-01)
**Rule (owner 2026-11-01):** "When the owner gives a rule, decision or plan, save it to its file in the same turn (memory note for standing rules, QUEUE for plans) before replying, and say where it was saved. Conversation is not storage."

Owner: "write every standing decision and plan into the queue or memory notes as soon as i make it. You keep forgetting
plans that we've made and procedures I want you to follow. The Atlas has been an absolute mess. And whenever it came time
to follow it, you didn't follow it."
1. Record in the same reply, before acting on it: a patron/palette/art decision -> the Atlas (plan_data.py + a LOG line in
   build.py, republished); a plan or task -> docs/dev/notes/QUEUE.md; a standing rule or procedure -> a memory note (and
   here if it is about how the supervisor works). Quote his words. Commit it.
2. Before every brief: grep QUEUE.md and the memory index for the topic and put the decisions in the brief. Patron or
   palette work: the brief starts from the Atlas (docs/dev/queue_briefs/extra_looks_slots.md, regenerated when the plan
   changes) and says "implement this as written".
3. Before a question reaches the owner: check it against QUEUE.md, memory and the Atlas. If they answer it, do not ask.
   Only a hard limit (perf guard, budget, a rule) that stops the plan goes to him, with numbers.
4. The Atlas self-check is the safety net: it fails on a patron shown on two palettes or a venue whose plan does not fit.
   When the Atlas looks wrong, fix the generator and add a check, never hand-wave it.
