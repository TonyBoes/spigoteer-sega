#!/usr/bin/env python3
"""Real ROM0 free space from the linker map: usage rom0free.py build/game.map

romusage overstates ROM0 (by ~341 B in this build). What actually fills ROM0 is
the chain of relocatable areas the linker places after the header: _CODE from 0x0200, then _HOME, _INITIALIZER, _GSINIT,
_GSFINAL. The free space is 0x4000 minus the end of the last one. Past 0x4000 the linker only warns ("Possible overflow
from Bank 0 into Bank 1") and the build silently corrupts bank 1; the Makefile fails the build on that warning.
"""
import re
import sys

end = 0
for line in open(sys.argv[1]):
    m = re.match(r'^(_\w+)\s+([0-9A-F]{8})\s+([0-9A-F]{8})', line)
    if m and not m[1].startswith('_HEADER'):
        a, n = int(m[2], 16), int(m[3], 16)
        if a < 0x4000 and n:
            end = max(end, a + n)
print(f"ROM0 real: ends at 0x{end:04X}, {0x4000 - end} bytes free (linker map; romusage's ROM_0 free column overstates it)")
