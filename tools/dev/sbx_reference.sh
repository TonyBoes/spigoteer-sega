#!/bin/bash
# tools/dev/sbx_reference.sh - the docs/reference half of
# .devcontainer/variants/gameboy/install.sh, for a Docker Sandboxes (sbx)
# microVM. Run with sudo after the toolchain is installed (see
# docs/dev/SANDBOX_SETUP.md). Writes /opt/gameboy (skeletons) and
# /usr/share/doc/gameboy (RGBDS man pages, variant CLAUDE.md, reference
# repos at the commits pinned in reference.txt, MANIFEST.md).
set -euo pipefail

VARIANT_DIR="$(cd "$(dirname "$(readlink -f "$0")")/../../.devcontainer/variants/gameboy" && pwd)"
DOC=/usr/share/doc/gameboy
REF="$DOC/reference"

clone_pinned() {  # <repo owner/name> <sha> <dest>
    local repo=$1 sha=$2 dst=$3
    rm -rf "$dst"; mkdir -p "$dst"
    git -C "$dst" init -q
    git -C "$dst" remote add origin "https://github.com/$repo.git"
    git -C "$dst" fetch -q --depth 1 origin "$sha"
    git -C "$dst" -c advice.detachedHead=false checkout -q FETCH_HEAD
    rm -rf "$dst/.git"
}

echo "==> skeletons"
rm -rf /opt/gameboy && mkdir -p /opt/gameboy
cp -r "$VARIANT_DIR/skeleton" /opt/gameboy/skeleton
cp /usr/local/include/gameboy/hardware.inc /opt/gameboy/skeleton/rgbds/src/hardware.inc

echo "==> RGBDS man pages as text"
mkdir -p "$DOC/rgbds-man"
for m in /usr/local/share/man/man1/rgb*.1 /usr/local/share/man/man5/rgb*.5 \
         /usr/local/share/man/man7/rgbds.7 /usr/local/share/man/man7/gbz80.7; do
    [ -f "$m" ] && groff -mandoc -Tutf8 -P-cbou "$m" > "$DOC/rgbds-man/$(basename "$m").txt" 2>/dev/null || true
done
cp "$VARIANT_DIR/CLAUDE.md" "$DOC/CLAUDE.variant.md"

echo "==> reference repositories"
mkdir -p "$REF"
manifest="$REF/MANIFEST.md"
{
    echo "# Reference material — read the rule before the code"
    echo
    echo "Cloned from pinned commits (.devcontainer/variants/gameboy/reference.txt)."
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
ln -sfn "$REF/pandocs/src" "$DOC/pandocs"
ln -sfn "$REF/gb-asm-tutorial/src" "$DOC/gb-asm-tutorial"
ln -sfn "$REF/gb-opcodes" "$DOC/gb-opcodes"

chown -R root:root "$DOC" /opt/gameboy /opt/sameboy /opt/gbdk /opt/mgbdis
chmod -R a+rX "$DOC" /opt/gameboy
echo "==> done: $(find "$REF" -mindepth 1 -maxdepth 1 -type d | wc -l) reference dirs"
