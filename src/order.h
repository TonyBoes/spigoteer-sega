// The order the story plays its venues in (owner 2026-11-07, the story map import): the saloon, the stadium, the bistro, the igloo, the lumber lodge, the robot factory, The Chrome Cow, the
// teahouse, the zoo, the space lounge. A CHAPTER is a position in that order (story_progress, the map's stop, the saved progress, the score carried from chapter to chapter, the debug box's step; story_chapter itself holds the VENUE being played);
// a VENUE is the content: the theme / patron group (cur_group), the level row, the tune, the scenes (SC_PRE_SALOON + 2 * venue), the goals, the steps, the boss, the mini-game, the
// pour. The venue ids keep the order they were built in (0 saloon, 1 stadium, 2 lodge, 3 bistro, 4 igloo, 5 factory ...): VEN(c) is the venue played as chapter c, POS(v) the chapter of venue v.
// tools/gen_smap_world.py checks this table against the map's order (assets/smap/world.json).
#ifndef ORDER_H
#define ORDER_H
static const uint8_t ven_at[10] = { 0, 1, 3, 4, 2, 5, 6, 7, 8, 9 };
static const uint8_t pos_of[10] = { 0, 1, 4, 2, 3, 5, 6, 7, 8, 9 };
#define VEN(c) (ven_at[(c)])
#define POS(v) (pos_of[(v)])
#endif
