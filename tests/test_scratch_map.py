# The story_scratch map (src/scratch.h; the table of users is USERS below). WRAM is full, so screens lay their buffers over story_scratch
# (520 bytes, story.c) and a few other shared places. That is safe while two users that are ALIVE AT THE SAME TIME never share a byte;
# 4279ba3 was the bug (the Mothership's lights over the Boss Rush list's struct). Three kinds of test:
#   - the static map: every group of users that live together has disjoint ranges, and the table matches the sources (a number moved in
#     a .c file, or a new use of story_scratch nobody registered, fails here and says what to update);
#   - the dynamic one: a Boss Rush fight leaves the list's state alone (every built boss, DMG and CGB);
#   - a game over inside a boss fight (ARCADE) leaves no boss "on" for the screens that reuse his bytes.
import glob
import re
from pathlib import Path

import pytest
from conftest import ROOT, clear_regulars
from test_flow import GAME_OVER, TITLE, PLAYING, lose_a_life, run_until, state

SRC = ROOT / "src"


def scratch_h():
    """The numbers of src/scratch.h: {SCR_*: int}."""
    text = (SRC / "scratch.h").read_text()
    env = {"STORY_SCRATCH": int(re.search(r"#define STORY_SCRATCH\s+(\d+)", (SRC / "game.h").read_text()).group(1))}
    for m in re.finditer(r"^#define (SCR_\w+)\s+\(?([^/\n]*?)\)?\s*(?://.*)?$", text, re.M):
        env[m.group(1)] = eval(m.group(2), {}, dict(env))
    return env


H = scratch_h()
N = H["STORY_SCRATCH"]
BOSS_OWN_N = H["SCR_BOSS_N"] - (8 + 1) * 5 - 4 - 4          # boss.h: BOSS_SCRATCH_N - (BOSS_POSES_MAX + 1) * BOSS_W_MAX - 4 - BOSS_FX_N
POSES_MAX = int(re.search(r"#define BOSS_POSES_MAX\s+(\d+)", (ROOT / "build" / "boss_art.h").read_text()).group(1))
assert POSES_MAX == 8, "BOSS_OWN_N below is computed for 8 poses: update this table"
B0 = H["SCR_BOSS_AT"]

