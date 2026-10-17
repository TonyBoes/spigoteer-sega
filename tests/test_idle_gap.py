"""No long wait for patrons (owner 2026-10-17: "On the stadium last call I ended up sitting for many seconds waiting for patrons").

A story shift's arrival pattern has breathers ('b', four spawn intervals); the quick refill (an empty screen brings the next patron within
REFILL_FRAMES) skipped them, so a breather on an empty screen left the player with nothing to do for 4 intervals (the Stadium's Last call,
"all bars at once": about 16 s). Rule: while the goal is not met, the screen is never without a patron for more than IDLE_MAX frames
(about 2 s), in every shift of every chapter, played by a bot that serves each patron a fixed time after he is on the bar."""
import pytest
from test_flow import PLAYING, state
import test_story as ts

pytestmark = pytest.mark.timeout(900)

IDLE_MAX = 120 + 30            # about 2 s with a patron's emergence (he is live from the frame he spawns)
SERVE_AFTER = 70               # frames a patron stays on the bar before the bot's "serve" removes him


def idle_gaps(gb, c, k, frames=9000):
    """Play the shift with the bot: the longest run of frames with no patron on screen while the goal is not met."""
    sh = ts.SHIFTS[c][k]
    goal = sh["count"]
    gb.write("tip_chance", 0)
    age = {}
    idle = worst = 0
    for _ in range(frames):
        gb.run(1)
        if state(gb) != PLAYING:
            break
        st = gb.read("patron_state", 16)
        live = 0
        for p in range(16):
            if st[p]:
                live += 1
                age[p] = age.get(p, 0) + 1
                if age[p] >= SERVE_AFTER:                      # served: gone, the serve counted
                    gb.write(gb.addr("patron_state") + p, 0)
                    gb.write("served", min(255, gb.mem("served") + 1))
                    age[p] = 0
            else:
                age[p] = 0
        if gb.mem("intro_timer"):
            continue
        if gb.mem("spawned") >= gb.mem("quota") and not live:
            break
        if live:
            idle = 0
        else:
            idle += 1
            worst = max(worst, idle)
        if sh["type"] == ts.G_SERVE and gb.mem("served") >= goal:
            break
    return worst


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_stadiums_last_call_never_leaves_the_bar_empty_for_long(model):
    with ts.to_shift(model, 1, 2) as gb:
        assert idle_gaps(gb, 1, 2) <= IDLE_MAX


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("c", range(10))
@pytest.mark.parametrize("k", range(3))
def test_no_shift_leaves_the_bar_empty_for_long(model, c, k):
    if ts.SHIFTS[c][k]["type"] != ts.G_SERVE:
        pytest.skip("only serve goals count patrons served")
    with ts.to_shift(model, c, k) as gb:
        w = idle_gaps(gb, c, k)
        print(c, k, "worst idle", w)
        assert w <= IDLE_MAX, (c, k, w)
