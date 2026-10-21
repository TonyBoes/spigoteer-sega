# The DX badge on the title (src/title.c, assets/art/dx_badge.txt): three 8x16 OBJ entries (OAM 20-22, OBJ tiles 40..45, OBJ palette 7) under the logo's
# right end, CGB only (a GBA in Color mode counts as a Color: is_cgb). It stamps on once the logo's last drip has fallen (DX_T0 title frames), and
#   - shows on the Color title as exactly the art's pixels (OAM and screen), and never on the DMG;
#   - is never crossed by the title's own sparkles, drips, bubbles or cursor;
#   - is gone on every other screen (the next screen's hide_all_sprites), and stamps on again when the title comes back;
#   - fades with the palette fade like the rest of the picture (the OBJ palette 7 is one of the 64 colours it steps).
import pytest

from conftest import ROOT, K_BONUS, K_BOSSRUSH, K_CLASSIC, K_CREDITS, K_MINIGAMES, K_PLAY, K_SOUNDTRACK, K_STORY, TRANS_ADDR, \
    gesture, release_gesture, title_level, title_pick, trans_enable, with_unlock, menu_to, menu_tap
from test_flow import state, run_until, TITLE
from test_menu_music import lcd_on
from test_sound import make_rom

ART = [r.rstrip("\n") for r in (ROOT / "assets/art/dx_badge.txt").read_text().splitlines() if r.strip() and not r.startswith(";")]
BOX = (127, 33)                      # the badge's top left on the screen (src/title.c DX_X, DX_Y)
W, H = 24, 16
BADGE_OAM = {(33 + 16, 127 + 8 + 8 * i, 40 + 2 * i) for i in range(3)}   # (y, x, tile) of the three entries
DX_T0 = 96                           # src/title.c DX_T0 at 9 letters, 5 fill states: 6 + 7 * 8 + 3 * 4 + 22
WALL = (2, 40)                       # a plain wall pixel left of the badge, below the logo


def title_t(gb):
    return gb.mem16("title_t")


def badge_entries(gb):
    return [s for s in gb.oam() if (s["y"], s["x"], s["tile"]) in BADGE_OAM and s["flags"] & 7 == 7]


def run_to_title_t(gb, t):
    run_until(gb, lambda: title_t(gb) >= t, 600)


def box(im):
    return [[im.getpixel((BOX[0] + x, BOX[1] + y)) for x in range(W)] for y in range(H)]


def classes(im):
    """The colour of each of the art's characters on this screen, or None where one character shows two colours."""
    px, wall, seen = box(im), im.getpixel(WALL), {}
    for y, row in enumerate(ART):
        for x, c in enumerate(row):
            col = wall if c == "." else px[y][x]
            if seen.setdefault(c, col) != col:
                return None
    return seen, wall


def badge_is_there(im):
    got = classes(im)
    if not got:
        return False
    seen, wall = got
    return seen["."] == wall and len({seen["-"], seen["+"], seen["#"], wall}) == 4


def non_wall(im):
    wall = im.getpixel(WALL)
    return sum(1 for row in box(im) for p in row if p != wall)


def test_the_badge_stamps_on_after_the_logo_on_color_and_never_on_dmg(boot):
    assert title_t(boot) < DX_T0 - 10 and not badge_entries(boot), "not yet: the last drip is still to fall"
    run_to_title_t(boot, DX_T0 + 3)
    boot.run(2)
    if boot.model_name == "cgb":
        got = badge_entries(boot)
        assert len(got) == 3 and {(s["y"], s["x"], s["tile"]) for s in got} == BADGE_OAM
        assert state(boot) == TITLE
    else:
        assert not badge_entries(boot)
        for _ in range(60):
            boot.run(5)
            assert not badge_entries(boot) and all(s["y"] == 0 for s in boot.oam()[20:23])


def test_the_badge_pixels_are_the_art_on_color_and_absent_on_dmg(boot):
    run_to_title_t(boot, DX_T0 + 12)
    boot.run(3)
    im = boot.image()
    if boot.model_name == "cgb":
        assert badge_is_there(im)
        seen, wall = classes(im)
        assert wall not in (seen["-"], seen["+"], seen["#"])
        assert len(set(seen.values())) == 4
        # cream is lighter than the red, the red lighter than the sign's dark body (the palette's order: 1, 2, 3)
        lum = {k: sum(v) for k, v in seen.items()}
        assert lum["-"] > lum["+"] > lum["#"], lum
        n_art = sum(c != "." for row in ART for c in row)
        assert non_wall(im) == n_art, (non_wall(im), n_art)
    else:
        assert non_wall(im) < 70, "DMG: at most a bubble crosses that rectangle"
        assert not badge_is_there(im)


def test_the_badge_is_never_crossed_by_the_title_s_effects():
    """Color: a bubble spawn is forced every few frames (the spawn x is random; those at the badge's x are moved left), over the whole animation."""
    gb = make_rom("cgb")
    gb.run(120)
    spawns = 0
    t0 = title_t(gb)
    for f in range(1050):                            # (the idle title shows the top-5 table at title_t 1200)
        if f % 9 == 0:
            gb.write("bubble_timer", 1)
            spawns += 1
        gb.run(1, True)                              # (rendered: image() would otherwise step one more frame)
        if title_t(gb) >= DX_T0 + 5:
            assert badge_is_there(gb.image()), f"frame {f} (title_t {title_t(gb)})"
    gb.pb.stop(save=False)
    assert spawns > 50 and title_t(gb) > t0 + 1000


