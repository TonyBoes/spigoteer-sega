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
    assert gm.STREAMED["map"] == gm.MAP_BANK == 25 and gm.TUNES[-1] == "map"
    data = (ROOT / "build" / "music_data.c").read_text()
    assert re.search(r"\{&song_map, 1, 8448, 3, 25, blob_map, 1536, groove_map, 0\}", data)
