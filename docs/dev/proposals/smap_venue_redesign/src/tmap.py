"""python3 tmap.py NAME: the cell grid of src/NAME.py with a letter per unique tile"""
import importlib
import sys

import common as C

C.tilemap(importlib.import_module(sys.argv[1]).build())
