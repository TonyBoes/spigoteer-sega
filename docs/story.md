# Spigoteer: "The Golden Spigot" (story script, owner-approved)

Milestone M11a, owner-approved 2026-10-09. Nothing here is wired into the game yet; M11b builds the text engine and
chapter goals, M11c the art. Everything below is original writing.

**Status 2026-10-17:** the whole story is built and playable (text engine, ten chapters, shifts, mini-games, bosses, the pictures, the finale and the
credits). Added since the original text: script beats ("Beats" below), Dregs's ten venue gags (running gag 1), the INTRO's pulsing burst star and crackle, a
fizzy-drink scene transition, shift timers capped at 99 s, and **STORY difficulty** (next paragraph). The script blocks below are unchanged.

**STORY difficulty (2026-10-17, commit 07e99b8).** A new story asks PICK ONE: EASY / NORMAL / HARD (cursor on NORMAL, B backs out; CONTINUE does not ask,
the save holds the choice in bits 6-7 of its progress byte). The score is recorded times 0.5 (EASY) or 1.5 (HARD) when the credits end, the initials screen
says "EASY X0.5" / "HARD X1.5", and the STORY table marks E / H after the score. EASY unlocks nothing (tunes, jingles, Boss Rush bosses, Practice reach and
medals); on CGB the HUD level flag is green (EASY) or red (HARD). EASY and HARD still play like NORMAL: what they change is for the owner's playtest notes.

**The 10th venue (owner, 2026-10-10 / 11; built 2026-10-11): The Chrome Cow.** The toughest-looking bar in
Fizzwater, all mohawks, leather and studs, where everyone very politely orders an ice-cold glass of milk. It is chapter
7, before the teahouse, and the space lounge moves to the end. The order, in story and arcade: 1 saloon, 2 stadium,
3 lumber lodge, 4 bistro, 5 igloo, 6 robot factory, 7 The Chrome Cow, 8 teahouse, 9 jungle zoo, 10 space lounge.
Owner **Granny Throttle**, piece the **drip tray**, twist the **mosh pit** (docs/minigames_bosses.md section 9; on in
its Happy hour and Last call), tune "Drunken Sailor" (traditional sea shanty, fast and punky), mini-game **Milk Run**
and boss **Duke** (sections 4.10 and 3.12 there; both built since). Difficulty stays tied to the position, not the venue:
the zoo takes the goals and pace chapter 9 had, space those of the last chapter, and space now leads into the finale.
The engine checklist was docs/venue10_impact.md.

## The pitch

In the town of Fizzwater, the **Golden Spigot** (it can pour any drink anyone could ever want)
sits on the fountain in the square. Every year the town's best pourer, Sal Tapley, the **Spigoteer**,
pours its first drink of the festival. This year his rival **Dregs Dribbleton** barges in and
orders "one of everything, all at once". The spigot overloads, goes KA-SPLOOSH and bursts into
ten pieces that land in ten famous venues. Each owner will hand a piece only to a spigoteer who
keeps their crowd happy. The Spigoteer goes on tour.

Cast (kept small): the Spigoteer, Dregs (comic rival, never a real threat), ten one-note venue
owners, and a narrator (text box only, no portrait).

Running gags:

