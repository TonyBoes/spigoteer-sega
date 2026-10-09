; Skeleton game: one-screen platformer, RGBDS 1.x syntax, hardware.inc v6 names.
; Replace freely; keep the shape.
;
; Everything a test can assert on is an exported WRAM label (wPlayerX ...),
; so it appears in build/game.sym and tests/ can read it by name.
;
; Conventions:
;   positions in pixels; velocity wPlayerVY is 8.8 fixed point, little endian
;   one frame = halt until VBlank -> read pad -> Update -> write shadow OAM;
;   the VBlank handler DMAs shadow OAM from a routine copied into HRAM
;   DMG and CGB both work: rgbfix -c marks the cart CGB-compatible and Init
;   writes grey CGB palettes when it finds itself on a CGB (a == $11 at boot)

INCLUDE "hardware.inc"
INCLUDE "level1.asm"          ; Level1Tiles/Collision/Entities + COL_*/ENT_* (generated)

; ---- tunables ---------------------------------------------------------------
DEF GRAVITY       EQU 48      ; 8.8 per frame
DEF JUMP_VEL      EQU -900    ; 8.8, negative is up
DEF JUMP_CUT      EQU -300    ; vy clamps to this when A is released early
DEF MAX_FALL      EQU 1024
DEF COYOTE_FRAMES EQU 6
DEF JUMP_BUFFER   EQU 6

; joypad byte: 1 = pressed, directions high nibble, buttons low nibble
DEF PADB_DOWN  EQU 7
DEF PADB_UP    EQU 6
DEF PADB_LEFT  EQU 5
DEF PADB_RIGHT EQU 4
DEF PADB_START EQU 3
DEF PADB_SELECT EQU 2
DEF PADB_B     EQU 1
DEF PADB_A     EQU 0

; ---- memory ------------------------------------------------------------------
SECTION "Shadow OAM", WRAM0, ALIGN[8]
wShadowOAM:: ds 40 * 4

SECTION "Game state", WRAM0
wPlayerX::      db      ; top-left of the 8x16 sprite, pixels
wPlayerY::      db
wPlayerVY::     dw      ; 8.8 signed
wOnGround::     db
wCoyote::       db
wJumpBuffer::   db
wFacing::       db      ; 0 right, 1 left
wAnimFrame::    db
wFrameCounter:: db
wJoy::          db
wJoyPrev::      db
wPressed::      db
wCollected::    db
wDead::         db
wLevelDone::    db
wVBlankDone::   db
wDY::           db      ; scratch: signed pixels to move this frame
wWasGround::    db
wIsCGB::        db

SECTION "HRAM", HRAM
hOAMDMA:: ds 10         ; the DMA routine lives here (code below is copied in)

; ---- interrupts and header ---------------------------------------------------
SECTION "VBlank vector", ROM0[$0040]
    push af
    call hOAMDMA
    ld a, 1
    ld [wVBlankDone], a
    pop af
    reti

SECTION "Header", ROM0[$0100]
    nop
    jp EntryPoint
    ds $150 - @, 0          ; rgbfix fills the header

; ---- init -------------------------------------------------------------------
SECTION "Init", ROM0

EntryPoint:
    di
    cp $11                  ; boot ROM leaves a = $11 on CGB
    jr nz, :+
    ld a, 1
:   ld [wIsCGB], a
    ld sp, $E000

    ; wait for VBlank, then turn the LCD off so VRAM is freely writable
.waitVBlank
    ldh a, [rLY]
    cp 144
    jr c, .waitVBlank
    xor a
    ldh [rLCDC], a

    ; clear WRAM state and shadow OAM
    ld hl, wShadowOAM
    ld bc, 40 * 4
    call ZeroMem
    ld hl, wPlayerX
    ld bc, wIsCGB - wPlayerX
    call ZeroMem

    ; DMA routine -> HRAM
    ld hl, OAMDMACode
    ld de, hOAMDMA
    ld bc, OAMDMACodeEnd - OAMDMACode
    call MemCopy

    ; background tiles -> $9000 (LCDC "block 2/1" addressing, ids 0..127 at $9000)
    ld hl, TilesData
    ld de, $9000
    ld bc, TilesDataEnd - TilesData
    call MemCopy
    ; sprite tiles -> $8000
    ld hl, PlayerData
    ld de, $8000
    ld bc, PlayerDataEnd - PlayerData
    call MemCopy
    ; tilemap: 20 columns of each of 18 rows into the 32-wide hardware map
    ld hl, Level1Tiles
    ld de, $9800
    ld b, Level1Height
.mapRow
    ld c, Level1Width
.mapCol
    ld a, [hl+]
    ld [de], a
    inc de
    dec c
    jr nz, .mapCol
    ld a, e                 ; de += 32 - width
    add 32 - Level1Width
    ld e, a
    jr nc, :+
    inc d
