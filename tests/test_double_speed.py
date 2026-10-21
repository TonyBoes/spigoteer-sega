# Color double speed (src/main_cold.c boot_init: cpu_fast() once at boot, a Color only; ROM byte 0x3FFE patched to 0 switches it off).
#
# tests/conftest.py loads a speed-off copy of the ROM into every other test, so those stay as they were written at normal speed. THIS file runs the
# ROM as built (`with double_speed():`) on a Color and checks what the speed change could break:
#   a  KEY1 says double speed after boot on a Color; a DMG does not switch (its frames still take 70224 cycles);
#   b  the music's tempo and pitch are the DMG's (the frame timer ticks twice as fast: music.c DS_NOW / DS_SCALE, the IF-flag wrap carry);
#      the pump's own arithmetic across a gap longer than the timer's 8 bits (1.87 frames in double speed);
#   c  the crowded scenes (RealisticPeak 12 patrons, ClassicPeak 16) never run a frame late: a game frame for every emulator frame;
#   d  a boss's entrance and the start of his fight, and his first-appearance card on the screen (window on);
#   e  menus and screen changes: no music tick gap over today's limits (tests/test_music_transitions.py's legs, the cycle counts doubled);
#   f  (RUN_SLOW, SameBoy) Milk Run's HUD row ends on line 7 as at normal speed;
#   g  the save round trip.
# The emulator's cycle counter doubles in double speed: a frame is 140448 of its cycles.
import contextlib
import os
import subprocess

import numpy as np
import pytest
from PIL import Image

import perf_helpers as ph
import test_boss_in_place as tbip
import test_music_transitions as tmt
import test_scores
from asm_rig import Call, Rig
from conftest import ROM, ROOT, double_speed, game_clock, hold_stage_anim, until_game
from gbtools import Rom
from tick_helpers import tick_log

pytestmark = pytest.mark.timeout(900)

FRAME = 70224


def booted(model, ds=True, frames=120):
    """A Rom on the title: the ROM as built (ds) or the speed-off copy. Use as `with booted(...) as gb`."""
    with double_speed() if ds else contextlib.nullcontext():
        gb = Rom(ROM, model)
    gb.model_name = model
    gb.run(frames)
    hold_stage_anim(gb)
    return gb


def cycles_per_frame(gb, n=30):
    c0 = gb.pb._cycles()
    gb.run(n)
    return (gb.pb._cycles() - c0) / n


# ---- a: the switch ------------------------------------------------------------------------------------------------------------------------
def test_the_shipped_rom_carries_the_speed_byte_set():
    assert ROM.read_bytes()[0x3FFE] == 0xFF, "the free ROM0 byte the test harness patches: 0xFF = switch to double speed on a Color"


def test_a_color_reports_double_speed_after_boot():
    with booted("cgb") as gb:
        assert gb.pb.memory[0xFF4D] & 0x80, "KEY1 bit 7: double speed"
        assert gb.mem("is_cgb") == 1
        assert 1.98 * FRAME <= cycles_per_frame(gb) <= 2.02 * FRAME, "a frame is 140448 CPU cycles in double speed"


def test_a_dmg_does_not_switch():
    with booted("dmg") as gb:
        assert gb.mem("is_cgb") == 0
        assert 0.98 * FRAME <= cycles_per_frame(gb) <= 1.02 * FRAME


def test_the_speed_byte_at_0_switches_a_color_off_for_the_rest_of_the_suite():
    with booted("cgb", ds=False) as gb:               # (conftest's speed-off copy)
        assert not gb.pb.memory[0xFF4D] & 0x80
        assert 0.98 * FRAME <= cycles_per_frame(gb) <= 1.02 * FRAME


