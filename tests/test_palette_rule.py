# The Color palette rule (owner 2026-11-13: "the same palette seems to repeat between appearances of that character"; "the first appearance of a patron is its default look";
# "make sure that we don't run into unintended consequences where certain palettes never end up showing up").
# src/mirror.c pick_pal: a look's first appearance in a level wears its default palette; later ones never the palette it wore last, nor (when another is allowed) one of the last two that spawned.
# Played as shipped: the ROM as built (ROM byte 0x3FFD = 0xFF, the DIV counter mixed into every pick: conftest.seeding()), Color at double speed, the LEVEL harness, every venue, many short levels.
# Before this rule the next appearance of a look had its previous palette 16-23 % of the time (1 / the look's palettes), and nothing measured a palette at all.
# PALRULE_ROM=<path> plays another ROM (the proof that these tests fail on the build before the rule).
import collections
import multiprocessing
import os
import random
import re

import pytest
from conftest import ROM, ROOT, double_speed, seeding, title_level
from gbtools import Rom

pytestmark = pytest.mark.parametrize("model", ["cgb"])
PLAY_ROM = os.environ.get("PALRULE_ROM", str(ROM))
RUNS, FRAMES = 20, 12000          # per venue: 20 short levels of about 45 patrons each


def look(v):
    return v & 7


def pal(v):
    return ((v >> 3) ^ v) & 7


def tables():
    """(pm, df): per group the palette masks (combo, boss) per look and the default palette per look: the generated venues from build/looks_pick.h, the Saloon's from src/mirror.c."""
    pick = (ROOT / "build" / "looks_pick.h").read_text()
    src = (ROOT / "src" / "mirror.c").read_text()
    pm, df = {}, {}
    body = re.search(r"#define LOOKS_PM_X(.*?)\n\n", pick, re.S).group(1)
    for g, (a, b) in enumerate(re.findall(r"\{ \{([^}]*)\}, \{([^}]*)\} \}", body), 1):
        pm[g] = [[int(x, 16) for x in a.split(",")], [int(x, 16) for x in b.split(",")]]
    body = re.search(r"#define LOOKS_DF_X(.*?)(?:\n\n|\Z)", pick, re.S).group(1)
    for g, row in enumerate(re.findall(r"\{([^}]*)\}", body), 1):
        df[g] = [int(x) for x in row.split(",")]
    m = re.search(r"pm_a\[10\]\[2\]\[8\] = \{ \{ \{([^}]*)\}, \{([^}]*)\} \}", src)
    pm[0] = [[int(x, 16) for x in m.group(1).split(",")], [int(x, 16) for x in m.group(2).split(",")]]
    df[0] = [int(x) for x in re.search(r"df_a\[10\]\[8\] = \{ \{([^}]*)\}", src).group(1).split(",")]
    return pm, df


def plan_table(g, boss=False):
    """The 256-entry (look, palette) table the pick indexes: build/looks_pick.h (generated venues), sal_combo / sal_boss through saloon_variant's index (the Saloon)."""
    if g:
        t = [int(x, 16) for x in re.search(r"%s_%d\[256\] = \{([^}]*)\}" % ("boss" if boss else "combo", g), (ROOT / "build" / "looks_pick.h").read_text()).group(1).split(",")]
        return [(look(v), pal(v & 0x3F)) for v in t]
    src = (ROOT / "src" / "mirror.c").read_text()
    body = re.search(r"%s\[%d\] = \{(.*?)\};" % ("sal_boss" if boss else "sal_combo", 21 if boss else 36), src, re.S).group(1)
    lst = [(int(a), int(b)) for a, b in re.findall(r"V\((\d), (\d)\)", body)]
    n = len(lst)
    return [lst[r * n >> 8] for r in range(256)]


def plan_shares(g, boss=False):
    t = plan_table(g, boss)
    pairs = collections.Counter(t)
    return {k: c / 256 for k, c in pairs.items()}


