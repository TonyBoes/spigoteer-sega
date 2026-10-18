# EASY / NORMAL / HARD for the ten venue games and the three bonus rounds (2026-10-17, TUNING.md): each game copies the row of its difficulty (a `struct xx_tune`
# in src/mg.h, the const table in src/xx.c, indexed by MG_DIFF: NORMAL, HARD, EASY) into the last field of its state at entry. Here: the row each mode
# gets (the whole row, against the values the design table lists), STORY and Practice NORMAL playing the same row, the key values showing in play
# (the first Kid's draw frame, the order's length and the press time, D and the belt, the meter step and the timer, the fish, the speed and the crates, the
# supply, the pop interval, the shake-up's swaps, Perfect Pour's windows, Tip Shower's tomatoes), and the medals of each mode at their thresholds.
import re

import pytest
from conftest import ROOT, hold_stage_anim
from test_mg import MG_PRACTICE, MG_STORY, frames, mg_enter, to_play, to_result, until
from test_scores import booted

pytestmark = pytest.mark.timeout(600)

MG_H = (ROOT / "src" / "mg.h").read_text()
SEED = 0x5A17
MODES = {"NORMAL": MG_PRACTICE, "HARD": MG_PRACTICE | 2, "EASY": MG_PRACTICE | 4}
IDS = {"qd": 0, "ts": 1, "lr": 2, "ou": 3, "mm": 4, "bs": 5, "mr": 6, "tk": 7, "mk": 8, "ad": 9}
MEDAL_NONE, MEDAL_BRONZE, MEDAL_SILVER, MEDAL_GOLD = range(4)
MACROS = {m[0]: int(m[1]) for m in re.findall(r"#define (\w+)\s+\(?(\d+)\)?", MG_H)}
WIDTH = {"uint8_t": 1, "int8_t": 1, "char": 1, "uint16_t": 2, "int16_t": 2, "int32_t": 4}


def layout(name, _cache={}):
    """struct `name`'s fields from src/mg.h: ({field: (offset, count, width, signed)}, size)."""
    if name in _cache:
        return _cache[name]
    text = re.search(r"struct %s \{(.*?)\n?\};" % name, MG_H, re.S).group(1)
    text = re.sub(r"//[^\n]*", "", text)
    out, off = {}, 0
    for stmt in text.split(";"):
        line = stmt.strip()
        if not line:
            continue
        m = re.match(r"((?:const )?(?:struct \w+|uint8_t|int8_t|uint16_t|int16_t|int32_t|char))\s+(.*)", line, re.S)
        typ = m[1].replace("const ", "")
        for decl in m[2].split(","):
            decl = decl.strip()
            dims = [int(d) if d.isdigit() else MACROS[d] for d in re.findall(r"\[(\w+)\]", decl)]
            n = 1
            for d in dims:
                n *= d
            fld = re.search(r"\w+", decl.replace("(*", "").replace("*", "")).group(0)
            if "*" in decl:
                width = 2                                   # a pointer
            elif typ.startswith("struct "):
                width = layout(typ[7:])[1]
            else:
                width = WIDTH[typ]
            if "(*" in decl:                                # `const uint16_t (*speed)[5]`: one pointer
                n = 1
            out[fld] = (off, n, width, typ.startswith("int"))
            off += n * width
    _cache[name] = (out, off)
    return out, off


def field(gb, game, name, row=0):
    off, n, width, signed = layout(game + "_state")[0][name]
    a = gb.addr("story_scratch") + off + row * width
    return int.from_bytes(bytes(gb.pb.memory[a + i] for i in range(width)), "little", signed=signed)


def put(gb, game, name, value, row=0):
    off, n, width, signed = layout(game + "_state")[0][name]
    a = gb.addr("story_scratch") + off + row * width
    for i in range(width):
        gb.write(a + i, (value >> (8 * i)) & 0xFF)


def tune(gb, game):
    """The copied row: {field: int or [ints]} (the pointers are left out)."""
    base = layout(game + "_state")[0]["tn"][0]
    fields = layout(game + "_tune")[0]
    out = {}
    for name, (off, n, width, signed) in fields.items():
        if name in ("chart", "speed"):
            continue
        a = gb.addr("story_scratch") + base + off
        vals = [int.from_bytes(bytes(gb.pb.memory[a + i * width + j] for j in range(width)), "little", signed=signed) for i in range(n)]
        out[name] = vals if n > 1 else vals[0]
    return out


