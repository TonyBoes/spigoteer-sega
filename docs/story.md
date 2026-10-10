# Spigoteer: "The Golden Spigot" (story script, owner-approved)

Milestone M11a, owner-approved 2026-10-09. Nothing here is wired into the game yet; M11b builds the text engine and
chapter goals, M11c the art. Everything below is original writing.

## The pitch

In the town of Fizzwater, the **Golden Spigot** (it can pour any drink anyone could ever want)
sits on the fountain in the square. Every year the town's best bartender, the **Spigoteer**,
pours its first drink of the festival. This year his rival **Dregs Dribbleton** barges in and
orders "one of everything, all at once". The spigot overloads, goes KA-SPLOOSH and bursts into
nine pieces that land in nine famous venues. Each owner will hand a piece only to a bartender who
keeps their crowd happy. The Spigoteer goes on tour.

Cast (kept small): the Spigoteer, Dregs (comic rival, never a real threat), nine one-note venue
owners, and a narrator (text box only, no portrait).

Running gags:

1. **Dregs is always one scene late.** He bursts into every after-venue scene to grab the piece
   and leaves the venue the way that venue would throw him out (swinging doors, crowd-surfed,
   spun out by plates, carried off on a conveyor...). In the zoo he finally gets help, and in
   the finale he says sorry.
2. **The mustache.** Sadie rates it four tumbleweeds. Aurora knits it a **pink mustache cozy**,
   which it wears for the rest of the game. Manager-Bot scans it, Zizz calls it a "face-broom",
   and the credits confirm it's still on.
3. **Where the pieces ended up.** Each one was being used for something silly: the handle was
   stuck in a piano, the nozzle piped frosting, the knob was on an igloo that has no door, the
   gasket was a robot's hat, the lever was a TV antenna, and the crown sat on a lion.
4. **The payoff.** The spigot can pour anything at all. After nine bars, the Spigoteer pours
   himself a nice cold glass of water.

Family-friendly notes: the saloon's foamy drink is called **sarsaparilla** and the bistro pours
**sparkling grape juice**. The game's art doesn't change, only the words. Nobody gets drunk:
drinks go to thirsty, sleepy, cold or hungry people. Teahouse and igloo: the owners are calm,
warm professionals who speak plain English. Their one-note traits are love of quiet and
knitting. There's no accent writing or put-on dialect anywhere.

## Chapters: goals and twists

Goals are written so the engine can check them with counters it already has or can add cheaply
(serves, empties caught, broken glasses, a timer, patrons reaching the tap). Twists are
optional. Each one changes one existing parameter or adds one small behaviour.

| # | Venue | Owner | Piece | Chapter goal (in-world / engine) | Optional twist |
|---|---|---|---|---|---|
| 1 | Saloon | Sadie Spurs | Handle | "Keep 15 cowboys happy" / serve 15 | None. This is the tutorial chapter, with slow walkers and a generous EMPTY_GAP. |
| 2 | Stadium concession | Coach Blitz | Spout | "Serve 20 fans; a fan at your tap costs two lives" / serve 20, a patron at the tap costs 2 lives (instead of 1) | **Quarters**: patrons come in 4 rushes with short breathers between them. |
| 3 | Lumber lodge | Big June | Valve | "Wake up 18 sleepy lumberjacks" / serve 18 | **Sasquatch sighting**: now and then the Sasquatch strolls past the back of one bar and its patrons stop to stare. That's a free single-bar distraction. |
| 4 | Bistro | Chef Colby | Nozzle | "Serve 20 chefs before the dinner rush" / serve 20 before the timer runs out | **Fine dining**: patrons sip longer, so empties come back bunched together. Fair-empties spacing still applies. |
| 5 | Igloo bar | Aurora | Knob | "20 cocoas before they cool" / serve 20 before the timer runs out | **Icy bars**: full and empty mugs slide faster. |
| 6 | Robot factory | Manager-Bot 3000 | Gasket | "Recycle 25 batteries" / catch 25 empties | **Conveyors**: empties come back faster than full batteries go out. |
| 7 | Teahouse | Hana | Pipe | "Serve with care; a broken cup costs two lives" / clear the venue, a broken glass costs 2 lives (instead of 1) | **Taiko rhythm**: patrons step on the drum beat instead of walking smoothly, which makes them easy to read and hard to rush. |
| 8 | Space lounge | Zizz | Lever | "25 glowing beakers for 3 species" / serve 25 | **Low gravity**: full drinks float more slowly, so you have to lead your throws. |
| 9 | Jungle zoo | Keeper Kiki | Crown | "Serve 30 animals" / serve 30 | **Cheeky monkeys**: now and then a monkey snatches a coconut mid-slide and it comes back as an empty straight away. |

