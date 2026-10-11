# Spigoteer: "The Golden Spigot" (story script, owner-approved)

Milestone M11a, owner-approved 2026-10-09. Nothing here is wired into the game yet; M11b builds the text engine and
chapter goals, M11c the art. Everything below is original writing.

**PROPOSAL (2026-10-10), awaiting owner approval: a 10th venue, The Chrome Cow.** It is the toughest-looking bar
in Fizzwater, all mohawks, leather and studs, and everyone in it very politely orders an ice-cold glass of milk. It
becomes chapter 7, before the teahouse, in story and arcade order. Owner's second decision (same day): the space
lounge moves to the end. The new order: 1 saloon, 2 stadium, 3 lumber lodge, 4 bistro, 5 igloo, 6 robot factory,
7 The Chrome Cow, 8 teahouse, 9 jungle zoo, 10 space lounge. Owner's decisions (2026-10-11): the name **The Chrome
Cow** is final; the mosh pit is on in its Last call too ("sure, we'll try it"); its tune is "Drunken Sailor"
(traditional sea shanty, public domain), played fast and punky. Difficulty stays tied to the position, not the venue:
the zoo takes the goals and pace chapter 9 had, space those of the last chapter, and space now leads into the finale
(the "last piece", "all ten pieces" and Dregs's rescue beats move from the zoo to space).
Owner **Granny Throttle**, piece the **drip tray**, twist the **mosh pit** (docs/minigames_bosses.md section 9),
mini-game **Milk Run** and boss **Duke** (sections 4.10 and 3.12 there), engine checklist in docs/venue10_impact.md.
The prose of this file (pitch, cast, gags, pictures, art list) already counts ten venues. The parts the build
reads stay as built until the engine change lands: tools/gen_story.py compiles every `### ID: "Title"` scene block
and checks the chapters and shifts tables against the game. So the new scenes' headings carry `PROPOSAL` (the build
skips them), proposed edits to built pages sit in separate `text` blocks under their scenes, and the new table rows
are in their own tables below the built ones. The engine change folds them in and drops these markers.

## The pitch

In the town of Fizzwater, the **Golden Spigot** (it can pour any drink anyone could ever want)
sits on the fountain in the square. Every year the town's best bartender, the **Spigoteer**,
pours its first drink of the festival. This year his rival **Dregs Dribbleton** barges in and
orders "one of everything, all at once". The spigot overloads, goes KA-SPLOOSH and bursts into
ten pieces that land in ten famous venues. Each owner will hand a piece only to a bartender who
keeps their crowd happy. The Spigoteer goes on tour.

Cast (kept small): the Spigoteer, Dregs (comic rival, never a real threat), ten one-note venue
owners, and a narrator (text box only, no portrait).

Running gags:

1. **Dregs is always one scene late.** He bursts into every after-venue scene to grab the piece
   and leaves the venue the way that venue would throw him out (swinging doors, crowd-surfed,
   spun out by plates, carried off on a conveyor, blown out by one loud chord...). In space he finally
   gets help (the Spigoteer asks Zizz to beam him back down), and in the finale he says sorry.
2. **The mustache.** Sadie rates it four tumbleweeds. Aurora knits it a **pink mustache cozy**,
   which it wears for the rest of the game. Manager-Bot scans it, Zizz calls it a "face-broom",
   and the credits confirm it's still on.
3. **Where the pieces ended up.** Each one was being used for something silly: the handle was
   stuck in a piano, the nozzle piped frosting, the knob was on an igloo that has no door, the
   gasket was a robot's hat, the drip tray was the house band's cymbal, the crown sat on a lion, and the
   lever was a TV antenna.
4. **The payoff.** The spigot can pour anything at all. After ten bars, the Spigoteer pours
   himself a nice cold glass of water.

