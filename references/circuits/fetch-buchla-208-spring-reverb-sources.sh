#!/usr/bin/env bash
# Fetches the sources buchla-208-spring-reverb.md was written from into references/circuits/sources/ (not kept in git)
# and checks each is the copy it was read from. A source that changed upstream fails loudly. Moved here 2026-10-22
# from 2sl gate (references/fetch-buchla-208-reverb-sources.sh) when gate 0.6.0 took the spring out. Its own script,
# not fetch-circuit-sources.sh: sound-au.com answers that script's browser User-Agent with 406.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$here/sources"

fetch() {
  local name="$1" url="$2" expected_sha256="$3"
  local out="$here/sources/$name"
  curl -fsSL -o "$out" "$url"
  local actual_sha256
  actual_sha256="$(sha256sum "$out" | cut -d' ' -f1)"
  if [ "$actual_sha256" != "$expected_sha256" ]; then
    echo "$name changed upstream: sha256 $actual_sha256, read from $expected_sha256 ($url)" >&2
    exit 1
  fi
  echo "fetched $out"
}

# Buchla & Associates' schematic B2080-12A, "Model 208 PSS, Output" (card 12), 8-17-73
# (scan courtesy Magnus Danielson, hosted by fluxmonkey.com)
fetch buchla-208-output-schematic-1973.jpg \
  "http://fluxmonkey.com/historicBuchla/buchlaFiles/Buchla_2080_12_200.jpg" \
  787a7b8525c03ba25253dceae18290ee2af72554085509d313d14933164b347c
# Rod Elliott (ESP), "Spring Reverb Tanks Explained and Demystified": Accutronics coil data (Table 1)
fetch sound-au-spring-reverb.htm \
  "https://sound-au.com/articles/reverb.htm" \
  b8240c33d7b72ee9ffd950fe472a16ef7e46d8da20727effc7240737f4d28a77
# Roman Sowa, modularsynthesis.com, "Boops Card 12 Replacement": what the original card 12 does
fetch modularsynthesis-boops-card12.htm \
  "https://modularsynthesis.com/roman/boops_208_card12/boops_card12.htm" \
  c0969a3c6545a5a6f56e96d4ddb3b80a6775e8f9eac4edc526244eca2a2d907d
