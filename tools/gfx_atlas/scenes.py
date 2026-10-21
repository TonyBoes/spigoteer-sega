"""The screen catalogue: how to reach each screen (by the tests' own helpers) on both models."""
import conftest as CF
from conftest import K_BONUS, K_PLAY, K_SETTINGS, title_pick
from test_scores import booted

SCREENS = []


def screen(id, group, name, window=None, note=""):
    def deco(fn):
        d = dict(id=id, group=group, name=name, fn=fn, note=note)
        if window:
            d["window"] = window
        SCREENS.append(d)
        return fn
    return deco


@screen("title", "Menus", "Title")
def _(model):
    return booted(model)


@screen("title_play", "Menus", "Title: PLAY")
def _(model):
    rom = booted(model)
    title_pick(rom, K_PLAY)
    rom.run(CF.MENU_SETTLE)
    return rom


@screen("title_bonus", "Menus", "Title: BONUS")
def _(model):
    rom = booted(model)
    title_pick(rom, K_BONUS)
    rom.run(CF.MENU_SETTLE)
    return rom


@screen("title_settings", "Menus", "Title: SETTINGS")
def _(model):
    rom = booted(model)
    title_pick(rom, K_SETTINGS)
    rom.run(CF.MENU_SETTLE)
    return rom


@screen("mg_list", "Menus", "BONUS > MINI GAMES (practice list)")
def _(model):
    import test_mg_list as T
    return T.to_list(booted(model))


@screen("rush_menu", "Menus", "BONUS > BOSS RUSH (menu)")
def _(model):
    import test_rush as T
    return T.to_rush(booted(model))


@screen("rush_list", "Menus", "BOSS RUSH: boss list")
def _(model):
    import test_rush as T
    return T.to_list(booted(model))


@screen("soundtrack", "Menus", "BONUS > SOUNDTRACK")
def _(model):
    import test_jukebox as T
    return T.to_jukebox(booted(model))


# ---- levels ----------------------------------------------------------------------------------------------------------------------
import perf_helpers as PH
from test_art import GROUPS, goto_group

VENUE_NAMES = ["The Saloon", "The Stadium", "The Lumber Lodge", "The Bistro", "The Igloo", "The Robot Factory", "The Chrome Cow", "The Teahouse",
               "The Jungle Zoo", "The Space Lounge"]


class Play:
    """The level-8 play script of tests/perf_helpers.py (the bartender fills, serves and moves between bars), lives and quota topped up.
    step(gb, i) is called once before each frame, in the preroll and then in the sampled window."""
    def __init__(self, gb, tip=True):
        self.gb, self.held, self.i, self.tip = gb, None, 0, tip

    def step(self, gb=None, i=None):
        gb = self.gb
        want = PH.SCRIPT[self.i % len(PH.SCRIPT)]
        self.i += 1
        if want != self.held:
            if self.held:
                gb.release(self.held)
            if want:
                gb.hold(want)
            self.held = want
        gb.write("lives", 3)
        gb.write("quota", 250)
        if self.tip and gb.mem16("tip_timer") < 100 and gb.mem16("show_timer") < 100:
            PH.put16(gb, "tip_timer", 400)
            gb.write("tip_bar", 1)
            gb.write("tip_x", 60)

    def run(self, frames):
        for _ in range(frames):
            self.step()
            self.gb.run(1)

    def settle(self, limit=400):
        """On to a frame of real play (a lost life's banner and the level's intro are over)."""
        for _ in range(limit):
            if self.gb.mem("game_state") == 1 and self.gb.mem("intro_timer") == 0:
                return
            self.step()
            self.gb.run(1)


def level_rom(model, group, classic=False):
    rom = booted(model)
    if classic:
        CF.title_pick(rom, K_PLAY, CF.K_CLASSIC)
        PH.start_game  # (CLASSIC starts by itself a few frames after the choice)
        for _ in range(60):
            rom.run(1)
            if rom.mem("game_state") == 1:
                break
    else:
        PH.start_game(rom)
        goto_group(rom, group)
    rom.write("tip_chance", 255)
    return rom


def level(group):
    def fn(model):
        rom = level_rom(model, group)
        p = Play(rom)
        p.run(700)
        p.settle()
        return rom, p.step
    return fn