Family-friendly notes: the saloon's foamy drink is called **sarsaparilla** and the bistro pours
**sparkling grape juice**. The game's art doesn't change, only the words. Nobody gets drunk:
drinks go to thirsty, sleepy, cold or hungry people. Teahouse and igloo: the owners are calm,
warm professionals who speak plain English. Their one-note traits are love of quiet and
knitting. There's no accent writing or put-on dialect anywhere. The Chrome Cow's crowd looks tough and orders
milk, please and thank you; its mosh pit is friendly shoving and nobody gets hurt. Granny Throttle talks tough and
is sweet underneath (she bakes cookies, because milk needs cookies), in plain words, with no biker slang put on.

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

**PROPOSAL (2026-10-10), awaiting owner approval.** With The Chrome Cow and the space lounge last, the chapters read
as below from chapter 7 (1-6 unchanged; "was" is the number in the built table above, which stays until the engine
change). The goal sizes follow the position, not the venue: the zoo, now 9th, takes the 25 that chapter 9 had (it was
the space lounge's), and the space lounge, now last, takes the 30 of the last chapter (it was the zoo's).

| # | Venue | Owner | Piece | Chapter goal (in-world / engine) | Optional twist |
|---|---|---|---|---|---|
| 7 (new) | Biker bar: The Chrome Cow | Granny Throttle | Drip tray | "Don't cry over spilt milk: serve 22 punks" / serve 22 | **Mosh pit**: a served patron sliding back bumps the walker behind him, who is shoved 16 px toward the tap (once per bump, never closer than 32 px to the tap). Serve the back one while the front one drinks. |
| 8 (was 7) | Teahouse | Hana | Pipe | "Serve with care; a broken cup costs two lives" / clear the venue, a broken glass costs 2 lives (instead of 1) | **Taiko rhythm** (unchanged) |
| 9 (was 9) | Jungle zoo | Keeper Kiki | Crown | "Serve 25 animals" / serve 25 | **Cheeky monkeys** (unchanged) |
| 10 (was 8) | Space lounge | Zizz | Lever | "30 glowing beakers for 3 species" / serve 30 | **Low gravity** (unchanged) |

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

**PROPOSAL (2026-10-10), awaiting owner approval.** With The Chrome Cow and the space lounge last, the shifts read
as below from chapter 7 (1-6 unchanged; the built table above stays until the engine change). The ramp follows the
position: chapters 7 and 8 keep the +15 % / -15 % Last call of the middle chapters, chapter 9 (the zoo) takes the
space lounge's old numbers (12 / 25 / 28, +20 % / -20 %), and chapter 10 (the space lounge) takes the zoo's old goals
(15 / 30 / 32) with a Last call one step harder than any other (+25 % / -25 %), so the last chapter is the hardest.
Each venue keeps its own arrival pattern, twist and wording. The Chrome Cow's mosh pit is on in its Happy
hour, as every twist, and in its Last call too (owner, 2026-10-11); never in the Opening shift or the boss fight.

| # | Opening shift (in-world / engine) | Happy hour | Last call | Last call arrivals |
|---|---|---|---|---|
| 7 (new) | "Serve 10 punks, ice-cold milk" / serve 10 | "Don't cry over spilt milk: serve 22 punks" / serve 22 | "The band plays faster: serve 24 punks" / serve 24 | Chord: three bars at once (1, 2, 3), a long breather, three more (4, 3, 2), a shorter breather. Walk +15 %, spawn -15 %, and the venue's tune plays 15 % faster. |
| 8 (was 7) | "Serve 7 guests; a broken cup costs two lives" / 7 guests, a broken glass costs 2 lives | (unchanged) | (unchanged) | Flood bar 4 (unchanged). |
| 9 (was 9) | "Serve 12 animals" / serve 12 | "Serve 25 animals" / serve 25 | "Stampede! Serve 28 animals" / serve 28 | Stampede (pattern unchanged). Walk +20 %, spawn -20 %. |
| 10 (was 8) | "Serve 15 glowing beakers" / serve 15 | "30 glowing beakers for 3 species" / serve 30 | "Serve 32 glowing beakers" / serve 32 | Inside out (pattern unchanged). Walk +25 %, spawn -25 %: the hardest Last call. |