1. **Dregs is always one scene late.** He bursts into every after-venue scene to grab the piece
   and leaves the venue the way that venue would throw him out (swinging doors, crowd-surfed,
   spun out by plates, carried off on a conveyor, blown out by one loud chord...). In space he finally
   gets help (the Spigoteer asks Zizz to beam him back down), and in the finale he says sorry.
   **Dregs's exits (animated, G17, src/dgag.c).** The narrator page after Dregs's own page in each POST scene plays the gag on the venue
   backdrop in OBJ sprites (2-3 s; A cannot turn the page until it ends, START still skips): he dashes in from the right, reaches for the prize,
   and the venue throws him off the LEFT edge (the bars have no doors on screen; dust and a crash sell one just out of view). After his dash and reach he stands a 1.2 s beat, arm out, while the text types, then the venue acts at 13/16 speed (playtest 2026-10-17: the shove used to follow his line too fast to follow). Saloon: two cowboys
   lay him on the bar and slide him down it. Stadium: three fans crowd-surf him. Lumber: he bolts out of his boots. Bistro: spun away by plates.
   Igloo: slides the icy bar and rolls out the tunnel downhill. Factory: the conveyor carries him into a returns box. Chrome Cow: the chord's
   sound arcs (page 1), the blast (page 2). Teahouse: the beat, then he bounces out. Zoo: monkeys steal his boots and hat. Space: the tractor
   beam takes him up; the "came down" page sets him down in a pink-jacketed souvenir T-shirt (CGB).
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
| 2 | Stadium concession | Coach Blitz | Spout | "Serve 20 fans; a fan at your tap costs two lives" / serve 20, a patron at the tap costs 2 lives (instead of 1) | **Innings**: patrons come in 4 rushes with short breathers between them. |
| 3 | Lumber lodge | Big June | Valve | "Wake up 18 sleepy lumberjacks" / serve 18 | **Sasquatch sighting**: now and then the Sasquatch strolls past the back of one bar and its patrons stop to stare. That's a free single-bar distraction. |
| 4 | Bistro | Chef Colby | Nozzle | "Serve 20 chefs before the dinner rush" / serve 20 before the timer runs out | **Fine dining**: patrons sip longer, so empties come back bunched together. Fair-empties spacing still applies. |
| 5 | Igloo bar | Aurora | Knob | "20 cocoas before they cool" / serve 20 before the timer runs out | **Icy bars**: full and empty mugs slide faster. |
| 6 | Robot factory | Manager-Bot 3000 | Gasket | "Recycle 25 batteries" / catch 25 empties | **Conveyors**: empties come back faster than full batteries go out. |
| 7 | Biker bar: The Chrome Cow | Granny Throttle | Drip tray | "Don't cry over spilt milk: serve 22 punks" / serve 22 | **Mosh pit**: a served patron sliding back bumps the walker behind him, who is shoved 16 px toward the tap (once per bump, never closer than 32 px to the tap; 48 in Last call). Serve the back one while the front one drinks. |
| 8 | Teahouse | Hana | Pipe | "Serve with care; a broken cup costs two lives" / clear the venue, a broken glass costs 2 lives (instead of 1) | **Taiko rhythm**: patrons step on the drum beat instead of walking smoothly, which makes them easy to read and hard to rush. |
| 9 | Jungle zoo | Keeper Kiki | Crown | "Serve 25 animals" / serve 25 | **Cheeky monkeys**: now and then a monkey snatches a coconut mid-slide and it comes back as an empty straight away. |
| 10 | Space lounge | Zizz | Lever | "30 glowing beakers for 3 species" / serve 30 | **Low gravity**: full drinks float more slowly, so you have to lead your throws. |

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
| 4 | "Serve 10 chefs before the rush" / serve 10 in 75 s | "Serve 20 chefs before the dinner rush" / serve 20 before the timer runs out | "Serve 22 chefs, tables for two" / serve 22 in 99 s | Pairs: two chefs at once (bars 1 and 3, then 2 and 4), then a longer gap. Walk +15 %, spawn -15 %. |
| 5 | "Serve 10 cocoas before they cool" / serve 10 in 75 s | "20 cocoas before they cool" / serve 20 before the timer runs out | "22 cocoas before they freeze" / serve 22 in 99 s | Zigzag: bars 1, 3, 2, 4, 3, 1, 4, 2, always a jump away from the last. Walk +15 %, spawn -15 %. |
| 6 | "Recycle 12 batteries" / catch 12 empties | "Recycle 25 batteries" / catch 25 empties | "Recycle 28, the batteries pile up" / catch 28 empties | Stairs up: one robot on each bar in turn, bottom to top. Walk +15 %, spawn -15 %. |
| 7 | "Serve 10 punks, ice-cold milk" / serve 10 | "Don't cry over spilt milk: serve 22 punks" / serve 22 | "The band plays faster: serve 24 punks" / serve 24 | Chord: three bars at once (1, 2, 3), a long breather, three more (4, 3, 2), a shorter breather. Walk +15 %, spawn -15 %, and the venue's tune plays faster (one frame less per row: 225 instead of 200 bpm). |
| 8 | "Serve 7 guests; a broken cup costs two lives" / 7 guests, a broken glass costs 2 lives | "Serve with care; a broken cup costs two lives" / clear the venue, a broken glass costs 2 lives | "Serve 15 guests; a broken cup costs two lives" / 15 guests, a broken glass costs 2 lives | Flood bar 4: every other guest comes to bar 4. Walk +15 %, spawn -15 %. |
| 9 | "Serve 12 animals" / serve 12 | "Serve 25 animals" / serve 25 | "Stampede! Serve 28 animals" / serve 28 | Stampede: all four bars at once top to bottom, a breather, then all four bottom to top. Walk +20 %, spawn -20 %. |
| 10 | "Serve 15 glowing beakers" / serve 15 | "30 glowing beakers for 3 species" / serve 30 | "Serve 32 glowing beakers" / serve 32 | Inside out: two at once on the middle bars, then two on the outer bars. Walk +25 %, spawn -25 %: the hardest Last call. |

The ramp follows the position: chapters 7 and 8 keep the +15 % / -15 % Last call of the middle chapters, chapter 9 (the
zoo) +20 % / -20 %, and chapter 10 (the space lounge) a Last call one step harder than any other. The Chrome Cow's mosh
pit is on in its Happy hour, as every twist, and in its Last call too (owner, 2026-10-11); never in the Opening shift,
the boss fight or arcade.

