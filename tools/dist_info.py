#!/usr/bin/env python3
"""Header facts of a Game Boy ROM (also the test's reader): dist_info.py ROM [VERSION] -> RELEASE.txt body on stdout."""
import hashlib, sys, datetime

CART = {0x1B: "MBC5+RAM+BATTERY"}
RAM = {0: "none", 2: "8 KB (1 bank)", 3: "32 KB (4 banks)"}


def header(d):
    return {
        "title": d[0x134:0x13F].split(b"\0")[0].decode("ascii"),
        "cgb_flag": d[0x143], "sgb_flag": d[0x146], "cart_type": d[0x147], "rom_size": d[0x148], "ram_size": d[0x149],
        "dest": d[0x14A], "old_licensee": d[0x14B], "new_licensee": d[0x144:0x146].decode("ascii"), "version": d[0x14C],
        "header_sum": d[0x14D], "global_sum": d[0x14E] << 8 | d[0x14F],
        "header_ok": (-sum(d[0x134:0x14D]) - 25) & 255 == d[0x14D],
        "global_ok": (sum(d) - d[0x14E] - d[0x14F]) & 0xFFFF == (d[0x14E] << 8 | d[0x14F]),
        "size": len(d),
    }


if __name__ == "__main__":
    d = open(sys.argv[1], "rb").read()
    h = header(d)
    ver = sys.argv[2] if len(sys.argv) > 2 else "?"
    print(f"Spigoteer v{ver}")
    print(f"Built (UTC):   {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M')}")
    print(f"SHA-256:       {hashlib.sha256(d).hexdigest()}")
    print(f"Size:          {h['size']} bytes ({h['size'] // 1024} KB, {h['size'] // 16384} banks)")
    print("Header:")
    print(f"  title        {h['title']}")
    print(f"  CGB flag     0x{h['cgb_flag']:02X} ({'runs on DMG and CGB' if h['cgb_flag'] == 0x80 else 'CGB only' if h['cgb_flag'] == 0xC0 else 'DMG only'})")
    print(f"  cart type    0x{h['cart_type']:02X} ({CART.get(h['cart_type'], '?')})")
    print(f"  ROM size     0x{h['rom_size']:02X}  RAM size 0x{h['ram_size']:02X} ({RAM.get(h['ram_size'], '?')})")
    print(f"  destination  0x{h['dest']:02X} ({'non-Japanese' if h['dest'] else 'Japan'})")
    print(f"  licensee     old 0x{h['old_licensee']:02X}, new '{h['new_licensee']}'")
    print(f"  version byte {h['version']}")
    print(f"  checksums    header 0x{h['header_sum']:02X} ({'ok' if h['header_ok'] else 'BAD'}), global 0x{h['global_sum']:04X} ({'ok' if h['global_ok'] else 'BAD'})")
    print("Licences: see licenses/ (README.txt) and CREDITS.md next to this file.")