for _g, _n in enumerate(VENUE_NAMES):
    screen("level_" + GROUPS[_g], "Levels (ARCADE, by venue)", "%d. %s (%s)" % (_g + 1, _n, GROUPS[_g]))(level(_g))


def show(group):
    def fn(model):
        rom = level_rom(model, group)
        p = Play(rom, tip=False)
        p.run(300)
        PH.put16(rom, "tip_timer", 0)
        PH.put16(rom, "show_timer", 704)
        p.run(20)
        return rom, p.step
    return fn


for _g, _n in enumerate(VENUE_NAMES):
    screen("show_" + GROUPS[_g], "Dancers' show (by venue)", "%d. %s (%s)" % (_g + 1, _n, GROUPS[_g]), window=240)(show(_g))


def classic(lv):
    def fn(model):
        rom = booted(model)
        CF.title_pick(rom, K_PLAY, CF.K_CLASSIC, press=False)
        rom.write("title_go", 0x80 | lv)
        rom.press("a", 2)
        rom.run(1)
        for _ in range(60):
            if rom.mem("game_state") == 1:
                break
            rom.run(1)
        rom.write("tip_chance", 255)
        p = Play(rom)
        p.run(700)
        p.settle()
        return rom, p.step
    return fn


screen("classic_3", "Levels (CLASSIC, mirrored)", "CLASSIC level 3: sports, the whole screen mirrored")(classic(3))
screen("classic_6", "Levels (CLASSIC, mirrored)", "CLASSIC level 6: punk bikers, split halves")(classic(6))
screen("classic_12", "Levels (CLASSIC, mirrored)", "CLASSIC level 12: space lounge, bars alternate (busiest)")(classic(12))


# ---- bosses ----------------------------------------------------------------------------------------------------------------------
BOSS_NAMES = ["Big Tex", "The Mascot", "Sasquatch", "The Critic", "The Yeti", "Prototype", "Duke", "Sumo Champ", "Leo the Lion", "Mothership"]


class BossPlay:
    """The bartender pours and serves while the fight runs (hold A to fill, move along the bars); lives topped up."""
    def __init__(self, gb):
        self.gb, self.held, self.i = gb, None, 0

    def step(self, gb=None, i=None):
        gb = self.gb
        want = PH.SCRIPT[self.i % len(PH.SCRIPT)]
        self.i += 1
        if want != self.held:
            if self.held:
                gb.release(self.held)
            if want:
                gb.hold(want)
            self.held = want
        gb.write("lives", 3)


def boss(c, entrance=False):
    def fn(model):
        import boss_common as BC
        rom = BC.fight(model, c, entrance=entrance)
        rom.write("tip_chance", 0)
        p = BossPlay(rom)
        for _ in range(240 if not entrance else 20):
            p.step()
            rom.run(1)
        return rom, p.step
    return fn


for _c, _n in enumerate(BOSS_NAMES):
    screen("boss_%d" % (_c + 1), "Bosses", "%d. %s (%s)" % (_c + 1, _n, GROUPS[_c]))(boss(_c))


# ---- mini-games ------------------------------------------------------------------------------------------------------------------
MINI = [(0, "quickdraw", "Quick Draw (saloon)"), (1, "shirt", "Shirt Cannon (stadium)"), (2, "logroll", "Log Roll (lumber lodge)"),
        (3, "orderup", "Order Up (bistro)"), (4, "marshmallow", "Marshmallows (igloo)"), (5, "battery", "Battery Sort (robot factory)"),
        (6, "milkrun", "Milk Run (Chrome Cow)"), (7, "taiko", "Taiko Pour (teahouse)"), (8, "monkey", "Monkey Biz (zoo)"),
        (9, "asteroid", "Asteroids (space lounge)"), (12, "shakeup", "Can Shake-Up (bonus)"), (13, "fillline", "Perfect Pour (bonus)"),
        (14, "tips", "Tip Shower (bonus)"), (16, "stub", "Green Light (framework stub)")]