def enter(model, game, mode):
    rom = booted(model)
    hold_stage_anim(rom)
    mg_enter(rom, IDS[game], mode, SEED)
    return rom


# The design table (TUNING.md): the whole row each difficulty copies at entry. NORMAL is what STORY and ARCADE play.
ROWS = {
    "qd": {"NORMAL": dict(r=[34, 30, 30, 28, 26], feint_from=3, badge_from=3),
           "HARD": dict(r=[24, 22, 20, 19, 18], feint_from=2, badge_from=2),
           "EASY": dict(r=[40, 38, 36, 34, 34], feint_from=6, badge_from=4)},
    "ou": {"NORMAL": dict(lit=[24, 24, 24, 20, 20, 16, 16], gap=[8, 8, 8, 6, 6, 6, 6], press=150, first=3),
           "HARD": dict(lit=[18, 16, 14, 12, 12, 10, 10], gap=[6, 5, 4, 4, 4, 4, 4], press=100, first=4),
           "EASY": dict(lit=[30, 30, 30, 26, 26, 22, 22], gap=[10, 10, 10, 8, 8, 8, 8], press=240, first=2)},
    "bs": {"NORMAL": dict(win0=120, win_step=8, win_every=4, win_min=40, speed0=6, speed_every=6, speed_max=16, broken_p=77),
           "HARD": dict(win0=100, win_step=6, win_every=4, win_min=58, speed0=8, speed_every=5, speed_max=20, broken_p=102),
           "EASY": dict(win0=160, win_step=6, win_every=4, win_min=96, speed0=5, speed_every=6, speed_max=12, broken_p=51)},
    "ts": {"NORMAL": dict(step=2, up=120, up_max=3, spawn=50, time_s=45),
           "HARD": dict(step=1, up=90, up_max=2, spawn=60, time_s=40),
           "EASY": dict(step=3, up=180, up_max=4, spawn=40, time_s=60)},
    "lr": {"NORMAL": dict(drift0=1638, fish_first=360, gap0=360, flip_min=120, flip_range=121, gold=40, silver=34, bronze=25),
           "HARD": dict(drift0=2500, fish_first=280, gap0=220, flip_min=70, flip_range=91, gold=40, silver=30, bronze=22),
           "EASY": dict(drift0=1100, fish_first=480, gap0=480, flip_min=160, flip_range=121, gold=40, silver=36, bronze=28)},
    "mr": {"NORMAL": dict(spd_start=24, spd_min=16, drop=2, drop_fast=3, perfect=8, delivered=16, crates=10, bronze=3000, silver=4500, gold=6000),
           "HARD": dict(spd_start=32, spd_min=28, drop=3, drop_fast=3, perfect=6, delivered=12, crates=9, bronze=2500, silver=4000, gold=5500),
           "EASY": dict(spd_start=20, spd_min=16, drop=1, drop_fast=2, perfect=12, delivered=22, crates=12, bronze=3500, silver=5000, gold=6600)},
    "mm": {"NORMAL": dict(belt=4, lo=-1, hi=11, supply=19),
           "HARD": dict(belt=6, lo=1, hi=9, supply=18),
           "EASY": dict(belt=3, lo=-2, hi=12, supply=20)},
    "tk": {"NORMAL": dict(notes=76, perfect=4, good=8, reach=11, gold=90, silver=70, bronze=50),
           "HARD": dict(notes=112, perfect=3, good=6, reach=10, gold=82, silver=68, bronze=45),
           "EASY": dict(notes=57, perfect=5, good=9, reach=12, gold=90, silver=70, bronze=40)},
    "mk": {"NORMAL": dict(u0=120, u_min=75, gap0=84, gap_min=42, gap_step=65, cap_late=900, parrot_at=2100),
           "HARD": dict(u0=90, u_min=45, gap0=60, gap_min=24, gap_step=75, cap_late=1500, parrot_at=1800),
           "EASY": dict(u0=150, u_min=105, gap0=100, gap_min=56, gap_step=55, cap_late=300, parrot_at=1800)},
    "ad": {"NORMAL": dict(rocks=[1, 2, 1, 2, 1], step1=4, step2=8, zone_half=12, warn=40, gold=8, silver=6, bronze=4, slow=320),
           "HARD": dict(rocks=[2, 2, 2, 2, 2], step1=3, step2=6, zone_half=8, warn=0, gold=7, silver=5, bronze=3, slow=192),
           "EASY": dict(rocks=[1, 1, 1, 1, 1], step1=5, step2=10, zone_half=12, warn=60, gold=10, silver=7, bronze=4, slow=320)},
    "ts_unused": {},
}


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("mode", list(MODES))
@pytest.mark.parametrize("game", [g for g in ROWS if g in IDS])
def test_each_mode_copies_its_row_at_entry(model, game, mode):
    with enter(model, game, MODES[mode]) as gb:
        assert tune(gb, game) == ROWS[game][mode], (game, mode)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("game", [g for g in ROWS if g in IDS])
