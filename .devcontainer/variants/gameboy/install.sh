#!/bin/bash
# variants/gameboy/install.sh — runs as root during the image build.
#
# Installs a complete, OFFLINE Game Boy / Game Boy Color development
# environment: both toolchains (RGBDS assembly, GBDK-2020 C), a headless
# accuracy reference (SameBoy's tester), a scriptable emulator for tests
# (PyBoy), asset converters, the agent-facing helper tools, project
# skeletons, and ~1 GB of reference source and documentation.
#
# Everything is fetched HERE, at build time, when the firewall is not yet
# in force. The variant adds no domains and no ports: the agent works
# entirely behind the DROP policy. See CLAUDE.md for what the agent sees.
#
# Every version is pinned below. To bump one: change it, rebuild, run the
# verification block (it runs automatically at the end), commit.
#
# Env knobs (for testing the script itself, not for projects):
#   GAMEBOY_SKIP_REFERENCE=1   skip the reference-repo clones (~1 GB)
#
set -euo pipefail

# ---- pins ------------------------------------------------------------------
: "${RGBDS_VERSION:=1.0.3}"          # https://github.com/gbdev/rgbds
: "${GBDK_VERSION:=4.5.0}"           # https://github.com/gbdk-2020/gbdk-2020
: "${SAMEBOY_VERSION:=1.0.3}"        # https://github.com/LIJI32/SameBoy
: "${PYBOY_VERSION:=2.7.0}"          # https://pypi.org/project/pyboy  (2.8.x is days old - bump deliberately)
: "${HARDWARE_INC_VERSION:=6.0.0}"   # https://github.com/gbdev/hardware.inc
: "${MGBDIS_COMMIT:=95d951a9881a0d7ff1a42a94d1be175da92b1777}"         # https://github.com/mattcurrie/mgbdis

VARIANT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
DOC=/usr/share/doc/gameboy
REF="$DOC/reference"
export DEBIAN_FRONTEND=noninteractive

log() { printf '\n==> %s\n' "$*"; }
die() { printf 'install.sh: %s\n' "$*" >&2; exit 1; }

# Clone one pinned commit without history, drop .git (MANIFEST records the sha).
clone_pinned() {  # <repo owner/name> <sha> <dest>
    local repo=$1 sha=$2 dst=$3
    rm -rf "$dst"; mkdir -p "$dst"
    git -C "$dst" init -q
    git -C "$dst" remote add origin "https://github.com/$repo.git"
    git -C "$dst" fetch -q --depth 1 origin "$sha"
    git -C "$dst" checkout -q FETCH_HEAD
    rm -rf "$dst/.git"
}

# ---- apt -------------------------------------------------------------------
log "apt packages"
apt-get update -qq
apt-get install -y -qq --no-install-recommends \
    cmake bison pkgconf libpng-dev \
    python3 python3-pip python3-venv \
    imagemagick poppler-utils jq groff-base \
    >/dev/null
