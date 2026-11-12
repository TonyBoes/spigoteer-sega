#!/usr/bin/env python3
"""DMG / Color equivalence checker for the test suite: which doubled tests may run on one model only.

A test is DOUBLED when it uses the `boot` fixture (tests/conftest.py: params dmg, cgb). It may go single-model
(`@pytest.mark.only_model('dmg')`) only when it is PROVEN model-independent. The proof, per test, has four parts:

  1. outcome     both instances pass.
  2. assertions  the assertions that passed (pytest_assertion_pass: source line + the evaluated values) are identical, in order.
  3. reads       per memory location / slice / screen the test read, the sequence of distinct values seen is identical
                 (consecutive repeats collapsed: a polling loop that needs one frame more on one model still agrees; the Color
                 boot is one frame out of phase, which is why raw read counts differ).
  4. final       the bytes at every location the test read are equal at the end of the test (a hash of the relevant WRAM/HRAM).
                 The whole-WRAM difference (is_cgb, sys_time, shadow OAM ...) is listed by `report` for information only.
  5. static      the test, the helpers it calls (same file, tests/*_helpers, conftest fixtures, transitively) and its fixtures
                 mention no model signal (is_cgb, model_name, 'cgb'/'dmg' compared, palette, golden, perf, double_speed, the
                 PERF_DS list ...). Harmless harness hits are waived in WAIVE, each with a reason.

Any doubt keeps both models. A function is eligible only if EVERY parametrised instance of it is.

    tools/dev/model_equiv.py run [pytest args]    run the suite (8 shards, tools/dev/ptest.py) with the recorder -> out/equiv/data
    tools/dev/model_equiv.py report               verdict table: eligible / kept, with the reason per kept test -> out/equiv/report.json
    tools/dev/model_equiv.py apply [--tier A,B,C] add the marker to the eligible tests (module level when the whole file is eligible)

The recorder is also a pytest plugin: `EQUIV_DIR=out/equiv/data PYTHONPATH=tools/dev pytest -p model_equiv ...`.
Re-run after any change to the game: the proof is about the ROM it ran on.
"""
import ast
import base64
import hashlib
import json
import os
import re
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "out" / "equiv"
DATA = Path(os.environ.get("EQUIV_DIR") or OUT / "data")

# Identifiers and string constants that mean "this code looks at the hardware model, colour, speed or timing".
SIGNAL = re.compile(
    r"is_cgb|model_name|^cgb|^dmg|_cgb|_dmg|palette|bcps|bcpd|ocps|ocpd|^bgp|^obp|_bgp|_obp|vram_bank|vbk|svbk|bank1|golden|screenshot|\.png"
    r"|perf(?!ect)|missed|drain|budget|double_speed|speed_off|key1|lateness|_late|cycles|register_file|hook_register"
    r"|_pal$|^pal_|^pal$|(?:^|_)colou?r(?:_|$)|grey|gray|cell_pal|^rgb|gba_hardware|\bmodel\b == |is_color", re.I)
MODEL_NAMES = {"model", "model_name"}
# Signals read and judged harmless; each is a harness that does not branch on the model.
WAIVE = {
    "hook_register@mg_enter", "register_file@mg_enter",     # tests/test_mg.py mg_enter: a PyBoy hook diverts the CPU once to call mg_enter (same bytes on both models)
}