:   dec b
    jr nz, .mapRow

    ; palettes
    ld a, %11100100
    ldh [rBGP], a
    ldh [rOBP0], a
    ld a, [wIsCGB]
    or a
    call nz, SetCGBPalettes

    ; spawn: find the ENT_SPAWN entity
    ld hl, Level1Entities
.findSpawn
    ld a, [hl+]
    cp ENT_SPAWN
    jr z, .spawnFound
    inc hl
    inc hl
    ld a, l
    cp LOW(Level1EntitiesEnd)
    jr nz, .findSpawn
    ld a, h
    cp HIGH(Level1EntitiesEnd)
    jr nz, .findSpawn
    jr .spawnDone
.spawnFound
    ld a, [hl+]
    add a
    add a
    add a
    ld [wPlayerX], a
    ld a, [hl]
    add a
    add a
    add a
    sub 8                   ; 16 px tall: feet on the tile
    ld [wPlayerY], a
.spawnDone

    ; LCD on: BG from $9800, tiles 0..127 at $9000, 8x16 sprites
    ld a, LCDC_ON | LCDC_BG_9800 | LCDC_BLOCK21 | LCDC_OBJ_16 | LCDC_OBJS | LCDC_BG
    ldh [rLCDC], a
    ld a, IE_VBLANK
    ldh [rIE], a
    xor a
    ldh [rIF], a
    ei

MainLoop:
    halt
    nop
    ld a, [wVBlankDone]
    or a
    jr z, MainLoop
    xor a
    ld [wVBlankDone], a
    call Update
    jr MainLoop

; ---- per-frame update --------------------------------------------------------
SECTION "Update", ROM0

Update:
    ld a, [wJoy]
    ld [wJoyPrev], a
    call ReadJoypad
    ld [wJoy], a
    ld b, a
    ld a, [wJoyPrev]
    cpl
    and b
    ld [wPressed], a

    ; -- horizontal, blocked by solid tiles beside head and feet
    ld a, [wJoy]
    bit PADB_LEFT, a
    jr z, .noLeft
    ld a, 1
    ld [wFacing], a
    ld a, [wPlayerX]
    dec a
    ld b, a
    call SideClear          ; Z = blocked
    jr z, .noLeft
    ld hl, wPlayerX
    dec [hl]
.noLeft
    ld a, [wJoy]
    bit PADB_RIGHT, a
    jr z, .noRight
    xor a
    ld [wFacing], a
    ld a, [wPlayerX]
    add 8
    ld b, a
    call SideClear          ; Z = blocked
    jr z, .noRight
    ld hl, wPlayerX
    inc [hl]
.noRight

    ; -- jump: buffered press + coyote time
    ld a, [wPressed]
    bit PADB_A, a
    jr z, .noNewPress
    ld a, JUMP_BUFFER
    ld [wJumpBuffer], a
    jr .bufferDone
.noNewPress
    ld a, [wJumpBuffer]
    or a
    jr z, .bufferDone
    dec a
    ld [wJumpBuffer], a
.bufferDone
    ld a, [wJumpBuffer]
    or a
    jr z, .noJump
    ld a, [wOnGround]
    ld b, a
    ld a, [wCoyote]
    or b
    jr z, .noJump
    ld hl, wPlayerVY
    ld a, LOW(JUMP_VEL)
    ld [hl+], a
    ld a, HIGH(JUMP_VEL)
    ld [hl], a
    xor a
    ld [wOnGround], a
    ld [wCoyote], a
    ld [wJumpBuffer], a
.noJump

    ; -- variable jump height: A released while rising fast -> clamp to JUMP_CUT
    ld a, [wJoy]
    bit PADB_A, a
    jr nz, .held
    ld a, [wPlayerVY + 1]
    bit 7, a
    jr z, .held             ; not rising
    cp HIGH(JUMP_CUT)       ; both negative: unsigned compare works
    jr c, .cut
    jr nz, .held
    ld a, [wPlayerVY]
    cp LOW(JUMP_CUT)
    jr nc, .held
.cut
    ld hl, wPlayerVY
    ld a, LOW(JUMP_CUT)
    ld [hl+], a
    ld a, HIGH(JUMP_CUT)
    ld [hl], a
.held

    ; -- gravity, clamp
    ld hl, wPlayerVY
    ld a, [hl]
    add GRAVITY
    ld [hl+], a
    ld a, [hl]
    adc 0
    ld [hl], a
    bit 7, a
    jr nz, .noClamp
    cp HIGH(MAX_FALL)
    jr c, .noClamp
    ld hl, wPlayerVY
    ld a, LOW(MAX_FALL)
    ld [hl+], a
    ld a, HIGH(MAX_FALL)
    ld [hl], a