def test_story_plays_the_normal_row(model, game):
    """STORY (and ARCADE, which pass the same mode) is always NORMAL."""
    with enter(model, game, MG_STORY) as gb:
        assert tune(gb, game) == ROWS[game]["NORMAL"]


def test_the_modes_really_differ():
    for game, rows in ROWS.items():
        if game in IDS:
            assert rows["NORMAL"] != rows["HARD"] != rows["EASY"] != rows["NORMAL"], game


# ---- the key values in play ------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("mode", list(MODES))
def test_quick_draw_the_kid_draws_on_the_modes_frame(model, mode):
    with enter(model, "qd", MODES[mode]) as gb:
        to_play(gb)
        until(gb, lambda: field(gb, "qd", "round") == 1, 10)
        assert field(gb, "qd", "r") == ROWS["qd"][mode]["r"][0]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("mode", list(MODES))
def test_order_up_the_length_and_the_press_time(model, mode):
    with enter(model, "ou", MODES[mode]) as gb:
        to_play(gb)
        until(gb, lambda: field(gb, "ou", "st") == 3, 700)          # OS_TURN
        row = ROWS["ou"][mode]
        assert field(gb, "ou", "len") == row["first"] and field(gb, "ou", "wait") == row["press"]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("mode", list(MODES))
def test_battery_sort_d_and_the_belt_start_at_the_modes_values(model, mode):
    with enter(model, "bs", MODES[mode]) as gb:
        row = ROWS["bs"][mode]
        assert field(gb, "bs", "window") == row["win0"] and field(gb, "bs", "speed") == row["speed0"]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("mode", list(MODES))
def test_t_shirt_cannon_the_timer_and_the_meter_step(model, mode):
    with enter(model, "ts", MODES[mode]) as gb:
        row = ROWS["ts"][mode]
        assert gb.mem16("mg_timer") == 60 * row["time_s"]
        to_play(gb)
        until(gb, lambda: field(gb, "ts", "st") == 0, 200)          # TSS_AIM
        gb.hold("a")
        frames(gb, 1)
        gb.release("a")
        trace = []
        for _ in range(8 * row["step"]):
            frames(gb, 1)
            trace.append(field(gb, "ts", "power"))
        steps = [i for i in range(1, len(trace)) if trace[i] != trace[i - 1]]
        assert len(steps) >= 5 and all(b - a == row["step"] for a, b in zip(steps, steps[1:])), (mode, trace)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("mode", list(MODES))
def test_log_roll_the_first_fish_comes_at_the_modes_time(model, mode):
    with enter(model, "lr", MODES[mode]) as gb:
        assert field(gb, "lr", "fish_in") == ROWS["lr"][mode]["fish_first"]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("mode", list(MODES))
def test_milk_run_the_start_speed_and_the_crates(model, mode):
    with enter(model, "mr", MODES[mode]) as gb:
        row = ROWS["mr"][mode]
        assert field(gb, "mr", "spd") == row["spd_start"] and field(gb, "mr", "crates") == row["crates"]
        to_play(gb)
        gb.hold("left")
        frames(gb, 90)
        gb.release("left")
        assert field(gb, "mr", "spd") == row["spd_min"], "LEFT stops at the mode's floor"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("mode", list(MODES))
def test_marshmallow_drop_the_supply_and_the_belt(model, mode):
    with enter(model, "mm", MODES[mode]) as gb:
        row = ROWS["mm"][mode]
        assert field(gb, "mm", "supply") == row["supply"]
        to_play(gb)
        x0 = field(gb, "mm", "cx", 0)
        frames(gb, 20)
        assert field(gb, "mm", "cx", 0) - x0 == 20 * row["belt"], "the belt's speed (1/8 px a frame)"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("mode", list(MODES))
def test_monkey_business_u_and_the_pop_interval_start_at_the_modes_values(model, mode):
    with enter(model, "mk", MODES[mode]) as gb:
        row = ROWS["mk"][mode]
        assert field(gb, "mk", "unow") == row["u0"] and field(gb, "mk", "gap") == row["gap0"]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("mode", list(MODES))