def _signals_of(tree):
    """Model-looking things in one function's AST: names / attributes / string constants matching SIGNAL, a literal 'dmg'/'cgb'
    that is compared or used as a dict key, and a subscript indexed by the model. A model merely passed through is no signal."""
    hits = set()
    passthru = {id(k.value) for n in ast.walk(tree) if isinstance(n, ast.Call) for k in n.keywords if k.arg == "cgb"}   # PyBoy(cgb=(model == "cgb"))
    for n in ast.walk(tree):
        if id(n) in passthru:
            continue
        if isinstance(n, ast.Name):
            toks = [n.id]
        elif isinstance(n, ast.Attribute):
            toks = [] if (n.attr == "model_name" and isinstance(n.ctx, ast.Store)) else [n.attr]
        elif isinstance(n, ast.arg):
            toks = [n.arg]
        elif isinstance(n, ast.Constant) and isinstance(n.value, str) and len(n.value) < 60:
            toks = [n.value]
        else:
            toks = []
        for t in toks:
            m = SIGNAL.search(t)
            if m and t not in ("dmg", "cgb"):
                hits.add(t)
        if isinstance(n, ast.Compare):
            for x in [n.left] + n.comparators:
                if isinstance(x, ast.Constant) and x.value in ("dmg", "cgb"):
                    hits.add(f"=={x.value}")
                if isinstance(x, (ast.Tuple, ast.List, ast.Set)) and any(isinstance(e, ast.Constant) and e.value in ("dmg", "cgb") for e in x.elts):
                    hits.add("in (dmg,cgb)")
        if isinstance(n, ast.Dict) and any(isinstance(k, ast.Constant) and k.value in ("dmg", "cgb") for k in n.keys):
            hits.add("dict by model")
        if isinstance(n, ast.Subscript):
            sl = n.slice
            if (isinstance(sl, ast.Name) and sl.id in MODEL_NAMES) or (isinstance(sl, ast.Attribute) and sl.attr in MODEL_NAMES):
                hits.add("indexed by model")
        if isinstance(n, ast.IfExp) and isinstance(n.test, ast.Name) and n.test.id in MODEL_NAMES:
            hits.add("if model")
        if isinstance(n, (ast.If, ast.While)) and isinstance(n.test, ast.Name) and n.test.id in MODEL_NAMES:
            hits.add("if model")
    return hits


# ---------------------------------------------------------------------------------------------------------- recorder


class _Trace:
    """What one test observed: per read location the sequence of distinct values it saw (consecutive repeats collapsed, so a polling
    loop that needs one frame more on one model still reads the same), the assertions that passed (with their evaluated values),
    and, per Rom, the final bytes at every location it read."""

    def __init__(self):
        self.seq = {}
        self.asserts = []
        self.roms = []        # one per Rom stopped during the test
        self.paused = 0
        self.n = 0

    def add(self, tag, val):
        if self.paused:
            return
        self.n += 1
        lst = self.seq.setdefault(tag, [])
        if not lst or lst[-1] != val:
            lst.append(val)

    def digest(self):
        h = hashlib.sha1()
        for k in sorted(self.seq):
            h.update(f"{k}:{self.seq[k]!r};".encode())
        return h.hexdigest()

    def assert_digest(self):
        return hashlib.sha1("\n".join(self.asserts).encode()).hexdigest()


_cur = None


class _MemView:
    def __init__(self, mem):
        self._m = mem

    def __getitem__(self, k):
        v = self._m[k]
        if _cur is not None:
            if isinstance(k, slice):
                _cur.add(f"m[{k.start!r}:{k.stop!r}]", hashlib.sha1(bytes(v)).hexdigest()[:12])
            elif isinstance(k, int):
                _cur.add(f"m[{k:#x}]", v)
            else:
                _cur.add(f"m[{k!r}]", v if isinstance(v, (int, float, str)) else hashlib.sha1(bytes(v)).hexdigest()[:12])
        return v

    def __setitem__(self, k, v):
        self._m[k] = v
        if _cur is not None:
            _cur.add("w", (k if isinstance(k, int) else str(k), v if isinstance(v, int) else "seq"))


class _PbProxy:
    def __init__(self, pb):
        object.__setattr__(self, "_pb", pb)
        object.__setattr__(self, "_mv", _MemView(pb.memory))

    @property
    def memory(self):
        return self._mv

    def __getattr__(self, name):
        v = getattr(self._pb, name)
        return v

    def __setattr__(self, name, v):
        setattr(self._pb, name, v)


def _partition_hash(im):
    """A screen as its pattern of equal pixels (first-occurrence relabelling): the same on DMG greys and Color tints."""
    import numpy as np
    a = np.asarray(im.convert("RGB")).reshape(-1, 3)
    key = (a[:, 0].astype(np.uint32) << 16) | (a[:, 1].astype(np.uint32) << 8) | a[:, 2]
    _, first, inv = np.unique(key, return_index=True, return_inverse=True)
    order = np.argsort(np.argsort(first))
    return hashlib.sha1(order[inv].astype(np.uint16).tobytes()).hexdigest()[:12]


