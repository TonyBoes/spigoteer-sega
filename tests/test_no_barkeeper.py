# The hero is Sal Tapley, the Spigoteer. The word for his job that the owner dropped (bartender, barkeep, barman, barmaid)
# must not reach the player: not in the story pages, cards, menus or any other string the build emits. Code identifiers and
# comments (bartender_x, BT_IDLE, ...) are internal and are not scanned.
import json
import re

from conftest import ROOT

BANNED = re.compile(r"BAR[ -]?(TEND|KEEP|MAN|MAID)", re.I)
STR = re.compile(r'"((?:[^"\\\n]|\\.)*)"')
COMMENT = re.compile(r"//[^\n]*|/\*.*?\*/|^[ \t]*#error[^\n]*", re.S | re.M)   # (#error is a build-time message, not on screen)


def literals(path):
    text = COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), path.read_text(errors="replace"))
    return [m.group(1) for m in STR.finditer(text)]


def walk(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for k, v in o.items():
            yield from walk(k)
            yield from walk(v)
    elif isinstance(o, list):
        for v in o:
            yield from walk(v)


def test_no_banned_word_in_source_or_generated_strings():
    bad = []
    for d in (ROOT / "src", ROOT / "build"):
        for f in sorted(list(d.glob("*.c")) + list(d.glob("*.h"))):
            bad += [(f.name, s) for s in literals(f) if BANNED.search(s)]
    assert not bad, bad


def test_no_banned_word_in_story_tables():
    story = json.loads((ROOT / "build" / "story.json").read_text())
    bad = [s for s in walk(story) if BANNED.search(s)]
    assert not bad, bad


def test_no_banned_word_in_the_script_or_the_rom():
    assert not BANNED.search((ROOT / "docs" / "story.md").read_text()), "docs/story.md (the script the pages are built from)"
    rom = (ROOT / "build" / "game.gb").read_bytes()
    assert not re.search(rb"BAR[ -]?(TEND|KEEP|MAN|MAID)", rom, re.I), "ASCII in the ROM"
