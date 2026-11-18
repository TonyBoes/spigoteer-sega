# Sandbox setup for the Sega port (Codex, sbx microVM)

`spigoteer-sega` keeps building the Game Boy ROM — it is the port's regression net — and adds Game Gear (then Master
System) targets. So this is `docs/dev/SANDBOX_SETUP.md` plus an SMS/GG test harness. Same VM: user `agent`
(passwordless sudo), Debian 13 (DHI), Python 3.14. Same rules: never let apt replace the image's Python, always
`--no-install-recommends`, dry-run apt and check no `python` package is in the `Inst` lines, environment variables in
`/etc/sandbox-persistent.sh`.

## Part 1: the Game Boy toolchain

Follow `docs/dev/SANDBOX_SETUP.md` steps 1-10 exactly, with three differences for Codex:

- Step 9: also run `echo 'export GBDK_HOME=/opt/gbdk/' | sudo tee -a /etc/sandbox-persistent.sh` if the plain `>>`
  fails for permissions.
- Its "Session start" paragraph (Claude auto-memory) does not apply. `AGENTS.md` says what replaces it.
- Its "Pixel-art skill" check does not apply: the shared skills store is mounted for Claude, not Codex. The skill is
  Game Boy-specific anyway.

Then run its checks table. Everything must match before Part 2, and the Game Boy verify run must pass:
`tools/dev/verify.sh /workspace sbx-setup` → `RESULT: PASS`. That is the baseline every later commit is held to.

## Part 2: the SMS/GG harness

GBDK 4.5.0 from Part 1 already compiles for Game Gear and Master System (`lcc -mz80:gg`, `lcc -mz80:sms`). What
Part 2 adds is the means to run and test those ROMs: two emulators and the `retrotools` package in `tools/retro/`.

| Tool | Role |
|---|---|
| stable-retro 1.0.1 | fast, headless driver for pytest (Genesis Plus GX core for SMS/GG); the SMS/GG counterpart of PyBoy |
| MesenCE 2.2.1 | cycle-accurate test runner; the SMS/GG counterpart of SameBoy |
| `retrotools` | `retrotest`, `retrocheck`, `retrosprite`, `retrolevel`, and `from retrotools import Rom` |

```bash
# 11. apt: virtual display and the libraries MesenCE loads (dry-run first: no python packages)
sudo apt-get install -s --no-install-recommends xvfb xauth libsdl2-2.0-0 libx11-6 libice6 libsm6 libfontconfig1 unzip | grep -i '^Inst.*python' || echo "no python: ok"
sudo apt-get install -y --no-install-recommends xvfb xauth libsdl2-2.0-0 libx11-6 libice6 libsm6 libfontconfig1 unzip

# 12. MesenCE 2.2.1, checksum-pinned, in a folder owned by agent (it extracts libraries beside itself on every start)
curl -fsSL -o $B/mesen.zip https://github.com/nesdev-org/MesenCE/releases/download/2.2.1/Mesen_2.2.1_Linux_x64.zip
echo "c88ff4d251b407515c43d3332d641927655cd69fb538996b6a21da4509dbb58f  $B/mesen.zip" | sha256sum -c -
sudo rm -rf /opt/mesence && sudo mkdir -p /opt/mesence && sudo unzip -q $B/mesen.zip -d /opt/mesence
sudo chown -R agent:agent /opt/mesence
```

Step 13 writes `/opt/mesence/settings.json` with exactly this content (use the editor tool, not a heredoc):

```json
{
  "Debug": { "ScriptWindow": { "AllowIoOsAccess": true } },
  "Nes": { "Port1": { "Type": "NesController" } },
  "Sms": { "Port1": { "Type": "SmsController" } }
}
```

Every line of it matters. Without the file, MesenCE starts its first-run wizard before it checks `--testrunner` and
hangs on an invisible window. Without the `Sms` line, no controller is plugged into the Master System's port and
Lua input is silently ignored (the Game Gear's controls are built in). Without `AllowIoOsAccess`, Lua cannot write
screenshots.

```bash
# 14. Python: stable-retro (has a cp314 wheel) and retrotools from the repo
sudo pip install --break-system-packages "stable-retro==1.0.1"
sudo pip install --break-system-packages <repo>/tools/retro/tools

# 15. SMS/GG references (devkitSMS documents the VDP and ships a PSG music library; sms-sound-test has PSG examples)
for spec in "devkitsms sverx/devkitSMS 533ae572c897cf44f1da865013ebf690134301a3" \
            "sms-sound-test maxim-zhao/sms-sound-test fe7349f1bde1b7becf0fbfc054a24a224dc37ae6"; do
    set -- $spec; d=/usr/share/doc/sega/reference/$1
    sudo mkdir -p $d && cd $d && sudo git init -q && sudo git remote add origin https://github.com/$2.git
    sudo git fetch -q --depth 1 origin $3 && sudo git checkout -q FETCH_HEAD && sudo rm -rf .git
done
echo 'export SEGA_DOC=/usr/share/doc/sega' | sudo tee -a /etc/sandbox-persistent.sh
```

Record in `$SEGA_DOC/reference/MANIFEST.md` the same use rule as the Game Boy manifest: both repos are `reuse`, under
the licence in their directory (devkitSMS mixes licences per file: read `LICENSES.txt` before reusing anything).

## Part 2 checks

| Check | Command | Expected |
|---|---|---|
| No Python replaced | same as Part 1 | unchanged |
| stable-retro | `python3 -c "from importlib.metadata import version as v; print(v('stable-retro'))"` | `1.0.1` |
| retrotools | `command -v retrotest retrocheck retrosprite retrolevel` | four paths |
| MesenCE owner | `find /opt/mesence ! -user agent \| head -1` | no output |
| GG build | `cd tools/retro/gbdk-skeleton && make TARGETS="gg sms"` | `build/gg/game.gg` and `build/sms/game.sms` |
| GG tests | `make test TARGETS="gg sms"` | `14 passed` |
| GG gate | `make check TARGETS="gg sms"` | `[gg] OK` and `[sms] OK`, PNGs in `out/check/` show the level |
| Gate input | `retrocheck build/sms/game.sms --frames 300 --hold right:150-190 --print player_x` | `player_x = 65` (not 24: 24 means the controller line is missing) |

`tools/retro/gbdk-skeleton/` is a small one-screen platformer built from one source for gb, sms and gg. It is the
worked example of GBDK's cross-platform API, not part of the game: read it for the patterns, then `make clean` it.

If MesenCE aborts at start, run it once by hand to see why:
`DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1 xvfb-run -a /opt/mesence/Mesen --testrunner <rom> <script.lua>`.
Known causes: a missing library from step 11, or `settings.json` absent or not valid JSON.