def _sym_table(rom):
    tab = sorted((a, n) for n, (b, a) in rom.symbols.items() if a >= 0xC000 and not n.startswith("."))
    return tab


def _install():
    from gbtools import Rom
    if getattr(Rom, "_equiv", False):
        return
    Rom._equiv = True
    stop, image = Rom.stop, Rom.image

    def _get(self):                                          # (tests also assign rom.pb: keep the raw object, hand out the recording proxy)
        raw = self.__dict__.get("_pb_raw")
        if raw is None:
            return None
        px = self.__dict__.get("_pb_px")
        if px is None or px._pb is not raw:
            px = self.__dict__["_pb_px"] = _PbProxy(raw)
        return px

    def _set(self, v):
        self.__dict__["_pb_raw"] = v
        self.__dict__["_pb_px"] = None

    def _stop(self):
        if _cur is not None and self.pb is not None and not getattr(self, "_eq_done", False):
            self._eq_done = True
            _cur.paused += 1
            try:
                m = self.__dict__["_pb_raw"].memory
                raw = bytes(m[0xC000:0xE000]) + bytes(m[0xFE00:0xFEA0]) + bytes(m[0xFF80:0xFFFF])
                fin = {}
                for tag in list(_cur.seq)[:3000]:                # the final bytes at every location the test read
                    mm = re.match(r"m\[(0x[0-9a-f]+)\]$", tag)
                    sl = re.match(r"m\[(\d+):(\d+)\]$", tag)
                    if mm:
                        fin[tag] = m[int(mm.group(1), 16)]
                    elif sl:
                        fin[tag] = hashlib.sha1(bytes(m[int(sl.group(1)):int(sl.group(2))])).hexdigest()[:12]
                _cur.roms.append({"model": self.model, "state": base64.b64encode(zlib.compress(raw, 6)).decode(), "final": fin})
                if "symtab" not in _cur.__dict__:
                    _cur.symtab = _sym_table(self)
            finally:
                _cur.paused -= 1
        stop(self)

    def _image(self):
        im = image(self)
        if _cur is not None:
            _cur.add("screen", _partition_hash(im))
        return im

    run = Rom.run

    def _run(self, *a, **k):                                 # (conftest's run wrapper reads frame_counter to place the boot: not the test's read)
        if _cur is None:
            return run(self, *a, **k)
        _cur.paused += 1
        try:
            return run(self, *a, **k)
        finally:
            _cur.paused -= 1

    Rom.run = _run
    Rom.pb = property(_get, _set)
    Rom.stop, Rom.image = _stop, _image


def _callee_sources(func, seen, depth=0):
    """Signals of func and, through the names it uses, of every function it can call in tests/ (a list of (function name, signals))."""
    import inspect
    import types
    out = []
    if func in seen or depth > 6:
        return out
    seen.add(func)
    try:
        f = inspect.getsourcefile(func) or ""
        if "/tests/" not in f.replace("\\", "/"):
            return out
        tree = ast.parse(__import__("textwrap").dedent(inspect.getsource(func)))
    except (OSError, TypeError, SyntaxError):
        return out
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)) and n.body \
                and isinstance(n.body[0], ast.Expr) and isinstance(getattr(n.body[0], "value", None), ast.Constant) \
                and isinstance(n.body[0].value.value, str):
            n.body = n.body[1:] or [ast.Pass()]
    out.append((getattr(func, '__name__', '?'), _signals_of(tree)))
    g = getattr(func, "__globals__", {})
    code = getattr(func, "__code__", None)
    names = set()
    attrs = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Name):
            names.add(n.id)
        elif isinstance(n, ast.Attribute):
            attrs.add(n.attr)
    for nm in names:
        o = g.get(nm)
        if isinstance(o, types.FunctionType):
            out += _callee_sources(o, seen, depth + 1)
        elif isinstance(o, types.ModuleType) and "/tests/" in (getattr(o, "__file__", "") or "").replace("\\", "/"):
            for a in attrs:
                oo = getattr(o, a, None)
                if isinstance(oo, types.FunctionType):
                    out += _callee_sources(oo, seen, depth + 1)
    del code
    return out


