#!/usr/bin/env bash
# Fetches the sources for how a Max for Live parameter loads, recalls and resets (references/README.md, "Parameter
# Mode", "live.thisdevice", "Maxobj.getvalueof", "Initialization and undo"; architecture/presets.md, "Neutral, Init,
# and a fresh device"): Cycling '74's Parameter Mode guide, the live.thisdevice and Maxobj references, and Ableton's
# Max for Live Production Guidelines. Kept out of git (references/live-parameter-sources/).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
out="$here/live-parameter-sources"
mkdir -p "$out"
fetch() {
  curl -fsSL -o "$out/$1" "$2"
  echo "fetched $out/$1"
}
fetch parameter-mode.html 'https://docs.cycling74.com/userguide/parameter_mode/'
fetch live.thisdevice.html 'https://docs.cycling74.com/reference/live.thisdevice'
fetch maxobj.html 'https://docs.cycling74.com/apiref/js/maxobj/'
fetch m4l-production-guidelines.md \
  'https://raw.githubusercontent.com/Ableton/maxdevtools/main/m4l-production-guidelines/m4l-production-guidelines.md'