## Script format

Text box: 18 characters per line, 3 lines per page. Allowed: `A-Z 0-9 . , ! ? ' - :` and space.
Each page below is one speaker line (it picks the speaker's portrait, or his variant for that page: see
"Portraits" in the art list; `NARRATOR` has no portrait)
followed by 1-3 text lines. Pages are separated by blank lines. The text is already wrapped,
so the engine prints it as is. Scene ids are what the engine would call each scene.

Text variants: a block whose speaker line reads `SPEAKER IF CONDITION`, right after a page of the same speaker, is
another text for that page. The engine shows it instead of the page's own text when the condition holds (the first
variant whose condition holds); the portrait and the name tag stay the page's. Conditions (`tools/gen_story.py`
CONDITIONS, set by the engine):

| Condition | Holds when |
|---|---|
| `GLASS_BROKEN` | a glass broke (a life lost to it) in the venue attempt that just ended: since the venue last started from its PRE scene, a restart after the last life, or CONTINUE |

The build fails on an unknown condition, a variant with no page above it or of another speaker, a variant with the same
text as its page, and two variants with the same condition on one page.

---

### INTRO: "The Big Pour"

Picture: Fizzwater town square at night. The Golden Spigot on its fountain bursts apart and ten sparkling pieces fly off in every direction.

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

PROPOSAL (2026-10-10), awaiting owner approval, with the 10th venue: pages 6-8 read

```text
NARRATOR
THE SPIGOT BURST
INTO TEN PIECES
AND FLEW AWAY!

NARRATOR
TEN VENUES, TEN
OWNERS. EACH WANTS
A GREAT BARTENDER.

SPIGOTEER
THEN I'LL KEEP
TEN CROWDS HAPPY!
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

PROPOSAL (2026-10-10), awaiting owner approval, with the 10th venue: page 5 reads

```text
SPIGOTEER
ONE DOWN, NINE
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

### PROPOSAL PRE_BIKER: "Mohawks and Milk"

PROPOSAL (2026-10-10), awaiting owner approval: chapter 7, The Chrome Cow. The heading drops `PROPOSAL` when the
engine change adds the chapter (speaker `GRANNY`, a new portrait).

Picture: a row of motorcycles outside a black, studded biker bar under a neon sign of a cow in sunglasses. Granny Throttle stands in the doorway in her patch-covered leather jacket with a tray of cookies; inside, the drummer bashes a golden drip tray.

```
NARRATOR
THE TOUGHEST BAR
IN FIZZWATER. ALL
MOHAWKS AND STUDS.

GRANNY
WIPE YOUR BOOTS,
MUSTACHE. I'M
GRANNY THROTTLE.

GRANNY
WELCOME TO THE
CHROME COW. WE
ONLY SERVE MILK.

SPIGOTEER
MILK? IN A PLACE
THIS TOUGH?

GRANNY
ICE-COLD MILK
MAKES STRONG
BONES, SWEETIE.

NARRATOR
A PUNK WITH A
GREEN MOHAWK SAID
PLEASE. TWICE.

GRANNY
YOUR DRIP TRAY?
OUR DRUMMER USES
IT AS A CYMBAL.

GRANNY
SERVE 22 OF MY
BABIES. NO CRYING
OVER SPILT MILK!

GRANNY
AND MIND THE MOSH
PIT. SERVE THE
BACK ONES FIRST.
```

### PROPOSAL POST_BIKER: "One Loud Chord"

PROPOSAL (2026-10-10), awaiting owner approval. Pages 6-7 are the owner's line for Dregs's exit, split over two
pages (it is 64 characters; a page holds 54).

Picture: the punks raise their glasses, milk mustaches all round, while Granny hands the golden drip tray over on a plate of cookies. Behind her the drummer happily bangs a pot lid.