## Script format

Text box: 18 characters per line, 3 lines per page. Allowed: `A-Z 0-9 . , ! ? ' - :` and space.
Each page below is one speaker line (it picks the speaker's portrait, or his variant for that page: see
"Portraits" in the art list; `NARRATOR` has no portrait)
followed by 1-3 text lines. Pages are separated by blank lines. The text is already wrapped,
so the engine prints it as is. Scene ids are what the engine would call each scene.

Beats (pauses in the typing; dramatic timing, 2026-10-15). Two marks, both optional:

* `|` or `||` written right after a word (before the space, or at the end of a line) pauses the typing there: `|` is a
  short beat (15 frames, a quarter second), `||` a long one (36 frames). The mark takes no room in the box (it replaces
  the space after the word, or sits in the free cell at the end of the line), so the lines wrap as before; a beat at the
  end of an 18-character line has no free cell and the build says so. Nothing is shown during a beat. A beat at the very
  end of a page is refused (it would pause nothing).
* `@beat` or `@beat N` on the line right after the speaker pauses before the page types (the box is blank, the portrait
  already changing): N from 1 to 7, 8 frames each (`@beat` alone is 3, 24 frames). Pick it for entrances and reveals.

The engine also adds its own gap before every page so a page turn never types at once: 12 frames after a change of speaker,
6 frames for the same speaker's next page (an `@beat` longer than that wins; the first page of a scene has none unless it
says `@beat`). A or B during any beat skips it and shows the rest of the page, as it does while typing; A again turns
the page. START still skips the scene. A text variant (below) has its own `|` marks and keeps the page's `@beat` unless it has one of its own.

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

Picture (pages 1-6): Fizzwater town square at night: the clock tower and houses at the left, the fountain right of centre. The whole Golden Spigot gleams on it, string lights hang across the square and a few townsfolk in hats wait in the foreground. The Spigoteer walks in from the right. (`assets/story/pictures/intro_before.txt`)

Picture (page 7): the same square a moment later, after a white flash. The intact Golden Spigot bursts into its ten pieces, which fly outward and off the screen (a short animation, OBJ sprites), each leaving a trail of faded dots in the sky that fades away. Over the spigot's spot a gold burst star (BG tiles, two sizes) is up at the flash and pulses (big, small, big...) while the pieces fly, then dies down once they are gone and an electric crackle (two flickering bolt sprites, with a rattle sound) takes its place above the broken stub and keeps on through pages 8-12. What is left: an empty rim with a broken stub and a last drip, and the fountain stopped (no jets). Dregs stands on the cobbles, the Spigoteer shrugs, and the townsfolk duck or point. Pages 8-12 stay on it. (`assets/story/pictures/intro_a.txt`, the pieces `assets/story/pictures/intro_pieces.txt`)

```
NARRATOR
@beat 4
ONCE UPON A TAP,
IN FIZZWATER TOWN,
STOOD THE GOLDEN

NARRATOR
SPIGOT. IT COULD
POUR ANY DRINK
ANYONE WANTED!

NARRATOR
EVERY YEAR AT THE
FESTIVAL, THE BEST
SERVER GOES FIRST.

SPIGOTEER
I'M SAL TAPLEY,
THE SPIGOTEER,|
REIGNING CHAMP!

NARRATOR
HE'S ALSO FAMOUS
FOR HIS MUSTACHE:
BIG, BOLD, TIDY.

DREGS
@beat 3
MOVE IT, MUSTACHE!
DREGS POURS FIRST:
ONE OF EVERYTHING!

NARRATOR
GLUG.| GLUG.| GLUG.|
GLUGGA-GLUGGA...||
KA-SPLOOOOSH!!!

NARRATOR
THE SPIGOT BURST
INTO TEN PIECES|
AND FLEW AWAY!

DREGS
@beat 2
OOPS.| FINDERS
KEEPERS! I'LL GET
ALL TEN FIRST!

SPIGOTEER
@beat 2
I'LL WIN ALL TEN
PIECES BACK AND
FIX THE SPIGOT!

NARRATOR
@beat 3
TEN VENUES, TEN
OWNERS. EACH WANTS
A GREAT SPIGOTEER.

SPIGOTEER
@beat 2
THEN I'LL KEEP
TEN CROWDS HAPPY!|
MUSTACHE: ONWARD!
```

---

### PRE_SALOON: "Howdy, Pardner"

Picture: dusty saloon front with swinging doors and a hitching post. Sadie leans on the doorframe.

