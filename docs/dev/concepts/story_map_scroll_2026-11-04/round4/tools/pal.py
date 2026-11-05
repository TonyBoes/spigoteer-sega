"""BG palettes of the round-2 map: index 0 is the ground the piece stands on, 3 the ink. Colours from the venues' own in-game palettes
(assets/approved/venues/*_pal.json); every channel a multiple of 8."""


def h(x):
    x = x.lstrip("#")
    return tuple(int(x[i:i + 2], 16) & 0xF8 for i in (0, 2, 4))


PALS = {
    # biomes (the ground a cell stands on; a venue's own palette doubles as its biome where the two are the same colours)
    "grass": ["b0d080", "6aa048", "28603c", "142418"],
    "farm": ["c8e888", "e8c860", "986838", "281808"],
    "road": ["f0e4b8", "c8a868", "886038", "281808"],
    "meadow": ["b8e080", "60b048", "286840", "181828"],
    "desert": ["f8e090", "e0b058", "a07038", "301408"],
    "snow": ["e8f8ff", "a8d0f0", "5088d0", "0c1838"],
    "forest": ["b0d080", "6aa048", "28603c", "142418"],
    "farm": ["c8e888", "e8c860", "986838", "281808"],
    "road": ["f0e4b8", "c8a068", "786040", "281808"],
    # venues
    "saloon": ["f8e090", "e8b060", "a05828", "301408"],
    "stadium": ["d4d8e4", "e04030", "283c78", "101428"],
    "lodge": ["b0d080", "e0b060", "905830", "2a1608"],
    "bistro": ["f4ecd8", "7cc0b4", "2a6a68", "0c2830"],
    "igloo": ["e8f8ff", "6aa8d8", "2a5090", "0c1838"],
    "factory": ["e8e8e0", "8898a8", "384858", "12181c"],
    "factory_b": ["e8e8e0", "f8a820", "384858", "12181c"],
    "cow": ["c8e888", "e8e0f0", "f03898", "2a1e34"],
    "tea": ["d8ecb0", "f4ecc8", "a05030", "2c1810"],
    "tea_b": ["d8ecb0", "f8b8d0", "b05878", "3c1828"],
    "zoo": ["d8f0a0", "58b048", "1c6a30", "082a18"],
    "zoogate": ["d8f0a0", "e8c880", "a05828", "2c1808"],
    "base": ["f8e090", "98a0b0", "1c2468", "080818"],
    "town1": ["fff0b0", "f0b888", "a090b0", "201828"],
    "town2": ["fff0b0", "b8dcf4", "e8a828", "201828"],
    "town3": ["fff0b0", "f0b888", "f08828", "201828"],
    "town4": ["fff0b0", "b8dcf4", "a090b0", "201828"],
    "town5": ["fff0b0", "f0b888", "e8a828", "201828"],
}
CLOUD = ["f8f8ff", "dce2f4", "b4bedc"]            # fog: lit cloud, shade, deep shade (index 1 to 3)
RGB = {k: [h(c) for c in v] for k, v in PALS.items()}


def get(name):
    """a palette by name; 'fog:<palette>' is the cloud colours over that palette's ground (index 0)"""
    if name.startswith("fog:"):
        base = name[4:]
        g = RGB[base][0] if base in RGB else h("f8f8ff")
        return [g] + [h(c) for c in CLOUD]
    return RGB[name]
def canon(name):
    """the first palette of the table with the same ground colour (index 0): fog edges over those grounds share one palette"""
    for k in RGB:
        if RGB[k][0] == RGB[name][0]:
            return k
    return name


DMG_SHADE = [248, 168, 88, 24]
