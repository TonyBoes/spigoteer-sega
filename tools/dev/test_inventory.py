#!/usr/bin/env python3
"""Read-only inventory of tests/: per file lines, test functions, parametrised case estimate, skip/xfail markers,
ROM symbols read (first string argument of gb.addr/mem/read*/write*/word...) that are missing from build/game.noi,
golden names used.  Writes JSON + a text table under out/ only.   usage: tools/dev/test_inventory.py"""
import ast, json, re, pathlib, collections

ROOT = pathlib.Path(__file__).resolve().parents[2]
TESTS = ROOT / "tests"
OUT = ROOT / "out"
OUT.mkdir(exist_ok=True)

noi = set()
for l in (ROOT / "build" / "game.noi").read_text().splitlines():
    p = l.split()
    if len(p) >= 3 and p[0] == "DEF":
        noi.add(p[1]); noi.add(p[1].lstrip("_"))
SYMFUNCS = {"addr", "mem", "mem16", "word", "read", "write", "write16", "peek", "poke", "sym", "label", "get", "put", "wait_until", "bank_of"}
IDENT = re.compile(r"^[A-Za-z_][A-Za-z_0-9]*$")


def lit_len(node):
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return len(node.elts)
    if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "range" and all(isinstance(a, ast.Constant) for a in node.args):
        a = [x.value for x in node.args]
        return len(range(*a))
    return None


def cases(fn):
    n = 1
    for d in fn.decorator_list:
        if isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr == "parametrize" and len(d.args) >= 2:
            l = lit_len(d.args[1])
            n *= l if l else 1
    return n


rows = []
fixture_params = {}
for f in sorted(TESTS.glob("*.py")):
    src = f.read_text()
    tree = ast.parse(src)
    r = dict(file=f.name, lines=src.count("\n") + 1, tests=0, cases=0, skips=[], xfails=[], missing=[], goldens=[])
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            r["tests"] += 1
            r["cases"] += cases(node)
            for d in node.decorator_list:
                s = ast.unparse(d)
                if "skip" in s and "mark" in s:
                    r["skips"].append((node.lineno, node.name, s[:140]))
                if "xfail" in s:
                    r["xfails"].append((node.lineno, node.name, s[:140]))
        if isinstance(node, ast.Call):
            fn = node.func
            nm = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
            if nm in ("skip", "importorskip") and isinstance(fn, ast.Attribute):
                r["skips"].append((node.lineno, "runtime", ast.unparse(node)[:140]))
            if nm in SYMFUNCS and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                v = node.args[0].value
                if IDENT.match(v) and v not in noi and len(v) > 2:
                    r["missing"].append((node.lineno, v))
    r["goldens"] = sorted(set(re.findall(r"""(?:golden|shot|golden_screen)\w*\(\s*(?:gb\s*,\s*)?f?["']([\w{}\-.]+)["']""", src)))
    rows.append(r)

(OUT / "inventory.json").write_text(json.dumps(rows, indent=1))
tot = collections.Counter()
lines = []
for r in sorted(rows, key=lambda r: -r["lines"]):
    lines.append(f"{r['lines']:6d} {r['tests']:4d} {r['cases']:5d} sk={len(r['skips']):3d} xf={len(r['xfails'])} miss={len(r['missing']):3d} {r['file']}")
    tot.update(lines=r["lines"], tests=r["tests"], cases=r["cases"])
(OUT / "inventory.txt").write_text("\n".join(lines) + f"\nTOTAL {dict(tot)}\n")
print("\n".join(lines[:200]))
print("TOTAL", dict(tot))