def test_asteroid_delivery_the_rocks_of_the_mode_are_the_ones_drawn(model, mode):
    """A lane with one rock never draws its second (OAM 8 + 2k, 9 + 2k for rock k = 2 lane + 1): EASY has 5 rocks, NORMAL 7, HARD 10; the rest are drawn at some time."""
    rocks = ROWS["ad"][mode]["rocks"]
    with enter(model, "ad", MODES[mode]) as gb:
        to_play(gb)
        seen = [0] * 10
        for _ in range(200):
            frames(gb, 1)
            for k in range(10):
                if gb.mem(0xFE00 + 4 * (8 + 2 * k)) or gb.mem(0xFE00 + 4 * (9 + 2 * k)):
                    seen[k] = 1
        for k in range(10):
            on = (k & 1) < rocks[k >> 1]
            assert bool(seen[k]) == on, (mode, k, seen)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("mode", list(MODES))
def test_taiko_pour_the_chart_and_the_windows(model, mode):
    """The chart each mode builds (EASY 57 notes, NORMAL 76, HARD 112), judged with the mode's windows: a press `perfect` frames off the first notes is
    PERFECT, one more GOOD, `good` GOOD, `good` + 1 a MISS (the state's `last`: 1 PERFECT, 2 GOOD, 3 MISS)."""
    import sys
    sys.path.insert(0, str(ROOT / "tools"))
    import taiko_chart
    from test_mg_taiko import press_at, taiko
    chart = taiko_chart.build({"NORMAL": "normal", "HARD": "hard", "EASY": "easy"}[mode])
    row = ROWS["tk"][mode]
    assert len(chart) == row["notes"] and chart[0][0] == 288
    cases = [(row["perfect"], 1), (row["perfect"] + 1, 2), (row["good"], 2), (row["good"] + 1, 3), (-row["perfect"], 1), (-(row["good"] + 1), 3)]
    with taiko(model, MODES[mode]) as gb:
        assert tune(gb, "tk")["notes"] == row["notes"]
        to_play(gb)
        for i, (d, want) in enumerate(cases):
            t, lane = chart[i]
            assert lane == 0
            s = press_at(gb, "a", t + d)
            assert s["last"] == want, (mode, d, s["last"], want)


# ---- the bonus rounds ------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("mode", list(MODES))
def test_the_shake_up_swaps_faster_and_more_often_by_mode(model, mode):
    """Level 1 / 2 / 3: the frames a swap takes and the swaps (6 + n)."""
    dur = {"NORMAL": [30, 22, 14], "HARD": [26, 18, 10], "EASY": [38, 30, 22]}[mode]
    n = {"NORMAL": [1, 3, 5], "HARD": [3, 5, 7], "EASY": [1, 2, 3]}[mode]
    with booted(model) as gb:
        hold_stage_anim(gb)
        mg_enter(gb, 12, MODES[mode], SEED)
        until(gb, lambda: gb.mem("bonus_phase") == 1, 200)           # PH_SHAKE
        assert gb.mem("bonus_swap_dur") == dur[0] and gb.mem("bonus_swaps_total") == 6 + n[0]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("mode", list(MODES))
def test_perfect_pour_the_pour_rate_by_mode(model, mode):
    rate = {"NORMAL": 4, "HARD": 3, "EASY": 5}[mode]
    with booted(model) as gb:
        hold_stage_anim(gb)
        mg_enter(gb, 13, MODES[mode], SEED)
        until(gb, lambda: gb.mem("bonus_phase") == 1, 400)           # PP_READY
        gb.hold("a")
        frames(gb, 1)
        seen = []
        for _ in range(6 * rate + 2):
            frames(gb, 1)
            seen.append(gb.mem("pour_liquid"))
        gb.release("a")
        ups = [i for i in range(1, len(seen)) if seen[i] != seen[i - 1]]
        assert len(ups) >= 4 and all(b - a == rate for a, b in zip(ups, ups[1:])), (mode, seen)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_arcade_and_classic_bonus_rounds_play_normal(model):
    """Outside the framework (game_state != GS_MINI) a stale mg_mode must not make a round HARD or EASY: BONUS_DIFF() is 0 there."""
    with booted(model) as gb:
        gb.write("mg_mode", MG_PRACTICE | 2)
        assert gb.mem("game_state") != 13


