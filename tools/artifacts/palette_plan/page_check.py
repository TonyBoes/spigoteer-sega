#!/usr/bin/env python3
"""The built page as the owner sees it, at 360 px, without a browser (none is installed in this container: no chromium, playwright or
selenium, and no network to fetch one). A static check of index.html and its CSS:

- every <img> points at a file that exists next to the page, is a real PNG with natural width and height > 0;
- an <img> rendered by an auto-width cell must have width/height attributes (the 10-25 "empty column" bug: the published skeleton's
  `img{max-width:100%}` shrank an unsized image in an auto-width table cell to nothing);
- an image wider than 320 px (its width attribute, else its natural width) needs `max-width:100%` in its class's CSS;
- at 360 px (the base rules plus the `@media (max-width: 640px)` ones) no rule fixes a width or min-width above 328 px without a
  `max-width` beside it, and nothing sets a px `min-width` wider than the screen.
Exit 1 and a list on any error. `page_check.py index.html`; build.py output is checked by `make atlas-page` and tests/test_atlas_page.py.
"""
import os
import re
import sys
from html.parser import HTMLParser

VIEW = 360
GUTTER = 16
MAXW = VIEW - 2 * GUTTER          # 328


class Scan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.imgs, self.css, self._in_style, self._td = [], [], False, 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("td", "th"):
            self._td += 1
        if tag == "img":
            a["_td"] = self._td > 0
            self.imgs.append(a)
        elif tag == "style":
            self._in_style = True

    def handle_endtag(self, tag):
        if tag in ("td", "th"):
            self._td = max(0, self._td - 1)
        if tag == "style":
            self._in_style = False

    def handle_data(self, data):
        if self._in_style:
            self.css.append(data)


def css_rules(css):
    """[(selector, {prop: value})] that apply at 360 px: base rules and the max-width media blocks (<= 640) in order."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out, i, n = [], 0, len(css)

    def block(s, i):
        d, j = 0, i
        while j < len(s):
            if s[j] == "{":
                d += 1
            elif s[j] == "}":
                d -= 1
                if d == 0:
                    return j
            j += 1
        return len(s) - 1

    def parse(s, active):
        i, res = 0, []
        while i < len(s):
            j = s.find("{", i)
            if j < 0:
                break
            head = s[i:j].strip()
            e = block(s, j)
            body = s[j + 1:e]
            if head.startswith("@media"):
                m = re.search(r"max-width:\s*(\d+)px", head)
                mn = re.search(r"min-width:\s*(\d+)px", head)
                ok = active and not (mn and int(mn.group(1)) > VIEW) and (not m or int(m.group(1)) >= VIEW) and "prefers-color" not in head and "print" not in head
                res += parse(body, ok)
            elif head.startswith("@"):
                pass
            elif active:
                props = {k.strip().lower(): v.strip().lower() for k, v in re.findall(r"([\w-]+)\s*:\s*([^;]+);?", body)}
                res.append((head, props))
            i = e + 1
        return res

    return parse(css, True)


def png_size(path):
    from PIL import Image
    with Image.open(path) as im:
        return im.size


def check(path):
    base = os.path.dirname(os.path.abspath(path))
    s = Scan()
    s.feed(open(path).read())
    rules = css_rules("\n".join(s.css))
    errs = []
    cls_css = {}
    for sel, props in rules:
        for c in re.findall(r"\.([\w-]+)", sel):
            cls_css.setdefault(c, {}).update(props)
    for sel, props in rules:
        for k in ("width", "min-width"):
            m = re.fullmatch(r"(\d+(?:\.\d+)?)px", props.get(k, ""))
            if m and float(m.group(1)) > MAXW and "max-width" not in props and "overflow-x" not in props:
                errs.append("CSS %s { %s: %spx } is wider than the %d px screen (no max-width)" % (sel, k, m.group(1), MAXW))
    seen = set()
    for a in s.imgs:
        src = (a.get("src") or "").split("?")[0]
        if not src or src.startswith("data:") or src.startswith("http"):
            continue
        f = os.path.join(base, src)
        if not os.path.exists(f):
            errs.append("img %s: file missing" % src)
            continue
        try:
            w, h = png_size(f)
        except Exception as e:
            errs.append("img %s: not a readable PNG (%s)" % (src, e))
            continue
        if w <= 0 or h <= 0:
            errs.append("img %s: natural size %dx%d" % (src, w, h))
        classes = (a.get("class") or "").split()
        props = {"max-width": "100%"}           # the published skeleton's img{max-width:100%}
        for sel, pr in rules:
            if sel.strip() == "img":
                props.update(pr)
        for c in classes:
            props.update(cls_css.get(c, {}))
        sized = a.get("width") and a.get("height")
        shrink = "max-width" in props and props["max-width"] != "none"
        key = (tuple(classes), bool(sized), a["_td"], src if not sized else "")
        if key in seen:
            continue
        seen.add(key)
        if not sized and shrink and "width" not in props and a["_td"]:
            errs.append("img %s (class %s): no width/height attributes and max-width shrinks it: it can collapse to 0 in an auto-width cell" % (src, " ".join(classes) or "-"))
        rw = int(a["width"]) if a.get("width", "").isdigit() else w
        if rw > MAXW and not (props.get("max-width", "").endswith("%")):
            errs.append("img %s (class %s): %d px wide with no max-width:100%%, over the %d px screen" % (src, " ".join(classes) or "-", rw, MAXW))
    return errs, len(s.imgs)


def main():
    path = sys.argv[1]
    errs, n = check(path)
    if errs:
        print("PAGE CHECK FAILED (%d problems, 360 px static check):" % len(errs), file=sys.stderr)
        for e in errs[:40]:
            print("  - " + e, file=sys.stderr)
        sys.exit(1)
    print("page_check: %d images, no horizontal overflow risk at %d px (static check, no browser available)" % (n, VIEW))


if __name__ == "__main__":
    main()
