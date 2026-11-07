"""scratch preview of round 4d: python3 prev4.py -> out/mb/p4_{dmg,cgb}.png (the piece alone on the farm ground, x6 close-up of the lot)"""
import common as C
import cow_lot4 as L

for cgb in (False, True):
    c = L.build()
    im = C.render(c, L.BIOME, L.AT, cgb).crop((24, 46 + 8, 112, 84))
    im.resize((im.width * 8, im.height * 8), 0).save(f'{C.ROOT}/out/mb/p4_{"cgb" if cgb else "dmg"}.png')
print(C.tile_count(c))