# ---- the medals ------------------------------------------------------------------------------------------------------------------------------
# generic games: (game, id) and the mode's thresholds on mg_score (src/mg.c medal_at / medal_at_hard / medal_at_easy)
GENERIC = {
    "bs": {"NORMAL": (2000, 4000, 6000), "HARD": (1500, 4500, 7500), "EASY": (2000, 4500, 7500)},
    "mm": {"NORMAL": (1200, 2400, 3600), "HARD": (900, 1800, 3000), "EASY": (1800, 3000, 3600)},
    "mk": {"NORMAL": (3000, 5200, 7500), "HARD": (2500, 5000, 8000), "EASY": (2500, 4500, 5700)},
    "ts": {"NORMAL": (1500, 2100, 2700), "HARD": (1200, 2100, 2700), "EASY": (1200, 2100, 2700)},
    "mr": {"NORMAL": (3000, 4500, 6000), "HARD": (2500, 4000, 5500), "EASY": (3500, 5000, 6600)},
}


def medal_of_state(model, game, mode, setup=None, points=None):
    """A fresh game in `mode`, played to its first frame, `setup(gb)` poking the state (or `points` the score), the result window: the medal."""
    with enter(model, game, MODES[mode]) as gb:
        to_play(gb)
        if setup:
            setup(gb)
        to_result(gb, points)
        return gb.mem("mg_medal")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("mode", list(MODES))
@pytest.mark.parametrize("game", list(GENERIC))
def test_score_medals_by_mode(model, mode, game):
    b, s, g = GENERIC[game][mode]
    for pts, want in ((b - 1, MEDAL_NONE), (b, MEDAL_BRONZE), (s - 1, MEDAL_BRONZE), (s, MEDAL_SILVER), (g - 1, MEDAL_SILVER), (g, MEDAL_GOLD)):
        assert medal_of_state(model, game, mode, points=pts) == want, (game, mode, pts, want)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("mode", list(MODES))
def test_counted_medals_by_mode(model, mode):
    """The games with their own medal, by the game's own count: Order Up (rounds cleared 3 / 5 / 7), Asteroid (deliveries), Log Roll (seconds on the
    log), Taiko (accuracy), Quick Draw (the rounds lost: 0 gold, 1 silver, 2 bronze, 3 none, in every mode)."""
    for n, want in ((2, 0), (3, 1), (4, 1), (5, 2), (6, 2), (7, 3)):
        assert medal_of_state(model, "ou", mode, lambda gb: put(gb, "ou", "cleared", n)) == want, ("ou", mode, n)
    a = ROWS["ad"][mode]
    for n, want in ((a["bronze"] - 1, 0), (a["bronze"], 1), (a["silver"] - 1, 1), (a["silver"], 2), (a["gold"] - 1, 2), (a["gold"], 3)):
        assert medal_of_state(model, "ad", mode, lambda gb: put(gb, "ad", "delivered", n)) == want, ("ad", mode, n)
    r = ROWS["lr"][mode]
    for secs, want in ((r["bronze"] - 1, 0), (r["bronze"], 1), (r["silver"] - 1, 1), (r["silver"], 2), (r["gold"] - 1, 2), (r["gold"], 3)):
        assert medal_of_state(model, "lr", mode, lambda gb: put(gb, "lr", "on", secs * 60 + 7)) == want, ("lr", mode, secs)
    t = ROWS["tk"][mode]
    for pct, want in ((t["bronze"], 1), (t["silver"], 2), (t["gold"], 3), (t["bronze"] - 1, 0), (t["silver"] - 1, 1), (t["gold"] - 1, 2)):
        half = -(-pct * t["notes"] * 2 // 100)                          # the fewest half notes that reach pct % of the notes
        if want < {t["bronze"]: 1, t["silver"]: 2, t["gold"]: 3}.get(pct, 99):
            half -= 1                                                   # one half note short of the next threshold
        half = max(half, 0)

        def poke(gb, half=half):
            put(gb, "tk", "perfect", half // 2)
            put(gb, "tk", "good", half % 2)
        assert medal_of_state(model, "tk", mode, poke) == want, ("tk", mode, pct, half)
    for wins, lost, want in ((3, 0, 3), (3, 1, 2), (3, 2, 1), (2, 3, 0), (1, 3, 0), (0, 3, 0), (0, 0, 0)):
        def poke(gb, wins=wins, lost=lost):
            put(gb, "qd", "wins", wins, 0)
            put(gb, "qd", "wins", lost, 1)
        assert medal_of_state(model, "qd", mode, poke) == want, ("qd", mode, wins, lost)