.noClamp

    ; -- vertical movement one pixel at a time: dy = high byte of vy
    ld a, [wPlayerVY + 1]
    ld [wDY], a
    ld a, [wOnGround]
    ld [wWasGround], a
    xor a
    ld [wOnGround], a
.vertLoop
    ld a, [wDY]
    or a
    jr z, .vertDone
    bit 7, a
    jr nz, .rising
    call FeetOnFloor        ; Z = floor under the feet at y+16
    jr nz, .fallStep
    xor a
    ld [wPlayerVY], a
    ld [wPlayerVY + 1], a
    inc a
    ld [wOnGround], a
    jr .vertDone
.fallStep
    ld hl, wPlayerY
    inc [hl]
    ld hl, wDY
    dec [hl]
    jr .vertLoop
.rising
    ld a, [wPlayerY]
    dec a
    ld c, a
    ld a, [wPlayerX]
    inc a
    ld b, a
    call SolidAt
    jr z, .ceiling
    ld a, [wPlayerX]
    add 6
    ld b, a
    call SolidAt
    jr z, .ceiling
    ld hl, wPlayerY
    dec [hl]
    ld hl, wDY
    inc [hl]
    jr .vertLoop
.ceiling
    xor a
    ld [wPlayerVY], a
    ld [wPlayerVY + 1], a
.vertDone
    ; standing on something after all that?
    ld a, [wPlayerVY + 1]
    bit 7, a
    jr nz, .coyote
    call FeetOnFloor
    jr nz, .coyote
    ld a, 1
    ld [wOnGround], a
.coyote
    ld a, [wOnGround]
    or a
    jr z, .inAir
    ld a, COYOTE_FRAMES
    ld [wCoyote], a
    jr .coyoteDone
.inAir
    ld a, [wWasGround]
    or a
    jr z, .decCoyote
    ld a, [wCoyote]
    or a
    jr nz, .decCoyote
    ld a, COYOTE_FRAMES
    ld [wCoyote], a
    jr .coyoteDone
.decCoyote
    ld a, [wCoyote]
    or a
    jr z, .coyoteDone
    dec a
    ld [wCoyote], a
.coyoteDone

    ; -- hazard under the feet
    ld a, [wPlayerX]
    add 4
    ld b, a
    ld a, [wPlayerY]
    add 15
    ld c, a
    call ColAt
    cp COL_HAZARD
    jr nz, .noHazard
    ld a, 1
    ld [wDead], a
.noHazard

    ; -- entities: 3 bytes each (type, tile x, tile y), AABB vs the 8x16 player
    ld hl, Level1Entities
.entLoop
    ld a, l
    cp LOW(Level1EntitiesEnd)
    jr nz, .entCheck
    ld a, h
    cp HIGH(Level1EntitiesEnd)
    jr z, .entDone
.entCheck
    ld a, [hl+]
    ld d, a                 ; type
    ld a, [hl+]
    add a
    add a
    add a
    ld e, a                 ; ex
    ld a, [hl+]
    add a
    add a
    add a
    ld c, a                 ; ey
    ld a, [wPlayerX]        ; px - ex in -7..7  <=>  px - ex + 7 < 15
    sub e
    add 7
    cp 15
    jr nc, .entLoop
    ld a, [wPlayerY]        ; py - ey in -15..7 <=>  py - ey + 15 < 23
    sub c
    add 15
    cp 23
    jr nc, .entLoop
    ld a, d
    cp ENT_EXIT
    jr nz, .notExit
    ld a, 1
    ld [wLevelDone], a
.notExit
    ld a, d
    cp ENT_COLLECTIBLE
    jr nz, .entLoop
    ld a, 1
    ld [wCollected], a
    jr .entLoop
.entDone

    ; -- animation and shadow OAM
    ld a, [wOnGround]
    or a
    jr z, .animIdle
    ld a, [wJoy]
    and (1 << PADB_LEFT) | (1 << PADB_RIGHT)
    jr z, .animIdle
    ld a, [wFrameCounter]
    and 7
    jr nz, .animDone
    ld a, [wAnimFrame]
    xor 1
    ld [wAnimFrame], a
    jr .animDone
.animIdle
    xor a
    ld [wAnimFrame], a
.animDone
    ld hl, wShadowOAM
    ld a, [wPlayerY]
    add 16                  ; OAM origin is (8,16)
    ld [hl+], a
    ld a, [wPlayerX]
    add 8
    ld [hl+], a
    ld a, [wAnimFrame]
    add a                   ; frame * 2 tiles (8x16 mode uses even tile ids)
    ld [hl+], a
    ld a, [wFacing]
    or a
    ld a, 0
    jr z, :+
    ld a, OAM_XFLIP
:   ld [hl], a
    ld hl, wFrameCounter
    inc [hl]
    ret