def _static_signals(item):
    func = getattr(item, "function", None)
    if func is None:
        return ["no function"]
    seen = set()
    srcs = _callee_sources(func, seen)
    try:
        for name in item.fixturenames:
            if name in ("boot", "_perf_guards_at_double_speed"):    # the doubling itself; the autouse speed switch (checked below)
                continue
            for fd in item.session._fixturemanager.getfixturedefs(name, item) or []:
                srcs += _callee_sources(fd.func, seen)
    except Exception as e:                                   # noqa: BLE001  (a fixture we cannot read is a doubt)
        return [f"fixture scan failed: {e}"]
    out = {f"{h}@{fn}" for fn, hs in srcs for h in hs} - WAIVE
    cf = sys.modules.get("conftest")
    mod, fn = item.module.__name__.split(".")[-1], func.__name__
    ds = getattr(cf, "PERF_DS", {})
    if mod in ds and (ds[mod] is None or fn in ds[mod]):
        out.add("PERF_DS: the [cgb] instance runs at double speed")
    return sorted(out)


def pytest_configure(config):
    if True:
        names = [p.stem for p in (ROOT / "tests").glob("*.py") if not p.stem.startswith("test_") and p.stem != "conftest"]
        pytest.register_assert_rewrite(*names)               # (helpers' asserts count as the test's assertions)
        DATA.mkdir(parents=True, exist_ok=True)


import pytest  # noqa: E402


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    global _cur
    cs = getattr(item, "callspec", None)
    doubled = bool(cs) and any(v in ("dmg", "cgb") for v in cs.params.values())
    if not doubled:
        yield
        return
    _install()                                               # (after conftest has wrapped Rom itself)
    _cur = _Trace()
    item._equiv_outcome = {}
    sig = None
    try:
        sig = _static_signals(item)
    except Exception as e:                                   # noqa: BLE001
        sig = [f"static scan failed: {e}"]
    yield
    t, _cur = _cur, None
    rec = {"id": item.nodeid, "static": sig, "trace": t.digest(), "n": t.n, "asserts": t.assert_digest(), "na": len(t.asserts),
           "seq": {k: v[:10] for k, v in list(t.seq.items())[:300]}, "alist": t.asserts[:300],
           "outcome": item._equiv_outcome, "roms": t.roms}
    if not hasattr(sys.modules[__name__], "_symtab_saved") and getattr(t, "symtab", None):
        (DATA / "symtab.json").write_text(json.dumps(t.symtab))
        sys.modules[__name__]._symtab_saved = True
    with open(DATA / f"rec.{os.getpid()}.jsonl", "a") as f:
        f.write(json.dumps(rec) + "\n")


def pytest_assertion_pass(item, lineno, orig, expl):
    if _cur is not None:
        _cur.asserts.append(f"{item.module.__name__}:{lineno}:" + re.sub(r"0x[0-9a-f]{8,}", "0xADDR", expl)[:400])


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    out = yield
    rep = out.get_result()
    if hasattr(item, "_equiv_outcome"):
        item._equiv_outcome[rep.when] = rep.outcome


# ------------------------------------------------------------------------------------------------------------ report


def _key(nodeid):
    """Node id with the model token replaced, so the dmg and cgb instance of one test share a key."""
    m = re.search(r"\[([^\]]*)\]$", nodeid)
    if not m:
        return nodeid, None
    parts = m.group(1).split("-")
    for i, p in enumerate(parts):
        if p in ("dmg", "cgb"):
            model = p
            parts[i] = "@"
            return nodeid[:m.start()] + "[" + "-".join(parts) + "]", model
    return nodeid, None


def _load():
    recs = {}
    for p in sorted(DATA.glob("rec.*.jsonl")):
        for ln in p.read_text().splitlines():
            r = json.loads(ln)
            recs[r["id"]] = r                                 # a later run of the same id wins
    return recs