# ---- b: the music keeps its tempo and pitch -----------------------------------------------------------------------------------------------
def music_run(model, ds, where, frames=300):
    """(hUGE ticks, music_frames advance, the channel-2 / wave-channel periods heard) over `frames` emulator frames on the title or in a level."""
    with booted(model, ds) as gb:
        if where == "level":
            ph.start_game(gb)
            gb.write("tip_chance", 0)
            gb.run(60)
        st = tick_log(gb)
        mf0 = gb.mem16("music_frames")
        periods = set()
        for _ in range(frames):
            gb.run(1)
            m = gb.pb.memory
            periods.add((m[0xFF18] | (m[0xFF19] & 7) << 8, m[0xFF1D] | (m[0xFF1E] & 7) << 8))
        return len(st), (gb.mem16("music_frames") - mf0) & 0xFFFF, periods


@pytest.mark.parametrize("where", ["title", "level"])
def test_the_music_ticks_as_often_as_on_a_dmg(where):
    n_dmg, mf_dmg, p_dmg = music_run("dmg", False, where)
    n_cgb, mf_cgb, p_cgb = music_run("cgb", True, where)
    n_ns, mf_ns, _ = music_run("cgb", False, where)
    print("TICKS", where, "dmg", n_dmg, "cgb double", n_cgb, "cgb normal", n_ns)
    assert 298 <= n_dmg <= 302, "a tick a frame on a DMG"
    assert abs(n_cgb - n_dmg) <= 1 and abs(mf_cgb - mf_dmg) <= 1, ("tempo: ticks per 300 frames", n_dmg, n_cgb, mf_dmg, mf_cgb)
    assert abs(n_ns - n_dmg) <= 1
    # (the pitch is the sound chip's, not the CPU's: the same notes, the same periods)
    assert p_cgb == p_dmg or len(p_cgb ^ p_dmg) <= 2, sorted(p_cgb ^ p_dmg)


def pump_gap_case(rig, model_ds, tima, tma, wrapped):
    """music_pump called with the timer as a gap of that length left it: did the driver tick (music_frames), what is left in the pump's remainder."""
    mf = rig.addr("music_frames")
    poke = {0xFF05: tima, 0xFF06: tma, 0xFF0F: 0xE0 | (0x04 if wrapped else 0)}
    r = rig.run([Call("music_pump", poke=poke)])[0]
    return mf in r.diff or (mf + 1) in r.diff


def test_a_pump_after_a_gap_longer_than_the_timers_eight_bits_ticks_in_double_speed_and_waits_in_normal_speed():
    """In double speed TIMA wraps in 1.87 frames: it reloads from TMA and sets IF bit 2. A pump 2.3 frames after the last tick sees TIMA small
    and the flag: it adds the 256 lost counts and ticks (the first case), no flag and TIMA small: not a frame yet (the second); at normal speed the
    flag is never read (the third and fourth: the same decisions as before)."""
    with booted("cgb", True) as gb:
        rig = Rig(ROM, "cgb", gb=gb)
        assert pump_gap_case(rig, True, 0x20, 0, True), "wrapped once: 256 + 32 counts = 2.1 frames, a tick is due"
        assert not pump_gap_case(rig, True, 0x20, 0, False), "TIMA 32 and no wrap: a quarter frame since the tick"
        assert pump_gap_case(rig, True, 0x95, 0, False), "TIMA 149 and no wrap: a frame since the tick"
        assert pump_gap_case(rig, True, 0x25, 0x05, True), "the reload value is TMA (the pump's flags and lateness): 256 + 37 - 5"
    with booted("cgb", False) as gb:
        rig = Rig(ROM, "cgb", gb=gb)
        assert not pump_gap_case(rig, False, 0x20, 0, True), "normal speed: the flag means nothing"
        assert pump_gap_case(rig, False, 0x48, 0, False), "TIMA 72 = a frame at 4096 Hz"


# ---- c: no late frames in the crowded scenes ------------------------------------------------------------------------------------------------
FRAMES = 1200


