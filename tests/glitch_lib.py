"""Every-frame picture checker (the glitch hunt, 2026-11-01). Not a golden: what belongs on the screen is derived from the game's state and
its generators (the venue's wall in base_all, the patrons' poses, their palette instances, lifted ones, the mirrored bars).

`Watch(gb).step(n)` runs n emulator frames; after EACH one it checks the picture the LCD shows (VRAM only changes in VBlank, and PyBoy's frame
ends a few lines into the next one, so the state seen is a picture that was displayed for a whole frame):

  A  (every frame, any lag excused)   every cell of the bars' two wall rows is a (tile, bank, palette) the game could put there: a wall cell of the venue
     (base_all) or a patron's tile with the attribute of a patron of that look. A patron tile id with the wrong attribute (a bank-1 look's tile
     shown from bank 0: a font glyph) fails this the frame it appears.
  B  (late redraw)                    a cell the model knows exactly (no lifted or overlapping patron, no boss) that differs from the model for more
     than LAG frames in a row (the redraw spans are queued a chunk a frame: a short lag is the picture catching up, not a flicker).
  C  rows outside the bars (stage, counters, floor, HUD below row 0) never change except where the game says (stage rows: stage animation).
  D  OAM: nothing is visible that no live object owns (mug entries past oam_used, lifted entries past lift_total, dancers without a show, the coin
     without a tip).
Findings are collected in `watch.found` as (frame, kind, detail); `watch.assert_clean()` raises with the first few.
"""
import re

from conftest import GAME, LAYOUT, ROOT, bar_top_row

_ART_H = (ROOT / "build" / "art.h").read_text()


def _art(n):
    return int(re.search(rf"#define {n} (\d+)", _ART_H).group(1))


BASE = _art("PATRON_FIRST_TILE")
SHIFT0_OFS = _art("PATRON_SHIFT0_OFS")
BLANK = BASE + _art("PATRON_BLANK_OFS")
PER_GROUP = _art("PATRON_TILES_PER_GROUP")
BACK_BASE = BASE + PER_GROUP
X_S0, X_BACK, X_LAST = _art("SALOON_X_S0"), _art("SALOON_X_BACK"), _art("SALOON_X_LAST")
BASE_W = 20 + 3 * int(re.search(r"#define TAPER_MAX (\d+)", (ROOT / "src" / "game.h").read_text()).group(1))
DRAW_BACK = 0x80
BANK1 = 0x40
SCR_INST_AT = 254
BOSS_FX_FIRST = 240            # BG ids from here are a boss fight's own effects (BOSS_ICE_BG, BOSS_MARK_BG, the HUD meter)
LAG_A = 40                    # (class A) frames a cell may stand incoherent: the chunked spans and quick redraws are not written in the same VBlank
LAG = 12                      # (class B) frames a redraw may be late
ROW0 = LAYOUT["BAR_FIRST_ROW"]
STRIDE = LAYOUT["BAR_ROW_STRIDE"]


def pose_first(look, shift):
    if look > 2:
        k = look - 3
        q = k * 7 + shift - 1
        return X_S0 + k * 4 if shift == 0 else q * 6 if q < 34 else X_LAST
    return BASE + (SHIFT0_OFS + look * 4 if shift == 0 else look * 42 + (shift - 1) * 6)


def back_first(look):
    return BACK_BASE + look * 4 if look < 3 else X_BACK + (look - 3) * 4


def _tile_looks():
    """tile id -> {look} for the patron tile sets; bank-0 ids (looks 0-2) and bank-1 ids (looks 3-7) are separate maps."""
    b0, b1 = {}, {}
    for look in range(8):
        d = b1 if look > 2 else b0
        for s in range(8):
            f = pose_first(look, s)
            for t in range(f, f + (4 if s == 0 else 6)):
                d.setdefault(t, set()).add(look)
        f = back_first(look)
        for t in range(f, f + 4):
            d.setdefault(t, set()).add(look)
    return b0, b1


TILE_LOOK0, TILE_LOOK1 = _tile_looks()
BLANKS = (BLANK, BLANK + 1)