# name: (first byte, one past the last, what it is). Ranges are from the code (each is checked against its source below), not the comments.
USERS = {
    # a boss fight (BOSS RUSH included): src/scratch.h
    "fight.LD": (H["SCR_LD_AT"], H["SCR_LD_END"], "boss.c: the in-place tile / palette jobs"),
    "fight.HB": (H["SCR_HB_AT"], H["SCR_HB_AT"] + H["SCR_HB_N"], "story.c boss_in_place: the HUD's goal columns"),
    "fight.BELT": (H["SCR_BELT_AT"], H["SCR_BELT_AT"] + H["SCR_BELT_N"], "boss_prototype.c: the belt's attributes"),
    "fight.CAP": (H["SCR_CAP_AT"], H["SCR_CAP_AT"] + H["SCR_CAP_N"], "boss.h BOSS_CAPBUF / Duke's ENT_BUF / the Sumo's HUD row"),
    "rush.STRUCT": (H["SCR_RUSH_AT"], H["SCR_RUSH_AT"] + H["SCR_RUSH_N"], "rush.h: the run's state, across fights"),
    "fight.LIGHTS": (H["SCR_LIGHTS_AT"], H["SCR_LIGHTS_AT"] + H["SCR_LIGHTS_N"], "boss.h LIGHTS_BUF (the Mothership)"),
    "fight.MAP": (B0, B0 + (POSES_MAX + 1) * 5, "boss.h boss_map: his pose table"),
    "fight.HAND": (B0 + (POSES_MAX + 1) * 5, B0 + (POSES_MAX + 1) * 5 + 4, "boss.h boss_hand (unused)"),
    "fight.OWN": (B0 + (POSES_MAX + 1) * 5 + 4, B0 + (POSES_MAX + 1) * 5 + 4 + BOSS_OWN_N, "boss.h BOSS_OWN: a boss file's state"),
    "fight.FX": (N - 4, N, "game.h BOSS_FX: the landing marker, the topper's look"),
    "tip2.COIN": (H["SCR_TIP2_AT"], H["SCR_TIP2_AT"] + H["SCR_TIP2_N"], "tip2.h struct tip2: the second tip coin (a level, a fight's level included)"),
    "split.PAL": (H["SCR_SPLIT_AT"], H["SCR_SPLIT_AT"] + H["SCR_SPLIT_N"], "game.h SPLIT_E_*: the mid-frame palette split's early reload (a Color level, a fight's level included)"),
    "inst.TAB": (H["SCR_INST_AT"], H["SCR_INST_AT"] + H["SCR_INST_N"], "game.h INST_OBJ / INST_BG: the patron palette instances' OBJ and BG slots (a level, a fight's level included)"),
    "keg.TAB": (H["SCR_KEG_AT"], H["SCR_KEG_AT"] + H["SCR_KEG_N"], "game.h KEG_PAL / KEG_STG / EV_*: the keg's colours, the HUD's own, the frame's event list (a Color level, a fight's level included)"),
    "evt.TAB": (H["SCR_EVT_AT"], H["SCR_EVT_AT"] + H["SCR_EVT_N"], "game.h EV_LINE / EV_KIND: the frame's events (line, kind) and the sentinel (a Color level, a fight's level included)"),
    "keg2.TAB": (H["SCR_KEG2_AT"], H["SCR_KEG2_AT"] + H["SCR_KEG2_N"], "game.h KEG_BCPS (SHOW_PAL, unused: OBJ_PAT / OBJ_SHOW took its job): whether BG 1 is the keg's (a Color level, a fight's level included)"),
    "obj.PAT": (H["SCR_OBJ_AT"], H["SCR_OBJ_AT"] + H["SCR_OBJ_N"], "game.h OBJ_PAT: OBJ 5's patron colours, written in HBlank below the dancers (a Color level, a fight's level included)"),
    "obj.PATX": (H["SCR_OBJX_AT"], H["SCR_OBJX_AT"] + H["SCR_OBJX_N"], "game.h OBJX_*: the three show palettes' buffers (OBJ 4 and OBJ 3's patron and show colours; a Color level's show)"),
    "obj.CO": (H["SCR_OBJXC_AT"], H["SCR_OBJXC_AT"] + H["SCR_OBJXC_N"], "game.h OBJX_CO: the same, a screen fade's destination colours (a show's stage wash, showlights.h, keeps its 16 bytes on the first half while a show plays: level.c obj_cols clears the stamp when a fade overwrites them)"),
    "ltst.STAMP": (H["SCR_LTST_AT"], H["SCR_LTST_AT"] + H["SCR_LTST_N"], "showlights.h SHOWLT_STAMP: which tint the show's wash buffer holds (a Color level's show, a fight's level included)"),
    "looks.HIST": (H["SCR_LOOKH_AT"], H["SCR_LOOKH_AT"] + H["SCR_LOOKH_N"], "scratch.h LOOK_HIST: the Color spawn rule's last 3 looks, the pending pick and its spawned count (a Color level, a fight's level included)"),
    "obj.F": (H["SCR_OBJF_AT"], H["SCR_OBJF_AT"] + H["SCR_OBJF_N"], "game.h OBJX_F / DANCE_STEP: the three palettes' flags, the dance's step"),
    "obj.SHOW": (H["SCR_OBJ2_AT"], H["SCR_OBJ2_AT"] + H["SCR_OBJ2_N"], "game.h OBJ_SHOW: OBJ 5's show colours, written in every VBlank of a show (a Color level, a fight's level included)"),
    # the Boss Rush screens (menu, list, NEXT, RESULT): the struct above and the row buffers
    "rush.ROWS": (0, 14 * 20, "rush.c ROW(k): the menu's and the list's row buffers"),
    "ol.STATE": (H["SCR_OL_AT"], H["SCR_OL_AT"] + H["SCR_OL_N"], "oneline.h struct ol_state: the arrows' bob and the key repeat (SOUNDTRACK, MINI GAMES, the Boss Rush list)"),
    # the story map
    "smap.ROWS": (0, 140, "smap.c ROWBUF"), "smap.ATTR_PANEL": (140, 160, "smap.c"), "smap.ATTR_TAG": (160, 180, "smap.c"),
    "smap.TAGROW": (180, 200, "smap.c"), "smap.V": (400, 412, "smap.c V(n)"),
    # the Practice list
    "mglist.ROWS": (0, 220, "mg_list.c ML_ROW(k) (11 rows)"), "mglist.STATE": (220, 222, "ml_d: the rows to redraw"),
    "mglist.ART": (222, 244, "mg_list.c struct pa: the illustration loader's state (222 + 22: ML_PA_AT, ML_STAGE_AT)"),
    "mglist.STAGE": (244, 244 + 80, "mg_list.c PA_STAGE: a stream chunk (5 tiles) / the map rows on their way through the copy queue"),
    # the soundtrack
    "jukebox.ROWS": (0, 9 * 20, "jukebox.c JB_ROW(k)"), "jukebox.METER": (180, 190, "jukebox.c struct jb_meter: the bars' levels and the DMG note-start state"),
    # the credits: CR (struct cr_state), the DMG header's two BGPs (main.c cast_isr), the card's colours, the owner's portrait, a staging buffer
    "credits.CR": (0, 68, "credits.c struct cr_state"), "credits.BGP": (68, 70, "cast_isr: header BGP, card BGP"),
    "credits.PAL": (72, 200, "CR_PAL: 128 bytes"), "credits.PT": (200, 427, "CR_PT: portrait_t (227 bytes, credits.c cr_fits)"),
    "credits.BUF": (427, 491, "CR_BUF: 64 bytes after the portrait"),
    # a picture scene (the INTRO, the finale's pictures): story.c PS_* and the generated burst (gen_story.py)
    "pic.FX_W": (0, 2, "PS_FX, PS_W"), "pic.ROWS": (2, 38, "PS_ROWS"), "pic.TILES": (40, 88, "PS_TILES"), "pic.PALS": (88, 128, "PS_PALS"),
    "pic.OUT": (128, 168, "PS_OUT"), "pic.PB_T": (168, 169, "PB_T"), "pic.CURSOR": (170, 172, "STB_CURSOR"), "pic.STAGE": (172, 180, "STB_STAGE"),
    "pic.RCUR": (180, 181, "STB_RCUR"), "pic.RSTAGE": (181, 185, "STB_RSTAGE"), "pic.SPARKS": (192, 237, "STB_SPK, RNG, TM, LEFT"),
    # a venue scene: the backdrop under the portrait slot (13 rows of map, then attributes)
    "scene.BD_MAP": (0, 260, "story.c bd_map"), "scene.BD_ATTR": (260, 520, "story.c bd_attr"),
    # the mini-games: one union (mg.h), the largest member is the Pour-Off (po_state)
    "mg.UNION": (0, 514, "mg.h union mg_ram: sizeof 514 (struct po_state), asserted <= STORY_SCRATCH"),
}

