Owner message 2026-11-09, verbatim:

From a helper agent. 

# Test Suite Audit — Investigation Only

Our tests have grown slow and are using a lot of tokens. Before we change anything, I need an accurate picture of how testing works in this project today.

## Ground rules

- **Read-only.** Do not edit, delete, consolidate, or add any tests, configs, hooks, CLAUDE.md, or agent files. Do not commit anything except the report below.
- **One timed run, at most.** You may run the full suite once to measure it. Delegate that run to the runner subagent, send raw output to `.claude/audit/test-run.log`, and have it return only a summary.
- **Spend tokens carefully.** Use cheap subagents for bulk file reading and counting, and have them return summaries rather than raw contents.
- **Report facts, not fixes.** If you have a recommendation, put it in the last section only.
- If something is unknown or can't be measured, say so. Don't guess.

## Questions

### 1. Inventory
- Test frameworks and tools in use, including golden/verdict-table checks, emulator or screenshot checks, and build checks.
- Every command used to run tests (full, single-file, single-test, by tag), and where each is defined.
- Count of test files and individual tests, broken down by type or folder.

### 2. Timing
- Total wall-clock time of the full suite (from the one timed run).
- The 10 slowest tests or groups, with times.
- Any setup or teardown cost that repeats per test (builds, ROM compiles, emulator boots, fixture generation).

### 3. When and how tests run
- Who triggers test runs: you, which subagents, hooks, or scripts?
- What triggers them: every edit, every task, before commits, on request?
- In a typical task, how often does the full suite run versus a targeted subset?
- Is there a documented targeted-test command? Do agents actually use it?

### 4. What comes back into context
- What output reaches your context after a test run: raw log, filtered log, or a summary?
- Approximate size of that output for a passing run and for a failing run.
- Verbosity flags currently used, and whether quieter options exist.
- Exactly what the runner subagent returns to you.

### 5. Growth history
- Test count over time, using git history (rough monthly or milestone counts are fine).
- Which agents or sessions add tests, and under what instructions?
- Any rule that says when to add a test, or when not to?

### 6. Possible redundancy (flag only, do not remove)
- Tests that appear to check the same behavior with different inputs or names.
- Tests for features or assets that no longer exist.
- Whether per-test coverage or mutation testing tools are available for this language and toolchain.

### 7. Current instructions, quoted
- Quote verbatim every testing-related instruction in CLAUDE.md, agent definitions, skills, and dev notes, with file path and line number.
- Any hooks in `.claude/settings.json` (or elsewhere) that touch test runs or output.
- Note any place where actual practice differs from what the instructions say.

### 8. Your own view
- Where does testing cost the most time? Where does it cost the most tokens?
- Anything about testing that has caused confusion, repeated work, or lost decisions.

## Deliverable

Write the report to `.claude/audit/test-audit-report.md`, using the section numbers above. Keep it compact: tables where they help, no pasted logs (reference the log file instead). End with:

- **Top 3 time costs** and **top 3 token costs**, each with evidence.
- **Recommendations (not yet approved):** a short list. Nothing gets changed until I review it.

When done, reply with only the report path and a 3-line summary.