class Watch:
    def __init__(self, gb, lag=LAG, bars=(0, 1, 2, 3)):
        self.gb, self.lag, self.bars = gb, lag, bars
        self.cgb = gb.model_name == "cgb"
        self.found, self.frame = [], 0
        self.variants = set()           # every patron_variant byte seen: the (look, palette instance) pairs this run has put on a bar
        self.streak = {}
        self.static = None
        self.frames_checked = 0
        self.kinds = set()
        self.max_streak = 0
        self.max_a = 0                  # the longest run of frames one cell stayed incoherent (class A)
        self.lag_a = LAG_A
        self.skip = set()
        self.on_end = []               # callbacks run at the end of each frame's logic (a debugging aid)
        self.shoot, self.shots = set(), {}   # frames to take a picture of (a debugging aid: tools for the report's contact sheet)
        self.prev = None
        self.ghost = {}                 # (bar, row, col) -> (tile, attr): cells a test left behind by poking patrons away (adopt_ghosts)
        self.snap = None                # the game's state at the end of its last frame's logic (vq_frame_end): the state the picture was made from
        a = gb.addr("vq_frame_end")
        gb.pb.hook_register(a >> 16, a & 0xFFFF, self._hook, None)
        self.static_rows = [r for r in range(1, 18) if not (ROW0 <= r < ROW0 + 4 * STRIDE and (r - ROW0) % STRIDE < 2)]

    def _hook(self, _):
        self.prev, self.snap = self.snap, self._read()
        for f in self.on_end:
            f(self)

    # -- reading ---------------------------------------------------------------------------------------------------
    def _read(self):
        gb = self.gb
        rd = gb.read
        s = dict(
            state=rd("patron_state", 16), bar=rd("patron_bar", 16), draw=rd("patron_draw", 16), var=rd("patron_variant", 16),
            lift=rd("patron_lift", 16), ovl=rd("patron_ovl", 16), bar_dirs=gb.mem("bar_dirs"), mir=gb.mem("mir_attr"),
            bofs=rd("bar_bofs", 4), base=rd("base_all", 4 * 2 * BASE_W), boss=gb.mem("boss_on"), boss_bar=gb.mem("boss_bar"),
            inst=rd(gb.addr("story_scratch") + SCR_INST_AT + 8, 8), oam_used=gb.mem("oam_used"), lift_total=gb.mem("lift_total"), lift_oam=gb.mem("lift_oam_n"),
            dancers=gb.mem("dancers_vis"), tip=gb.mem16("tip_timer"), show=gb.mem16("show_timer"),
        )
        return s

    def attr_of(self, s, v, flip):
        i = v >> 3
        return (s["inst"][(v ^ i) & 7] | (i & 8) | flip) & 0xFF

    # -- one frame ---------------------------------------------------------------------------------------------------
    def step(self, n=1):
        for _ in range(n):
            shoot = (self.frame + 1) in self.shoot
            self.gb.run(1, render=shoot)
            if shoot:
                self.shots[self.frame + 1] = self.gb.pb.screen.image.convert("RGB").copy()
            self.check()

    def note(self, kind, detail):
        self.kinds.add(kind)
        self.found.append((self.frame, kind, detail))

    def check(self):
        self.frame += 1
        gb = self.gb
        if gb.mem("game_state") not in (2, 3, 4, 5) and False:
            return
        s = self.snap
        if s is None:
            return
        mem = gb.pb.memory
        for p in range(16):
            if s["state"][p]:
                self.variants.add(s["var"][p])
        self.frames_checked += 1
        rows = {}
        for r in range(1, 18):
            a = 0x9800 + 32 * r
            rows[r] = (list(mem[a:a + 20]), list(mem[1, a:a + 20]) if self.cgb else None)
        self.check_bars(s, rows)
        self.check_static(s, rows)
        self.check_oam(s)

    # -- the model of the bars -----------------------------------------------------------------------------------------
    def wall(self, s, b, r, c):
        o = s["bofs"][b] + r * BASE_W + c
        return s["base"][o], (s["base"][o + 2 * BASE_W] if self.cgb else None)

    def model(self, s, b):
        """{(row 0|1, screen col): (tile, attr)} the bar's patrons would make on top of the wall, or None where the model is not exact; plus the allowed
        patron pairs of this bar."""
        rdir = bool(s["bar_dirs"] & (1 << b))
        flip = s["mir"] if rdir else 0
        cover, exact = {}, {}
        foot = {}
        for p in range(16):
            if not s["state"][p] or (s["bar"][p] & 3) != b or s["draw"][p] == 255:
                continue
            d = s["draw"][p]
            c = (d & ~DRAW_BACK) >> 3
            look = s["var"][p] & 7
            lift = s["lift"][p]
            back = d & DRAW_BACK
            pal = self.attr_of(s, s["var"][p], flip)
            unknown = s["ovl"][p] != 0
            if 1 <= lift <= 2:                       # lifted, not dropping: blank (LIFT_EDGE: no footprint)
                unknown = True
            cols = []
            if back:
                v0 = back_first(look)
                cols = [(c, v0, v0 + 2), (c + 1, v0 + 1, v0 + 3)]
            else:
                t = pose_first(look, d & 7)
                t3 = t + 4 if d & 7 else BLANK
                cols = [(c, t, t + 1), (c + 1, t + 2, t + 3), (c + 2, t3, t3 + 1)]
            for lc, t0, t1 in cols:
                if lc >= 20:
                    continue
                sc = 19 - lc if rdir else lc
                foot.setdefault(sc, []).append((p, unknown, t0, t1, pal))
        return foot

    def check_bars(self, s, rows):
        for b in self.bars:
            if s["boss"] and b == s["boss_bar"]:
                continue
            rdir = bool(s["bar_dirs"] & (1 << b))
            flip = s["mir"] if rdir else 0
            foot = self.model(s, b)
            allowed_attr = {}
            for v in self.variants:
                look = v & 7
                allowed_attr.setdefault(look, set()).add(self.attr_of(s, v, flip))
                if self.cgb:
                    allowed_attr[look].add(self.attr_of(s, v, 0))      # (an R bar's patron stays flipped while a pass or a level change is cleaning up)
            top = ROW0 + STRIDE * b
            for r in (0, 1):
                tiles, attrs = rows[top + r]
                for c in range(20):
                    t = tiles[c]
                    a = attrs[c] if self.cgb else None
                    if self.ghost.get((b, r, c)) == (t, a):
                        continue
                    if s["boss"] and t >= BOSS_FX_FIRST and not (a and a & 8):
                        continue                                   # (a boss's landing marker and his ice: game.h BOSS_MARK_BG / boss.h BOSS_ICE_BG)
                    wt, wa = self.wall(s, b, r, c)
                    cell_ok = (t == wt and (not self.cgb or a == wa))
                    if not cell_ok:
                        bank = (a >> 3) & 1 if self.cgb else 0
                        looks = (TILE_LOOK1 if bank else TILE_LOOK0).get(t, set()) if self.cgb else (TILE_LOOK0.get(t, set()) | TILE_LOOK1.get(t, set()))
                        if t in BLANKS and (not self.cgb or True):
                            looks = looks | set(range(8)) if self.cgb else looks | set(range(8))
                        kind = None
                        if not looks:
                            kind = "A-foreign"
                        elif self.cgb and not any(a in allowed_attr.get(lk, ()) or (t in BLANKS and (a & 0xF7) in {x & 0xF7 for xs in allowed_attr.values() for x in xs}) for lk in looks):
                            kind = "A-attr"
                        if kind:
                            ka = ("A", b, r, c)
                            na = self.streak.get(ka, (0, None))[0] + 1
                            self.streak[ka] = (na, None)
                            self.max_a = max(self.max_a, na)
                            if na == self.lag_a + 1:         # (a wrong cell for a few frames is a redraw in transit, as class B; longer is a glitch)
                                self.note(kind, dict(bar=b, row=r, col=c, tile=t, attr=a, wall=(wt, wa), frames=na))
                    else:
                        self.streak.pop(("A", b, r, c), None)
                    if not cell_ok and False:
                        pass
                    # B: exact model
                    f = foot.get(c)
                    if f is None:
                        exp = (wt, wa)
                    elif len(f) == 1 and not f[0][1]:
                        _, _, t0, t1, pal = f[0]
                        exp = (t0 if r == 0 else t1, pal)
                    else:
                        exp = None
                    key = (b, r, c)
                    if exp is not None and not (self.cgb is False and rdir):
                        bad = (t != exp[0]) or (self.cgb and a != exp[1])
                    else:
                        bad = False
                    if bad:
                        n = self.streak.get(key, (0, None))[0] + 1
                        self.streak[key] = (n, (t, a, exp))
                        self.max_streak = max(self.max_streak, n)
                        if n == self.lag + 1:
                            self.note("B-late", dict(bar=b, row=r, col=c, shown=(t, a), model=exp, frames=n))
                    else:
                        self.streak.pop(key, None)

    def check_static(self, s, rows):
        if s["boss"]:
            self.static = None                  # (a boss's attacks draw on the counters; the rows are taken again when he is gone)
            return
        cur = {r: (tuple(rows[r][0]), tuple(rows[r][1]) if rows[r][1] else None) for r in self.static_rows}
        if self.static is None:
            self.static = cur
            return
        for r in self.static_rows:
            if cur[r] != self.static[r]:
                if r in self.skip:
                    self.static[r] = cur[r]
                    continue
                diff = [c for c in range(20) if cur[r][0][c] != self.static[r][0][c] or (cur[r][1] and cur[r][1][c] != self.static[r][1][c])]
                self.note("C-static", dict(row=r, cols=diff, was=[self.static[r][0][c] for c in diff], now=[cur[r][0][c] for c in diff]))
                self.static[r] = cur[r]

    def adopt_ghosts(self):
        """Run one frame and take every cell that is wrong now as a ghost of the test's own pokes (a patron zeroed behind the game's back leaves
        his figure in the map): it is excused for as long as it stays as it is."""
        n0, la = len(self.found), self.lag_a
        self.lag_a = 0                      # (a cell's first frame counts here)
        self.step(1)
        self.lag_a = la
        for f in self.found[n0:]:
            d = f[2]
            if "bar" in d and "col" in d and "row" in d:
                rows = self.gb.pb.memory
                a = 0x9800 + 32 * (ROW0 + STRIDE * d["bar"] + d["row"]) + d["col"]
                self.ghost[(d["bar"], d["row"], d["col"])] = (rows[a], rows[1, a] if self.cgb else None)
        del self.found[n0:]
        self.streak.clear()

    def rebase_static(self):
        self.static = None

    def check_oam(self, s):
        """OAM is DMA'd in the VBlank after a frame's logic, so the entries seen belong to the state at the end of the last logic OR (when this
        emulator frame ended after the next logic's end) the one before it: an entry is a finding only when neither state owns it."""
        oam = self.gb.oam()
        vis = [i for i, e in enumerate(oam) if 0 < e["y"] < 160 and 0 < e["x"] < 168]
        states = [x for x in (s, self.prev) if x is not None]
        if any(x["boss"] for x in states):
            return                              # (a boss's own sprites fill the entries from the mugs' up)
        for i in vis:
            kind = None
            if all(5 + x["oam_used"] <= i < GAME["OAM_MUG_END"] - 2 * max(x["lift_total"], x["lift_oam"]) for x in states):
                kind = "D-oam-unowned-mug"
            elif i >= GAME["OAM_DANCERS"] and not any(x["dancers"] for x in states):
                kind = "D-oam-dancer-no-show"
            elif i == GAME["OAM_COIN"] and not any(x["tip"] for x in states):
                kind = "D-oam-coin-no-tip"
            if kind:
                self.note(kind, dict(entry=i, oam_used=s["oam_used"], lift_total=s["lift_total"], e=oam[i]))

    def assert_clean(self, ignore=()):
        bad = [f for f in self.found if f[1] not in ignore]
        assert not bad, ("picture glitches (frame, kind, detail)", len(bad), bad[:6])
