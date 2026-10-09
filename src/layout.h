// Screen layout (20x18 tiles). Plain numeric defines so tests/ can parse them.
//   row 0        HUD
//   rows 1-4     stage (sign, curtains, platform edge); no sprites here except M5's dancers
//   bar b        rows BAR_TOP_ROW(b) .. +2: two wall rows (patrons) + one counter row
//   row 17       floor
#ifndef LAYOUT_H
#define LAYOUT_H
#define HUD_ROW           0
#define STAGE_FIRST_ROW   1
#define STAGE_LAST_ROW    4     // the platform edge
#define BAR_FIRST_ROW     5
#define BAR_ROW_STRIDE    3     // wall, wall, counter
#define BAR_COUNTER_DROW  2     // counter row = BAR_TOP_ROW(b) + this
#define FLOOR_ROW        17
#define MUG_DY            4     // mug/fill/glass sprite top, in px below the bar's top (counter surface under its base)
#define BAR_TOP_ROW(b)      (BAR_FIRST_ROW + BAR_ROW_STRIDE * (b))
#define BAR_COUNTER_ROW(b)  (BAR_TOP_ROW(b) + BAR_COUNTER_DROW)
#define BAR_TOP_Y(b)        (BAR_TOP_ROW(b) * 8)          // screen y of the bar's first pixel row
#define BAR_COUNTER_Y(b)    (BAR_COUNTER_ROW(b) * 8)
#endif
