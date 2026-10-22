# Cartridge RAM images for the save tests (tests/test_erase.py, tests/test_save_upgrade.py): every block src/save.c knows, built the way the
# game writes it, and the observations that say how a boot read them. The SRAM map (save.c):
#   0x00 main "TPR7" (progress, step, tunes)   0x0A "SV" venue-start score   0x12 "BC" bar change   0x18 "DU" debug unlock
#   0x40 "MGP2" practice + boss rush           0x70 "MGB1" bonus rounds       0x7A "MD" EASY / HARD medals
#   0x80 "HSA1" ARCADE, 0xC0 "HSS1" STORY, 0x100 "HSC2" CLASSIC top 5s
from conftest import BX_AT, DU_AT, bx_block, du_block, menu_items, title_pick, K_SETTINGS, MENU_SETTLE

SV_AT, BC_AT, PR_AT, DX_AT, TBL_AT = 0x0A, 0x12, 0x40, BX_AT + 10, (0x80, 0xC0, 0x100)
BLOCKS = {"main": (0x00, 10), "SV": (SV_AT, 8), "BC": (BC_AT, 5), "DU": (DU_AT, 5), "MGP2": (PR_AT, 46), "MGB1": (BX_AT, 10), "MD": (DX_AT, 6),
          "HSA1": (TBL_AT[0], 36), "HSS1": (TBL_AT[1], 36), "HSC2": (TBL_AT[2], 36)}
SIZE = 0x2000


def sv_block(chapter, score, bad=False):
    b = bytes([ord("S"), ord("V"), chapter]) + score.to_bytes(3, "little")
    c = (0x5A + sum(b)) & 255
    return b + bytes([c ^ 1 if bad else c, c ^ 0xFF])


def bc_block(mode):
    b = bytearray(b"BC" + bytes([mode]))
    c = (0x5A + sum(b)) & 255
    return bytes(b + bytes([c, c ^ 255]))


def md_block(easy, hard):
    b = bytearray(b"MD" + bytes([easy, hard]))
    c = (0x5A + sum(b)) & 255
    return bytes(b + bytes([c, c ^ 255]))


def put(img, at, block):
    r = bytearray(img)
    r[at:at + len(block)] = block
    return bytes(r)


def full_image(story=2, step=0, tunes=0x2345 | 1):
    """Every block, filled: ARCADE / STORY / CLASSIC tables, story progress and tunes, practice medals and the boss rush, the bonus rounds (NORMAL, EASY
    and HARD medals, the cards), the venue-start score of chapter `story`, BAR CHANGE on KEEP, the debug menu unlocked."""
    from test_difficulty import dx_block
    from test_rush import pr_block2
    from test_scores import v7_image
    img = v7_image([("AAA", 9000), ("BBB", 800)], story=story, step=step, tunes=tunes, story_tbl=[("CCC", 7000)], classic=[("DDD", 6000)])
    img = put(img, PR_AT, pr_block2(0x1FF, [0x1B, 2, 1], bits=0x3, best=[1234, 2345], all_score=50000, all_time=3000, all_n=2))
    img = put(img, BX_AT, bx_block(reached=7, medals=0x1B, seen=0x00FF))
    img = put(img, DX_AT, dx_block(0x06, 0x1B))
    img = put(img, SV_AT, sv_block(story, 777))
    img = put(img, BC_AT, bc_block(1))
    img = put(img, DU_AT, du_block())
    return img


def without(img, *names):
    """The image with these blocks erased (zero bytes where they were)."""
    r = bytearray(img)
    for n in names:
        at, n_bytes = BLOCKS[n]
        r[at:at + n_bytes] = bytes(n_bytes)
    return bytes(r)


def corrupt(img, name):
    """The image with block `name`'s checksum wrong (the block is otherwise whole)."""
    r = bytearray(img)
    at, n = BLOCKS[name]
    r[at + n - 2] ^= 1
    return bytes(r)


# ---- what a boot made of it ----
def observe(rom):
    """The game's working copies after the boot, read by name: the story, tunes, practice, the three tables, the bar-change flag."""
    return dict(progress=rom.mem("story_progress"), reached=rom.mem("story_reached"), tunes=rom.mem16("tune_unlocked"), migrated=rom.mem("save_migrated"),
                mg_unlocked=rom.mem16("mg_unlocked"), mg_best=bytes(rom.read("mg_best", 10)), scores=bytes(rom.read("top_scores", 60)),
                names=bytes(rom.read("top_names", 45)), keep=rom.mem("level_dirs") & 0x80, hi=bytes(rom.read("hi_digits", 6)))


def debug_line(rom):
    """1: SETTINGS lists DEBUG MENU (the game reads the unlock as set)."""
    from conftest import K_DEBUG
    title_pick(rom, K_SETTINGS)
    rom.run(MENU_SETTLE)
    n = K_DEBUG in menu_items(rom)
    rom.press("b", 2)
    rom.run(MENU_SETTLE)
    return int(n)


def bonus_view(rom):
    """The first bonus round in BONUS > MINI GAMES, in each mode: the medal word shown (NORMAL, HARD, EASY): the saved bonus medals as read."""
    import test_mg_list as ml
    from test_difficulty import BONUS_FIRST, EASY, HARD, NORMAL, goto_mode
    ml.to_list(rom)
    ml.tap(rom, "down")                          # (the first bonus round)
    rom.run(4)
    out = []
    for mode in (NORMAL, HARD, EASY):
        goto_mode(rom, mode)
        out.append(ml.medal_word(rom))
    return out


def continue_score(model, img):
    """CONTINUE's score on a boot of img (the venue-start block as read): the PLAY submenu settled (a table's HI line takes frames to build, and a press
    in them is lost), then CONTINUE, then the PRE scene's score."""
    from conftest import K_PLAY, hold_stage_anim, menu_tap
    from test_flow import run_until, state
    from test_pause import score_of
    from test_scores import booted
    from test_flow import GS_GOAL, GS_STORY
    rom = booted(model, img)
    try:
        hold_stage_anim(rom)
        title_pick(rom, K_PLAY)
        rom.run(30)
        menu_tap(rom, "a")
        run_until(rom, lambda: state(rom) in (GS_STORY, GS_GOAL), 60)      # (a step reached: the shift's goal banner, else the PRE scene)
        rom.run(10)
        return score_of(rom)
    finally:
        rom.stop()


def all_views(model, img):
    """Everything above about one boot of img, plus the bonus list and CONTINUE (separate boots)."""
    from test_scores import booted
    with booted(model, img) as rom:
        o = observe(rom)
        o["debug"] = debug_line(rom)
    with booted(model, img) as rom:
        o["bonus"] = bonus_view(rom)
    o["continue"] = continue_score(model, img) if o["progress"] and o["progress"] < 10 else None
    return o
