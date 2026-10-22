BRIEF (queued 2026-10-21): GBA first-boot SCREEN prompt. Base it on the GBA bright branch (worktree-agent-a4493bb09ecf5272e), merged with current main.

Owner (Q28): "Yes, it is good. Do we have a way to detect when the cartridge is in a GameBoy advance? If so I want the user to be able to select the option whenever they first boot up and have that saved, but changeable in settings. Many people use emulators or modern screens with their modded game boys these days. And the extra brightness often given for period correct GBA games looks washed out on modern displays."

- Detection: yes, via GBDK _is_GBA (boot register B bit 0). Emulators in GBA mode (mGBA etc.) set it too.
- On a GBA (detected) with NO saved SCREEN choice, show a one-time screen at boot, before the title, with a live preview:
  - show the title art or a sample picture, switching between NORMAL and BRIGHT as the cursor moves;
  - the player picks with A;
  - wording plain, e.g. "SCREEN: NORMAL (modern / backlit screens)" / "BRIGHT (original GBA screen)";
  - save the choice (the existing SC save block); SETTINGS > SCREEN stays the way to change it.
- On a GBC or DMG: no prompt (GBC keeps NORMAL by default; DMG never sees the option).
- On a GBA, the DEFAULT highlighted option is NORMAL, since many players use modern screens; the owner says BRIGHT looks washed out there.
- Art for the prompt screen uses existing title tiles/glyphs if possible; any new art goes through the owner's skill.
- Tests: the prompt appears once on GBA without a choice and never again after; not on GBC/DMG; the choice is saved and changeable in SETTINGS; older saves are fine; erase brings the prompt back.
- The marimba-test widening from that branch (1.5 -> 3%) must NOT be kept. Use the test-robust branch's register-based marimba test instead.
- Full verification as usual, plus an unlocked ROM.
