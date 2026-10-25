#!/bin/bash
# Stall watchdog for background subagents. Replaces re-arming a Monitor every 30 minutes.
#
#   tools/dev/watch_agents.sh <idle-minutes> <agent-id> [<agent-id> ...]
#
# Run it with the Bash tool in the background (run_in_background). It stays silent while every listed agent's
# transcript keeps changing, and EXITS (which wakes the session) only when:
#   - an agent's transcript has had no activity for <idle-minutes>   -> "STALL agent-<id> idle <n> min"
#   - a transcript cannot be found                                   -> "MISSING agent-<id>"
#   - it has run for 8 hours                                         -> "WATCHDOG_TIMEOUT"
#
# Restart it with the current list whenever you launch an agent or one finishes (you are awake then anyway).
# Starting a new watchdog stops the previous one through its PID file, so there is never more than one.
# No pgrep: it matches its own loop.

set -u
IDLE_MIN=${1:?usage: watch_agents.sh <idle-minutes> <agent-id>...}
shift
[ $# -ge 1 ] || { echo "usage: watch_agents.sh <idle-minutes> <agent-id>..."; exit 1; }

PIDFILE=/workspace/out/watchdog.pid
mkdir -p /workspace/out
if [ -f "$PIDFILE" ]; then
  OLD=$(cat "$PIDFILE")
  if [ -n "$OLD" ] && [ "$OLD" != "$$" ] && kill -0 "$OLD" 2>/dev/null; then kill "$OLD" 2>/dev/null; fi
fi
echo $$ > "$PIDFILE"
trap '[ "$(cat "$PIDFILE" 2>/dev/null)" = "$$" ] && rm -f "$PIDFILE"' EXIT

ROOT=${CLAUDE_CONFIG_DIR:-$HOME/.claude}/projects/-workspace
find_transcript() {
  # newest match for this agent id in any session of this project
  ls -t "$ROOT"/*/subagents/agent-"$1".jsonl 2>/dev/null | head -1
}

START=$(date +%s)
LIMIT=$((IDLE_MIN * 60))
while true; do
  NOW=$(date +%s)
  for ID in "$@"; do
    ID=${ID#agent-}
    F=$(find_transcript "$ID")
    if [ -z "$F" ]; then
      # give a just-launched agent two minutes to create its transcript
      if [ $((NOW - START)) -gt 120 ]; then echo "MISSING agent-$ID"; exit 3; fi
      continue
    fi
    AGE=$((NOW - $(stat -c %Y "$F")))
    if [ "$AGE" -ge "$LIMIT" ]; then
      echo "STALL agent-$ID idle $((AGE / 60)) min ($F)"
      echo "last entry: $(tail -c 400 "$F" | tr -d '\n' | tail -c 300)"
      exit 2
    fi
  done
  if [ $((NOW - START)) -ge 28800 ]; then echo "WATCHDOG_TIMEOUT"; exit 4; fi
  sleep 60
done
