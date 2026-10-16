# Old saves (owner 2026-10-16 audit): every block src/save.c added over the weeks -- "MGP1"/"MGP2" practice, "MGB1" bonus rounds, "MD" EASY / HARD medals,
# "SV" venue-start score, "BC" bar change, "DU" debug unlock -- is optional: a cartridge written before it loads cleanly with that block's defaults and every
# other block as it was. A block that does not check out reads as absent. The images are built the way each stage of the game wrote them (tests/save_images.py).
import pytest
from conftest import du_block, bx_block
from save_images import BC_AT, BLOCKS, DU_AT, DX_AT, PR_AT, SIZE, SV_AT, TBL_AT, all_views, bc_block, corrupt, full_image, md_block, put, sv_block, without
from test_difficulty import dx_block
from test_mg_list import pr_block
from test_scores import v3_image, v4_image, v5_image, v6_image, v7_image
from conftest import BX_AT

pytestmark = pytest.mark.timeout(600)

MODELS = ["dmg", "cgb"]
NONE_WORD = "SHAKE-UP"           # the bonus line with no medal: the game's name for it


def bonus_expect(normal, hard, easy):
    return [normal or NONE_WORD, hard or NONE_WORD, easy or NONE_WORD]


@pytest.fixture(scope="module", params=MODELS)
def views(request):
    """The views of the full image and of a blank cartridge (per model)."""
    m = request.param
    return m, all_views(m, full_image()), all_views(m, None)


def test_the_full_image_reads_as_written(views):
    model, full, blank = views
    assert full["progress"] == 2 and full["reached"] == 0 and full["tunes"] == 0x2345 | 1 and full["keep"] == 0x80 and full["debug"] == 1
    assert full["mg_unlocked"] == 0x1FF and full["mg_best"][:3] == bytes([0x1B, 2, 1])
    assert full["bonus"] == bonus_expect("GOLD", "GOLD", "SILVER") and full["continue"] == 777
    assert full["scores"][:8] == (9000).to_bytes(4, "little") + (800).to_bytes(4, "little")
    assert blank["progress"] == 0 and blank["tunes"] == 1 and blank["keep"] == 0 and blank["debug"] == 0 and blank["bonus"] == bonus_expect(0, 0, 0)
    assert blank["mg_unlocked"] == 0 and blank["mg_best"] == bytes(10) and blank["scores"] == bytes(60) and blank["continue"] is None


# the stages the save went through (the order the blocks arrived), each a cartridge written then
def stage(n):
    """Stage n of the save's history: 0 only the main block and the three tables, 1 + practice "MGP1", 2 "MGP2" (+ the boss rush), 3 + the bonus rounds "MGB1",
    4 + "MD", 5 + the venue-start score "SV", 6 + "BC", 7 + "DU"."""
    full = full_image()
    img = without(full, "MGP2", "MGB1", "MD", "SV", "BC", "DU")
    if n == 1:
        img = put(img, PR_AT, pr_block(0x1FF, [0x1B, 2, 1], magic=b"MGP1"))
    if n >= 2:
        img = put(img, PR_AT, full[PR_AT:PR_AT + 46])
    if n >= 3:
        img = put(img, BX_AT, full[BX_AT:BX_AT + 10])
    if n >= 4:
        img = put(img, DX_AT, full[DX_AT:DX_AT + 6])
    if n >= 5:
        img = put(img, SV_AT, full[SV_AT:SV_AT + 8])
    if n >= 6:
        img = put(img, BC_AT, full[BC_AT:BC_AT + 5])
    if n >= 7:
        img = put(img, DU_AT, full[DU_AT:DU_AT + 5])
    return img


def expected(stage_n, full, blank):
    e = dict(full)
    if stage_n < 1:
        e["mg_unlocked"], e["mg_best"] = blank["mg_unlocked"], blank["mg_best"]
    if stage_n < 3:
        e["bonus"] = bonus_expect(0, 0, 0)
    elif stage_n < 4:
        e["bonus"] = bonus_expect("GOLD", 0, 0)
    if stage_n < 5:
        e["continue"] = 0                    # (a story to continue, no venue-start score: 0)
    if stage_n < 6:
        e["keep"] = 0
    if stage_n < 7:
        e["debug"] = 0
    return e


@pytest.mark.parametrize("n", range(8))
def test_a_save_from_each_stage_loads_with_defaults_for_the_blocks_it_does_not_have(views, n):
    model, full, blank = views
    got = all_views(model, stage(n))
    assert got == expected(n, full, blank), n


@pytest.mark.parametrize("n", [1, 2, 3, 4, 5, 6, 7])
def test_booting_a_stage_writes_nothing_but_the_practice_migration(n):
    """The boot never rewrites a block it read (an MGP1 block alone becomes MGP2, its mini-games kept, the rush part empty)."""
    from conftest import sram_peek
    from test_erase import boot_with
    img = stage(n)
    rom = boot_with("cgb", img)
    try:
        ram = sram_peek(rom, 0, SIZE)
    finally:
        rom.stop()
    if n == 1:
        assert ram[PR_AT:PR_AT + 4] == b"MGP2" and ram[PR_AT + 4:PR_AT + 6] == img[PR_AT + 4:PR_AT + 6] and ram[PR_AT + 6:PR_AT + 16] == img[PR_AT + 6:PR_AT + 16]
        assert ram[PR_AT + 16:PR_AT + 44] == bytes(28), "the rush part empty"
        ram = put(ram, PR_AT, img[PR_AT:PR_AT + 46])
    assert ram == img


