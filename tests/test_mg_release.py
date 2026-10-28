"""The Practice list entry of each venue mini-game, one table for all eight (they were eight copies of the same two tests).

(game, list position, list name, the HUD title in play, medal the release block gives it). The list is in chapter order
(docs/story.md); the debug build has every game unlocked, the release build lists a game only once STORY or ARCADE reached it."""
import pytest
from test_flow import run_until, state
from test_mg import GS_MGLIST, GS_MINI, MG_PRACTICE, MG_RESULT, frames, score, text
from test_mg_list import MG_PLANNED, medal_word, pr_block, release_rom, selection, tap as list_tap, to_game, to_list, with_block
from test_scores import booted, v7_image

pytestmark = pytest.mark.timeout(300)

MEDAL_SILVER, MEDAL_GOLD = 2, 3
#          id  list name           HUD title            release medal
GAMES = [(1, "SHIRT CANNON",    "SHIRT CANNON",      MEDAL_SILVER),
         (2, "LOG ROLL",        "LOG ROLL",          MEDAL_SILVER),
         (4, "MARSHMALLOWS",    "MARSHMALLOW DROP",  MEDAL_SILVER),
         (5, "BATTERY SORT",    "BATTERY SORT",      MEDAL_GOLD),
         (6, "MILK RUN",        "MILK RUN",          MEDAL_SILVER),
         (7, "TAIKO POUR",      "TAIKO POUR",        MEDAL_SILVER),
         (8, "MONKEY BUSINESS", "MONKEY BUSINESS",   MEDAL_SILVER),
         (9, "ASTEROIDS",       "ASTEROID DELIVERY", MEDAL_SILVER)]
IDS = [g[1].replace(" ", "_") for g in GAMES]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("gid,name,title,medal", GAMES, ids=IDS)
def test_bonus_mini_games_lists_and_plays_it(model, gid, name, title, medal):
    """BONUS > MINI GAMES (the debug build: all unlocked): the game on its line (chapter order); A plays it in practice
    (score from 0); its result's B comes back to the list on it."""
    with to_list(booted(model)) as gb:
        to_game(gb, gid)
        assert gb.mem("ml_sel") == gid
        list_tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_MINI and gb.pb.memory[0xFF40] & 0x80, 30)
        assert gb.mem("mg_id") == gid and gb.mem("mg_mode") == MG_PRACTICE and score(gb) == 0
        assert text(gb, 2) == title
        gb.write("mg_phase", MG_RESULT)
        run_until(gb, lambda: gb.mem("overlay_on") == 1, 10)
        frames(gb, 3)
        gb.press("b", 2)
        run_until(gb, lambda: state(gb) == GS_MGLIST and gb.pb.memory[0xFF40] & 0x80, 30)
        gb.run(3)
        assert gb.mem("ml_sel") == gid and selection(gb) == name


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("gid,name,title,medal", GAMES, ids=IDS)
def test_the_release_list_unlocks_it_when_reached(model, gid, name, title, medal, release_built):
    """`make release`: the game is "? ? ?" until STORY or ARCADE reached it; with its bit (and a best medal) in Practice's
    block it lists by name with the medal and plays."""
    best = [0] * MG_PLANNED
    best[gid] = medal
    ram = with_block(v7_image(), pr_block(1 << gid, best))
    with release_rom(model, ram) as gb:
        to_list(gb)
        assert selection(gb) == "? ? ?"
        to_game(gb, gid)
        assert (selection(gb), medal_word(gb)) == (name, {MEDAL_SILVER: "SILVER", MEDAL_GOLD: "GOLD"}[medal])
        list_tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_MINI, 30)
        assert gb.mem("mg_id") == gid and gb.mem("mg_mode") == MG_PRACTICE