class Mash:
    """A little input: A and the D-pad pressed in a fixed rhythm (deterministic), so a game shows more than its idle picture."""
    SEQ = ["a", None, "left", "a", None, "right", "up", "a", "down", "a", None, "left", "right", "a"]

    def __init__(self, gb):
        self.gb, self.held = gb, None

    def step(self, gb=None, i=None):
        k = self.gb.frame // 6
        want = self.SEQ[k % len(self.SEQ)]
        if want != self.held:
            if self.held:
                self.gb.release(self.held)
            if want:
                self.gb.hold(want)
            self.held = want


def minigame(gid, mode=None, play=True):
    def fn(model):
        import test_mg as T
        rom = booted(model)
        T.mg_enter(rom, gid, T.MG_PRACTICE if mode is None else mode)
        m = Mash(rom)
        if play:
            for _ in range(600):
                if rom.mem("mg_phase") == T.MG_PLAY:
                    break
                rom.run(1)
            for _ in range(30):
                m.step()
                rom.run(1)
        return rom, m.step
    return fn


for _gid, _k, _n in MINI:
    screen("mg_" + _k, "Mini-games", _n)(minigame(_gid))


# ---- pause menus and HOW TO PLAY cards ------------------------------------------------------------------------------------------
def tapk(rom, b, settle=3):
    rom.press(b, 2)
    rom.run(settle)


@screen("pause_level", "Pause and cards", "Pause menu in a level")
def _(model):
    rom = level_rom(model, 0)
    p = Play(rom)
    p.run(200)
    p.settle()
    rom.release("a")
    for k in ("left", "right", "up", "down"):
        rom.release(k)
    tapk(rom, "start")
    rom.run(10)
    return rom


@screen("pause_boss", "Pause and cards", "Pause menu in a boss fight (has HOW TO PLAY)")
def _(model):
    import boss_common as BC
    rom = BC.fight(model, 0)
    rom.run(60)
    tapk(rom, "start")
    rom.run(10)
    return rom


@screen("pause_boss_card", "Pause and cards", "Boss hint card (pause > HOW TO PLAY)")
def _(model):
    import boss_common as BC
    rom = BC.fight(model, 0)
    rom.run(60)
    tapk(rom, "start")
    tapk(rom, "down")
    tapk(rom, "a", 3)
    rom.run(60)
    return rom


@screen("pause_minigame", "Pause and cards", "Pause menu in a mini-game")
def _(model):
    import test_mg as T
    rom = booted(model)
    T.mg_enter(rom, 0, T.MG_PRACTICE)
    for _ in range(600):
        if rom.mem("mg_phase") == T.MG_PLAY:
            break
        rom.run(1)
    rom.run(20)
    tapk(rom, "start")
    rom.run(10)
    return rom


def card(gid, pages=0):
    def fn(model):
        import test_mg as T
        rom = booted(model, cards=False)
        T.mg_enter(rom, gid, T.MG_PRACTICE)
        rom.run(3)
        for _ in range(pages):
            tapk(rom, "a", 20)
            rom.run(40)
        rom.run(10)
        return rom
    return fn


screen("card_quickdraw", "Pause and cards", "HOW TO PLAY card: Quick Draw (1 page)", window=120)(card(0))
screen("card_milkrun", "Pause and cards", "HOW TO PLAY card: Milk Run page 1 of 3", window=120)(card(6))
screen("card_milkrun_3", "Pause and cards", "HOW TO PLAY card: Milk Run page 3 of 3", window=120)(card(6, 2))


# ---- story: the map, the pictures, the banners ------------------------------------------------------------------------------------
@screen("story_map", "Story", "Story map (6 venues cleared)")
def _(model):
    import test_story_map as T
    return T.to_map(model, 6)


@screen("story_map_venue", "Story", "Story map: a cleared venue's PLAY / BACK panel")
def _(model):
    import test_story_map as T
    return T.venue_panel(model, 5, 1)


@screen("story_map_town", "Story", "Story map: the town (festival, Pour-Off)")
def _(model):
    import test_story_map as T
    return T.town_panel(model, 9)


@screen("story_intro_before", "Story", "Story picture: INTRO, the spigot and fountain (page 1)")
def _(model):
    import test_story as TS
    rom = TS.start_story(model)
    TS.page_ready(rom)
    return rom