# ---- a block that does not check out reads as absent, and the others are not disturbed ----
FIELDS = {"main": ("progress", "reached", "tunes", "continue"), "MGP2": ("mg_unlocked", "mg_best"), "MGB1": ("bonus",), "MD": ("bonus",), "SV": ("continue",),
          "BC": ("keep",), "DU": ("debug",), "HSA1": ("scores", "names", "hi"), "HSS1": ("scores", "names"), "HSC2": ("scores", "names")}
TABLE = {"HSA1": 0, "HSS1": 1, "HSC2": 2}


@pytest.mark.parametrize("name", list(BLOCKS))
def test_a_bad_checksum_reads_as_absent_and_touches_only_its_own_part(views, name):
    model, full, blank = views
    bad = all_views(model, corrupt(full_image(), name))
    if name == "main":                                     # (the story and the tunes go; the tables are blocks of their own and stay: save.c hi_load)
        for k in FIELDS["main"]:
            assert bad[k] == blank[k], k
        for k in full:
            if k not in FIELDS["main"]:
                assert bad[k] == full[k], k
        return
    gone = all_views(model, without(full_image(), name))
    assert bad == gone, f"{name}: a bad checksum is an absent block"
    assert bad != full, name
    for k in full:                                         # (the other blocks' parts are as in the full image)
        if k in FIELDS[name] or (k in ("scores", "names", "hi") and name in TABLE):
            continue
        assert bad[k] == full[k], (name, k)
    if name in TABLE:                                      # one table empty, the other two as they were
        for u in range(3):
            now, was = bad["scores"][u * 20:u * 20 + 20], full["scores"][u * 20:u * 20 + 20]
            assert now == (bytes(20) if u == TABLE[name] else was), (name, u)


@pytest.mark.parametrize("name", [n for n in BLOCKS if n != "main"])
def test_a_block_with_the_wrong_magic_or_a_flipped_complement_reads_as_absent(views, name):
    model, full, blank = views
    gone = all_views(model, without(full_image(), name))
    at, n = BLOCKS[name]
    r = bytearray(full_image())
    r[at] ^= 0x20
    assert all_views(model, bytes(r)) == gone, "the magic"
    r = bytearray(full_image())
    r[at + n - 1] ^= 1
    assert all_views(model, bytes(r)) == gone, "the complement"


# ---- the older versions of the main block (3 to 6) hold their table where the later blocks live ----
OLD = {3: v3_image, 4: v4_image, 5: v5_image, 6: v6_image}


@pytest.mark.parametrize("ver", [3, 4, 5, 6])
def test_an_old_main_block_s_table_bytes_never_read_as_a_later_block(views, ver):
    """Versions 3-6 keep a top 5 in bytes 4-33, where "SV" (0x0A), "BC" (0x12) and "DU" (0x18) now sit: its initials and scores must not unlock
    the debug menu, turn BAR KEEP on or give CONTINUE a score. (Their tables are dropped by the migration.)"""
    model, full, blank = views
    entries = [("SVA", 100), ("BCD", 99), ("DUX", 98), ("ZZZ", 97), ("SV ", 96)]
    kw = dict(story=2) if ver == 3 else dict(story=2, step=1) if ver == 4 else dict(story=2, step=1, tunes=0x31)
    img = OLD[ver](entries, **kw)
    got = all_views(model, img)
    assert got["keep"] == 0 and got["debug"] == 0 and got["continue"] == 0
    assert got["scores"] == bytes(60) and got["progress"] == (2 if ver >= 6 else 2) and got["migrated"] == ver
    assert got["bonus"] == bonus_expect(0, 0, 0) and got["mg_unlocked"] == 0


@pytest.mark.parametrize("ver", [3, 4, 5, 6])
def test_an_old_save_keeps_the_blocks_that_live_beyond_its_bytes(views, ver):
    """An old main block with practice, bonus rounds and EASY / HARD medals (0x40 and up are free in every version): migrated, the rest kept."""
    model, full, blank = views
    kw = dict(story=2) if ver == 3 else dict(story=2, step=1) if ver == 4 else dict(story=2, step=1, tunes=0x31)
    img = OLD[ver]([("ABC", 500)], **kw)
    for name in ("MGP2", "MGB1", "MD"):
        at, n = BLOCKS[name]
        img = put(img, at, full_image()[at:at + n])
    got = all_views(model, img)
    assert got["migrated"] == ver and got["progress"] == 2
    assert got["mg_unlocked"] == full["mg_unlocked"] and got["mg_best"] == full["mg_best"] and got["bonus"] == full["bonus"]
    assert got["keep"] == 0 and got["debug"] == 0 and got["continue"] == 0 and got["scores"] == bytes(60)
