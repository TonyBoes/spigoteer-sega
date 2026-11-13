# Boss Rush portraits cut off (owner 2026-11-13)

Record of the three proposals (A whole figure, B hand-drawn 0.7 reductions, C top-first crop). The owner picked A, centred vertically (Q59): it is now the
default (tools/gen_rush_portraits.py, src/rush.c: the selected boss's tiles stream into a spare slot, then swap). `options_b.txt`, `gen_variant.py` and the
sheet scripts are kept as the record: `gen_variant.py` and `rp_common.py` were written against the generator as it was at commit "Boss Rush portraits cut
off: three proposals behind RUSHPIC" (they call helpers that the final generator no longer has), and the RUSHPIC flag is gone from the Makefile and src.
`make_sheets.py` / `shoot_list.py` (real-engine list screenshots, DMG and Color) still work against the default ROM.
