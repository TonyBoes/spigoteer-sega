"""Today's four pieces: tile counts and renders (the same render as the options use)."""
import common as C
import v_igloo, v_cow, v_zoo, v_space

AT = {'igloo': (53, 6), 'cow': (39, 23), 'zoo': (17, 36), 'space': (1, 34)}
BIO = {'igloo': 'snow', 'cow': 'farm', 'zoo': 'jungle', 'space': 'desert'}
MOD = {'igloo': v_igloo, 'cow': v_cow, 'zoo': v_zoo, 'space': v_space}


def canvas(name, dmg=True):
    return MOD[name].build(dmg=dmg)


if __name__ == '__main__':
    for n in AT:
        c = canvas(n)
        reg = (0, 0, 6, 6) if n == 'space' else None
        print(n, c.w, c.h, 'DMG tiles', C.tile_count(c, reg), ' (Color-build variant', C.tile_count(canvas(n, False), reg), ')')