# Users alive at the same time: within a group no two ranges may share a byte. (A screen never lives with another screen's group: each
# one is entered with the LCD off and rebuilds what it reads. A group says what a single screen or mode holds together.)
GROUPS = {
    "a boss fight, in a BOSS RUSH run (the struct is alive through every fight)":
        ["fight.LD", "fight.HB", "fight.BELT", "fight.CAP", "rush.STRUCT", "fight.LIGHTS", "fight.MAP", "fight.HAND", "fight.OWN", "fight.FX", "tip2.COIN", "split.PAL", "inst.TAB", "keg.TAB", "keg2.TAB", "evt.TAB", "ltst.STAMP", "looks.HIST", "obj.PAT", "obj.SHOW", "obj.PATX", "obj.CO", "obj.F"],
    "a Boss Rush screen": ["rush.ROWS", "rush.STRUCT", "ol.STATE"],
    "the story map": ["smap.ROWS", "smap.ATTR_PANEL", "smap.ATTR_TAG", "smap.TAGROW", "smap.V"],
    "the Practice list": ["mglist.ROWS", "mglist.STATE", "mglist.ART", "mglist.STAGE", "ol.STATE"],
    "the soundtrack": ["jukebox.ROWS", "jukebox.METER", "ol.STATE"],
    "the credits": ["credits.CR", "credits.BGP", "credits.PAL", "credits.PT", "credits.BUF"],
    "a picture scene": ["pic.FX_W", "pic.ROWS", "pic.TILES", "pic.PALS", "pic.OUT", "pic.PB_T", "pic.CURSOR", "pic.STAGE", "pic.RCUR", "pic.RSTAGE", "pic.SPARKS"],
    "a venue scene": ["scene.BD_MAP", "scene.BD_ATTR"],
}