def late_share(model, ds, **scene):
    """The share of emulator frames in which the game did not finish a frame (no vq_frame_end): with no late frame every emulator frame has exactly
    one game frame."""
    with booted(model, ds) as gb:
        seen = {}

        def check(g, i):
            c = game_clock(g)
            if "last" in seen:
                seen["late"] += c.frames - seen["last"] == 0
                seen["many"] += c.frames - seen["last"] > 1
                seen["n"] += 1
            else:
                seen.update(late=0, many=0, n=0)
            seen["last"] = c.frames

        ph.realistic_run(gb, FRAMES, check, **scene)
        return seen["late"], seen["many"], seen["n"]


SCENES = {"realistic12": dict(target=12), "classic16": dict(target=16, cls=ph.ClassicPeak, classic=25)}


@pytest.mark.parametrize("name", list(SCENES))
def test_the_crowded_scenes_have_no_late_frame_in_double_speed(name):
    late, many, n = late_share("cgb", True, **SCENES[name])
    print("LATE", name, late, "of", n)
    assert n >= FRAMES - 2 and late == 0 and many == 0, (name, late, many, n)


def test_the_measure_sees_the_lateness_at_normal_speed():
    """The control: the same ClassicPeak scene at normal speed (the speed-off copy) is late in most frames."""
    late, many, n = late_share("cgb", False, **SCENES["classic16"])
    print("LATE classic16 normal speed", late, "of", n)
    assert late > 0.2 * n, (late, n)


# ---- d: a boss's entrance, his fight, his first-appearance card ------------------------------------------------------------------------------
BOSSES = [0, 4, 9]


def entrance_history(c):
    """The state at the end of every game frame's logic (conftest.until_game: a hook, so the sample is never mid-frame whatever the speed) from the
    quota met to the card opening: (game_state, his state while he is on, LCD on, his columns stamped)."""
    hist = []
    with tbip.last_call("cgb", c, tbip.bk_block(0)) as gb:
        tbip.win(gb, c, 2)

        def cond():
            hist.append((tbip.state(gb), gb.mem("boss_on") and gb.mem("boss_state"), bool(gb.pb.memory[tbip.LCDC] & 0x80), any(gb.read("boss_cols", 5))))
            if len(hist) == 4 and not gb.mem("boss_on"):
                tbip.clear_bars(gb)
            return tbip.state(gb) == tbip.PAUSED
        until_game(gb, cond, limit=1500)
    return hist


@pytest.mark.parametrize("c", BOSSES)
def test_a_boss_enters_the_fight_begins_and_his_card_opens_after_it_in_double_speed(c):
    """tests/test_boss_in_place.py's entrance test, sampled per game frame (the test there samples per emulator frame: in double speed that falls in the
    middle of the frame's logic): he comes in (BS_ENTER, BS_WALKIN), the fight begins (BS_WALK, his columns on his bar) and only then does the first-
    appearance card open, the LCD on until the card's own fade."""
    with double_speed():
        h = entrance_history(c)
        card_at = len(h) - 1
        assert h[card_at][0] == tbip.PAUSED, "the card opened"
        entrance = [k for k, x in enumerate(h) if x[1] in (tbip.BS_ENTER, tbip.BS_WALKIN)]
        assert entrance and card_at > entrance[-1], "after his entrance"
        assert all(x[0] == tbip.PLAYING for x in h[:card_at]), "playing until the card"
        assert any(x[1] == tbip.BS_WALK for x in h[:card_at]), "a whole frame of the fight before the card"
        assert h[card_at - 1][3], "him on his bar in the frame the card fades out"
        assert all(x[2] for x in h[:card_at]), "the LCD was on until the card"


@pytest.mark.parametrize("c", BOSSES)
def test_his_card_pauses_the_game_resumes_it_and_is_on_the_screen_in_double_speed(c):
    with double_speed():
        tbip.test_the_first_time_a_boss_appears_the_game_pauses_on_his_card_and_resumes_when_it_is_left("cgb", c)
        tbip.test_his_card_is_on_the_screen_while_it_is_open_not_the_paused_game_behind_it("cgb", c)


