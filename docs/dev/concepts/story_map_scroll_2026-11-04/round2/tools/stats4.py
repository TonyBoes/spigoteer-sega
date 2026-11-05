"""Sprites per scanline and OAM objects (8x16 mode: every object is 16 lines tall, an 8 x 8 picture takes a whole object)."""
import render2 as R
import world2 as W


def objects(here, cam, late=True, bang=False):
    """list of (x, y, h) objects on screen for Sal standing at stop `here` with the camera at cam"""
    cx, cy = cam
    fx, fy = W.STOPS[here]
    x, y = fx - 8, fy - 24
    objs = []
    for col in (0, 8):                                   # Sal: 16 x 24 = two columns, each two 8 x 16 objects
        objs.append((x + col, y, 16))
        objs.append((x + col, y + 16, 16))
    for b in W.NEIGH[here]:
        d = W.exit_dir(here, b)
        ax, ay = {"R": (x + 18, y + 8), "L": (x - 10, y + 8), "U": (x + 4, y - 9), "D": (x + 4, y + 25)}[d]
        objs.append((ax, ay, 16))
    if bang:
        objs.append((W.STOPS["town"][0] - 4, W.STOPS["town"][1] - 36, 16))
    for n, (sx, sy) in W.STOPS.items():
        objs.append((sx - 4, sy - 8, 16))                # a dot per stop (open or locked)
    vx, vy = W.VENUES["space"][1][0] * 8 + 62, W.VENUES["space"][1][1] * 8 + 6
    for i in range(3):
        objs.append((vx + 8 * i, vy, 16))                # the UFO, 24 x 16
    vis = [(ox - cx, oy - cy, h) for (ox, oy, h) in objs if -8 < ox - cx < 160 and -16 < oy - cy < 144]
    return vis


def worst(here, cam):
    vis = objects(here, cam)
    line = [sum(1 for (_, oy, h) in vis if oy <= l < oy + h) for l in range(144)]
    return len(vis), max(line)


if __name__ == "__main__":
    wo, wl = 0, 0
    for s in W.STOPS:
        n, l = worst(s, R.view_cam(s))
        print(f"{s:8s} objects on screen {n:2d}   most on one line {l}")
        wo, wl = max(wo, n), max(wl, l)
    print("worst:", wo, wl)
