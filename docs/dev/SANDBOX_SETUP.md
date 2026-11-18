# Sandbox setup (Docker Sandboxes / sbx microVM)

How to rebuild Spigoteer's toolchain in an sbx microVM. It replaces the devcontainer image built from
`.devcontainer/variants/gameboy/` (its `install.sh` and `reference.txt` are still the source of the pins).
First done 2026-11-18, on the `agent` user (passwordless sudo), Debian 13 (Docker Hardened Images base), Python 3.14.10.

## Rules for this environment

- **Never let apt replace the image's Python.** It comes from the DHI package `python-3.14-minimal`. Always use
  `--no-install-recommends`, and never install Debian's `python3`, `python3-pip` or `python3-venv` (the variant
  script does; here they are skipped). Dry-run with `apt-get install -s ...` and check no `python` package is in the
  `Inst` lines.
- Python packages go in system-wide with `sudo pip install --break-system-packages`.
- Environment variables persist through `/etc/sandbox-persistent.sh` (sourced before every shell command). No shell
  completions in it.
- Network: Debian, DHI apt, PyPI, npm and GitHub are allowed. Everything below comes from those.
- Clone mode: the repo is a private clone; Tony fetches commits with `git fetch sandbox-<name>`.

## Install (about 5 minutes)

Scratch builds go in any empty directory (`$B` below), not in the repo. `<repo>` is the clone's path.

```bash
# 1. apt (build tools, rgbds deps, ImageMagick, pdftotext, groff)
sudo apt-get update
sudo apt-get install -y --no-install-recommends \
    build-essential cmake bison pkgconf libpng-dev imagemagick poppler-utils jq groff-base

# 2. RGBDS 1.0.3 from the tag
git clone --depth 1 --branch v1.0.3 https://github.com/gbdev/rgbds.git $B/rgbds
cmake -S $B/rgbds -B $B/rgbds/build -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr/local
cmake --build $B/rgbds/build -j16
sudo cmake --install $B/rgbds/build

# 3. hardware.inc v6.0.0
sudo mkdir -p /usr/local/include/gameboy
sudo curl -fsSL -o /usr/local/include/gameboy/hardware.inc \
    https://raw.githubusercontent.com/gbdev/hardware.inc/v6.0.0/hardware.inc

# 4. GBDK-2020 4.5.0 (release tarball) and its tools on PATH
curl -fsSL https://github.com/gbdk-2020/gbdk-2020/releases/download/4.5.0/gbdk-linux64.tar.gz | sudo tar -xz -C /opt
for t in lcc png2asset png2hicolorgb romusage gbcompress bankpack ihxcheck makebin; do
    [ -x /opt/gbdk/bin/$t ] && sudo ln -sf /opt/gbdk/bin/$t /usr/local/bin/$t
done
sudo mkdir -p /usr/share/doc/gameboy
sudo pdftotext -layout /opt/gbdk/gbdk_manual.pdf /usr/share/doc/gameboy/gbdk-manual.txt

# 5. SameBoy 1.0.3 headless tester (boot ROMs sit next to the binary)
git clone --depth 1 --branch v1.0.3 https://github.com/LIJI32/SameBoy.git $B/SameBoy
make -C $B/SameBoy -j16 tester CONF=release
sudo mkdir -p /opt/sameboy && sudo cp $B/SameBoy/build/bin/tester/* /opt/sameboy/
sudo ln -sf /opt/sameboy/sameboy_tester /usr/local/bin/sameboy_tester

# 6. mgbdis at the pinned commit, plus a wrapper /usr/local/bin/mgbdis (mode 0755):
#      #!/bin/sh
#      exec python3 /opt/mgbdis/mgbdis.py "$@"
sudo mkdir -p /opt/mgbdis && cd /opt/mgbdis && sudo git init -q
sudo git remote add origin https://github.com/mattcurrie/mgbdis.git
sudo git fetch --depth 1 origin 95d951a9881a0d7ff1a42a94d1be175da92b1777
sudo git checkout FETCH_HEAD && sudo rm -rf .git

# 7. Python: PyBoy 2.7.0, test stack, and the variant's gbtools (gbtest, gbsprite, lvl2gb, gbcheck)
sudo pip install --break-system-packages "pyboy==2.7.0" pillow numpy pytest pytest-timeout
sudo pip install --break-system-packages <repo>/.devcontainer/variants/gameboy/tools

# 8. Skeletons, RGBDS man pages as text, the 39 reference repos and MANIFEST.md (about 1 minute, 375 MB)
sudo <repo>/tools/dev/sbx_reference.sh

# 9. Environment and paths
echo 'export GBDK_HOME=/opt/gbdk/' >> /etc/sandbox-persistent.sh
echo 'export GAMEBOY_DOC=/usr/share/doc/gameboy' >> /etc/sandbox-persistent.sh
sudo ln -sfn <repo> /workspace      # verify.sh, watch_agents.sh, the agent files and skills assume /workspace

# 10. Git identity: user.name "Tony Boes", user.email Tony's address (ask him; not written here)
git config --global user.name "Tony Boes"
```

Not installed (not needed): Node/npm (Claude Code is the native install), ffmpeg, pytest-xdist
(`tools/dev/ptest.py` shards pytest itself).

Session start (from `CLAUDE.md`): copy `docs/dev/memory_snapshot/*.md` into the auto-memory directory
(`~/.claude/projects/<project>/memory/`), then read the newest `docs/dev/notes/HANDOFF_*.md`.

## Checks and expected results

| Check | Command | Expected |
|---|---|---|
| Python not replaced | `readlink /usr/bin/python3; python3 --version; dpkg -S /usr/bin/python3` | `python3.14`, `Python 3.14.10`, `python-3.14-minimal` |
| RGBDS | `rgbasm --version` | `rgbasm v1.0.3` |
| GBDK | `ls /opt/gbdk/bin/sdcc; echo $GBDK_HOME` | file exists; `/opt/gbdk/` |
| SameBoy | `sameboy_tester 2>&1 \| head -1; ls /opt/sameboy/*_boot.bin` | `SameBoy Tester v1.0.3`; dmg/cgb/sgb/agb boot ROMs |
| Python stack | `python3 -c "from importlib.metadata import version as v; print([v(p) for p in ('pyboy','pillow','numpy','pytest','pytest-timeout')])"` | pyboy `2.7.0` (2.7.0 has no `pyboy.__version__`; the variant's own check would fail on it) |
| gbtools | `command -v gbtest gbsprite lvl2gb gbcheck` | four paths under `/usr/bin` |
| Reference | `ls $GAMEBOY_DOC/reference \| wc -l; ls $GAMEBOY_DOC/pandocs/Specifications.md` | `40` (39 dirs + MANIFEST.md); file exists |
| Pixel-art skill | `ls /home/agent/.claude/skills/gb-pixel-art/SKILL.md` | exists (the host's skills store, mounted) |
| Git identity | `git config user.name; git config user.email` | `Tony Boes`; Tony's address |
| ROM builds | `make` (clean: about 60 s here) | ends with `ROM0 real: ends at 0x3E12, 494 bytes free` |
| Emulator check | `make check` | `[dmg] OK`, `[cgb] OK`, screenshots in `out/check/` show the title screen |
| Test suite | `tools/dev/verify.sh /workspace sbx-setup` (by a gb-runner agent) | `RESULT: PASS`, then `END`, in `out/verify/sbx-setup.log` |

PyBoy prints `UserWarning: Using SDL2 binaries from pysdl2-dll ...` on import. Harmless (headless use).