```
SADIE
HOWDY, STRANGER!|
I'M SADIE SPURS.
WELCOME TO MY BAR.

SADIE
THAT MUSTACHE?| I
RATE IT FOUR
TUMBLEWEEDS.| NICE.

SPIGOTEER
I HEAR YOU FOUND
A SHINY PIECE OF
GOLDEN SPIGOT?

SADIE
SURE DID!| KEEP
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
FIVE TUMBLEWEEDS!|
MY TOP RATING!

SADIE
HERE'S YOUR PIECE:
THE HANDLE. GOT
STUCK IN MY PIANO.

DREGS
@beat 3
OUTTA MY WAY! THAT
HANDLE'S MINE! I
CALLED DIBS!

NARRATOR
@beat 2
THE COWBOYS SLID
DREGS STRAIGHT OUT
THE SWINGING DOORS

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
TWEET!| GATHER UP,
ROOKIE! I'M COACH
BLITZ. MY STADIUM!

COACH
GOT YOUR SPOUT
RIGHT HERE. FOUND
IT AT SECOND BASE.

SPIGOTEER
WHAT'S THE PLAY,
COACH?

COACH
LET ONE FAN REACH
YOUR TAP AND IT|
COSTS TWO LIVES!

NARRATOR
@beat 2
AFTER HAPPY HOUR,
A BONUS GAME. WIN
GOLD, GAIN A LIFE!

NARRATOR
AFTER LAST CALL,
A BOSS BLOCKS THE
WAY TO THE PIECE.

COACH
THE SODA'S COLD,|
THE CROWD IS HOT.
TWEET!| GO GO GO!
```

### POST_STADIUM: "Home Run"