@pytest.mark.parametrize("c", BOSSES)
def test_a_boss_fight_runs_and_ends_in_double_speed(c):
    with double_speed():
        with tbip.last_call("cgb", c) as gb:
            tbip.win(gb, c, 2)
            gb.run(3)
            if not gb.mem("boss_on"):
                tbip.clear_bars(gb)
            for _ in range(300):
                gb.run(1)
                if gb.mem("boss_on") and gb.mem("boss_state") == 0 and gb.mem("boss_hp"):
                    break
            assert gb.mem("boss_on") == 1 and gb.mem("boss_state") == 0 and gb.mem("boss_hp"), "the fight began"
            gb.run(120)
            assert gb.mem("boss_on") == 1 and gb.mem("game_state") == 1, "and goes on"


# ---- e: menus and screen changes keep the tune in time ------------------------------------------------------------------------------------
@pytest.mark.parametrize("scenario", list(tmt.SCENARIOS))
def test_screen_changes_keep_the_tune_in_time_in_double_speed(scenario, monkeypatch):
    """tests/test_music_transitions.py's legs on the ROM as built: the same limits (a tick interval within [0.3, 1.6] frames, the paused bass within
    a tenth), with a frame counted as the emulator counts it in double speed."""
    monkeypatch.setattr(tmt, "FRAME", 2 * FRAME)
    with double_speed():
        tmt.test_transitions_keep_the_tune_in_time("cgb", scenario)


# ---- f: Milk Run's raster split, on SameBoy -------------------------------------------------------------------------------------------------
SLOW = bool(os.environ.get("RUN_SLOW"))


@pytest.mark.skipif(not SLOW, reason="slow: one build and three SameBoy runs of 12 emulated seconds (RUN_SLOW=1)")
def test_milk_runs_hud_row_ends_on_line_7_in_double_speed():
    """-DAUTO_MR boots into Milk Run's practice round. The HUD row (lines 0-7) must be the same on a Color in double speed, a Color at normal speed (ROM
    byte 0x3FFE 0) and the street must start on line 8 in all of them: mr_lcd_isr's SCX write lands after the split line's pixels (HBlank), as at
    normal speed (it landed on the line itself in double speed: the row's last line scrolled with the street). SameBoy, not PyBoy: only it draws the
    line at the dot the register was written."""
    bdir = ROOT / "out" / "dsmr"
    bdir.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["make", f"BUILD={bdir / 'build'}", f"OUT={bdir / 'out'}", "DEBUGFLAGS=-DDEBUG_MENU -DAUTO_MR"], cwd=ROOT,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-2000:]
    data = (bdir / "build" / "game.gb").read_bytes()
    shots = {}
    for tag, model, speed in (("ds", "cgb", 0xFF), ("ns", "cgb", 0), ("dmg", "dmg", 0xFF)):
        b = bytearray(data)
        b[0x3FFE] = speed
        rom = bdir / f"{tag}.gb"
        rom.write_bytes(bytes(b))
        subprocess.run(["sameboy_tester", f"--{model}", "--length", "12", str(rom)], capture_output=True, timeout=600)
        shots[tag] = np.array(Image.open(rom.with_suffix(".bmp")).convert("RGB")).astype(int)
    assert (shots["ds"][:8] == shots["ns"][:8]).all(), "the HUD row's eight lines: the same in double speed and at normal speed"
    street = shots["ds"][8:16]
    assert (street != shots["ds"][7]).any(), "line 8 is the street, not a repeat of line 7"
    assert shots["ds"][:8].std() > 0 and (shots["dmg"][:8] != shots["dmg"][8]).any()


# ---- g: the save --------------------------------------------------------------------------------------------------------------------------
def test_the_table_survives_a_reset_in_double_speed():
    """A top-5 entry saved to the cartridge RAM at game over and read back by a second boot (all three tables, the hi score on the title)."""
    with double_speed():
        test_scores.test_the_table_survives_a_reset("cgb")


def test_a_story_save_loads_in_double_speed():
    with double_speed():
        test_scores.test_a_version_6_save_keeps_its_story_and_starts_the_tables_fresh("cgb")