```
GRANNY
22 HAPPY BABIES,
22 MILK MUSTACHES.
NOT BAD, MUSTACHE.

GRANNY
HERE'S YOUR DRIP
TRAY. AND COOKIES.
WARM ONES. EAT UP.

SPIGOTEER
WHAT WILL YOUR
DRUMMER PLAY NOW?

GRANNY
A POT LID. HE'S
HAPPY. LOOK AT
THAT LITTLE FACE.

DREGS
MOVE IT, GRANDMA!
THAT TRAY'S MINE!
AND THE COOKIES!

NARRATOR
THE BAND PLAYED
ONE LOUD CHORD.

NARRATOR
IT BLEW DREGS
RIGHT OUT THE DOOR

GRANNY
COME BACK WHEN
YOU LEARN TO SAY
PLEASE, SWEETIE!

SPIGOTEER
SEVEN DOWN! NEXT,
SOMEWHERE QUIET.
MY EARS NEED IT.
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

PROPOSAL (2026-10-10), awaiting owner approval, with the 10th venue (the teahouse now follows the loudest bar in
town): one new page between page 3 (Hana's "SHH.") and page 4 (his "SORRY. I MEAN:"), every line of Hana's kept

```text
SPIGOTEER
WHAT? MY EARS ARE
STILL RINGING FROM
THE CHROME COW!
```

### POST_TEAHOUSE: "Harmony"

Picture: Hana pours tea for the Spigoteer at a low table while the taiko drummer bows.

Page 1 has a text variant (owner's decision, 2026-10-10): "NOT ONE CUP" when the teahouse run that ended in this scene
broke no cup, "SO FEW CUPS" (`HANA IF GLASS_BROKEN`) when a cup broke in any of its shifts. The run is the whole venue
attempt since it last started (from PRE_TEAHOUSE, after losing the last life, or by CONTINUE); a broken cup is the event
the chapter's strict rule charges two lives for.

```
HANA
NOT ONE CUP
BROKEN. THAT IS
RARE. THANK YOU.

HANA IF GLASS_BROKEN
SO FEW CUPS
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

PROPOSAL (2026-10-10), awaiting owner approval, with the 10th venue and the zoo next: the last page reads

```text
SPIGOTEER
EIGHT DOWN. NEXT
STOP: THE JUNGLE!
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

PROPOSAL (2026-10-10), awaiting owner approval: the space lounge is chapter 10, the last venue (its PRE and POST
scenes move after the zoo's when the engine change folds this in). Pages 1-5 and 7 stay; a new page after page 5
says this is the last piece, and the goal page reads 30

```text
ZIZZ
THE LAST PIECE?
IT IS ON OUR ROOF.
WE ARE USING IT.

ZIZZ
SERVE 30 GLOWING
BEAKERS TO MY
GUESTS. ALL THREE!
```

### POST_SPACE: "Out of This World"

Picture: the alien musician plays a many-armed keytar while Zizz floats up holding the golden lever. (PROPOSAL, space
last: above them a little saucer beams Dregs back down, in a sparkly souvenir T-shirt.)

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

PROPOSAL (2026-10-10), awaiting owner approval: with the space lounge last, POST_SPACE leads into the finale. It takes
the zoo's "all the pieces" and "let's go home" beats, and Dregs finally gets help (Zizz's cousin beams him up for a
closer look; the Spigoteer asks for him back). The whole scene reads

```text
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

SPIGOTEER
ALL TEN PIECES!
...WAIT. WHERE'S
DREGS?

DREGS
FINALLY, I'M ON
TIME! GIVE ME THE-
WHY AM I FLOATING?

NARRATOR
A FRIENDLY SAUCER
BEAMED DREGS UP
FOR A CLOSER LOOK.

ZIZZ
OOPS. MY COUSIN
COLLECTS EARTH
SOUVENIRS.

SPIGOTEER
ZIZZ, COULD YOU
PLEASE BEAM HIM
BACK DOWN?

NARRATOR
DREGS CAME DOWN
IN A SPARKLY
SOUVENIR T-SHIRT.

SPIGOTEER
COME ON, DREGS.
LET'S GO HOME.
I'LL POUR YOU ONE.
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