Picture: the scoreboard flashes WIN as Coach dumps a cooler of soda over the Spigoteer and the cheerleaders kick. (Animated, G17b, src/dgag.c phase 3: on the "SPLOOSH!" page Coach's cooler slides in over the Spigoteer, tips, pours an orange soda stream onto him, a dithered sheet of soda runs down him and splashes at his feet, the cooler lifts away and a few drips are left; 2.5 s, A waits, START skips.)

```
COACH
HOME RUN!| TEAM
SPIGOTEER WINS!
HIT THE SHOWERS!

NARRATOR
@beat 2
SPLOOSH!| THE
SPIGOTEER GOT THE
VICTORY SODA BATH.

SPIGOTEER
MY MUSTACHE IS
ALL STICKY. WORTH
IT FOR THE SPOUT!

DREGS
@beat 3
WAIT! I'M HERE FOR
THE SPOUT- HEY!
PUT ME DOWN!

NARRATOR
@beat 2
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
TIMBER!| OH, SORRY.
I SAY THAT A LOT.
I'M BIG JUNE.

JUNE
MY LUMBERJACKS RUN
ON COFFEE. AND
THEY'RE SLEEPY.

SPIGOTEER
UM.| WHO'S THE BIG
HAIRY FELLA
BEHIND YOU?

JUNE
@beat 2
SASQUATCH?| HA!
NO SUCH THING.|
NOW, THE JOB:

JUNE
WAKE UP ALL THEM
SLEEPYHEADS! THEN
THE VALVE'S YOURS.
```

### POST_LUMBER: "Bigfoot, Big Heart"

Picture: the Sasquatch gently hands the golden valve to the Spigoteer while June looks the other way.

```
JUNE
EVERYONE'S WIDE
AWAKE! WORTH A
VALVE. HERE,| UH...

NARRATOR
THE SASQUATCH
HANDED IT OVER,|
THEN TIPTOED OFF.

JUNE
SEE? NO SUCH THING
AS A SASQUATCH.|
TIMBER!

DREGS
@beat 3
GIMME THAT VALVE!|
...WAIT. WHO'S THE
BIG HAIRY FELLA?

NARRATOR
@beat 2
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
CHEF COLBY.| YOU
LOOK GOUDA TODAY.

SPIGOTEER
@beat 3
...WAS THAT A
CHEESE PUN?

COLBY
I CAN'T HELP IT.|
IT'S NACHO FAULT.|
IT'S MINE.

COLBY
MY CHEFS ARE OFF
DUTY AND HUNGRY.
SERVE THEM ALL.

COLBY
SPARKLING GRAPE
JUICE, CHILLED.|
NOW BRIE QUICK!
```

### POST_BISTRO: "The Cheese Course"

Picture: Colby lifts a silver dome to reveal the golden nozzle while the plate-spinning waiter twirls in the background.

```
COLBY
MAGNIFICENT! YOU
ARE THE BIG|
CHEESE NOW!

COLBY
YOUR NOZZLE. MY
PASTRY CHEF USED
IT FOR FROSTING.

SPIGOTEER
IT'S A LITTLE
STICKY. AND|
DELICIOUS.

DREGS
@beat 3
I'LL TAKE THAT
NOZZLE, CHEF!
...WHOA,| PLATES!

NARRATOR
@beat 2
DREGS GOT TANGLED
IN SPINNING PLATES
AND SPUN AWAY!

COLBY
SAFE TRAVELS,
FRIEND. AND STAY|
GRATE!

SPIGOTEER
FOUR DOWN! NEXT:
THE KNOB. IT'S ON
AN IGLOO. BRRR!
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
SOMETHING: A|
MUSTACHE COZY!

SPIGOTEER
IT'S...| VERY COZY.
AND VERY PINK.|
THANK YOU!

AURORA
MY GUESTS CAME IN
FROM THE COLD.
SERVE THEM COCOA.

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
WARM!| TAKE THE
KNOB. IT'S YOURS.

AURORA
IT WAS MY IGLOO'S
DOORKNOB. ODD, AS|
IT HAS NO DOOR.

DREGS
@beat 3
HAND OVER THE
KNOB! WHOA, ICY!
WHOA- WHOAAAA!

NARRATOR
@beat 2
DREGS SLID DOWN
THE BAR, OUT THE
TUNNEL, DOWNHILL.

SPIGOTEER
FIVE DOWN!| AND MY
MUSTACHE HAS NEVER
BEEN SO TOASTY.

SPIGOTEER
NEXT: A GASKET.
A ROBOT WEARS IT
AS A HAT. ONWARD!
```

---

### PRE_ROBOT: "Beep Boop, Spigoteer"

Picture: factory floor with conveyor belts and a big lightning-bolt sign. Robots stand in line and Manager-Bot 3000 sits on a hover platform.

```
MANAGER-BOT
GREETINGS, HUMAN.
I AM MANAGER-BOT
3000.| STATUS: HI.

MANAGER-BOT
SCANNING...|
MUSTACHE DETECTED.
ALSO A PINK COZY.

SPIGOTEER
@beat 2
IT WAS A GIFT.
I'M HERE ABOUT
THE GASKET.

MANAGER-BOT
MY WORKERS NEED
POWER. RECYCLE
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
STATUS: HAPPY.|
BEEP BOOP.

MANAGER-BOT
TAKE THE GASKET.
UNIT 12 WAS USING|
IT AS A HAT.

SPIGOTEER
HE LOOKED GREAT
IN IT, HONESTLY.

DREGS
@beat 3
STEP ASIDE, TIN
CANS! THAT GASKET
IS MI-| HEY! BELT!

NARRATOR
@beat 2
THE CONVEYOR BELT
CARRIED DREGS TO
BOX 4: RETURNS.

MANAGER-BOT
STATUS: AMUSED.|
HA.| HA.| HA.

SPIGOTEER
SIX DOWN! NEXT:
THE DRIP TRAY. THE
HOUSE BAND HAS IT.
```

---

### PRE_BIKER: "Mohawks and Milk"

Picture: a row of motorcycles outside a black, studded biker bar under a neon sign of a cow in sunglasses. Granny Throttle stands in the doorway in her patch-covered leather jacket with a tray of cookies; inside, the drummer bashes a golden drip tray.

```
NARRATOR
THE TOUGHEST BAR
IN FIZZWATER. ALL|
MOHAWKS AND STUDS.

GRANNY
WIPE YOUR BOOTS,|
MUSTACHE. I'M
GRANNY THROTTLE.

GRANNY
WELCOME TO THE
CHROME COW. WE|
ONLY SERVE MILK.

SPIGOTEER
MILK?| IN A PLACE
THIS TOUGH?

GRANNY
ICE-COLD MILK
MAKES STRONG
BONES, SWEETIE.

NARRATOR
A PUNK WITH A
GREEN MOHAWK SAID|
PLEASE.| TWICE.

GRANNY
YOUR DRIP TRAY?|
OUR DRUMMER USES
IT AS A CYMBAL.

GRANNY
SERVE ALL OF MY
BABIES.| NO CRYING
OVER SPILT MILK!

GRANNY
AND MIND THE MOSH
PIT. SERVE THE
BACK ONES FIRST.
```

### POST_BIKER: "One Loud Chord"

Pages 6-7 are the owner's line for Dregs's exit, split over two pages (it is 64 characters; a page holds 54).

Picture: the punks raise their glasses, milk mustaches all round, while Granny hands the golden drip tray over on a plate of cookies. Behind her the drummer happily bangs a pot lid.

```
GRANNY
HAPPY BABIES,
MILK MUSTACHES.|
NOT BAD, MUSTACHE.

GRANNY
HERE'S YOUR DRIP
TRAY. AND COOKIES.
WARM ONES. EAT UP.

SPIGOTEER
WHAT WILL YOUR
DRUMMER PLAY NOW?

GRANNY
A POT LID.| HE'S
HAPPY. LOOK AT
THAT LITTLE FACE.

DREGS
@beat 3
MOVE IT, GRANDMA!
THAT TRAY'S MINE!
AND THE COOKIES!

NARRATOR
@beat 2
THE BAND PLAYED|
ONE LOUD CHORD.

NARRATOR
@beat 3
IT BLEW DREGS
RIGHT OUT THE DOOR

GRANNY
@beat 2
COME BACK WHEN
YOU LEARN TO SAY|
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
@beat 3
WELCOME.| I AM
HANA, MASTER OF
THIS TEAHOUSE.

SPIGOTEER
HELLO!!! NICE TO
MEET YOU!!! I'M
HERE FOR THE PIPE!

HANA
@beat 4
SHH. HERE, WE
ENJOY THE QUIET.|
ALSO THE TEA.

SPIGOTEER
WHAT?| MY EARS ARE
STILL RINGING FROM
THE CHROME COW!

SPIGOTEER
SORRY. I MEAN:|
HELLO. NICE TO
MEET YOU.

HANA
YOUR PIPE FELL IN|
MY BAMBOO FOUNTAIN
IT FIT PERFECTLY.

HANA
SERVE WITH CARE.|
ONE BROKEN CUP
COSTS TWO LIVES.

HANA
AND FOLLOW THE
DRUM.| GOOD TEA
HAS A RHYTHM.
```

### POST_TEAHOUSE: "Harmony"

Picture: Hana pours tea for the Spigoteer at a low table while the taiko drummer bows.

Page 1 has a text variant (owner's decision, 2026-10-10): "NOT ONE CUP" when the teahouse run that ended in this scene
broke no cup, "SO FEW CUPS" (`HANA IF GLASS_BROKEN`) when a cup broke in any of its shifts. The run is the whole venue
attempt since it last started (from PRE_TEAHOUSE, after losing the last life, or by CONTINUE); a broken cup is the event
the chapter's strict rule charges two lives for.

```
HANA
@beat 3
NOT ONE CUP
BROKEN.| THAT IS
RARE. THANK YOU.

HANA IF GLASS_BROKEN
SO FEW CUPS
BROKEN.| THAT IS
RARE. THANK YOU.

HANA
THE PIPE. MY
FOUNTAIN WILL MISS
IT. TAKE IT HOME.

DREGS
@beat 3
HAND OVER THAT
PIPE!!! I AM VERY
LOUD AND RUDE!!!

NARRATOR
@beat 2
THE DRUMMER STRUCK
ONE MIGHTY BEAT.|
DREGS TUMBLED OUT.

HANA
@beat 3
AH. QUIET AGAIN.|
MORE TEA?

SPIGOTEER
EIGHT DOWN. NEXT
STOP: THE JUNGLE!|
...QUIETLY.
```

---

### PRE_ZOO: "Call of the Wild"

Picture: a jungle zoo bar under hanging vines. Leo the lion lounges on a rock with the golden crown on his mane, and Keeper Kiki crouches in the ferns.

```
KIKI
@beat 3
AND HERE WE SEE|
THE RARE MUSTACHED
SPIGOTEER...

SPIGOTEER
HI.| ARE YOU
NARRATING ME?

KIKI
IT SPEAKS!| HOW
EXTRAORDINARY.|
I'M KEEPER KIKI.

KIKI
YOUR NEXT PIECE,
THE CROWN, IS ON|
LEO THE LION.

KIKI
SERVE THE THIRSTY
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
REMARKABLE.| THE
LION APPROACHES...
...AND PURRS.

NARRATOR
LEO PLACED THE
CROWN ON THE|
SPIGOTEER'S HEAD.

DREGS
@beat 3
RIGHT HERE! THAT
CROWN IS MINE! I-
OH NO.| MONKEYS.

NARRATOR
@beat 2
THE MONKEYS STOLE
HIS SHOES, HIS HAT
AND HIS DIGNITY.

SPIGOTEER
NINE DOWN!| ONE
PIECE LEFT. NEXT:
OUTER SPACE.| BUS?
```

---

### PRE_SPACE: "One Small Sip"

Picture: a neon space lounge with a ringed planet in the window. A city bus with a SPACE route sign is parked outside the airlock.

```
NARRATOR
@beat 2
THE SPIGOTEER
TOOK THE BUS TO
OUTER SPACE.

NARRATOR
@beat 3
IT WAS A VERY|
LONG BUS RIDE.

ZIZZ
GREETINGS, EARTH|
DRINK-SLIDER! I AM
ZIZZ, YOUR HOST!

ZIZZ
YOUR FACE-BROOM
IS MOST HANDSOME!|
ALSO VERY PINK.

SPIGOTEER
THANKS. I'M HERE
FOR THE LEVER.

ZIZZ
THE LAST PIECE?|
IT IS ON OUR ROOF.
WE ARE USING IT.

ZIZZ
SERVE GLOWING
BEAKERS TO MY
GUESTS.| EVERYONE!

ZIZZ
LOW GRAVITY HERE:|
DRINKS FLOAT SLOW.
HOLD YOUR SPOONS!
```

### POST_SPACE: "Out of This World"

Picture: the alien musician plays a many-armed keytar while Zizz floats up holding the golden lever. Above them a little
saucer beams Dregs back down, in a sparkly souvenir T-shirt.

```
ZIZZ
YOU ARE THE CAT'S|
PAJAMAS! THE BEE'S
ELBOWS!

ZIZZ
TAKE THE LEVER.
WE USED IT AS A|
TV ANTENNA.

SPIGOTEER
WHAT DID YOU
WATCH?

ZIZZ
@beat 2
A SHOW ABOUT A
MUSTACHED MAN WHO|
SLIDES DRINKS.

SPIGOTEER
ALL TEN PIECES!|
...WAIT.| WHERE'S
DREGS?

DREGS
@beat 3
FINALLY, I'M ON
TIME!| GIVE ME THE-
WHY AM I FLOATING?

NARRATOR
@beat 2
A FRIENDLY SAUCER
BEAMED DREGS UP
FOR A CLOSER LOOK.

ZIZZ
OOPS.| MY COUSIN
COLLECTS EARTH
SOUVENIRS.

SPIGOTEER
ZIZZ,| COULD YOU
PLEASE BEAM HIM
BACK DOWN?

NARRATOR
@beat 2
DREGS CAME DOWN
IN A SPARKLY
SOUVENIR T-SHIRT.

SPIGOTEER
@beat 3
COME ON, DREGS.
LET'S GO HOME.|
I'LL POUR YOU ONE.
```

---

### FINALE_A: "The First Pour"

Picture: the same Fizzwater square by day, pennants among the string lights. The restored Golden Spigot gleams on its fountain, its water runs into the glass the Spigoteer (in his cozy) holds up to the jet, a sheepish Dregs stands by, and the ten owners are lined up along the bottom. (`assets/story/pictures/finale_a.txt`; FINALE_B shows it too.)

The FINALE is split in two (the Pour-Off, docs/minigames_bosses.md section 5, plays between the halves: a SALOON race against Dregs, first to 20 serves, built into the story after this scene). The two new pages (DREGS, SPIGOTEER) are **proposed, pending owner approval** (docs/minigames_bosses.md section 7's suggested text); the other pages are the owner-approved script, moved unchanged.

```
NARRATOR
@beat 3
BACK IN FIZZWATER,
THE TEN PIECES|
CLICKED TOGETHER.

NARRATOR
@beat 2
THE GOLDEN SPIGOT
SHONE ONCE MORE!|
THE CROWD GASPED.

NARRATOR
@beat 2
THE OWNERS CAME:
SADIE, COACH, JUNE
COLBY AND AURORA.

NARRATOR
MANAGER-BOT,
GRANNY, HANA, KIKI
AND ZIZZ.

SADIE
SIX TUMBLEWEEDS!|
I DIDN'T KNOW I
HAD SIX!

DREGS
@beat 3
HOLD IT!| WHO
POURS FIRST? I
SAY: A POUR-OFF!

SPIGOTEER
@beat 2
FIRST TO 20
SERVES. YOU'RE ON,
DREGS.

NARRATOR
THE POUR-OFF WILL
BE AT SADIE'S
SALOON.
```

### FINALE_B: "The First Pour"

Picture: the same as FINALE_A (the Pour-Off was played in between, in the saloon). The first page (DREGS, the sorry portrait) is **proposed, pending owner approval**; its second page is the owner-approved "YOU POUR FIRST. YOU EARNED IT." with its first line (the old "SORRY I BROKE IT.", now said on the first page) dropped; the rest is unchanged. (`assets/story/pictures/finale_a.txt`)

```
DREGS
@beat 4
I LOST FAIR AND
SQUARE.| SORRY I
BROKE IT.

DREGS
@beat 2
YOU POUR FIRST.|
YOU EARNED IT.

SPIGOTEER
@beat 3
IT CAN POUR ANY
DRINK ANYONE COULD
EVER WANT.| SO...

SPIGOTEER
@beat 5
...I'LL HAVE A
NICE COLD GLASS|
OF WATER.

NARRATOR
@beat 3
AFTER TEN BARS,|
IT WAS THE BEST|
DRINK EVER POURED.

SPIGOTEER
@beat 3
NOW, WHO'S
THIRSTY?| FIRST
ROUND'S ON ME!
```

### CREDITS: "Last Call"

Picture: the morning after, the same Fizzwater square at dawn. The restored Golden Spigot drips on its fountain, Dregs in an apron mops the cobbles, last night's string lights have come loose, and the Sasquatch's coffee stand opens at the right. (`assets/story/pictures/credits_b.txt`)

```
NARRATOR
@beat 3
DREGS NOW WORKS
AS A BUSBOY. HE
LOVES IT.| MOSTLY.

NARRATOR
@beat 2
THE SASQUATCH
SELLS COFFEE NOW.|
JUNE DOUBTS IT.

NARRATOR
@beat 2
AND THE PINK
MUSTACHE COZY?|
STILL WORN DAILY.

NARRATOR
@beat 4
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

All done (approved art imported pixel-exact, 2026-10-10; GRANNY 2026-10-11): **SPIGOTEER, SADIE, DREGS, COACH, JUNE,
COLBY, AURORA, MANAGER-BOT, HANA, ZIZZ, KIKI, GRANNY**, and two variants. There are no placeholders left: a speaker without art fails the build.
DREGS's main portrait is the sheepish drawing (owner's choice; it replaced the first approved Dregs).

Variants (`assets/story/portraits.json` "variants": a range of pages in script order, resolved per page by
`tools/gen_story.py`; the build fails on a range that names no scene or page, whose given page is not the speaker's, that
overlaps another variant of his or that no page uses):

| Variant | Source | Pages |
|---|---|---|
| SPIGOTEER COZY | `spigoteer_cozy.txt` | From PRE_IGLOO page 3 (his "IT'S... VERY COZY." right after Aurora knits it on page 2) to the end of the game: every Spigoteer page of PRE_IGLOO through FINALE_B (CREDITS has none). |
| DREGS SORRY | `dregs_sorry.txt` | FINALE_B pages 1-2, his apology "SORRY I BROKE IT." and "YOU POUR FIRST." (his only FINALE_B pages; his FINALE_A challenge has the main portrait). |

| Portrait | One line |
|---|---|
| SPIGOTEER | Big curled mustache, spigoteer's apron and bow tie, confident grin. |
| SPIGOTEER (cozy) | The same with the pink knitted mustache cozy, from PRE_IGLOO page 3 onward. |
| DREGS | Lanky rival with a scraggly little mustache and a crooked bow tie, sheepish. His FINALE_B apology has its own variant (hand behind his head). |
| SADIE | Small saloon owner, huge hat, sheriff-style star badge, big laugh. |
| COACH | Coach Blitz: ball cap, whistle in his teeth, clipboard. |
| JUNE | Big June: red plaid, knit beanie, axe over her shoulder, cheerful. |
| COLBY | Chef Colby: tall toque, wedge-of-cheese pin, twinkle in his eye. |
| AURORA | Aurora: warm smile, fur-trimmed parka hood, knitting needles. |
| MANAGER-BOT | Manager-Bot 3000: boxy head, single screen-face showing a smile, antenna. |
| HANA | Tea master: calm expression, simple work kimono and apron, holding a tea whisk. Dignified, not a caricature. |
| ZIZZ | Zizz: round jelly-like alien with three eyes and a bow tie, glowing. |
| KIKI | Keeper Kiki: safari hat, binoculars, finger to her lips. |
| GRANNY | Granny Throttle: grey bun under a bandana, round glasses, patch-covered leather jacket, a cookie in one hand; a tough squint over a soft smile. |
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
| PRE_BIKER | Motorcycles outside a black, studded bar under a neon cow in sunglasses; Granny in the doorway with cookies, the drummer bashing the drip tray inside. |
| POST_BIKER | Punks with milk mustaches raising their glasses; Granny hands over the drip tray on a plate of cookies; the drummer bangs a pot lid. |
| PRE_TEAHOUSE | Teahouse by a pond, cherry blossoms, bamboo fountain missing a pipe. |
| POST_TEAHOUSE | Hana pouring tea at a low table; taiko drummer bows. |
| PRE_ZOO | Jungle bar under vines, Leo wearing the golden crown, Kiki in the ferns. |
| POST_ZOO | Leo crowns the Spigoteer; flamingos high-kick behind. |
| PRE_SPACE | Neon lounge, ringed planet in the window, a city bus parked at the airlock. |
| POST_SPACE | Alien musician with a many-armed keytar; Zizz floats with the lever; a little saucer beams Dregs back down in a souvenir T-shirt. |
| FINALE_A, FINALE_B | Restored spigot gleaming by day, ten owners and Dregs around it, a glass of water. |
| CREDITS | Spigot dripping over the credits, Dregs mopping in an apron. |

Reuse: the ten golden pieces can share one small sprite sheet (handle, spout, valve, nozzle,
knob, gasket, drip tray, pipe, lever, crown). A between-chapter "spigot progress" screen that fills in one
piece per chapter would reuse them for free.
