# Development notes (recovery point)

Everything needed to pick the work back up if a session's context is lost.

| Path | Contents |
|---|---|
| `SUPERVISOR.md` | How the main session works: delegate, verify, goldens, merge, report. |
| `LESSONS.md` | Best practices and tools found during the project; carried over to the next game. |
| `notes/QUEUE.md` | The work queue: what's next, with briefs (for example, the Sunday 2026-10-25 Saloon patron build). |
| `notes/PATRON_SPEC.md`, `notes/PATRON_QA_answers.md` | The patron art spec and the owner's answers. |
| `notes/HANDOFF_2026-10-25.md` (latest), `notes/HANDOFF_2026-10-17.md`, `notes/PLAN.full.md` | An earlier hand-off and the full plan history. |
| `agent_rules/` | The rules every worker agent is briefed with (`rules_code.txt`) and shared brief parts. |
| `queue_briefs/` | Briefs for queued agent tasks. |
| `concepts/` | Patron concept art and candidates (ASCII + PNG), including the owner's redraws (DUSTY, HANK, MABEL, REDD). |
| `memory_snapshot/` | A copy of Claude's memory notes for this project: the owner's decisions and standing rules. |

The review pages' sources live in `tools/artifacts/` and `tools/gfx_atlas/`; see `tools/artifacts/README.md`.

Update rule: when the working copies change (queue, briefs, concepts, memory), copy them here in the same session.