def look_shares(g):
    """The looks' expected shares: the plan's, after the pick's history filter. try_spawn / pick_x draw a table entry and draw again (r + 97) while its look is one of the last 3 that spawned,
    which takes odds from the common looks and gives them to the rare ones (the venue 4 look with 19 of 256 entries really comes about 12 % of the time, not 7.4 %): the same before the palette rule
    (measured on its baseline ROM over 60 levels: 0.125 against 0.124 after). Simulated here on the real table, 100000 spawns, a fixed seed."""
    tab = [lk for lk, _ in plan_table(g)]
    rnd, h, c, n = random.Random(g), [255] * 3, collections.Counter(), 100000
    for _ in range(n):
        r = rnd.randrange(256)
        while tab[r] in h:
            r = (r + 97) & 255
        c[tab[r]] += 1
        h = [tab[r]] + h[:2]
    return {lk: v / n for lk, v in c.items()}


def problems(counts, shares, min_ratio=0.1, z=4, looks=None):
    """What is wrong with the pairs' counts against the plan's shares (empty list: fine): a pair that never came or came far under its share, a look whose share moved.
    A look's share is a binomial proportion of the n spawns, so it may sit z standard deviations (sqrt(want * (1 - want) / n)) from its expected share `looks` (the plan's when not given): 980 spawns
    allow 0.042 around 0.12, and a rarely drawn look cannot be flagged by luck; the real spread is a little under that (per level the draws are not independent, the filter spreads them)."""
    n = sum(counts.values())
    bad = []
    for (lk, p), s in sorted(shares.items()):
        c = counts.get((lk, p), 0)
        if c == 0 or c < min_ratio * s * n:
            bad.append(("pair under its share", lk, p, c, round(s * n, 1)))
    for lk in sorted({k[0] for k in shares}):
        want = looks[lk] if looks else sum(s for k, s in shares.items() if k[0] == lk)
        got = sum(c for k, c in counts.items() if k[0] == lk) / n
        if abs(got - want) > z * (want * (1 - want) / n) ** 0.5 + 0.005:
            bad.append(("look share moved", lk, round(got, 3), round(want, 3)))
    return bad


def test_the_tables_agree_with_the_pairs_the_plan_allows(model):
    pm, df = tables()
    assert sorted(pm) == list(range(10)), sorted(pm)
    for g in range(10):
        for boss in (False, True):
            allowed = collections.defaultdict(int)
            for lk, p in plan_table(g, boss):
                allowed[lk] |= 1 << p
            for lk in range(8):
                assert pm[g][boss][lk] == allowed[lk], (g, boss, lk, "the palette mask is the table's pairs")
        for lk in range(8):
            if pm[g][0][lk]:
                assert pm[g][0][lk] >> df[g][lk] & 1, (g, lk, "the default palette is one the look may wear")
            assert pm[g][1][lk] & ~pm[g][0][lk] == 0, (g, lk, "a fight's palettes are a subset")


def test_the_coverage_check_sees_a_starved_table(model):
    """The check itself: a palette that never comes, one far under its share, a look that doubles."""
    shares = {(0, 0): 0.25, (0, 1): 0.25, (1, 0): 0.25, (1, 1): 0.25}
    assert problems({(0, 0): 250, (0, 1): 250, (1, 0): 250, (1, 1): 250}, shares) == []
    assert problems({(0, 0): 400, (0, 1): 0, (1, 0): 300, (1, 1): 300}, shares)[0][:2] == ("pair under its share", 0)
    assert any(b[0] == "pair under its share" for b in problems({(0, 0): 350, (0, 1): 20, (1, 0): 330, (1, 1): 300}, shares))
    assert any(b[0] == "look share moved" for b in problems({(0, 0): 400, (0, 1): 400, (1, 0): 100, (1, 1): 100}, shares))


