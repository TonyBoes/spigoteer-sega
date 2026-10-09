// Skeleton game: one-screen platformer. Replace freely; keep the shape.
//
// Everything a test can assert on is a plain global in WRAM, so it shows up
// in build/game.noi and tests/ can read it by name (player_x, player_y, ...).
//
// Conventions:
//   - positions in pixels, velocities in 8.8 fixed point (1 px = 256)
//   - the whole frame runs between vsync() calls; OAM is written through
//     GBDK's shadow OAM (move_sprite) and DMA'd in the VBlank handler
//   - DMG and CGB both work: lcc -Wm-yc marks the cart CGB-compatible and
//     the CGB palettes come straight from png2asset
#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>

#include "tiles.h"
#include "player.h"
#include "level1.h"

// ---- tunables (also readable from tests) ----------------------------------
#define GRAVITY        48      // 8.8 per frame
#define JUMP_VEL      (-900)   // 8.8, negative is up
#define MAX_FALL       1024
#define WALK_SPEED       1     // px per frame
#define COYOTE_FRAMES    6     // may still jump this many frames after leaving ground
#define JUMP_BUFFER      6     // a press this many frames before landing still jumps

// ---- state (globals => symbols) -----------------------------------------------
uint8_t  player_x, player_y;      // top-left of the 8x16 sprite, in pixels
int16_t  player_vy;               // 8.8
uint8_t  on_ground;
uint8_t  coyote, jump_buffer;
uint8_t  facing;                  // 0 right, 1 left
uint8_t  anim_frame;
uint8_t  frame_counter;
uint8_t  joy, joy_prev;
uint8_t  collected;               // collectibles taken (test hook)
uint8_t  dead;                    // touched a hazard
uint8_t  level_done;              // reached the exit

#define SPAWN_X 24
#define SPAWN_Y 72

// ---- collision --------------------------------------------------------------
static uint8_t col_at(uint8_t px, uint8_t py) {
    uint8_t tx = px >> 3, ty = py >> 3;
    if (tx >= LEVEL1_WIDTH || ty >= LEVEL1_HEIGHT) return COL_SOLID;
    return level1_collision[ty * LEVEL1_WIDTH + tx];
}

static uint8_t solid_at(uint8_t px, uint8_t py) {
    return col_at(px, py) == COL_SOLID;
}

// one-way platforms count only when falling onto them from above
static uint8_t floor_at(uint8_t px, uint8_t py) {
    uint8_t c = col_at(px, py);
    return c == COL_SOLID || (c == COL_PLATFORM && (py & 7) == 0 && player_vy >= 0);
}

// ---- game -----------------------------------------------------------------
static void load_level(void) {
    set_bkg_data(0, tiles_TILE_COUNT, tiles_tiles);
    set_bkg_tiles(0, 0, LEVEL1_WIDTH, LEVEL1_HEIGHT, level1_tiles);
    for (uint8_t i = 0; i < LEVEL1_ENTITY_COUNT; i++) {
        if (level1_entities[i].type == ENT_SPAWN) {
            player_x = level1_entities[i].x << 3;
            player_y = (level1_entities[i].y << 3) - 8;   // 16 px tall, feet on the tile
        }
    }
}

static void init(void) {
    DISPLAY_OFF;
    if (_cpu == CGB_TYPE) {
        set_bkg_palette(0, 1, tiles_palettes);
        set_sprite_palette(0, 1, player_palettes);
    } else {
        BGP_REG  = 0xE4;   // 11 10 01 00: index 3 darkest
        OBP0_REG = 0xE4;
    }
    SPRITES_8x16;
    set_sprite_data(0, player_TILE_COUNT, player_tiles);
    set_sprite_tile(0, 0);
    load_level();
    player_vy = 0; on_ground = 0; coyote = 0; jump_buffer = 0;
    facing = 0; anim_frame = 0; frame_counter = 0; collected = 0; dead = 0; level_done = 0;
    SHOW_BKG; SHOW_SPRITES;
    DISPLAY_ON;
}

static void update(void) {
    joy_prev = joy;
    joy = joypad();
    uint8_t pressed = joy & ~joy_prev;

    // horizontal
    if (joy & J_LEFT)  { facing = 1; if (!solid_at(player_x - 1, player_y + 15) && !solid_at(player_x - 1, player_y)) player_x -= WALK_SPEED; }
    if (joy & J_RIGHT) { facing = 0; if (!solid_at(player_x + 8, player_y + 15) && !solid_at(player_x + 8, player_y)) player_x += WALK_SPEED; }

    // jump: buffered press + coyote time
    if (pressed & J_A) jump_buffer = JUMP_BUFFER;
    else if (jump_buffer) jump_buffer--;
    if (jump_buffer && (on_ground || coyote)) {
        player_vy = JUMP_VEL; on_ground = 0; coyote = 0; jump_buffer = 0;
    }
    if (!(joy & J_A) && player_vy < -300) player_vy = -300;   // variable height

    // vertical, 8.8
    player_vy += GRAVITY;
    if (player_vy > MAX_FALL) player_vy = MAX_FALL;
    int8_t dy = (int8_t)(player_vy >> 8);
    uint8_t was_ground = on_ground;
    on_ground = 0;
    while (dy > 0) {   // falling: stop on floor under either foot
        if (floor_at(player_x + 1, player_y + 16) || floor_at(player_x + 6, player_y + 16)) { player_vy = 0; on_ground = 1; break; }
        player_y++; dy--;
    }
    while (dy < 0) {   // rising: stop on ceiling
        if (solid_at(player_x + 1, player_y - 1) || solid_at(player_x + 6, player_y - 1)) { player_vy = 0; break; }
        player_y--; dy++;
    }
    if (dy == 0 && player_vy >= 0 && (floor_at(player_x + 1, player_y + 16) || floor_at(player_x + 6, player_y + 16))) on_ground = 1;
    if (on_ground) coyote = COYOTE_FRAMES;
    else if (was_ground && coyote == 0) coyote = COYOTE_FRAMES;
    else if (coyote) coyote--;

    // hazards and entities (test hooks; a real game does more here)
    if (col_at(player_x + 4, player_y + 15) == COL_HAZARD) dead = 1;
    for (uint8_t i = 0; i < LEVEL1_ENTITY_COUNT; i++) {
        uint8_t ex = level1_entities[i].x << 3, ey = level1_entities[i].y << 3;
        uint8_t hit = player_x < ex + 8 && player_x + 8 > ex && player_y < ey + 8 && player_y + 16 > ey;
        if (!hit) continue;
        if (level1_entities[i].type == ENT_EXIT) level_done = 1;
        if (level1_entities[i].type == ENT_COLLECTIBLE) collected = 1;
    }

    // draw
    if (!on_ground) anim_frame = 0;
    else if (joy & (J_LEFT | J_RIGHT)) { if ((frame_counter & 7) == 0) anim_frame ^= 1; }
    else anim_frame = 0;
    set_sprite_tile(0, anim_frame << 1);
    set_sprite_prop(0, facing ? S_FLIPX : 0);
    move_sprite(0, player_x + 8, player_y + 16);   // OAM origin is (8,16)
    frame_counter++;
}

void main(void) {
    init();
    while (1) {
        vsync();
        update();
    }
}