PROPOSAL (2026-10-10), awaiting owner approval: the zoo is chapter 9, no longer the last venue. Pages 4 and 5 read

```text
KIKI
YOUR NEXT PIECE,
THE CROWN, IS ON
LEO THE LION.

KIKI
SERVE 25 THIRSTY
ANIMALS AND HE MAY
JUST HAND IT OVER.
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

PROPOSAL (2026-10-10), awaiting owner approval: with the space lounge last, the zoo is no longer the end of the tour.
Dregs still leaves the zoo the zoo's way (the monkeys), and the "all the pieces" and "let's go home" beats move to
POST_SPACE. The whole scene reads

```text
KIKI
REMARKABLE. THE
LION APPROACHES...
...AND PURRS.

NARRATOR
LEO PLACED THE
CROWN ON THE
SPIGOTEER'S HEAD.

DREGS
RIGHT HERE! THAT
CROWN IS MINE! I-
OH NO. MONKEYS.

NARRATOR
THE MONKEYS STOLE
HIS SHOES, HIS HAT
AND HIS DIGNITY.

SPIGOTEER
NINE DOWN! ONE
PIECE LEFT. NEXT:
OUTER SPACE. BUS?
```

---

### FINALE: "The First Pour"

Picture: Fizzwater square by day. The restored Golden Spigot gleams on its fountain, and all ten owners plus a sheepish Dregs gather round as it pours a glass of water.

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

PROPOSAL (2026-10-10), awaiting owner approval, with the 10th venue: pages 1 and 7 read

```text
NARRATOR
BACK IN FIZZWATER,
THE TEN PIECES
CLICKED TOGETHER.

NARRATOR
AFTER TEN BARS,
IT WAS THE BEST
DRINK EVER POURED.
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
PROPOSAL (2026-10-10), awaiting owner approval: **GRANNY** (Granny Throttle) is the one portrait still to draw, a
proposal to the owner first, before the engine change adds her as a speaker.
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
| GRANNY | PROPOSAL (2026-10-10): Granny Throttle: grey bun under a bandana, round glasses, patch-covered leather jacket, a cookie in one hand; a tough squint over a soft smile. |
| NARRATOR | No portrait. The text box runs full width, or shows a small golden spigot icon. |

### Still pictures (one per scene, about 160x96 above the text box)

| Scene | One line |
|---|---|
| INTRO | Night square, the Golden Spigot bursting and ten pieces flying off. |
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
| PRE_BIKER | PROPOSAL (2026-10-10): motorcycles outside a black, studded bar under a neon cow in sunglasses; Granny in the doorway with cookies, the drummer bashing the drip tray inside. |
| POST_BIKER | PROPOSAL (2026-10-10): punks with milk mustaches raising their glasses; Granny hands over the drip tray on a plate of cookies; the drummer bangs a pot lid. |
| PRE_TEAHOUSE | Teahouse by a pond, cherry blossoms, bamboo fountain missing a pipe. |
| POST_TEAHOUSE | Hana pouring tea at a low table; taiko drummer bows. |
| PRE_SPACE | Neon lounge, ringed planet in the window, a city bus parked at the airlock. |
| POST_SPACE | Alien musician with a many-armed keytar; Zizz floats with the lever. PROPOSAL (space last): a little saucer beams Dregs back down in a souvenir T-shirt. |
| PRE_ZOO | Jungle bar under vines, Leo wearing the golden crown, Kiki in the ferns. |
| POST_ZOO | Leo crowns the Spigoteer; flamingos high-kick behind. |
| FINALE | Restored spigot gleaming by day, ten owners and Dregs around it, a glass of water. |
| CREDITS | Spigot dripping over the credits, Dregs mopping in an apron. |

Reuse: the ten golden pieces can share one small sprite sheet (handle, spout, valve, nozzle,
knob, gasket, drip tray, pipe, lever, crown). A between-chapter "spigot progress" screen that fills in one
piece per chapter would reuse them for free.