def _state_diff(ra, rb, symtab):
    """Symbols (WRAM/HRAM/OAM) whose bytes differ between two final states; list of names."""
    import bisect
    addrs = [a for a, _ in symtab]
    names = [n for _, n in symtab]
    layout = [(0xC000, 0xE000), (0xFE00, 0xFEA0), (0xFF80, 0xFFFF)]
    A = zlib.decompress(base64.b64decode(ra["state"]))
    B = zlib.decompress(base64.b64decode(rb["state"]))
    if len(A) != len(B):
        return ["<size>"]
    diff, off = set(), 0
    for lo, hi in layout:
        for i in range(hi - lo):
            if A[off + i] != B[off + i]:
                a = lo + i
                k = bisect.bisect_right(addrs, a) - 1
                diff.add(names[k] if k >= 0 and lo != 0xFE00 else f"<{a:#06x}>")
        off += hi - lo
    return sorted(diff)


def report():
    recs = _load()
    symtab = json.loads((DATA / "symtab.json").read_text()) if (DATA / "symtab.json").exists() else []
    groups = {}
    for i, r in recs.items():
        k, m = _key(i)
        groups.setdefault(k, {})[m] = r
    verdict = {}
    diffsyms = {}
    for k, g in groups.items():
        d, c = g.get("dmg"), g.get("cgb")
        if not d or not c:
            verdict[k] = ("keep", "only one model collected")
            continue
        why = []
        for r in (d, c):
            if r["outcome"].get("call") != "passed" or r["outcome"].get("setup") != "passed":
                why.append("not passed on both")
                break
        if not why:
            for r in (d, c):
                if r["static"]:
                    why.append("static: " + ",".join(r["static"][:4]))
                    break
        if not why and d["asserts"] != c["asserts"]:
            a, b = d["alist"], c["alist"]
            j = next((x for x in range(min(len(a), len(b))) if a[x] != b[x]), min(len(a), len(b)))
            why.append(f"assertions differ at #{j} ({(a[j] if j < len(a) else '-')[:90]} vs {(b[j] if j < len(b) else '-')[:90]})")
        if not why and d["trace"] != c["trace"]:
            ks = sorted(set(d["seq"]) | set(c["seq"]))
            loc = next((x for x in ks if d["seq"].get(x) != c["seq"].get(x)), "?")
            why.append(f"reads differ at {loc} ({d['seq'].get(loc)} vs {c['seq'].get(loc)})")
        if not why and d["na"] == 0 and d["n"] == 0:
            why.append("test observed nothing (no assertion, no read)")
        if not why:
            for x, y in zip(d["roms"], c["roms"]):
                if x["final"] != y["final"]:
                    kk = next(k for k in x["final"] if x["final"][k] != y["final"].get(k))
                    why.append(f"final value of a read location differs: {kk} ({x['final'][kk]} vs {y['final'].get(kk)})")
                    break
        if not why:
            if len(d["roms"]) != len(c["roms"]):
                why.append("different number of Roms")
            else:
                ds = set()
                for x, y in zip(d["roms"], c["roms"]):
                    ds |= set(_state_diff(x, y, symtab))
                for s in ds:                                 # (informational: unread state may differ, e.g. is_cgb itself)
                    diffsyms[s] = diffsyms.get(s, 0) + 1
        verdict[k] = ("keep", "; ".join(why)) if why else ("eligible", "")
    # a function is eligible only when every one of its instances is
    byfunc = {}
    for k, (v, why) in verdict.items():
        fn = k.split("[")[0]
        byfunc.setdefault(fn, []).append((k, v, why))
    func_ok = {fn: all(v == "eligible" for _, v, _ in L) for fn, L in byfunc.items()}
    res = {"verdict": {k: list(v) for k, v in verdict.items()}, "func_eligible": func_ok, "diff_symbols": diffsyms}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report.json").write_text(json.dumps(res, indent=1))
    ne = sum(1 for v, _ in verdict.values() if v == "eligible")
    print(f"pairs {len(verdict)}  eligible pairs {ne}  eligible functions {sum(func_ok.values())}/{len(func_ok)}")
    reasons = {}
    for k, (v, why) in verdict.items():
        if v == "keep":
            reasons[why.split(":")[0].split(" at ")[0]] = reasons.get(why.split(":")[0].split(" at ")[0], 0) + 1
    for r, n in sorted(reasons.items(), key=lambda x: -x[1]):
        print(f"  kept  {n:5d}  {r}")
    print("symbols differing at the end of tests (count of pairs):")
    for s, n in sorted(diffsyms.items(), key=lambda x: -x[1])[:40]:
        print(f"  {n:5d}  {s}  ")
    return res