def test_the_logo_s_last_drip_has_fallen_before_the_badge_stamps_on():
    """The drip under the second E (OAM 7) falls beside the badge's left edge: the badge is never on the screen while a drip is."""
    gb = make_rom("cgb")
    gb.run(120)
    both = drips = 0
    for _ in range(DX_T0 + 60):
        gb.run(1)
        up, drip = bool(badge_entries(gb)), gb.oam()[7]["y"] != 0
        both += up and drip
        drips += drip
    gb.pb.stop(save=False)
    assert drips > 20 and both == 0, (drips, both)


SCREENS = {}


def screen(f):
    SCREENS[f.__name__[3:]] = f
    return f


@screen
def to_arcade(gb):
    title_level(gb)


@screen
def to_story(gb):
    title_pick(gb, K_PLAY, K_STORY)


@screen
def to_classic(gb):
    title_pick(gb, K_PLAY, K_CLASSIC)


@screen
def to_soundtrack(gb):
    title_pick(gb, K_BONUS, K_SOUNDTRACK)


@screen
def to_minigames(gb):
    title_pick(gb, K_BONUS, K_MINIGAMES)


@screen
def to_bossrush(gb):
    title_pick(gb, K_BONUS, K_BOSSRUSH)


@screen
def to_credits(gb):
    title_pick(gb, K_BONUS, K_CREDITS)


@pytest.mark.parametrize("name", sorted(SCREENS))
def test_the_badge_is_gone_on_every_other_screen(name):
    gb = make_rom("cgb")
    gb.run(120)
    run_to_title_t(gb, DX_T0 + 5)
    gb.run(2)
    assert len(badge_entries(gb)) == 3
    SCREENS[name](gb)
    gb.run(15)                                       # (CLASSIC's start takes a few frames to clear the title's sprites since main's 30 fps work)
    for _ in range(12):
        gb.run(10)
        assert not badge_entries(gb), name
        assert not any((s["y"], s["x"], s["tile"]) in BADGE_OAM for s in gb.oam()), name
    gb.pb.stop(save=False)


def test_the_badge_is_gone_in_the_debug_menu_and_on_the_idle_table():
    gb = make_rom("cgb", with_unlock())
    gb.run(120)
    run_to_title_t(gb, DX_T0 + 5)
    assert len(badge_entries(gb)) == 3
    gesture(gb)
    release_gesture(gb)
    gb.run(30)
    assert state(gb) != TITLE or not badge_entries(gb)
    assert not badge_entries(gb)
    gb.press("b", 2)
    gb.run(60)
    assert state(gb) == TITLE
    gb.pb.stop(save=False)
    gb = make_rom("cgb")
    gb.run(120)
    run_to_title_t(gb, DX_T0 + 5)
    from test_scores import idle_title
    idle_title(gb)
    gb.run(120)
    assert state(gb) != TITLE and not badge_entries(gb)
    gb.pb.stop(save=False)


def test_the_badge_stamps_on_again_when_the_title_comes_back():
    gb = make_rom("cgb")
    gb.run(120)
    run_to_title_t(gb, DX_T0 + 5)
    title_pick(gb, K_BONUS, K_SOUNDTRACK)
    gb.run(40)
    assert state(gb) != TITLE and not badge_entries(gb)
    gb.press("b", 2)
    run_until(gb, lambda: state(gb) == TITLE and lcd_on(gb), 200)
    gb.run(4)
    assert title_t(gb) < DX_T0 - 10 and not badge_entries(gb), "a fresh title: the logo fills again, the badge comes last"
    run_to_title_t(gb, DX_T0 + 5)
    gb.run(2)
    assert len(badge_entries(gb)) == 3 and badge_is_there(gb.image())
    gb.pb.stop(save=False)


def white(p):
    return min(p) >= 0xF0


def test_the_badge_fades_with_the_palette_fade_and_is_never_the_picture_on_a_white_screen():
    """Transitions on: BONUS > MINI GAMES is the quick white fade. Every frame the LCD shows: where the wall has gone white, the badge's rectangle
    must be (nearly) white too, and the badge colours step toward white in the same frames (OBJ palette 7 is one of the 64 colours it fades)."""
    gb = make_rom("cgb")
    gb.run(120)
    trans_enable(gb, True)
    run_to_title_t(gb, DX_T0 + 5)
    title_pick(gb, K_BONUS)
    gb.run(8)
    menu_to(gb, K_MINIGAMES)
    gb.run(8)
    assert badge_is_there(gb.image())
    gb.pb.button_press("a")
    walls, dark_on_white, lit = [], 0, 0
    for i in range(90):
        gb.run(1, True)
        if i == 1:
            gb.pb.button_release("a")
        if not lcd_on(gb):
            continue
        im = gb.image()
        px = [p for row in box(im) for p in row]
        if white(im.getpixel(WALL)):
            walls.append(i)
            dark_on_white += sum(1 for p in px if min(p) < 0xC0)
        elif badge_entries(gb):
            lit += 1
    gb.pb.stop(save=False)
    assert walls, "the fade passed through a white screen"
    assert dark_on_white == 0, f"{dark_on_white} badge pixels still dark while the wall was white"