; ---- collision helpers ----------------------------------------------------------
SECTION "Collision", ROM0

; b = px, c = py  ->  a = collision kind. Outside the map counts as solid.
; Preserves b, c. Clobbers hl, de.
ColAt::
    ld a, b
    cp Level1Width * 8
    jr nc, .outside
    ld a, c
    cp Level1Height * 8
    jr nc, .outside
    srl a                   ; ty
    srl a
    srl a
    ld l, a
    ld h, 0
    add hl, hl              ; ty*2
    add hl, hl              ; ty*4
    ld d, h
    ld e, l
    add hl, hl              ; ty*8
    add hl, hl              ; ty*16
    add hl, de              ; ty*20  (= Level1Width; change this if the width changes)
    ld a, b
    srl a
    srl a
    srl a
    ld e, a
    ld d, 0
    add hl, de
    ld de, Level1Collision
    add hl, de
    ld a, [hl]
    ret
.outside
    ld a, COL_SOLID
    ret

; b = px, c = py  ->  Z if solid
SolidAt::
    call ColAt
    cp COL_SOLID
    ret

; b = px, c = py  ->  Z if the player can stand here: solid, or a one-way
; platform when the feet are exactly at its top edge and we are not rising
FloorAt::
    call ColAt
    cp COL_SOLID
    ret z
    cp COL_PLATFORM
    jr nz, .no
    ld a, c
    and 7
    jr nz, .no
    ld a, [wPlayerVY + 1]
    bit 7, a
    jr nz, .no
    xor a                   ; Z
    ret
.no
    or 1                    ; NZ
    ret

; Z if floor under either foot at y+16
FeetOnFloor::
    ld a, [wPlayerY]
    add 16
    ld c, a
    ld a, [wPlayerX]
    inc a
    ld b, a
    call FloorAt
    ret z
    ld a, [wPlayerX]
    add 6
    ld b, a
    jp FloorAt

; b = x column to test (already x-1 or x+8)  ->  Z if head or feet row is solid there (blocked)
SideClear:
    ld a, [wPlayerY]
    add 15
    ld c, a
    call SolidAt
    ret z
    ld a, [wPlayerY]
    ld c, a
    jp SolidAt

; ---- utilities --------------------------------------------------------------------
SECTION "Utilities", ROM0

; a = joypad byte: directions in the high nibble, buttons in the low, 1 = pressed
ReadJoypad::
    ld a, JOYP_GET_CTRL_PAD
    ldh [rJOYP], a
    ldh a, [rJOYP]          ; settle
    ldh a, [rJOYP]
    cpl
    and JOYP_INPUTS
    swap a
    ld b, a
    ld a, JOYP_GET_BUTTONS
    ldh [rJOYP], a
    ldh a, [rJOYP]
    ldh a, [rJOYP]
    ldh a, [rJOYP]
    cpl
    and JOYP_INPUTS
    or b
    ld b, a
    ld a, JOYP_GET_NONE
    ldh [rJOYP], a
    ld a, b
    ret

; hl = src, de = dst, bc = len
MemCopy::
    ld a, [hl+]
    ld [de], a
    inc de
    dec bc
    ld a, b
    or c
    jr nz, MemCopy
    ret

; hl = dst, bc = len
ZeroMem::
    xor a
    ld [hl+], a
    dec bc
    ld a, b
    or c
    jr nz, ZeroMem
    ret

; copied to HRAM: start OAM DMA from wShadowOAM and wait ~160 us
OAMDMACode:
    ld a, HIGH(wShadowOAM)
    ldh [rDMA], a
    ld a, 40
.wait
    dec a
    jr nz, .wait
    ret
OAMDMACodeEnd:

; CGB: palette 0 of BG and OBJ as the same 4 greys (index 0 white). Palette
; RAM is only safely writable with the LCD off or during VBlank; we are off.
SetCGBPalettes:
    ld a, BGPI_AUTOINC
    ldh [rBGPI], a
    ld hl, GreyPalette
    ld c, 8
.bg
    ld a, [hl+]
    ldh [rBGPD], a
    dec c
    jr nz, .bg
    ld a, OBPI_AUTOINC
    ldh [rOBPI], a
    ld hl, GreyPalette
    ld c, 8
.obj
    ld a, [hl+]
    ldh [rOBPD], a
    dec c
    jr nz, .obj
    ret

GreyPalette:    ; BGR555 little endian: white, light, dark, black
    dw $7FFF, $5294, $294A, $0000

; ---- assets (generated into build/ by the Makefile) ------------------------------
SECTION "Tiles", ROM0
TilesData:  INCBIN "tiles.2bpp"
TilesDataEnd:
PlayerData: INCBIN "player.2bpp"
PlayerDataEnd:
