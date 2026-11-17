"""THE FINAL SET (round 18): the one build of the ten scene pages, every owner's approved choice fixed here. The generator's default entry point.

  Coach (Stadium)        round 15: the dark fill under the brim tip + no wall blue under the brim (scenes_f GAPFILL "dark15"); round 9's 2 px undersides.
  June (Lumber Lodge)    round 12: the owner's own cut-out (owner_masks/owner_june_mask.jpg), hat specks as drawn; art colours ours.
  Kiki (Jungle Zoo)      round 14: the owner's own cut-out (owner_kiki_mask.png), two odd pixels in our nearest palette colour, near-black through slot 3 of the zoo's bar palette,
                         at most 8 sprites a line (the cells that do not fit stay BG owner cells); the game's mouth and pigtail art.
  Hana (Teahouse)        round 17: the owner's own cut-out (owner_hana_mask.jpg, flood-filled from the picture's edge), slot 3 of the teahouse stage_a / stage_b / bar palettes = #100818,
                         at most 8 sprites a line.
  Granny (Chrome Cow)    round 19: the owner's own cut-out (owner_granny_mask.png, teal = room); 9 of the story-background pixels he kept in other colours are art pixels in her nearest
                         palette colour that fits the cell, the other 74 stay near-black; at most 8 sprites a line.
  everyone else          round 9: the mask rule (scenes_c.backdrop_mask), the outline ring and the 2 px dark underside (scenes_f UNDER).

build_final(key) sets every toggle explicitly (nothing depends on a previous call) and restores them. The older rounds still rebuild through the toggles in scenes_f / scenes_c
(PAINT_ON, GAPFILL, JUNEFILL, RING_PAL, MASK_PICS, JUNE_FIX): they are left as they were, off, and the final set never turns them on except where listed above.
"""
import copy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from scenes_lib import *      # noqa: E402
import scenes_c as C          # noqa: E402
import scenes_f as F          # noqa: E402

MASKS = HERE / "owner_masks"
LIMITS = {"line": 8, "objs": 23, "pals": 8}
HEART = "#c83028"        # Granny: the heart tattoo on her neck, her bandana red (round 20)
CONFIG = {
    "saloon": {"accents": True},
    "sports": {"gapfill": "dark15"},
    "lodge": {"mask": ("june", "owner_june_mask.jpg")},
    "bistro": {},
    "igloo": {},
    "factory": {},
    "biker": {"mask": ("granny", "owner_granny_mask.png"), "limits": LIMITS, "accents": True},
    "teahouse": {"mask": ("hana", "owner_hana_mask.jpg"), "slot3": {"stage_a": "#100818", "stage_b": "#100818", "bar": "#100818"}, "limits": LIMITS},
    "zoo": {"mask": ("kiki", "owner_kiki_mask.png"), "slot3": {"bar": "#2c1808"}, "limits": LIMITS, "accents": True},
    "space": {},
}
OWNER_OF = {"saloon": "sadie", "sports": "coach", "lodge": "june", "bistro": "colby", "igloo": "aurora", "factory": "managerbot", "biker": "granny", "teahouse": "hana", "zoo": "kiki", "space": "zizz"}


def build_final(key):
    """-> (venue, r, comps{cgb}); r is scenes_f.build's dict"""
    cfg = CONFIG[key]
    ven = [v for v in F.VENUES if v.key == key][0]
    saved = (F.OVERLAY_COLOR_ONLY, F.OVERLAY_SHADE, F.OVERLAYS, F.UNDER, F.PAINT_ON, F.GAPFILL, F.JUNEFILL, F.RING_PAL, C.JUNE_FIX, C.MASK_PICS, C.PIXEL_OVERRIDE, copy.deepcopy(ven.pal))
    try:
        F.UNDER, F.PAINT_ON, F.JUNEFILL, F.RING_PAL, C.JUNE_FIX = True, False, None, {}, False
        F.OVERLAYS = {key: cfg["overlay"]} if "overlay" in cfg else {}
        F.OVERLAY_COLOR_ONLY = set()
        if cfg.get("accents"):
            # the story's Color-only OBJ accents (Granny's red lips) as Color-only sprites over the BG replacement, at their own story colours
            from audit_story import story_grids
            hx, sh, accpos, bg_, rows_ = story_grids(OWNER_OF[key])
            F.OVERLAYS = {key: [(x, y, hx[y][x]) for (x, y) in sorted(accpos)]}
            F.OVERLAY_COLOR_ONLY = {key}
        F.OVERLAY_SHADE = {key: cfg["overlay_shade"]} if "overlay_shade" in cfg else {}
        F.GAPFILL = cfg.get("gapfill")
        C.MASK_PICS = {cfg["mask"][0]: MASKS / cfg["mask"][1]} if "mask" in cfg else {}
        C.PIXEL_OVERRIDE = cfg.get("override", {})
        for pal, hx in cfg.get("slot3", {}).items():
            ven.pal[pal] = [ven.pal[pal][0], ven.pal[pal][1], ven.pal[pal][2], hx]
        r = F.build(ven, cfg.get("limits"))
        comps = {cgb: F.composite(r, ven, cgb) for cgb in (False, True)}
        stats = {"dmg": F.bg_stats(F.bg_with_perf(r, ven, False)), "cgb": F.bg_stats(F.bg_with_perf(r, ven, True)), "obj": F.obj_stats(r, ven, True)}
        return ven, r, comps, stats
    finally:
        F.OVERLAY_COLOR_ONLY, F.OVERLAY_SHADE, F.OVERLAYS, F.UNDER, F.PAINT_ON, F.GAPFILL, F.JUNEFILL, F.RING_PAL, C.JUNE_FIX, C.MASK_PICS, C.PIXEL_OVERRIDE, ven.pal = saved


import contextlib      # noqa: E402


@contextlib.contextmanager
def configured(key):
    """(integration, tools/gen_scene_pages.py) the toggles, overlays and palette changes of build_final(key) held while the caller builds and composites with the venue: -> cfg"""
    cfg = CONFIG[key]
    ven = [v for v in F.VENUES if v.key == key][0]
    saved = (F.OVERLAY_COLOR_ONLY, F.OVERLAY_SHADE, F.OVERLAYS, F.UNDER, F.PAINT_ON, F.GAPFILL, F.JUNEFILL, F.RING_PAL, C.JUNE_FIX, C.MASK_PICS, C.PIXEL_OVERRIDE, copy.deepcopy(ven.pal))
    try:
        F.UNDER, F.PAINT_ON, F.JUNEFILL, F.RING_PAL, C.JUNE_FIX = True, False, None, {}, False
        F.OVERLAYS = {key: cfg["overlay"]} if "overlay" in cfg else {}
        F.OVERLAY_COLOR_ONLY = set()
        if cfg.get("accents"):
            from audit_story import story_grids
            hx, sh, accpos, bg_, rows_ = story_grids(OWNER_OF[key])
            F.OVERLAYS = {key: [(x, y, hx[y][x]) for (x, y) in sorted(accpos)]}
            F.OVERLAY_COLOR_ONLY = {key}
        F.OVERLAY_SHADE = {key: cfg["overlay_shade"]} if "overlay_shade" in cfg else {}
        F.GAPFILL = cfg.get("gapfill")
        C.MASK_PICS = {cfg["mask"][0]: MASKS / cfg["mask"][1]} if "mask" in cfg else {}
        C.PIXEL_OVERRIDE = cfg.get("override", {})
        for pal, hx in cfg.get("slot3", {}).items():
            ven.pal[pal] = [ven.pal[pal][0], ven.pal[pal][1], ven.pal[pal][2], hx]
        yield cfg
    finally:
        F.OVERLAY_COLOR_ONLY, F.OVERLAY_SHADE, F.OVERLAYS, F.UNDER, F.PAINT_ON, F.GAPFILL, F.JUNEFILL, F.RING_PAL, C.JUNE_FIX, C.MASK_PICS, C.PIXEL_OVERRIDE, ven.pal = saved
