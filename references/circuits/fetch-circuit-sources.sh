#!/usr/bin/env bash
# Fetches the sources references/circuits/*.md were written from into references/circuits/sources/ and checks each is the copy
# it was read from (sha256, 2026-10-18 / 2026-10-19). Nothing fetched is kept in git (.gitignore).
# Fails loudly, naming the file, when a download fails or a file changed upstream.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
out_dir="$here/sources"
mkdir -p "$out_dir"
# name | url | sha256
sources=(
  "ltc1060-1060fb.pdf|https://www.komponenten.es.aau.dk/fileadmin/komponenten/Data_Sheet/Switch_Cap/LTC1060.pdf|4114b99dbe5fef8ed1ef7520f69f27209bbbf7cae50a88ef507bd95fb960bf25"
  "mf10-n.pdf|https://www.ti.com/lit/ds/symlink/mf10-n.pdf|0e837564aa0bc5e6b3f78bd95e3fa45b0bf7c8554989e4f76d9d86b3c876079d"
)
failed=0
for entry in "${sources[@]}"; do
  IFS='|' read -r name url expected_sha256 <<< "$entry"
  target="$out_dir/$name"
  if ! curl -fsSL -o "$target" "$url"; then
    echo "FAILED to download $name from $url" >&2
    failed=1
    continue
  fi
  actual_sha256="$(sha256sum "$target" | cut -d' ' -f1)"
  if [ "$actual_sha256" != "$expected_sha256" ]; then
    echo "CHANGED: $name ($url) has sha256 $actual_sha256, the notes were written from $expected_sha256" >&2
    failed=1
  else
    echo "ok $name"
  fi
done
exit "$failed"