def test_the_badge_adds_no_more_than_ten_sprites_to_any_line():
    gb = make_rom("cgb")
    gb.run(120)
    worst = 0
    from test_flow import most_per_scanline
    for _ in range(500):
        gb.run(1)
        worst = max(worst, most_per_scanline(gb))
    gb.pb.stop(save=False)
    assert 3 <= worst <= 10, worst


# ---- the rainbow: OBJ palette 7's colours 2 (near shadow) and 3 (far shadow) cycle, 48 steps of 2 frames (96 frames); colour 1 (cream) never changes ----
from test_menu_music import obj_palette
from conftest import check_golden

CREAM = bytes([(31 | 30 << 5 | 24 << 10) & 255, (31 | 30 << 5 | 24 << 10) >> 8])


def colours(gb):
    p = obj_palette(gb, 7)
    return p[2:4], p[4:6], p[6:8]


def test_the_shadows_cycle_through_a_rainbow_on_color_and_the_letters_never_change():
    gb = make_rom("cgb")
    gb.run(120)
    if gb.model_name != "cgb":
        pytest.skip("CGB only")
    run_to_title_t(gb, DX_T0 - 2)
    first = colours(gb)
    assert first[0] == CREAM
    seen = []
    for _ in range(DX_T0 - title_t(gb) + 3 + 300):
        gb.run(1)
        c = colours(gb)
        assert c[0] == CREAM, "the letters (colour 1) never change"
        if title_t(gb) >= DX_T0:
            seen.append((title_t(gb), c[1], c[2]))
    gb.pb.stop(save=False)
    near = {c[1] for c in seen}
    far = {c[2] for c in seen}
    assert len(near) >= 40 and len(far) >= 40, (len(near), len(far))
    by_t = {t: (n, f) for t, n, f in seen}
    assert by_t[DX_T0 + 1][0] == first[1] and by_t[DX_T0 + 1][1] == first[2], "the cycle starts from the palette the title loaded: no jump"
    for t in range(DX_T0 + 2, DX_T0 + 150):
        assert by_t[t] == by_t[t + 96], f"a full period is 96 frames (title_t {t})"
    assert by_t[DX_T0 + 2] != by_t[DX_T0 + 50], "half a period on, the colours are different"


def rgb(c):
    v = c[0] | c[1] << 8
    return v & 31, v >> 5 & 31, v >> 10 & 31


def test_the_far_shadow_is_darker_than_the_near_one_in_every_step():
    gb = make_rom("cgb")
    gb.run(120)
    run_to_title_t(gb, DX_T0)
    for _ in range(100):
        gb.run(1)
        _, near, far = colours(gb)
        assert sum(rgb(far)) < sum(rgb(near)), (rgb(near), rgb(far))
        assert near != far
    gb.pb.stop(save=False)


def test_the_palette_is_written_in_vblank_only():
    """title_update (which writes the two colours first thing, behind an LY 144..150 gate) is entered in VBlank on every title frame, and every frame
    in which palette 7 changed was one the gate let through."""
    gb = make_rom("cgb")
    gb.run(120)
    bank, addr = gb.symbols["title_update"]
    lys = []
    gb.pb.hook_register(bank, addr, lambda _: lys.append(gb.pb.memory[0xFF44]), None)
    run_to_title_t(gb, DX_T0 - 2)
    changed = frames = 0
    prev = colours(gb)
    for _ in range(250):
        n = len(lys)
        gb.run(1)
        c = colours(gb)
        for ly in lys[n:]:
            frames += 1
            assert 144 <= ly <= 153, f"a title frame entered at LY {ly}: its logic is not in VBlank"
            if c != prev and title_t(gb) >= DX_T0:
                changed += 1
                assert ly <= 150, f"palette 7 changed on a frame entered at LY {ly}, past the gate"
        prev = c
    gb.pb.stop(save=False)
    assert frames >= 240 and changed >= 100, (frames, changed)


def test_the_dmg_badge_area_does_not_animate():
    gb = make_rom("dmg")
    gb.run(120)
    if gb.model_name != "dmg":
        pytest.skip("DMG only")
    run_to_title_t(gb, DX_T0 + 3)
    assert not badge_entries(gb) and obj_palette(gb, 7) is None
    gb.pb.stop(save=False)


def test_golden_the_badge_at_one_rainbow_phase(boot):
    """One fixed phase (title_t DX_T0 + 2 * 12, 12 steps = a quarter turn), CGB only (the DMG has no badge and no animation)."""
    if boot.model_name != "cgb":
        pytest.skip("CGB only")
    run_to_title_t(boot, DX_T0 + 24)
    assert title_t(boot) == DX_T0 + 24
    boot.run(0)
    check_golden(boot, "dx_rainbow_phase")