# Every use of the name in code (comments stripped), per file: a new one (or a removed one) fails until the map above is looked at.
USES = {"build/story_pictures.c": 9, "src/ad.c": 1, "src/boss.c": 1, "src/boss.h": 2, "src/boss_duke.c": 1, "src/boss_prototype.c": 1,
        "src/boss_sumo.c": 1, "src/credits.c": 7, "src/game.h": 27, "src/lift.c": 2,"src/jukebox.c": 3, "src/main.c": 61, "src/mg.h": 3, "src/mg_list.c": 5,
        "src/mk.c": 1, "src/oneline.h": 1, "src/mm.c": 1, "src/ou.c": 1, "src/po.c": 1, "src/rush.c": 2, "src/rush.h": 2, "src/scratch.h": 3, "src/showlights.h": 1, "src/smap.c": 6,
        "src/story.c": 16, "src/tip2.h": 1, "src/tk.c": 1, "src/trans.c": 5, "src/ts.c": 1}

# the numbers each source must still contain (a literal moved there without the table moving fails here)
SOURCE_HAS = {
    "src/story.c": [r"story_scratch\[0\]", r"story_scratch\[1\]", r"story_scratch \+ 2\)", r"story_scratch \+ 40\)", r"story_scratch\[168\]",
                    r"story_scratch \+ STORY_PIC_ROWS \* 20", r"#define PS_BURST 3", r"story_scratch \+ 40 \+ PS_BURST \* 16\)\)",
                    r"story_scratch \+ 40 \+ PS_BURST \* 16 \+ 40\)\)", r"story_scratch \+ SCR_HB_AT"],
    "src/smap.c": [r"story_scratch \+ 140\)", r"story_scratch \+ 160\)", r"story_scratch \+ 180\)", r"story_scratch\[400 \+ \(n\)\]", r"#define ROWS_MAX\s+7"],
    "src/mg_list.c": [r"story_scratch \+ \(uint8_t\)\(k\) \* 20", r"story_scratch \+ ML_ROWS \* 20\)\)", r"#define ML_ROWS\s+11\b", r"#define ML_PA_AT\s+\(ML_ROWS \* 20 \+ 2\)", r"#define ML_STAGE_AT\s+\(ML_PA_AT \+ 22\)"],
    "src/jukebox.c": [r"story_scratch \+ \(uint8_t\)\(k\) \* 20", r"story_scratch \+ JB_ROWS \* 20\)\)", r"#define JB_ROWS\s+9\b"],
    "src/oneline.h": [r"story_scratch \+ SCR_OL_AT\)\)"],
    "src/credits.c": [r"story_scratch \+ 72\)", r"story_scratch \+ 200\)\)", r"story_scratch \+ 200 \+ sizeof\(portrait_t\)", r"sizeof\(struct cr_state\) <= 68"],
    "src/main.c": [r"story_scratch\[69\]", r"story_scratch\[68\]"],
    "src/rush.c": [r"story_scratch \+ \(uint8_t\)\(k\) \* 20"],
    "src/boss.c": [r"story_scratch \+ SCR_LD_AT"], "src/boss_prototype.c": [r"story_scratch \+ SCR_BELT_AT"],
    "src/boss_duke.c": [r"story_scratch \+ SCR_CAP_AT"], "src/boss_sumo.c": [r"story_scratch \+ SCR_CAP_AT"],
    "src/boss.h": [r"story_scratch \+ SCR_CAP_AT", r"story_scratch \+ SCR_BOSS_AT", r"#define BOSS_SCRATCH_N\s+73\b"],
    "src/rush.h": [r"#define RUSH_AT\s+SCR_RUSH_AT"],
}


def code(path):
    return re.sub(r"//[^\n]*", "", (ROOT / path).read_text())


def test_every_group_of_users_alive_together_is_disjoint():
    for group, names in GROUPS.items():
        for i, a in enumerate(names):
            lo, hi, _ = USERS[a]
            assert 0 <= lo < hi <= N, (a, lo, hi)
            for b in names[i + 1:]:
                lo2, hi2, _ = USERS[b]
                assert hi <= lo2 or hi2 <= lo, f"{a} [{lo},{hi}) and {b} [{lo2},{hi2}) share bytes, and both live in {group}"
    for name, (lo, hi, what) in USERS.items():
        assert 0 <= lo < hi <= N, (name, lo, hi)


def test_a_scratch_user_not_in_a_group_is_a_decision():
    """Every USERS entry is in a group (a lone entry means nobody said what it lives with)."""
    grouped = {n for names in GROUPS.values() for n in names} | {"mg.UNION"}
    assert set(USERS) == grouped, sorted(set(USERS) ^ grouped)