# -------------------------------------------------------------------------------------------------------------- apply

MARK = "@pytest.mark.only_model('dmg')"


def _file_funcs(path):
    src = path.read_text()
    tree = ast.parse(src)
    funcs = {}

    def visit(body, cls=None):
        for n in body:
            if isinstance(n, ast.ClassDef):
                visit(n.body, n.name)
            elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test"):
                funcs[(cls, n.name)] = n
    visit(tree.body)
    return src, tree, funcs


def apply(tiers=None):
    res = json.loads((OUT / "report.json").read_text())
    tier = {}
    md = ROOT / "docs/dev/notes/test_doubling_review_2026-11-12.md"
    for ln in md.read_text().splitlines():
        m = re.match(r"\| (test_\w+\.py) \|.*\| ([ABC]) \|", ln)
        if m:
            tier[m.group(1)] = m.group(2)
    byfile = {}
    for fn, ok in res["func_eligible"].items():
        f, _, name = fn.partition("::")
        byfile.setdefault(f, {})[name] = ok
    changed = {}
    for f, d in sorted(byfile.items()):
        if tiers and tier.get(Path(f).name, "?") not in tiers:
            continue
        if not any(d.values()):
            continue
        path = ROOT / f
        src, tree, funcs = _file_funcs(path)
        lines = src.split("\n")
        n_all = len(d)
        n_ok = sum(d.values())
        has_mark = "pytestmark" in src
        if n_ok == n_all and not has_mark:
            # module level: after the last top-level import / before first def; put it after the imports block
            at = 0
            for n in tree.body:
                if isinstance(n, (ast.Import, ast.ImportFrom)) or (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)):
                    at = n.end_lineno
            if "import pytest" not in src:
                lines.insert(at, "import pytest"); at += 1
            lines.insert(at, "pytestmark = pytest.mark.only_model('dmg')   # model_equiv.py: DMG and Color proven equal for every test here")
            path.write_text("\n".join(lines))
            changed[f] = (n_ok, "module")
            continue
        ins = []
        for name, ok in d.items():
            if not ok:
                continue
            base = name.split("::")[-1]
            hit = [(c, n) for (c, nm), n in funcs.items() if nm == base]
            if len(hit) != 1:
                continue
            n = hit[0][1]
            first = min([n.lineno] + [x.lineno for x in n.decorator_list])
            ins.append((first, " " * n.col_offset + MARK))
        for ln_no, text in sorted(ins, reverse=True):
            lines.insert(ln_no - 1, text)
        if ins and "import pytest" not in src:
            lines.insert(0, "import pytest")
        path.write_text("\n".join(lines))
        changed[f] = (len(ins), "per-test")
    for f, (n, how) in changed.items():
        print(f"{f}: {n} functions ({how})")


# ---------------------------------------------------------------------------------------------------------------- cli


def main(argv):
    if not argv or argv[0] not in ("run", "report", "apply"):
        print(__doc__)
        return 2
    if argv[0] == "run":
        import shutil
        import subprocess
        shutil.rmtree(DATA, ignore_errors=True)
        DATA.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ, EQUIV_DIR=str(DATA), PYTHONPATH=f"{ROOT / 'tools' / 'dev'}:{os.environ.get('PYTHONPATH', '')}",
                   PYTEST_ADDOPTS="-p model_equiv -o enable_assertion_pass_hook=true " + os.environ.get("PYTEST_ADDOPTS", ""))
        return subprocess.call([sys.executable, str(ROOT / "tools/dev/ptest.py")] + argv[1:], cwd=ROOT, env=env)
    if argv[0] == "report":
        report()
        return 0
    tiers = None
    if "--tier" in argv:
        tiers = set(argv[argv.index("--tier") + 1].split(","))
    apply(tiers)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
