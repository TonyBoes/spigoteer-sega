# patron-rev-2: in a Color Saloon level LYC_REG alternates between the window's own line and the palette split's line (game.h SPLIT_*): the
# window's own line is then in HRAM SPLIT_WANT. Everywhere else (the DMG, every other screen) it is LYC_REG itself.
SPLIT_ON, SPLIT_WANT, LYC = 0xFFD4, 0xFFD5, 0xFF45


def win_lyc(read):
    """The window's own LYC; `read(addr)` reads a byte (gb.mem, or lambda a: gb.pb.memory[a])."""
    return read(SPLIT_WANT) if read(SPLIT_ON) else read(LYC)
