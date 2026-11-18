// Skeleton game: one-screen platformer, ONE source for Game Boy (DMG/CGB),
// Sega Master System and Game Gear, via GBDK-2020's cross-platform API.
// Same game, level and physics as the nes/gameboy skeletons, so tests match.
//
// Portability rules this file follows (keep them when you extend it):
//   - include <gbdk/platform.h>, never <gb/gb.h> or <sms/sms.h> directly
//   - place things with DEVICE_* constants, never hard-coded screen sizes
//   - tiles are 2bpp Game Boy format; on SMS/GG set_2bpp_palette() maps the
//     four shades onto palette entries as they load
//   - the player is two 8x8 sprites (8x16 mode differs between consoles)
//   - SMS/GG sprites cannot flip; guarded by HARDWARE_SPRITE_CAN_FLIP_X
//
// Test-visible state is plain globals => symbols in build/<target>/game.noi.
#include <gbdk/platform.h>
#include <stdint.h>

#include "tiles.h"
#include "player.h"
#include "level1.h"

// Level origin in tiles, centred in the visible screen: GB (0,0), GG (0,0), SMS (6,3).
// NOT plus DEVICE_SCREEN_X/Y_OFFSET: on Game Gear, GBDK's tile-map calls
// (set_bkg_tiles, set_tile_map) add the visible-window offset themselves.
// Sprite coordinates do not, so SPR_X0/SPR_Y0 use DEVICE_SPRITE_PX_OFFSET_*.
#define LX ((DEVICE_SCREEN_WIDTH  - LEVEL1_WIDTH)  / 2)
#define LY ((DEVICE_SCREEN_HEIGHT - LEVEL1_HEIGHT) / 2)
#define SPR_X0 (DEVICE_SPRITE_PX_OFFSET_X + LX * 8)
#define SPR_Y0 (DEVICE_SPRITE_PX_OFFSET_Y + LY * 8)

#define GRAVITY        48
#define JUMP_VEL      (-900)
#define JUMP_CUT      (-300)
#define MAX_FALL       1024
#define COYOTE_FRAMES  6
#define JUMP_BUFFER    6

uint8_t  player_x, player_y;
int16_t  player_vy;
uint8_t  on_ground, coyote, jump_buffer, facing, anim_frame, frame_counter;
uint8_t  joy, joy_prev;
uint8_t  collected, dead, level_done;

// 4 greys, lightest first. SMS/GG: entries 4-15 unused; sprites use palette 1 (entry 0 transparent).
static const palette_color_t greys[4] = {
    RGB8(255, 255, 255), RGB8(170, 170, 170), RGB8(85, 85, 85), RGB8(0, 0, 0),
};

static uint8_t col_at(uint8_t px, uint8_t py) {
    uint8_t tx = px >> 3, ty = py >> 3;
    if (tx >= LEVEL1_WIDTH || ty >= LEVEL1_HEIGHT) return COL_SOLID;
    return level1_collision[ty * LEVEL1_WIDTH + tx];
}
static uint8_t solid_at(uint8_t px, uint8_t py) { return col_at(px, py) == COL_SOLID; }
static uint8_t floor_at(uint8_t px, uint8_t py) {
    uint8_t c = col_at(px, py);
    return c == COL_SOLID || (c == COL_PLATFORM && (py & 7) == 0 && player_vy >= 0);
}
static uint8_t feet_on_floor(void) {
    return floor_at(player_x + 1, player_y + 16) || floor_at(player_x + 6, player_y + 16);
}

