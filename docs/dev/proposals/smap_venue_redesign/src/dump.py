"""python3 dump.py NAME x0 y0 x1 y1: print a window of the typed pixels (for the clean-up pass)"""
import importlib
import sys

n, x0, y0, x1, y1 = sys.argv[1], *map(int, sys.argv[2:6])
c = importlib.import_module(n).build()
print('     ' + ''.join(str(x % 10) for x in range(x0, x1)))
for y in range(y0, y1):
    print(f'{y:3d}  ' + ''.join(c.px[y][x] for x in range(x0, x1)))