def test_no_unregistered_use_of_story_scratch():
    seen = {}
    for f in glob.glob(str(ROOT / "src" / "*.[ch]")) + [str(ROOT / "build" / "story_pictures.c")]:
        rel = str(Path(f).relative_to(ROOT))
        n = len(re.findall(r"story_scratch|STORY_SCRATCH", code(rel)))
        if n:
            seen[rel] = n
    assert seen == USES, (
        "a use of story_scratch / STORY_SCRATCH was added or removed: say in src/scratch.h or USERS/GROUPS in tests/test_scratch_map.py which bytes "
        "it takes and what is alive with it, then update USES. Differences: "
        + str({k: (seen.get(k), USES.get(k)) for k in set(seen) | set(USES) if seen.get(k) != USES.get(k)}))


@pytest.mark.parametrize("path", sorted(SOURCE_HAS))
def test_the_table_still_matches_the_source(path):
    text = code(path)
    for pat in SOURCE_HAS[path]:
        assert re.search(pat, text), f"{path}: {pat!r} is gone: a share of story_scratch moved, update USERS in tests/test_scratch_map.py"


def test_the_fight_chain_is_the_rush_structs_neighbours():
    """The Boss Rush struct fits between the fight's staging and its lights, with every byte of the lights' own (4279ba3: 395 -> 387)."""
    assert H["SCR_CAP_AT"] + H["SCR_CAP_N"] <= H["SCR_RUSH_AT"]
    assert H["SCR_RUSH_AT"] + H["SCR_RUSH_N"] <= H["SCR_LIGHTS_AT"]
    assert not 395 + H["SCR_RUSH_N"] <= H["SCR_LIGHTS_AT"], "the layout of 0a9027a (RUSH_AT 395) would not pass: the check can see the old bug"


# ---- the dynamic ones -------------------------------------------------------------------------------------------------------------------
from test_rush import BUILT, RS_LIST, RUSH_AT, beat, booted, into_fight, on_rush, tap, to_list  # noqa: E402

# struct rush_state (src/rush.h) bytes a fight must not change: the menu line, the list line, built (2), nlines (mode and n are the
# run's own: CHOOSE sets them)
KEPT = {"sel": 2, "list_sel": 3, "built": 44, "built_hi": 45, "nlines": 47}


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("boss", BUILT)
def test_a_boss_rush_fight_keeps_the_lists_state(model, boss):
    """Every boss, played through his entrance to BOSS BEATEN: the struct's menu / list / built / nlines bytes are as they were
    (his bytes, the staging and the Mothership's lights are all over this buffer: a share between them shows up here)."""
    with booted(model) as gb:
        to_list(gb)
        for _ in range(BUILT.index(boss)):
            tap(gb, "right")
        base = gb.addr("story_scratch") + RUSH_AT
        before = bytes(gb.read(base, H["SCR_RUSH_N"]))
        tap(gb, "a")
        into_fight(gb, entered=False)
        gb.run(900)                                       # (the entrance, the first of the fight: every special at least begins)
        gb.write("boss_hook", 3)
        clear_regulars(gb)
        run_until(gb, lambda: state(gb) != PLAYING, 400)
        run_until(gb, lambda: on_rush(gb), 600)
        gb.run(10)
        after = bytes(gb.read(base, H["SCR_RUSH_N"]))
        for k, off in KEPT.items():
            assert after[off] == before[off], (k, before.hex(), after.hex())


# ---- a game over inside a boss fight ----------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("c", [0, 7])
def test_an_arcade_game_over_in_a_boss_fight_leaves_no_boss_on(model, c):
    """ARCADE out of lives inside a boss fight ends in the title with boss_on still 1: the Practice list's mini-games (the Pour-Off and
    the others lay their state over BOSS_OWN / BOSS_FX) and their pause menu (NR51 for the Sumo) then run with a boss 'on'."""
    from test_arcade import start_arcade
    from test_story import boss_from_opening, to_goal
    from boss_common import frames
    with start_arcade(model) as gb:
        to_goal(gb)
        boss_from_opening(gb, c)
        to_goal(gb, boss_start=False)
        frames(gb, 5)
        assert gb.mem("boss_on") == 1 and gb.mem("boss_id") == c
        gb.write("lives", 1)
        lose_a_life(gb)
        run_until(gb, lambda: state(gb) == GAME_OVER, 400)
        for _ in range(900):
            if state(gb) == TITLE:
                break
            gb.press("a", 2)
            gb.run(10)
        assert state(gb) == TITLE
        gb.run(60)
        assert gb.mem("boss_on") == 0, "the title is up and the last fight's boss is still on"