@screen("story_intro_after", "Story", "Story picture: INTRO, the explosion (page 7)")
def _(model):
    import test_story as TS
    import test_story_pictures as TP
    rom = TS.start_story(model)
    for _ in range(6):
        TS.page_ready(rom)
        rom.press("a", 2)
    for _ in range(40):
        rom.run(1)
        if TS.picture_switching(rom):
            break
    for _ in range(60):
        rom.run(1)
        if rom.mem("story_typed") != 54 and rom.mem("story_scratch") == 0:
            break
    TS.page_ready(rom)
    for _ in range(80):
        if TP.burst_t(rom) == 255:
            break
        rom.run(1)
    return rom


@screen("story_pre_igloo", "Story", "Story scene: the igloo's PRE scene (Aurora)")
def _(model):
    import test_story as TS
    from test_scores import v7_image
    rom = TS.start_story(model, v7_image([], story=4), cont=True)
    TS.page_ready(rom)
    return rom


@screen("story_pre_zoo", "Story", "Story scene: the zoo's PRE scene (Kiki)")
def _(model):
    import test_story as TS
    from test_scores import v7_image
    rom = TS.start_story(model, v7_image([], story=8), cont=True)
    TS.page_ready(rom)
    return rom


@screen("story_goal", "Story", "Story: a chapter's goal banner")
def _(model):
    import test_story as TS
    return TS.to_chapter(model, 0, banner=True)


@screen("story_finale_a", "Story", "Story picture: FINALE A (before the Pour-Off)")
def _(model):
    import test_story_pictures as TP
    import test_story as TS
    rom = TP.to_finale(model)
    TS.page_ready(rom)
    return rom


@screen("story_finale_b", "Story", "Story picture: FINALE B (after the Pour-Off)")
def _(model):
    import test_story_pictures as TP
    import test_story as TS
    rom = TP.to_finale(model)
    TS.through_the_pouroff(rom)
    TS.page_ready(rom)
    return rom


# ---- credits ---------------------------------------------------------------------------------------------------------------------
def credits(card=None, frame=None):
    def fn(model):
        import test_credits as T
        rom = booted(model)
        rom.write("sound_on", 0)
        CF.title_pick(rom, K_BONUS, CF.K_CREDITS)
        for _ in range(20):
            if rom.mem("story_phase") == T.SP_CREDITS:
                break
            rom.run(1)
        rom.run(2)
        T.at(rom, T.CARD_START[card] + 5 if card is not None else frame)
        return rom
    return fn


screen("credits_title", "Credits", "Credits: CAST OF CHARACTERS title card", window=120)(credits(0))
screen("credits_spigoteer", "Credits", "Credits: Sal Tapley card", window=120)(credits(1))
screen("credits_dregs", "Credits", "Credits: Dregs card", window=120)(credits(2))
screen("credits_owner", "Credits", "Credits: a venue owner's card (the saloon)", window=120)(credits(3))
screen("credits_patrons", "Credits", "Credits: a venue's three patrons (the saloon)", window=120)(credits(4))
screen("credits_boss", "Credits", "Credits: a venue's boss (Big Tex)", window=120)(credits(5))


def credits_roll(stage):
    def fn(model):
        import test_credits as T
        rom = credits(frame=T.ROLL + 12)(model)
        rom.run(70)
        for f in range(T.ROLL_START, T.ROLL_START + 90, 2):
            T.set_t(rom, f)
            rom.run(1)
        if stage == "top":
            for _ in range(40):
                if T.scroll(rom) >= 45:
                    break
                rom.run(1)
            return rom
        for f in range(T.ROLL_START + 100, T.ROLL_START + 900, 2):
            T.set_t(rom, f)
            rom.run(1)
        if stage == "robots":
            for _ in range(400):
                if T.scroll(rom) >= 170:
                    break
                rom.run(1)
            return rom
        for f in range(T.ROLL_START + 900, T.SCROLL_END + 40, 2):
            T.set_t(rom, f)
            rom.run(1)
        rom.run(10)
        return rom
    return fn


screen("credits_roll", "Credits", "Credits: the roll, top", window=120)(credits_roll("top"))
screen("credits_roll_robots", "Credits", "Credits: the roll, the robots walk by", window=120)(credits_roll("robots"))
screen("credits_last", "Credits", "Credits: THANKS FOR PLAYING", window=120)(credits_roll("last"))


