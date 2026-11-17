# The credits generator must give the same files from the same sources, whatever Python's string hash is (a frozenset of colours iterated in hash order once
# decided which palette entry a colour got: two builds of the same sources differed, and so did the roll's faults). `make verify FULL=1` compares ROM sha1s.
import os
import subprocess
import sys

import pytest

from conftest import ROOT

CONFIGS = {
    "default": {},
    "split": {"CRFLOW": "SMOOTH", "CRSCENE": "1", "CRSPLIT": "1", "CRART": "18"},
}


def gen(tmp, name, seed, env):
    out = tmp / name
    out.mkdir()
    e = dict(os.environ, PYTHONHASHSEED=str(seed), **env)
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "gen_credits.py"), str(out)], cwd=ROOT, env=e, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-1500:] + r.stderr[-1500:]
    return {p.name: p.read_bytes() for p in sorted(out.iterdir())}


@pytest.mark.parametrize("cfg", sorted(CONFIGS))
def test_the_credits_generator_is_the_same_under_any_hash_seed(tmp_path, cfg):
    a = gen(tmp_path, "a", 1, CONFIGS[cfg])
    b = gen(tmp_path, "b", 777, CONFIGS[cfg])
    assert sorted(a) == sorted(b)
    assert [n for n in a if a[n] != b[n]] == []