## Shifts

Each chapter plays its venue several times in a row, as shifts: **Opening shift** (about half the
goal, walkers 15 % slower, patrons 15 % further apart), **Happy hour** (the chapter goal above, at
the venue's normal pace; the chapter's twist will apply here), a mini-game slot, **Last call**
(faster walkers, patrons closer together, and the venue's own arrival pattern), then a boss slot.
The mini-game and boss slots are skipped until they are built. Lives: 3 per venue, carried from
shift to shift (a gold medal in the mini-game adds one, up to 4); losing the last one restarts the
venue at its Opening shift. A strict rule (stadium: a fan at the tap; teahouse: a broken cup) costs
2 lives instead of 1. Every shift keeps the chapter's kind of goal. Bars are numbered 1 (top) to 4 (bottom).

| # | Opening shift (in-world / engine) | Happy hour | Last call | Last call arrivals |
|---|---|---|---|---|
| 1 | "Serve 8 cowboys" / serve 8 | "Keep 15 cowboys happy" / serve 15 | "Serve 18 cowboys, one bar at a time" / serve 18 | Stairs down: one patron on each bar in turn, top to bottom. Walk +10 %, spawn -10 %. |
| 2 | "Serve 10 fans; a fan at your tap costs two lives" / serve 10, a fan at the tap costs 2 lives | "Serve 20 fans; a fan at your tap costs two lives" / serve 20, a patron at the tap costs 2 lives | "22 fans rush in; a fan at your tap costs two lives" / serve 22, a fan at the tap costs 2 lives | All bars at once: four fans a moment apart, one on each bar, then a long breather. Walk +5 %, spawn -5 %. |
| 3 | "Wake up 9 sleepy lumberjacks" / serve 9 | "Wake up 18 sleepy lumberjacks" / serve 18 | "Wake up 20, one bar is packed" / serve 20 | Flood bar 2: every other patron comes to bar 2, the rest take turns on the others. Walk +15 %, spawn -15 %. |
| 4 | "Serve 10 chefs before the rush" / serve 10 in 75 s | "Serve 20 chefs before the dinner rush" / serve 20 before the timer runs out | "Serve 22 chefs, tables for two" / serve 22 in 120 s | Pairs: two chefs at once (bars 1 and 3, then 2 and 4), then a longer gap. Walk +15 %, spawn -15 %. |
| 5 | "Serve 10 cocoas before they cool" / serve 10 in 75 s | "20 cocoas before they cool" / serve 20 before the timer runs out | "22 cocoas before they freeze" / serve 22 in 120 s | Zigzag: bars 1, 3, 2, 4, 3, 1, 4, 2, always a jump away from the last. Walk +15 %, spawn -15 %. |
| 6 | "Recycle 12 batteries" / catch 12 empties | "Recycle 25 batteries" / catch 25 empties | "Recycle 28, the batteries pile up" / catch 28 empties | Stairs up: one robot on each bar in turn, bottom to top. Walk +15 %, spawn -15 %. |
| 7 | "Serve 7 guests; a broken cup costs two lives" / 7 guests, a broken glass costs 2 lives | "Serve with care; a broken cup costs two lives" / clear the venue, a broken glass costs 2 lives | "Serve 15 guests; a broken cup costs two lives" / 15 guests, a broken glass costs 2 lives | Flood bar 4: every other guest comes to bar 4. Walk +15 %, spawn -15 %. |
| 8 | "Serve 12 glowing beakers" / serve 12 | "25 glowing beakers for 3 species" / serve 25 | "Serve 28 glowing beakers" / serve 28 | Inside out: two at once on the middle bars, then two on the outer bars. Walk +20 %, spawn -20 %. |
| 9 | "Serve 15 animals" / serve 15 | "Serve 30 animals" / serve 30 | "Stampede! Serve 32 animals" / serve 32 | Stampede: all four bars at once top to bottom, a breather, then all four bottom to top. Walk +20 %, spawn -20 %. |

## Script format

Text box: 18 characters per line, 3 lines per page. Allowed: `A-Z 0-9 . , ! ? ' - :` and space.
Each page below is one speaker line (it picks the speaker's portrait, or his variant for that page: see
"Portraits" in the art list; `NARRATOR` has no portrait)
followed by 1-3 text lines. Pages are separated by blank lines. The text is already wrapped,
so the engine prints it as is. Scene ids are what the engine would call each scene.

---

### INTRO: "The Big Pour"

Picture: Fizzwater town square at night. The Golden Spigot on its fountain bursts apart and nine sparkling pieces fly off in every direction.

```
NARRATOR
ONCE UPON A TAP,
IN FIZZWATER TOWN,
STOOD THE GOLDEN

NARRATOR
SPIGOT. IT COULD
POUR ANY DRINK
ANYONE WANTED!

SPIGOTEER
EACH YEAR, I POUR
THE FIRST DRINK.
NICE AND STEADY.

DREGS
MOVE IT, MUSTACHE!
DREGS POURS FIRST:
ONE OF EVERYTHING!

NARRATOR
GLUG. GLUG. GLUG.
GLUGGA-GLUGGA...
KA-SPLOOOOSH!!!

NARRATOR
THE SPIGOT BURST
INTO NINE PIECES
AND FLEW AWAY!

NARRATOR
NINE VENUES, NINE
OWNERS. EACH WANTS
A GREAT BARTENDER.

SPIGOTEER
THEN I'LL KEEP
NINE CROWDS HAPPY!
MUSTACHE: ONWARD!
```

---

### PRE_SALOON: "Howdy, Pardner"

Picture: dusty saloon front with swinging doors and a hitching post. Sadie leans on the doorframe.

```
SADIE
HOWDY, STRANGER!
I'M SADIE SPURS.
WELCOME TO MY BAR.

SADIE
THAT MUSTACHE? I
RATE IT FOUR
TUMBLEWEEDS. NICE.

SPIGOTEER
I HEAR YOU FOUND
A SHINY PIECE OF
GOLDEN SPIGOT?

SADIE
SURE DID! KEEP 15
THIRSTY COWBOYS
HAPPY, IT'S YOURS.

SADIE
SARSAPARILLA'S ON
TAP. SLIDE 'EM
DOWN THE BAR!
```

### POST_SALOON: "Five Tumbleweeds"

Picture: cowboys and the cowgirl throw their hats in the air while Sadie hands over the golden handle.

```
SADIE
WHOOEE! THAT'S
FIVE TUMBLEWEEDS!
MY TOP RATING!

SADIE
HERE'S YOUR PIECE:
THE HANDLE. GOT
STUCK IN MY PIANO.

DREGS
OUTTA MY WAY! THAT
HANDLE'S MINE! I
CALLED DIBS!

NARRATOR
THE COWBOYS SLID
DREGS STRAIGHT OUT
THE SWINGING DOORS

SPIGOTEER
ONE DOWN, EIGHT
TO GO. NEXT STOP:
THE BIG GAME!
```

---

### PRE_STADIUM: "Game Day"

Picture: stadium concession stand under floodlights. The scoreboard reads HOME 0 VISITORS 0 and Coach Blitz holds a whistle.

```
COACH
TWEET! HUDDLE UP,
ROOKIE! I'M COACH
BLITZ. MY STAND.

COACH
GOT YOUR SPOUT
RIGHT HERE. FOUND
IT AT MIDFIELD.

SPIGOTEER
WHAT'S THE PLAY,
COACH?

COACH
LET ONE FAN REACH
YOUR TAP AND IT
COSTS TWO LIVES!

COACH
THE SODA'S COLD,
THE CROWD IS HOT.
TWEET! GO GO GO!
```

### POST_STADIUM: "Touchdown"

Picture: the scoreboard flashes WIN as Coach dumps a cooler of soda over the Spigoteer and the cheerleaders kick.

```
COACH
TOUCHDOWN! TEAM
SPIGOTEER WINS!
HIT THE SHOWERS!

NARRATOR
SPLOOSH! THE
SPIGOTEER GOT THE
VICTORY SODA BATH.

SPIGOTEER
MY MUSTACHE IS
ALL STICKY. WORTH
IT FOR THE SPOUT!

DREGS
WAIT! I'M HERE FOR
THE SPOUT- HEY!
PUT ME DOWN!

NARRATOR
THE FANS CROWD-
SURFED DREGS ALL
THE WAY OUTSIDE.

COACH
NEXT UP: THE
WOODS. BRING A
SWEATER, ROOKIE!
```

---

### PRE_LUMBER: "Timber!"

Picture: log lodge among snowy pines with a giant coffee pot on the stove. In the window behind Big June, a big hairy shape waves.

```
JUNE
TIMBER! OH, SORRY.
I SAY THAT A LOT.
I'M BIG JUNE.

JUNE
MY LUMBERJACKS RUN
ON COFFEE. AND
THEY'RE SLEEPY.

SPIGOTEER
UM. WHO'S THE BIG
HAIRY FELLA
BEHIND YOU?

JUNE
SASQUATCH? HA!
NO SUCH THING.
NOW, THE JOB:

JUNE
WAKE UP 18 SLEEPY
LUMBERJACKS. THEN
THE VALVE'S YOURS.
```

### POST_LUMBER: "Bigfoot, Big Heart"

Picture: the Sasquatch gently hands the golden valve to the Spigoteer while June looks the other way.

```
JUNE
ALL 18 WIDE AWAKE!
THAT'S WORTH A
VALVE. HERE, UH...

NARRATOR
THE SASQUATCH
HANDED IT OVER,
THEN TIPTOED OFF.

JUNE
SEE? NO SUCH THING
AS A SASQUATCH.
TIMBER!

DREGS
GIMME THAT VALVE!
...WAIT. WHO'S THE
BIG HAIRY FELLA?

NARRATOR
DREGS RAN SO FAST
HE LEFT HIS BOOTS
BEHIND.

SPIGOTEER
3 DOWN! NEXT, A
FANCY BISTRO. BEST
COMB MY MUSTACHE.
```

---

### PRE_BISTRO: "Table for One"

Picture: candlelit bistro with checkered tablecloths. The head chef, pastry chef and grill cook peek through the kitchen pass.

```
COLBY
WELCOME! I AM
CHEF COLBY. YOU
LOOK GOUDA TODAY.

SPIGOTEER
...WAS THAT A
CHEESE PUN?

COLBY
I CAN'T HELP IT.
IT'S NACHO FAULT.
IT'S MINE.

COLBY
MY CHEFS ARE OFF
DUTY AND HUNGRY.
SERVE 20 OF THEM.

COLBY
SPARKLING GRAPE
JUICE, CHILLED.
NOW BRIE QUICK!
```

### POST_BISTRO: "The Cheese Course"

Picture: Colby lifts a silver dome to reveal the golden nozzle while the plate-spinning waiter twirls in the background.

```
COLBY
MAGNIFICENT! YOU
ARE THE BIG
CHEESE NOW!

COLBY
YOUR NOZZLE. MY
PASTRY CHEF USED
IT FOR FROSTING.

SPIGOTEER
IT'S A LITTLE
STICKY. AND
DELICIOUS.

DREGS
I'LL TAKE THAT
NOZZLE, CHEF!
...WHOA, PLATES!

NARRATOR
DREGS GOT TANGLED
IN SPINNING PLATES
AND SPUN AWAY!

COLBY
SAFE TRAVELS,
FRIEND. AND STAY
GRATE!
```

---

### PRE_IGLOO: "Snow Place Like Home"

Picture: a big glowing igloo under the northern lights. Aurora stands in the entrance tunnel with knitting needles and a steaming mug.

```
AURORA
COME IN, COME IN!
I'M AURORA. YOU
LOOK FROZEN SOLID!

AURORA
HERE, I KNIT YOU
SOMETHING: A
MUSTACHE COZY!

SPIGOTEER
IT'S... VERY COZY.
AND VERY PINK.
THANK YOU!

AURORA
MY GUESTS CAME IN
FROM THE COLD.
SERVE 20 COCOAS

AURORA
BEFORE THEY COOL.
AND CAREFUL: THE
BAR IS ICY!
```

### POST_IGLOO: "Warm and Fuzzy"

Picture: the Spigoteer in his pink mustache cozy holds up the golden knob while the penguins wave goodbye.

```
AURORA
EVERY MUG STILL
WARM! TAKE THE
KNOB. IT'S YOURS.

AURORA
IT WAS MY IGLOO'S
DOORKNOB. ODD, AS
IT HAS NO DOOR.

DREGS
HAND OVER THE
KNOB! WHOA, ICY!
WHOA- WHOAAAA!

NARRATOR
DREGS SLID DOWN
THE BAR, OUT THE
TUNNEL, DOWNHILL.

SPIGOTEER
FIVE DOWN! AND MY
MUSTACHE HAS NEVER
BEEN SO TOASTY.
```

---

### PRE_ROBOT: "Beep Boop, Barkeep"

Picture: factory floor with conveyor belts and a big lightning-bolt sign. Robots stand in line and Manager-Bot 3000 sits on a hover platform.

```
MANAGER-BOT
GREETINGS, HUMAN.
I AM MANAGER-BOT
3000. STATUS: HI.

MANAGER-BOT
SCANNING...
MUSTACHE DETECTED.
ALSO A PINK COZY.

SPIGOTEER
IT WAS A GIFT.
I'M HERE ABOUT
THE GASKET.

MANAGER-BOT
MY WORKERS NEED
POWER. RECYCLE 25
EMPTY BATTERIES.

MANAGER-BOT
CAUTION: THE BARS
ARE CONVEYORS.
EMPTIES RUN FAST.
```

### POST_ROBOT: "Does Not Compute"

Picture: the breakdancing robot spins on its dome while Manager-Bot holds out the golden gasket.

```
MANAGER-BOT
RECYCLING: DONE.
STATUS: HAPPY.
BEEP BOOP.

MANAGER-BOT
TAKE THE GASKET.
UNIT 12 WAS USING
IT AS A HAT.

SPIGOTEER
HE LOOKED GREAT
IN IT, HONESTLY.

DREGS
STEP ASIDE, TIN
CANS! THAT GASKET
IS MI- HEY! BELT!

NARRATOR
THE CONVEYOR BELT
CARRIED DREGS TO
BOX 4: RETURNS.

MANAGER-BOT
STATUS: AMUSED.
HA. HA. HA.
```

---

### PRE_TEAHOUSE: "A Quiet Cup"

Picture: a wooden teahouse beside a garden pond under cherry blossoms. Its bamboo fountain is missing a piece.

```
HANA
WELCOME. I AM
HANA, MASTER OF
THIS TEAHOUSE.

SPIGOTEER
HELLO!!! NICE TO
MEET YOU!!! I'M
HERE FOR THE PIPE!

HANA
SHH. HERE, WE
ENJOY THE QUIET.
ALSO THE TEA.

SPIGOTEER
SORRY. I MEAN:
HELLO. NICE TO
MEET YOU.

HANA
YOUR PIPE FELL IN
MY BAMBOO FOUNTAIN
IT FIT PERFECTLY.

HANA
SERVE WITH CARE.
ONE BROKEN CUP
COSTS TWO LIVES.

HANA
AND FOLLOW THE
DRUM. GOOD TEA
HAS A RHYTHM.
```

### POST_TEAHOUSE: "Harmony"

Picture: Hana pours tea for the Spigoteer at a low table while the taiko drummer bows.

```
HANA
NOT ONE CUP
BROKEN. THAT IS
RARE. THANK YOU.

HANA
THE PIPE. MY
FOUNTAIN WILL MISS
IT. TAKE IT HOME.

DREGS
HAND OVER THAT
PIPE!!! I AM VERY
LOUD AND RUDE!!!

NARRATOR
THE DRUMMER STRUCK
ONE MIGHTY BEAT.
DREGS TUMBLED OUT.

HANA
AH. QUIET AGAIN.
MORE TEA?

SPIGOTEER
SEVEN DOWN. NEXT
STOP: OUTER SPACE!
...QUIETLY.
```

---

### PRE_SPACE: "One Small Sip"

Picture: a neon space lounge with a ringed planet in the window. A city bus with a SPACE route sign is parked outside the airlock.

```
NARRATOR
THE SPIGOTEER
TOOK THE BUS TO
OUTER SPACE.

NARRATOR
IT WAS A VERY
LONG BUS RIDE.

ZIZZ
GREETINGS, EARTH
DRINK-SLIDER! I AM
ZIZZ, YOUR HOST!

ZIZZ
YOUR FACE-BROOM
IS MOST HANDSOME!
ALSO VERY PINK.

SPIGOTEER
THANKS. I'M HERE
FOR THE LEVER.

ZIZZ
SERVE 25 GLOWING
BEAKERS TO MY
GUESTS. ALL THREE!

ZIZZ
LOW GRAVITY HERE:
DRINKS FLOAT SLOW.
HOLD YOUR SPOONS!
```

### POST_SPACE: "Out of This World"

Picture: the alien musician plays a many-armed keytar while Zizz floats up holding the golden lever.

```
ZIZZ
YOU ARE THE CAT'S
PAJAMAS! THE BEE'S
ELBOWS!

ZIZZ
TAKE THE LEVER.
WE USED IT AS A
TV ANTENNA.

SPIGOTEER
WHAT DID YOU
WATCH?

ZIZZ
A SHOW ABOUT A
MUSTACHED MAN WHO
SLIDES DRINKS.

DREGS
FINALLY, I'M ON
TIME! GIVE ME THE-
WHY AM I FLOATING?

NARRATOR
DREGS DRIFTED OFF
INTO SPACE. LUCKY
FOR HIM, A BUS.

SPIGOTEER
ONE PIECE LEFT!
IT'S A JUNGLE OUT
THERE. LITERALLY.
```

---

### PRE_ZOO: "Call of the Wild"

Picture: a jungle zoo bar under hanging vines. Leo the lion lounges on a rock with the golden crown on his mane, and Keeper Kiki crouches in the ferns.

```
KIKI
AND HERE WE SEE
THE RARE MUSTACHED
BARTENDER...

SPIGOTEER
HI. ARE YOU
NARRATING ME?

KIKI
IT SPEAKS! HOW
EXTRAORDINARY.
I'M KEEPER KIKI.

KIKI
THE LAST PIECE,
THE CROWN, IS ON
LEO THE LION.

KIKI
SERVE 30 THIRSTY
ANIMALS AND HE MAY
JUST HAND IT OVER.

KIKI
WATCH THE MONKEYS.
THEY LOVE TO STEAL
A COCONUT.
```

### POST_ZOO: "King of the Tap"

Picture: Leo places the golden crown on the Spigoteer's head while the flamingos high-kick behind them.

```
KIKI
REMARKABLE. THE
LION APPROACHES...
...AND PURRS.

NARRATOR
LEO PLACED THE
CROWN ON THE
SPIGOTEER'S HEAD.

SPIGOTEER
ALL NINE PIECES!
...WAIT. WHERE'S
DREGS?

DREGS
RIGHT HERE. AND
THIS TIME I'M-
OH NO. MONKEYS.

NARRATOR
THE MONKEYS STOLE
HIS SHOES, HIS HAT
AND HIS DIGNITY.

SPIGOTEER
COME ON, DREGS.
LET'S GO HOME.
I'LL POUR YOU ONE.
```

---

### FINALE: "The First Pour"

Picture: Fizzwater square by day. The restored Golden Spigot gleams on its fountain, and all nine owners plus a sheepish Dregs gather round as it pours a glass of water.

```
NARRATOR
BACK IN FIZZWATER,
THE NINE PIECES
CLICKED TOGETHER.

NARRATOR
THE GOLDEN SPIGOT
SHONE ONCE MORE!
THE CROWD GASPED.

SADIE
SIX TUMBLEWEEDS!
I DIDN'T KNOW I
HAD SIX!

DREGS
SORRY I BROKE IT.
YOU POUR FIRST.
YOU EARNED IT.

SPIGOTEER
IT CAN POUR ANY
DRINK ANYONE COULD
EVER WANT. SO...

SPIGOTEER
...I'LL HAVE A
NICE COLD GLASS
OF WATER.

NARRATOR
AFTER NINE BARS,
IT WAS THE BEST
DRINK EVER POURED.

SPIGOTEER
NOW, WHO'S
THIRSTY? FIRST
ROUND'S ON ME!
```

### CREDITS: "Last Call"

Picture: the Golden Spigot drips over the scrolling credits while Dregs, in an apron, mops the floor in the corner.

```
NARRATOR
DREGS NOW WORKS
AS A BUSBOY. HE
LOVES IT. MOSTLY.

NARRATOR
THE SASQUATCH
SELLS COFFEE NOW.
JUNE DOUBTS IT.

NARRATOR
AND THE PINK
MUSTACHE COZY?
STILL WORN DAILY.

NARRATOR
THANKS FOR
PLAYING SPIGOTEER!
LAST CALL!
```

---

## Art list

### Portraits (56x56 busts, one per speaker; DMG 4 shades, CGB up to 3 BG palettes, an optional 1-OBJ accent)

The approved style (owner, 2026-10-10: style S3 of the portrait study). Each portrait is a 56x56 bust (7x7 tiles) in a
framed panel on the left over the venue backdrop, standing on the text box (the frame's bottom edge is the box's top
panel), facing right toward the Spigoteer at his taps; light from the upper right.

* Source: `assets/story/portraits/<name>.txt` in the portrait-v2 colour-key format: `@size 56 56`, `@maxpal 3`, an
  `@key` table (`<char> <DMG shade 0-3> <#rrggbb> <name> [obj=<base char>]`), then the pixels, one key per pixel. The DMG
  shade of a key is its BG colour index, so one set of tiles serves both models; on CGB each 8x8 tile picks one of up to
  3 palettes whose slot k is the colour of shade k. Two colours on one shade in a tile cannot be shown: the build fails.
* An `obj=` key is a CGB-only accent drawn by one 8x16 OBJ over the BG (Sadie's gold star); DMG shows the base key's
  shade underneath. At most one per portrait in this style (3 sprites on a line with the Spigoteer's 2).
* Budget: at most 44 unique tiles a portrait (no flips), 3 CGB BG palettes (slots 2-4), the background shade 2 with a
  per-character CGB colour, skin and whites shade 0, outline shade 3.

All done (approved art imported pixel-exact, 2026-10-10): **SPIGOTEER, SADIE, DREGS, COACH, JUNE, COLBY, AURORA,
MANAGER-BOT, HANA, ZIZZ, KIKI**, and two variants. There are no placeholders left: a speaker without art fails the build.
DREGS's main portrait is the sheepish drawing (owner's choice; it replaced the first approved Dregs).

Variants (`assets/story/portraits.json` "variants": a range of pages in script order, resolved per page by
`tools/gen_story.py`; the build fails on a range that names no scene or page, whose given page is not the speaker's, that
overlaps another variant of his or that no page uses):

| Variant | Source | Pages |
|---|---|---|
| SPIGOTEER COZY | `spigoteer_cozy.txt` | From PRE_IGLOO page 3 (his "IT'S... VERY COZY." right after Aurora knits it on page 2) to the end of the game: every Spigoteer page of PRE_IGLOO through FINALE (CREDITS has none). |
| DREGS SORRY | `dregs_sorry.txt` | FINALE page 4, his apology "SORRY I BROKE IT." (his only FINALE page). |

| Portrait | One line |
|---|---|
| SPIGOTEER | Big curled mustache, bartender's apron and bow tie, confident grin. |
| SPIGOTEER (cozy) | The same with the pink knitted mustache cozy, from PRE_IGLOO page 3 onward. |
| DREGS | Lanky rival with a scraggly little mustache and a crooked bow tie, sheepish. His FINALE apology has its own variant (hand behind his head). |
| SADIE | Small saloon owner, huge hat, sheriff-style star badge, big laugh. |
| COACH | Coach Blitz: ball cap, whistle in his teeth, clipboard. |
| JUNE | Big June: red plaid, knit beanie, axe over her shoulder, cheerful. |
| COLBY | Chef Colby: tall toque, wedge-of-cheese pin, twinkle in his eye. |
| AURORA | Aurora: warm smile, fur-trimmed parka hood, knitting needles. |
| MANAGER-BOT | Manager-Bot 3000: boxy head, single screen-face showing a smile, antenna. |
| HANA | Tea master: calm expression, simple work kimono and apron, holding a tea whisk. Dignified, not a caricature. |
| ZIZZ | Zizz: round jelly-like alien with three eyes and a bow tie, glowing. |
| KIKI | Keeper Kiki: safari hat, binoculars, finger to her lips. |
| NARRATOR | No portrait. The text box runs full width, or shows a small golden spigot icon. |

### Still pictures (one per scene, about 160x96 above the text box)

| Scene | One line |
|---|---|
| INTRO | Night square, the Golden Spigot bursting and nine pieces flying off. |
| PRE_SALOON | Saloon front with swinging doors, Sadie in the doorway. |
| POST_SALOON | Cowboys tossing hats; Sadie hands over the handle. |
| PRE_STADIUM | Concession stand under floodlights, scoreboard 0-0, Coach with whistle. |
| POST_STADIUM | Soda-cooler shower on the Spigoteer; scoreboard reads WIN. |
| PRE_LUMBER | Pine lodge, giant coffee pot, a Sasquatch waving in the window behind June. |
| POST_LUMBER | The Sasquatch hands over the valve; June looks away. |
| PRE_BISTRO | Candlelit bistro, three chefs peeking through the kitchen pass. |
| POST_BISTRO | Silver dome lifted to reveal the nozzle; plate spinner behind. |
| PRE_IGLOO | Glowing igloo under the northern lights, Aurora knitting at the entrance. |
| POST_IGLOO | Spigoteer in the pink cozy with the knob; penguins waving. |
| PRE_ROBOT | Conveyor belts, big lightning-bolt sign, Manager-Bot on its platform. |
| POST_ROBOT | Breakdancing robot on its dome; Manager-Bot offers the gasket. |
| PRE_TEAHOUSE | Teahouse by a pond, cherry blossoms, bamboo fountain missing a pipe. |
| POST_TEAHOUSE | Hana pouring tea at a low table; taiko drummer bows. |
| PRE_SPACE | Neon lounge, ringed planet in the window, a city bus parked at the airlock. |
| POST_SPACE | Alien musician with a many-armed keytar; Zizz floats with the lever. |
| PRE_ZOO | Jungle bar under vines, Leo wearing the golden crown, Kiki in the ferns. |
| POST_ZOO | Leo crowns the Spigoteer; flamingos high-kick behind. |
| FINALE | Restored spigot gleaming by day, nine owners and Dregs around it, a glass of water. |
| CREDITS | Spigot dripping over the credits, Dregs mopping in an apron. |

Reuse: the nine golden pieces can share one small sprite sheet (handle, spout, valve, nozzle,
knob, gasket, pipe, lever, crown). A between-chapter "spigot progress" screen that fills in one
piece per chapter would reuse them for free.