# ---- the Pour-Off, flow screens, debug menu ---------------------------------------------------------------------------------------
@screen("pouroff_intro", "Other", "The Pour-Off: intro banner", window=120)
def _(model):
    import test_pouroff as T
    return T.enter(model)


@screen("pouroff", "Other", "The Pour-Off: Sal against Dregs")
def _(model):
    import test_pouroff as T
    rom = T.start(model)
    m = Mash(rom)
    for _ in range(60):
        m.step()
        rom.run(1)
    return rom, m.step


def _game_over(model, score=0):
    import test_scores as T
    rom = booted(model)
    T.game_over_with(rom, score)
    rom.run(10)
    return rom


@screen("game_over", "Other", "Game over", window=120)
def _(model):
    return _game_over(model, 10)


@screen("life_lost", "Other", "Life lost (the patron reached the tap)", window=120)
def _(model):
    import test_flow as TF
    rom = level_rom(model, 0)
    rom.run(60)
    TF.lose_a_life(rom)
    rom.run(20)
    return rom


@screen("level_clear", "Other", "Level clear (ARCADE)", window=150)
def _(model):
    import test_flow as TF
    import test_story as TS
    rom = level_rom(model, 0)
    p = Play(rom)
    p.run(300)
    TS.clear_bars(rom)
    TF.run_until(rom, lambda: TF.state(rom) == TF.LEVEL_CLEAR, 60)
    rom.run(10)
    return rom


@screen("high_scores", "Other", "High scores table (after a top-5 game over)", window=120)
def _(model):
    import test_scores as T
    import test_flow as TF
    rom = booted(model)
    T.game_over_with(rom, 123456)
    for _ in range(900):
        if TF.state(rom) == T.GS_SCORES:
            break
        if TF.state(rom) == T.GS_INITIALS:
            rom.press("a", 2)
            rom.run(4)
        rom.run(1)
    rom.run(30)
    return rom


@screen("initials", "Other", "Initials entry (top-5 score)", window=120)
def _(model):
    import test_scores as T
    import test_flow as TF
    rom = booted(model)
    T.game_over_with(rom, 123456)
    for _ in range(900):
        if TF.state(rom) == T.GS_INITIALS:
            break
        rom.run(1)
    rom.run(30)
    return rom


@screen("mg_result", "Other", "Mini-game result screen (Quick Draw)", window=120)
def _(model):
    import test_mg as T
    rom = booted(model)
    T.mg_enter(rom, 0, T.MG_PRACTICE)
    for _ in range(600):
        if rom.mem("mg_phase") == T.MG_PLAY:
            break
        rom.run(1)
    rom.run(20)
    rom.write("mg_score", 900)
    rom.write("mg_phase", T.MG_RESULT)
    rom.run(80)
    return rom


@screen("mg_intro", "Other", "Mini-game intro banner (Quick Draw)", window=90)
def _(model):
    import test_mg as T
    rom = booted(model)
    T.mg_enter(rom, 0, T.MG_PRACTICE)
    return rom


@screen("debug_menu", "Other", "Debug menu (unlocked)", window=90)
def _(model):
    import test_debug as T
    rom = booted(model)
    T.combo(rom)
    T.release_combo(rom)
    rom.run(5)
    return rom


def boss_entrance(c):
    def fn(model):
        import boss_common as BC
        rom = BC.fight(model, c, entrance=True)
        rom.write("tip_chance", 0)
        return rom
    return fn


for _c, _n in enumerate(BOSS_NAMES):
    screen("bossin_%d" % (_c + 1), "Boss entrances", "%d. %s: entrance (%s)" % (_c + 1, _n, GROUPS[_c]))(boss_entrance(_c))


def story_level(c):
    def fn(model):
        import test_story as TS
        rom = TS.to_chapter(model, c)
        rom.write("tip_chance", 255)
        p = BossPlay(rom)
        for _ in range(300):
            p.step()
            rom.run(1)
        return rom, p.step
    return fn


screen("story_level_saloon", "Story", "Story level: the saloon's Opening (goal in the HUD)")(story_level(0))
screen("story_level_bistro", "Story", "Story level: the bistro's Opening (goal in the HUD)")(story_level(3))
