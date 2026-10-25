#!/usr/bin/env python3
"""Keep long test and build output out of the context window.

Two modes:
  hook mode (no arguments): a Claude Code PreToolUse hook for Bash. Reads the tool call as JSON on stdin. If the
      command is a plain `make`, `make test`, `make check`, `make cfall` or `pytest` run (optionally with VAR=value
      prefixes), it rewrites the command so the full output goes to a log file and only a summary is printed.
      Any other command is left alone.
  summary mode (`filter_test_output.py --summary LOG`): prints the summary of a log.

Nothing is lost: short output (<= SHORT lines) is printed whole, and the full log's path is always printed.
The exit code of the original command is kept.
"""
import json
import re
import shlex
import sys

SHORT = 30           # print the whole log if it is this short
MAX_MATCHES = 120    # cap on matched lines in a long log
TAIL = 15            # last lines of a long log (pytest summary, romusage, gbcheck verdicts)

# Plain test/build commands only: env prefixes allowed, no pipes, redirects, chaining or substitution.
ENV = r"(?:[A-Za-z_][A-Za-z0-9_]*=[^\s;&|<>`$()]+\s+)*"
CMD = r"(?:make(?:\s+(?:-B|-j\d*|test|check|cfall|preview|atlas|[A-Za-z_]+=[^\s;&|<>`$()]+))*" \
      r"|(?:python3\s+(?:-I\s+)?-m\s+)?pytest(?:\s+[^;&|<>`$()]+)?)"
PATTERN = re.compile(r"^\s*" + ENV + CMD + r"\s*$")

INTERESTING = re.compile(
    r"^(FAILED|ERROR)\b|^E\s|Traceback|Error|error:|\bfailed\b|\bpassed\b|golden|bbox|"
    r"\[(dmg|cgb)\]|WRAM|ROM0|romusage|warning:|Timeout|Killed",
    re.IGNORECASE,
)


def summarize(path):
    try:
        with open(path, errors="replace") as f:
            lines = f.read().splitlines()
    except OSError as e:
        print(f"[filter] could not read {path}: {e}")
        return
    if len(lines) <= SHORT:
        print("\n".join(lines))
        return
    hits = [l for l in lines[:-TAIL] if INTERESTING.search(l)]
    if len(hits) > MAX_MATCHES:
        hits = hits[:MAX_MATCHES] + [f"... {len(hits) - MAX_MATCHES} more matching lines in the full log"]
    print(f"[filter] {len(lines)} lines of output; showing {len(hits)} matching lines and the last {TAIL}.")
    if hits:
        print("\n".join(hits))
        print("[filter] ---- last lines ----")
    print("\n".join(lines[-TAIL:]))


def hook():
    data = json.load(sys.stdin)
    cmd = (data.get("tool_input") or {}).get("command", "")
    if not cmd or "\n" in cmd or not PATTERN.match(cmd):
        print("{}")
        return
    me = shlex.quote(__file__)
    wrapped = (
        'LOG=$(mktemp "${TMPDIR:-/tmp}/claude-testlog.XXXXXX"); '
        f"{{ {cmd} ; }} > \"$LOG\" 2>&1; rc=$?; "
        f'python3 {me} --summary "$LOG"; '
        'echo "[filter] full output: $LOG (exit $rc)"; exit $rc'
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "updatedInput": {**data["tool_input"], "command": wrapped},
        }
    }))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--summary":
        summarize(sys.argv[2])
    else:
        try:
            hook()
        except Exception:
            print("{}")  # never block a command because the filter failed