rm -rf /var/lib/apt/lists/*

# ---- RGBDS (build from tag; Debian's package predates 1.0) -----------------
log "RGBDS $RGBDS_VERSION"
tmp=$(mktemp -d)
git clone -q --depth 1 --branch "v$RGBDS_VERSION" https://github.com/gbdev/rgbds.git "$tmp/rgbds"
cmake -S "$tmp/rgbds" -B "$tmp/rgbds/build" -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr/local >/dev/null
cmake --build "$tmp/rgbds/build" -j"$(nproc)" >/dev/null
cmake --install "$tmp/rgbds/build" >/dev/null
rm -rf "$tmp"

# ---- hardware.inc ----------------------------------------------------------
log "hardware.inc v$HARDWARE_INC_VERSION"
mkdir -p /usr/local/include/gameboy
curl -fsSL --max-time 60 -o /usr/local/include/gameboy/hardware.inc \
    "https://raw.githubusercontent.com/gbdev/hardware.inc/v$HARDWARE_INC_VERSION/hardware.inc"
grep -q 'rLCDC' /usr/local/include/gameboy/hardware.inc || die "hardware.inc download looks wrong"

# ---- GBDK-2020 (release tarball, built on Ubuntu 22.04; runs on trixie) ----
log "GBDK-2020 $GBDK_VERSION"
rm -rf /opt/gbdk
curl -fsSL --max-time 300 \
    "https://github.com/gbdk-2020/gbdk-2020/releases/download/$GBDK_VERSION/gbdk-linux64.tar.gz" \
    | tar -xz -C /opt
[ -x /opt/gbdk/bin/lcc ] || die "GBDK tarball did not produce /opt/gbdk/bin/lcc"
# Expose the tools the agent calls by name. lcc finds the rest via GBDK_HOME.
for t in lcc png2asset png2hicolorgb romusage gbcompress bankpack ihxcheck makebin; do
    [ -x "/opt/gbdk/bin/$t" ] && ln -sf "/opt/gbdk/bin/$t" "/usr/local/bin/$t"
done
# The manual ships as PDF; the agent reads text.
pdftotext -layout /opt/gbdk/gbdk_manual.pdf "$DOC.gbdk_manual.txt.tmp" 2>/dev/null || true
mkdir -p "$DOC"
[ -s "$DOC.gbdk_manual.txt.tmp" ] && mv "$DOC.gbdk_manual.txt.tmp" "$DOC/gbdk-manual.txt" || rm -f "$DOC.gbdk_manual.txt.tmp"

# ---- SameBoy tester (headless; needs rgbds for its boot ROMs, no SDL) ------
log "SameBoy tester $SAMEBOY_VERSION"
tmp=$(mktemp -d)
git clone -q --depth 1 --branch "v$SAMEBOY_VERSION" https://github.com/LIJI32/SameBoy.git "$tmp/SameBoy"
make -C "$tmp/SameBoy" -j"$(nproc)" tester CONF=release >/dev/null
rm -rf /opt/sameboy && mkdir -p /opt/sameboy
# The tester looks for boot ROMs next to its own (resolved) executable.
cp "$tmp/SameBoy/build/bin/tester/"* /opt/sameboy/
ln -sf /opt/sameboy/sameboy_tester /usr/local/bin/sameboy_tester
rm -rf "$tmp"

# superfamiconv is deliberately absent: upstream moved to Rust (v0.12) and
# rgbgfx (-n 8) and png2asset both pack CGB palettes themselves.

# ---- mgbdis (disassembler) --------------------------------------------------
log "mgbdis ${MGBDIS_COMMIT:0:8}"
clone_pinned mattcurrie/mgbdis "$MGBDIS_COMMIT" /opt/mgbdis
cat > /usr/local/bin/mgbdis <<'EOF'
#!/bin/sh
exec python3 /opt/mgbdis/mgbdis.py "$@"
EOF
chmod 0755 /usr/local/bin/mgbdis

# ---- Python: PyBoy + the gbtools package ----------------------------------
log "PyBoy $PYBOY_VERSION and gbtools"
pip install -q --break-system-packages \
    "pyboy==$PYBOY_VERSION" pillow numpy pytest pytest-timeout
pip install -q --break-system-packages "$VARIANT_DIR/tools"
for t in gbtest gbsprite lvl2gb gbcheck; do
    command -v "$t" >/dev/null || die "gbtools did not install $t"
done

# ---- skeletons ---------------------------------------------------------------
log "project skeletons"
rm -rf /opt/gameboy && mkdir -p /opt/gameboy
cp -r "$VARIANT_DIR/skeleton" /opt/gameboy/skeleton
cp /usr/local/include/gameboy/hardware.inc /opt/gameboy/skeleton/rgbds/src/hardware.inc

# ---- documentation and reference source -----------------------------------
log "documentation"
mkdir -p "$DOC"
mandir=/usr/local/share/man/man1
mkdir -p "$DOC/rgbds-man"
for m in "$mandir"/rgb*.1 /usr/local/share/man/man5/rgb*.5 /usr/local/share/man/man7/rgbds.7 /usr/local/share/man/man7/gbz80.7; do
    [ -f "$m" ] && groff -mandoc -Tutf8 -P-cbou "$m" > "$DOC/rgbds-man/$(basename "$m").txt" 2>/dev/null || true
done
cp "$VARIANT_DIR/CLAUDE.md" "$DOC/CLAUDE.variant.md"

if [ "${GAMEBOY_SKIP_REFERENCE:-0}" = "1" ]; then
    log "GAMEBOY_SKIP_REFERENCE=1: skipping reference clones"
else
    log "reference repositories (this is the slow part)"
    mkdir -p "$REF"
    manifest="$REF/MANIFEST.md"
    {
        echo "# Reference material — read the rule before the code"
        echo
        echo "Cloned at image build from pinned commits (variants/gameboy/reference.txt)."
        echo "History removed; the commit column is the provenance."
        echo
        echo "| use | meaning |"
        echo "|---|---|"
        echo "| **study** | commercial disassembly. Read it to learn technique. Copy NOTHING: no code, graphics, music, text, data. |"
        echo "| **reuse** | open-source. Reusable under its own licence (see LICENSE in the directory; attribute as it requires). |"
        echo "| **docs** | documentation. |"
        echo "| **test** | emulator test suites. For checking emulators, not our ROMs. |"
        echo
        echo "| dir | repo | commit | use | licence | note |"
        echo "|---|---|---|---|---|---|"
    } > "$manifest"
    grep -vE '^\s*(#|$)' "$VARIANT_DIR/reference.txt" | while read -r dir repo sha use note; do
        printf '   %-22s %s\n' "$dir" "$repo"
        clone_pinned "$repo" "$sha" "$REF/$dir"
        lic="none found"
        for f in "$REF/$dir"/LICENSE* "$REF/$dir"/LICENCE* "$REF/$dir"/COPYING*; do
            [ -f "$f" ] && { lic="$(basename "$f") — $(head -c 60 "$f" | tr -d '\r\n' | tr -s ' ')…"; break; }
        done
        printf '| `%s` | %s | `%s` | %s | %s | %s |\n' "$dir" "$repo" "${sha:0:10}" "$use" "$lic" "$note" >> "$manifest"
    done
    # Convenience links to the markdown the agent will open most.
    ln -sfn "$REF/pandocs/src" "$DOC/pandocs"
    ln -sfn "$REF/gb-asm-tutorial/src" "$DOC/gb-asm-tutorial"
    ln -sfn "$REF/gb-opcodes" "$DOC/gb-opcodes"
fi

# Reading material must not be writable by the agent (which has no sudo for
# anything but the firewall, but belt and braces).
chown -R root:root "$DOC" /opt/gameboy /opt/sameboy /opt/gbdk /opt/mgbdis
chmod -R a+rX "$DOC" /opt/gameboy

# ---- verify -------------------------------------------------------------------
# A silent partial install presents later as a confusing agent session.
log "verify"
v=$(rgbasm --version 2>&1);            [[ "$v" == *"$RGBDS_VERSION"* ]]       || die "rgbasm version: $v"
v=$(lcc --version 2>&1 | head -1);     [[ -n "$v" ]]                         || die "lcc does not run"
[ -x /opt/gbdk/bin/sdcc ]                                                     || die "sdcc missing from GBDK"
v=$(sameboy_tester 2>&1 | head -1);    [[ "$v" == *"$SAMEBOY_VERSION"* ]]     || die "sameboy_tester: $v"
[ -f /opt/sameboy/dmg_boot.bin ] && [ -f /opt/sameboy/cgb_boot.bin ]         || die "SameBoy boot ROMs missing"
[ -s "$DOC/rgbds-man/rgbasm.5.txt" ]                                         || echo "WARN: RGBDS man pages not converted"
python3 -c "import pyboy, PIL, numpy, pytest, gbtools; assert pyboy.__version__ == '$PYBOY_VERSION', pyboy.__version__" \
                                                                              || die "python stack"
[ -f "$DOC/gbdk-manual.txt" ]                                                 || echo "WARN: GBDK manual text not produced"
if [ "${GAMEBOY_SKIP_REFERENCE:-0}" != "1" ]; then
    n=$(grep -cvE '^\s*(#|$)' "$VARIANT_DIR/reference.txt")
    got=$(find "$REF" -mindepth 1 -maxdepth 1 -type d | wc -l)
    [ "$got" -eq "$n" ]                                                       || die "expected $n reference dirs, found $got"
    [ -f "$REF/pandocs/src/Specifications.md" ]                              || die "pandocs looks wrong"
fi
log "gameboy variant installed: rgbds $RGBDS_VERSION, gbdk $GBDK_VERSION, sameboy $SAMEBOY_VERSION, pyboy $PYBOY_VERSION"