static void init(void) {
    DISPLAY_OFF;
#if defined(SEGA)
    set_bkg_palette(0, 1, greys);
    set_sprite_palette(0, 1, greys);
    set_2bpp_palette(COMPAT_PALETTE(0, 1, 2, 3));
#elif defined(GAMEBOY)
    if (_cpu == CGB_TYPE) {
        set_bkg_palette(0, 1, greys);
        set_sprite_palette(0, 1, greys);
    }
    BGP_REG = OBP0_REG = 0xE4;   // DMG: index 3 darkest
#endif
    SPRITES_8x8;
    set_bkg_data(0, tiles_TILE_COUNT, tiles_tiles);
    set_sprite_data(0, player_TILE_COUNT, player_tiles);
    set_bkg_tiles(LX, LY, LEVEL1_WIDTH, LEVEL1_HEIGHT, level1_tiles);
    for (uint8_t i = 0; i < LEVEL1_ENTITY_COUNT; i++) {
        if (level1_entities[i].type == ENT_SPAWN) {
            player_x = level1_entities[i].x << 3;
            player_y = (level1_entities[i].y << 3) - 8;
        }
    }
    SHOW_BKG; SHOW_SPRITES;
    DISPLAY_ON;
}
static void update(void) {
    joy_prev = joy;
    joy = joypad();
    uint8_t pressed = joy & ~joy_prev;

    if (joy & J_LEFT)  { facing = 1; if (!solid_at(player_x - 1, player_y + 15) && !solid_at(player_x - 1, player_y)) player_x--; }
    if (joy & J_RIGHT) { facing = 0; if (!solid_at(player_x + 8, player_y + 15) && !solid_at(player_x + 8, player_y)) player_x++; }

    if (pressed & J_A) jump_buffer = JUMP_BUFFER;
    else if (jump_buffer) jump_buffer--;
    if (jump_buffer && (on_ground || coyote)) {
        player_vy = JUMP_VEL; on_ground = 0; coyote = 0; jump_buffer = 0;
    }
    if (!(joy & J_A) && player_vy < JUMP_CUT) player_vy = JUMP_CUT;

    player_vy += GRAVITY;
    if (player_vy > MAX_FALL) player_vy = MAX_FALL;
    int8_t dy = (int8_t)(player_vy >> 8);
    uint8_t was_ground = on_ground;
    on_ground = 0;
    while (dy > 0) {
        if (feet_on_floor()) { player_vy = 0; on_ground = 1; break; }
        player_y++; dy--;
    }
    while (dy < 0) {
        if (solid_at(player_x + 1, player_y - 1) || solid_at(player_x + 6, player_y - 1)) { player_vy = 0; break; }
        player_y--; dy++;
    }
    if (dy == 0 && player_vy >= 0 && feet_on_floor()) on_ground = 1;
    if (on_ground) coyote = COYOTE_FRAMES;
    else if (was_ground && coyote == 0) coyote = COYOTE_FRAMES;
    else if (coyote) coyote--;

    if (col_at(player_x + 4, player_y + 15) == COL_HAZARD) dead = 1;
    for (uint8_t i = 0; i < LEVEL1_ENTITY_COUNT; i++) {
        uint8_t ex = level1_entities[i].x << 3, ey = level1_entities[i].y << 3;
        if (!(player_x < ex + 8 && player_x + 8 > ex && player_y < ey + 8 && player_y + 16 > ey)) continue;
        if (level1_entities[i].type == ENT_EXIT) level_done = 1;
        if (level1_entities[i].type == ENT_COLLECTIBLE) collected = 1;
    }

    if (!on_ground) anim_frame = 0;
    else if (joy & (J_LEFT | J_RIGHT)) { if ((frame_counter & 7) == 0) anim_frame ^= 1; }
    else anim_frame = 0;
    frame_counter++;
}

static void draw(void) {
    // player.png in reading order: frame0 top, frame1 top, frame0 bottom, frame1 bottom
    set_sprite_tile(0, anim_frame);
    set_sprite_tile(1, 2 + anim_frame);
#if HARDWARE_SPRITE_CAN_FLIP_X
    set_sprite_prop(0, facing ? S_FLIPX : 0);
    set_sprite_prop(1, facing ? S_FLIPX : 0);
#endif
    move_sprite(0, SPR_X0 + player_x, SPR_Y0 + player_y);
    move_sprite(1, SPR_X0 + player_x, SPR_Y0 + player_y + 8);
}

void main(void) {
    init();
    while (1) {
        vsync();
        update();
        draw();
    }
}