def one_level(a):
    lv, wait = a
    seen = []
    with double_speed(), seeding(), Rom(PLAY_ROM, "cgb") as gb:
        gb.run(120 + wait)
        title_level(gb, lv)
        for _ in range(60):
            if gb.mem("game_state") == 1:
                break
            gb.run(1)
        gb.write("tip_chance", 0)
        prev = [0] * 16
        lastsp = 0
        newp = []
        for fr in range(FRAMES):
            if fr % 30 == 0:
                gb.write("lives", 9)
                gb.write("served", 0)
                gb.write("quota", 255)
            if fr % 4 == 0:                                   # (nobody drinks: whoever nears the tap is taken off, or the level would restart)
                st, px = gb.read("patron_state", 16), gb.read("patron_x", 16)
                gone = [i for i in range(16) if st[i] and px[i] >= 64]
                for i in gone:
                    gb.write(gb.addr("patron_state") + i, 0)
                    gb.write(gb.addr("patron_lift") + i, 0)
                    gb.write(gb.addr("patron_draw") + i, 255)
                if gone:
                    gb.write("patrons_live", sum(1 for i in range(16) if st[i] and i not in gone))
                    gb.write("lists_dirty", 1)
                    gb.write("lists_ok", 0)
            gb.run(1)
            sp = gb.mem("spawned")
            if sp < lastsp or gb.mem("lives") < 9:                                   # (a new level: a patron got to the tap, or the level was cleared: the rule starts again)
                seen.append(-1)
                prev = [0] * 16
                gb.write("lives", 9)
            lastsp = sp
            st, v = gb.read("patron_state", 16), gb.read("patron_variant", 16)
            for i in newp:                                       # (the variant byte is written a little after the slot's state, which a frame can end between: read it a frame later;
                if st[i]:                                        # and a patron the add took back at once (lift_spawn failed: "the add can still fail") is not one who came)
                    seen.append(v[i] & 0x7F)
            newp = []
            for i in range(16):
                if st[i] and not prev[i]:
                    newp.append(i)
                prev[i] = st[i]
        return seen, gb.mem("spawned"), gb.mem("cur_group")


def one_level_safe(a):
    try:
        return one_level(a)
    except AssertionError:                                    # (a title press that landed in the title's own animation: that run is lost, the others count)
        return None


def play_venue(g):
    jobs = [(g + 1, 7 * i + 3 * g) for i in range(RUNS)]
    with multiprocessing.get_context("fork").Pool(3) as pool:
        return [r for r in pool.map(one_level_safe, jobs) if r]


@pytest.mark.timeout(900)
@pytest.mark.parametrize("group", range(10))
def test_every_allowed_pair_comes_up_the_first_is_default_and_no_look_repeats_its_palette(model, group):
    pm, df = tables()
    levels = play_venue(group)
    assert len(levels) >= RUNS // 2, len(levels)
    counts = collections.Counter()
    firsts = 0
    nlev = 0
    for seen, spawned, grp in levels:
        assert grp == group
        parts = [[]]
        for v in seen:
            if v == -1:
                parts.append([])
            else:
                parts[-1].append(v)
        assert abs(spawned - len(parts[-1])) <= 2, ("`spawned` counts the patrons that came", spawned, len(parts[-1]))
        for part in parts:
            if not part:
                continue
            last = {}
            nlev += 1
            for v in part:
                lk, p = look(v), pal(v & 0x3F)
                counts[(lk, p)] += 1
                assert pm[group][0][lk] >> p & 1, (lk, p, "an allowed pair")
                if lk not in last:
                    assert p == df[group][lk], (lk, p, "the first appearance of look %d in a level wears its default palette %d" % (lk, df[group][lk]))
                    firsts += 1
                elif bin(pm[group][0][lk]).count("1") > 1:
                    assert p != last[lk], (lk, p, "the same palette as this look's last appearance")
                last[lk] = p
    assert firsts >= 5 * nlev // 2, (firsts, nlev)
    assert problems(counts, plan_shares(group), looks=look_shares(group)) == []
