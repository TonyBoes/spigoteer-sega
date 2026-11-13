# Music batch 5 as integrated: Swipesy (the story map's tune), then Easy Winners (the credits tune and the soundtrack-only fast one).
# The note data is the audition generator's output (rags_data on the audition branch) byte for byte: the digests below were taken from it.
import hashlib
import re
import sys

from conftest import ROOT

sys.path.insert(0, str(ROOT / "tools"))
import gen_music as gm       # noqa: E402
import harmony as H          # noqa: E402
import songs                 # noqa: E402


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def test_swipesy_is_the_audition_data():
    t = songs.SONGS["swipesy"]
    assert (digest(t["ch2"]), digest(t["ch3"]), digest(t["ch1"]), digest(t["groove"])) == (
        "b0a0575402f5ca07", "a584360df2954792", "d37fba6c73d0962e", "91e414673d80be96")
    assert t["tempo"] == 11 and t["ch1_inst"] == ("voice", "voice") and t["inst"] == gm.LEAD_PRO and not t["swing"] and not t["ch4"]
    assert H.nrows(t["ch2"]) == H.nrows(t["ch3"]) == H.nrows(t["ch1"]) == 768
    assert len(t["groove"].split()) == 32 and 768 % 32 == 0


def test_swipesy_in_the_rom_streams_like_the_title():
    b = gm.build("map", songs.SONGS["swipesy"], False)
    assert b["total"] == 768 and b["n_orders"] == 12 and gm.pass_frames(768, 11) == 8448
    assert gm.STREAMED["map"] == gm.MAP_BANK == 25 and gm.ORDER[15] == "map"
    data = (ROOT / "build" / "music_data.c").read_text()
    assert re.search(r"\{&song_map, 1, 8448, 3, 25, blob_map, 1536, groove_map, 0\}", data)


def test_easy_winners_credits_is_the_audition_data():
    t = songs.SONGS["credits"]
    assert (digest(t["ch2"]), digest(t["ch3"]), digest(t["ch1"]), digest(t["track"])) == (
        "9a02be46438aa14b", "cc1fa80ac108d1e1", "411c55059250a90d", "befc5a9b3c9e689e"), "rags_data.easywinners_credits_r5(join='pickup', bass='upper', voice='voice', lead='brass'); ch3 with the held bass"
    assert t["tempo"] == 15 and not t["groove"] and not t["swing"] and t["ch1_inst"] == ("voice", "ring50")
    assert H.nrows(t["ch2"]) == H.nrows(t["ch3"]) == H.nrows(t["ch1"]) == H.nrows(t["track"]) == 707
    assert gm.kick_body(t) == t["ch3"], "no kick body on this tune: its drums are a track, not a groove"


def test_the_fast_easy_winners_is_the_audition_data_and_only_in_the_soundtrack():
    t = songs.SONGS["ewfast"]
    assert (digest(t["ch2"]), digest(t["ch3"]), digest(t["ch1"]), digest(t["groove"])) == (
        "1e04557c442bbd32", "aceeb55c156bf318", "208074bfb2dc49fc", "3628231130946d9c"), "rags_data.easywinners_map()"
    assert t["tempo"] == 9 and t["swing"] == 0xAA and t["short_orders"] == (0, 7) and H.nrows(t["ch2"]) == 704
    b = gm.build("ewfast", t, False)
    assert b["total"] == 704 and b["n_orders"] == 12 and gm.pass_frames(704, 9, 0xAA) == 5984
    assert gm.ORDER[-3:] == ["map", "credits", "ewfast"] and gm.STREAMED["ewfast"] == 26
    # played nowhere in the game: only music.h names it (the soundtrack player starts tunes by their number)
    for f in (ROOT / "src").glob("*.c"):
        assert "TUNE_EWFAST" not in f.read_text(), f.name
