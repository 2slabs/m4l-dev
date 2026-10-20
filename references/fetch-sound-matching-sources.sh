#!/usr/bin/env bash
# Fetches the sources references/sound-matching.md was written from into references/sound-matching-sources/ and
# checks each is the copy it was read from (sha256, 2026-10-19). PDFs are never committed: the directory is
# gitignored. Fails loudly, naming the file, when a download fails or a file changed upstream.
# arXiv URLs name the version that was read (v1 / v2); an unversioned URL would silently follow a newer one.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
out_dir="$here/sound-matching-sources"
mkdir -p "$out_dir"
# name | url | sha256
sources=(
  "ddsp-engel-iclr2020-2001.04643v1.pdf|https://arxiv.org/pdf/2001.04643v1|41aa87d9710abd0c66837502684d5a5f58e0cb1e34a62eb2d14e25944dbb0856"
  "parallel-wavegan-yamamoto-2019-1910.11480v2.pdf|https://arxiv.org/pdf/1910.11480v2|f91b87aef598450f590a22b08aef92e5ffac03eb172001493dc6c8a9ba2452c4"
  "sound2synth-chen-2022-2205.03043v2.pdf|https://arxiv.org/pdf/2205.03043v2|2c8e99841ca7e287eeb6681cc032eddac61ce039cc903d535f63336e53733a74"
  "turian-henry-pitch-2020-2012.04572v2.pdf|https://arxiv.org/pdf/2012.04572v2|93237aa54303bb78b032ddeeef86458389bb239b351185363e2a6d1f8399265f"
  "shier-percussive-transient-spectral-2023-2309.06649v1.pdf|https://arxiv.org/pdf/2309.06649v1|03a41548d9e19e8185dc3f4c4e75cac4d64c1760b3d65594cd7e631f7df36925"
  "shier-timbre-remapping-nime2024-2407.04547v1.pdf|https://arxiv.org/pdf/2407.04547v1|2acb46fb7501f99c3c1071144d8b03d5c74cfae9e896a66ecd05d400c934db4c"
  "salimi-sound-similarity-metrics-2025-2506.22628v2.pdf|https://arxiv.org/pdf/2506.22628v2|52f51e3f73a076fcc0583d48d6b3dbfe5b5e6e71b660f3e16551f3875f91d65b"
  "yee-king-vst-programming-tetci2018.pdf|https://eprints-gro.gold.ac.uk/22516/1/myk_lf_vsti_programming.pdf|f1f1f8494e47209d26b5e05e8cb14c4591231ef010644f9ffdad64140455e894"
  "hansen-cma-es-tutorial-1604.00772v2.pdf|https://arxiv.org/pdf/1604.00772v2|96645df3058f229084eb70fd9531c601665c1c118a49929aa3b6ceadbf36a223"
  "yin-decheveigne-kawahara-jasa2002.pdf|https://cagnazzo.wp.imt.fr/files/2013/05/2002_JASA_YIN.pdf|0055503a04be6b1453eaf0a768c90d123adb004643a1421e0a542155c6778344"
)
failed=0
for entry in "${sources[@]}"; do
  IFS='|' read -r name url expected_sha256 <<< "$entry"
  target="$out_dir/$name"
  if ! curl -fsSL --retry 3 --retry-delay 5 -o "$target" "$url"; then
    echo "FAILED to download $name from $url" >&2
    rm -f "$target"
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
