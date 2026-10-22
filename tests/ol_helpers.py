# Reading the three one-line menus (src/oneline.h; BONUS > SOUNDTRACK, MINI GAMES, BOSS RUSH's list) off the screen: the tilemap decoded to text, the
# selection line's arrows, the hint row, the key-repeat probe. Shared by tests/test_jukebox.py, test_mg_list.py, test_rush.py and test_oneline.py.
import re

from conftest import ROOT
from test_flow import tilemap_row

ART_H = (ROOT / "build" / "art.h").read_text()
STORY_H = (ROOT / "build" / "story.h").read_text()
GLYPH_CH = {int(m[1]): m[0] for m in re.findall(r"#define TILE_GLYPH_(\w) (\d+)", ART_H)}
BLANK = int(re.search(r"#define TILE_HUD_BLANK (\d+)", ART_H).group(1))
PANEL_TOP = int(re.search(r"#define TILE_PANEL_TOP (\d+)", ART_H).group(1))
PANEL_BOT = int(re.search(r"#define TILE_PANEL_BOT (\d+)", ART_H).group(1))
FONT = int(re.search(r"#define BAR_TILE_COUNT (\d+)", ART_H).group(1))      # STORY_FONT_BASE
for _n, _o in (("ST_GLYPH_PERIOD", 0), ("ST_GLYPH_COMMA", 1), ("ST_GLYPH_EXCL", 2), ("ST_GLYPH_QUEST", 3), ("ST_GLYPH_APOS", 4), ("ST_GLYPH_HYPHEN", 5),
               ("ST_GLYPH_COLON", 6), ("ST_FRAME_TL", 7)):
    assert f"#define {_n} (STORY_FONT_BASE + {_o})" in STORY_H, _n
PUNCT = {FONT: ".", FONT + 1: ",", FONT + 2: "!", FONT + 3: "?", FONT + 4: "'", FONT + 5: "-", FONT + 6: ":"}
KEY_A, KEY_B = FONT + 7, FONT + 8                  # the hint row's A and B buttons
OL_T = 4                                           # src/oneline.h: BG ids of the shared tiles, OL_T + n
ARROW_L, ARROW_R, ARROW_L_OUT, ARROW_R_OUT = OL_T, OL_T + 1, OL_T + 2, OL_T + 3
FILL = OL_T + 4                                    # + 0..8: a bar with that many pixels filled
BOX = OL_T + 13                                    # + 0..7: the frame's edges
BACK = OL_T + 21
SLASH = OL_T + 22
ICON = OL_T + 23                                   # + 0..3
ROW_BAND, ROW_HINT, SEP = 3, 16, 15
SKIN_MEDAL = 1                                     # src/game.h SKIN_TILE_MEDAL + the medal: 1 bronze, 2 silver, 3 gold
MEDAL_WORD = {SKIN_MEDAL: "BRONZE", SKIN_MEDAL + 1: "SILVER", SKIN_MEDAL + 2: "GOLD"}


def tile_char(t):
    if t == BLANK:
        return " "
    if t == SLASH:
        return "/"
    if t == KEY_A:
        return "@"
    if t == KEY_B:
        return "$"
    return GLYPH_CH.get(t) or PUNCT.get(t) or "~"


def text(gb, row, x0=0, n=20):
    """A screen row as text, trailing blanks stripped ('@' and '$' the A and B buttons, '~' a tile that is not a letter)."""
    return "".join(tile_char(t) for t in tilemap_row(gb, row, x0, n)).rstrip()


def header(gb):
    return text(gb, 0)


def header_text(title, counter=""):
    """What the header row reads: the title from column 1 and the counter ending in column 18 (the row is read back right-stripped)."""
    row = [" "] * 20
    row[1:1 + len(title)] = title
    if counter:
        row[19 - len(counter):19] = counter
    return "".join(row).rstrip()


def selection(gb):
    """The selection line's name (row 3, columns 1-18)."""
    return text(gb, ROW_BAND, 1, 18).strip()


def arrows(gb):
    """(left, right): the arrows' tiles on row 3, columns 0 and 19."""
    t = tilemap_row(gb, ROW_BAND, 0, 20)
    return t[0], t[19]


def arrows_out(gb):
    """(left out, right out): an arrow is out while the bob is out and for a few frames after a press on its side."""
    l, r = arrows(gb)
    assert l in (ARROW_L, ARROW_L_OUT) and r in (ARROW_R, ARROW_R_OUT), (l, r)
    return l == ARROW_L_OUT, r == ARROW_R_OUT


def hint(gb):
    return text(gb, ROW_HINT).strip()


def band_rows_ok(gb):
    """Rows 2 and 4 are the panel's light lines, rows 1 and 5 are not."""
    return set(tilemap_row(gb, 2, 0, 20)) == {PANEL_TOP} and set(tilemap_row(gb, 4, 0, 20)) == {PANEL_BOT}


def attr(gb, row, col):
    """The CGB palette of a BG cell."""
    return gb.pb.memory[1, 0x9800 + row * 32 + col] & 7


def hold_changes(gb, button, var, frames, clock=None):
    """Press `button` and hold it for `frames` frames: when the byte `var` changed, as the frame number counted from the press (the first frame 0), or, with
    `clock` (the address of a byte the game counts a frame in), as that byte's value mod 256 (the game's own frames: an emulator frame can hold none)."""
    seen, last = [], gb.mem(var)
    gb.pb.button_press(button)
    for f in range(frames):
        gb.pb.tick(1, False)
        v = gb.mem(var)
        if v != last:
            seen.append(f if clock is None else gb.mem(clock))
            last = v
    gb.pb.button_release(button)
    gb.pb.tick(2, False)
    return seen
