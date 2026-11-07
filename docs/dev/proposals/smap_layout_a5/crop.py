"""Crops a map picture by cells.  python3 -I crop.py IN.png OUT.png CX0 CY0 CX1 CY1   (cells, inclusive; x1 pictures)"""
import sys

from PIL import Image

im = Image.open(sys.argv[1])
x0, y0, x1, y1 = map(int, sys.argv[3:7])
im.crop((x0 * 8, y0 * 8, (x1 + 1) * 8, (y1 + 1) * 8)).save(sys.argv[2])
